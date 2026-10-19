"""Formulários com validação (Flask-WTF), já protegidos contra CSRF."""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import EmailField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError

from .modelos import Livro, Usuario


class FormCadastro(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired("Informe seu nome."), Length(max=120)])
    email = EmailField("E-mail", validators=[DataRequired("Informe seu e-mail."), Email("E-mail inválido.")])
    senha = PasswordField("Senha", validators=[
        DataRequired("Crie uma senha."), Length(min=8, message="A senha precisa ter pelo menos 8 caracteres.")])
    confirmar = PasswordField("Confirme a senha", validators=[EqualTo("senha", "As senhas não são iguais.")])
    enviar = SubmitField("Criar conta")

    def validate_email(self, campo):
        if Usuario.query.filter_by(email=campo.data.strip().lower()).first():
            raise ValidationError("Já existe uma conta com este e-mail.")


class FormLogin(FlaskForm):
    email = EmailField("E-mail", validators=[DataRequired("Informe seu e-mail.")])
    senha = PasswordField("Senha", validators=[DataRequired("Informe sua senha.")])
    enviar = SubmitField("Entrar")


def _isbn_valido(texto: str) -> bool:
    """Confere o dígito verificador de ISBN-10 ou ISBN-13."""
    digitos = texto.replace("-", "").replace(" ", "").upper()
    if len(digitos) == 13 and digitos.isdigit():
        soma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digitos))
        return soma % 10 == 0
    if len(digitos) == 10 and digitos[:9].isdigit() and (digitos[9].isdigit() or digitos[9] == "X"):
        valores = [int(d) for d in digitos[:9]] + [10 if digitos[9] == "X" else int(digitos[9])]
        return sum(v * (10 - i) for i, v in enumerate(valores)) % 11 == 0
    return False


class FormLivro(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired("Informe o título."), Length(max=200)])
    autor = StringField("Autor", validators=[DataRequired("Informe o autor."), Length(max=160)])
    isbn = StringField("ISBN (opcional)", validators=[Optional(), Length(max=17)])
    ano = IntegerField("Ano de publicação", validators=[
        Optional(), NumberRange(min=1450, max=date.today().year, message="Ano inválido.")])
    genero = StringField("Gênero", validators=[Optional(), Length(max=60)])
    exemplares = IntegerField("Exemplares", default=1, validators=[
        DataRequired("Informe quantos exemplares existem."),
        NumberRange(min=1, max=999, message="Entre 1 e 999 exemplares.")])
    enviar = SubmitField("Salvar livro")

    def __init__(self, *args, livro_id: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.livro_id = livro_id

    def validate_isbn(self, campo):
        if not campo.data:
            return
        if not _isbn_valido(campo.data):
            raise ValidationError("ISBN inválido. Confira os números.")
        outro = Livro.query.filter_by(isbn=campo.data.replace(" ", "")).first()
        if outro and outro.id != self.livro_id:
            raise ValidationError(f"Este ISBN já está cadastrado em \"{outro.titulo}\".")
