"""Cálculos e formatação dos relatórios."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from .modelo import Transacao

NOMES_MESES = (
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)


@dataclass
class Resumo:
    receitas: Decimal
    despesas: Decimal

    @property
    def saldo(self) -> Decimal:
        return self.receitas - self.despesas


def formatar_moeda(valor: Decimal) -> str:
    """Formata no padrão brasileiro: Decimal('1234.5') -> 'R$ 1.234,50'."""
    sinal = "-" if valor < 0 else ""
    texto = f"{abs(valor):,.2f}"                      # '1,234.50'
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sinal}R$ {texto}"


def nome_do_mes(ano: int, mes: int) -> str:
    return f"{NOMES_MESES[mes - 1]}/{ano}"


def filtrar_por_mes(transacoes: list[Transacao], ano: int, mes: int) -> list[Transacao]:
    selecionadas = [t for t in transacoes if t.data.year == ano and t.data.month == mes]
    return sorted(selecionadas, key=lambda t: (t.data, t.id))


def calcular_resumo(transacoes: list[Transacao]) -> Resumo:
    receitas = sum((t.valor for t in transacoes if t.tipo == "receita"), Decimal("0"))
    despesas = sum((t.valor for t in transacoes if t.tipo == "despesa"), Decimal("0"))
    return Resumo(receitas, despesas)


def gastos_por_categoria(transacoes: list[Transacao]) -> dict[str, Decimal]:
    """Soma as despesas de cada categoria, da maior para a menor."""
    totais: dict[str, Decimal] = defaultdict(Decimal)
    for t in transacoes:
        if t.tipo == "despesa":
            totais[t.categoria] += t.valor
    return dict(sorted(totais.items(), key=lambda item: item[1], reverse=True))


def tabela_transacoes(transacoes: list[Transacao]) -> str:
    if not transacoes:
        return "Nenhuma transacao encontrada."

    linhas = [
        f"{'ID':>4}  {'Data':<10}  {'Tipo':<8}  {'Categoria':<14}  {'Valor':>14}  Descricao",
        "-" * 75,
    ]
    for t in transacoes:
        valor = formatar_moeda(t.valor if t.tipo == "receita" else -t.valor)
        linhas.append(
            f"{t.id:>4}  {t.data.strftime('%d/%m/%Y'):<10}  {t.tipo:<8}  "
            f"{t.categoria[:14]:<14}  {valor:>14}  {t.descricao}"
        )
    return "\n".join(linhas)


def texto_resumo(transacoes: list[Transacao], ano: int, mes: int) -> str:
    resumo = calcular_resumo(transacoes)
    linhas = [
        f"=== Resumo de {nome_do_mes(ano, mes)} ===",
        f"  Receitas : {formatar_moeda(resumo.receitas):>16}",
        f"  Despesas : {formatar_moeda(resumo.despesas):>16}",
        f"  Saldo    : {formatar_moeda(resumo.saldo):>16}",
    ]

    categorias = gastos_por_categoria(transacoes)
    if categorias:
        linhas.append("\n  Gastos por categoria:")
        for categoria, total in categorias.items():
            percentual = total / resumo.despesas * 100
            barra = "#" * round(percentual / 5)  # cada '#' = 5%
            linhas.append(f"  {categoria:<14} {formatar_moeda(total):>14}  "
                          f"{percentual:5.1f}%  {barra}")

    if resumo.saldo < 0:
        linhas.append("\n  Atencao: voce gastou mais do que recebeu neste mes!")
    return "\n".join(linhas)
