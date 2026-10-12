from flask import Flask, jsonify, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from config import Config

db = SQLAlchemy()
migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        raise RuntimeError('Задайте DATABASE_URL у .env (див. .env.example).')
    db.init_app(app)
    from app import models  # noqa: F401
    migrate.init_app(app, db)
    from app.routes import bp
    app.register_blueprint(bp)

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {
            400: 'Некоректний запит.', 404: 'Запис або сторінку не знайдено.',
            405: 'Метод не підтримується.', 413: 'Запит завеликий.',
            415: 'Надішліть дані у форматі JSON.',
        }
        return jsonify(error=messages.get(error.code, 'Помилка запиту.')), error.code

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.error('Database operation failed: %s', type(error).__name__)
        return jsonify(error='База даних недоступна. Перевірте підключення та міграції.'), 503

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    return app
