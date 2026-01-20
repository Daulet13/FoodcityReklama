from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key' # Добавьте секретный ключ для сессий и флеш-сообщений
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from models import (db, User, Counterparty, CounterpartyType, Role,
                    PropertyObject, PropertyObjectType, ServiceType, BusinessCategory,
                    PropertyObjectTypeEnum, ServiceTypeEnum, BusinessCategoryEnum,
                    Contract, ContractStatus, Specification, SpecificationService, BillingType,
                    Realization, RealizationService, RealizationSource, PaymentType, PaymentStatus,
                    Payment, payment_realization_association)

db.init_app(app)
migrate = Migrate(app, db)

def parse_date(value: str):
    value = (value or '').strip()
    if not value:
        return None
    try:
        # Сначала пробуем наш основной формат dd/mm/yyyy
        return datetime.strptime(value, '%d/%m/%Y').date()
    except ValueError:
        # Если не получилось, пробуем стандартный формат YYYY-MM-DD
        return datetime.strptime(value, '%Y-%m-%d').date()

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
    
    # Данные для всех форм, загружаются всегда
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
        } for spec in contract.specifications
    }
    
    form_with_error = None # Для хранения данных невалидной формы

    if request.method == 'POST':
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
            return redirect(url_for('contract_detail', contract_id=contract.id))

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
            return redirect(url_for('contract_detail', contract_id=contract.id))

        elif form_type == 'update_specification':
            spec = Specification.query.get_or_404(int(request.form['specification_id']))
            spec.number = request.form['number']
            spec.start_date = parse_date(request.form['start_date'])
            spec.end_date = parse_date(request.form['end_date'])
            spec.description = request.form.get('description')
            db.session.commit()
            flash('Спецификация обновлена.', 'success')
            return redirect(url_for('contract_detail', contract_id=contract.id))

        elif form_type == 'delete_specification':
            spec = Specification.query.get_or_404(int(request.form['specification_id']))
            if spec.services or spec.realizations:
                flash('Нельзя удалить спецификацию: есть связанные услуги или реализации.', 'danger')
            else:
                db.session.delete(spec)
                db.session.commit()
                flash('Спецификация удалена.', 'success')
            return redirect(url_for('contract_detail', contract_id=contract.id))

        elif form_type == 'add_service':
            spec_id = int(request.form.get('specification_id'))
            spec = Specification.query.get_or_404(spec_id)
            service_start = parse_date(request.form['start_date'])
            service_end = parse_date(request.form.get('end_date'))
            
            error = None
            if service_start < spec.start_date or service_start > spec.end_date:
                error = f'Дата начала услуги должна быть в пределах спецификации ({spec.start_date.strftime("%d/%m/%Y")} - {spec.end_date.strftime("%d/%m/%Y")}).'
            if service_end and (service_end < spec.start_date or service_end > spec.end_date):
                error = f'Дата окончания услуги должна быть в пределах спецификации ({spec.start_date.strftime("%d/%m/%Y")} - {spec.end_date.strftime("%d/%m/%Y")}).'

            if error:
                flash(error, 'danger')
                form_with_error = { 'type': 'add_service', 'spec_id': spec_id, 'data': request.form }
            else:
                new_service = SpecificationService(
                    specification_id=spec_id,
                    service_type_id=int(request.form['service_type_id']),
                    property_object_id=int(request.form['property_object_id']) if request.form.get('property_object_id') else None,
                    description=request.form.get('description'),
                    billing_type=BillingType[request.form['billing_type']],
                    start_date=service_start,
                    end_date=service_end,
                    amount=request.form['amount']
                )
                db.session.add(new_service)
                db.session.commit()
                flash('Услуга добавлена.', 'success')
                return redirect(url_for('contract_detail', contract_id=contract.id))

        elif form_type == 'update_service':
            service = SpecificationService.query.get_or_404(int(request.form['service_id']))
            spec = service.specification
            service_start = parse_date(request.form['start_date'])
            service_end = parse_date(request.form.get('end_date'))
            
            error = None
            if service_start < spec.start_date or service_start > spec.end_date:
                error = f'Дата начала услуги должна быть в пределах спецификации ({spec.start_date.strftime("%d/%m/%Y")} - {spec.end_date.strftime("%d/%m/%Y")}).'
            if service_end and (service_end < spec.start_date or service_end > spec.end_date):
                error = f'Дата окончания услуги должна быть в пределах спецификации ({spec.start_date.strftime("%d/%m/%Y")} - {spec.end_date.strftime("%d/%m/%Y")}).'

            if error:
                flash(error, 'danger')
                form_with_error = { 'type': 'update_service', 'service_id': service.id, 'data': request.form }
            else:
                service.service_type_id = int(request.form['service_type_id'])
                service.property_object_id = int(request.form['property_object_id']) if request.form.get('property_object_id') else None
                service.description = request.form.get('description')
                service.billing_type = BillingType[request.form['billing_type']]
                service.start_date = service_start
                service.end_date = service_end
                service.amount = request.form['amount']
                db.session.commit()
                flash('Услуга обновлена.', 'success')
                return redirect(url_for('contract_detail', contract_id=contract.id))

        elif form_type == 'delete_service':
            service = SpecificationService.query.get_or_404(int(request.form['service_id']))
            db.session.delete(service)
            db.session.commit()
            flash('Услуга удалена.', 'success')
            return redirect(url_for('contract_detail', contract_id=contract.id))

    return render_template('contract_detail.html', 
                           contract=contract,
                           service_types=service_types,
                           property_objects=property_objects,
                           billing_types=billing_types,
                           counterparties=counterparties,
                           managers=managers,
                           categories=categories,
                           statuses=statuses,
                           spec_usage=spec_usage,
                           form_with_error=form_with_error)

@app.route('/realizations', methods=['GET', 'POST'])
def realizations_list():
    one_off_form_data = None

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'update_realization':
            realization = Realization.query.get_or_404(int(request.form['realization_id']))
            realization.date = parse_date(request.form['date'])
            realization.month = realization.date.month
            realization.year = realization.date.year
            
            # Для MANUAL реализаций разрешаем редактировать все поля
            if realization.source == RealizationSource.MANUAL:
                realization.counterparty_id = int(request.form['counterparty_id'])
                realization.contract_id = int(request.form['contract_id']) if request.form.get('contract_id') else None
                realization.specification_id = int(request.form['specification_id']) if request.form.get('specification_id') else None
                realization.manager_id = int(request.form['manager_id'])
                
                # Обновляем услугу
                if realization.services:
                    service = realization.services[0]
                    service.service_type_id = int(request.form['service_type_id'])
                    service.property_object_id = int(request.form['property_object_id']) if request.form.get('property_object_id') else None
                    service.sale_amount = Decimal(request.form['sale_amount'].replace(',', '.'))
            
            # Для всех реализаций (AUTO и MANUAL) разрешаем редактировать описание и расходы
            if realization.services:
                service = realization.services[0]
                service.description = request.form.get('description')
                service.expense_amount = Decimal(request.form.get('expense_amount', '0').replace(',', '.'))
            
            db.session.commit()
            flash('Реализация обновлена.', 'success')
            return redirect(url_for('realizations_list'))
            
        elif form_type == 'delete_realization':
            realization = Realization.query.get_or_404(int(request.form['realization_id']))
            db.session.delete(realization)
            db.session.commit()
            flash('Реализация удалена.', 'success')
            return redirect(url_for('realizations_list'))

        elif form_type == 'create_one_off':
            form = request.form
            one_off_form_data = form.to_dict()
            has_error = False

            try:
                realization_date = parse_date(form['date'])
            except (ValueError, KeyError):
                flash('Неверный формат даты.', 'danger')
                has_error = True
                realization_date = None

            counterparty_id = form.get('counterparty_id')
            if not counterparty_id:
                flash('Укажите контрагента.', 'danger')
                has_error = True
            else:
                try:
                    counterparty_id = int(counterparty_id)
                except ValueError:
                    counterparty_id = None
                    flash('Указан некорректный контрагент.', 'danger')
                    has_error = True

            contract = None
            contract_id_raw = form.get('contract_id')
            if contract_id_raw:
                try:
                    contract = Contract.query.get(int(contract_id_raw))
                    if not contract:
                        flash('Выбранный договор не найден.', 'danger')
                        has_error = True
                    elif counterparty_id and contract.counterparty_id != counterparty_id:
                        flash('Договор не принадлежит выбранному контрагенту.', 'danger')
                        has_error = True
                        contract = None
                except ValueError:
                    flash('Указан некорректный договор.', 'danger')
                    has_error = True

            specification = None
            specification_id_raw = form.get('specification_id')
            if specification_id_raw:
                try:
                    specification = Specification.query.get(int(specification_id_raw))
                    if not specification:
                        flash('Выбранная спецификация не найдена.', 'danger')
                        has_error = True
                    elif contract and specification.contract_id != contract.id:
                        flash('Спецификация не относится к выбранному договору.', 'danger')
                        has_error = True
                        specification = None
                    elif not contract and specification:
                        contract = specification.contract
                        one_off_form_data['contract_id'] = str(contract.id)
                except ValueError:
                    flash('Указана некорректная спецификация.', 'danger')
                    has_error = True

            manager_id = form.get('manager_id')
            manager = None
            if manager_id:
                try:
                    manager = User.query.get(int(manager_id))
                    if not manager:
                        flash('Выбранный менеджер не найден.', 'danger')
                        has_error = True
                except ValueError:
                    flash('Указан некорректный менеджер.', 'danger')
                    has_error = True
            elif contract:
                manager = contract.manager
                manager_id = contract.manager_id
                one_off_form_data['manager_id'] = str(manager_id)
            else:
                flash('Укажите менеджера.', 'danger')
                has_error = True

            # payment_status всегда NOT_PAID для новой реализации (в будущем будет автоматически из платежей)

            service_type_id = form.get('service_type_id')
            service_type = None
            if service_type_id:
                try:
                    service_type = ServiceType.query.get(int(service_type_id))
                    if not service_type:
                        flash('Выбранный тип услуги не найден.', 'danger')
                        has_error = True
                except ValueError:
                    flash('Указан некорректный тип услуги.', 'danger')
                    has_error = True
            else:
                flash('Выберите тип услуги.', 'danger')
                has_error = True

            property_object_id = form.get('property_object_id') or None
            if property_object_id:
                try:
                    property_object = PropertyObject.query.get(int(property_object_id))
                    if not property_object:
                        flash('Выбранный объект не найден.', 'danger')
                        has_error = True
                        property_object_id = None
                except ValueError:
                    flash('Указан некорректный объект.', 'danger')
                    has_error = True
                    property_object_id = None

            description = form.get('description')

            sale_amount = None
            try:
                sale_amount = Decimal(form.get('sale_amount', '0').replace(',', '.'))
                if sale_amount <= 0:
                    flash('Сумма продажи должна быть больше нуля.', 'danger')
                    has_error = True
                    sale_amount = None
            except (InvalidOperation, AttributeError):
                flash('Укажите корректную сумму продажи.', 'danger')
                has_error = True

            expense_amount = Decimal('0')
            expense_raw = form.get('expense_amount')
            if expense_raw:
                try:
                    expense_amount = Decimal(expense_raw.replace(',', '.'))
                    if expense_amount < 0:
                        flash('Расходы не могут быть отрицательными.', 'danger')
                        has_error = True
                        expense_amount = Decimal('0')
                except InvalidOperation:
                    flash('Укажите корректную сумму расходов.', 'danger')
                    has_error = True
                    expense_amount = Decimal('0')

            if has_error or not all([realization_date, counterparty_id, manager, service_type, sale_amount]):
                return render_template(
                    'realizations.html',
                    realizations=Realization.query.order_by(Realization.date.desc()).all(),
                    counterparties=Counterparty.query.order_by(Counterparty.brand_name).all(),
                    contracts=Contract.query.order_by(Contract.number).all(),
                    specifications=Specification.query.order_by(Specification.number).all(),
                    managers=User.query.filter_by(role=Role.MANAGER).order_by(User.name).all(),
                    service_types=ServiceType.query.order_by(ServiceType.name).all(),
                    property_objects=PropertyObject.query.order_by(PropertyObject.name).all(),
                    now=datetime.now(),
                    one_off_form_data=one_off_form_data
                )

            realization = Realization(
                date=realization_date,
                month=realization_date.month,
                year=realization_date.year,
                source=RealizationSource.MANUAL,
                payment_status=PaymentStatus.NOT_PAID,
                counterparty_id=counterparty_id,
                contract_id=contract.id if contract else None,
                specification_id=specification.id if specification else None,
                manager_id=manager.id
            )

            service = RealizationService(
                description=description,
                sale_amount=sale_amount,
                expense_amount=expense_amount,
                property_object_id=int(property_object_id) if property_object_id else None,
                service_type_id=service_type.id,
                realization=realization
            )

            db.session.add(realization)
            db.session.add(service)
            db.session.commit()
            flash('Разовая реализация создана.', 'success')
            return redirect(url_for('realizations_list'))

    realizations = Realization.query.order_by(Realization.date.desc()).all()
    counterparties = Counterparty.query.order_by(Counterparty.brand_name).all()
    contracts = Contract.query.order_by(Contract.number).all()
    specifications = Specification.query.order_by(Specification.number).all()
    managers = User.query.filter_by(role=Role.MANAGER).order_by(User.name).all()
    service_types = ServiceType.query.order_by(ServiceType.name).all()
    property_objects = PropertyObject.query.order_by(PropertyObject.name).all()

    return render_template('realizations.html', 
                          realizations=realizations, 
                          counterparties=counterparties,
                          contracts=contracts,
                          specifications=specifications,
                          managers=managers,
                          service_types=service_types,
                          property_objects=property_objects,
                          now=datetime.now(),
                          one_off_form_data=one_off_form_data)

@app.route('/generate-realizations', methods=['POST'])
def generate_realizations():
    month_year_str = request.form.get('month')
    if not month_year_str:
        flash('Необходимо выбрать месяц для генерации.', 'danger')
        return redirect(url_for('realizations_list'))

    year, month = map(int, month_year_str.split('-'))
    month_start = date(year, month, 1)
    next_month = date(year + (month // 12), (month % 12) + 1, 1)
    month_end = next_month - timedelta(days=1)
    
    # 1. Найти все активные договоры
    active_contracts = Contract.query.filter_by(status=ContractStatus.ACTIVE).all()
    
    generated_count = 0

    for contract in active_contracts:
        # 2. Найти все подходящие спецификации
        specs = Specification.query.filter(
            Specification.contract_id == contract.id,
            Specification.start_date <= month_end,
            Specification.end_date >= month_start
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
                        date=month_start,
                        source=RealizationSource.AUTO,
                        month=month,
                        year=year,
                        payment_status=PaymentStatus.NOT_PAID,
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


@app.route('/payments', methods=['GET', 'POST'])
def payments_list():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'create_payment':
            form = request.form
            has_error = False
            
            try:
                payment_date = parse_date(form['date'])
            except (ValueError, KeyError):
                flash('Неверный формат даты.', 'danger')
                has_error = True
                payment_date = None
            
            counterparty_id_raw = form.get('counterparty_id')
            counterparty_id = None
            if not counterparty_id_raw:
                flash('Укажите контрагента.', 'danger')
                has_error = True
            else:
                try:
                    counterparty_id = int(counterparty_id_raw)
                    counterparty = Counterparty.query.get(counterparty_id)
                    if not counterparty:
                        flash('Выбранный контрагент не найден.', 'danger')
                        has_error = True
                except ValueError:
                    flash('Указан некорректный контрагент.', 'danger')
                    has_error = True
            
            contract_id = None
            contract_id_raw = form.get('contract_id')
            if contract_id_raw:
                try:
                    contract_id_val = int(contract_id_raw)
                    contract = Contract.query.get(contract_id_val)
                    if not contract:
                        flash('Выбранный договор не найден.', 'danger')
                        has_error = True
                    elif counterparty_id and contract.counterparty_id != counterparty_id:
                        flash('Договор не принадлежит выбранному контрагенту.', 'danger')
                        has_error = True
                    else:
                        contract_id = contract_id_val
                except ValueError:
                    flash('Указан некорректный договор.', 'danger')
                    has_error = True
            
            try:
                payment_type = PaymentType[form['payment_type']]
            except KeyError:
                payment_type = None
                flash('Выберите корректный тип оплаты.', 'danger')
                has_error = True
            
            amount = None
            try:
                amount = Decimal(form.get('amount', '0').replace(',', '.'))
                if amount <= 0:
                    flash('Сумма платежа должна быть больше нуля.', 'danger')
                    has_error = True
                    amount = None
            except (InvalidOperation, AttributeError):
                flash('Укажите корректную сумму платежа.', 'danger')
                has_error = True
            
            selected_realizations_ids = form.getlist('realization_ids')
            selected_realizations = []
            if selected_realizations_ids:
                for realization_id_raw in selected_realizations_ids:
                    try:
                        realization_id = int(realization_id_raw)
                        realization = Realization.query.get(realization_id)
                    except ValueError:
                        realization = None
                    if not realization:
                        flash('Выбрана некорректная реализация.', 'danger')
                        has_error = True
                        break
                    if counterparty_id and realization.counterparty_id != counterparty_id:
                        flash('Выбранная реализация не принадлежит контрагенту платежа.', 'danger')
                        has_error = True
                        break
                    if realization.debt_amount <= 0:
                        continue
                    selected_realizations.append(realization)
            
            if has_error or not all([payment_date, counterparty_id, payment_type, amount]):
                return redirect(url_for('payments_list'))
            
            # Создаем платеж
            payment = Payment(
                date=payment_date,
                initial_amount=amount,
                unallocated_amount=amount,
                payment_type=payment_type,
                counterparty_id=counterparty_id,
                contract_id=contract_id
            )
            
            db.session.add(payment)
            db.session.flush()  # Получаем ID платежа
            
            total_allocated = Decimal('0')
            for realization in selected_realizations:
                if total_allocated >= amount:
                    break
                debt = realization.debt_amount
                if debt <= 0:
                    continue
                allocation_amount = min(debt, amount - total_allocated)
                if allocation_amount <= 0:
                    continue
                db.session.execute(payment_realization_association.insert().values(
                    payment_id=payment.id,
                    realization_id=realization.id,
                    amount=allocation_amount
                ))
                realization.paid_amount = Decimal(str(realization.paid_amount)) + allocation_amount
                realization.update_payment_status()
                total_allocated += allocation_amount
            
            payment.unallocated_amount = max(Decimal('0'), amount - total_allocated)
            db.session.commit()
            
            if total_allocated > 0:
                if payment.unallocated_amount > 0:
                    flash(f'Платеж создан. На реализации распределено {total_allocated:.2f} руб., аванс {payment.unallocated_amount:.2f} руб.', 'success')
                else:
                    flash('Платеж создан и полностью распределён на выбранные реализации.', 'success')
            else:
                flash('Платеж создан как аванс. Распределение выполните позже.', 'success')
            return redirect(url_for('payments_list'))
    
    payments = Payment.query.order_by(Payment.date.desc()).all()
    counterparties = Counterparty.query.order_by(Counterparty.brand_name).all()
    contracts = Contract.query.order_by(Contract.number).all()

    # Список неоплаченных реализаций для каждого контрагента
    eligible_realizations = Realization.query.filter(Realization.payment_status != PaymentStatus.PAID).order_by(Realization.date.asc()).all()
    realizations_by_counterparty = {}
    for realization in eligible_realizations:
        debt = realization.debt_amount
        if debt <= 0:
            continue
        realizations_by_counterparty.setdefault(realization.counterparty_id, []).append(realization)

    realizations_payload = {}
    for counterparty_id, items in realizations_by_counterparty.items():
        realizations_payload[str(counterparty_id)] = [
            {
                'id': item.id,
                'number': item.number,
                'date': item.date.strftime('%d/%m/%Y'),
                'contract_number': item.contract.number if item.contract else None,
                'specification_number': item.specification.number if item.specification else None,
                'total': float(item.total_sale),
                'paid': float(item.paid_amount or 0),
                'debt': float(item.debt_amount)
            }
            for item in items
        ]
    
    return render_template('payments.html',
                          payments=payments,
                          counterparties=counterparties,
                          contracts=contracts,
                          payment_types=list(PaymentType),
                          realizations_json=realizations_payload,
                          now=datetime.now())

@app.route('/update-payment/<int:payment_id>', methods=['POST'])
def update_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    form = request.form
    
    try:
        payment_date = parse_date(form['date'])
    except (ValueError, KeyError):
        flash('Неверный формат даты.', 'danger')
        return redirect(url_for('payments_list'))
    
    counterparty_id_raw = form.get('counterparty_id')
    counterparty_id = None
    if not counterparty_id_raw:
        flash('Укажите контрагента.', 'danger')
        return redirect(url_for('payments_list'))
    else:
        try:
            counterparty_id = int(counterparty_id_raw)
            counterparty = Counterparty.query.get(counterparty_id)
            if not counterparty:
                flash('Выбранный контрагент не найден.', 'danger')
                return redirect(url_for('payments_list'))
        except ValueError:
            flash('Указан некорректный контрагент.', 'danger')
            return redirect(url_for('payments_list'))
    
    contract_id = None
    contract_id_raw = form.get('contract_id')
    if contract_id_raw:
        try:
            contract_id_val = int(contract_id_raw)
            contract = Contract.query.get(contract_id_val)
            if not contract:
                flash('Выбранный договор не найден.', 'danger')
                return redirect(url_for('payments_list'))
            elif counterparty_id and contract.counterparty_id != counterparty_id:
                flash('Договор не принадлежит выбранному контрагенту.', 'danger')
                return redirect(url_for('payments_list'))
            else:
                contract_id = contract_id_val
        except ValueError:
            flash('Указан некорректный договор.', 'danger')
            return redirect(url_for('payments_list'))
    
    try:
        payment_type = PaymentType[form['payment_type']]
    except KeyError:
        flash('Выберите корректный тип оплаты.', 'danger')
        return redirect(url_for('payments_list'))
    
    # Обновляем только базовые поля (дата, контрагент, договор, тип)
    # Сумму не трогаем, чтобы не нарушить существующие привязки
    payment.date = payment_date
    payment.counterparty_id = counterparty_id
    payment.contract_id = contract_id
    payment.payment_type = payment_type
    
    db.session.commit()
    flash('Платеж обновлён.', 'success')
    return redirect(url_for('payments_list'))

@app.route('/delete-payment/<int:payment_id>', methods=['POST'])
def delete_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    # Проверяем, есть ли привязанные реализации
    allocated_realizations = db.session.execute(
        payment_realization_association.select().where(
            payment_realization_association.c.payment_id == payment_id
        )
    ).fetchall()
    
    if allocated_realizations:
        # Откатываем все распределения
        for row in allocated_realizations:
            realization = Realization.query.get(row.realization_id)
            if realization:
                realization.paid_amount = Decimal(str(realization.paid_amount)) - Decimal(str(row.amount))
                realization.update_payment_status()
        
        # Удаляем записи из таблицы связи
        db.session.execute(
            payment_realization_association.delete().where(
                payment_realization_association.c.payment_id == payment_id
            )
        )
    
    db.session.delete(payment)
    db.session.commit()
    flash('Платеж удалён, распределения откатаны.', 'success')
    return redirect(url_for('payments_list'))


if __name__ == '__main__':
    app.run(debug=True)
