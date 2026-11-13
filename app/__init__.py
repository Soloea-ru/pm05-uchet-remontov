from datetime import date, datetime
from pathlib import Path

from flask import Flask, render_template

from .config import Config, ROOT, load_env_file
from .models import db, init_db


def format_dmy(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    text = str(value)
    try:
        if len(text) > 10:
            return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
        return datetime.strptime(text[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return text


def create_app(config=None):
    load_env_file()
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    Config.apply(app)
    if config:
        app.config.update(config)

    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    engine_options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
    if uri.startswith("sqlite"):
        connect_args = dict(engine_options.get("connect_args") or {})
        connect_args["check_same_thread"] = False
        engine_options["connect_args"] = connect_args
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    db.init_app(app)

    from .routes import bp, inject_template_context

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

    with app.app_context():
        init_db()
    return app
