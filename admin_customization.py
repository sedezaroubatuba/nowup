import os, re, sqlite3, hmac, hashlib, secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from mailing import send_email, configured as email_configured

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("NOWUP_DB", BASE / "data" / "nowup.db"))
router = APIRouter()
templates = Jinja2Templates(directory=str(BASE / "templates"))

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    return conn

def require_admin(request: Request):
    token=request.cookies.get("nowup_session")
    if not token:
        raise HTTPException(401,"Faça login novamente")
    conn=db()
    row=conn.execute("""
      SELECT u.id,u.role FROM sessions s
      JOIN users u ON u.id=s.user_id
      WHERE s.token=? AND s.expires_at>? AND u.is_active=1
    """,(token,datetime.now(timezone.utc).isoformat())).fetchone()
    conn.close()
    if not row or row["role"]!="admin":
        raise HTTPException(403,"Acesso administrativo necessário")
    return row

@router.post("/admin/aparencia")
def save_appearance(
    request: Request,
    brand_name: str=Form("NowUp"),
    primary_color: str=Form("#2457e6"),
    accent_color: str=Form("#ff8a32"),
    theme_name: str=Form("personalizado"),
    font_family: str=Form("Inter"),
    hero_title: str=Form("Encontre quem resolve."),
    hero_subtitle: str=Form(""),
    public_email: str=Form(""),
    support_whatsapp: str=Form("")
):
    require_admin(request)
    themes={
      "oceanico":("#075BD8","#FF6A00"),"royal":("#243BFF","#8B5CF6"),"turquesa":("#007F8B","#20C997"),"esmeralda":("#087F5B","#F59F00"),"floresta":("#245C3A","#A3E635"),
      "por-do-sol":("#C2410C","#FBBF24"),"coral":("#E84855","#FF8A5B"),"rubi":("#B42318","#F04438"),"vinho":("#7F1D3F","#D946EF"),"uva":("#6D28D9","#EC4899"),
      "lavanda":("#7C3AED","#A78BFA"),"noturno":("#172554","#38BDF8"),"grafite":("#263238","#00B8A9"),"preto-dourado":("#171717","#D4A017"),"cafe":("#6F4E37","#D97706"),
      "areia":("#9A6700","#F2C14E"),"azul-petroleo":("#164E63","#06B6D4"),"ceu":("#0284C7","#22D3EE"),"brasil":("#08783E","#F7C600"),"neon":("#312E81","#22C55E")}
    if theme_name in themes:
        primary_color,accent_color=themes[theme_name]
    else:
        theme_name="personalizado"
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}",primary_color):
        primary_color="#2457e6"
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}",accent_color):
        accent_color="#ff8a32"
    allowed_fonts={"Inter","Arial","Georgia","Trebuchet MS","Verdana"}
    if font_family not in allowed_fonts:
        font_family="Inter"
    data={
      "brand_name":brand_name.strip()[:40] or "NowUp",
      "primary_color":primary_color,
      "accent_color":accent_color,
      "theme_name":theme_name,
      "font_family":font_family,
      "hero_title":hero_title.strip()[:120] or "Encontre quem resolve.",
      "hero_subtitle":hero_subtitle.strip()[:320],
      "public_email":public_email.strip()[:160],
      "support_whatsapp":support_whatsapp.strip()[:30]
    }
    conn=db()
    for key,value in data.items():
        conn.execute("INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value))
    conn.commit(); conn.close()
    return RedirectResponse("/admin#aparencia",303)

@router.post("/admin/perfil")
def save_admin_profile(request: Request, name: str=Form(...)):
    admin=require_admin(request)
    clean=name.strip()[:100]
    if not clean:
        return RedirectResponse("/admin#perfil",303)
    conn=db(); conn.execute("UPDATE users SET name=? WHERE id=?",(clean,admin["id"])); conn.commit(); conn.close()
    return RedirectResponse("/admin#perfil",303)


def verify_password(password: str, stored: str):
    try:
        salt,digest=stored.split("$",1)
        calc=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),240_000).hex()
        return hmac.compare_digest(calc,digest)
    except Exception:
        return False

def create_secure_session(uid: int, dest: str, admin: bool=False):
    token=secrets.token_urlsafe(32)
    ttl=timedelta(minutes=30) if admin else timedelta(days=30)
    expires=(datetime.now(timezone.utc)+ttl).isoformat()
    conn=db(); conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",(token,uid,expires)); conn.commit(); conn.close()
    resp=RedirectResponse(dest,303)
    kwargs={"httponly":True,"samesite":"lax","secure":os.getenv("NOWUP_HTTPS","0")=="1"}
    if not admin:
        kwargs["max_age"]=int(ttl.total_seconds())
    resp.set_cookie("nowup_session",token,**kwargs)
    return resp

@router.post("/entrar")
def secure_login(email: str=Form(...),password: str=Form(...),tipo: str=Form("")):
    normalized=email.strip().lower()
    conn=db(); u=conn.execute("SELECT * FROM users WHERE email=? AND is_active=1",(normalized,)).fetchone(); conn.close()
    suffix=f"&tipo={tipo}" if tipo in ("cliente","profissional","admin") else ""
    if not u or not verify_password(password,u["password_hash"]):
        return RedirectResponse(f"/entrar?erro=1{suffix}",303)
    if u["role"]!="admin" and "email_verified" in u.keys() and not u["email_verified"]:
        return RedirectResponse(f"/entrar?erro=verificacao{suffix}",303)
    expected={"admin":"admin","profissional":"professional","cliente":"customer"}.get(tipo)
    if expected and u["role"]!=expected:
        return RedirectResponse(f"/entrar?tipo={tipo}&erro=perfil",303)
    if u["role"]=="admin":
        # O código enviado por e-mail é obrigatório em todo acesso ADM.
        if not email_configured():
            return RedirectResponse("/entrar?tipo=admin&erro=2fa",303)
        challenge=secrets.token_urlsafe(32); code=f"{secrets.randbelow(1_000_000):06d}"; expires=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
        conn=db(); conn.execute("CREATE TABLE IF NOT EXISTS admin_login_codes(challenge TEXT PRIMARY KEY,user_id INTEGER NOT NULL,code_hash TEXT NOT NULL,expires_at TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0)")
        code_hash=hashlib.sha256(code.encode()).hexdigest(); conn.execute("DELETE FROM admin_login_codes WHERE user_id=? OR expires_at<=?",(u["id"],datetime.now(timezone.utc).isoformat())); conn.execute("INSERT INTO admin_login_codes(challenge,user_id,code_hash,expires_at) VALUES(?,?,?,?)",(challenge,u["id"],code_hash,expires)); conn.commit(); conn.close()
        html=f"<div style='font-family:Arial,sans-serif'><h2>Código de acesso administrativo NowUp</h2><p>Seu código é:</p><p style='font-size:32px;font-weight:bold;letter-spacing:8px'>{code}</p><p>Ele expira em 10 minutos. Se não foi você, altere sua senha.</p></div>"
        if not send_email(u["email"],u["name"],"Código de acesso administrativo NowUp",html):
            conn=db(); conn.execute("DELETE FROM admin_login_codes WHERE challenge=?",(challenge,)); conn.commit(); conn.close(); return RedirectResponse("/entrar?tipo=admin&erro=2fa",303)
        resp=RedirectResponse("/admin/codigo",303); resp.set_cookie("nowup_admin_challenge",challenge,max_age=600,httponly=True,samesite="lax",secure=os.getenv("NOWUP_HTTPS","0")=="1"); return resp
    if u["role"]=="professional":
        return create_secure_session(u["id"],"/painel")
    return create_secure_session(u["id"],"/")

@router.get("/admin/codigo")
def admin_code_page(request: Request):
    if not request.cookies.get("nowup_admin_challenge"):
        return RedirectResponse("/entrar?tipo=admin",303)
    return templates.TemplateResponse("admin_code.html",{"request":request})

@router.post("/admin/codigo")
def admin_code_verify(request: Request, code:str=Form(...)):
    challenge=request.cookies.get("nowup_admin_challenge")
    if not challenge: return RedirectResponse("/entrar?tipo=admin",303)
    conn=db(); row=conn.execute("SELECT * FROM admin_login_codes WHERE challenge=?",(challenge,)).fetchone()
    if not row or row["expires_at"]<=datetime.now(timezone.utc).isoformat() or row["attempts"]>=5:
        if row: conn.execute("DELETE FROM admin_login_codes WHERE challenge=?",(challenge,)); conn.commit()
        conn.close(); resp=RedirectResponse("/entrar?tipo=admin&erro=2fa_expirado",303); resp.delete_cookie("nowup_admin_challenge"); return resp
    valid=hmac.compare_digest(hashlib.sha256(code.strip().encode()).hexdigest(),row["code_hash"])
    if not valid:
        conn.execute("UPDATE admin_login_codes SET attempts=attempts+1 WHERE challenge=?",(challenge,)); conn.commit(); conn.close(); return RedirectResponse("/admin/codigo?erro=1",303)
    uid=row["user_id"]; conn.execute("DELETE FROM admin_login_codes WHERE challenge=?",(challenge,)); conn.commit(); conn.close(); resp=create_secure_session(uid,"/admin",admin=True); resp.delete_cookie("nowup_admin_challenge"); return resp

@router.get("/admin/entrar")
def force_admin_login(request: Request):
    token=request.cookies.get("nowup_session")
    if token:
        conn=db(); conn.execute("DELETE FROM sessions WHERE token=?",(token,)); conn.commit(); conn.close()
    resp=RedirectResponse("/entrar?tipo=admin",303)
    resp.delete_cookie("nowup_session")
    return resp
