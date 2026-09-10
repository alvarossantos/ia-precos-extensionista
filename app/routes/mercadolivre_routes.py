import logging

from flask import Blueprint, jsonify, request

from ..services import mercadolivre_oauth as ml

logger = logging.getLogger(__name__)
mercadolivre_bp = Blueprint("mercadolivre", __name__)


@mercadolivre_bp.route("/ml/status")
def ml_status():
    return jsonify(ml.status())


@mercadolivre_bp.route("/ml/auth-url")
def ml_auth_url():
    url = ml.gerar_auth_url()
    if not url:
        return jsonify({"erro": "ML_CLIENT_ID não configurado no .env"}), 400
    return jsonify({"url": url})


@mercadolivre_bp.route("/ml/callback")
def ml_callback():
    """Callback OAuth — troca authorization code por access_token."""
    code = request.args.get("code")
    if not code:
        return jsonify({"erro": "Código de autorização não recebido"}), 400

    try:
        ml.trocar_code_por_token(code)
    except RuntimeError as e:
        return jsonify({"erro": str(e)}), 400

    return """
    <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#1a1a2e;color:#fff;">
    <h1>✅ Mercado Livre conectado!</h1>
    <p>Token salvo com sucesso. Pode fechar esta janela.</p>
    <script>setTimeout(()=>window.close(), 2000);</script>
    </body></html>
    """
