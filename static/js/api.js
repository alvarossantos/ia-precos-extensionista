/* Shared API helpers — used by all Vue components */
const API_BASE = `${window.location.origin}/api`;

const fetchJSON = async (url, options = {}) => {
  try {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!r.ok) {
      console.warn('[API]', r.status, r.statusText, url);
      return null;
    }
    return await r.json();
  } catch (e) {
    console.error('[API] fetch falhou:', url, e.message);
    return null;
  }
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

const escapeHtml = (v) => {
  if (v == null) return '';
  return String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
};

/* ── Alertas API ─────────────────────────────────────── */
const AlertasAPI = {
  async listar() {
    const data = await fetchJSON(`${API_BASE}/alertas`);
    return data?.alertas || [];
  },

  async criar(produto, preco_alvo, condicao = 'menor') {
    const data = await fetchJSON(`${API_BASE}/alertas`, {
      method: 'POST',
      body: JSON.stringify({ produto, preco_alvo, condicao }),
    });
    return data?.alerta || null;
  },

  async remover(id) {
    return await fetchJSON(`${API_BASE}/alertas/${id}`, { method: 'DELETE' });
  },

  async toggle(id) {
    return await fetchJSON(`${API_BASE}/alertas/${id}/toggle`, { method: 'POST' });
  },

  async verificar() {
    return await fetchJSON(`${API_BASE}/alertas/verificar`);
  },
};
