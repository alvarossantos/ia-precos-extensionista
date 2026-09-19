# PreçoCerto — Sistema de Análise e Comparação de Preços

Atividade Extensionista — 6º período, Sistemas de Informação, UEMG
Unidade Acadêmica de Passos. Compara preços de produtos em múltiplas
lojas brasileiras e analisa tendências de criptomoedas, oferecendo
previsões por IA como apoio à decisão de compra.

## Como rodar

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Acesse `http://127.0.0.1:5000`. O Flask serve a API (`/api/...`) e
o frontend Vue 3 (`/`) na mesma porta.

Testes:

```bash
pytest -v
```

## Deploy no Render

1. Criar conta no [Render](https://render.com)
2. New → Web Service → conectar repositório GitHub
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --preload`
5. Criar PostgreSQL gratuito (New → PostgreSQL)
6. Copiar Internal Database URL → Environment → `DATABASE_URL`
7. Adicionar chaves de API no Environment

## Arquitetura

```
run.py                    # ponto de entrada
app/
  __init__.py             # application factory (create_app)
  config.py               # configuração via variáveis de ambiente
  extensions.py           # logging + rate limiting (Flask-Limiter)
  http_client.py          # sessão requests com timeout + retry + binance_get()
  db.py                   # PostgreSQL (DATABASE_URL) ou SQLite (local)
  repos.py                # singletons dos repositórios
  repositories/
    cache_repository.py   # cache de buscas
    historico_repository.py # série histórica de preços
  services/
    cripto_service.py     # Binance + CoinGecko (fallback)
    llm_service.py        # OpenRouter + NVIDIA NIM (fallback)
    previsao_service.py   # SMA20/SMA50 + refinamento por IA
    produtos/
      fontes.py           # scraping/API de cada loja
      filtros.py          # relevância, acessórios, inglês, IA
      ranking.py          # pontuação com distribuição por fonte
      aggregator.py       # pipelines de busca paralela
  routes/
    pages.py              # serves index.html + /health + /favicon.ico
    historico_routes.py   # /api/historico
    previsao_routes.py    # /api/previsao
    buscar_routes.py      # /api/buscar
    comparar_routes.py    # /api/comparar
    analise_ia_routes.py  # /api/analise-ia
    fontes_routes.py      # /api/fontes
static/                   # Vue 3 + Vue Router (CDN)
  index.html
  favicon.svg
  css/styles.css
  js/
    api.js                # fetchJSON helpers
    userStore.js          # localStorage (alertas, histórico, buscas)
    app.js                # Vue app + router + detecção de OS
    components/
      DashboardTab.js     # cripto/produto + gráfico + previsão IA
      BuscarTab.js        # busca multi-fonte + alertas
      CompararTab.js      # comparação lado a lado
      AlertasTab.js       # gerenciamento de alertas (localStorage)
      HistoricoTab.js     # histórico de buscas
tests/
  test_filtros.py
  test_previsao_service.py
  test_ranking.py
```

## Variáveis de ambiente

Veja `.env.example` para a lista completa.

| Variável | Obrigatória | Efeito se ausente |
|---|---|---|
| `DATABASE_URL` | Produção | Usa SQLite local (desenvolvimento) |
| `OPENROUTER_API_KEY` | Não | Previsão sem texto IA |
| `NVIDIA_API_KEY` | Não | Fallback IA indisponível |
| `SERPAPI_API_KEY` | Não | Google Shopping/orgânico vazios |
| `CACHE_TTL_HORAS` | Não (6h) | Intervalo entre buscas externas |

## Fontes de dados

| Fonte | Tipo | Requer chave |
|---|---|---|
| Binance | API pública | Não |
| CoinGecko | API pública (fallback) | Não |
| Americanas | API VTEX | Não |
| Carrefour | API VTEX | Não |
| KaBuM! | API interna | Não |
| Samsung Store | Intelligent Search API | Não |
| Buscapé | Scraping (`__NEXT_DATA__`) | Não |
| Zoom | Scraping (`__NEXT_DATA__`) | Não |
| Google Shopping | SerpAPI | Sim |
| Google orgânico | SerpAPI | Sim |

## Limitações conhecidas

- **Buscapé/Zoom** dependem de estrutura interna (`__NEXT_DATA__`). Se
  mudarem o layout, retornam vazio (fail-open — outras fontes continuam).
- **Rate limiting em memória.** Para múltiplos workers, migrar para Redis.
- **CORS aberto** (`*`). Restringir ao domínio real em produção.
- **Buscapé/Zoom bloqueados em cloud.** IPs de datacenter recebem 403.
  Outras fontes continuam funcionando (fail-open).

## O que mudou do protótipo original

- Alertas sem filtro → agora usam pipeline filtrado de relevância
- Mercado Livre removido (API instável)
- XSS corrigido (escapeHtml + data-* attributes)
- Pipeline de busca unificado em `aggregator.py`
- Frontend migrado de HTMX para Vue 3 + Vue Router
- Tema escuro/claro segue preferência do OS
- Estilos nativos por plataforma (iOS/Android/macOS/Windows)
- Busca paralela com ThreadPoolExecutor (~1.4s vs 10s)
- Ranking com distribuição por fonte (não só preço)
- CoinGecko como fallback quando Binance bloqueia (cloud IPs)
- NVIDIA NIM como fallback direto quando OpenRouter falha
- Deploy no Render com PostgreSQL gerenciado
