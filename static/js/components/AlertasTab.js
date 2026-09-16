/* AlertasTab — CRUD de alertas de preço (banco de dados via API) */
const AlertasTab = {
  template: `
    <div class="glass-card p-4">
      <h5 class="fw-semibold mb-3 text-white">
        <i class="fa-solid fa-bell me-2 text-danger"></i>Alertas de Preço
      </h5>
      <p class="text-secondary mb-3">Configure alertas para ser notificado quando um produto atingir o preço desejado.</p>

      <!-- Criar Alerta -->
      <div class="glass-card p-3 mb-4 border border-primary">
        <h6 class="text-primary mb-3"><i class="fa-solid fa-plus-circle me-1"></i> Novo Alerta</h6>
        <form @submit.prevent="criar" class="alertas-form">
          <div class="row g-3">
            <div class="col-md-5">
              <input type="text" v-model="novo.produto" class="form-control bg-dark text-white border-secondary"
                     placeholder="Nome do produto" required>
            </div>
            <div class="col-md-3">
              <div class="input-group">
                <span class="input-group-text bg-dark text-white border-secondary">R$</span>
                <input type="number" v-model.number="novo.preco_alvo" class="form-control bg-dark text-white border-secondary"
                       placeholder="Preço alvo" step="0.01" min="0.01" required>
              </div>
            </div>
            <div class="col-md-2">
              <select v-model="novo.condicao" class="form-select bg-dark text-white border-secondary">
                <option value="menor">Preço menor que</option>
                <option value="maior">Preço maior que</option>
              </select>
            </div>
            <div class="col-md-2">
              <button class="btn btn-primary w-100" type="submit" :disabled="criando">
                <i class="fa-solid fa-bell me-1"></i> {{ criando ? 'Criando...' : 'Criar' }}
              </button>
            </div>
          </div>
        </form>
      </div>

      <!-- Alertas Disparados (verificação server-side) -->
      <div v-if="disparados.length" class="alert alert-success bg-success bg-opacity-10 border-success mb-4">
        <h6 class="alert-heading"><i class="fa-solid fa-bell-ring me-1"></i> Alertas Disparados</h6>
        <div v-for="d in disparados" :key="d.id" class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2 alert-ativado-item">
          <span>
            <strong>{{ d.produto }}</strong> — Preço atual: <span class="text-success fw-bold">{{ formatPrice(d.preco_atual) }}</span>
            ({{ d.condicao === 'menor' ? '<' : '>' }} {{ formatPrice(d.preco_alvo) }})
            <span class="text-secondary ms-1">via {{ d.fonte }}</span>
          </span>
          <span class="badge bg-success"><i class="fa-solid fa-check me-1"></i>Ativado</span>
        </div>
      </div>

      <!-- Verificação em andamento -->
      <div v-if="verificando" class="text-center text-info py-3 mb-3">
        <i class="fa-solid fa-spinner fa-spin me-1"></i> Verificando preços atuais...
      </div>

      <!-- Lista de Alertas -->
      <div v-if="alertas.length">
        <div v-for="a in alertas" :key="a.id"
             class="d-flex flex-wrap justify-content-between align-items-center gap-2 glass-card p-3 mb-2 alert-list-item">
          <div>
            <span class="text-white fw-semibold">{{ a.produto }}</span>
            <span class="text-secondary ms-2">
              {{ a.condicao === 'menor' ? '<' : '>' }} {{ formatPrice(a.preco_alvo) }}
            </span>
            <span v-if="!a.ativo" class="badge bg-secondary ms-2">Pausado</span>
          </div>
          <div class="d-flex gap-1">
            <button class="btn btn-sm btn-outline-warning" @click="toggleAlerta(a.id)" :disabled="processando === a.id"
                    :title="a.ativo ? 'Pausar' : 'Ativar'">
              <i :class="a.ativo ? 'fa-solid fa-pause' : 'fa-solid fa-play'"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger" @click="deletar(a.id)" :disabled="processando === a.id">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
      <div v-else-if="!loading" class="text-center text-secondary py-4">
        <i class="fa-solid fa-bell-slash fa-2x mb-2 opacity-25"></i>
        <p class="mb-0">Nenhum alerta configurado.</p>
      </div>
    </div>
  `,

  data() {
    return {
      alertas: [],
      disparados: [],
      novo: { produto: '', preco_alvo: null, condicao: 'menor' },
      loading: false,
      verificando: false,
      criando: false,
      processando: null,
    };
  },

  methods: {
    async carregar() {
      this.loading = true;
      this.alertas = await AlertasAPI.listar();
      this.loading = false;
    },

    async criar() {
      if (!this.novo.produto || !this.novo.preco_alvo) return;
      this.criando = true;
      await AlertasAPI.criar(this.novo.produto, this.novo.preco_alvo, this.novo.condicao);
      this.novo = { produto: '', preco_alvo: null, condicao: 'menor' };
      this.criando = false;
      await this.carregar();
    },

    async deletar(id) {
      this.processando = id;
      await AlertasAPI.remover(id);
      this.processando = null;
      await this.carregar();
    },

    async toggleAlerta(id) {
      this.processando = id;
      await AlertasAPI.toggle(id);
      this.processando = null;
      await this.carregar();
    },

    async verificarAlertas() {
      if (!this.alertas.length) { this.disparados = []; return; }

      this.verificando = true;
      const data = await AlertasAPI.verificar();
      this.disparados = data?.disparados || [];
      this.verificando = false;
    },

    formatPrice,
  },

  async mounted() {
    await this.carregar();
    await this.verificarAlertas();
  },
};
