"""Configuração central da aplicação, carregada de variáveis de ambiente.

Antes esses valores estavam espalhados como constantes soltas pelo
mock_backend.py. Centralizar aqui facilita trocar comportamento
(timeouts, TTL, limites) sem mexer em código, só no .env.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _bool_env(nome: str, padrao: bool) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "yes", "sim")


class Config:
    # ---- Flask ----
    DEBUG = _bool_env("FLASK_DEBUG", True)
    HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # ---- Bancos locais (SQLite) ----
    # Nota: o desenho original do projeto previa Postgres para o schema
    # fonte/produto/preco_historico/previsao. Este backend de
    # desenvolvimento usa SQLite (cache, histórico local e alertas) por
    # simplicidade — ver README, seção "Limitações conhecidas".
    CACHE_DB_PATH = os.getenv("CACHE_DB_PATH", "cache.db")
    HISTORICO_DB_PATH = os.getenv("HISTORICO_DB_PATH", "historico_local.db")
    ALERTAS_DB_PATH = os.getenv("ALERTAS_DB_PATH", "alertas.db")

    # ---- Cache / TTL ----
    CACHE_TTL_HORAS = int(os.getenv("CACHE_TTL_HORAS", "6"))

    # ---- HTTP (fontes externas) ----
    HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
    HTTP_MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "2"))

    # ---- Rate limiting (Flask-Limiter) ----
    RATE_LIMIT_ENABLED = _bool_env("RATE_LIMIT_ENABLED", True)
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60 per minute")
    RATE_LIMIT_BUSCA = os.getenv("RATE_LIMIT_BUSCA", "20 per minute")
    RATE_LIMIT_IA = os.getenv("RATE_LIMIT_IA", "10 per minute")

    # ---- Binance (cripto) ----
    BINANCE_BASE = "https://api.binance.com/api/v3"

    # ---- SerpAPI (Google Shopping / Google orgânico) ----
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

    # ---- OpenRouter (IA) ----
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"


config = Config()
