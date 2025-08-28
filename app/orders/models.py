import datetime as dt

from app.extensions import db


class Order(db.Model):
    """
    Represents a Treasury order placed by a user.

    Attributes:
        id (int): Primary key.
        term (str): The order's maturity term (e.g. '1M', '10Y').
        amount (int): Face value of the order in dollars (must be a multiple of 1000).
        order_type (str): Type of order, e.g. 'Market' or 'Limit'.
        timing (str): Order timing, e.g. 'Day Only', 'GTC' (Good Till Canceled), or 'FOK' (Fill or Kill).
        limit_price (float, optional): The limit yield (percent) if this is a limit order.
        executed_price (float, optional): The yield at which the order was actually executed.
        status (str): Current status — 'OPEN', 'FILLED', or 'CANCELLED'.
        created_at (datetime): Timestamp of order creation.
    """
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(16), nullable=False)
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)
    order_type = db.Column(db.String(10), nullable=False, default="MARKET")
    timing = db.Column(db.String(10), nullable=False, default="DAY")
    status = db.Column(db.String(10), nullable=False, default="OPEN")
    limit_price = db.Column(db.Numeric(precision=6, scale=3), nullable=True)
    executed_price = db.Column(db.Numeric(precision=6, scale=3), nullable=True)
    purchased_price = db.Column(db.Numeric(precision=6, scale=3), nullable=True)

    def as_dict(self):
        return {
            "id": self.id,
            "term": self.term,
            "amount": float(self.amount),
            "created_at": self.created_at.isoformat(),
            "order_type": self.order_type,
            "timing": self.timing,
            "status": self.status,
            "limit_price": (
                float(self.limit_price) if self.limit_price is not None else None
            ),
            "executed_price": (
                float(self.executed_price) if self.executed_price is not None else None
            ),
            "purchased_price": (
                float(self.purchased_price)
                if self.purchased_price is not None
                else None
            ),
        }
