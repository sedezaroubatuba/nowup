# Correções verificadas — 23/10/2026

A aplicação inspecionada utiliza FastAPI/SQLite/Jinja e React/Vite no Super ADM. Afirmações dos prints sobre Next.js, Supabase/RLS ou Lighthouse 58 não foram demonstradas neste código. Não há nota técnica nova sem validação de cada etapa.

## Alterações
- Revogação de sessões compartilhada entre painel novo, legado e CMS; encerramento remove a sessão original.
- Startup preserva senha, papel e bloqueio do administrador existente; criação inicial exige email explícito e senha de 12 caracteres. Não troca automaticamente senhas antigas.
- Checkout grava chave de idempotência na mesma transação do pedido. Reenvios com a mesma chave retornam o mesmo pedido; chave reutilizada com dados diferentes retorna 409. Clientes antigos têm deduplicação por conteúdo por dois minutos.
- Marketing isolado deixa de receber pedidos, itens e valores individuais; recebe data agregada da última compra para segmentação.
- Snapshot elimina consultas por pedido/loja, preserva minutos locais e marca lojas bloqueadas ou contas desativadas como indisponíveis.
- Filtro 18h–02h inclui madrugada do dia operacional e exclui 02h em diante. Botões de alertas usam semântica e foco de botão.
- Falhas operacionais do SQLite retornam 503 com mensagem genérica. Detalhes ficam no log do servidor.
- Removidas duas rotas duplicadas que estavam encobertas por implementações já registradas, incluindo login com segundo fator.
- Fonte do painel restaurado em frontend-admin, build servido em static/adm227; atualização periódica de 15s em pedidos e 60s nas demais áreas, suspensa em aba oculta.

## Validação
17 testes Python passaram (Kanban, administração, revogação e checkout), mais teste JavaScript do turno noturno e build Vite. Verificação HTTP isolada: sessão revogada 401 nos dois painéis, reenvio retorna o mesmo tracking e um único pedido de R$30 apesar de preço adulterado no cliente. Simulação de banco indisponível retorna 503.
Benchmark sintético local: 500 lojas/30.000 pedidos, 30 consultas no snapshot, cerca de 9,3 MB de JSON. Tempo de aproximadamente 0,28s somente para montar snapshot no ambiente local; não mede rede, renderização ou concorrência.

## Pendências
Histórico completo ainda é enviado ao painel. Exige endpoints paginados e agregações de métricas no servidor antes de afirmar escala de 10.000 pedidos/dia. Integrações Asaas/campanhas, KYC externo e recursos marcados unsupported não foram implementados nesta correção. Não houve Lighthouse ou revisão visual em 375/768/1440px. Senhas antigas precisam ser revisadas pelo administrador.

## Implantação
Publicar este commit completo; não copiar apenas index.html. Manter banco e uploads existentes no disco persistente, fazer backup e usar o fluxo normal de deploy. A tabela de idempotência é criada sem apagar dados. Em instalação nova, configurar NOWUP_ADMIN_EMAIL e NOWUP_ADMIN_PASSWORD forte antes do primeiro startup. Em instalação existente, manter o email administrativo correto. A publicação em produção e seus logs precisam ser conferidos após o deploy.

## Complemento visual incluído no mesmo pacote
O Super ADM conectado usa tokens para roxo principal (#7036c6), hover, pressionado, foco, superfície e textos. O botão compartilhado indica gravação com spinner e aria-busy, bloqueia interação e acompanha a trava síncrona de mutações. Envio concorrente é rejeitado antes de atingir a rede e a trava é liberada em sucesso ou erro. Contraste de textos secundários e placeholders foi aumentado; controles móveis receberam ajustes de tamanho, campos e contenção das tabelas. Indicador azul de métricas passa a roxo, preservando cores semânticas de status.

Validado: build Vite e dois testes JavaScript (incluindo concorrência e desbloqueio após falha). A revisão visual completa em navegador nas larguras 375/768/1440 continua pendente; estes ajustes se aplicam ao Super ADM e não representam padronização completa de todas as páginas legadas, lojista e cliente.
