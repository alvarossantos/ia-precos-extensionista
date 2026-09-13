/* HistoricoTab — Search history (localStorage) */
const HistoricoTab = {
  template: `
    <div class="glass-card p-4">
      <h5 class="fw-semibold mb-3 text-white">
        <i class="fa-solid fa-clock-rotate-left me-2 text-info"></i>Histórico de Buscas
      </h5>
      <p class="text-secondary mb-3">Últimas buscas realizadas no sistema.</p>

      <div v-if="buscas.length" class="d-flex justify-content-end mb-3">
        <button class="btn btn-sm btn-outline-danger" @click="limpar">
          <i class="fa-solid fa-trash me-1"></i> Limpar tudo
        </button>
      </div>

      <div v-if="buscas.length">
        <div v-for="(b, i) in buscas" :key="i"
             class="d-flex flex-wrap justify-content-between align-items-center gap-2 glass-card p-3 mb-2">
          <div>
            <span class="text-white fw-semibold">{{ b.produto }}</span>
          </div>
          <small class="text-secondary">{{ formatDate(b.data) }}</small>
        </div>
      </div>
      <div v-else class="text-center text-secondary py-4">
        <i class="fa-solid fa-clock-rotate-left fa-2x mb-2 opacity-25"></i>
        <p class="mb-0">Nenhuma busca realizada ainda.</p>
      </div>
    </div>
  `,

  data() {
    return { buscas: [], loading: false };
  },

  methods: {
    carregar() {
      this.loading = true;
      this.buscas = UserStore.listarHistorico();
      this.loading = false;
    },

    limpar() {
      if (!confirm('Limpar todo o histórico de buscas?')) return;
      UserStore.limparHistorico();
      this.buscas = [];
    },

    formatDate(dateStr) {
      if (!dateStr) return '--';
      const d = new Date(dateStr);
      return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    },
  },

  mounted() {
    this.carregar();
  },
};
