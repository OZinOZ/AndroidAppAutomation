import pytest

from appautomation.naming import (
    address_adapt, get_city_name, get_city_path, get_record_range, get_task_key,
)
from appautomation.text_utils import (
    search_google_info, search_google_small, search_price, to_float, to_int,
)

BOLT_DISCOUNT = r"^(.*?)[\$S](\d+\.?\d+)(.*? .*?)[\$S](\d+\.?\d+)(.*?)$"


def test_to_float_and_int():
    assert to_float("$12.50") == 12.5
    assert to_float("n/a") == 0.0
    assert to_int("20 km") == 20


def test_google_info_with_hours():
    assert search_google_info("Fastest 1hr 5 min (23.4 km) traffic") == (23.4, 65)


def test_google_info_no_match():
    assert search_google_info("nothing here") == (0.0, 0)


def test_google_small_fallback():
    assert search_google_small("12 min away 5.2 km") == (5.2, 12)


def test_search_price_discount_group():
    assert search_price("Bolt $25.10 fast $21.30 4 min", BOLT_DISCOUNT, 4) == 21.3


def test_search_price_missing_decimal_point():
    assert search_price("x $2130 y z", r"^(.*?)[\$S](\d+)(.*? .*?)$", 2) == 21.3


@pytest.mark.parametrize("task,city,path,key", [
    ("BOLT_NYC", "NYC", "NYC", "BOLT"),
    ("MIA_DROPOFF", "MIA", "MIA_DROPOFF", "DEFAULT"),
    ("NYC", "NYC", "NYC", "DEFAULT"),
    ("TIME_NYC", "TIME_NYC", "TIME_NYC", "TIME"),
])
def test_task_names(task, city, path, key):
    assert get_city_path(task) == path
    assert get_task_key(task) == key
    if task != "TIME_NYC":
        assert get_city_name(task) == city


def test_address_adapt():
    assert address_adapt("Times Square", "BOLT_NYC") == "NY,Times Square,New York"
    assert address_adapt("Union Square", "SFO").endswith(",San Francisco")
    # All bundled cities are domestic: no country suffix is appended
    assert "United States" not in address_adapt("Times Square", "BOLT_NYC")


def test_record_range():
    assert get_record_range(1, 10, 9) == (1, 10)
    assert get_record_range(400, 0, 9) == (40 % 101, (40 + 3) % 101)
