"""Shared OCR base class: crop handling, binarisation and fare-field extraction.

Subclasses implement engine-specific text extraction; this class owns the
image preprocessing (crop regions from config, grayscale, Otsu threshold,
morphological closing) and the fare vocabulary.
"""
import re

import cv2
import numpy as np

from core.common import (MODE_TEXT, charge_map, filename_map, search_google_info,
                         search_google_small, search_price, search_surge,
                         split_search_type_price, to_float)
from core.config import CONFIG


class ImgOcr(object):
    def __init__(self, img: str, row: dict, mode: str, phone: str,
                 city: str, selection: bool, reader=None):
        self.image = img
        self.row = row
        self.mode = filename_map(mode)
        self.city = city
        self.selection = selection
        self.reader = reader
        self.phone = phone

        # Crop regions and preprocessing parameters come from config.yaml,
        # keyed by the device model (the phone alias used on the command line)
        self.range = CONFIG.get('crop_ranges', {}).get(phone, {})

    def get_image_range(self, scope: str):
        if scope not in self.range:
            raise KeyError(f"Crop region '{scope}' is not defined for device "
                           f"'{self.phone}' in config.yaml -> crop_ranges")

        img_cv = cv2.imread(self.image)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        top, bottom, left, right = self.range[scope]
        return img_cv[top:bottom, left:right]

    def get_image_processed(self, scope: str):
        img_roi = self.get_image_range(scope)
        img_thresh = cv2.threshold(img_roi, 120, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        kernel_size = CONFIG.get('morph_kernel_size', {}).get(self.phone, 3)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        return cv2.morphologyEx(img_thresh, cv2.MORPH_CLOSE, kernel)

    def save_surge(self, surge: str):
        surge = search_surge(surge)
        if surge != '':
            self.row['surge'] = surge

    def save_detail(self, detail: list):
        """Map a flat list of OCR'd label/value strings onto fare fields."""
        for item, charges in charge_map.items():
            fee = 0.0
            raw_value = None
            for charge in charges:
                if charge in detail:
                    value = detail[detail.index(charge) + 1]
                    range_match = re.match(r"^\D*(\d+(?:\.\d+)?-\d+(?:\.\d+)?)\D*$", value)
                    if range_match:
                        raw_value = range_match.group(1)
                    else:
                        fee += to_float(value)

            if raw_value is not None:
                self.row[item] = raw_value
            elif fee != 0.0:
                self.row[item] = fee
            elif any(charge in detail for charge in charges):
                self.row[item] = 0

    def save_price(self, price: str):
        """Extract the headline fare from a fare-list screenshot.

        Three heuristics, selected by screenshot-type code:
        - codes starting with 'U': single price, optional crossed-out original
        - code 'B': '$xx.xx' pairs separated by whitespace
        - everything else: a tier name anchors the price inside a dense list
        """
        if self.mode.startswith('U'):
            if 'NZD' in price:
                price_pattern = r"^(\D*)(\d+\.?\d{2}).*$"
                discount_pattern = r"^(\D*)(\d+\.?\d{2})(\D*)(\d+\.?\d{2}).*$"
            else:
                price_pattern = r"^(\D*?)(\d+\.?\d{2})(.*)$"
                discount_pattern = r"^(\D*?)(\d+\.?\d{2})( .)(\d+\.?\d{2})(.*)$"
            discount_id = 4
        elif self.mode.startswith('B'):
            price_pattern = r"^(.*?)[\$S](\d+\.?\d+)(.*? .*?)$"
            discount_pattern = r"^(.*?)[\$S](\d+\.?\d+)(.*? .*?)[\$S](\d+\.?\d+)(.*?)$"
            discount_id = 4
        else:
            anchor = MODE_TEXT.get(self.mode, MODE_TEXT['D'])
            price_pattern = rf"^(.*?)\s?{anchor}.*?[\$S58]?(\d+[.,]\d{{2}})(.*)$"
            discount_pattern = (rf"{anchor}.*?[S5s$]\s*(\d+(?:\.\d{{1,2}})?).*?"
                                rf"[S5s$]\s*(\d+(?:\.\d{{1,2}})?).*?[S5s$]\s*(\d+(?:\.\d{{1,2}})?)")
            discount_id = 3

        if len(price.split()) == 1:
            self.row['price'] = search_price(price, price_pattern, 2)
        else:
            if self.mode.startswith('D') and self.mode in MODE_TEXT:
                # Dense tier list: bracket the price between tier names
                discount_pattern = r"[Ss$]?\s*(\d+(?:\.\d+)?)(?![.\d])(?!\s+(?:am|pm)\b)"
                self.row['price'] = split_search_type_price(MODE_TEXT[self.mode], price,
                                                            discount_pattern)
            else:
                self.row['price'] = search_price(price, discount_pattern, discount_id)

            if 0.0 == self.row['price']:
                self.row['price'] = search_price(price, price_pattern, 2)

    def save_google(self, google_0: str, google_1: str):
        """Extract (distance, duration) from one or two map summary strings."""
        distance, duration = search_google_info(google_0)
        if 0.0 == distance or 0 == duration:
            distance, duration = search_google_info(google_1)
            if 0.0 == distance or 0 == duration:
                distance, duration = search_google_small(google_0)
                if 0.0 == distance or 0 == duration:
                    distance, duration = search_google_small(google_1)

        self.row['dist'] = distance
        self.row['trip'] = duration

    def check_addresses(self, addresses: list):
        """Validate that the OCR'd addresses match the route under test.

        Writes a two-digit confidence pair (src/dst, 25/50/88) into row['valid']
        so downstream review can prioritise low-confidence rows.
        """
        def validate_address(address, substrings):
            if not substrings:
                return 88

            if any(s == address or address in s for s in substrings):
                return 50

            combined = [f"{a} {b}" for i, a in enumerate(substrings)
                        for b in substrings[i + 1:]]
            if any(c == address or address in c for c in combined):
                return 50

            return 25

        clean_texts = [re.sub("[^A-Za-z0-9 '&/]", "", text).strip().lower()
                       for text in addresses if text.strip()]
        src_matches = [t for t in clean_texts
                       if t and (t in self.row['src'] or self.row['src'] in t)]
        dst_matches = [t for t in clean_texts
                       if t and (t in self.row['dst'] or self.row['dst'] in t)]

        src_valid = validate_address(self.row['src'], src_matches)
        dst_valid = validate_address(self.row['dst'], dst_matches)

        if 88 in (src_valid, dst_valid):
            print('Mode:', self.mode, 'Address extract:', addresses)
            print('SRC match:', src_matches, 'DST match:', dst_matches)

        validation = f"{src_valid}+{dst_valid}"
        self.row['valid'] = (f"{self.row['valid']}+({validation})"
                             if self.row.get('valid') else validation)

        if '88' in self.row['valid'] and self.mode not in self.row['surge']:
            self.row['surge'] += self.mode
