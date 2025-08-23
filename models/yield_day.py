from extensions import db
import datetime as dt
from decimal import Decimal
from constants import YIELD_FIELDS

class YieldDay(db.Model):
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