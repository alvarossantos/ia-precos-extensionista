"""Previsão de tendência de preço: cruzamento de médias móveis (SMA)
com refinamento opcional de raciocínio via IA (OpenRouter).

Para produtos comuns (não cripto), o histórico é construído aos poucos
— cada busca salva um snapshot. Com poucos pontos, o SMA não funciona
bem, então a IA compensa analisando a faixa de preços e fontes.
"""

from . import llm_service


def calcular_sma(historico, periodo):
    if len(historico) < periodo:
        return None
    valores = [item["close"] for item in historico[-periodo:]]
    return sum(valores) / len(valores)


def _previsao_ia(produto: str, tipo: str, historico, preco_atual: float,
                  base_sma: dict, resultados: list = None):
    """Refina a previsão SMA com raciocínio de um LLM. Em caso de falha
    ou ausência de chave, retorna a previsão SMA original (fail-open).
    """
    if not llm_service.ia_disponivel() or not historico:
        return base_sma

    # Monta contexto rico para a IA
    ultimos = historico[-15:]
    serie = ", ".join(f"{p['close']:.2f}" for p in ultimos)

    # Informações de preço
    precos = [p["close"] for p in historico]
    menor = min(precos)
    maior = max(precos)
    media = sum(precos) / len(precos)
    variacao = ((preco_atual - precos[0]) / precos[0] * 100) if len(precos) > 1 else 0

    # Informações de fontes (se disponível)
    fontes_info = ""
    if resultados:
        fontes = {}
        for r in resultados:
            f = r.get("fonte", "Outra")
            if f not in fontes:
                fontes[f] = {"menor": r.get("preco", 0), "maior": r.get("preco", 0), "count": 0}
            fontes[f]["count"] += 1
            if r.get("preco", 0) < fontes[f]["menor"]:
                fontes[f]["menor"] = r["preco"]
            if r.get("preco", 0) > fontes[f]["maior"]:
                fontes[f]["maior"] = r["preco"]
        fontes_info = "\nFontes consultadas:\n"
        for f, info in fontes.items():
            fontes_info += f"  - {f}: {info['count']} ofertas (R${info['menor']:.2f} a R${info['maior']:.2f})\n"

    sistema = (
        "Você é um analista de mercado especialista em precificação no Brasil. "
        "Responda em pt-BR, em 2-3 frases curtas e objetivas.\n"
        "IMPORTANTE: Para produtos comuns (não cripto), preços mudam pouco entre buscas. "
        "Analise a faixa de preços entre fontes para dar uma avaliação útil."
    )
    prompt = (
        f"Produto: {produto} (tipo: {tipo})\n"
        f"Preço atual: R$ {preco_atual:.2f}\n"
        f"Histórico: {len(historico)} pontos coletados\n"
        f"Faixa de preços: R$ {menor:.2f} a R$ {maior:.2f} (média R$ {media:.2f})\n"
        f"Variação desde primeira busca: {variacao:+.2f}%\n"
        f"Série de preços: {serie}\n"
        f"{fontes_info}\n"
        f"Tendência técnica (SMA): {base_sma.get('tendencia')} "
        f"(confiança {base_sma.get('confianca')}%)\n\n"
        "Dê uma análise útil: o preço está justo? Vale esperar promoção? "
        "Qual a melhor fonte? Em 2-3 frases."
    )

    raciocinio_ia, modelo_ia = llm_service.chat(sistema, prompt)
    if not raciocinio_ia:
        return base_sma

    base_sma = dict(base_sma)
    base_sma["raciocinio"] = raciocinio_ia
    base_sma["ia_gerado"] = True
    base_sma["modelo"] = modelo_ia
    return base_sma


def gerar_previsao(produto: str, tipo: str, historico, preco_atual: float,
                    resultados: list = None):
    sma20 = calcular_sma(historico, 20)
    sma50 = calcular_sma(historico, 50)

    # Com poucos pontos, usa análise de faixa de preços
    if sma20 is None or sma50 is None:
        precos = [p["close"] for p in historico]
        if len(precos) >= 2:
            menor = min(precos)
            maior = max(precos)
            variacao = ((preco_atual - precos[0]) / precos[0] * 100)
            diff_pct = ((maior - menor) / menor * 100) if menor > 0 else 0

            if diff_pct < 2:
                raciocinio = (
                    f"Preço estável: R$ {menor:.2f} a R$ {maior:.2f} "
                    f"(variação de {diff_pct:.1f}% entre {len(historico)} buscas). "
                    "O histórico ainda é curto — consulte novamente para evoluir a análise."
                )
                confianca = 45 + min(15, len(precos) * 3)
            elif variacao > 2:
                raciocinio = (
                    f"Preço subiu {variacao:+.1f}% desde a primeira busca "
                    f"(R$ {precos[0]:.2f} → R$ {preco_atual:.2f}). "
                    "Possível tendência de alta ou variação entre fontes."
                )
                confianca = 50 + min(20, len(precos) * 3)
            elif variacao < -2:
                raciocinio = (
                    f"Preço caiu {variacao:+.1f}% desde a primeira busca "
                    f"(R$ {precos[0]:.2f} → R$ {preco_atual:.2f}). "
                    "Possível tendência de queda ou promoção ativa."
                )
                confianca = 50 + min(20, len(precos) * 3)
            else:
                raciocinio = (
                    f"Preço relativamente estável: R$ {menor:.2f} a R$ {maior:.2f}. "
                    f"Histórico com {len(historico)} pontos — o valor cresce com cada busca."
                )
                confianca = 45 + min(15, len(precos) * 3)

            base = {
                "tendencia": "stable" if abs(variacao) < 3 else ("up" if variacao > 0 else "down"),
                "confianca": round(max(40, min(75, confianca)), 1),
                "raciocinio": raciocinio,
            }
        else:
            base = {
                "tendencia": "stable",
                "confianca": 35.0,
                "raciocinio": (
                    f"Ainda há apenas {len(historico)} ponto(s) de histórico. "
                    "Cada nova busca adiciona um ponto à série. "
                    "Consulte novamente mais tarde para ver tendências."
                ),
            }
        return _previsao_ia(produto, tipo, historico, preco_atual, base, resultados)

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
    return _previsao_ia(produto, tipo, historico, preco_atual, base, resultados)
