"""Shared helpers: city metadata, address qualification, price parsing and
route loading."""
import os
import re

import pandas as pd

from core.config import CONFIG, routes_dir

# Screenshot-type prefixes.  These are opaque codes that link capture output
# to OCR crop regions; see config.yaml -> crop_ranges.
FARE_SUFFIXES = ['D', 'U', 'B']

# Cities used to qualify addresses for search (code -> display name)
city_map = CONFIG.get('city_map', {})
# State suffix appended to addresses where required (code -> state)
citi_state = CONFIG.get('city_state', {})
# Country suffix appended for cross-border cities (code -> country)
city_country = CONFIG.get('city_country', {})
city_reverse = dict(zip(city_map.values(), city_map.keys()))

# Address variants recognised in the qualification step
SERVICES = ['MAX', 'PICKUP', 'DROPOFF', 'EATS', 'DELIVER', 'TRAVEL', 'SELECT']
PREFIXES = ['APP']


def get_city_name(city: str) -> str:
    parts = city.split('_')
    if parts[0] in PREFIXES:
        return city[len(parts[0]) + 1: len(parts[0]) + 4]
    elif parts[-1] in SERVICES:
        return city[:3]
    return city


def get_city_path(city: str) -> str:
    parts = city.split('_')
    if parts[0] in PREFIXES:
        return city[len(parts[0]) + 1:]
    return city


def file_exist(path: str, city: str, date: str, idx: int, suffix: str) -> bool:
    return os.path.exists(os.path.join(path, f"{city}{date}{idx:03d}{suffix}.png"))


def file_exist_multi(path: str, city: str, date: str, idx: int, suffix: str) -> tuple:
    file_path = os.path.join(path, f"{city}{date}{idx:03d}{suffix}.png")
    return os.path.exists(file_path), file_path


def address_adapt(origin: str, city: str) -> str:
    """Qualify a plain address with state/country so that in-app search
    resolves it unambiguously."""
    abbr = get_city_name(city)
    state = citi_state.get(abbr, '')
    new_addr = origin if abbr not in city_map else state + ',' + origin + ',' + city_map[abbr]
    if abbr in city_country and city_country[abbr] not in new_addr:
        new_addr = new_addr + ',' + city_country[abbr]
    return new_addr


def address_origin(adapts: str, city: str) -> str:
    if city in city_map and city_map[city] in adapts:
        return adapts.removesuffix(',' + city_map[city])
    return adapts


def get_record_range(input_start: int, input_end: int) -> tuple:
    return input_start, input_end


def to_float(price: str) -> float:
    price = re.sub("[^0-9.]", "", str(price)).strip()
    try:
        return float(price)
    except ValueError:
        return 0.0


def to_int(price: str) -> int:
    price = re.sub("[^0-9]", "", str(price)).strip()
    try:
        return int(price)
    except ValueError:
        return 0


def search_google_info(map_info: str) -> tuple:
    """Extract (distance km, duration min) from a map summary string."""
    pattern = r"^(.*? ?)(\dhr ?)?(\d+) ?min ?\((\d+.?\d?) ?km\).*$"
    match = re.match(pattern, ' '.join(map_info.split()))
    if match:
        if match.group(2):
            return to_float(match.group(4)), 60 * to_int(match.group(2)) + to_int(match.group(3))
        return to_float(match.group(4)), to_int(match.group(3))
    return 0.0, 0


def search_google_small(map_info: str) -> tuple:
    map_new = ' '.join(map_info.split())
    match = re.match(r"^.*?(\d+).*min.*?(\d+\.?\d?).*km.*$", map_new)
    if match:
        return to_float(match.group(2)), to_int(match.group(1))
    match = re.match(r"^(.*?)( \d+ )(.*?)min.*?(\d+\.?\d?).*km.*$", map_new)
    if match:
        return to_float(match.group(4)), to_int(match.group(2))
    return 0.0, 0


def search_surge(surge_str: str):
    """Map a surge description to its S/M/L code."""
    surge_key = [['slightly', 'lot', 'increased', 'higher'],
                 ['S', 'L', 'M', 'M']]
    if 0 < len(surge_str.strip()):
        for i in range(len(surge_key[0])):
            if surge_key[0][i] in surge_str:
                return surge_key[1][i]
    return ''


def search_price(price_str: str, pattern: str, idx: int) -> float:
    match = re.match(pattern, price_str)
    if match:
        if '.' not in match.group(idx):
            new_price = match.group(idx)[:-2] + '.' + match.group(idx)[-2:]
            return to_float(new_price)
        return to_float(match.group(idx))
    return 0.0


def re_search_price(price_str: str, pattern: str, idx: int) -> float:
    match = re.search(pattern, price_str)
    if match:
        if '.' not in match.group(idx):
            new_price = match.group(idx)[:-2] + '.' + match.group(idx)[-2:]
            return to_float(new_price)
        return to_float(match.group(idx))
    return 0.0


def split_search_price(price_str: str, anchor: str, pattern: str) -> float:
    """Extract a price between an anchor tier name and the next tier name."""
    start_idx = price_str.find(anchor)
    if start_idx != -1:
        price_str = price_str[start_idx:]

    for end_key in MODE_TEXT.values():
        if end_key != anchor:
            end_idx = price_str.find(end_key)
            if end_idx != -1:
                price_str = price_str[:end_idx]

    matches = re.findall(pattern, price_str)
    return to_float(matches[-1])


def split_search_type_price(car_type: str, price_str: str, pattern: str) -> float:
    start_idx = price_str.find(car_type)
    if start_idx != -1:
        price_str = price_str[start_idx:]

    for end_key in MODE_TEXT.values():
        if end_key != car_type:
            end_idx = price_str.find(end_key)
            if end_idx != -1:
                price_str = price_str[:end_idx]

    matches = re.findall(pattern, price_str)
    return 0.0 if len(matches) == 0 else to_float(matches[-1])


# Fare-component vocabulary: canonical field -> label variants that appear on
# fare detail screens.  Extend these when your target app uses other wording.
charge_map = {'toll': ['Estimated Tolls', 'Estimated tolls', 'Highway Fee'],
              'surcharge': ['CTP Fee', 'Airport Fee', 'Estimated surcharges', 'Holiday Surcharge'],
              'base': ['Base fare', 'Start'], 'rateB': ['Base Fare'], 'kilo': ['per kilometre', 'Per km'],
              'minute': ['Per Minute', 'Per min'], 'booking': ['Booking Fee', 'Convenience Fee', 'Booking fee'],
              'rateT': ['Time Rate'], 'rateD': ['Distance Rate'],
              'minimum': ['Minimum fare', 'Minimum Fare', 'Minimum price'],
              'long': ['Above 20 km'], 'short': ['0-12 km', '12 km', '0 - 12 km'],
              'medium': ['12 - 20 km', '20 km']}

# Service-tier text shown on the fare list, keyed by screenshot-type code.
# Adapt these to the apps you automate - they are only used to locate and
# bracket price text on the screen.
MODE_TEXT = {'D': 'Express', 'DE': 'Express', 'DM': 'Max', 'DD': 'Delivery',
             'DT': 'Travel', 'U': 'RideX'}
MODE_SUFFIX = {v: k for k, v in MODE_TEXT.items()}

# Map a screenshot-type code to the crop key used for address validation
scope_map = {'D': 'DA', 'G': 'GA', 'GU': 'GA', 'UX': 'UA', 'U': 'UA'}

# OCR crop-key normalisation (detail variants fall back to their base key)
def filename_map(origin: str) -> str:
    if origin.startswith('U'):
        return 'UI' if origin.endswith('I') else 'U'
    elif origin.startswith('D') and origin.endswith('I'):
        return 'DI'
    elif origin == 'GU':
        return 'G'
    return origin


def read_routes(city: str) -> list:
    route_csv = os.path.join(routes_dir(), city + '.csv')
    df = pd.read_csv(route_csv)
    return df.to_dict('records')


def read_routes_filter(city: str, filters: list) -> list:
    route_csv = os.path.join(routes_dir(), city + '.csv')
    df = pd.read_csv(route_csv)
    df_filter = df[(df['route_id'].isin(filters)) == True]
    return df_filter.to_dict('records')
