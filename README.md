# Segredo Gelado - Back-end

Primeira versão executável do sistema de delivery em **Python + FastAPI + MySQL**, com autenticação **JWT** e senhas com hash Argon2.

## O que funciona

- Login e autorização: administrador, atendente, produção e entregador.
- Pedidos com `canalPedido`: WHATSAPP, TELEFONE, IFOOD, 99FOOD, KEETA e novos canais cadastrados.
- Opções de 1, 3 e 6 bolas, com preço definido no servidor.
- Sorvete por sabor: 60 g por bola; embalagens por unidade; coberturas por embalagem com ajuste manual.
- Pedido direto pendente, pagamento mock aprovado ou negado e baixa transacional do estoque.
- Pedido simulado de marketplace já pago, com baixa imediata e proteção contra duplicação.
- Preparação, atribuição a um entregador escalado e conclusão da entrega.
- Ajuda por acidente ou contestação, disponível para consulta da equipe.
- Ausente/Não entregue: estorno mock imediato, registro de prejuízo pelo pedido estornado e produto aguardando retorno.
- Conferência de retorno, segregação do estoque de venda, descarte ou registro de doação.
- Auditoria das operações sensíveis e erros padronizados sem copiar os dados pessoais recebidos.

**Pagamentos, estornos e pedidos externos são simulações. Nenhuma plataforma está conectada e nenhum dinheiro é movimentado.** Cadastrar Keeta ou outro canal não estabelece uma integração real.

## 1. Preparar o MySQL

Requisitos: Python 3.12 e MySQL 8.4. Execute o bloco abaixo no MySQL Workbench conectado como administrador, substituindo a senha antes de executar. O banco e o usuário são exclusivos do projeto.

```sql
CREATE DATABASE segredo_gelado CHARACTER SET utf8mb4;
CREATE USER 'segredo'@'localhost' IDENTIFIED BY 'SUBSTITUA_POR_SENHA_FORTE';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON segredo_gelado.* TO 'segredo'@'localhost';
```

Se já existir um banco com esse nome, escolha outro nome para não misturar os dados. As instruções não exigem remover bancos existentes.

## 2. Instalar no Windows

Abra o terminal na pasta que contém este README:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -c constraints-tested.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Edite `.env` no seu computador. Em `DATABASE_URL`, informe usuário, senha, host, porta e banco do MySQL. Em `JWT_SECRET`, coloque a chave gerada no último comando. Não publique `.env` nem envie suas senhas pelo chat. Se a senha contiver `@`, `:`, `/`, `#` ou `%`, codifique esses caracteres na URL (por exemplo, `@` vira `%40`).

## 3. Criar tabelas e dados iniciais

```powershell
.\.venv\Scripts\python.exe -m app.cli init-db
.\.venv\Scripts\python.exe -m app.cli create-admin
.\.venv\Scripts\python.exe -m app.cli seed-demo
```

O administrador é criado interativamente, sem senha padrão. A senha não é exibida. A inicialização cria somente tabelas ausentes; alterações futuras do esquema precisam de uma nova migração. `docs/schema-mysql.sql` contém o esquema inicial equivalente, como referência e alternativa ao comando `init-db`.

O seed é repetível e não sobrescreve cadastros existentes. Os preços de **R$ 8, R$ 20 e R$ 36 são exemplos**, não preços informados pela empresa. Os estoques começam zerados. Cadastre entradas antes de confirmar vendas.

## 4. Executar e usar

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra a documentação interativa em `http://127.0.0.1:8000/docs`. Use **Authorize**, com o login e a senha do administrador. O login usa formulário `username` e `password`; o token é enviado como `Authorization: Bearer ...`. Expira em 30 minutos por padrão.

### Demonstração do fluxo

1. Consulte `GET /catalog/offers` e `GET /inventory` para obter os identificadores.
2. Use `POST /inventory/{id}/adjustments` para registrar entradas. Exemplo: `{"quantity":1000,"reason":"Entrada demonstrativa"}` para sorvete e 20 unidades para caixinhas.
3. Crie o pedido pelo exemplo abaixo, substituindo os IDs pelos seus cadastros.
4. Confirme o pagamento em `POST /orders/{id}/payment/mock`, com `{"approved":true}`. Com `false`, a tentativa é negada, o pedido continua pendente e o estoque permanece igual.
5. Atualize para `EM_PREPARACAO` e depois `PRONTO_PARA_ENTREGA` em `PATCH /orders/{id}/status`.
6. Crie os entregadores em `POST /users`, registre a escala do dia em `PUT /shifts` e atribua o pedido em `POST /orders/{id}/delivery`.
7. Autentique o entregador. Consulte `/deliveries/mine` e utilize as ações de resultado ou ajuda.

```json
{
  "canalPedido": "WHATSAPP",
  "external_id": "pedido-demo-001",
  "customer_name": "Cliente fictício",
  "customer_contact": "000000000",
  "address": "Rua demonstrativa, 10",
  "payment_method": "PIX",
  "already_paid": false,
  "items": [{
    "offer_id": 2,
    "quantity": 1,
    "flavors": [{"inventory_id": 1, "balls": 3}],
    "packages": [{"inventory_id": 3, "quantity": 1}]
  }]
}
```

`flavors[].balls` é a quantidade de bolas desse sabor **por porção**. `items[].quantity` é a quantidade de porções. `packages[].quantity` é o total de embalagens **da linha inteira**. A cobertura não entra nessa baixa automática.

Para simular iFood, use `canalPedido=IFOOD`, `already_paid=true` e `payment_method=PLATAFORMA`. O recebimento no MVP ocorre pelo mesmo endpoint autenticado, sem chamar APIs externas. O preço e o valor total são calculados pelo servidor.

O par canal + código externo é único. Repetir exatamente o mesmo pedido retorna o registro existente, sem nova baixa. Dados diferentes com o mesmo código retornam 409. Confirmações de pagamento e resultados de entrega repetidos não repetem a baixa nem o estorno.

### Entregas e doações

- `ENTREGUE`: encerra com sucesso, mantendo o pagamento.
- `AUSENTE` ou `NAO_ENTREGUE`: encerra sem sucesso, confirma estorno mock integral e gera um registro aguardando retorno físico. Não devolve saldo ao estoque de venda.
- `POST /deliveries/{id}/help`, tipo `ACIDENTE` ou `CONTESTACAO`: registra ocorrência aberta sem encerrar a entrega. A equipe consulta `/incidents`; envio de push e atendimento da ocorrência ficam para evolução.
- `POST /donations/items/{id}/return`: confirma o retorno e a condição. Produto adequado fica disponível; inadequado fica descartado.
- `POST /donations`: registra a destinação. Somente produtos retornados e disponíveis podem ser doados.

As doações de sexta-feira são registradas pela equipe. Não existe tarefa automática que marque um produto como doado sem a destinação física. A escala 5x2 é cadastrada manualmente; o sistema exige que o entregador esteja escalado na data da atribuição, considerada no fuso America/Sao_Paulo.

## 5. Testes

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Por padrão, usa um SQLite em memória e não toca no banco configurado em `.env`. Para verificar também no MySQL, crie um **banco descartável cujo nome termine em `_test`**, com usuário autorizado a criar e apagar tabelas:

```powershell
$env:TEST_MYSQL_URL = "mysql+pymysql://usuario:senha@127.0.0.1:3306/segredo_gelado_test?charset=utf8mb4"
.\.venv\Scripts\python.exe -m pytest tests -q
Remove-Item Env:TEST_MYSQL_URL
```

Essa modalidade cria e apaga as tabelas no banco de teste. Nunca use o banco da operação. Os cenários estão em `docs/PLANO_DE_TESTES.md`; o resultado verificado no MySQL está em `docs/test-results-mysql.xml`.

Importe `docs/Segredo_Gelado.postman_collection.json` no Postman. Preencha as variáveis `username` e `password` com o administrador do banco demonstrativo e execute a coleção em ordem. Ela cria dados fictícios, registra entradas e executa um pedido; use um banco de demonstração. Não exporte a coleção com sua senha preenchida.

## Organização

- `app/models.py`: entidades persistentes e restrições do domínio.
- `app/schemas.py`: contratos e validações de entrada e saída.
- `app/services.py`: casos de uso e regras transacionais.
- `app/db.py`: conexão e unidade de transação.
- `app/security.py`: hash de senha, emissão e validação JWT, permissões.
- `app/main.py`: interface HTTP e documentação OpenAPI.
- `app/cli.py`: esquema inicial, administrador e seed.
- `tests/`: validação automatizada com banco isolado.

O esquema implementado simplifica a modelagem conceitual: entregadores são usuários com perfil ENTREGADOR; o folguista é identificado por `relief`; sabores e embalagens compartilham a tabela de estoque; os produtos retornados são descritos por pedido em um registro de doação. O histórico de preços e sabores é preservado nos itens do pedido.

## Privacidade e limites desta versão

A finalidade dos dados de cliente é atender e entregar o pedido. O modelo coleta nome, contato e endereço, sem CPF ou dados de cartão. Senhas são armazenadas com Argon2. JWT contém somente identificador do usuário e informações de validade; as permissões atuais são consultadas no banco. Produção não recebe contato ou endereço; entregadores só consultam suas entregas. Auditoria registra IDs e ações, sem copiar os dados pessoais.

Esta versão é um Back-end local, sem aplicativo ou painel visual. HTTPS, proteção contra tentativas excessivas de login, gestão de segredos, backups, política de retenção/exclusão e monitoramento devem ser tratados antes de uso real. Não há integração real com WhatsApp, telefonia, iFood, 99Food, Keeta, gateways, push ou estornos reais. O atendimento telefônico é representado pelo cadastro autenticado do pedido.

## Alinhamento ao roteiro acadêmico

O MVP segue o cenário Segredo Gelado definido na conversa. O roteiro original também exige contexto de rede/unidades, cardápio por unidade, fidelização com consentimento e promoções ao menos conceituais. Esses itens **não estão implementados nem completamente descritos nesta adaptação**; devem ser conciliados com o professor antes de considerar a entrega acadêmica completa. O campo `canalPedido` é representado por um cadastro de canais validado pelo servidor para permitir novas plataformas, em vez de um ENUM fechado; essa diferença também deve ser justificada no relatório.

O repositório está disponível em https://github.com/fabiofz/sorvetes-artesanais. O Swagger pode ser acessado localmente seguindo as instruções deste README; não há deploy público da API.

## Referências técnicas

- [FastAPI - OAuth2 e JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [SQLAlchemy - MySQL e MariaDB](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)


## Demonstração reproduzível

Execute `python -m app.demo --output docs/demo-resultados.json` após instalar as dependências de desenvolvimento. O padrão é SQLite em memória. Para MySQL, use DEMO_DATABASE_URL apontando para um banco vazio e descartável terminado em `_test`. O comando recusa bancos com tabelas preexistentes e remove o esquema que criou ao terminar. Veja `docs/DEMONSTRACAO.md` e as evidências `docs/demo-resultados-mysql.json` e `docs/demo-resultados-sqlite.json`. Nenhum serviço externo é acionado e não há movimentação financeira real.
