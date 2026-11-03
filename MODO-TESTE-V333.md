# Modo de teste do administrador

Acesso: ADM → Modo de teste → Abrir NowUp em teste.

- Atalho visível tanto no ADM tradicional quanto no Super ADM.
- Tela de controle para cadastrar loja/cliente e alternar entre os perfis de teste.
- Criação rápida de loja: escolher cardápio, vitrine ou ambos, sem documentos e sem pagamento.
- Formulários completos continuam disponíveis; a confirmação de e-mail e liberação do plano são simuladas no ambiente privado.
- Faixa permanente identifica o teste. Sair do teste restaura a sessão administrativa real.
- Para contratar de verdade, sair do teste e cadastrar/contratar na operação real. Não existe conversão automática, cópia de testes para produção ou pagamento real dentro do teste.

## Isolamento

Cada administrador recebe um processo privado, banco SQLite vazio e diretório separado de fotos. O processo não recebe credenciais do PostgreSQL, pagamentos, e-mail, Redis ou armazenamento de produção. Conexões de rede e execução de processos externos são bloqueadas no processo de teste. O transporte interno usa pipes, sem porta pública.

A sessão administrativa real é validada em todas as requisições do teste. Os cookies de acesso dos perfis simulados recebem prefixo próprio. O armazenamento do navegador usa um prefixo específico para separar carrinhos. Formulários e requisições iniciados em uma página de teste recebem uma marca para impedir gravações na operação real quando uma aba antiga permanece aberta depois da saída do teste.

Os testes não aparecem nas lojas públicas, nos pedidos, no faturamento ou nas estatísticas reais. As telas administrativas do teste mostram apenas o banco simulado. Nada do banco real é copiado.

## Operação e limites

O processo de teste inicia somente quando um administrador usa o botão. Requer permissão para iniciar subprocessos Python, utiliza memória adicional e mantém dados temporários até o reinício do serviço. Uma instância de aplicação mantém seu próprio ambiente de teste; se houver vários workers ou réplicas, configurar afinidade de sessão antes de usar esta versão.

Integrações externas não são exercitadas de verdade. PIX/cartão, envio de mensagens, backups externos e notificações precisam ser validados separadamente em seus ambientes de homologação. O modo não altera credenciais nem infraestrutura de produção.

## Validação

Testes de integração conferem autenticação e bloqueio de lojistas, abertura do ADM simulado, cadastro de cliente, criação de loja com cardápio liberado, preservação da sessão real, saída, bloqueio de requisições de abas antigas e contagem inalterada de usuários/pedidos reais. Também verificam que segredos de produção não entram no ambiente do processo privado.

Comando: python3 -m pytest -q tests/test_playground333.py tests/test_security229.py tests/test_origin311.py
