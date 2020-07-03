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


def makeEnc(alphabet):
    index = {c:i for i, c in enumerate(alphabet)}
    iindex = {v:k for k, v in index.items()}
    base = len(index)

    def encode(number, *, _iindex=iindex, _base=base):
        chars = ''
        while number > 0:
            number, rem = divmod(number, _base)
            chars = _iindex[rem] + chars

        return chars

    def decode(chars, *, _index=index, _base=base):
        number = 0
        for c in chars:
            number = number * _base + _index[c]

        return number


    return encode, decode


# NOTE this assume normalization and downcasing happened in a previous step
# NOTE base32 crockford is big endian under string indexing, * self._base
# acts to move the previous number(s) to the left by one place in that base
crockford_alphabet = '0123456789abcdefghjkmnpqrstvwxyz'
zooko_alphabet     = 'ybndrfg8ejkmcpqxot1uwisza345h769'
pio_alphabet       = 'abcdefghijkmnpqrstuvwxyz23456789'  # start with d is fun
rfc_alphabet       = 'abcdefghijklmnopqrstuvwxyz234567'

(
    base32_crockford_encode,
    base32_crockford_decode,
 ) = makeEnc(crockford_alphabet)

(
    base32_zooko_encode,
    base32_zooko_decode,
) = makeEnc(zooko_alphabet)

(
    base32_pio_encode,
    base32_pio_decode,
) = makeEnc(pio_alphabet)

(
    base32_rfc_encode,
    base32_rfc_decode,
) = makeEnc(rfc_alphabet)
