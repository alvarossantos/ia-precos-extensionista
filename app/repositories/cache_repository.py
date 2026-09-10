"""Camada de cache (recall) para o sistema de previsão de preços.

Antes de buscar/scrapear um produto numa fonte externa (Mercado
Livre, Amazon, Binance, etc.), verifica no SQLite se esse produto já
foi buscado recentemente. Se sim, evita nova busca externa e
reaproveita o histórico já salvo.

Uso típico (camada de serviço):

    cache = CacheRepository()
    if cache.deve_buscar("produto_123", ttl_horas=24):
        dados = buscador_externo.buscar("produto_123")
        historico_repo.salvar(dados)
        cache.registrar_busca("produto_123")
    else:
        dados = historico_repo.buscar_ultimo("produto_123")
"""

import logging
from datetime import datetime, timedelta

from ..db import conexao

logger = logging.getLogger(__name__)


class CacheRepository:
    """Responsável apenas pelo controle de 'quando foi buscado'.
    Não guarda preços — isso é responsabilidade do HistoricoRepository."""

    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._criar_tabela()

    def _criar_tabela(self):
        with conexao(self.db_path) as conn:
            conn.execute(
                """
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
        """True se o produto nunca foi buscado, ou se a última busca
        está fora do prazo de validade (ttl_horas)."""
        with conexao(self.db_path) as conn:
            row = conn.execute(
                "SELECT ultima_busca_em FROM busca_cache WHERE produto_id = ?",
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
                """
                INSERT INTO busca_cache (produto_id, fonte, ultima_busca_em)
                VALUES (?, ?, ?)
                ON CONFLICT(produto_id) DO UPDATE SET
                    ultima_busca_em = excluded.ultima_busca_em,
                    fonte = excluded.fonte
                """,
                (produto_id, fonte, agora),
            )
        logger.debug("Busca registrada: produto=%s fonte=%s", produto_id, fonte)

    def ultima_busca(self, produto_id: str):
        with conexao(self.db_path) as conn:
            row = conn.execute(
                "SELECT ultima_busca_em FROM busca_cache WHERE produto_id = ?",
                (produto_id,),
            ).fetchone()
        return datetime.fromisoformat(row[0]) if row else None

    def listar_recentes(self, limite: int = 20):
        """Últimas buscas registradas — usado por /api/historico-buscas."""
        limite = max(1, min(limite, 100))
        with conexao(self.db_path) as conn:
            rows = conn.execute(
                "SELECT produto_id, fonte, ultima_busca_em FROM busca_cache "
                "ORDER BY ultima_busca_em DESC LIMIT ?",
                (limite,),
            ).fetchall()
        return [
            {"produto": r[0], "fonte": r[1], "data": r[2]}
            for r in rows
        ]
