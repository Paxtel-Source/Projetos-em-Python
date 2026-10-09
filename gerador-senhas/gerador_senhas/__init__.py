"""Gerador de senhas seguras com medidor de força."""

from .forca import avaliar_forca, calcular_entropia
from .gerador import gerar_senha

__all__ = ["gerar_senha", "avaliar_forca", "calcular_entropia"]
__version__ = "1.0.0"
