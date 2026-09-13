"""Instâncias únicas (singletons) dos repositórios, compartilhadas
por todas as rotas. Criadas em um módulo próprio (em vez de dentro de
cada rota) para não reabrir/recriar tabelas a cada requisição.
"""

from .config import config
from .repositories.cache_repository import CacheRepository
from .repositories.historico_repository import HistoricoRepository

cache_repo = CacheRepository(config.CACHE_DB_PATH)
historico_repo = HistoricoRepository(config.HISTORICO_DB_PATH)
