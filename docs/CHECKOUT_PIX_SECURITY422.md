# Checkout e Pix estático — revisão de segurança 422

## Escopo e achados

O checkout já consultava produtos da loja e calculava preços, promoções, adicionais, combos, peso e frete no backend. Entretanto, campos financeiros extras eram silenciosamente ignorados. Foram adicionadas listas de campos permitidos, rejeição explícita de valores enviados pelo cliente, validação de loja declarada e limites de estrutura/total. A mudança não transforma preços exibidos no navegador em valores confiáveis.

A chave já vinha do banco e o QR era gerado no backend por `qrcode`, sem serviço externo de QR. A chave não foi movida para JavaScript nem para uma configuração global: cada loja continua com seus dados no banco. O campo redundante `key` foi removido do objeto Pix entregue à interface e a chave avulsa deixou de ser impressa na tela de pagamento. **A chave permanece necessariamente legível dentro do próprio BR Code / Copia e Cola. Ela não é uma senha.**

Antes, aceitar o pedido permitia avançar para preparo sem verificar o recebimento. Agora todos os caminhos ativos de avanço (lojista, revisão e administrador) passam pela verificação compartilhada de Pix antes de preparar, marcar pronto, enviar ou concluir.

## Contrato de entrada

- O cliente informa IDs dos produtos, quantidades e escolhas: adicionais por ID/quantidade, composição dos combos, tamanho/cor, ingredientes retirados, peso em gramas, observações e talheres.
- Nome/telefone, endereço/bairro/referência, entrega/retirada, forma de pagamento, troco e agendamento continuam disponíveis. O troco é a cédula informada pelo cliente, não um desconto ou preço.
- A rota identifica a loja pelo cardápio. Se `store_id` ou `professional_id` forem enviados, devem corresponder à loja resolvida pelo servidor. Produtos são consultados com o ID dessa mesma loja.
- Preço, subtotal, total, frete, desconto, chave/payload Pix e confirmação de pagamento vindos do cliente são rejeitados. A rejeição também inspeciona as escolhas aninhadas; o ID do adicional continua sendo usado para obter o preço no banco.
- Campos duplicados no formulário são rejeitados. O carrinho aceita de 1 a 50 linhas, até 256 KiB, com profundidade de escolhas limitada. Os validadores existentes continuam verificando quantidades, disponibilidade, variações e estoque.
- Valores finais são inteiros em centavos, não negativos e com limites compatíveis com o payload Pix. O servidor verifica `total = subtotal + frete` antes de gravar.

A reserva de estoque da loja de roupas foi ajustada para enviar somente ID/quantidade dos adicionais, em vez de encaminhar seus objetos de exibição com preço.

## Estado inicial e recebimento

1. Pedido Pix novo: `orders.status = awaiting_payment`, histórico com a mesma etapa e rótulo **Aguardando Confirmação de Pagamento**.
2. QR Code disponível no acompanhamento autenticado, gerado com o total e a chave consultados no servidor. Chave ausente/inválida não produz QR e a tela orienta falar com a loja.
3. Aceitar itens não marca o Pix como pago. Nenhum comprovante ou campo do navegador marca recebimento.
4. Apenas o lojista autenticado da própria loja pode chamar a confirmação manual de crédito. A conferência grava o total atual, o usuário e o horário em `order_payment_checks401`.
5. Se o Pix for conferido antes do aceite dos itens, o pedido passa de `awaiting_payment` para `new` (aguardando aceite). A interface já mostra o Pix confirmado. Essa conferência não vende estoque nem inicia preparo automaticamente.
6. Após aceite e conferência, o lojista pode avançar. Tentativas de avançar Pix sem conferência, inclusive por POST direto ou pela administração, recebem HTTP 409.
7. Se o total for alterado, a conferência de um valor anterior deixa de liberar o avanço. É necessário conferir o valor atual.
8. Dinheiro/cartão/on_delivery mantêm o fluxo anterior. Cancelamentos e devoluções continuam manuais; não há integração bancária ou confirmação automática.

A atualização automática e as notificações reconhecem a nova etapa. Cardápio e Vitrine continuam separados. O envio de mensagens via wa.me permanece manual.

## Aviso obrigatório

Imediatamente acima do QR Code, em destaque:

> Atenção: antes de confirmar o pagamento no seu banco, confira se o destinatário é o estabelecimento escolhido

## Banco e implantação

Não é necessária alteração de esquema: `orders.status` já é texto e a tabela de conferência já existe. O inicializador do banco garante idempotentemente a tabela de conferência em instalações novas. Não há backfill de estados históricos, alteração de chaves, preços ou conversão de bancos. A implementação mantém o adaptador PostgreSQL existente; uma falha na conexão não provoca migração silenciosa para outro banco.

## Validação

Os testes usam banco **SQLite isolado**, pelo mesmo contrato de acesso do projeto; não enviam dinheiro nem criam pedidos reais de produção. Os cenários cobrem rejeição de preço/total/frete/desconto/chave, preços atualizados, loja inválida, valores e payload do servidor, estado inicial nos dois canais, confirmação por proprietário, bloqueio de avanço, alteração de total, comprovante sem poder de confirmação, cálculo por peso, combos, adicionais, estoque, idempotência, QR decodificado e separação de canais.

A interface é validada por JSDOM, incluindo a posição e o texto do aviso, links manuais de status, aceite e atualização sem navegação completa. Não é um pentest completo do sistema, uma validação de configuração da infraestrutura PostgreSQL, nem uma confirmação do aplicativo bancário em um aparelho real.

### Conferência manual no aparelho

1. Fazer um pedido Pix de teste em cada canal. Conferir `Aguardando Confirmação de Pagamento`, valor calculado pelo servidor, aviso acima do QR e destinatário correto no banco. Não é necessário concluir a transferência para testar a tela.
2. Como cliente, tentar confirmar recebimento pela rota do lojista: deve ser proibido. Anexar comprovante não deve liberar preparo.
3. Como lojista, aceitar itens e tentar iniciar preparo sem conferir Pix: deve ser bloqueado. Não marcar recebimento em pedido real sem conferir o banco.
4. Em pedido de teste, conferir manualmente o recebimento e verificar aviso verde para o cliente. O preparo continua exigindo ação explícita e aceite dos itens.
5. Alterar o total por revisão autorizada: conferir que o recebimento anterior não libera o novo total.
6. Testar dinheiro/cartão, adicionais, combos e peso; verificar que não aparece QR em métodos não Pix.
7. Verificar pedidos da Vitrine e do Cardápio em suas próprias listas, além de atualização automática e notificações.

Resultado da rodada final: **181 testes Python passaram**, além de **12 testes JavaScript/JSDOM**, incluindo a decodificação real do QR Code de teste. As verificações de compilação e diferenças de arquivo também passaram.

## Arquivos da entrega

- `app.py`
- `docs/CHECKOUT_PIX_SECURITY422.md`
- `nowup_admin227.py`
- `nowup_channels408.py`
- `nowup_checkout_security422.py`
- `nowup_inventory391.py`
- `nowup_merchant228.py`
- `nowup_notinha401.py`
- `nowup_pix.py`
- `nowup_push75.py`
- `nowup_review127.py`
- `nowup_storeapp257.py`
- `static/fashion-stock391.js`
- `static/menu-orders408.js`
- `static/order-link377.js`
- `static/pix-payments.js`
- `templates/base.html`
- `templates/menu.html`
- `templates/menu_orders408.html`
- `templates/menu_orders_fragment408.html`
- `templates/merchant_order407.html`
- `templates/order_revision.html`
- `templates/order_tracking.html`
- `templates/pro_panel.html`
- `templates/profile.html`
- `templates/whatsapp_status_button421.html`
- `tests/pix-security422.test.cjs`
- `tests/test_checkout_security422.py`
- `tests/test_combo_units364.py`
- `tests/test_immediate_pix_isolation398.py`
- `tests/test_inventory391.py`
- `tests/test_payment_controls419.py`
- `tests/test_pix.py`
- `tests/test_storeapp257.py`
- `tests/test_weight370.py`
- `tests/test_whatsapp_central418.py`
- `tests/test_whatsapp_status421.py`
