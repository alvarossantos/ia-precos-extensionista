from flask import Blueprint, jsonify, request

from ..repos import cache_repo
from ..utils.params import int_param

historico_buscas_bp = Blueprint("historico_buscas", __name__)


@historico_buscas_bp.route("/historico-buscas")
def historico_buscas():
    limite = int_param(request, "limite", 20)
    buscas = cache_repo.listar_recentes(limite)
    return jsonify({"buscas": buscas, "total": len(buscas)})
