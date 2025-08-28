import datetime as dt
import random
import time
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Tuple


import requests
from app.constants import YIELD_FIELDS


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

# --- helpers (all private/module-local) ---

def _month_url_for(date: dt.date) -> str:
    year = str(date.year)
    month = date.strftime("%m")
    base = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview"
    return f"{base}?data=daily_treasury_yield_curve&field_tdr_date_value_month={year}{month}"

def _parse_records(xml_text: str) -> List[Tuple[dt.date, Dict[str, float]]]:
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
        "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
    }
    root = ET.fromstring(xml_text)
    records: List[Tuple[dt.date, Dict[str, float]]] = []

    for e in root.findall("atom:entry", ns):
        props = e.find("atom:content/m:properties", ns)
        if props is None:
            continue
        date_node = props.find("d:record_date", ns)
        if date_node is None:
            # your code checks NEW_DATE (upper) as an alternative
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

    return records

def _pick_latest_on_or_before(records: List[Tuple[dt.date, Dict[str, float]]],
                              target: dt.date) -> Optional[Tuple[dt.date, Dict[str, float]]]:
    if not records:
        return None
    records.sort(key=lambda r: r[0])
    candidates = [r for r in records if r[0] <= target]
    return candidates[-1] if candidates else records[-1]

def _fallback_payload(today: dt.date) -> Dict:
    sample_values = {
        "1 Mo": 5.30, "2 Mo": 5.28, "3 Mo": 5.25, "6 Mo": 5.15,
        "1 Yr": 4.95, "2 Yr": 4.60, "3 Yr": 4.40, "5 Yr": 4.20,
        "7 Yr": 4.10, "10 Yr": 4.05, "20 Yr": 4.25, "30 Yr": 4.15,
    }
    return {
        "date": today.isoformat(),
        "points": [{"term": k, "value": v} for k, v in sample_values.items()],
    }

def _points_from(values: Dict[str, float]) -> List[Dict]:
    ordered = [(label, values.get(label)) for _, label in YIELD_FIELDS]
    return [{"term": term, "value": val} for term, val in ordered if val is not None]


def fetch_yields_latest(date: Optional[dt.date] = None) -> Dict:
    """
    Fetch the latest Treasury yield curve data from the Treasury.gov XML feed.
    Returns: {"date": "YYYY-MM-DD", "points": [{"term": "...", "value": ...}, ...]}
    """
    if date is None:
        date = dt.date.today()

    last_record = None
    try:
        url = _month_url_for(date)
        resp = get_with_retries(url, timeout=20)
        resp.raise_for_status()
        records = _parse_records(resp.text)
        last_record = _pick_latest_on_or_before(records, date)
    except Exception as e:
        print(e)

    if not last_record:
        return _fallback_payload(dt.date.today())

    rec_date, values = last_record
    return {"date": rec_date.isoformat(), "points": _points_from(values)}
