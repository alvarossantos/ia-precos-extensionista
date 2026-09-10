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

def buscar_americanas(produto: str, limite: int = 5):
    """Americanas VTEX API — gratuita, sem autenticação."""
    termo_url = quote(produto, safe="")
    url = f"https://www.americanas.com.br/api/catalog_system/pub/products/search/{termo_url}"
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
        permalink = f"https://www.americanas.com.br/produto/{link_text}" if link_text else ""

        resultados.append({
            "nome": item.get("productName", ""),
            "preco": preco,
            "preco_original": preco_lista if preco_lista and preco_lista != preco else None,
            "moeda": "BRL",
            "permalink": permalink,
            "thumbnail": thumbnail,
            "fonte": "Americanas",
            "frete_gratis": False,
        })
    return resultados


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
            "frete_gratis": False,
        })
    return resultados


# ==================== Buscapé / Zoom (mesma engine Mosaico) ====================

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

        resultados.append({
            "nome": item.get("name", ""),
            "preco": preco,
            "preco_original": None,
            "moeda": "BRL",
            "permalink": permalink,
            "thumbnail": item.get("image", ""),
            "fonte": fonte,
            "frete_gratis": False,
        })
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

def _serpapi_get(params: dict, timeout: int = 20):
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


def buscar_google_shopping(produto: str, limite: int = 5):
    """Google Shopping via SerpAPI. Requer SERPAPI_API_KEY; sem chave, [].""" 
    dados = _serpapi_get({
        "engine": "google_shopping", "q": produto, "hl": "pt-br", "gl": "br", "num": limite,
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

        resultados.append({
            "nome": item.get("title", ""),
            "preco": preco,
            "preco_original": None,
            "moeda": "BRL",
            "permalink": item.get("product_link", "") or item.get("link", ""),
            "thumbnail": item.get("thumbnail", ""),
            "fonte": "Google Shopping",
            "frete_gratis": False,
        })
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
            "frete_gratis": False,
        })
    return resultados[:limite]


# ==================== Mercado Livre ====================

def buscar_mercadolivre(produto: str, limite: int = 5, access_token: str = None):
    """Busca no Mercado Livre via API pública de sites/{site}/search.

    Esse endpoint funciona SEM autenticação (é o que o projeto usa
    para o histórico local — ver memória do projeto). Se um
    `access_token` de OAuth estiver disponível (fluxo /api/ml/*), ele
    é enviado para obter limites de uso mais altos, mas não é
    obrigatório — o backend original exigia o token e falhava sem ele,
    o que não reflete a documentação pública da API.
    """
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
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
            "frete_gratis": item.get("shipping", {}).get("free_shipping", False),
        })
    return resultados
