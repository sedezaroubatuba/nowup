"""Planos comerciais atuais; com permissões por canal de pedidos."""
FEATURES = ('Todos os recursos do painel do lojista: produtos, combos, ingredientes, '
            'acompanhamentos, adicionais, promoções, banners, slides, configurações '
            'e atualizações disponibilizadas no painel.')
PLANS = {
    'cardapio': ('Só cardápio/catálogo', 4990),
    'ambos': ('Vitrine (plano anterior, fora da oferta piloto)', 9990),
    'completo': ('Cardápio + Vitrine de Ubatuba por cortesia', 4990),
}

def admin_plans():
    descriptions = {
        'cardapio': ' Link próprio e pedidos no WhatsApp, com Instagram e site; sem exposição na vitrine geral.',
        'ambos': ' Exposição na vitrine geral, com cardápio e pedidos somente dentro do NowUp.',
        'completo': ' Cardápio por R$ 49,90/mês e Vitrine de Ubatuba por cortesia durante o piloto, sujeita à aprovação administrativa. Pedidos e painéis separados; mesma conta do lojista.',
    }
    return [dict(id=key, name=name, price=price, features=FEATURES + descriptions[key])
            for key, (name, price) in PLANS.items()]

def synchronize_admin(conn):
    """Retain the old definitions for audit; never rewrite store contracts."""
    import json
    expected = admin_plans()
    current = conn.execute("SELECT id,data FROM adm227_entities WHERE kind='plans' ORDER BY id").fetchall()
    if [(r[0], json.loads(r[1])) for r in current] == list(enumerate(expected, 1)):
        return
    for row in current:
        conn.execute("INSERT OR IGNORE INTO adm227_entities(kind,id,data) VALUES('plans_archive339',?,?)", (row[0], row[1]))
    conn.execute("DELETE FROM adm227_entities WHERE kind='plans'")
    for index, value in enumerate(expected, 1):
        conn.execute("INSERT INTO adm227_entities(kind,id,data) VALUES('plans',?,?)", (index, json.dumps(value, ensure_ascii=False)))


def showcase_city409(city, state='SP'):
    return (city or '').strip().casefold() == 'ubatuba' and (state or 'SP').strip().upper() == 'SP'


def offers409(pro):
    details=dict(pro)
    keys=('cardapio','completo') if showcase_city409(details.get('city'),details.get('state')) else ('cardapio',)
    return {key:PLANS[key] for key in keys}


def for_store(pro):
    # Keep historical plan identifiers readable; new sales use offers409.
    return dict(PLANS)


def require_internal_checkout405(pro, request, channel):
    """The internal endpoint cannot grant or impersonate the WhatsApp channel."""
    from fastapi import HTTPException
    if pro['plan_active'] not in ('ambos', 'completo'):
        raise HTTPException(403, 'Este plano finaliza pedidos pelo link próprio no WhatsApp.')
    if (channel != 'internal' or request.headers.get('x-nowup-store-app') == '256'
            or request.query_params.get('loja') == '1'
            or request.query_params.get('origem') == 'externo'):
        raise HTTPException(403, 'Para pedir pelo link próprio, use a finalização pelo WhatsApp disponível no plano da loja.')
