"""Guarda snapshots de preço coletados de fontes externas.

Suporta PostgreSQL (produção/Render) e SQLite (desenvolvimento local).
"""

import logging
from datetime import datetime, timedelta

from ..db import conexao, _is_postgres

logger = logging.getLogger(__name__)

PH = "%s" if _is_postgres() else "?"


class HistoricoRepository:
    def __init__(self, db_path: str = "historico_local.db"):
        self.db_path = db_path
        self._criar_tabela()

    def _criar_tabela(self):
        with conexao(self.db_path) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS preco_snapshot (
                    id {'SERIAL PRIMARY KEY' if _is_postgres() else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
                    produto TEXT NOT NULL,
                    nome_encontrado TEXT,
                    preco REAL NOT NULL,
                    moeda TEXT DEFAULT 'BRL',
                    fonte TEXT,
                    coletado_em TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_preco_snapshot_produto_data "
                "ON preco_snapshot (produto, coletado_em)"
            )

    def salvar_preco(self, produto: str, preco: float, nome_encontrado: str = None,
                      moeda: str = "BRL", fonte: str = "multi"):
        with conexao(self.db_path) as conn:
            conn.execute(
                f"""
                INSERT INTO preco_snapshot (produto, nome_encontrado, preco, moeda, fonte, coletado_em)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH})
                """,
                (produto, nome_encontrado, preco, moeda, fonte, datetime.now().isoformat()),
            )
        logger.info("Preço salvo: produto=%s preco=%s fonte=%s", produto, preco, fonte)

    def buscar_historico(self, produto: str, dias: int = None):
        with conexao(self.db_path) as conn:
            if dias:
                data_inicio = (datetime.now() - timedelta(days=dias)).isoformat()
                cursor = conn.execute(
                    f"""
                    SELECT preco, coletado_em FROM preco_snapshot
                    WHERE produto = {PH} AND coletado_em >= {PH}
                    ORDER BY coletado_em ASC
                    """,
                    (produto, data_inicio),
                )
            else:
                cursor = conn.execute(
                    f"""
                    SELECT preco, coletado_em FROM preco_snapshot
                    WHERE produto = {PH}
                    ORDER BY coletado_em ASC
                    """,
                    (produto,),
                )
            linhas = cursor.fetchall()

        return [
            {
                "time": datetime.fromisoformat(coletado_em).strftime("%d/%m %H:%M"),
                "close": preco,
            }
            for preco, coletado_em in linhas
        ]
