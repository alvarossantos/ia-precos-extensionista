"""Previsão de tendência de preço: cruzamento de médias móveis (SMA)
com refinamento opcional de raciocínio via IA (OpenRouter).
"""

from . import llm_service


def calcular_sma(historico, periodo):
    if len(historico) < periodo:
        return None
    valores = [item["close"] for item in historico[-periodo:]]
    return sum(valores) / len(valores)


def _previsao_ia(produto: str, tipo: str, historico, preco_atual: float, base_sma: dict):
    """Refina a previsão SMA com raciocínio de um LLM. Em caso de falha
    ou ausência de chave, retorna a previsão SMA original (fail-open).
    """
    if not llm_service.ia_disponivel() or not historico:
        return base_sma

    ultimos = historico[-15:]
    serie = ", ".join(f"{p['close']:.2f}" for p in ultimos)

    sistema = (
        "Você é um analista de mercado especialista em precificação e tendências. "
        "Responda em pt-BR, em 2-3 frases curtas e objetivas, com base nos dados fornecidos."
    )
    prompt = (
        f"Produto/ativo: {produto} (tipo: {tipo})\n"
        f"Preço atual: {preco_atual}\n"
        f"Tendência técnica (SMA): {base_sma.get('tendencia')} "
        f"(confiança {base_sma.get('confianca')}%)\n"
        f"Últimos preços da série: {serie}\n\n"
        "Dê uma análise resumida e indique a tendência esperada a curto prazo."
    )

    raciocinio_ia, modelo_ia = llm_service.chat(sistema, prompt)
    if not raciocinio_ia:
        return base_sma

    base_sma = dict(base_sma)
    base_sma["raciocinio"] = raciocinio_ia
    base_sma["ia_gerado"] = True
    base_sma["modelo"] = modelo_ia
    return base_sma


def gerar_previsao(produto: str, tipo: str, historico, preco_atual: float):
    sma20 = calcular_sma(historico, 20)
    sma50 = calcular_sma(historico, 50)

    if sma20 is None or sma50 is None:
        base = {
            "tendencia": "stable",
            "confianca": 50.0,
            "raciocinio": (
                f"Ainda há poucos pontos ({len(historico)}) para análise. "
                "O histórico cresce a cada nova busca."
            ),
        }
        return _previsao_ia(produto, tipo, historico, preco_atual, base)

    diff_pct = ((preco_atual - sma20) / sma20) * 100

    if sma20 > sma50 and preco_atual > sma20:
        tendencia, raciocinio = "up", "Alta: preço acima das médias móveis de curto e longo prazo."
    elif sma20 < sma50 and preco_atual < sma20:
        tendencia, raciocinio = "down", "Queda: preço abaixo das médias móveis, pressão vendedora."
    elif sma20 > sma50 and preco_atual < sma20:
        tendencia, raciocinio = "stable", "Correção de curto prazo dentro de tendência de alta macro."
    else:
        tendencia, raciocinio = "stable", "Mercado lateralizado, sem força direcional clara."

    confianca = 75 + min(20, abs(diff_pct)) if tendencia != "stable" else 55.0
    base = {
        "tendencia": tendencia,
        "confianca": round(max(40, min(99, confianca)), 1),
        "raciocinio": raciocinio,
    }
    return _previsao_ia(produto, tipo, historico, preco_atual, base)
