from datetime import datetime, timedelta, timezone
from decimal import Decimal
import jwt
from sqlalchemy import select, func
from app import models as m
from app.config import settings


def create(setup, body):
    c, h, _, _ = setup
    r = c.post('/orders', json=body, headers=h['atendente'])
    assert r.status_code == 201, r.text
    return r.json()['id']


def dispatch(setup, body):
    c, h, users, _ = setup
    id = create(setup, body)
    assert c.post(f'/orders/{id}/payment/mock', json={'approved': True}, headers=h['atendente']).status_code == 200
    for status in ['EM_PREPARACAO', 'PRONTO_PARA_ENTREGA']:
        r = c.patch(f'/orders/{id}/status', json={'status': status}, headers=h['producao'])
        assert r.status_code == 200, r.text
    r = c.post(f'/orders/{id}/delivery', json={'driver_id': users['entregador']}, headers=h['atendente'])
    assert r.status_code == 201, r.text
    return id, r.json()['id']


def test_login_and_hash(setup):
    c, h, _, Session = setup
    r = c.get('/auth/me', headers=h['admin'])
    assert r.json()['role'] == 'ADMIN'
    with Session() as db:
        user = db.scalar(select(m.User).where(m.User.username == 'admin'))
        assert user.password_hash.startswith('$argon2')
    assert 'password_hash' not in c.get('/users', headers=h['admin']).text


def test_order_payment_debits_once(setup, order_body):
    c, h, _, Session = setup
    id = create(setup, order_body)
    with Session() as db: assert db.get(m.Inventory, 1).balance == 1000
    for _ in range(2):
        r = c.post(f'/orders/{id}/payment/mock', json={'approved': True}, headers=h['atendente'])
        assert r.status_code == 200 and r.json()['order']['financial_status'] == 'PAGO'
    with Session() as db:
        assert db.get(m.Inventory, 1).balance == 880
        assert db.get(m.Inventory, 2).balance == 940
        assert db.get(m.Inventory, 3).balance == 19
        assert db.get(m.Inventory, 4).balance == 2
        assert db.scalar(select(func.count()).select_from(m.Movement)) == 3


def test_marketplace_prepaid_and_idempotent(setup, order_body):
    c, h, _, Session = setup
    order_body.update(canalPedido='IFOOD', already_paid=True, payment_method='PLATAFORMA')
    id = create(setup, order_body)
    r = c.post('/orders', json=order_body, headers=h['atendente'])
    assert r.status_code == 200 and r.json()['id'] == id
    assert r.json()['financial_status'] == 'PAGO'
    assert len(c.get('/orders?canalPedido=IFOOD', headers=h['atendente']).json()) == 1
    assert c.get('/orders?canalPedido=TELEFONE', headers=h['atendente']).json() == []
    with Session() as db: assert db.get(m.Inventory, 1).balance == 880


def test_successful_delivery(setup, order_body):
    c, h, _, Session = setup
    order_id, delivery_id = dispatch(setup, order_body)
    r = c.post(f'/deliveries/{delivery_id}/result', json={'result': 'ENTREGUE'}, headers=h['entregador'])
    assert r.json()['result'] == 'ENTREGUE'
    assert r.json()['financial_status'] == 'PAGO'
    with Session() as db: assert db.scalar(select(func.count()).select_from(m.Refund)) == 0


def test_help_does_not_close_delivery(setup, order_body):
    c, h, _, Session = setup
    order_id, delivery_id = dispatch(setup, order_body)
    for kind in ['ACIDENTE', 'CONTESTACAO']:
        r = c.post(f'/deliveries/{delivery_id}/help', json={'kind': kind}, headers=h['entregador'])
        assert r.status_code == 201
    assert len(c.get('/incidents', headers=h['atendente']).json()) == 2
    with Session() as db:
        assert db.get(m.Order, order_id).status == 'EM_ENTREGA'
        assert db.get(m.Delivery, delivery_id).result is None


def test_absent_refund_return_donation(setup, order_body):
    c, h, _, Session = setup
    order_id, delivery_id = dispatch(setup, order_body)
    for _ in range(2):
        r = c.post(f'/deliveries/{delivery_id}/result', json={'result': 'AUSENTE'}, headers=h['entregador'])
        assert r.status_code == 200 and r.json()['financial_status'] == 'ESTORNADO'
    item = c.get('/donations/items', headers=h['atendente']).json()[0]
    assert item['status'] == 'AGUARDANDO_RETORNO'
    r = c.post(f"/donations/items/{item['id']}/return", json={'suitable': True, 'condition': 'Retorno conferido'}, headers=h['atendente'])
    assert r.json()['status'] == 'DISPONIVEL'
    r = c.post('/donations', json={'item_ids': [item['id']], 'destination': 'Ação de sexta-feira'}, headers=h['atendente'])
    assert r.status_code == 201
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(m.Refund)) == 1
        assert db.get(m.Inventory, 1).balance == 880
        assert db.get(m.DonationItem, item['id']).status == 'DOADO'


def test_denied_payment_keeps_stock(setup, order_body):
    c, h, _, Session = setup
    id = create(setup, order_body)
    r = c.post(f'/orders/{id}/payment/mock', json={'approved': False}, headers=h['atendente'])
    assert r.status_code == 200 and r.json()['approved'] is False
    assert r.json()['order']['financial_status'] == 'PENDENTE'
    with Session() as db: assert db.get(m.Inventory, 1).balance == 1000


def test_unauthenticated_and_wrong_password(setup):
    c, _, _, _ = setup
    assert c.get('/orders').status_code == 401
    r = c.post('/auth/token', data={'username': 'admin', 'password': 'errada'})
    assert r.status_code == 401
    assert 'password' not in r.text


def test_role_and_driver_isolation(setup, order_body):
    c, h, _, _ = setup
    assert c.post('/inventory', json={'name': 'Teste', 'category': 'SORVETE'}, headers=h['entregador']).status_code == 403
    order_id, delivery_id = dispatch(setup, order_body)
    assert c.get('/orders', headers=h['entregador']).status_code == 403
    assert c.get('/deliveries/mine', headers=h['outro']).json() == []
    assert c.post(f'/deliveries/{delivery_id}/result', json={'result': 'ENTREGUE'}, headers=h['outro']).status_code == 404
    production = c.get(f'/orders/{order_id}', headers=h['producao']).json()
    assert 'address' not in production and 'customer' not in production


def test_missing_channel_invalid_balls(setup, order_body):
    c, h, _, _ = setup
    body = dict(order_body); del body['canalPedido']
    assert c.post('/orders', json=body, headers=h['atendente']).status_code == 422
    order_body['items'][0]['flavors'][0]['balls'] = 1
    assert c.post('/orders', json=order_body, headers=h['atendente']).status_code == 422


def test_insufficient_stock_rolls_back_all_items(setup, order_body):
    c, h, _, Session = setup
    with Session() as db, db.begin(): db.get(m.Inventory, 2).balance = 10
    id = create(setup, order_body)
    r = c.post(f'/orders/{id}/payment/mock', json={'approved': True}, headers=h['atendente'])
    assert r.status_code == 409
    with Session() as db:
        assert db.get(m.Inventory, 1).balance == 1000
        assert db.get(m.Inventory, 3).balance == 20
        assert db.get(m.Order, id).payment.status == 'PENDENTE'
        assert db.scalar(select(func.count()).select_from(m.Movement)) == 0


def test_prepaid_order_rollback_and_payload_conflict(setup, order_body):
    c, h, _, Session = setup
    id = create(setup, order_body)
    order_body['address'] = 'Outro endereço, 99'
    assert c.post('/orders', json=order_body, headers=h['atendente']).status_code == 409
    order_body.update(canalPedido='IFOOD', already_paid=True, payment_method='PLATAFORMA', external_id='nova')
    with Session() as db, db.begin(): db.get(m.Inventory, 3).balance = 0
    assert c.post('/orders', json=order_body, headers=h['atendente']).status_code == 409
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(m.Order)) == 1
        assert db.get(m.Inventory, 1).balance == 1000


def test_invalid_status_and_unavailable_driver(setup, order_body):
    c, h, users, _ = setup
    id = create(setup, order_body)
    assert c.patch(f'/orders/{id}/status', json={'status': 'EM_PREPARACAO'}, headers=h['producao']).status_code == 409
    c.post(f'/orders/{id}/payment/mock', json={'approved': True}, headers=h['atendente'])
    c.patch(f'/orders/{id}/status', json={'status': 'EM_PREPARACAO'}, headers=h['producao'])
    c.patch(f'/orders/{id}/status', json={'status': 'PRONTO_PARA_ENTREGA'}, headers=h['producao'])
    assert c.post(f'/orders/{id}/delivery', json={'driver_id': users['outro']}, headers=h['atendente']).status_code == 409


def test_return_must_precede_donation_and_discard(setup, order_body):
    c, h, _, Session = setup
    _, delivery_id = dispatch(setup, order_body)
    c.post(f'/deliveries/{delivery_id}/result', json={'result': 'NAO_ENTREGUE'}, headers=h['entregador'])
    item = c.get('/donations/items', headers=h['atendente']).json()[0]
    data = {'item_ids': [item['id']], 'destination': 'Ação social'}
    assert c.post('/donations', json=data, headers=h['atendente']).status_code == 409
    c.post(f"/donations/items/{item['id']}/return", json={'suitable': False, 'condition': 'Produto impróprio'}, headers=h['atendente'])
    assert c.post('/donations', json=data, headers=h['atendente']).status_code == 409


def test_expired_and_wrongly_signed_jwt(setup):
    c, _, _, _ = setup
    now = datetime.now(timezone.utc)
    payload = {'sub': '1', 'iss': 'segredo-gelado', 'aud': 'segredo-api', 'iat': now - timedelta(hours=2), 'exp': now - timedelta(hours=1)}
    token = jwt.encode(payload, settings().jwt_secret, algorithm='HS256')
    assert c.get('/auth/me', headers={'Authorization': 'Bearer '+token}).status_code == 401
    payload['exp'] = now + timedelta(minutes=10)
    token = jwt.encode(payload, 'wrong-secret-key-at-least-thirty-two-chars', algorithm='HS256')
    assert c.get('/auth/me', headers={'Authorization': 'Bearer '+token}).status_code == 401


def test_new_channel_and_manual_topping_control(setup):
    c, h, _, _ = setup
    assert c.post('/channels', json={'name': 'NOVA_PLATAFORMA', 'prepaid': True}, headers=h['admin']).status_code == 201
    assert c.post('/inventory/4/adjustments', json={'quantity': -1, 'reason': 'Embalagem acabou'}, headers=h['admin']).status_code == 200
    assert c.post('/inventory/4/adjustments', json={'quantity': '0.5', 'reason': 'Inválido'}, headers=h['admin']).status_code == 422
