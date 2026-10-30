from fastapi import FastAPI,HTTPException,Form
from fastapi.testclient import TestClient
from nowup_feedback270 import install

def test_html_feedback_and_json_contract():
    app=FastAPI();install(app)
    @app.post('/bairro')
    def duplicate():raise HTTPException(400,'Este bairro já está cadastrado. <script>alert(1)</script>')
    @app.post('/validar')
    def validate(eta:int=Form(...)):return {'ok':True}
    client=TestClient(app)
    html=client.post('/bairro',headers={'Accept':'text/html'})
    assert html.status_code==400 and 'text/html' in html.headers['content-type']
    assert 'Este bairro já está cadastrado.' in html.text
    assert '<script>alert(1)</script>' not in html.text and '&lt;script&gt;' in html.text
    assert 'Voltar e conferir' in html.text
    api=client.post('/bairro',headers={'Accept':'application/json'})
    assert api.status_code==400 and api.json()['detail'].startswith('Este bairro')
    assert client.post('/validar',data={'eta':'errado'},headers={'Accept':'text/html'}).status_code==422
    assert 'Algum campo está vazio' in client.post('/validar',headers={'Accept':'text/html'}).text
    assert isinstance(client.post('/validar').json()['detail'],list)
    assert client.get('/ausente',headers={'Accept':'text/html'}).status_code==404
