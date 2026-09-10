"""Sessão HTTP compartilhada, com retry/backoff automático.

Antes, cada função de busca (Americanas, KaBuM, Samsung, Buscapé,
Zoom, Binance, OpenRouter...) chamava `requests.get/post` direto, sem
retry — uma falha transitória de rede (timeout, 503, 429) derrubava a
fonte inteira para aquela requisição. Todas as integrações externas
devem passar a usar `get()`/`post()` deste módulo.
"""

import logging

import requests
from requests.adapters import HTTPAdapter, Retry

from .config import config

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}


def _criar_sessao() -> requests.Session:
    sessao = requests.Session()
    retries = Retry(
        total=config.HTTP_MAX_RETRIES,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    sessao.mount("https://", adapter)
    sessao.mount("http://", adapter)
    sessao.headers.update(HEADERS)
    return sessao


sessao_http = _criar_sessao()


def get(url: str, **kwargs):
    kwargs.setdefault("timeout", config.HTTP_TIMEOUT)
    return sessao_http.get(url, **kwargs)


def post(url: str, **kwargs):
    kwargs.setdefault("timeout", config.HTTP_TIMEOUT)
    return sessao_http.post(url, **kwargs)
