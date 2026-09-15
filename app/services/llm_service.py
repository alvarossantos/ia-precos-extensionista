"""Integração com IA via OpenRouter, com fallback automático entre
modelos gratuitos.

Nota sobre concorrência: `_modelo_ativo_index` é estado compartilhado
entre requisições. Protegido por um lock simples porque o Flask dev
server pode rodar com `threaded=True`; se este backend for um dia
servido por múltiplos processos (gunicorn com vários workers), essa
memória deixa de ser compartilhada entre processos — o pior caso é
apenas "esquecer" o último modelo que funcionou e testar a lista de
novo, sem quebrar nada.
"""

import logging
import threading

import requests

from .. import http_client
from ..config import config

logger = logging.getLogger(__name__)

# Modelos fallback em ordem de prioridade. O primeiro (config.OPENROUTER_MODEL)
# é o padrão; os demais entram em rollback quando o modelo ativo falha
# (rate limit, quota, erro, etc.). "openrouter/free" roteia automaticamente
# para o melhor modelo gratuito disponível no momento.
_FALLBACK_MODELOS = [
    "openrouter/free",
    "meta-llama/llama-3.1-8b-instruct",
    "google/gemini-flash-1.5",
    "mistralai/mistral-7b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/llama-3.1-nemotron-mini-4b-instruct",
    "nvidia/llama-3.3-70b-instruct",
]

_lock = threading.Lock()
_modelo_ativo_index = 0


def ia_disponivel() -> bool:
    return bool(config.OPENROUTER_API_KEY)


def _lista_modelos():
    """Modelo primário do .env + fallbacks, sem duplicatas."""
    primario = config.OPENROUTER_MODEL.strip()
    lista = [primario]
    for m in _FALLBACK_MODELOS:
        if m not in lista:
            lista.append(m)
    return lista


def chat(sistema: str, prompt: str, modelo: str = None, max_tokens: int = 200, timeout: int = 30):
    """Chama um modelo via OpenRouter com rollback automático entre a
    lista de fallbacks. Retorna (texto, modelo_usado) ou (None, None)
    se todos falharem ou não houver chave configurada."""
    global _modelo_ativo_index

    if not ia_disponivel():
        return None, None

    if modelo is not None:
        modelos = [modelo]
    else:
        with _lock:
            indice_atual = _modelo_ativo_index
        lista = _lista_modelos()
        modelos = lista[indice_atual:] + lista[:indice_atual]

    ultimo_erro = None
    for mdl in modelos:
        try:
            resp = http_client.post(
                config.OPENROUTER_BASE,
                headers={
                    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://127.0.0.1:5000",
                    "X-Title": "Preditor IA",
                },
                json={
                    "model": mdl,
                    "messages": [
                        {"role": "system", "content": sistema},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            texto = (resp.json()["choices"][0]["message"].get("content") or "").strip()
            if texto:
                lista_completa = _lista_modelos()
                if mdl in lista_completa:
                    with _lock:
                        _modelo_ativo_index = lista_completa.index(mdl)
                return texto, mdl
            ultimo_erro = f"{mdl}: resposta vazia"
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (401, 402, 403, 429, 500, 502, 503, 504):
                ultimo_erro = f"{mdl}: HTTP {status}"
                continue
            ultimo_erro = f"{mdl}: HTTP {status}"
        except requests.RequestException as e:
            ultimo_erro = f"{mdl}: {e}"

    logger.warning("Todos os modelos de IA falharam. Último erro: %s", ultimo_erro)
    return None, None
