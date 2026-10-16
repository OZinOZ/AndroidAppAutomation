"""Tesseract backend. Requires the Tesseract binary; point the executable at
its install path (or add it to PATH) before running."""
import re

import pytesseract
from core.common import (charge_map, scope_map, search_price, to_float)
from ocr.img_ocr import ImgOcr

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ImgTesser(ImgOcr):
    def image_to_string(self, scope: str) -> str:
        try:
            return pytesseract.image_to_string(self.get_image_range(scope))
        except Exception:
            return ''

    def image_to_str_list(self, scope: str) -> list:
        try:
            return pytesseract.image_to_string(self.get_image_processed(scope)).splitlines()
        except Exception:
            return []

    def parse_info(self):
        # Fare-detail pages pair charge labels with values in separate columns,
        # so we OCR the label region and the price region independently.
        keywords = {
            'DI': ['DI1', 'DI2', 'Fare', 'Services Fee', 'Government Transport Levy',
                   'Handling Fee', 'CTP Fee', 'Fuel Surcharge', 'Airport Fee',
                   'Estimated Tolls'],
            'UI': ['UI1', 'UI2', 'Base fare', 'Minimum fare', '+ Per Minute',
                   '+ per kilometre', 'Estimated surcharges', 'Estimated tolls',
                   'Booking Fee'],
        }

        if self.mode not in keywords:
            return

        img_text = self.image_to_string(keywords[self.mode][0]).splitlines()
        charges = [re.sub("[^A-Za-z ]", "", it).strip()
                   for it in img_text if it in keywords[self.mode]]

        img_text = self.image_to_string(keywords[self.mode][1]).splitlines()
        prices = [it for it in img_text if it and to_float(it[1:]) != 0.0]

        if len(charges) <= len(prices):
            for item, mappings in charge_map.items():
                fee = sum(to_float(prices[charges.index(it)][1:])
                          for it in mappings if it in charges)
                if 0.0 != fee:
                    self.row[item] = fee

    def parse_surge(self):
        self.save_surge(self.image_to_string(self.mode[0] + 'S'))

    def parse_google(self):
        self.save_google(self.image_to_string('G'), self.image_to_string('G2'))

    def parse_fare(self):
        price_pattern = r"^(.*?)(\d+\.?\d+)(.*)$"
        discount_pattern = r"^(.*?)(\d+\.?\d+)(.*? .*?)(\d+\.?\d+)(.*?)$"
        paired_pattern = r"^(.*?)\$(\d+\.?\d+)(.*? .*?)\$(\d+\.?\d+)(.*?)$"

        img_text = self.image_to_string(self.mode)

        if 'B' == self.mode:
            self.row['price'] = search_price(' '.join(img_text.split()), paired_pattern, 4)
        else:
            self.row['price'] = search_price(' '.join(img_text.split()), discount_pattern, 4)
            if 0.0 == self.row['price']:
                self.row['price'] = search_price(' '.join(img_text.split()), price_pattern, 2)

    # Route information used for address validation
    def parse_addresses(self):
        img_text = self.image_to_str_list(scope_map[self.mode[0]])
        self.check_addresses(img_text)

    # Fare-rule page (component charges)
    def parse_rule(self):
        charge_list = self.image_to_str_list('DRL')
        charges = [it.strip() for it in charge_list if it != '']

        price_list = self.image_to_str_list('DRR')
        prices = [it for it in price_list if it and to_float(it[1:]) != 0.0]

        if len(charges) <= len(prices):
            for item, mappings in charge_map.items():
                fee = sum(to_float(prices[charges.index(it)][1:])
                          for it in mappings if it in charges)
                if 0.0 != fee:
                    self.row[item] = fee
