"""
utils.py
--------
Funciones de apoyo reutilizables en toda la aplicación:
 - Formato de moneda en Pesos Colombianos (COP)
 - Nombres de meses en español
 - Cálculo de rangos de fechas de un mes
 - Cálculo del mes anterior (para el periodo presupuestal de un movimiento)
"""

import calendar
from datetime import date

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def format_cop(value):
    """
    Formatea un número como Peso Colombiano: $ 1.500.000
    Usa punto como separador de miles y sin decimales (convención local).
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    entero = round(value)
    signo = "-" if entero < 0 else ""
    formateado = "{:,.0f}".format(abs(entero)).replace(",", ".")
    return f"{signo}$ {formateado}"


def nombre_mes(mes: int) -> str:
    return MESES_ES.get(mes, str(mes))


def rango_mes(month: int, year: int):
    """Devuelve (primer_dia, ultimo_dia) del mes/año indicados."""
    primer_dia = date(year, month, 1)
    ultimo_dia_num = calendar.monthrange(year, month)[1]
    ultimo_dia = date(year, month, ultimo_dia_num)
    return primer_dia, ultimo_dia


def mes_actual():
    hoy = date.today()
    return hoy.month, hoy.year


def mes_anterior(month: int, year: int):
    """Devuelve (mes, año) del mes inmediatamente anterior al indicado."""
    if month == 1:
        return 12, year - 1
    return month - 1, year


def periodo_por_defecto(fecha: date, usar_mes_anterior: bool = False):
    """
    Calcula el (mes, año) de PRESUPUESTO para un movimiento, a partir de
    su fecha real. Si usar_mes_anterior=True, se desplaza un mes hacia
    atrás (ej: un gasto del 2 de marzo que corresponde al presupuesto
    de febrero).
    """
    if usar_mes_anterior:
        return mes_anterior(fecha.month, fecha.year)
    return fecha.month, fecha.year
