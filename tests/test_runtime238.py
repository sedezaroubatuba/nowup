"""Security boundaries, bounded renewal and a WAL backup/restore round trip."""
import sqlite3
from datetime import datetime, timedelta, timezone
import pytest
from starlette.requests import Request
from nowup_runtime238 import mutation_origin_allowed, renew_session
from nowup_security import session_user


def request(headers=None, path='/painel/cardapio/exibicao', method='POST'):
    pairs={'host':'testserver',**(headers or {})}
    return Request({'type':'http','method':method,'scheme':'https','path':path,'root_path':'','query_string':b'','server':('testserver',443),'headers':[(k.encode(),v.encode()) for k,v in pairs.items()]})


@pytest.mark.parametrize('headers,allowed',[
    ({},False),({'origin':'null'},False),({'origin':''},False),
    ({'origin':'https://evil.invalid'},False),({'origin':'https://testserver.evil.invalid'},False),
    ({'origin':'http://testserver'},False),({'origin':'https://testserver:444'},False),
    ({'origin':'https://testserver'},True),({'referer':'https://testserver/painel'},True),
    ({'origin':'null','referer':'https://testserver/painel'},False),
    ({'origin':'https://testserver','sec-fetch-site':'cross-site'},False),
])
def test_mutation_origin(headers,allowed,monkeypatch):
    monkeypatch.delenv('NOWUP_PUBLIC_ORIGIN',raising=False)
    assert mutation_origin_allowed(request(headers)) is allowed


def test_webhook_only_exact_route_is_exempt():
    assert mutation_origin_allowed(request(path='/integracoes/asaas/webhook'))
    assert not mutation_origin_allowed(request(path='/integracoes/asaas/webhook/other'))
    assert mutation_origin_allowed(request(method='GET'))


@pytest.fixture
def sessions(tmp_path):
    path=tmp_path/'sessions.db'
    def database():
        c=sqlite3.connect(path);c.row_factory=sqlite3.Row;return c
    with database() as c:
        c.executescript("CREATE TABLE users(id INTEGER PRIMARY KEY,role TEXT,is_active INTEGER);CREATE TABLE sessions(token TEXT PRIMARY KEY,user_id INTEGER,expires_at TEXT,absolute_expires_at238 TEXT DEFAULT '');")
        c.execute("INSERT INTO users VALUES(1,'professional',1)")
        now=datetime.now(timezone.utc)
        c.execute('INSERT INTO sessions VALUES(?,?,?,?)',('token',1,(now+timedelta(days=2)).isoformat(),(now+timedelta(days=90)).isoformat()))
    return database,now


def test_renewal_once_daily_and_absolute_limit(sessions):
    db,now=sessions
    assert renew_session(db,'token',now=now)==30*86400
    assert renew_session(db,'token',now=now+timedelta(minutes=1)) is None
    assert renew_session(db,'token',now=now+timedelta(days=2))==30*86400
    with db() as c:
        bound=(now+timedelta(hours=3)).isoformat()
        c.execute('UPDATE sessions SET absolute_expires_at238=?',(bound,))
    assert renew_session(db,'token',now=now)==3*3600
    with db() as c:assert c.execute('SELECT expires_at FROM sessions').fetchone()[0]==bound


def test_expired_revoked_and_disabled_sessions_are_not_renewed(sessions):
    db,now=sessions
    with db() as c:c.execute('UPDATE sessions SET absolute_expires_at238=?',((now-timedelta(seconds=1)).isoformat(),))
    with db() as c:assert session_user(c,'token') is None
    assert renew_session(db,'token') is None
    with db() as c:
        c.execute("UPDATE sessions SET absolute_expires_at238='' ")
        c.execute('UPDATE users SET is_active=0')
    assert renew_session(db,'token') is None
    with db() as c:c.execute('DELETE FROM sessions')
    assert renew_session(db,'token') is None


def test_backup_restores_committed_wal_data_and_files(tmp_path,monkeypatch):
    import nowup_backup as backup
    from restore_backup import stage_backup
    database=tmp_path/'source.db';uploads=tmp_path/'uploads';uploads.mkdir();(uploads/'photo.txt').write_text('test-file')
    c=sqlite3.connect(database);c.execute('PRAGMA journal_mode=WAL')
    c.execute('CREATE TABLE products(id INTEGER PRIMARY KEY,image_filename TEXT,name TEXT)')
    c.execute("INSERT INTO products VALUES(1,'photo.txt','Committed in WAL')");c.commit()
    monkeypatch.setattr(backup,'_db',database);monkeypatch.setattr(backup,'_uploads',uploads)
    destination=tmp_path/'archive';destination.mkdir()
    try:
        archive=backup.create_archive(destination)
        restored=tmp_path/'restored'
        assert stage_backup(archive,restored)==1
        with sqlite3.connect(restored/'database/nowup.db') as restored_db:
            assert restored_db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert restored_db.execute('SELECT name FROM products').fetchone()[0]=='Committed in WAL'
        assert (restored/'uploads/photo.txt').read_text()=='test-file'
    finally:c.close()


def test_https_termination_and_configured_public_origin(monkeypatch):
    monkeypatch.setenv('NOWUP_HTTPS','1')
    scope=dict(request({'origin':'https://testserver'}).scope,scheme='http')
    assert mutation_origin_allowed(Request(scope))
    monkeypatch.setenv('NOWUP_PUBLIC_ORIGIN','https://nowup.example')
    assert not mutation_origin_allowed(Request(scope))
    scope['headers']=[(b'host',b'internal'),(b'origin',b'https://nowup.example')]
    assert mutation_origin_allowed(Request(scope))
