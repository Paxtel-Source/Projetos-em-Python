# 🔐 Gerador de Senhas Seguras

Programa de linha de comando em Python que gera **senhas aleatórias seguras** e mede a **força** de qualquer senha. Usa o módulo `secrets`, feito para criptografia, em vez do `random`, que é previsível.

## Funcionalidades

- Escolha do **tamanho** (4 a 128) e da **quantidade** de senhas
- Liga e desliga **maiúsculas, minúsculas, números e símbolos**
- Garante **pelo menos um caractere de cada tipo** escolhido
- Opção para **evitar caracteres ambíguos** (`0`/`O`, `1`/`l`/`I`), boa para senhas que serão digitadas
- **Medidor de força** com barra visual e entropia em bits
- Modo `--avaliar` para testar uma senha sua sem que ela apareça na tela
- 23 testes automatizados com `pytest`

## Estrutura

```
gerador-senhas/
├── gerador_senhas/
│   ├── __init__.py     # Expõe as funções principais do pacote
│   ├── __main__.py     # Interface de linha de comando (argparse)
│   ├── gerador.py      # Lógica de geração das senhas
│   └── forca.py        # Cálculo de entropia e medidor de força
├── tests/
│   └── test_gerador.py
├── pyproject.toml      # Configuração do pytest
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Dependências

- **Python 3.10** ou mais recente
- Nenhuma biblioteca externa: só a biblioteca padrão (`secrets`, `string`, `argparse`, `math`)
- `pytest` apenas para rodar os testes

## Como executar

1. Entre na pasta do projeto:
   ```bash
   cd gerador-senhas
   ```
2. Gere uma senha de 16 caracteres:
   ```bash
   python -m gerador_senhas
   ```
3. Outros exemplos:
   ```bash
   python -m gerador_senhas -t 24 -q 5          # 5 senhas de 24 caracteres
   python -m gerador_senhas --sem-simbolos       # só letras e números
   python -m gerador_senhas -t 6 --sem-maiusculas --sem-minusculas --sem-simbolos  # PIN numérico
   python -m gerador_senhas --evitar-ambiguos    # sem 0/O, 1/l/I
   python -m gerador_senhas --avaliar            # mede a força de uma senha sua
   python -m gerador_senhas --help               # todas as opções
   ```

> No Windows, se `python` não funcionar, use `py`. No Linux/macOS, pode ser `python3`.

## Exemplo de uso

```
$ python -m gerador_senhas -t 20 -q 2
Y5De%Yeb(N=E!DNJT;LB
  Forca: [####################] Muito forte (129 bits de entropia)
0Xpp8]f=cF0#V<]A7Zm)
  Forca: [####################] Muito forte (129 bits de entropia)

$ python -m gerador_senhas -t 8 --sem-simbolos
RyPk4myh
  Forca: [############--------] Razoavel (48 bits de entropia)
```

## Como a força é calculada

A **entropia** mede quão imprevisível é uma senha:

```
entropia (bits) = tamanho × log2(quantidade de caracteres possíveis)
```

Uma senha de 8 letras minúsculas tem 8 × log2(26) ≈ 38 bits. Com 16 caracteres misturando letras, números e símbolos, passa de 100 bits. Cada bit a mais **dobra** o número de tentativas que um atacante precisa fazer.

| Entropia     | Classificação |
|--------------|---------------|
| até 28 bits  | Muito fraca   |
| 28 a 36      | Fraca         |
| 36 a 60      | Razoável      |
| 60 a 80      | Forte         |
| 80 ou mais   | Muito forte   |

Além da fórmula, senhas famosas (`123456`, `senha123`...) e senhas com um ou dois caracteres repetidos (`aaaaaaaa`) são sempre rebaixadas.

## Rodando os testes

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Conceitos praticados

Módulo `secrets` (aleatoriedade segura), `argparse`, pacotes Python (`__init__.py` e `__main__.py`), `dataclass`, type hints, tratamento de exceções, testes com `pytest` (incluindo `parametrize` e `capsys`).
