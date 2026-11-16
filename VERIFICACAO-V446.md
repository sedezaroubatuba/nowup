# V446 - Pacote de ajustes e reauditoria de pré-lançamento

Base de produção: d8d4e25d5e747d9ce1b50b4aea8bf52017b5b22c.

## Entregas

- Formulários de cadastro e contrato enviam apenas campos aceitos pelo servidor. Cupons de mensalidade não são apresentados como integração ativa.
- Horários modificados no ADM atualizam `business_hours`. Editar outros campos sem mexer nos horários preserva a programação existente.
- Suporte e denúncias usam os registros reais da central. Respostas de funcionários ficam em um ledger separado com autoria preservada, visível ao usuário e à central. Registros administrativos anteriores são preservados.
- Novos detalhes de pedido incluem canal, itens/opções, observações, pagamento, comprovantes protegidos e histórico. Não criam sessão de lojista nem confirmam Pix automaticamente.
- Sistema mostra banco ativo, contagens, estado sanitizado de backups e erros HTTP 5xx capturados após a ativação. Não expõe DSN, chave de backup, mensagens de exceção ou tokens de pedidos.
- Textos operacionais distinguem registros reais, planejamento e modo de teste. Explicações de relatórios refletem o fluxo atual do Cardápio.
- Expectativas legadas dos testes foram alinhadas ao aceite antes do Pix e ao WhatsApp como alternativa. Proteções de preço, conta, canal e reenvio continuam testadas.

## Verificação

Instalar `requirements-dev.txt`, `npm ci` na raiz e em `frontend-admin`.

- `python tools/run_checks348.py` executa cada arquivo Python em processo isolado.
- `npm test` na raiz e `npm test` em `frontend-admin`.
- `npm run build` em `frontend-admin`; o resultado deve ser copiado para `static/adm227` antes da publicação.
- Regressões específicas: `tests/test_prelaunch446.py` e `frontend-admin/tests/forms446.test.mjs`.

A reauditoria executou todos os arquivos existentes, voltou a executar os arquivos corrigidos e contabilizou apenas o último resultado de cada arquivo, sem somar repetições. Resultado final: 627 testes Python, 112 JavaScript do produto e 10 JavaScript do ADM aprovados, sem falhas ou skips. Também houve um ensaio adicional de 37 acessos HTTP em SQLite descartável e renderização de cinco áreas do ADM em DOM simulado.

## Pendências externas preservadas

Este pacote não integra cobrança Asaas, não migra o banco nem aumenta plano de hospedagem. Confirmar o banco ativo em Sistema, homologar qualquer migração em destino separado e restaurar uma cópia real antes de aprovar recuperação. O diagnóstico não marca restauração como comprovada sem esse exercício.

Som, vibração, bloqueio de tela, retorno de aplicativo e instalação devem ser verificados em aparelhos reais. O diagnóstico de e-mail indica configuração, não comprova entrega. Termos e privacidade ainda exigem finalização para a operação comercial. Não classificar o produto como homologado para venda ampla com base somente nos testes automáticos.
