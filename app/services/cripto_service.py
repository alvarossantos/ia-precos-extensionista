"""Fonte de dados de criptomoedas via Binance (API pública)."""

import logging
from datetime import datetime

from .. import http_client
from ..config import config

logger = logging.getLogger(__name__)

# Intervalos Binance por período (dias) → (intervalo, limite)
_PERIODO_INTERVALOS = {
    7: ("1d", 7),
    30: ("1d", 30),
    90: ("1d", 90),
    180: ("1d", 180),
    365: ("1d", 365),
}


def intervalo_por_periodo(periodo: int):
    """Mapeia período em dias para (intervalo, limite) da Binance."""
    if periodo in _PERIODO_INTERVALOS:
        return _PERIODO_INTERVALOS[periodo]
    # Períodos não mapeados: usa 1d com limite proporcional (cap 365)
    return "1d", min(periodo, 365)


def buscar_historico_cripto(symbol: str, limite: int = 100, intervalo: str = "1d"):
    resp = http_client.get(
        f"{config.BINANCE_BASE}/klines",
        params={"symbol": symbol, "interval": intervalo, "limit": limite},
    )
    resp.raise_for_status()
    dados = resp.json()
    return [
        {
            "time": datetime.fromtimestamp(item[0] / 1000).strftime("%d/%m/%y"),
            "close": float(item[4]),
        }
        for item in dados
    ]


def buscar_preco_atual_cripto(symbol: str):
    resp = http_client.get(f"{config.BINANCE_BASE}/ticker/24hr", params={"symbol": symbol})
    resp.raise_for_status()
    dados = resp.json()
    return float(dados["lastPrice"]), float(dados["priceChangePercent"])
