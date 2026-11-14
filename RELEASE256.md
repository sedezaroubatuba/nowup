# V256 — Caixa, pedidos, WhatsApp e estoque opcional

O caixa agora registra abertura, recebimentos por método, sangrias, suprimentos, devoluções e fechamento imutável. Pedidos cancelados não geram venda concluída. Cada origem entra uma vez, e pedidos ou comandas ativos da sessão bloqueiam seu fechamento.

Exemplo: R$ 100 iniciais, vendas de R$ 50 em dinheiro, R$ 80 Pix e R$ 120 em cartão, suprimento de R$ 20 e sangria de R$ 30 resultam em R$ 250 vendidos e R$ 140 de dinheiro esperado. Pix e cartão não aumentam a gaveta. Recebimentos de comandas ainda abertas aparecem separados do total de vendas concluídas.

## Comportamento

- Acesso do lojista a `/painel/caixa` e `/painel/estoque`, com autenticação e isolamento por loja.
- Uma sessão aberta por loja; é possível abrir outro turno no mesmo dia após fechar o anterior. Abertura e movimentos repetidos com o mesmo identificador não duplicam lançamentos.
- Pedido criado durante uma sessão é associado àquela sessão. Pedido sem sessão permanece fora dela e aparece como histórico a conciliar; não há importação automática de pedidos antigos.
- Venda concluída gera lançamento único. Pagamento “combinar” precisa ser informado antes de concluir. Nas vendas do NowUp, concluir é o ato operacional usado para reconhecer o recebimento informado; não há confirmação bancária automática de Pix.
- Pagamentos das comandas manuais são lançados ao registrar; correções e cancelamentos com devolução geram contrapartidas. Contas abertas impedem fechar a sessão.
- Fechamento conserva valores, origens e lançamentos em fotografia imutável. Uma devolução posterior é vinculada ao recebimento original e lançada em uma sessão aberta. Não modifica o fechamento anterior nem repõe automaticamente mercadoria de venda já entregue.
- Edição de entrega/retirada e bairro usa cotação do servidor e proposta para aprovação do cliente antes do aceite. Depois de iniciado o fluxo de atendimento, mudança financeira de entrega é bloqueada. Retirada aprovada zera frete e limpa endereço.
- Total final zero é rejeitado. Brindes podem compor venda com total positivo.
- Transições explícitas no servidor e também no banco impedem saltos de status por outras rotas. Retirada conclui após “pronto”; entrega exige “saiu para entrega”.
- “Enviar status no WhatsApp” abre `wa.me` com telefone normalizado do cliente e mensagem com loja, código, status, itens, adicionais, totais e endereço. O lojista ainda precisa tocar em enviar no WhatsApp. Não há confirmação de entrega/leitura nem disparo automático.
- Estoque quantitativo é opcional. Produtos existentes continuam sem controle. Ativá-lo reserva unidades no checkout, libera uma vez no cancelamento e não dá nova baixa na conclusão. Revisões e vendas manuais usam as mesmas reservas atômicas.
- A edição de estoque exige finalizar os pedidos ativos do produto; valores são unidades disponíveis após reservas. Combos com componentes configurados ficam fora desse controle por unidades. Não foi implementado estoque por peso ou baixa de ingredientes/adicionais.
- Histórico de pedidos informa que usa a data de criação. Vendas consolidadas existentes usam conclusão; caixa usa sessões que podem atravessar meia-noite, com horários de Brasília.

## Migração

`nowup_finance256.initialize` é uma migração aditiva e idempotente executada no startup, depois das tabelas de vendas manuais. Adiciona tabelas, colunas, índices e gatilhos SQLite. `nowup_review127.initialize` adiciona os dados de entrega da proposta de revisão.

Não troca infraestrutura, não apaga histórico, não preenche estoque dos produtos existentes e não altera cobrança recorrente. O repositório consultado usa SQLite; confirmar a versão e o mecanismo de banco do serviço publicado antes do merge/deploy. Esta mudança não foi validada para um fork que use PostgreSQL.

## Validação executada

- Suíte Python completa: 105 testes passaram (`tests` e `test_admin205.py`).
- Após o último ajuste de verificação de recebimento original, os 17 testes de `tests/test_finance256.py` passaram novamente.
- JavaScript do carrinho: 5 testes passaram.
- JavaScript do ADM: 5 testes passaram.
- Compilação dos arquivos Python modificados e conferência de whitespace passaram.
- Inicialização completa em banco descartável, sessão real de lojista, `/health`, `/painel`, `/painel/caixa`, `/painel/estoque` e abertura do primeiro caixa: respostas esperadas.
- Todos os testes usaram SQLite descartável e clientes fictícios. Sem envio de mensagens a clientes reais e sem acesso ao banco da Sede Zero.

### Carga local acelerada

Foram criados 500 pedidos lógicos, com 50 workers concorrentes, 50 identidades fictícias e reenvios idempotentes adicionais. Foram concluídos 400 e cancelados 100. Foram conferidos IDs únicos, associação aos clientes, total de itens, métodos de pagamento e fechamento. Total concluído: R$ 1.200,00; sem divergência de centavos.

Uma execução local observada levou 11,53 segundos para criação, status e conciliação. Tempos em segundos, dependentes deste ambiente:

| Operação | p50 | p95 | p99 | Máximo |
| --- | ---: | ---: | ---: | ---: |
| Criação | 0,0363 | 1,6717 | 2,4470 | 3,0969 |
| Status | 0,0176 | 1,2391 | 2,6421 | 5,2489 |

Isso não mede a capacidade do Render e não substitui teste contínuo de 120 minutos. Não foram medidos navegador móvel real, tempo de visibilidade no painel sob rede real nem velocidade de abertura do WhatsApp. A prévia local respondeu HTTP, mas o navegador remoto não conseguiu alcançar o servidor local (`ERR_CONNECTION_REFUSED`); verificação visual e Safari/iPhone permanecem pendentes.

## Antes da publicação

1. Confirmar a área de trabalho e o serviço Render com o usuário; comparar commit publicado, branch de deploy e SQLite efetivo com a base desta alteração.
2. Confirmar backup recuperável e validar a migração em cópia do banco existente. As migrações são aditivas, mas testes em bancos descartáveis não substituem validação dos dados reais de uma versão diferente.
3. Revisar o PR e executar verificação visual em staging, incluindo Android/iPhone, movimento de caixa, aprovação de frete e abertura manual de WhatsApp.
4. Publicar pelo serviço existente e acompanhar o deploy específico e `/health`. Não criar outro serviço nem modificar plano/domínio como parte desta correção.
5. Em problema após movimentações financeiras, preservar o banco e os lançamentos. Não restaurar um backup antigo ou remover os gatilhos para forçar operações. Preparar correção compatível antes de voltar código; rollback de código sem considerar a migração não é procedimento suficiente.

## Estado

Implementado e validado localmente em branch separada. Produção não alterada. Mensalidades/cobrança recorrente fora do escopo.
