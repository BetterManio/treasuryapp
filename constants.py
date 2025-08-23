from typing import List, Tuple

# Mapping of XML field names to pretty labels & plot order
YIELD_FIELDS: List[Tuple[str, str]] = [
    ("BC_1MONTH", "1 Mo"),
    ("BC_2MONTH", "2 Mo"),
    ("BC_3MONTH", "3 Mo"),
    ("BC_6MONTH", "6 Mo"),
    ("BC_1YEAR", "1 Yr"),
    ("BC_2YEAR", "2 Yr"),
    ("BC_3YEAR", "3 Yr"),
    ("BC_5YEAR", "5 Yr"),
    ("BC_7YEAR", "7 Yr"),
    ("BC_10YEAR", "10 Yr"),
    ("BC_20YEAR", "20 Yr"),
    ("BC_30YEAR", "30 Yr"),
]

TERM_TO_DAYS = {
    "1 Mo": 30,
    "2 Mo": 60,
    "3 Mo": 91,    # 13-week bill
    "6 Mo": 182,   # 26-week bill
    "1 Yr": 365,
    "2 Yr": 2 * 365,
    "3 Yr": 3 * 365,
    "5 Yr": 5 * 365,
    "7 Yr": 7 * 365,
    "10 Yr": 10 * 365,
    "20 Yr": 20 * 365,
    "30 Yr": 30 * 365,
}