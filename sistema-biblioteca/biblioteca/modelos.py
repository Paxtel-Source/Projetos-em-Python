"""Tabelas do banco de dados (SQLAlchemy)."""

from datetime import date, datetime

from flask_login import UserMixin
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from .extensoes import db, login_manager

LEITOR = "leitor"
BIBLIOTECARIO = "bibliotecario"


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(256), nullable=False)
    papel = db.Column(db.String(20), nullable=False, default=LEITOR)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    emprestimos = db.relationship("Emprestimo", back_populates="usuario", lazy="dynamic")

    # A senha nunca é guardada: só o hash (que não dá para reverter)
    def definir_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def senha_correta(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    @property
    def bibliotecario(self) -> bool:
        return self.papel == BIBLIOTECARIO

    @property
    def emprestimos_ativos(self) -> list["Emprestimo"]:
        return self.emprestimos.filter(Emprestimo.data_devolucao.is_(None)).order_by(Emprestimo.data_prevista).all()

    @property
    def tem_atraso(self) -> bool:
        return any(e.atrasado for e in self.emprestimos_ativos)


@login_manager.user_loader
def carregar_usuario(usuario_id: str) -> Usuario | None:
    return db.session.get(Usuario, int(usuario_id))


class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False, index=True)
    autor = db.Column(db.String(160), nullable=False, index=True)
    isbn = db.Column(db.String(17), unique=True)
    ano = db.Column(db.Integer)
    genero = db.Column(db.String(60))
    exemplares = db.Column(db.Integer, nullable=False, default=1)

    emprestimos = db.relationship("Emprestimo", back_populates="livro", lazy="dynamic",
                                  cascade="all, delete-orphan")

    @property
    def emprestados(self) -> int:
        return self.emprestimos.filter(Emprestimo.data_devolucao.is_(None)).count()

    @property
    def disponiveis(self) -> int:
        return max(self.exemplares - self.emprestados, 0)


class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey("livro.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    data_emprestimo = db.Column(db.Date, nullable=False, default=date.today)
    data_prevista = db.Column(db.Date, nullable=False)
    data_devolucao = db.Column(db.Date)            # vazio enquanto não devolver
    renovado = db.Column(db.Boolean, nullable=False, default=False)

    livro = db.relationship("Livro", back_populates="emprestimos")
    usuario = db.relationship("Usuario", back_populates="emprestimos")

    @property
    def ativo(self) -> bool:
        return self.data_devolucao is None

    @property
    def dias_de_atraso(self) -> int:
        referencia = self.data_devolucao or date.today()
        return max((referencia - self.data_prevista).days, 0)

    @property
    def atrasado(self) -> bool:
        return self.ativo and self.dias_de_atraso > 0


def contar_por_genero() -> list[tuple[str, int]]:
    """Quantidade de títulos por gênero, para os filtros da página inicial."""
    return (db.session.query(Livro.genero, func.count(Livro.id))
            .filter(Livro.genero.isnot(None)).group_by(Livro.genero).order_by(Livro.genero).all())
