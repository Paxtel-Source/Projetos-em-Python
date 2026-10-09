# 🐍 Projetos Python

![Testes](https://github.com/SEU_USUARIO/Projetos-Python/actions/workflows/testes.yml/badge.svg)

Coleção de projetos em **Python** para praticar os fundamentos da linguagem: linha de comando, arquivos, módulos da biblioteca padrão, gráficos e testes automatizados.

| Projeto | Descrição | Conceitos principais |
|---------|-----------|----------------------|
| [🔐 Gerador de Senhas](gerador-senhas/) | Gera senhas seguras e mede a força de senhas | `secrets`, `argparse`, entropia, `pytest` |
| [💰 Controle de Gastos](controle-gastos/) | Registra receitas e despesas, com resumo mensal e gráfico | `dataclass`, `Decimal`, JSON, `matplotlib` |

## Organização

Cada projeto é um **pacote Python** independente, com a mesma estrutura:

```
projeto/
├── nome_do_pacote/     # Código-fonte, dividido em módulos
│   ├── __init__.py
│   └── __main__.py     # Permite rodar com "python -m nome_do_pacote"
├── tests/              # Testes automatizados (pytest)
├── pyproject.toml      # Configuração do pytest
├── requirements.txt    # Dependências para usar o programa
├── requirements-dev.txt# Dependências para desenvolver (pytest)
└── README.md           # O que faz e como usar
```

## Requisitos

- **Python 3.10** ou mais recente ([download](https://www.python.org/downloads/))
- `pip` para instalar as dependências

## Como usar

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/Projetos-Python.git
cd Projetos-Python

# Entre em um dos projetos e siga o README dele
cd gerador-senhas
python -m gerador_senhas
```

## Testes automatizados

Cada projeto tem testes com `pytest`. Para rodar:

```bash
cd gerador-senhas        # ou controle-gastos
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

Os testes também rodam **automaticamente no GitHub** a cada `push`, pelo **GitHub Actions** (veja `.github/workflows/testes.yml`). O selo no topo deste README fica verde quando todos passam.
