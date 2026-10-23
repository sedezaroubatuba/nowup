# NowUp Brasil — V228 P0/P1

Preparado em 23/10/2026 sobre o código publicado fb5571536d4e84617756f702883428ad8f286cd3 (conteúdo local equivalente 5b0b80d, exceto arquivos antigos sem referência). Não publicado em produção nesta entrega.

## O que mudou

- Registro único de sessões em `adm227_access`, com migração aditiva dos campos antigos. Logout revoga, elimina a sessão original e limpa cookies. O frontend limpa armazenamento de autenticação e redireciona para `/entrar?logout=ok`. APIs negam sessão revogada com 401; páginas protegidas existentes continuam usando o mesmo leitor de sessão.
- Inicialização exige `NOWUP_ADMIN_SECRET` e `NOWUP_JWT_SECRET` distintos e com pelo menos 32 caracteres. Senhas de administradores existentes não são redefinidas na inicialização. Sessões continuam opacas; o segundo segredo assina links temporários, não cria um JWT de autenticação no navegador.
- `/admin/super/api/state` carrega configuração e cadastro de lojas, sem histórico de pedidos, clientes ou produtos. Esses três diretórios são paginados, com limite máximo de 50. Os valores monetários são centavos.
- `/admin/super/api/metrics?from=2026-10-22&to=2026-10-22&city=&store=` soma apenas pedidos `completed`; cache privado em memória de 30 segundos. `/analytics/hourly` agrupa horas no SQL, em Brasília. O painel usa esses endpoints e preserva o Kanban.
- Turnos usam intervalos semiabertos. Para 18h–02h: `hour_from=18&hour_to=2`. O intervalo inclui 01:59 do dia seguinte e exclui 02:00 e 02:59. Sem filtro de turno, 02:59 pertence ao dia civil correto. O bairro é o gravado no pedido (`delivery_neighborhood`), não o bairro atual da loja.
- WAL, timeout de escrita de 5 segundos e índices de pedidos, itens e visitas. Visitas são registradas em tarefa de resposta, fora do carregamento da vitrine e do checkout. Essa tarefa é best effort; cobrança usa fila durável, não BackgroundTasks.
- Checkout exige `X-Idempotency-Key`. O navegador gera e preserva a chave por conteúdo, envia com fetch e reutiliza em retry. A transação `BEGIN IMMEDIATE` salva pedido e chave juntos. Mesmo envio retorna mesmo pedido; dados diferentes com a mesma chave retornam 409. Preços continuam calculados no servidor. Carrinho tem persistência local e sincronização autenticada; uma versão temporal reduz gravações antigas após finalização.
- Marketing sem permissão de pedidos/clientes não recebe seus arrays e não acessa os endpoints. Permissões `:read` não autorizam revisão de KYC nem mutações financeiras.
- Tokens CSS compartilhados, foco visível, botões de 44px, grades de categorias com duas colunas no celular e quatro no desktop. O CSS foi alterado; a revisão visual integral em navegador ainda está pendente. Arquivos históricos de estilos não foram convertidos cegamente: a contagem de 923 cores não foi tratada como 923 defeitos.

## Cobrança e KYC

Asaas é acessado apenas no servidor. Ao aprovar uma loja nova, o sistema valida documento e plano/preço e grava um job. Para lojas já aprovadas, existe ação `Preparar cobrança Asaas` no painel de documentos, ou POST `/admin/super/api/billing/{store}/provision` com justificativa. O worker cria cliente e assinatura, usando referências externas e recuperando IDs existentes antes de criar. HTTP externo ocorre fora da transação de escrita do SQLite. Nenhum retorno de fila significa pagamento confirmado.

O webhook `/webhooks/asaas` exige `asaas-access-token` e deduplica pelo ID do evento. Pagamentos possuem ledger por ID de cobrança, sem somar duas vezes eventos repetidos. Eventos atrasados de vencimento não desfazem o recebimento da mesma cobrança. O código trata RECEIVED, CONFIRMED, OVERDUE, REFUNDED e DELETED; cancelamento aceita o nome solicitado `SUBSCRIPTION_CANCELED` e os eventos oficiais `SUBSCRIPTION_DELETED`/`SUBSCRIPTION_INACTIVATED`.

D0 é o vencimento; D+1 a D+3 têm carência; bloqueio em D+4. Loja que já pagou mantém acesso na carência se KYC estiver aprovado; loja que nunca pagou permanece indisponível. Bloqueio manual de moderação é separado e não é removido por pagamento. Novos pedidos e vitrine são bloqueados no servidor com 403, preservando histórico e suporte. Conciliação diária consulta assinaturas e todas as páginas de cobranças. Worker executa a cada minuto, com lock de processo e leases de job; não depende de o painel estar aberto.

KYC valida dígitos de CPF/CNPJ numérico, rejeitando sequências repetidas. Não verifica identidade nem situação cadastral na Receita. Upload máximo de 5 MB (PDF/PNG/JPG), privado, com conteúdo e identificador criptografados via AES-GCM. Downloads usam URL assinada de 10 minutos. A revisão requer documentos pessoal e do negócio, justificativa e permissão de escrita. Mudanças ficam em `billing_audit`. Os documentos privados também entram no backup. Conservar o segredo de criptografia com os backups: trocar `NOWUP_ADMIN_SECRET` sem migrar os documentos impede sua leitura.

## Antes de implantar

**A migração não presume que lojas antigas estejam pagas ou verificadas.** Elas entram com KYC e assinatura pendentes; portanto podem ficar indisponíveis até revisão e conciliação. Preparar primeiro em homologação, validar os cadastros/contratos reais e definir a transição antes de aplicar ao banco de produção. Não falsificar aprovação ou pagamento para contornar esse requisito.

Configurar no Render, sem colocar segredos no código ou no chat:

| Variável | Uso |
| --- | --- |
| `NOWUP_ADMIN_SECRET` | Segredo aleatório estável para criptografia privada; mínimo 32 caracteres |
| `NOWUP_JWT_SECRET` | Outro segredo aleatório para links assinados; mínimo 32 caracteres |
| `ASAAS_API_KEY` | Chave da conta correta no Asaas |
| `ASAAS_WEBHOOK_TOKEN` | Token próprio de webhook, mínimo 32 caracteres; diferente da API key |
| `ASAAS_API_BASE` | Homologação: `https://api-sandbox.asaas.com/v3`; produção: `https://api.asaas.com/v3` |
| `NOWUP_BILLING_WORKER` | Manter `0` durante revisão; ativar `1` após configurar Asaas/webhook |
| `NOWUP_KYC_DIR` | Diretório privado em disco persistente, por exemplo `/app/persist/kyc-private` |

O blueprint gera os dois segredos em instalações novas. Serviços existentes configurados manualmente precisam recebê-los antes do deploy; sem eles a inicialização falha de propósito. Manter os caminhos atuais de banco e uploads no disco persistente. Não copiar bancos de testes, diretórios audit_work, node_modules ou credenciais. Fazer backup completo antes de migrar. Para cron externo com o mesmo banco, executar `python3 scripts/billing228_once.py` a cada minuto; não usar outro disco/container sem acesso ao mesmo SQLite persistente.

## Testes e build

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install pytest httpx
python3 -m pytest -q
npm --prefix frontend-admin ci
npm --prefix frontend-admin test
npm --prefix frontend-admin run build
python3 scripts/benchmark228.py
```

A suíte usa bancos temporários e API Asaas simulada. Resultado: 31 testes Python e 3 JavaScript passaram, além da compilação Vite. Inclui 4 testes Kanban e 10 da central anterior; não se deve limitar a suíte a 14 só para reproduzir a contagem antiga.

O bundle compilado já está em `static/adm227`. Ao alterar o fonte, reconstruir e copiar `frontend-admin/dist/` inteiro para `static/adm227/` antes de publicar.

Benchmark local descartável, 500 lojas e 30.000 pedidos: métrica sem cache ~28 ms, resposta 93 bytes; 10 consultas concorrentes retornaram 200 e p95 por nearest rank ~107 ms. O estado não enviou pedidos e a página de pedidos trouxe 50 de 30.000. O JSON original do benchmark está no pacote. Esses resultados medem leitura HTTP no TestClient local, não produção, nem escrita sustentada de 10.000 pedidos/dia.

## Homologação ainda necessária

1. No Asaas sandbox, aprovar uma loja, verificar um único cliente e assinatura, pagar e conferir reativação. Repetir webhook, simular vencimento e conciliar. Alteração de preço de assinatura existente exige fluxo de contrato conciliado e é recusada, em vez de simular atualização de cobrança.
2. Revisar visualmente home, loja, checkout e painéis em 375, 768 e 1440px; verificar foco, menus, categorias, banner e carrinho. Não foi executado Lighthouse nem teste visual completo nesta entrega.
3. Medir carga com infraestrutura real, concorrência de escrita, conexões móveis, volume acumulado de meses, rotina de backup e restore em ambiente separado. SQLite tem um escritor; o benchmark não constitui garantia de escala.
4. Campanhas externas, temas agendados, verificação externa de identidade e suporte a CNPJ alfanumérico não fazem parte desta implementação. A validação aqui é numérica conforme o escopo solicitado.
