"""UI element lookup and interaction helpers on top of uiautomator2.

``UiResource`` keeps two conveniences over raw uiautomator2:

1. selector prefixes per app (resource-id namespaces) come from
   ``config.yaml -> selector_prefixes``, so app modules only reference the
   short id, e.g. ``rh.click(idx='confirm_button')``;
2. every lookup logs what it is waiting for, which makes unattended runs
   debuggable from the log file alone.
"""
import logging
import time

import uiautomator2 as u2
from uiautomator2 import Device

from core.config import CONFIG


class UiResource(object):
    def __init__(self, dev: Device, app_type: str):
        self.dev = dev
        self.app = app_type
        self.delay = 2
        self.max_wait = 5

        # '@package:id/' prefixes keyed by app type, loaded from config
        self.id_mapping = CONFIG.get('selector_prefixes', {})
        # Optional xpath templates applied when looking elements up by text
        self.text_mapping = CONFIG.get('text_xpath', {})

    # RESOURCE OPERATION
    def get_xpath(self, idx: str, text: str, path: str) -> str:
        if idx != '':
            xpath = self.id_mapping[self.app] + idx
        elif text != '' and self.app in self.text_mapping:
            xpath = self.text_mapping[self.app] % text
        else:
            xpath = path
        return xpath

    # Check whether item exists
    def exists(self, idx='', text='', path=''):
        xpath = self.get_xpath(idx, text, path)
        logging.info(self.app + ' CHECK EXIST ' + xpath)
        return self.dev.xpath(xpath).exists

    # Check multiple items at the same time
    def exists_multi(self, path_type: str, paths: list):
        logging.info(self.app + ' CHECK EXISTS MULTI ' + str(paths))
        for it in paths:
            if path_type == 'id':
                xpath = self.id_mapping[self.app] + it
            elif path_type == 'text':
                xpath = self.text_mapping[self.app] % it
            else:
                xpath = it

            if self.dev.xpath(xpath).exists:
                return True, it

        return False, ''

    # Wait for an item
    def wait_xpath(self, xpath: str) -> bool:
        for i in range(self.max_wait):
            time.sleep(self.delay)
            if self.dev.xpath(xpath).exists:
                logging.info(self.app + ' WAIT exist ' + xpath + ' loop ' + str(i))
                return True

        logging.error(self.app + ' WAIT NOT exist ' + xpath)
        return False

    def wait(self, idx='', text='', path=''):
        return self.wait_xpath(self.get_xpath(idx, text, path))

    # Wait for multiple items at the same time
    def wait_multi(self, path_type: str, paths: list):
        for _ in range(self.max_wait):
            time.sleep(self.delay)
            for it in paths:
                if path_type == 'id':
                    xpath = self.id_mapping[self.app] + it
                elif path_type == 'text':
                    xpath = self.text_mapping[self.app] % it
                else:
                    xpath = it

                if self.dev.xpath(xpath).exists:
                    logging.info(self.app + ' WAIT MULTI found: ' + it)
                    return True, it

        logging.error(self.app + ' WAIT MULTI NOTHING found')
        return False, ''

    def wait_multi_input(self, path_type: str, paths: list, fill: str) -> bool:
        logging.info(self.app + ' WAIT MULTI INPUT ' + str(paths))
        result, item = self.wait_multi(path_type, paths)
        if result:
            self.input_only(idx=item, content=fill)
            return True

        logging.error(str(paths) + ' DOES NOT SHOW')
        return False

    def wait_multi_clickitem(self, path_type: str, paths: list) -> bool:
        logging.info(self.app + ' WAIT MULTI CLICK ' + str(paths))
        result, item = self.wait_multi(path_type, paths)
        if result:
            self.click_item(idx=item)
            return True

        logging.error(str(paths) + ' DOES NOT SHOW')
        return False

    def wait_multi_click(self, path_type: str, paths: list) -> bool:
        result, item = self.wait_multi(path_type, paths)
        if result:
            if path_type == 'text':
                self.click_only(text=item)
            else:
                self.click_only(idx=item)
            return True

        logging.error(str(paths) + ' DOES NOT SHOW')
        return False

    def click_only(self, idx='', text='', path=''):
        xpath = self.get_xpath(idx, text, path)
        try:
            self.dev.xpath(xpath).click()
        except u2.exceptions.XPathElementNotFoundError:
            logging.error(self.app + ' ' + xpath + ' XPathElementNotFoundError')

    def click(self, idx='', text='', path=''):
        xpath = self.get_xpath(idx, text, path)
        logging.info(self.app + ' CLICK ' + xpath)

        if self.wait_xpath(xpath):
            self.click_only(idx, text, path)
        else:
            logging.error(self.app + ' ' + xpath + ' ERROR NOT FOUND')

    def input_only(self, idx='', text='', path='', content=''):
        xpath = self.get_xpath(idx, text, path)

        self.dev.xpath(xpath).click()
        time.sleep(1)  # Wait for the click to take effect
        self.dev.xpath(xpath).click()
        self.dev(focused=True).set_text(content)

    def input(self, idx='', text='', path='', content='') -> bool:
        xpath = self.get_xpath(idx, text, path)
        logging.info(self.app + ' INPUT ' + idx + text + path)

        if self.wait_xpath(xpath):
            self.input_only(idx, text, path, content)
            return True

        logging.error(self.app + ' ' + xpath + ' ERROR NOT FOUND')
        return False

    # Wait and click the first match in a list
    def click_list(self, idx='', text='', path='') -> bool:
        xpath = self.get_xpath(idx, text, path)
        logging.info(self.app + ' CLICK LIST ' + xpath)

        time.sleep(3)
        if self.dev.xpath(xpath).exists:
            self.dev.xpath(xpath).all()[0].click()
            return True

        logging.error(self.app + ' NOT FOUND ' + xpath)
        return False

    def click_item(self, idx='', text='', path=''):
        xpath = self.get_xpath(idx, text, path)
        self.dev.xpath(xpath).all()[0].click()

    def id_operation(self, idx='', exist='', click='', fill='') -> bool:
        xpath = self.id_mapping[self.app][1:] + idx
        if 'exist' == exist:
            if not self.dev(resourceId=xpath).exists():
                logging.error(self.app + ' ' + xpath + ' NOT exist')
                return False

        if 'click' == click:
            if self.dev(resourceId=xpath).exists():
                logging.info(self.app + ' ' + idx + ' click')
                self.dev(resourceId=xpath).click()

                # Clicking twice keeps behaviour consistent across devices
                time.sleep(1)
                if self.dev(resourceId=xpath).exists():
                    self.dev(resourceId=xpath).click()

        if '' != fill:
            if self.dev(resourceId=xpath).exists():
                logging.info(self.app + ' ' + idx + ' input ' + fill)
                self.dev(focused=True).set_text(fill)

        return True

    def click_sleep(self, pre_sleep: float, x_val: float, y_val: float, sleep: float):
        if 0 != pre_sleep:
            time.sleep(pre_sleep)
        self.dev.click(x_val, y_val)
        if 0 != sleep:
            time.sleep(sleep)

    def click_sleep_multi(self, pre_sleep: float, x_val: float, y_val: float, sleep: float, count: int):
        for _ in range(count):
            self.click_sleep(pre_sleep, x_val, y_val, sleep)

    def text_wait(self, txt='') -> bool:
        for i in range(self.max_wait):
            time.sleep(self.delay)
            if self.dev(text=txt).exists:
                logging.info(self.app + ' WAIT found ' + txt)
                return True

        logging.info(self.app + ' WAIT not found ' + txt)
        return False

    def text_wait_sleep(self, txt='', sleep=0):
        logging.info(self.app + ' wait for ' + txt)
        if sleep > 0:
            time.sleep(sleep)

        self.dev(text=txt).wait()
        if sleep > 0:
            time.sleep(sleep)

    def text_operation(self, txt='', exist='', click='') -> bool:
        if 'exist' == exist:
            if not self.dev(text=txt).exists():
                logging.error(self.app + ' ' + txt + ' NOT exist')
                return False

        if 'click' == click:
            if self.dev(text=txt).exists():
                logging.info(self.app + ' ' + txt + ' click')
                self.dev(text=txt).click()

                time.sleep(1)
                if self.dev(text=txt).exists():
                    self.dev(text=txt).click()
            else:
                logging.error(self.app + ' ' + txt + ' NOT FOUND')
                return False

        return True

    def text_click(self, txt='') -> bool:
        if not self.dev(text=txt).exists():
            logging.error(self.app + ' ' + txt + ' NOT exist')
            return False

        logging.info(self.app + ' ' + txt + ' click')
        self.dev(text=txt).click()
        return True

    def text_operation_wait(self, text='', exist='', click='', sleep=0) -> bool:
        self.text_wait(txt=text)
        if self.text_operation(text, exist, click):
            if sleep > 0:
                time.sleep(sleep)
            return True
        return False

    def text_operation_sleep(self, txt='', exist='', click='', sleep=0) -> bool:
        if self.text_operation(txt, exist, click):
            if sleep > 0:
                time.sleep(sleep)
            return True
        return False

    def get_text_bottom(self, txt='') -> int:
        if self.dev(text=txt).exists():
            _, _, _, bottom = self.dev(text=txt).bounds()
            return bottom
        return 0

    def get_text_top(self, txt='') -> int:
        if self.dev(text=txt).exists():
            _, top, _, _ = self.dev(text=txt).bounds()
            return top
        return 0

    def desc_operation(self, desc='') -> bool:
        multiples = self.dev(descriptionStartsWith=desc)
        if 0 < len(multiples):
            self.dev(description=multiples[0].info['contentDescription']).click()
            return True
        return False

    def swipes(self, direction: str, scale: float, sleeps: float, times: int) -> bool:
        for _ in range(times):
            if direction == 'up' and 0 != scale:
                self.dev.swipe_ext("up", scale=scale)
            elif direction == 'down' and 0 != scale:
                self.dev.swipe_ext("down", scale=scale)
            elif direction == 'back':
                self.dev.press("back")

            if 0 != sleeps:
                time.sleep(sleeps)

        return True

    def xpath_operation(self, path_name='', exist='', click='') -> bool:
        if 'exist' == exist:
            self.dev.xpath(path_name).wait()
            if not self.dev.xpath(path_name).exists:
                logging.error(self.app + ' ' + path_name + ' NOT exist')
                return False

            logging.info(self.app + ' ' + path_name + ' found')

        if 'click' == click:
            logging.info(self.app + ' ' + path_name + ' click')
            self.dev.xpath(path_name).click()
            time.sleep(3)
            if self.dev.xpath(path_name).exists:
                self.dev.xpath(path_name).click()

        return True

    def click_obj_middle(self, pre_wait=0, xpath='', post_wait=0) -> bool:
        if pre_wait > 0:
            time.sleep(pre_wait)

        xpath_elem = self.dev.xpath(xpath)
        if xpath_elem.exists:
            lx, ly, rx, ry = xpath_elem.bounds
            logging.info(self.app + ' ' + xpath + ' click middle: '
                         + str((lx + rx) // 2) + ',' + str((ly + ry) // 2))

            self.dev.click((lx + rx) // 2, (ly + ry) // 2)

            if post_wait > 0:
                time.sleep(post_wait)
            return True

        logging.error(self.app + ' ' + xpath + ' NOT exist')
        return False

    def swipe_objects(self, from_path='', to_path='') -> bool:
        from_elem = self.dev.xpath(from_path)
        to_elem = self.dev.xpath(to_path)
        if from_elem.exists and to_elem.exists:
            from_x1, from_y1, from_x2, from_y2 = from_elem.bounds
            to_x1, to_y1, to_x2, to_y2 = to_elem.bounds
            self.dev.swipe((from_x1 + from_x2) / 2, (from_y1 + from_y2) / 2,
                           (to_x1 + to_x2) / 2, to_y1)
            return True

        logging.error(self.app + ' ' + from_path + ' ' + to_path + ' NOT both exist')
        return False
