"""Encontra o preço dentro do HTML de uma página de produto."""

import json
import re
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup


class PrecoNaoEncontrado(Exception):
    """A página foi baixada, mas não foi possível achar o preço nela."""


def ler_preco_texto(texto: str) -> Decimal:
    """Converte textos como "R$ 1.299,90", "1299.90" ou "por R$ 49" em Decimal.

    Raises:
        ValueError: se não houver um número no texto.
    """
    encontrado = re.search(r"\d[\d.,]*", texto.replace("\xa0", " "))
    if not encontrado:
        raise ValueError(f"Nenhum número encontrado em: {texto!r}")
    numero = encontrado.group().rstrip(".,")

    if "," in numero:
        # Formato brasileiro: ponto separa milhar e vírgula separa centavos
        numero = numero.replace(".", "").replace(",", ".")
    elif numero.count(".") > 1 or re.fullmatch(r"\d{1,3}(\.\d{3})+", numero):
        # "1.299" ou "1.299.000": os pontos são de milhar
        numero = numero.replace(".", "")

    try:
        return Decimal(numero).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Preço inválido: {texto!r}") from None


def _preco_json_ld(sopa: BeautifulSoup) -> Decimal | None:
    """Procura o preço nos dados estruturados (schema.org) que muitas lojas publicam.

    Exemplo de bloco procurado:
        <script type="application/ld+json">
          {"@type": "Product", "offers": {"price": "1299.90"}}
        </script>
    """
    for bloco in sopa.find_all("script", type="application/ld+json"):
        try:
            dados = json.loads(bloco.string or "")
        except json.JSONDecodeError:
            continue

        # O bloco pode ser um objeto, uma lista ou ter um "@graph" com vários itens
        pendentes = dados if isinstance(dados, list) else [dados]
        while pendentes:
            item = pendentes.pop()
            if not isinstance(item, dict):
                continue
            pendentes.extend(item.get("@graph", []))
            ofertas = item.get("offers")
            if isinstance(ofertas, dict):
                ofertas = [ofertas]
            for oferta in ofertas or []:
                preco = oferta.get("price") or oferta.get("lowPrice")
                if preco is not None:
                    return ler_preco_texto(str(preco))
    return None


def extrair_preco(html: str, seletor: str | None = None) -> Decimal:
    """Devolve o preço do produto encontrado no HTML.

    Se houver um seletor CSS (por exemplo ".preco-atual"), usa o texto do
    elemento. Sem seletor, procura nos dados estruturados da página.

    Raises:
        PrecoNaoEncontrado: se o preço não for encontrado.
    """
    sopa = BeautifulSoup(html, "html.parser")

    if seletor:
        elemento = sopa.select_one(seletor)
        if elemento is None:
            raise PrecoNaoEncontrado(f"Nenhum elemento combina com o seletor {seletor!r}.")
        # Alguns sites guardam o valor em um atributo, como content="1299.90"
        texto = elemento.get("content") or elemento.get_text(" ", strip=True)
        try:
            return ler_preco_texto(texto)
        except ValueError as erro:
            raise PrecoNaoEncontrado(str(erro)) from None

    preco = _preco_json_ld(sopa)
    if preco is None:
        raise PrecoNaoEncontrado(
            "A página não tem dados estruturados de preço. Informe um seletor CSS para o produto."
        )
    return preco
