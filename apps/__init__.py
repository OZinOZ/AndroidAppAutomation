"""App registry.

To add a new target application:

1. add its resource-id prefix to ``config.yaml -> selector_prefixes``;
2. subclass :class:`core.app.App`, set ``app_type`` / ``package`` /
   ``activity`` / ``suffixes`` and implement :meth:`get_info`;
3. register the class here and add its key to the city/app sequence mapping
   in ``main.py`` (or in ``config.yaml -> app_sequence``).

Two real-world capture modules (Bolt and InDrive) ship as worked examples;
their resource ids are public knowledge (any user can dump a UI hierarchy),
but note that automating an app may conflict with its terms of service.

To add a new target application:

1. add its resource-id prefix to ``config.yaml -> selector_prefixes``;
2. subclass :class:`core.app.App`, set ``app_type`` / ``package`` /
   ``activity`` / ``suffixes`` and implement :meth:`get_info`;
3. register the class here and add its key to the city/app sequence mapping
   in ``main.py`` (or in ``config.yaml -> app_sequence``).
"""
from apps.bolt import Bolt
from apps.demo_ride import DemoRide
from apps.indrive import InDrive

APP_REGISTRY = {
    'demo': DemoRide,
    'bolt': Bolt,
    'indrive': InDrive,
}

# Apps to run for a city when config.yaml has no app_sequence override
DEFAULT_APP_SEQUENCE = ['demo']
