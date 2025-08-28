import datetime as dt

from app.extensions import db
from flask import jsonify, request

from . import bp
from .models import YieldDay
from .utils import fetch_yields_latest


@bp.get("/api/yield-curve")
def api_yield_curve():
    date_str = request.args.get("date")
    date = None
    if date_str:
        try:
            date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if date is None:
        date = dt.date.today()
    yd = YieldDay.query.filter_by(date=date).first()
    if yd:
        return jsonify({"date": date.isoformat(), "points": yd.as_points()})
    data = fetch_yields_latest(date)
    try:
        rec_date = dt.datetime.strptime(data["date"], "%Y-%m-%d").date()
        curve_dict = {
            p["term"]: p["value"]
            for p in data.get("points", [])
            if p.get("term") and p.get("value") is not None
        }
        if curve_dict:
            db.session.add(YieldDay(date=rec_date, data=curve_dict))
            db.session.commit()
    except Exception as e:
        pass
    return jsonify(data)
