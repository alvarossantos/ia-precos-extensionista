"""Filtros aplicados sobre resultados agregados de produtos:
relevância textual, remoção de usados, remoção de acessórios/jogos,
piso de preço por categoria e filtro final por IA.
"""

import logging
import re

from ...utils.texto import normalizar
from .. import llm_service

logger = logging.getLogger(__name__)

_TERMOS_IGNORADOS = {
    "celular", "smartphone", "produto", "novo", "original",
    "para", "com", "de", "da", "do", "na", "no", "brasil",
}


def filtrar_relevancia(resultados: list, termo: str, min_palavras: int = 1) -> list:
    """Filtra resultados cujo nome não tem relação com o termo buscado.

    Extrai palavras significativas (>=2 chars, não genéricas) do termo
    e mantém apenas itens cujo nome contém TODAS elas.
    """
    palavras = [
        p for p in re.findall(r"[a-z0-9]+", normalizar(termo))
        if len(p) >= 2 and p not in _TERMOS_IGNORADOS
    ]
    if not palavras:
        return resultados

    filtrados = [
        r for r in resultados
        if all(p in normalizar(r.get("nome", "")) for p in palavras)
    ]
    return filtrados if filtrados else resultados


_TERMOS_USADO = (
    "usado", "usada", "seminovo", "recondicionado", "reciclado",
    "aberto", "troca", "open box", "vitrine", "segunda mão", "2ª mão",
)


def filtrar_novos(resultados: list, termo: str) -> list:
    """Remove itens usados/recondicionados (mantém apenas novos).

    Se o próprio termo buscado contém "usado" (ex.: "iphone usado
    barato"), não força a remoção — o usuário quer usados de propósito.
    """
    termo_norm = normalizar(termo)
    if any(t in termo_norm for t in _TERMOS_USADO):
        return resultados

    return [
        r for r in resultados
        if not any(t in normalizar(r.get("nome", "")) for t in _TERMOS_USADO)
    ]


_TERMOS_ACESSORIO = (
    "jogo ", "jogos ", "game ", "games ", "midia ", "mídia ",
    "blu-ray", "bluray", "dvd ",
    "controle ", "controlador ", "controller ", "joystick ", "gamepad ",
    "headset ", "fone ", "capa ", "case ", "skin ", "película ", "protetor ",
    "base de carregamento", "dock ", "carregador ", "charger ",
    "cabo ", "suporte ", "stand ", "portal ",
    "capa ", "película ", "film ", "pouch ", "bumper",
    "powerbank", "power bank", "adaptador ", "hub ",
    "ssd ", "memoria ram", "memória ram", "cooler ", "pasta termica",
    "mouse pad", "mousepad", "teclado ", "mouse ", "webcam",
)

# Produtos onde itens abaixo desse valor quase sempre são jogos/acessórios.
_PRODUTOS_PRECO_MINIMO = {
    "playstation": 500, "ps5": 500, "ps4": 300,
    "xbox": 500, "nintendo switch": 500, "switch": 500,
    "iphone": 1500, "samsung galaxy": 1000, "galaxy s": 1000,
    "macbook": 3000, "mac book": 3000,
}


def preco_minimo_produto(produto: str) -> float:
    """Preço mínimo esperado para o tipo de produto (0 = sem filtro)."""
    p = produto.lower()
    for chave, minimo in _PRODUTOS_PRECO_MINIMO.items():
        if chave in p:
            return minimo
    return 0


def eh_acessorio(nome: str) -> bool:
    """Nome sugere acessório/jogo em vez do produto principal.

    Só marca como acessório se o nome COMEÇA com termo de acessório.
    Ex: 'Capa PS5' → acessório, 'Sony PlayStation 5 Console' → não.
    """
    n = normalizar(nome)
    return any(n.startswith(t) or f" {t}" in n for t in _TERMOS_ACESSORIO)


def filtrar_por_ia(resultados: list, produto: str) -> list:
    """Usa IA para identificar e remover acessórios/itens irrelevantes.

    Fail-open: em caso de indisponibilidade, falha, ou se todos forem
    removidos, retorna a lista original sem alterações.
    """
    if not llm_service.ia_disponivel() or len(resultados) <= 1:
        return resultados

    itens = []
    for i, r in enumerate(resultados):
        preco = r.get("preco")
        nome = r.get("nome", "")[:80]
        fonte = r.get("fonte", "")
        preco_str = f"R${preco:.2f}" if preco else "s/preco"
        itens.append(f"{i}|{nome}|{preco_str}|{fonte}")
    lista_texto = "\n".join(itens)

    sistema = (
        "Você é um filtro de produtos. Analise a lista e identifique APENAS "
        "o PROPRIO produto buscado — não jogos, acessórios, capas, controladores, "
        "headsets, memórias, cabos, cartuchos, mídias, DLCs, ou qualquer item "
        "que seja COMPATÍVEL MAS NÃO SEJA o produto em si.\n"
        "Exemplos:\n"
        "- 'PlayStation 5' = o CONSOLE (R$2.000-5.000), não jogos PS5 (R$20-300)\n"
        "- 'iPhone 16' = o CELULAR (R$2.000+), não capa (R$20-100)\n"
        "- 'ASUS TUF A16' = o NOTEBOOK (R$4.000+), não mouse pad ou SSD\n\n"
        "Se os itens mais baratos parecerem jogos/acessórios e houver itens "
        "mais caros que sejam o produto principal, selecione apenas os caros.\n\n"
        "Responda SOMENTE com os números dos itens válidos, separados por vírgula. "
        "Ex: 0,2,5. Se nenhum for o produto, responda: NENHUM"
    )
    prompt = (
        f"Produto buscado: {produto}\n\n"
        f"Resultados:\n{lista_texto}\n\n"
        "Quais números são o PROPRIO produto (não jogos, acessórios, compatíveis)?"
    )

    texto, _ = llm_service.chat(sistema, prompt, max_tokens=60, timeout=15)
    if not texto:
        return resultados

    texto = texto.strip().upper()
    if "NENHUM" in texto or "NINGU" in texto:
        return resultados

    try:
        indices = {
            int(parte) for parte in texto.replace(" ", "").split(",")
            if parte.strip().isdigit()
        }
    except ValueError:
        return resultados

    if not indices:
        return resultados

    filtrados = [r for i, r in enumerate(resultados) if i in indices]
    return filtrados if filtrados else resultados


# ==================== Validação de URLs ====================

import concurrent.futures
from ... import http_client


def _url_tem_conteudo(url: str) -> bool:
    """Verifica se uma URL retorna conteúdo real (HTTP 200 com tamanho aceitável).

    Faz um HEAD first (rápido); se não suportar, faz GET parcial.
    Retorna False se: timeout, status >= 400, ou página muito pequena (< 5KB)
    o que geralmente indica página de erro ou redirect quebrado.
    """
    if not url or not url.startswith("http"):
        return False
    try:
        resp = http_client.get(url, timeout=8, stream=True, allow_redirects=True)
        if resp.status_code >= 400:
            return False
        # Lê apenas os primeiros 10KB para verificar se tem conteúdo real
        chunk = next(resp.iter_content(chunk_size=10240), b"")
        resp.close()
        # Páginas de erro/blank geralmente têm < 5KB
        return len(chunk) >= 5120
    except Exception:
        return False


def validar_urls(resultados: list, max_workers: int = 5) -> list:
    """Valida URLs dos resultados em paralelo.

    Remove itens cuja URL retorna 502/404/página vazia.
    Mantém itens sem permalink (ex: Google orgânico sem link direto).
    Fail-open: se a validação falhar, mantém o item.
    """
    if not resultados:
        return resultados

    def _check(r):
        permalink = r.get("permalink", "")
        if not permalink:
            return r  # sem link, mantém
        if _url_tem_conteudo(permalink):
            return r
        logger.warning("URL inválida removida: %s (%s)", permalink[:60], r.get("nome", "")[:30])
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        resultados_validados = list(executor.map(_check, resultados))

    filtrados = [r for r in resultados_validados if r is not None]
    return filtrados if filtrados else resultados  # fail-open
