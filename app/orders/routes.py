from decimal import Decimal

from app.constants import YIELD_FIELDS
from app.extensions import db
from flask import redirect, request, url_for

from . import bp
from .models import Order
from .utils import process_market_order


@bp.post("/orders")
def create_order():
    """
    Create and persist a new order in the database.

    We would make this a form (Flask-WTF) in the future

    Args:
        term (str): Maturity term (e.g. '1M', '10Y').
        amount (int): Face value of the order in dollars (must be a multiple of 1000).
        order_type (str): 'Market' or 'Limit'.
        timing (str): Order timing — 'Day Only', 'GTC' (Good Till Cancelled), or 'FOK' (Fill or Kill).
        limit_price (float, optional): Yield percent at which to execute if this is a limit order.

    Returns:
        Redirect to index page.
    """
    term = request.form.get("term")
    amount_raw = request.form.get("amount")
    valid_terms = [label for _, label in YIELD_FIELDS]
    if term not in valid_terms:
        return redirect(url_for("index"))
    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise ValueError
    except Exception:
        return redirect(url_for("index"))

    order_type = (request.form.get("order_type") or "MARKET").upper()
    timing = (request.form.get("timing") or "DAY").upper()

    if order_type not in ("MARKET", "LIMIT"):
        return redirect(url_for("index"))

    if order_type == "MARKET":
        timing = "DAY"
        limit_price = None
    else:
        if timing not in ("DAY", "GTC", "FOK"):
            return redirect(url_for("index"))
        lp_raw = request.form.get("limit_price")
        try:
            limit_price = Decimal(lp_raw)
            if limit_price <= 0:
                raise ValueError
        except Exception:
            return redirect(url_for("index"))

    order = Order(
        term=term,
        amount=amount,
        order_type=order_type,
        timing=timing,
        limit_price=limit_price,
        executed_price=None,
        status="OPEN",
    )
    db.session.add(order)
    db.session.commit()
    try:
        process_market_order(order)
    except Exception as e:
        print(e)
        pass
    return redirect(url_for("main.index"))
