"""Cadastro, login e logout."""

from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensoes import db
from .formularios import FormCadastro, FormLogin
from .modelos import Usuario

bp = Blueprint("auth", __name__)


def bibliotecario_requerido(funcao):
    """Decorador: só bibliotecários acessam a rota (os demais recebem 403)."""
    @wraps(funcao)
    @login_required
    def envoltorio(*args, **kwargs):
        if not current_user.bibliotecario:
            abort(403)
        return funcao(*args, **kwargs)
    return envoltorio


def _destino_seguro(destino: str | None) -> str:
    """Evita redirecionar para outro site depois do login (open redirect)."""
    if destino and not urlsplit(destino).netloc and destino.startswith("/"):
        return destino
    return url_for("livros.catalogo")


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("livros.catalogo"))
    form = FormCadastro()
    if form.validate_on_submit():
        usuario = Usuario(nome=form.nome.data.strip(), email=form.email.data.strip().lower())
        usuario.definir_senha(form.senha.data)
        db.session.add(usuario)
        db.session.commit()
        login_user(usuario)
        flash(f"Bem-vindo(a), {usuario.nome.split()[0]}! Sua conta foi criada.", "sucesso")
        return redirect(url_for("livros.catalogo"))
    return render_template("auth/cadastro.html", form=form)


@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if current_user.is_authenticated:
        return redirect(url_for("livros.catalogo"))
    form = FormLogin()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data.strip().lower()).first()
        if usuario and usuario.senha_correta(form.senha.data):
            login_user(usuario)
            return redirect(_destino_seguro(request.args.get("next")))
        # A mesma mensagem para e-mail ou senha errados não revela quais e-mails existem
        flash("E-mail ou senha incorretos.", "erro")
    return render_template("auth/entrar.html", form=form)


@bp.route("/sair", methods=["POST"])
@login_required
def sair():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("livros.catalogo"))
