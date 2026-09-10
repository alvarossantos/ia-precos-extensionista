from .alertas_routes import alertas_bp
from .analise_ia_routes import analise_ia_bp
from .buscar_routes import buscar_bp
from .comparar_routes import comparar_bp
from .fontes_routes import fontes_bp
from .historico_buscas_routes import historico_buscas_bp
from .historico_routes import historico_bp
from .mercadolivre_routes import mercadolivre_bp
from .pages import pages_bp
from .previsao_routes import previsao_bp


def registrar_rotas(app):
    app.register_blueprint(pages_bp)

    api_blueprints = (
        historico_bp, previsao_bp, buscar_bp, comparar_bp,
        analise_ia_bp, fontes_bp, alertas_bp, historico_buscas_bp,
        mercadolivre_bp,
    )
    for bp in api_blueprints:
        app.register_blueprint(bp, url_prefix="/api")
