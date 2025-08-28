from app.main import bp
from app.orders.models import Order
from flask import render_template


@bp.get("/")
def index():
    orders = [o.as_dict() for o in Order.query.order_by(Order.created_at.desc()).all()]
    return render_template(
        "index.html",
        orders=orders,
    )
