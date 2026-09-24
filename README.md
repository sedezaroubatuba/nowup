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

## Segurança e operação

Configure no Render, sem gravar os valores no repositório:

- `NOWUP_ADMIN_EMAIL`: e-mail exclusivo do administrador.
- `NOWUP_ADMIN_PASSWORD`: senha inicial com pelo menos 12 caracteres. Ela só é usada para criar a conta em um banco novo; alterar a variável depois não redefine a senha existente. Use a recuperação por e-mail para trocar a senha.
- `NOWUP_BASE_URL`: origem pública exata, por exemplo `https://nowup-i9n4.onrender.com`; os formulários POST exigem Origin ou Referer desta origem.
- `NOWUP_HTTPS=1`, `BREVO_API_KEY` e `NOWUP_EMAIL_FROM`: chave e remetente verificado para confirmação e recuperação.
- `NOWUP_DB`, `NOWUP_UPLOAD_DIR`, `NOWUP_BACKUP_DIR`: caminhos em armazenamento persistente. Os três não devem depender do sistema de arquivos efêmero do container.

O comando `python backup.py` cria um arquivo `.tar.gz` com uma cópia consistente do SQLite e os uploads. Agende sua execução diária no serviço de hospedagem ou em um job externo que tenha acesso aos volumes. Mantenha uma cópia fora do mesmo servidor e teste periodicamente a restauração em ambiente isolado. `NOWUP_BACKUP_KEEP` define quantos arquivos locais conservar (padrão 14). Não exponha os backups pela pasta pública `/uploads`.

Para testar em um ambiente separado: `pip install -r requirements-dev.txt && pytest -q`. Confira entrada de cada perfil, confirmação pelo Brevo, recuperação de senha, bloqueio de tentativas, ações administrativas e restauração do backup antes de publicar.

**Pendência:** autenticação em duas etapas do administrador. O acesso de administrador continua protegido pela senha e sessão curta, mas o segundo fator ainda não foi implementado. A implantação, o agendamento de backup e a configuração do Brevo exigem acesso aos respectivos serviços.
