# Demonstração executada - Segredo Gelado

Resultado: **APROVADO**. Banco: **MySQL 8.4.11**.
Execução registrada: 2026-11-16T01:15:39.346902-03:00

Dados fictícios; iFood, pagamento, estorno e doação simulados. Nenhum dinheiro real movimentado.

## Etapas
1. Login JWT dos usuários fictícios - HTTP 200.
2. Receber pedido iFood fictício já pago - HTTP 201.
3. Reenviar pedido sem duplicar - HTTP 200.
4. Atualizar para EM_PREPARACAO - HTTP 200.
5. Atualizar para PRONTO_PARA_ENTREGA - HTTP 200.
6. Atribuir entregador escalado - HTTP 201.
7. Cliente ausente e estorno mock - HTTP 200.
8. Repetir resultado sem novo estorno - HTTP 200.
9. Consultar retorno pendente - HTTP 200.
10. Confirmar retorno físico fictício - HTTP 200.
11. Registrar destinação fictícia à doação - HTTP 201.
12. Conferir pedido final - HTTP 200.

## Estoque observado

| Item | Inicial | Após pagamento | Após doação fictícia |
|---|---:|---:|---:|
| Chocolate | 1000.000 G | 880.000 G | 880.000 G |
| Morango | 1000.000 G | 940.000 G | 940.000 G |
| Caixinha | 20.000 UN | 19.000 UN | 19.000 UN |
| Cobertura | 2.000 UN | 2.000 UN | 2.000 UN |

## Resultado final
- Pedido: AUSENTE.
- Pagamento: ESTORNADO.
- Estornos mock: 1, no valor demonstrativo de R$ 20.00.
- Produto retornado: DOADO.
- Dez verificações aprovadas, separadas dos 17 testes da suíte.

Doação fictícia registrada na data da execução; não representa doação física ou agendamento de sexta-feira.

## Reproduzir
Instale as dependências de desenvolvimento do projeto e execute:

`python -m app.demo --output docs/demo-resultados.json`

Sem configuração adicional, o comando usa SQLite em memória. Para MySQL, informe DEMO_DATABASE_URL com um banco vazio, descartável e terminado em _test. A demonstração recusa bancos que já possuem tabelas e remove somente o esquema que criou após finalizar. O relatório não contém senhas nem tokens.
