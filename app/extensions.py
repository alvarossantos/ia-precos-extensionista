"""Extensões compartilhadas: logging estruturado e rate limiting.

Antes, falhas em qualquer lugar do backend eram engolidas por
`except Exception: pass/continue`, sem nenhum rastro. Isso torna
praticamente impossível descobrir por que uma fonte parou de
retornar dados. Com logging configurado, toda falha tratada ainda
aparece no console (nível WARNING/ERROR) — sem quebrar a resposta
ao usuário, mas sem desaparecer silenciosamente.
"""

import logging
import sys

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .config import config

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[config.RATE_LIMIT_DEFAULT] if config.RATE_LIMIT_ENABLED else [],
    enabled=config.RATE_LIMIT_ENABLED,
    storage_uri="memory://",
)


def configurar_logging(debug: bool = False) -> None:
    nivel = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    # Bibliotecas de terceiros tendem a ser muito verbosas em DEBUG.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING if not debug else logging.INFO)
