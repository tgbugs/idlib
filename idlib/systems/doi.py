import requests  # resolver dejoure
import ontquery as oq  # temp implementation detail
import idlib
from idlib.utils import cache_result, resolution_chain_responses


class _DoiPrefixes(oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


_DoiPrefixes({'DOI':'https://doi.org/',
              'doi':'https://doi.org/',})

class DoiId(oq.OntId, idlib.Stream):  # also _technically_ a stream
    """ The actual representation of the DOI, but we'll ignore that for now """
    _namespaces = _DoiPrefixes

    def __new__(cls, doi_in_various_states_of_mangling=None, iri=None):
        if doi_in_various_states_of_mangling is None and iri is not None:
            doi_in_various_states_of_mangling = iri

        normalize = cls.normalize(doi_in_various_states_of_mangling)
        self = super().__new__(cls, prefix='doi', suffix=normalize)
        self._unnormalized = doi_in_various_states_of_mangling
        self.validate()
        return self

    @property
    def identifier(self):
        # identifier streams return themselves as their identifier
        return self

    def _checksum(self, cypher):
        m = cypher()
        m.update(str(self).encode())
        return m.digest()

    @property
    def metadata(self):
        return None  # FIXME vs identifier?

    @property
    def data(self):
        return None  # FIXME vs identifier?

    @staticmethod
    def normalize(doi):
        doi = doi.replace(' ', '')
        if 'http' in doi or 'doi.org' in doi:
            doi = '10.' + doi.split('.org/10.', 1)[-1]
        elif doi.startswith('doi:'):
            doi = doi.strip('doi:')
        elif doi.startswith('DOI:'):
            doi = doi.strip('DOI:')
        return doi

    @property
    def valid(self):
        return self.suffix is not None and self.suffix.startswith('10.')

    def validate(self):
        if not self.valid:
            raise exc.MalformedIdentifierError(f'{self._unnormalize} does not appear '
                                               f'to be of type {self.__class__}')


class Doi(idlib.Stream, idlib.Uri, idlib.Handle):  # FIXME that 'has canonical representaiton as a uri' issue
    """ The DOI stream. """

    _family = idlib.families.ISO
    _id_class = DoiId

    def __init__(self, doi_in_various_states_of_mangling=None, iri=None):
        self._identifier = self._id_class(doi_in_various_states_of_mangling, iri)

    @property
    def identifier(self):
        return self._identifier

    @property
    def id_bound_metadata(self):  # FIXME bound_id_metadata bound_id_data
        metadata = self.metadata()
        # wouldn't it be nice if all the metadata schemas had a common field called 'identifier' ?
        URL = metadata['URL']
        DOI = metadata['DOI']
        #prefix = metadata['prefix']  # NOTE NOT the curie meaning of prefix
        return self._id_class(DOI)

    identifier_bound_metadata = id_bound_metadata

    @property
    def id_bound_ver_metadata(self):
        # DOIs are the metadat bound version identifier 
        # they run backwards compared to ontology ids
        # by (hopefully) pointing up to a collection
        return None

    identifier_bound_version_metadata = id_bound_ver_metadata

    @property
    def id_bound_data(self):
        data = self.data()  # FIXME mimetype ... from previous? icky
        # beautiful soup this fellow
        return None  # FIXME TODO

    identifier_bound_data = id_bound_data
    def progenitor(self):
        # FIXME there is no single progeneitor here ?
        # or rather, the stream is broken up into objects
        # long before we can do anything about it

        # also metadata headers and data headers are separate
        # possibly even more separate than desired, but of course
        # these aren't single streams, they are bundles of streams
        # so tuple ?
        self.headers()
        self.metadata()
        self.data()
        return self._chain_headers, self._resp_metadata, self._resp_data

    @cache_result
    def headers(self):
        self._chain_headers  = list(resolution_chain_responses(self))
        return self._chain_headers[-1].headers

    @cache_result
    def metadata(self):
        # e.g. crossref, datacite, etc.
        # so this stuff isnt quite to the spec that is doccumented here
        # https://crosscite.org/docs.html
        # nor here
        # https://support.datacite.org/docs/datacite-content-resolver
        accept = (
            'application/vnd.datacite.datacite+json, '  # first so it can fail
            'application/json, '  # undocumented fallthrough for crossref ?
        )
        resp = requests.get(self, headers={'Accept': accept})
        self._resp_metadata = resp  # FIXME for progenitor
        if resp.ok:
            return resp.json()
        else:
            resp.raise_for_status()  # TODO see if this is really a good idea or not

    @cache_result  # FIXME very much must cache these
    def _checksum(self, cypher):  # FIXME unqualified checksum goes to ... metadata ???
        m = cypher()
        metadata = self.metadata()
        ts_created = metadata['created']['timestamp']  # key errors inbound I'm sure
        m.update(self.identifier.checksum(cypher))
        m.update(self.id_bound_metadata.checksum(cypher))
        m.update(str(ts_created).encode())  # unix epoch -> ??
        return m.digest()


    def data(self, mimetype_accept=None):
        # FIXME TODO should the data associated with the doi
        # be the metadata about the object or the object itself?
        # from a practical standpoint derefercing the doi is
        # required before you can content negotiate on the
        # actual document itself, which is a practical necessity
        # if somewhat confusing
        self._resp_data = requests.get(self)  # FIXME TODO
        return self._resp_data.content

    # additional streams ...

    def ttl(self):  # this is another potential way to deal with mimetypes
        # both datacite and crossref produce in turtle
        resp = requests.get(self, headers={'Accept': 'text/turtle'})
        return resp.text

    def metadata_events(self):
        """ metadata about dois from the crossref events api """
        events_endpoint = 'https://api.eventdata.crossref.org/v1/events'
        rp = aug.RepoPath(__file__)
        try:
            email = rp.repo.config_reader().get_value('user', 'email')
            log.warning(f'your email {email} is being sent to crossref as part of the friendly way to use their api')
            mailto = f'mailto={email}'
        except aug.exceptions.NotInRepoError:
            # TODO failover to the git repo api?
            mailto = 'tgbugs+sparcur-no-git@gmail.com'

        resp_obj = requests.get(f'{events_endpoint}?{mailto}&obj-id={self.handle}')
        resp_sub = requests.get(f'{events_endpoint}?{mailto}&subj-id={self.handle}')
        # TODO if > 1000 get the rest using the pagination token
        yield from resp_sub.json()['message']['events']
        yield from resp_obj.json()['message']['events']


    # alternate representations

    def asHandle(self):
        return idlib.Handle(self.suffix)
