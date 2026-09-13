"""Application factory.

Antes, `mock_backend.py` criava o `Flask(__name__)` no nível do
módulo e registrava tudo nele diretamente — o que funciona para um
protótipo, mas dificulta testar (não dá pra criar uma segunda
instância do app com config diferente para os testes) e mistura
"configurar app" com "definir rotas". `create_app()` resolve os dois.
"""

import logging

from flask import Flask
from flask_cors import CORS

from .config import config
from .db import criar_tabelas
from .extensions import configurar_logging, limiter
from .routes import registrar_rotas

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    configurar_logging(debug=config.DEBUG)

    app = Flask(__name__, static_folder="../static", static_url_path="",
                template_folder="templates")
    app.config["JSON_AS_ASCII"] = False

    origins = "*" if config.CORS_ORIGINS == "*" else config.CORS_ORIGINS.split(",")
    CORS(app, origins=origins)

    limiter.init_app(app)

    criar_tabelas()
    registrar_rotas(app)

    logger.info("Aplicação criada (debug=%s, cors_origins=%s)", config.DEBUG, origins)
    return app
