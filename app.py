from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from models import User, Counterparty, CounterpartyType

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


if __name__ == '__main__':
    app.run(debug=True)
