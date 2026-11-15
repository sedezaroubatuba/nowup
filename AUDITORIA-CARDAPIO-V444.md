# Auditoria Cardápio e notinhas — 15/11/2026

Base: 15ca7448c402a5a2a7aea8cde3553223c2ccc123.

## Execução isolada

- SQLite temporário, usuários/produtos fictícios e FastAPI TestClient; nenhum pedido real, cobrança ou mensagem de WhatsApp enviado.
- 150 pedidos de Cardápio, 20 trabalhadores, Pix/dinheiro alternados; 150 consultas de acompanhamento e 150 notinhas.
- 15 reenvios idempotentes: mesmos números de pedido; 150 registros finais, sem duplicação.
- Soma reconciliada: R$ 900,00, calculada pelo servidor a partir dos produtos.
- 30 cadastros: 15 produtos e 15 adicionais pagos, sem foto obrigatória.
- Anti-spam: 5 pedidos aceitos e o sexto bloqueado com HTTP 429, sem gerar novo registro.
- Tempo da rajada mais cadastros: 5,19 s; p95 por pedido com acompanhamento/notinha: 1,793 s. Valores locais, não medem capacidade ou latência do Render/PostgreSQL.

## Validação

103 testes do servidor aprovados; excluído o teste antigo de 500 pedidos do caixa, pois a carga solicitada foi coberta pela rajada própria do Cardápio. 6 testes de interface aprovados. Após ajustes finais dos textos, 6 testes de notinhas/transferência novamente aprovados.

Cobertura: escopo por loja/usuário, preços do servidor, Pix após aceite no Cardápio, confirmação de recebimento, alteração de valores, combos/adicionais/observações, troco/entrega, impressão, contador, agendamento, caixa, cadastro e seleção em lote.

## Correções

1. Transferência ao WhatsApp agora bloqueia novas mensagens e comprovantes no NowUp, mantendo leitura do histórico. Revalidação sob transação/bloqueio de linha impede gravação concorrente após a transferência.
2. Interface da conversa fecha o envio ao receber a atualização de canal; a seleção do WhatsApp emite o evento imediatamente.
3. Notinha e status distinguem atendimento manual pelo WhatsApp de pedido encerrado ou ainda aguardando aceite.
4. Sete expectativas antigas de testes foram atualizadas: Cardápio inicia em `new`, Pix só após aceite, aviso ao lojista e componente atual de alertas.

## Limites

Não houve auditoria fiscal de NF-e/NFC-e, teste bancário real, impressão física nem carga no PostgreSQL de produção. Notinhas são resumos de pedidos, não documentos fiscais. Sem exclusão de dados ou limpeza do banco real. A navegação autenticada real depende da sessão do lojista; a validação do fluxo foi realizada por testes isolados.
