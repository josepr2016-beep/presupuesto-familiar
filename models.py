"""
models.py
---------
Define las tablas de la base de datos usando Flask-SQLAlchemy (ORM).

Tablas:
    Category        -> Categorías de Ingreso / Gasto / Ahorro
    Account         -> Cuentas bancarias o efectivo
    Transaction     -> Movimientos diarios (ingresos, gastos, ahorros)
    Budget          -> Presupuesto asignado por categoría/mes/año
    BalanceCheck    -> Registro histórico de conciliación (saldo real ingresado)
"""

from datetime import date, datetime
from extensions import db

# ---------------------------------------------------------------------------
# Constantes de tipos (se usan como "Enum" simples basados en texto para que
# SQLite las guarde de forma legible y sea fácil de depurar/exportar a Excel)
# ---------------------------------------------------------------------------
TIPO_INGRESO = "ingreso"
TIPO_GASTO = "gasto"
TIPO_AHORRO = "ahorro"
TIPOS_VALIDOS = [TIPO_INGRESO, TIPO_GASTO, TIPO_AHORRO]

TIPO_CUENTA_BANCO = "banco"
TIPO_CUENTA_EFECTIVO = "efectivo"
TIPOS_CUENTA_VALIDOS = [TIPO_CUENTA_BANCO, TIPO_CUENTA_EFECTIVO]


class Category(db.Model):
    """Categoría personalizada: pertenece a uno de los 3 grandes grupos."""
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # ingreso | gasto | ahorro
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    transactions = db.relationship("Transaction", backref="category", lazy=True)
    budgets = db.relationship("Budget", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name} ({self.type})>"


class Account(db.Model):
    """Cuenta bancaria o efectivo disponible en el hogar."""
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # banco | efectivo
    initial_balance = db.Column(db.Float, nullable=False, default=0.0)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship("Transaction", backref="account", lazy=True)
    balance_checks = db.relationship("BalanceCheck", backref="account", lazy=True)

    def theoretical_balance(self, up_to_date=None):
        """
        Calcula el saldo TEÓRICO de la cuenta:
        saldo_inicial + ingresos - gastos - ahorros (todos los movimientos
        registrados en esta cuenta hasta la fecha indicada).
        """
        up_to_date = up_to_date or date.today()
        query = Transaction.query.filter(
            Transaction.account_id == self.id,
            Transaction.date <= up_to_date,
        )
        total = self.initial_balance
        for t in query.all():
            if t.type == TIPO_INGRESO:
                total += t.amount
            else:  # gasto o ahorro: ambos "salen" de la cuenta de origen
                total -= t.amount
        return total

    def __repr__(self):
        return f"<Account {self.name} ({self.type})>"


class Transaction(db.Model):
    """Movimiento diario: ingreso, gasto o ahorro."""
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # ingreso | gasto | ahorro
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount} {self.date}>"


class Budget(db.Model):
    """Presupuesto proyectado para una categoría en un mes/año determinado."""
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    planned_amount = db.Column(db.Float, nullable=False, default=0.0)

    __table_args__ = (
        db.UniqueConstraint("category_id", "month", "year", name="uq_budget_categoria_mes_anio"),
    )

    def __repr__(self):
        return f"<Budget cat={self.category_id} {self.month}/{self.year} = {self.planned_amount}>"


class BalanceCheck(db.Model):
    """
    Registro histórico de conciliación: el usuario anota el saldo REAL
    (el que ve en el banco/billetera) en una fecha determinada, para
    compararlo contra el saldo teórico calculado por el sistema.
    """
    __tablename__ = "balance_checks"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    real_balance = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BalanceCheck acc={self.account_id} real={self.real_balance} {self.date}>"
