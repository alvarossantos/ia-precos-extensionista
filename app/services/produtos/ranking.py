"""Pontuação e ordenação de resultados por relevância ao termo buscado."""

from difflib import SequenceMatcher

_TERMOS_USADO_PENALIZA = (
    "usado", "usada", "recondicionado", "reciclado",
    "aberto", "troca", "open box", "display", "vitrine",
)

_TERMOS_ACESSORIO_PENALIZA = (
    "acessório", "acessorio", "capa", "tampa", "case",
    "película", "pelicula", "carregador", "cabo", "fone",
    "sim card", "chip", "kit de reparo", "reparo", "tela",
    "bateria", "suporte", "adesivo", "proteção", "protecao",
)


def relevancia_do_resultado(nome: str, termo: str) -> float:
    """Pontua o quanto um nome de produto corresponde ao termo buscado.

    Retorna um float [0, 1]: quanto maior, mais o nome "é" o produto
    buscado. Combina similaridade textual (difflib) com um bônus
    quando o termo completo aparece no nome, e penaliza usados/acessórios.
    """
    nome = (nome or "").lower()
    termo = (termo or "").lower()

    if not nome:
        return 0.0

    ratio = SequenceMatcher(None, termo, nome).ratio()
    cover = (
        SequenceMatcher(None, termo, nome).find_longest_match(0, len(termo), 0, len(nome)).size
        / max(1, len(termo))
    )
    score = max(ratio, cover)

    if termo and termo in nome:
        score = max(score, 0.92)

    if any(p in nome for p in _TERMOS_USADO_PENALIZA):
        score *= 0.5

    if any(p in nome for p in _TERMOS_ACESSORIO_PENALIZA):
        score *= 0.3

    return score


def ranking_relevancia(resultados: list, termo: str, limite: int = None) -> list:
    """Ordena resultados por relevância ao termo (e depois por preço).

    Prioriza o produto mais próximo do que foi digitado, não apenas o
    mais barato. Ex.: buscar 'iphone 16 128gb' favorece o 'iPhone 16
    128GB' sobre um 'iPhone 16 Pro Max 256GB' mais barato.
    """
    for r in resultados:
        r["_score"] = relevancia_do_resultado(r.get("nome", ""), termo)

    resultados.sort(
        key=lambda x: (x.get("preco") is None, -x.get("_score", 0), x.get("preco") or float("inf"))
    )

    if limite:
        resultados = resultados[:limite]

    for r in resultados:
        r.pop("_score", None)
    return resultados
