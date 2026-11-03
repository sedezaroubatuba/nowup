"""Planos comerciais atuais; ambos incluem todos os recursos do lojista."""
FEATURES = ('Todos os recursos do painel do lojista: produtos, combos, ingredientes, '
            'acompanhamentos, adicionais, promoções, banners, slides, configurações '
            'e atualizações disponibilizadas no painel.')
PLANS = {
    'cardapio': ('Só cardápio/catálogo', 4990),
    'ambos': ('Cardápio/catálogo + vitrine', 9990),
}

def admin_plans():
    return [dict(id=key, name=name, price=price, features=FEATURES +
                 (' Link próprio, sem exposição na vitrine geral.' if key == 'cardapio'
                  else ' Link próprio e exposição na vitrine geral.'))
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
