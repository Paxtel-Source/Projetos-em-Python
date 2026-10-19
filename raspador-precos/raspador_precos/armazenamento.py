"""Lista de produtos (JSON) e histórico de preços (CSV)."""

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ARQUIVO_PRODUTOS = Path("produtos.json")
ARQUIVO_HISTORICO = Path("historico.csv")
CAMPOS_HISTORICO = ["data", "produto", "preco"]


@dataclass
class Produto:
    nome: str
    url: str
    preco_alvo: Decimal | None = None   # avisa quando o preço chegar a este valor
    seletor: str | None = None          # seletor CSS do preço (opcional)

    def para_dict(self) -> dict:
        dados = asdict(self)
        dados["preco_alvo"] = str(self.preco_alvo) if self.preco_alvo is not None else None
        return dados

    @classmethod
    def de_dict(cls, dados: dict) -> "Produto":
        alvo = dados.get("preco_alvo")
        return cls(
            nome=dados["nome"],
            url=dados["url"],
            preco_alvo=Decimal(str(alvo)) if alvo not in (None, "") else None,
            seletor=dados.get("seletor") or None,
        )


@dataclass
class Registro:
    data: datetime
    produto: str
    preco: Decimal


# ---------- Produtos ----------

def carregar_produtos(caminho: Path = ARQUIVO_PRODUTOS) -> list[Produto]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8") as arquivo:
        return [Produto.de_dict(item) for item in json.load(arquivo)]


def salvar_produtos(produtos: list[Produto], caminho: Path = ARQUIVO_PRODUTOS) -> None:
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump([p.para_dict() for p in produtos], arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")


# ---------- Histórico ----------

def registrar_preco(registro: Registro, caminho: Path = ARQUIVO_HISTORICO) -> None:
    """Acrescenta uma linha ao histórico, criando o arquivo com cabeçalho se preciso."""
    novo = not caminho.exists()
    with caminho.open("a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        if novo:
            escritor.writerow(CAMPOS_HISTORICO)
        escritor.writerow([registro.data.isoformat(timespec="seconds"), registro.produto, str(registro.preco)])


def ler_historico(produto: str | None = None, caminho: Path = ARQUIVO_HISTORICO) -> list[Registro]:
    """Lê o histórico, em ordem de data. Pode filtrar por nome do produto."""
    if not caminho.exists():
        return []
    with caminho.open(newline="", encoding="utf-8") as arquivo:
        registros = [
            Registro(datetime.fromisoformat(linha["data"]), linha["produto"], Decimal(linha["preco"]))
            for linha in csv.DictReader(arquivo)
            if produto is None or linha["produto"] == produto
        ]
    return sorted(registros, key=lambda r: r.data)


def ultimo_preco(produto: str, caminho: Path = ARQUIVO_HISTORICO) -> Decimal | None:
    historico = ler_historico(produto, caminho)
    return historico[-1].preco if historico else None
