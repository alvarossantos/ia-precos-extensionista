/* BuscarTab — Product search with stats + results grid + alert creation */
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
      <div v-if="stats" class="row g-3 mb-4 stats-grid">
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
          <div class="product-card position-relative">
            <div class="d-flex gap-3" @click="abrirLink(r.permalink)" style="cursor:pointer">
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

            <!-- Alert button + inline form -->
            <div class="mt-2 pt-2 border-top border-secondary border-opacity-25">
              <button v-if="alertaAberto !== i" class="btn btn-sm btn-outline-warning w-100"
                      @click.stop="abrirAlerta(i, r)">
                <i class="fa-solid fa-bell me-1"></i> Criar Alerta
              </button>
              <div v-else class="alert-form-inline" @click.stop>
                <div class="row g-2 align-items-end">
                  <div class="col">
                    <label class="form-label text-secondary" style="font-size:0.7rem;">Preço alvo</label>
                    <div class="input-group input-group-sm">
                      <span class="input-group-text bg-dark text-white border-secondary" style="font-size:0.75rem;">R$</span>
                      <input type="number" v-model.number="alertaForm.preco_alvo" class="form-control bg-dark text-white border-secondary"
                             placeholder="0.00" step="0.01" min="0.01" style="font-size:0.8rem;">
                    </div>
                  </div>
                  <div class="col-auto">
                    <select v-model="alertaForm.condicao" class="form-select form-select-sm bg-dark text-white border-secondary" style="font-size:0.75rem; width:auto;">
                      <option value="menor">&lt; valor</option>
                      <option value="maior">&gt; valor</option>
                    </select>
                  </div>
                  <div class="col-auto">
                    <button class="btn btn-sm btn-warning" @click="criarAlerta(i)" :disabled="alertaCriando || !alertaForm.preco_alvo">
                      <i v-if="alertaCriando" class="fa-solid fa-spinner fa-spin"></i>
                      <i v-else class="fa-solid fa-check"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary ms-1" @click="alertaAberto = null">
                      <i class="fa-solid fa-xmark"></i>
                    </button>
                  </div>
                </div>
                <div v-if="alertaFeedback" class="mt-1" :class="alertaFeedback.ok ? 'text-success' : 'text-danger'" style="font-size:0.75rem;">
                  {{ alertaFeedback.msg }}
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
      alertaAberto: null,
      alertaForm: { produto: '', preco_alvo: null, condicao: 'menor' },
      alertaCriando: false,
      alertaFeedback: null,
    };
  },

  methods: {
    async buscar() {
      if (!this.query.trim()) return;
      this.loading = true;
      this.erro = null;
      this.searched = true;
      this.lastQuery = this.query;
      this.alertaAberto = null;

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

    abrirAlerta(idx, resultado) {
      this.alertaAberto = idx;
      this.alertaFeedback = null;
      this.alertaForm = {
        produto: resultado.nome || this.lastQuery,
        preco_alvo: resultado.preco || null,
        condicao: 'menor',
      };
    },

    async criarAlerta(idx) {
      if (!this.alertaForm.produto || !this.alertaForm.preco_alvo) return;
      this.alertaCriando = true;
      this.alertaFeedback = null;

      try {
        const r = await fetch(`${API_BASE}/alertas`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.alertaForm),
        });
        const data = await r.json();
        if (r.ok) {
          this.alertaFeedback = { ok: true, msg: 'Alerta criado!' };
          setTimeout(() => { this.alertaAberto = null; this.alertaFeedback = null; }, 1500);
        } else {
          this.alertaFeedback = { ok: false, msg: data.erro || 'Erro ao criar alerta.' };
        }
      } catch (e) {
        this.alertaFeedback = { ok: false, msg: 'Falha na conexão.' };
      }

      this.alertaCriando = false;
    },

    abrirLink(url) {
      if (url) window.open(url, '_blank');
    },

    formatPrice,
  },
};
