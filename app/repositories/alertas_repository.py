"""Repositório de alertas de preço.

No backend original essa lógica (criar tabela, INSERT/SELECT/DELETE
cru) ficava espalhada dentro das próprias funções de rota em
mock_backend.py. Extraída para uma classe própria pelos mesmos
motivos dos outros repositórios: testável isoladamente e sem SQL
duplicado entre rotas.
"""

import logging
from datetime import datetime

from ..db import conexao

logger = logging.getLogger(__name__)

CONDICOES_VALIDAS = ("menor", "maior")


class AlertasRepository:
    def __init__(self, db_path: str = "alertas.db"):
        self.db_path = db_path
        self._criar_tabela()

    def _criar_tabela(self):
        with conexao(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alertas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                "SELECT id, produto, preco_alvo, condicao FROM alertas WHERE ativo = 1"
            ).fetchall()
        return [
            {"id": r[0], "produto": r[1], "preco_alvo": r[2], "condicao": r[3]}
            for r in rows
        ]

    def criar(self, produto: str, preco_alvo: float, condicao: str) -> int:
        if condicao not in CONDICOES_VALIDAS:
            condicao = "menor"
        with conexao(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO alertas (produto, preco_alvo, condicao, ativo, criado_em) "
                "VALUES (?, ?, ?, 1, ?)",
                (produto, preco_alvo, condicao, datetime.now().isoformat()),
            )
            alerta_id = cursor.lastrowid
        logger.info("Alerta criado: id=%s produto=%s alvo=%s", alerta_id, produto, preco_alvo)
        return alerta_id

    def remover(self, alerta_id: int):
        with conexao(self.db_path) as conn:
            conn.execute("DELETE FROM alertas WHERE id = ?", (alerta_id,))
        logger.info("Alerta removido: id=%s", alerta_id)
