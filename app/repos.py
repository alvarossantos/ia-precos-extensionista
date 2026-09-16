"""Instâncias únicas (singletons) dos repositórios, compartilhadas
por todas as rotas. Inicialização lazy — cria na primeira acesso.
"""

from .config import config

_cache_repo = None
_historico_repo = None
_alertas_repo = None


def _get_cache_repo():
    global _cache_repo
    if _cache_repo is None:
        from .repositories.cache_repository import CacheRepository
        _cache_repo = CacheRepository(config.CACHE_DB_PATH)
    return _cache_repo


def _get_historico_repo():
    global _historico_repo
    if _historico_repo is None:
        from .repositories.historico_repository import HistoricoRepository
        _historico_repo = HistoricoRepository(config.HISTORICO_DB_PATH)
    return _historico_repo


def _get_alertas_repo():
    global _alertas_repo
    if _alertas_repo is None:
        from .repositories.alertas_repository import AlertasRepository
        _alertas_repo = AlertasRepository(config.CACHE_DB_PATH)
    return _alertas_repo


class _RepoProxy:
    """Proxy que inicializa o repo no primeiro acesso."""
    def __init__(self, getter):
        object.__setattr__(self, '_getter', getter)

    def __getattr__(self, name):
        return getattr(self._getter(), name)


cache_repo = _RepoProxy(_get_cache_repo)
historico_repo = _RepoProxy(_get_historico_repo)
alertas_repo = _RepoProxy(_get_alertas_repo)
