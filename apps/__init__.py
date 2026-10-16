"""App registry.

To add a new target application:

1. add its resource-id prefix to ``config.yaml -> selector_prefixes``;
2. subclass :class:`core.app.App`, set ``app_type`` / ``package`` /
   ``activity`` / ``suffixes`` and implement :meth:`get_info`;
3. register the class here and add its key to the city/app sequence mapping
   in ``main.py`` (or in ``config.yaml -> app_sequence``).

Only a generic demo implementation ships with this repository.  Modules for
specific commercial apps stay out of the public code base - check the terms
of service of any app you automate.
"""
from apps.demo_ride import DemoRide

APP_REGISTRY = {
    'demo': DemoRide,
}

# Apps to run for a city when config.yaml has no app_sequence override
DEFAULT_APP_SEQUENCE = ['demo']
