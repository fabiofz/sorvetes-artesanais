# 7. Conclusão e referências

## 7.1 Demonstração do fluxo completo

Foi executado um cenário fictício em MySQL com um pedido identificado como originado do iFood. A simulação utilizou uma porção de três bolas, sendo duas de Chocolate e uma de Morango, uma caixinha e o valor demonstrativo de R$ 20,00.

O pedido chegou pago e provocou a baixa automática de 120 g de Chocolate, 60 g de Morango e uma caixinha. O reenvio do mesmo pedido não gerou novo pedido nem repetiu a baixa. A cobertura permaneceu sem alteração, pois seu controle é por embalagem.

Após a preparação e a atribuição ao entregador escalado, foi registrado o resultado Ausente. O pagamento passou a Estornado por meio do adaptador mock, com um único registro de estorno integral. A repetição do resultado não gerou outro estorno.

O produto ficou aguardando retorno físico. Após a confirmação fictícia do retorno e da condição, foi registrado como disponível para doação e, posteriormente, como doado. Nenhum saldo foi devolvido ao estoque de venda.

A doação é um registro fictício feito na data da execução. Ela não representa uma doação física nem o acionamento de um agendamento de sexta-feira. A confirmação da condição do produto também faz parte exclusivamente do cenário simulado.

## 7.2 Conclusão

O projeto resultou em um MVP de Back-end para centralizar os pedidos da Segredo Gelado: Sorvetes Artesanais. A implementação em Python utiliza MySQL para persistência, FastAPI para a interface da API e JWT para autenticação, com permissões distintas para administração, atendimento, produção e entrega.

A separação entre situação financeira e andamento operacional permitiu representar pedidos pagos ainda em preparação ou entrega. O controle de estoque considera o consumo estimado de 60 g por bola, a baixa de embalagens por unidade e a movimentação manual das coberturas por embalagem.

A suíte automatizada apresentou 17 testes aprovados, sem falhas ou erros, tanto no MySQL quanto no SQLite em memória. A demonstração adicional apresentou dez verificações aprovadas em cada ambiente. Essas dez verificações pertencem à demonstração e não foram somadas à contagem de 17 testes da suíte.

Os resultados obtidos sustentam o funcionamento dos cenários demonstrados, incluindo a prevenção de duplicações, a consistência das baixas e a separação dos produtos destinados à doação. A arquitetura separa interface HTTP, contratos, regras de aplicação, entidades e persistência, facilitando a evolução do protótipo.

As referências técnicas de implementação incluem a documentação do FastAPI, do SQLAlchemy e do MySQL, além da especificação JWT apresentada na RFC 7519 (FASTAPI, s.d.; SQLALCHEMY, s.d.; ORACLE, s.d.; JONES; BRADLEY; SAKIMURA, 2015).

## 7.3 Limitações e trabalhos futuros

Pagamentos, estornos e recebimentos de marketplaces são simulados. A demonstração não se conectou ao iFood ou a qualquer outra plataforma e não movimentou dinheiro real. Os preços utilizados são exemplos e precisam ser substituídos pelos valores da empresa.

Permanecem como evoluções a conexão real com as plataformas, o aplicativo do entregador, o painel da equipe, as notificações, o tratamento completo das ocorrências e a configuração do ambiente definitivo. A escala é cadastrada manualmente, sem geração automática do regime 5x2.

Não foram realizados testes de carga, de concorrência simultânea ou de integração com serviços externos reais. Os resultados não demonstram prontidão para operação comercial.

O roteiro original contempla também rede de unidades, cardápio por unidade, fidelização com consentimento e promoções. Esses elementos precisam ser conciliados com a adaptação Segredo Gelado antes de considerar a entrega acadêmica completa.

## 7.4 Referências

FASTAPI. OAuth2 with Password (and hashing), Bearer with JWT tokens. [s.d.]. Disponível em: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/. Acesso em: 16 nov. 2026.

SQLALCHEMY. MySQL and MariaDB: SQLAlchemy 2.1 Documentation. [s.d.]. Disponível em: https://docs.sqlalchemy.org/en/21/dialects/mysql.html. Acesso em: 16 nov. 2026.

ORACLE. MySQL 8.4 Reference Manual. [s.d.]. Disponível em: https://dev.mysql.com/doc/refman/8.4/en/. Acesso em: 16 nov. 2026.

JONES, M.; BRADLEY, J.; SAKIMURA, N. JSON Web Token (JWT). RFC 7519. Maio 2015. Disponível em: https://www.rfc-editor.org/rfc/rfc7519.html. Acesso em: 16 nov. 2026.