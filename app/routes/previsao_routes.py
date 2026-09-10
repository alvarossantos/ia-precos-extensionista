import logging

import requests
from flask import Blueprint, jsonify, request

from ..config import config
from ..extensions import limiter
from ..repos import cache_repo, historico_repo
from ..services import cripto_service, previsao_service
from ..services.produtos.aggregator import obter_dados_produto_comum
from ..utils.params import int_param

logger = logging.getLogger(__name__)
previsao_bp = Blueprint("previsao", __name__)


@previsao_bp.route("/previsao")
@limiter.limit(config.RATE_LIMIT_BUSCA)
def previsao():
    produto = request.args.get("produto", "").strip()
    tipo = request.args.get("tipo", "cripto")
    periodo = int_param(request, "periodo", 30)

    if not produto:
        return jsonify({"erro": "parâmetro 'produto' é obrigatório"}), 400

    if tipo == "cripto":
        intervalo, limite = cripto_service.intervalo_por_periodo(periodo)
        try:
            hist = cripto_service.buscar_historico_cripto(produto, limite=limite, intervalo=intervalo)
            preco_atual, _ = cripto_service.buscar_preco_atual_cripto(produto)
        except requests.RequestException as e:
            logger.warning("Falha ao consultar Binance para '%s': %s", produto, e)
            return jsonify({"erro": f"Falha ao consultar Binance: {e}"}), 502
    else:
        try:
            hist, preco_fresco, _ = obter_dados_produto_comum(
                produto, cache_repo, historico_repo, ttl_horas=config.CACHE_TTL_HORAS, dias=periodo,
            )
        except Exception as e:
            logger.exception("Falha ao buscar produtos para '%s'", produto)
            return jsonify({"erro": f"Falha ao buscar produtos: {e}"}), 502

        if not hist:
            return jsonify({"erro": f"Nenhum resultado para '{produto}'"}), 404

        preco_atual = preco_fresco if preco_fresco is not None else hist[-1]["close"]

    return jsonify(previsao_service.gerar_previsao(produto, tipo, hist, preco_atual))
