# Система учета оплат - Детальный план реализации

## Принятые архитектурные решения

### Вариант реализации: Гибкая ручная привязка платежей

**Принцип работы:**
- Один платеж может закрыть одну или несколько реализаций (многие ко многим)
- Пользователь самостоятельно выбирает, какие реализации оплачиваются чекбоксами
- Нераспределенный остаток платежа становится авансом контрагента
- Аванс может быть зачтен при следующем платеже

### Ключевые сценарии:

1. **Оплата равна сумме реализаций** - Реализации помечаются как "Оплачено"
2. **Переплата** - Реализации "Оплачено", остаток → аванс
3. **Недоплата** - Реализации "Частично оплачено"
4. **Платеж без привязки** - Весь платеж становится авансом
5. **Зачет аванса** - При создании нового платежа можно зачесть существующий аванс

### Отказ от автоматического распределения

- **НЕ реализуем:** Автоматическое распределение платежей по методу ФИФО
- **Причина:** Сложность реализации, риск ошибок, избыточность для текущих задач

---

## Модель данных

### 1. Таблица `Payment` (Платежи)

```python
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    initial_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Изначальная сумма платежа
    unallocated_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Неразнесенный остаток (аванс)
    payment_type = db.Column(db.Enum(PaymentType), nullable=False)  # Наличные / Безналичные
    
    counterparty_id = db.Column(db.Integer, db.ForeignKey('counterparty.id'), nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=True)  # Опционально
    
    counterparty = db.relationship('Counterparty', backref='payments')
    contract = db.relationship('Contract', backref='payments')
```

### 2. Таблица связи "Многие-ко-многим" `payment_realization_association`

```python
payment_realization_association = db.Table('payment_realization_association',
    db.Column('payment_id', db.Integer, db.ForeignKey('payment.id'), primary_key=True),
    db.Column('realization_id', db.Integer, db.ForeignKey('realization.id'), primary_key=True),
    db.Column('amount', db.Column(db.Numeric(10, 2), nullable=False))  # Сколько именно зачтено на эту реализацию
)
```

**Важно:** Поле `amount` в таблице связи позволяет частично распределять платеж между реализациями.

### 3. Изменения в модели `Realization`

```python
class Realization(db.Model):
    # ... существующие поля ...
    
    # НОВОЕ ПОЛЕ:
    paid_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Сколько уже оплачено
    
    # Связь с платежами:
    payments = db.relationship('Payment', 
                               secondary=payment_realization_association, 
                               backref='realizations',
                               lazy='dynamic')
    
    @property
    def debt_amount(self):
        """Остаток долга по реализации"""
        return max(Decimal('0'), self.total_sale - self.paid_amount)
    
    def update_payment_status(self):
        """Автоматическое обновление статуса оплаты"""
        if self.paid_amount == 0:
            self.payment_status = PaymentStatus.NOT_PAID
        elif self.paid_amount < self.total_sale:
            self.payment_status = PaymentStatus.PARTIALLY_PAID
        else:
            self.payment_status = PaymentStatus.PAID
```

---

## Страница `/payments` - Структура

### Форма создания платежа

**Поля:**
1. **Контрагент** (обязательно, dropdown)
2. **Договор** (опционально, динамически подгружается по контрагенту)
3. **Дата платежа** (Flatpickr, формат dd/mm/yyyy)
4. **Сумма платежа** (number, обязательна, > 0)
5. **Тип оплаты** (dropdown: Наличные / Безналичные)

**Динамическая секция "Выбор реализаций":**
- Появляется после выбора контрагента
- Таблица со списком всех неоплаченных/частично оплаченных реализаций этого контрагента
- Колонки:
  - [ ] Чекбокс
  - Дата реализации
  - Номер реализации
  - Договор/Спецификация
  - Сумма реализации
  - Оплачено
  - Остаток долга
- При выборе чекбоксов автоматически подставляется сумма остатка долга
- Показывается "Итого выбрано: X руб."

**Блок "Аванс контрагента":**
- Если у контрагента есть неразнесенные платежи, показывается блок:
  - "Доступный аванс: X руб."
  - Кнопка "Зачесть аванс"
  - При нажатии система автоматически распределяет аванс на выбранные реализации

**Кнопки:**
- "Сохранить платеж" (primary)
- "Отмена" (secondary)

### Список платежей

**Таблица с колонками:**
- Дата
- Контрагент
- Договор (если есть)
- Сумма
- Распределено
- Аванс (unallocated_amount)
- Тип оплаты
- Действия (Изменить, Удалить)

**Фильтры:**
- Период (дата от - до)
- Контрагент
- Тип оплаты

---

## Бизнес-логика в `app.py`

### 1. Создание платежа (`create_payment`)

```python
@app.route('/payments', methods=['POST'])
def create_payment():
    form = request.form
    
    # Валидация
    counterparty_id = int(form['counterparty_id'])
    amount = Decimal(form['amount'])
    selected_realizations = form.getlist('realization_ids')  # Список ID выбранных реализаций
    
    # Создание платежа
    payment = Payment(
        date=parse_date(form['date']),
        initial_amount=amount,
        unallocated_amount=amount,  # Пока вся сумма неразнесена
        payment_type=PaymentType[form['payment_type']],
        counterparty_id=counterparty_id,
        contract_id=int(form['contract_id']) if form.get('contract_id') else None
    )
    
    # Распределение по реализациям
    total_allocated = Decimal('0')
    for realization_id in selected_realizations:
        realization = Realization.query.get(realization_id)
        allocation_amount = min(
            realization.debt_amount,  # Остаток долга
            amount - total_allocated  # Остаток платежа
        )
        
        # Связываем платеж с реализацией
        db.session.execute(
            payment_realization_association.insert().values(
                payment_id=payment.id,
                realization_id=realization_id,
                amount=allocation_amount
            )
        )
        
        # Обновляем paid_amount у реализации
        realization.paid_amount += allocation_amount
        realization.update_payment_status()
        
        total_allocated += allocation_amount
    
    # Обновляем неразнесенный остаток (аванс)
    payment.unallocated_amount = amount - total_allocated
    
    db.session.add(payment)
    db.session.commit()
    
    flash('Платеж создан.', 'success')
    return redirect(url_for('payments_list'))
```

### 2. Зачет аванса (`allocate_advance`)

```python
@app.route('/payments/allocate-advance', methods=['POST'])
def allocate_advance():
    form = request.form
    counterparty_id = int(form['counterparty_id'])
    selected_realizations = form.getlist('realization_ids')
    
    # Найти все платежи с неразнесенным остатком у этого контрагента
    payments_with_advance = Payment.query.filter_by(
        counterparty_id=counterparty_id
    ).filter(Payment.unallocated_amount > 0).order_by(Payment.date).all()
    
    total_advance = sum(p.unallocated_amount for p in payments_with_advance)
    total_needed = sum(
        Realization.query.get(rid).debt_amount 
        for rid in selected_realizations
    )
    
    # Сценарий 1: Аванса хватает
    if total_advance >= total_needed:
        remaining_advance = total_advance
        
        for realization_id in selected_realizations:
            realization = Realization.query.get(realization_id)
            debt = realization.debt_amount
            allocation = min(debt, remaining_advance)
            
            # Найти платеж с авансом для распределения
            for payment in payments_with_advance:
                if payment.unallocated_amount > 0:
                    allocation_amount = min(allocation, payment.unallocated_amount)
                    
                    # Связываем
                    db.session.execute(
                        payment_realization_association.insert().values(
                            payment_id=payment.id,
                            realization_id=realization_id,
                            amount=allocation_amount
                        )
                    )
                    
                    # Обновляем
                    realization.paid_amount += allocation_amount
                    realization.update_payment_status()
                    payment.unallocated_amount -= allocation_amount
                    remaining_advance -= allocation_amount
                    
                    if remaining_advance <= 0:
                        break
        
        db.session.commit()
        flash(f'Зачтено {total_needed} руб. из аванса.', 'success')
    
    # Сценарий 2: Аванса не хватает
    else:
        # Зачитываем весь аванс, реализации помечаются как частично оплаченные
        # ... аналогичная логика, но allocation = min(debt, remaining_advance)
        flash(f'Зачтено {total_advance} руб. из аванса. Остаток долга: {total_needed - total_advance} руб.', 'info')
    
    return redirect(url_for('payments_list'))
```

### 3. Отображение суммы аванса для контрагента

```python
def get_counterparty_advance(counterparty_id):
    """Получить сумму неразнесенного аванса контрагента"""
    return db.session.query(func.sum(Payment.unallocated_amount)).filter_by(
        counterparty_id=counterparty_id
    ).scalar() or Decimal('0')
```

---

## Последовательность реализации

### Этап 1: Модели и миграции (1-2 часа)
- [ ] Создать модель `Payment`
- [ ] Создать таблицу связи `payment_realization_association`
- [ ] Добавить поле `paid_amount` в `Realization`
- [ ] Создать миграцию БД
- [ ] Применить миграцию

### Этап 2: Базовый CRUD платежей (2-3 часа)
- [ ] Создать страницу `/payments` со списком
- [ ] Создать форму добавления платежа (без выбора реализаций)
- [ ] Реализовать сохранение платежа как аванса (без распределения)
- [ ] Реализовать отображение списка платежей

### Этап 3: Привязка к реализациям (3-4 часа)
- [ ] Добавить динамическую таблицу с реализациями в форму
- [ ] Реализовать логику распределения платежа на выбранные реализации
- [ ] Обновление `paid_amount` и статусов реализаций
- [ ] Расчет и сохранение `unallocated_amount`

### Этап 4: Зачет аванса (2-3 часа)
- [ ] Добавить блок отображения аванса в форме
- [ ] Реализовать кнопку "Зачесть аванс"
- [ ] Реализовать логику зачета (сценарии 1 и 2)

### Этап 5: Редактирование и удаление (2-3 часа)
- [ ] Реализовать редактирование платежа (модальное окно)
- [ ] При редактировании: пересчет связей с реализациями
- [ ] Реализовать удаление платежа с проверкой зависимостей
- [ ] При удалении: возврат `paid_amount` у реализаций

### Этап 6: Визуализация и отчеты (2-3 часа)
- [ ] Обновить таблицу реализаций: показывать "Оплачено X из Y"
- [ ] Добавить блок "Оплаты" в карточку реализации
- [ ] Создать отчет "Дебиторская задолженность" (контрагенты с долгами)
- [ ] Обновить дашборд: виджет "Неоплаченные реализации"

---

## Тестирование

### Сценарии для проверки:

1. **Создание платежа без привязки** → Должен создаться как аванс
2. **Создание платежа на одну реализацию (полная оплата)** → Статус "Оплачено"
3. **Создание платежа на одну реализацию (частичная оплата)** → Статус "Частично оплачено"
4. **Создание платежа на несколько реализаций** → Все статусы обновляются
5. **Переплата** → Реализации оплачены, остаток → аванс
6. **Зачет аванса (хватает)** → Реализации оплачены, аванс уменьшен
7. **Зачет аванса (не хватает)** → Реализации частично оплачены
8. **Редактирование платежа** → Пересчет всех связей
9. **Удаление платежа** → Возврат сумм в `paid_amount`

---

## Примечания

- Все суммы хранятся в `Decimal` для точности расчетов
- Статусы оплаты обновляются автоматически через `update_payment_status()`
- При любом изменении платежа необходимо пересчитывать связанные реализации
- Аванс хранится в `unallocated_amount` платежа, а не в отдельной таблице (упрощение)
- В будущем можно добавить отчет "Движение авансов" для отслеживания истории

