"""Inicia o servidor do chat.

Exemplos:
    python -m chat_tempo_real
    python -m chat_tempo_real --porta 9000
    python -m chat_tempo_real --host 0.0.0.0     # outras pessoas da sua rede podem entrar
"""

import argparse
import socket
import sys

from aiohttp import web

from .servidor import criar_app


def ip_na_rede_local() -> str | None:
    """Descobre o IP deste computador na rede (sem enviar nada pela internet)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chat_tempo_real", description="Chat em tempo real com WebSockets.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="endereço do servidor; use 0.0.0.0 para aceitar outros computadores da rede")
    parser.add_argument("--porta", type=int, default=8080, help="porta do servidor (padrão: 8080)")
    args = parser.parse_args(argv)

    print(f"Chat rodando em http://127.0.0.1:{args.porta}")
    if args.host == "0.0.0.0" and (ip := ip_na_rede_local()):
        print(f"Na mesma rede, abra http://{ip}:{args.porta}")
    print("Aperte Ctrl+C para parar.")
    try:
        web.run_app(criar_app(), host=args.host, port=args.porta, print=None)
    except OSError as erro:
        print(f"Erro: não foi possível usar a porta {args.porta} ({erro.strerror}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
