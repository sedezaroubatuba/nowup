import os, json
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def configured():
    return bool(
        os.getenv("BREVO_API_KEY","").strip()
        and os.getenv("NOWUP_EMAIL_FROM","").strip()
        and os.getenv("NOWUP_BASE_URL","").strip()
    )

def send_email(to_email: str, to_name: str, subject: str, html: str):
    api_key=os.getenv("BREVO_API_KEY","").strip()
    sender_email=os.getenv("NOWUP_EMAIL_FROM","").strip()
    if not api_key or not sender_email:
        return False
    payload={
      "sender":{"name":"NowUp","email":sender_email},
      "to":[{"email":to_email,"name":to_name or to_email}],
      "subject":subject,
      "htmlContent":html
    }
    req=Request(
      "https://api.brevo.com/v3/smtp/email",
      data=json.dumps(payload).encode("utf-8"),
      headers={"api-key":api_key,"accept":"application/json","content-type":"application/json"},
      method="POST"
    )
    try:
        with urlopen(req,timeout=12) as resp:
            return 200 <= resp.status < 300
    except (HTTPError,URLError,TimeoutError):
        return False

def send_verification(to_email: str, to_name: str, token: str):
    base=os.getenv("NOWUP_BASE_URL","").strip().rstrip("/")
    if not base:
        return False
    link=f"{base}/verificar-email?token={quote(token)}"
    html=f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
    <h2>Confirme seu cadastro na NowUp</h2>
    <p>Olá, {to_name}.</p>
    <p>Recebemos seu cadastro. Confirme seu e-mail para concluir:</p>
    <p><a href="{link}" style="background:#2457e6;color:#fff;padding:12px 18px;border-radius:10px;text-decoration:none;font-weight:bold">Confirmar meu e-mail</a></p>
    <p style="color:#667085;font-size:13px">O link expira em 24 horas. Se você não fez este cadastro, ignore esta mensagem.</p>
    </div>"""
    return send_email(to_email,to_name,"Confirme seu cadastro na NowUp",html)
