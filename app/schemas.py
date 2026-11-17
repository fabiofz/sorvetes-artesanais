from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

Role = Literal['ADMIN', 'ATENDENTE', 'PRODUCAO', 'ENTREGADOR']

class NewUser(Input):
    username: str = Field(min_length=3, max_length=80, pattern=r'^[a-zA-Z0-9_.-]+$')
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=4, max_length=128)
    role: Role
    relief: bool = False

class NewStock(Input):
    name: str = Field(min_length=2, max_length=100)
    category: Literal['SORVETE', 'EMBALAGEM', 'COBERTURA']

class StockAdjustment(Input):
    quantity: Decimal = Field(max_digits=12, decimal_places=3)
    reason: str = Field(min_length=3, max_length=200)

    @field_validator('quantity')
    @classmethod
    def nonzero(cls, value):
        if value == 0:
            raise ValueError('Informe uma entrada ou saída diferente de zero.')
        return value

class OfferInput(Input):
    balls: Literal[1, 3, 6]
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

class ChannelInput(Input):
    name: str = Field(min_length=2, max_length=40, pattern=r'^[A-Z0-9_]+$')
    prepaid: bool

class FlavorInput(Input):
    inventory_id: int = Field(gt=0)
    balls: int = Field(ge=1, le=6)

class PackageInput(Input):
    inventory_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100)

class ItemInput(Input):
    offer_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100)
    flavors: list[FlavorInput] = Field(min_length=1, max_length=6)
    # Quantidade de embalagens para esta linha inteira, não por porção.
    packages: list[PackageInput] = Field(min_length=1, max_length=10)

    @model_validator(mode='after')
    def no_duplicate_inventory(self):
        for entries in (self.flavors, self.packages):
            if len({x.inventory_id for x in entries}) != len(entries):
                raise ValueError('Não repita um sabor ou embalagem na mesma linha.')
        return self

class NewOrder(Input):
    canalPedido: str = Field(min_length=2, max_length=40, pattern=r'^[A-Z0-9_]+$')
    external_id: str = Field(min_length=1, max_length=100)
    customer_name: str = Field(min_length=2, max_length=100)
    customer_contact: str = Field(min_length=3, max_length=40)
    address: str = Field(min_length=5, max_length=300)
    payment_method: Literal['PIX', 'CARTAO', 'DINHEIRO', 'PLATAFORMA']
    already_paid: bool = False
    items: list[ItemInput] = Field(min_length=1, max_length=50)

class PaymentInput(Input):
    approved: bool

class StatusInput(Input):
    status: Literal['EM_PREPARACAO', 'PRONTO_PARA_ENTREGA']

class AssignInput(Input):
    driver_id: int = Field(gt=0)

class ShiftInput(Input):
    driver_id: int = Field(gt=0)
    day: date
    working: bool

class ResultInput(Input):
    result: Literal['ENTREGUE', 'NAO_ENTREGUE', 'AUSENTE']

class HelpInput(Input):
    kind: Literal['CONTESTACAO', 'ACIDENTE']
    description: str = Field(default='', max_length=500)

class ReturnInput(Input):
    suitable: bool
    condition: str = Field(min_length=3, max_length=200)

class DonateInput(Input):
    item_ids: list[int] = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=3, max_length=200)

    @model_validator(mode='after')
    def no_duplicates(self):
        if len(set(self.item_ids)) != len(self.item_ids):
            raise ValueError('Não repita itens na doação.')
        return self

class TokenOut(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class FlavorOut(BaseModel):
    inventory_id: int
    balls: int

class PackageOut(BaseModel):
    inventory_id: int
    quantity: int

class ItemOut(BaseModel):
    id: int
    balls: int
    quantity: int
    unit_price: str
    flavors: list[FlavorOut]
    packages: list[PackageOut]

class CustomerOut(BaseModel):
    name: str
    contact: str

class DeliveryOut(BaseModel):
    id: int
    driver_id: int
    result: str | None = None

class OrderOut(BaseModel):
    id: int
    canalPedido: str
    external_id: str
    status: str
    financial_status: str
    total: str
    created_at: datetime
    items: list[ItemOut]
    customer: CustomerOut | None = None
    address: str | None = None
    delivery: DeliveryOut | None = None

class PaymentOut(BaseModel):
    approved: bool
    mode: str
    order: OrderOut

class DeliveryResultOut(BaseModel):
    id: int
    result: str
    financial_status: str
    payment_mode: str

class ErrorDetail(BaseModel):
    field: str
    issue: str

class ErrorOut(BaseModel):
    error: str
    message: str
    details: list[ErrorDetail]
    timestamp: str
    path: str
    requestId: str | None
