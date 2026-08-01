"""
config.py
---------
Configuración central de la aplicación.
Todos los valores sensibles/ajustables se manejan aquí para no
tener "números mágicos" ni rutas repartidas por el código.
"""

import os

# Carpeta base del proyecto (donde vive este archivo)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _resolver_database_uri() -> str:
    """
    Resuelve la URI de la base de datos según el entorno:

    - En LOCAL (sin variable DATABASE_URL): usa SQLite dentro de 'instance/'.
      Perfecto para desarrollo/pruebas en el computador.

    - En LA NUBE (con DATABASE_URL definida, ej. Render/Railway): usa esa
      base de datos (normalmente PostgreSQL), que es persistente y no
      depende de que ningún computador esté encendido.

    Nota técnica: algunos proveedores (Render, Heroku) entregan la URL con
    el prefijo antiguo 'postgres://', pero SQLAlchemy 2.x requiere
    'postgresql://'. Se corrige automáticamente para evitar errores de
    conexión al desplegar.
    """
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        # Sin variable de entorno -> modo local con SQLite
        return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'presupuesto.db')}"

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return database_url


class Config:
    # Clave usada por Flask para firmar la sesión/cookies.
    # En producción SIEMPRE se debe definir como variable de entorno propia
    # (nunca dejar la de por defecto en un servidor público).
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")

    SQLALCHEMY_DATABASE_URI = _resolver_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Evita conexiones "muertas" que algunos proveedores de Postgres en la
    # nube cierran tras un tiempo de inactividad (previene errores 500
    # intermitentes tras periodos sin tráfico).
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Nombre de la moneda usada en toda la aplicación
    MONEDA = "COP"

    # True cuando la app corre en la nube (se usó DATABASE_URL externa)
    ES_ENTORNO_NUBE = bool(os.environ.get("DATABASE_URL"))
