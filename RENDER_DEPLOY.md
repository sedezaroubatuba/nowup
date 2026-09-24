# Publicar a NowUp no Render

Esta versão já está preparada para Render com Docker e disco persistente.

## 1) Coloque a pasta em um repositório Git
Crie um repositório privado no GitHub e envie todos os arquivos desta pasta, incluindo `Dockerfile` e `render.yaml`.

## 2) No Render
1. Entre no Render.
2. Escolha **New > Blueprint**.
3. Conecte o repositório da NowUp.
4. O Render lerá `render.yaml`.
5. Informe `NOWUP_ADMIN_EMAIL` e `NOWUP_ADMIN_PASSWORD` quando solicitado. Use uma senha forte e diferente da senha de demonstração.
6. Confirme a criação do serviço.

## 3) Teste
Quando o deploy terminar, abra a URL `*.onrender.com` criada pelo Render.

## 4) Domínio próprio
No serviço do Render, abra **Settings > Custom Domains**, adicione seu domínio e siga os registros DNS informados pelo Render.

## Dados persistentes
O banco e as imagens são gravados em `/app/persist`, que está ligado ao disco persistente definido no `render.yaml`.

## Importante
O plano precisa suportar Persistent Disk. A versão gratuita não deve ser usada com SQLite/uploads locais porque o filesystem padrão é efêmero.
