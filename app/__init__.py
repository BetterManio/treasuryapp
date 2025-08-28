from config import Config
from flask import Flask

from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        from app.orders.models import Order
        from app.yields.models import YieldDay

        db.create_all()

    # Register blueprints here

    from app.main import bp as main_bp

    app.register_blueprint(main_bp)
    from app.orders import bp as orders_bp

    app.register_blueprint(orders_bp)
    from app.yields import bp as yields_bp

    app.register_blueprint(yields_bp)

    return app
