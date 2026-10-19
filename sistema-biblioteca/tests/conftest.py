import pytest

from biblioteca import create_app
from biblioteca.extensoes import db
from biblioteca.modelos import BIBLIOTECARIO, LEITOR, Livro, Usuario


@pytest.fixture
def app():
    """Uma aplicação nova, com banco em memória, para cada teste."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "teste",
    })
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cliente(app):
    return app.test_client()


def criar_usuario(nome="Leo", email="leo@exemplo.com", papel=LEITOR, senha="senha1234"):
    usuario = Usuario(nome=nome, email=email, papel=papel)
    usuario.definir_senha(senha)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def criar_livro(titulo="Dom Casmurro", autor="Machado de Assis", exemplares=1, genero="Romance"):
    livro = Livro(titulo=titulo, autor=autor, exemplares=exemplares, genero=genero)
    db.session.add(livro)
    db.session.commit()
    return livro


def entrar(cliente, email="leo@exemplo.com", senha="senha1234"):
    return cliente.post("/entrar", data={"email": email, "senha": senha}, follow_redirects=True)


@pytest.fixture
def leitor(app):
    return criar_usuario()


@pytest.fixture
def bibliotecario(app):
    return criar_usuario("Bia", "bia@exemplo.com", BIBLIOTECARIO)
