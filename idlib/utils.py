from functools import wraps
import requests
from idlib import exceptions as exc


def resolution_chain(iri):
    for head in resolution_chain_responses(iri):
        yield head.url


def resolution_chain_responses(iri):
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

    if head.status_code >= 400:
        raise exc.ResolutionError(f'Nothing found at {head.url}\n')


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
