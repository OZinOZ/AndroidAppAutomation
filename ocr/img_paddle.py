import logging
import re

from core.common import scope_map
from ocr.img_ocr import ImgOcr
from paddleocr import PaddleOCR
from ppocr.utils.logging import get_logger


class ImgPaddle(ImgOcr):
    def __init__(self, img: str, row: dict, mode: str, phone: str,
                 city: str, selection: bool, reader=None):
        super(ImgPaddle, self).__init__(img, row, mode, phone, city, selection, reader)

        # PaddleOCR is very chatty at INFO level
        get_logger().setLevel(logging.ERROR)

    def image_recognize(self, scope: str) -> list:
        words = []
        try:
            result = self.reader.ocr(self.get_image_range(scope), cls=True)
            for res in result or []:
                if res is None:
                    continue
                for line in res:
                    words.append(line[1][0])
        except Exception:
            pass

        return words

    def image_to_string(self, scope: str) -> str:
        return ' '.join(self.image_recognize(scope))

    def image_to_clear_list(self, scope: str) -> list:
        output = []
        for clean in self.image_recognize(scope):
            clean = re.sub("[^A-Za-z0-9 ]", "", clean).strip().lower()
            if len(clean) > 2:
                output.append(clean)
        return output

    def image_to_list(self, scope: str) -> list:
        output = []
        for clean in self.image_recognize(scope):
            output.append(re.sub("[^A-Za-z0-9. ]", "", clean).strip())
        return output

    def parse_info(self):
        self.save_detail(self.image_to_list(self.mode))

    # Surge banner: S / M / L classification
    def parse_surge(self):
        self.save_surge(self.image_to_string(self.mode[0] + 'S'))

    def parse_google(self):
        self.save_google(self.image_to_string('G'), self.image_to_string('G2'))

    # Headline fare on the fare list
    def parse_fare(self):
        self.save_price(self.image_to_string(self.mode))

    # Route information used for address validation
    def parse_addresses(self):
        img_text = self.image_to_clear_list(scope_map[self.mode[0]])
        self.check_addresses(img_text)
