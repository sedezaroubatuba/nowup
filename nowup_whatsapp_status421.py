"""Per-store manual WhatsApp status messages. No outbound messaging or sent receipt."""
import json
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

STATUSES = (
    ('new', 'Recebido', 'Olá {{nome_cliente}}, seu pedido {{numero_pedido}} foi recebido na {{nome_loja}}! Já estamos preparando. Obrigado!'),
    ('confirmed', 'Pedido confirmado', 'Olá {{nome_cliente}}, seu pedido {{numero_pedido}} foi confirmado na {{nome_loja}}! Obrigado!'),
    ('preparing', 'Em preparo', 'Olá {{nome_cliente}}, seu pedido {{numero_pedido}} entrou em preparo na {{nome_loja}}! Já já sai para entrega.'),
    ('out_for_delivery', 'Saiu para entrega', 'Olá {{nome_cliente}}, seu pedido {{numero_pedido}} saiu para entrega da {{nome_loja}}! Fica de olho aí.'),
    ('completed', 'Entregue', 'Olá {{nome_cliente}}, seu pedido {{numero_pedido}} foi entregue! Obrigado pela preferência na {{nome_loja}}, volta sempre!'),
    ('cancelled', 'Cancelado', 'Olá {{nome_cliente}}, seu pedido {{numero_pedido}} foi cancelado na {{nome_loja}}. Qualquer coisa chama a gente aqui.'),
)
DEFAULTS = {key: text for key, _, text in STATUSES}


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS whatsapp_status_settings421 (
        professional_id INTEGER PRIMARY KEY REFERENCES professionals(id) ON DELETE CASCADE,
        enabled INTEGER NOT NULL DEFAULT 1, templates_json TEXT NOT NULL DEFAULT '{}')''')


def settings(c, professional_id):
    row = c.execute('SELECT enabled,templates_json FROM whatsapp_status_settings421 WHERE professional_id=?', (professional_id,)).fetchone()
    custom = {}
    if row:
        try: custom = json.loads(row['templates_json'])
        except (ValueError, TypeError): pass
    if not isinstance(custom, dict): custom = {}
    return {'enabled': bool(row['enabled']) if row else True,
            'templates': {key: custom.get(key, text) if isinstance(custom.get(key, text), str) else text for key, text in DEFAULTS.items()}}


def install(g):
    def startup():
        with g['db']() as c: initialize(c); c.commit()
    g['app'].router.add_event_handler('startup', startup)

    def store(request, c):
        user = g['require_user'](request, 'professional')
        pro = c.execute('SELECT * FROM professionals WHERE user_id=?', (user['id'],)).fetchone()
        if not pro: raise HTTPException(404, 'Loja não encontrada')
        return pro

    @g['app'].get('/painel/cardapio/mensagens-whatsapp')
    def edit(request: Request):
        with g['db']() as c:
            pro = store(request, c)
            config = settings(c, pro['id'])
        return g['templates'].TemplateResponse('whatsapp_status421.html', g['context'](request,
            pro=pro, wa_settings421=config, wa_statuses421=STATUSES, wa_defaults421=DEFAULTS),
            headers={'Cache-Control': 'private, no-store'})

    @g['app'].post('/painel/cardapio/mensagens-whatsapp')
    async def save(request: Request):
        form = await request.form()
        action = str(form.get('action', 'save'))
        with g['db']() as c:
            pro = store(request, c)
            enabled = 1 if form.get('enabled') == '1' else 0
            texts = dict(DEFAULTS) if action == 'restore' else {key: str(form.get(key, '')).strip() for key in DEFAULTS}
            if any(not text or len(text) > 1500 for text in texts.values()):
                raise HTTPException(400, 'Preencha todos os textos com até 1.500 caracteres.')
            c.execute('''INSERT INTO whatsapp_status_settings421(professional_id,enabled,templates_json)
                VALUES(?,?,?) ON CONFLICT(professional_id) DO UPDATE SET
                enabled=excluded.enabled,templates_json=excluded.templates_json''',
                (pro['id'], enabled, json.dumps(texts, ensure_ascii=False)))
            c.commit()
        return RedirectResponse('/painel/cardapio/mensagens-whatsapp?ok=salvo', 303)
