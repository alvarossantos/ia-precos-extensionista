"""Agrega resultados de várias fontes e aplica os pipelines de
filtragem/ranking usados pelas rotas.

Antes, a sequência "buscar → filtrar relevância → (filtrar novos) →
ranking" estava reimplementada quase idênticamente dentro de
/api/buscar, /api/comparar, /api/analise-ia e /api/alertas/verificar
— este último, inclusive, sem NENHUM filtro (usava o primeiro
resultado bruto de `buscar_produtos`, podendo disparar um alerta por
causa de um acessório irrelevante). `buscar_ofertas()` abaixo unifica
esse pipeline em um único lugar testável.
"""

import logging
import threading
from datetime import datetime

from . import fontes
from .filtros import eh_acessorio, eh_titulo_ingles, filtrar_novos, filtrar_por_ia, filtrar_relevancia, preco_minimo_produto, validar_urls
from .ranking import ranking_relevancia

logger = logging.getLogger(__name__)

FONTES_PADRAO = [
    "americanas", "carrefour", "kabum", "samsung", "buscape", "zoom",
    "google_shopping", "google_organico",
]

_BUSCADORES = {
    "americanas": fontes.buscar_americanas,
    "carrefour": fontes.buscar_carrefour,
    "kabum": fontes.buscar_kabum,
    "samsung": fontes.buscar_samsung,
    "buscape": fontes.buscar_buscape,
    "zoom": fontes.buscar_zoom,
    "google_shopping": fontes.buscar_google_shopping,
    "google_organico": fontes.buscar_google_organico,
}


class _CacheEmMemoria:
    """Cache curto (minutos) em memória para `buscar_produtos`,
    evitando golpear todas as fontes de novo em chamadas repetidas no
    mesmo carregamento de página (ex.: /api/historico + /api/previsao
    do mesmo produto, quase simultâneas)."""

    def __init__(self, ttl_segundos: int = 300):
        self._ttl = ttl_segundos
        self._dados = {}
        self._lock = threading.Lock()

    def get(self, chave: str):
        with self._lock:
            item = self._dados.get(chave)
        if not item:
            return None
        ts, valor = item
        if (datetime.now() - ts).total_seconds() > self._ttl:
            return None
        return valor

    def set(self, chave: str, valor):
        with self._lock:
            self._dados[chave] = (datetime.now(), valor)


_cache_memoria = _CacheEmMemoria()


def buscar_produtos(produto: str, limite: int = 5, fontes_selecionadas: list = None) -> list:
    """Busca em múltiplas fontes em paralelo e agrega os resultados.

    Uma fonte que falhar é logada e ignorada — não derruba a busca
    inteira (fail-open por fonte).
    """
    import concurrent.futures

    fontes_selecionadas = fontes_selecionadas or FONTES_PADRAO
    cache_key = f"produtos:{produto}:{','.join(sorted(fontes_selecionadas))}"

    cacheados = _cache_memoria.get(cache_key)
    if cacheados is not None:
        return list(cacheados)

    todos = []

    def _buscar(nome_fonte):
        buscador = _BUSCADORES.get(nome_fonte)
        if buscador is None:
            return []
        try:
            return buscador(produto, limite)
        except Exception as e:
            logger.warning("Fonte '%s' falhou para '%s': %s", nome_fonte, produto, e)
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(fontes_selecionadas)) as executor:
        resultados = list(executor.map(_buscar, fontes_selecionadas))
        for lista in resultados:
            todos.extend(lista)

    todos.sort(key=lambda x: (x.get("preco") is None, x.get("preco") or float("inf")))
    _cache_memoria.set(cache_key, todos)
    return todos


def buscar_ofertas(produto: str, limite: int = 5, fontes_selecionadas: list = None,
                    so_novos: bool = False) -> list:
    """Pipeline padrão: agrega fontes (paralelo) → filtra por relevância →
    remove acessórios/jogos → remove nomes em inglês → aplica piso de preço
    → valida URLs → ordena.
    Busca 15 por fonte para compensar perdas nos filtros.
    """
    resultados = buscar_produtos(produto, limite=15, fontes_selecionadas=fontes_selecionadas)
    resultados = filtrar_relevancia(resultados, produto)
    resultados = [r for r in resultados if not eh_acessorio(r.get("nome", ""))]
    resultados = [r for r in resultados if not eh_titulo_ingles(r.get("nome", ""))]
    minimo = preco_minimo_produto(produto)
    if minimo:
        resultados = [r for r in resultados if r.get("preco") is None or r["preco"] >= minimo]
    if so_novos:
        resultados = filtrar_novos(resultados, produto)
    resultados = validar_urls(resultados)
    return ranking_relevancia(resultados, produto, limite=limite)


def _pipeline_pesado(produto: str, busca_limite: int, ranking_limite: int) -> list:
    """Pipeline "pesado" do dashboard: além da relevância textual,
    remove acessórios/jogos por heurística, aplica piso de preço por
    categoria, valida URLs e faz uma passada final de filtro por IA."""
    resultados = buscar_produtos(produto, limite=busca_limite)
    resultados = filtrar_relevancia(resultados, produto)
    resultados = filtrar_novos(resultados, produto)
    resultados = [r for r in resultados if not eh_acessorio(r.get("nome", ""))]
    # Remove resultados cujo título é exclusivamente em inglês
    # (Google Shopping retorna nomes em inglês para eletrônicos)
    resultados = [r for r in resultados if not eh_titulo_ingles(r.get("nome", ""))]

    minimo = preco_minimo_produto(produto)
    if minimo:
        resultados = [r for r in resultados if r.get("preco") is None or r["preco"] >= minimo]

    # Valida URLs (remove páginas com 502/conteúdo vazio)
    resultados = validar_urls(resultados)

    resultados = filtrar_por_ia(resultados, produto)
    return ranking_relevancia(resultados, produto, limite=ranking_limite)


def obter_dados_produto_comum(produto: str, cache_repo, historico_repo,
                               ttl_horas: int, dias: int = None):
    """Retorna (historico, preco_atual_fresco, resultados_finais) para
    um produto comum, atualizando o histórico local a cada `ttl_horas`.
    """
    if cache_repo.deve_buscar(produto, ttl_horas=ttl_horas):
        try:
            relevantes = _pipeline_pesado(produto, busca_limite=10, ranking_limite=5)
            com_preco = [r for r in relevantes if r.get("preco") is not None]
            if com_preco:
                melhor = min(com_preco, key=lambda x: x["preco"])
                historico_repo.salvar_preco(
                    produto, preco=melhor["preco"], nome_encontrado=melhor["nome"],
                    moeda=melhor["moeda"], fonte=melhor["fonte"],
                )
                cache_repo.registrar_busca(produto, fonte="multi")
        except Exception:
            logger.exception("Falha ao atualizar histórico de '%s'", produto)

    historico = historico_repo.buscar_historico(produto, dias=dias)

    preco_atual_fresco = None
    resultados_finais = []
    try:
        resultados_finais = _pipeline_pesado(produto, busca_limite=20, ranking_limite=50)
        com_preco = sorted(
            (r for r in resultados_finais if r.get("preco") is not None),
            key=lambda x: x["preco"],
        )
        resultados_finais = com_preco
        if com_preco:
            preco_atual_fresco = com_preco[0]["preco"]
    except Exception:
        logger.exception("Falha ao buscar resultados frescos de '%s'", produto)

    return historico, preco_atual_fresco, resultados_finais
