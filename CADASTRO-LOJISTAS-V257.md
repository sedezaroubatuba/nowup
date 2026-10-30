# Cadastro e conferência de lojistas

Base: codex/categorias-icones-v230, commit 79853c7.

Novos lojistas: CNPJ numérico com validação de dígitos, razão social, responsável, CPF e vínculo; fachada, comprovante do CNPJ, documento do responsável e comprovante de endereço comercial. Fotos JPG/PNG/WebP até 5 MB, convertidas sem metadados para JPEG. Anexos privados no banco, fora das pastas públicas.

Super ADM: /admin/verificacao-lojistas. Conferência manual com motivo, responsável e data. Acesso aos anexos registrado. A aprovação do cadastro exige a conferência documental; ativação comercial e pagamento seguem os fluxos existentes. Não há consulta automática de CNPJ, biometria ou prova de vida.

Lojista: /painel/documentos mostra a situação e o motivo e permite reenvio completo durante análise ou após pedido de correção. Cadastros anteriores preservam sua aprovação, incluindo a Sede Zero; nenhuma loja é marcada automaticamente como identidade verificada.

Clientes: nome, e-mail, telefone obrigatório, endereço, senha e aceite existentes. Sem documentos adicionais.

As tabelas são criadas no startup. O tamanho dos anexos aumenta o banco e seus backups. Esta base usa SQLite; a compatibilidade com a branch PostgreSQL não foi validada.

Validação: testes de dígitos, imagens, armazenamento privado, bloqueio de aprovação e recusa de acesso de clientes, além da suíte de auditoria existente.
