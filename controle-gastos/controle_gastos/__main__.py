"""Interface de linha de comando.

Sem argumentos, abre um menu interativo:
    python -m controle_gastos

Ou use os comandos diretos:
    python -m controle_gastos adicionar despesa 45,90 -c Alimentacao -d "Mercado"
    python -m controle_gastos listar --mes 10/2026
    python -m controle_gastos resumo
    python -m controle_gastos grafico
    python -m controle_gastos remover 3
"""

import argparse
import sys
from pathlib import Path

from . import armazenamento
from .armazenamento import ErroArquivo
from .modelo import (
    CATEGORIAS_SUGERIDAS, Transacao, ler_data, ler_mes, ler_tipo, ler_valor,
    normalizar_categoria,
)
from .relatorios import (
    filtrar_por_mes, formatar_moeda, gastos_por_categoria, nome_do_mes,
    tabela_transacoes, texto_resumo,
)


# ---------- Ações (usadas tanto pelos comandos quanto pelo menu) ----------

def acao_adicionar(caminho: Path, tipo: str, valor: str, categoria: str = "",
                   descricao: str = "", data: str = "") -> None:
    transacoes = armazenamento.carregar(caminho)
    nova = Transacao(
        id=armazenamento.proximo_id(transacoes),
        tipo=ler_tipo(tipo),
        valor=ler_valor(valor),
        categoria=normalizar_categoria(categoria),
        descricao=descricao.strip(),
        data=ler_data(data),
    )
    transacoes.append(nova)
    armazenamento.salvar(transacoes, caminho)
    print(f"{nova.tipo.capitalize()} de {formatar_moeda(nova.valor)} registrada "
          f"(ID {nova.id}, {nova.data.strftime('%d/%m/%Y')}).")


def acao_listar(caminho: Path, mes: str = "") -> None:
    ano, m = ler_mes(mes)
    print(f"\nTransacoes de {nome_do_mes(ano, m)}:\n")
    print(tabela_transacoes(filtrar_por_mes(armazenamento.carregar(caminho), ano, m)))


def acao_resumo(caminho: Path, mes: str = "") -> None:
    ano, m = ler_mes(mes)
    do_mes = filtrar_por_mes(armazenamento.carregar(caminho), ano, m)
    print()
    print(texto_resumo(do_mes, ano, m))


def acao_remover(caminho: Path, id_texto: str) -> None:
    try:
        id_alvo = int(id_texto)
    except ValueError:
        raise ValueError("O ID deve ser um numero inteiro.") from None

    transacoes = armazenamento.carregar(caminho)
    restantes = [t for t in transacoes if t.id != id_alvo]
    if len(restantes) == len(transacoes):
        raise ValueError(f"Nenhuma transacao com ID {id_alvo}.")
    armazenamento.salvar(restantes, caminho)
    print(f"Transacao {id_alvo} removida.")


def acao_grafico(caminho: Path, mes: str = "", mostrar: bool = False) -> None:
    from .grafico import gerar_grafico  # só carrega o matplotlib se for usado

    ano, m = ler_mes(mes)
    gastos = gastos_por_categoria(filtrar_por_mes(armazenamento.carregar(caminho), ano, m))
    destino = Path(f"grafico-{ano}-{m:02d}.png")
    gerar_grafico(gastos, f"Gastos por categoria - {nome_do_mes(ano, m)}", destino, mostrar)
    print(f"Grafico salvo em '{destino}'.")


# ---------- Menu interativo ----------

def perguntar(rotulo: str) -> str:
    try:
        return input(rotulo)
    except EOFError:
        raise KeyboardInterrupt from None


def menu_interativo(caminho: Path) -> None:
    opcoes = {
        "1": "Adicionar receita",
        "2": "Adicionar despesa",
        "3": "Listar transacoes do mes",
        "4": "Resumo do mes",
        "5": "Gerar grafico de gastos",
        "6": "Remover transacao",
        "0": "Sair",
    }

    while True:
        print("\n======= CONTROLE DE GASTOS =======")
        for chave, texto in opcoes.items():
            print(f" {chave}. {texto}")
        escolha = perguntar("Opcao: ").strip()

        try:
            if escolha in ("1", "2"):
                tipo = "receita" if escolha == "1" else "despesa"
                valor = perguntar("Valor (ex: 45,90): ")
                print("Categorias sugeridas: " + ", ".join(CATEGORIAS_SUGERIDAS))
                categoria = perguntar("Categoria: ")
                descricao = perguntar("Descricao (opcional): ")
                data = perguntar("Data dd/mm/aaaa (Enter = hoje): ")
                acao_adicionar(caminho, tipo, valor, categoria, descricao, data)
            elif escolha == "3":
                acao_listar(caminho, perguntar("Mes mm/aaaa (Enter = atual): "))
            elif escolha == "4":
                acao_resumo(caminho, perguntar("Mes mm/aaaa (Enter = atual): "))
            elif escolha == "5":
                acao_grafico(caminho, perguntar("Mes mm/aaaa (Enter = atual): "))
            elif escolha == "6":
                acao_remover(caminho, perguntar("ID da transacao: "))
            elif escolha == "0":
                print("Ate mais!")
                return
            else:
                print("Opcao invalida.")
        except (ValueError, RuntimeError) as erro:
            print(f"Erro: {erro}")


# ---------- Argumentos de linha de comando ----------

def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="controle_gastos",
        description="Controle de receitas e despesas pessoais. "
                    "Sem argumentos, abre o menu interativo.",
    )
    parser.add_argument("--arquivo", type=Path, default=armazenamento.ARQUIVO_PADRAO,
                        help="arquivo de dados (padrao: gastos.json)")
    sub = parser.add_subparsers(dest="comando")

    p = sub.add_parser("adicionar", help="registra uma receita ou despesa")
    p.add_argument("tipo", help="receita ou despesa (ou r / d)")
    p.add_argument("valor", help="ex: 45,90 ou 1.200,00")
    p.add_argument("-c", "--categoria", default="", help="ex: Alimentacao")
    p.add_argument("-d", "--descricao", default="")
    p.add_argument("--data", default="", help="dd/mm/aaaa (padrao: hoje)")

    for nome, ajuda in (("listar", "lista as transacoes do mes"),
                        ("resumo", "mostra receitas, despesas e saldo do mes")):
        p = sub.add_parser(nome, help=ajuda)
        p.add_argument("--mes", default="", help="mm/aaaa (padrao: mes atual)")

    p = sub.add_parser("grafico", help="gera um grafico PNG dos gastos do mes")
    p.add_argument("--mes", default="", help="mm/aaaa (padrao: mes atual)")
    p.add_argument("--mostrar", action="store_true", help="abre o grafico em uma janela")

    p = sub.add_parser("remover", help="remove uma transacao pelo ID")
    p.add_argument("id")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)
    caminho: Path = args.arquivo

    try:
        if args.comando is None:
            menu_interativo(caminho)
        elif args.comando == "adicionar":
            acao_adicionar(caminho, args.tipo, args.valor, args.categoria,
                           args.descricao, args.data)
        elif args.comando == "listar":
            acao_listar(caminho, args.mes)
        elif args.comando == "resumo":
            acao_resumo(caminho, args.mes)
        elif args.comando == "grafico":
            acao_grafico(caminho, args.mes, args.mostrar)
        elif args.comando == "remover":
            acao_remover(caminho, args.id)
    except (ValueError, RuntimeError, ErroArquivo) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAte mais!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
