"""Leitura e gravação das transações em um arquivo JSON."""

import json
import os
from pathlib import Path

from .modelo import Transacao

ARQUIVO_PADRAO = Path("gastos.json")


class ErroArquivo(Exception):
    """O arquivo de dados existe, mas não pôde ser lido."""


def carregar(caminho: Path = ARQUIVO_PADRAO) -> list[Transacao]:
    """Lê as transações do arquivo. Se ele não existir, retorna uma lista vazia."""
    if not caminho.exists():
        return []
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return [Transacao.de_dict(item) for item in dados["transacoes"]]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as erro:
        raise ErroArquivo(f"O arquivo '{caminho}' esta corrompido: {erro}") from erro


def salvar(transacoes: list[Transacao], caminho: Path = ARQUIVO_PADRAO) -> None:
    """Grava as transações de forma segura.

    Primeiro escreve em um arquivo temporário e só depois substitui o original.
    Assim, se o programa travar no meio, o arquivo antigo continua intacto.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")

    conteudo = {"versao": 1, "transacoes": [t.para_dict() for t in transacoes]}
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)

    os.replace(temporario, caminho)


def proximo_id(transacoes: list[Transacao]) -> int:
    return max((t.id for t in transacoes), default=0) + 1
