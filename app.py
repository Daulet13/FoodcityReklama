from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from datetime import datetime
from sqlalchemy import extract

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key' # Добавьте секретный ключ для сессий и флеш-сообщений
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from models import (db, User, Counterparty, CounterpartyType, Role,
                    PropertyObject, PropertyObjectType, ServiceType, BusinessCategory,
                    PropertyObjectTypeEnum, ServiceTypeEnum, BusinessCategoryEnum,
                    Contract, ContractStatus, Specification, SpecificationService, BillingType,
                    Realization, RealizationService, RealizationSource, PaymentType)

def parse_date(value: str):
    value = (value or '').strip()
    if not value:
        return None
    return datetime.strptime(value, '%d/%m/%Y').date()

@app.cli.command('init-db')
def init_db_command():
    """Initializes the database with dictionary values."""
    if PropertyObjectType.query.count() == 0:
        print("Populating PropertyObjectType...")
        for item in PropertyObjectTypeEnum:
            db.session.add(PropertyObjectType(name=item))
    
    if ServiceType.query.count() == 0:
        print("Populating ServiceType...")
        for item in ServiceTypeEnum:
            db.session.add(ServiceType(name=item))

    if BusinessCategory.query.count() == 0:
        print("Populating BusinessCategory...")
        for item in BusinessCategoryEnum:
            db.session.add(BusinessCategory(name=item))
            
    db.session.commit()
    print("Dictionaries populated.")

@app.cli.command('create-manager')
def create_manager_command():
    """Creates a test manager."""
    if User.query.filter_by(email='manager@test.com').count() == 0:
        manager = User(
            name='Борис',
            email='manager@test.com',
            role=Role.MANAGER,
            is_active=True
        )
        db.session.add(manager)
        db.session.commit()
        print("Manager 'Борис' created.")
    else:
        print("Manager 'Борис' already exists.")


@app.route('/')
def hello_world():
    return redirect(url_for('counterparties_list'))

@app.route('/counterparties', methods=['GET', 'POST'])
def counterparties_list():
    types = list(CounterpartyType)

    if request.method == 'POST':
        form_type = request.form.get('form_type', 'create')

        if form_type == 'create':
            new_counterparty = Counterparty(
                brand_name=request.form['brand_name'],
                full_name=request.form['full_name'],
                type=CounterpartyType[request.form['type']]
            )
            db.session.add(new_counterparty)
            db.session.commit()
            flash('Контрагент добавлен.', 'success')

        elif form_type == 'update':
            counterparty_id = int(request.form.get('counterparty_id'))
            counterparty = Counterparty.query.get_or_404(counterparty_id)
            counterparty.brand_name = request.form['brand_name']
            counterparty.full_name = request.form['full_name']
            counterparty.type = CounterpartyType[request.form['type']]
            db.session.commit()
            flash('Изменения сохранены.', 'success')

        elif form_type == 'delete':
            counterparty_id = int(request.form.get('counterparty_id'))
            counterparty = Counterparty.query.get_or_404(counterparty_id)

            if counterparty.contracts:
                flash('Нельзя удалить контрагента: имеются связанные договоры.', 'danger')
            else:
                db.session.delete(counterparty)
                db.session.commit()
                flash('Контрагент удален.', 'success')

        return redirect(url_for('counterparties_list'))

    all_counterparties = Counterparty.query.order_by(Counterparty.brand_name).all()
    return render_template('counterparties.html', counterparties=all_counterparties, types=types)

@app.route('/property-objects', methods=['GET', 'POST'])
def property_objects_list():
    object_types = PropertyObjectType.query.order_by(PropertyObjectType.name).all()

    if request.method == 'POST':
        form_type = request.form.get('form_type', 'create')

        if form_type == 'create':
            new_object = PropertyObject(
                name=request.form['name'],
                type_id=int(request.form['type_id']),
                characteristics=request.form.get('characteristics'),
                location=request.form.get('location')
            )
            db.session.add(new_object)
            db.session.commit()
            flash('Объект добавлен.', 'success')

        elif form_type == 'update':
            object_id = int(request.form.get('object_id'))
            obj = PropertyObject.query.get_or_404(object_id)
            obj.name = request.form['name']
            obj.type_id = int(request.form['type_id'])
            obj.location = request.form.get('location')
            obj.characteristics = request.form.get('characteristics')
            db.session.commit()
            flash('Изменения сохранены.', 'success')

        elif form_type == 'delete':
            object_id = int(request.form.get('object_id'))
            obj = PropertyObject.query.get_or_404(object_id)

            spec_usage = SpecificationService.query.filter_by(property_object_id=obj.id).count()
            realization_usage = RealizationService.query.filter_by(property_object_id=obj.id).count()

            if spec_usage or realization_usage:
                flash('Нельзя удалить объект: он используется в спецификациях или реализациях.', 'danger')
            else:
                db.session.delete(obj)
                db.session.commit()
                flash('Объект удален.', 'success')

        return redirect(url_for('property_objects_list'))
    
    all_objects = PropertyObject.query.order_by(PropertyObject.name).all()
    usage_map = {
        obj.id: SpecificationService.query.filter_by(property_object_id=obj.id).count() +
                 RealizationService.query.filter_by(property_object_id=obj.id).count()
        for obj in all_objects
    }
    return render_template('property_objects.html', 
                           objects=all_objects, 
                           object_types=object_types,
                           usage_map=usage_map)

@app.route('/contracts', methods=['GET', 'POST'])
def contracts_list():
    counterparties = Counterparty.query.order_by(Counterparty.brand_name).all()
    managers = User.query.filter_by(role=Role.MANAGER).order_by(User.name).all()
    categories = BusinessCategory.query.order_by(BusinessCategory.name).all()
    statuses = list(ContractStatus)

    if request.method == 'POST':
        form_type = request.form.get('form_type', 'create')

        if form_type == 'create':
            new_contract = Contract(
                number=request.form['number'],
                date=parse_date(request.form['date']),
                app_end_date=parse_date(request.form.get('app_end_date')),
                pavilion_number=request.form.get('pavilion_number') or None,
                status=ContractStatus[request.form['status']],
                counterparty_id=int(request.form['counterparty_id']),
                manager_id=int(request.form['manager_id']),
                category_id=int(request.form['category_id'])
            )
            db.session.add(new_contract)
            db.session.commit()
            flash('Договор добавлен.', 'success')

        elif form_type == 'update':
            contract_id = int(request.form.get('contract_id'))
            contract = Contract.query.get_or_404(contract_id)
            contract.number = request.form['number']
            contract.date = parse_date(request.form['date'])
            contract.app_end_date = parse_date(request.form.get('app_end_date'))
            contract.pavilion_number = request.form.get('pavilion_number') or None
            contract.status = ContractStatus[request.form['status']]
            contract.counterparty_id = int(request.form['counterparty_id'])
            contract.manager_id = int(request.form['manager_id'])
            contract.category_id = int(request.form['category_id'])
            db.session.commit()
            flash('Изменения по договору сохранены.', 'success')

        elif form_type == 'delete':
            contract_id = int(request.form.get('contract_id'))
            contract = Contract.query.get_or_404(contract_id)
            if contract.specifications or contract.realizations:
                flash('Нельзя удалить договор: есть связанные спецификации или реализации.', 'danger')
            else:
                db.session.delete(contract)
                db.session.commit()
                flash('Договор удален.', 'success')

        return redirect(url_for('contracts_list'))

    contracts = Contract.query.order_by(Contract.date.desc()).all()
    usage_map = {
        contract.id: {
            'specifications': len(contract.specifications),
            'realizations': len(contract.realizations)
        }
        for contract in contracts
    }

    return render_template('contracts.html', 
                           contracts=contracts,
                           counterparties=counterparties,
                           managers=managers,
                           categories=categories,
                           statuses=statuses,
                           usage_map=usage_map)

@app.route('/contract/<int:contract_id>', methods=['GET', 'POST'])
def contract_detail(contract_id):
    contract = Contract.query.get_or_404(contract_id)

    if request.method == 'POST':
        # Определяем, какая форма была отправлена
        form_type = request.form.get('form_type')

        if form_type == 'update_contract':
            contract.number = request.form['number']
            contract.date = parse_date(request.form['date'])
            contract.app_end_date = parse_date(request.form.get('app_end_date'))
            contract.pavilion_number = request.form.get('pavilion_number') or None
            contract.status = ContractStatus[request.form['status']]
            contract.counterparty_id = int(request.form['counterparty_id'])
            contract.manager_id = int(request.form['manager_id'])
            contract.category_id = int(request.form['category_id'])
            db.session.commit()
            flash('Договор обновлён.', 'success')

        elif form_type == 'delete_contract':
            if contract.specifications or contract.realizations:
                flash('Нельзя удалить договор: есть связанные спецификации или реализации.', 'danger')
                return redirect(url_for('contract_detail', contract_id=contract.id))
            db.session.delete(contract)
            db.session.commit()
            flash('Договор удалён.', 'success')
            return redirect(url_for('contracts_list'))

        elif form_type == 'add_specification':
            new_spec = Specification(
                number=request.form['number'],
                start_date=parse_date(request.form['start_date']),
                end_date=parse_date(request.form['end_date']),
                description=request.form.get('description'),
                contract_id=contract.id
            )
            db.session.add(new_spec)
            db.session.commit()
            flash('Спецификация добавлена.', 'success')

        elif form_type == 'update_specification':
            spec = Specification.query.get_or_404(int(request.form['specification_id']))
            spec.number = request.form['number']
            spec.start_date = parse_date(request.form['start_date'])
            spec.end_date = parse_date(request.form['end_date'])
            spec.description = request.form.get('description')
            db.session.commit()
            flash('Спецификация обновлена.', 'success')

        elif form_type == 'delete_specification':
            spec = Specification.query.get_or_404(int(request.form['specification_id']))
            if spec.services or spec.realizations:
                flash('Нельзя удалить спецификацию: есть связанные услуги или реализации.', 'danger')
            else:
                db.session.delete(spec)
                db.session.commit()
                flash('Спецификация удалена.', 'success')

        elif form_type == 'add_service':
            spec_id = int(request.form.get('specification_id'))
            new_service = SpecificationService(
                specification_id=spec_id,
                service_type_id=int(request.form['service_type_id']),
                property_object_id=int(request.form['property_object_id']) if request.form.get('property_object_id') else None,
                description=request.form.get('description'),
                billing_type=BillingType[request.form['billing_type']],
                start_date=parse_date(request.form['start_date']),
                end_date=parse_date(request.form.get('end_date')),
                amount=request.form['amount']
            )
            db.session.add(new_service)
            db.session.commit()
            flash('Услуга добавлена.', 'success')

        elif form_type == 'update_service':
            service = SpecificationService.query.get_or_404(int(request.form['service_id']))
            service.service_type_id = int(request.form['service_type_id'])
            service.property_object_id = int(request.form['property_object_id']) if request.form.get('property_object_id') else None
            service.description = request.form.get('description')
            service.billing_type = BillingType[request.form['billing_type']]
            service.start_date = parse_date(request.form['start_date'])
            service.end_date = parse_date(request.form.get('end_date'))
            service.amount = request.form['amount']
            db.session.commit()
            flash('Услуга обновлена.', 'success')

        elif form_type == 'delete_service':
            service = SpecificationService.query.get_or_404(int(request.form['service_id']))
            db.session.delete(service)
            db.session.commit()
            flash('Услуга удалена.', 'success')

        return redirect(url_for('contract_detail', contract_id=contract.id))

    # Данные для форм
    service_types = ServiceType.query.all()
    property_objects = PropertyObject.query.all()
    billing_types = list(BillingType)
    counterparties = Counterparty.query.order_by(Counterparty.brand_name).all()
    managers = User.query.filter_by(role=Role.MANAGER).order_by(User.name).all()
    categories = BusinessCategory.query.order_by(BusinessCategory.name).all()
    statuses = list(ContractStatus)
    spec_usage = {
        spec.id: {
            'services': len(spec.services),
            'realizations': len(spec.realizations)
        }
        for spec in contract.specifications
    }

    return render_template('contract_detail.html', 
                           contract=contract,
                           service_types=service_types,
                           property_objects=property_objects,
                           billing_types=billing_types,
                           counterparties=counterparties,
                           managers=managers,
                           categories=categories,
                           statuses=statuses,
                           spec_usage=spec_usage)

@app.route('/realizations', methods=['GET', 'POST'])
def realizations_list():
    if request.method == 'POST':
        # Логика для создания разовой реализации (пока заглушка)
        pass
    realizations = Realization.query.order_by(Realization.date.desc()).all()
    return render_template('realizations.html', realizations=realizations, now=datetime.now())

@app.route('/generate-realizations', methods=['POST'])
def generate_realizations():
    month_year_str = request.form.get('month')
    if not month_year_str:
        flash('Необходимо выбрать месяц для генерации.', 'danger')
        return redirect(url_for('realizations_list'))

    year, month = map(int, month_year_str.split('-'))
    
    # 1. Найти все активные договоры
    active_contracts = Contract.query.filter_by(status=ContractStatus.ACTIVE).all()
    
    generated_count = 0

    for contract in active_contracts:
        # 2. Найти все подходящие спецификации
        specs = Specification.query.filter(
            Specification.contract_id == contract.id,
            extract('year', Specification.start_date) <= year,
            extract('month', Specification.start_date) <= month,
            extract('year', Specification.end_date) >= year,
            extract('month', Specification.end_date) >= month
        ).all()

        for spec in specs:
            # 3. Найти все ежемесячные услуги
            monthly_services = SpecificationService.query.filter_by(
                specification_id=spec.id,
                billing_type=BillingType.MONTHLY
            ).all()

            for service in monthly_services:
                 # 4. Проверить, не создана ли уже реализация
                exists = Realization.query.filter_by(
                    contract_id=contract.id,
                    specification_id=spec.id,
                    month=month,
                    year=year
                ).join(RealizationService).filter(RealizationService.description == service.description).count() > 0

                if not exists:
                    # 5. Создать реализацию
                    new_realization = Realization(
                        date=datetime(year, month, 1),
                        source=RealizationSource.AUTO,
                        month=month,
                        year=year,
                        payment_type=PaymentType.NON_CASH,
                        counterparty_id=contract.counterparty_id,
                        contract_id=contract.id,
                        specification_id=spec.id,
                        manager_id=contract.manager_id,
                    )
                    
                    realization_service = RealizationService(
                        description=service.description,
                        sale_amount=service.amount,
                        property_object_id=service.property_object_id,
                        service_type_id=service.service_type_id,
                        realization=new_realization
                    )
                    
                    db.session.add(new_realization)
                    db.session.add(realization_service)
                    generated_count += 1
    
    if generated_count > 0:
        db.session.commit()
        flash(f'Успешно сгенерировано {generated_count} новых реализаций за {month:02}.{year}.', 'success')
    else:
        flash(f'Новых реализаций для генерации за {month:02}.{year} не найдено.', 'info')

    return redirect(url_for('realizations_list'))


if __name__ == '__main__':
    app.run(debug=True)
