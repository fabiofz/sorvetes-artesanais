import os
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('JWT_SECRET', 'test-only-secret-not-for-production-0123456789')
from app.db import Base, get_db
from app.main import app
from app import models as m
from app.security import passwords

@pytest.fixture
def setup():
    # TEST_MYSQL_URL só pode apontar para um banco descartável cujo nome termine em _test.
    url = os.environ.get('TEST_MYSQL_URL')
    if url:
        from sqlalchemy.engine import make_url
        assert (make_url(url).database or '').endswith('_test'), 'Use um banco descartável terminado em _test.'
        engine = create_engine(url)
    else:
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        from sqlalchemy import event
        @event.listens_for(engine, 'connect')
        def fk(conn, _): conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)
    def override():
        with Session() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
    app.dependency_overrides[get_db] = override
    password = 'TesteSeguro123!'
    with Session() as db, db.begin():
        users = {}
        hashed = passwords.hash(password)
        for username, role in [('admin', 'ADMIN'), ('atendente', 'ATENDENTE'), ('producao', 'PRODUCAO'),
                               ('entregador', 'ENTREGADOR'), ('outro', 'ENTREGADOR')]:
            row = m.User(username=username, name=username, password_hash=hashed, role=role)
            db.add(row); db.flush(); users[username] = row.id
        for name, prepaid in [('WHATSAPP', False), ('TELEFONE', False), ('IFOOD', True), ('99FOOD', True), ('KEETA', True)]:
            db.add(m.Channel(name=name, prepaid=prepaid))
        db.add(m.Offer(id=1, balls=3, price=Decimal('20.00')))
        for id, name, category, unit, balance in [(1, 'Chocolate', 'SORVETE', 'G', 1000),
                (2, 'Morango', 'SORVETE', 'G', 1000), (3, 'Caixinha', 'EMBALAGEM', 'UN', 20),
                (4, 'Cobertura', 'COBERTURA', 'UN', 2)]:
            db.add(m.Inventory(id=id, name=name, category=category, unit=unit, balance=balance))
        db.add(m.Shift(driver_id=users['entregador'], day=datetime.now(ZoneInfo('America/Sao_Paulo')).date(), working=True))
    with TestClient(app) as client:
        headers = {}
        for name in users:
            response = client.post('/auth/token', data={'username': name, 'password': password})
            assert response.status_code == 200, response.text
            headers[name] = {'Authorization': 'Bearer ' + response.json()['access_token']}
        yield client, headers, users, Session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture
def order_body():
    return {'canalPedido': 'WHATSAPP', 'external_id': 'pedido-001', 'customer_name': 'Cliente teste',
            'customer_contact': '000000000', 'address': 'Rua fictícia, 10', 'payment_method': 'PIX',
            'already_paid': False, 'items': [{'offer_id': 1, 'quantity': 1,
            'flavors': [{'inventory_id': 1, 'balls': 2}, {'inventory_id': 2, 'balls': 1}],
            'packages': [{'inventory_id': 3, 'quantity': 1}]}]}
