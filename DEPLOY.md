# Publicar a NowUp no domínio

A aplicação está pronta para rodar em qualquer hospedagem com Docker ou Python 3.12.

## Variáveis obrigatórias em produção
- `NOWUP_ADMIN_EMAIL`: seu e-mail de administrador
- `NOWUP_ADMIN_PASSWORD`: senha forte do administrador
- `NOWUP_HTTPS=1`

## Persistência
Monte volumes persistentes em:
- `/app/data` — banco SQLite
- `/app/uploads` — fotos enviadas pelos profissionais

## Domínio
Depois que a hospedagem gerar o endereço público, configure no provedor do domínio um CNAME/A conforme a hospedagem orientar e ative HTTPS.

## Escala
Para o MVP, SQLite é adequado. Se o tráfego crescer bastante, migre para PostgreSQL e armazenamento S3/Supabase Storage. A interface pode continuar a mesma.
