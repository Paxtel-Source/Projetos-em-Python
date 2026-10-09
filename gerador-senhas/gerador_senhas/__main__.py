"""Interface de linha de comando.

Uso:
    python -m gerador_senhas                  # 1 senha de 16 caracteres
    python -m gerador_senhas -t 24 -q 5       # 5 senhas de 24 caracteres
    python -m gerador_senhas --sem-simbolos   # só letras e números
    python -m gerador_senhas --avaliar        # mede a força de uma senha sua
"""

import argparse
import getpass
import sys

from .forca import avaliar_forca, desenhar_barra
from .gerador import TAMANHO_MAXIMO, TAMANHO_MINIMO, gerar_senha


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gerador_senhas",
        description="Gera senhas seguras e mede a forca de senhas.",
    )
    parser.add_argument("-t", "--tamanho", type=int, default=16,
                        help=f"quantidade de caracteres ({TAMANHO_MINIMO}-{TAMANHO_MAXIMO}, padrao: 16)")
    parser.add_argument("-q", "--quantidade", type=int, default=1,
                        help="quantas senhas gerar (padrao: 1)")
    parser.add_argument("--sem-maiusculas", action="store_true", help="nao usar letras maiusculas")
    parser.add_argument("--sem-minusculas", action="store_true", help="nao usar letras minusculas")
    parser.add_argument("--sem-numeros", action="store_true", help="nao usar numeros")
    parser.add_argument("--sem-simbolos", action="store_true", help="nao usar simbolos")
    parser.add_argument("--evitar-ambiguos", action="store_true",
                        help="remove caracteres parecidos, como 0/O e 1/l/I")
    parser.add_argument("--avaliar", action="store_true",
                        help="em vez de gerar, mede a forca de uma senha digitada")
    return parser


def exibir_avaliacao(senha: str) -> None:
    resultado = avaliar_forca(senha)
    print(f"  Forca: {desenhar_barra(resultado)} {resultado.nivel} "
          f"({resultado.entropia:.0f} bits de entropia)")


def modo_avaliar() -> int:
    # getpass esconde o que é digitado e não deixa a senha no histórico do terminal
    senha = getpass.getpass("Digite a senha para avaliar (nao aparece na tela): ")
    if not senha:
        print("Nenhuma senha digitada.", file=sys.stderr)
        return 1
    exibir_avaliacao(senha)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)

    if args.avaliar:
        return modo_avaliar()

    if not 1 <= args.quantidade <= 100:
        print("Erro: a quantidade deve estar entre 1 e 100.", file=sys.stderr)
        return 1

    try:
        for _ in range(args.quantidade):
            senha = gerar_senha(
                tamanho=args.tamanho,
                minusculas=not args.sem_minusculas,
                maiusculas=not args.sem_maiusculas,
                numeros=not args.sem_numeros,
                simbolos=not args.sem_simbolos,
                evitar_ambiguos=args.evitar_ambiguos,
            )
            print(senha)
            exibir_avaliacao(senha)
    except ValueError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
