import requests
from . import exceptions as exc
from .utils import log


def resolution_chain(iri):
    for head in resolution_chain_responses(iri):
        yield head.url


def try_get(s, head):
    # see whether the server has a bad/broken support for head requests
    # sometimes they return e.g. 400 instead of 405, and really they should
    # just work because they work correctly with get request ...
    head = s.get(head.url, stream=True)
    if head.ok:
        log.info(f'bad HEAD implementation {head.url}')
    else:
        content = head.content
        if content:
            if head.headers['Content-Type'] == 'application/json':
                try:
                    j = head.json()
                    log.error(f'{head.url} error json {j}')
                except Exception as e:
                    log.error(f'{head.url} error text {head.text}')

    head.close()
    return head


def resolution_chain_responses(iri, raise_on_final=True):
    #doi = doi  # TODO
    s = requests.Session()
    head = s.head(iri, allow_redirects=False)
    if head.status_code < 400:
        yield head
    else:
        head = try_get(s, head)
        yield head

    while head.is_redirect and head.status_code < 400:  # FIXME redirect loop issue
        yield head.next
        try:
            head = s.send(head.next)
        except requests.exceptions.SSLError as e:
            raise exc.InbetweenError(msg) from e

        if head.status_code < 400:
            yield head
        else:
            head = try_get(s, head)
            yield head

        if not head.is_redirect:
            break

    if raise_on_final:  # we still want the chain ... null pointer error comes later?
        if head.status_code == 404:
            head.raise_for_status()  # probably a permissions issue
        elif head.status_code >= 500:
            msg = f'Remote in error due to {head.status_code} at {head.url}\n'
            raise exc.RemoteError(msg)
        elif head.status_code >= 400:
            msg = f'Nothing found due to {head.status_code} at {head.url}\n'
            raise exc.ResolutionError(msg)

    if head.status_code >= 400:
        # XXX this seems like the "right" thing to do, but it will
        # probably break a bunch of stuff, but at least this way it
        # will be visible now, obviously yeilding None as the final
        # element in the reference chain conflates all the possible
        # reasons so raising is a better solution and is the default
        # for a reason but at least this way the user knows that the
        # final element of the chain dereference to nothing instead of
        # assuming that the last element succeeded
        yield None
