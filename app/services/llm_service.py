"""Integração com IA via OpenRouter + NVIDIA NIM como fallback direto.

Fallback automático entre modelos gratuitos. Se o OpenRouter falhar
para todos os modelos, tenta a NVIDIA NIM API diretamente.

Nota sobre concorrência: `_modelo_ativo_index` é estado compartilhado
entre requisições. Protegido por um lock simples porque o Flask dev
server pode rodar com `threaded=True`.
"""

import logging
import threading

import requests

from .. import http_client
from ..config import config

logger = logging.getLogger(__name__)

# Modelos fallback OpenRouter em ordem de prioridade
_FALLBACK_OPENROUTER = [
    "openrouter/free",
    "meta-llama/llama-3.1-8b-instruct",
    "google/gemini-flash-1.5",
    "mistralai/mistral-7b-instruct",
]

# Modelos NVIDIA NIM diretos (não dependem do OpenRouter)
_FALLBACK_NVIDIA = [
    "nvidia/llama-3.3-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/llama-3.1-nemotron-mini-4b-instruct",
]

_lock = threading.Lock()
_modelo_ativo_index = 0


def ia_disponivel() -> bool:
    return bool(config.OPENROUTER_API_KEY or config.NVIDIA_API_KEY)


def _lista_modelos():
    """Modelo primário do .env + fallbacks OpenRouter, sem duplicatas."""
    primario = config.OPENROUTER_MODEL.strip()
    lista = [primario]
    for m in _FALLBACK_OPENROUTER:
        if m not in lista:
            lista.append(m)
    return lista


def _chamar_openrouter(modelos, sistema, prompt, max_tokens, timeout):
    """Tenta modelos via OpenRouter. Retorna (texto, modelo) ou None."""
    for mdl in modelos:
        try:
            resp = http_client.post(
                config.OPENROUTER_BASE,
                headers={
                    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://ia-precos-extensionista-g.onrender.com",
                    "X-Title": "PreçoCerto",
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
                return texto, mdl
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (401, 402, 403, 429, 500, 502, 503, 504):
                logger.warning("OpenRouter %s: HTTP %s", mdl, status)
                continue
        except requests.RequestException as e:
            logger.warning("OpenRouter %s: %s", mdl, e)

    return None, None


def _chamar_nvidia(sistema, prompt, max_tokens, timeout):
    """Tenta modelos via NVIDIA NIM direto. Retorna (texto, modelo) ou None."""
    if not config.NVIDIA_API_KEY:
        return None, None

    for mdl in _FALLBACK_NVIDIA:
        try:
            resp = http_client.post(
                config.NVIDIA_BASE,
                headers={
                    "Authorization": f"Bearer {config.NVIDIA_API_KEY}",
                    "Content-Type": "application/json",
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
                return texto, f"nvidia/{mdl}"
        except Exception as e:
            logger.warning("NVIDIA %s: %s", mdl, e)

    return None, None


def chat(sistema: str, prompt: str, modelo: str = None, max_tokens: int = 200, timeout: int = 30):
    """Chama IA com fallback: OpenRouter → NVIDIA NIM.
    Retorna (texto, modelo_usado) ou (None, None)."""
    global _modelo_ativo_index

    if not ia_disponivel():
        return None, None

    # Se modelo específico solicitado, tenta só ele
    if modelo is not None:
        texto, mdl = _chamar_openrouter([modelo], sistema, prompt, max_tokens, timeout)
        if texto:
            return texto, mdl
        texto, mdl = _chamar_nvidia(sistema, prompt, max_tokens, timeout)
        return (texto, mdl) if texto else (None, None)

    # Fallback automático: OpenRouter primeiro, depois NVIDIA
    with _lock:
        indice_atual = _modelo_ativo_index

    lista = _lista_modelos()
    modelos = lista[indice_atual:] + lista[:indice_atual]

    texto, mdl = _chamar_openrouter(modelos, sistema, prompt, max_tokens, timeout)
    if texto:
        if mdl in lista:
            with _lock:
                _modelo_ativo_index = lista.index(mdl)
        return texto, mdl

    # OpenRouter falhou tudo → tenta NVIDIA direto
    logger.info("OpenRouter falhou — tentando NVIDIA NIM")
    texto, mdl = _chamar_nvidia(sistema, prompt, max_tokens, timeout)
    if texto:
        return texto, mdl

    logger.warning("Todos os provedores de IA falharam")
    return None, None
