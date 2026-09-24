# NowUp — guia de profissionalização

Este arquivo existe para que um futuro desenvolvedor entenda rapidamente o projeto e não precise redescobrir decisões já tomadas.

## Arquitetura atual
- FastAPI + Jinja2
- SQLite em disco persistente no Render
- Uploads de imagens no disco persistente
- Sessões salvas no banco
- Senhas com PBKDF2-HMAC-SHA256
- Render via Docker/Blueprint
- GitHub: sedezaroubatuba/nowup

## Perfis
- Cliente: pesquisa, avaliação e denúncia
- Profissional: perfil, categorias, fotos, posts/status e WhatsApp
- Administrador: gestão de clientes, profissionais, categorias, denúncias, publicidade e aparência

## Segurança já preparada
- Cookies HttpOnly/SameSite e HTTPS
- Senha mínima de 8 caracteres no cadastro
- Confirmação de senha e aceite de Termos/Privacidade
- Validação de formato + domínio de e-mail com email-validator
- E-mail do administrador reservado
- Confirmação de e-mail preparada via Brevo
- Profissional fica oculto enquanto aguarda confirmação de e-mail quando o serviço de e-mail estiver configurado
- Login por tipo de perfil
- Entrada administrativa pode forçar nova autenticação e usa sessão curta

## E-mail transacional
Variáveis:
- BREVO_API_KEY
- NOWUP_EMAIL_FROM
- NOWUP_BASE_URL

Quando essas três variáveis existem, novos cadastros recebem link de confirmação por e-mail. O link expira em 24 horas.

## Aparência editável no admin
Tabela site_settings:
- brand_name
- primary_color
- accent_color
- font_family
- hero_title
- hero_subtitle
- public_email
- support_whatsapp

## Antes de divulgação em escala
1. Adicionar proteção CSRF aos formulários.
2. Adicionar rate limiting em login, cadastro, avaliações e denúncias.
3. Adicionar recuperação de senha por e-mail.
4. Adicionar auditoria das ações administrativas.
5. Adicionar backup automático e teste periódico de restauração.
6. Migrar SQLite para PostgreSQL quando houver crescimento relevante de acessos/escritas.
7. Migrar imagens para object storage/CDN antes de grande escala.
8. Adicionar moderação e política de remoção de conteúdo.
9. Criar testes automatizados de cadastro, login, perfil, admin e uploads.
10. Revisar LGPD, termos e política de privacidade com profissional jurídico antes de expansão nacional.

## Prioridade de custo
No MVP, prefira:
- manter cadastro gratuito;
- usar e-mail transacional em plano gratuito;
- evitar SMS/WhatsApp de autenticação enquanto o volume for baixo;
- só migrar infraestrutura conforme métricas reais justificarem.

## Checklist de entrega de um futuro programador
O desenvolvedor deve entregar cada mudança com:
- commit no GitHub;
- deploy de teste;
- teste no celular;
- confirmação de que banco e uploads persistem após redeploy;
- documentação de novas variáveis de ambiente;
- rollback possível.
