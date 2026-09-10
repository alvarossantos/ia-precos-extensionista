"""Testes do serviço de previsão. Sem OPENROUTER_API_KEY configurada,
`gerar_previsao` roda só a parte determinística (SMA) — o que dá pra
testar sem mockar chamadas de rede.
"""

from app.services.previsao_service import calcular_sma, gerar_previsao


def _serie(valores):
    return [{"time": f"{i:02d}/01", "close": v} for i, v in enumerate(valores, start=1)]


def test_calcular_sma_poucos_pontos_retorna_none():
    assert calcular_sma(_serie([1, 2, 3]), periodo=20) is None


def test_calcular_sma_media_simples():
    historico = _serie([10, 20, 30])
    assert calcular_sma(historico, periodo=3) == 20


def test_gerar_previsao_sem_historico_suficiente():
    historico = _serie([100, 105, 103])
    previsao = gerar_previsao("produto teste", "comum", historico, preco_atual=103)
    # Com 3 pontos e variação de +3%, tendencia pode ser "up" ou "stable"
    assert previsao["tendencia"] in ("up", "stable")
    assert 0 <= previsao["confianca"] <= 100
    assert previsao["raciocinio"]  # tem raciocínio


def test_gerar_previsao_tendencia_de_alta():
    # 60 pontos crescentes: SMA20 > SMA50 e preço atual acima da SMA20
    historico = _serie([100 + i for i in range(60)])
    preco_atual = historico[-1]["close"] + 5
    previsao = gerar_previsao("produto teste", "comum", historico, preco_atual)
    assert previsao["tendencia"] == "up"
    assert previsao["confianca"] > 55


def test_gerar_previsao_tendencia_de_queda():
    historico = _serie([200 - i for i in range(60)])
    preco_atual = historico[-1]["close"] - 5
    previsao = gerar_previsao("produto teste", "comum", historico, preco_atual)
    assert previsao["tendencia"] == "down"
