import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template

ROOT = Path(__file__).resolve().parent.parent


def format_dmy(value):
    if not value:
        return "—"
    text = str(value)
    try:
        if len(text) > 10:
            return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
        return datetime.strptime(text[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return text


def create_app(config=None):
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "pm05-dev-key")
    app.config["DATABASE"] = str(ROOT / "instance" / "app.db")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if config:
        app.config.update(config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    from .db import close_db, init_db
    from .routes import bp, inject_template_context

    app.teardown_appcontext(close_db)
    app.context_processor(inject_template_context)
    app.register_blueprint(bp)
    app.add_template_filter(format_dmy, "dmy")

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "error.html",
            code=403,
            title="Недостаточно прав",
            message="Раздел доступен только диспетчеру.",
        ), 403

    @app.errorhandler(404)
    def missing(_error):
        return render_template(
            "error.html",
            code=404,
            title="Страница не найдена",
            message="Такой страницы нет. Вернитесь на главную.",
        ), 404

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template(
            "error.html",
            code=400,
            title="Запрос устарел",
            message="Обновите страницу и отправьте форму ещё раз.",
        ), 400

    if not Path(app.config["DATABASE"]).exists():
        with app.app_context():
            init_db()
    return app
