"""V457: merchant-only bottom shortcuts, without modifying customer navigation."""
from test_merchant228 import env
from bs4 import BeautifulSoup

def test_merchant_panel_has_fixed_shortcuts_without_customer_nav(env):
    m,client,*_=env
    response=client.get('/painel')
    assert response.status_code==200
    soup=BeautifulSoup(response.text,'html.parser')
    menus=soup.select('nav.nu457-merchant-bottom')
    assert len(menus)==1
    assert not soup.select('nav.mobile-bottom-nav')
    assert not soup.select('nav.nu198-bottom')
    links={a.get('data-merchant-tab457'):a.get('href') for a in menus[0].select('a')}
    assert links=={
        'inicio':'/painel#inicio',
        'historico':'/painel/todos-produtos',
        'cadastro':'/painel#cardapio',
        'pedidos':'/painel#pedidos-ativos',
    }

def test_history_panel_also_has_merchant_bottom_navigation(env):
    m,client,*_=env
    response=client.get('/painel/todos-produtos')
    assert response.status_code==200
    soup=BeautifulSoup(response.text,'html.parser')
    assert len(soup.select('nav.nu457-merchant-bottom'))==1
    assert not soup.select('nav.mobile-bottom-nav')
    assert 'merchant-bottom457.css' in response.text
    assert 'merchant-bottom457.js' in response.text

def test_public_page_never_inherits_merchant_shortcuts(env):
    m,client,*_=env
    response=client.get('/profissionais')
    assert response.status_code==200
    soup=BeautifulSoup(response.text,'html.parser')
    assert not soup.select('nav.nu457-merchant-bottom')
    assert len(soup.select('nav.mobile-bottom-nav'))==1
