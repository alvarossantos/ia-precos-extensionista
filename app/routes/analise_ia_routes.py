import logging

from flask import Blueprint, jsonify, request

from ..config import config
from ..extensions import limiter
from ..services import llm_service
from ..services.produtos.aggregator import buscar_ofertas
from ..utils.params import int_param

logger = logging.getLogger(__name__)
analise_ia_bp = Blueprint("analise_ia", __name__)


@analise_ia_bp.route("/analise-ia")
@limiter.limit(config.RATE_LIMIT_IA)
def analise_ia():
    """Coleta os preços reais das fontes e usa um LLM (OpenRouter) para
    montar um dashboard inteligente: melhor compra, faixa de preço e conselho."""
    produto = request.args.get("produto", "").strip()
    limite = min(int_param(request, "limite", 5), 20)

    if not produto:
        return jsonify({"erro": "parâmetro 'produto' é obrigatório"}), 400

    try:
        resultados = buscar_ofertas(produto, limite=limite)
    except Exception as e:
        logger.warning("Falha ao coletar preços para análise de IA de '%s': %s", produto, e)
        resultados = []

    precos = [r["preco"] for r in resultados if r["preco"]]

    fontes_agrupadas = {}
    for r in resultados:
        fontes_agrupadas.setdefault(r.get("fonte", "Outra"), []).append(r)

    base = {
        "produto": produto,
        "total_ofertas": len(resultados),
        "por_fonte": {k: len(v) for k, v in fontes_agrupadas.items()},
        "menor_preco": min(precos) if precos else None,
        "maior_preco": max(precos) if precos else None,
        "preco_medio": round(sum(precos) / len(precos), 2) if precos else None,
        "melhor_oferta": resultados[0] if resultados else None,
        "ia_disponivel": llm_service.ia_disponivel(),
    }

    # Sem IA disponível ou sem preços coletados → retorna só os dados (fail-open)
    if not llm_service.ia_disponivel() or not precos:
        return jsonify(base)

    resumo = "\n".join(
        f"- {r['nome'][:60]} → R$ {r['preco']} ({r['fonte']})" for r in resultados[:8]
    )

    sistema = (
        "Você é um assistente de compras especializado em precificação no Brasil. "
        "Responda em pt-BR, de forma objetiva, em até 4 frases. "
        "Dê um conselho prático de compra com base nos preços encontrados."
    )
    prompt = (
        f"Produto pesquisado: {produto}\n"
        f"Menor preço: R$ {base['menor_preco']} | Maior: R$ {base['maior_preco']} "
        f"| Média: R$ {base['preco_medio']} | Total de ofertas: {base['total_ofertas']}\n"
        f"Ofertas encontradas:\n{resumo}\n\n"
        "Resuma: qual é a melhor compra (melhor custo-benefício), a faixa de preço "
        "justa para este produto e uma dica prática (ex.: vale esperar promoção?)."
    )

    texto, modelo = llm_service.chat(sistema, prompt)
    base["analise"] = texto
    base["modelo"] = modelo
    return jsonify(base)
