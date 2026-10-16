"""Central configuration loader.

The runtime configuration lives in ``config.yaml`` (git-ignored).
``config.example.yaml`` documents every supported key and acts as the fallback
so that a fresh clone can at least be imported and linted without setup.
"""
import os

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load() -> dict:
    for name in ('config.yaml', 'config.example.yaml'):
        path = os.path.join(_ROOT, name)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as handle:
                data = yaml.load(handle, Loader=yaml.FullLoader)
                return data or {}
    raise FileNotFoundError('No config.yaml or config.example.yaml found')


CONFIG = _load()


def base_dir() -> str:
    return CONFIG.get('work_base', '.')


def routes_dir() -> str:
    return CONFIG.get('routes_dir', 'data')
