# Status do Cardápio por WhatsApp — envio manual

Implementação restrita à central `/painel/cardapio/pedidos` e à notinha aberta por essa central. Não envia mensagens por servidor, não usa Meta/Cloud API/BSP, não agenda mensagens e não cobra por mensagem. O fluxo anterior em que o cliente envia o pedido pelo wa.me permanece intacto.

## Etapas

| Banco | Texto na central / mensagem |
|---|---|
| new | Recebido |
| confirmed | Pedido confirmado |
| preparing | Em preparo |
| out_for_delivery | Saiu para entrega |
| completed | Entregue |
| cancelled | Cancelado |

Uma recusa (`rejected`) pode compartilhar o texto de Cancelado. Pedidos antigos em `ready` mantêm a ação de avançar para entrega ou conclusão. Na central do Cardápio, Em preparo avança diretamente para entrega (ou conclusão de retirada). A Vitrine mantém sua sequência anterior. As regras existentes de autorização, aprovação do cliente, estoque e encerramento continuam no endpoint original de status.

## Configurações por loja

`Configurações da Loja → Mensagens WhatsApp`, também acessível pela central. GET/POST `/painel/cardapio/mensagens-whatsapp` exigem proprietário autenticado e resolvem a loja pela conta da sessão; não aceitam um ID de loja enviado pelo navegador.

Cada uma das seis mensagens aceita `{{nome_cliente}}`, `{{numero_pedido}}` e `{{nome_loja}}`. O lojista pode editar, restaurar individualmente, restaurar todos os padrões e ligar/desligar o botão. Limite de 1.500 caracteres por texto, exigido também no servidor. Dados de cliente são escapados no HTML; substituições na mensagem são feitas uma única vez.

Migração idempotente: tabela `whatsapp_status_settings421`, com uma linha por `professional_id`. `templates_json` guarda os textos e `enabled` guarda a opção da loja. Não altera pedidos. Migração executada por `init_db` e startup; SQL PostgreSQL em `migrations/421_whatsapp_status.sql`. Lojas sem configuração usam os textos padrão.

## Botão e confirmação visual

Em cada status suportado, o card e a notinha da central oferecem **Enviar status no WhatsApp**. O link usa `https://wa.me/` com dígitos, DDI 55 e DDD, seguido de `?text=` + `encodeURIComponent(mensagem)`. Telefones vazios ou inválidos ocultam o botão e mostram **Cliente sem WhatsApp**. Um número nacional de DDD 55 recebe corretamente mais um 55 de país.

O link abre em nova aba (`target="_blank"`, `rel="noopener noreferrer"`). Nenhum evento de atualização de status abre o WhatsApp automaticamente. Após o clique aparece **Enviado às HH:MM · confirme o envio no WhatsApp.** É somente indicação visual de abertura: não comprova envio, entrega ou leitura. Não é gravada como confirmação no banco e não bloqueia novo clique. O horário permanece durante a atualização automática da tela para o mesmo pedido/status e é separado por etapa.

## Validação realizada em ambiente isolado

- 16 testes Python: migração repetida, seis padrões, configurações por loja, restaurar, ligar/desligar, limites, autenticação, HTML seguro, alteração de status e isolamento de canais; regressões de central, aprovação, Pix e notinha.
- 11 testes JavaScript/JSDOM: telefone, substituição e encoding, clique manual em link de nova aba, horário visual, reenvio, troca de etapa, atualização automática, botão desligado/sem número; regressões de aceite sem navegação e alarmes.
- Teste de clique simulado com cliente `João & Ana`, pedido `NU #42`, loja `Sede Zero + Adega`: URL decodificada corresponde exatamente à mensagem. Nenhuma mensagem real foi enviada.

## Teste manual no aparelho

1. Entrar como lojista, abrir Configurações da Loja → Mensagens WhatsApp e conferir os seis textos, incluindo Pedido confirmado.
2. Editar Pedido confirmado, manter o botão ligado e salvar. Abrir Pedidos do WhatsApp/Cardápio.
3. Em um pedido de teste, tocar Aceitar pedido. Verificar Pedido confirmado e o botão de WhatsApp no card/notinha. A tela não deve abrir WhatsApp sozinha.
4. Tocar Enviar status no WhatsApp. Verificar nova aba, destino `55 + DDD + telefone`, cliente, número e loja corretos e caracteres especiais preservados. O texto deve estar pronto para envio; só tocar Enviar no WhatsApp se desejar enviá-lo de fato.
5. Voltar: conferir horário visual e tocar de novo, validando reenvio. Esperar a atualização automática e conferir que a indicação permanece.
6. Avançar para Em preparo, Saiu para entrega e Entregue. Em outro pedido, cancelar com motivo. Conferir mensagem correspondente a cada etapa.
7. Testar pedido sem telefone: Cliente sem WhatsApp. Desligar a opção da loja e recarregar a central: nenhum botão de envio disponível. Restaurar os padrões e reativar.
8. Conferir outra loja e a fila da Vitrine: textos da primeira loja e controles novos não devem aparecer ali.

O teste automatizado simula o clique e valida a URL; a abertura do aplicativo WhatsApp e o envio final precisam ser conferidos no aparelho do lojista.

## Arquivos

- `app.py`: instalação e migração no init_db.
- `nowup_whatsapp_status421.py`: padrões, migração e configuração autenticada por loja.
- `nowup_channels408.py`: configuração da loja e rótulos/progressão apenas na central.
- `static/whatsapp-status421.js` e `.css`: links manuais, encoding, indicação visual e botão móvel.
- `templates/whatsapp_status421.html`: editor da loja.
- `templates/whatsapp_status_button421.html`: botão reutilizado somente no Cardápio.
- `templates/menu_orders408.html`, `menu_orders_fragment408.html`, `merchant_order407.html`: integração na central e notinha.
- `templates/pro_panel.html`: entrada em Configurações da Loja.
- `migrations/421_whatsapp_status.sql`, `tests/test_whatsapp_status421.py`, `tests/whatsapp-status421.test.cjs` e este documento.
