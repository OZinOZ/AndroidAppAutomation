"""Example 3 - drive one app programmatically (needs a connected phone).

Records Google Maps distance and Bolt fare for a single route and saves the
screenshots in ./workspace/screenshots/demo.

Run:  python examples/03_programmatic_capture.py <adb-serial>
"""

import sys
from pathlib import Path

from appautomation import device
from appautomation.apps import Bolt, Google

serial = sys.argv[1]
output = Path("workspace/screenshots/demo")
output.mkdir(parents=True, exist_ok=True)

dev = device.connect(serial)          # uses `adb` from PATH
if dev is None:
    sys.exit("Could not connect to the phone")
device.wake_and_unlock(dev)

for app_cls in (Google, Bolt):
    app = app_cls(dev, route_id=1, pickup="Federation Square,Melbourne",
                  destination="Melbourne Airport", city="MEL", date="0101",
                  output_dir=str(output))
    print(app_cls.__name__, "OK" if app.get_info() else "FAILED")
