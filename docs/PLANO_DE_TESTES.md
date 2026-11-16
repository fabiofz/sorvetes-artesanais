# Cenários automatizados

Execute `python -m pytest tests -q` na raiz do projeto. Todos os dados são fictícios.

| Nº | Cenário | Resultado esperado |
|---|---|---|
| 1 | Login válido e consulta do perfil | 200; JWT aceito; senha armazenada com Argon2 e não exposta |
| 2 | Pedido direto, pagamento e repetição | 201/200; baixa de 120 g de Chocolate, 60 g de Morango e 1 caixinha uma única vez |
| 3 | Pedido iFood pago e repetição | 201/200; mesmo pedido, baixa única; filtro por canal funciona |
| 4 | Preparação e entrega concluída | 200; Entregue e Pago; nenhum estorno |
| 5 | Ajuda por acidente e contestação | 201; ocorrências visíveis à equipe; entrega permanece em andamento |
| 6 | Ausente, estorno, retorno e doação | 200/201; um estorno, estoque sem reposição, retorno confirmado antes da doação |
| 7 | Pagamento mock negado | 200 com approved=false; pagamento pendente e estoque preservado |
| 8 | Sem token e senha errada | 401; mensagem sem senha recebida |
| 9 | Perfil sem permissão e entrega de outro usuário | 403/404; produção sem contato/endereço; entregador sem acesso à lista geral |
| 10 | Canal ausente e soma de bolas inválida | 422; pedido inválido rejeitado |
| 11 | Falta de um sabor durante a baixa | 409; rollback de todas as baixas e do pagamento |
| 12 | Mesmo código com outro conteúdo e marketplace sem estoque | 409; sem pedido extra nem baixa parcial |
| 13 | Preparar sem pagamento e atribuir a entregador sem escala | 409; transição bloqueada |
| 14 | Doar antes do retorno ou após descarte | 409; item não doado |
| 15 | JWT expirado ou com assinatura diferente | 401 |
| 16 | Novo canal e cobertura por embalagem | 201/200; entrada/saída inteira; fração de embalagem rejeitada com 422 |

A configuração TEST_MYSQL_URL permite repetir a mesma suíte em um MySQL descartável. Ela valida o dialeto e a persistência reais, mas não é um teste de carga nem de corrida entre múltiplas conexões simultâneas. Os controles de concorrência incluem bloqueio pessimista de linhas e restrições únicas no banco.

| 17 | Sequência HTTP da coleção Postman | As 28 requisições retornam os status esperados, incluindo cadastro, login, entrega, estorno e doação |

O cenário 17 executa os requests da coleção com substituição de variáveis pelo teste Python. Ele valida a sequência HTTP; os scripts JavaScript da coleção continuam destinados ao Postman.
