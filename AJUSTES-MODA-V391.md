# NowUp Brasil - Moda V391

Implementação sobre o código existente (FastAPI, JavaScript e PostgreSQL), sem migração de framework. Escopo visual exclusivo das lojas com `business_type=fashion`.

## Comportamento entregue

- Cards compactos em duas colunas verticais intercaladas, sem carrossel de produtos. Primeira peça em destaque.
- Pesquisa e categorias fixas no topo. Categorias deslizam horizontalmente; selecionar uma mostra somente suas peças.
- Pesquisa, categoria e vitrine reutilizam os mesmos nós de card: sem descrição ou personalização expandida na busca.
- Depois de adicionar, o card mantém quantidade, +, -, borda verde e botão Remover. Alterações não exigem abrir o carrinho.
- Reserva no servidor por 10 minutos, com carrinho bloqueado para envio enquanto aguarda validação. A expiração é aplicada pelo servidor mesmo com navegador fechado; a disponibilidade visual é consultada a cada 15 segundos.
- Confirmação dá baixa uma vez; cancelamento/rejeição libera reservas ou repõe a baixa uma vez. Alterações de quantidade na revisão passam pela mesma conferência transacional antes da confirmação.
- Reservas expiradas deixam de consumir saldo. Se um lojista confirmar depois disso, o servidor confere e readquire saldo disponível na mesma transação; se outro cliente já o reservou, a confirmação é bloqueada.
- Reenvio do mesmo pedido continua idempotente. Anti-spam de pedidos e recálculo de preços permanecem ativos.

## Estoque legado e por variação

A opção **Quantidade por tamanho e cor** permite linhas como `M;Preto;5` e `M;Branco;2`. Combinações omitidas ficam com saldo zero. Para tamanho único ou ausência de cor, deixe o respectivo campo vazio (`;Preto;5` ou `M;;5`).

Saldos antigos por tamanho continuam compartilhados entre cores, e saldos totais continuam compartilhados entre todos os tamanhos/cores: não são multiplicados durante a migração. O lojista pode cadastrar os saldos reais por combinação para usar o novo modo. Produtos com **Não controlar estoque** continuam sem limite físico configurado; é necessário ativar o controle para proteger um saldo finito.

Não é permitido reduzir um saldo abaixo do que já está reservado nem trocar o controle enquanto houver reservas incompatíveis. Não são inventados saldos para peças existentes.

## Arquivos de aplicação

| Arquivo | Mudança |
|---|---|
| `nowup_inventory391.py` | Tabelas de saldo, reservas e variações do pedido; transações, bloqueio por loja e linhas `FOR UPDATE` no PostgreSQL; endpoints de reserva/disponibilidade; baixa e reposição idempotentes. |
| `nowup_fashion_stock389.py` | Validação do modo tamanho + cor e preservação dos modos legados. |
| `app.py` | Inicialização aditiva do esquema; cadastro/edição de estoque por variação; reserva no pedido interno; snapshot das escolhas; baixa/reposição nas transições do lojista. |
| `nowup_storeapp257.py` | Reserva atômica no checkout WhatsApp e snapshots de tamanho/cor, mantendo preço e fluxo existentes. Clientes antigos ainda conferem estoque atomicamente no checkout. |
| `nowup_review127.py` | Conferência e baixa de estoque na aprovação de revisões; liberação no cancelamento. |
| `nowup_admin227.py` | Aplica o mesmo controle às transições feitas pelo administrador. |
| `nowup_scheduling380.py` | Libera reservas nas expirações/cancelamentos automáticos de pedidos. |
| `static/fashion385.js` | Clique do card deixa os controles de quantidade funcionarem; botão Remover; editor de estoque por variação. |
| `static/fashion385.css` | Controles visíveis e verdes, grade vertical intercalada, cabeçalho fixo e categorias horizontais. |
| `static/fashion-layout391.js` | Uma única renderização compacta para vitrine, categoria e busca; cálculo das alturas do mosaico. |
| `static/fashion-stock391.js` | Sincronização do carrinho com reserva do servidor, tratamento de estoque esgotado/expirado e atualização de disponibilidade. |
| `static/menu88.js` | Operações de remoção/restauração do carrinho e espera da confirmação de reserva antes do envio. |
| `static/storefront187.js` | Encaminha somente moda ao layout novo; preserva a loja geral. |
| `templates/fashion385.html` | Campo de saldos tamanho/cor e explicação da reserva automática. |
| `templates/base.html` | Carrega os novos recursos somente para moda e atualiza versões de cache. |
| `templates/menu.html`, `templates/profile.html` | Atualiza a versão do JavaScript de carrinho. |

## Arquivos de testes e automação

| Arquivo | Mudança |
|---|---|
| `requirements-dev.txt`, `tests/test_pix.py` | Inclui o decodificador de QR Code na instalação de desenvolvimento e torna obrigatória a leitura do QR Pix no teste. |
| `conftest.py` | Ambiente descartável para a suíte; força SQLite de teste e retira DSN de produção durante pytest. |
| `tests/test_inventory391.py` | Disputa de 30 clientes por 10 peças, expiração, remoção, cores independentes, checkout, confirmação, cancelamento e reenvio. |
| `tools/check_inventory391_postgres.py` | Mesmas invariantes centrais com transações concorrentes em PostgreSQL real, em esquema aleatório descartável. |
| `.github/workflows/security308.yml` | Instala as dependências JavaScript para tornar obrigatória a verificação DOM do painel na suíte de servidor. |
| `.github/workflows/inventory391.yml` | Executa a validação de estoque com PostgreSQL 18 isolado. |
| `tests/fashion-layout391.test.cjs` | Confere filtro por categoria, busca e reutilização dos cards compactos. |
| `tests/merchant-settings.dom.cjs` | Nome novo do verificador de HTML recebido por stdin; evita que `npm test` fique esperando entrada. |
| `tests/test_merchant_settings.py` | Invoca esse verificador pelo novo nome e resolve jsdom instalado no projeto. |
| `tests/test_banners384.py` | Isola o dicionário de configuração de banners para não contaminar outras fixtures. |
| `tests/test_merchant228.py`, `tests/test_categories230.py` | Bancos e uploads por fixture; alinha CMS, autenticação e verificação ao mesmo banco descartável; desfaz configurações ao terminar. |
| `tests/test_checkout247.py` | Alinha os módulos auxiliares ao banco temporário de cada checkout. |
| `tests/test_audit255.py`, `tests/test_links352.py`, `tests/test_plans339.py`, `tests/test_push375.py`, `tests/test_revision348.py`, `tests/test_storeapp256.py`, `test_admin205.py` | Restaura configurações de módulos depois de cada teste, evitando autenticação e caminhos herdados. |
| `tests/test_storeaccounts345.py` | Restaura serviços e variáveis alterados pela fixture. |
| `tests/test_catalog_audit354.py`, `tests/test_combo_units364.py`, `tests/test_menu_origin355.py` | Atualiza expectativas para pedido enviado por link e aguardando revisão. Continua verificando valores e persistência dos detalhes. |
| `tests/test_fashion385.py` | Atualiza a versão esperada do recurso de moda. |

## Como testar manualmente

Faça os cenários de compra numa loja de teste. A demonstração pública permite explorar o visual, mas mantém o bloqueio de pedidos reais.

### 1. Quantidade e remoção

1. Abra uma loja de moda e toque em Vestido midi roxo.
2. Escolha tamanho M, cor Preto e quantidade 1; adicione.
3. Confira borda verde e quantidade 1 no próprio card.
4. Toque em + e depois em - no card. Confira a quantidade e o total do carrinho.
5. Toque em Remover. Confira o retorno do botão Adicionar e a liberação da reserva.

### 2. Reserva, baixa, cancelamento e esgotamento

1. No painel de uma loja de teste, cadastre M/Preto com 2 peças e M/Branco com 1, usando o controle por tamanho e cor.
2. Entre com o cliente A num navegador e reserve 2 M/Preto no carrinho.
3. Entre com o cliente B em outro navegador/aba anônima. M/Preto deve estar esgotado; M/Branco continua disponível.
4. Remova as peças do cliente A. Após atualizar a disponibilidade, B pode reservar M/Preto.
5. Reserve novamente e espere mais de 10 minutos sem alterar o carrinho. A reserva não deve bloquear outros clientes. O cliente original deve atualizar a reserva antes de enviar.
6. Envie um pedido de 1 M/Preto. Confira o link WhatsApp preparado e o acompanhamento; não é necessário mandar mensagem real para verificar a gravação.
7. Confirme como lojista. O saldo físico deve cair de 2 para 1, uma única vez.
8. Recarregue/reenvie a mesma confirmação. O saldo permanece 1.
9. Cancele com motivo. O saldo volta para 2, uma única vez.
10. Repita o teste com duas confirmações concorrentes e confira que um saldo reservado por outro cliente nunca é consumido.

### 3. Layout, pesquisa e categorias

1. Abra a loja de moda no celular e no computador.
2. Role para baixo: pesquisa e categorias devem continuar no topo; as peças seguem em duas colunas intercaladas.
3. Selecione Vestidos: devem aparecer somente vestidos, mantendo o mosaico.
4. Selecione Camisetas ou Tênis/Sapatos: devem aparecer somente os produtos da categoria correspondente.
5. Pesquise um nome dentro da categoria e volte a Todos. A descrição e os seletores não podem abrir dentro da listagem; toque no card para ver os detalhes.
6. Confira o cabeçalho e os controles depois de adicionar uma peça e depois de limpar a busca.

### 4. Regressão da loja geral

1. Abra uma loja geral de teste; confira o layout existente.
2. Adicione produtos, altere quantidades e confira preços, frete e total.
3. Envie um pedido e confira o link do WhatsApp e o acompanhamento.
4. Reenvie a mesma solicitação: deve continuar com um único pedido.
5. Tente seis pedidos novos do mesmo cliente na mesma loja em menos de cinco minutos: o sexto deve ser bloqueado pelo anti-spam.

## Validação automatizada

- Suíte conjunta: `PYTHONPATH=.:tests python -m pytest tests test_admin205.py -q`.
- JavaScript: `npm ci` e `npm test`.
- PostgreSQL: `NOWUP_TEST_PG_URL391=<DSN exclusivamente de teste> python tools/check_inventory391_postgres.py`.
- O verificador PostgreSQL cria e remove somente um esquema aleatório próprio. Nunca usar DSN de produção para esse comando.

O esquema novo é criado de forma aditiva na inicialização. Lojas gerais não são convertidas para estoque de moda. A reserva não inicia cobrança nem confirma pagamentos.
