# Ajustes de segurança e navegação V238

- Alterações por POST/PUT/PATCH/DELETE exigem Origin válido ou Referer da mesma origem. Origin ausente e Referer ausente, Origin null, esquema/porta divergentes e Sec-Fetch-Site cross-site são rejeitados. NOWUP_HTTPS=1 contempla TLS terminado no proxy; NOWUP_PUBLIC_ORIGIN permite fixar a origem pública. O webhook Asaas, quando instalado, mantém a autenticação própria por segredo.
- Sessões de cliente/lojista usam 30 dias de validade renovável no máximo diariamente, até 90 dias absolutos. Após esse limite é necessário entrar novamente. Sessões antigas são limitadas na migração; logout, revogação e inativação continuam válidos. A verificação de usuário é reutilizada somente dentro da mesma requisição.
- A home carrega até 60 candidatos completos e renderiza até 24 na lista principal, mantendo destaques e rodízio. Todas as lojas continuam acessíveis no diretório paginado de 24 lojas, com filtros preservados. O filtro de lojas abertas preserva a avaliação de todas as candidatas.
- Novos índices cobrem avaliações, fotos, exposições por data e pedidos do cliente. Visitas e exposições já registradas evitam gravações vazias. A revisão não modifica o modo de journal do banco em produção: WAL foi ensaiado localmente e apresentou regressão neste cenário.
- O carrossel cria os cartões da primeira página e da próxima inicialmente. As demais páginas são montadas conforme a navegação. As imagens de produtos recebem loading lazy e decoding async; busca e personalização preservam os dados completos originais.
- O teste de backup usa dados sintéticos, gera uma cópia consistente inclusive com dados em WAL e restaura banco e arquivo em uma pasta nova. Isso não confirma as credenciais do armazenamento externo, o disco do Render nem a restauração dos dados reais.

## Limites da validação

Teste de carga local e curto, HTML sem recursos do navegador, com gerador e servidor na mesma máquina. A base revisada tem 500 lojas elegíveis à listagem pública e 50 mil produtos. Os números antigos com clones sem categoria pública não são uma certificação de 500 lojas visíveis. PostgreSQL, armazenamento externo de imagens e validação de carga sustentada com pedidos/chat em homologação equivalente à produção continuam como etapas próprias.

## Comparação local curta

Mesma base elegível e mistura de navegação: 60% loja, 20% home e 20% busca, sem pausa. Em 100 requisições concorrentes, o p95 passou de 4436 ms para 3258 ms, sem falhas em ambas as etapas. Em 1000 concorrentes, a taxa de sucesso foi de 39,55% para 51,82%, ainda insuficiente: houve 676 timeouts em 1403 tentativas na versão ajustada. Esse ensaio não valida 1000 usuários em produção nem inclui checkout, chat ou imagens.
