import requests
from . import exceptions as exc
from .utils import log


def resolution_chain(iri, headers_fun=None):
    for head in resolution_chain_responses(iri, headers_fun=headers_fun):
        yield head.url


_user_agent_idiocy = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0'


def try_get(s, head, headers_fun=None):
    # see whether the server has a bad/broken support for head requests
    # sometimes they return e.g. 400 instead of 405, and really they should
    # just work because they work correctly with get request ...
    head = s.get(head.url, stream=True)

    if head.ok:
        log.info(f'bad HEAD implementation {head.url}')
    elif head.status_code < 500:
        head.close()
        headers = {'User-Agent': _user_agent_idiocy}
        head = s.get(head.url, headers=headers, stream=True)
        if head.ok:
            log.info(f'bad HEAD implementation AND bad User-Agent behavior {head.url}')
        else:
            headers = None
            if headers_fun is not None:
                # headers_fun is used to ensure that e.g. auth headers
                # are only sent to the netloc's they are for
                headers = headers_fun(head.url)
                if headers is not None:
                    head = s.get(head.url, headers=headers, stream=True)
                    if head.ok:
                        # we log a warning because dereferencing a public id
                        # and encountering a permission boundary is bad
                        # TODO likely need a way to fail on this condition
                        # or at least indicate that it happend in band
                        msg = f'additional headers were added for {head.url}'
                        log.warning(msg)

    if not head.ok:
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


def resolution_raise_logic(head):
    """ broken out into its own function for reuse to avoid re-resolving
        in cases where we need to interpose additional operations between
        a dereference failure and raising the error
    """
    if not head.ok:
        try:
            head.raise_for_status()
        except Exception as e:
            if head.status_code == 404:
                msg = f'Nothing found due to {head.status_code} at {head.url}\n'
                raise exc.IdDoesNotExistError(msg) from e  # often a permissions issue
            elif head.status_code >= 500:
                msg = f'Remote in error due to {head.status_code} at {head.url}\n'
                raise exc.RemoteError(msg) from e
            elif head.status_code >= 400:
                msg = f'Nothing found due to {head.status_code} at {head.url}\n'
                raise exc.ResolutionError(msg) from e


def resolution_chain_responses(iri, raise_on_final=True, headers_fun=None):
    #doi = doi  # TODO
    s = requests.Session()
    head = s.head(iri, allow_redirects=False)
    if head.status_code < 400:
        yield head
    else:
        head = try_get(s, head, headers_fun=headers_fun)
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
            head = try_get(s, head, headers_fun=headers_fun)
            yield head

        if not head.is_redirect:
            break

    if raise_on_final:  # we still want the chain ... null pointer error comes later?
        resolution_raise_logic(head)

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
