"""Extensões do Flask criadas uma vez e ligadas à aplicação em create_app."""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()   # protege todos os formulários contra CSRF

login_manager = LoginManager()
login_manager.login_view = "auth.entrar"
login_manager.login_message = "Entre na sua conta para continuar."
login_manager.login_message_category = "info"
