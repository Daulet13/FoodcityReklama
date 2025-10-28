from app import db
import enum


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
