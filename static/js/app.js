document.addEventListener('DOMContentLoaded', () => {
    // ==================== DOM Elements ====================
    const modeToggle = document.getElementById('modeToggle');
    const criptoSelector = document.getElementById('criptoSelector');
    const comumSelector = document.getElementById('comumSelector');
    const assetSelect = document.getElementById('assetSelect');
    const produtoInput = document.getElementById('produtoInput');
    const buscarProdutoBtn = document.getElementById('buscarProdutoBtn');
    const currentPriceEl = document.getElementById('currentPrice');
    const priceChangeEl = document.getElementById('priceChange');
    const infoText = document.getElementById('infoText');
    const aiIcon = document.getElementById('aiIcon');
    const aiTrendEl = document.getElementById('aiTrend');
    const aiConfidenceEl = document.getElementById('aiConfidence');
    const predictionGlow = document.getElementById('predictionGlow');
    const technicalProgress = document.getElementById('technicalProgress');
    const aiReasoning = document.getElementById('aiReasoning');
    const refreshBtn = document.getElementById('refreshBtn');
    const periodoSelect = document.getElementById('periodoSelect');

    // Dashboard de Valores (modo Produto)
    const produtoValores = document.getElementById('produtoValores');
    const pvMenor = document.getElementById('pvMenor');
    const pvMaior = document.getElementById('pvMaior');
    const pvMedia = document.getElementById('pvMedia');
    const pvMenorData = document.getElementById('pvMenorData');
    const pvMaiorData = document.getElementById('pvMaiorData');
    const pvOfertas = document.getElementById('pvOfertas');
    const pvFontes = document.getElementById('pvFontes');
    const pvMelhorOferta = document.getElementById('pvMelhorOferta');
    const pvOfertaImg = document.getElementById('pvOfertaImg');
    const pvOfertaNome = document.getElementById('pvOfertaNome');
    const pvOfertaFonte = document.getElementById('pvOfertaFonte');
    const pvOfertaLink = document.getElementById('pvOfertaLink');
    const soNovosToggle = document.getElementById('soNovosToggle');
    const analiseIaBtn = document.getElementById('analiseIaBtn');
    const pvAnaliseIa = document.getElementById('pvAnaliseIa');
    const pvAnaliseTexto = document.getElementById('pvAnaliseTexto');
    const pvAnaliseModelo = document.getElementById('pvAnaliseModelo');

    // Tabs
    const mainTabs = document.getElementById('mainTabs');
    const tabBtns = mainTabs.querySelectorAll('.nav-link');

    // Buscar
    const buscaAmpliadaInput = document.getElementById('buscaAmpliadaInput');
    const buscaAmpliadaBtn = document.getElementById('buscaAmpliadaBtn');
    const buscaLimite = document.getElementById('buscaLimite');
    const buscaStats = document.getElementById('buscaStats');
    const buscaResultados = document.getElementById('buscaResultados');

    // Comparar
    const compararInput = document.getElementById('compararInput');
    const compararBtn = document.getElementById('compararBtn');
    const compararResultados = document.getElementById('compararResultados');

    // Alertas
    const alertaProduto = document.getElementById('alertaProduto');
    const alertaPreco = document.getElementById('alertaPreco');
    const alertaCondicao = document.getElementById('alertaCondicao');
    const criarAlertaBtn = document.getElementById('criarAlertaBtn');
    const alertasLista = document.getElementById('alertasLista');
    const alertasAtivados = document.getElementById('alertasAtivados');
    const alertasAtivadosLista = document.getElementById('alertasAtivadosLista');

    // Histórico
    const historicoLista = document.getElementById('historicoLista');

    // ==================== State ====================
    let priceChart = null;
    let modoAtual = 'cripto';
    // Relativo à própria origem: o Flask serve o frontend e a API no
    // mesmo host/porta, então isso funciona em localhost, rede local
    // ou um domínio de produção sem precisar editar o código.
    const API_BASE = `${window.location.origin}/api`;

    // ==================== Utils ====================

    // Escapa HTML antes de injetar texto vindo do backend (nomes de
    // produto, fontes, termos de busca) em innerHTML. Esses dados vêm
    // de scraping de terceiros e do que o usuário digitou — sem isso,
    // um nome de produto malicioso poderia injetar HTML/JS na página
    // (XSS refletido).
    const escapeHtml = (valor) => {
        if (valor == null) return '';
        return String(valor)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    const formatPrice = (price, tipo = 'comum') => {
        if (price == null) return '--';
        const moeda = tipo === 'cripto' ? 'USD' : 'BRL';
        const locale = tipo === 'cripto' ? 'en-US' : 'pt-BR';
        return new Intl.NumberFormat(locale, { style: 'currency', currency: moeda }).format(price);
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '--';
        const d = new Date(dateStr);
        return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    };

    // ==================== Tabs ====================
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.add('d-none'));
            const tabId = btn.dataset.tab;
            document.getElementById(`tab-${tabId}`).classList.remove('d-none');

            // Carregar dados ao trocar de tab
            if (tabId === 'alertas') carregarAlertas();
            if (tabId === 'historico') carregarHistorico();
        });
    });

    // ==================== Mode Toggle (Cripto / Produto) ====================
    modeToggle.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-mode]');
        if (!btn) return;

        modoAtual = btn.dataset.mode;

        modeToggle.querySelectorAll('button').forEach(b => {
            b.classList.toggle('btn-primary', b === btn);
            b.classList.toggle('btn-outline-primary', b !== btn);
        });

        criptoSelector.classList.toggle('d-none', modoAtual !== 'cripto');
        comumSelector.classList.toggle('d-none', modoAtual !== 'comum');

        infoText.textContent = modoAtual === 'cripto'
            ? 'Selecione um ativo para analisar o histórico e obter a previsão.'
            : 'Digite o nome de um produto para buscar o histórico e a previsão.';

        if (modoAtual === 'cripto') updateDashboard();
    });

    buscarProdutoBtn.addEventListener('click', () => updateDashboard());
    produtoInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') updateDashboard();
    });

    // ==================== API Calls ====================
    const fetchJSON = async (url) => {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.erro || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Erro em ${url}:`, error);
            return null;
        }
    };

    // ==================== Dashboard (Original) ====================
    const calcularSMA = (data, period) => {
        if (data.length < period) return null;
        let sum = 0;
        for (let i = data.length - period; i < data.length; i++) {
            sum += data[i].close;
        }
        return sum / period;
    };

    const renderChart = (historicalData, extemos = {}) => {
        const ctx = document.getElementById('priceChart').getContext('2d');
        const labels = historicalData.map(d => d.time);
        const prices = historicalData.map(d => d.close);

        if (priceChart) priceChart.destroy();

        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

        // Datasets de destaque (menor/maior valor), com apenas 1 ponto cada
        const auxiliarDatasets = [];

        // helper: monta um dataset de pontos nulos, com o extremo preenchido
        const criarDatasetPonto = (indice, cor) => {
            const pontos = prices.map(() => null);
            if (indice >= 0 && indice < prices.length) pontos[indice] = prices[indice];
            return {
                label: '',
                data: pontos,
                borderColor: cor,
                backgroundColor: cor,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBorderWidth: 2,
                pointBorderColor: '#0f172a',
                showLine: false,
                fill: false,
            };
        };

        let menorIdx = -1, maiorIdx = -1;
        if (extemos.menor_valor) {
            menorIdx = historicalData.findIndex(p => p.time === extemos.menor_valor.data);
            auxiliarDatasets.push(criarDatasetPonto(menorIdx, '#10b981'));
        }
        if (extemos.maior_valor) {
            maiorIdx = historicalData.findIndex(p => p.time === extemos.maior_valor.data);
            auxiliarDatasets.push(criarDatasetPonto(maiorIdx, '#ef4444'));
        }

        priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Preço de Fechamento',
                    data: prices,
                    borderColor: '#3b82f6',
                    backgroundColor: gradient,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.4,
                }, ...auxiliarDatasets]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        filter: (item) => item.raw !== null,
                        callbacks: {
                            label: (item) => {
                                if (item.datasetIndex === 0) {
                                    return ` Preço: ${formatPrice(item.raw)}`;
                                }
                                const isMenor = item.datasetIndex === (auxiliarDatasets[0] ? 1 : -1)
                                    && extemos.menor_valor;
                                const rotulo = isMenor ? 'Menor valor' : 'Maior valor';
                                return ` ${rotulo}: ${formatPrice(item.raw)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8', maxTicksLimit: 10 }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8' }
                    }
                },
                interaction: { mode: 'nearest', axis: 'x', intersect: false }
            }
        });
    };

    const renderPrevisao = (previsao) => {
        const { tendencia, confianca, raciocinio } = previsao;

        predictionGlow.className = `prediction-bg-glow ${tendencia}`;
        aiConfidenceEl.textContent = `Nível de Confiança: ${confianca}%`;
        technicalProgress.style.width = `${confianca}%`;
        aiReasoning.textContent = raciocinio;

        // Indicador de IA (OpenRouter) quando disponível
        const iaBadge = document.getElementById('aiModelBadge');
        if (iaBadge) {
            if (previsao.ia_gerado) {
                iaBadge.classList.remove('d-none');
                const nomeModelo = (previsao.modelo || 'IA').split('/').pop();
                iaBadge.innerHTML = `<i class="fa-solid fa-robot me-1"></i>${escapeHtml(nomeModelo)}`;
                iaBadge.title = `Modelo: ${previsao.modelo}`;
            } else {
                iaBadge.classList.add('d-none');
            }
        }

        if (tendencia === 'up') {
            aiIcon.innerHTML = '<i class="fa-solid fa-arrow-trend-up text-success" style="font-size: 3rem;"></i>';
            aiTrendEl.textContent = 'Tendência de Alta';
            aiTrendEl.className = 'fw-bold mb-2 gradient-text-up';
            technicalProgress.className = 'progress-bar bg-success';
        } else if (tendencia === 'down') {
            aiIcon.innerHTML = '<i class="fa-solid fa-arrow-trend-down text-danger" style="font-size: 3rem;"></i>';
            aiTrendEl.textContent = 'Tendência de Queda';
            aiTrendEl.className = 'fw-bold mb-2 gradient-text-down';
            technicalProgress.className = 'progress-bar bg-danger';
        } else {
            aiIcon.innerHTML = '<i class="fa-solid fa-minus text-warning" style="font-size: 3rem;"></i>';
            aiTrendEl.textContent = 'Mercado Estável / Lateral';
            aiTrendEl.className = 'fw-bold mb-2 gradient-text-stable';
            technicalProgress.className = 'progress-bar bg-warning';
        }
    };

    const mostrarEstadoCarregando = () => {
        currentPriceEl.textContent = 'Carregando...';
        priceChangeEl.textContent = '--';
        currentPriceEl.classList.remove('text-success', 'text-danger');
        priceChangeEl.classList.remove('text-success', 'text-danger');

        predictionGlow.className = 'prediction-bg-glow loading';
        aiIcon.innerHTML = '<div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;"></div>';
        aiTrendEl.textContent = 'Analisando Padrões...';
        aiTrendEl.className = 'fw-bold mb-2';
        aiConfidenceEl.textContent = 'Calculando convergência...';
        technicalProgress.className = 'progress-bar progress-bar-striped progress-bar-animated bg-primary';
        technicalProgress.style.width = '100%';
        aiReasoning.textContent = 'Consultando o backend de previsão...';
    };

    const updateDashboard = async () => {
        const produto = modoAtual === 'cripto' ? assetSelect.value : produtoInput.value.trim();
        if (modoAtual === 'comum' && !produto) return;

        const periodo = periodoSelect.value;

        mostrarEstadoCarregando();

        const [dadosHistorico, dadosPrevisao] = await Promise.all([
            fetchJSON(`${API_BASE}/historico?produto=${encodeURIComponent(produto)}&tipo=${modoAtual}&periodo=${periodo}`),
            fetchJSON(`${API_BASE}/previsao?produto=${encodeURIComponent(produto)}&tipo=${modoAtual}&periodo=${periodo}`),
        ]);

        if (dadosHistorico && dadosPrevisao) {
            currentPriceEl.textContent = formatPrice(dadosHistorico.preco_atual, modoAtual);

            const isPositive = dadosHistorico.variacao_24h >= 0;
            const changeSign = isPositive ? '+' : '';
            priceChangeEl.textContent = `${changeSign}${dadosHistorico.variacao_24h.toFixed(2)}% (24h)`;
            priceChangeEl.className = `text-muted mt-2 fw-medium mb-0 ${isPositive ? 'text-success' : 'text-danger'}`;

            if (modoAtual === 'comum') {
                infoText.textContent = `Histórico do ML — ${dadosHistorico.pontos_coletados} ponto(s). A série cresce a cada busca.`;
            }

            renderChart(dadosHistorico.historico, {
                menor_valor: dadosHistorico.menor_valor,
                maior_valor: dadosHistorico.maior_valor,
            });
            renderPrevisao(dadosPrevisao);

            // Mostra a data em que ocorreram o menor e o maior valor histórico
            if (dadosHistorico.menor_valor) {
                pvMenorData.textContent = `📅 ${dadosHistorico.menor_valor.data}`;
            }
            if (dadosHistorico.maior_valor) {
                pvMaiorData.textContent = `📅 ${dadosHistorico.maior_valor.data}`;
            }

            // Dashboard de valores atuais (somente no modo produto)
            if (modoAtual === 'comum') {
                carregarValoresProduto(produto);
            } else {
                produtoValores.classList.add('d-none');
                pvMenorData.textContent = '--';
                pvMaiorData.textContent = '--';
            }
        } else {
            currentPriceEl.textContent = 'Erro';
            priceChangeEl.textContent = 'Tente novamente';
            aiReasoning.textContent = 'Erro ao conectar com o backend. Rodando mock_backend.py?';
            produtoValores.classList.add('d-none');
        }
    };

    // ==================== Dashboard de Valores do Produto ====================
    const carregarValoresProduto = async (produto) => {
        // Usa o /api/historico (que já inclui estatisticas e resultados)
        // para manter consistência com o preço principal do dashboard.
        const periodo = parseInt(periodoSelect.value, 10) || 30;
        const dados = await fetchJSON(`${API_BASE}/historico?produto=${encodeURIComponent(produto)}&tipo=${modoAtual}&periodo=${periodo}`);

        if (!dados || !dados.estatisticas) {
            produtoValores.classList.add('d-none');
            return;
        }

        const s = dados.estatisticas;
        pvMenor.textContent = formatPrice(s.menor_preco);
        pvMaior.textContent = formatPrice(s.maior_preco);
        pvMedia.textContent = formatPrice(s.preco_medio);
        pvOfertas.textContent = dados.resultados ? dados.resultados.length : dados.pontos_coletados;
        pvFontes.textContent = '--';

        // Melhor oferta: primeiro resultado com preço
        const oferta = dados.resultados ? dados.resultados.find(r => r.preco != null) : null;
        if (oferta) {
            pvMelhorOferta.classList.remove('d-none');
            pvOfertaNome.textContent = oferta.nome || 'Produto';
            pvOfertaFonte.textContent = `${oferta.fonte || ''} · ${formatPrice(oferta.preco)}`;
            pvOfertaImg.src = oferta.thumbnail || '';
            pvOfertaImg.onerror = () => { pvOfertaImg.src = ''; };
            pvOfertaLink.href = oferta.permalink || '#';
        } else {
            pvMelhorOferta.classList.add('d-none');
        }

        produtoValores.classList.remove('d-none');
    };

    // Toggle "Só novos" recarrega o dashboard de valores
    soNovosToggle.addEventListener('change', () => {
        const produto = produtoInput.value.trim();
        if (produto) carregarValoresProduto(produto);
    });

    // Análise de preços com IA
    analiseIaBtn.addEventListener('click', async () => {
        const produto = produtoInput.value.trim();
        if (!produto) return;

        pvAnaliseIa.classList.remove('d-none');
        pvAnaliseTexto.textContent = 'Consultando a IA...';
        pvAnaliseModelo.textContent = '';
        pvAnaliseModelo.classList.remove('d-none');
        pvAnaliseModelo.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        const soNovos = soNovosToggle.checked;
        const dados = await fetchJSON(`${API_BASE}/analise-ia?produto=${encodeURIComponent(produto)}&limite=8&so_novos=${soNovos}`);

        if (!dados || !dados.analise) {
            pvAnaliseTexto.textContent = dados && !dados.ia_disponivel
                ? 'IA não configurada. Adicione OPENROUTER_API_KEY no .env para habilitar a análise.'
                : 'Não foi possível gerar a análise agora. Tente novamente.';
            pvAnaliseModelo.classList.add('d-none');
            return;
        }

        pvAnaliseTexto.textContent = dados.analise;
        const nomeModelo = (dados.modelo || 'IA').split('/').pop();
        pvAnaliseModelo.textContent = nomeModelo;
        pvAnaliseModelo.classList.remove('d-none');
    });

    assetSelect.addEventListener('change', updateDashboard);
    refreshBtn.addEventListener('click', updateDashboard);
    periodoSelect.addEventListener('change', updateDashboard);

    // ==================== Busca Ampliada ====================
    buscaAmpliadaBtn.addEventListener('click', async () => {
        const produto = buscaAmpliadaInput.value.trim();
        if (!produto) return;

        const limite = buscaLimite.value;
        buscaResultados.innerHTML = '<div class="col-12 search-loading"><div class="spinner-border text-primary mb-2"></div><p>Buscando produtos...</p></div>';
        buscaStats.classList.add('d-none');

        const dados = await fetchJSON(`${API_BASE}/buscar?produto=${encodeURIComponent(produto)}&limite=${limite}`);

        if (!dados) {
            buscaResultados.innerHTML = '<div class="col-12 text-center text-danger py-4"><p>Erro ao buscar produtos</p></div>';
            return;
        }

        // Stats
        if (dados.estatisticas) {
            const s = dados.estatisticas;
            document.getElementById('statMenor').textContent = formatPrice(s.menor_preco);
            document.getElementById('statMaior').textContent = formatPrice(s.maior_preco);
            document.getElementById('statMedia').textContent = formatPrice(s.preco_medio);
            // Mostrar fontes consultadas
            const fontesUsadas = Object.keys(dados.por_fonte || {}).join(', ');
            document.getElementById('statFrete').textContent = fontesUsadas || '--';
            buscaStats.classList.remove('d-none');
        }

        // Resultados
        if (!dados.resultados || dados.resultados.length === 0) {
            buscaResultados.innerHTML = '<div class="col-12 text-center text-secondary py-4"><p>Nenhum resultado encontrado</p></div>';
            return;
        }

        buscaResultados.innerHTML = dados.resultados.map(r => {
            const desconto = r.preco_original && r.preco
                ? Math.round((1 - r.preco / r.preco_original) * 100)
                : 0;

            // Cor da badge conforme fonte
            const fonteCores = {
                'Americanas': 'primary',
                'KaBuM': 'danger',
                'Samsung': 'info',
                'Mercado Livre': 'warning',
                'Buscapé': 'success',
                'Zoom': 'warning',
                'Google Shopping': 'secondary',
                'Google': 'light',
            };
            const fonteCor = fonteCores[r.fonte] || 'secondary';

            const nomeExibido = r.nome
                ? (r.nome.length > 60 ? r.nome.substring(0, 60) + '...' : r.nome)
                : 'Sem nome';

            return `
                <div class="col-md-6 col-lg-4">
                    <div class="product-card position-relative" data-permalink="${escapeHtml(r.permalink || '')}">
                        ${desconto > 0 ? `<span class="discount-badge">-${desconto}%</span>` : ''}
                        <div class="d-flex gap-3">
                            <img src="${escapeHtml(r.thumbnail || '')}" class="product-thumb" alt="${escapeHtml(r.nome || '')}" loading="lazy"
                                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2280%22 height=%2280%22><rect fill=%22%23334155%22 width=%2280%22 height=%2280%22/><text fill=%22%2364748b%22 x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-size=%2214%22>IMG</text></svg>'">
                            <div class="flex-grow-1">
                                <h6 class="mb-1 text-white" style="font-size: 0.85rem; line-height: 1.3;">
                                    ${escapeHtml(nomeExibido)}
                                </h6>
                                <div class="mb-1">
                                    <span class="product-price">${formatPrice(r.preco)}</span>
                                    ${r.preco_original ? `<span class="product-original-price">${formatPrice(r.preco_original)}</span>` : ''}
                                </div>
                                <div class="d-flex gap-2 flex-wrap">
                                    <span class="badge bg-${fonteCor} bg-opacity-25 text-${fonteCor} border border-${fonteCor} border-opacity-50" style="font-size: 0.7rem;">
                                        <i class="fa-solid fa-store me-1"></i>${escapeHtml(r.fonte || 'Loja')}
                                    </span>
                                    ${r.frete_gratis ? '<span class="badge badge-frete"><i class="fa-solid fa-truck me-1"></i>Frete Grátis</span>' : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Abre o link do produto ao clicar no card. Antes isso era um
        // onclick inline com o permalink interpolado direto na string
        // ("onclick=\"window.open('${r.permalink}')\""), o que permite
        // que uma fonte externa maliciosa injete JavaScript arbitrário
        // (ex.: um permalink terminado em algo como `');alert(1);//`
        // fecharia a string e executaria código). Ler de data-permalink
        // evita esse vetor por completo.
        buscaResultados.querySelectorAll('.product-card[data-permalink]').forEach((card) => {
            card.addEventListener('click', () => {
                const url = card.dataset.permalink;
                if (url) window.open(url, '_blank', 'noopener,noreferrer');
            });
        });
    });

    buscaAmpliadaInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') buscaAmpliadaBtn.click();
    });

    // ==================== Comparação ====================
    compararBtn.addEventListener('click', async () => {
        const termos = compararInput.value.trim();
        if (!termos) return;

        compararResultados.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-warning mb-2"></div><p>Comparando preços...</p></div>';

        const dados = await fetchJSON(`${API_BASE}/comparar?termos=${encodeURIComponent(termos)}`);

        if (!dados || !dados.comparacao) {
            compararResultados.innerHTML = '<div class="text-center text-danger py-4"><p>Erro ao comparar</p></div>';
            return;
        }

        compararResultados.innerHTML = dados.comparacao.map(c => {
            if (c.erro) {
                return `<div class="col-md-4"><div class="compare-card"><div class="compare-header">${escapeHtml(c.termo)}</div><p class="text-danger">${escapeHtml(c.erro)}</p></div></div>`;
            }

            const fontesBadge = (c.fontes || []).map(f => {
                const cores = { 'Americanas': 'primary', 'KaBuM': 'danger', 'Samsung': 'info', 'Mercado Livre': 'warning', 'Buscapé': 'success', 'Zoom': 'warning', 'Google Shopping': 'secondary', 'Google': 'light' };
                const cor = cores[f] || 'secondary';
                return `<span class="badge bg-${cor} bg-opacity-25 text-${cor} border border-${cor} border-opacity-50 me-1" style="font-size: 0.65rem;">${escapeHtml(f)}</span>`;
            }).join('');

            const nomeTop = c.top_resultado && c.top_resultado.nome
                ? (c.top_resultado.nome.length > 50 ? c.top_resultado.nome.substring(0, 50) + '...' : c.top_resultado.nome)
                : '';

            return `
                <div class="col-md-4">
                    <div class="compare-card">
                        <div class="compare-header text-white">${escapeHtml(c.termo)}</div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="compare-price text-success">${formatPrice(c.menor_preco)}</span>
                            <small class="text-secondary">${c.resultados} resultados</small>
                        </div>
                        ${c.preco_medio ? `<small class="text-secondary">Média: ${formatPrice(c.preco_medio)}</small>` : ''}
                        <div class="mt-2">${fontesBadge}</div>
                        ${c.top_resultado ? `
                            <hr class="border-secondary my-2">
                            <small class="text-muted d-block mb-1" style="font-size: 0.8rem;">
                                ${escapeHtml(nomeTop)}
                            </small>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="fw-bold">${formatPrice(c.top_resultado.preco)}</span>
                                <a href="#" data-permalink="${escapeHtml(c.top_resultado.permalink || '')}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-primary compare-link">
                                    <i class="fa-solid fa-external-link-alt"></i>
                                </a>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');

        compararResultados.querySelectorAll('a.compare-link[data-permalink]').forEach((link) => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const url = link.dataset.permalink;
                if (url) window.open(url, '_blank', 'noopener,noreferrer');
            });
        });
    });

    compararInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') compararBtn.click();
    });

    // ==================== Alertas ====================
    const carregarAlertas = async () => {
        const dados = await fetchJSON(`${API_BASE}/alertas`);
        if (!dados || !dados.alertas) return;

        if (dados.alertas.length === 0) {
            alertasLista.innerHTML = '<div class="text-center text-secondary py-4"><i class="fa-solid fa-bell-slash fa-3x mb-3 opacity-25"></i><p>Nenhum alerta configurado</p></div>';
            alertasAtivados.classList.add('d-none');
            return;
        }

        const ativos = dados.alertas.filter(a => a.ativo);
        const outros = dados.alertas.filter(a => !a.ativo);

        // Lista principal
        alertasLista.innerHTML = ativos.map(a => `
            <div class="alerta-card ativado">
                <div>
                    <span class="alerta-produto">${escapeHtml(a.produto)}</span>
                    <span class="text-secondary ms-2">
                        ${a.condicao === 'menor' ? '< Preço menor que' : '> Preço maior que'}
                        <span class="alerta-preco ms-1">${formatPrice(a.preco_alvo)}</span>
                    </span>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-danger" data-alerta-id="${a.id}">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('') || '<div class="text-center text-secondary py-3"><p>Nenhum alerta ativo</p></div>';

        alertasLista.querySelectorAll('button[data-alerta-id]').forEach((btn) => {
            btn.addEventListener('click', () => deletarAlerta(Number(btn.dataset.alertaId)));
        });

        // Verificar alertas atingidos
        const verificados = await fetchJSON(`${API_BASE}/alertas/verificar`);
        if (verificados && verificados.atingidos && verificados.atingidos.length > 0) {
            alertasAtivados.classList.remove('d-none');
            alertasAtivadosLista.innerHTML = verificados.atingidos.map(a => `
                <div class="alerta-card" style="border-color: var(--success-color);">
                    <div>
                        <span class="alerta-produto text-success">${escapeHtml(a.produto)}</span>
                        <span class="ms-2">
                            Preço atual: <strong class="text-success">${formatPrice(a.preco_atual)}</strong>
                            ${a.condicao === 'menor' ? '≤' : '≥'} <span class="alerta-preco">${formatPrice(a.preco_alvo)}</span>
                        </span>
                    </div>
                    <span class="badge bg-success"><i class="fa-solid fa-check me-1"></i>Ativado</span>
                </div>
            `).join('');
        } else {
            alertasAtivados.classList.add('d-none');
        }
    };

    criarAlertaBtn.addEventListener('click', async () => {
        const produto = alertaProduto.value.trim();
        const preco = alertaPreco.value;
        const condicao = alertaCondicao.value;

        if (!produto || !preco) {
            alert('Preencha produto e preço alvo');
            return;
        }

        const resp = await fetch(`${API_BASE}/alertas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ produto, preco_alvo: parseFloat(preco), condicao }),
        });

        if (resp.ok) {
            alertaProduto.value = '';
            alertaPreco.value = '';
            carregarAlertas();
        } else {
            const err = await resp.json().catch(() => ({}));
            alert(err.erro || 'Erro ao criar alerta');
        }
    });

    // Função global para deletar alerta
    window.deletarAlerta = async (id) => {
        if (!confirm('Remover este alerta?')) return;
        await fetch(`${API_BASE}/alertas/${id}`, { method: 'DELETE' });
        carregarAlertas();
    };

    // ==================== Histórico de Buscas ====================
    const carregarHistorico = async () => {
        const dados = await fetchJSON(`${API_BASE}/historico-buscas?limite=20`);
        if (!dados || !dados.buscas || dados.buscas.length === 0) {
            historicoLista.innerHTML = '<div class="text-center text-secondary py-4"><i class="fa-solid fa-inbox fa-3x mb-3 opacity-25"></i><p>Nenhuma busca registrada ainda</p></div>';
            return;
        }

        historicoLista.innerHTML = dados.buscas.map(b => `
            <div class="historico-item">
                <div>
                    <span class="text-white fw-medium">${escapeHtml(b.produto)}</span>
                    <span class="badge bg-secondary ms-2">${escapeHtml(b.fonte || 'mercado_livre')}</span>
                </div>
                <small class="text-secondary">${formatDate(b.data)}</small>
            </div>
        `).join('');
    };

    // ==================== Init ====================
    updateDashboard();
});
