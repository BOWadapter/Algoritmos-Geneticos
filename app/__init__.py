from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    db.init_app(app)

    with app.app_context():
        from . import models
        from .routes import bp as main_bp
        app.register_blueprint(main_bp)
        db.create_all()  # Crea la BD (SQLite) al primer arranque

    return app
