# Verificação e operação — V348

Base: commit de produção 538d8f0a920300bd03cdfa6fc478140deb744ce2.

## Verificar alterações

Use Python 3.12 e Node 22. Em um ambiente isolado, sem credenciais de produção:

```
pip install -r requirements-dev.txt
python tools/run_checks348.py
npm ci
npm test
npx playwright install chromium
node --test tests/*.browser.cjs
```

Suítes Python são executadas separadamente porque fixtures legadas alteram globals e ambiente.
Não juntar seus resultados com repetições para inflar contagens.

## Comportamentos corrigidos

- Promoção válida: estritamente maior que zero e menor que o preço normal. Catálogo,
  busca, revisão do pedido, vendas e checkout usam a mesma regra. Alterar o preço pelo
  Super ADM remove uma promoção incompatível. Pedidos anteriores mantêm o preço histórico.
- Reenvio de confirmação: intervalo de 60 segundos por conta, até 3 tentativas por janela
  de 10 minutos e limite por origem. Reutiliza o token ainda válido. A resposta para
  e-mails existentes ou inexistentes é genérica. Mesma proteção nas contas exclusivas.
- Novo pedido: até 5 por conta/loja em 5 minutos e 15 por conta no período. Repetir uma
  chave já concluída continua devolvendo o mesmo pedido, mesmo após atingir o limite.
- Nome e contato seguem a conta autenticada nos dois checkouts; a conta continua ligada
  por ID. O telefone informado é usado quando a conta não possui telefone. Não se declara
  esse número como identidade documental verificada. Destinatário separado ainda não é recurso.
- Link de acompanhamento: somente comprador autenticado e proprietário da loja recebem
  itens/endereço/conversa/pagamento. Outros visitantes recebem apenas situação durante
  sete dias. O link antigo continua acessível ao comprador autenticado. Respostas não são
  armazenadas em cache nem enviam o endereço completo como referência para outros sites.
- Conversa: 20 mensagens por minuto por lado do pedido. Comprovantes: 3 por minuto por
  conta, até 10 arquivos e 20 MB por pedido; reenvio do mesmo comprovante não duplica.
- /health consulta banco e verifica espaço livre mínimo de 10 MB; retorna 503 em falha.
  Isso não substitui alerta de crescimento, teste de escrita ou monitoramento de pedidos.
  render.yaml passa a declarar /health. Alterar o arquivo não comprova que o serviço
  existente tenha adotado o campo: conferir no painel Render.
- Docker exclui históricos ZIP, testes, caches e bancos locais. Nenhum histórico do Git
  é apagado. Dependências de testes ficam explícitas e Node possui lockfile.

## Cobrança e disponibilidade

Asaas permanece uma integração pendente. Não tratar simulação como cobrança real. Cobrança
manual, quando adotada, requer referência de pagamento e conferência do responsável.
Não ativar credenciais ou cobrança de clientes por testes. Mensalidade e pagamento de pedidos
são integrações distintas. Estoque físico/PDV continua exigindo conferência antes do aceite.

## Recuperação de backup

Guardar chave de recuperação separadamente. Em ambiente novo, baixar uma cópia externa,
descriptografar, conferir cada SHA-256 do manifesto e restaurar o dump com pg_restore
compatível. Restaurar também uploads e comparar referências, documentos e comprovantes.
Nunca executar restauração sobre o banco em produção. Medir duração, validar login e pedido
no ambiente recuperado e registrar a cópia utilizada. Um teste SQLite sintético não substitui
esse exercício com o backup PostgreSQL real.

## Capacidade

Medir PostgreSQL e disco de uploads separadamente. O espaço livre de uploads não representa
espaço livre do PostgreSQL. Definir avisos de capacidade e backup antigo, medir crescimento
semanal e aumentar recursos quando o consumo e a latência justificarem. Não existe garantia
para 500 lojas ou 10 mil pedidos/dia sem teste representativo e monitoramento.

## Pendências que não podem ser inventadas em código

- Identificação do responsável, canal oficial, retenção, exclusão e fornecedores para textos
  finais de privacidade/termos, com validação apropriada à operação.
- Restauração do backup externo PostgreSQL real em destino separado.
- Integração e homologação Asaas; cobrança, renovação, cancelamento e webhooks duplicados.
- Integração de estoque/PDV, se desejada; capacidade medida e avaliação em aparelhos reais.
