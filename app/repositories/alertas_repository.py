"""Repositório de alertas de preço.

Suporta PostgreSQL (produção/Render) e SQLite (desenvolvimento local).
Gerencia alertas que disparam quando o preço de um produto atinge o alvo.
"""

import logging
from datetime import datetime

from ..db import conexao, _is_postgres

logger = logging.getLogger(__name__)

PH = "%s" if _is_postgres() else "?"

CONDICOES_VALIDAS = ("menor", "maior")


class AlertasRepository:
    def __init__(self, db_path: str = "alertas.db"):
        self.db_path = db_path
        self._criar_tabela()

    def _criar_tabela(self):
        with conexao(self.db_path) as conn:
            id_col = "SERIAL PRIMARY KEY" if _is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS alertas (
                    id {id_col},
                    produto TEXT NOT NULL,
                    preco_alvo REAL NOT NULL,
                    condicao TEXT NOT NULL DEFAULT 'menor',
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT NOT NULL
                )
                """
            )

    def listar(self):
        with conexao(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, produto, preco_alvo, condicao, ativo, criado_em "
                "FROM alertas ORDER BY criado_em DESC"
            ).fetchall()
        return [
            {
                "id": r[0], "produto": r[1], "preco_alvo": r[2],
                "condicao": r[3], "ativo": bool(r[4]), "criado_em": r[5],
            }
            for r in rows
        ]

    def listar_ativos(self):
        with conexao(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT id, produto, preco_alvo, condicao FROM alertas WHERE ativo = 1"
            ).fetchall()
        return [
            {"id": r[0], "produto": r[1], "preco_alvo": r[2], "condicao": r[3]}
            for r in rows
        ]

    def obter(self, alerta_id: int):
        with conexao(self.db_path) as conn:
            row = conn.execute(
                f"SELECT id, produto, preco_alvo, condicao, ativo, criado_em "
                f"FROM alertas WHERE id = {PH}",
                (alerta_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "produto": row[1], "preco_alvo": row[2],
            "condicao": row[3], "ativo": bool(row[4]), "criado_em": row[5],
        }

    def criar(self, produto: str, preco_alvo: float, condicao: str) -> int:
        if condicao not in CONDICOES_VALIDAS:
            condicao = "menor"
        with conexao(self.db_path) as conn:
            cursor = conn.execute(
                f"INSERT INTO alertas (produto, preco_alvo, condicao, ativo, criado_em) "
                f"VALUES ({PH}, {PH}, {PH}, 1, {PH})",
                (produto, preco_alvo, condicao, datetime.now().isoformat()),
            )
            if _is_postgres():
                alerta_id = cursor.fetchone()[0]
            else:
                alerta_id = cursor.lastrowid
        logger.info("Alerta criado: id=%s produto=%s alvo=%s", alerta_id, produto, preco_alvo)
        return alerta_id

    def toggle(self, alerta_id: int, ativo: bool):
        with conexao(self.db_path) as conn:
            conn.execute(
                f"UPDATE alertas SET ativo = {PH} WHERE id = {PH}",
                (1 if ativo else 0, alerta_id),
            )
        logger.info("Alerta %s: id=%s", "ativado" if ativo else "desativado", alerta_id)

    def remover(self, alerta_id: int):
        with conexao(self.db_path) as conn:
            conn.execute(f"DELETE FROM alertas WHERE id = {PH}", (alerta_id,))
        logger.info("Alerta removido: id=%s", alerta_id)
