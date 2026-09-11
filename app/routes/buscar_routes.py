import logging

from flask import Blueprint, jsonify, request

from ..config import config
from ..extensions import limiter
from ..services.produtos.aggregator import FONTES_PADRAO, buscar_ofertas
from ..utils.params import int_param

logger = logging.getLogger(__name__)
buscar_bp = Blueprint("buscar", __name__)


@buscar_bp.route("/buscar")
@limiter.limit(config.RATE_LIMIT_BUSCA)
def buscar():
    """Busca ampliada em múltiplas fontes."""
    produto = request.args.get("produto", "").strip()
    limite = min(int_param(request, "limite", 5), 50)
    fontes_raw = request.args.get("fontes", ",".join(FONTES_PADRAO))
    fontes_selecionadas = [f.strip() for f in fontes_raw.split(",") if f.strip()]
    so_novos = request.args.get("so_novos", "").lower() in ("1", "true", "sim", "novos")

    if not produto:
        return jsonify({"erro": "parâmetro 'produto' é obrigatório"}), 400

    try:
        resultados = buscar_ofertas(produto, limite=limite, fontes_selecionadas=fontes_selecionadas,
                                     so_novos=so_novos)
    except Exception as e:
        logger.exception("Falha ao buscar '%s'", produto)
        return jsonify({"erro": f"Falha ao buscar: {e}"}), 502

    if not resultados:
        return jsonify({"erro": f"Nenhum resultado para '{produto}'"}), 404

    precos = [r["preco"] for r in resultados if r["preco"] is not None]
    fontes_agrupadas = {}
    for r in resultados:
        fontes_agrupadas.setdefault(r.get("fonte", "Outra"), []).append(r)

    return jsonify({
        "produto": produto,
        "total": len(resultados),
        "resultados": resultados,
        "por_fonte": {k: len(v) for k, v in fontes_agrupadas.items()},
        "estatisticas": {
            "menor_preco": min(precos) if precos else None,
            "maior_preco": max(precos) if precos else None,
            "preco_medio": round(sum(precos) / len(precos), 2) if precos else None,
            "melhor_oferta": resultados[0] if resultados else None,
        },
    })
