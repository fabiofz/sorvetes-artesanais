"""Cenário fictício reproduzível em banco vazio, sem integrações externas."""
import argparse
from datetime import datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import secrets
from uuid import uuid4
from zoneinfo import ZoneInfo


def run_demo(database_url=None):
    os.environ.setdefault('DATABASE_URL', 'sqlite://')
    os.environ.setdefault('JWT_SECRET', secrets.token_hex(32))
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, inspect, select, func, text, event
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db import Base, get_db
    from app.main import app
    from app import models as m
    from app.security import passwords

    if database_url:
        url = make_url(database_url)
        if url.get_backend_name() != 'mysql' or not (url.database or '').endswith('_test'):
            raise ValueError('Use um banco MySQL vazio e descartável terminado em _test.')
        engine = create_engine(database_url, pool_pre_ping=True)
        backend = 'MySQL'
    else:
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        @event.listens_for(engine, 'connect')
        def sqlite_fk(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        backend = 'SQLite em memória'
    if inspect(engine).get_table_names():
        engine.dispose()
        raise ValueError('O banco precisa estar vazio. Nenhuma tabela foi alterada.')
    Session = sessionmaker(engine, expire_on_commit=False)
    report = {'scenario': 'Pedido iFood fictício, cliente ausente, estorno mock e doação',
              'executed_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
              'database': backend, 'external_integrations': 'mock', 'real_money_moved': False,
              'steps': [], 'checks': {},
              'note': 'Doação fictícia registrada na data da execução; não representa doação física ou agendamento de sexta-feira.'}
    previous = app.dependency_overrides.get(get_db)
    created = False
    try:
        created = True
        Base.metadata.create_all(engine)
        def override():
            with Session() as db:
                try:
                    yield db
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
        app.dependency_overrides[get_db] = override
        password = secrets.token_urlsafe(24)
        with Session() as db, db.begin():
            if backend == 'MySQL': report['database_version'] = db.scalar(text('SELECT VERSION()'))
            hashed = passwords.hash(password)
            admin = m.User(username='demo_admin', name='Administrador fictício', password_hash=hashed, role='ADMIN')
            driver = m.User(username='demo_driver', name='Entregador fictício', password_hash=hashed, role='ENTREGADOR')
            db.add_all([admin, driver]); db.flush(); driver_id = driver.id
            db.add(m.Shift(driver_id=driver.id, day=datetime.now(ZoneInfo('America/Sao_Paulo')).date(), working=True))
            db.add(m.Channel(name='IFOOD', prepaid=True))
            offer = m.Offer(balls=3, price=Decimal('20.00'))
            stocks = [m.Inventory(name=name, category=category, unit=unit, balance=balance) for name,category,unit,balance in [
                ('Chocolate','SORVETE','G',1000),('Morango','SORVETE','G',1000),
                ('Caixinha','EMBALAGEM','UN',20),('Cobertura','COBERTURA','UN',2)]]
            db.add_all([offer,*stocks]);db.flush();offer_id=offer.id;ids=[x.id for x in stocks]
        def snapshot():
            with Session() as db:
                return {x.name:{'balance':str(x.balance),'unit':x.unit} for x in db.scalars(select(m.Inventory).order_by(m.Inventory.id))}
        report['stock_before']=snapshot()
        with TestClient(app) as client:
            def login(name):
                response=client.post('/auth/token',data={'username':name,'password':password})
                if response.status_code!=200: raise RuntimeError('Falha no login fictício.')
                return {'Authorization':'Bearer '+response.json()['access_token']}
            admin_headers=login('demo_admin');driver_headers=login('demo_driver')
            report['steps'].append({'name':'Login JWT dos usuários fictícios','http_status':200,'result':'Administrador e entregador autenticados. Tokens omitidos.'})
            def call(name,method,route,expected,payload=None,driver=False):
                kwargs={'headers':driver_headers if driver else admin_headers}
                if payload is not None:kwargs['json']=payload
                response=client.request(method,route,**kwargs)
                if response.status_code!=expected:raise RuntimeError(f'{name}: HTTP esperado {expected}; recebido {response.status_code}.')
                result=response.json()
                report['steps'].append({'name':name,'method':method,'route':route,'http_status':response.status_code,'request':payload,'response':result})
                return result
            data={'canalPedido':'IFOOD','external_id':'demo-'+uuid4().hex,'customer_name':'Cliente fictício','customer_contact':'000000000',
                'address':'Rua demonstrativa, 10','payment_method':'PLATAFORMA','already_paid':True,
                'items':[{'offer_id':offer_id,'quantity':1,'flavors':[{'inventory_id':ids[0],'balls':2},{'inventory_id':ids[1],'balls':1}],
                          'packages':[{'inventory_id':ids[2],'quantity':1}]}]}
            order=call('Receber pedido iFood fictício já pago','POST','/orders',201,data);order_id=order['id']
            assert order['financial_status']=='PAGO'
            duplicate=call('Reenviar pedido sem duplicar','POST','/orders',200,data)
            report['stock_after_payment']=snapshot()
            for status in ['EM_PREPARACAO','PRONTO_PARA_ENTREGA']:
                call('Atualizar para '+status,'PATCH',f'/orders/{order_id}/status',200,{'status':status})
            delivery=call('Atribuir entregador escalado','POST',f'/orders/{order_id}/delivery',201,{'driver_id':driver_id});delivery_id=delivery['id']
            result=call('Cliente ausente e estorno mock','POST',f'/deliveries/{delivery_id}/result',200,{'result':'AUSENTE'},driver=True)
            assert result['financial_status']=='ESTORNADO'
            call('Repetir resultado sem novo estorno','POST',f'/deliveries/{delivery_id}/result',200,{'result':'AUSENTE'},driver=True)
            returned=call('Consultar retorno pendente','GET','/donations/items',200)[0];item_id=returned['id']
            assert returned['status']=='AGUARDANDO_RETORNO'
            confirmed=call('Confirmar retorno físico fictício','POST',f'/donations/items/{item_id}/return',200,
                           {'suitable':True,'condition':'Condição aprovada apenas para este cenário fictício'})
            assert confirmed['status']=='DISPONIVEL'
            call('Registrar destinação fictícia à doação','POST','/donations',201,{'item_ids':[item_id],'destination':'Ação social fictícia - demonstração'})
            final=call('Conferir pedido final','GET',f'/orders/{order_id}',200)
        report['stock_after_donation']=snapshot()
        with Session() as db:
            refund_count=db.scalar(select(func.count()).select_from(m.Refund))
            movement_count=db.scalar(select(func.count()).select_from(m.Movement))
            item=db.get(m.DonationItem,item_id)
            donation_status=item.status
            report['final_state']={'order_id':order_id,'order_status':final['status'],'financial_status':final['financial_status'],
                'refund_count':refund_count,'refund_value':str(db.scalar(select(m.Refund)).amount),
                'stock_movement_count':movement_count,'donation_status':donation_status}
        paid=report['stock_after_payment']
        report['checks']={'pedido_nao_duplicado':duplicate['id']==order_id,
            'chocolate_baixa_120g':Decimal(paid['Chocolate']['balance'])==880,
            'morango_baixa_60g':Decimal(paid['Morango']['balance'])==940,
            'caixinha_baixa_uma_unidade':Decimal(paid['Caixinha']['balance'])==19,
            'cobertura_sem_baixa_automatica':Decimal(paid['Cobertura']['balance'])==2,
            'baixa_unica':movement_count==3,'estorno_mock_unico':refund_count==1,
            'pagamento_estornado':final['financial_status']=='ESTORNADO',
            'retorno_sem_repor_estoque_venda':report['stock_after_donation']==paid,
            'doacao_ficticia_registrada':donation_status=='DOADO'}
        assert all(report['checks'].values()),report['checks']
        report['result']='APROVADO'
        return report
    finally:
        if previous is None:app.dependency_overrides.pop(get_db,None)
        else:app.dependency_overrides[get_db]=previous
        if created:Base.metadata.drop_all(engine)
        engine.dispose()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='docs/demo-resultados.json')
    args=parser.parse_args()
    report=run_demo(os.environ.get('DEMO_DATABASE_URL'))
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Demonstração {report['result']} em {report['database']}: {len(report['checks'])} verificações aprovadas.")
    print('Evidência:',target)

if __name__=='__main__':main()
