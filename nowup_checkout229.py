"""Checkout idempotency. The order and its request record commit atomically."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.responses import RedirectResponse


def begin_checkout(conn, customer_id, professional_id, request_key, payload):
    try:
        if request_key and not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', request_key):
            raise HTTPException(400, 'Identificador do pedido inválido. Atualize a página.')
        # Canonical JSON avoids different whitespace producing different legacy keys.
        try:
            payload = {**payload, 'cart': json.loads(payload['cart'])}
        except (ValueError, TypeError):
            raise HTTPException(400, 'Carrinho inválido')
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
            separators=(',', ':')).encode()).hexdigest()
        key = request_key or 'legacy-' + digest
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('''SELECT r.payload_hash,r.created_at,o.tracking_token
            FROM checkout_requests229 r JOIN orders o ON o.id=r.order_id
            WHERE r.customer_id=? AND r.professional_id=? AND r.request_key=?''',
            (customer_id, professional_id, key)).fetchone()
        if row and not request_key and row['created_at'] < (datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat():
            conn.execute('DELETE FROM checkout_requests229 WHERE customer_id=? AND professional_id=? AND request_key=?',
                (customer_id, professional_id, key))
            row = None
        if row and row['payload_hash'] != digest:
            raise HTTPException(409, 'Este envio já foi usado com outros dados. Atualize a página para fazer um novo pedido.')
        return (row['tracking_token'] if row else None), key, digest
    except Exception:
        conn.rollback()
        conn.close()
        raise


def remember_checkout(conn, customer_id, professional_id, key, digest, order_id, created_at):
    conn.execute('INSERT INTO checkout_requests229 VALUES(?,?,?,?,?,?)',
        (customer_id, professional_id, key, digest, order_id, created_at))


def completed_response(slug, token):
    response = RedirectResponse('/pedido/' + token, 303)
    response.set_cookie('nowup_cart_completed', slug, max_age=120, samesite='lax', path='/')
    return response
