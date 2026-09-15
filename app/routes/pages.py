from flask import Blueprint, current_app, redirect, send_from_directory

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return send_from_directory(current_app.static_folder, "index.html")


@pages_bp.route("/health")
def health():
    return {"status": "ok"}


@pages_bp.route("/favicon.ico")
def favicon_ico():
    """Redireciona favicon.ico para favicon.svg."""
    return redirect("/favicon.svg")
