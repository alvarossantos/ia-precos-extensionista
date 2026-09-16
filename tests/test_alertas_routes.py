"""Testes de integração para as rotas de alertas.

Usa Flask test client para testar os endpoints sem subir servidor.
Cada teste usa banco isolado via monkeypatch nos paths do config.
"""

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    """Cria app Flask para testes com banco isolado."""
    import os
    os.environ.pop("DATABASE_URL", None)

    # Força paths de banco para diretório temporário
    cache_db = str(tmp_path / "cache.db")
    historico_db = str(tmp_path / "historico.db")
    monkeypatch.setenv("CACHE_DB_PATH", cache_db)
    monkeypatch.setenv("HISTORICO_DB_PATH", historico_db)

    # Força re-leitura do config
    from app.config import config as cfg
    cfg.CACHE_DB_PATH = cache_db
    cfg.HISTORICO_DB_PATH = historico_db

    # Reseta singletons para recriar com novos paths
    import app.repos as repos_mod
    repos_mod._cache_repo = None
    repos_mod._historico_repo = None
    repos_mod._alertas_repo = None

    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


class TestAlertasRoutes:
    def test_listar_vazio(self, client):
        r = client.get("/api/alertas")
        assert r.status_code == 200
        data = r.json
        assert data["total"] == 0
        assert data["alertas"] == []

    def test_criar_alerta(self, client):
        r = client.post("/api/alertas", json={
            "produto": "notebook dell",
            "preco_alvo": 3000,
            "condicao": "menor",
        })
        assert r.status_code == 201
        data = r.json
        assert data["ok"] is True
        assert data["alerta"]["produto"] == "notebook dell"
        assert data["alerta"]["preco_alvo"] == 3000
        assert data["alerta"]["ativo"] is True

    def test_criar_alerta_sem_produto(self, client):
        r = client.post("/api/alertas", json={"preco_alvo": 3000})
        assert r.status_code == 400

    def test_criar_alerta_preco_invalido(self, client):
        r = client.post("/api/alertas", json={
            "produto": "notebook dell",
            "preco_alvo": -100,
        })
        assert r.status_code == 400

    def test_listar_apos_criar(self, client):
        client.post("/api/alertas", json={
            "produto": "notebook dell",
            "preco_alvo": 3000,
        })
        r = client.get("/api/alertas")
        assert r.status_code == 200
        assert r.json["total"] == 1

    def test_remover_alerta(self, client):
        r = client.post("/api/alertas", json={
            "produto": "notebook dell",
            "preco_alvo": 3000,
        })
        alerta_id = r.json["alerta"]["id"]
        r = client.delete(f"/api/alertas/{alerta_id}")
        assert r.status_code == 200
        assert r.json["ok"] is True

    def test_remover_alerta_inexistente(self, client):
        r = client.delete("/api/alertas/999")
        assert r.status_code == 404

    def test_toggle_alerta(self, client):
        r = client.post("/api/alertas", json={
            "produto": "notebook dell",
            "preco_alvo": 3000,
        })
        alerta_id = r.json["alerta"]["id"]
        r = client.post(f"/api/alertas/{alerta_id}/toggle")
        assert r.status_code == 200
        assert r.json["ativo"] is False

    def test_verificar_sem_alertas(self, client):
        r = client.get("/api/alertas/verificar")
        assert r.status_code == 200
        assert r.json["verificados"] == 0
        assert r.json["disparados"] == []
