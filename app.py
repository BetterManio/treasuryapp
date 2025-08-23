import os
import datetime as dt
from decimal import Decimal
from typing import Dict, List, Tuple
import time, random

import requests
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
import xml.etree.ElementTree as ET
from extensions import db

from constants import YIELD_FIELDS, TERM_TO_DAYS


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///orders.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

    db.init_app(app)

    with app.app_context():
        from models import Order, YieldDay
        db.create_all()

    return app

app = create_app()

from models import Order, YieldDay

def get_with_retries(url, timeout=10, max_attempts=4, backoff=0.5):
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            session = requests.Session()
            resp = session.get(url, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"Upstream {resp.status_code}", response=resp)
            return resp
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            last_err = e
            if attempt == max_attempts:
                break
            # exponential backoff with a little jitter
            sleep = backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.2)
            time.sleep(sleep)
    raise last_err

def purchased_price_from_yield(face_value, annual_yield, term):
    days_to_maturity = TERM_TO_DAYS[term]
    price_per_100 = 100.0 / (1.0 + float(annual_yield/100) * (float(days_to_maturity) / 365.0))
    return float(face_value) * (price_per_100 / 100.0)


def process_market_order(order: Order):
    if order.order_type != "MARKET" or order.status != "OPEN":
        return
    date = dt.date.today()
    yd = YieldDay.query.filter_by(date=date).first()
    if yd:
        data=yd.as_points()
        for pair in data:
            if pair['term'] == order.term:
                order.executed_price = pair['value']
                purchased_price = purchased_price_from_yield(order.amount, order.executed_price, order.term)
                order.purchased_price = purchased_price
                order.status = "FILLED"
                db.session.commit()
                return


def fetch_yields_latest(date=None):
    if date is None:
        date = dt.date.today()
    year = str(date.year)
    month = str(date.strftime("%m"))
    base_url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview?data=daily_treasury_yield_curve&field_tdr_date_value_month="
    url = base_url+year+month

    last_record = None
    try:
        resp = get_with_retries(url, timeout=20)
        resp.raise_for_status()
        xml_text = resp.text
        root = ET.fromstring(xml_text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
            "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
        }
        entries = root.findall("atom:entry", ns)
        records: List[Tuple[dt.date, Dict[str, float]]] = []
        for e in entries:
            props = e.find("atom:content/m:properties", ns)
            if props is None:
                continue
            date_node = props.find("d:record_date", ns)
            if date_node is None:
                date_node = props.find("d:NEW_DATE", ns)
            if date_node is None or not date_node.text:
                continue
            try:
                dts = date_node.text.split("T")[0]
                rec_date = dt.datetime.strptime(dts, "%Y-%m-%d").date()
            except Exception:
                continue

            values: Dict[str, float] = {}
            for xml_key, pretty in YIELD_FIELDS:
                n = props.find(f"d:{xml_key}", ns)
                if n is not None and n.text not in (None, ""):
                    try:
                        values[pretty] = float(n.text)
                    except ValueError:
                        pass
            if values:
                records.append((rec_date, values))

        if records:
            records.sort(key=lambda r: r[0])
            target = date
            candidates = [r for r in records if r[0] <= target]
            last_record = candidates[-1] if candidates else records[-1]
    except Exception as e:
        print(e)

    if not last_record:
        # Fallback sample (dummy values)
        sample_values = {
            "1 Mo": 5.30,
            "2 Mo": 5.28,
            "3 Mo": 5.25,
            "6 Mo": 5.15,
            "1 Yr": 4.95,
            "2 Yr": 4.60,
            "3 Yr": 4.40,
            "5 Yr": 4.20,
            "7 Yr": 4.10,
            "10 Yr": 4.05,
            "20 Yr": 4.25,
            "30 Yr": 4.15,
        }
        return {"date": dt.date.today().isoformat(), "points": [{"term": k, "value": v} for k, v in sample_values.items()]}

    rec_date, values = last_record
    ordered = [(label, values.get(label)) for _, label in [(k, v) for k, v in YIELD_FIELDS]]
    points = [{"term": term, "value": val} for term, val in ordered if val is not None]
    return {"date": rec_date.isoformat(), "points": points}


@app.get("/")
def index():
    return render_template(
        "index.html",
        orders=[o.as_dict() for o in Order.query.order_by(Order.created_at.desc()).all()],
    )


@app.get("/api/yield-curve")
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
        curve_dict = {p["term"]: p["value"] for p in data.get("points", []) if p.get("term") and p.get("value") is not None}
        if curve_dict:
            db.session.add(YieldDay(date=rec_date, data=curve_dict))
            db.session.commit()
    except Exception as e:
        pass
    return jsonify(data)


@app.post("/orders")
def create_order():
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

    order = Order(term=term, amount=amount, order_type=order_type, timing=timing, limit_price=limit_price, executed_price=None, status="OPEN")
    db.session.add(order)
    db.session.commit()
    try:
        process_market_order(order)
    except Exception as e:
        print(e)
        pass
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
