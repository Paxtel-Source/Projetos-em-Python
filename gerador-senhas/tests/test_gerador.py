import string

import pytest

from gerador_senhas import avaliar_forca, calcular_entropia, gerar_senha
from gerador_senhas.__main__ import main
from gerador_senhas.gerador import AMBIGUOS, SIMBOLOS


# ---------- gerar_senha ----------

@pytest.mark.parametrize("tamanho", [4, 16, 64, 128])
def test_tamanho_correto(tamanho):
    assert len(gerar_senha(tamanho)) == tamanho


def test_contem_todas_as_categorias():
    # Repetimos várias vezes porque o resultado é aleatório
    for _ in range(200):
        senha = gerar_senha(8)
        assert any(c in string.ascii_lowercase for c in senha)
        assert any(c in string.ascii_uppercase for c in senha)
        assert any(c in string.digits for c in senha)
        assert any(c in SIMBOLOS for c in senha)


def test_apenas_numeros():
    senha = gerar_senha(10, minusculas=False, maiusculas=False, simbolos=False)
    assert senha.isdigit()


def test_sem_simbolos():
    for _ in range(50):
        assert gerar_senha(32, simbolos=False).isalnum()


def test_evitar_ambiguos():
    for _ in range(50):
        assert not set(gerar_senha(64, evitar_ambiguos=True)) & AMBIGUOS


def test_senhas_diferentes():
    assert len({gerar_senha(16) for _ in range(100)}) == 100


@pytest.mark.parametrize("tamanho", [0, 3, 129, -5])
def test_tamanho_invalido(tamanho):
    with pytest.raises(ValueError):
        gerar_senha(tamanho)


def test_nenhuma_categoria():
    with pytest.raises(ValueError):
        gerar_senha(10, minusculas=False, maiusculas=False, numeros=False, simbolos=False)


# ---------- medidor de força ----------

def test_entropia_vazia():
    assert calcular_entropia("") == 0


def test_entropia_cresce_com_tamanho():
    assert calcular_entropia("abcdefgh") < calcular_entropia("abcdefghijkl")


@pytest.mark.parametrize("senha", ["123456", "senha123", "PASSWORD"])
def test_senhas_comuns_sao_muito_fracas(senha):
    assert avaliar_forca(senha).nivel == "Muito fraca"


def test_caractere_repetido_e_fraco():
    assert avaliar_forca("aaaaaaaaaaaaaaaaaaaa").pontos <= 1


def test_senha_gerada_e_muito_forte():
    assert avaliar_forca(gerar_senha(20)).nivel == "Muito forte"


# ---------- linha de comando ----------

def test_cli_quantidade(capsys):
    assert main(["-t", "12", "-q", "3"]) == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    senhas = [linha for linha in linhas if not linha.startswith("  Forca")]
    assert len(senhas) == 3
    assert all(len(s) == 12 for s in senhas)


def test_cli_erro_tamanho(capsys):
    assert main(["-t", "2"]) == 1
    assert "Erro" in capsys.readouterr().err
