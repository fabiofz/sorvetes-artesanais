# 5. Entrega técnica - primeira versão

## Tecnologias definidas

- Linguagem: Python 3.12.
- API: FastAPI, com documentação Swagger/OpenAPI.
- Banco de dados: MySQL 8.4, acessado com SQLAlchemy e PyMySQL.
- Autenticação: JWT com validade configurável e verificação de assinatura, emissor e destinatário.
- Senhas: hash Argon2.
- Testes: pytest e cliente HTTP da API, com validação em MySQL isolado.

## Fluxo demonstrado

Pedido multicanal -> pagamento mock -> baixa de estoque -> preparação -> atribuição ao entregador escalado -> resultado da entrega.

Em caso de Ausente ou Não entregue: estorno mock confirmado -> retorno físico pendente -> conferência -> registro de doação ou descarte. A mercadoria não retorna ao estoque de venda.

## Principais operações

| Grupo | Operações |
|---|---|
| Acesso | Login e consulta do usuário autenticado |
| Administração | Cadastro de usuários, canais e preços |
| Estoque | Cadastro, entradas, ajustes e consulta de movimentações |
| Pedidos | Criação, consulta, filtro por canal e atualização da preparação |
| Pagamento | Aprovação ou negativa simulada, com baixa única de estoque |
| Entrega | Escala diária, atribuição, consulta individual e resultado |
| Ajuda | Registro de contestação ou acidente e consulta pela equipe |
| Doação | Registro de retorno, condição e destinação |
| Auditoria | Histórico das operações sensíveis |

## Artefatos

- Código-fonte em `app/`.
- Configuração de exemplo em `.env.example`, sem credenciais reais.
- Esquema MySQL em `docs/schema-mysql.sql`.
- Contrato OpenAPI em `docs/openapi.json` e Swagger local em `/docs`.
- Coleção Postman com 28 requisições.
- Cenários e evidências automatizadas em `tests/` e `docs/test-results-*.xml`.
- Instruções de instalação, criação das tabelas, seed e execução no README.

## Pendências

Configurar a conexão com o banco definitivo no computador do aluno, confirmar os preços e as embalagens de cada opção, revisar o projeto e conciliar os itens obrigatórios do roteiro original com a adaptação Segredo Gelado. Repositório: https://github.com/fabiofz/sorvetes-artesanais. O Swagger tem execução local documentada; não há deploy público da API.

Integrações com plataformas, pagamento, estorno, telefonia e notificações reais não estão implementadas. O aplicativo do entregador e o painel da equipe são interfaces futuras; esta entrega é somente o Back-end.
