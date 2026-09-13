/* BuscarTab — Product search with stats + results grid */
const BuscarTab = {
  template: `
    <div class="glass-card p-4">
      <h5 class="fw-semibold mb-3 text-white">
        <i class="fa-solid fa-magnifying-glass me-2 text-info"></i>Busca Ampliada de Produtos
      </h5>
      <p class="text-secondary mb-3">Busca os top resultados com comparação de preços e estatísticas.</p>

      <form class="input-group mb-4" @submit.prevent="buscar">
        <input type="text" v-model="query" class="form-control bg-dark text-white border-secondary"
               placeholder="Digite o nome do produto..." required>
        <select v-model.number="limite" class="form-select bg-dark text-white border-secondary" style="max-width: 120px;">
          <option :value="3">Top 3</option>
          <option :value="5">Top 5</option>
          <option :value="10">Top 10</option>
          <option :value="20">Top 20</option>
          <option :value="50">Todos</option>
        </select>
        <button class="btn btn-primary" type="submit" :disabled="loading">
          <i class="fa-solid fa-magnifying-glass me-1"></i> {{ loading ? 'Buscando...' : 'Buscar' }}
        </button>
      </form>

      <!-- Stats -->
      <div v-if="stats" class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="glass-card p-3 text-center h-100">
            <small class="text-secondary d-block"><i class="fa-solid fa-arrow-down text-success me-1"></i>Menor Preço</small>
            <span class="fs-5 fw-bold text-success">{{ formatPrice(stats.menor_preco) }}</span>
          </div>
        </div>
        <div class="col-md-3">
          <div class="glass-card p-3 text-center h-100">
            <small class="text-secondary d-block"><i class="fa-solid fa-arrow-up text-danger me-1"></i>Maior Preço</small>
            <span class="fs-5 fw-bold text-danger">{{ formatPrice(stats.maior_preco) }}</span>
          </div>
        </div>
        <div class="col-md-3">
          <div class="glass-card p-3 text-center h-100">
            <small class="text-secondary d-block"><i class="fa-solid fa-chart-column text-primary me-1"></i>Preço Médio</small>
            <span class="fs-5 fw-bold text-primary">{{ formatPrice(stats.preco_medio) }}</span>
          </div>
        </div>
        <div class="col-md-3">
          <div class="glass-card p-3 text-center h-100">
            <small class="text-secondary d-block"><i class="fa-solid fa-store text-warning me-1"></i>Fontes</small>
            <span class="fs-5 fw-bold text-warning">{{ fontesList.join(', ') || '--' }}</span>
          </div>
        </div>
      </div>

      <!-- Results -->
      <div v-if="erro" class="text-center text-danger py-4">
        <i class="fa-solid fa-exclamation-triangle fa-3x mb-3 opacity-25"></i>
        <p>{{ erro }}</p>
      </div>
      <div v-else-if="resultados.length" class="row g-3">
        <div v-for="(r, i) in resultados" :key="i" class="col-md-6 col-lg-4">
          <div class="product-card position-relative" @click="abrirLink(r.permalink)">
            <div class="d-flex gap-3">
              <img v-if="r.thumbnail" :src="r.thumbnail" class="product-thumb" :alt="r.nome" loading="lazy"
                   @error="$event.target.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2280%22 height=%2280%22><rect fill=%22%23334155%22 width=%2280%22 height=%2280%22/><text fill=%22%2364748b%22 x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-size=%2214%22>IMG</text></svg>'">
              <div class="flex-grow-1">
                <h6 class="mb-1 text-white" style="font-size: 0.85rem; line-height: 1.3;">{{ r.nome }}</h6>
                <div class="mb-1">
                  <span class="product-price">{{ formatPrice(r.preco) }}</span>
                  <del v-if="r.preco_original" class="text-secondary ms-2" style="font-size:0.75rem;">
                    {{ formatPrice(r.preco_original) }}
                  </del>
                </div>
                <div class="d-flex gap-2 flex-wrap">
                  <span class="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-50" style="font-size: 0.7rem;">
                    <i class="fa-solid fa-store me-1"></i>{{ r.loja || r.fonte }}
                  </span>
                  <span v-if="r.frete_gratis" class="badge bg-success bg-opacity-25 text-success border border-success border-opacity-50" style="font-size: 0.7rem;">
                    <i class="fa-solid fa-truck me-1"></i>Frete Grátis
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="!loading && searched" class="text-center text-secondary py-5">
        <i class="fa-solid fa-box-open fa-3x mb-3 opacity-25"></i>
        <p>Nenhum resultado para '{{ lastQuery }}'</p>
      </div>
      <div v-else class="text-center text-secondary py-5">
        <i class="fa-solid fa-box-open fa-3x mb-3 opacity-25"></i>
        <p>Digite um produto e clique em Buscar</p>
      </div>
    </div>
  `,

  data() {
    return {
      query: '',
      limite: 50,
      resultados: [],
      stats: null,
      fontesList: [],
      erro: null,
      loading: false,
      searched: false,
      lastQuery: '',
    };
  },

  methods: {
    async buscar() {
      if (!this.query.trim()) return;
      this.loading = true;
      this.erro = null;
      this.searched = true;
      this.lastQuery = this.query;

      const params = new URLSearchParams({ produto: this.query, limite: this.limite });
      const data = await fetchJSON(`${API_BASE}/buscar?${params}`);

      if (!data) {
        this.erro = 'Erro ao buscar produtos.';
        this.resultados = [];
        this.stats = null;
      } else {
        this.resultados = data.resultados || [];
        this.stats = data.estatisticas || null;
        this.fontesList = Object.keys(data.por_fonte || {});
        if (!this.resultados.length) this.erro = null;
      }

      this.loading = false;
    },

    abrirLink(url) {
      if (url) window.open(url, '_blank');
    },

    formatPrice,
  },
};
