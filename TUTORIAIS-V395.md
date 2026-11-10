# Tutoriais do painel

Acesso pelo atalho Tutoriais no início e no menu lateral do lojista.

- Conteúdo e alvos: `static/tutorials-data395.js`.
- Guia que navega e destaca campos reais: `static/tutorials395.js`.
- Área de leitura e exemplos de 1, 2 e 4 produtos: `templates/tutorials395.html`.
- O guia não preenche, envia nem salva formulários. Não executa pedidos ou pagamentos.
- Moda recebe conteúdo específico e não mostra tutoriais de comida nem os formatos do carrossel.
- Um alvo ausente por plano/configuração recebe uma explicação; não é substituído por outro campo.

## Ao alterar o painel ou o fluxo

1. Revise os textos e seletores dos tutoriais afetados.
2. Confira no painel os campos destacados, a navegação, os exemplos e o funcionamento no celular.
3. Rode `npm test`.
4. Depois da revisão, rode `node tools/check_tutorials395.cjs --reviewed` e inclua o arquivo atualizado no commit.
5. Se modificar os recursos estáticos, atualize suas versões no `pro_panel.html`.

O workflow `tutorials395.yml` compara hashes das telas e dos fluxos acompanhados com a última revisão e falha se detectar diferenças. É um sinal para revisão humana: não reescreve instruções, não gera capturas automaticamente e não garante sozinho que alterações de comportamento estejam cobertas. Novas telas relevantes devem ser incluídas na lista do verificador.

## Validação desta entrega

- 56 testes JavaScript aprovados, incluindo 5 cenários do guia: navegação, preservação de formulários, fechamento, opção ausente, pesquisa, moda e layout.
- Templates compilados com Jinja; exemplos renderizados com catálogo vazio/preenchido e moda; escape de nomes conferido.
- Revisão visual autenticada em produção ainda necessária. O navegador da sessão recusou a abertura da prévia local; nenhum login de lojista foi usado.
