"""Comandos locais: init-db, create-admin e seed-demo."""
import argparse
from getpass import getpass
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import Base, engine
from app import models as m
from app.security import passwords

def init_db():
    # Migração inicial não destrutiva: somente cria tabelas ausentes.
    Base.metadata.create_all(engine())
    print('Esquema inicial criado. Nenhuma tabela foi apagada.')

def create_admin():
    username = input('Login do administrador: ').strip()
    name = input('Nome: ').strip()
    password = getpass('Senha (mínimo de 4 caracteres): ')
    if len(password) < 4 or len(username) < 3 or not name:
        raise SystemExit('Dados inválidos. Nada foi gravado.')
    if getpass('Confirme a senha: ') != password:
        raise SystemExit('As senhas não coincidem.')
    with Session(engine()) as db, db.begin():
        if db.scalar(select(m.User).where(m.User.username == username)):
            raise SystemExit('Login já cadastrado.')
        db.add(m.User(username=username, name=name, password_hash=passwords.hash(password), role='ADMIN'))
    print('Administrador criado. A senha não foi exibida nem armazenada em texto puro.')

def seed_demo():
    with Session(engine()) as db, db.begin():
        for name, prepaid in [('WHATSAPP', False), ('TELEFONE', False), ('IFOOD', True), ('99FOOD', True), ('KEETA', True)]:
            if not db.scalar(select(m.Channel).where(m.Channel.name == name)):
                db.add(m.Channel(name=name, prepaid=prepaid))
        for balls, price in [(1, '8.00'), (3, '20.00'), (6, '36.00')]:
            if not db.scalar(select(m.Offer).where(m.Offer.balls == balls)):
                db.add(m.Offer(balls=balls, price=Decimal(price)))
        for name, category in [('Chocolate', 'SORVETE'), ('Morango', 'SORVETE'),
                               ('Caixinha', 'EMBALAGEM'), ('Cestinha', 'EMBALAGEM'),
                               ('Cobertura de chocolate', 'COBERTURA')]:
            if not db.scalar(select(m.Inventory).where(m.Inventory.name == name)):
                db.add(m.Inventory(name=name, category=category, unit='G' if category == 'SORVETE' else 'UN', balance=0))
    print('Dados demonstrativos criados sem alterar cadastros existentes.')
    print('Preços são exemplos. Estoques começam zerados; registre entradas antes de vender.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['init-db', 'create-admin', 'seed-demo'])
    args = parser.parse_args()
    {'init-db': init_db, 'create-admin': create_admin, 'seed-demo': seed_demo}[args.command]()
