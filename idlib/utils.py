import requests


def resolution_chain(iri):
    #doi = doi  # TODO
    s = requests.Session()
    head = requests.head(iri)
    yield head.url
    while head.is_redirect and head.status_code < 400:  # FIXME redirect loop issue
        yield head.next.url
        head = s.send(head.next)
        yield head.url
        if not head.is_redirect:
            break

    if head.status_code >= 400:
        raise ResolutionError(f'Nothing found at {head.url}\n')
