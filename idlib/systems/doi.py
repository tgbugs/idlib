import ontquery as oq  # temp implementation detail
import idlib
from idlib import formats
from idlib import streams
from idlib import exceptions as exc
from idlib import conventions as conv
from idlib.cache import cache
from idlib.utils import cache_result, log
from idlib.config import auth


class _DoiPrefixes(conv.QnameAsLocalHelper, oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


_DoiPrefixes({'DOI':'https://doi.org/',
              'doi':'https://doi.org/',})


class DoiId(oq.OntId, idlib.Identifier, idlib.Stream):  # also _technically_ a stream
    """ The actual representation of the DOI, but we'll ignore that for now """
    _namespaces = _DoiPrefixes
    _local_conventions = _namespaces
    _id_class = str  # eventually we have to drop down to something
    local_regex = '^10\.[0-9]{4,9}[-._;()/:a-zA-Z0-9]+$'
    canonical_regex = '^https:\/\/doi.org/10\.[0-9]{4,9}[-._;()/:a-zA-Z0-9]+$'

    def __new__(cls, doi_in_various_states_of_mangling=None, iri=None):
        if doi_in_various_states_of_mangling is None and iri is not None:
            doi_in_various_states_of_mangling = iri

        normalize = cls.normalize(doi_in_various_states_of_mangling)
        self = super().__new__(cls, prefix='doi', suffix=normalize)
        self._unnormalized = doi_in_various_states_of_mangling
        self.validate()
        return self

    #@property
    #def identifier(self):
        ## identifier streams return themselves as their identifier
        #return self

    def _checksum(self, cypher):
        m = cypher()
        m.update(self.identifier.encode())
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
            raise exc.MalformedIdentifierError(f'{self._unnormalized} does not appear '
                                               f'to be of type {self.__class__}')


# have to exclude, idlib.Uri, idlib.Handle because they are the identifiers NOT the
# streams, and the streams aren't just strings, oops!
# BUT WAIT: maybe we DO want to conflate them!
class Doi(formats.Rdf, idlib.Stream):  # FIXME that 'has canonical representaiton as a uri' issue
    """ The DOI stream. """

    _family = idlib.families.ISO
    _id_class = DoiId

    identifier_actionable = streams.StreamUri.identifier_actionable
    dereference_chain = streams.StreamUri.dereference_chain
    dereference = streams.StreamUri.dereference
    progenitor = streams.StreamUri.progenitor
    headers = streams.StreamUri.headers
    data = streams.StreamUri.data

    def __init__(self, doi_in_various_states_of_mangling=None, iri=None):
        self._identifier = self._id_class(doi_in_various_states_of_mangling, iri)

    def __gt__(self, other):
        if isinstance(other, idlib.Stream):
            return self.identifier > other.identifier
        else:
            return False  # FIXME TODO

    def progenitor(self):
        self.metadata()
        meta = self._resp_metadata if hasattr(self, '_resp_metadata') else self._path_metadata
        return self.dereference_chain(), meta

    @property
    def id_bound_metadata(self):  # FIXME bound_id_metadata bound_id_data
        metadata = self.metadata()
        # wouldn't it be nice if all the metadata schemas had a common field called 'identifier' ?
        URL = metadata['URL']
        DOI = metadata['DOI']
        #prefix = metadata['prefix']  # NOTE NOT the curie meaning of prefix
        return self._id_class(DOI)  # FIXME pretty sure this should just be self.__class__ ?

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

    @cache_result
    def metadata(self):
        metadata, path = self._metadata(self.identifier)
        # oh look an immediate violation of the URI assumption ...
        self._path_metadata = path
        return metadata

    @cache(auth.get_path('cache-path') / 'doi_json', create=True, return_path=True)
    def _metadata(self, identifier):
        # e.g. crossref, datacite, etc.
        # so this stuff isnt quite to the spec that is doccumented here
        # https://crosscite.org/docs.html
        # nor here
        # https://support.datacite.org/docs/datacite-content-resolver
        accept = (
            'application/vnd.datacite.datacite+json, '  # first so it can fail
            'application/json, '  # undocumented fallthrough for crossref ?
        )
        resp = self._requests.get(identifier, headers={'Accept': accept})
        self._resp_metadata = resp  # FIXME for progenitor
        if resp.ok:
            return resp.json()
        else:
            try:
                self._resp_metadata.raise_for_status()
            except Exception as e:
                if not resp.ok and resp.status_code != 404:  # FIXME control flow here is bad
                    try:
                        return self._metadata_datacite(identifier)
                    except Exception as e2:
                        try:
                            return self._metadata_crossref(identifier)
                        except Exception as e3:
                            raise exc.RemoteError(identifier) from e3
                else:
                    raise exc.RemoteError(identifier) from e

    def _metadata_crossref(self, identifier):
        """ Sometimes crossref will barf due to redirecting to
        https://api.crossref.org/v1/works/{shoulder}/{id}/transform
        instead of just
        https://api.crossref.org/v1/works/{shoulder}/{id}
        """
        accept = (
            'application/json, '
        )
        crossref_api = f"https://api.crossref.org/v1/works/{identifier.suffix}"
        resp = self._requests.get(crossref_api, headers={'Accept': accept})
        self._resp_metadata = resp  # FIXME for progenitor
        if resp.ok:
            j = resp.json()
            return j['message']
        else:
            try:
                self._resp_metadata.raise_for_status()
            except Exception as e:
                raise exc.RemoteError(identifier) from e

    def _metadata_datacite(self, identifier):
        """ Try to get data directly from datacite api """
        # FIXME TODO this is why we need a remote/repository class
        # to simplify requesting data on an identifier from a remote
        # what we have here does not compose well at all
        accept = (
            'application/vnd.datacite.datacite+json, '  # first so it can fail
            'application/json, '  # undocumented fallthrough for crossref ?
        )
        datacite_api = f"https://api.datacite.org/dois/{identifier.suffix}"
        resp = self._requests.get(datacite_api, headers={'Accept': accept})
        self._resp_metadata = resp  # FIXME for progenitor
        if resp.ok:
            return resp.json()
        else:
            try:
                self._resp_metadata.raise_for_status()
            except Exception as e:
                raise exc.RemoteError(identifier) from e

    @cache_result  # FIXME very much must cache these
    def _checksum(self, cypher):  # FIXME unqualified checksum goes to ... metadata ???
        m = cypher()
        metadata = self.metadata()
        ts_created = metadata['created']['timestamp']  # key errors inbound I'm sure
        m.update(self.identifier.checksum(cypher))
        m.update(self.id_bound_metadata.checksum(cypher))
        m.update(str(ts_created).encode())  # unix epoch -> ??
        return m.digest()

    # additional streams ...

    def ttl(self):  # this is another potential way to deal with mimetypes
        # both datacite and crossref produce in turtle
        resp = self._requests.get(self.identifier, headers={'Accept': 'text/turtle'})
        self._ttl_resp = resp
        ct = resp.headers['Content-Type']  # FIXME this can KeyError !?
        if 'text/html' in ct:
            # sigh blackfynn
            log.warning(f'{resp.url} is not turtle it is {ct}')  # FIXME duplicate log messages happen here
            return
        else:
            return resp.text

    def metadata_events(self):
        """ metadata about dois from the crossref events api """
        import augpathlib as aug
        events_endpoint = 'https://api.eventdata.crossref.org/v1/events'
        rp = aug.RepoPath(__file__)  # FIXME need __file__ from the calling scope
        try:
            email = rp.repo.config_reader().get_value('user', 'email')
            log.warning(
                (f'your email {email} is being sent to crossref as '
                 'part of the friendly way to use their api'))
            mailto = f'mailto={email}'
        except aug.exceptions.NotInRepoError:
            # TODO failover to the git repo api?
            mailto = 'tgbugs+idlib-no-git@gmail.com'

        handle = self.identifier.suffix
        resp_obj = self._requests.get(f'{events_endpoint}?{mailto}&obj-id={handle}')
        resp_sub = self._requests.get(f'{events_endpoint}?{mailto}&subj-id={handle}')
        # TODO if > 1000 get the rest using the pagination token
        yield from resp_sub.json()['message']['events']
        yield from resp_obj.json()['message']['events']

    # normalized fields

    @property
    def title(self):
        m = self.metadata()
        if 'title' in m:
            return m['title']

        elif 'titles' in m and m['titles']:
            # arbitrary choice to return the first
            return m['titles'][0]['title']

    label = title
    synonyms = tuple()

    @property
    def description(self):
        m = self.metadata()
        breakpoint()

    @property
    def resourceTypeGeneral(self):
        m = self.metadata()
        rtg = 'resourceTypeGeneral' 
        if 'types' in m and rtg in m['types']:
            return m['types'][rtg]

    @property
    def category(self):  # FIXME naming
        """ this is the idlib normalized type of the dereferenced object
        """
            # using category since it matches well with the ontology and registry naming
            # and avoids collisions with type, resourceType, etc.

        rtg = self.resourceTypeGeneral
        if rtg:
            return rtg

        m = self.metadata()
        if 'source' in m and m['source'] == 'Crossref':
            # FIXME sigh ... need representaitons for each
            # type of metadata to avoid this nonsense

            # XXX WARNING the type field on protocols.io records is WRONG
            # dataset was listed because there was no other type that was close
            # so consider that field garbage
            ct = 'container-title'
            if ct in m and m[ct] == 'protocols.io':
                return 'Protocol'

            aj = 'article-journal'
            if 'type' in m and m['type'] == aj:
                return 'ArticleJournal'

    # output streams

    def _triples_gen(self,
                     rdflib=None,
                     rdf=None,
                     rdfs=None,
                     owl=None,
                     NIFRID=None,
                     TEMP=None,
                     **kwargs):
        """ implementation of method to produce a
            triplified version of the record """
        s = self.asType(rdflib.URIRef)
        yield s, rdf.type, owl.NamedIndividual
        try:
            if self.category:
                yield s, rdf.type, rdflib.URIRef(TEMP[self.category])  # FIXME TODO
        except exc.ResolutionError as e:
            log.exception(e)
            yield s, TEMP.resolutionError, rdflib.Literal(True)
            return
        except exc.RemoteError as e:
            log.exception(e)
            yield s, TEMP.remoteError, rdflib.Literal(True)
            return

        yield s, rdfs.label, rdflib.Literal(self.label)

    # alternate representations

    def asHandle(self):
        return idlib.Handle(self.identifier.suffix)

    def asUri(self, asType=None):
        return (self.identifier.iri
                if asType is None else
                asType(self.identifier.iri))
