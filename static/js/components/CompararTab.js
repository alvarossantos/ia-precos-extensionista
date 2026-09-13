/* CompararTab — Compare products side by side */
const CompararTab = {
  template: `
    <div class="glass-card p-4">
      <h5 class="fw-semibold mb-3 text-white">
        <i class="fa-solid fa-scale-balanced me-2 text-warning"></i>Comparação de Preços
      </h5>
      <p class="text-secondary mb-3">Compare preços entre diferentes termos de busca (separados por vírgula).</p>

      <form class="input-group mb-4" @submit.prevent="comparar">
        <input type="text" v-model="termosInput" class="form-control bg-dark text-white border-secondary"
               placeholder="Ex: iPhone 15 128GB, iPhone 15 256GB, Samsung S24" required>
        <button class="btn btn-warning" type="submit" :disabled="loading">
          <i class="fa-solid fa-scale-balanced me-1"></i> {{ loading ? 'Comparando...' : 'Comparar' }}
        </button>
      </form>

      <div v-if="erro" class="text-center text-danger py-4">
        <p>{{ erro }}</p>
      </div>
      <div v-else-if="comparacao.length" class="row g-3">
        <div v-for="(c, i) in comparacao" :key="i" class="col-md-4">
          <div class="glass-card p-3 h-100">
            <h6 class="text-white fw-semibold mb-2">{{ c.termo }}</h6>
            <div v-if="c.erro" class="text-danger">{{ c.erro }}</div>
            <template v-else>
              <div class="mb-2">
                <small class="text-secondary">Menor preço:</small>
                <span class="fw-bold text-success ms-1">{{ formatPrice(c.menor_preco) }}</span>
              </div>
              <div class="mb-2">
                <small class="text-secondary">Média:</small>
                <span class="fw-bold text-primary ms-1">{{ formatPrice(c.preco_medio) }}</span>
              </div>
              <div class="mb-2">
                <small class="text-secondary">Resultados:</small>
                <span class="fw-bold text-warning ms-1">{{ c.resultados }}</span>
              </div>
              <div class="mb-2" v-if="c.fontes?.length">
                <span v-for="f in c.fontes" :key="f" class="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-50 me-1" style="font-size:0.65rem;">
                  {{ f }}
                </span>
              </div>
              <div v-if="c.top_resultado" class="border-top border-secondary pt-2 mt-2">
                <small class="text-secondary d-block mb-1"><i class="fa-solid fa-crown text-warning me-1"></i>Melhor oferta</small>
                <p class="mb-1 text-white" style="font-size:0.8rem;">{{ c.top_resultado.nome }}</p>
                <a v-if="c.top_resultado.permalink" :href="c.top_resultado.permalink" target="_blank"
                   class="btn btn-sm btn-outline-success">
                  <i class="fa-solid fa-external-link-alt me-1"></i>Ver
                </a>
              </div>
            </template>
          </div>
        </div>
      </div>
      <div v-else class="text-center text-secondary py-5">
        <i class="fa-solid fa-code-compare fa-3x mb-3 opacity-25"></i>
        <p>Insira pelo menos 2 termos separados por vírgula</p>
      </div>
    </div>
  `,

  data() {
    return {
      termosInput: '',
      comparacao: [],
      erro: null,
      loading: false,
    };
  },

  methods: {
    async comparar() {
      const termos = this.termosInput.split(',').map(t => t.trim()).filter(Boolean);
      if (termos.length < 2) { this.erro = 'Insira pelo menos 2 termos.'; return; }
      this.loading = true;
      this.erro = null;

      const data = await fetchJSON(`${API_BASE}/comparar?termos=${encodeURIComponent(termos.join(','))}`);
      if (data) {
        this.comparacao = data.comparacao || [];
      } else {
        this.erro = 'Erro ao comparar.';
      }
      this.loading = false;
    },

    formatPrice,
  },
};
