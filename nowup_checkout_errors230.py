"""Unexpected checkout failures: preserve expected errors and atomic retry semantics."""
import inspect
import logging
from functools import wraps
from fastapi import HTTPException

logger = logging.getLogger(__name__)
MESSAGE = ('Não foi possível confirmar o resultado do pedido. '
           "Confira 'Meus Pedidos' antes de tentar novamente.")


def checkout_errors(function):
    # The existing handler owns the transaction and closes it in finally.
    # Do not retry here: a failure can happen after a successful commit.
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except HTTPException:
            raise
        except Exception:
            # No request body, session token or customer data is added to logs.
            logger.exception('Falha inesperada no checkout')
            raise HTTPException(status_code=503, detail=MESSAGE) from None
    # FastAPI must resolve postponed annotations using the original globals.
    wrapped.__signature__ = inspect.signature(function, eval_str=True)
    return wrapped
