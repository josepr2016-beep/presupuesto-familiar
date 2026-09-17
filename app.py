"""
app.py
------
Aplicación web de Presupuesto Familiar.

Módulos incluidos:
  /                -> Redirige al Dashboard
  /registro        -> Registro diario de movimientos (mobile-first)
  /movimientos     -> Detalle completo de movimientos de un mes + edición
  /categorias      -> Gestión de categorías (Ingreso/Gasto/Ahorro)
  /cuentas         -> Gestión de cuentas bancarias y efectivo
  /presupuesto     -> Asignación de presupuesto mensual
  /dashboard       -> Consolidación Presupuesto vs Ejecución + alertas
  /conciliacion    -> Cruce saldo real vs saldo teórico

Ejecutar con:  python app.py
"""

import os
from datetime import date, datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func

from config import Config
from extensions import db
from models import (
    Category, Account, Transaction, Budget, BalanceCheck,
    TIPO_INGRESO, TIPO_GASTO, TIPO_AHORRO, TIPOS_VALIDOS, TIPOS_CUENTA_VALIDOS,
)
from utils import format_cop, nombre_mes, rango_mes, mes_actual, periodo_por_defecto


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Aseguramos que exista la carpeta 'instance' donde vive el archivo .db
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)

    # Filtro Jinja para usar {{ valor | cop }} en las plantillas
    app.jinja_env.filters["cop"] = format_cop
    app.jinja_env.globals["nombre_mes"] = nombre_mes

    with app.app_context():
        db.create_all()
        _migrar_esquema()
        _seed_categorias_por_defecto()

    register_routes(app)
    return app


def _migrar_esquema():
    """
    Migración ligera e idempotente (se puede correr muchas veces sin
    problema, incluso en cada arranque del servidor).

    Agrega las columnas budget_month / budget_year a la tabla
    'transactions' si todavía no existen (instalaciones creadas antes de
    esta funcionalidad), y rellena su valor a partir de la fecha real de
    cada movimiento ya guardado. No borra ni modifica ningún otro dato.
    """
    inspector_cols = {"budget_month", "budget_year"}
    with db.engine.connect() as conn:
        for columna in inspector_cols:
            try:
                conn.execute(db.text(f"ALTER TABLE transactions ADD COLUMN {columna} INTEGER"))
                conn.commit()
            except Exception:
                # La columna ya existe (o la tabla aún no existe en un
                # primer arranque limpio, en cuyo caso create_all ya la
                # creó completa) -> no es un error real, seguimos.
                conn.rollback()

    # Backfill: movimientos antiguos que quedaron sin periodo presupuestal
    pendientes = Transaction.query.filter(
        db.or_(Transaction.budget_month.is_(None), Transaction.budget_year.is_(None))
    ).all()
    for t in pendientes:
        t.budget_month = t.date.month
        t.budget_year = t.date.year
    if pendientes:
        db.session.commit()


def _seed_categorias_por_defecto():
    """Si la base de datos está vacía, crea categorías básicas de ejemplo
    para que la app no se vea vacía en el primer uso."""
    if Category.query.count() > 0:
        return

    defaults = [
        ("Salario", TIPO_INGRESO), ("Otros ingresos", TIPO_INGRESO),
        ("Mercado", TIPO_GASTO), ("Arriendo/Hipoteca", TIPO_GASTO),
        ("Servicios públicos", TIPO_GASTO), ("Transporte", TIPO_GASTO),
        ("Salud", TIPO_GASTO), ("Educación", TIPO_GASTO),
        ("Entretenimiento", TIPO_GASTO), ("Otros gastos", TIPO_GASTO),
        ("Fondo de emergencia", TIPO_AHORRO), ("Ahorro programado", TIPO_AHORRO),
    ]
    for nombre, tipo in defaults:
        db.session.add(Category(name=nombre, type=tipo))
    db.session.commit()


def register_routes(app):

    # ------------------------------------------------------------------
    # HOME -> Dashboard
    # ------------------------------------------------------------------
    @app.route("/")
    def index():
        return redirect(url_for("dashboard"))

    # ------------------------------------------------------------------
    # HEALTH CHECK -> usado por el proveedor de nube para verificar que el
    # servidor y la base de datos están respondiendo.
    # ------------------------------------------------------------------
    @app.route("/health")
    def health():
        try:
            db.session.execute(db.text("SELECT 1"))
            return jsonify(status="ok", db="conectada"), 200
        except Exception as e:  # pragma: no cover - solo diagnóstico
            return jsonify(status="error", detalle=str(e)), 500

    # ------------------------------------------------------------------
    # MÓDULO 1: REGISTRO DIARIO (optimizado para celular)
    # ------------------------------------------------------------------
    @app.route("/registro", methods=["GET", "POST"])
    def registro():
        if request.method == "POST":
            try:
                tipo = request.form["type"]
                category_id = int(request.form["category_id"])
                account_id = int(request.form["account_id"])
                amount = float(request.form["amount"])
                fecha = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
                descripcion = request.form.get("description", "").strip()
                usar_mes_anterior = "mes_anterior" in request.form

                if tipo not in TIPOS_VALIDOS:
                    raise ValueError("Tipo de movimiento inválido")
                if amount <= 0:
                    raise ValueError("El monto debe ser mayor a cero")

                budget_month, budget_year = periodo_por_defecto(fecha, usar_mes_anterior)

                nuevo = Transaction(
                    type=tipo, category_id=category_id, account_id=account_id,
                    amount=amount, date=fecha, description=descripcion,
                    budget_month=budget_month, budget_year=budget_year,
                )
                db.session.add(nuevo)
                db.session.commit()

                if usar_mes_anterior:
                    flash(f"Movimiento registrado y contabilizado en el presupuesto de {nombre_mes(budget_month)} {budget_year}.", "success")
                else:
                    flash("Movimiento registrado correctamente.", "success")
            except (KeyError, ValueError) as e:
                flash(f"Error al registrar: {e}", "danger")
            return redirect(url_for("registro"))

        categorias = Category.query.filter_by(active=True).order_by(Category.type, Category.name).all()
        cuentas = Account.query.filter_by(active=True).order_by(Account.name).all()

        # Últimos 15 movimientos para feedback inmediato en el celular
        movimientos = (
            Transaction.query.order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(15).all()
        )
        return render_template(
            "registro.html",
            categorias=categorias, cuentas=cuentas, movimientos=movimientos,
            hoy=date.today().isoformat(),
        )

    @app.route("/registro/eliminar/<int:mov_id>", methods=["POST"])
    def eliminar_movimiento(mov_id):
        mov = Transaction.query.get_or_404(mov_id)
        db.session.delete(mov)
        db.session.commit()
        flash("Movimiento eliminado.", "info")
        return redirect(request.referrer or url_for("registro"))

    # API auxiliar: filtra categorías según el tipo elegido (usado por JS)
    @app.route("/api/categorias/<tipo>")
    def api_categorias_por_tipo(tipo):
        categorias = Category.query.filter_by(type=tipo, active=True).order_by(Category.name).all()
        return jsonify([{"id": c.id, "name": c.name} for c in categorias])

    # ------------------------------------------------------------------
    # MÓDULO NUEVO: DETALLE DE MOVIMIENTOS DE UN MES + EDICIÓN
    # ------------------------------------------------------------------
    @app.route("/movimientos")
    def movimientos():
        mes_actual_num, anio_actual_num = mes_actual()
        month = int(request.args.get("month", mes_actual_num))
        year = int(request.args.get("year", anio_actual_num))
        category_id = request.args.get("category_id", type=int)
        tipo = request.args.get("type")

        # El filtro es por PERIODO PRESUPUESTAL (budget_month/year), no por
        # la fecha real, para que un gasto marcado "mes anterior" aparezca
        # en el mes al que realmente pertenece presupuestalmente.
        query = Transaction.query.filter_by(budget_month=month, budget_year=year)
        if category_id:
            query = query.filter_by(category_id=category_id)
        if tipo in TIPOS_VALIDOS:
            query = query.filter_by(type=tipo)

        lista = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()

        categorias = Category.query.order_by(Category.type, Category.name).all()
        categoria_filtrada = Category.query.get(category_id) if category_id else None

        totales = {
            TIPO_INGRESO: sum(m.amount for m in lista if m.type == TIPO_INGRESO),
            TIPO_GASTO: sum(m.amount for m in lista if m.type == TIPO_GASTO),
            TIPO_AHORRO: sum(m.amount for m in lista if m.type == TIPO_AHORRO),
        }

        return render_template(
            "movimientos.html",
            movimientos=lista, month=month, year=year,
            categorias=categorias, category_id=category_id,
            categoria_filtrada=categoria_filtrada, tipo_filtrado=tipo,
            totales=totales,
        )

    @app.route("/movimientos/editar/<int:mov_id>", methods=["GET", "POST"])
    def editar_movimiento(mov_id):
        mov = Transaction.query.get_or_404(mov_id)

        if request.method == "POST":
            try:
                mov.type = request.form["type"]
                mov.category_id = int(request.form["category_id"])
                mov.account_id = int(request.form["account_id"])
                mov.amount = float(request.form["amount"])
                mov.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
                mov.description = request.form.get("description", "").strip()
                mov.budget_month = int(request.form["budget_month"])
                mov.budget_year = int(request.form["budget_year"])

                if mov.type not in TIPOS_VALIDOS:
                    raise ValueError("Tipo de movimiento inválido")
                if mov.amount <= 0:
                    raise ValueError("El monto debe ser mayor a cero")

                db.session.commit()
                flash("Movimiento actualizado correctamente.", "success")
                return redirect(url_for("movimientos", month=mov.budget_month, year=mov.budget_year))
            except (KeyError, ValueError) as e:
                db.session.rollback()
                flash(f"Error al actualizar: {e}", "danger")
                return redirect(url_for("editar_movimiento", mov_id=mov_id))

        categorias = Category.query.order_by(Category.type, Category.name).all()
        cuentas = Account.query.order_by(Account.name).all()
        return render_template(
            "editar_movimiento.html", mov=mov, categorias=categorias, cuentas=cuentas
        )

    # ------------------------------------------------------------------
    # MÓDULO 2: GESTIÓN DE CATEGORÍAS
    # ------------------------------------------------------------------
    @app.route("/categorias", methods=["GET", "POST"])
    def categorias():
        if request.method == "POST":
            nombre = request.form.get("name", "").strip()
            tipo = request.form.get("type")
            if not nombre or tipo not in TIPOS_VALIDOS:
                flash("Debes indicar un nombre y un tipo válido.", "danger")
            else:
                db.session.add(Category(name=nombre, type=tipo))
                db.session.commit()
                flash("Categoría creada.", "success")
            return redirect(url_for("categorias"))

        todas = Category.query.order_by(Category.type, Category.name).all()
        agrupadas = {
            TIPO_INGRESO: [c for c in todas if c.type == TIPO_INGRESO],
            TIPO_GASTO: [c for c in todas if c.type == TIPO_GASTO],
            TIPO_AHORRO: [c for c in todas if c.type == TIPO_AHORRO],
        }
        return render_template("categorias.html", agrupadas=agrupadas)

    @app.route("/categorias/editar/<int:cat_id>", methods=["POST"])
    def editar_categoria(cat_id):
        cat = Category.query.get_or_404(cat_id)
        cat.name = request.form.get("name", cat.name).strip()
        cat.active = "active" in request.form
        db.session.commit()
        flash("Categoría actualizada.", "success")
        return redirect(url_for("categorias"))

    @app.route("/categorias/eliminar/<int:cat_id>", methods=["POST"])
    def eliminar_categoria(cat_id):
        cat = Category.query.get_or_404(cat_id)
        if cat.transactions or cat.budgets:
            cat.active = False
            db.session.commit()
            flash("La categoría tiene movimientos asociados; se desactivó en lugar de eliminarla.", "warning")
        else:
            db.session.delete(cat)
            db.session.commit()
            flash("Categoría eliminada.", "info")
        return redirect(url_for("categorias"))

    # ------------------------------------------------------------------
    # MÓDULO 3: GESTIÓN DE CUENTAS (bancos / efectivo)
    # ------------------------------------------------------------------
    @app.route("/cuentas", methods=["GET", "POST"])
    def cuentas():
        if request.method == "POST":
            nombre = request.form.get("name", "").strip()
            tipo = request.form.get("type")
            saldo_inicial = request.form.get("initial_balance", "0")
            try:
                saldo_inicial = float(saldo_inicial)
            except ValueError:
                saldo_inicial = 0.0

            if not nombre or tipo not in TIPOS_CUENTA_VALIDOS:
                flash("Debes indicar un nombre y un tipo de cuenta válido.", "danger")
            else:
                db.session.add(Account(name=nombre, type=tipo, initial_balance=saldo_inicial))
                db.session.commit()
                flash("Cuenta creada.", "success")
            return redirect(url_for("cuentas"))

        todas = Account.query.order_by(Account.name).all()
        return render_template("cuentas.html", cuentas=todas)

    @app.route("/cuentas/editar/<int:acc_id>", methods=["POST"])
    def editar_cuenta(acc_id):
        acc = Account.query.get_or_404(acc_id)
        acc.name = request.form.get("name", acc.name).strip()
        acc.active = "active" in request.form
        db.session.commit()
        flash("Cuenta actualizada.", "success")
        return redirect(url_for("cuentas"))

    @app.route("/cuentas/eliminar/<int:acc_id>", methods=["POST"])
    def eliminar_cuenta(acc_id):
        acc = Account.query.get_or_404(acc_id)
        if acc.transactions or acc.balance_checks:
            acc.active = False
            db.session.commit()
            flash("La cuenta tiene movimientos asociados; se desactivó en lugar de eliminarla.", "warning")
        else:
            db.session.delete(acc)
            db.session.commit()
            flash("Cuenta eliminada.", "info")
        return redirect(url_for("cuentas"))

    # ------------------------------------------------------------------
    # MÓDULO 4: PRESUPUESTO MENSUAL (optimizado para PC)
    # ------------------------------------------------------------------
    @app.route("/presupuesto", methods=["GET", "POST"])
    def presupuesto():
        mes_actual_num, anio_actual_num = mes_actual()
        month = int(request.values.get("month", mes_actual_num))
        year = int(request.values.get("year", anio_actual_num))

        if request.method == "POST":
            for key, value in request.form.items():
                if key.startswith("monto_"):
                    cat_id = int(key.split("_")[1])
                    try:
                        monto = float(value) if value else 0.0
                    except ValueError:
                        monto = 0.0

                    presupuesto_existente = Budget.query.filter_by(
                        category_id=cat_id, month=month, year=year
                    ).first()
                    if presupuesto_existente:
                        presupuesto_existente.planned_amount = monto
                    else:
                        db.session.add(Budget(
                            category_id=cat_id, month=month, year=year, planned_amount=monto
                        ))
            db.session.commit()
            flash(f"Presupuesto de {nombre_mes(month)} {year} guardado.", "success")
            return redirect(url_for("presupuesto", month=month, year=year))

        categorias_presupuestables = (
            Category.query.filter(Category.type.in_([TIPO_GASTO, TIPO_AHORRO]), Category.active == True)
            .order_by(Category.type, Category.name).all()
        )
        presupuestos_actuales = {
            b.category_id: b.planned_amount
            for b in Budget.query.filter_by(month=month, year=year).all()
        }

        return render_template(
            "presupuesto.html",
            categorias=categorias_presupuestables,
            presupuestos=presupuestos_actuales,
            month=month, year=year,
        )

    # ------------------------------------------------------------------
    # MÓDULO 5: DASHBOARD - Presupuesto vs Ejecutado + alertas
    # ------------------------------------------------------------------
    @app.route("/dashboard")
    def dashboard():
        mes_actual_num, anio_actual_num = mes_actual()
        month = int(request.args.get("month", mes_actual_num))
        year = int(request.args.get("year", anio_actual_num))

        # Todos los totales del Dashboard se calculan por PERIODO
        # PRESUPUESTAL (budget_month/budget_year), no por fecha real, para
        # que los movimientos marcados "mes anterior" cuenten en el mes al
        # que presupuestalmente pertenecen.
        def total_ejecutado(tipo):
            resultado = (
                db.session.query(func.sum(Transaction.amount))
                .filter(
                    Transaction.type == tipo,
                    Transaction.budget_month == month,
                    Transaction.budget_year == year,
                )
                .scalar()
            )
            return resultado or 0.0

        total_ingresos = total_ejecutado(TIPO_INGRESO)
        total_gastos = total_ejecutado(TIPO_GASTO)
        total_ahorros = total_ejecutado(TIPO_AHORRO)
        balance_neto = total_ingresos - total_gastos - total_ahorros

        categorias = (
            Category.query.filter(Category.type.in_([TIPO_GASTO, TIPO_AHORRO]))
            .order_by(Category.type, Category.name).all()
        )

        detalle = []
        for cat in categorias:
            presupuestado = (
                Budget.query.filter_by(category_id=cat.id, month=month, year=year).first()
            )
            monto_presupuestado = presupuestado.planned_amount if presupuestado else 0.0

            ejecutado = (
                db.session.query(func.sum(Transaction.amount))
                .filter(
                    Transaction.category_id == cat.id,
                    Transaction.budget_month == month,
                    Transaction.budget_year == year,
                )
                .scalar()
            ) or 0.0

            if monto_presupuestado > 0:
                porcentaje = round((ejecutado / monto_presupuestado) * 100, 1)
            else:
                porcentaje = 100.0 if ejecutado > 0 else 0.0

            if porcentaje >= 100:
                nivel_alerta = "danger"
            elif porcentaje >= 80:
                nivel_alerta = "warning"
            else:
                nivel_alerta = "success"

            if monto_presupuestado > 0 or ejecutado > 0:
                detalle.append({
                    "categoria": cat,
                    "presupuestado": monto_presupuestado,
                    "ejecutado": ejecutado,
                    "porcentaje": min(porcentaje, 999),
                    "nivel_alerta": nivel_alerta,
                    "diferencia": monto_presupuestado - ejecutado,
                })

        return render_template(
            "dashboard.html",
            month=month, year=year,
            total_ingresos=total_ingresos, total_gastos=total_gastos,
            total_ahorros=total_ahorros, balance_neto=balance_neto,
            detalle=detalle,
        )

    # ------------------------------------------------------------------
    # MÓDULO 6: CONCILIACIÓN DE EFECTIVO Y CUENTAS
    # ------------------------------------------------------------------
    @app.route("/conciliacion", methods=["GET", "POST"])
    def conciliacion():
        if request.method == "POST":
            account_id = int(request.form["account_id"])
            fecha = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            saldo_real = float(request.form["real_balance"])
            nota = request.form.get("note", "").strip()

            db.session.add(BalanceCheck(
                account_id=account_id, date=fecha, real_balance=saldo_real, note=nota
            ))
            db.session.commit()
            flash("Conciliación registrada.", "success")
            return redirect(url_for("conciliacion"))

        cuentas = Account.query.filter_by(active=True).order_by(Account.name).all()

        resumen = []
        for cuenta in cuentas:
            saldo_teorico = cuenta.theoretical_balance()
            ultima_conciliacion = (
                BalanceCheck.query.filter_by(account_id=cuenta.id)
                .order_by(BalanceCheck.date.desc(), BalanceCheck.id.desc()).first()
            )
            saldo_real = ultima_conciliacion.real_balance if ultima_conciliacion else None
            diferencia = (saldo_real - saldo_teorico) if saldo_real is not None else None

            resumen.append({
                "cuenta": cuenta,
                "saldo_teorico": saldo_teorico,
                "saldo_real": saldo_real,
                "diferencia": diferencia,
                "fecha_conciliacion": ultima_conciliacion.date if ultima_conciliacion else None,
            })

        historial = (
            BalanceCheck.query.order_by(BalanceCheck.date.desc(), BalanceCheck.id.desc()).limit(20).all()
        )

        return render_template(
            "conciliacion.html", cuentas=cuentas, resumen=resumen,
            historial=historial, hoy=date.today().isoformat(),
        )

    return app


# Punto de entrada para ejecución local: python app.py
app = create_app()

if __name__ == "__main__":
    # host="0.0.0.0" permite acceder desde el celular usando la IP local
    # del computador (ej: http://192.168.1.10:5000) dentro de la misma red WiFi.
    app.run(host="0.0.0.0", port=5000, debug=True)
