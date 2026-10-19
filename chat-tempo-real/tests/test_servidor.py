"""Testes com o servidor de verdade e conexões WebSocket (pytest-aiohttp)."""

import asyncio

import pytest

from chat_tempo_real.servidor import CHAVE_CHAT, criar_app


@pytest.fixture
async def cliente(aiohttp_client):
    return await aiohttp_client(criar_app())


async def receber_ate(ws, tipo, limite=2.0):
    """Lê mensagens até chegar uma do tipo pedido."""
    async def procurar():
        while True:
            mensagem = await ws.receive_json()
            if mensagem["tipo"] == tipo:
                return mensagem
    return await asyncio.wait_for(procurar(), limite)


async def entrar(cliente, apelido, sala="geral"):
    ws = await cliente.ws_connect("/ws")
    await ws.send_json({"tipo": "entrar", "apelido": apelido, "sala": sala})
    await receber_ate(ws, "bem_vindo")
    return ws


async def test_pagina_e_arquivos_estaticos(cliente):
    resposta = await cliente.get("/")
    assert resposta.status == 200
    assert "Chat em Tempo Real" in await resposta.text()
    for arquivo in ("app.js", "style.css"):
        assert (await cliente.get(f"/static/{arquivo}")).status == 200


async def test_conversa_entre_dois_navegadores(cliente):
    ana = await entrar(cliente, "Ana")
    leo = await entrar(cliente, "Leo")
    assert (await receber_ate(ana, "sistema"))["texto"] == "Leo entrou no chat."

    await leo.send_json({"tipo": "mensagem", "texto": "Olá, Ana!"})
    for ws in (ana, leo):
        mensagem = await receber_ate(ws, "mensagem")
        assert mensagem["apelido"] == "Leo" and mensagem["texto"] == "Olá, Ana!"

    await leo.close()
    assert (await receber_ate(ana, "sistema"))["texto"] == "Leo saiu do chat."
    await ana.close()


async def test_quem_chega_recebe_o_historico(cliente):
    ana = await entrar(cliente, "Ana")
    await ana.send_json({"tipo": "mensagem", "texto": "primeira"})
    await receber_ate(ana, "mensagem")

    leo = await cliente.ws_connect("/ws")
    await leo.send_json({"tipo": "entrar", "apelido": "Leo"})
    boas_vindas = await receber_ate(leo, "bem_vindo")
    assert [m["texto"] for m in boas_vindas["historico"]] == ["primeira"]
    assert boas_vindas["usuarios"] == ["Ana", "Leo"]
    await ana.close()
    await leo.close()


async def test_erros_voltam_para_o_navegador(cliente):
    ws = await cliente.ws_connect("/ws")
    await ws.send_str("isto não é JSON")
    assert (await ws.receive_json())["texto"] == "Mensagem em formato inválido."
    await ws.send_str("[1, 2]")
    assert (await ws.receive_json())["tipo"] == "erro"
    await ws.send_json({"tipo": "mensagem", "texto": "oi"})
    assert "apelido" in (await ws.receive_json())["texto"]
    await ws.send_json({"tipo": "entrar", "apelido": "x"})
    assert "2 a 20" in (await ws.receive_json())["texto"]

    # A conexão continua aberta e funcionando depois dos erros
    await ws.send_json({"tipo": "entrar", "apelido": "Ana"})
    assert (await receber_ate(ws, "bem_vindo"))["apelido"] == "Ana"
    await ws.close()


async def test_apelido_em_uso(cliente):
    ana = await entrar(cliente, "Ana")
    outra = await cliente.ws_connect("/ws")
    await outra.send_json({"tipo": "entrar", "apelido": "ana"})
    assert "já está em uso" in (await receber_ate(outra, "erro"))["texto"]
    await ana.close()
    await outra.close()


async def test_queda_da_conexao_libera_o_apelido(cliente):
    ana = await entrar(cliente, "Ana")
    await ana.close()
    chat = cliente.server.app[CHAVE_CHAT]
    for _ in range(200):                         # espera até 2 s o servidor perceber
        if not chat.participantes:
            break
        await asyncio.sleep(0.01)
    assert not chat.participantes
    nova = await entrar(cliente, "Ana")
    await nova.close()
