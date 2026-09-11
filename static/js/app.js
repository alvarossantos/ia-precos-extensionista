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

    // ==================== State ====================
    let priceChart = null;
    let modoAtual = 'cripto';
    const API_BASE = `${window.location.origin}/api`;

    // ==================== Utils ====================
    const escapeHtml = (valor) => {
        if (valor == null) return '';
        return String(valor).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    };

    const formatPrice = (price) => {
        if (price == null) return '--';
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(price);
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '--';
        const d = new Date(dateStr);
        return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    };

    const fetchJSON = async (url) => {
        try {
            const response = await fetch(url);
            if (!response.ok) return null;
            return await response.json();
        } catch { return null; }
    };

    // ==================== Tabs ====================
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.add('d-none'));
            document.getElementById(`tab-${btn.dataset.tab}`).classList.remove('d-none');
        });
    });

    // ==================== Mode Toggle ====================
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
    produtoInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') updateDashboard(); });

    // ==================== Chart ====================
    const renderChart = (historicalData, extemos = {}) => {
        const ctx = document.getElementById('priceChart').getContext('2d');
        const labels = historicalData.map(d => d.time);
        const prices = historicalData.map(d => d.close);

        if (priceChart) priceChart.destroy();

        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

        const criarDatasetPonto = (indice, cor) => {
            const pontos = prices.map(() => null);
            if (indice >= 0 && indice < prices.length) pontos[indice] = prices[indice];
            return { label: '', data: pontos, borderColor: cor, backgroundColor: cor, pointRadius: 6, pointHoverRadius: 8, pointBorderWidth: 2, pointBorderColor: '#0f172a', showLine: false, fill: false };
        };

        const auxiliarDatasets = [];
        if (extemos.menor_valor) auxiliarDatasets.push(criarDatasetPonto(historicalData.findIndex(p => p.time === extemos.menor_valor.data), '#10b981'));
        if (extemos.maior_valor) auxiliarDatasets.push(criarDatasetPonto(historicalData.findIndex(p => p.time === extemos.maior_valor.data), '#ef4444'));

        priceChart = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets: [{ label: 'Preço de Fechamento', data: prices, borderColor: '#3b82f6', backgroundColor: gradient, borderWidth: 2, pointRadius: 0, pointHoverRadius: 6, fill: true, tension: 0.4 }, ...auxiliarDatasets] },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false, backgroundColor: 'rgba(15, 23, 42, 0.9)', titleColor: '#fff', bodyColor: '#fff', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, filter: (item) => item.raw !== null, callbacks: { label: (item) => item.datasetIndex === 0 ? ` Preço: ${formatPrice(item.raw)}` : ` ${item.datasetIndex === 1 ? 'Menor' : 'Maior'} valor: ${formatPrice(item.raw)}` } } },
                scales: { x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', maxTicksLimit: 10 } }, y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } } },
                interaction: { mode: 'nearest', axis: 'x', intersect: false }
            }
        });
    };

    // ==================== Previsão ====================
    const renderPrevisao = (previsao) => {
        const { tendencia, confianca, raciocinio } = previsao;
        predictionGlow.className = `prediction-bg-glow ${tendencia}`;
        aiConfidenceEl.textContent = `Nível de Confiança: ${confianca}%`;
        technicalProgress.style.width = `${confianca}%`;
        aiReasoning.textContent = raciocinio;

        const iaBadge = document.getElementById('aiModelBadge');
        if (iaBadge) {
            if (previsao.ia_gerado) { iaBadge.classList.remove('d-none'); iaBadge.innerHTML = `<i class="fa-solid fa-robot me-1"></i>${escapeHtml((previsao.modelo || 'IA').split('/').pop())}`; iaBadge.title = `Modelo: ${previsao.modelo}`; }
            else { iaBadge.classList.add('d-none'); }
        }

        if (tendencia === 'up') { aiIcon.innerHTML = '<i class="fa-solid fa-arrow-trend-up text-success" style="font-size: 3rem;"></i>'; aiTrendEl.textContent = 'Tendência de Alta'; aiTrendEl.className = 'fw-bold mb-2 gradient-text-up'; technicalProgress.className = 'progress-bar bg-success'; }
        else if (tendencia === 'down') { aiIcon.innerHTML = '<i class="fa-solid fa-arrow-trend-down text-danger" style="font-size: 3rem;"></i>'; aiTrendEl.textContent = 'Tendência de Queda'; aiTrendEl.className = 'fw-bold mb-2 gradient-text-down'; technicalProgress.className = 'progress-bar bg-danger'; }
        else { aiIcon.innerHTML = '<i class="fa-solid fa-minus text-warning" style="font-size: 3rem;"></i>'; aiTrendEl.textContent = 'Mercado Estável / Lateral'; aiTrendEl.className = 'fw-bold mb-2 gradient-text-stable'; technicalProgress.className = 'progress-bar bg-warning'; }
    };

    // ==================== Dashboard ====================
    const mostrarEstadoCarregando = () => {
        currentPriceEl.textContent = 'Carregando...'; priceChangeEl.textContent = '--';
        currentPriceEl.classList.remove('text-success', 'text-danger'); priceChangeEl.classList.remove('text-success', 'text-danger');
        predictionGlow.className = 'prediction-bg-glow loading';
        aiIcon.innerHTML = '<div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;"></div>';
        aiTrendEl.textContent = 'Analisando Padrões...'; aiTrendEl.className = 'fw-bold mb-2';
        aiConfidenceEl.textContent = 'Calculando convergência...';
        technicalProgress.className = 'progress-bar progress-bar-striped progress-bar-animated bg-primary'; technicalProgress.style.width = '100%';
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
            currentPriceEl.textContent = formatPrice(dadosHistorico.preco_atual);
            const isPositive = dadosHistorico.variacao_24h >= 0;
            priceChangeEl.textContent = `${isPositive ? '+' : ''}${dadosHistorico.variacao_24h.toFixed(2)}% (24h)`;
            priceChangeEl.className = `text-muted mt-2 fw-medium mb-0 ${isPositive ? 'text-success' : 'text-danger'}`;

            if (modoAtual === 'comum') {
                const pontos = dadosHistorico.pontos_coletados;
                const est = dadosHistorico.estatisticas || {};
                let info = `${pontos} ponto(s) no histórico`;
                if (est.menor_preco && est.maior_preco) { info += ` | Faixa: R$ ${est.menor_preco.toFixed(2)} a R$ ${est.maior_preco.toFixed(2)}`; }
                if (pontos < 5) info += ' | Consulte novamente mais tarde para ver tendências';
                infoText.textContent = info;
            }

            renderChart(dadosHistorico.historico, { menor_valor: dadosHistorico.menor_valor, maior_valor: dadosHistorico.maior_valor });
            renderPrevisao(dadosPrevisao);

            if (dadosHistorico.menor_valor) pvMenorData.textContent = dadosHistorico.menor_valor.data;
            if (dadosHistorico.maior_valor) pvMaiorData.textContent = dadosHistorico.maior_valor.data;

            if (modoAtual === 'comum') carregarValoresProduto(produto);
            else { produtoValores.classList.add('d-none'); pvMenorData.textContent = '--'; pvMaiorData.textContent = '--'; }
        } else {
            currentPriceEl.textContent = 'Erro'; priceChangeEl.textContent = 'Tente novamente';
            aiReasoning.textContent = 'Erro ao conectar com o backend.'; produtoValores.classList.add('d-none');
        }
    };

    // ==================== Dashboard de Valores ====================
    const carregarValoresProduto = async (produto) => {
        const periodo = parseInt(periodoSelect.value, 10) || 30;
        const dados = await fetchJSON(`${API_BASE}/historico?produto=${encodeURIComponent(produto)}&tipo=${modoAtual}&periodo=${periodo}`);
        if (!dados || !dados.estatisticas) { produtoValores.classList.add('d-none'); return; }

        const s = dados.estatisticas;
        pvMenor.textContent = formatPrice(s.menor_preco); pvMaior.textContent = formatPrice(s.maior_preco);
        pvMedia.textContent = formatPrice(s.preco_medio); pvOfertas.textContent = dados.resultados ? dados.resultados.length : dados.pontos_coletados;
        pvFontes.textContent = '--';

        const oferta = dados.resultados ? dados.resultados.find(r => r.preco != null) : null;
        if (oferta) {
            pvMelhorOferta.classList.remove('d-none'); pvOfertaNome.textContent = oferta.nome || 'Produto';
            pvOfertaFonte.textContent = `${oferta.fonte || ''} · ${formatPrice(oferta.preco)}`;
            pvOfertaImg.src = oferta.thumbnail || ''; pvOfertaImg.onerror = () => { pvOfertaImg.src = ''; };
            pvOfertaLink.href = oferta.permalink || '#';
        } else { pvMelhorOferta.classList.add('d-none'); }

        produtoValores.classList.remove('d-none');
    };

    soNovosToggle.addEventListener('change', () => {
        const produto = produtoInput.value.trim();
        if (produto) carregarValoresProduto(produto);
    });

    // Análise de preços com IA
    analiseIaBtn.addEventListener('click', async () => {
        const produto = produtoInput.value.trim();
        if (!produto) return;
        pvAnaliseIa.classList.remove('d-none'); pvAnaliseTexto.textContent = 'Consultando a IA...';
        pvAnaliseModelo.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; pvAnaliseModelo.classList.remove('d-none');

        const soNovos = soNovosToggle.checked;
        const dados = await fetchJSON(`${API_BASE}/analise-ia?produto=${encodeURIComponent(produto)}&limite=8&so_novos=${soNovos}`);
        if (!dados || !dados.analise) {
            pvAnaliseTexto.textContent = dados && !dados.ia_disponivel ? 'IA não configurada.' : 'Não foi possível gerar a análise.';
            pvAnaliseModelo.classList.add('d-none'); return;
        }
        pvAnaliseTexto.textContent = dados.analise;
        pvAnaliseModelo.textContent = (dados.modelo || 'IA').split('/').pop();
        pvAnaliseModelo.classList.remove('d-none');
    });

    assetSelect.addEventListener('change', updateDashboard);
    refreshBtn.addEventListener('click', updateDashboard);
    periodoSelect.addEventListener('change', updateDashboard);

    // ==================== Init ====================
    updateDashboard();
});
