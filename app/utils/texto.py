"""Utilitários de texto compartilhados.

`normalizar` existia duplicada em três lugares diferentes do
mock_backend.py original (_filtrar_relevancia, _filtrar_novos,
_eh_acessorio) — cada uma com seu próprio `import unicodedata` local.
Centralizada aqui para não divergir com o tempo.
"""

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparação textual tolerante."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def extrair_preco_br(texto: str):
    """Extrai um preço em R$ de um texto livre. Retorna float ou None."""
    if not texto:
        return None
    m = re.search(r"R\$\s*([\d.,]+)", texto)
    if not m:
        return None
    try:
        return float(m.group(1).replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None
