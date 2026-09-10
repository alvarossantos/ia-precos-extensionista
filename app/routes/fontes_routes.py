from flask import Blueprint, jsonify

fontes_bp = Blueprint("fontes", __name__)


@fontes_bp.route("/fontes")
def fontes():
    """Lista fontes de dados disponíveis (para exibir no frontend)."""
    return jsonify({
        "fontes": [
            {"id": "americanas", "nome": "Americanas", "tipo": "VTEX API", "gratuita": True},
            {"id": "kabum", "nome": "KaBuM!", "tipo": "API interna", "gratuita": True},
            {"id": "samsung", "nome": "Samsung Store", "tipo": "Intelligent Search API", "gratuita": True},
            {"id": "buscape", "nome": "Buscapé", "tipo": "Agregador (scraping)", "gratuita": True},
            {"id": "zoom", "nome": "Zoom", "tipo": "Agregador (scraping)", "gratuita": True},
            {"id": "google_shopping", "nome": "Google Shopping", "tipo": "SerpAPI", "gratuita": False},
            {"id": "google_organico", "nome": "Google (busca orgânica)", "tipo": "SerpAPI", "gratuita": False},
            {"id": "mercadolivre", "nome": "Mercado Livre", "tipo": "API pública", "gratuita": True},
            {"id": "binance", "nome": "Binance", "tipo": "API pública", "gratuita": True, "categorias": ["cripto"]},
        ]
    })
