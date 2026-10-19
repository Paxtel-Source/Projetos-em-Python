"""Regras de negócio dos empréstimos, separadas das rotas para ficarem fáceis de testar."""

from datetime import date, timedelta

from flask import current_app

from .extensoes import db
from .modelos import Emprestimo, Livro, Usuario


class RegraViolada(Exception):
    """A operação não é permitida. A mensagem explica o motivo ao usuário."""


def emprestar(livro: Livro, usuario: Usuario, hoje: date | None = None) -> Emprestimo:
    hoje = hoje or date.today()
    limite = current_app.config["LIMITE_EMPRESTIMOS"]
    ativos = usuario.emprestimos_ativos

    if livro.disponiveis == 0:
        raise RegraViolada(f"Todos os exemplares de \"{livro.titulo}\" estão emprestados no momento.")
    if any(e.livro_id == livro.id for e in ativos):
        raise RegraViolada("Você já está com um exemplar deste livro.")
    if any(e.atrasado for e in ativos):
        raise RegraViolada("Você tem livro atrasado. Devolva-o antes de pegar outro.")
    if len(ativos) >= limite:
        raise RegraViolada(f"O limite é de {limite} livros ao mesmo tempo. Devolva um para pegar outro.")

    emprestimo = Emprestimo(
        livro=livro, usuario=usuario, data_emprestimo=hoje,
        data_prevista=hoje + timedelta(days=current_app.config["PRAZO_DIAS"]),
    )
    db.session.add(emprestimo)
    db.session.commit()
    return emprestimo


def devolver(emprestimo: Emprestimo, hoje: date | None = None) -> Emprestimo:
    if not emprestimo.ativo:
        raise RegraViolada("Este empréstimo já foi devolvido.")
    emprestimo.data_devolucao = hoje or date.today()
    db.session.commit()
    return emprestimo


def renovar(emprestimo: Emprestimo, hoje: date | None = None) -> Emprestimo:
    hoje = hoje or date.today()
    if not emprestimo.ativo:
        raise RegraViolada("Este empréstimo já foi devolvido.")
    if emprestimo.renovado:
        raise RegraViolada("Cada empréstimo só pode ser renovado uma vez.")
    if emprestimo.data_prevista < hoje:
        raise RegraViolada("Empréstimos atrasados não podem ser renovados.")

    emprestimo.data_prevista += timedelta(days=current_app.config["RENOVACAO_DIAS"])
    emprestimo.renovado = True
    db.session.commit()
    return emprestimo
