"""Per-device analysis orchestration: locate captured screenshots, run the
OCR parser for each screenshot type and aggregate results into a CSV."""
import logging
import os
import re

from core.common import file_exist_multi, read_routes
from core.file_handle import FileHandle
from core.file_parser import FileParser

try:
    import easyocr
    UseEasyOcr = True
except ImportError:
    UseEasyOcr = False

try:
    from paddleocr import PaddleOCR
    UsePaddle = True
except ImportError:
    UsePaddle = False

# Screenshot-type codes parsed in selection mode (one per service tier)
TIER_CODES = ['D', 'DT']


class Phone(object):
    def __init__(self, city: str, date: str, input_dir: str, selection: bool, brand: str):
        self.city = city
        self.date = date
        self.input = input_dir
        self.selection = selection
        self.brand = brand

        if UseEasyOcr:
            # Loaded once; the model stays in memory for the whole run
            self.reader = easyocr.Reader(['en'], gpu=True)
        elif UsePaddle:
            self.reader = PaddleOCR(use_angle_cls=True, lang='en')
        else:
            self.reader = None

    @staticmethod
    def clean_addr(address: str) -> str:
        return re.sub("[^A-Za-z0-9 ]", "", address.lower())

    def analyse_entries(self):
        """Parse the standard capture set for every route in the city file."""
        logging.info("%s analyse all routes start", self.brand.upper())

        fp = FileParser(self.brand, self.city, self.selection, self.reader)
        fh = FileHandle(self.input, self.city, self.date)

        route_list = read_routes(self.city)

        # Screenshot-type codes to look for, per route
        file_id_map = ['D', 'DI', 'UX', 'UXI', 'UC', 'UCI', 'UL', 'ULI',
                       'G', 'GU', 'GB', 'B', 'BI']

        for route_id, route in enumerate(route_list, 1):
            base_row = {'src': self.clean_addr(route['src']),
                        'dst': self.clean_addr(route['dst']), 'surge': '', 'valid': ''}

            primary_row = {'id': route_id, **base_row}
            secondary_row = {'id': route_id, **base_row}
            extra_row = {'id': route_id, **base_row}

            for file_id in file_id_map:
                file_flag, file_path = file_exist_multi(self.input, self.city, self.date,
                                                        route_id, file_id)
                if file_flag:
                    if file_id.startswith('B') or file_id.startswith('UC') or file_id.startswith('UL'):
                        fp.parse(file_id, file_path, primary_row, extra_row)
                    else:
                        fp.parse(file_id, file_path, primary_row, secondary_row)
                elif file_id == 'G':
                    # Map screenshots are occasionally written with an index suffix
                    for i in range(2):
                        alt_flag, search_path = file_exist_multi(self.input, self.city, self.date,
                                                                 route_id, file_id + str(i))
                        if alt_flag:
                            os.rename(search_path, file_path)
                            fp.parse(file_id, file_path, primary_row, secondary_row)
                            break

            # Distance / trip time captured by any app applies to all of them
            if 'dist' in primary_row and 'dist' not in secondary_row:
                secondary_row.update({'dist': primary_row['dist'], 'trip': primary_row['trip']})

            for row, label in [(primary_row, 'App A'), (secondary_row, 'App B')]:
                if '=' in row['valid']:
                    row['valid'] = row['valid'].rstrip('=')
                if 'time' in row:
                    print(f'{label}:', row)

            primary_row['src'] = primary_row['dst'] = ''
            secondary_row['src'] = secondary_row['dst'] = ''

            if 'time' in extra_row:
                extra_row.update({'dist': secondary_row.get('dist', ''),
                                  'trip': secondary_row.get('trip', '')})

                if 'time' in primary_row:
                    fh.write_row(primary_row, secondary_row, extra_row)
                else:
                    fh.write_row(extra_row, secondary_row, {})
            else:
                fh.write_row(primary_row, secondary_row, {})

            if 'time' in primary_row or 'time' in secondary_row:
                print('-+-+-+-+-+-+-+-+-+-+-+-+')

        logging.info("%s analyse finish", self.brand.upper())

    def analyse_multilines_entries(self):
        """Parse captures where several service tiers were recorded per route."""
        logging.info("%s analyse selection routes start", self.brand.upper())

        fp = FileParser(self.brand, self.city, self.selection, self.reader)
        fh = FileHandle(self.input, self.city, self.date)

        route_list = read_routes(self.city)

        for route_id, route in enumerate(route_list, 1):
            base_row = {'src': self.clean_addr(route['src']),
                        'dst': self.clean_addr(route['dst']), 'surge': '', 'valid': ''}

            primary_row = {'id': route_id, **base_row}
            secondary_row = {'id': route_id, **base_row}

            for file_id in TIER_CODES:
                primary_row["price"] = primary_row["dist"] = ""
                primary_row["trip"] = primary_row["surcharge"] = ""
                primary_row["date"] = primary_row["time"] = primary_row["surge"] = ""

                file_flag, file_path = file_exist_multi(self.input, self.city, self.date,
                                                        route_id, file_id)
                if file_flag:
                    fp.parse_multi(file_id, file_path, primary_row, secondary_row)

                    info_flag, info_path = file_exist_multi(self.input, self.city, self.date,
                                                            route_id, file_id + 'I')
                    if info_flag:
                        fp.parse_multi(file_id + 'I', info_path, primary_row, secondary_row)

                    alt_flag, google_path = file_exist_multi(self.input, self.city, self.date,
                                                             route_id, 'G')
                    if alt_flag:
                        fp.parse_multi('G', google_path, primary_row, secondary_row)

                primary_row['src'] = primary_row['dst'] = ''
                fh.write_row(primary_row, {}, {})
                print(file_id, primary_row)

            file_flag, file_path = file_exist_multi(self.input, self.city, self.date,
                                                    route_id, 'UX')
            if file_flag:
                fp.parse_multi('UX', file_path, primary_row, secondary_row)

                info_flag, info_path = file_exist_multi(self.input, self.city, self.date,
                                                        route_id, 'UXI')
                if info_flag:
                    fp.parse_multi('UXI', info_path, primary_row, secondary_row)

                alt_flag, google_path = file_exist_multi(self.input, self.city, self.date,
                                                         route_id, 'G')
                if alt_flag:
                    fp.parse_multi('G', google_path, primary_row, secondary_row)

                if 'dist' in primary_row:
                    secondary_row.update({'dist': primary_row['dist'],
                                          'trip': primary_row['trip']})

            secondary_row['src'] = secondary_row['dst'] = ''
            print('UX', secondary_row)
            fh.write_row({}, secondary_row, {})

        logging.info("%s analyse selection finish", self.brand.upper())
