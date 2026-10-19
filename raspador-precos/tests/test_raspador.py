from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from raspador_precos import alertas, armazenamento, coleta
from raspador_precos.__main__ import main, verificar
from raspador_precos.armazenamento import Produto, Registro
from raspador_precos.extrator import PrecoNaoEncontrado, extrair_preco, ler_preco_texto

D = Decimal


# ---------- Leitura de preços ----------

@pytest.mark.parametrize("texto, esperado", [
    ("R$ 1.299,90", "1299.90"),
    ("R$\xa049,90", "49.90"),
    ("por R$ 49 à vista", "49.00"),
    ("1299.90", "1299.90"),
    ("1.299", "1299.00"),
    ("R$ 1.299.000,00", "1299000.00"),
    ("12x de R$ 10,00", "12.00"),     # pega o primeiro número: use um seletor preciso
])
def test_ler_preco_texto(texto, esperado):
    assert ler_preco_texto(texto) == D(esperado)


def test_ler_preco_sem_numero():
    with pytest.raises(ValueError):
        ler_preco_texto("Indisponível")


def test_extrair_com_seletor():
    html = '<div><span class="antigo">R$ 300,00</span><span class="atual">R$ 249,90</span></div>'
    assert extrair_preco(html, ".atual") == D("249.90")


def test_extrair_de_atributo_content():
    html = '<meta itemprop="price" content="99.50"><span itemprop="price" content="99.50">R$ 99,50</span>'
    assert extrair_preco(html, "[itemprop=price]") == D("99.50")


def test_extrair_json_ld_sem_seletor():
    html = '''<script type="application/ld+json">
      {"@graph": [{"@type": "WebPage"},
                  {"@type": "Product", "offers": [{"price": 1549.0}]}]}
    </script>'''
    assert extrair_preco(html) == D("1549.00")


def test_extrair_falha_com_mensagem_clara():
    with pytest.raises(PrecoNaoEncontrado, match="seletor"):
        extrair_preco("<p>sem preço</p>", ".preco")
    with pytest.raises(PrecoNaoEncontrado, match="dados estruturados"):
        extrair_preco("<p>sem preço</p>")


# ---------- robots.txt ----------

class RespostaFalsa:
    def __init__(self, texto="", status=200):
        self.text, self.status_code = texto, status
        self.ok = status < 400
        self.encoding = "utf-8"

    def raise_for_status(self):
        if not self.ok:
            import requests
            raise requests.HTTPError(response=self)


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    """Nos testes não há pausa entre acessos e o cache de robots.txt começa vazio."""
    monkeypatch.setattr(coleta, "PAUSA_ENTRE_ACESSOS", 0)
    coleta._regras_do_site.cache_clear()


def test_robots_bloqueia(monkeypatch):
    def get(url, **kwargs):
        if url.endswith("/robots.txt"):
            return RespostaFalsa("User-agent: *\nDisallow: /privado/\n")
        return RespostaFalsa("<p>ok</p>")
    monkeypatch.setattr(coleta.requests, "get", get)

    assert coleta.pode_acessar("https://loja.exemplo/produto/1")
    assert not coleta.pode_acessar("https://loja.exemplo/privado/x")
    with pytest.raises(coleta.AcessoBloqueado):
        coleta.baixar_pagina("https://loja.exemplo/privado/x")
    assert coleta.baixar_pagina("https://loja.exemplo/produto/1") == "<p>ok</p>"


def test_erro_http_vira_mensagem(monkeypatch):
    def get(url, **kwargs):
        return RespostaFalsa("", 404) if not url.endswith("robots.txt") else RespostaFalsa("")
    monkeypatch.setattr(coleta.requests, "get", get)
    with pytest.raises(coleta.FalhaNoDownload, match="404"):
        coleta.baixar_pagina("https://loja.exemplo/sumiu")


# ---------- Armazenamento ----------

def test_produtos_ida_e_volta(tmp_path):
    caminho = tmp_path / "produtos.json"
    produtos = [Produto("A", "https://a", D("10.50"), ".preco"), Produto("B", "https://b")]
    armazenamento.salvar_produtos(produtos, caminho)
    assert armazenamento.carregar_produtos(caminho) == produtos


def test_historico(tmp_path):
    caminho = tmp_path / "historico.csv"
    agora = datetime(2026, 10, 1, 12, 0)
    armazenamento.registrar_preco(Registro(agora + timedelta(days=1), "A", D("9.90")), caminho)
    armazenamento.registrar_preco(Registro(agora, "A", D("12.00")), caminho)
    armazenamento.registrar_preco(Registro(agora, "B", D("5.00")), caminho)

    historico_a = armazenamento.ler_historico("A", caminho)
    assert [r.preco for r in historico_a] == [D("12.00"), D("9.90")]   # ordenado por data
    assert armazenamento.ultimo_preco("A", caminho) == D("9.90")
    assert armazenamento.ultimo_preco("C", caminho) is None
    assert len(armazenamento.ler_historico(caminho=caminho)) == 3


# ---------- Alertas ----------

def test_alerta_preco_alvo():
    p = Produto("Fone", "https://x", D("200"))
    alerta = alertas.verificar_alerta(p, D("189.90"), None)
    assert alerta and "alvo" in alerta.motivo


def test_alerta_queda():
    p = Produto("Fone", "https://x")
    alerta = alertas.verificar_alerta(p, D("90"), D("100"))
    assert alerta and "10%" in alerta.motivo


def test_sem_alerta():
    p = Produto("Fone", "https://x", D("50"))
    assert alertas.verificar_alerta(p, D("100"), D("100")) is None
    assert alertas.verificar_alerta(p, D("110"), D("100")) is None


def test_carregar_env_nao_sobrescreve(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comentário\nEMAIL_REMETENTE='eu@exemplo.com'\nTELEGRAM_TOKEN=123\n", encoding="utf-8")
    monkeypatch.delenv("EMAIL_REMETENTE", raising=False)
    monkeypatch.setenv("TELEGRAM_TOKEN", "do-sistema")
    alertas.carregar_env(env)
    import os
    assert os.environ["EMAIL_REMETENTE"] == "eu@exemplo.com"
    assert os.environ["TELEGRAM_TOKEN"] == "do-sistema"


def test_envio_email(monkeypatch):
    enviados = []

    class SMTPFalso:
        def __init__(self, servidor, porta, timeout):
            self.servidor = servidor
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self): pass
        def login(self, usuario, senha): self.usuario = usuario
        def send_message(self, msg): enviados.append(msg)

    monkeypatch.setattr(alertas.smtplib, "SMTP", SMTPFalso)
    monkeypatch.setenv("EMAIL_REMETENTE", "eu@exemplo.com")
    monkeypatch.setenv("EMAIL_SENHA", "senha-de-app")
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)

    alerta = alertas.Alerta(Produto("Fone", "https://x"), D("10"), "baixou")
    assert alertas.enviar_alertas([alerta]) == ["e-mail"]
    assert "Fone" in enviados[0]["Subject"]
    assert "R$ 10,00" in enviados[0].get_content()


def test_sem_canais_configurados(monkeypatch):
    for chave in ("EMAIL_REMETENTE", "EMAIL_SENHA", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"):
        monkeypatch.delenv(chave, raising=False)
    alerta = alertas.Alerta(Produto("Fone", "https://x"), D("10"), "baixou")
    assert alertas.enviar_alertas([alerta]) == []


# ---------- Fluxo completo ----------

def test_verificar_registra_e_alerta(tmp_path, monkeypatch, capsys):
    paginas = {"https://loja.exemplo/fone": '<span class="p">R$ 150,00</span>'}
    monkeypatch.setattr("raspador_precos.__main__.baixar_pagina", lambda url: paginas[url])
    historico = tmp_path / "h.csv"
    produto = Produto("Fone", "https://loja.exemplo/fone", None, ".p")

    assert verificar([produto], historico, enviar=False) == []        # 1ª vez: sem comparação
    paginas["https://loja.exemplo/fone"] = '<span class="p">R$ 120,00</span>'
    alertas_gerados = verificar([produto], historico, enviar=False)
    assert len(alertas_gerados) == 1 and "20%" in alertas_gerados[0].motivo
    assert "antes R$ 150,00" in capsys.readouterr().out
    assert len(armazenamento.ler_historico("Fone", historico)) == 2


def test_cli_adicionar_listar_remover(tmp_path, capsys):
    base = ["--produtos", str(tmp_path / "p.json"), "--historico", str(tmp_path / "h.csv")]
    assert main(base + ["adicionar", "Fone", "https://x", "--alvo", "199,90"]) == 0
    assert main(base + ["adicionar", "Fone", "https://y"]) == 1          # nome repetido
    assert main(base + ["listar"]) == 0
    saida = capsys.readouterr().out
    assert "R$ 199,90" in saida and "ainda não verificado" in saida
    assert main(base + ["remover", "Fone"]) == 0
    assert main(base + ["remover", "Fone"]) == 1


def test_demo_completa(tmp_path, capsys):
    """Sobe a loja de demonstração de verdade (servidor local) e verifica os 3 produtos."""
    assert main(["--historico", str(tmp_path / "h.csv"), "demo"]) == 0
    saida = capsys.readouterr().out
    assert "Fone Bluetooth: R$ 189,90" in saida
    assert "Teclado Mecânico: R$ 279,90" in saida
    assert "Mouse sem Fio: R$ 89,90" in saida
    assert "chegou ao preço alvo" in saida
