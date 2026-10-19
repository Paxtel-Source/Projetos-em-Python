"""Comandos de terminal: flask --app biblioteca <comando>."""

import getpass
from datetime import date, timedelta

import click

from .extensoes import db
from .modelos import BIBLIOTECARIO, Emprestimo, Livro, Usuario

# Títulos clássicos em domínio público, para testar o sistema
LIVROS_EXEMPLO = [
    ("Dom Casmurro", "Machado de Assis", 1899, "Romance", 3),
    ("Memórias Póstumas de Brás Cubas", "Machado de Assis", 1881, "Romance", 2),
    ("O Alienista", "Machado de Assis", 1882, "Novela", 2),
    ("O Cortiço", "Aluísio Azevedo", 1890, "Romance", 2),
    ("Iracema", "José de Alencar", 1865, "Romance", 1),
    ("Senhora", "José de Alencar", 1875, "Romance", 2),
    ("Triste Fim de Policarpo Quaresma", "Lima Barreto", 1915, "Romance", 1),
    ("Os Sertões", "Euclides da Cunha", 1902, "Não ficção", 1),
    ("A Moreninha", "Joaquim Manuel de Macedo", 1844, "Romance", 2),
    ("Eu", "Augusto dos Anjos", 1912, "Poesia", 1),
    ("Lira dos Vinte Anos", "Álvares de Azevedo", 1853, "Poesia", 1),
    ("A Escrava Isaura", "Bernardo Guimarães", 1875, "Romance", 1),
    ("Noite na Taverna", "Álvares de Azevedo", 1855, "Contos", 2),
    ("O Guarani", "José de Alencar", 1857, "Romance", 2),
]


def registrar_comandos(app):

    @app.cli.command("criar-bibliotecario")
    @click.option("--nome", prompt="Nome")
    @click.option("--email", prompt="E-mail")
    def criar_bibliotecario(nome, email):
        """Cria uma conta de bibliotecário (ou promove uma conta existente)."""
        email = email.strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            usuario.papel = BIBLIOTECARIO
            click.echo(f"{usuario.nome} agora é bibliotecário(a).")
        else:
            senha = getpass.getpass("Senha (mínimo 8 caracteres): ")
            if len(senha) < 8:
                raise click.ClickException("A senha precisa ter pelo menos 8 caracteres.")
            usuario = Usuario(nome=nome.strip(), email=email, papel=BIBLIOTECARIO)
            usuario.definir_senha(senha)
            db.session.add(usuario)
            click.echo(f"Conta de bibliotecário(a) criada para {email}.")
        db.session.commit()

    @app.cli.command("popular")
    def popular():
        """Preenche o banco com livros e contas de demonstração."""
        if Livro.query.first():
            raise click.ClickException("O banco já tem livros. Apague instance/biblioteca.db para recomeçar.")

        livros = [Livro(titulo=t, autor=a, ano=ano, genero=g, exemplares=n) for t, a, ano, g, n in LIVROS_EXEMPLO]
        db.session.add_all(livros)

        contas = [
            ("Bia Bibliotecária", "bibliotecaria@exemplo.com", BIBLIOTECARIO),
            ("Leo Leitor", "leitor@exemplo.com", "leitor"),
        ]
        usuarios = []
        for nome, email, papel in contas:
            u = Usuario(nome=nome, email=email, papel=papel)
            u.definir_senha("senha1234")
            usuarios.append(u)
        db.session.add_all(usuarios)

        # Dois empréstimos para o leitor, um deles atrasado, para o painel ter o que mostrar
        hoje = date.today()
        db.session.add_all([
            Emprestimo(livro=livros[0], usuario=usuarios[1], data_emprestimo=hoje - timedelta(days=3),
                       data_prevista=hoje + timedelta(days=11)),
            Emprestimo(livro=livros[3], usuario=usuarios[1], data_emprestimo=hoje - timedelta(days=20),
                       data_prevista=hoje - timedelta(days=6)),
        ])
        db.session.commit()
        click.echo(f"{len(livros)} livros e 2 contas criados (senha das duas: senha1234):")
        for nome, email, papel in contas:
            click.echo(f"  {email:<28} {papel}")
