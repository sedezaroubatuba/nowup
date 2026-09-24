import hashlib
import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_login_csrf_lockout_reset_and_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("NOWUP_DB",str(tmp_path/"nowup.db"))
    monkeypatch.setenv("NOWUP_UPLOAD_DIR",str(tmp_path/"uploads"))
    monkeypatch.setenv("NOWUP_ADMIN_EMAIL","owner@example.com")
    monkeypatch.setenv("NOWUP_ADMIN_PASSWORD","strong-admin-password-123")
    monkeypatch.setenv("NOWUP_BASE_URL","https://nowup.example")
    monkeypatch.setenv("NOWUP_HTTPS","1")
    import admin_customization, email_verification, password_reset, app
    for module in (admin_customization,email_verification,password_reset,app):
        importlib.reload(module)
    app.init_db()
    origin={"Origin":"https://nowup.example"}
    with TestClient(app.app,base_url="https://nowup.example") as client:
        assert client.post("/entrar",data={"email":"owner@example.com","password":"wrong"},headers={"Origin":"https://evil.example"}).status_code==403
        for _ in range(5):
            client.post("/entrar",data={"email":"owner@example.com","password":"wrong"},headers=origin)
        locked=client.post("/entrar",data={"email":"owner@example.com","password":"strong-admin-password-123"},headers=origin,follow_redirects=False)
        assert "bloqueado" in locked.headers["location"]
        conn=app.db()
        conn.execute("DELETE FROM login_attempts");conn.commit();conn.close()
        good=client.post("/entrar",data={"email":"owner@example.com","password":"strong-admin-password-123"},headers=origin,follow_redirects=False)
        assert good.headers["location"]=="/admin"
        client.post("/admin/categorias",data={"name":"Teste"},headers=origin)
        conn=app.db()
        assert conn.execute("SELECT COUNT(*) FROM admin_audit").fetchone()[0]>=1
        conn.close()
        token="test-reset-token"
        conn=app.db()
        uid=conn.execute("SELECT id FROM users WHERE email='owner@example.com'").fetchone()[0]
        from datetime import datetime,timedelta,timezone
        conn.execute("INSERT INTO password_resets VALUES(?,?,?,?)",(uid,hashlib.sha256(token.encode()).hexdigest(),
            (datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(),datetime.now(timezone.utc).isoformat()))
        conn.commit();conn.close()
        changed=client.post("/recuperar-senha",data={"token":token,"password":"new-password-12345","password_confirm":"new-password-12345"},headers=origin,follow_redirects=False)
        assert changed.headers["location"]=="/entrar?senha=alterada"
        assert client.get("/admin").status_code==401
        reused=client.post("/recuperar-senha",data={"token":token,"password":"new-password-12345","password_confirm":"new-password-12345"},headers=origin)
        assert "inválido" in reused.text


def test_backup_can_restore_database_and_uploads(tmp_path, monkeypatch):
    import sqlite3, tarfile
    monkeypatch.setenv("NOWUP_DB",str(tmp_path/"live.db"))
    monkeypatch.setenv("NOWUP_UPLOAD_DIR",str(tmp_path/"uploads"))
    monkeypatch.setenv("NOWUP_BACKUP_DIR",str(tmp_path/"backups"))
    (tmp_path/"uploads").mkdir()
    (tmp_path/"uploads"/"photo.jpg").write_bytes(b"sample")
    conn=sqlite3.connect(tmp_path/"live.db")
    conn.execute("CREATE TABLE sample(value TEXT)")
    conn.execute("INSERT INTO sample VALUES('restored')")
    conn.commit();conn.close()
    import backup
    importlib.reload(backup)
    backup.backup()
    archive=next((tmp_path/"backups").glob("*.tar.gz"))
    with tarfile.open(archive) as tar:
        db_file=tar.extractfile("nowup.db")
        restored=tmp_path/"restored.db"
        restored.write_bytes(db_file.read())
        assert tar.extractfile("uploads/photo.jpg").read()==b"sample"
    conn=sqlite3.connect(restored)
    assert conn.execute("SELECT value FROM sample").fetchone()[0]=="restored"
    conn.close()
