"""Explicit, optional NowUp marketing choices; never infer consent from registration."""
import hashlib
import re
from datetime import datetime,timezone

VERSION='nowup-promocoes-2026-11-v1'
TEXT={'email':'Quero receber promoções e cupons do NowUp por e-mail.',
      'whatsapp':'Quero receber promoções e cupons do NowUp por WhatsApp.'}

def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS marketing_preferences309(
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      channel TEXT NOT NULL CHECK(channel IN ('email','whatsapp')),
      allowed INTEGER NOT NULL CHECK(allowed IN (0,1)),contact_hash TEXT NOT NULL,
      version TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,channel))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS marketing_consent_events309(
      id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      channel TEXT NOT NULL,allowed INTEGER NOT NULL,contact_hash TEXT NOT NULL,
      version TEXT NOT NULL,consent_text TEXT NOT NULL,source TEXT NOT NULL,created_at TEXT NOT NULL)''')

def contact_hash(channel,value):
    value=str(value or '').strip().lower()
    if channel=='whatsapp':
        value=re.sub(r'\D','',value)
        if value.startswith('55') and len(value) in (12,13):value=value[2:]
    return hashlib.sha256((channel+':'+value).encode()).hexdigest()

def contacts(conn,uid):
    user=conn.execute("SELECT email,phone,is_active,email_verified FROM users WHERE id=? AND role='customer'",(uid,)).fetchone()
    return dict(user) if user else None

def preferences(conn,uid):
    result={'email':False,'whatsapp':False};user=contacts(conn,uid)
    if not user or not user['is_active']:return result
    for row in conn.execute('SELECT * FROM marketing_preferences309 WHERE user_id=?',(uid,)):
        contact=user['email' if row['channel']=='email' else 'phone']
        result[row['channel']]=bool(row['allowed'] and row['version']==VERSION and row['contact_hash']==contact_hash(row['channel'],contact))
    return result

def save(conn,uid,email=False,whatsapp=False,source='account'):
    user=contacts(conn,uid)
    if not user:return
    for channel,allowed in [('email',email),('whatsapp',whatsapp)]:
        value=user['email' if channel=='email' else 'phone'];allowed=bool(allowed and str(value or '').strip())
        digest=contact_hash(channel,value);stamp=datetime.now(timezone.utc).isoformat()
        old=conn.execute('SELECT allowed,contact_hash,version FROM marketing_preferences309 WHERE user_id=? AND channel=?',(uid,channel)).fetchone()
        if old and (bool(old['allowed']),old['contact_hash'],old['version'])==(allowed,digest,VERSION):continue
        conn.execute('INSERT INTO marketing_preferences309 VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,channel) DO UPDATE SET allowed=excluded.allowed,contact_hash=excluded.contact_hash,version=excluded.version,updated_at=excluded.updated_at',(uid,channel,int(allowed),digest,VERSION,stamp))
        conn.execute('INSERT INTO marketing_consent_events309(user_id,channel,allowed,contact_hash,version,consent_text,source,created_at) VALUES(?,?,?,?,?,?,?,?)',(uid,channel,int(allowed),digest,VERSION,TEXT[channel],source,stamp))

def eligible(conn,uid,channel):
    """Campaign integrations must check this at send time, including withdrawals."""
    if channel not in TEXT:return False
    user=contacts(conn,uid)
    return bool(user and user['is_active'] and user['email_verified'] and preferences(conn,uid)[channel])
