from datetime import date, timedelta

import pytest

from biblioteca.extensoes import db
from biblioteca.formularios import _isbn_valido
from biblioteca.modelos import Emprestimo, Livro, Usuario
from biblioteca.regras import RegraViolada, devolver, emprestar, renovar
from conftest import criar_livro, criar_usuario, entrar

# Datas relativas a hoje: "atrasado" é calculado com a data real
HOJE = date.today()


# ================= Contas e login =================

def test_cadastro_cria_leitor_e_entra(cliente, app):
    resposta = cliente.post("/cadastro", data={
        "nome": "Ana Souza", "email": "Ana@Exemplo.com", "senha": "segredo123", "confirmar": "segredo123",
    }, follow_redirects=True)
    assert "Bem-vindo(a), Ana!" in resposta.text
    usuario = Usuario.query.filter_by(email="ana@exemplo.com").one()   # e-mail normalizado
    assert usuario.papel == "leitor"
    assert usuario.senha_hash != "segredo123"                          # senha nunca em texto puro


def test_cadastro_valida_campos(cliente, leitor):
    resposta = cliente.post("/cadastro", data={
        "nome": "X", "email": "leo@exemplo.com", "senha": "curta", "confirmar": "outra",
    })
    assert "Já existe uma conta com este e-mail." in resposta.text
    assert "pelo menos 8 caracteres" in resposta.text
    assert "As senhas não são iguais." in resposta.text


def test_login_errado_nao_revela_qual_campo(cliente, leitor):
    resposta = entrar(cliente, senha="errada")
    assert "E-mail ou senha incorretos." in resposta.text
    resposta = entrar(cliente, email="ninguem@exemplo.com")
    assert "E-mail ou senha incorretos." in resposta.text


def test_login_e_logout(cliente, leitor):
    assert "Meus empréstimos" in entrar(cliente).text
    resposta = cliente.post("/sair", follow_redirects=True)
    assert "Você saiu da sua conta." in resposta.text


def test_redirecionamento_seguro(cliente, leitor):
    resposta = cliente.post("/entrar?next=https://site-malicioso.com",
                            data={"email": "leo@exemplo.com", "senha": "senha1234"})
    assert resposta.headers["Location"] == "/"
    resposta = cliente.post("/sair")
    resposta = cliente.post("/entrar?next=/emprestimos/meus",
                            data={"email": "leo@exemplo.com", "senha": "senha1234"})
    assert resposta.headers["Location"] == "/emprestimos/meus"


# ================= Permissões =================

@pytest.mark.parametrize("url", ["/livros/novo", "/emprestimos/painel"])
def test_leitor_nao_acessa_area_do_bibliotecario(cliente, leitor, url):
    entrar(cliente)
    assert cliente.get(url).status_code == 403


def test_visitante_vai_para_o_login(cliente):
    resposta = cliente.get("/emprestimos/meus")
    assert resposta.status_code == 302 and "/entrar" in resposta.headers["Location"]


def test_bibliotecario_cadastra_edita_e_exclui(cliente, bibliotecario):
    entrar(cliente, "bia@exemplo.com")
    resposta = cliente.post("/livros/novo", data={
        "titulo": "O Alienista", "autor": "Machado de Assis", "isbn": "978-85-359-0277-8",
        "ano": 1882, "genero": "Novela", "exemplares": 2,
    }, follow_redirects=True)
    assert "foi adicionado ao catálogo" in resposta.text
    livro = Livro.query.one()

    cliente.post(f"/livros/{livro.id}/editar", data={
        "titulo": "O Alienista", "autor": "Machado de Assis", "isbn": "", "ano": 1882,
        "genero": "Novela", "exemplares": 5,
    })
    assert db.session.get(Livro, livro.id).exemplares == 5

    cliente.post(f"/livros/{livro.id}/excluir")
    assert Livro.query.count() == 0


def test_isbn_e_validado(cliente, bibliotecario):
    entrar(cliente, "bia@exemplo.com")
    resposta = cliente.post("/livros/novo", data={
        "titulo": "X", "autor": "Y", "isbn": "978-85-359-0277-9", "exemplares": 1})
    assert "ISBN inválido" in resposta.text


@pytest.mark.parametrize("isbn, valido", [
    ("978-85-359-0277-8", True), ("9788535902778", True), ("0-306-40615-2", True),
    ("080442957X", True), ("9788535902779", False), ("12345", False),
])
def test_digito_verificador_isbn(isbn, valido):
    assert _isbn_valido(isbn) is valido


# ================= Regras de empréstimo =================

def test_emprestar_e_devolver(app, leitor):
    livro = criar_livro(exemplares=2)
    e = emprestar(livro, leitor, hoje=HOJE)
    assert e.data_prevista == HOJE + timedelta(days=14)
    assert livro.disponiveis == 1
    devolver(e, hoje=HOJE + timedelta(days=3))
    assert livro.disponiveis == 2
    with pytest.raises(RegraViolada, match="já foi devolvido"):
        devolver(e)


def test_sem_exemplares_disponiveis(app, leitor):
    livro = criar_livro(exemplares=1)
    emprestar(livro, criar_usuario("Outro", "outro@exemplo.com"), hoje=HOJE)
    with pytest.raises(RegraViolada, match="Todos os exemplares"):
        emprestar(livro, leitor, hoje=HOJE)


def test_mesmo_livro_duas_vezes(app, leitor):
    livro = criar_livro(exemplares=3)
    emprestar(livro, leitor, hoje=HOJE)
    with pytest.raises(RegraViolada, match="já está com um exemplar"):
        emprestar(livro, leitor, hoje=HOJE)


def test_limite_de_emprestimos(app, leitor):
    for i in range(3):
        emprestar(criar_livro(titulo=f"Livro {i}"), leitor, hoje=HOJE)
    with pytest.raises(RegraViolada, match="limite é de 3"):
        emprestar(criar_livro(titulo="Quarto"), leitor, hoje=HOJE)


def test_atraso_bloqueia_novo_emprestimo(app, leitor):
    antigo = Emprestimo(livro=criar_livro(), usuario=leitor, data_emprestimo=date.today() - timedelta(days=20),
                        data_prevista=date.today() - timedelta(days=6))
    db.session.add(antigo)
    db.session.commit()
    assert antigo.atrasado and antigo.dias_de_atraso == 6
    assert leitor.tem_atraso
    with pytest.raises(RegraViolada, match="livro atrasado"):
        emprestar(criar_livro(titulo="Outro"), leitor)


def test_renovar_uma_vez(app, leitor):
    e = emprestar(criar_livro(), leitor, hoje=HOJE)
    renovar(e, hoje=HOJE + timedelta(days=10))
    assert e.data_prevista == HOJE + timedelta(days=21)
    with pytest.raises(RegraViolada, match="uma vez"):
        renovar(e, hoje=HOJE + timedelta(days=11))


def test_nao_renova_atrasado(app, leitor):
    e = emprestar(criar_livro(), leitor, hoje=HOJE)
    with pytest.raises(RegraViolada, match="atrasados"):
        renovar(e, hoje=HOJE + timedelta(days=20))


def test_reduzir_exemplares_abaixo_do_emprestado(cliente, bibliotecario, leitor):
    livro = criar_livro(exemplares=2)
    emprestar(livro, leitor)
    emprestar(livro, criar_usuario("C", "c@exemplo.com"))
    entrar(cliente, "bia@exemplo.com")
    resposta = cliente.post(f"/livros/{livro.id}/editar", data={
        "titulo": livro.titulo, "autor": livro.autor, "exemplares": 1})
    assert "não pode ser menor" in resposta.text
    resposta = cliente.post(f"/livros/{livro.id}/excluir", follow_redirects=True)
    assert "Não é possível excluir" in resposta.text


# ================= Páginas =================

def test_fluxo_pelo_site(cliente, leitor, bibliotecario):
    livro = criar_livro()
    entrar(cliente)
    resposta = cliente.post(f"/livros/{livro.id}/emprestar", follow_redirects=True)
    assert "Empréstimo feito!" in resposta.text

    resposta = cliente.get("/emprestimos/meus")
    assert "Dom Casmurro" in resposta.text and "Devolver até" in resposta.text

    emprestimo = Emprestimo.query.one()
    resposta = cliente.post(f"/emprestimos/{emprestimo.id}/renovar", follow_redirects=True)
    assert "Renovado!" in resposta.text

    # Leitor não registra devolução; bibliotecário sim
    assert cliente.post(f"/emprestimos/{emprestimo.id}/devolver").status_code == 403
    cliente.post("/sair")
    entrar(cliente, "bia@exemplo.com")
    painel = cliente.get("/emprestimos/painel")
    assert "Dom Casmurro" in painel.text and "Leo" in painel.text
    resposta = cliente.post(f"/emprestimos/{emprestimo.id}/devolver", follow_redirects=True)
    assert "Devolução de" in resposta.text
    assert not emprestimo.ativo


def test_leitor_nao_renova_emprestimo_de_outro(cliente, leitor):
    outro = criar_usuario("Outro", "outro@exemplo.com")
    e = emprestar(criar_livro(), outro)
    entrar(cliente)
    assert cliente.post(f"/emprestimos/{e.id}/renovar").status_code == 403


def test_busca_e_filtro(cliente, app):
    criar_livro("Dom Casmurro", "Machado de Assis", genero="Romance")
    criar_livro("Eu", "Augusto dos Anjos", genero="Poesia")
    assert "Augusto" in cliente.get("/?q=anjos").text
    assert "Dom Casmurro" not in cliente.get("/?q=anjos").text
    resposta = cliente.get("/?genero=Poesia")
    assert "Eu" in resposta.text and "Dom Casmurro" not in resposta.text
    assert "Nenhum livro encontrado" in cliente.get("/?q=xyz").text


def test_paginacao(cliente, app):
    for i in range(15):
        criar_livro(f"Livro {i:02d}")
    pagina1 = cliente.get("/").text
    assert "Página 1 de 2" in pagina1 and "Livro 00" in pagina1 and "Livro 14" not in pagina1
    assert "Livro 14" in cliente.get("/?pagina=2").text


def test_404(cliente):
    resposta = cliente.get("/livros/999")
    assert resposta.status_code == 404 and "Não encontramos" in resposta.text


def test_comando_popular(app):
    resultado = app.test_cli_runner().invoke(args=["popular"])
    assert resultado.exit_code == 0, resultado.output
    assert Livro.query.count() == 14
    assert Usuario.query.filter_by(papel="bibliotecario").count() == 1
    assert Emprestimo.query.count() == 2
    resultado = app.test_cli_runner().invoke(args=["popular"])
    assert resultado.exit_code != 0                     # não duplica os dados
