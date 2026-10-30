from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string


def channels() -> dict:
    return settings.MESSAGING["CHANNELS"]


@lru_cache(maxsize=None)
def _instance(dotted: str):
    return import_string(dotted)()


def get_provider(channel: str):
    return _instance(channels()[channel]["provider"])


def all_providers():
    """Distinct provider instances with the channels each serves."""
    out = {}
    for channel, cfg in channels().items():
        out.setdefault(cfg["provider"], []).append(channel)
    return [(_instance(path), chans) for path, chans in out.items()]
