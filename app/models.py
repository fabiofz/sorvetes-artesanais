from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey,
                        Integer, JSON, Numeric, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    relief: Mapped[bool] = mapped_column(Boolean, default=False)

class Shift(Base):
    __tablename__ = 'shifts'
    __table_args__ = (UniqueConstraint('driver_id', 'day'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    day: Mapped[datetime] = mapped_column(Date)
    working: Mapped[bool] = mapped_column(Boolean)

class Channel(Base):
    __tablename__ = 'channels'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    prepaid: Mapped[bool] = mapped_column(Boolean)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Offer(Base):
    __tablename__ = 'offers'
    __table_args__ = (CheckConstraint('balls IN (1, 3, 6)'), CheckConstraint('price > 0'))
    id: Mapped[int] = mapped_column(primary_key=True)
    balls: Mapped[int] = mapped_column(Integer, unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

class Inventory(Base):
    __tablename__ = 'inventory'
    __table_args__ = (CheckConstraint('balance >= 0'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(20))
    unit: Mapped[str] = mapped_column(String(10))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)

class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(40))

class Order(Base):
    __tablename__ = 'orders'
    __table_args__ = (UniqueConstraint('channel_id', 'external_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'))
    channel_id: Mapped[int] = mapped_column(ForeignKey('channels.id'))
    external_id: Mapped[str] = mapped_column(String(100))
    payload_hash: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(String(300))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(30), default='RECEBIDO')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    customer: Mapped[Customer] = relationship()
    channel: Mapped[Channel] = relationship()
    items: Mapped[list['OrderItem']] = relationship(cascade='all, delete-orphan')
    payment: Mapped['Payment'] = relationship(uselist=False)
    delivery: Mapped['Delivery | None'] = relationship(uselist=False)

class OrderItem(Base):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'))
    offer_id: Mapped[int] = mapped_column(ForeignKey('offers.id'))
    balls: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    flavors: Mapped[list['FlavorItem']] = relationship(cascade='all, delete-orphan')
    packages: Mapped[list['PackageUse']] = relationship(cascade='all, delete-orphan')

class FlavorItem(Base):
    __tablename__ = 'flavor_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('order_items.id'))
    inventory_id: Mapped[int] = mapped_column(ForeignKey('inventory.id'))
    balls: Mapped[int] = mapped_column(Integer)

class PackageUse(Base):
    __tablename__ = 'package_uses'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('order_items.id'))
    inventory_id: Mapped[int] = mapped_column(ForeignKey('inventory.id'))
    quantity: Mapped[int] = mapped_column(Integer)

class Movement(Base):
    __tablename__ = 'movements'
    __table_args__ = (UniqueConstraint('order_id', 'inventory_id', 'kind'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey('inventory.id'))
    order_id: Mapped[int | None] = mapped_column(ForeignKey('orders.id'))
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    reason: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Payment(Base):
    __tablename__ = 'payments'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    method: Mapped[str] = mapped_column(String(30))
    processor: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default='PENDENTE')
    reference: Mapped[str | None] = mapped_column(String(120))

class Refund(Base):
    __tablename__ = 'refunds'
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey('payments.id'), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    reference: Mapped[str] = mapped_column(String(120), unique=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Delivery(Base):
    __tablename__ = 'deliveries'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), unique=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    result: Mapped[str | None] = mapped_column(String(20))
    departed_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)

class Incident(Base):
    __tablename__ = 'incidents'
    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey('deliveries.id'))
    kind: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(500), default='')
    status: Mapped[str] = mapped_column(String(20), default='ABERTA')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Donation(Base):
    __tablename__ = 'donations'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    destination: Mapped[str] = mapped_column(String(200))
    donated_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class DonationItem(Base):
    __tablename__ = 'donation_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), unique=True)
    donation_id: Mapped[int | None] = mapped_column(ForeignKey('donations.id'))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default='AGUARDANDO_RETORNO')
    condition: Mapped[str | None] = mapped_column(String(200))
    received_at: Mapped[datetime | None] = mapped_column(DateTime)

class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
