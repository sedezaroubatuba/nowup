# NowUp: revisão de segurança, fluidez e prévia — 11/11/2026

Base examinada: `e847fbe4f1c6c089dabdffe4751fab7ea04f96a0`, branch de produção `codex/categorias-icones-v230`.

## Alterações implementadas

- Login principal, login exclusivo da loja e equipe ADM executam a comparação de senha também para contas inexistentes/inativas. Isso reduz a diferença de tempo que poderia ajudar a descobrir contas. Limites de tentativas continuam ativos, antes do processamento da senha. O hash fictício nunca autentica uma conta.
- Abrir `GET /admin/entrar` não apaga mais a sessão atual. Sair continua exigindo a ação explícita `POST /sair`, protegida pela verificação de origem.
- O quadro do lojista mantém os cartões existentes quando a resposta do servidor não mudou. Isso evita substituir elementos e perder interação sem necessidade. Pedidos novos continuam atualizando o quadro.
- O complemento de status das notificações consulta o servidor somente quando a lista está visível e interrompe consultas após 401/403. O som e os alertas de novos pedidos não foram pausados.
- Versões dos dois arquivos JavaScript atualizadas para evitar reutilização do código antigo pelo navegador.

## Validação

- Python: **496 testes passaram** (`PYTHONPATH=.:tests python -m pytest -q --disable-warnings`).
- JavaScript: 59 testes existentes aprovados, mais uma regressão nova que comprova a preservação de cartões em respostas iguais e a atualização quando o pedido muda.
- Dependências: `pip-audit -r requirements.txt`, **55 dependências, nenhuma vulnerabilidade conhecida reportada**. Não equivale a ausência garantida de vulnerabilidades.
- Casos verificados incluem sessão expirada/revogada, conta desativada, logout, origem de requisições, permissões, isolamento entre lojas, recuperação de senha, arquivos privados, anexos, duplicidade de pedidos, preços recalculados e Pix imediato.
- Três falhas iniciais da suíte completa eram manutenção dos próprios testes: a fixture trocava o banco após configurar os banners; duas expectativas ainda exigiam revisão antes do Pix ou o texto antigo do botão de confirmação. As expectativas agora conferem o fluxo vigente, mantendo os controles de privacidade e pagamento não confirmado.

## Observações da operação publicada antes da alteração

`/health`, `/entrar` e cardápio da Sede Zero responderam HTTP 200. Cabeçalhos de HTTPS, bloqueio de enquadramento, `nosniff`, política de conteúdo e `private, no-store` presentes nas páginas verificadas. Não foram usados logins nem dados pessoais de clientes reais.

Métricas Render da janela consultada: memória aproximadamente 148 MiB de 512 MiB, uso de CPU aproximadamente 0,004 core. Isso representa a janela observada, não uma garantia de capacidade sob carga.

O cardápio da Sede Zero devolveu cerca de 1,05 MB de HTML descomprimido, já com gzip e 442 imagens marcadas como lazy. Compressão e lazy loading já existem; a evolução futura de maior impacto é reduzir a quantidade de cartões renderizados de uma vez, preservando busca, categorias e produtos. Essa alteração ampla não foi aplicada sem a validação visual do catálogo.

## Prévia para avaliação

https://nowup-previa-cadastro-menu-samuel.samuelsantos74068.chatgpt.site

Protótipo privado e independente do sistema real. Cadastro em três etapas para produtos, combos e acompanhamentos/adicionais; exemplo inicial por tipo de loja; revisão; prévia do item; menus branco, azul-petróleo e lavanda claro. Nenhum produto, preço ou categoria da operação real é modificado. Funções avançadas existentes serão preservadas ao implementar o desenho aprovado. Rascunho do protótipo dura apenas enquanto a página está aberta.

## Teste de 300 pedidos / duas horas

Execução: https://github.com/sedezaroubatuba/nowup/actions/runs/42971648014

**Em andamento no momento deste relatório. Resultado final ainda não disponível.**

- 150 pedidos no fluxo principal e 150 no cardápio independente, intercalados durante 7.200 segundos.
- Cópia fictícia da Sede Zero; sem clientes, estoque, pagamentos ou relatórios reais.
- Contas e sessões reais da aplicação em banco SQLite descartável; endpoints ASGI da mesma aplicação, sem substituir `current_user`.
- Confere valor, destinatário e decodificação do QR Pix, origem do pedido, acompanhamento autenticado e repetição idempotente.
- Rede externa e subprocessos bloqueados pelo executor. Não envia WhatsApp, e-mail, push ou Pix bancário real.
- Artefato final: `nowup-pix-soak404-results`, com `status.json` e `requests.jsonl`.
- Smoke separado: quatro pedidos acelerados, quatro aprovados. Isso não é o resultado do teste de duas horas.

## Limites

Esta revisão automatizada não é uma certificação ou teste de invasão completo. O teste de duas horas não mede PostgreSQL nem carga do Render, entrega de WhatsApp, notificações externas ou liquidação Pix no banco. Não houve alteração de credenciais, contratação de infraestrutura ou migração do banco de produção.

Referências: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html e https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html.
