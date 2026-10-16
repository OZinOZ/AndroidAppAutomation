import re

from core.common import MODE_TEXT, scope_map
from ocr.img_ocr import ImgOcr


class ImgEasy(ImgOcr):
    def image_to_string(self, scope: str) -> str:
        try:
            return ' '.join(self.reader.readtext(self.get_image_range(scope), detail=0))
        except Exception:
            return ''

    def image_to_clear_list(self, scope: str) -> list:
        return [clean for text in self.reader.readtext(self.get_image_range(scope), detail=0)
                if len(clean := re.sub(r"[^A-Za-z0-9 \-]", "", text).strip().lower()) > 2]

    def image_to_list(self, scope: str) -> list:
        return self.reader.readtext(self.get_image_range(scope), detail=0)

    def parse_info(self):
        self.save_detail(self.image_to_list(self.mode))

    # Surge banner: S / M / L classification
    def parse_surge(self):
        self.save_surge(self.image_to_string(self.mode[0] + 'S'))

    def parse_google(self):
        self.save_google(self.image_to_string('G'), self.image_to_string('G2'))

    # Headline fare on the fare list
    def parse_fare(self):
        if self.mode == 'U':
            # Newer layouts render the default tier in a separate panel
            if MODE_TEXT['U'] in self.image_to_string('U2'):
                self.save_price(self.image_to_string('U3'))
                return

            self.save_price(self.image_to_string(self.mode))
            return

        if self.mode.startswith('D'):
            text_val = self.image_to_string('D')
            if MODE_TEXT.get(self.mode, '') in text_val:
                self.save_price(text_val)
                return

            text_val = self.image_to_string('D2')
            if MODE_TEXT.get(self.mode, '') in text_val:
                self.save_price(text_val)

    # Route information used for address validation
    def parse_addresses(self):
        img_text = self.image_to_clear_list(scope_map[self.mode[0]])
        self.check_addresses(img_text)

    # Fare-rule page (component charges)
    def parse_rule(self):
        rule_list = self.image_to_list('DR')
        self.save_detail(rule_list)
