"""Medidor de força de senhas baseado em entropia."""

import math
import string
from dataclasses import dataclass

from .gerador import SIMBOLOS

# Senhas muito usadas que devem ser sempre consideradas fracas
SENHAS_COMUNS = {
    "123456", "12345678", "123456789", "password", "senha", "senha123",
    "qwerty", "abc123", "111111", "000000", "iloveyou", "admin", "brasil",
}


@dataclass(frozen=True)
class Avaliacao:
    entropia: float
    nivel: str
    pontos: int  # de 0 a 4, usado para desenhar a barra


NIVEIS = [
    (28, "Muito fraca", 0),
    (36, "Fraca", 1),
    (60, "Razoavel", 2),
    (80, "Forte", 3),
    (math.inf, "Muito forte", 4),
]


def tamanho_do_alfabeto(senha: str) -> int:
    """Estima quantos caracteres diferentes poderiam aparecer na senha."""
    alfabeto = 0
    if any(c in string.ascii_lowercase for c in senha):
        alfabeto += 26
    if any(c in string.ascii_uppercase for c in senha):
        alfabeto += 26
    if any(c in string.digits for c in senha):
        alfabeto += 10
    if any(c in SIMBOLOS for c in senha):
        alfabeto += len(SIMBOLOS)
    if any(not c.isascii() or (c not in SIMBOLOS and not c.isalnum()) for c in senha):
        alfabeto += 32  # outros símbolos, espaços e acentos
    return alfabeto


def calcular_entropia(senha: str) -> float:
    """Entropia em bits: tamanho × log2(tamanho do alfabeto).

    Quanto maior, mais tentativas um atacante precisa para adivinhar a senha.
    """
    alfabeto = tamanho_do_alfabeto(senha)
    if not senha or alfabeto == 0:
        return 0.0
    return len(senha) * math.log2(alfabeto)


def avaliar_forca(senha: str) -> Avaliacao:
    """Classifica a senha de 'Muito fraca' a 'Muito forte'."""
    entropia = calcular_entropia(senha)

    # Penalidades para padrões que a fórmula de entropia não enxerga
    if senha.lower() in SENHAS_COMUNS:
        return Avaliacao(entropia, "Muito fraca", 0)
    if senha and len(set(senha)) <= 2:
        entropia = min(entropia, 20.0)  # ex.: "aaaaaaaa" ou "abababab"

    for limite, nivel, pontos in NIVEIS:
        if entropia < limite:
            return Avaliacao(entropia, nivel, pontos)
    raise AssertionError("inalcançável")  # pragma: no cover


def desenhar_barra(avaliacao: Avaliacao, largura: int = 20) -> str:
    """Retorna uma barra de texto, por exemplo: [##########----------]"""
    cheio = round(largura * (avaliacao.pontos + 1) / len(NIVEIS))
    return "[" + "#" * cheio + "-" * (largura - cheio) + "]"
