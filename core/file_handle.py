"""CSV output writer for the analysis stage."""
import csv
import glob
import os


class FileHandle(object):
    def __init__(self, input_dir: str, city: str, date: str):
        self.input = input_dir
        self.city = city
        self.date = date
        self.csv_name = os.path.join(input_dir, 'ZZ_' + self.city + '_' + date + '.csv')
        self.fields = ['id', 'date', 'time', 'dist', 'trip', 'toll', 'surcharge', 'surge', 'price',
                       'base', 'minimum', 'minute', 'kilo', 'booking',
                       'rateB', 'short', 'medium', 'long', 'rateT', 'rateD',
                       'valid', 'src', 'dst']

        self.csv_file = open(self.csv_name, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=self.fields)
        self.csv_writer.writeheader()

    def get_list(self):
        return os.listdir(self.input)

    def get_png_list(self, city: str = ''):
        png_files = glob.glob(os.path.join(self.input, '*.png'))
        if city != '':
            png_files = [f for f in png_files if city in f]
        return sorted(png_files, key=os.path.getctime, reverse=False)

    def get_jpg_list(self):
        return glob.glob(os.path.join(self.input, '*.jpg'))

    def write_row(self, primary: dict, secondary: dict, extra: dict = None):
        """Write one row per app result dict that carries an 'id' key."""
        for row in [primary, secondary, extra or {}]:
            if 'id' in row:
                self.csv_writer.writerow(row)

    def close(self):
        self.csv_file.close()
