"""Sistema de Biblioteca: livros, leitores e empréstimos, com login e níveis de acesso."""

import os
from pathlib import Path

from flask import Flask, render_template

from .extensoes import csrf, db, login_manager


def create_app(config: dict | None = None) -> Flask:
    """Cria a aplicação (padrão "application factory": facilita os testes)."""
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.config.update(
        # Em produção, defina SECRET_KEY como variável de ambiente
        SECRET_KEY=os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{Path(app.instance_path) / 'biblioteca.db'}"),
        PRAZO_DIAS=14,          # dias para devolver
        RENOVACAO_DIAS=7,       # dias a mais ao renovar
        LIMITE_EMPRESTIMOS=3,   # livros ao mesmo tempo por leitor
        LIVROS_POR_PAGINA=12,
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from . import modelos  # noqa: F401  (registra as tabelas)
    from .auth import bp as auth_bp
    from .comandos import registrar_comandos
    from .emprestimos import bp as emprestimos_bp
    from .livros import bp as livros_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(livros_bp)
    app.register_blueprint(emprestimos_bp)
    registrar_comandos(app)

    @app.errorhandler(403)
    def proibido(_erro):
        return render_template("erro.html", codigo=403,
                               mensagem="Esta página é só para bibliotecários."), 403

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        return render_template("erro.html", codigo=404,
                               mensagem="Não encontramos o que você procurou."), 404

    with app.app_context():
        db.create_all()

    return app
