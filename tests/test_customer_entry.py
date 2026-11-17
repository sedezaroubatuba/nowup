"""Customer-only public menu entry and merchant session isolation."""
from test_checkout247 import checkout


def _slug(url):
    return url.split("/")[2]


def test_shared_cardapio_guest_sees_customer_only_entry(checkout, monkeypatch):
    m, client, order_url, _, _, _ = checkout
    slug = _slug(order_url)
    monkeypatch.setattr(m, "current_user", lambda request: None)
    redirect = client.get(f"/p/{slug}/cardapio", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"] == f"/p/{slug}/menu?conta=1"
    page = client.get(redirect.headers["location"])
    assert page.status_code == 200
    assert "Criar conta de cliente" in page.text
    assert "Já sou cliente" in page.text
    assert "Painel profissional" not in page.text
    client_login = client.get("/entrar?tipo=cliente")
    assert client_login.status_code == 200
    assert "Cadastrar minha loja" not in client_login.text
    assert "Entrar como lojista" not in client_login.text


def test_shared_menu_never_displays_saved_merchant_identity(checkout, monkeypatch):
    m, client, order_url, _, _, _ = checkout
    slug = _slug(order_url)
    with m.db() as conn:
        owner = conn.execute("SELECT user_id FROM professionals WHERE slug=?", (slug,)).fetchone()[0]
    merchant = {"id": owner, "role": "professional", "name": "OWNER_PRIVATE_SESSION"}
    monkeypatch.setattr(m, "current_user", lambda request: merchant)
    redirect = client.get(f"/p/{slug}/cardapio", follow_redirects=False)
    assert redirect.headers["location"] == f"/p/{slug}/menu?conta=1"
    page = client.get(redirect.headers["location"])
    assert page.status_code == 200
    assert "OWNER_PRIVATE_SESSION" not in page.text
    assert "Painel profissional" not in page.text
    assert "Criar conta de cliente" in page.text
    assert '"ownerView": true' in page.text
    merchant_link = client.get("/lojista/entrar", follow_redirects=False)
    assert merchant_link.headers["location"] == "/painel"


def test_customer_share_link_stays_in_menu_without_login_banner(checkout, monkeypatch):
    m, client, order_url, _, _, customer = checkout
    slug = _slug(order_url)
    monkeypatch.setattr(m, "current_user", lambda request: customer)
    redirect = client.get(f"/p/{slug}/cardapio?origem=externo", follow_redirects=False)
    assert redirect.headers["location"] == f"/p/{slug}/menu?origem=externo"
    page = client.get(redirect.headers["location"])
    assert page.status_code == 200
    assert 'class="nowup-customer-entry"' not in page.text
    assert "Painel profissional" not in page.text
