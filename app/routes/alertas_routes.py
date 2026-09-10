import logging

from flask import Blueprint, jsonify, request

from ..repos import alertas_repo
from ..services.produtos.aggregator import buscar_ofertas

logger = logging.getLogger(__name__)
alertas_bp = Blueprint("alertas", __name__)


@alertas_bp.route("/alertas", methods=["GET"])
def listar_alertas():
    return jsonify({"alertas": alertas_repo.listar()})


@alertas_bp.route("/alertas", methods=["POST"])
def criar_alerta():
    dados = request.get_json(silent=True) or {}
    produto = (dados.get("produto") or "").strip()
    preco_alvo = dados.get("preco_alvo")
    condicao = dados.get("condicao", "menor")

    if not produto or preco_alvo is None:
        return jsonify({"erro": "produto e preco_alvo são obrigatórios"}), 400

    try:
        preco_alvo = float(preco_alvo)
    except (TypeError, ValueError):
        return jsonify({"erro": "preco_alvo deve ser numérico"}), 400

    if preco_alvo <= 0:
        return jsonify({"erro": "preco_alvo deve ser maior que zero"}), 400

    alerta_id = alertas_repo.criar(produto, preco_alvo, condicao)
    return jsonify({"id": alerta_id, "mensagem": "Alerta criado"}), 201


@alertas_bp.route("/alertas/<int:alerta_id>", methods=["DELETE"])
def deletar_alerta(alerta_id: int):
    alertas_repo.remover(alerta_id)
    return jsonify({"mensagem": "Alerta removido"})


@alertas_bp.route("/alertas/verificar")
def verificar_alertas():
    """Verifica se algum alerta ativo foi atingido pelo preço atual.

    Antes, essa checagem usava o primeiro resultado BRUTO de
    `buscar_produtos` (sem nenhum filtro de relevância) — um acessório
    irrelevante e barato poderia disparar um alerta por engano. Agora
    reusa o mesmo pipeline filtrado de `/api/buscar`.
    """
    ativos = alertas_repo.listar_ativos()
    atingidos = []

    for alerta in ativos:
        try:
            resultados = buscar_ofertas(alerta["produto"], limite=1)
        except Exception as e:
            logger.warning("Falha ao verificar alerta de '%s': %s", alerta["produto"], e)
            continue

        if not resultados or resultados[0].get("preco") is None:
            continue

        preco_atual = resultados[0]["preco"]
        condicao = alerta["condicao"]
        disparou = (
            (condicao == "menor" and preco_atual <= alerta["preco_alvo"])
            or (condicao == "maior" and preco_atual >= alerta["preco_alvo"])
        )
        if disparou:
            atingidos.append({
                "id": alerta["id"], "produto": alerta["produto"],
                "preco_alvo": alerta["preco_alvo"], "preco_atual": preco_atual,
                "condicao": condicao, "fonte": resultados[0].get("fonte", ""),
            })

    return jsonify({"atingidos": atingidos, "total_alertas": len(ativos)})
