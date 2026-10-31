"""Resolve product discounts once at registration; checkout uses stored cents."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fastapi import HTTPException


def promotional_cents(base, final, mode, percentage, enabled, parse_price):
    if mode not in ('legacy', 'final', 'percent'):
        raise HTTPException(400, 'Tipo de desconto inválido.')
    if mode != 'legacy' and not enabled:
        return 0
    if mode == 'percent':
        try:
            percent = Decimal(percentage.strip().replace(',', '.'))
        except (InvalidOperation, ValueError):
            raise HTTPException(400, 'Informe uma porcentagem válida.')
        if not percent.is_finite() or not 0 < percent < 100:
            raise HTTPException(400, 'O desconto deve ser maior que 0% e menor que 100%.')
        value = int((Decimal(base) * (100 - percent) / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    else:
        if not final.strip():
            if mode == 'legacy':return 0
            raise HTTPException(400, 'Informe o preço promocional.')
        value = parse_price(final)
    if value <= 0 or value >= base:
        raise HTTPException(400, 'O preço promocional deve ser maior que zero e menor que o preço normal.')
    return value
