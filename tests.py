import unittest
from app.orders.utils import purchased_price_from_yield
import datetime as dt
from textwrap import dedent
from unittest.mock import patch

from app.yields.utils import fetch_yields_latest

from app.yields.utils import _parse_records, _pick_latest_on_or_before, _points_from


XML = dedent("""\
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:NEW_DATE>2025-08-20T00:00:00</d:NEW_DATE>
        <d:BC_1MONTH>5.10</d:BC_1MONTH>
        <d:BC_10YEAR>4.20</d:BC_10YEAR>
      </m:properties>
    </content>
  </entry>
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:NEW_DATE>2025-08-22T00:00:00</d:NEW_DATE>
        <d:BC_1MONTH>5.12</d:BC_1MONTH>
        <d:BC_10YEAR>4.18</d:BC_10YEAR>
      </m:properties>
    </content>
  </entry>
</feed>
""")
             
XML2 = dedent("""\
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:record_date>2025-08-22T00:00:00</d:record_date>
        <d:bc_1month>5.12</d:bc_1month>
        <d:bc_3month>5.01</d:bc_3month>
        <d:bc_10year>4.18</d:bc_10year>
      </m:properties>
    </content>
  </entry>
</feed>
""")
             
class TestPricing(unittest.TestCase):
    def test_purchased_price_from_yield_1m(self):
        price = purchased_price_from_yield(1000, 4.47, "1 Mo")
        self.assertAlmostEqual(price, 996.34, places=2)

    def test_purchased_price_from_yield_6m(self):
        price = purchased_price_from_yield(1000, 5.15, "6 Mo")
        self.assertAlmostEqual(price, 974.96, places=2)

    def test_purchased_price_from_yield_1y(self):
        price = purchased_price_from_yield(1000, 4.95, "1 Yr")
        self.assertAlmostEqual(price, 952.83, places=2)

class TestYieldParsing(unittest.TestCase):
    def test_parse_records_two_entries(self):
        records = _parse_records(XML)
        self.assertEqual(len(records), 2)
        self.assertIsInstance(records[0][0], dt.date)
        self.assertIsInstance(records[0][1], dict)
        # spot-check a field
        self.assertIn("1 Mo", records[0][1])

    def test_pick_latest_on_or_before(self):
        records = _parse_records(XML)
        picked = _pick_latest_on_or_before(records, dt.date(2025, 8, 21))
        self.assertIsNotNone(picked)
        self.assertEqual(picked[0].isoformat(), "2025-08-20")
        picked2 = _pick_latest_on_or_before(records, dt.date(2025, 8, 22))
        self.assertEqual(picked2[0].isoformat(), "2025-08-22")

    def test_points_from_orders_labels(self):
        records = _parse_records(XML)
        _, values = records[-1]
        points = _points_from(values)
        labels = [p["term"] for p in points]
        # Should include our mapped labels in canonical order
        self.assertIn("1 Mo", labels)
        self.assertIn("10 Yr", labels)

class DummyResp:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("bad status")

class TestFetchLatest(unittest.TestCase):
    @patch("app.yields.utils.get_with_retries")
    def test_fetch_yields_latest_happy_path(self, mock_get):
        mock_get.return_value = DummyResp(XML, 200)
        data = fetch_yields_latest(dt.date(2025, 8, 22))
        self.assertEqual(data["date"], "2025-08-22")
        m = {p["term"]: p["value"] for p in data["points"]}
        self.assertAlmostEqual(m["1 Mo"], 5.12)
        self.assertAlmostEqual(m["10 Yr"], 4.18)

    @patch("app.yields.utils.get_with_retries")
    def test_fetch_yields_latest_fallback_on_error(self, mock_get):
        mock_get.side_effect = Exception("network down")
        data = fetch_yields_latest(dt.date(2025, 8, 22))
        self.assertIn("date", data)
        self.assertIn("points", data)
        self.assertGreater(len(data["points"]), 0)

if __name__ == "__main__":
    unittest.main()
