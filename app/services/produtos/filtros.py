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

# Palavras comuns em nomes de produtos em português (indica listing BR)
_PALAVRAS_PT = {
    "notebook", "computador", "placa", "processador", "memória", "memoria",
    "armazenamento", "tela", "teclado", "mouse", "impressora", "monitor",
    "fone", "caixa de som", "speaker", "headphone", "headset",
    "smart tv", "televisão", "geladeira", "ar condicionado",
    "aspirador", "liquidificador", "batedeira", "forno", "microondas",
    "micro-ondas", "air fryer", "fritadeira", "cafeteira", "chaleira",
    "torradeira", "sanduicheira", "waffleira", "grill", "panela",
    "máquina de lavar", "maquina de lavar", "secador", "chapinha",
    "ventoinha", "cooler", "gabinete",
    "fonte", "placa-mãe", "placa mae", "mousepad", "webcam",
    "fone de ouvido", "capa", "película", "pelicula",
    "carregador", "cabo", "suporte", "braço", "mesa", "cadeira",
    "console", "controle", "joystick", "volante",
    "robô", "robo",
}


# Sufixos de marketing que o Google Shopping appenda em listings BR
# Ex: "Asus TUF ... online ao melhor preço no Mercado Livre"
# O regex remove a partir de "online", "melhor preço", "comprar", etc.
_SUFIXOS_MARKETING = re.compile(
    r"\s+(?:online|ao\s+melhor\s+preço|com\s+preço|comprar|confira|aproveite|encontre|veja\s+mais).*$",
    re.IGNORECASE,
)


def eh_titulo_ingles(nome: str) -> bool:
    """Heurística: retorna True se o título parece ser exclusivamente em inglês.

    Remove sufixos de marketing brasileiro (ex: "online ao melhor preço")
    antes de analisar. Verifica caracteres acentuados e palavras-chave de
    produto BR.
    """
    if not nome:
        return False

    # Remove sufixos de marketing brasileiro que mascaram o título real
    nome_limpo = _SUFIXOS_MARKETING.sub("", nome).strip()
    nome_norm = normalizar(nome_limpo)

    # Caracteres acentuados indicam português (no título limpo)
    if re.search(r"[ãçêíóúâôûáé]", nome_limpo.lower()):
        return False

    # Palavras-chave de produto BR
    for palavra in _PALAVRAS_PT:
        if palavra in nome_norm:
            return False

    return True

# Sinônimos/abreviações: se o usuário busca "ps5", aceitar "playstation 5" etc.
_SINONIMOS = {
    "ps5": ["playstation 5", "play station 5", "ps 5"],
    "ps4": ["playstation 4", "play station 4", "ps 4"],
    "xbox": ["xbox series", "xbox one"],
    "iphone": ["iphone"],
    "galaxy": ["galaxy"],
    "macbook": ["macbook", "mac book"],
    "rtx": ["rtx"],
    "ssd": ["ssd"],
}


def _expandir_termos(termo: str) -> list[str]:
    """Expande o termo de busca com sinônimos para melhor matching."""
    termo_norm = normalizar(termo)
    extras = []
    for chave, sinos in _SINONIMOS.items():
        if chave in termo_norm or termo_norm in chave:
            extras.extend(sinos)
    return extras


def filtrar_relevancia(resultados: list, termo: str, min_palavras: int = 1) -> list:
    """Filtra resultados cujo nome não tem relação com o termo buscado.

    Verifica se o nome contém as palavras do termo OU qualquer sinônimo.
    Fail-open: se nada passar, retorna a lista original.
    """
    palavras = [
        p for p in re.findall(r"[a-z0-9]+", normalizar(termo))
        if len(p) >= 2 and p not in _TERMOS_IGNORADOS
    ]
    sinos = _expandir_termos(termo)
    if not palavras and not sinos:
        return resultados

    def _matches(r):
        nome = normalizar(r.get("nome", ""))
        # Match por palavras individuais (AND)
        if palavras and all(p in nome for p in palavras):
            return True
        # Match por sinônimo (OR — qualquer sinônimo basta)
        if sinos and any(s in nome for s in sinos):
            return True
        return False

    filtrados = [r for r in resultados if _matches(r)]
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

# Sufixos que indicam jogo/acessório para o produto (não é o console)
_SUFIXOS_ACESSORIO = (
    "para ps5", "para ps4", "for ps5", "for ps4",
    "para xbox", "for xbox", "para switch", "for switch",
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

    Marca como acessório se:
    - Nome começa com termo de acessório (ex: 'Capa PS5')
    - Nome contém sufixo 'para PS5'/'for PS5' (ex: 'GRID Legends para PS5')
    """
    n = normalizar(nome)
    if any(n.startswith(t) or f" {t}" in n for t in _TERMOS_ACESSORIO):
        return True
    if any(s in n for s in _SUFIXOS_ACESSORIO):
        return True
    return False


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
    """Verifica se uma URL não é claramente quebrada.

    404/410 com conteúdo pequeno (<5KB) → removida.
    404/410 com conteúdo grande (>=5KB) → mantém (SPA como Americanas retorna 404 mas funciona no browser).
    Timeout/connection error → mantém (fail-open).
    """
    if not url or not url.startswith("http"):
        return False
    try:
        resp = http_client.get(url, timeout=12, allow_redirects=True)
        # 404/410 com pouco conteúdo = página realmente não existe
        if resp.status_code in (404, 410) and len(resp.text) < 5000:
            return False
        return True
    except Exception:
        return True
    except Exception:
        # Qualquer erro (timeout, connection, etc) → mantém (fail-open)
        return True


def validar_urls(resultados: list, max_workers: int = 5, max_validar: int = 10) -> list:
    """Valida URLs dos resultados em paralelo (no máximo max_validar).

    Remove itens cuja URL retorna 404/410.
    Mantém itens sem permalink, ou se a validação falhar (fail-open).
    """
    if not resultados:
        return resultados

    # Só valida os top N (por preço) — não valida todos para não lentidão
    com_preco = [r for r in resultados if r.get("preco") is not None]
    sem_preco = [r for r in resultados if r.get("preco") is None]
    com_preco.sort(key=lambda x: x["preco"])
    para_validar = com_preco[:max_validar]
    nao_validar = com_preco[max_validar:]

    def _check(r):
        permalink = r.get("permalink", "")
        if not permalink:
            return r  # sem link, mantém
        if _url_tem_conteudo(permalink):
            return r
        logger.warning("URL inválida removida: %s (%s)", permalink[:60], r.get("nome", "")[:30])
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        resultados_validados = list(executor.map(_check, para_validar))

    filtrados = [r for r in resultados_validados if r is not None]
    # Retorna: validados + não validados (por preço alto) + sem preço
    return filtrados + nao_validar + sem_preco if (filtrados + nao_validar + sem_preco) else resultados
