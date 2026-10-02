from __future__ import annotations
import os, re, io, hmac, hashlib, secrets, sqlite3, unicodedata, json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse
from urllib.request import Request as URLRequest, urlopen
from urllib.error import HTTPError, URLError

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from email_validator import validate_email, EmailNotValidError
from admin_customization import router as admin_customization_router
from mailing import send_verification, send_email
from email_verification import router as email_verification_router
from cms import router as cms_router, init_cms_db

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("NOWUP_DB", BASE / "data" / "nowup.db"))
UPLOAD_DIR = Path(os.getenv("NOWUP_UPLOAD_DIR", BASE / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
# Mantém clientes e profissionais conectados até escolherem sair.
# O prazo longo existe apenas como proteção técnica do cookie/sessão.
SESSION_DAYS = 3650
MAX_PHOTOS = 10
MAX_UPLOAD = 5 * 1024 * 1024
ADMIN_SESSION_MINUTES = 30

app = FastAPI(title="NowUp", version="1.0.0")
app.include_router(admin_customization_router)
app.include_router(email_verification_router)
app.include_router(cms_router)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
templates = Jinja2Templates(directory=str(BASE / "templates"))

@app.middleware("http")
async def security_headers_and_csrf(request: Request, call_next):
    # Proteção CSRF por origem sem consumir formulários multipart.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin=request.headers.get("origin"); referer=request.headers.get("referer"); host=request.headers.get("host","")
        origin_host=urlparse(origin).netloc if origin else ""; referer_host=urlparse(referer).netloc if referer else ""
        if (origin_host and host and origin_host!=host) or (not origin_host and referer_host and host and referer_host!=host):
            return JSONResponse({"detail":"Requisição bloqueada por segurança"},status_code=403)
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=(self)"
    return response


def now_iso():
    return datetime.now(timezone.utc).isoformat()

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
DAYS = ["segunda","terca","quarta","quinta","sexta","sabado","domingo"]
DAY_LABELS = {"segunda":"Segunda", "terca":"Terça", "quarta":"Quarta", "quinta":"Quinta", "sexta":"Sexta", "sabado":"Sábado", "domingo":"Domingo"}

def parse_business_hours(raw: str):
    try:
        data=json.loads(raw or "{}")
        return data if isinstance(data,dict) else {}
    except (ValueError,TypeError):
        return {}

def business_hours_lines(pro):
    schedule=parse_business_hours(pro["business_hours"]); lines=[]
    for day in DAYS:
        row=schedule.get(day,{})
        if row.get("enabled"):
            lines.append(f"{DAY_LABELS[day]}: {row.get('start','09:00')}–{row.get('end','18:00')}")
    return lines

def shop_status(pro):
    manual=pro["business_status"] or "open"
    labels={"paused":"Loja pausada", "temporarily_closed":"Fechada temporariamente", "vacation":"Fechada para férias", "ad_paused":"Anúncio pausado"}
    if manual in labels:
        return {"open":False,"code":manual,"label":labels[manual],"detail":"Fechada manualmente pelo estabelecimento"}
    now=datetime.now(SAO_PAULO_TZ); schedule=parse_business_hours(pro["business_hours"])
    if not schedule:
        return {"open":True,"code":"open","label":"Loja aberta","detail":"Horário ainda não configurado"}
    minute=now.hour*60+now.minute; today=now.weekday(); opened=False
    def interval(day_index):
        row=schedule.get(DAYS[day_index],{})
        if not row.get("enabled"): return None
        try:
            sh,sm=map(int,row.get("start","09:00").split(":")); eh,em=map(int,row.get("end","18:00").split(":"))
            return sh*60+sm,eh*60+em
        except (ValueError,AttributeError): return None
    current=interval(today)
    if current:
        start,end=current; opened=(start<=minute<end) if end>start else minute>=start
    previous=interval((today-1)%7)
    if previous:
        start,end=previous
        if end<=start and minute<end: opened=True
    return {"open":opened,"code":"open" if opened else "closed","label":"Loja aberta" if opened else "Loja fechada","detail":now.strftime("Horário de agora: %H:%M")}

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

def active_cities(settings=None):
    settings = settings or get_settings()
    cities = [c.strip() for c in settings.get("active_cities", "Ubatuba").split(",") if c.strip()]
    return cities or ["Ubatuba"]

def email_service_configured():
    return bool(
        os.getenv("BREVO_API_KEY", "").strip()
        and os.getenv("NOWUP_EMAIL_FROM", "").strip()
        and os.getenv("NOWUP_BASE_URL", "").strip()
    )

def verification_token():
    return secrets.token_urlsafe(32), (datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()

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

def clean_link(raw: str):
    value=(raw or "").strip()[:500]
    if value.startswith("/") or value.startswith("https://") or value.startswith("http://"):
        return value
    return ""

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
    banners = conn.execute("SELECT * FROM banners WHERE active=1 AND image_filename!='' ORDER BY sort_order,id LIMIT 3").fetchall()
    business_slides = conn.execute("SELECT id,slug,display_name,slide_image_filename FROM professionals WHERE blocked=0 AND in_slider=1 AND slide_image_filename!='' ORDER BY id DESC LIMIT 10").fetchall()
    settings = get_settings(conn)
    conn.close()
    return {
        "request": request,
        "user": current_user(request),
        "categories": cats,
        "banners": banners,
        "business_slides": business_slides,
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
    CREATE TABLE IF NOT EXISTS admin_login_codes(
      challenge TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      code_hash TEXT NOT NULL,
      attempts INTEGER NOT NULL DEFAULT 0,
      expires_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS password_reset_tokens(
      token_hash TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      expires_at TEXT NOT NULL,
      used INTEGER NOT NULL DEFAULT 0
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
    CREATE TABLE IF NOT EXISTS favorites(
      customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      created_at TEXT NOT NULL,
      PRIMARY KEY(customer_id,professional_id)
    );
    CREATE TABLE IF NOT EXISTS notifications(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      title TEXT NOT NULL,
      message TEXT NOT NULL DEFAULT '',
      link TEXT NOT NULL DEFAULT '',
      read_at TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id,read_at,id);
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
      image_filename TEXT DEFAULT '',
      sort_order INTEGER NOT NULL DEFAULT 100,
      clicks INTEGER NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS site_settings(
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS analytics_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      event_type TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_analytics_professional_date
      ON analytics_events(professional_id,created_at);
    CREATE INDEX IF NOT EXISTS idx_analytics_type
      ON analytics_events(event_type);
    CREATE TABLE IF NOT EXISTS daily_home_visits(
      visit_date TEXT NOT NULL,
      visitor_key TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY(visit_date,visitor_key)
    );
    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      customer_name TEXT NOT NULL DEFAULT '',
      customer_phone TEXT NOT NULL DEFAULT '',
      fulfillment_type TEXT NOT NULL DEFAULT 'pickup',
      payment_method TEXT NOT NULL DEFAULT 'pix',
      address TEXT NOT NULL DEFAULT '',
      notes TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'new',
      total_cents INTEGER NOT NULL DEFAULT 0,
      whatsapp_opened INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS order_items(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
      product_id INTEGER,
      product_name TEXT NOT NULL,
      quantity INTEGER NOT NULL DEFAULT 1,
      unit_price_cents INTEGER NOT NULL DEFAULT 0,
      notes TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS product_options(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      price_cents INTEGER NOT NULL DEFAULT 0,
      available INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 100
    );
    CREATE TABLE IF NOT EXISTS order_item_options(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_item_id INTEGER NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
      option_id INTEGER,
      option_name TEXT NOT NULL,
      price_cents INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS order_status_history(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_orders_professional_date
      ON orders(professional_id,created_at);
    CREATE INDEX IF NOT EXISTS idx_orders_professional_status
      ON orders(professional_id,status);
    CREATE INDEX IF NOT EXISTS idx_order_items_order
      ON order_items(order_id);
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      description TEXT NOT NULL DEFAULT '',
      category TEXT NOT NULL DEFAULT 'Geral',
      price_cents INTEGER NOT NULL DEFAULT 0,
      image_filename TEXT NOT NULL DEFAULT '',
      available INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 100,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS product_categories(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      sort_order INTEGER NOT NULL DEFAULT 100,
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      UNIQUE(professional_id,name)
    );
    CREATE INDEX IF NOT EXISTS idx_products_professional
      ON products(professional_id,available,sort_order,id);
    CREATE INDEX IF NOT EXISTS idx_product_categories_professional
      ON product_categories(professional_id,active,sort_order,id);
    """)
    ensure_column(conn, "users", "email_verified", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "users", "verification_token", "TEXT DEFAULT ''")
    ensure_column(conn, "users", "verification_expires_at", "TEXT DEFAULT ''")
    ensure_column(conn, "users", "address", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "users", "neighborhood", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "users", "preferred_payment", "TEXT NOT NULL DEFAULT 'pix'")
    ensure_column(conn, "professionals", "business_type", "TEXT NOT NULL DEFAULT 'professional'")
    ensure_column(conn, "professionals", "external_url", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "menu_url", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "menu_clicks", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "professionals", "external_clicks", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "professionals", "avatar_filename", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "cover_filename", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "address", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "hide_address", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "professionals", "service_area", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "opening_hours", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "business_hours", "TEXT NOT NULL DEFAULT '{}'")
    ensure_column(conn, "professionals", "business_status", "TEXT NOT NULL DEFAULT 'open'")
    ensure_column(conn, "professionals", "instagram_url", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "facebook_url", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "website_url", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "whatsapp_message", "TEXT DEFAULT 'Olá! Encontrei você pelo NowUp e gostaria de saber mais.'")
    ensure_column(conn, "professionals", "is_demo", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "professionals", "in_slider", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "professionals", "featured_image_filename", "TEXT DEFAULT ''")
    ensure_column(conn, "professionals", "slide_image_filename", "TEXT DEFAULT ''")
    ensure_column(conn, "banners", "image_filename", "TEXT DEFAULT ''")
    ensure_column(conn, "banners", "sort_order", "INTEGER NOT NULL DEFAULT 100")
    ensure_column(conn, "banners", "clicks", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "banners", "template", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "banners", "background_color", "TEXT DEFAULT '#075bd8'")
    ensure_column(conn, "banners", "text_color", "TEXT DEFAULT '#ffffff'")
    ensure_column(conn, "banners", "font_family", "TEXT DEFAULT 'Inter'")
    ensure_column(conn, "banners", "brightness", "INTEGER NOT NULL DEFAULT 100")
    ensure_column(conn, "banners", "zoom", "INTEGER NOT NULL DEFAULT 100")
    ensure_column(conn, "banners", "position_x", "INTEGER NOT NULL DEFAULT 50")
    ensure_column(conn, "banners", "position_y", "INTEGER NOT NULL DEFAULT 50")
    ensure_column(conn, "banners", "desktop_height", "INTEGER NOT NULL DEFAULT 360")
    ensure_column(conn, "banners", "mobile_height", "INTEGER NOT NULL DEFAULT 240")
    ensure_column(conn, "orders", "payment_method", "TEXT NOT NULL DEFAULT 'pix'")
    ensure_column(conn, "orders", "order_code", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "orders", "subtotal_cents", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "orders", "delivery_fee_cents", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "orders", "neighborhood", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "orders", "address_reference", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "orders", "change_for_cents", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "orders", "customer_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL")
    ensure_column(conn, "orders", "tracking_token", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "orders", "cancellation_reason", "TEXT NOT NULL DEFAULT ''")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_tracking_token ON orders(tracking_token) WHERE tracking_token!=''")
    ensure_column(conn, "professionals", "delivery_fee_cents", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "professionals", "minimum_order_cents", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "professionals", "prep_minutes", "INTEGER NOT NULL DEFAULT 40")
    ensure_column(conn, "professionals", "allows_delivery", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "professionals", "allows_pickup", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "professionals", "pix_key", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "products", "promo_price_cents", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "products", "featured", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "products", "max_quantity", "INTEGER NOT NULL DEFAULT 99")
    defaults = {
      "brand_name": "NowUp",
      "primary_color": "#08131F",
      "accent_color": "#08BCEB",
      "theme_name": "noturno",
      "font_family": "Inter",
      "hero_title": "Encontre quem resolve.",
      "hero_subtitle": "Busque profissionais por serviço e localização. Veja trabalhos recentes, avaliações e fale direto pelo WhatsApp.",
      "hero_image_filename": "",
      "hero_brightness": "100",
      "hero_zoom": "100",
      "hero_position_x": "50",
      "hero_position_y": "50",
      "hero_desktop_height": "540",
      "hero_mobile_height": "540",
      "public_email": "",
      "support_whatsapp": ""
      ,"active_cities": "Ubatuba",
      "ticker_text": "",
      "ticker_enabled": "0",
      "ticker_color": "#e30613",
      "ticker_animation": "continuous",
      "slide_interval_seconds": "3"
    }
    for key, value in defaults.items():
        conn.execute("INSERT OR IGNORE INTO site_settings(key,value) VALUES(?,?)", (key,value))
    # Categorias amplas; profissões específicas são encontradas pelos serviços/palavras-chave.
    default_categories = [
      ("Restaurantes e lanchonetes","🍽️"), ("Prestadores de serviços","🛠️"),
      ("Lojas de vestuário","👕"), ("Pet shops e veterinários","🐾"),
      ("Conveniências e adegas","🛒"), ("Mercados e mercearias","🧺"),
      ("Padarias e cafeterias","☕"), ("Beleza e estética","💇"),
      ("Saúde e bem-estar","🩺"), ("Farmácias","💊"),
      ("Casa, móveis e decoração","🛋️"), ("Materiais de construção","🧱"),
      ("Automóveis e motos","🚗"), ("Tecnologia e eletrônicos","📱"),
      ("Turismo e hospedagem","🏨"), ("Imobiliárias","🏠"),
      ("Educação e cursos","🎓"), ("Esportes e lazer","⚽"),
      ("Calçados e acessórios","👟"), ("Comércio em geral","🏪")
    ]
    catalog_key = "category_catalog_v2"
    catalog_ready = conn.execute("SELECT value FROM site_settings WHERE key=?", (catalog_key,)).fetchone()
    for i,(name,icon) in enumerate(default_categories,1):
        slug=slugify(name)
        conn.execute("INSERT OR IGNORE INTO categories(name,slug,icon,sort_order,active) VALUES(?,?,?,?,1)",(name,slug,icon,i))
        conn.execute("UPDATE categories SET name=?,icon=?,sort_order=?,active=1 WHERE slug=?",(name,icon,i,slug))
    if not catalog_ready:
        desired_slugs=[slugify(name) for name,_ in default_categories]
        placeholders=",".join("?" for _ in desired_slugs)
        category_ids={r["slug"]:r["id"] for r in conn.execute(
            f"SELECT id,slug FROM categories WHERE slug IN ({placeholders})", desired_slugs
        ).fetchall()}
        old_assignments=conn.execute("""
          SELECT DISTINCT pc.professional_id,c.name,c.slug,p.business_type
          FROM professional_categories pc
          JOIN categories c ON c.id=pc.category_id
          JOIN professionals p ON p.id=pc.professional_id
        """).fetchall()
        conn.execute(f"DELETE FROM professional_categories WHERE category_id NOT IN (SELECT id FROM categories WHERE slug IN ({placeholders}))", desired_slugs)
        for row in old_assignments:
            old=(row["name"] or "").lower()
            if row["slug"] in category_ids:
                target=row["slug"]
            elif "pet" in old or "veterin" in old:
                target="pet-shops-e-veterinarios"
            elif row["business_type"] == "restaurant":
                target="restaurantes-e-lanchonetes"
            elif row["business_type"] == "convenience":
                target="conveniencias-e-adegas"
            elif row["business_type"] == "professional":
                target="prestadores-de-servicos"
            else:
                target="comercio-em-geral"
            if category_ids.get(target):
                conn.execute("INSERT OR IGNORE INTO professional_categories(professional_id,category_id) VALUES(?,?)",(row["professional_id"],category_ids[target]))
        conn.execute(f"DELETE FROM categories WHERE slug NOT IN ({placeholders})", desired_slugs)
        conn.execute("INSERT INTO site_settings(key,value) VALUES(?,?)",(catalog_key,"1"))
    # V49: remove uma única vez os antigos perfis de demonstração para que o
    # administrador possa recriá-los corretamente pelo novo formulário.
    demo_reset_key = "v49_demo_profiles_reset"
    if not conn.execute("SELECT 1 FROM site_settings WHERE key=?", (demo_reset_key,)).fetchone():
        demo_users=[r[0] for r in conn.execute("SELECT user_id FROM professionals WHERE is_demo=1").fetchall()]
        for user_id in demo_users:
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.execute("INSERT INTO site_settings(key,value) VALUES(?,?)", (demo_reset_key, now_iso()))
    admin_email = os.getenv("NOWUP_ADMIN_EMAIL", "admin@nowup.local").strip().lower()
    admin_pass = os.getenv("NOWUP_ADMIN_PASSWORD", "nowup2026")
    admin = conn.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone()
    if admin:
        conn.execute("UPDATE users SET role='admin', is_active=1, email_verified=1, password_hash=? WHERE id=?",
                     (hash_password(admin_pass), admin["id"]))
        admin_id=admin["id"]
    else:
        cur=conn.execute("INSERT INTO users(role,name,email,password_hash,email_verified,created_at) VALUES('admin','Administrador NowUp',?,?,1,?)",
                         (admin_email, hash_password(admin_pass), now_iso()))
        admin_id=cur.lastrowid
    # Reinícios e novos deploys encerram qualquer painel administrativo aberto.
    conn.execute("DELETE FROM sessions WHERE user_id=?",(admin_id,))
    if not conn.execute("SELECT 1 FROM banners").fetchone():
        conn.execute("INSERT INTO banners(title,subtitle,created_at) VALUES(?,?,?)",
                     ("Divulgue sua empresa na NowUp","Espaço para publicidade por cidade ou categoria.",now_iso()))
    conn.commit(); conn.close()

@app.on_event("startup")
def startup():
    init_db()
    init_cms_db()
    # Cópia SQLite consistente; o disco persistente deve incluir a pasta data.
    backup_dir=DB_PATH.parent/"backups"; backup_dir.mkdir(parents=True,exist_ok=True)
    destination=backup_dir/f"nowup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.db"
    source=sqlite3.connect(DB_PATH); target=sqlite3.connect(destination)
    try: source.backup(target)
    finally: target.close(); source.close()
    for old in sorted(backup_dir.glob("nowup-*.db"),reverse=True)[7:]: old.unlink(missing_ok=True)

@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str="", city: str="", category: str="", business_type: str=""):
    conn = db()
    settings = get_settings(conn)
    cities = active_cities(settings)
    city = city.strip() or cities[0]
    params=[]; where=["p.blocked=0"]
    if q:
        where.append("(p.display_name LIKE ? OR p.services LIKE ? OR p.description LIKE ? OR EXISTS(SELECT 1 FROM professional_categories pcq JOIN categories cq ON cq.id=pcq.category_id WHERE pcq.professional_id=p.id AND cq.name LIKE ?) OR EXISTS(SELECT 1 FROM products pr WHERE pr.professional_id=p.id AND pr.available=1 AND (pr.name LIKE ? OR pr.description LIKE ? OR pr.category LIKE ?)))")
        like=f"%{q.strip()}%"; params += [like,like,like,like,like,like,like]
    if city:
        where.append("p.city LIKE ?"); params.append(f"%{city}%")
    if category:
        where.append("EXISTS(SELECT 1 FROM professional_categories pc JOIN categories c ON c.id=pc.category_id WHERE pc.professional_id=p.id AND c.slug=?)")
        params.append(category)
    if business_type in ("professional","restaurant","store","convenience","other"):
        where.append("p.business_type=?"); params.append(business_type)
    visitor_key=request.cookies.get("nowup_visitor") or secrets.token_urlsafe(18)
    visit_date=datetime.now(SAO_PAULO_TZ).date().isoformat()
    conn.execute("INSERT OR IGNORE INTO daily_home_visits(visit_date,visitor_key,created_at) VALUES(?,?,?)",(visit_date,visitor_key,now_iso()))
    conn.commit()
    people_today=conn.execute("SELECT COUNT(*) FROM daily_home_visits WHERE visit_date=?",(visit_date,)).fetchone()[0]
    rows = conn.execute(f"""
      SELECT p.*, u.name as owner_name,
       COALESCE((SELECT ROUND(AVG(stars),1) FROM reviews r WHERE r.professional_id=p.id),0) rating,
       (SELECT COUNT(*) FROM reviews r WHERE r.professional_id=p.id) review_count,
       (SELECT COUNT(*) FROM products pr WHERE pr.professional_id=p.id AND pr.available=1) product_count,
       COALESCE(
         CASE WHEN p.featured=1 THEN NULLIF(p.featured_image_filename,'') END,
         NULLIF(p.cover_filename,''),
         NULLIF(p.avatar_filename,''),
         (SELECT filename FROM photos ph WHERE ph.professional_id=p.id ORDER BY is_cover DESC,id ASC LIMIT 1)
       ) cover
      FROM professionals p JOIN users u ON u.id=p.user_id
      WHERE {' AND '.join(where)}
      ORDER BY p.featured DESC,p.verified DESC,rating DESC,p.id DESC LIMIT 12
    """, params).fetchall()
    rows=[dict(r) for r in rows]
    for row in rows: row["shop_status"]=shop_status(row)
    posts = conn.execute("""
      SELECT po.*,p.display_name,p.slug,p.city,
      COALESCE(NULLIF(p.avatar_filename,''),NULLIF(p.cover_filename,''),(SELECT filename FROM photos ph WHERE ph.professional_id=p.id ORDER BY is_cover DESC,id ASC LIMIT 1)) avatar
      FROM posts po JOIN professionals p ON p.id=po.professional_id
      WHERE p.blocked=0 AND po.post_type!='status' ORDER BY po.id DESC LIMIT 12
    """).fetchall()
    user=current_user(request); favorite_ids=set()
    if user and user["role"]=="customer":
        favorite_ids={r[0] for r in conn.execute("SELECT professional_id FROM favorites WHERE customer_id=?",(user["id"],)).fetchall()}
    restaurants=[r for r in rows if r["business_type"]=="restaurant"]
    offers=[r for r in rows if r["featured"]]
    recommended=[r for r in rows if r["business_type"]!="restaurant"]
    conn.close()
    response=templates.TemplateResponse("home.html", context(request, professionals=rows, restaurants=restaurants, offers=offers, recommended=recommended, favorite_ids=favorite_ids, posts=posts, q=q, city=city, category=category, business_type=business_type, active_cities=cities, people_today=people_today, has_home_filter=bool(q or category or business_type)))
    if not request.cookies.get("nowup_visitor"):
        response.set_cookie("nowup_visitor",visitor_key,max_age=31536000,httponly=True,samesite="lax",secure=request.url.scheme=="https")
    return response

@app.get("/profissionais", response_class=HTMLResponse)
def professionals(request: Request, category: str="", city: str="", neighborhood: str="", cep: str="", q: str="", business_type: str=""):
    conn=db(); where=["p.blocked=0"]; params=[]; cities=active_cities(get_settings(conn)); city=city.strip() or cities[0]
    for field,val in [("p.city",city),("p.neighborhood",neighborhood),("p.cep",cep)]:
        if val: where.append(f"{field} LIKE ?"); params.append(f"%{val}%")
    if q:
        where.append("(p.display_name LIKE ? OR p.services LIKE ? OR p.description LIKE ? OR EXISTS(SELECT 1 FROM professional_categories pcq JOIN categories cq ON cq.id=pcq.category_id WHERE pcq.professional_id=p.id AND cq.name LIKE ?) OR EXISTS(SELECT 1 FROM products pr WHERE pr.professional_id=p.id AND pr.available=1 AND (pr.name LIKE ? OR pr.description LIKE ? OR pr.category LIKE ?)))"); like=f"%{q.strip()}%"; params += [like,like,like,like,like,like,like]
    if category:
        where.append("EXISTS(SELECT 1 FROM professional_categories pc JOIN categories c ON c.id=pc.category_id WHERE pc.professional_id=p.id AND c.slug=?)"); params.append(category)
    if business_type in ("professional","restaurant","store","convenience","other"):
        where.append("p.business_type=?"); params.append(business_type)
    rows=conn.execute(f"""
      SELECT p.*,
       COALESCE((SELECT ROUND(AVG(stars),1) FROM reviews r WHERE r.professional_id=p.id),0) rating,
       (SELECT COUNT(*) FROM reviews r WHERE r.professional_id=p.id) review_count,
       COALESCE(NULLIF(p.cover_filename,''),NULLIF(p.avatar_filename,''),(SELECT filename FROM photos ph WHERE ph.professional_id=p.id ORDER BY is_cover DESC,id ASC LIMIT 1)) cover
      FROM professionals p WHERE {' AND '.join(where)}
      ORDER BY p.featured DESC,p.verified DESC,rating DESC,p.id DESC LIMIT 100
    """,params).fetchall(); conn.close()
    return templates.TemplateResponse("professionals.html", context(request, professionals=rows, active_cities=cities, filters={"category":category,"city":city,"neighborhood":neighborhood,"cep":cep,"q":q,"business_type":business_type}))

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
    conn.execute("UPDATE professionals SET views=views+1 WHERE id=?",(p["id"],))
    conn.execute("INSERT INTO analytics_events(professional_id,event_type,created_at) VALUES(?,?,?)",(p["id"],"profile_view",now_iso())); conn.commit()
    photos=conn.execute("SELECT * FROM photos WHERE professional_id=? ORDER BY is_cover DESC,id DESC",(p["id"],)).fetchall()
    posts=conn.execute("SELECT * FROM posts WHERE professional_id=? ORDER BY id DESC",(p["id"],)).fetchall()
    reviews=conn.execute("SELECT r.*,u.name FROM reviews r JOIN users u ON u.id=r.customer_id WHERE r.professional_id=? ORDER BY r.id DESC",(p["id"],)).fetchall()
    cats=conn.execute("SELECT c.* FROM categories c JOIN professional_categories pc ON pc.category_id=c.id WHERE pc.professional_id=?",(p["id"],)).fetchall()
    product_count=conn.execute("SELECT COUNT(*) FROM products WHERE professional_id=? AND available=1",(p["id"],)).fetchone()[0]
    current=current_user(request); can_review=False
    if current and current["role"]=="customer":
        can_review=bool(conn.execute("SELECT 1 FROM orders WHERE customer_id=? AND professional_id=? AND status='completed' LIMIT 1",(current["id"],p["id"])).fetchone())
    conn.close()
    pub=dict(p); pub["document_masked"]=mask_doc(pub["document"]); pub["wa_link"]=wa_link(pub["whatsapp"],pub.get("whatsapp_message") or "Olá! Encontrei você pelo NowUp e gostaria de saber mais.")
    status=shop_status(p)
    return templates.TemplateResponse("profile.html", context(request, pro=pub, photos=photos, posts=posts, reviews=reviews, pro_categories=cats, product_count=product_count, shop_status=status, hours_lines=business_hours_lines(p), can_review=can_review))

@app.get("/p/{slug}/menu", response_class=HTMLResponse)
def native_menu(request: Request, slug: str):
    conn=db(); p=conn.execute("SELECT * FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p: conn.close(); raise HTTPException(404,"Empresa não encontrada")
    products=conn.execute("""SELECT pr.* FROM products pr
      WHERE pr.professional_id=? AND pr.available=1
      AND (NOT EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category))
        OR EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category) AND pc.active=1))
      ORDER BY pr.category,pr.sort_order,pr.id DESC""",(p["id"],)).fetchall()
    menu_categories=[]
    for product in products:
        category=(product["category"] or "Geral").strip() or "Geral"
        if category not in menu_categories: menu_categories.append(category)
    product_options={}
    for row in conn.execute("""SELECT po.* FROM product_options po JOIN products pr ON pr.id=po.product_id
      WHERE pr.professional_id=? AND po.available=1 ORDER BY po.sort_order,po.id""",(p["id"],)).fetchall():
        product_options.setdefault(row["product_id"],[]).append(row)
    conn.execute("UPDATE professionals SET menu_clicks=menu_clicks+1 WHERE id=?",(p["id"],))
    conn.execute("INSERT INTO analytics_events(professional_id,event_type,created_at) VALUES(?,?,?)",(p["id"],"menu_click",now_iso())); conn.commit(); conn.close()
    status=shop_status(p)
    return templates.TemplateResponse("menu.html", context(request, pro=p, products=products, product_options=product_options, menu_categories=menu_categories, shop_status=status))

@app.post("/p/{slug}/menu/pedido")
def native_menu_order(request: Request, slug: str, customer_name: str=Form(...), customer_phone: str=Form(...), fulfillment_type: str=Form("pickup"), payment_method: str=Form("pix"), address: str=Form(""), neighborhood: str=Form(""), address_reference: str=Form(""), change_for: str=Form(""), notes: str=Form(""), cart_json: str=Form(...)):
    logged=current_user(request)
    if not logged or logged["role"]!="customer": return RedirectResponse("/entrar?erro=pedido-login",303)
    conn=db(); p=conn.execute("SELECT * FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p: conn.close(); raise HTTPException(404)
    if not shop_status(p)["open"]: conn.close(); return RedirectResponse(f"/p/{slug}/menu?fechado=1",303)
    try: raw_items=json.loads(cart_json)
    except Exception: conn.close(); raise HTTPException(400,"Carrinho inválido")
    if not isinstance(raw_items,list) or not raw_items: conn.close(); raise HTTPException(400,"Carrinho vazio")
    clean_items=[]; subtotal=0
    for raw in raw_items[:50]:
        try: pid=int(raw.get("id")); qty=max(1,min(99,int(raw.get("quantity",1)))); item_notes=str(raw.get("notes","")).strip()[:300]
        except (TypeError,ValueError,AttributeError): continue
        product=conn.execute("SELECT * FROM products WHERE id=? AND professional_id=? AND available=1",(pid,p["id"])).fetchone()
        if product:
            qty=min(qty,max(1,product["max_quantity"] or 99)); chosen=[]; extras=0
            option_ids=raw.get("options",[]) if isinstance(raw,dict) else []
            if isinstance(option_ids,list):
                for oid in option_ids[:20]:
                    try: option=conn.execute("SELECT * FROM product_options WHERE id=? AND product_id=? AND available=1",(int(oid),pid)).fetchone()
                    except (TypeError,ValueError): option=None
                    if option: chosen.append(option); extras += option["price_cents"]
            unit=(product["promo_price_cents"] if product["promo_price_cents"]>0 else product["price_cents"])+extras
            clean_items.append((product,qty,item_notes,chosen,unit)); subtotal += unit*qty
    if not clean_items: conn.close(); raise HTTPException(400,"Nenhum produto disponível no carrinho")
    fulfillment_type="delivery" if fulfillment_type=="delivery" else "pickup"
    if fulfillment_type=="delivery" and not p["allows_delivery"]: conn.close(); raise HTTPException(400,"Esta loja não realiza entregas")
    if fulfillment_type=="pickup" and not p["allows_pickup"]: conn.close(); raise HTTPException(400,"Esta loja não permite retirada")
    if subtotal < (p["minimum_order_cents"] or 0): conn.close(); raise HTTPException(400,"O pedido não atingiu o valor mínimo")
    delivery_fee=(p["delivery_fee_cents"] or 0) if fulfillment_type=="delivery" else 0; total=subtotal+delivery_fee
    payment_labels={"pix":"Pix","cash":"Dinheiro","credit":"Cartão de crédito","debit":"Cartão de débito","on_delivery":"Combinar no atendimento"}
    payment_method=payment_method if payment_method in payment_labels else "pix"
    change_for_cents=price_to_cents(change_for) if payment_method=="cash" and change_for.strip() else 0
    customer_id=logged["id"]
    created=now_iso(); tracking_token=secrets.token_urlsafe(24)
    cur=conn.execute("""INSERT INTO orders(professional_id,customer_id,customer_name,customer_phone,fulfillment_type,address,notes,status,total_cents,whatsapp_opened,created_at,updated_at,subtotal_cents,delivery_fee_cents,neighborhood,address_reference,change_for_cents,tracking_token)
      VALUES(?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?,?,?)""",(p["id"],customer_id,customer_name.strip()[:120],customer_phone.strip()[:30],fulfillment_type,address.strip()[:300],notes.strip()[:500],"new",total,created,created,subtotal,delivery_fee,neighborhood.strip()[:120],address_reference.strip()[:220],change_for_cents,tracking_token))
    order_id=cur.lastrowid
    order_code=f"NU-{order_id:06d}"; conn.execute("UPDATE orders SET payment_method=?,order_code=? WHERE id=?",(payment_method,order_code,order_id))
    conn.execute("INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)",(order_id,"new",created))
    for product,qty,item_notes,chosen,unit in clean_items:
        item_cur=conn.execute("INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price_cents,notes) VALUES(?,?,?,?,?,?)",(order_id,product["id"],product["name"],qty,unit,item_notes))
        for option in chosen: conn.execute("INSERT INTO order_item_options(order_item_id,option_id,option_name,price_cents) VALUES(?,?,?,?)",(item_cur.lastrowid,option["id"],option["name"],option["price_cents"]))
    conn.commit(); conn.close()
    return RedirectResponse(f"/pedido/{tracking_token}",303)

ORDER_STATUS_LABELS={
  "new":"Pedido recebido", "confirmed":"Pedido aceito", "preparing":"Em preparo",
  "ready":"Pronto", "out_for_delivery":"Saiu para entrega", "completed":"Concluído",
  "cancelled":"Cancelado", "rejected":"Recusado"
}

def tracked_order(conn, token: str):
    return conn.execute("""SELECT o.*,p.display_name,p.slug,p.whatsapp,p.prep_minutes
      FROM orders o JOIN professionals p ON p.id=o.professional_id
      WHERE o.tracking_token=?""",(token,)).fetchone()

def order_whatsapp_message(conn, order):
    payment_labels={"pix":"Pix","cash":"Dinheiro","credit":"Cartão de crédito","debit":"Cartão de débito","on_delivery":"Combinar no atendimento"}
    items=conn.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id",(order["id"],)).fetchall()
    lines=[f"Olá! Quero falar sobre o pedido {order['order_code']} feito pelo NowUp:",""]
    for item in items:
        lines.append(f"{item['quantity']}x {item['product_name']} — R$ {(item['unit_price_cents']*item['quantity'])/100:.2f}")
        if item["notes"]: lines.append(f"   Obs.: {item['notes']}")
    lines += ["",f"Total: R$ {order['total_cents']/100:.2f}",f"Pagamento: {payment_labels.get(order['payment_method'],'A combinar')}",f"Cliente: {order['customer_name']}"]
    return "\n".join(lines)

@app.get("/pedido/{token}", response_class=HTMLResponse)
def order_tracking(request: Request, token: str):
    conn=db(); order=tracked_order(conn,token)
    if not order: conn.close(); raise HTTPException(404,"Pedido não encontrado")
    items=conn.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id",(order["id"],)).fetchall(); options={}
    for option in conn.execute("""SELECT oio.* FROM order_item_options oio JOIN order_items oi ON oi.id=oio.order_item_id
      WHERE oi.order_id=? ORDER BY oio.id""",(order["id"],)).fetchall(): options.setdefault(option["order_item_id"],[]).append(option)
    history=conn.execute("SELECT * FROM order_status_history WHERE order_id=? ORDER BY id",(order["id"],)).fetchall(); conn.close()
    return templates.TemplateResponse("order_tracking.html",context(request,order=order,items=items,options=options,history=history,status_labels=ORDER_STATUS_LABELS))

@app.get("/pedido/{token}/status")
def order_tracking_status(token: str):
    conn=db(); order=tracked_order(conn,token); conn.close()
    if not order: raise HTTPException(404,"Pedido não encontrado")
    return JSONResponse({"status":order["status"],"label":ORDER_STATUS_LABELS.get(order["status"],order["status"]),"updated_at":order["updated_at"]})

@app.post("/pedido/{token}/whatsapp")
def order_tracking_whatsapp(token: str):
    conn=db(); order=tracked_order(conn,token)
    if not order: conn.close(); raise HTTPException(404,"Pedido não encontrado")
    message=order_whatsapp_message(conn,order); conn.execute("UPDATE orders SET whatsapp_opened=1 WHERE id=?",(order["id"],)); conn.commit(); conn.close()
    return RedirectResponse(wa_link(order["whatsapp"],message),303)

@app.post("/p/{slug}/whatsapp")
def whatsapp_click(slug: str):
    conn=db(); p=conn.execute("SELECT * FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p: conn.close(); raise HTTPException(404)
    conn.execute("UPDATE professionals SET whatsapp_clicks=whatsapp_clicks+1 WHERE id=?",(p["id"],))
    conn.execute("INSERT INTO analytics_events(professional_id,event_type,created_at) VALUES(?,?,?)",(p["id"],"whatsapp_click",now_iso())); conn.commit(); conn.close()
    return RedirectResponse(wa_link(p["whatsapp"],p["whatsapp_message"] or "Olá! Encontrei você pelo NowUp e gostaria de saber mais."), status_code=303)

@app.get("/p/{slug}/cardapio")
def menu_click(slug: str):
    conn=db(); p=conn.execute("SELECT id,menu_url FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p or not clean_link(p["menu_url"]): conn.close(); raise HTTPException(404)
    conn.execute("UPDATE professionals SET menu_clicks=menu_clicks+1 WHERE id=?",(p["id"],))
    conn.execute("INSERT INTO analytics_events(professional_id,event_type,created_at) VALUES(?,?,?)",(p["id"],"menu_click",now_iso())); conn.commit(); target=p["menu_url"]; conn.close()
    return RedirectResponse(target,303)

@app.get("/p/{slug}/link")
def external_click(slug: str):
    conn=db(); p=conn.execute("SELECT id,external_url FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p or not clean_link(p["external_url"]): conn.close(); raise HTTPException(404)
    conn.execute("UPDATE professionals SET external_clicks=external_clicks+1 WHERE id=?",(p["id"],))
    conn.execute("INSERT INTO analytics_events(professional_id,event_type,created_at) VALUES(?,?,?)",(p["id"],"external_click",now_iso())); conn.commit(); target=p["external_url"]; conn.close()
    return RedirectResponse(target,303)

@app.get("/p/{slug}/social/{network}")
def social_click(slug: str, network: str):
    columns={"instagram":"instagram_url","facebook":"facebook_url","site":"website_url"}
    column=columns.get(network)
    if not column: raise HTTPException(404)
    conn=db(); p=conn.execute(f"SELECT id,{column} target FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p or not clean_link(p["target"]): conn.close(); raise HTTPException(404)
    conn.execute("UPDATE professionals SET external_clicks=external_clicks+1 WHERE id=?",(p["id"],))
    conn.execute("INSERT INTO analytics_events(professional_id,event_type,created_at) VALUES(?,?,?)",(p["id"],"external_click",now_iso())); conn.commit(); target=p["target"]; conn.close()
    return RedirectResponse(target,303)

@app.get("/cadastro/cliente", response_class=HTMLResponse)
def signup_customer_page(request: Request): return templates.TemplateResponse("signup_customer.html", context(request))

@app.post("/cadastro/cliente")
def signup_customer(name: str=Form(...), email: str=Form(...), phone: str=Form(""), password: str=Form(...), password_confirm: str=Form(...), accept_terms: Optional[str]=Form(None)):
    normalized_email=normalize_email(email)
    admin_email=os.getenv("NOWUP_ADMIN_EMAIL", "admin@nowup.local").strip().lower()
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
    if not email_service_configured():
        return RedirectResponse("/cadastro/cliente?erro=email_indisponivel",303)
    token,expires=verification_token()
    conn=db()
    try:
        cur=conn.execute(
            "INSERT INTO users(role,name,email,phone,password_hash,email_verified,verification_token,verification_expires_at,created_at) VALUES('customer',?,?,?,?,?,?,?,?)",
            (name.strip(),normalized_email,phone.strip(),hash_password(password),0,token,expires,now_iso())
        )
        conn.commit(); uid=cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close(); return RedirectResponse("/cadastro/cliente?erro=email",303)
    conn.close()
    if not send_verification(normalized_email,name.strip(),token):
        return RedirectResponse("/cadastro/aguardando?erro=envio_email",303)
    return RedirectResponse("/cadastro/aguardando",303)

@app.get("/cadastro/profissional", response_class=HTMLResponse)
def signup_pro_page(request: Request):
    return templates.TemplateResponse("signup_professional.html", context(request, active_cities=active_cities()))

@app.post("/cadastro/profissional")
def signup_professional(name: str=Form(...), email: str=Form(...), phone: str=Form(...), password: str=Form(...), password_confirm: str=Form(...), accept_terms: Optional[str]=Form(None), doc_type: str=Form(...), document: str=Form(...), business_type: str=Form("professional"), city: str=Form(...), neighborhood: str=Form(""), cep: str=Form(""), description: str=Form(""), services: str=Form(""), category_ids: list[int]=Form(default=[])):
    normalized_email=normalize_email(email)
    admin_email=os.getenv("NOWUP_ADMIN_EMAIL", "admin@nowup.local").strip().lower()
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
    if not email_service_configured():
        return RedirectResponse("/cadastro/profissional?erro=email_indisponivel",303)
    if business_type not in ("professional","restaurant","store","convenience","other"):
        business_type="other"
    cities=active_cities()
    if city not in cities: city=cities[0]
    token,expires=verification_token()
    conn=db()
    try:
        cur=conn.execute(
            "INSERT INTO users(role,name,email,phone,password_hash,email_verified,verification_token,verification_expires_at,created_at) VALUES('professional',?,?,?,?,?,?,?,?)",
            (name.strip(),normalized_email,phone.strip(),hash_password(password),0,token,expires,now_iso())
        ); uid=cur.lastrowid
        slug=unique_slug(conn,name)
        cur=conn.execute("INSERT INTO professionals(user_id,slug,display_name,doc_type,document,whatsapp,city,neighborhood,cep,description,services,business_type,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (uid,slug,name.strip(),doc_type,document.strip(),phone.strip(),city.strip(),neighborhood.strip(),cep.strip(),description.strip(),services.strip(),business_type,now_iso())); pid=cur.lastrowid
        for cid in category_ids[:1]:
            conn.execute("INSERT OR IGNORE INTO professional_categories(professional_id,category_id) VALUES(?,?)",(pid,cid))
        conn.execute("UPDATE professionals SET blocked=1 WHERE id=?",(pid,))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback(); conn.close(); return RedirectResponse("/cadastro/profissional?erro=email",303)
    conn.close()
    if not send_verification(normalized_email,name.strip(),token):
        return RedirectResponse("/cadastro/aguardando?erro=envio_email",303)
    return RedirectResponse("/cadastro/aguardando",303)

@app.get("/cadastro/sucesso", response_class=HTMLResponse)
def signup_success(request: Request, tipo: str="cliente"):
    u=current_user(request)
    if not u:
        return RedirectResponse("/entrar",303)
    return templates.TemplateResponse("signup_success.html", context(request, tipo=tipo))

def create_session_response(uid:int, dest:str, is_admin:bool=False):
    lifetime=timedelta(minutes=ADMIN_SESSION_MINUTES) if is_admin else timedelta(days=SESSION_DAYS)
    token=secrets.token_urlsafe(32); expires=(datetime.now(timezone.utc)+lifetime).isoformat()
    conn=db(); conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",(token,uid,expires)); conn.commit(); conn.close()
    resp=RedirectResponse(dest,303)
    cookie_options={"httponly":True,"samesite":"lax","secure":os.getenv("NOWUP_HTTPS","0")=="1"}
    if not is_admin:
        cookie_options["max_age"]=SESSION_DAYS*86400
    resp.set_cookie("nowup_session",token,**cookie_options)
    return resp

@app.get("/entrar", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse("login.html", context(request))

@app.get("/recuperar-senha", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", context(request))

@app.post("/recuperar-senha")
def forgot_password(email: str=Form(...)):
    normalized=normalize_email(email)
    if normalized:
        conn=db(); user=conn.execute("SELECT id,name,email FROM users WHERE email=? AND is_active=1",(normalized,)).fetchone()
        if user:
            raw=secrets.token_urlsafe(40); token_hash=hashlib.sha256(raw.encode()).hexdigest(); expires=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()
            conn.execute("DELETE FROM password_reset_tokens WHERE user_id=?",(user["id"],)); conn.execute("INSERT INTO password_reset_tokens(token_hash,user_id,expires_at) VALUES(?,?,?)",(token_hash,user["id"],expires)); conn.commit()
            base=os.getenv("NOWUP_BASE_URL","").strip().rstrip("/")
            if base:
                link=f"{base}/redefinir-senha?token={quote(raw)}"
                send_email(user["email"],user["name"],"Redefina sua senha da NowUp",f'<div style="font-family:Arial,sans-serif"><h2>Redefinir senha</h2><p>Olá, {user["name"]}.</p><p><a href="{link}" style="background:#075bd8;color:#fff;padding:12px 18px;border-radius:10px;text-decoration:none">Criar nova senha</a></p><p>O link expira em 30 minutos.</p></div>')
        conn.close()
    return RedirectResponse("/recuperar-senha?enviado=1",303)

def valid_reset_token(raw: str):
    if not raw: return None
    conn=db(); row=conn.execute("SELECT * FROM password_reset_tokens WHERE token_hash=? AND used=0 AND expires_at>?",(hashlib.sha256(raw.encode()).hexdigest(),now_iso())).fetchone(); conn.close(); return row

@app.get("/redefinir-senha", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str=""):
    return templates.TemplateResponse("reset_password.html", context(request,token=token,invalid=not bool(valid_reset_token(token))))

@app.post("/redefinir-senha")
def reset_password(token: str=Form(...), password: str=Form(...), password_confirm: str=Form(...)):
    row=valid_reset_token(token)
    if not row: return RedirectResponse("/redefinir-senha?token="+quote(token),303)
    if len(password)<8 or password!=password_confirm: return RedirectResponse("/redefinir-senha?erro=1&token="+quote(token),303)
    conn=db(); conn.execute("UPDATE users SET password_hash=? WHERE id=?",(hash_password(password),row["user_id"])); conn.execute("UPDATE password_reset_tokens SET used=1 WHERE token_hash=?",(row["token_hash"],)); conn.execute("DELETE FROM sessions WHERE user_id=?",(row["user_id"],)); conn.commit(); conn.close()
    return RedirectResponse("/entrar?senha_redefinida=1",303)

@app.post("/entrar")
def login(email: str=Form(...), password: str=Form(...)):
    conn=db(); u=conn.execute("SELECT * FROM users WHERE email=? AND is_active=1",(email.strip().lower(),)).fetchone(); conn.close()
    if not u or not verify_password(password,u["password_hash"]): return RedirectResponse("/entrar?erro=1",303)
    if u["role"]!="admin" and not u["email_verified"]: return RedirectResponse("/entrar?erro=verificacao",303)
    dest="/admin" if u["role"]=="admin" else ("/painel" if u["role"]=="professional" else "/cliente")
    return create_session_response(u["id"],dest)

@app.post("/sair")
def logout(request: Request):
    token=request.cookies.get("nowup_session")
    if token:
        conn=db(); conn.execute("DELETE FROM sessions WHERE token=?",(token,)); conn.commit(); conn.close()
    resp=RedirectResponse("/",303); resp.delete_cookie("nowup_session"); return resp

@app.get("/painel", response_class=HTMLResponse)
def pro_panel(request: Request, mes: str="", inicio: str="", fim: str="", pedido_status: str="todos"):
    u=require_user(request,"professional"); conn=db()
    p=conn.execute("SELECT * FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    photos=conn.execute("SELECT * FROM photos WHERE professional_id=? ORDER BY is_cover DESC,id DESC",(p["id"],)).fetchall()
    posts=conn.execute("SELECT * FROM posts WHERE professional_id=? ORDER BY id DESC LIMIT 20",(p["id"],)).fetchall()
    products=conn.execute("SELECT * FROM products WHERE professional_id=? ORDER BY category,sort_order,id DESC",(p["id"],)).fetchall()
    product_options={}
    for row in conn.execute("""SELECT po.* FROM product_options po JOIN products pr ON pr.id=po.product_id
      WHERE pr.professional_id=? ORDER BY po.sort_order,po.id""",(p["id"],)).fetchall():
        product_options.setdefault(row["product_id"],[]).append(row)
    product_categories=conn.execute("SELECT * FROM product_categories WHERE professional_id=? ORDER BY sort_order,id",(p["id"],)).fetchall()
    if not product_categories:
        existing=[]
        for row in products:
            name=(row["category"] or "Geral").strip() or "Geral"
            if name.lower() not in [x.lower() for x in existing]: existing.append(name)
        if not existing: existing=["Geral"]
        for index,name in enumerate(existing,1):
            conn.execute("INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",(p["id"],name,index,1,now_iso()))
        conn.commit(); product_categories=conn.execute("SELECT * FROM product_categories WHERE professional_id=? ORDER BY sort_order,id",(p["id"],)).fetchall()
    selected={r[0] for r in conn.execute("SELECT category_id FROM professional_categories WHERE professional_id=?",(p["id"],)).fetchall()}
    today=datetime.now(timezone.utc).date()
    try:
        if inicio and fim:
            start=datetime.strptime(inicio,"%Y-%m-%d").date(); end=datetime.strptime(fim,"%Y-%m-%d").date()
        elif mes:
            start=datetime.strptime(mes+"-01","%Y-%m-%d").date()
            next_month=(start.replace(day=28)+timedelta(days=4)).replace(day=1)
            end=next_month-timedelta(days=1)
        else:
            end=today; start=today-timedelta(days=29)
    except ValueError:
        end=today; start=today-timedelta(days=29)
    if start>end: start,end=end,start
    if (end-start).days>366: start=end-timedelta(days=366)
    event_rows=conn.execute("""SELECT event_type,COUNT(*) total FROM analytics_events
      WHERE professional_id=? AND date(created_at) BETWEEN ? AND ? GROUP BY event_type""",
      (p["id"],start.isoformat(),end.isoformat())).fetchall()
    counts={r["event_type"]:r["total"] for r in event_rows}
    daily_rows=conn.execute("""SELECT date(created_at) day,
      SUM(CASE WHEN event_type='profile_view' THEN 1 ELSE 0 END) views,
      SUM(CASE WHEN event_type!='profile_view' THEN 1 ELSE 0 END) clicks
      FROM analytics_events WHERE professional_id=? AND date(created_at) BETWEEN ? AND ?
      GROUP BY date(created_at) ORDER BY day DESC LIMIT 31""",
      (p["id"],start.isoformat(),end.isoformat())).fetchall()
    days=max(1,(end-start).days+1); period_views=counts.get("profile_view",0)
    analytics={"views":period_views,
      "whatsapp":counts.get("whatsapp_click",0),"menu":counts.get("menu_click",0),"external":counts.get("external_click",0),
      "clicks":counts.get("whatsapp_click",0)+counts.get("menu_click",0)+counts.get("external_click",0),
      "daily_avg":round(period_views/days,1),"weekly_avg":round(period_views/max(days/7,1),1),
      "monthly_avg":round(period_views/max(days/30,1),1),"days":days}
    settings=get_settings(conn); support_link=wa_link(settings.get("support_whatsapp",""),"Olá! Sou profissional cadastrado na NowUp e preciso de ajuda com meu painel.")
    profile_fields=[p["display_name"],p["whatsapp"],p["description"],p["services"],p["city"],p["neighborhood"],p["avatar_filename"],p["cover_filename"],p["service_area"],p["opening_hours"]]
    profile_completion=round(sum(bool(str(v or "").strip()) for v in profile_fields)*100/len(profile_fields))
    order_where=["o.professional_id=?", "date(o.created_at) BETWEEN ? AND ?"]
    order_params=[p["id"],start.isoformat(),end.isoformat()]
    allowed_order_status={"new","confirmed","preparing","ready","out_for_delivery","completed","cancelled","rejected"}
    if pedido_status in allowed_order_status:
        order_where.append("o.status=?"); order_params.append(pedido_status)
    else:
        pedido_status="todos"
    orders=conn.execute(f"""SELECT o.*,
      COALESCE((SELECT SUM(oi.quantity) FROM order_items oi WHERE oi.order_id=o.id),0) item_count
      FROM orders o WHERE {' AND '.join(order_where)} ORDER BY o.id DESC LIMIT 100""",order_params).fetchall()
    order_items_by_order={}
    order_item_options={}
    if orders:
        order_ids=[order["id"] for order in orders]; placeholders=",".join("?" for _ in order_ids)
        for item in conn.execute(f"SELECT * FROM order_items WHERE order_id IN ({placeholders}) ORDER BY id",order_ids).fetchall():
            order_items_by_order.setdefault(item["order_id"],[]).append(item)
        for option in conn.execute(f"""SELECT oio.* FROM order_item_options oio JOIN order_items oi ON oi.id=oio.order_item_id
          WHERE oi.order_id IN ({placeholders}) ORDER BY oio.id""",order_ids).fetchall():
            order_item_options.setdefault(option["order_item_id"],[]).append(option)
    order_summary=conn.execute("""SELECT COUNT(*) total,
      COALESCE(SUM(CASE WHEN status!='cancelled' THEN total_cents ELSE 0 END),0) revenue_cents,
      COALESCE(ROUND(AVG(CASE WHEN status!='cancelled' THEN total_cents END)),0) avg_ticket_cents,
      SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) completed,
      SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) cancelled
      FROM orders WHERE professional_id=? AND date(created_at) BETWEEN ? AND ?""",
      (p["id"],start.isoformat(),end.isoformat())).fetchone()
    top_products=conn.execute("""SELECT oi.product_name,
      SUM(oi.quantity) quantity, SUM(oi.quantity*oi.unit_price_cents) revenue_cents,
      COUNT(DISTINCT oi.order_id) order_count
      FROM order_items oi JOIN orders o ON o.id=oi.order_id
      WHERE o.professional_id=? AND o.status!='cancelled' AND date(o.created_at) BETWEEN ? AND ?
      GROUP BY lower(oi.product_name) ORDER BY quantity DESC,revenue_cents DESC LIMIT 15""",
      (p["id"],start.isoformat(),end.isoformat())).fetchall()
    latest_order_id=conn.execute("SELECT COALESCE(MAX(id),0) FROM orders WHERE professional_id=?",(p["id"],)).fetchone()[0]
    conn.close()
    status=shop_status(p); business_hours=parse_business_hours(p["business_hours"])
    return templates.TemplateResponse("pro_panel.html", context(request, pro=p, photos=photos, posts=posts, products=products, product_options=product_options, product_categories=product_categories, selected=selected, max_photos=MAX_PHOTOS, active_cities=active_cities(), analytics=analytics, daily_rows=daily_rows, filter_start=start.isoformat(), filter_end=end.isoformat(), filter_month=mes, support_link=support_link, profile_completion=profile_completion, orders=orders, order_items_by_order=order_items_by_order, order_item_options=order_item_options, order_summary=order_summary, top_products=top_products, order_status=pedido_status, shop_status=status, business_hours=business_hours, days=DAYS, day_labels=DAY_LABELS, latest_order_id=latest_order_id))

@app.get("/painel/pedidos/novos")
def pro_new_orders(request: Request, after: int=0):
    u=require_user(request,"professional"); conn=db()
    p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    rows=conn.execute("""SELECT id,customer_name,total_cents,created_at FROM orders
      WHERE professional_id=? AND id>? ORDER BY id ASC LIMIT 10""",(p["id"],max(0,after))).fetchall()
    latest=conn.execute("SELECT COALESCE(MAX(id),0) FROM orders WHERE professional_id=?",(p["id"],)).fetchone()[0]
    conn.close()
    return JSONResponse({"latest_id":latest,"orders":[{"id":r["id"],"customer_name":r["customer_name"] or "Cliente","total_cents":r["total_cents"],"created_at":r["created_at"]} for r in rows]})

def price_to_cents(raw: str):
    value=(raw or "0").strip().replace("R$","").replace(" ","")
    if "," in value: value=value.replace(".","").replace(",",".")
    try: return max(0,int(round(float(value)*100)))
    except ValueError: raise HTTPException(400,"Preço inválido")

@app.post("/painel/cardapio/categorias")
def pro_menu_category_add(request: Request, name: str=Form(...)):
    u=require_user(request,"professional"); clean=name.strip()[:80]
    if not clean: return RedirectResponse("/painel?erro=categoria#cardapio",303)
    conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    next_order=conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM product_categories WHERE professional_id=?",(p["id"],)).fetchone()[0]
    try: conn.execute("INSERT INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",(p["id"],clean,next_order,1,now_iso())); conn.commit()
    except sqlite3.IntegrityError: pass
    conn.close(); return RedirectResponse("/painel?ok=categoria#cardapio",303)

@app.post("/painel/cardapio/categorias/{category_id}")
def pro_menu_category_edit(request: Request, category_id: int, name: str=Form(...), active: Optional[str]=Form(None)):
    u=require_user(request,"professional"); clean=name.strip()[:80]
    conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone(); old=conn.execute("SELECT * FROM product_categories WHERE id=? AND professional_id=?",(category_id,p["id"])).fetchone()
    if old and clean:
        conn.execute("UPDATE product_categories SET name=?,active=? WHERE id=?",(clean,1 if active else 0,category_id))
        conn.execute("UPDATE products SET category=?,updated_at=? WHERE professional_id=? AND lower(category)=lower(?)",(clean,now_iso(),p["id"],old["name"])); conn.commit()
    conn.close(); return RedirectResponse("/painel?ok=categoria#cardapio",303)

@app.post("/painel/cardapio/categorias/{category_id}/excluir")
def pro_menu_category_delete(request: Request, category_id: int):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone(); row=conn.execute("SELECT * FROM product_categories WHERE id=? AND professional_id=?",(category_id,p["id"])).fetchone()
    if row:
        conn.execute("UPDATE products SET category='Geral',updated_at=? WHERE professional_id=? AND lower(category)=lower(?)",(now_iso(),p["id"],row["name"]))
        conn.execute("DELETE FROM product_categories WHERE id=?",(category_id,)); conn.execute("INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",(p["id"],"Geral",999,1,now_iso())); conn.commit()
    conn.close(); return RedirectResponse("/painel?ok=categoria-excluida#cardapio",303)

@app.post("/painel/cardapio/produtos")
def pro_product_add(request: Request, name: str=Form(...), description: str=Form(""), category: str=Form("Geral"), price: str=Form(...), promo_price: str=Form(""), max_quantity: int=Form(99), featured: Optional[str]=Form(None), available: Optional[str]=Form(None), photo: Optional[UploadFile]=File(None)):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone(); fn=""
    if photo and photo.filename: fn=save_image(photo)
    created=now_iso(); conn.execute("INSERT INTO products(professional_id,name,description,category,price_cents,image_filename,available,created_at,updated_at,promo_price_cents,featured,max_quantity) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(p["id"],name.strip()[:140],description.strip()[:600],category.strip()[:80] or "Geral",price_to_cents(price),fn,1 if available else 0,created,created,price_to_cents(promo_price) if promo_price.strip() else 0,1 if featured else 0,max(1,min(99,max_quantity))))
    conn.commit(); conn.close(); return RedirectResponse("/painel?ok=produto#cardapio",303)

@app.post("/painel/cardapio/produtos/{product_id}")
def pro_product_edit(request: Request, product_id: int, name: str=Form(...), description: str=Form(""), category: str=Form("Geral"), price: str=Form(...), promo_price: str=Form(""), max_quantity: int=Form(99), featured: Optional[str]=Form(None), available: Optional[str]=Form(None), photo: Optional[UploadFile]=File(None)):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone(); product=conn.execute("SELECT * FROM products WHERE id=? AND professional_id=?",(product_id,p["id"])).fetchone()
    if not product: conn.close(); raise HTTPException(404)
    fn=product["image_filename"]
    if photo and photo.filename:
        new_fn=save_image(photo)
        if fn:
            try: (UPLOAD_DIR/fn).unlink(missing_ok=True)
            except OSError: pass
        fn=new_fn
    conn.execute("UPDATE products SET name=?,description=?,category=?,price_cents=?,image_filename=?,available=?,updated_at=?,promo_price_cents=?,featured=?,max_quantity=? WHERE id=?",(name.strip()[:140],description.strip()[:600],category.strip()[:80] or "Geral",price_to_cents(price),fn,1 if available else 0,now_iso(),price_to_cents(promo_price) if promo_price.strip() else 0,1 if featured else 0,max(1,min(99,max_quantity)),product_id)); conn.commit(); conn.close()
    return RedirectResponse("/painel?ok=produto#cardapio",303)

@app.post("/painel/cardapio/configuracoes")
def pro_menu_settings(request: Request, delivery_fee: str=Form("0"), minimum_order: str=Form("0"), prep_minutes: int=Form(40), pix_key: str=Form(""), allows_delivery: Optional[str]=Form(None), allows_pickup: Optional[str]=Form(None)):
    u=require_user(request,"professional"); conn=db()
    conn.execute("""UPDATE professionals SET delivery_fee_cents=?,minimum_order_cents=?,prep_minutes=?,pix_key=?,allows_delivery=?,allows_pickup=? WHERE user_id=?""",
      (price_to_cents(delivery_fee),price_to_cents(minimum_order),max(5,min(240,prep_minutes)),pix_key.strip()[:180],1 if allows_delivery else 0,1 if allows_pickup else 0,u["id"]))
    conn.commit(); conn.close(); return RedirectResponse("/painel?ok=config-cardapio#cardapio",303)

@app.post("/painel/cardapio/produtos/{product_id}/adicionais")
def pro_product_option_add(request: Request, product_id: int, option_name: str=Form(...), option_price: str=Form("0")):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    product=conn.execute("SELECT id FROM products WHERE id=? AND professional_id=?",(product_id,p["id"])).fetchone()
    if not product: conn.close(); raise HTTPException(404)
    name=option_name.strip()[:100]
    if name:
        next_order=conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM product_options WHERE product_id=?",(product_id,)).fetchone()[0]
        conn.execute("INSERT INTO product_options(product_id,name,price_cents,available,sort_order) VALUES(?,?,?,?,?)",(product_id,name,price_to_cents(option_price),1,next_order)); conn.commit()
    conn.close(); return RedirectResponse("/painel?ok=adicional#cardapio",303)

@app.post("/painel/cardapio/adicionais/{option_id}/excluir")
def pro_product_option_delete(request: Request, option_id: int):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    conn.execute("DELETE FROM product_options WHERE id=? AND product_id IN (SELECT id FROM products WHERE professional_id=?)",(option_id,p["id"])); conn.commit(); conn.close()
    return RedirectResponse("/painel?ok=adicional-excluido#cardapio",303)

@app.post("/painel/cardapio/produtos/{product_id}/excluir")
def pro_product_delete(request: Request, product_id: int):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone(); product=conn.execute("SELECT * FROM products WHERE id=? AND professional_id=?",(product_id,p["id"])).fetchone()
    if product:
        if product["image_filename"]:
            try: (UPLOAD_DIR/product["image_filename"]).unlink(missing_ok=True)
            except OSError: pass
        conn.execute("DELETE FROM products WHERE id=?",(product_id,)); conn.commit()
    conn.close(); return RedirectResponse("/painel?ok=produto-excluido#cardapio",303)

@app.post("/painel/pedidos/{order_id}/status")
def pro_order_status(request: Request, order_id: int, status: str=Form(...), reason: str=Form("")):
    u=require_user(request,"professional")
    allowed={"new","confirmed","preparing","ready","out_for_delivery","completed","cancelled","rejected"}
    if status not in allowed: raise HTTPException(400,"Status inválido")
    conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    order=conn.execute("SELECT id,status,customer_id,tracking_token FROM orders WHERE id=? AND professional_id=?",(order_id,p["id"])).fetchone()
    if not order: conn.close(); raise HTTPException(404,"Pedido não encontrado")
    reason=reason.strip()[:300]
    if status in {"cancelled","rejected"} and not reason:
        conn.close(); return RedirectResponse(f"/painel?erro=motivo-obrigatorio#pedido-{order_id}",303)
    conn.execute("UPDATE orders SET status=?,cancellation_reason=?,updated_at=? WHERE id=?",(status,reason if status in {"cancelled","rejected"} else "",now_iso(),order_id))
    conn.execute("INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)",(order_id,status,now_iso()))
    if order["customer_id"] and status != order["status"]:
        label=ORDER_STATUS_LABELS.get(status,status); message=f"Seu pedido foi atualizado para: {label}."
        if reason: message += f" Motivo: {reason}"
        conn.execute("INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)",(order["customer_id"],"Atualização do pedido",message,f"/pedido/{order['tracking_token']}",now_iso()))
    conn.commit(); conn.close()
    return RedirectResponse("/painel?ok=pedido#pedidos",303)

@app.post("/painel/pedidos/{order_id}/editar")
def pro_order_edit(request: Request, order_id: int, customer_name: str=Form(...), customer_phone: str=Form(...), fulfillment_type: str=Form("pickup"), payment_method: str=Form("pix"), address: str=Form(""), notes: str=Form("")):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    order=conn.execute("SELECT id FROM orders WHERE id=? AND professional_id=?",(order_id,p["id"])).fetchone()
    if not order: conn.close(); raise HTTPException(404,"Pedido não encontrado")
    fulfillment_type="delivery" if fulfillment_type=="delivery" else "pickup"
    if payment_method not in {"pix","cash","credit","debit","on_delivery"}: payment_method="pix"
    conn.execute("UPDATE orders SET customer_name=?,customer_phone=?,fulfillment_type=?,payment_method=?,address=?,notes=?,updated_at=? WHERE id=?",(customer_name.strip()[:120],customer_phone.strip()[:30],fulfillment_type,payment_method,address.strip()[:300],notes.strip()[:500],now_iso(),order_id))
    conn.commit(); conn.close(); return RedirectResponse("/painel?ok=pedido-editado#pedidos",303)

@app.post("/painel/pedidos/{order_id}/itens/{item_id}")
def pro_order_item_edit(request: Request, order_id: int, item_id: int, quantity: int=Form(1), notes: str=Form(""), remove: Optional[str]=Form(None)):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    item=conn.execute("SELECT oi.id FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE oi.id=? AND oi.order_id=? AND o.professional_id=?",(item_id,order_id,p["id"])).fetchone()
    if not item: conn.close(); raise HTTPException(404,"Item não encontrado")
    if remove: conn.execute("DELETE FROM order_items WHERE id=?",(item_id,))
    else: conn.execute("UPDATE order_items SET quantity=?,notes=? WHERE id=?",(max(1,min(99,quantity)),notes.strip()[:300],item_id))
    subtotal=conn.execute("SELECT COALESCE(SUM(quantity*unit_price_cents),0) FROM order_items WHERE order_id=?",(order_id,)).fetchone()[0]
    delivery_fee=conn.execute("SELECT delivery_fee_cents FROM orders WHERE id=?",(order_id,)).fetchone()[0]
    conn.execute("UPDATE orders SET subtotal_cents=?,total_cents=?,updated_at=? WHERE id=?",(subtotal,subtotal+delivery_fee,now_iso(),order_id)); conn.commit(); conn.close()
    return RedirectResponse("/painel?ok=item-editado#pedidos",303)

@app.post("/painel/horarios")
async def pro_business_hours(request: Request):
    u=require_user(request,"professional"); form=await request.form(); schedule={}
    for day in DAYS:
        start=str(form.get(f"{day}_start","09:00")); end=str(form.get(f"{day}_end","18:00"))
        if not re.fullmatch(r"\d{2}:\d{2}",start): start="09:00"
        if not re.fullmatch(r"\d{2}:\d{2}",end): end="18:00"
        schedule[day]={"enabled":form.get(f"{day}_enabled")=="1","start":start,"end":end}
    manual=str(form.get("business_status","open"))
    if manual not in {"open","paused","temporarily_closed","vacation","ad_paused"}: manual="open"
    conn=db(); conn.execute("UPDATE professionals SET business_hours=?,business_status=?,opening_hours=? WHERE user_id=?",(json.dumps(schedule,ensure_ascii=False),manual,"Horários automáticos configurados",u["id"])); conn.commit(); conn.close()
    return RedirectResponse("/painel?ok=horarios#horarios",303)

@app.post("/painel/perfil")
def pro_update(request: Request, display_name: str=Form(...), whatsapp: str=Form(...), business_type: str=Form(""), city: str=Form(...), neighborhood: str=Form(""), address: str=Form(""), cep: str=Form(""), description: str=Form(""), services: str=Form(""), service_area: str=Form(""), opening_hours: str=Form(""), business_status: str=Form("open"), hide_address: Optional[str]=Form(None), whatsapp_message: str=Form(""), category_ids: list[int]=Form(default=[])):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    if business_type not in ("professional","restaurant","store","convenience","other"):
        business_type=conn.execute("SELECT business_type FROM professionals WHERE id=?",(p["id"],)).fetchone()[0]
    cities=active_cities(get_settings(conn))
    if city not in cities: city=cities[0]
    if business_status not in ("open","paused","temporarily_closed","vacation","ad_paused"): business_status="open"
    default_message="Olá! Encontrei você pelo NowUp e gostaria de saber mais."
    conn.execute("UPDATE professionals SET display_name=?,whatsapp=?,business_type=?,city=?,neighborhood=?,address=?,cep=?,description=?,services=?,service_area=?,opening_hours=?,business_status=?,hide_address=?,whatsapp_message=? WHERE id=?",(display_name.strip()[:120],whatsapp.strip()[:30],business_type,city,neighborhood.strip()[:120],address.strip()[:220],cep.strip()[:20],description.strip()[:1200],services.strip()[:1200],service_area.strip()[:500],opening_hours.strip()[:500],business_status,1 if hide_address else 0,(whatsapp_message.strip() or default_message)[:300],p["id"]))
    conn.execute("DELETE FROM professional_categories WHERE professional_id=?",(p["id"],))
    for cid in category_ids[:1]: conn.execute("INSERT OR IGNORE INTO professional_categories(professional_id,category_id) VALUES(?,?)",(p["id"],cid))
    conn.commit(); conn.close(); return RedirectResponse("/painel?ok=perfil",303)

@app.get("/cliente", response_class=HTMLResponse)
def customer_panel(request: Request):
    u=require_user(request,"customer"); conn=db()
    reviews=conn.execute("""SELECT r.*,p.display_name,p.slug FROM reviews r
      JOIN professionals p ON p.id=r.professional_id WHERE r.customer_id=? ORDER BY r.id DESC""",(u["id"],)).fetchall()
    favorites=conn.execute("""SELECT p.*,
      COALESCE(NULLIF(p.cover_filename,''),NULLIF(p.avatar_filename,''),(SELECT filename FROM photos ph WHERE ph.professional_id=p.id ORDER BY is_cover DESC,id ASC LIMIT 1)) cover
      FROM favorites f JOIN professionals p ON p.id=f.professional_id
      WHERE f.customer_id=? AND p.blocked=0 ORDER BY f.created_at DESC""",(u["id"],)).fetchall()
    orders=conn.execute("""SELECT o.*,p.display_name,p.slug FROM orders o
      JOIN professionals p ON p.id=o.professional_id
      WHERE o.customer_id=? OR (o.customer_id IS NULL AND replace(replace(replace(replace(o.customer_phone,' ',''),'-',''),'(',''),')','')=?)
      ORDER BY o.id DESC LIMIT 30""",(u["id"],normalize_phone(u["phone"] or "") or "__none__")).fetchall()
    notifications=conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 30",(u["id"],)).fetchall()
    unread_notifications=conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read_at=''",(u["id"],)).fetchone()[0]
    conn.close()
    return templates.TemplateResponse("customer_panel.html", context(request, reviews=reviews, favorites=favorites, orders=orders, notifications=notifications, unread_notifications=unread_notifications, status_labels=ORDER_STATUS_LABELS))

@app.post("/cliente/conta")
def customer_account_update(request: Request, name: str=Form(...), phone: str=Form(""), address: str=Form(""), neighborhood: str=Form(""), preferred_payment: str=Form("pix")):
    u=require_user(request,"customer"); clean_name=name.strip()[:120]; clean_phone=phone.strip()[:30]
    if not clean_name or (clean_phone and not normalize_phone(clean_phone)):
        return RedirectResponse("/cliente?erro=conta#conta",303)
    if preferred_payment not in {"pix","cash","credit","debit","on_delivery"}: preferred_payment="pix"
    conn=db(); conn.execute("UPDATE users SET name=?,phone=?,address=?,neighborhood=?,preferred_payment=? WHERE id=?",(clean_name,clean_phone,address.strip()[:300],neighborhood.strip()[:120],preferred_payment,u["id"])); conn.commit(); conn.close()
    return RedirectResponse("/cliente?ok=conta#conta",303)

@app.post("/cliente/notificacoes/ler")
def customer_notifications_read(request: Request):
    u=require_user(request,"customer"); conn=db(); conn.execute("UPDATE notifications SET read_at=? WHERE user_id=? AND read_at=''",(now_iso(),u["id"])); conn.commit(); conn.close()
    return RedirectResponse("/cliente#notificacoes",303)

@app.post("/favoritos/{professional_id}")
def toggle_favorite(request: Request, professional_id: int, next: str=Form("/cliente")):
    u=require_user(request,"customer"); conn=db()
    exists=conn.execute("SELECT 1 FROM favorites WHERE customer_id=? AND professional_id=?",(u["id"],professional_id)).fetchone()
    if exists: conn.execute("DELETE FROM favorites WHERE customer_id=? AND professional_id=?",(u["id"],professional_id))
    else:
        valid=conn.execute("SELECT 1 FROM professionals WHERE id=? AND blocked=0",(professional_id,)).fetchone()
        if valid: conn.execute("INSERT INTO favorites(customer_id,professional_id,created_at) VALUES(?,?,?)",(u["id"],professional_id,now_iso()))
    conn.commit(); conn.close()
    safe_next=next if next.startswith("/") and not next.startswith("//") else "/cliente"
    return RedirectResponse(safe_next,303)

@app.post("/painel/links")
def pro_links(request: Request, whatsapp: str=Form(...), external_url: str=Form(""), menu_url: str=Form(""), instagram_url: str=Form(""), facebook_url: str=Form(""), website_url: str=Form("")):
    u=require_user(request,"professional"); conn=db()
    conn.execute("UPDATE professionals SET whatsapp=?,external_url=?,menu_url=?,instagram_url=?,facebook_url=?,website_url=? WHERE user_id=?",(whatsapp.strip(),clean_link(external_url),clean_link(menu_url),clean_link(instagram_url),clean_link(facebook_url),clean_link(website_url),u["id"]))
    conn.commit(); conn.close(); return RedirectResponse("/painel?ok=links#links",303)

@app.post("/painel/identidade")
def pro_identity(request: Request, avatar: Optional[UploadFile]=File(None), cover: Optional[UploadFile]=File(None)):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT * FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    avatar_fn=p["avatar_filename"] or ""; cover_fn=p["cover_filename"] or ""
    if avatar and avatar.filename:
        new_avatar=save_image(avatar)
        if avatar_fn:
            try: (UPLOAD_DIR/avatar_fn).unlink(missing_ok=True)
            except OSError: pass
        avatar_fn=new_avatar
    if cover and cover.filename:
        new_cover=save_image(cover)
        if cover_fn:
            try: (UPLOAD_DIR/cover_fn).unlink(missing_ok=True)
            except OSError: pass
        cover_fn=new_cover
    conn.execute("UPDATE professionals SET avatar_filename=?,cover_filename=? WHERE id=?",(avatar_fn,cover_fn,p["id"])); conn.commit(); conn.close()
    return RedirectResponse("/painel?ok=identidade#identidade",303)

@app.post("/painel/identidade/{image_type}/excluir")
def pro_identity_delete(request: Request, image_type: str):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT * FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    column={"perfil":"avatar_filename","capa":"cover_filename"}.get(image_type)
    if column:
        filename=p[column] or ""
        if filename:
            try: (UPLOAD_DIR/filename).unlink(missing_ok=True)
            except OSError: pass
        conn.execute(f"UPDATE professionals SET {column}='' WHERE id=?",(p["id"],)); conn.commit()
    conn.close(); return RedirectResponse("/painel?ok=imagem-removida#identidade",303)

@app.post("/painel/publicidade")
def pro_ad_images(request: Request, featured_image: Optional[UploadFile]=File(None), slide_image: Optional[UploadFile]=File(None)):
    u=require_user(request,"professional"); conn=db(); p=conn.execute("SELECT * FROM professionals WHERE user_id=?",(u["id"],)).fetchone()
    updates=[]; values=[]
    for upload,column,enabled in ((featured_image,"featured_image_filename",p["featured"]),(slide_image,"slide_image_filename",p["in_slider"])):
        if upload and upload.filename and enabled:
            filename=save_image(upload); old=p[column] or ""
            if old:
                try: (UPLOAD_DIR/old).unlink(missing_ok=True)
                except OSError: pass
            updates.append(f"{column}=?"); values.append(filename)
    if updates:
        values.append(p["id"]); conn.execute(f"UPDATE professionals SET {','.join(updates)} WHERE id=?",values); conn.commit()
    conn.close(); return RedirectResponse("/painel?ok=publicidade#publicidade",303)

def save_image(upload: UploadFile):
    if upload.content_type not in {"image/jpeg","image/png","image/webp"}:
        raise HTTPException(400,"Formato inválido. Use JPG, PNG ou WebP")
    data=upload.file.read(MAX_UPLOAD+1)
    if len(data)>MAX_UPLOAD: raise HTTPException(400,"Imagem maior que 5MB")
    try:
        im=Image.open(io.BytesIO(data)); im.verify()
        im=Image.open(io.BytesIO(data))
        if im.width*im.height>24_000_000: raise HTTPException(400,"Imagem com resolução muito alta")
        im=im.convert("RGB")
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
    if post_type not in ("post","status","promotion","menu"): post_type="post"
    if photo and photo.filename: fn=save_image(photo)
    conn.execute("INSERT INTO posts(professional_id,text,photo_filename,post_type,created_at) VALUES(?,?,?,?,?)",(p["id"],text[:500],fn,post_type,now_iso())); conn.commit(); conn.close(); return RedirectResponse("/painel?ok=post",303)

@app.post("/p/{slug}/avaliar")
def review(request: Request, slug:str, stars:int=Form(...), comment:str=Form("")):
    u=require_user(request,"customer"); stars=max(1,min(5,stars)); conn=db(); p=conn.execute("SELECT id FROM professionals WHERE slug=? AND blocked=0",(slug,)).fetchone()
    if not p: conn.close(); raise HTTPException(404)
    completed=conn.execute("SELECT 1 FROM orders WHERE customer_id=? AND professional_id=? AND status='completed' LIMIT 1",(u["id"],p["id"])).fetchone()
    if not completed: conn.close(); return RedirectResponse(f"/p/{slug}?erro=avaliacao-sem-pedido#avaliacoes",303)
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
def admin(request: Request, inicio: str="", fim: str=""):
    require_user(request,"admin"); conn=db()
    stats={
      "professionals":conn.execute("SELECT COUNT(*) FROM professionals").fetchone()[0],
      "customers":conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
      "reports":conn.execute("SELECT COUNT(*) FROM reports WHERE status='pending'").fetchone()[0],
      "wa":conn.execute("SELECT COALESCE(SUM(whatsapp_clicks),0) FROM professionals").fetchone()[0],
      "views":conn.execute("SELECT COALESCE(SUM(views),0) FROM professionals").fetchone()[0],
      "menu":conn.execute("SELECT COALESCE(SUM(menu_clicks),0) FROM professionals").fetchone()[0],
    }
    try:
        report_end=datetime.strptime(fim,"%Y-%m-%d").date() if fim else datetime.now(timezone.utc).date()
        report_start=datetime.strptime(inicio,"%Y-%m-%d").date() if inicio else report_end-timedelta(days=29)
    except ValueError:
        report_end=datetime.now(timezone.utc).date(); report_start=report_end-timedelta(days=29)
    if report_start>report_end: report_start,report_end=report_end,report_start
    if (report_end-report_start).days>366: report_start=report_end-timedelta(days=366)
    report_orders=conn.execute("""SELECT COUNT(*) total,
      SUM(CASE WHEN status='new' THEN 1 ELSE 0 END) new_orders,
      SUM(CASE WHEN status IN ('confirmed','preparing','ready','out_for_delivery') THEN 1 ELSE 0 END) accepted,
      SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) completed,
      SUM(CASE WHEN status IN ('cancelled','rejected') THEN 1 ELSE 0 END) cancelled,
      COALESCE(SUM(CASE WHEN status IN ('confirmed','preparing','ready','out_for_delivery','completed') THEN total_cents ELSE 0 END),0) revenue_cents,
      COALESCE(ROUND(AVG(CASE WHEN status IN ('confirmed','preparing','ready','out_for_delivery','completed') THEN total_cents END)),0) avg_ticket_cents
      FROM orders WHERE date(created_at) BETWEEN ? AND ?""",(report_start.isoformat(),report_end.isoformat())).fetchone()
    report_top=conn.execute("""SELECT p.display_name,COUNT(o.id) orders_count,
      COALESCE(SUM(CASE WHEN o.status IN ('confirmed','preparing','ready','out_for_delivery','completed') THEN o.total_cents ELSE 0 END),0) revenue_cents
      FROM professionals p LEFT JOIN orders o ON o.professional_id=p.id AND date(o.created_at) BETWEEN ? AND ?
      GROUP BY p.id ORDER BY orders_count DESC,revenue_cents DESC LIMIT 10""",(report_start.isoformat(),report_end.isoformat())).fetchall()
    pros=conn.execute("""SELECT p.*,u.email,u.email_verified,
      (SELECT category_id FROM professional_categories pc WHERE pc.professional_id=p.id LIMIT 1) category_id
      FROM professionals p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC LIMIT 100""").fetchall()
    clients=conn.execute("SELECT id,name,email,phone,is_active,email_verified,created_at FROM users WHERE role='customer' ORDER BY id DESC LIMIT 100").fetchall()
    admin_categories=conn.execute("SELECT * FROM categories ORDER BY sort_order,name").fetchall()
    reports=conn.execute("SELECT r.*,u.name customer,p.display_name professional FROM reports r JOIN users u ON u.id=r.customer_id JOIN professionals p ON p.id=r.professional_id ORDER BY r.id DESC LIMIT 50").fetchall()
    suggestions=conn.execute("SELECT * FROM suggestions ORDER BY id DESC LIMIT 30").fetchall(); banners=conn.execute("SELECT * FROM banners ORDER BY sort_order,id").fetchall(); conn.close()
    return templates.TemplateResponse("admin.html", context(request, stats=stats, pros=pros, clients=clients, admin_categories=admin_categories, reports=reports, suggestions=suggestions, admin_banners=banners, report_orders=report_orders, report_top=report_top, report_start=report_start.isoformat(), report_end=report_end.isoformat()))

NOWUP_THEMES = {
    "oceanico": ("#075BD8", "#FF6A00"),
    "royal": ("#243BFF", "#8B5CF6"),
    "turquesa": ("#007F8B", "#20C997"),
    "esmeralda": ("#087F5B", "#F59F00"),
    "floresta": ("#245C3A", "#A3E635"),
    "por-do-sol": ("#C2410C", "#FBBF24"),
    "coral": ("#E84855", "#FF8A5B"),
    "rubi": ("#B42318", "#F04438"),
    "vinho": ("#7F1D3F", "#D946EF"),
    "uva": ("#6D28D9", "#EC4899"),
    "lavanda": ("#7C3AED", "#A78BFA"),
    "noturno": ("#08131F", "#08BCEB"),
    "grafite": ("#263238", "#00B8A9"),
    "preto-dourado": ("#171717", "#D4A017"),
    "cafe": ("#6F4E37", "#D97706"),
    "areia": ("#9A6700", "#F2C14E"),
    "azul-petroleo": ("#164E63", "#06B6D4"),
    "ceu": ("#0284C7", "#22D3EE"),
    "brasil": ("#08783E", "#F7C600"),
    "neon": ("#312E81", "#22C55E"),
}

@app.post("/admin/aparencia")
def admin_appearance(request: Request, brand_name:str=Form("NowUp"), font_family:str=Form("Inter"), primary_color:str=Form("#08131F"), accent_color:str=Form("#08BCEB"), theme_name:str=Form("noturno"), hero_title:str=Form(""), hero_subtitle:str=Form(""), public_email:str=Form(""), support_whatsapp:str=Form(""), active_cities:str=Form("Ubatuba")):
    require_user(request,"admin")
    allowed_fonts={"Inter","Arial","Georgia","Trebuchet MS","Verdana"}; font_family=font_family if font_family in allowed_fonts else "Inter"
    cities=", ".join(dict.fromkeys(c.strip()[:80] for c in active_cities.split(",") if c.strip())) or "Ubatuba"
    if theme_name in NOWUP_THEMES:
        primary_color, accent_color = NOWUP_THEMES[theme_name]
    else:
        theme_name = "personalizado"
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", primary_color): primary_color="#2457e6"
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent_color): accent_color="#ff8a32"
    values={"brand_name":brand_name.strip()[:80] or "NowUp","font_family":font_family,"primary_color":primary_color,"accent_color":accent_color,"theme_name":theme_name,"hero_title":hero_title.strip()[:180],"hero_subtitle":hero_subtitle.strip()[:500],"public_email":public_email.strip()[:160],"support_whatsapp":support_whatsapp.strip()[:40],"active_cities":cities}
    conn=db()
    for key,value in values.items(): conn.execute("INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value))
    conn.commit(); conn.close(); return RedirectResponse("/admin?ok=aparencia#aparencia",303)

@app.post("/admin/faixa-e-slides")
def admin_ticker_and_slides(request: Request, ticker_color:str=Form("#e30613"), ticker_text:str=Form(""), ticker_enabled:str=Form("0"), ticker_animation:str=Form("continuous"), slide_interval_seconds:str=Form("3")):
    require_user(request,"admin")
    try: seconds=max(1,min(15,int(slide_interval_seconds)))
    except (TypeError,ValueError): seconds=3
    color=ticker_color.strip()[:20]
    if not re.fullmatch(r"#[0-9a-fA-F]{6}",color): color="#e30613"
    if ticker_animation not in {"continuous","blink","inside-out","outside-in"}: ticker_animation="continuous"
    values={"ticker_color":color,"ticker_text":ticker_text.strip()[:300],"ticker_enabled":"1" if ticker_enabled=="1" else "0","ticker_animation":ticker_animation,"slide_interval_seconds":str(seconds)}
    conn=db()
    for key,value in values.items(): conn.execute("INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value))
    conn.commit(); conn.close()
    return RedirectResponse("/admin?ok=faixa#faixa-slides",303)

@app.post("/admin/categorias")
def admin_add_category(request: Request, name:str=Form(...), icon:str=Form("🛠️")):
    require_user(request,"admin"); conn=db()
    try: conn.execute("INSERT INTO categories(name,slug,icon,sort_order) VALUES(?,?,?,999)",(name.strip(),slugify(name),icon[:8])); conn.commit()
    except sqlite3.IntegrityError: pass
    conn.close(); return RedirectResponse("/admin#categorias",303)

@app.post("/admin/categorias/{cid}/alternar")
def admin_toggle_category(request: Request, cid:int):
    require_user(request,"admin"); conn=db(); conn.execute("UPDATE categories SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(cid,)); conn.commit(); conn.close(); return RedirectResponse("/admin#categorias",303)

@app.post("/admin/categorias/{cid}/editar")
def admin_edit_category(request: Request, cid:int, name:str=Form(...), icon:str=Form("🛠️")):
    require_user(request,"admin"); clean=name.strip()
    if not clean: return RedirectResponse("/admin#categorias",303)
    conn=db()
    try:
        conn.execute("UPDATE categories SET name=?,slug=?,icon=? WHERE id=?",(clean,slugify(clean),icon[:12],cid)); conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
    conn.close(); return RedirectResponse("/admin#categorias",303)

@app.post("/admin/categorias/{cid}/mover/{direction}")
def admin_move_category(request: Request, cid:int, direction:str):
    require_user(request,"admin")
    if direction not in ("up","down"): raise HTTPException(400)
    conn=db(); current=conn.execute("SELECT id,sort_order FROM categories WHERE id=?",(cid,)).fetchone()
    if current:
        op="<" if direction=="up" else ">"; order="DESC" if direction=="up" else "ASC"
        other=conn.execute(f"SELECT id,sort_order FROM categories WHERE sort_order {op} ? ORDER BY sort_order {order},id {order} LIMIT 1",(current["sort_order"],)).fetchone()
        if other:
            marker=-1000000-current["id"]
            conn.execute("UPDATE categories SET sort_order=? WHERE id=?",(marker,current["id"]))
            conn.execute("UPDATE categories SET sort_order=? WHERE id=?",(current["sort_order"],other["id"]))
            conn.execute("UPDATE categories SET sort_order=? WHERE id=?",(other["sort_order"],current["id"]))
            conn.commit()
    conn.close(); return RedirectResponse("/admin#categorias",303)

@app.post("/admin/clientes/{uid}/alternar")
def admin_toggle_client(request: Request, uid:int):
    require_user(request,"admin"); conn=db(); conn.execute("UPDATE users SET is_active=CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE id=? AND role='customer'",(uid,)); conn.execute("DELETE FROM sessions WHERE user_id=? AND (SELECT is_active FROM users WHERE id=?)=0",(uid,uid)); conn.commit(); conn.close(); return RedirectResponse("/admin#clientes",303)

@app.post("/admin/clientes/{uid}/editar")
def admin_edit_client(request: Request, uid:int, name:str=Form(...), email:str=Form(...), phone:str=Form("")):
    require_user(request,"admin"); normalized=normalize_email(email)
    if not name.strip() or not normalized: return RedirectResponse("/admin#clientes",303)
    conn=db()
    try:
        conn.execute("UPDATE users SET name=?,email=?,phone=? WHERE id=? AND role='customer'",(name.strip()[:120],normalized,phone.strip()[:30],uid)); conn.commit()
    except sqlite3.IntegrityError: conn.rollback()
    conn.close(); return RedirectResponse("/admin#clientes",303)

@app.post("/admin/clientes/{uid}/excluir")
def admin_delete_client(request: Request, uid:int):
    require_user(request,"admin")
    return RedirectResponse("/admin?erro=exclusao-desativada#clientes",303)

@app.post("/admin/categorias/{cid}/excluir")
def admin_delete_category(request: Request, cid:int):
    require_user(request,"admin"); conn=db(); conn.execute("DELETE FROM categories WHERE id=?",(cid,)); conn.commit(); conn.close(); return RedirectResponse("/admin#categorias",303)

@app.post("/admin/profissionais/{pid}/acao/{action}")
def admin_pro_action(request: Request, pid:int, action:str):
    require_user(request,"admin"); conn=db()
    if action=="verificar": conn.execute("UPDATE professionals SET verified=CASE verified WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(pid,))
    elif action=="destaque": conn.execute("UPDATE professionals SET featured=CASE featured WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(pid,))
    elif action=="slide": conn.execute("UPDATE professionals SET in_slider=CASE in_slider WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(pid,))
    elif action=="bloquear":
        pro=conn.execute("SELECT user_id,blocked FROM professionals WHERE id=?",(pid,)).fetchone()
        if pro:
            new_blocked=0 if pro["blocked"] else 1
            conn.execute("UPDATE professionals SET blocked=? WHERE id=?",(new_blocked,pid))
            conn.execute("UPDATE users SET is_active=? WHERE id=?",(0 if new_blocked else 1,pro["user_id"]))
            if new_blocked: conn.execute("DELETE FROM sessions WHERE user_id=?",(pro["user_id"],))
    else: conn.close(); raise HTTPException(400)
    conn.commit(); conn.close(); return RedirectResponse("/admin#profissionais",303)

@app.post("/admin/perfis/demonstracao")
def admin_add_demo_profile(request: Request, display_name:str=Form(...), whatsapp:str=Form(...), address:str=Form(...), category_id:int=Form(...), city:str=Form("Ubatuba"), neighborhood:str=Form(""), description:str=Form(""), services:str=Form(""), avatar:Optional[UploadFile]=File(None), cover:Optional[UploadFile]=File(None), photo:Optional[UploadFile]=File(None)):
    require_user(request,"admin")
    name=display_name.strip()[:120]; phone=whatsapp.strip()[:30]; address=address.strip()[:240]
    if not name or not normalize_phone(phone) or not address:
        return RedirectResponse("/admin?erro=perfil-demo#cadastro-rapido",303)
    avatar_upload=avatar if avatar and avatar.filename else photo
    cover_upload=cover if cover and cover.filename else None
    if not avatar_upload or not avatar_upload.filename:
        return RedirectResponse("/admin?erro=perfil-demo#cadastro-rapido",303)
    avatar_filename=save_image(avatar_upload)
    cover_filename=save_image(cover_upload) if cover_upload else avatar_filename
    conn=db()
    try:
        slug=unique_slug(conn,name)
        demo_email=f"demo-{secrets.token_hex(8)}@nowup.local"
        cur=conn.execute("INSERT INTO users(role,name,email,phone,password_hash,is_active,email_verified,created_at) VALUES('professional',?,?,?,?,1,1,?)",
                         (name,demo_email,phone,hash_password(secrets.token_urlsafe(32)),now_iso()))
        uid=cur.lastrowid
        category=conn.execute("SELECT id,slug FROM categories WHERE id=? AND active=1",(category_id,)).fetchone()
        if not category: raise ValueError("categoria inválida")
        business_type="restaurant" if "restaurante" in category["slug"] else ("convenience" if "conveniencia" in category["slug"] else ("professional" if "prestador" in category["slug"] else "other"))
        cur=conn.execute("""INSERT INTO professionals(user_id,slug,display_name,doc_type,document,whatsapp,city,neighborhood,cep,address,description,services,business_type,verified,featured,blocked,avatar_filename,cover_filename,is_demo,created_at)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (uid,slug,name,"CNPJ","",phone,city.strip()[:100] or "Ubatuba",neighborhood.strip()[:120],"",address,description.strip()[:1200],services.strip()[:1200],business_type,0,0,0,avatar_filename,cover_filename,1,now_iso()))
        pid=cur.lastrowid
        conn.execute("INSERT INTO professional_categories(professional_id,category_id) VALUES(?,?)",(pid,category_id))
        conn.execute("INSERT INTO photos(professional_id,filename,caption,is_cover,created_at) VALUES(?,?,?,?,?)",(pid,cover_filename,"Capa do perfil",1,now_iso()))
        conn.commit()
    except Exception:
        conn.rollback()
        try:
            (UPLOAD_DIR/avatar_filename).unlink(missing_ok=True)
            if cover_filename != avatar_filename: (UPLOAD_DIR/cover_filename).unlink(missing_ok=True)
        except OSError: pass
        conn.close()
        return RedirectResponse("/admin?erro=perfil-demo#cadastro-rapido",303)
    conn.close()
    return RedirectResponse("/admin?ok=perfil-demo#profissionais",303)

@app.post("/admin/profissionais/{pid}/editar")
def admin_edit_professional(request: Request, pid:int, display_name:str=Form(...), city:str=Form(""), email:str=Form(...), whatsapp:str=Form(""), address:str=Form(""), neighborhood:str=Form(""), description:str=Form(""), services:str=Form(""), category_id:int=Form(0), avatar:Optional[UploadFile]=File(None), cover:Optional[UploadFile]=File(None)):
    require_user(request,"admin"); normalized=normalize_email(email)
    if not display_name.strip() or not normalized: return RedirectResponse("/admin#profissionais",303)
    conn=db(); pro=conn.execute("SELECT user_id,avatar_filename,cover_filename,is_demo FROM professionals WHERE id=?",(pid,)).fetchone()
    if pro:
        try:
            avatar_filename=pro["avatar_filename"] or ""; cover_filename=pro["cover_filename"] or ""
            if pro["is_demo"] and avatar and avatar.filename: avatar_filename=save_image(avatar)
            if pro["is_demo"] and cover and cover.filename: cover_filename=save_image(cover)
            conn.execute("UPDATE professionals SET display_name=?,city=?,whatsapp=?,address=?,neighborhood=?,description=?,services=?,avatar_filename=?,cover_filename=? WHERE id=?",(display_name.strip()[:120],city.strip()[:100],whatsapp.strip()[:30],address.strip()[:240],neighborhood.strip()[:120],description.strip()[:1200],services.strip()[:1200],avatar_filename,cover_filename,pid))
            if pro["is_demo"] and category_id:
                conn.execute("DELETE FROM professional_categories WHERE professional_id=?",(pid,))
                conn.execute("INSERT OR IGNORE INTO professional_categories(professional_id,category_id) SELECT ?,id FROM categories WHERE id=? AND active=1",(pid,category_id))
            conn.execute("UPDATE users SET email=? WHERE id=?",(normalized,pro["user_id"])); conn.commit()
        except sqlite3.IntegrityError: conn.rollback()
    conn.close(); return RedirectResponse("/admin#profissionais",303)

@app.post("/admin/profissionais/{pid}/excluir")
def admin_delete_professional(request: Request, pid:int):
    require_user(request,"admin"); conn=db()
    pro=conn.execute("SELECT user_id,is_demo,avatar_filename,cover_filename FROM professionals WHERE id=?",(pid,)).fetchone()
    if not pro or not pro["is_demo"]:
        conn.close(); return RedirectResponse("/admin?erro=apenas-perfil-ficticio#profissionais",303)
    files=[pro["avatar_filename"],pro["cover_filename"]]
    files += [r[0] for r in conn.execute("SELECT filename FROM photos WHERE professional_id=?",(pid,)).fetchall()]
    conn.execute("DELETE FROM users WHERE id=?",(pro["user_id"],)); conn.commit(); conn.close()
    for filename in set(f for f in files if f):
        try: (UPLOAD_DIR/filename).unlink(missing_ok=True)
        except OSError: pass
    return RedirectResponse("/admin?ok=perfil-excluido#profissionais",303)

@app.post("/admin/perfis/demonstracao/excluir-todos")
def admin_delete_all_demo_profiles(request: Request):
    require_user(request,"admin"); conn=db()
    rows=conn.execute("SELECT user_id,avatar_filename,cover_filename FROM professionals WHERE is_demo=1").fetchall()
    files=[]
    for row in rows:
        files.extend([row["avatar_filename"],row["cover_filename"]])
        conn.execute("DELETE FROM users WHERE id=?",(row["user_id"],))
    conn.commit(); conn.close()
    for filename in set(f for f in files if f):
        try: (UPLOAD_DIR/filename).unlink(missing_ok=True)
        except OSError: pass
    return RedirectResponse("/admin?ok=perfis-ficticios-excluidos#profissionais",303)

@app.post("/admin/denuncias/{rid}/{status}")
def admin_report_action(request: Request, rid:int, status:str):
    require_user(request,"admin")
    if status not in ('pending','reviewed','resolved','archived'): raise HTTPException(400)
    conn=db(); conn.execute("UPDATE reports SET status=? WHERE id=?",(status,rid)); conn.commit(); conn.close(); return RedirectResponse("/admin#denuncias",303)

@app.post("/admin/banners")
def admin_banner_add(request: Request, link:str=Form(""), brightness:int=Form(100), zoom:int=Form(100), position_x:int=Form(50), position_y:int=Form(50), desktop_height:int=Form(360), mobile_height:int=Form(240), image:Optional[UploadFile]=File(None)):
    require_user(request,"admin"); fn=""
    if image and image.filename: fn=save_image(image)
    if not fn: return RedirectResponse("/admin?erro=imagem-banner#publicidade",303)
    brightness=max(40,min(160,brightness)); zoom=max(100,min(200,zoom)); position_x=max(0,min(100,position_x)); position_y=max(0,min(100,position_y)); desktop_height=max(240,min(600,desktop_height)); mobile_height=max(180,min(500,mobile_height))
    conn=db(); next_order=conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM banners").fetchone()[0]
    active_count=conn.execute("SELECT COUNT(*) FROM banners WHERE active=1").fetchone()[0]
    conn.execute("INSERT INTO banners(title,subtitle,link,image_filename,sort_order,active,template,background_color,text_color,font_family,brightness,zoom,position_x,position_y,desktop_height,mobile_height,created_at) VALUES('','',?,?,?,?,1,'#000000','#ffffff','Inter',?,?,?,?,?,?,?)",(clean_link(link),fn,next_order,1 if active_count<10 else 0,brightness,zoom,position_x,position_y,desktop_height,mobile_height,now_iso())); conn.commit(); conn.close(); return RedirectResponse("/admin#publicidade",303)

@app.post("/admin/banners/{bid}/editar")
def admin_banner_edit(request: Request, bid:int, link:str=Form(""), brightness:int=Form(100), zoom:int=Form(100), position_x:int=Form(50), position_y:int=Form(50), desktop_height:int=Form(360), mobile_height:int=Form(240), image:Optional[UploadFile]=File(None)):
    require_user(request,"admin"); conn=db(); banner=conn.execute("SELECT * FROM banners WHERE id=?",(bid,)).fetchone()
    if not banner: conn.close(); raise HTTPException(404)
    fn=banner["image_filename"] or ""
    if image and image.filename:
        new_fn=save_image(image)
        if fn:
            try: (UPLOAD_DIR/fn).unlink(missing_ok=True)
            except OSError: pass
        fn=new_fn
    brightness=max(40,min(160,brightness)); zoom=max(100,min(200,zoom)); position_x=max(0,min(100,position_x)); position_y=max(0,min(100,position_y)); desktop_height=max(240,min(600,desktop_height)); mobile_height=max(180,min(500,mobile_height))
    conn.execute("UPDATE banners SET title='',subtitle='',link=?,image_filename=?,template=1,background_color='#000000',text_color='#ffffff',font_family='Inter',brightness=?,zoom=?,position_x=?,position_y=?,desktop_height=?,mobile_height=? WHERE id=?",(clean_link(link),fn,brightness,zoom,position_x,position_y,desktop_height,mobile_height,bid)); conn.commit(); conn.close()
    return RedirectResponse("/admin#publicidade",303)

@app.post("/admin/banners/{bid}/alternar")
def admin_banner_toggle(request: Request, bid:int):
    require_user(request,"admin"); conn=db(); banner=conn.execute("SELECT active FROM banners WHERE id=?",(bid,)).fetchone()
    if banner and not banner["active"] and conn.execute("SELECT COUNT(*) FROM banners WHERE active=1").fetchone()[0]>=10:
        conn.close(); return RedirectResponse("/admin?erro=limite-slides#publicidade",303)
    conn.execute("UPDATE banners SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(bid,)); conn.commit(); conn.close(); return RedirectResponse("/admin#publicidade",303)

@app.post("/admin/capa")
def admin_hero_cover(request: Request, image:Optional[UploadFile]=File(None), brightness:int=Form(100), zoom:int=Form(100), position_x:int=Form(50), position_y:int=Form(50), desktop_height:int=Form(540), mobile_height:int=Form(540)):
    require_user(request,"admin"); conn=db(); old=get_settings(conn).get("hero_image_filename",""); fn=old
    if image and image.filename: fn=save_image(image)
    brightness=max(40,min(160,brightness)); zoom=max(100,min(200,zoom)); position_x=max(0,min(100,position_x)); position_y=max(0,min(100,position_y)); desktop_height=max(420,min(760,desktop_height)); mobile_height=max(480,min(760,mobile_height))
    values=(("hero_image_filename",fn),("hero_brightness",brightness),("hero_zoom",zoom),("hero_position_x",position_x),("hero_position_y",position_y),("hero_desktop_height",desktop_height),("hero_mobile_height",mobile_height))
    for key,value in values: conn.execute("INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))
    conn.commit(); conn.close()
    if old and fn != old:
        try: (UPLOAD_DIR/old).unlink(missing_ok=True)
        except OSError: pass
    return RedirectResponse("/admin#aparencia",303)

@app.post("/admin/banners/{bid}/mover/{direction}")
def admin_move_banner(request: Request, bid:int, direction:str):
    require_user(request,"admin")
    if direction not in ("up","down"): raise HTTPException(400)
    conn=db(); cur=conn.execute("SELECT id,sort_order FROM banners WHERE id=?",(bid,)).fetchone()
    if cur:
        op="<" if direction=="up" else ">"; order="DESC" if direction=="up" else "ASC"
        other=conn.execute(f"SELECT id,sort_order FROM banners WHERE sort_order {op} ? ORDER BY sort_order {order},id {order} LIMIT 1",(cur["sort_order"],)).fetchone()
        if other:
            conn.execute("UPDATE banners SET sort_order=? WHERE id=?",(-1000000-cur["id"],cur["id"]))
            conn.execute("UPDATE banners SET sort_order=? WHERE id=?",(cur["sort_order"],other["id"]))
            conn.execute("UPDATE banners SET sort_order=? WHERE id=?",(other["sort_order"],cur["id"])); conn.commit()
    conn.close(); return RedirectResponse("/admin#publicidade",303)

@app.post("/admin/banners/{bid}/excluir")
def admin_delete_banner(request: Request, bid:int):
    require_user(request,"admin"); conn=db(); banner=conn.execute("SELECT image_filename FROM banners WHERE id=?",(bid,)).fetchone(); conn.execute("DELETE FROM banners WHERE id=?",(bid,)); conn.commit(); conn.close()
    if banner and banner["image_filename"]:
        try: (UPLOAD_DIR/banner["image_filename"]).unlink(missing_ok=True)
        except OSError: pass
    return RedirectResponse("/admin#publicidade",303)

@app.get("/anuncio/{bid}")
def banner_click(bid:int):
    conn=db(); banner=conn.execute("SELECT link FROM banners WHERE id=? AND active=1",(bid,)).fetchone()
    if not banner: conn.close(); raise HTTPException(404)
    conn.execute("UPDATE banners SET clicks=clicks+1 WHERE id=?",(bid,)); conn.commit(); conn.close()
    return RedirectResponse(banner["link"] or "/",303)

@app.get("/health")
def health(): return JSONResponse({"ok":True,"service":"NowUp"})
