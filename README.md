# Preditor IA — Sistema de Previsão de Tendências de Preços

Atividade Extensionista — 6º período, Sistemas de Informação, UEMG
Unidade Acadêmica de Passos. Analisa o histórico de preços de
criptomoedas e produtos comuns e sugere tendências (alta, queda,
estabilidade) como apoio à decisão de compra.

Este diretório é uma reorganização do protótipo original
(`mock_backend.py` + `index.html` + `js/app.js` em arquivos únicos)
em um backend Flask estruturado em módulos, mais robusto a falhas de
rede/scraping e com testes automatizados. O comportamento das rotas
da API foi mantido — quem já integrou com o frontend não precisa
mudar nada — mas a organização interna e alguns bugs foram corrigidos
(ver "O que mudou" no fim deste arquivo).

## Como rodar

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # opcional — funciona sem editar nada
python run.py
```

Acesse `http://127.0.0.1:5000`. O Flask serve tanto a API (`/api/...`)
quanto o frontend estático (`/`) na mesma porta.

Para rodar os testes:

```bash
pytest -v
```

## Arquitetura

```
run.py                  # ponto de entrada (python run.py)
app/
  __init__.py            # application factory (create_app)
  config.py               # toda configuração via variáveis de ambiente
  extensions.py            # logging + rate limiting (Flask-Limiter)
  http_client.py            # sessão requests com timeout + retry/backoff
  db.py                      # conexão SQLite (WAL) compartilhada
  repos.py                    # instâncias únicas dos repositórios
  repositories/                # acesso a dados (SQLite)
    cache_repository.py          # "já busquei isso recentemente?"
    historico_repository.py       # série histórica de preços coletados
    alertas_repository.py          # CRUD de alertas de preço
  services/                    # regras de negócio, sem Flask/SQL direto
    cripto_service.py            # Binance
    llm_service.py                 # OpenRouter, com fallback entre modelos
    previsao_service.py             # SMA20/SMA50 + refinamento por IA
    mercadolivre_oauth.py            # fluxo OAuth do Mercado Livre
    produtos/
      fontes.py                       # scraping/API de cada loja
      filtros.py                       # relevância, novos, acessórios, IA
      ranking.py                        # pontuação e ordenação final
      aggregator.py                      # junta tudo: pipelines de busca
  routes/                       # só HTTP: parse de request, chama service,
                                 # devolve jsonify — 1 blueprint por área
static/                  # frontend (index.html, css/, js/) — sem mudanças
                          # de funcionalidade, só correções de segurança
tests/                    # testes de unidade (funções puras, sem rede)
```

A regra usada para separar as camadas: **routes** não sabem de SQL
nem de scraping (só HTTP), **services** não sabem de Flask, e
**repositories** não sabem de regra de negócio, só de persistência.
Isso é o que torna `tests/` possível sem subir servidor nem mockar
rede — `previsao_service`, `filtros` e `ranking` são funções puras
testadas diretamente.

## Variáveis de ambiente

Veja `.env.example` para a lista completa e comentada. Nenhuma é
obrigatória: sem `OPENROUTER_API_KEY`, a previsão cai para o SMA puro
(sem o texto de IA); sem `SERPAPI_API_KEY`, as fontes Google Shopping
e Google orgânico simplesmente retornam vazio; sem `ML_CLIENT_ID`, a
busca no Mercado Livre continua funcionando (usa o endpoint público),
só sem o limite de uso mais alto do OAuth.

| Variável | Obrigatória | Efeito se ausente |
|---|---|---|
| `OPENROUTER_API_KEY` | Não | Previsão/análise sem texto gerado por IA |
| `SERPAPI_API_KEY` | Não | Google Shopping e Google orgânico ficam vazios |
| `ML_CLIENT_ID` / `ML_CLIENT_SECRET` | Não | Mercado Livre busca sem OAuth (limites menores) |
| `CACHE_TTL_HORAS` | Não (padrão 6) | Intervalo mínimo entre buscas externas do mesmo produto |
| `CORS_ORIGINS` | Não (padrão `*`) | Em produção, defina o domínio real do frontend |

## Fontes de dados

| Fonte | Tipo | Requer chave | Observação |
|---|---|---|---|
| Binance | API pública | Não | Cripto |
| Mercado Livre | API pública | Não | OAuth opcional (limites maiores) |
| Americanas | API VTEX | Não | |
| KaBuM! | API interna | Não | |
| Samsung Store | Intelligent Search API | Não | |
| Buscapé / Zoom | Scraping (`__NEXT_DATA__`) | Não | **Frágil** — ver limitações |
| Google Shopping / Google | SerpAPI | Sim (`SERPAPI_API_KEY`) | |

## Limitações conhecidas

- **SQLite em vez de Postgres.** O desenho original do projeto previa
  Postgres com schema `fonte/produto/preco_historico/previsao`. Este
  backend de desenvolvimento usa três bancos SQLite (`cache.db`,
  `historico_local.db`, `alertas.db`) por simplicidade — adequado para
  demonstração/apresentação, mas numa eventual entrega "de produção"
  valeria migrar para Postgres com SQLAlchemy.
- **Buscapé e Zoom dependem de uma estrutura interna não documentada**
  (`__NEXT_DATA__` no HTML da página de busca). Se essas plataformas
  mudarem o layout, essas duas fontes passam a retornar lista vazia
  silenciosamente (o restante do pipeline continua funcionando com as
  fontes que sobrarem — é um fail-open intencional, mas vale saber
  que é o ponto mais provável de quebrar sem aviso).
- **Rate limiting é em memória** (`Flask-Limiter` com `storage_uri="memory://"`).
  Funciona bem para um processo único (como este projeto roda); se um
  dia for servido com múltiplos processos/workers, os limites deixam
  de ser compartilhados entre eles — trocar para Redis nesse caso.
- **CORS aberto por padrão** (`CORS_ORIGINS=*`). Adequado para rodar
  localmente; restrinja ao domínio real antes de expor publicamente.
- **Tokens do Mercado Livre em texto simples** no `.env`. Aceitável
  para um projeto acadêmico rodando localmente; não é o padrão
  recomendado para produção (cofre de segredos, variáveis de ambiente
  do provedor de hospedagem, etc.).

## O que mudou em relação ao protótipo original

Além da reorganização em módulos, esta versão corrigiu alguns
problemas encontrados durante a revisão:

- **Alertas de preço sem filtro nenhum.** `/api/alertas/verificar`
  usava o primeiro resultado bruto da busca (sem checar relevância) —
  um acessório barato e irrelevante podia disparar um alerta por
  engano. Agora reusa o mesmo pipeline filtrado de `/api/buscar`.
- **Busca no Mercado Livre exigia OAuth sem necessidade.** O endpoint
  usado (`/sites/{site}/search`) é público; o código antigo lançava
  erro se não houvesse `ML_ACCESS_TOKEN` configurado. Agora o token é
  enviado só se existir.
- **Falhas silenciosas.** Dezenas de `except Exception: pass/continue`
  foram substituídos por `logger.warning`/`logger.exception`, sem
  mudar o comportamento (a resposta ao usuário continua a mesma), mas
  agora dá pra ver no console quando e por que uma fonte falhou.
- **XSS no frontend.** Nome de produto (vindo de scraping de
  terceiros) e o link do produto (usado dentro de um `onclick` inline
  com o valor interpolado direto na string) eram injetados sem escape
  no `innerHTML`. Adicionado um helper `escapeHtml()` e os cliques
  passaram a ler de `data-*` + `addEventListener` em vez de HTML
  inline.
- **`.env` reescrito à mão.** A função que salvava o token do Mercado
  Livre reabria e reescrevia o arquivo `.env` inteiro linha a linha;
  trocada por `dotenv.set_key`, que edita só a chave necessária.
- **Pipeline de busca duplicado 4 vezes.** `/api/buscar`,
  `/api/comparar`, `/api/analise-ia` e a verificação de alertas
  reimplementavam quase a mesma sequência "buscar → filtrar
  relevância → (filtrar novos) → ranking". Unificado em
  `aggregator.buscar_ofertas()`.
# ia-precos-extensionista
