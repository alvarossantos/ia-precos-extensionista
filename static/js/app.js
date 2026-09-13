/* Vue 3 app — Router + Root shell */
const { createApp, ref, computed } = Vue;
const { createRouter, createWebHashHistory } = VueRouter;

/* ---------- Router ---------- */
const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: DashboardTab, meta: { tab: 'dashboard', icon: 'fa-chart-line', label: 'Dashboard' } },
  { path: '/buscar', component: BuscarTab, meta: { tab: 'buscar', icon: 'fa-magnifying-glass', label: 'Buscar Produtos' } },
  { path: '/comparar', component: CompararTab, meta: { tab: 'comparar', icon: 'fa-scale-balanced', label: 'Comparar' } },
  { path: '/alertas', component: AlertasTab, meta: { tab: 'alertas', icon: 'fa-bell', label: 'Alertas' } },
  { path: '/historico', component: HistoricoTab, meta: { tab: 'historico', icon: 'fa-clock-rotate-left', label: 'Histórico' } },
];

const router = createRouter({ history: createWebHashHistory(), routes });

/* ---------- App Shell ---------- */
const AppShell = {
  template: `
    <div>
      <!-- Navbar -->
      <nav class="navbar navbar-expand-lg glass-nav mb-4">
        <div class="container">
          <a class="navbar-brand d-flex align-items-center fw-bold" href="#/dashboard">
            <i class="fa-solid fa-brain text-primary me-2 fs-3"></i>
            <span class="gradient-text">Preditor IA</span>
          </a>
          <div class="d-flex align-items-center gap-3">
            <span class="badge bg-primary-subtle text-primary border border-primary rounded-pill px-3 py-2">
              <i class="fa-solid fa-circle-nodes me-1"></i> Ativo
            </span>
            <button class="btn btn-sm btn-outline-secondary" @click="toggleTheme" title="Alternar tema">
              <i class="fa-solid fa-circle-half-stroke"></i>
            </button>
          </div>
        </div>
      </nav>

      <div class="container">
        <!-- Header -->
        <div class="row mb-4">
          <div class="col-12 text-center text-md-start">
            <h1 class="fw-bold mb-2">Previsão de Tendências de Mercado</h1>
            <p class="text-secondary">Sistema de apoio à decisão com análise preditiva e busca de preços.</p>
          </div>
        </div>

        <!-- Tabs -->
        <ul class="nav nav-pills glass-card p-2 mb-4 justify-content-center">
          <li class="nav-item" v-for="r in tabRoutes" :key="r.path">
            <router-link :to="r.path" class="nav-link" active-class="active">
              <i :class="'fa-solid ' + r.meta.icon + ' me-1'"></i> {{ r.meta.label }}
            </router-link>
          </li>
        </ul>

        <!-- Route view -->
        <router-view></router-view>

        <!-- Footer -->
        <footer class="mt-5 text-center text-secondary py-3 border-top border-secondary border-opacity-25">
          <small>Preditor IA — Atividade Extensionista (UEMG Passos). Dados via Binance API e lojas brasileiras.</small>
        </footer>
      </div>
    </div>
  `,

  computed: {
    tabRoutes() {
      return routes.filter(r => r.meta?.icon);
    },
  },

  methods: {
    toggleTheme() {
      const html = document.documentElement;
      const current = html.getAttribute('data-bs-theme');
      html.setAttribute('data-bs-theme', current === 'dark' ? 'light' : 'dark');
    },
  },
};

/* ---------- Mount ---------- */
const app = createApp(AppShell);
app.use(router);
app.mount('#app');
