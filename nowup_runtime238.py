"""Origin validation and bounded, infrequent renewal of persistent sessions."""
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

UNSAFE = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})
# This route authenticates independently with its Asaas webhook secret.
WEBHOOKS = frozenset({'/integracoes/asaas/webhook'})


def origin_tuple(value):
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            return None
        return parsed.scheme, parsed.hostname.lower(), parsed.port or (443 if parsed.scheme == 'https' else 80)
    except (ValueError, TypeError):
        return None


def mutation_origin_allowed(request):
    if request.method not in UNSAFE or request.url.path in WEBHOOKS:
        return True
    if request.headers.get('sec-fetch-site') == 'cross-site':
        return False
    base = request.base_url.replace(scheme='https') if os.getenv('NOWUP_HTTPS', '0') == '1' else request.base_url
    target = os.getenv('NOWUP_PUBLIC_ORIGIN') or str(base)
    expected = origin_tuple(target)
    if 'origin' in request.headers:
        return expected is not None and origin_tuple(request.headers['origin']) == expected
    return expected is not None and origin_tuple(request.headers.get('referer', '')) == expected


def renew_session(database, token, days=30, now=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    conn = database()
    try:
        from nowup_security import session_user
        user = session_user(conn, token)
        if not user or user['role'] not in ('customer', 'professional'):
            return None
        row = conn.execute('SELECT expires_at,absolute_expires_at238 FROM sessions WHERE token=?', (token,)).fetchone()
        if not row:
            return None
        absolute = row['absolute_expires_at238'] or (now + timedelta(days=90)).isoformat()
        if absolute <= stamp:
            return None
        expires = min((now + timedelta(days=days)).isoformat(), absolute)
        # A visit renews at most daily. Clamp legacy overlong expiry immediately.
        if row['expires_at'] <= (datetime.fromisoformat(expires)-timedelta(days=1)).isoformat() or row['expires_at'] > expires or not row['absolute_expires_at238']:
            changed = conn.execute('''UPDATE sessions SET expires_at=?,absolute_expires_at238=?
                WHERE token=? AND expires_at>? AND (absolute_expires_at238='' OR absolute_expires_at238>?)''',
                (expires, absolute, token, stamp, stamp)).rowcount
            conn.commit()
            return max(1, int((datetime.fromisoformat(expires)-now).total_seconds())) if changed else None
        return None
    finally:
        conn.close()
