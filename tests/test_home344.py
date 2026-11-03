from test_checkout247 import checkout

def test_home_exposure_batches_writes_and_keeps_daily_uniqueness(checkout):
    m, *_ = checkout
    today = m.datetime.now(m.SAO_PAULO_TZ).date().isoformat()
    with m.db() as c:
        rows = [dict(r) for r in c.execute('SELECT p.*,0 AS rating,1 AS product_count FROM professionals p')]
        for row in rows: row['shop_status'] = m.shop_status(row)
        statements = []
        c.set_trace_callback(statements.append)
        for _ in range(2):
            statements.clear()
            selected, rotating, catalogs = m.select_home_stores90(c, rows, 'batch344', today)
            writes = [s for s in statements if s.upper().startswith('INSERT OR IGNORE INTO HOME_STORE_EXPOSURE90')]
            assert len(writes) <= 1
            assert selected
        assert c.execute("SELECT COUNT(*) FROM (SELECT professional_id FROM home_store_exposure90 WHERE visitor_key='batch344' GROUP BY professional_id HAVING COUNT(*)>1)").fetchone()[0] == 0
