import logging

import requests
from flask import Blueprint, jsonify, request

from ..config import config
from ..extensions import limiter
from ..repos import cache_repo, historico_repo
from ..services import cripto_service
from ..services.produtos.aggregator import obter_dados_produto_comum
from ..utils.params import int_param

logger = logging.getLogger(__name__)
historico_bp = Blueprint("historico", __name__)


@historico_bp.route("/historico")
@limiter.limit(config.RATE_LIMIT_BUSCA)
def historico():
    produto = request.args.get("produto", "").strip()
    tipo = request.args.get("tipo", "cripto")
    periodo = int_param(request, "periodo", 30)

    if not produto:
        return jsonify({"erro": "parâmetro 'produto' é obrigatório"}), 400

    resultados_finais = []

    if tipo == "cripto":
        intervalo, limite = cripto_service.intervalo_por_periodo(periodo)
        try:
            hist = cripto_service.buscar_historico_cripto(produto, limite=limite, intervalo=intervalo)
            preco_atual, variacao_24h = cripto_service.buscar_preco_atual_cripto(produto)
        except requests.RequestException as e:
            logger.warning("Falha ao consultar Binance para '%s': %s", produto, e)
            return jsonify({"erro": f"Falha ao consultar Binance: {e}"}), 502

        menor = min(hist, key=lambda p: p["close"]) if hist else None
        maior = max(hist, key=lambda p: p["close"]) if hist else None
        estatisticas = {
            "menor_preco": menor["close"] if menor else None,
            "maior_preco": maior["close"] if maior else None,
            "preco_medio": round(sum(p["close"] for p in hist) / len(hist), 2) if hist else None,
        }
        menor_valor = {"preco": menor["close"], "data": menor["time"]} if menor else None
        maior_valor = {"preco": maior["close"], "data": maior["time"]} if maior else None

    else:
        try:
            hist, preco_fresco, resultados_finais = obter_dados_produto_comum(
                produto, cache_repo, historico_repo, ttl_horas=config.CACHE_TTL_HORAS, dias=periodo,
            )
        except Exception as e:
            logger.exception("Falha ao buscar produtos para '%s'", produto)
            return jsonify({"erro": f"Falha ao buscar produtos: {e}"}), 502

        if not hist:
            return jsonify({"erro": f"Nenhum resultado para '{produto}'"}), 404

        preco_atual = preco_fresco if preco_fresco is not None else hist[-1]["close"]
        variacao_24h = (
            round(((hist[-1]["close"] - hist[0]["close"]) / hist[0]["close"]) * 100, 2)
            if len(hist) > 1 else 0.0
        )

        precos_extremos = [r["preco"] for r in resultados_finais if r.get("preco") is not None]
        if precos_extremos:
            menor_valor = {"preco": min(precos_extremos), "data": "atual"}
            maior_valor = {"preco": max(precos_extremos), "data": "atual"}
        else:
            menor_valor = maior_valor = None

        estatisticas = {
            "menor_preco": min(precos_extremos) if precos_extremos else None,
            "maior_preco": max(precos_extremos) if precos_extremos else None,
            "preco_medio": round(sum(precos_extremos) / len(precos_extremos), 2) if precos_extremos else None,
        }

    return jsonify({
        "produto": produto,
        "tipo": tipo,
        "preco_atual": preco_atual,
        "variacao_24h": variacao_24h,
        "historico": hist,
        "pontos_coletados": len(hist),
        "menor_valor": menor_valor,
        "maior_valor": maior_valor,
        "estatisticas": estatisticas,
        "resultados": resultados_finais,
    })
