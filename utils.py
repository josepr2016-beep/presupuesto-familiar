"""
utils.py
--------
Funciones de apoyo reutilizables en toda la aplicación:
 - Formato de moneda en Pesos Colombianos (COP)
 - Nombres de meses en español
 - Cálculo de rangos de fechas de un mes
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
    # Formateamos con separador de miles "," (estándar de Python) y luego
    # lo reemplazamos por "." para seguir la convención colombiana.
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
