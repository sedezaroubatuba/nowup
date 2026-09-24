from __future__ import annotations
import os, re, io, hmac, hashlib, secrets, sqlite3, unicodedata, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from urllib.request import Request as URLRequest, urlopen
from urllib.error import HTTPError, URLError

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from email_validator import validate_email, EmailNotValidError
from admin_customization import router as admin_customization_router
from mailing import send_verification
from email_verification import router as email_verification_router
from password_reset import router as password_reset_router

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("NOWUP_DB", BASE / "data" / "nowup.db"))
UPLOAD_DIR = Path(os.getenv("NOWUP_UPLOAD_DIR", BASE / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SESSION_DAYS = 30
MAX_PHOTOS = 10
MAX_UPLOAD = 5 * 1024 * 1024
ADMIN_SESSION_MINUTES = 30

app = FastAPI(title="NowUp", version="1.0.0")
app.include_router(admin_customization_router)
app.include_router(email_verification_router)
app.include_router(password_reset_router)
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        from urllib.parse import urlsplit
        expected = os.getenv("NOWUP_BASE_URL", "").strip().rstrip("/")
        expected_origin = (urlsplit(expected).scheme + "://" + urlsplit(expected).netloc) if expected else str(request.base_url).rstrip("/")
        source = request.headers.get("origin") or request.headers.get("referer", "")
        parsed = urlsplit(source)
        source_origin = parsed.scheme + "://" + parsed.netloc if parsed.scheme and parsed.netloc else ""
        if not source_origin or not hmac.compare_digest(source_origin, expected_origin):
            return JSONResponse({"detail": "Origem da requisição não autorizada"}, status_code=403)
    actor = current_user(request) if request.method == "POST" and request.url.path.startswith("/admin/") else None
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if os.getenv("NOWUP_HTTPS", "0") == "1":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if actor and actor["role"] == "admin" and response.status_code < 400:
        conn = db()
        conn.execute("INSERT INTO admin_audit(user_id,action,created_at) VALUES(?,?,?)",
                     (actor["id"], request.url.path[:250], now_iso()))
        conn.commit(); conn.close()
    return response

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
templates = Jinja2Templates(directory=str(BASE / "templates"))


def now_iso():
    return datetime.now(timezone.utc).isoformat()

def normalize_email(raw: str):
    try:
        result = validate_email((raw or "").strip(), check_deliverability=True)
        return result.normalized.lower()
    except EmailNotValidError:
        return None

def normalize_phone(raw: str):
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    return digits if len(digits) in (10, 11) else None

def get_settings(conn=None):
    owns = conn is None
    conn = conn or db()
    rows = conn.execute("SELECT key,value FROM site_settings").fetchall()
    data = {r["key"]: r["value"] for r in rows}
    if owns:
        conn.close()
    return data

def email_service_configured():
    return bool(
        os.getenv("BREVO_API_KEY", "").strip()
        and os.getenv("NOWUP_EMAIL_FROM", "").strip()
        and os.getenv("NOWUP_BASE_URL", "").strip()
    )

def ensure_column(conn, table: str, name: str, definition: str):
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

def slugify(value: str):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or secrets.token_hex(4)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_password(password: str, salt: Optional[str]=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 240_000)
    return f"{salt}${digest.hex()}"

def verify_password(password: str, stored: str):
    try:
        salt, digest = stored.split("$", 1)
        calc = hash_password(password, salt).split("$",1)[1]
        return hmac.compare_digest(calc, digest)
    except Exception:
        return False

def mask_doc(doc: str):
    digits = re.sub(r"\D", "", doc or "")
    if len(digits) == 11:
        return f"***.{digits[3:6]}.{digits[6:9]}-**"
    if len(digits) == 14:
        return f"**.{digits[2:5]}.{digits[5:8]}/****-**"
    return "Documento verificado" if digits else ""

def wa_link(phone: str, text: str):
    digits = re.sub(r"\D", "", phone or "")
    if digits and not digits.startswith("55"):
        digits = "55" + digits
    return f"https://wa.me/{digits}?text={quote(text)}" if digits else "#"

def unique_slug(conn, name: str, table="professionals"):
    base = slugify(name); candidate = base; i = 2
    while conn.execute(f"SELECT 1 FROM {table} WHERE slug=?", (candidate,)).fetchone():
        candidate = f"{base}-{i}"; i += 1
    return candidate

def current_user(request: Request):
    token = request.cookies.get("nowup_session")
    if not token: return None
    conn = db()
    row = conn.execute("""
      SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
      WHERE s.token=? AND s.expires_at > ? AND u.is_active=1
    """, (token, now_iso())).fetchone()
    conn.close()
    return dict(row) if row else None

def require_user(request: Request, role: Optional[str]=None):
    u = current_user(request)
    if not u:
        raise HTTPException(401, "Faça login para continuar")
    if role and u["role"] != role:
        raise HTTPException(403, "Acesso não autorizado")
    return u

def context(request: Request, **kwargs):
    conn = db()
    cats = conn.execute("SELECT * FROM categories WHERE active=1 ORDER BY sort_order,name").fetchall()
    banners = conn.execute("SELECT * FROM banners WHERE active=1 ORDER BY id DESC LIMIT 3").fetchall()
    settings = get_settings(conn)
    conn.close()
    return {
        "request": request,
        "user": current_user(request),
        "categories": cats,
        "banners": banners,
        "settings": settings,
        "email_service_ready": email_service_configured(),
        **kwargs
    }

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      role TEXT NOT NULL CHECK(role IN ('customer','professional','admin')),
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      phone TEXT DEFAULT '',
      password_hash TEXT NOT NULL,
      is_active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions(
      token TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      expires_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS categories(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      slug TEXT NOT NULL UNIQUE,
      icon TEXT DEFAULT '🛠️',
      active INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 100
    );
    CREATE TABLE IF NOT EXISTS professionals(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
      slug TEXT NOT NULL UNIQUE,
      display_name TEXT NOT NULL,
      doc_type TEXT CHECK(doc_type IN ('CPF','CNPJ')),
      document TEXT DEFAULT '',
      whatsapp TEXT DEFAULT '',
      city TEXT DEFAULT '', neighborhood TEXT DEFAULT '', cep TEXT DEFAULT '',
      description TEXT DEFAULT '',
      services TEXT DEFAULT '',
      verified INTEGER NOT NULL DEFAULT 0,
      featured INTEGER NOT NULL DEFAULT 0,
      blocked INTEGER NOT NULL DEFAULT 0,
      views INTEGER NOT NULL DEFAULT 0,
      whatsapp_clicks INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS professional_categories(
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
      PRIMARY KEY(professional_id,category_id)
    );
    CREATE TABLE IF NOT EXISTS photos(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      filename TEXT NOT NULL,
      caption TEXT DEFAULT '',
      is_cover INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS posts(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      text TEXT NOT NULL,
      photo_filename TEXT DEFAULT '',
      post_type TEXT NOT NULL DEFAULT 'post',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS reviews(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
      comment TEXT DEFAULT '',
      created_at TEXT NOT NULL,
      UNIQUE(customer_id,professional_id)
    );
    CREATE TABLE IF NOT EXISTS reports(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      reason TEXT NOT NULL,
      details TEXT DEFAULT '',
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS suggestions(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
      name TEXT DEFAULT '', email TEXT DEFAULT '', message TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS banners(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      subtitle TEXT DEFAULT '',
      link TEXT DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS password_resets(
      user_id INTEGER PRIMARY KEY, token_hash TEXT NOT NULL,
      expires_at TEXT NOT NULL, requested_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS admin_audit(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS site_settings(
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
    """)
    ensure_column(conn, "users", "email_verified", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "users", "verification_token", "TEXT DEFAULT ''")
    ensure_column(conn, "users", "verification_expires_at", "TEXT DEFAULT ''")
    defaults = {
      "brand_name": "NowUp",
      "primary_color": "#2457e6",
      "accent_color": "#ff8a32",
      "font_family": "Inter",
      "hero_title": "Encontre quem resolve.",
      "hero_subtitle": "Busque profissionais por serviço e localização. Veja trabalhos recentes, avaliações e fale direto pelo WhatsApp.",
      "public_email": "",
      "support_whatsapp": ""
    }
    for key, value in defaults.items():
        conn.execute("INSERT OR IGNORE INTO site_settings(key,value) VALUES(?,?)", (key,value))
    default_categories = [
      ("Encanador","🔧"),("Eletricista","⚡"),("Pedreiro","🧱"),("Serralheiro","⚙️"),
      ("Limpeza de estofado","🛋️"),("Pet Shop","🐾"),("Veterinário","🩺"),("Vidraceiro","🪟"),
      ("Pintor","🎨"),("Chaveiro","🔑"),("Jardineiro","🌿"),("Ar-condicionado","❄️"),("Outros","📌")
    ]
    for i,(name,icon) in enumerate(default_categories,1):
        conn.execute("INSERT OR IGNORE INTO categories(name,slug,icon,sort_order) VALUES(?,?,?,?)",(name,slugify(name),icon,i))
    admin_email = os.getenv("NOWUP_ADMIN_EMAIL", "").strip().lower()
    admin_pass = os.getenv("NOWUP_ADMIN_PASSWORD", "")
    if admin_email and admin_pass and len(admin_pass) >= 12:
        admin = conn.execute("SELECT id,role FROM users WHERE email=?", (admin_email,)).fetchone()
        if not admin:
            conn.execute("INSERT INTO users(role,name,email,password_hash,email_verified,created_at) VALUES('admin','Administrador NowUp',?,?,1,?)",
                         (admin_email, hash_password(admin_pass), now_iso()))
        elif admin["role"] != "admin":
            raise RuntimeError("NOWUP_ADMIN_EMAIL já pertence a outra conta")
    elif not conn.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
        raise RuntimeError("Configure NOWUP_ADMIN_EMAIL e NOWUP_ADMIN_PASSWORD (mínimo 12 caracteres) no Render")
    if not conn.execute("SELECT 1 FROM banners").fetchone():
        conn.execute("INSERT INTO banners(title,subtitle,created_at) VALUES(?,?,?)",
                     ("Divulgue sua empresa na NowUp","Espaço para publicidade por cidade ou categoria.",now_iso()))
    conn.commit(); conn.close()

@app.on_event("startup")
def startup(): init_db()

@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str="", city: str="", category: str=""):
    conn = db()
    params=[]; where=["p.blocked=0"]
    if q:
        where.append("(p.display_name LIKE ? OR p.services LIKE ? OR p.description LIKE ?)")
        like=f"%{q}%"; params += [like,like,like]
    if city:
        where.append("p.city LIKE ?"); params.append(f"%{city}%")
    if category:
        where.append("EXISTS(SELECT 1 FROM professional_categories pc JOIN categories c ON c.id=pc.category_id WHERE pc.professional_id=p.id AND c.slug=?)")
        params.append(category)
    rows = conn.execute(f"""
      SELECT p.*, u.name as owner_name,
       COALESCE((SELECT ROUND(AVG(stars),1) FROM reviews r WHERE r.professional_id=p.id),0) rating,
       (SELECT COUNT(*) FROM reviews r WHERE r.professional_id=p.id) review_count,
       (SELECT filename FROM photos ph WHERE ph.professional_id=p.id ORDER BY is_cover DESC,id ASC LIMIT 1) cover
      FROM professionals p JOIN users u ON u.id=p.user_id
      WHERE {' AND '.join(where)}
      ORDER BY p.featured DESC,p.verified DESC,rating DESC,p.id DESC LIMIT 12
    """, params).fetchall()
    posts = conn.execute("""
      SELECT po.*,p.display_name,p.slug,p.city,
      (SELECT filename FROM photos ph WHERE ph.professional_id=p.id ORDER BY is_cover DESC,id ASC LIMIT 1) avatar
      FROM posts po JOIN professionals p ON p.id=po.professional_id
      WHERE p.blocked=0 AND po.post_type='post' ORDER BY po.id DESC LIMIT 12
    """).fetchall()
    statuses = conn.execute("""
      SELECT po.*,p.display_name,p.slug,
      COALESCE(po.photo_filename,(SELECT filename FROM photos ph WHERE ph.professional_id=p.id ORDER BY is_cover DESC,id ASC LIMIT 1)) status_image
      FROM posts po JOIN professionals p ON p.id=po.professional_id
      WHERE p.blocked=0 AND po.post_type='status' AND po.created_at > ? ORDER BY po.id DESC LIMIT 20
    """, ((datetime.now(timezone.utc)-timedelta(hours=24)).isoformat(),)).fetchall()
    conn.close()
    return templates.TemplateResponse("home.html", context(request, professionals=rows, posts=posts, statuses=statuses, q=q, city=city, category=category))

@app.get("/profissionais", response_class=HTMLResponse)
def professionals(request: Request, category: str="", city: str="", neighborhood: str="", cep: str="", q: str=""):
    conn=db(); where=["p.blocked=0"]; params=[]
    for field,val in [("p.city",city),("p.neighborhood",neighborhood),("p.cep",cep)]:
        if val: where.append(f"{field} LIKE ?"); params.append(f"%{val}%")
    if q:
        where.append("(p.display_name LIKE ? OR p.services LIKE ? OR p.description LIKE ?)"); like=f"%{q}%"; params += [like,like,like]
    if category:
        where.append("EXISTS(SELECT 1 FROM professional_categories pc JOIN categories c ON c.id=pc.category_id WHERE pc.professional_id=p.id AND c.slug=?)"); params.append(category)
    rows=conn.execute(f"""
      SELECT p.*,
       COALESCE((SELECT ROUND(AVG(stars),1) FROM reviews r WHERE r.professional_id=p.id),0) rating,
       (SELECT COUNT(*) FROM reviews r WHERE r.professional_id=p.id) review_count,
       (SELECT filename FROM photos ph WHERE ph.professional_id=p.id ORDER BY is_cover DESC,id ASC LIMIT 1) cover
      FROM professionals p WHERE {' AND '.join(where)}
      ORDER BY p.featured DESC,p.verified DESC,rating DESC,p.id DESC LIMIT 100
    """,params).fetchall(); conn.close()
    return templates.TemplateResponse("professionals.html", context(request, professionals=rows, filters={"category":category,"city":city,"neighborhood":neighborhood,"cep":cep,"q":q}))

@app.get("/p/{slug}", response_class=HTMLResponse)
def profile(request: Request, slug: str):
    conn=db()
    p=conn.execute("""
      SELECT p.*,
       COALESCE((SELECT ROUND(AVG(stars),1) FROM reviews r WHERE r.professional_id=p.id),0) rating,
       (SELECT COUNT(*) FROM reviews r WHERE r.professional_id=p.id) review_count
      FROM professionals p WHERE p.slug=? AND p.blocked=0
    """,(slug,)).fetchone()
    if not p: conn.close(); raise HTTPException(404,"Profissional não encontrado")
    conn.execute("UPDATE professionals SET views=views+1 WHERE id=?",(p["id"],)); conn.commit()
    photos=conn.execute("SELECT * FROM photos WHERE professional_id=? ORDER BY is_cover DESC,id DESC",(p["id"],)).fetchall()
    posts=conn.execute("SELECT * FROM posts WHERE professional_id=? ORDER BY id DESC",(p["id"],)).fetchall()
    reviews=conn.execute("SELECT r.*,u.name FROM reviews r JOIN users u ON u.id=r.customer_id WHERE r.professional_id=? ORDER BY r.id DESC",(p["id"],)).fetchall()
    cats=conn.execute("SELECT c.* FROM categories c JOIN professional_categories pc ON pc.category_id=c.id WHERE pc.professional_id=?",(p["id"],)).fetchall()
    conn.close()
    pub=dict(p); pub["document_masked"]=mask_doc(pub["document"]); pub["wa_link"]=wa_link(pub["whatsapp"],f"Olá! Encontrei seu perfil na NowUp e gostaria de saber mais sobre seus serviços.")
    return templates.TemplateResponse("profile.html", context(request, pro=pub, photos=photos, posts=posts, reviews=reviews, pro_categories=cats))

@app.post("/p/{slug}/whatsapp")
def whatsapp_click(slug: str):
    conn=db(); p=conn.execute("SELECT * FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p: conn.close(); raise HTTPException(404)
    conn.execute("UPDATE professionals SET whatsapp_clicks=whatsapp_clicks+1 WHERE id=?",(p["id"],)); conn.commit(); conn.close()
    return RedirectResponse(wa_link(p["whatsapp"],"Olá! Encontrei seu perfil na NowUp e gostaria de um orçamento."), status_code=303)

@app.get("/cadastro/cliente", response_class=HTMLResponse)
def signup_customer_page(request: Request): return templates.TemplateResponse("signup_customer.html", context(request))

@app.post("/cadastro/cliente")
def signup_customer(name: str=Form(...), email: str=Form(...), phone: str=Form(""), password: str=Form(...), password_confirm: str=Form(...), accept_terms: Optional[str]=Form(None)):
    normalized_email=normalize_email(email)
    admin_email=os.getenv("NOWUP_ADMIN_EMAIL", "").strip().lower()
    if not normalized_email:
        return RedirectResponse("/cadastro/cliente?erro=email_invalido",303)
    if normalized_email == admin_email:
        return RedirectResponse("/cadastro/cliente?erro=admin",303)
    if phone and not normalize_phone(phone):
        return RedirectResponse("/cadastro/cliente?erro=telefone",303)
    if len(password)<8:
        return RedirectResponse("/cadastro/cliente?erro=senha",303)
    if password != password_confirm:
        return RedirectResponse("/cadastro/cliente?erro=confirmacao",303)
    if not accept_terms:
        return RedirectResponse("/cadastro/cliente?erro=termos",303)
    verify_required=email_service_configured()
    token=secrets.token_urlsafe(32) if verify_required else ""
    expires=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat() if verify_required else ""
    conn=db()
    try:
        cur=conn.execute(
            "INSERT INTO users(role,name,email,phone,password_hash,email_verified,verification_token,verification_expires_at,created_at) VALUES('customer',?,?,?,?,?,?,?,?)",
            (name.strip(),normalized_email,phone.strip(),hash_password(password),0 if verify_required else 1,token,expires,now_iso())
        )
        conn.commit(); uid=cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close(); return RedirectResponse("/cadastro/cliente?erro=email",303)
    conn.close()
    if verify_required:
        send_verification(normalized_email,name.strip(),token)
        return RedirectResponse("/cadastro/aguardando",303)
    return create_session_response(uid,"/cadastro/sucesso?tipo=cliente")

@app.get("/cadastro/profissional", response_class=HTMLResponse)
def signup_pro_page(request: Request):
    return templates.TemplateResponse("signup_professional.html", context(request))

@app.post("/cadastro/profissional")
def signup_professional(name: str=Form(...), email: str=Form(...), phone: str=Form(...), password: str=Form(...), password_confirm: str=Form(...), accept_terms: Optional[str]=Form(None), doc_type: str=Form(...), document: str=Form(...), city: str=Form(...), neighborhood: str=Form(""), cep: str=Form(""), description: str=Form(""), services: str=Form(""), category_ids: list[int]=Form(default=[])):
    normalized_email=normalize_email(email)
    admin_email=os.getenv("NOWUP_ADMIN_EMAIL", "").strip().lower()
    if not normalized_email:
        return RedirectResponse("/cadastro/profissional?erro=email_invalido",303)
    if normalized_email == admin_email:
        return RedirectResponse("/cadastro/profissional?erro=admin",303)
    if not normalize_phone(phone):
        return RedirectResponse("/cadastro/profissional?erro=telefone",303)
    if len(password)<8:
        return RedirectResponse("/cadastro/profissional?erro=senha",303)
    if password != password_confirm:
        return RedirectResponse("/cadastro/profissional?erro=confirmacao",303)
    if not accept_terms:
        return RedirectResponse("/cadastro/profissional?erro=termos",303)
    verify_required=email_service_configured()
    token=secrets.token_urlsafe(32) if verify_required else ""
    expires=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat() if verify_required else ""
    conn=db()
    try:
        cur=conn.execute(
            "INSERT INTO users(role,name,email,phone,password_hash,email_verified,verification_token,verification_expires_at,created_at) VALUES('professional',?,?,?,?,?,?,?,?)",
            (name.strip(),normalized_email,phone.strip(),hash_password(password),0 if verify_required else 1,token,expires,now_iso())
        ); uid=cur.lastrowid
        slug=unique_slug(conn,name)
        cur=conn.execute("INSERT INTO professionals(user_id,slug,display_name,doc_type,document,whatsapp,city,neighborhood,cep,description,services,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                         (uid,slug,name.strip(),doc_type,document.strip(),phone.strip(),city.strip(),neighborhood.strip(),cep.strip(),description.strip(),services.strip(),now_iso())); pid=cur.lastrowid
        for cid in category_ids[:5]:
            conn.execute("INSERT OR IGNORE INTO professional_categories(professional_id,category_id) VALUES(?,?)",(pid,cid))
        if verify_required:
            conn.execute("UPDATE professionals SET blocked=1 WHERE id=?",(pid,))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback(); conn.close(); return RedirectResponse("/cadastro/profissional?erro=email",303)
    conn.close()
    if verify_required:
        send_verification(normalized_email,name.strip(),token)
        return RedirectResponse("/cadastro/aguardando",303)
    return create_session_response(uid,"/cadastro/sucesso?tipo=profissional")

@app.get("/cadastro/sucesso", response_class=HTMLResponse)
def signup_success(request: Request, tipo: str="cliente"):
    u=current_user(request)
    if not u:
        return RedirectResponse("/entrar",303)
    return templates.TemplateResponse("signup_success.html", context(request, tipo=tipo))

def create_session_response(uid:int, dest:str):
    token=secrets.token_urlsafe(32); expires=(datetime.now(timezone.utc)+timedelta(days=SESSION_DAYS)).isoformat()
    conn=db(); conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",(token,uid,expires)); conn.commit(); conn.close()
    resp=RedirectResponse(dest,303); resp.set_cookie("nowup_session",token,max_age=SESSION_DAYS*86400,httponly=True,samesite="lax",secure=os.getenv("NOWUP_HTTPS","0")=="1")
    return resp

@app.get("/entrar", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse("login.html", context(request))

@app.post("/entrar")
def login(email: str=Form(...), password: str=Form(...)):
    conn=db(); u=conn.execute("SELECT * FROM users WHERE email=? AND is_active=1",(email.strip().lower(),)).fetchone(); conn.close()
    if not u or not verify_password(password,u["password_hash"]): return RedirectResponse("/entrar?erro=1",303)
    dest="/admin" if u["role"]=="admin" else ("/painel" if u["role"]=="professional" else "/")
    return create_session_response(u["id"],dest)

@app.post("/sair")
def logout(request: Request):
    token=request.cookies.get("nowup_session")
    if token:
        conn=db(); conn.execute("DELETE FROM sessions WHERE token=?",(token,)); conn.commit(); conn.close()
    resp=RedirectResponse("/",303); resp.delete_cookie("nowup_session"); return resp

@app.get("/painel", response_class=HTMLResponse)
def pro_panel(request: Request):
    u=require_user(request,"professional"); conn=db()
    p=conn.execute("SELECT * FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    photos=conn.execute("SELECT * FROM photos WHERE professional_id=? ORDER BY is_cover DESC,id DESC",(p["id"],)).fetchall()
    posts=conn.execute("SELECT * FROM posts WHERE professional_id=? ORDER BY id DESC LIMIT 20",(p["id"],)).fetchall()
    selected={r[0] for r in conn.execute("SELECT category_id FROM professional_categories WHERE professional_id=?",(p["id"],)).fetchall()}
    conn.close()
    return templates.TemplateResponse("pro_panel.html", context(request, pro=p, photos=photos, posts=posts, selected=selected, max_photos=MAX_PHOTOS))

@app.post("/painel/perfil")
def pro_update(request: Request, display_name: str=Form(...), whatsapp: str=Form(...), city: str=Form(...), neighborhood: str=Form(""), cep: str=Form(""), description: str=Form(""), services: str=Form(""), category_ids: list[int]=Form(default=[])):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    conn.execute("UPDATE professionals SET display_name=?,whatsapp=?,city=?,neighborhood=?,cep=?,description=?,services=? WHERE id=?",(display_name,whatsapp,city,neighborhood,cep,description,services,p["id"]))
    conn.execute("DELETE FROM professional_categories WHERE professional_id=?",(p["id"],))
    for cid in category_ids[:5]: conn.execute("INSERT OR IGNORE INTO professional_categories(professional_id,category_id) VALUES(?,?)",(p["id"],cid))
    conn.commit(); conn.close(); return RedirectResponse("/painel?ok=perfil",303)

def save_image(upload: UploadFile):
    data=upload.file.read(MAX_UPLOAD+1)
    if len(data)>MAX_UPLOAD: raise HTTPException(400,"Imagem maior que 5MB")
    try:
        im=Image.open(io.BytesIO(data)); im.verify()
        im=Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((1600,1600))
    except Exception: raise HTTPException(400,"Arquivo não é uma imagem válida")
    filename=secrets.token_hex(16)+".jpg"; im.save(UPLOAD_DIR/filename,"JPEG",quality=88,optimize=True)
    return filename

@app.post("/painel/fotos")
def upload_photo(request: Request, photo: UploadFile=File(...), caption: str=Form("")):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    count=conn.execute("SELECT COUNT(*) FROM photos WHERE professional_id=?",(p["id"],)).fetchone()[0]
    if count>=MAX_PHOTOS: conn.close(); return RedirectResponse("/painel?erro=limite-fotos",303)
    fn=save_image(photo); is_cover=1 if count==0 else 0
    conn.execute("INSERT INTO photos(professional_id,filename,caption,is_cover,created_at) VALUES(?,?,?,?,?)",(p["id"],fn,caption[:160],is_cover,now_iso())); conn.commit(); conn.close()
    return RedirectResponse("/painel?ok=foto",303)

@app.post("/painel/fotos/{photo_id}/capa")
def set_cover(request: Request, photo_id:int):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    ph=conn.execute("SELECT * FROM photos WHERE id=? AND professional_id=?",(photo_id,p["id"])).fetchone()
    if ph:
        conn.execute("UPDATE photos SET is_cover=0 WHERE professional_id=?",(p["id"],)); conn.execute("UPDATE photos SET is_cover=1 WHERE id=?",(photo_id,)); conn.commit()
    conn.close(); return RedirectResponse("/painel#fotos",303)

@app.post("/painel/fotos/{photo_id}/excluir")
def delete_photo(request: Request, photo_id:int):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone(); ph=conn.execute("SELECT * FROM photos WHERE id=? AND professional_id=?",(photo_id,p["id"])).fetchone()
    if ph:
        try: (UPLOAD_DIR/ph["filename"]).unlink(missing_ok=True)
        except: pass
        conn.execute("DELETE FROM photos WHERE id=?",(photo_id,)); conn.commit()
        if ph["is_cover"]:
            nxt=conn.execute("SELECT id FROM photos WHERE professional_id=? ORDER BY id LIMIT 1",(p["id"],)).fetchone()
            if nxt: conn.execute("UPDATE photos SET is_cover=1 WHERE id=?",(nxt["id"],)); conn.commit()
    conn.close(); return RedirectResponse("/painel#fotos",303)

@app.post("/painel/publicar")
def publish_post(request: Request, text: str=Form(...), post_type: str=Form("post"), photo: Optional[UploadFile]=File(None)):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone(); fn=""
    if post_type not in ("post","status"): post_type="post"
    if photo and photo.filename: fn=save_image(photo)
    conn.execute("INSERT INTO posts(professional_id,text,photo_filename,post_type,created_at) VALUES(?,?,?,?,?)",(p["id"],text[:500],fn,post_type,now_iso())); conn.commit(); conn.close(); return RedirectResponse("/painel?ok=post",303)

@app.post("/p/{slug}/avaliar")
def review(request: Request, slug:str, stars:int=Form(...), comment:str=Form("")):
    u=require_user(request,"customer"); stars=max(1,min(5,stars)); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p: conn.close(); raise HTTPException(404)
    conn.execute("""INSERT INTO reviews(customer_id,professional_id,stars,comment,created_at) VALUES(?,?,?,?,?)
                  ON CONFLICT(customer_id,professional_id) DO UPDATE SET stars=excluded.stars,comment=excluded.comment,created_at=excluded.created_at""",
                 (u["id"],p["id"],stars,comment[:500],now_iso())); conn.commit(); conn.close(); return RedirectResponse(f"/p/{slug}#avaliacoes",303)

@app.post("/p/{slug}/denunciar")
def report(request: Request, slug:str, reason:str=Form(...), details:str=Form("")):
    u=require_user(request,"customer"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE slug=?",(slug,)).fetchone()
    if not p: conn.close(); raise HTTPException(404)
    conn.execute("INSERT INTO reports(customer_id,professional_id,reason,details,created_at) VALUES(?,?,?,?,?)",(u["id"],p["id"],reason[:80],details[:1000],now_iso())); conn.commit(); conn.close(); return RedirectResponse(f"/p/{slug}?denuncia=ok",303)

@app.post("/sugestao")
def suggestion(request: Request, name:str=Form(""), email:str=Form(""), message:str=Form(...)):
    u=current_user(request); conn=db(); conn.execute("INSERT INTO suggestions(user_id,name,email,message,created_at) VALUES(?,?,?,?,?)",((u or {}).get("id"),name[:100],email[:150],message[:1000],now_iso())); conn.commit(); conn.close(); return RedirectResponse("/?sugestao=ok",303)

@app.get("/quem-somos", response_class=HTMLResponse)
def about(request: Request): return templates.TemplateResponse("about.html", context(request))
@app.get("/privacidade", response_class=HTMLResponse)
def privacy(request: Request): return templates.TemplateResponse("privacy.html", context(request))
@app.get("/termos", response_class=HTMLResponse)
def terms(request: Request): return templates.TemplateResponse("terms.html", context(request))

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    require_user(request,"admin"); conn=db()
    stats={
      "professionals":conn.execute("SELECT COUNT(*) FROM professionals").fetchone()[0],
      "customers":conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
      "reports":conn.execute("SELECT COUNT(*) FROM reports WHERE status='pending'").fetchone()[0],
      "wa":conn.execute("SELECT COALESCE(SUM(whatsapp_clicks),0) FROM professionals").fetchone()[0],
      "views":conn.execute("SELECT COALESCE(SUM(views),0) FROM professionals").fetchone()[0],
    }
    pros=conn.execute("SELECT p.*,u.email,u.email_verified FROM professionals p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC LIMIT 50").fetchall()
    clients=conn.execute("SELECT id,name,email,phone,is_active,email_verified,created_at FROM users WHERE role='customer' ORDER BY id DESC LIMIT 100").fetchall()
    admin_categories=conn.execute("SELECT * FROM categories ORDER BY sort_order,name").fetchall()
    reports=conn.execute("SELECT r.*,u.name customer,p.display_name professional FROM reports r JOIN users u ON u.id=r.customer_id JOIN professionals p ON p.id=r.professional_id ORDER BY r.id DESC LIMIT 50").fetchall()
    suggestions=conn.execute("SELECT * FROM suggestions ORDER BY id DESC LIMIT 30").fetchall(); banners=conn.execute("SELECT * FROM banners ORDER BY id DESC").fetchall(); conn.close()
    return templates.TemplateResponse("admin.html", context(request, stats=stats, pros=pros, clients=clients, admin_categories=admin_categories, reports=reports, suggestions=suggestions, admin_banners=banners))

@app.post("/admin/categorias")
def admin_add_category(request: Request, name:str=Form(...), icon:str=Form("🛠️")):
    require_user(request,"admin"); conn=db()
    try: conn.execute("INSERT INTO categories(name,slug,icon,sort_order) VALUES(?,?,?,999)",(name.strip(),slugify(name),icon[:8])); conn.commit()
    except sqlite3.IntegrityError: pass
    conn.close(); return RedirectResponse("/admin#categorias",303)

@app.post("/admin/categorias/{cid}/alternar")
def admin_toggle_category(request: Request, cid:int):
    require_user(request,"admin"); conn=db(); conn.execute("UPDATE categories SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(cid,)); conn.commit(); conn.close(); return RedirectResponse("/admin#categorias",303)

@app.post("/admin/clientes/{uid}/alternar")
def admin_toggle_client(request: Request, uid:int):
    require_user(request,"admin"); conn=db(); conn.execute("UPDATE users SET is_active=CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE id=? AND role='customer'",(uid,)); conn.execute("DELETE FROM sessions WHERE user_id=? AND (SELECT is_active FROM users WHERE id=?)=0",(uid,uid)); conn.commit(); conn.close(); return RedirectResponse("/admin#clientes",303)

@app.post("/admin/categorias/{cid}/excluir")
def admin_delete_category(request: Request, cid:int):
    require_user(request,"admin"); conn=db(); conn.execute("DELETE FROM categories WHERE id=?",(cid,)); conn.commit(); conn.close(); return RedirectResponse("/admin#categorias",303)

@app.post("/admin/profissionais/{pid}/{action}")
def admin_pro_action(request: Request, pid:int, action:str):
    require_user(request,"admin"); conn=db()
    if action=="verificar": conn.execute("UPDATE professionals SET verified=CASE verified WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(pid,))
    elif action=="destaque": conn.execute("UPDATE professionals SET featured=CASE featured WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(pid,))
    elif action=="bloquear": conn.execute("UPDATE professionals SET blocked=CASE blocked WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(pid,))
    else: conn.close(); raise HTTPException(400)
    conn.commit(); conn.close(); return RedirectResponse("/admin#profissionais",303)

@app.post("/admin/denuncias/{rid}/{status}")
def admin_report_action(request: Request, rid:int, status:str):
    require_user(request,"admin")
    if status not in ('pending','reviewed','resolved','archived'): raise HTTPException(400)
    conn=db(); conn.execute("UPDATE reports SET status=? WHERE id=?",(status,rid)); conn.commit(); conn.close(); return RedirectResponse("/admin#denuncias",303)

@app.post("/admin/banners")
def admin_banner_add(request: Request, title:str=Form(...), subtitle:str=Form(""), link:str=Form("")):
    require_user(request,"admin"); conn=db(); conn.execute("INSERT INTO banners(title,subtitle,link,created_at) VALUES(?,?,?,?)",(title[:120],subtitle[:240],link[:300],now_iso())); conn.commit(); conn.close(); return RedirectResponse("/admin#publicidade",303)

@app.post("/admin/banners/{bid}/alternar")
def admin_banner_toggle(request: Request, bid:int):
    require_user(request,"admin"); conn=db(); conn.execute("UPDATE banners SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(bid,)); conn.commit(); conn.close(); return RedirectResponse("/admin#publicidade",303)

@app.get("/health")
def health(): return JSONResponse({"ok":True,"service":"NowUp"})
