from bs4 import BeautifulSoup
from test_merchant228 import env

def test_panel_keeps_help_in_settings_and_sound_in_dialog(env):
    m,client,owner,pid,_=env
    page=client.get('/painel');assert page.status_code==200
    soup=BeautifulSoup(page.text,'html.parser')
    progress=soup.select_one('[data-onboarding416]')
    assert progress.find_parent(id='perfil')
    sound=soup.select_one('[data-order-alerts]')
    assert sound.find_parent('dialog')['id']=='merchant-sound427'
    assert not sound.find_parent('dialog').has_attr('open')
    assert soup.select_one('#stock-reminder427 [data-close427]')
    assert soup.select_one('#perfil [data-open-stock427]')
    assert not soup.select_one('.pro-dashboard > [data-onboarding416]')
    assert not soup.select_one('.v60-top .v61-bell')
    assert soup.select_one('#perfil .v61-bell')
