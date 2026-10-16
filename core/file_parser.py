"""Route parsed screenshots through whichever OCR engine is available.

Engine preference: EasyOCR > PaddleOCR > Tesseract.  The chosen engine must
provide parse_fare / parse_surge / parse_info / parse_google / parse_rule.
"""
import os
import time

from ocr.img_ocr import ImgOcr  # noqa: F401  (base class re-exported for app modules)

try:
    import easyocr
    from ocr.img_easy import ImgEasy
    UseEasyOcr = True
except ImportError:
    UseEasyOcr = False

try:
    import paddleocr  # noqa: F401
    from ocr.img_paddle import ImgPaddle
    UsePaddle = True
except ImportError:
    UsePaddle = False

if not UseEasyOcr and not UsePaddle:
    from ocr.img_tesser import ImgTesser


def _engine(file_path: str, result: dict, file_id: str, phone: str, city: str,
            selection: bool, reader):
    if UseEasyOcr:
        return ImgEasy(file_path, result, file_id, phone, city, selection, reader)
    if UsePaddle:
        return ImgPaddle(file_path, result, file_id, phone, city, selection, reader)
    return ImgTesser(file_path, result, file_id, phone, city, selection)


class FileParser(object):
    def __init__(self, phone: str, city: str, selection: bool, reader=None):
        self.phone = phone
        self.city = city
        self.selection = selection
        self.reader = reader

    def parse(self, file_id: str, file_path: str, primary: dict, secondary: dict):
        """Parse a screenshot captured by the sequential capture mode."""
        second_ids = ['GU', 'GC', 'GB', 'B', 'BI']
        result = secondary if file_id.startswith('U') or file_id in second_ids else primary

        img_parser = _engine(file_path, result, file_id, self.phone, self.city,
                             self.selection, self.reader)

        # Fare list screenshot
        if file_id in ['D', 'UX', 'UC', 'UL', 'B']:
            local_time = time.localtime(os.path.getmtime(file_path))
            result['date'] = "%04d/%02d/%02d" % (local_time.tm_year, local_time.tm_mon, local_time.tm_mday)
            result['time'] = "%02d:%02d" % (local_time.tm_hour, local_time.tm_min)

            img_parser.parse_fare()
            if file_id != 'B':
                img_parser.parse_surge()

        # Fare detail screenshot
        if file_id.endswith('I'):
            img_parser.parse_info()

        # Map reference screenshot
        if file_id.startswith('G'):
            img_parser.parse_google()

        # Fare-rule screenshot
        if file_id.startswith('DR'):
            img_parser.parse_rule()

    def parse_multi(self, file_id: str, file_path: str, primary: dict, secondary: dict):
        """Parse screenshots captured when multiple service tiers are selected."""
        result = secondary if file_id.startswith('U') else primary

        img_parser = _engine(file_path, result, file_id, self.phone, self.city,
                             self.selection, self.reader)

        if not file_id.endswith('I') and not file_id.startswith('G'):
            local_time = time.localtime(os.getmtime(file_path))
            result['time'] = "%02d:%02d" % (local_time.tm_hour, local_time.tm_min)
            result['date'] = "%04d/%02d/%02d" % (local_time.tm_year, local_time.tm_mon, local_time.tm_mday)

            img_parser.parse_fare()
            img_parser.parse_surge()

        if file_id.endswith('I'):
            img_parser.parse_info()

        if file_id.startswith('G'):
            img_parser.parse_google()

    def parse_auto(self, file_id: str, file_path: str, target: dict):
        img_parser = _engine(file_path, target, file_id, self.phone, self.city,
                             self.selection, self.reader)
        img_parser.parse_fare()
