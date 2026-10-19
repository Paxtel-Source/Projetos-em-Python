"""Decide quando avisar e envia o aviso por e-mail e/ou Telegram.

As credenciais ficam em variáveis de ambiente (ou no arquivo .env), nunca no código:

    EMAIL_REMETENTE, EMAIL_SENHA, EMAIL_DESTINO, SMTP_SERVIDOR (padrão smtp.gmail.com), SMTP_PORTA (padrão 587)
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""

import os
import smtplib
from dataclasses import dataclass
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path

import requests

from .armazenamento import Produto


@dataclass
class Alerta:
    produto: Produto
    preco: Decimal
    motivo: str

    @property
    def mensagem(self) -> str:
        return (f"{self.produto.nome}: {formatar_moeda(self.preco)} ({self.motivo})\n"
                f"{self.produto.url}")


def formatar_moeda(valor: Decimal) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def verificar_alerta(produto: Produto, preco: Decimal, anterior: Decimal | None) -> Alerta | None:
    """Avisa quando o preço chega ao alvo ou cai em relação à última verificação."""
    if produto.preco_alvo is not None and preco <= produto.preco_alvo:
        return Alerta(produto, preco, f"chegou ao preço alvo de {formatar_moeda(produto.preco_alvo)}")
    if anterior is not None and preco < anterior:
        queda = (anterior - preco) / anterior * 100
        return Alerta(produto, preco, f"baixou {queda:.0f}%, antes era {formatar_moeda(anterior)}")
    return None


# ---------- Configuração (.env) ----------

def carregar_env(caminho: Path = Path(".env")) -> None:
    """Lê linhas CHAVE=valor do arquivo .env para as variáveis de ambiente.

    Variáveis já definidas no sistema têm prioridade sobre o arquivo.
    """
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


# ---------- Envio ----------

def enviar_email(alertas: list[Alerta]) -> bool:
    remetente = os.environ.get("EMAIL_REMETENTE")
    senha = os.environ.get("EMAIL_SENHA")
    destino = os.environ.get("EMAIL_DESTINO", remetente)
    if not (remetente and senha):
        return False

    mensagem = EmailMessage()
    mensagem["Subject"] = f"Preço baixou: {alertas[0].produto.nome}" + (
        f" e mais {len(alertas) - 1}" if len(alertas) > 1 else "")
    mensagem["From"] = remetente
    mensagem["To"] = destino
    mensagem.set_content("\n\n".join(a.mensagem for a in alertas))

    servidor = os.environ.get("SMTP_SERVIDOR", "smtp.gmail.com")
    porta = int(os.environ.get("SMTP_PORTA", "587"))
    with smtplib.SMTP(servidor, porta, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(remetente, senha)
        smtp.send_message(mensagem)
    return True


def enviar_telegram(alertas: list[Alerta]) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return False

    texto = "🔔 Preço baixou!\n\n" + "\n\n".join(a.mensagem for a in alertas)
    resposta = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": texto, "disable_web_page_preview": True},
        timeout=15,
    )
    resposta.raise_for_status()
    return True


def enviar_alertas(alertas: list[Alerta]) -> list[str]:
    """Envia por todos os canais configurados. Devolve os canais que funcionaram."""
    if not alertas:
        return []
    canais = []
    for nome, funcao in (("e-mail", enviar_email), ("Telegram", enviar_telegram)):
        try:
            if funcao(alertas):
                canais.append(nome)
        except (smtplib.SMTPException, OSError, requests.RequestException) as erro:
            print(f"  Aviso: não foi possível enviar por {nome}: {erro}")
    return canais
