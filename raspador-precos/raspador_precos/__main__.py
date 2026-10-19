"""Linha de comando do monitor de preços.

Exemplos:
    python -m raspador_precos demo
    python -m raspador_precos adicionar "Fone Bluetooth" https://loja.exemplo/fone --alvo 199,90
    python -m raspador_precos verificar
    python -m raspador_precos vigiar --intervalo 60
    python -m raspador_precos historico "Fone Bluetooth"
    python -m raspador_precos grafico "Fone Bluetooth"
"""

import argparse
import sys
import threading
import time
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import armazenamento as dados
from .alertas import carregar_env, enviar_alertas, formatar_moeda, verificar_alerta
from .armazenamento import Produto, Registro
from .coleta import AcessoBloqueado, FalhaNoDownload, baixar_pagina
from .extrator import PrecoNaoEncontrado, extrair_preco, ler_preco_texto


# ---------- Verificação ----------

def verificar(produtos: list[Produto], caminho_historico: Path = dados.ARQUIVO_HISTORICO,
              enviar: bool = True) -> list:
    """Busca o preço de cada produto, grava no histórico e devolve os alertas."""
    alertas = []
    agora = datetime.now()
    for produto in produtos:
        try:
            preco = extrair_preco(baixar_pagina(produto.url), produto.seletor)
        except (AcessoBloqueado, FalhaNoDownload, PrecoNaoEncontrado) as erro:
            print(f"  ✗ {produto.nome}: {erro}")
            continue

        anterior = dados.ultimo_preco(produto.nome, caminho_historico)
        dados.registrar_preco(Registro(agora, produto.nome, preco), caminho_historico)

        variacao = ""
        if anterior is not None and preco != anterior:
            seta = "↓" if preco < anterior else "↑"
            variacao = f"  {seta} antes {formatar_moeda(anterior)}"
        print(f"  • {produto.nome}: {formatar_moeda(preco)}{variacao}")

        alerta = verificar_alerta(produto, preco, anterior)
        if alerta:
            alertas.append(alerta)
            print(f"    🔔 {alerta.motivo}")

    if alertas and enviar:
        canais = enviar_alertas(alertas)
        if canais:
            print(f"  Aviso enviado por {' e '.join(canais)}.")
        else:
            print("  Configure e-mail ou Telegram no arquivo .env para receber os avisos (veja o README).")
    return alertas


# ---------- Comandos ----------

def cmd_listar(args) -> int:
    produtos = dados.carregar_produtos(args.produtos)
    if not produtos:
        print("Nenhum produto cadastrado. Use o comando 'adicionar'.")
        return 0
    for p in produtos:
        ultimo = dados.ultimo_preco(p.nome, args.historico)
        alvo = formatar_moeda(p.preco_alvo) if p.preco_alvo else "sem alvo"
        atual = formatar_moeda(ultimo) if ultimo else "ainda não verificado"
        print(f"• {p.nome}\n    último preço: {atual} | alvo: {alvo}\n    {p.url}")
    return 0


def cmd_adicionar(args) -> int:
    produtos = dados.carregar_produtos(args.produtos)
    if any(p.nome == args.nome for p in produtos):
        print(f"Erro: já existe um produto chamado {args.nome!r}.", file=sys.stderr)
        return 1
    alvo = ler_preco_texto(args.alvo) if args.alvo else None
    produtos.append(Produto(args.nome, args.url, alvo, args.seletor))
    dados.salvar_produtos(produtos, args.produtos)
    print(f"Produto {args.nome!r} adicionado. Rode 'verificar' para buscar o preço.")
    return 0


def cmd_remover(args) -> int:
    produtos = dados.carregar_produtos(args.produtos)
    restantes = [p for p in produtos if p.nome != args.nome]
    if len(restantes) == len(produtos):
        print(f"Erro: nenhum produto chamado {args.nome!r}.", file=sys.stderr)
        return 1
    dados.salvar_produtos(restantes, args.produtos)
    print(f"Produto {args.nome!r} removido. O histórico de preços foi mantido.")
    return 0


def cmd_verificar(args) -> int:
    produtos = dados.carregar_produtos(args.produtos)
    if not produtos:
        print("Nenhum produto cadastrado. Use o comando 'adicionar'.")
        return 1
    print(f"Verificando {len(produtos)} produto(s) às {datetime.now():%H:%M}...")
    verificar(produtos, args.historico)
    return 0


def cmd_vigiar(args) -> int:
    print(f"Vigiando os preços a cada {args.intervalo} minuto(s). Aperte Ctrl+C para parar.")
    try:
        while True:
            cmd_verificar(args)
            time.sleep(args.intervalo * 60)
    except KeyboardInterrupt:
        print("\nParado.")
    return 0


def cmd_historico(args) -> int:
    registros = dados.ler_historico(args.nome, args.historico)
    if not registros:
        print("Ainda não há preços registrados.")
        return 0
    for r in registros:
        print(f"{r.data:%d/%m/%Y %H:%M}  {formatar_moeda(r.preco):>14}  {r.produto}")
    return 0


def cmd_grafico(args) -> int:
    from .grafico import gerar_grafico

    registros = dados.ler_historico(args.nome, args.historico)
    produto = next((p for p in dados.carregar_produtos(args.produtos) if p.nome == args.nome), None)
    destino = Path(f"grafico-{args.nome.lower().replace(' ', '-')}.png")
    try:
        gerar_grafico(args.nome, registros, destino, produto.preco_alvo if produto else None)
    except ValueError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    print(f"Gráfico salvo em {destino}")
    return 0


def cmd_demo(args) -> int:
    """Sobe uma loja de mentira no próprio computador e verifica os preços dela."""
    pasta = Path(__file__).resolve().parent.parent / "loja_demo"
    manipulador = partial(_ManipuladorSilencioso, directory=str(pasta))
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), manipulador)
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    base = f"http://127.0.0.1:{porta}"
    produtos = [
        Produto("Fone Bluetooth", f"{base}/fone.html", ler_preco_texto("200"), ".preco-atual"),
        Produto("Teclado Mecânico", f"{base}/teclado.html", ler_preco_texto("250")),
        Produto("Mouse sem Fio", f"{base}/mouse.html", None, "#preco"),
    ]
    print(f"Loja de demonstração rodando em {base}\n")
    verificar(produtos, Path(args.historico.parent / "historico-demo.csv"), enviar=False)
    servidor.shutdown()
    print("\nO Fone Bluetooth está abaixo do preço alvo, por isso gerou um alerta.")
    print("Veja o README para cadastrar produtos de lojas de verdade.")
    return 0


class _ManipuladorSilencioso(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # não polui o terminal com cada acesso
        pass


# ---------- Argumentos ----------

def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raspador_precos",
                                     description="Acompanha preços de produtos e avisa quando baixam.")
    parser.add_argument("--produtos", type=Path, default=dados.ARQUIVO_PRODUTOS,
                        help="arquivo com a lista de produtos (padrão: produtos.json)")
    parser.add_argument("--historico", type=Path, default=dados.ARQUIVO_HISTORICO,
                        help="arquivo do histórico de preços (padrão: historico.csv)")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("demo", help="testa o programa em uma loja de demonstração").set_defaults(funcao=cmd_demo)
    sub.add_parser("listar", help="mostra os produtos cadastrados").set_defaults(funcao=cmd_listar)

    p = sub.add_parser("adicionar", help="cadastra um produto para acompanhar")
    p.add_argument("nome")
    p.add_argument("url")
    p.add_argument("--alvo", help="preço desejado, ex.: 199,90")
    p.add_argument("--seletor", help="seletor CSS do preço na página, ex.: .preco-atual")
    p.set_defaults(funcao=cmd_adicionar)

    p = sub.add_parser("remover", help="para de acompanhar um produto")
    p.add_argument("nome")
    p.set_defaults(funcao=cmd_remover)

    sub.add_parser("verificar", help="busca os preços agora").set_defaults(funcao=cmd_verificar)

    p = sub.add_parser("vigiar", help="verifica repetidamente, a cada N minutos")
    p.add_argument("--intervalo", type=int, default=60, help="minutos entre verificações (padrão: 60)")
    p.set_defaults(funcao=cmd_vigiar)

    p = sub.add_parser("historico", help="mostra os preços registrados")
    p.add_argument("nome", nargs="?", help="nome do produto (opcional)")
    p.set_defaults(funcao=cmd_historico)

    p = sub.add_parser("grafico", help="gera um gráfico PNG da variação de preço")
    p.add_argument("nome")
    p.set_defaults(funcao=cmd_grafico)

    return parser


def main(argv: list[str] | None = None) -> int:
    carregar_env()
    args = criar_parser().parse_args(argv)
    if getattr(args, "intervalo", 60) < 1:
        print("Erro: o intervalo mínimo é de 1 minuto.", file=sys.stderr)
        return 1
    try:
        return args.funcao(args)
    except ValueError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
