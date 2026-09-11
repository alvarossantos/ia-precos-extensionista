"""Guarda, em SQLite, cada snapshot de preço coletado de verdade para
produtos comuns. Como as fontes não fornecem histórico retroativo, o
histórico é construído aos poucos: cada vez que o cache decide que é
preciso buscar de novo, o novo preço vira mais um ponto na série.
"""

import logging
from datetime import datetime, timedelta

from ..db import conexao

logger = logging.getLogger(__name__)


class HistoricoRepository:
    def __init__(self, db_path: str = "historico_local.db"):
        self.db_path = db_path
        self._criar_tabela()

    def _criar_tabela(self):
        with conexao(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS preco_snapshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produto TEXT NOT NULL,
                    nome_encontrado TEXT,
                    preco REAL NOT NULL,
                    moeda TEXT DEFAULT 'BRL',
                    fonte TEXT,
                    coletado_em TEXT NOT NULL
                )
                """
            )
            # Índice: toda leitura filtra por produto e ordena por data.
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_preco_snapshot_produto_data "
                "ON preco_snapshot (produto, coletado_em)"
            )

    def salvar_preco(self, produto: str, preco: float, nome_encontrado: str = None,
                      moeda: str = "BRL", fonte: str = "multi"):
        with conexao(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO preco_snapshot (produto, nome_encontrado, preco, moeda, fonte, coletado_em)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (produto, nome_encontrado, preco, moeda, fonte, datetime.now().isoformat()),
            )
        logger.info("Preço salvo: produto=%s preco=%s fonte=%s", produto, preco, fonte)

    def buscar_historico(self, produto: str, dias: int = None):
        """Retorna a série de preços já coletados, no formato
        [{'time': 'dd/mm HH:MM', 'close': preco}, ...], ordenado por data.
        """
        with conexao(self.db_path) as conn:
            if dias:
                data_inicio = (datetime.now() - timedelta(days=dias)).isoformat()
                cursor = conn.execute(
                    """
                    SELECT preco, coletado_em FROM preco_snapshot
                    WHERE produto = ? AND coletado_em >= ?
                    ORDER BY coletado_em ASC
                    """,
                    (produto, data_inicio),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT preco, coletado_em FROM preco_snapshot
                    WHERE produto = ?
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
