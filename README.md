# 🐍 Projetos em Python

![Testes](https://github.com/Paxtel-Source/Projetos-em-Python/actions/workflows/testes.yml/badge.svg)

Coleção de projetos em **Python**, dos fundamentos (linha de comando, arquivos, biblioteca padrão) até aplicações web, raspagem de dados e comunicação em tempo real. Todos têm testes automatizados.

## Fundamentos

| Projeto | Descrição | Conceitos principais |
|---------|-----------|----------------------|
| [🔐 Gerador de Senhas](gerador-senhas/) | Gera senhas seguras e mede a força de senhas | `secrets`, `argparse`, entropia, `pytest` |
| [💰 Controle de Gastos](controle-gastos/) | Registra receitas e despesas, com resumo mensal e gráfico | `dataclass`, `Decimal`, JSON, `matplotlib` |

## Intermediário

| Projeto | Descrição | Conceitos principais |
|---------|-----------|----------------------|
| [🏷️ Raspador de Preços](raspador-precos/) | Acompanha preços em lojas online e avisa por e-mail ou Telegram quando baixam | `requests`, `BeautifulSoup`, `robots.txt`, CSV, SMTP |
| [📚 Sistema de Biblioteca](sistema-biblioteca/) | Site com login, catálogo de livros, empréstimos, renovação e controle de atrasos | `Flask`, `SQLAlchemy`, `Flask-Login`, CSRF, Jinja2 |
| [💬 Chat em Tempo Real](chat-tempo-real/) | Chat no navegador com salas, pessoas online e "está digitando…" | `asyncio`, `aiohttp`, WebSocket, JavaScript |

<p align="center">
  <img src="sistema-biblioteca/docs/catalogo.png" width="49%" alt="Catálogo do Sistema de Biblioteca">
  <img src="chat-tempo-real/docs/preview.png" width="49%" alt="Chat em Tempo Real">
</p>

## Organização

Cada projeto é um **pacote Python** independente, com a mesma estrutura:

```
projeto/
├── nome_do_pacote/      # Código-fonte, dividido em módulos
│   ├── __init__.py
│   └── __main__.py      # Permite rodar com "python -m nome_do_pacote"
├── tests/               # Testes automatizados (pytest)
├── pyproject.toml       # Configuração do pytest
├── requirements.txt     # Dependências para usar o programa
├── requirements-dev.txt # Dependências para desenvolver (pytest)
└── README.md            # O que faz e como usar
```

O **Sistema de Biblioteca** é uma aplicação Flask, então roda com `flask --app biblioteca run` em vez de `python -m`. O README de cada projeto explica como usar.

## Requisitos

- **Python 3.10** ou mais recente ([download](https://www.python.org/downloads/))
- `pip` para instalar as dependências

## Como usar

```bash
# Clone o repositório
git clone https://github.com/Paxtel-Source/Projetos-em-Python.git
cd Projetos-em-Python

# Entre em um dos projetos, crie um ambiente virtual e siga o README dele
cd chat-tempo-real
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python -m chat_tempo_real
```

Use um **ambiente virtual por projeto**: cada um tem dependências diferentes.

## Testes automatizados

Cada projeto tem testes com `pytest`. Para rodar:

```bash
cd raspador-precos        # ou qualquer outro projeto
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

| Projeto | Testes |
|---------|-------:|
| Gerador de Senhas | 23 |
| Controle de Gastos | 21 |
| Raspador de Preços | 25 |
| Sistema de Biblioteca | 30 |
| Chat em Tempo Real | 33 |

Os testes também rodam **automaticamente no GitHub** a cada `push`, pelo **GitHub Actions**, em Python 3.10, 3.12 e 3.13 (veja `.github/workflows/testes.yml`). O selo no topo deste README fica verde quando todos passam.
