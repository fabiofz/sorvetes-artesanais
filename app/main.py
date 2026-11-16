from datetime import datetime, timezone
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Query, Response, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app import models as m, schemas as s, services as svc
from app.config import settings
from app.db import get_db
from app.security import current_user, roles, passwords, DUMMY_HASH, issue_token

app = FastAPI(title='Segredo Gelado - API', version='0.1.0',
              responses={code: {'model': s.ErrorOut} for code in [401,403,404,409,422,503]},
              description='MVP acadêmico. Pagamentos, estornos e recebimentos externos são simulados. Não movimenta dinheiro real.')
DB = Depends(get_db, scope='function')
ADMIN = Depends(roles('ADMIN'))
STAFF = Depends(roles('ADMIN', 'ATENDENTE'))
TEAM = Depends(roles('ADMIN', 'ATENDENTE', 'PRODUCAO'))

@app.middleware('http')
async def identify_request(request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers['X-Request-ID'] = request.state.request_id
    response.headers['Cache-Control'] = 'no-store'
    return response


def error(request, code, message, details=None, headers=None):
    return JSONResponse(status_code=code, headers=headers, content={
        'error': {401: 'NAO_AUTENTICADO', 403: 'SEM_PERMISSAO', 404: 'NAO_ENCONTRADO',
                  409: 'CONFLITO', 422: 'DADOS_INVALIDOS', 503: 'INDISPONIVEL'}.get(code, 'ERRO'),
        'message': message, 'details': details or [],
        'timestamp': datetime.now(timezone.utc).isoformat(), 'path': request.url.path,
        'requestId': getattr(request.state, 'request_id', None)})

@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    return error(request, exc.status_code, str(exc.detail), headers=exc.headers)

@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # Nunca replica valores recebidos (senhas, contatos, endereços) no erro.
    details = [{'field': '.'.join(map(str, x['loc'])), 'issue': x['type']} for x in exc.errors()]
    return error(request, 422, 'Confira os campos enviados.', details)

@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return error(request, 409, 'Registro duplicado ou referência inconsistente. Consulte o recurso e tente novamente.')

@app.exception_handler(OperationalError)
async def unavailable(request, exc):
    return error(request, 503, 'Banco indisponível ou operação concorrente. Tente novamente.')

@app.get('/health', tags=['Sistema'])
def health():
    return {'status': 'ok', 'payment_mode': settings().payment_mode}

@app.post('/auth/token', tags=['Login'], response_model=s.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db=DB):
    user = db.scalar(select(m.User).where(m.User.username == form.username))
    valid = passwords.verify(form.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        raise HTTPException(401, 'Usuário ou senha inválidos.', headers={'WWW-Authenticate': 'Bearer'})
    svc.audit(db, user, 'LOGIN', 'user', user.id)
    return {'access_token': issue_token(user.id), 'token_type': 'bearer',
            'expires_in': settings().jwt_minutes * 60}

@app.get('/auth/me', tags=['Login'])
def me(user=Depends(current_user)):
    return {'id': user.id, 'name': user.name, 'role': user.role}

@app.post('/users', status_code=201, tags=['Usuários'])
def create_user(data: s.NewUser, db=DB, actor=ADMIN):
    if data.relief and data.role != 'ENTREGADOR':
        raise HTTPException(422, 'Somente entregadores podem ser folguistas.')
    user = m.User(username=data.username, name=data.name, password_hash=passwords.hash(data.password),
                  role=data.role, relief=data.relief)
    db.add(user); db.flush()
    svc.audit(db, actor, 'USUARIO_CRIADO', 'user', user.id)
    return {'id': user.id, 'name': user.name, 'role': user.role, 'relief': user.relief}

@app.get('/users', tags=['Usuários'])
def users(db=DB, actor=ADMIN, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    return [{'id': x.id, 'name': x.name, 'role': x.role, 'active': x.active, 'relief': x.relief}
            for x in db.scalars(select(m.User).order_by(m.User.id).offset(offset).limit(limit))]

@app.put('/shifts', tags=['Entregas'])
def shift(data: s.ShiftInput, db=DB, actor=STAFF):
    driver = svc.require(db, m.User, data.driver_id)
    if driver.role != 'ENTREGADOR' or not driver.active:
        raise HTTPException(422, 'Informe um entregador ativo.')
    row = db.scalar(select(m.Shift).where(m.Shift.driver_id == driver.id, m.Shift.day == data.day).with_for_update())
    if row: row.working = data.working
    else:
        row = m.Shift(**data.model_dump()); db.add(row)
    db.flush(); svc.audit(db, actor, 'ESCALA_ATUALIZADA', 'shift', row.id)
    return {'id': row.id, **data.model_dump()}

@app.get('/shifts', tags=['Entregas'])
def shifts(db=DB, actor=STAFF, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    return [{'id': x.id, 'driver_id': x.driver_id, 'day': x.day, 'working': x.working}
            for x in db.scalars(select(m.Shift).order_by(m.Shift.day.desc()).offset(offset).limit(limit))]

@app.get('/channels', tags=['Canais'])
def channels(db=DB, actor=TEAM):
    return [{'id': x.id, 'name': x.name, 'prepaid': x.prepaid} for x in db.scalars(select(m.Channel))]

@app.post('/channels', status_code=201, tags=['Canais'])
def new_channel(data: s.ChannelInput, db=DB, actor=ADMIN):
    row = m.Channel(**data.model_dump()); db.add(row); db.flush()
    svc.audit(db, actor, 'CANAL_CRIADO', 'channel', row.id)
    return {'id': row.id, **data.model_dump(), 'real_integration': False}

@app.put('/catalog/offers', tags=['Cardápio'])
def offer(data: s.OfferInput, db=DB, actor=ADMIN):
    row = db.scalar(select(m.Offer).where(m.Offer.balls == data.balls).with_for_update())
    if row: row.price = data.price
    else: row = m.Offer(**data.model_dump()); db.add(row)
    db.flush(); svc.audit(db, actor, 'PRECO_ATUALIZADO', 'offer', row.id)
    return {'id': row.id, 'balls': row.balls, 'price': str(row.price)}

@app.get('/catalog/offers', tags=['Cardápio'])
def offers(db=DB, actor=TEAM):
    return [{'id': x.id, 'balls': x.balls, 'price': str(x.price)} for x in db.scalars(select(m.Offer).order_by(m.Offer.balls))]

@app.post('/inventory', status_code=201, tags=['Estoque'])
def create_stock(data: s.NewStock, db=DB, actor=ADMIN):
    row = m.Inventory(**data.model_dump(), unit='G' if data.category == 'SORVETE' else 'UN', balance=0)
    db.add(row); db.flush(); svc.audit(db, actor, 'ESTOQUE_CADASTRADO', 'inventory', row.id)
    return {'id': row.id, 'name': row.name, 'unit': row.unit, 'balance': '0'}

@app.get('/inventory', tags=['Estoque'])
def inventory(db=DB, actor=TEAM, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    return [{'id': x.id, 'name': x.name, 'category': x.category, 'unit': x.unit, 'balance': str(x.balance)}
            for x in db.scalars(select(m.Inventory).order_by(m.Inventory.id).offset(offset).limit(limit))]

@app.post('/inventory/{stock_id}/adjustments', tags=['Estoque'])
def adjust(stock_id: int, data: s.StockAdjustment, db=DB, actor=ADMIN):
    stock = svc.require(db, m.Inventory, stock_id, lock=True)
    svc.balance_change(db, stock, data.quantity, actor, data.reason)
    svc.audit(db, actor, 'ESTOQUE_AJUSTADO', 'inventory', stock.id)
    return {'id': stock.id, 'balance': str(stock.balance)}

@app.get('/inventory/movements', tags=['Estoque'])
def movements(db=DB, actor=STAFF, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    return [{'id': x.id, 'inventory_id': x.inventory_id, 'order_id': x.order_id,
             'quantity': str(x.quantity), 'kind': x.kind, 'reason': x.reason}
            for x in db.scalars(select(m.Movement).order_by(m.Movement.id.desc()).offset(offset).limit(limit))]

@app.post('/orders', tags=['Pedidos'], status_code=201, response_model=s.OrderOut, response_model_exclude_none=True)
def create_order(data: s.NewOrder, response: Response, db=DB, actor=STAFF):
    order, created = svc.create_order(db, data, actor)
    response.status_code = 201 if created else 200
    return svc.order_view(order, actor.role)

@app.get('/orders', tags=['Pedidos'], response_model=list[s.OrderOut], response_model_exclude_none=True)
def orders(db=DB, actor=TEAM, canalPedido: str | None = None,
           offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    query = select(m.Order)
    if canalPedido: query = query.join(m.Channel).where(m.Channel.name == canalPedido)
    query = query.order_by(m.Order.id.desc()).offset(offset).limit(limit)
    return [svc.order_view(x, actor.role) for x in db.scalars(query)]

@app.get('/orders/{order_id}', tags=['Pedidos'], response_model=s.OrderOut, response_model_exclude_none=True)
def get_order(order_id: int, db=DB, actor=TEAM):
    return svc.order_view(svc.require(db, m.Order, order_id), actor.role)

@app.post('/orders/{order_id}/payment/mock', tags=['Pagamento mock'], response_model=s.PaymentOut, response_model_exclude_none=True)
def pay(order_id: int, data: s.PaymentInput, db=DB, actor=STAFF):
    order, approved = svc.pay_order(db, order_id, data.approved, actor)
    return {'approved': approved, 'mode': 'mock', 'order': svc.order_view(order, actor.role)}

@app.patch('/orders/{order_id}/status', tags=['Pedidos'], response_model=s.OrderOut, response_model_exclude_none=True)
def status(order_id: int, data: s.StatusInput, db=DB, actor=TEAM):
    return svc.order_view(svc.change_status(db, order_id, data.status, actor), actor.role)

@app.post('/orders/{order_id}/delivery', status_code=201, tags=['Entregas'])
def assign(order_id: int, data: s.AssignInput, db=DB, actor=STAFF):
    row = svc.assign_delivery(db, order_id, data.driver_id, actor)
    return {'id': row.id, 'order_id': row.order_id, 'driver_id': row.driver_id}

@app.get('/deliveries/mine', tags=['Entregas'], response_model=list[s.OrderOut], response_model_exclude_none=True)
def my_deliveries(db=DB, actor=Depends(roles('ENTREGADOR')),
                  offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    query = select(m.Order).join(m.Delivery).where(m.Delivery.driver_id == actor.id).order_by(m.Order.id.desc()).offset(offset).limit(limit)
    return [svc.order_view(x, actor.role) for x in db.scalars(query)]

@app.post('/deliveries/{delivery_id}/result', tags=['Entregas'], response_model=s.DeliveryResultOut)
def result(delivery_id: int, data: s.ResultInput, db=DB, actor=Depends(roles('ENTREGADOR'))):
    row = svc.finish_delivery(db, delivery_id, data.result, actor)
    order = svc.require(db, m.Order, row.order_id)
    return {'id': row.id, 'result': row.result, 'financial_status': order.payment.status, 'payment_mode': 'mock'}

@app.post('/deliveries/{delivery_id}/help', status_code=201, tags=['Ocorrências'])
def help_request(delivery_id: int, data: s.HelpInput, db=DB, actor=Depends(roles('ENTREGADOR'))):
    row = svc.help_delivery(db, delivery_id, data, actor)
    return {'id': row.id, 'kind': row.kind, 'status': row.status}

@app.get('/incidents', tags=['Ocorrências'])
def incidents(db=DB, actor=STAFF, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    return [{'id': x.id, 'delivery_id': x.delivery_id, 'kind': x.kind,
             'description': x.description, 'status': x.status, 'created_at': x.created_at}
            for x in db.scalars(select(m.Incident).order_by(m.Incident.id.desc()).offset(offset).limit(limit))]

@app.get('/donations/items', tags=['Doações'])
def donation_items(db=DB, actor=STAFF, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    return [{'id': x.id, 'order_id': x.order_id, 'description': x.description,
             'status': x.status, 'condition': x.condition, 'received_at': x.received_at}
            for x in db.scalars(select(m.DonationItem).order_by(m.DonationItem.id).offset(offset).limit(limit))]

@app.post('/donations/items/{item_id}/return', tags=['Doações'])
def receive(item_id: int, data: s.ReturnInput, db=DB, actor=STAFF):
    row = svc.receive_return(db, item_id, data, actor)
    return {'id': row.id, 'status': row.status}

@app.post('/donations', status_code=201, tags=['Doações'])
def donate(data: s.DonateInput, db=DB, actor=STAFF):
    row = svc.donate(db, data, actor)
    return {'id': row.id, 'item_ids': data.item_ids, 'destination': row.destination, 'donated_at': row.donated_at}

@app.get('/audit', tags=['Auditoria'])
def audit_log(db=DB, actor=ADMIN, offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    return [{'id': x.id, 'actor_id': x.actor_id, 'action': x.action,
             'entity': x.entity, 'entity_id': x.entity_id, 'created_at': x.created_at}
            for x in db.scalars(select(m.Audit).order_by(m.Audit.id.desc()).offset(offset).limit(limit))]
