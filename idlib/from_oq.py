import ontquery as oq  # temporary implementation detail
import idlib
from idlib import streams
from idlib.utils import cache_result


# from neurondm.simple
class OntTerm(oq.OntTerm):
    """ ask things about a term! """
    skip_for_instrumentation = True

    def __new__(cls, *args, **kwargs):
        self = oq.OntId.__new__(cls, *args, **kwargs)
        self._args = args
        self._kwargs = kwargs
        return self

    def fetch(self):
        newself = super().__new__(self.__class__, *self._args, **self._kwargs)
        self.__dict__ = newself.__dict__
        return self


class URIInstrumentation(oq.terms.InstrumentedIdentifier):

    @property
    def headers(self):
        """ request headers """
        if not hasattr(self, '_headers'):
            resp = requests.head(self.iri)  # TODO status handling for all these
            self._headers = resp.headers

        return self._headers

    @property
    def resolution_chain(self):
        # FIXME what should an identifier object represent?
        # the eternal now of the identifier? or the state
        # that it was in when this particular representation
        # was created? This means that really each one of these
        # objects should be timestamped and that equiality of
        # instrumented objects should return false, which seems
        # very bad for usability ...
        if not hasattr(self, '_resolution_chain'):
            # FIXME the chain should at least be formed out of
            # IriHeader objects ...
            self._resolution_chain = [uri for uri in resolution_chain(self)]

        yield from self._resolution_chain

    def resolve(self, target_class=None):
        """ match the terminology used by pathlib """
        # TODO generic probing instrumented identifier matcher
        # by protocol, domain name, headers, etc.
        for uri in self.resolution_chain:
            pass

        if target_class is not None:
            return target_class(uri)

        else:
            return uri  # FIXME TODO identifier it


class _PioPrefixes(oq.OntCuries): pass
PioPrefixes = _PioPrefixes.new()
PioPrefixes({'pio.view': 'https://www.protocols.io/view/',
             'pio.edit': 'https://www.protocols.io/edit/',  # sigh
             'pio.private': 'https://www.protocols.io/private/',
             'pio.fileman': 'https://www.protocols.io/file-manager/',
             'pio.api': 'https://www.protocols.io/api/v3/protocols/',
})


class PioId(oq.OntId, idlib.Identifier):
    _namespaces = PioPrefixes

    def __new__(cls, curie_or_iri=None, iri=None, prefix=None, suffix=None):
        if curie_or_iri is None and iri:
            curie_or_iri = iri

        if curie_or_iri is not None:
            # FIXME trailing nonsense for abstract etc
            normalized = curie_or_iri.replace('://protocols.io', '://www.protocols.io')
        else:
            normalized = None

        self = super().__new__(cls, curie_or_iri=normalized, iri=iri,
                               prefix=prefix, suffix=suffix)

        self._unnormalized = curie_or_iri if curie_or_iri else self.iri
        return self
        
    @property
    def uri_api(self):
        return self.__class__(prefix='pio.api', suffix=self.slug)

    def normalize(self):
        return self

    @property
    def slug(self):
        if self.suffix is None:
            breakpoint()
        return self.suffix.rsplit('/', 1)[0] if '/' in self.suffix else self.suffix


class Pio(idlib.Stream):
    """ instrumented protocols """

    _id_class = PioId
    # FIXME defining this here breaks the import chain
    # since protocols.py imports from core.py (sigh)
    _wants_instance = '.protocols.ProtocolData'  # this is an awful pattern
    # but what do you want :/

    dereference_chain = streams.StreamUri.dereference_chain
    dereference = streams.StreamUri.dereference
    progenitor = streams.StreamUri.progenitor
    headers = streams.StreamUri.headers

    def __gt__(self, other):
        if isinstance(other, idlib.Stream):
            return self.identifier > other.identifier
        else:
            return False  # FIXME TODO

    @property
    def slug(self):
        return self.identifier.slug

    @property
    def doi(self):
        data = self.data()
        if data:
            doi = data['doi']
            if doi:
                return idlib.Doi(doi)

    @property
    def uri_human(self):  # FIXME HRM ... confusion with pio.private iris
        """ the not-private uri """
        data = self.data
        if data:
            uri = data['uri']
            if uri:
                return self.__class__(prefix='pio.view', suffix=uri)

    def data(self):
        if not hasattr(self, '_data'):
            blob = self._protocol_data.protocol(self.identifier)
            if blob is not None:
                self._status_code = blob['status_code']
                self._data = blob['protocol']
            else:
                self._data = None  # FIXME raise

        return self._data

    @property
    def hasVersions(self):
        return bool(self.data['has_versions'])

    @property
    def versions(self):
        yield from self.data['versions']  # TODO ...

    @property
    def created(self):
        # FIXME I don't think this is TZLOCAL for any reason beyond accident of circumstances
        # I think this is PDT i.e. the location of the protocols.io servers
        tzl = TZLOCAL()
        return datetime.fromtimestamp(self.data['created_on'], tz=tzl)

    @property
    def updated(self):
        tzl = TZLOCAL()
        return datetime.fromtimestamp(self.data['changed_on'], tz=tzl)

    @property
    def creator(self):
        return PioUserInst('pio.user:' + self.data['creator']['username'])

    @property
    def authors(self):
        for u in self.data['authors']:
            yield PioUserInst(prefix='pio.user', suffix=u['username'])


class _PioUserPrefixes(oq.OntCuries): pass
PioUserPrefixes = _PioUserPrefixes.new()
PioUserPrefixes({'pio.user': 'https://www.protocols.io/researchers/',
                 'pio.api.user': 'https://www.protocols.io/api/v3/researchers/',
})


class PioUserId(oq.OntId):
    _namespaces = PioUserPrefixes


class PioUser(idlib.Stream):
    _id_class = PioUserId
    _wants_instance = '.protocols.ProtocolData'  # this is an awful pattern

    @property
    def uri_human(self):
        return self.__class__(prefix='pio.user', suffix=self.suffix)

    @property
    def uri_api(self):
        return self.__class__(prefix='pio.api.user', suffix=self.suffix)

    @cache_result
    def metadata(self):
        uri = self.uri_api + '?with_extras=1'
        # FIXME this is a dumb an convoluted way to get authed api access
        blob = self._protocol_data.get(uri)
        self._status_code = blob['status_code']
        return blob['researcher']

    @property
    def orcid(self):
        orcid = self.metadata()['orcid']
        if orcid is not None:
            return idlib.Orcid(prefix='orcid', suffix=orcid)


class IsniId(oq.OntId):  # TODO
    prefix = 'http://isni.org/isni/'
    _ror_key = 'ISNI'


class Auto:
    """ dispatch to type on identifier structure """
    def __new__(cls, something):
        if '10.' in something:
            if 'http' in something and 'doi.org' not in something:
                pass  # probably a publisher uri that uses the handle
            else:
                return idlib.Doi(something)

        if 'orcid' in something:
            return idlib.Orcid(something)

        if '/ror.org/' in something or something.startswith('ror:'):
            return idlib.Ror(something)

        if 'protocols.io' in something:
            return idlib.Pio(something)

        return oq.OntId(something)  # FIXME idlib.StreamUri ?
