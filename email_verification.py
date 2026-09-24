import os, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from email_validator import validate_email, EmailNotValidError
from mailing import send_verification, configured

BASE=Path(__file__).resolve().parent
DB_PATH=Path(os.getenv("NOWUP_DB",BASE/"data"/"nowup.db"))
templates=Jinja2Templates(directory=str(BASE/"templates"))
router=APIRouter()

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    return conn

@router.get("/cadastro/aguardando",response_class=HTMLResponse)
def waiting(request: Request):
    return templates.TemplateResponse("verify_pending.html",{"request":request})

@router.get("/verificar-email")
def verify(token: str=""):
    if not token:
        return RedirectResponse("/entrar?erro=verificacao",303)
    conn=db()
    u=conn.execute("SELECT id,verification_expires_at FROM users WHERE verification_token=?",(token,)).fetchone()
    if not u:
        conn.close(); return RedirectResponse("/entrar?erro=verificacao",303)
    try:
        valid_until=datetime.fromisoformat(u["verification_expires_at"])
    except Exception:
        valid_until=datetime.now(timezone.utc)-timedelta(seconds=1)
    if valid_until < datetime.now(timezone.utc):
        conn.close(); return RedirectResponse("/entrar?erro=expirado",303)
    conn.execute("UPDATE users SET email_verified=1,verification_token='',verification_expires_at='' WHERE id=?",(u["id"],))
    conn.commit(); conn.close()
    return RedirectResponse("/entrar?verificado=1",303)

@router.post("/reenviar-verificacao")
def resend(email: str=Form(...)):
    if not configured():
        return RedirectResponse("/entrar?erro=verificacao",303)
    try:
        normalized=validate_email(email.strip(),check_deliverability=True).normalized.lower()
    except EmailNotValidError:
        return RedirectResponse("/entrar?erro=verificacao",303)
    conn=db()
    u=conn.execute("SELECT id,name,email_verified FROM users WHERE email=?",(normalized,)).fetchone()
    if not u:
        conn.close(); return RedirectResponse("/entrar?erro=verificacao",303)
    if u["email_verified"]:
        conn.close(); return RedirectResponse("/entrar?verificado=1",303)
    token=secrets.token_urlsafe(32)
    expires=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()
    conn.execute("UPDATE users SET verification_token=?,verification_expires_at=? WHERE id=?",(token,expires,u["id"]))
    conn.commit(); conn.close()
    send_verification(normalized,u["name"],token)
    return RedirectResponse("/cadastro/aguardando?reenviado=1",303)
