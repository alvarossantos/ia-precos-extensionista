"""Parsing tolerante de parâmetros de query string."""


def int_param(request, nome: str, padrao: int) -> int:
    try:
        return int(request.args.get(nome, padrao))
    except (TypeError, ValueError):
        return padrao
