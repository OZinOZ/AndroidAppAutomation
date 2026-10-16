"""Example 1 - text parsing helpers. Needs no phone and no OCR engine.

Run:  python examples/01_text_parsing.py
"""

from appautomation.naming import address_adapt, get_city_name, get_city_path, get_record_range
from appautomation.text_utils import search_google_info, search_price, to_float

# --- Google Maps summary text as OCR sees it -------------------------------
print(search_google_info("Fastest route 1hr 5 min (23.4 km) Light traffic"))   # (23.4, 65)

# --- Bolt fare text: two prices means "discounted price" is the second one --
BOLT_DISCOUNT = r"^(.*?)[\$S](\d+\.?\d+)(.*? .*?)[\$S](\d+\.?\d+)(.*?)$"
print(search_price("Bolt $25.10 fast $21.30 4 min", BOLT_DISCOUNT, 4))         # 21.3

print(to_float("$12.50"))                                                       # 12.5

# --- Task names ---------------------------------------------------------------
print(get_city_name("BOLT_NYC"), get_city_path("BOLT_NYC"))                    # NYC NYC
print(address_adapt("Times Square", "BOLT_NYC"))                          # NY,Times Square,New York
print(get_record_range(400, 0, now_hour=9))                                     # hourly batch window
