from flask_sqlalchemy import SQLAlchemy
import enum
from datetime import datetime

db = SQLAlchemy()


class Role(enum.Enum):
    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'

class CounterpartyType(enum.Enum):
    LLC = 'ООО'
    IP = 'ИП'

class PropertyObjectTypeEnum(enum.Enum):
    LED_SCREEN = 'LED-экран'
    PAVILION = 'Павильон'
    SHIELD = 'Щит'
    BOX = 'Короб'
    BANNER = 'Баннер'
    SIGNBOARD = 'Вывеска'
    INTERIOR = 'Интерьерная реклама'
    OTHER = 'Другое'

class ServiceTypeEnum(enum.Enum):
    PLACEMENT = 'Размещение'
    DESIGN = 'Дизайн'
    INSTALLATION = 'Монтаж'
    DISMANTLING = 'Демонтаж'
    MANUFACTURING = 'Изготовление'
    PRODUCTION = 'Производство'
    CONSULTATION = 'Консультация'
    OTHER = 'Другое'

class BusinessCategoryEnum(enum.Enum):
    SAUSAGE = 'Колбаса'
    DRINKS = 'Напитки'
    CHEESE = 'Сыр'
    SEAFOOD = 'Морепродукты'
    CONFECTIONERY = 'Кондитерские изделия'
    RESTAURANT = 'Ресторан/Кафе'
    GROCERY = 'Продуктовый магазин'
    SERVICES = 'Услуги'
    OTHER = 'Другое'

class ContractStatus(enum.Enum):
    ACTIVE = 'Активный'
    ARCHIVE = 'Архив'

class BillingType(enum.Enum):
    MONTHLY = 'Ежемесячное'
    ONE_TIME = 'Разовое'

class RealizationSource(enum.Enum):
    AUTO = 'По договору/спецификации (автоматически)'
    MANUAL = 'По договору/спецификации (вручную)'
    ONCE = 'Разовая (без договора)'

class PaymentType(enum.Enum):
    CASH = 'Наличные'
    NON_CASH = 'Безналичный'

class PaymentStatus(enum.Enum):
    NOT_PAID = 'Не оплачено'
    PARTIALLY_PAID = 'Частично оплачено'
    PAID = 'Оплачено'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum(Role), default=Role.MANAGER, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<User {self.name}>'

class Counterparty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(CounterpartyType), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    brand_name = db.Column(db.String(100), nullable=False)
    inn = db.Column(db.String(12), unique=True)
    contacts = db.Column(db.JSON)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Counterparty {self.brand_name}>'

class PropertyObjectType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum(PropertyObjectTypeEnum), nullable=False, unique=True)

    def __repr__(self):
        return f'<PropertyObjectType {self.name.value}>'

class PropertyObject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('property_object_type.id'), nullable=False)
    characteristics = db.Column(db.Text)
    location = db.Column(db.Text)

    type = db.relationship('PropertyObjectType', backref=db.backref('property_objects', lazy=True))

    def __repr__(self):
        return f'<PropertyObject {self.name}>'

class ServiceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum(ServiceTypeEnum), nullable=False, unique=True)

    def __repr__(self):
        return f'<ServiceType {self.name.value}>'

class BusinessCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum(BusinessCategoryEnum), nullable=False, unique=True)

    def __repr__(self):
        return f'<BusinessCategory {self.name.value}>'

class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    app_end_date = db.Column(db.Date)
    pavilion_number = db.Column(db.String(50))
    status = db.Column(db.Enum(ContractStatus), default=ContractStatus.ACTIVE, nullable=False)

    counterparty_id = db.Column(db.Integer, db.ForeignKey('counterparty.id'), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('business_category.id'), nullable=False)

    counterparty = db.relationship('Counterparty', backref=db.backref('contracts', lazy=True))
    manager = db.relationship('User', backref=db.backref('contracts', lazy=True))
    category = db.relationship('BusinessCategory', backref=db.backref('contracts', lazy=True))

    def __repr__(self):
        return f'<Contract {self.number}>'

class Specification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)

    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    contract = db.relationship('Contract', backref=db.backref('specifications', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Specification {self.number} for Contract {self.contract.number}>'

class SpecificationService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    billing_type = db.Column(db.Enum(BillingType), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    specification_id = db.Column(db.Integer, db.ForeignKey('specification.id'), nullable=False)
    property_object_id = db.Column(db.Integer, db.ForeignKey('property_object.id'))
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_type.id'), nullable=False)

    specification = db.relationship('Specification', backref=db.backref('services', lazy=True, cascade="all, delete-orphan"))
    property_object = db.relationship('PropertyObject')
    service_type = db.relationship('ServiceType')
    
    def __repr__(self):
        return f'<SpecificationService {self.id}>'

class Realization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False, default=lambda: str(datetime.now().timestamp())) # Временный авто-номер
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    source = db.Column(db.Enum(RealizationSource), nullable=False)
    month = db.Column(db.Integer) # Месяц реализации (1-12)
    year = db.Column(db.Integer) # Год реализации
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.NOT_PAID, nullable=False)

    counterparty_id = db.Column(db.Integer, db.ForeignKey('counterparty.id'), nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))
    specification_id = db.Column(db.Integer, db.ForeignKey('specification.id'))
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    counterparty = db.relationship('Counterparty', backref='realizations')
    contract = db.relationship('Contract', backref='realizations')
    specification = db.relationship('Specification', backref='realizations')
    manager = db.relationship('User', backref='realizations')

    @property
    def total_sale(self):
        return sum(service.sale_amount for service in self.services)

    @property
    def total_expense(self):
        return sum(service.expense_amount for service in self.services)
    
    @property
    def total_profit(self):
        return self.total_sale - self.total_expense

class RealizationService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    sale_amount = db.Column(db.Numeric(10, 2), nullable=False)
    expense_amount = db.Column(db.Numeric(10, 2), default=0)
    
    realization_id = db.Column(db.Integer, db.ForeignKey('realization.id'), nullable=False)
    property_object_id = db.Column(db.Integer, db.ForeignKey('property_object.id'))
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_type.id'), nullable=False)
    
    realization = db.relationship('Realization', backref=db.backref('services', cascade="all, delete-orphan"))
    property_object = db.relationship('PropertyObject')
    service_type = db.relationship('ServiceType')
