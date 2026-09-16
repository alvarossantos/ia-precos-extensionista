"""Helper de conexão com banco de dados.

Suporta PostgreSQL (via DATABASE_URL, para Render) e SQLite (local).
Em produção (Render), usa psycopg (v3) com pool de conexões.
Em desenvolvimento, usa SQLite com WAL.
"""

import logging
import os
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool = None


def _is_postgres() -> bool:
    return DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")


if _is_postgres():
    # Render exige sslmode=require
    if "sslmode=" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"

    try:
        import psycopg

        def _get_pool():
            global _pool
            if _pool is None:
                from psycopg_pool import ConnectionPool
                _pool = ConnectionPool(
                    DATABASE_URL,
                    min_size=1,
                    max_size=5,
                )
                logger.info("Pool de conexões PostgreSQL criado (min=1, max=5)")
            return _pool

        @contextmanager
        def conexao(db_path: str = None):
            pool = _get_pool()
            with pool.connection() as conn:
                try:
                    yield conn
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

        def criar_tabelas():
            try:
                with conexao() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS busca_cache (
                            produto_id TEXT PRIMARY KEY,
                            fonte TEXT,
                            ultima_busca_em TEXT NOT NULL
                        )
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_busca_cache_data
                        ON busca_cache (ultima_busca_em DESC)
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS preco_snapshot (
                            id SERIAL PRIMARY KEY,
                            produto TEXT NOT NULL,
                            nome_encontrado TEXT,
                            preco REAL NOT NULL,
                            moeda TEXT DEFAULT 'BRL',
                            fonte TEXT,
                            coletado_em TEXT NOT NULL
                        )
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_preco_snapshot_produto_data
                        ON preco_snapshot (produto, coletado_em)
                    """)
                    conn.commit()
                logger.info("Tabelas PostgreSQL criadas/verificadas")
            except Exception as e:
                logger.error("Falha ao criar tabelas PostgreSQL: %s", e)

    except ImportError:
        logger.warning("psycopg não instalado — usando SQLite como fallback")

        @contextmanager
        def conexao(db_path: str):
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

        def criar_tabelas():
            pass

else:
    # SQLite local (desenvolvimento)
    @contextmanager
    def conexao(db_path: str):
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def criar_tabelas():
        pass
