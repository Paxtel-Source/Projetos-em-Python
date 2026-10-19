"""Empréstimos: o leitor vê e renova os seus; o bibliotecário acompanha todos e registra devoluções."""

from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .auth import bibliotecario_requerido
from .extensoes import db
from .modelos import Emprestimo, Livro, Usuario
from .regras import RegraViolada, devolver, renovar

bp = Blueprint("emprestimos", __name__, url_prefix="/emprestimos")


@bp.route("/meus")
@login_required
def meus():
    historico = (current_user.emprestimos.filter(Emprestimo.data_devolucao.isnot(None))
                 .order_by(Emprestimo.data_devolucao.desc()).limit(20).all())
    return render_template("emprestimos/meus.html", ativos=current_user.emprestimos_ativos, historico=historico)


@bp.route("/<int:emprestimo_id>/renovar", methods=["POST"])
@login_required
def renovar_emprestimo(emprestimo_id):
    emprestimo = db.get_or_404(Emprestimo, emprestimo_id)
    # O leitor só renova os próprios empréstimos
    if emprestimo.usuario_id != current_user.id and not current_user.bibliotecario:
        abort(403)
    try:
        renovar(emprestimo)
        flash(f"Renovado! Nova data de devolução: {emprestimo.data_prevista:%d/%m/%Y}.", "sucesso")
    except RegraViolada as erro:
        flash(str(erro), "erro")
    return redirect(request.referrer or url_for("emprestimos.meus"))


@bp.route("/painel")
@bibliotecario_requerido
def painel():
    filtro = request.args.get("filtro", "ativos")
    consulta = (Emprestimo.query.filter(Emprestimo.data_devolucao.is_(None))
                .join(Livro).join(Usuario).order_by(Emprestimo.data_prevista))
    if filtro == "atrasados":
        consulta = consulta.filter(Emprestimo.data_prevista < date.today())

    resumo = {
        "livros": Livro.query.count(),
        "leitores": Usuario.query.count(),
        "ativos": Emprestimo.query.filter(Emprestimo.data_devolucao.is_(None)).count(),
        "atrasados": Emprestimo.query.filter(Emprestimo.data_devolucao.is_(None),
                                             Emprestimo.data_prevista < date.today()).count(),
    }
    return render_template("emprestimos/painel.html", emprestimos=consulta.all(), filtro=filtro, resumo=resumo)


@bp.route("/<int:emprestimo_id>/devolver", methods=["POST"])
@bibliotecario_requerido
def registrar_devolucao(emprestimo_id):
    emprestimo = db.get_or_404(Emprestimo, emprestimo_id)
    try:
        devolver(emprestimo)
        atraso = emprestimo.dias_de_atraso
        aviso = f" com {atraso} dia(s) de atraso" if atraso else ""
        flash(f"Devolução de \"{emprestimo.livro.titulo}\" registrada{aviso}.", "sucesso")
    except RegraViolada as erro:
        flash(str(erro), "erro")
    return redirect(request.referrer or url_for("emprestimos.painel"))
