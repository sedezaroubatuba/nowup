# PostgreSQL — preparação V239

O suporte está em `codex/postgresql-v239`. O banco publicado não foi trocado. SQLite continua sendo o padrão; PostgreSQL só é usado com `NOWUP_DB_ENGINE=postgres` e `DATABASE_URL` válida. Falhas no PostgreSQL não fazem o aplicativo abrir um SQLite vazio.

## O que está preparado

- Conexão compartilhada pelos módulos principal, CMS, aparência e confirmação de e-mail; pool limitado por `NOWUP_PG_POOL_SIZE` (padrão 8).
- Compatibilidade do SQL legado, ids e sequências, conflitos de inserção, consultas de data, relatórios e referências entre tabelas. Preços continuam em centavos inteiros; totais inteiros não são convertidos em ponto flutuante.
- Pedidos repetidos usam bloqueio por cliente/loja/chave na mesma transação, além da chave única. Fluxos administrativos que exigiam exclusão de escritor mantêm bloqueio transacional.
- Cópia SQLite consistente, incluindo WAL, para um destino vazio. Todos os registros são conferidos por contagem e SHA-256 por tabela antes de confirmar a transação. O destino existente é recusado; o SQLite de origem não é apagado nem alterado.
- Backup nativo com `pg_dump` e as fotos, mantendo criptografia e armazenamento externo existentes. O formato antigo de backup SQLite continua aceito. `pg_restore` só é utilizado em um destino novo e vazio com confirmação explícita.
- Modo de manutenção para suspender as páginas e os trabalhadores de notificações durante a troca; `/health` continua disponível.

## Antes de ativar em produção

1. Criar um PostgreSQL 18 no Render, na mesma região do serviço NowUp. Escolher o plano no painel; este repositório não cria cobrança ou banco automaticamente.
2. Salvar a **Internal Database URL** como segredo `DATABASE_URL` no Render. Não inserir a URL no GitHub, nos arquivos ou no chat. Manter `NOWUP_DB_ENGINE=sqlite` neste primeiro momento.
3. Conferir os testes do workflow `PostgreSQL migration checks`: regressões SQLite, PostgreSQL 18 real, pedido concorrente, backup/restauração nativos e construção do Docker. O cliente PostgreSQL 18 está incluído no Docker.
4. Validar primeiro em homologação. Depois publicar o código compatível no serviço principal, ainda com SQLite. Preservar `/app/persist/uploads` e o disco atual: esta mudança de banco não transfere as imagens para outro armazenamento.
5. Conferir backup externo recente e restauração em ambiente isolado. Um teste sintético não confirma as credenciais do R2 nem a existência de todas as fotos reais.

## Troca controlada

No Render, depois de disponibilizar este código com SQLite:

1. Ativar `NOWUP_MAINTENANCE=1`, fazer deploy e aguardar o encerramento da instância anterior. Não deixar outra instância, painel antigo ou trabalhador escrevendo no SQLite.
2. No Shell do serviço, usar a URL já salva como segredo; não colá-la no comando:

```sh
NOWUP_DB_ENGINE=postgres python migrate_postgres239.py --source /app/persist/nowup.db --report /app/persist/migration-report239.json
```

3. Só continuar se o comando terminar com sucesso e o relatório tiver `verified: true`. Uma interrupção ou divergência exige investigar; não ligar o aplicativo no destino incompleto.
4. Alterar `NOWUP_DB_ENGINE=postgres`, manter manutenção ativa e fazer deploy. Conferir os logs de inicialização e o status de backups. A origem SQLite permanece no disco.
5. Desativar manutenção e validar login de cliente e lojista, busca, produtos, personalização, pedido, repetição de envio, chat, relatório e notificações. Acompanhar erros e conexão do pool.
6. Conferir o primeiro backup nativo externo. Retomar divulgação somente após validar a operação.

**Retorno:** antes de aceitar alterações no PostgreSQL, é possível voltar para SQLite e desativar manutenção. Depois que houver novos pedidos ou alterações no PostgreSQL, não voltar simplesmente à cópia SQLite antiga: isso perderia essas alterações; precisa de reconciliação ou restauração planejada.

## Conferir/restaurar backup PostgreSQL

Os comandos de restauração não sobrescrevem banco ou pasta existentes. Usar uma URL de banco NOVO como segredo `DATABASE_URL` apenas nesse processo. Não apontar ao banco publicado.

```sh
python restore_backup.py arquivo.zip.enc --output /tmp/recuperacao-nowup
python restore_postgres239.py --staged /tmp/recuperacao-nowup --confirm-empty-target
```

O primeiro comando pede a chave de criptografia de forma oculta caso não esteja no ambiente. O segundo restaura o dump e compara as contagens; as fotos ficam na pasta conferida e precisam ser disponibilizadas no armazenamento antes de usar o ambiente recuperado.

## Limites e validação

Testes locais usam o motor PostgreSQL incorporado PGlite para compatibilidade, migração e fluxos sequenciais. Isso não comprova concorrência nativa nem desempenho do Render. O workflow usa PostgreSQL 18 completo para conferir concorrência e as ferramentas nativas. Nenhum resultado valida automaticamente 1.000 usuários simultâneos; medir novamente em homologação com plano e carga equivalentes à produção.

Documentação oficial de conexão e região: https://render.com/docs/postgresql-creating-connecting
