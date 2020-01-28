import logging
from functools import wraps
import requests
from idlib import exceptions as exc
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


try:
    # must come after log to avoid circulary imports (for now)
    from sparcur.utils import cache  # temp
    from sparcur.config import auth as sauth  # temp
except ImportError as e:
    from functools import wraps
    def cache(*args, return_path=False, **kwargs):
        def inner(function):
            @wraps(function)
            def superinner(*args, **kwargs):
                if return_path:
                    return function(*args, **kwargs), None
                else:
                    return function(*args, **kwargs)

            return superinner

        return inner


    class _Sauth:
        def get_path(*args, **kwargs):
            return ''

    sauth = _Sauth()



class StringProgenitor(str):
    def __new__(cls, value, *, progenitor=None):
        if progenitor is None:
            raise TypeError('progenitor is a required keyword argument')

        self = super().__new__(cls, value)
        self.progenitor = progenitor
        return self

    def __getnewargs_ex__(self):
        return (self,), dict(progenitor=self.progenitor)


def resolution_chain(iri):
    for head in resolution_chain_responses(iri):
        yield head.url


def resolution_chain_responses(iri, raise_on_final=True):
    #doi = doi  # TODO
    s = requests.Session()
    head = requests.head(iri)
    yield head
    while head.is_redirect and head.status_code < 400:  # FIXME redirect loop issue
        yield head.next
        head = s.send(head.next)
        yield head
        if not head.is_redirect:
            break

    if raise_on_final:  # we still want the chain ... null pointer error comes later?
        if head.status_code == 404:
            head.raise_for_status()  # probably a permissions issue
        elif head.status_code >= 400:
            msg = f'Nothing found due to {head.status_code} at {head.url}\n'
            raise exc.ResolutionError(msg)


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
