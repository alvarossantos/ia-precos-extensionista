from app.services.produtos.ranking import ranking_relevancia, relevancia_do_resultado


def test_relevancia_favorece_nome_exato():
    score_exato = relevancia_do_resultado("iPhone 15 128GB", "iphone 15 128gb")
    score_parcial = relevancia_do_resultado("iPhone 15 Pro Max 256GB", "iphone 15 128gb")
    assert score_exato > score_parcial


def test_relevancia_penaliza_usado_e_acessorio():
    base = relevancia_do_resultado("iPhone 15 128GB", "iphone 15")
    usado = relevancia_do_resultado("iPhone 15 128GB usado", "iphone 15")
    capa = relevancia_do_resultado("Capa para iPhone 15", "iphone 15")
    assert usado < base
    assert capa < base


def test_ranking_relevancia_prioriza_correspondencia_sobre_preco():
    resultados = [
        {"nome": "iPhone 15 Pro Max 512GB", "preco": 8000},
        {"nome": "iPhone 15 128GB", "preco": 4500},
    ]
    ranking = ranking_relevancia(resultados, "iphone 15 128gb")
    assert ranking[0]["nome"] == "iPhone 15 128GB"


def test_ranking_relevancia_respeita_limite():
    resultados = [{"nome": f"iPhone 15 variante {i}", "preco": 100 + i} for i in range(5)]
    ranking = ranking_relevancia(resultados, "iphone 15", limite=2)
    assert len(ranking) == 2
