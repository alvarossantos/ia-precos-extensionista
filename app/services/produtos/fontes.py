"""Busca de produtos em múltiplas fontes externas.

Cada `_buscar_*` retorna uma lista de dicts no formato:
    {"nome", "preco", "preco_original", "moeda", "permalink",
     "thumbnail", "fonte", "frete_gratis", ...}

Todas usam `app.http_client` (timeout + retry/backoff padrão) em vez
de `requests` direto, e propagam exceções para quem chama decidir
como tratar — a função `buscar_produtos` em aggregator.py é quem
decide ignorar falhas de uma fonte individual (com log, não silêncio).
"""

import json
import logging
import re
from urllib.parse import quote

from ... import http_client
from ...config import config
from ...utils.texto import extrair_preco_br

logger = logging.getLogger(__name__)


# ==================== Americanas (VTEX) ====================

def _buscar_vtex(base_url: str, fonte: str, loja: str, produto: str, limite: int = 5):
    """Genérico para lojas VTEX (Americanas, Carrefour, etc)."""
    termo_url = quote(produto, safe="")
    url = f"{base_url}/api/catalog_system/pub/products/search/{termo_url}"
    resp = http_client.get(url, params={"_from": 0, "_to": limite - 1})
    resp.raise_for_status()

    resultados = []
    for item in resp.json():
        items = item.get("items", [])
        if not items:
            continue
        it = items[0]
        sellers = it.get("sellers", [])
        if not sellers:
            continue
        offer = sellers[0].get("commertialOffer", {})
        preco = offer.get("Price", 0)
        preco_lista = offer.get("ListPrice", 0)
        if preco <= 0:
            continue

        imgs = it.get("images", [])
        thumbnail = imgs[0].get("imageUrl", "") if imgs else ""
        link_text = item.get("linkText", "")
        permalink = f"{base_url}/produto/{link_text}" if link_text else ""

        resultados.append({
            "nome": item.get("productName", ""),
            "preco": preco,
            "preco_original": preco_lista if preco_lista and preco_lista != preco else None,
            "moeda": "BRL",
            "permalink": permalink,
            "thumbnail": thumbnail,
            "fonte": fonte,
            "loja": loja,
            "frete_gratis": False,
        })
    return resultados


def buscar_americanas(produto: str, limite: int = 5):
    """Americanas VTEX API — gratuita, sem autenticação."""
    return _buscar_vtex("https://www.americanas.com.br", "Americanas", "Americanas", produto, limite)


def buscar_carrefour(produto: str, limite: int = 5):
    """Carrefour VTEX API — gratuita, sem autenticação."""
    return _buscar_vtex("https://www.carrefour.com.br", "Carrefour", "Carrefour", produto, limite)


# ==================== KaBuM ====================

def buscar_kabum(produto: str, limite: int = 5):
    """KaBuM API — gratuita, sem autenticação."""
    resp = http_client.get(
        "https://servicespub.prod.api.aws.grupokabum.com.br/catalog/v2/products",
        params={"query": produto, "page_number": 1, "page_size": limite},
    )
    resp.raise_for_status()

    resultados = []
    for item in resp.json().get("data", []):
        attrs = item.get("attributes", {})
        preco = attrs.get("price", 0)
        old_price = attrs.get("old_price", 0)
        if preco <= 0:
            continue

        desc_raw = attrs.get("description", "")
        nome = re.sub(r"<[^>]+>", "", desc_raw).strip().split("\n")[0][:120]

        thumb = attrs.get("thumbnail", "") or ""
        if not thumb:
            item_id = item.get("id", "")
            thumb = f"https://images.kabum.com.br/produtos/fotos/{item_id}/image.jpg" if item_id else ""

        permalink = attrs.get("permalink", "")
        if not permalink and item.get("id"):
            slug = nome.lower().replace(" ", "-").replace("/", "-")[:80]
            permalink = f"https://www.kabum.com.br/produto/{item.get('id')}/{slug}"

        resultados.append({
            "nome": nome,
            "preco": preco,
            "preco_original": old_price if old_price and old_price != preco else None,
            "moeda": "BRL",
            "permalink": permalink,
            "thumbnail": thumb,
            "fonte": "KaBuM",
            "loja": "KaBuM",
            "frete_gratis": bool(attrs.get("has_free_shipping", False)),
            "desconto": attrs.get("discount_percentage", 0),
        })
    return resultados


# ==================== Samsung Store ====================

def buscar_samsung(produto: str, limite: int = 5):
    """Samsung Store Intelligent Search — gratuita, sem autenticação."""
    resp = http_client.get(
        "https://shop.samsung.com/br/api/io/_v/api/intelligent-search/product_search/v2",
        params={"query": produto, "page": 1, "count": limite, "locale": "pt-BR"},
    )
    resp.raise_for_status()

    resultados = []
    for item in resp.json().get("products", []):
        price_range = item.get("priceRange", {})
        selling = price_range.get("sellingPrice", {})
        preco = selling.get("lowPrice") or 0
        list_price = (price_range.get("listPrice") or {}).get("lowPrice") or 0
        if preco <= 0:
            continue

        link = item.get("link", "")
        permalink = f"https://shop.samsung.com/br{link}" if link else ""

        items_list = item.get("items", [])
        thumb = ""
        if items_list and items_list[0].get("images"):
            thumb = items_list[0]["images"][0].get("imageUrl", "")

        resultados.append({
            "nome": item.get("productName", ""),
            "preco": preco,
            "preco_original": list_price if list_price and list_price != preco else None,
            "moeda": "BRL",
            "permalink": permalink,
            "thumbnail": thumb,
            "fonte": "Samsung",
            "loja": "Samsung",
            "frete_gratis": False,
        })
    return resultados


# ==================== Buscapé / Zoom (mesma engine Mosaico) ====================

def _extrair_url_loja_direta(item: dict, base_url: str) -> str | None:
    """Tenta extrair URL direta da loja (ex: Amazon) a partir dos dados do hit.

    Buscapé/Zoom não expõem links diretos das lojas, mas o campo
    'externalReviewsUrl' às vezes contém a URL de reviews da Amazon
    com o ASIN, que permite construir o link direto do produto.
    """
    # Tenta extrair ASIN da Amazon do externalReviewsUrl
    ext_url = item.get("externalReviewsUrl", "")
    if "amazon" in ext_url:
        m = re.search(r"/(B[A-Z0-9]{9})", ext_url)
        if m:
            asin = m.group(1)
            return f"https://www.amazon.com.br/dp/{asin}"

    # Tenta extrair de reviews[].externalReviewsUrl (estrutura aninhada)
    reviews = item.get("reviews", [])
    if isinstance(reviews, list):
        for rev in reviews:
            if isinstance(rev, dict):
                ext = rev.get("externalReviewsUrl", "")
                if "amazon" in ext:
                    m = re.search(r"/(B[A-Z0-9]{9})", ext)
                    if m:
                        asin = m.group(1)
                        return f"https://www.amazon.com.br/dp/{asin}"

    return None


def _buscar_url_loja_direta(produto_url: str) -> str | None:
    """Busca a página do produto e extrai URL direta da loja (Amazon).

    Faz uma requisição à página do produto no Buscapé/Zoom e procura
    pelo externalReviewsUrl que contém o ASIN da Amazon.
    Limitado a timeout curto para não lentidão.
    """
    try:
        resp = http_client.get(produto_url, timeout=8)
        resp.raise_for_status()
        html = resp.text

        # Procura por externalReviewsUrl com Amazon
        m = re.search(r'"externalReviewsUrl"\s*:\s*"(https?://[^"]*amazon[^"]*)"', html)
        if m:
            ext_url = m.group(1)
            asin_match = re.search(r"/(B[A-Z0-9]{9})", ext_url)
            if asin_match:
                return f"https://www.amazon.com.br/dp/{asin_match.group(1)}"
    except Exception:
        pass
    return None


def _parse_mosaico_hits(html: str, base_url: str, limite: int, fonte: str):
    """Parser genérico para Buscapé/Zoom.

    Os dados ficam no JSON __NEXT_DATA__ → props → initialReduxState →
    hits → hits. Isso é uma estrutura interna não documentada dessas
    plataformas: pode mudar sem aviso. Se o parsing falhar, retorna
    lista vazia (fail-open) em vez de propagar exceção — é a fonte
    mais frágil do pipeline.
    """
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html, re.S,
    )
    if not m:
        logger.warning("[%s] __NEXT_DATA__ não encontrado — layout pode ter mudado", fonte)
        return []

    try:
        data = json.loads(m.group(1))
        hits = data["props"]["initialReduxState"]["hits"]["hits"]
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        logger.warning("[%s] falha ao parsear __NEXT_DATA__: %s", fonte, e)
        return []

    resultados = []
    for item in hits[:limite]:
        preco = item.get("price", 0)
        if not preco or preco <= 0:
            continue

        url = item.get("url", "")

        # Pula anúncios promovidos — Buscapé/Zoom usam /lead?oid= para ads
        if not url or url.startswith("/lead"):
            continue

        permalink = url if url.startswith("http") else f"{base_url}{url}"
        permalink = permalink.split("?")[0]

        # Tenta extrair URL direta da loja (Amazon)
        url_loja = _extrair_url_loja_direta(item, base_url)

        # Nome da loja (melhor oferta)
        best_offer = item.get("bestOffer", {})
        loja = best_offer.get("merchantName", "") if isinstance(best_offer, dict) else ""

        resultados.append({
            "nome": item.get("name", ""),
            "preco": preco,
            "preco_original": None,
            "moeda": "BRL",
            "permalink": url_loja or permalink,
            "permalink_detalhe": permalink if url_loja else None,
            "thumbnail": item.get("image", ""),
            "fonte": fonte,
            "loja": loja,
            "frete_gratis": False,
            "_buscape_url": permalink if not url_loja else None,
        })

    # Para os top 3 sem link direto, tenta buscar na página do produto
    import concurrent.futures
    com_detalhe = [r for r in resultados if r.get("_buscape_url")]
    if com_detalhe:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futuros = {
                executor.submit(_buscar_url_loja_direta, r["_buscape_url"]): r
                for r in com_detalhe[:3]
            }
            for futuro in concurrent.futures.as_completed(futuros):
                r = futuros[futuro]
                url_direta = futuro.result()
                if url_direta:
                    r["permalink_detalhe"] = r["permalink"]
                    r["permalink"] = url_direta
                r.pop("_buscape_url", None)
    # Limpa campo interno dos que não foram processados
    for r in resultados:
        r.pop("_buscape_url", None)

    return resultados


def buscar_buscape(produto: str, limite: int = 5):
    termo_url = quote(produto, safe="")
    resp = http_client.get(f"https://www.buscape.com.br/busca/{termo_url}")
    resp.raise_for_status()
    return _parse_mosaico_hits(resp.text, "https://www.buscape.com.br", limite, "Buscapé")


def buscar_zoom(produto: str, limite: int = 5):
    termo_url = quote(produto, safe="")
    resp = http_client.get(f"https://www.zoom.com.br/search?q={termo_url}")
    resp.raise_for_status()
    return _parse_mosaico_hits(resp.text, "https://www.zoom.com.br", limite, "Zoom")


# ==================== SerpAPI (Google Shopping / Google orgânico) ====================

def _serpapi_get(params: dict, timeout: int = 30):
    """Chamada genérica à SerpAPI. Retorna JSON ou None (sem chave ou erro)."""
    if not config.SERPAPI_API_KEY:
        return None
    try:
        resp = http_client.get(
            "https://serpapi.com/search.json",
            params={**params, "api_key": config.SERPAPI_API_KEY},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:  # SerpAPI é opcional (fail-open) — sem chave, tudo bem
        logger.warning("SerpAPI indisponível: %s", e)
        return None


# Lojas nacionais conhecidas (para priorização no Google Shopping)
_LOJAS_NACIONAIS = {
    "kabum", "magazine luiza", "magalu", "americanas", "casas bahia",
    "havan", "pontofrio", "submarino", "renner", "riachuelo",
    "saraiva", "fast shop", "small", "extraport", "amazon.com.br",
    "playstation store", "buscape", "zoom",
}


def _is_loja_nacional(source: str) -> bool:
    """Verifica se a loja é brasileira conhecida."""
    s = (source or "").lower()
    return any(loja in s for loja in _LOJAS_NACIONAIS)


def buscar_google_shopping(produto: str, limite: int = 5):
    """Google Shopping via SerpAPI. Prioriza lojas nacionais."""
    # Pede mais resultados para poder filtrar/priorizar
    dados = _serpapi_get({
        "engine": "google_shopping", "q": produto, "hl": "pt-br", "gl": "br",
        "num": max(limite * 4, 20),
    })
    if not dados:
        return []

    resultados = []
    for item in dados.get("shopping_results", []):
        preco_raw = item.get("price", "")
        preco = None
        if preco_raw:
            try:
                preco = float(preco_raw.replace("R$", "").replace(".", "").replace(",", ".").strip())
            except ValueError:
                preco = None
        if not preco or preco <= 0:
            continue

        source = item.get("source", "")
        resultados.append({
            "nome": item.get("title", ""),
            "preco": preco,
            "preco_original": None,
            "moeda": "BRL",
            "permalink": item.get("product_link", "") or item.get("link", ""),
            "thumbnail": item.get("thumbnail", ""),
            "fonte": "Google Shopping",
            "loja": source,
            "frete_gratis": False,
            "_nacional": _is_loja_nacional(source),
        })

    # Prioriza lojas nacionais, depois por preço
    resultados.sort(key=lambda x: (not x.get("_nacional", False), x["preco"]))

    # Remove flag interna
    for r in resultados:
        r.pop("_nacional", None)

    return resultados[:limite]


def buscar_google_organico(produto: str, limite: int = 5):
    """Busca orgânica no Google via SerpAPI. Preço só quando aparece no snippet."""
    dados = _serpapi_get({
        "engine": "google", "q": produto, "hl": "pt-br", "gl": "br", "num": limite,
    })
    if not dados:
        return []

    resultados = []
    for item in dados.get("organic_results", []):
        if not item.get("link"):
            continue
        resultados.append({
            "nome": item.get("title", "") or "",
            "preco": extrair_preco_br(item.get("snippet", "") or ""),
            "preco_original": None,
            "moeda": "BRL",
            "permalink": item.get("link", ""),
            "thumbnail": item.get("favicon", ""),
            "fonte": "Google",
            "loja": "",
            "frete_gratis": False,
        })
    return resultados[:limite]


# ==================== Mercado Livre ====================

def buscar_mercadolivre(produto: str, limite: int = 5, access_token: str = None):
    """Busca no Mercado Livre — DESABILITADO.

    A API pública retorna 403 desde ~2025 (bloqueada sem OAuth).
    A página de busca é SPA 100% JavaScript, impossível scrapar.
    O Google Shopping não indexa produtos do ML.

    Retorna [] sempre. Mantido para compatibilidade com FONTES_PADRAO.
    Para reativar, é necessário um access_token OAuth válido.
    """
    if not access_token:
        return []

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = http_client.get(
            f"{config.ML_BASE}/sites/{config.ML_SITE_ID}/search",
            params={"q": produto, "limit": limite},
            headers=headers,
        )
        resp.raise_for_status()
        resultados = []
        for item in resp.json().get("results", []):
            preco = item.get("price", 0)
            if preco <= 0:
                continue
            resultados.append({
                "nome": item.get("title", ""),
                "preco": preco,
                "preco_original": item.get("original_price"),
                "moeda": "BRL",
                "permalink": item.get("permalink", ""),
                "thumbnail": item.get("thumbnail", "").replace("http://", "https://"),
                "fonte": "Mercado Livre",
                "loja": "Mercado Livre",
                "frete_gratis": item.get("shipping", {}).get("free_shipping", False),
            })
        return resultados
    except Exception:
        return []
