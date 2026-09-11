"""Endpoints que retornam HTML fragments para HTMX.

Cada rota renderiza um template Jinja2 e retorna o HTML direto.
O HTMX injeta o resultado no DOM via hx-target.
"""

import logging

from flask import Blueprint, render_template, request

from ..config import config
from ..extensions import limiter
from ..repos import alertas_repo, cache_repo, historico_repo
from ..services.produtos.aggregator import FONTES_PADRAO, buscar_ofertas

logger = logging.getLogger(__name__)
html_bp = Blueprint("html", __name__)


# ==================== Busca ====================

@html_bp.route("/hx/buscar")
@limiter.limit(config.RATE_LIMIT_BUSCA)
def hx_buscar():
    produto = request.args.get("produto", "").strip()
    limite = min(int(request.args.get("limite", 5) or 5), 50)
    fontes_raw = request.args.get("fontes", ",".join(FONTES_PADRAO))
    fontes_selecionadas = [f.strip() for f in fontes_raw.split(",") if f.strip()]
    so_novos = request.args.get("so_novos", "").lower() in ("1", "true", "sim", "novos")

    if not produto:
        return render_template("fragments/buscar_resultados.html",
                               erro="Digite um produto para buscar"), 200

    try:
        resultados = buscar_ofertas(produto, limite=limite,
                                     fontes_selecionadas=fontes_selecionadas,
                                     so_novos=so_novos)
    except Exception as e:
        logger.exception("Falha ao buscar '%s'", produto)
        return render_template("fragments/buscar_resultados.html",
                               erro=f"Erro ao buscar: {e}"), 200

    if not resultados:
        return render_template("fragments/buscar_resultados.html",
                               erro=f"Nenhum resultado para '{produto}'"), 200

    # Estatísticas
    precos = [r["preco"] for r in resultados if r.get("preco")]
    fontes_agrupadas = {}
    for r in resultados:
        fontes_agrupadas.setdefault(r.get("fonte", "Outra"), []).append(r)

    stats = {
        "menor_preco": min(precos) if precos else None,
        "maior_preco": max(precos) if precos else None,
        "preco_medio": round(sum(precos) / len(precos), 2) if precos else None,
    }

    return render_template("fragments/buscar_resultados.html",
                           resultados=resultados, erro=None)


@html_bp.route("/hx/buscar/stats")
@limiter.limit(config.RATE_LIMIT_BUSCA)
def hx_buscar_stats():
    """Estatísticas da busca (separado para hx-target independente)."""
    produto = request.args.get("produto", "").strip()
    limite = min(int(request.args.get("limite", 5) or 5), 50)
    fontes_raw = request.args.get("fontes", ",".join(FONTES_PADRAO))
    fontes_selecionadas = [f.strip() for f in fontes_raw.split(",") if f.strip()]
    so_novos = request.args.get("so_novos", "").lower() in ("1", "true", "sim", "novos")

    if not produto:
        return render_template("fragments/buscar_stats.html",
                               estatisticas=None, fontes=[]), 200

    try:
        resultados = buscar_ofertas(produto, limite=limite,
                                     fontes_selecionadas=fontes_selecionadas,
                                     so_novos=so_novos)
    except Exception:
        return render_template("fragments/buscar_stats.html",
                               estatisticas=None, fontes=[]), 200

    precos = [r["preco"] for r in resultados if r.get("preco")]
    fontes_agrupadas = {}
    for r in resultados:
        fontes_agrupadas.setdefault(r.get("fonte", "Outra"), []).append(r)

    stats = {
        "menor_preco": min(precos) if precos else None,
        "maior_preco": max(precos) if precos else None,
        "preco_medio": round(sum(precos) / len(precos), 2) if precos else None,
    }

    return render_template("fragments/buscar_stats.html",
                           estatisticas=stats,
                           fontes=list(fontes_agrupadas.keys()))


# ==================== Comparar ====================

@html_bp.route("/hx/comparar")
@limiter.limit(config.RATE_LIMIT_BUSCA)
def hx_comparar():
    termos_raw = request.args.get("termos", "").strip()
    if not termos_raw:
        return render_template("fragments/comparar_resultados.html",
                               comparacao=None, erro=None), 200

    termos = [t.strip() for t in termos_raw.split(",") if t.strip()]
    if len(termos) < 2:
        return render_template("fragments/comparar_resultados.html",
                               comparacao=None,
                               erro="Insira pelo menos 2 termos"), 200

    comparacao = []
    for termo in termos:
        try:
            resultados = buscar_ofertas(termo, limite=5)
            precos = [r["preco"] for r in resultados if r.get("preco")]
            fontes_unicas = list({r.get("fonte", "") for r in resultados})
            comparacao.append({
                "termo": termo,
                "menor_preco": min(precos) if precos else None,
                "preco_medio": round(sum(precos) / len(precos), 2) if precos else None,
                "resultados": len(resultados),
                "fontes": fontes_unicas,
                "top_resultado": resultados[0] if resultados else None,
                "erro": None,
            })
        except Exception as e:
            comparacao.append({"termo": termo, "erro": str(e)})

    return render_template("fragments/comparar_resultados.html",
                           comparacao=comparacao, erro=None)


# ==================== Alertas ====================

@html_bp.route("/hx/alertas")
def hx_listar_alertas():
    alertas = alertas_repo.listar()
    return render_template("fragments/alertas_lista.html", alertas=alertas)


@html_bp.route("/hx/alertas", methods=["POST"])
@limiter.limit(config.RATE_LIMIT_BUSCA)
def hx_criar_alerta():
    dados = request.get_json(silent=True) or {}
    produto = (dados.get("produto") or "").strip()
    preco_alvo = dados.get("preco_alvo")
    condicao = dados.get("condicao", "menor")

    if not produto or preco_alvo is None:
        return render_template("fragments/alertas_lista.html",
                               alertas=alertas_repo.listar()), 200

    try:
        preco_alvo = float(preco_alvo)
    except (TypeError, ValueError):
        return render_template("fragments/alertas_lista.html",
                               alertas=alertas_repo.listar()), 200

    if preco_alvo > 0:
        alertas_repo.criar(produto, preco_alvo, condicao)

    return render_template("fragments/alertas_lista.html",
                           alertas=alertas_repo.listar())


@html_bp.route("/hx/alertas/<int:alerta_id>", methods=["DELETE"])
def hx_deletar_alerta(alerta_id: int):
    alertas_repo.remover(alerta_id)
    return render_template("fragments/alertas_lista.html",
                           alertas=alertas_repo.listar())


@html_bp.route("/hx/alertas/verificar")
def hx_verificar_alertas():
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

    return render_template("fragments/alertas_ativados.html", atingidos=atingidos)


# ==================== Histórico ====================

@html_bp.route("/hx/historico")
def hx_historico():
    limite = int(request.args.get("limite", 20) or 20)
    buscas = cache_repo.listar_recentes(limite=limite)
    return render_template("fragments/historico_lista.html", buscas=buscas)
