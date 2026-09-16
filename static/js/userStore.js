/* userStore.js — Dados do usuário em localStorage (ES module) */

const _keys = {
  alertas: 'precocerto-alertas',
  historico: 'precocerto-historico',
};

function _get(key) {
  try { return JSON.parse(localStorage.getItem(key)) || []; }
  catch { return []; }
}

function _set(key, data) {
  localStorage.setItem(key, JSON.stringify(data));
}

function _uuid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export const UserStore = {
  /* ── Alertas ─────────────────────────────────────── */
  listarAlertas() {
    return _get(_keys.alertas);
  },

  criarAlerta(produto, preco_alvo, condicao = 'menor') {
    const alertas = this.listarAlertas();
    const alerta = {
      id: _uuid(),
      produto,
      preco_alvo: parseFloat(preco_alvo),
      condicao,
      ativo: true,
      criado_em: new Date().toISOString(),
    };
    alertas.unshift(alerta);
    _set(_keys.alertas, alertas);
    return alerta;
  },

  removerAlerta(id) {
    const alertas = this.listarAlertas().filter(a => a.id !== id);
    _set(_keys.alertas, alertas);
  },

  /* ── Histórico de Buscas ─────────────────────────── */
  listarHistorico() {
    return _get(_keys.historico);
  },

  salvarBusca(produto) {
    if (!produto || !produto.trim()) return;
    const historico = this.listarHistorico();
    const agora = Date.now();
    const filtrado = historico.filter(h => {
      if (h.produto.toLowerCase() !== produto.trim().toLowerCase()) return true;
      return (agora - new Date(h.data).getTime()) > 5 * 60 * 1000;
    });
    filtrado.unshift({
      produto: produto.trim(),
      data: new Date().toISOString(),
    });
    _set(_keys.historico, filtrado.slice(0, 50));
  },

  limparHistorico() {
    _set(_keys.historico, []);
  },
};
