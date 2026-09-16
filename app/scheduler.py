"""Scheduler para verificação periódica de alertas de preço.

Roda um job a cada N minutos, busca preços dos produtos monitorados
e dispara log quando o preço atinge o alvo configurado.

Em produção (Render free tier), o scheduler roda no mesmo worker que
o Flask (gunicorn --preload) para evitar custo extra.
"""

import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

_scheduler = None


def _verificar_alertas_job():
    """Job executado periodicamente pelo APScheduler."""
    try:
        from .repos import alertas_repo
        from .services.produtos.aggregator import buscar_ofertas
    except ImportError:
        logger.warning("Dependências não disponíveis — pulando verificação de alertas")
        return

    ativos = alertas_repo.listar_ativos()
    if not ativos:
        logger.debug("Nenhum alerta ativo — nada a verificar")
        return

    logger.info("Verificando %d alertas ativos...", len(ativos))
    disparados = 0

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
                disparados += 1
                logger.warning(
                    "🔔 ALERTA DISPARADO: %s | Preço atual R$%.2f %s R$%.2f | Fonte: %s",
                    alerta["produto"], preco_atual,
                    "<=" if condicao == "menor" else ">=",
                    preco_alvo, melhor.get("fonte", ""),
                )
        except (requests.RequestException, ValueError) as e:
            logger.warning("Falha ao verificar alerta %s (%s): %s", alerta["id"], alerta["produto"], e)
        except Exception as e:
            logger.exception("Erro inesperado ao verificar alerta %s", alerta["id"])

    if disparados:
        logger.warning("Verificação concluída: %d/%d alertas dispararam", disparados, len(ativos))
    else:
        logger.info("Verificação concluída: nenhum alerta disparou")


def iniciar_scheduler(intervalo_minutos: int = 15):
    """Inicia o scheduler de verificação de alertas.

    Em desenvolvimento (debug=True), usa intervalo mais curto.
    Em produção, usa o intervalo configurado (padrão: 15 min).
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler já está rodando")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning("APScheduler não instalado — verificação de alertas será manual")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _verificar_alertas_job,
        trigger=IntervalTrigger(minutes=intervalo_minutos),
        id="verificar_alertas",
        name="Verificação periódica de alertas de preço",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler iniciado: verificação a cada %d minutos", intervalo_minutos)


def parar_scheduler():
    """Para o scheduler (chamado no shutdown do app)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler parado")
