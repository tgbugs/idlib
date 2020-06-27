import requests


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
