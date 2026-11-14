# V424 — Caixa compatível com a versão de produção

Base de produção: `8219e318eb386d27f8353f004fb1bc19213932ff`, branch `codex/categorias-icones-v230`. O PR #96 foi preparado sobre uma base antiga e não deve ser publicado. Esta implementação preserva PostgreSQL, Pix manual V422, mensagens WhatsApp V421, estoque de moda V391, checkout V411 e edição de produtos V423.

## Alterações

- `/painel/caixa`: abertura com saldo inicial, uma sessão aberta por loja, sangrias, suprimentos, pagamentos por forma, devoluções vinculadas ao recebimento, conferência e fechamento.
- Cada venda concluída entra uma vez; canceladas e recusadas ficam fora das vendas. Pagamentos manuais de comandas abertas entram nos recebimentos, mas essas pendências impedem o fechamento. Dinheiro esperado soma apenas dinheiro, saldo inicial e movimentos, descontando devoluções. Pix/cartão não aumentam a gaveta.
- Fechamento gera fotografia persistida de valores, origens e movimentos. Vendas manuais incluídas em fechamento ficam protegidas inclusive contra cancelamento posterior; uma devolução é registrada em nova sessão, sem editar o fechamento. Devolução financeira não repõe estoque automaticamente.
- Não importa receita histórica anterior à abertura. Um pedido antigo entregue durante a sessão é reconhecido pela conclusão. Pode haver mais de um turno por dia, mas apenas uma sessão simultaneamente aberta. Horários exibidos em Brasília.
- Edição de modalidade, endereço ou bairro recalcula o frete no servidor e propõe revisão ao cliente antes do aceite. Só após aprovação altera total e modalidade. Retirada aprovada remove frete. Uma edição sem mudança de entrega preserva o frete contratado.
- Pedido com total zero é rejeitado nos dois canais. Revisões também não podem produzir total zero. Pagamento “combinar” precisa ser definido antes de concluir, inclusive no ADM.
- Preserva a conferência de Pix no banco antes do preparo e os fluxos já publicados de WhatsApp e estoque. Não cria um segundo sistema de estoque.

## Migração e backup

Cria quatro tabelas (`cash_sessions424`, `cash_moves424`, `cash_sources424`, `cash_refunds424`) e seus índices. Acrescenta `delivery_json424` às revisões. Não remove tabelas, produtos, pedidos ou dados existentes. Usa o adaptador PostgreSQL já existente, sem gatilhos exclusivos de SQLite.

Na primeira ativação do caixa, quando o armazenamento externo está configurado, executa o backup criptografado existente e confirma o upload antes de criar as tabelas financeiras. Falha de backup interrompe essa ativação. Logs anteriores da produção confirmaram PostgreSQL, fotos sem ausência e backup automático concluído. Nenhuma credencial é incluída no código ou neste relatório.

## Verificação

- Testes financeiros: saldo inicial, soma por método, repetição de abertura/movimentos, fechamento duplicado, cancelamento, pedido zero, proteção de venda manual após fechamento, isolamento por loja, abertura concorrente, devolução sem alterar o snapshot e frete aprovado pelo cliente.
- Migração passa pelo tradutor PostgreSQL real do projeto. Workflow `cash424.yml` usa PostgreSQL 18 descartável e testa 20 aberturas concorrentes, movimentos idempotentes e fechamento. O teste recusa DSNs não locais e nunca usa o banco de produção.
- Carga local acelerada: 500 pedidos, 100 clientes fictícios respeitando o limite de cinco pedidos, 50 workers; reenvios idempotentes; 400 concluídos e 100 cancelados. Associação dos clientes, itens, IDs e caixa conferidos: R$ 1.200,00, sem divergência. Uma execução levou 18,59 segundos; p95 de criação 2,087 segundos. Não é um teste de duas horas no Render.
- 102 testes JavaScript passaram. A rodada direcionada de servidor teve 96 testes aprovados; a rodada final específica de caixa/Pix teve 38 aprovados, antes dos últimos ajustes apenas de exibição de recebimentos e teste de método de pagamento.
- A primeira rodada ampla encontrou 12 falhas. Onze foram reproduzidas no commit de produção sem esta alteração, por expectativas anteriores à V422/Pix imediato e oferta atual. A outra era falta local de jsdom, resolvida. Os testes legados foram alinhados às regras já publicadas, mantendo verificações de rejeição de preços adulterados, Pix não conferido, canais e isolamento. Nenhuma regra de mensalidade foi alterada. A rodada ampla seguinte aprovou 593 testes e apontou duas expectativas restantes de texto/estado Pix; ambas foram corrigidas nos testes e passaram em nova execução. A publicação deve aguardar as verificações do PR, incluindo o PostgreSQL real descartável.

A verificação visual em Android/iPhone e um ensaio de 120 minutos no Render não foram executados. Os testes HTTP e de banco descartável não substituem essas validações. Não foram enviados WhatsApps nem criados pedidos de teste em produção.

## Operação

Abrir o caixa antes do turno, informar o dinheiro inicial e concluir/cancelar pedidos e comandas antes de fechar. Devoluções exigem motivo e referência ao pedido ou recebimento original. Não apagar a migração nem restaurar um backup antigo sobre vendas novas para reverter código; manter os registros financeiros e corrigir de forma compatível.
