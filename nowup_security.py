"""Shared opaque-session validation, including Super ADM revocations."""
import hashlib
import sqlite3
from datetime import datetime, timezone


def session_user(conn, token):
    if not token:
        return None
    row = conn.execute('''SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
        WHERE s.token=? AND s.expires_at>? AND u.is_active=1''',
        (token, datetime.now(timezone.utc).isoformat())).fetchone()
    if row is None:
        return None
    try:
        access = conn.execute('SELECT end FROM adm227_access WHERE session_hash=?',
            (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    except sqlite3.OperationalError as exc:
        # Existing installations may not have installed the Super ADM schema yet.
        if 'no such table: adm227_access' not in str(exc):
            raise
        access = None
    return None if access and access['end'] else row


def revoke_session(conn, token_hash):
    """Delete the exact opaque session as well as its team equivalent."""
    for row in conn.execute('SELECT token FROM sessions').fetchall():
        if hashlib.sha256(row['token'].encode()).hexdigest() == token_hash:
            conn.execute('DELETE FROM sessions WHERE token=?', (row['token'],))
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='push_subscriptions'").fetchone():
                conn.execute('DELETE FROM push_subscriptions WHERE session_hash=?', (token_hash,))
    conn.execute('DELETE FROM adm227_team_sessions WHERE token_hash=?', (token_hash,))
