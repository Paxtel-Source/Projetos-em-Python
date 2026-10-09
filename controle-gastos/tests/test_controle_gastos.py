from datetime import date
from decimal import Decimal

import pytest

from controle_gastos import armazenamento
from controle_gastos.__main__ import main
from controle_gastos.modelo import Transacao, ler_data, ler_mes, ler_tipo, ler_valor
from controle_gastos.relatorios import (
    calcular_resumo, filtrar_por_mes, formatar_moeda, gastos_por_categoria,
)


def transacao(id, tipo, valor, categoria="Outros", data=date(2026, 10, 5)):
    return Transacao(id, tipo, Decimal(valor), categoria, "", data)


@pytest.fixture
def exemplos():
    return [
        transacao(1, "receita", "3000.00", "Salario"),
        transacao(2, "despesa", "1200.00", "Moradia"),
        transacao(3, "despesa", "45.90", "Alimentacao"),
        transacao(4, "despesa", "300.10", "Alimentacao"),
        transacao(5, "despesa", "99.99", "Lazer", date(2026, 9, 30)),  # outro mês
    ]


# ---------- Validação de entradas ----------

@pytest.mark.parametrize("texto, esperado", [
    ("45,90", "45.90"),
    ("1.234,56", "1234.56"),
    ("R$ 10", "10.00"),
    ("1234.5", "1234.50"),
])
def test_ler_valor(texto, esperado):
    assert ler_valor(texto) == Decimal(esperado)


@pytest.mark.parametrize("texto", ["abc", "0", "-5", "", "nan"])
def test_ler_valor_invalido(texto):
    with pytest.raises(ValueError):
        ler_valor(texto)


def test_ler_data():
    assert ler_data("25/12/2026") == date(2026, 12, 25)
    assert ler_data("2026-12-25") == date(2026, 12, 25)
    assert ler_data("") == date.today()
    with pytest.raises(ValueError):
        ler_data("31/02/2026")


def test_ler_mes():
    assert ler_mes("10/2026") == (2026, 10)
    assert ler_mes("2026-10") == (2026, 10)
    with pytest.raises(ValueError):
        ler_mes("13/2026")


def test_ler_tipo():
    assert ler_tipo("D") == "despesa"
    assert ler_tipo("Receita") == "receita"
    with pytest.raises(ValueError):
        ler_tipo("investimento")


# ---------- Relatórios ----------

def test_formatar_moeda():
    assert formatar_moeda(Decimal("1234.5")) == "R$ 1.234,50"
    assert formatar_moeda(Decimal("-0.99")) == "-R$ 0,99"
    assert formatar_moeda(Decimal("1000000")) == "R$ 1.000.000,00"


def test_filtrar_por_mes(exemplos):
    assert [t.id for t in filtrar_por_mes(exemplos, 2026, 10)] == [1, 2, 3, 4]


def test_resumo(exemplos):
    resumo = calcular_resumo(filtrar_por_mes(exemplos, 2026, 10))
    assert resumo.receitas == Decimal("3000.00")
    assert resumo.despesas == Decimal("1546.00")
    assert resumo.saldo == Decimal("1454.00")


def test_gastos_por_categoria(exemplos):
    gastos = gastos_por_categoria(filtrar_por_mes(exemplos, 2026, 10))
    assert gastos == {"Moradia": Decimal("1200.00"), "Alimentacao": Decimal("346.00")}
    assert list(gastos) == ["Moradia", "Alimentacao"]  # maior primeiro


# ---------- Arquivo ----------

def test_salvar_e_carregar(tmp_path, exemplos):
    caminho = tmp_path / "dados.json"
    armazenamento.salvar(exemplos, caminho)
    assert armazenamento.carregar(caminho) == exemplos


def test_carregar_inexistente(tmp_path):
    assert armazenamento.carregar(tmp_path / "nao_existe.json") == []


def test_carregar_corrompido(tmp_path):
    caminho = tmp_path / "ruim.json"
    caminho.write_text("{ isso nao e json", encoding="utf-8")
    with pytest.raises(armazenamento.ErroArquivo):
        armazenamento.carregar(caminho)


# ---------- Linha de comando ----------

def test_fluxo_completo(tmp_path, capsys):
    arquivo = str(tmp_path / "gastos.json")
    assert main(["--arquivo", arquivo, "adicionar", "r", "2500", "-c", "salario",
                 "--data", "01/10/2026"]) == 0
    assert main(["--arquivo", arquivo, "adicionar", "d", "80,50", "-c", "lazer",
                 "--data", "02/10/2026"]) == 0
    assert main(["--arquivo", arquivo, "remover", "2"]) == 0
    assert main(["--arquivo", arquivo, "remover", "2"]) == 1  # já removido

    capsys.readouterr()
    assert main(["--arquivo", arquivo, "resumo", "--mes", "10/2026"]) == 0
    saida = capsys.readouterr().out
    assert "R$ 2.500,00" in saida
    assert "Lazer" not in saida


def test_grafico(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    monkeypatch.chdir(tmp_path)
    assert main(["adicionar", "d", "100", "-c", "Mercado", "--data", "05/10/2026"]) == 0
    assert main(["grafico", "--mes", "10/2026"]) == 0
    assert (tmp_path / "grafico-2026-10.png").stat().st_size > 0
