"""Helper de conexão SQLite compartilhado pelos repositórios.

Habilita WAL (Write-Ahead Log), que permite leituras concorrentes
enquanto uma escrita acontece — reduz bastante os "database is
locked" que o SQLite padrão costuma dar sob uso concorrente (ex.:
Flask + verificação de alertas rodando ao mesmo tempo).
"""

import sqlite3
from contextlib import contextmanager


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
