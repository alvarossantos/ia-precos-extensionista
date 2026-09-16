/* DashboardTab — Cripto/Produto dashboard with Chart.js + AI prediction */
import { API_BASE, fetchJSON, formatPrice } from '../api.js';
import { UserStore } from '../userStore.js';

export const DashboardTab = {
  template: `
    <div>
      <div class="row g-4 mb-4">
        <!-- Ativo Selector -->
        <div class="col-lg-5">
          <div class="glass-card h-100 p-4 d-flex flex-column justify-content-between">
            <div>
              <div class="d-flex justify-content-between align-items-center mb-3 dashboard-header">
                <h5 class="fw-semibold mb-0 text-white">
                  <i class="fa-solid fa-coins me-2 text-warning"></i>Ativo Selecionado
                </h5>
                <div class="btn-group btn-group-sm">
                  <button type="button" class="btn" :class="modo === 'cripto' ? 'btn-primary' : 'btn-outline-primary'"
                          @click="setModo('cripto')">Cripto</button>
                  <button type="button" class="btn" :class="modo === 'comum' ? 'btn-primary' : 'btn-outline-primary'"
                          @click="setModo('comum')">Produto</button>
                </div>
              </div>

              <!-- Cripto selector -->
              <div v-if="modo === 'cripto'" class="mb-2">
                <select v-model="asset" class="form-select bg-dark text-white border-secondary w-100 shadow-sm">
                  <option v-for="a in assets" :key="a.value" :value="a.value">{{ a.label }}</option>
                </select>
              </div>

              <!-- Produto selector -->
              <div v-else class="mb-2">
                <div class="input-group">
                  <input type="text" v-model="produtoInput" class="form-control bg-dark text-white border-secondary"
                         placeholder="Ex: iPhone 15, PS5, Notebook Dell..."
                         @keydown.enter="updateDashboard"
                         :disabled="loading">
                  <button class="btn btn-primary" @click="updateDashboard" type="button" :disabled="loading">
                    <i v-if="loading" class="fa-solid fa-spinner fa-spin"></i>
                    <i v-else class="fa-solid fa-magnifying-glass"></i>
                  </button>
                </div>
                <div v-if="errorMsg" class="alert alert-danger mt-2 mb-0 py-2" style="font-size:0.85rem;">
                  <i class="fa-solid fa-circle-exclamation me-1"></i>{{ errorMsg }}
                </div>
              </div>

              <div class="text-center my-4">
                <h2 class="display-4 fw-bold mb-0 lh-1" :class="priceColor">{{ currentPrice }}</h2>
                <p class="text-muted mt-2 fw-medium mb-0" :class="changeColor">{{ priceChange }}</p>
              </div>
            </div>

            <div class="alert alert-secondary bg-transparent border-secondary text-light mt-3 mb-0" role="alert">
              <i class="fa-solid fa-circle-info text-info me-2"></i>
              <span>{{ infoText }}</span>
            </div>
          </div>
        </div>

        <!-- AI Prediction -->
        <div class="col-lg-7">
          <div class="glass-card h-100 p-4 position-relative overflow-hidden">
            <div class="prediction-bg-glow" :class="trendClass"></div>

            <div class="d-flex justify-content-between align-items-start mb-4 position-relative z-1">
              <h5 class="fw-semibold mb-0 text-white">
                <i class="fa-solid fa-wand-magic-sparkles me-2 text-primary"></i>Previsão da IA
              </h5>
              <div class="d-flex gap-2">
                <span v-if="previsao.modelo" class="badge bg-success" title="Raciocínio gerado por IA">
                  <i class="fa-solid fa-robot me-1"></i>{{ shortModel }}
                </span>
                <span class="badge bg-dark border border-secondary text-light">
                  <i class="fa-regular fa-clock me-1"></i>Curto Prazo
                </span>
              </div>
            </div>

            <div class="text-center position-relative z-1 my-3">
              <div class="mb-3">
                <i v-if="previsao.tendencia === 'up'" class="fa-solid fa-arrow-trend-up text-success" style="font-size: 3rem;"></i>
                <i v-else-if="previsao.tendencia === 'down'" class="fa-solid fa-arrow-trend-down text-danger" style="font-size: 3rem;"></i>
                <i v-else class="fa-solid fa-minus text-warning" style="font-size: 3rem;"></i>
              </div>
              <h2 class="fw-bold mb-2" :class="'gradient-text-' + (previsao.tendencia || 'stable')">{{ trendLabel }}</h2>
              <p class="text-muted fs-5 mb-0">Nível de Confiança: {{ previsao.confianca || '--' }}%</p>
            </div>

            <div class="mt-4 position-relative z-1">
              <div class="d-flex justify-content-between mb-1">
                <small class="text-secondary fw-semibold">Indicadores Técnicos</small>
                <small class="text-secondary fw-semibold">Alinhamento</small>
              </div>
              <div class="progress" style="height: 10px;">
                <div class="progress-bar" :class="progressClass" role="progressbar"
                     :style="{ width: (previsao.confianca || 0) + '%' }"></div>
              </div>
              <div class="mt-3 text-center">
                <small class="text-light opacity-75">{{ previsao.raciocinio || 'Coletando dados históricos para inferência...' }}</small>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Chart -->
      <div class="row">
        <div class="col-12">
          <div class="glass-card p-4">
            <div class="d-flex justify-content-between align-items-center mb-4 chart-header">
              <h5 class="fw-semibold mb-0 text-white">
                <i class="fa-solid fa-chart-line me-2 text-info"></i>Histórico de Preços
              </h5>
              <div class="d-flex align-items-center gap-2">
                <select v-model.number="periodo" class="form-select form-select-sm bg-dark text-white border-secondary" style="width: auto;">
                  <option :value="7">7 dias</option>
                  <option :value="30">30 dias</option>
                  <option :value="90">3 meses</option>
                  <option :value="180">6 meses</option>
                  <option :value="365">1 ano</option>
                </select>
                <button class="btn btn-sm btn-outline-primary" @click="updateDashboard" :disabled="loading">
                  <i v-if="loading" class="fa-solid fa-spinner fa-spin me-1"></i>
                  <i v-else class="fa-solid fa-rotate-right me-1"></i>{{ loading ? 'Carregando...' : 'Atualizar' }}
                </button>
              </div>
            </div>
            <div class="chart-container" style="position: relative; height:400px; width:100%">
              <canvas ref="chartCanvas"></canvas>
            </div>
          </div>
        </div>
      </div>

      <!-- Produto Dashboard -->
      <div v-if="modo === 'comum' && historico" class="row mt-4">
        <div class="col-12">
          <div class="glass-card p-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
              <h5 class="fw-semibold mb-0 text-white">
                <i class="fa-solid fa-tags me-2 text-success"></i>Valores Atuais do Produto
              </h5>
              <div class="d-flex flex-wrap align-items-center gap-2">
                <div class="form-check form-switch mb-0">
                  <input class="form-check-input" type="checkbox" id="soNovosToggle" v-model="soNovos">
                  <label class="form-check-label text-secondary" for="soNovosToggle">Só novos</label>
                </div>
                <button class="btn btn-sm btn-outline-info" @click="analiseIa" :disabled="loadingIa">
                  <i class="fa-solid fa-robot me-1"></i>{{ loadingIa ? 'Analisando...' : 'Analisar com IA' }}
                </button>
                <span class="badge bg-success bg-opacity-25 text-success border border-success border-opacity-50">
                  <i class="fa-solid fa-store me-1"></i>{{ fontesCount }}
                </span>
              </div>
            </div>

            <div class="row g-2 g-md-3 mb-3 stats-grid">
              <div class="col-6 col-md-3">
                <div class="glass-card text-center h-100">
                  <span class="stat-label"><i class="fa-solid fa-arrow-down text-success me-1"></i>Menor Preço</span>
                  <span class="stat-value text-success">{{ formatPrice(stats.menor_preco) }}</span>
                  <span class="stat-sub">{{ historico?.menor_valor?.data || '--' }}</span>
                </div>
              </div>
              <div class="col-6 col-md-3">
                <div class="glass-card text-center h-100">
                  <span class="stat-label"><i class="fa-solid fa-arrow-up text-danger me-1"></i>Maior Preço</span>
                  <span class="stat-value text-danger">{{ formatPrice(stats.maior_preco) }}</span>
                  <span class="stat-sub">{{ historico?.maior_valor?.data || '--' }}</span>
                </div>
              </div>
              <div class="col-6 col-md-3">
                <div class="glass-card text-center h-100">
                  <span class="stat-label"><i class="fa-solid fa-chart-column text-primary me-1"></i>Preço Médio</span>
                  <span class="stat-value text-primary">{{ formatPrice(stats.preco_medio) }}</span>
                </div>
              </div>
              <div class="col-6 col-md-3">
                <div class="glass-card text-center h-100">
                  <span class="stat-label"><i class="fa-solid fa-box-open text-warning me-1"></i>Ofertas</span>
                  <span class="stat-value text-warning">{{ ofertasCount }}</span>
                </div>
              </div>
            </div>

            <!-- Best offer -->
            <div v-if="melhorOferta" class="glass-card p-3">
              <small class="text-secondary d-block mb-2"><i class="fa-solid fa-crown text-warning me-1"></i>Melhor Oferta</small>
              <div class="d-flex align-items-center gap-3 melhor-oferta-row">
                <img v-if="melhorOferta.thumbnail" :src="melhorOferta.thumbnail" class="product-thumb"
                     style="width:48px;height:48px;object-fit:cover;border-radius:6px;" alt="oferta">
                <div class="flex-grow-1">
                  <p class="mb-0 text-white" style="font-size:0.85rem;line-height:1.3;">{{ melhorOferta.nome }}</p>
                  <small class="text-secondary">{{ melhorOferta.fonte }} · {{ formatPrice(melhorOferta.preco) }}</small>
                </div>
                <a v-if="melhorOferta.permalink" :href="melhorOferta.permalink" target="_blank" class="btn btn-sm btn-outline-success">
                  <i class="fa-solid fa-external-link-alt me-1"></i>Ver
                </a>
              </div>
            </div>

            <!-- IA Analysis -->
            <div v-if="analise" class="glass-card p-3 mt-3" style="border-left: 4px solid var(--info-color);">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <small class="text-info fw-semibold">
                  <i class="fa-solid fa-robot me-1"></i>Análise de Preços com IA
                </small>
                <span v-if="analise.modelo" class="badge bg-info bg-opacity-25 text-info border border-info" style="font-size:0.65rem;">
                  {{ shortAnaliseModel }}
                </span>
              </div>
              <p class="mb-0 text-light opacity-90" style="font-size:0.9rem;line-height:1.5;">{{ analise.analise }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,

  data() {
    return {
      modo: 'cripto',
      asset: 'BTCUSDT',
      assets: [
        { value: 'BTCUSDT', label: 'Bitcoin (BTC)' },
        { value: 'ETHUSDT', label: 'Ethereum (ETH)' },
        { value: 'BNBUSDT', label: 'Binance Coin (BNB)' },
        { value: 'SOLUSDT', label: 'Solana (SOL)' },
        { value: 'ADAUSDT', label: 'Cardano (ADA)' },
        { value: 'DOGEUSDT', label: 'Dogecoin (DOGE)' },
        { value: 'XRPUSDT', label: 'XRP (XRP)' },
      ],
      produtoInput: '',
      periodo: 30,
      soNovos: false,
      currentPrice: 'Carregando...',
      priceChange: '--',
      historico: null,
      previsao: {},
      analise: null,
      loading: false,
      loadingIa: false,
      errorMsg: '',
      priceChart: null,
    };
  },

  computed: {
    stats() { return this.historico?.estatisticas || {}; },
    ofertasCount() { return this.historico?.resultados?.length || this.historico?.pontos_coletados || 0; },
    fontesCount() {
      if (!this.historico?.resultados) return '--';
      const f = new Set(this.historico.resultados.map(r => r.fonte));
      return f.size + ' fonte(s)';
    },
    melhorOferta() {
      if (!this.historico?.resultados) return null;
      return this.historico.resultados.find(r => r.preco != null) || null;
    },
    infoText() {
      return this.modo === 'cripto'
        ? 'Selecione um ativo para analisar o histórico e obter a previsão.'
        : 'Digite o nome de um produto para buscar o histórico e a previsão.';
    },
    currentProduto() {
      return this.modo === 'cripto' ? this.asset : this.produtoInput.trim();
    },
    shortModel() { return (this.previsao.modelo || '').split('/').pop(); },
    shortAnaliseModel() { return (this.analise?.modelo || '').split('/').pop(); },
    trendClass() {
      return this.historico ? (this.previsao.tendencia || 'loading') : 'loading';
    },
    trendLabel() {
      const t = this.previsao.tendencia;
      if (t === 'up') return 'Tendência de Alta';
      if (t === 'down') return 'Tendência de Queda';
      return 'Mercado Estável / Lateral';
    },
    progressClass() {
      const t = this.previsao.tendencia;
      if (t === 'up') return 'bg-success';
      if (t === 'down') return 'bg-danger';
      return 'bg-warning';
    },
    priceColor() { return ''; },
    changeColor() {
      if (!this.historico) return '';
      return this.historico.variacao_24h >= 0 ? 'text-success' : 'text-danger';
    },
  },

  watch: {
    asset() { this.updateDashboard(); },
    periodo() { this.updateDashboard(); },
  },

  methods: {
    setModo(m) {
      this.modo = m;
      if (m === 'cripto') this.updateDashboard();
    },

    async updateDashboard() {
      const produto = this.currentProduto;
      if (this.modo === 'comum' && !produto) return;

      this.loading = true;
      this.errorMsg = '';
      console.log('[Dashboard] updateDashboard:', { produto, modo: this.modo, periodo: this.periodo });

      try {
        const [h, p] = await Promise.all([
          fetchJSON(`${API_BASE}/historico?produto=${encodeURIComponent(produto)}&tipo=${this.modo}&periodo=${this.periodo}`),
          fetchJSON(`${API_BASE}/previsao?produto=${encodeURIComponent(produto)}&tipo=${this.modo}&periodo=${this.periodo}`),
        ]);

        console.log('[Dashboard] historico:', h ? `${h.resultados?.length || 0} resultados` : 'NULL');
        console.log('[Dashboard] previsao:', p ? p.tendencia : 'NULL');

        if (h && !h.erro) {
          this.historico = h;
          this.currentPrice = formatPrice(h.preco_atual);
          const v = h.variacao_24h || 0;
          this.priceChange = `${v >= 0 ? '+' : ''}${v.toFixed(2)}% (24h)`;
          if (this.modo === 'comum') UserStore.salvarBusca(produto);
          this.$nextTick(() => this.renderChart(h.historico, { menor_valor: h.menor_valor, maior_valor: h.maior_valor }));
        } else {
          this.currentPrice = 'Erro';
          this.priceChange = h?.erro || 'Tente novamente';
          this.errorMsg = h?.erro || 'Nenhum resultado encontrado para este produto.';
        }

        this.previsao = p || {};
      } catch (e) {
        console.error('[Dashboard] Erro inesperado:', e);
        this.currentPrice = 'Erro';
        this.priceChange = 'Falha na requisição';
        this.errorMsg = 'Erro de conexão. Verifique o console (F12).';
      } finally {
        this.loading = false;
      }
    },

    renderChart(data, extremos = {}) {
      if (!this.$refs.chartCanvas || !data?.length) return;
      const ctx = this.$refs.chartCanvas.getContext('2d');
      const labels = data.map(d => d.time);
      const prices = data.map(d => d.close);

      if (this.priceChart) this.priceChart.destroy();

      const gradient = ctx.createLinearGradient(0, 0, 0, 400);
      gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
      gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

      const mkDot = (idx, color) => {
        const pts = prices.map(() => null);
        if (idx >= 0 && idx < prices.length) pts[idx] = prices[idx];
        return { data: pts, borderColor: color, backgroundColor: color, pointRadius: 6, pointHoverRadius: 8, pointBorderWidth: 2, pointBorderColor: '#0f172a', showLine: false, fill: false };
      };

      const extras = [];
      if (extremos.menor_valor) extras.push(mkDot(data.findIndex(p => p.time === extremos.menor_valor.data), '#10b981'));
      if (extremos.maior_valor) extras.push(mkDot(data.findIndex(p => p.time === extremos.maior_valor.data), '#ef4444'));

      this.priceChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets: [{ label: 'Preço', data: prices, borderColor: '#3b82f6', backgroundColor: gradient, borderWidth: 2, pointRadius: 0, pointHoverRadius: 6, fill: true, tension: 0.4 }, ...extras] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false, backgroundColor: 'rgba(15,23,42,0.9)', titleColor: '#fff', bodyColor: '#fff', filter: (i) => i.raw !== null } },
          scales: { x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', maxTicksLimit: 10 } }, y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } } },
          interaction: { mode: 'nearest', axis: 'x', intersect: false },
        },
      });
    },

    async analiseIa() {
      const produto = this.currentProduto;
      if (!produto) return;
      this.loadingIa = true;
      this.analise = { analise: 'Consultando a IA...' };
      const d = await fetchJSON(`${API_BASE}/analise-ia?produto=${encodeURIComponent(produto)}&limite=8&so_novos=${this.soNovos}`);
      this.analise = d || { analise: 'Erro ao conectar.' };
      this.loadingIa = false;
    },

    formatPrice,
  },

  mounted() {
    this.updateDashboard();
  },
};
