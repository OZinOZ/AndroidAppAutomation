"""A generic, fully self-contained example app module.

``DemoRide`` shows the expected structure of a capture module: start the app,
dismiss first-run popups, qualify a route, capture the fare list and the fare
detail page, then return True/False so the runner can retry or move on.

All resource ids and text anchors here are placeholders - dump your target
app's hierarchy with ``adb shell uiautomator dump`` (or uiautomator2's
``dev.dump_hierarchy()``) and replace them, together with the selector prefix
in ``config.yaml -> selector_prefixes``.
"""
import logging
import time

from core.app import App
from core.uiresource import UiResource

# Placeholder resource ids - replace with values dumped from your target app
RIDE_SEARCH_VIEW = 'ride_search_view'
RIDE_SEARCH_INPUT = 'ride_search_input'
RIDE_SUGGESTION = 'suggestion_item'
RIDE_FARE_LIST = 'fare_list'
RIDE_FARE_CARD = 'fare_card'
RIDE_FARE_DETAIL = 'fare_detail'

# Text anchors commonly rendered by ride-hailing apps
TEXT_WHERE_TO = 'Where to?'
TEXT_CHOOSE_RIDE = 'Choose a ride'
TEXT_SKIP = 'Skip'


class DemoRide(App):
    app_type = 'DEMO'
    package = 'com.example.ridedemo'
    activity = '.MainActivity'
    # Screenshot codes produced here; 'D' = fare list, 'DI' = fare detail.
    # They must exist in config.yaml -> crop_ranges for the OCR stage.
    suffixes = ['D', 'DI']

    def __init__(self, dev, route: int, pickup: str, destination: str, city: str,
                 date: str, output: str, selection: str, present: str):
        super(DemoRide, self).__init__(dev, route, pickup, destination, city,
                                       date, output, present)
        self.selection = selection

    # --- helpers ---------------------------------------------------------

    def dismiss_popups(self, rh: UiResource):
        """First-run dialogs vary by build; try the common ones in order."""
        for candidate in ['ub__tooltip_button_primary',
                          'community_guidelines_accept_button']:
            if rh.exists(idx=candidate):
                logging.info('DEMO dismiss popup %s', candidate)
                rh.click(idx=candidate)
                time.sleep(2)

        rh.text_operation_sleep(TEXT_SKIP, '', 'click', 2)

    def enter_address(self, rh: UiResource, view: str, field: str, address: str) -> bool:
        """Tap an address entry point, type the address and accept the first
        suggestion returned by the app's search."""
        if not rh.wait(idx=view):
            logging.error('DEMO: entry view %s not found', view)
            return False

        if not rh.id_operation(view, 'exist', 'click', ''):
            return False

        if not rh.wait(idx=field):
            rh.id_operation(view, '', 'click', '')
            time.sleep(1)

        if not rh.id_operation(field, 'exist', 'click', address):
            logging.error('DEMO: failed to enter address %s', address)
            return False

        time.sleep(2)
        if not rh.click_list(idx=RIDE_SUGGESTION):
            logging.error('DEMO: no search suggestion accepted for %s', address)
            return False

        return True

    # --- main flow -------------------------------------------------------

    def get_info(self) -> bool:
        logging.info('DEMO START')
        self.dev.app_start(self.package, self.activity, wait=True, stop=True)
        rh = UiResource(self.dev, self.app_type)

        time.sleep(3)
        self.dismiss_popups(rh)

        # Open the address search screen
        if rh.exists(idx=RIDE_SEARCH_VIEW):
            rh.click(idx=RIDE_SEARCH_VIEW)
        elif rh.text_operation(TEXT_WHERE_TO, 'exist', 'click'):
            logging.info('DEMO: opened search via text anchor')
        else:
            logging.error('DEMO: cannot find the search entry point')
            super(DemoRide, self).screenshot('ERR')
            return False

        # Pickup
        if not self.enter_address(rh, RIDE_SEARCH_VIEW, RIDE_SEARCH_INPUT, self.src):
            return False

        # Destination (the search screen is already open after the pickup)
        if not rh.wait(idx=RIDE_SEARCH_INPUT):
            logging.error('DEMO: destination field not found')
            return False

        if not rh.id_operation(RIDE_SEARCH_INPUT, 'exist', 'click', self.dst):
            return False

        time.sleep(2)
        if not rh.click_list(idx=RIDE_SUGGESTION):
            logging.error('DEMO: no destination suggestion accepted')
            return False

        # Fare list
        if not rh.text_wait(TEXT_CHOOSE_RIDE):
            logging.error('DEMO: fare list did not load')
            return False

        time.sleep(2)
        super(DemoRide, self).screenshot('D')
        logging.info('DEMO: fare list captured')

        # Fare detail for the selected service tier
        if self.selection != '':
            if rh.exists(idx=RIDE_FARE_CARD):
                rh.click(idx=RIDE_FARE_CARD)
                time.sleep(2)
                self.dev.swipe_ext('up', scale=0.4)

                if rh.exists(idx=RIDE_FARE_DETAIL):
                    super(DemoRide, self).screenshot('DI')
                    logging.info('DEMO: fare detail captured')

                self.dev.press('back')
                time.sleep(1)

        logging.info('DEMO FINISH')
        return True
