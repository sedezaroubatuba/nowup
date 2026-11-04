# V355 - Cardápio e vitrine com origens separadas

O painel continua único. O cardápio mantém cadastro, fotos, ingredientes,
combos e os destinos de pedido configurados pelo lojista.

Sem `NOWUP_MENU_ORIGIN`, os links atuais continuam funcionando. O PWA da
vitrine ainda pode capturá-los: a separação de abertura depende do novo domínio.
Cada loja passa a usar um service worker limitado a `/p/<slug>/`.

## Ativação após comprar o domínio

1. Conectar, por exemplo, `menu.dominio-do-proprietario` ao MESMO serviço
   principal do Render. Configurar DNS e verificar certificado HTTPS.
2. Manter a origem da vitrine em `NOWUP_PUBLIC_ORIGIN` / `NOWUP_BASE_URL`.
3. Só então configurar `NOWUP_MENU_ORIGIN=https://menu.dominio-do-proprietario`
   e publicar a configuração. Não incluir caminhos e não usar a origem da vitrine.
4. Conferir links de copiar/abrir do painel, confirmação e recuperação por e-mail,
   login exclusivo da loja, carrinho e preparação do WhatsApp em Android e Safari.
5. Conferir no aparelho com o NowUp já instalado que o novo link abre fora da
   vitrine. A instalação do cardápio continua opcional e usa a identidade da loja.

A mudança não transfere cookies entre origens. Clientes podem precisar entrar
novamente na conta da loja. A instalação antiga do cardápio não é migrada
automaticamente: usar o novo link para reinstalar quando necessário.

Com a configuração ativa, os links externos antigos de cardápio redirecionam
apenas navegações GET/HEAD; formulários e pedidos POST não são reenviados.
O novo endereço não oferece a vitrine nem seu manifesto de instalação.
Termos e privacidade continuam disponíveis dentro da loja. A origem de escrita
é validada separadamente, sem liberar requisições cruzadas entre os aplicativos.

## Verificação local

Executar com banco SQLite descartável e as dependências de teste instaladas:

```sh
python -m pytest -q tests/test_menu_origin355.py tests/test_storeapp256.py tests/test_storeapp257.py tests/test_runtime238.py
python -m pytest -q tests/test_storeaccounts345.py
node --test tests/store-worker355.test.cjs
```

A suíte de contas precisa de processo separado, pois sua fixture inicializa o
módulo de aplicação com outro banco. Não testa Safari físico nem DNS/TLS futuro.
