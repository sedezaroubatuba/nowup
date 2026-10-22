# Painel do lojista V228

O painel em `/painel` passa a usar menu lateral roxo no computador e menu recolhível no celular. A entrada abre a sala de pedidos. Produtos, categorias, adicionais, horários, relatórios e histórico continuam nos fluxos existentes; ferramentas secundárias ficam em “Mais ferramentas”.

O quadro agrupa Novos, Em preparo (inclui Prontos), Em entrega e Encerrados. Todos os pedidos abertos, inclusive de dias anteriores, permanecem visíveis. Encerrados são os do dia atual. A busca filtra código ou nome do cliente. No celular, as abas mostram uma etapa por vez. O quadro consulta o servidor a cada dez segundos enquanto estiver visível; não substitui os formulários de edição de produtos ou a conversa aberta.

As ações de status utilizam as rotas existentes, com validação de loja, revisão, aprovação do cliente, motivo de cancelamento e proteção dos pedidos encerrados. Para ver itens, revisar, recusar, cancelar ou conversar, abra “Ver itens / conversar”. O controle original de som foi mantido; o navegador ainda exige interação para liberar o áudio.

## Publicação

Use o serviço principal do NowUp no Render, branch `main`, e publique o commit “Painel do lojista com menu roxo e Kanban responsivo V228”. Não são necessárias variáveis novas ou migração de banco. A versão continua usando o SQLite atual; PostgreSQL é uma etapa separada.

Após o status Live, entrar como lojista, verificar menu, produtos, configurações, pedidos e revisão. Testar o som no aparelho que receberá pedidos. Para reverter o visual, republicar o commit anterior no Render; a alteração não remove tabelas ou registros.

## Validação

Quatro testes de integração em banco isolado: isolamento por loja, pedidos de dias anteriores, totais, renderização e escape de dados, autenticação, aprovação e transições de status. Conferência em Chromium: menu, busca, atualização, envio de status e larguras 320, 390, 768, 1024 e 1440 px, sem erros de JavaScript ou transbordamento horizontal.

Executar: `python -m pytest -q tests/test_merchant228.py` (requer dependências do projeto e pytest/httpx no ambiente de testes).
