# Cadastro conforme o plano

Só cardápio ou catálogo usa cadastro simples: nome da loja, e-mail, celular, senha e endereço. CPF ou CNPJ é opcional; quando informado, é validado. Não são exigidos nem armazenados anexos de documentação nesse fluxo. Categorias e informações extras são opcionais no cadastro simples. A cidade é digitada livremente.

A vitrine mantém CNPJ, dados do responsável e os quatro documentos privados obrigatórios. A disponibilidade por cidade é validada no navegador e no servidor, sem trocar silenciosamente uma cidade não atendida por Ubatuba.

O lojista pode escolher Outro e informar seu tipo de comércio. O nome é salvo no perfil e exibido no perfil público e no ADM. O texto não cria automaticamente uma categoria pública compartilhada.

A confirmação do e-mail e a aprovação do plano/pagamento permanecem. Cadastro simples não libera acesso pago automaticamente. Uma posterior migração à vitrine exige documentação conferida e cidade atendida. O lojista pode enviar os documentos em Documentos da loja; a análise da migração não interrompe seu cardápio ativo.

São adicionadas as colunas professionals.simple_menu346 e professionals.business_segment346. Cadastros antigos mantêm seus dados e sua situação.

Validação: registros de cardápio e catálogo sem anexos, CPF/CNPJ opcional, exigências completas da vitrine, cidade fora da área, segmento manual, aprovação simples e migração com análise. O teste de interface cobre troca de plano, campos obrigatórios/ocultos, documento opcional, cidade e categoria manual.
