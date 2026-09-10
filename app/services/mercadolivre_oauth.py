"""Fluxo OAuth do Mercado Livre.

O token OAuth é opcional para a busca de produtos (ver
`produtos/fontes.py::buscar_mercadolivre`), mas dá limites de uso
mais altos quando configurado — por isso o fluxo continua disponível.
"""

import logging
import os

import requests
from dotenv import find_dotenv, set_key

from .. import http_client
from ..config import config

logger = logging.getLogger(__name__)


def status():
    """Verifica se o ML está configurado e com token válido."""
    access_token = os.getenv("ML_ACCESS_TOKEN")
    conectado = False
    usuario = None

    if access_token:
        try:
            resp = http_client.get(
                f"{config.ML_BASE}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                dados = resp.json()
                conectado = True
                usuario = dados.get("nickname", dados.get("id"))
            elif resp.status_code == 401:
                if refresh_token():
                    return status()
        except requests.RequestException as e:
            logger.warning("Falha ao consultar /users/me do Mercado Livre: %s", e)

    return {
        "conectado": conectado,
        "usuario": usuario,
        "client_id_configurado": bool(config.ML_CLIENT_ID),
    }


def gerar_auth_url():
    if not config.ML_CLIENT_ID:
        return None
    return (
        "https://auth.mercadolivre.com.br/authorization"
        "?response_type=code"
        f"&client_id={config.ML_CLIENT_ID}"
        f"&redirect_uri={config.ML_REDIRECT_URI}"
    )


def trocar_code_por_token(code: str):
    """Troca o authorization code por access_token/refresh_token."""
    if not (config.ML_CLIENT_ID and config.ML_CLIENT_SECRET):
        raise RuntimeError("ML_CLIENT_ID e ML_CLIENT_SECRET devem estar no .env")

    resp = http_client.post(
        f"{config.ML_BASE}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": config.ML_CLIENT_ID,
            "client_secret": config.ML_CLIENT_SECRET,
            "code": code,
            "redirect_uri": config.ML_REDIRECT_URI,
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Falha ao obter token: {resp.text}")

    dados = resp.json()
    _salvar_tokens(dados["access_token"], dados["refresh_token"])
    return dados


def refresh_token() -> bool:
    """Renova o access_token usando o refresh_token salvo."""
    refresh = os.getenv("ML_REFRESH_TOKEN")
    if not (config.ML_CLIENT_ID and config.ML_CLIENT_SECRET and refresh):
        return False

    try:
        resp = http_client.post(
            f"{config.ML_BASE}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": config.ML_CLIENT_ID,
                "client_secret": config.ML_CLIENT_SECRET,
                "refresh_token": refresh,
            },
        )
        if resp.status_code == 200:
            dados = resp.json()
            _salvar_tokens(dados["access_token"], dados["refresh_token"])
            return True
    except requests.RequestException as e:
        logger.warning("Falha ao renovar token do Mercado Livre: %s", e)
    return False


def _salvar_tokens(access_token: str, refresh_token_: str):
    """Salva tokens em runtime (env do processo) e persiste no .env.

    Antes o .env era reescrito linha a linha manualmente (`open` +
    `readlines` + `writelines`); usa `python-dotenv.set_key`, que edita
    só a chave necessária e não corrompe o arquivo se o processo for
    interrompido no meio da escrita.
    """
    os.environ["ML_ACCESS_TOKEN"] = access_token
    os.environ["ML_REFRESH_TOKEN"] = refresh_token_

    caminho_env = find_dotenv(usecwd=True)
    if not caminho_env:
        logger.warning("Nenhum arquivo .env encontrado — tokens salvos só em memória")
        return
    set_key(caminho_env, "ML_ACCESS_TOKEN", access_token)
    set_key(caminho_env, "ML_REFRESH_TOKEN", refresh_token_)
