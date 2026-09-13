"""Camada de cache para o sistema de previsão de preços.

Suporta PostgreSQL (produção/Render) e SQLite (desenvolvimento local).
"""

import logging
from datetime import datetime, timedelta

from ..db import conexao, _is_postgres

logger = logging.getLogger(__name__)

PH = "%s" if _is_postgres() else "?"


class CacheRepository:
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._criar_tabela()

    def _criar_tabela(self):
        with conexao(self.db_path) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS busca_cache (
                    produto_id TEXT PRIMARY KEY,
                    fonte TEXT,
                    ultima_busca_em TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_busca_cache_data "
                "ON busca_cache (ultima_busca_em DESC)"
            )

    def deve_buscar(self, produto_id: str, ttl_horas: int = 24) -> bool:
        with conexao(self.db_path) as conn:
            row = conn.execute(
                f"SELECT ultima_busca_em FROM busca_cache WHERE produto_id = {PH}",
                (produto_id,),
            ).fetchone()

        if row is None:
            return True

        ultima_busca = datetime.fromisoformat(row[0])
        return datetime.now() - ultima_busca > timedelta(hours=ttl_horas)

    def registrar_busca(self, produto_id: str, fonte: str = None):
        agora = datetime.now().isoformat()
        with conexao(self.db_path) as conn:
            conn.execute(
                f"""
                INSERT INTO busca_cache (produto_id, fonte, ultima_busca_em)
                VALUES ({PH}, {PH}, {PH})
                ON CONFLICT(produto_id) DO UPDATE SET
                    ultima_busca_em = EXCLUDED.ultima_busca_em,
                    fonte = EXCLUDED.fonte
                """,
                (produto_id, fonte, agora),
            )
        logger.debug("Busca registrada: produto=%s fonte=%s", produto_id, fonte)

    def ultima_busca(self, produto_id: str):
        with conexao(self.db_path) as conn:
            row = conn.execute(
                f"SELECT ultima_busca_em FROM busca_cache WHERE produto_id = {PH}",
                (produto_id,),
            ).fetchone()
        return datetime.fromisoformat(row[0]) if row else None

    def listar_recentes(self, limite: int = 20):
        limite = max(1, min(limite, 100))
        with conexao(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT produto_id, fonte, ultima_busca_em FROM busca_cache "
                f"ORDER BY ultima_busca_em DESC LIMIT {PH}",
                (limite,),
            ).fetchall()
        return [
            {"produto": r[0], "fonte": r[1], "data": r[2]}
            for r in rows
        ]
