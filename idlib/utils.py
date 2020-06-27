import logging
from datetime import datetime, timezone
from functools import wraps
from idlib import exceptions as exc


## logging

def makeSimpleLogger(name, level=logging.INFO):
    # TODO use extra ...
    logger = logging.getLogger(name)
    logger.setLevel(level)
    ch = logging.StreamHandler()  # FileHander goes to disk
    fmt = ('[%(asctime)s] - %(levelname)8s - '
           '%(name)14s - '
           '%(filename)16s:%(lineno)-4d - '
           '%(message)s')
    formatter = logging.Formatter(fmt)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


log = makeSimpleLogger('idlib')
logd = log.getChild('data')


## time (from pyontutils.utils)

def TZLOCAL():
    return datetime.now(timezone.utc).astimezone().tzinfo


# families (mostly a curiosity)
class families:
    IETF = object()
    ISO = object()
    NAAN = object()


class StringProgenitor(str):
    def __new__(cls, value, *, progenitor=None):
        if progenitor is None:
            raise TypeError('progenitor is a required keyword argument')

        self = super().__new__(cls, value)
        self._progenitor = progenitor
        return self

    def progenitor(self):
        return self._progenitor

    def __getnewargs_ex__(self):
        # have to str(self) to avoid infinite recursion
        return (str(self),), dict(progenitor=self._progenitor)


def cache_result(method):
    """ if the method has run, stash the value for when the method is called again
    WITH NO ARGUMENTS (or at some point the same arguments), last one wins I think
    if you need to clear the cached value CREATE A NEW INSTANCE """

    cache_name = '_cache_' + method.__name__
    @wraps(method)
    def inner(self, *args, **kwargs):
        if not args and not kwargs:
            if hasattr(self, cache_name):
                return getattr(self, cache_name)

        out = method(self, *args, **kwargs)
        setattr(self, cache_name, out)
        return out

    return inner
