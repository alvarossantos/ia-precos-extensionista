import logging

from flask import Blueprint, jsonify, request

from ..config import config
from ..extensions import limiter
from ..services.produtos.aggregator import buscar_ofertas

logger = logging.getLogger(__name__)
comparar_bp = Blueprint("comparar", __name__)


@comparar_bp.route("/comparar")
@limiter.limit(config.RATE_LIMIT_BUSCA)
def comparar():
    """Compara preços entre múltiplos termos (até 5)."""
    termos_raw = request.args.get("termos", "")
    if not termos_raw:
        return jsonify({"erro": "parâmetro 'termos' obrigatório (separado por vírgula)"}), 400

    termos = [t.strip() for t in termos_raw.split(",") if t.strip()]
    if len(termos) < 2:
        return jsonify({"erro": "insira pelo menos 2 termos para comparar"}), 400

    comparacao = []
    for termo in termos[:5]:
        try:
            resultados = buscar_ofertas(termo, limite=3)
        except Exception as e:
            logger.warning("Falha ao comparar '%s': %s", termo, e)
            comparacao.append({"termo": termo, "erro": "falha na busca"})
            continue

        precos = [r["preco"] for r in resultados if r["preco"]]
        fontes_usadas = list({r.get("fonte", "") for r in resultados})
        comparacao.append({
            "termo": termo,
            "resultados": len(resultados),
            "menor_preco": min(precos) if precos else None,
            "preco_medio": round(sum(precos) / len(precos), 2) if precos else None,
            "fontes": fontes_usadas,
            "top_resultado": resultados[0] if resultados else None,
        })

    return jsonify({"comparacao": comparacao})
