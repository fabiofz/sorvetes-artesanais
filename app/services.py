from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from app import models as m


def audit(db, actor, action, entity, entity_id=None):
    db.add(m.Audit(actor_id=actor.id, action=action, entity=entity, entity_id=entity_id))


def require(db, model, key, lock=False):
    query = select(model).where(model.id == key)
    if lock:
        query = query.with_for_update()
    obj = db.scalar(query)
    if obj is None:
        raise HTTPException(404, 'Registro não encontrado.')
    return obj


def order_locked(db, order_id):
    return require(db, m.Order, order_id, lock=True)


def balance_change(db, stock, quantity, actor, reason, order_id=None, kind='AJUSTE'):
    quantity = Decimal(quantity)
    if stock.unit == 'UN' and quantity != quantity.to_integral_value():
        raise HTTPException(422, 'Embalagens e coberturas exigem quantidades inteiras.')
    if stock.balance + quantity < 0:
        raise HTTPException(409, f'Estoque insuficiente para o item {stock.id}.')
    stock.balance += quantity
    db.add(m.Movement(inventory_id=stock.id, order_id=order_id, actor_id=actor.id,
                      kind=kind, quantity=quantity, reason=reason))


def debit_stock(db, order, actor):
    required = defaultdict(Decimal)
    for item in order.items:
        for flavor in item.flavors:
            required[flavor.inventory_id] += Decimal(flavor.balls * item.quantity * 60)
        for package in item.packages:
            required[package.inventory_id] += Decimal(package.quantity)
    # Ordem determinística reduz deadlocks entre pedidos que usam os mesmos sabores.
    for stock_id in sorted(required):
        stock = require(db, m.Inventory, stock_id, lock=True)
        balance_change(db, stock, -required[stock_id], actor, 'Pedido pago', order.id, 'VENDA')


def create_order(db, data, actor):
    channel = db.scalar(select(m.Channel).where(m.Channel.name == data.canalPedido))
    if not channel or not channel.active:
        raise HTTPException(422, 'Canal de venda não cadastrado ou inativo.')
    fingerprint = sha256(data.model_dump_json().encode()).hexdigest()
    existing = db.scalar(select(m.Order).where(m.Order.channel_id == channel.id,
                                              m.Order.external_id == data.external_id))
    if existing:
        if existing.payload_hash != fingerprint:
            raise HTTPException(409, 'Código externo já utilizado com dados diferentes.')
        return existing, False
    if data.already_paid != channel.prepaid:
        raise HTTPException(422, 'Marketplaces chegam pagos; pedidos diretos são confirmados pelo pagamento mock.')
    if channel.prepaid != (data.payment_method == 'PLATAFORMA'):
        raise HTTPException(422, 'Meio de pagamento incompatível com o canal.')
    customer = m.Customer(name=data.customer_name, contact=data.customer_contact)
    db.add(customer)
    db.flush()
    order = m.Order(customer_id=customer.id, channel_id=channel.id, external_id=data.external_id,
                    payload_hash=fingerprint, address=data.address, total=Decimal('0'), status='RECEBIDO')
    db.add(order)
    db.flush()
    total = Decimal('0')
    for row in data.items:
        offer = require(db, m.Offer, row.offer_id)
        if sum(x.balls for x in row.flavors) != offer.balls:
            raise HTTPException(422, 'A soma das bolas por sabor deve corresponder à opção de venda.')
        item = m.OrderItem(order_id=order.id, offer_id=offer.id, balls=offer.balls,
                           quantity=row.quantity, unit_price=offer.price)
        for flavor in row.flavors:
            stock = require(db, m.Inventory, flavor.inventory_id)
            if stock.category != 'SORVETE':
                raise HTTPException(422, 'O sabor deve ser um item de estoque de sorvete.')
            item.flavors.append(m.FlavorItem(inventory_id=stock.id, balls=flavor.balls))
        for package in row.packages:
            stock = require(db, m.Inventory, package.inventory_id)
            if stock.category != 'EMBALAGEM':
                raise HTTPException(422, 'Selecione caixinha ou cestinha como embalagem.')
            item.packages.append(m.PackageUse(inventory_id=stock.id, quantity=package.quantity))
        order.items.append(item)
        total += offer.price * row.quantity
    order.total = total
    payment = m.Payment(order_id=order.id, amount=total, method=data.payment_method,
                        processor=channel.name if channel.prepaid else 'MOCK', status='PENDENTE')
    order.payment = payment
    db.add(payment)
    db.flush()
    if channel.prepaid:
        debit_stock(db, order, actor)
        payment.status = 'PAGO'
        payment.reference = f'mock-marketplace-{order.id}'
    audit(db, actor, 'PEDIDO_CRIADO', 'order', order.id)
    db.flush()
    return order, True


def pay_order(db, order_id, approved, actor):
    order = order_locked(db, order_id)
    payment = order.payment
    if order.channel.prepaid:
        raise HTTPException(409, 'O pagamento deste canal é controlado pela plataforma.')
    if payment.status == 'ESTORNADO':
        raise HTTPException(409, 'O pedido já foi estornado.')
    if payment.status == 'PAGO':
        return order, True
    if not approved:
        audit(db, actor, 'PAGAMENTO_MOCK_NEGADO', 'order', order.id)
        return order, False
    debit_stock(db, order, actor)
    payment.status = 'PAGO'
    payment.reference = f'mock-payment-{order.id}'
    audit(db, actor, 'PAGAMENTO_MOCK_APROVADO', 'order', order.id)
    db.flush()
    return order, True


def change_status(db, order_id, target, actor):
    order = order_locked(db, order_id)
    if order.status == target:
        return order
    expected = {'EM_PREPARACAO': 'RECEBIDO', 'PRONTO_PARA_ENTREGA': 'EM_PREPARACAO'}
    if order.payment.status != 'PAGO' or order.status != expected[target]:
        raise HTTPException(409, 'Transição inválida ou pagamento ainda não confirmado.')
    order.status = target
    audit(db, actor, 'STATUS_' + target, 'order', order.id)
    return order


def assign_delivery(db, order_id, driver_id, actor):
    order = order_locked(db, order_id)
    if order.delivery and order.delivery.driver_id == driver_id and order.status == 'EM_ENTREGA':
        return order.delivery
    if order.status != 'PRONTO_PARA_ENTREGA' or order.payment.status != 'PAGO':
        raise HTTPException(409, 'O pedido precisa estar pago e pronto para entrega.')
    driver = require(db, m.User, driver_id)
    if driver.role != 'ENTREGADOR' or not driver.active:
        raise HTTPException(422, 'O usuário não é um entregador ativo.')
    today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    shift = db.scalar(select(m.Shift).where(m.Shift.driver_id == driver_id, m.Shift.day == today))
    if not shift or not shift.working:
        raise HTTPException(409, 'Entregador sem escala de trabalho para hoje.')
    delivery = m.Delivery(order_id=order.id, driver_id=driver_id)
    db.add(delivery)
    order.status = 'EM_ENTREGA'
    audit(db, actor, 'ENTREGA_ATRIBUIDA', 'order', order.id)
    db.flush()
    return delivery


def authorized_delivery(db, delivery_id, actor, lock=False):
    # Sempre bloqueia pedido antes da entrega, mantendo a mesma ordem de locks.
    delivery = require(db, m.Delivery, delivery_id)
    if actor.role == 'ENTREGADOR' and delivery.driver_id != actor.id:
        raise HTTPException(404, 'Entrega não encontrada.')
    if lock:
        order_locked(db, delivery.order_id)
        db.refresh(delivery, with_for_update=True)
    return delivery


def finish_delivery(db, delivery_id, result, actor):
    delivery = authorized_delivery(db, delivery_id, actor, lock=True)
    order = require(db, m.Order, delivery.order_id)
    if delivery.result:
        if delivery.result == result:
            return delivery
        raise HTTPException(409, 'A entrega já foi encerrada com outro resultado.')
    if order.status != 'EM_ENTREGA':
        raise HTTPException(409, 'A entrega não está em andamento.')
    delivery.result = result
    delivery.ended_at = m.now()
    order.status = result
    if result in ('AUSENTE', 'NAO_ENTREGUE'):
        payment = order.payment
        # Adaptador mock: sucesso imediato e referência determinística. Sem dinheiro real.
        reference = f'mock-refund-{payment.id}'
        db.add(m.Refund(payment_id=payment.id, amount=payment.amount, reference=reference))
        payment.status = 'ESTORNADO'
        descriptions = []
        for item in order.items:
            flavors = ', '.join(f'{x.balls} bola(s) de {require(db, m.Inventory, x.inventory_id).name}'
                                for x in item.flavors)
            descriptions.append(f'{item.quantity} porção(ões) de {item.balls} bola(s): {flavors}')
        db.add(m.DonationItem(order_id=order.id, description='; '.join(descriptions),
                              status='AGUARDANDO_RETORNO'))
        audit(db, actor, 'ESTORNO_MOCK_CONFIRMADO', 'order', order.id)
    audit(db, actor, 'ENTREGA_' + result, 'delivery', delivery.id)
    db.flush()
    return delivery


def help_delivery(db, delivery_id, data, actor):
    delivery = authorized_delivery(db, delivery_id, actor, lock=True)
    if delivery.result:
        raise HTTPException(409, 'A entrega já está encerrada.')
    incident = m.Incident(delivery_id=delivery.id, kind=data.kind, description=data.description)
    db.add(incident)
    audit(db, actor, 'AJUDA_' + data.kind, 'delivery', delivery.id)
    db.flush()
    return incident


def receive_return(db, item_id, data, actor):
    item = require(db, m.DonationItem, item_id, lock=True)
    target = 'DISPONIVEL' if data.suitable else 'DESCARTADO'
    if item.status != 'AGUARDANDO_RETORNO':
        if item.status == target and item.condition == data.condition:
            return item
        raise HTTPException(409, 'O retorno já foi registrado.')
    item.status = target
    item.condition = data.condition
    item.received_at = m.now()
    audit(db, actor, 'RETORNO_' + target, 'donation_item', item.id)
    return item


def donate(db, data, actor):
    items = [require(db, m.DonationItem, key, lock=True) for key in sorted(data.item_ids)]
    if any(item.status != 'DISPONIVEL' for item in items):
        raise HTTPException(409, 'Somente produtos retornados e disponíveis podem ser doados.')
    donation = m.Donation(actor_id=actor.id, destination=data.destination)
    db.add(donation)
    db.flush()
    for item in items:
        item.status = 'DOADO'
        item.donation_id = donation.id
    audit(db, actor, 'DOACAO_REGISTRADA', 'donation', donation.id)
    return donation


def order_view(order, role):
    result = {'id': order.id, 'canalPedido': order.channel.name, 'external_id': order.external_id,
              'status': order.status, 'financial_status': order.payment.status,
              'total': str(order.total), 'created_at': order.created_at,
              'items': [{'id': x.id, 'balls': x.balls, 'quantity': x.quantity,
                         'unit_price': str(x.unit_price),
                         'flavors': [{'inventory_id': f.inventory_id, 'balls': f.balls} for f in x.flavors],
                         'packages': [{'inventory_id': p.inventory_id, 'quantity': p.quantity} for p in x.packages]}
                        for x in order.items]}
    if role in ('ADMIN', 'ATENDENTE', 'ENTREGADOR'):
        result['customer'] = {'name': order.customer.name, 'contact': order.customer.contact}
        result['address'] = order.address
    if order.delivery:
        result['delivery'] = {'id': order.delivery.id, 'driver_id': order.delivery.driver_id,
                              'result': order.delivery.result}
    return result
