"""Modelo de dados e conversão/validação das entradas do usuário."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

TIPOS = ("receita", "despesa")

CATEGORIAS_SUGERIDAS = (
    "Alimentacao", "Moradia", "Transporte", "Saude",
    "Educacao", "Lazer", "Salario", "Outros",
)


@dataclass
class Transacao:
    id: int
    tipo: str          # "receita" ou "despesa"
    valor: Decimal     # Decimal evita erros de arredondamento com dinheiro
    categoria: str
    descricao: str
    data: date

    def para_dict(self) -> dict:
        """Converte para um dicionário que pode ser salvo em JSON."""
        return {
            "id": self.id,
            "tipo": self.tipo,
            "valor": str(self.valor),  # como texto, para não perder precisão
            "categoria": self.categoria,
            "descricao": self.descricao,
            "data": self.data.isoformat(),
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Transacao":
        return cls(
            id=int(dados["id"]),
            tipo=dados["tipo"],
            valor=Decimal(dados["valor"]),
            categoria=dados["categoria"],
            descricao=dados.get("descricao", ""),
            data=date.fromisoformat(dados["data"]),
        )


# ---------- Conversão das entradas digitadas ----------

def ler_valor(texto: str) -> Decimal:
    """Converte '1.234,56', '45,90', 'R$ 10' ou '1234.56' em Decimal.

    Raises:
        ValueError: se o texto não for um valor positivo.
    """
    limpo = texto.strip().replace("R$", "").replace(" ", "")
    if "," in limpo:  # formato brasileiro: ponto é milhar, vírgula é decimal
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        raise ValueError(f"Valor invalido: '{texto}'.") from None
    if not valor.is_finite() or valor <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    return valor.quantize(Decimal("0.01"))


def ler_data(texto: str | None) -> date:
    """Aceita 'dd/mm/aaaa' ou 'aaaa-mm-dd'. Vazio significa hoje."""
    if not texto or not texto.strip():
        return date.today()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            continue
    raise ValueError(f"Data invalida: '{texto}'. Use dd/mm/aaaa.")


def ler_mes(texto: str | None) -> tuple[int, int]:
    """Aceita 'mm/aaaa' ou 'aaaa-mm' e retorna (ano, mes). Vazio é o mês atual."""
    if not texto or not texto.strip():
        hoje = date.today()
        return hoje.year, hoje.month
    for formato in ("%m/%Y", "%Y-%m"):
        try:
            d = datetime.strptime(texto.strip(), formato)
            return d.year, d.month
        except ValueError:
            continue
    raise ValueError(f"Mes invalido: '{texto}'. Use mm/aaaa.")


def ler_tipo(texto: str) -> str:
    tipo = texto.strip().lower()
    atalhos = {"r": "receita", "d": "despesa"}
    tipo = atalhos.get(tipo, tipo)
    if tipo not in TIPOS:
        raise ValueError("O tipo deve ser 'receita' ou 'despesa'.")
    return tipo


def normalizar_categoria(texto: str) -> str:
    texto = " ".join(texto.split())
    return texto.capitalize() if texto else "Outros"
