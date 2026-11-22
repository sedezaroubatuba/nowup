"""Regression tests for grouped catalog items and owner-specific promotions (v260)."""
import importlib
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    directory = tmp_path_factory.mktemp("groups260")
    os.environ["NOWUP_DB"] = str(directory / "test.db")
    os.environ["NOWUP_UPLOAD_DIR"] = str(directory / "uploads")
    os.environ["NOWUP_ADMIN_EMAIL"] = "admin@test.invalid"
    os.environ["NOWUP_ADMIN_PASSWORD"] = "isolated-local-test-password"
    m = importlib.import_module("app")
    m.init_db()
    with m.db() as conn:
        stores = conn.execute(
            "SELECT id,user_id,slug FROM professionals ORDER BY id LIMIT 2"
        ).fetchall()
        assert len(stores) == 2
        for idx, pro in enumerate(stores):
            conn.execute(
                "UPDATE professionals SET is_premium=1,plan_active='ambos',offer_mode='menu' WHERE id=?",
                (pro["id"],),
            )
            conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
                         (f"group-test-{idx}", pro["user_id"],
                          (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()))
            conn.execute("INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",
                         (pro["id"], "Tabacaria", 10, 1, m.now_iso()))
        conn.commit()
    client = TestClient(m.app, headers={"Origin": "http://testserver"})
    client.cookies.set("nowup_session", "group-test-0")
    return m, client, stores


def test_create_items_and_single_public_group(env):
    m, client, stores = env
    pid = stores[0]["id"]
    response = client.post("/painel/cardapio/agrupadores",
                           data={"name": "Essências – sabores", "category": "Tabacaria"},
                           follow_redirects=False)
    assert response.status_code == 303
    with m.db() as conn:
        group = conn.execute(
            "SELECT * FROM products WHERE professional_id=? AND is_group_header260=1 ORDER BY id DESC LIMIT 1",
            (pid,),
        ).fetchone()
    assert group and group["category"] == "Tabacaria"
    for name in ("Morango", "Uva", "Melancia"):
        assert client.post(
            f"/painel/cardapio/agrupadores/{group['id']}/itens",
            data={"name": name, "price": "12,00", "available": "1"},
            follow_redirects=False,
        ).status_code == 303
    with m.db() as conn:
        children = conn.execute("SELECT * FROM products WHERE group_parent_id260=? ORDER BY id",
                                (group["id"],)).fetchall()
    assert len(children) == 3
    response = client.get(f"/p/{stores[0]['slug']}/menu")
    assert response.status_code == 200
    assert response.text.count('data-group260="1"') == 1
    assert 'data-id="' + str(children[0]["id"]) + '"' in response.text
    assert response.text.count('Ver 3 sabores') == 1
    assert 'groups260.css' in response.text
    return group, children


def test_availability_promotion_dates_and_order_pricing(env):
    m, client, stores = env
    with m.db() as conn:
        group = conn.execute(
            "SELECT * FROM products WHERE professional_id=? AND is_group_header260=1 ORDER BY id DESC LIMIT 1",
            (stores[0]["id"],),
        ).fetchone()
    if not group:
        test_create_items_and_single_public_group(env)
        with m.db() as conn:
            group = conn.execute("SELECT * FROM products WHERE professional_id=? AND is_group_header260=1 ORDER BY id DESC LIMIT 1",
                                 (stores[0]["id"],)).fetchone()
    with m.db() as conn:
        children = conn.execute("SELECT * FROM products WHERE group_parent_id260=? ORDER BY id",
                                (group["id"],)).fetchall()
    selected = [children[0]["id"], children[1]["id"]]
    today = datetime.now(m.SAO_PAULO_TZ).date().isoformat()
    response = client.post(
        f"/painel/cardapio/agrupadores/{group['id']}/promocao",
        data={"item_ids": selected, "promo_price": "10,00", "promo_start": today},
        follow_redirects=False,
    )
    assert response.status_code == 303
    with m.db() as conn:
        values = conn.execute("SELECT * FROM products WHERE group_parent_id260=? ORDER BY id",
                              (group["id"],)).fetchall()
        assert [p["promo_price_cents"] for p in values] == [1000, 1000, 0]
        assert m.nowup_groups260.effective_promo_cents(values[0], today) == 1000
        assert m.nowup_groups260.effective_promo_cents(values[2], today) == 0
    assert client.post(
        f"/painel/cardapio/agrupadores/{group['id']}/itens/{children[0]['id']}/disponibilidade",
        data={"available": "0"}, follow_redirects=False,
    ).status_code == 303
    with m.db() as conn:
        assert conn.execute("SELECT available FROM products WHERE id=?",
                            (children[0]["id"],)).fetchone()[0] == 0
    response = client.get(f"/p/{stores[0]['slug']}/menu")
    assert "Morango" in response.text and "Indisponível" in response.text


def test_no_cross_store_mutation_and_group_removal_preserves_products(env):
    m, client, stores = env
    with m.db() as conn:
        group = conn.execute(
            "SELECT id FROM products WHERE professional_id=? AND is_group_header260=1 ORDER BY id DESC LIMIT 1",
            (stores[0]["id"],),
        ).fetchone()
    client.cookies.set("nowup_session", "group-test-1")
    assert client.post(
        f"/painel/cardapio/agrupadores/{group['id']}/promocao",
        data={"promo_price": "1,00"}, follow_redirects=False,
    ).status_code == 404
    assert client.post(
        f"/painel/cardapio/agrupadores/{group['id']}/excluir",
        follow_redirects=False,
    ).status_code == 404
    client.cookies.set("nowup_session", "group-test-0")
    assert client.post(
        f"/painel/cardapio/agrupadores/{group['id']}/excluir",
        follow_redirects=False,
    ).status_code == 303
    with m.db() as conn:
        assert conn.execute("SELECT 1 FROM products WHERE id=?", (group["id"],)).fetchone() is None
        assert conn.execute(
            "SELECT COUNT(*) FROM products WHERE professional_id=? AND group_parent_id260=0 AND name IN ('Morango','Uva','Melancia')",
            (stores[0]["id"],),
        ).fetchone()[0] == 3
