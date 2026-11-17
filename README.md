# Segredo Gelado - Sorvetes Artesanais

Back-end para organizar os pedidos de uma sorveteria que trabalha só com delivery. O projeto usa Python, FastAPI e MySQL, com login por JWT.

A ideia é reunir os pedidos do WhatsApp, telefone, iFood e 99Food em um só lugar, acompanhar as entregas e controlar o estoque. Também é possível cadastrar outros canais, como a Keeta.

Nesta versão, os pedidos das plataformas, os pagamentos e os estornos são simulados. Não há conexão com serviços externos nem movimentação de dinheiro real.

## Como iniciar no WSL

É preciso ter Python 3.12 ou mais recente. Dentro da pasta do projeto, execute:

```bash
./iniciar.sh
```

Na primeira vez, o script prepara o ambiente Python e instala as dependências. Depois, confere o MySQL, cria as tabelas que faltam e pede o cadastro do administrador, caso ainda não exista um.

Se o terminal mostrar “Permissão negada”, execute:

```bash
chmod +x iniciar.sh criar-banco-local.sh
```

### Se ainda não tiver o banco

Execute antes de iniciar o app:

```bash
./criar-banco-local.sh
```

Esse script instala e inicia o MySQL no WSL, cria o banco `segredo_gelado` e salva a conexão no arquivo `.env`. Ele pede a senha do sudo no terminal e não apaga bancos existentes. Se já houver um `.env`, ele preserva o arquivo e interrompe a configuração.

Se você já usa outro MySQL, o `iniciar.sh` pede os dados de conexão quando não encontra o `.env`. Nesse caso, o banco precisa estar criado e acessível pelo WSL.

O `.env` guarda a conexão com o banco e a chave JWT. Use `.env.example` como referência e mantenha suas credenciais fora do Git.

## Como acessar

Com o app rodando, abra [http://localhost:8000/docs](http://localhost:8000/docs).

Essa página é o Swagger, onde você pode testar a API. Clique em **Authorize** e informe o usuário e a senha que cadastrou. A senha não aparece enquanto é digitada no terminal.

Mantenha o terminal aberto enquanto usa o app. Para encerrar, pressione **Ctrl+C**.

Para conferir apenas a conexão com o banco:

```bash
./iniciar.sh --verificar
```

## O que dá para testar

- Criar pedidos e consultar por canal de origem.
- Confirmar ou negar um pagamento simulado.
- Conferir a baixa do estoque e atualizar o preparo.
- Atribuir uma entrega a um entregador escalado.
- Marcar a entrega como entregue, ausente ou não entregue.
- Pedir ajuda em caso de acidente ou contestação.
- Registrar o retorno dos produtos e sua destinação para doação.

O sorvete é controlado por sabor, considerando cerca de 60 g por bola. Caixinhas e cestinhas são contadas por unidade. As coberturas são controladas por embalagem, com atualização manual quando acabam ou são repostas.

Pedidos ausentes ou não entregues recebem estorno simulado. Os produtos retornados ficam separados do estoque de venda e só podem ser registrados como doados depois da conferência do retorno.

Os cadastros de exemplo usam preços fictícios e começam com estoque zerado. Antes de vender, registre as entradas em `POST /inventory/{id}/adjustments`.

## Testes

Instale as dependências de teste e execute:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt -c constraints-tested.txt
.venv/bin/python -m pytest tests -q
```

Por padrão, os testes usam um banco em memória e não alteram o banco do app.

Para testar pelo Postman, importe [a coleção do projeto](docs/Segredo_Gelado.postman_collection.json), preencha `username` e `password` e execute as requisições em ordem. Use um banco de demonstração, pois a coleção cria cadastros, movimenta estoque e registra pedidos.

Também há uma demonstração automática com dados fictícios:

```bash
.venv/bin/python -m app.demo --output docs/demo-resultados.json
```

Ela usa um banco em memória e percorre o fluxo de pedido, entrega sem sucesso, estorno e doação. Os detalhes estão em [DEMONSTRACAO.md](docs/DEMONSTRACAO.md).

## Onde encontrar as coisas

- `app/`: código da API, regras de negócio, login e banco de dados.
- `tests/`: testes automatizados.
- [Diagramas](docs/diagramas/README.md): casos de uso, banco e classes.
- [Plano de testes](docs/PLANO_DE_TESTES.md): cenários e resultados esperados.
- [Esquema MySQL](docs/schema-mysql.sql): estrutura inicial das tabelas.
- [OpenAPI](docs/openapi.json): documentação dos endpoints.

O projeto ainda é um protótipo. O aplicativo dos entregadores, o painel de atendimento e as integrações reais ficam para as próximas etapas. A escala e as doações de sexta-feira são registradas pela equipe, sem agendamento automático.

O roteiro acadêmico também pede unidades, fidelização e promoções. Esses pontos ainda precisam ser ajustados nesta adaptação antes da entrega final.
