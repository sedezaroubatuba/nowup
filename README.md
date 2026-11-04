# NowUp

Cardápio/catálogo digital, pedidos e vitrine regional em FastAPI/Jinja.
A mensalidade e os pagamentos dos pedidos não estão automatizados pelo Asaas.

## Operação atual

- Cadastro e sessões distintos por papel; contas exclusivas no cardápio independente.
- Catálogo, combos, personalizações, adicionais, promoções, pedidos e painel de separação.
- Taxa por bairro, pedido mínimo, revisão e acompanhamento do pedido.
- Documentos de lojistas e comprovantes privados, aprovação manual e trilha administrativa.
- PostgreSQL opt-in e SQLite para uso local; falha no PostgreSQL não troca para outro banco.
- Backup externo criptografado quando configurado; verificar status e testar recuperação.

## Rodar localmente

Use Python 3.12. Configure um banco descartável, diretório de fotos e as variáveis
NOWUP_ADMIN_EMAIL e NOWUP_ADMIN_PASSWORD (mínimo de 12 caracteres) antes da primeira
inicialização. Não há credencial administrativa padrão suportada.

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Em produção, use HTTPS e NOWUP_HTTPS=1. Para PostgreSQL, configure
NOWUP_DB_ENGINE=postgres e DATABASE_URL no provedor, sem credenciais no repositório.
As imagens continuam precisando de armazenamento persistente.

## Testes e liberação

Consulte VERIFICACAO-V348.md para comandos, correções, limites, recuperação e pendências.
O health check /health consulta o banco e capacidade mínima; ele não substitui o
monitoramento de pedidos nem comprova entrega de notificações.

Antes da expansão comercial, validar cobrança, textos e procedimentos de dados,
restauração real de backup PostgreSQL, atendimento e capacidade sob carga representativa.
