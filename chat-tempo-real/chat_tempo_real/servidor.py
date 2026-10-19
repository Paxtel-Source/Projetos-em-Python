"""Servidor web: entrega a página do chat e mantém as conexões WebSocket."""

import asyncio
import json
from pathlib import Path

from aiohttp import WSMsgType, web

from .salas import Chat, ErroDoChat

PASTA_ESTATICA = Path(__file__).parent / "static"
CHAVE_CHAT = web.AppKey("chat", Chat)


async def pagina_inicial(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(PASTA_ESTATICA / "index.html")


async def conexao_websocket(request: web.Request) -> web.WebSocketResponse:
    """Uma execução desta função por navegador conectado, enquanto ele estiver aberto."""
    chat = request.app[CHAVE_CHAT]
    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=8 * 1024)
    await ws.prepare(request)

    try:
        async for mensagem in ws:
            if mensagem.type != WSMsgType.TEXT:
                continue
            try:
                dados = json.loads(mensagem.data)
                if not isinstance(dados, dict):
                    raise ValueError
            except ValueError:
                await ws.send_json({"tipo": "erro", "texto": "Mensagem em formato inválido."})
                continue
            try:
                await chat.processar(ws, dados)
            except ErroDoChat as erro:
                await ws.send_json({"tipo": "erro", "texto": str(erro)})
    finally:
        # Sai do chat mesmo se a conexão cair sem aviso. O aiohttp cancela esta
        # função quando o navegador desconecta; o shield garante que a saída
        # termine e que os outros sejam avisados.
        await asyncio.shield(chat.sair(ws))
    return ws


async def _fechar_conexoes(app: web.Application) -> None:
    """Ao desligar o servidor, avisa os navegadores em vez de cortar a conexão."""
    for conexao in list(app[CHAVE_CHAT].participantes):
        await conexao.close(code=1001, message=b"Servidor desligando")


def criar_app() -> web.Application:
    app = web.Application()
    app[CHAVE_CHAT] = Chat()
    app.router.add_get("/", pagina_inicial)
    app.router.add_get("/ws", conexao_websocket)
    app.router.add_static("/static", PASTA_ESTATICA)
    app.on_shutdown.append(_fechar_conexoes)
    return app
