/* Vue 3 app — Router + Root shell */
const { createApp } = Vue;
const { createRouter, createWebHashHistory } = VueRouter;

/* ---------- Router ---------- */
const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: DashboardTab, meta: { tab: 'dashboard', icon: 'fa-chart-line', label: 'Dashboard', mobileLabel: 'Home' } },
  { path: '/buscar', component: BuscarTab, meta: { tab: 'buscar', icon: 'fa-magnifying-glass', label: 'Buscar Produtos', mobileLabel: 'Buscar' } },
  { path: '/comparar', component: CompararTab, meta: { tab: 'comparar', icon: 'fa-scale-balanced', label: 'Comparar', mobileLabel: 'Comparar' } },
  { path: '/alertas', component: AlertasTab, meta: { tab: 'alertas', icon: 'fa-bell', label: 'Alertas', mobileLabel: 'Alertas' } },
  { path: '/historico', component: HistoricoTab, meta: { tab: 'historico', icon: 'fa-clock-rotate-left', label: 'Histórico', mobileLabel: 'Histórico' } },
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
            <i class="fa-solid fa-tag text-primary me-2 fs-3"></i>
            <span class="gradient-text">PreçoCerto</span>
          </a>
          <div class="d-flex align-items-center gap-3">
            <button class="btn btn-sm btn-outline-secondary" @click="toggleTheme" :title="isDark ? 'Modo claro' : 'Modo escuro'">
              <i :class="isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon'"></i>
            </button>
          </div>
        </div>
      </nav>

      <div class="container main-content">
        <!-- Header -->
        <div class="row mb-4">
          <div class="col-12 text-center text-md-start">
            <h1 class="fw-bold mb-2">Previsão de Tendências de Mercado</h1>
            <p class="text-secondary">Sistema de apoio à decisão com análise preditiva e busca de preços.</p>
          </div>
        </div>

        <!-- Tabs (desktop only) -->
        <ul class="nav nav-pills glass-card p-2 mb-4 justify-content-center desktop-tabs">
          <li class="nav-item" v-for="r in tabRoutes" :key="r.path">
            <router-link :to="r.path" class="nav-link" active-class="active">
              <i :class="'fa-solid ' + r.meta.icon + ' me-1'"></i> {{ r.meta.label }}
            </router-link>
          </li>
        </ul>

        <!-- Route view -->
        <router-view></router-view>

        <!-- Footer (desktop) -->
        <footer class="mt-5 text-center text-secondary py-3 border-top border-secondary border-opacity-25 desktop-footer">
          <small>PreçoCerto — Atividade Extensionista (UEMG Passos). Dados via Binance API e lojas brasileiras.</small>
        </footer>
      </div>

      <!-- Mobile Bottom Nav -->
      <nav class="mobile-bottom-nav">
        <router-link v-for="r in tabRoutes" :key="r.path" :to="r.path"
                     class="mobile-nav-item" :class="{ active: $route.path === r.path }">
          <i :class="'fa-solid ' + r.meta.icon"></i>
          <span>{{ r.meta.mobileLabel || r.meta.label }}</span>
        </router-link>
      </nav>
    </div>
  `,

  data() {
    return {
      isDark: document.documentElement.getAttribute('data-bs-theme') !== 'light',
    };
  },

  computed: {
    tabRoutes() {
      return routes.filter(r => r.meta?.icon);
    },
  },

  methods: {
    toggleTheme() {
      const html = document.documentElement;
      const current = html.getAttribute('data-bs-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-bs-theme', next);
      this.isDark = next === 'dark';
      localStorage.setItem('precocerto-theme', next);
    },
  },

  created() {
    const saved = localStorage.getItem('precocerto-theme');
    if (saved) {
      document.documentElement.setAttribute('data-bs-theme', saved);
      this.isDark = saved === 'dark';
    }
  },
};

/* ---------- Mount ---------- */
try {
  const app = createApp(AppShell);
  app.use(router);
  app.mount('#app');
  console.log('[Vue] App montada com sucesso');
} catch (e) {
  console.error('[Vue] Erro ao montar app:', e);
  document.getElementById('app').innerHTML =
    '<div class="container py-5 text-center">' +
    '<h3 class="text-danger">Erro ao carregar aplicação</h3>' +
    '<pre class="text-start mt-3 p-3 bg-dark text-light rounded" style="font-size:0.8rem">' + e.message + '</pre>' +
    '<p class="text-secondary mt-2">Abra o Console (F12) para mais detalhes.</p></div>';
}
