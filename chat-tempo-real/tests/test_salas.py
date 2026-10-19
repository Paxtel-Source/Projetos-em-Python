"""Testes das regras do chat, com conexões falsas (sem servidor)."""

import pytest

from chat_tempo_real.salas import (TAMANHO_HISTORICO, Chat, ErroDoChat, validar_apelido,
                                   validar_sala, validar_texto)


class ConexaoFalsa:
    """Guarda tudo o que o servidor mandaria para o navegador."""

    def __init__(self, nome=""):
        self.nome = nome
        self.recebidas: list[dict] = []

    async def send_json(self, dados):
        self.recebidas.append(dados)

    def do_tipo(self, tipo):
        return [m for m in self.recebidas if m["tipo"] == tipo]

    def ultima(self, tipo):
        return self.do_tipo(tipo)[-1]


class ConexaoQuebrada(ConexaoFalsa):
    async def send_json(self, dados):
        raise ConnectionResetError


class Relogio:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora


@pytest.fixture
def relogio():
    return Relogio()


@pytest.fixture
def chat(relogio):
    return Chat(relogio=relogio)


# ---------- Validação ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("Ana", "Ana"), ("  João   Pedro ", "João Pedro"), ("dev_01", "dev_01"), ("Zé-Maria", "Zé-Maria"),
])
def test_apelidos_validos(entrada, esperado):
    assert validar_apelido(entrada) == esperado


@pytest.mark.parametrize("entrada", ["A", "", None, "x" * 21, "<script>", "ana!", "a@b"])
def test_apelidos_invalidos(entrada):
    with pytest.raises(ErroDoChat):
        validar_apelido(entrada)


def test_nome_de_sala_e_normalizado():
    assert validar_sala("Jogos Online") == "jogos-online"
    assert validar_sala("  PYTHON ") == "python"
    for invalida in ["", "sala!", "-sala", "a" * 25, "sala--dupla"]:
        with pytest.raises(ErroDoChat):
            validar_sala(invalida)


def test_texto():
    assert validar_texto("  oi  ") == "oi"
    with pytest.raises(ErroDoChat, match="vazia"):
        validar_texto("   ")
    with pytest.raises(ErroDoChat, match="500"):
        validar_texto("x" * 501)


# ---------- Entrar e sair ----------

async def test_entrar_recebe_boas_vindas(chat):
    ana = ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    boas_vindas = ana.ultima("bem_vindo")
    assert boas_vindas["sala"] == "geral" and boas_vindas["usuarios"] == ["Ana"]
    assert boas_vindas["historico"] == []
    assert {"nome": "geral", "pessoas": 1} in ana.ultima("salas")["salas"]


async def test_outros_sao_avisados(chat):
    ana, leo = ConexaoFalsa(), ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    await chat.entrar(leo, "Leo")
    assert ana.ultima("sistema")["texto"] == "Leo entrou no chat."
    assert ana.ultima("usuarios")["usuarios"] == ["Ana", "Leo"]
    assert not leo.do_tipo("sistema")            # quem entra não recebe o próprio aviso

    await chat.sair(leo)
    assert ana.ultima("sistema")["texto"] == "Leo saiu do chat."
    assert ana.ultima("usuarios")["usuarios"] == ["Ana"]
    await chat.sair(leo)                         # sair duas vezes não dá erro


async def test_apelido_repetido_ignora_maiusculas(chat):
    await chat.entrar(ConexaoFalsa(), "Ana")
    with pytest.raises(ErroDoChat, match="já está em uso"):
        await chat.entrar(ConexaoFalsa(), "ANA")


async def test_apelido_fica_livre_quando_a_pessoa_sai(chat):
    ana = ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    await chat.sair(ana)
    await chat.entrar(ConexaoFalsa(), "Ana")


async def test_nao_entra_duas_vezes(chat):
    ana = ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    with pytest.raises(ErroDoChat, match="já entrou"):
        await chat.entrar(ana, "Outra")


# ---------- Mensagens ----------

async def test_mensagem_vai_so_para_a_sala(chat):
    ana, leo, bia = ConexaoFalsa(), ConexaoFalsa(), ConexaoFalsa()
    await chat.entrar(ana, "Ana", "python")
    await chat.entrar(leo, "Leo", "python")
    await chat.entrar(bia, "Bia", "geral")
    await chat.enviar_mensagem(ana, "  print('oi')  ")

    for conexao in (ana, leo):
        mensagem = conexao.ultima("mensagem")
        assert mensagem["apelido"] == "Ana" and mensagem["texto"] == "print('oi')"
        assert mensagem["horario"].endswith("+00:00")
    assert not bia.do_tipo("mensagem")


async def test_historico_para_quem_chega_depois(chat):
    ana = ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    for i in range(TAMANHO_HISTORICO + 5):
        chat.relogio.agora += 2                  # espaça as mensagens para não cair no limite
        await chat.enviar_mensagem(ana, f"mensagem {i}")

    leo = ConexaoFalsa()
    await chat.entrar(leo, "Leo")
    historico = leo.ultima("bem_vindo")["historico"]
    assert len(historico) == TAMANHO_HISTORICO   # só as últimas 50
    assert historico[0]["texto"] == "mensagem 5"
    assert historico[-1]["texto"] == f"mensagem {TAMANHO_HISTORICO + 4}"


async def test_limite_de_mensagens(chat, relogio):
    ana = ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    for _ in range(5):
        await chat.enviar_mensagem(ana, "spam")
    with pytest.raises(ErroDoChat, match="Calma"):
        await chat.enviar_mensagem(ana, "spam")
    relogio.agora += 5.1                         # passou a janela de 5 segundos
    await chat.enviar_mensagem(ana, "voltei")
    assert ana.ultima("mensagem")["texto"] == "voltei"


async def test_digitando_vai_para_os_outros(chat):
    ana, leo = ConexaoFalsa(), ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    await chat.entrar(leo, "Leo")
    await chat.digitando(ana)
    assert leo.ultima("digitando") == {"tipo": "digitando", "apelido": "Ana"}
    assert not ana.do_tipo("digitando")


async def test_conexao_quebrada_nao_atrapalha_as_outras(chat):
    ana, quebrada = ConexaoFalsa(), ConexaoQuebrada()
    await chat.entrar(ana, "Ana")
    await chat.entrar(quebrada, "Quebrada")
    await chat.enviar_mensagem(ana, "alguém aí?")
    assert ana.ultima("mensagem")["texto"] == "alguém aí?"


# ---------- Salas ----------

async def test_trocar_de_sala(chat):
    ana, leo = ConexaoFalsa(), ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    await chat.entrar(leo, "Leo")
    await chat.trocar_sala(ana, "python")

    assert ana.ultima("bem_vindo")["sala"] == "python"
    assert leo.ultima("sistema")["texto"] == "Ana foi para a sala #python."
    assert leo.ultima("usuarios")["usuarios"] == ["Leo"]
    salas = {s["nome"]: s["pessoas"] for s in leo.ultima("salas")["salas"]}
    assert salas["geral"] == 1 and salas["python"] == 1

    await chat.enviar_mensagem(leo, "oi?")
    assert not ana.do_tipo("mensagem")


async def test_sala_criada_some_quando_esvazia(chat):
    ana, leo = ConexaoFalsa(), ConexaoFalsa()
    await chat.entrar(ana, "Ana")
    await chat.entrar(leo, "Leo")
    await chat.trocar_sala(ana, "Jogos Online")
    assert "jogos-online" in chat.salas
    nomes = [s["nome"] for s in leo.ultima("salas")["salas"]]
    assert nomes == ["geral", "python", "linguagem-c", "ajuda", "jogos-online"]

    await chat.trocar_sala(ana, "geral")
    assert "jogos-online" not in chat.salas
    await chat.trocar_sala(ana, "geral")         # já está nela: nada acontece

    await chat.sair(ana)
    await chat.sair(leo)
    assert "geral" in chat.salas                 # salas fixas ficam mesmo vazias


# ---------- Protocolo ----------

async def test_processar_exige_entrar_primeiro(chat):
    with pytest.raises(ErroDoChat, match="apelido"):
        await chat.processar(ConexaoFalsa(), {"tipo": "mensagem", "texto": "oi"})


async def test_processar_tipo_desconhecido(chat):
    ana = ConexaoFalsa()
    await chat.processar(ana, {"tipo": "entrar", "apelido": "Ana"})
    with pytest.raises(ErroDoChat, match="desconhecido"):
        await chat.processar(ana, {"tipo": "hackear"})
    await chat.processar(ana, {"tipo": "mensagem", "texto": "oi"})
    assert ana.ultima("mensagem")["texto"] == "oi"
