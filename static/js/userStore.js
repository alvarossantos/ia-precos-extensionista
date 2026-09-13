/* userStore.js — Dados do usuário em localStorage.
 *
 * O backend só guarda preços/cache (admin).
 * Alertas, histórico e buscas ficam no navegador do usuário.
 */
const UserStore = {
  KEYS: {
    alertas: 'precocerto-alertas',
    historico: 'precocerto-historico',
  },

  /* ── Helpers ─────────────────────────────────────── */
  _get(key) {
    try { return JSON.parse(localStorage.getItem(key)) || []; }
    catch { return []; }
  },

  _set(key, data) {
    localStorage.setItem(key, JSON.stringify(data));
  },

  _uuid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  },

  /* ── Alertas ─────────────────────────────────────── */
  listarAlertas() {
    return this._get(this.KEYS.alertas);
  },

  criarAlerta(produto, preco_alvo, condicao = 'menor') {
    const alertas = this.listarAlertas();
    const alerta = {
      id: this._uuid(),
      produto,
      preco_alvo: parseFloat(preco_alvo),
      condicao,
      ativo: true,
      criado_em: new Date().toISOString(),
    };
    alertas.unshift(alerta);
    this._set(this.KEYS.alertas, alertas);
    return alerta;
  },

  removerAlerta(id) {
    const alertas = this.listarAlertas().filter(a => a.id !== id);
    this._set(this.KEYS.alertas, alertas);
  },

  /* ── Histórico de Buscas ─────────────────────────── */
  listarHistorico() {
    return this._get(this.KEYS.historico);
  },

  salvarBusca(produto) {
    if (!produto || !produto.trim()) return;
    const historico = this.listarHistorico();
    // Remove duplicata recente (mesma busca em < 5 min)
    const agora = Date.now();
    const filtrado = historico.filter(h => {
      if (h.produto.toLowerCase() !== produto.trim().toLowerCase()) return true;
      return (agora - new Date(h.data).getTime()) > 5 * 60 * 1000;
    });
    filtrado.unshift({
      produto: produto.trim(),
      data: new Date().toISOString(),
    });
    // Mantém últimas 50 buscas
    this._set(this.KEYS.historico, filtrado.slice(0, 50));
  },

  limparHistorico() {
    this._set(this.KEYS.historico, []);
  },
};
