"""Fonte de dados de criptomoedas via Binance (API pública).
Fallback: CoinGecko quando a Binance bloqueia (418 anti-bot em cloud).
"""

import logging
from datetime import datetime

from .. import http_client
from ..config import config

logger = logging.getLogger(__name__)

_PERIODO_INTERVALOS = {
    7: ("1d", 7),
    30: ("1d", 30),
    90: ("1d", 90),
    180: ("1d", 180),
    365: ("1d", 365),
}

# Mapeamento Binance symbol → CoinGecko id
_SYMBOL_TO_GECKO = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "DOTUSDT": "polkadot",
    "DOGEUSDT": "dogecoin",
    "AVAXUSDT": "avalanche-2",
    "MATICUSDT": "matic-network",
    "LINKUSDT": "chainlink",
    "LTCUSDT": "litecoin",
}


def intervalo_por_periodo(periodo: int):
    if periodo in _PERIODO_INTERVALOS:
        return _PERIODO_INTERVALOS[periodo]
    return "1d", min(periodo, 365)


def _symbol_to_gecko(symbol: str) -> str | None:
    """Converte symbol Binance para CoinGecko id."""
    return _SYMBOL_TO_GECKO.get(symbol.upper())


def _buscar_via_binance(symbol: str, limite: int, intervalo: str):
    """Tenta buscar na Binance. Retorna lista ou levanta exceção."""
    resp = http_client.binance_get(
        f"{config.BINANCE_BASE}/klines",
        params={"symbol": symbol, "interval": intervalo, "limit": limite},
    )
    if resp.status_code == 418:
        raise ValueError("Binance bloqueou (anti-bot)")
    resp.raise_for_status()
    dados = resp.json()
    return [
        {
            "time": datetime.fromtimestamp(item[0] / 1000).strftime("%d/%m/%y"),
            "close": float(item[4]),
        }
        for item in dados
    ]


def _buscar_preco_via_binance(symbol: str):
    """Tenta buscar preço na Binance. Retorna (preco, variacao)."""
    resp = http_client.binance_get(
        f"{config.BINANCE_BASE}/ticker/24hr",
        params={"symbol": symbol},
    )
    if resp.status_code == 418:
        raise ValueError("Binance bloqueou (anti-bot)")
    resp.raise_for_status()
    dados = resp.json()
    return float(dados["lastPrice"]), float(dados["priceChangePercent"])


def _buscar_via_coingecko(symbol: str, dias: int):
    """Fallback: CoinGecko free API."""
    gecko_id = _symbol_to_gecko(symbol)
    if not gecko_id:
        raise ValueError(f"Symbol {symbol} não mapeado para CoinGecko")

    resp = http_client.get(
        f"https://api.coingecko.com/api/v3/coins/{gecko_id}/market_chart",
        params={"vs_currency": "usd", "days": dias, "interval": "daily"},
        timeout=20,
    )
    resp.raise_for_status()
    dados = resp.json()
    prices = dados.get("prices", [])
    return [
        {
            "time": datetime.fromtimestamp(p[0] / 1000).strftime("%d/%m/%y"),
            "close": p[1],
        }
        for p in prices
    ]


def _buscar_preco_via_coingecko(symbol: str):
    """Fallback: preço atual via CoinGecko."""
    gecko_id = _symbol_to_gecko(symbol)
    if not gecko_id:
        raise ValueError(f"Symbol {symbol} não mapeado para CoinGecko")

    resp = http_client.get(
        f"https://api.coingecko.com/api/v3/simple/price",
        params={"ids": gecko_id, "vs_currencies": "usd", "include_24hr_vol": "true"},
        timeout=15,
    )
    resp.raise_for_status()
    dados = resp.json().get(gecko_id, {})
    preco = dados.get("usd", 0)
    # CoinGecko não tem variação 24h no /simple/price sem market_data
    return preco, 0.0


def buscar_historico_cripto(symbol: str, limite: int = 100, intervalo: str = "1d"):
    """Busca histórico. Tenta Binance, fallback CoinGecko."""
    try:
        return _buscar_via_binance(symbol, limite, intervalo)
    except Exception as e:
        logger.warning("Binance falhou para %s: %s — tentando CoinGecko", symbol, e)
        dias = min(limite, 365)
        return _buscar_via_coingecko(symbol, dias)


def buscar_preco_atual_cripto(symbol: str):
    """Busca preço atual. Tenta Binance, fallback CoinGecko."""
    try:
        return _buscar_preco_via_binance(symbol)
    except Exception as e:
        logger.warning("Binance falhou para %s: %s — tentando CoinGecko", symbol, e)
        return _buscar_preco_via_coingecko(symbol)
