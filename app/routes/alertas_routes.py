"""Rotas de alertas de preço.

CRUD completo + verificação periódica de preços.
Alertas ficam no banco de dados (não em localStorage).
"""

import logging

import requests
from flask import Blueprint, jsonify, request

from ..config import config
from ..extensions import limiter
from ..repos import alertas_repo
from ..services.produtos.aggregator import buscar_ofertas

logger = logging.getLogger(__name__)
alertas_bp = Blueprint("alertas", __name__)


@alertas_bp.route("/alertas", methods=["GET"])
def listar():
    """Lista todos os alertas do usuário."""
    alertas = alertas_repo.listar()
    return jsonify({"alertas": alertas, "total": len(alertas)})


@alertas_bp.route("/alertas", methods=["POST"])
def criar():
    """Cria um novo alerta de preço.

    Body JSON: { "produto": str, "preco_alvo": float, "condicao": "menor"|"maior" }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "JSON obrigatório"}), 400

    produto = (dados.get("produto") or "").strip()
    preco_alvo = dados.get("preco_alvo")
    condicao = dados.get("condicao", "menor")

    if not produto:
        return jsonify({"erro": "Campo 'produto' obrigatório"}), 400
    if not isinstance(preco_alvo, (int, float)) or preco_alvo <= 0:
        return jsonify({"erro": "Campo 'preco_alvo' deve ser um número positivo"}), 400

    alerta_id = alertas_repo.criar(produto, float(preco_alvo), condicao)
    alerta = alertas_repo.obter(alerta_id)
    return jsonify({"ok": True, "alerta": alerta}), 201


@alertas_bp.route("/alertas/<int:alerta_id>", methods=["DELETE"])
def remover(alerta_id: int):
    """Remove um alerta."""
    alerta = alertas_repo.obter(alerta_id)
    if not alerta:
        return jsonify({"erro": "Alerta não encontrado"}), 404
    alertas_repo.remover(alerta_id)
    return jsonify({"ok": True})


@alertas_bp.route("/alertas/<int:alerta_id>/toggle", methods=["POST"])
def toggle(alerta_id: int):
    """Ativa/desativa um alerta."""
    alerta = alertas_repo.obter(alerta_id)
    if not alerta:
        return jsonify({"erro": "Alerta não encontrado"}), 404
    alertas_repo.toggle(alerta_id, not alerta["ativo"])
    return jsonify({"ok": True, "ativo": not alerta["ativo"]})


@alertas_bp.route("/alertas/verificar", methods=["GET"])
def verificar():
    """Verifica todos os alertas ativos contra preços atuais.

    Retorna lista de alertas que dispararam (preço atingiu o alvo).
    """
    ativos = alertas_repo.listar_ativos()
    if not ativos:
        return jsonify({"disparados": [], "verificados": 0})

    disparados = []
    for alerta in ativos:
        try:
            resultados = buscar_ofertas(alerta["produto"], limite=1)
            if not resultados:
                continue

            melhor = resultados[0]
            preco_atual = melhor.get("preco")
            if preco_atual is None:
                continue

            condicao = alerta["condicao"]
            preco_alvo = alerta["preco_alvo"]
            disparou = (
                (condicao == "menor" and preco_atual <= preco_alvo) or
                (condicao == "maior" and preco_atual >= preco_alvo)
            )

            if disparou:
                disparados.append({
                    "id": alerta["id"],
                    "produto": alerta["produto"],
                    "preco_alvo": preco_alvo,
                    "condicao": condicao,
                    "preco_atual": preco_atual,
                    "fonte": melhor.get("fonte", ""),
                    "nome_encontrado": melhor.get("nome", ""),
                    "url": melhor.get("url", ""),
                })
        except (requests.RequestException, ValueError) as e:
            logger.warning("Falha ao verificar alerta %s (%s): %s", alerta["id"], alerta["produto"], e)
        except Exception as e:
            logger.exception("Erro inesperado ao verificar alerta %s", alerta["id"])

    return jsonify({
        "disparados": disparados,
        "verificados": len(ativos),
        "total_disparados": len(disparados),
    })
