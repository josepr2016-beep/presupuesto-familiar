"""
extensions.py
-------------
Aquí se instancia SQLAlchemy de forma independiente para evitar
importaciones circulares entre app.py y models.py.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
