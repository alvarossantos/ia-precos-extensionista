/* HistoricoTab — Search history list */
const HistoricoTab = {
  template: `
    <div class="glass-card p-4">
      <h5 class="fw-semibold mb-3 text-white">
        <i class="fa-solid fa-clock-rotate-left me-2 text-info"></i>Histórico de Buscas
      </h5>
      <p class="text-secondary mb-3">Últimas buscas realizadas no sistema.</p>

      <div v-if="buscas.length">
        <div v-for="(b, i) in buscas" :key="i"
             class="d-flex justify-content-between align-items-center glass-card p-3 mb-2">
          <div>
            <span class="text-white fw-semibold">{{ b.produto }}</span>
            <span v-if="b.fonte" class="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-50 ms-2" style="font-size:0.65rem;">
              {{ b.fonte }}
            </span>
          </div>
          <small class="text-secondary">{{ formatDate(b.data || b.criado_em) }}</small>
        </div>
      </div>
      <div v-else-if="!loading" class="text-center text-secondary py-4">
        <i class="fa-solid fa-clock-rotate-left fa-2x mb-2 opacity-25"></i>
        <p class="mb-0">Nenhuma busca realizada ainda.</p>
      </div>
    </div>
  `,

  data() {
    return { buscas: [], loading: false };
  },

  methods: {
    async carregar() {
      this.loading = true;
      const data = await fetchJSON(`${API_BASE}/historico-buscas?limite=20`);
      this.buscas = data?.buscas || [];
      this.loading = false;
    },
    formatDate,
  },

  mounted() {
    this.carregar();
  },
};
