"""Apply the owner's requested plan once, without creating a second store."""
import json


def upgrade_sede_zero(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS nowup_migrations352 (name TEXT PRIMARY KEY)')
    key = 'sede-zero-completo352'
    if conn.execute('SELECT 1 FROM nowup_migrations352 WHERE name=?', (key,)).fetchone():
        return False
    p = conn.execute("SELECT p.* FROM professionals p JOIN users u ON u.id=p.user_id WHERE p.slug='samuel-dos-santos-silva' AND upper(trim(p.display_name))='ADEGA SEDE ZERO' AND p.city='Ubatuba' AND p.is_demo=0 AND p.blocked=0 AND p.admission_status='approved' AND u.is_active=1").fetchone()
    if not p:
        return False
    conn.execute("UPDATE professionals SET plan_active='completo',is_premium=1 WHERE id=?", (p['id'],))
    row = conn.execute("SELECT data FROM adm227_entities WHERE kind='storemeta' AND id=?", (p['id'],)).fetchone()
    meta = json.loads(row[0]) if row else {}
    meta['plan'] = 'completo'
    # Keep any negotiated contract price, due dates, and payment history intact.
    conn.execute("INSERT INTO adm227_entities(kind,id,data) VALUES('storemeta',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data", (p['id'], json.dumps(meta, ensure_ascii=False)))
    conn.execute("INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,'','whatsapp') ON CONFLICT(professional_id) DO UPDATE SET mode='whatsapp'", (p['id'],))
    conn.execute('INSERT INTO nowup_migrations352(name) VALUES(?)', (key,))
    return True


def install(g):
    @g['app'].on_event('startup')
    def requested_upgrade352():
        with g['db']() as conn:
            changed = upgrade_sede_zero(conn)
            conn.commit()
        if changed:
            print('[plan352] Existing Sede Zero store enabled for catalogue link and WhatsApp', flush=True)
