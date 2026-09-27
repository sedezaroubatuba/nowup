# NowUp — MVP funcional

Sistema web completo para divulgação de profissionais, sem intermediação de pagamentos.

## O que funciona
- Busca por serviço, categoria, cidade, bairro e CEP
- Cadastro/login separado de cliente e profissional
- Perfil profissional público com CPF/CNPJ mascarado
- Até 10 fotos por profissional, com foto de capa
- Feed de trabalhos publicados
- Avaliações por clientes autenticados
- Denúncias privadas por clientes autenticados
- Contagem de visualizações e cliques no WhatsApp
- Painel profissional
- Painel administrativo
- Categorias criadas/ativadas pelo Admin
- Profissionais: verificação, destaque e bloqueio
- Denúncias: revisão/resolução
- Banners/publicidade
- Sugestões
- Cookies, Quem Somos, Privacidade e Termos
- Banco SQLite persistente
- Dockerfile para hospedagem

## Rodar localmente
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```
Abra: http://127.0.0.1:8000

## Admin de demonstração
- E-mail: `admin@nowup.local`
- Senha: `nowup2026`

**Troque em produção** usando `NOWUP_ADMIN_EMAIL` e `NOWUP_ADMIN_PASSWORD` antes de criar o banco.

## Para publicar no domínio
Hospede o projeto em um servidor/container persistente (VPS, Render, Railway, Fly.io ou similar), mantenha `/data` e `/uploads` em volume persistente e aponte o domínio para a hospedagem. Ative HTTPS e defina `NOWUP_HTTPS=1`.

## Antes do lançamento comercial
Recomenda-se: política LGPD final, termos revisados por advogado, backups automáticos, e-mail de recuperação de senha, logs/auditoria, proteção CSRF/rate limit, armazenamento de imagens em objeto (S3/Supabase Storage) quando houver escala e migração do SQLite para PostgreSQL quando o uso crescer.
