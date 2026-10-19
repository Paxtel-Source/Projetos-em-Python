"""Regras do chat: apelidos, salas, histórico e limite de mensagens.

Este módulo não depende do aiohttp. Cada participante só precisa de uma
conexão com o método assíncrono send_json(dados), por isso os testes podem
usar conexões falsas, sem abrir nenhum servidor.

Protocolo (mensagens JSON):

    Navegador → servidor
        {"tipo": "entrar", "apelido": "Ana", "sala": "geral"}
        {"tipo": "mensagem", "texto": "Olá!"}
        {"tipo": "trocar_sala", "sala": "python"}
        {"tipo": "digitando"}

    Servidor → navegador
        bem_vindo, mensagem, sistema, usuarios, salas, digitando, erro
"""

import asyncio
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

SALAS_FIXAS = ("geral", "python", "linguagem-c", "ajuda")
TAMANHO_HISTORICO = 50        # mensagens guardadas por sala
TAMANHO_MAXIMO_TEXTO = 500    # caracteres por mensagem
LIMITE_MENSAGENS = 5          # no máximo 5 mensagens...
JANELA_SEGUNDOS = 5.0         # ...a cada 5 segundos por pessoa

PADRAO_APELIDO = re.compile(r"^[\w-]+( [\w-]+)*$")      # \w aceita letras com acento
PADRAO_SALA = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ErroDoChat(Exception):
    """Pedido inválido. A mensagem é mostrada para quem fez o pedido."""


# ---------- Validação ----------

def validar_apelido(apelido) -> str:
    apelido = " ".join(str(apelido or "").split())       # tira espaços repetidos
    if not 2 <= len(apelido) <= 20:
        raise ErroDoChat("O apelido precisa ter de 2 a 20 caracteres.")
    if not PADRAO_APELIDO.match(apelido):
        raise ErroDoChat("Use só letras, números, espaço, _ e - no apelido.")
    return apelido


def validar_sala(nome) -> str:
    nome = "-".join(str(nome or "").strip().lower().split())
    if not 1 <= len(nome) <= 24 or not PADRAO_SALA.match(nome):
        raise ErroDoChat("Nome de sala inválido: use até 24 letras minúsculas, números e hífens.")
    return nome


def validar_texto(texto) -> str:
    texto = str(texto or "").strip()
    if not texto:
        raise ErroDoChat("A mensagem está vazia.")
    if len(texto) > TAMANHO_MAXIMO_TEXTO:
        raise ErroDoChat(f"A mensagem passou de {TAMANHO_MAXIMO_TEXTO} caracteres.")
    return texto


def agora_iso() -> str:
    """Horário em UTC; o navegador converte para o fuso de quem está lendo."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- Participantes e salas ----------

@dataclass(eq=False)
class Participante:
    conexao: object
    apelido: str
    sala: "Sala | None" = None
    envios: deque = field(default_factory=lambda: deque(maxlen=LIMITE_MENSAGENS))

    def pode_enviar(self, agora: float) -> bool:
        """Limite de mensagens: guarda o horário dos últimos envios."""
        if len(self.envios) == LIMITE_MENSAGENS and agora - self.envios[0] < JANELA_SEGUNDOS:
            return False
        self.envios.append(agora)
        return True


@dataclass(eq=False)
class Sala:
    nome: str
    fixa: bool = False
    participantes: list[Participante] = field(default_factory=list)
    historico: deque = field(default_factory=lambda: deque(maxlen=TAMANHO_HISTORICO))

    @property
    def apelidos(self) -> list[str]:
        return sorted((p.apelido for p in self.participantes), key=str.casefold)


# ---------- O chat ----------

class Chat:
    def __init__(self, relogio=time.monotonic):
        self.salas: dict[str, Sala] = {nome: Sala(nome, fixa=True) for nome in SALAS_FIXAS}
        self.participantes: dict[object, Participante] = {}
        self.relogio = relogio          # trocado nos testes para controlar o tempo

    async def processar(self, conexao, dados: dict) -> None:
        """Recebe uma mensagem do navegador e chama a ação certa."""
        tipo = dados.get("tipo")
        if tipo == "entrar":
            await self.entrar(conexao, dados.get("apelido"), dados.get("sala"))
        elif conexao not in self.participantes:
            raise ErroDoChat("Escolha um apelido para entrar no chat.")
        elif tipo == "mensagem":
            await self.enviar_mensagem(conexao, dados.get("texto"))
        elif tipo == "trocar_sala":
            await self.trocar_sala(conexao, dados.get("sala"))
        elif tipo == "digitando":
            await self.digitando(conexao)
        else:
            raise ErroDoChat("Tipo de mensagem desconhecido.")

    # ----- Ações -----

    async def entrar(self, conexao, apelido, sala=None) -> Participante:
        if conexao in self.participantes:
            raise ErroDoChat("Você já entrou no chat.")
        apelido = validar_apelido(apelido)
        if any(p.apelido.casefold() == apelido.casefold() for p in self.participantes.values()):
            raise ErroDoChat(f"O apelido \"{apelido}\" já está em uso. Escolha outro.")
        nome_sala = validar_sala(sala or "geral")

        participante = Participante(conexao, apelido)
        self.participantes[conexao] = participante
        await self._colocar_na_sala(participante, nome_sala, f"{apelido} entrou no chat.")
        return participante

    async def enviar_mensagem(self, conexao, texto) -> None:
        participante = self.participantes[conexao]
        texto = validar_texto(texto)
        if not participante.pode_enviar(self.relogio()):
            raise ErroDoChat("Calma! Espere alguns segundos antes de mandar mais mensagens.")
        dados = {"tipo": "mensagem", "apelido": participante.apelido, "texto": texto, "horario": agora_iso()}
        participante.sala.historico.append(dados)
        await self._transmitir(participante.sala.participantes, dados)

    async def trocar_sala(self, conexao, nome) -> None:
        participante = self.participantes[conexao]
        nome = validar_sala(nome)
        if participante.sala.nome == nome:
            return
        await self._tirar_da_sala(participante, f"{participante.apelido} foi para a sala #{nome}.")
        await self._colocar_na_sala(participante, nome, f"{participante.apelido} entrou na sala.")

    async def digitando(self, conexao) -> None:
        participante = self.participantes[conexao]
        outros = [p for p in participante.sala.participantes if p is not participante]
        await self._transmitir(outros, {"tipo": "digitando", "apelido": participante.apelido})

    async def sair(self, conexao) -> None:
        """Chamado quando a conexão fecha, de propósito ou por queda."""
        participante = self.participantes.pop(conexao, None)
        if participante is None:
            return
        await self._tirar_da_sala(participante, f"{participante.apelido} saiu do chat.")
        await self._enviar_salas()

    # ----- Apoio -----

    def resumo_salas(self) -> list[dict]:
        """Salas fixas primeiro, na ordem definida; depois as criadas, em ordem alfabética."""
        criadas = sorted(nome for nome, sala in self.salas.items() if not sala.fixa)
        return [{"nome": nome, "pessoas": len(self.salas[nome].participantes)}
                for nome in (*SALAS_FIXAS, *criadas)]

    async def _colocar_na_sala(self, participante: Participante, nome: str, aviso: str) -> None:
        sala = self.salas.setdefault(nome, Sala(nome))
        sala.participantes.append(participante)
        participante.sala = sala
        await self._transmitir([participante], {
            "tipo": "bem_vindo", "apelido": participante.apelido, "sala": sala.nome,
            "historico": list(sala.historico), "usuarios": sala.apelidos,
        })
        outros = [p for p in sala.participantes if p is not participante]
        await self._transmitir(outros, {"tipo": "sistema", "texto": aviso, "horario": agora_iso()})
        await self._transmitir(outros, {"tipo": "usuarios", "usuarios": sala.apelidos})
        await self._enviar_salas()

    async def _tirar_da_sala(self, participante: Participante, aviso: str) -> None:
        sala = participante.sala
        sala.participantes.remove(participante)
        participante.sala = None
        if not sala.participantes and not sala.fixa:
            del self.salas[sala.nome]          # sala criada por alguém e que ficou vazia
            return
        await self._transmitir(sala.participantes, {"tipo": "sistema", "texto": aviso, "horario": agora_iso()})
        await self._transmitir(sala.participantes, {"tipo": "usuarios", "usuarios": sala.apelidos})

    async def _enviar_salas(self) -> None:
        await self._transmitir(self.participantes.values(), {"tipo": "salas", "salas": self.resumo_salas()})

    @staticmethod
    async def _transmitir(participantes, dados: dict) -> None:
        """Envia para todos ao mesmo tempo. Uma conexão com problema não atrapalha as outras."""
        await asyncio.gather(*(p.conexao.send_json(dados) for p in list(participantes)),
                             return_exceptions=True)
