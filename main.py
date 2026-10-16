"""Command-line entry point.

Typical usage::

    # capture fares for routes 1-10 recorded in data/MEL.csv
    python main.py model_a MEL 1207 1 10

    # re-run OCR analysis on screenshots already on disk
    python main.py model_a MEL 1207 1 10 --analyse

    # capture only a subset of routes (data defined in PARTIAL_ROUTES)
    python main.py model_a MEL 1207 1 10 --partial

    # offer non-default service tiers in the target app
    python main.py model_a MEL 1207 1 10 --selection
"""
import argparse
import json
import logging
import os
import random
import subprocess
import sys
import time
from datetime import date
from types import SimpleNamespace

import uiautomator2 as u2
import yaml

from apps import APP_REGISTRY, DEFAULT_APP_SEQUENCE
from core.common import (address_adapt, file_exist, get_city_path,
                         get_record_range, read_routes)
from core.config import CONFIG, base_dir
from core.notify import send_message
from core.phone import Phone

# OCR engines are optional; analysis-only mode works without any of them
AnalysisOnly = True
try:
    import easyocr  # noqa: F401
except ImportError:
    try:
        import paddleocr  # noqa: F401
    except ImportError:
        AnalysisOnly = False

MAX_FAIL_THRESHOLD = 3
# Routes to include when --partial is set
PARTIAL_ROUTES = []


def get_parameters(arg_list: list) -> SimpleNamespace:
    parser = argparse.ArgumentParser(description='Capture and analyse app fares on Android devices.')
    parser.add_argument('phone', help='device alias defined in config.yaml -> devices')
    parser.add_argument('city', help='city code, e.g. MEL (routes live in <routes_dir>/<city>.csv)')
    parser.add_argument('date', help='record date as MMDD, or 0000 for today')
    parser.add_argument('start', type=int, help='first route id to process')
    parser.add_argument('end', type=int, help='last route id to process')
    parser.add_argument('--analyse', action='store_true', help='run analysis only')
    parser.add_argument('--selection', action='store_true', help='offer non-default service tiers')
    parser.add_argument('--partial', action='store_true', help='process only PARTIAL_ROUTES')

    args = parser.parse_args(arg_list[1:])

    para = SimpleNamespace(**vars(args))
    para.phone = para.phone.lower()
    para.city = para.city.upper()
    para.city_route = get_city_path(para.city)
    para.date = ("%02d%02d" % (date.today().month, date.today().day)
                 if para.date == '0000' else para.date)
    para.base = base_dir()
    para.start, para.end = get_record_range(para.start, para.end)

    devices = CONFIG.get('devices', {})
    if para.phone not in devices:
        parser.error(f"device alias '{para.phone}' is not defined in config.yaml -> devices")
    para.serial_num = devices[para.phone]

    return para


def get_route_list(para: SimpleNamespace) -> list:
    routes = read_routes(para.city_route)
    return [r for r in routes
            if para.start <= int(r['id']) <= para.end
            and (not para.partial or int(r['id']) in PARTIAL_ROUTES)]


def connect_device(serial: str):
    """Restart the uiautomator2 agent and connect to one device."""
    adb = CONFIG.get('adb_path', 'adb')
    try:
        subprocess.check_call([adb, '-s', serial, 'shell',
                               '/data/local/tmp/atx-agent', 'server', '-d', '--stop'])
    except Exception as exc:
        logging.error('atx-agent stop failed: %s', str(exc))

    time.sleep(3)
    try:
        dev = u2.connect(serial)
    except Exception:
        logging.error('Unable to connect, retrying in 30 seconds')
        time.sleep(30)
        try:
            dev = u2.connect(serial)
        except Exception:
            logging.error('Unable to connect, giving up')
            return None

    logging.info(json.dumps(dev.device_info))
    dev.settings['wait_timeout'] = 8
    return dev


def unlock_device(dev):
    dev.screen_on()
    time.sleep(0.5)
    dev.unlock()
    time.sleep(0.5)
    dev.swipe_ext('up', scale=0.8)
    time.sleep(0.5)
    dev.swipe(0.5, 0.9, 0.5, 0.1, 0.5)
    time.sleep(0.5)


def call_app(dev, row: dict, para: SimpleNamespace) -> bool:
    """Run every app mapped to this city for one route, with one retry."""
    app_keys = CONFIG.get('app_sequence', {}).get(get_city_path(para.city),
                                                  DEFAULT_APP_SEQUENCE)
    selection_text = CONFIG.get('default_selections', {})
    result = True

    for key in app_keys:
        app_cls = APP_REGISTRY[key]
        app_exe = app_cls(
            dev, int(row['id']),
            address_adapt(row['src'], para.city),
            address_adapt(row['dst'], para.city),
            row.get('city', para.city_route), para.date,
            para.output_dir,
            selection_text.get(key, 'RideX' if para.selection else ''),
            row.get('present', ''))

        try:
            result = app_exe.get_info()
        except RuntimeError:
            raise RuntimeError('App not logged in')
        except Exception as exc:
            logging.error('Error: %s', str(exc))
            result = False

        if not result and 'present' not in row:
            logging.error('RETRY record: %s', str(row))
            try:
                result = app_exe.get_info()
            except RuntimeError:
                raise RuntimeError('App not logged in')
            except Exception as exc:
                logging.error('Error: %s', str(exc))
                result = False

        if not result:
            logging.error('FAILED AT %s, skip this row', key)
            return False

    return result


def finish_task(dev, title: str, body: str):
    if dev is not None:
        dev.reset_uiautomator()
        dev.screen_off()

    logging.error(title + ' ' + body)
    send_message(title, body)
    sys.exit(0)


def analyse(para: SimpleNamespace):
    logging.info('Start to analyse %s', para.phone)
    city_phone = Phone(para.city_route, para.date, para.output_dir,
                       para.selection, para.phone)
    if para.selection:
        city_phone.analyse_multilines_entries()
    else:
        city_phone.analyse_entries()


if __name__ == '__main__':
    para = get_parameters(sys.argv)
    para.output_dir = os.path.join(para.base, 'screenshots',
                                   '_'.join([str(para.date), para.city_route, para.phone]))

    if para.analyse or AnalysisOnly:
        os.makedirs(para.output_dir, exist_ok=True)
        analyse(para)
        sys.exit(0)

    log_dir = os.path.join(para.base, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(log_dir,
                                              f"{para.date}_{para.city}_{para.phone}.log"),
                        filemode='w', level=logging.INFO,
                        format='%(asctime)s %(levelname)-7s %(message)s')

    route_list = get_route_list(para)

    dev = connect_device(para.serial_num)
    if dev is None:
        finish_task(dev, 'FAILED to connect!!',
                    ', '.join([para.date, para.city, para.phone]))

    os.makedirs(para.output_dir, exist_ok=True)
    unlock_device(dev)

    failed_attempts = 0
    for row in route_list:
        try:
            if not call_app(dev, row, para):
                failed_attempts += 1
                if failed_attempts >= MAX_FAIL_THRESHOLD:
                    finish_task(dev, 'FAILED too many times!!',
                                ', '.join(['FAIL', para.date, para.city, para.phone]))
        except RuntimeError:
            finish_task(dev, 'FAIL to start APP!!',
                        ', '.join(['FAIL', para.date, para.city, para.phone]))

        # A small, variable pause keeps request patterns human-like
        time.sleep(random.randint(1, 10))

    # Re-run any route missing its fare screenshots
    all_suffixes = sorted({s for key in DEFAULT_APP_SEQUENCE
                           for s in APP_REGISTRY[key].suffixes})
    for row in route_list:
        if not all([file_exist(para.output_dir, para.city_route, para.date,
                               int(row['id']), suf) for suf in all_suffixes]):
            logging.info('Row %s incomplete, redo it', str(row))
            try:
                call_app(dev, row, para)
            except RuntimeError:
                finish_task(dev, 'FAIL to start APP!!',
                            ', '.join(['FAIL', para.date, para.city, para.phone]))

    if 'CHECK' not in para.city:
        analyse(para)

    finish_task(dev, 'Successfully finished.',
                ', '.join(['OK', para.date, para.city, para.phone]))
