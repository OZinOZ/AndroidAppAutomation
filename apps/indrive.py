"""InDrive capture module (real-world example).

The simplest production flow in this repository: start the app, dismiss a
possible "location changed" system dialog, fill pick-up and drop-off through
the same address field (the screen switches between them), and take one
fare-list screenshot (``IN``).

Useful as a first template when porting a new app: it shows coordinate
taps for suggestion acceptance and text-field reuse with a single id.

Resource-id namespace: ``sinet.startup.inDriver:id/`` is registered in
``config.yaml -> selector_prefixes`` under the ``INDRIVE`` key.
"""
import logging
import time

from core.app import App
from core.uiresource import UiResource

# System dialog buttons ("Use current location changed?" prompt)
SYSTEM_BUTTON = 'android:id/text1'


class InDrive(App):
    app_type = 'INDRIVE'
    package = 'sinet.startup.inDriver'
    activity = '.ui.splash.SplashActivity'
    # 'IN' = fare list
    suffixes = ['IN']

    def __init__(self, dev, route: int, pickup: str, destination: str, city: str,
                 date: str, output: str, selection: str, present: str):
        super(InDrive, self).__init__(dev, route, pickup, destination, city,
                                      date, output, present)
        self.selection = selection

    def enter_address(self, rh: UiResource, anchor: str, address: str):
        """Tap one of the two address rows, type the address and tap the
        first suggestion (positioned at a fixed relative coordinate)."""
        if rh.wait(idx=anchor):
            rh.click_only(idx=anchor)

        if rh.wait(idx='address_edittext'):
            rh.input_only(idx='address_edittext', content=address)

        time.sleep(2)
        rh.dev.click(0.438, 0.249)

    def get_info(self) -> bool:
        logging.info('INDRIVE START')
        self.dev.app_start(self.package, self.activity, stop=True)
        rh = UiResource(self.dev, self.app_type)
        time.sleep(5)

        # InDrive may ask whether the device location changed; answer "NO"
        # to keep using the manually entered pick-up point
        dialog = self.dev(resourceId=SYSTEM_BUTTON, text='NO')
        if dialog.wait():
            dialog.click()

        self.enter_address(rh, 'form_multilineellipsizetextview_from', self.src)
        self.enter_address(rh, 'form_multilineellipsizetextview_to', self.dst)

        time.sleep(2)
        super(InDrive, self).screenshot('IN')

        logging.info('INDRIVE FINISH')
        return True
