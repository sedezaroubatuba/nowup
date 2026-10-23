# NowUp — Categorias e galeria de ícones V230

A segunda prévia foi implementada: cabeçalho roxo, cartões brancos com ícones roxos e categoria selecionada em roxo com desenho e texto brancos.

Os mesmos desenhos vetoriais aparecem nos atalhos da home, na lista expandida de categorias, na navegação da loja, no menu lateral, nos títulos dos carrosséis e em “Ver todos”.

## Cadastro

No painel do lojista, abra **Categorias → Adicionar / editar categorias**. Digite o nome: a opção **Automático pelo nome** sugere o ícone. Em **Trocar ícone**, pesquise e escolha entre 36 desenhos. Salve a categoria para compartilhar a escolha entre aparelhos e telas. A galeria também está disponível na gestão de categorias do administrador.

Categorias antigas recebem ícones automaticamente, sem novo cadastro. Nomes desconhecidos usam o desenho de categoria geral. Ícones escolhidos manualmente permanecem após renomear. Volte para **Automático** para acompanhar o nome novamente.

## Publicação

A alteração está na branch `codex/categorias-icones-v230`, baseada na `main`. Para publicar no serviço atual, integre a alteração à branch usada pelo Render e execute **Manual Deploy → Deploy latest commit**, caso o deploy automático esteja desativado. Não é necessário copiar arquivos manualmente.

A inicialização acrescenta `icon_key` à tabela `product_categories`, preservando categorias e produtos existentes. O catálogo de desenhos é local e não requer serviço pago, geração de imagem ou chave de API.

## Verificação

Testes de correspondência dos nomes, escolha manual, isolamento entre lojas, renomeação, migração idempotente e renderização das telas. Os testes existentes de pedidos, sessão e checkout também foram executados.
