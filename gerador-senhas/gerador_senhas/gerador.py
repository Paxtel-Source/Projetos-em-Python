"""Geração de senhas usando o módulo `secrets` (aleatoriedade criptográfica)."""

import secrets
import string

TAMANHO_MINIMO = 4
TAMANHO_MAXIMO = 128

# Caracteres fáceis de confundir ao ler ou digitar (0/O, 1/l/I etc.)
AMBIGUOS = set("0O1lI|`'\"")

SIMBOLOS = "!@#$%&*()-_=+[]{};:,.<>?/"


def montar_categorias(
    minusculas: bool = True,
    maiusculas: bool = True,
    numeros: bool = True,
    simbolos: bool = True,
    evitar_ambiguos: bool = False,
) -> list[str]:
    """Retorna a lista de grupos de caracteres escolhidos pelo usuário."""
    categorias = []
    if minusculas:
        categorias.append(string.ascii_lowercase)
    if maiusculas:
        categorias.append(string.ascii_uppercase)
    if numeros:
        categorias.append(string.digits)
    if simbolos:
        categorias.append(SIMBOLOS)

    if evitar_ambiguos:
        categorias = ["".join(c for c in grupo if c not in AMBIGUOS) for grupo in categorias]

    return [grupo for grupo in categorias if grupo]


def gerar_senha(
    tamanho: int = 16,
    minusculas: bool = True,
    maiusculas: bool = True,
    numeros: bool = True,
    simbolos: bool = True,
    evitar_ambiguos: bool = False,
) -> str:
    """Gera uma senha aleatória.

    A senha sempre contém pelo menos um caractere de cada categoria escolhida,
    e a posição desses caracteres também é sorteada.

    Raises:
        ValueError: se o tamanho for inválido ou nenhuma categoria for escolhida.
    """
    if not TAMANHO_MINIMO <= tamanho <= TAMANHO_MAXIMO:
        raise ValueError(f"O tamanho deve estar entre {TAMANHO_MINIMO} e {TAMANHO_MAXIMO}.")

    categorias = montar_categorias(minusculas, maiusculas, numeros, simbolos, evitar_ambiguos)
    if not categorias:
        raise ValueError("Escolha pelo menos um tipo de caractere.")
    if tamanho < len(categorias):
        raise ValueError(f"O tamanho precisa ser pelo menos {len(categorias)} "
                         "para incluir todos os tipos escolhidos.")

    # 1) Um caractere garantido de cada categoria
    caracteres = [secrets.choice(grupo) for grupo in categorias]

    # 2) O restante sorteado entre todos os caracteres permitidos
    todos = "".join(categorias)
    caracteres += [secrets.choice(todos) for _ in range(tamanho - len(caracteres))]

    # 3) Embaralha para que os caracteres garantidos não fiquem sempre no início
    secrets.SystemRandom().shuffle(caracteres)
    return "".join(caracteres)
