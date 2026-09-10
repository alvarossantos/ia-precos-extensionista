from app.services.produtos.filtros import (
    eh_acessorio,
    filtrar_novos,
    filtrar_relevancia,
    preco_minimo_produto,
)


def test_filtrar_relevancia_remove_itens_sem_relacao():
    resultados = [
        {"nome": "iPhone 15 128GB Preto"},
        {"nome": "Capinha de silicone qualquer"},
    ]
    filtrados = filtrar_relevancia(resultados, "iphone 15")
    assert len(filtrados) == 1
    assert filtrados[0]["nome"] == "iPhone 15 128GB Preto"


def test_filtrar_relevancia_fail_open_quando_nada_bate():
    resultados = [{"nome": "Produto qualquer"}]
    # termo sem nenhuma palavra em comum -> mantém tudo (fail-open)
    filtrados = filtrar_relevancia(resultados, "xyzabc123")
    assert filtrados == resultados


def test_filtrar_novos_remove_usados():
    resultados = [
        {"nome": "PS5 novo lacrado"},
        {"nome": "PS5 usado seminovo"},
    ]
    filtrados = filtrar_novos(resultados, "ps5")
    assert len(filtrados) == 1
    assert "usado" not in filtrados[0]["nome"].lower()


def test_filtrar_novos_nao_remove_quando_usuario_pede_usado():
    resultados = [{"nome": "PS5 usado seminovo"}]
    filtrados = filtrar_novos(resultados, "ps5 usado")
    assert filtrados == resultados


def test_eh_acessorio_identifica_capa_mas_nao_console():
    assert eh_acessorio("Capa protetora PS5") is True
    assert eh_acessorio("Sony PlayStation 5 Console") is False


def test_preco_minimo_produto_conhece_categoria():
    assert preco_minimo_produto("iPhone 15 Pro") == 1500
    assert preco_minimo_produto("Caneca de café") == 0
