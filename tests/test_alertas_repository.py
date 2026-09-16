"""Testes de integração para o repositório de alertas.

Usa SQLite em memória para testar CRUD sem depender de rede ou banco externo.
"""

import sqlite3
from unittest.mock import patch

import pytest


@pytest.fixture
def repo():
    """Cria um AlertasRepository com SQLite em memória."""
    with patch("app.repositories.alertas_repository.conexao") as mock_conn:
        # Configura conexão em memória
        mem_db = sqlite3.connect(":memory:")
        mem_db.execute("PRAGMA journal_mode=WAL")

        def ctx_mgr(db_path=None):
            from contextlib import contextmanager

            @contextmanager
            def _conn():
                yield mem_db
                mem_db.commit()

            return _conn()

        mock_conn.side_effect = ctx_mgr

        from app.repositories.alertas_repository import AlertasRepository

        r = AlertasRepository(":memory:")
        # Substitui a conexão real pela mockada
        r._conn = mem_db
        yield r, mem_db
        mem_db.close()


class TestAlertasRepository:
    def test_criar_alerta(self, repo):
        repo_obj, db = repo
        alerta_id = repo_obj.criar("notebook dell", 3000.0, "menor")
        assert alerta_id is not None
        assert alerta_id > 0

    def test_listar_alertas(self, repo):
        repo_obj, db = repo
        repo_obj.criar("notebook dell", 3000.0, "menor")
        repo_obj.criar("iphone 15", 5000.0, "maior")
        alertas = repo_obj.listar()
        assert len(alertas) == 2
        assert alertas[0]["produto"] == "iphone 15"  # Mais recente primeiro

    def test_listar_ativos(self, repo):
        repo_obj, db = repo
        id1 = repo_obj.criar("notebook dell", 3000.0, "menor")
        repo_obj.criar("iphone 15", 5000.0, "menor")
        repo_obj.toggle(id1, False)  # Desativa primeiro
        ativos = repo_obj.listar_ativos()
        assert len(ativos) == 1
        assert ativos[0]["produto"] == "iphone 15"

    def test_obter_alerta(self, repo):
        repo_obj, db = repo
        id1 = repo_obj.criar("notebook dell", 3000.0, "menor")
        alerta = repo_obj.obter(id1)
        assert alerta is not None
        assert alerta["produto"] == "notebook dell"
        assert alerta["preco_alvo"] == 3000.0
        assert alerta["condicao"] == "menor"
        assert alerta["ativo"] is True

    def test_obter_alerta_inexistente(self, repo):
        repo_obj, db = repo
        assert repo_obj.obter(999) is None

    def test_toggle_alerta(self, repo):
        repo_obj, db = repo
        id1 = repo_obj.criar("notebook dell", 3000.0, "menor")
        repo_obj.toggle(id1, False)
        alerta = repo_obj.obter(id1)
        assert alerta["ativo"] is False
        repo_obj.toggle(id1, True)
        alerta = repo_obj.obter(id1)
        assert alerta["ativo"] is True

    def test_remover_alerta(self, repo):
        repo_obj, db = repo
        id1 = repo_obj.criar("notebook dell", 3000.0, "menor")
        repo_obj.remover(id1)
        assert repo_obj.obter(id1) is None

    def test_condicao_invalida_padrao_para_menor(self, repo):
        repo_obj, db = repo
        id1 = repo_obj.criar("notebook dell", 3000.0, "invalido")
        alerta = repo_obj.obter(id1)
        assert alerta["condicao"] == "menor"
