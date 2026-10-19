"""Catálogo de livros: busca para todos, cadastro e edição para bibliotecários."""

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from .auth import bibliotecario_requerido
from .extensoes import db
from .formularios import FormLivro
from .modelos import Livro, contar_por_genero
from .regras import RegraViolada, emprestar

bp = Blueprint("livros", __name__)


@bp.route("/")
def catalogo():
    busca = request.args.get("q", "").strip()
    genero = request.args.get("genero", "").strip()
    pagina = request.args.get("pagina", 1, type=int)

    consulta = Livro.query
    if busca:
        termo = f"%{busca}%"
        consulta = consulta.filter(or_(Livro.titulo.ilike(termo), Livro.autor.ilike(termo), Livro.isbn.ilike(termo)))
    if genero:
        consulta = consulta.filter(Livro.genero == genero)

    paginacao = consulta.order_by(Livro.titulo).paginate(
        page=pagina, per_page=current_app.config["LIVROS_POR_PAGINA"], error_out=False)
    return render_template("livros/catalogo.html", paginacao=paginacao, busca=busca,
                           genero=genero, generos=contar_por_genero())


@bp.route("/livros/<int:livro_id>")
def detalhe(livro_id):
    livro = db.get_or_404(Livro, livro_id)
    return render_template("livros/detalhe.html", livro=livro)


@bp.route("/livros/<int:livro_id>/emprestar", methods=["POST"])
@login_required
def pegar_emprestado(livro_id):
    livro = db.get_or_404(Livro, livro_id)
    try:
        emprestimo = emprestar(livro, current_user)
    except RegraViolada as erro:
        flash(str(erro), "erro")
    else:
        flash(f"Empréstimo feito! Devolva até {emprestimo.data_prevista:%d/%m/%Y}.", "sucesso")
    return redirect(url_for("livros.detalhe", livro_id=livro.id))


def _preencher(livro: Livro, form: FormLivro) -> None:
    livro.titulo = form.titulo.data.strip()
    livro.autor = form.autor.data.strip()
    livro.isbn = form.isbn.data.replace(" ", "") if form.isbn.data else None
    livro.ano = form.ano.data
    livro.genero = form.genero.data.strip() if form.genero.data else None
    livro.exemplares = form.exemplares.data


@bp.route("/livros/novo", methods=["GET", "POST"])
@bibliotecario_requerido
def novo():
    form = FormLivro()
    if form.validate_on_submit():
        livro = Livro()
        _preencher(livro, form)
        db.session.add(livro)
        db.session.commit()
        flash(f"\"{livro.titulo}\" foi adicionado ao catálogo.", "sucesso")
        return redirect(url_for("livros.detalhe", livro_id=livro.id))
    return render_template("livros/formulario.html", form=form, titulo_pagina="Novo livro")


@bp.route("/livros/<int:livro_id>/editar", methods=["GET", "POST"])
@bibliotecario_requerido
def editar(livro_id):
    livro = db.get_or_404(Livro, livro_id)
    form = FormLivro(obj=livro, livro_id=livro.id)
    if form.validate_on_submit():
        if form.exemplares.data < livro.emprestados:
            form.exemplares.errors.append(
                f"Há {livro.emprestados} exemplar(es) emprestado(s); o total não pode ser menor que isso.")
        else:
            _preencher(livro, form)
            db.session.commit()
            flash("Livro atualizado.", "sucesso")
            return redirect(url_for("livros.detalhe", livro_id=livro.id))
    return render_template("livros/formulario.html", form=form, titulo_pagina="Editar livro", livro=livro)


@bp.route("/livros/<int:livro_id>/excluir", methods=["POST"])
@bibliotecario_requerido
def excluir(livro_id):
    livro = db.get_or_404(Livro, livro_id)
    if livro.emprestados:
        flash("Não é possível excluir um livro que está emprestado.", "erro")
        return redirect(url_for("livros.detalhe", livro_id=livro.id))
    db.session.delete(livro)
    db.session.commit()
    flash(f"\"{livro.titulo}\" foi removido do catálogo.", "info")
    return redirect(url_for("livros.catalogo"))
