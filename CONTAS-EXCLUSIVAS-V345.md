# Contas exclusivas do cardápio

O cadastro e login pelo link independente de uma loja pertencem exclusivamente àquela loja. Isso também vale para o catálogo. O marketplace mantém seu cadastro e acesso próprios.

- Cadastro, confirmação de e-mail, senha e recuperação próprios por loja.
- Mesmo endereço de e-mail pode ter contas distintas em lojas diferentes; senhas, endereço e histórico não são compartilhados.
- Cookie limitado ao caminho da loja e sessão opaca validada no servidor contra a loja e a conta. Copiar o token para o cookie do marketplace ou de outra loja não concede acesso.
- Logout, recuperação de senha, conversa, comprovantes e acompanhamento de pedidos mantêm a mesma separação.
- Clientes exclusivos ficam fora das campanhas de marketing do marketplace.
- Administradores e lojistas preservam a visualização administrativa existente.

## Rotas

`/p/{slug}/menu?loja=1` abre o produto independente, com cadastro em `/p/{slug}/cadastro`. Lojas no plano somente cardápio usam a identidade independente também no acesso direto ao seu perfil. Lojas com vitrine e cardápio conservam o acesso do marketplace; o link independente utiliza o acesso separado.

## Dados anteriores

A migração é aditiva. Nenhuma conta, pedido ou sessão existente é apagada ou atribuída automaticamente a um lojista. Quem possuía somente conta geral do NowUp deve criar sua conta exclusiva na loja. Os pedidos anteriores permanecem no histórico da conta original. Esse vínculo não pode ser inferido somente pelo e-mail, pois a conta geral podia comprar em várias lojas.

## Implementação

São adicionados `users.customer_store345`, `users.customer_email345` e `sessions.store_id345`, além do índice único do e-mail por loja. A coluna tradicional de e-mail guarda uma chave técnica aleatória para contas exclusivas; as telas autenticadas e as mensagens transacionais utilizam o e-mail de contato da loja, armazenado separadamente.

## Validação

Integração cobre contas independentes com o mesmo e-mail, confirmação e recuperação limitadas à loja, cookies e tokens manipulados, logout independente, marca nas telas, chat, status, pedido real em banco de teste e reconciliação do carrinho sem sessão do marketplace. Foram executadas também as verificações existentes de segurança, renovação, sandbox administrativo, canais de pedidos e consentimento de marketing.
