import os
import time

from uiautomator2 import Device


class App(object):
    """Base class for one target application running on one device.

    Subclasses implement :meth:`get_info`, drive the UI with
    :class:`core.uiresource.UiResource` and produce the screenshots that the
    OCR pipeline consumes.  Screenshot file names follow the convention::

        <CITY><DATE><ROUTE:03d><SUFFIX>.png

    where SUFFIX codes identify the screenshot type (fare list, fare detail,
    surge banner, map reference, ...) and double as the crop keys used by the
    OCR stage.
    """

    # Key into config.yaml -> selector_prefixes
    app_type = ''
    # Android package / activity used to (re)start the app
    package = ''
    activity = ''
    # Screenshot-type codes this app produces, used for completeness checks
    suffixes = []

    def __init__(self, dev: Device, route: int, pickup: str,
                 destination: str, city: str, date: str, output: str, present: str):
        self.city = city
        self.date = date
        self.dev = dev
        self.src = pickup
        self.dst = destination
        self.rid = route
        self.output = output
        self.present = present

    def screenshot(self, suffix: str):
        time.sleep(3)
        if self.present == '':
            self.dev.screenshot(os.path.join(self.output,
                                             "%s%s%03d%s.png" %
                                             (self.city, self.date, self.rid, suffix)))
        else:
            self.dev.screenshot(os.path.join(self.output,
                                             "%s_%s%s.png" %
                                             (self.present, self.date, suffix)))
