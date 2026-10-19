"""Baixa páginas respeitando as regras do site (robots.txt) e com intervalo entre acessos."""

import time
from functools import lru_cache
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

# O robô se identifica com um nome próprio, em vez de fingir ser um navegador
AGENTE = "RaspadorPrecosEstudante/1.0 (+https://github.com/Paxtel-Source/Projetos-em-Python)"
TEMPO_LIMITE = 15          # segundos esperando a resposta
PAUSA_ENTRE_ACESSOS = 2.0  # segundos entre dois acessos ao mesmo site

_ultimo_acesso: dict[str, float] = {}


class AcessoBloqueado(Exception):
    """O robots.txt do site não permite acessar essa página."""


class FalhaNoDownload(Exception):
    """A página não pôde ser baixada (sem internet, erro do site etc.)."""


@lru_cache(maxsize=64)
def _regras_do_site(raiz: str) -> RobotFileParser:
    """Baixa e guarda o robots.txt de cada site (uma vez por execução)."""
    regras = RobotFileParser()
    try:
        resposta = requests.get(f"{raiz}/robots.txt", headers={"User-Agent": AGENTE}, timeout=TEMPO_LIMITE)
    except requests.RequestException:
        regras.parse([])                  # sem robots.txt acessível: nada é proibido
        return regras

    if resposta.status_code in (401, 403):
        regras.parse(["User-agent: *", "Disallow: /"])   # site fechado para robôs
    elif resposta.ok:
        regras.parse(resposta.text.splitlines())
    else:
        regras.parse([])
    return regras


def pode_acessar(url: str) -> bool:
    """Confere no robots.txt se o site permite que robôs acessem a URL."""
    partes = urlsplit(url)
    return _regras_do_site(f"{partes.scheme}://{partes.netloc}").can_fetch(AGENTE, url)


def _esperar_a_vez(site: str) -> None:
    """Garante um intervalo mínimo entre dois acessos ao mesmo site."""
    passou = time.monotonic() - _ultimo_acesso.get(site, 0)
    if passou < PAUSA_ENTRE_ACESSOS:
        time.sleep(PAUSA_ENTRE_ACESSOS - passou)
    _ultimo_acesso[site] = time.monotonic()


def baixar_pagina(url: str) -> str:
    """Devolve o HTML da página.

    Raises:
        AcessoBloqueado: se o robots.txt proibir o acesso.
        FalhaNoDownload: se a página não puder ser baixada.
    """
    if not pode_acessar(url):
        raise AcessoBloqueado(f"O site não permite robôs nesta página (robots.txt): {url}")

    _esperar_a_vez(urlsplit(url).netloc)
    try:
        resposta = requests.get(url, headers={"User-Agent": AGENTE}, timeout=TEMPO_LIMITE)
        resposta.raise_for_status()
    except requests.Timeout:
        raise FalhaNoDownload(f"O site demorou mais de {TEMPO_LIMITE}s para responder: {url}") from None
    except requests.HTTPError as erro:
        raise FalhaNoDownload(f"O site respondeu com erro {erro.response.status_code}: {url}") from None
    except requests.RequestException:
        raise FalhaNoDownload(f"Não foi possível acessar {url}. Confira a internet e o endereço.") from None

    resposta.encoding = resposta.encoding or resposta.apparent_encoding
    return resposta.text
