import datetime as dt

from app.constants import TERM_TO_DAYS
from app.extensions import db
from app.yields.models import YieldDay

from .models import Order


def purchased_price_from_yield(face_value: int, annual_yield: int, term: str) -> float:
    days_to_maturity = TERM_TO_DAYS[term]
    price_per_100 = 100.0 / (
        1.0 + float(annual_yield / 100) * (float(days_to_maturity) / 365.0)
    )
    return round(float(face_value) * (price_per_100 / 100.0),2)


def process_market_order(order: Order) -> None:
    """
    Attempt to execute an order against available yield data.

    Market orders:
        - Fill immediately at the yield for the given term.
        - Update status to 'FILLED'.

    Limit orders:
        - Fill if the day's yield is at or better than the limit.
        - Otherwise, leave status as 'OPEN'.

    Args:
        order (Order): The order to process.
        yield_day (YieldDay): Yield data for the relevant date.

    Returns:
        None. Updates the given order in-place and commits changes.
    """
    if order.order_type != "MARKET" or order.status != "OPEN":
        return
    date = dt.date.today()
    yd = YieldDay.query.filter_by(date=date).first()
    if yd:
        data = yd.as_points()
        for pair in data:
            if pair["term"] == order.term:
                order.executed_price = pair["value"]
                purchased_price = purchased_price_from_yield(
                    order.amount, order.executed_price, order.term
                )
                order.purchased_price = purchased_price
                order.status = "FILLED"
                db.session.commit()
                return
