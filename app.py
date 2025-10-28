from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

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
                    Contract, ContractStatus, Specification)
from datetime import datetime

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
    if request.method == 'POST':
        new_counterparty = Counterparty(
            brand_name=request.form['brand_name'],
            full_name=request.form['full_name'],
            type=CounterpartyType[request.form['type']]
        )
        db.session.add(new_counterparty)
        db.session.commit()
        return redirect(url_for('counterparties_list'))

    all_counterparties = Counterparty.query.all()
    types = list(CounterpartyType)
    return render_template('counterparties.html', counterparties=all_counterparties, types=types)

@app.route('/property-objects', methods=['GET', 'POST'])
def property_objects_list():
    if request.method == 'POST':
        new_object = PropertyObject(
            name=request.form['name'],
            type_id=request.form['type_id'],
            characteristics=request.form.get('characteristics'),
            location=request.form.get('location')
        )
        db.session.add(new_object)
        db.session.commit()
        return redirect(url_for('property_objects_list'))
    
    all_objects = PropertyObject.query.all()
    object_types = PropertyObjectType.query.all()
    return render_template('property_objects.html', 
                           objects=all_objects, 
                           object_types=object_types)

@app.route('/contracts', methods=['GET', 'POST'])
def contracts_list():
    if request.method == 'POST':
        new_contract = Contract(
            number=request.form['number'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            app_end_date=datetime.strptime(request.form['app_end_date'], '%Y-%m-%d').date() if request.form['app_end_date'] else None,
            pavilion_number=request.form.get('pavilion_number'),
            status=ContractStatus[request.form['status']],
            counterparty_id=request.form['counterparty_id'],
            manager_id=request.form['manager_id'],
            category_id=request.form['category_id']
        )
        db.session.add(new_contract)
        db.session.commit()
        return redirect(url_for('contracts_list'))

    contracts = Contract.query.all()
    counterparties = Counterparty.query.all()
    managers = User.query.filter_by(role=Role.MANAGER).all()
    categories = BusinessCategory.query.all()
    statuses = list(ContractStatus)
    
    return render_template('contracts.html', 
                           contracts=contracts,
                           counterparties=counterparties,
                           managers=managers,
                           categories=categories,
                           statuses=statuses)

@app.route('/contract/<int:contract_id>', methods=['GET', 'POST'])
def contract_detail(contract_id):
    contract = Contract.query.get_or_404(contract_id)

    if request.method == 'POST':
        # Добавление новой спецификации
        new_spec = Specification(
            number=request.form['number'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
            description=request.form.get('description'),
            contract_id=contract.id
        )
        db.session.add(new_spec)
        db.session.commit()
        return redirect(url_for('contract_detail', contract_id=contract.id))

    return render_template('contract_detail.html', contract=contract)


if __name__ == '__main__':
    app.run(debug=True)
