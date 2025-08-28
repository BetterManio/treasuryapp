import datetime as dt

from app.constants import YIELD_FIELDS
from app.extensions import db


class YieldDay(db.Model):
    """
    Stores Treasury yield curve data for a specific date.

    Attributes:
        id (int): Primary key.
        date (date): The calendar date of the yield data.
        data (JSON): Mapping of term → yield percent, e.g.
            {
                "1M": 5.12,
                "2Y": 4.47,
                "10Y": 3.95
            }
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, index=True)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

    def as_points(self):
        pts = []
        for _, label in YIELD_FIELDS:
            v = self.data.get(label)
            if v is not None:
                pts.append({"term": label, "value": float(v)})
        return pts
