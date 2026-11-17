# Segredo Gelado

Back-end em Python, FastAPI e MySQL, com login por JWT.

## Para executar no WSL

É necessário ter Python 3.12 ou mais recente e acesso ao sudo para preparar o MySQL.

Na pasta do projeto:

```bash
chmod +x criar-banco-local.sh iniciar.sh
./criar-banco-local.sh
./iniciar.sh
```

O primeiro script prepara o MySQL e salva a conexão no `.env`. O segundo instala as dependências, cria as tabelas e pede o cadastro do administrador, se necessário.

Nas próximas vezes, execute apenas:

```bash
./iniciar.sh
```

Abra [http://localhost:8000/docs](http://localhost:8000/docs) e clique em **Authorize** para entrar com seu usuário e senha.

Para encerrar, pressione **Ctrl+C** no terminal.

Pagamentos e integrações com plataformas são simulados.
