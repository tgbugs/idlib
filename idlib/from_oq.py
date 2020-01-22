import ontquery as oq  # temporary implementation detail
import pyontutils.core
import idlib


# from neurondm.simple
class OntTerm(pyontutils.core.OntTerm):
    """ ask things about a term! """
    skip_for_instrumentation = True

    def __new__(cls, *args, **kwargs):
        self = OntId.__new__(cls, *args, **kwargs)
        self._args = args
        self._kwargs = kwargs
        return self

    def fetch(self):
        newself = super().__new__(self.__class__, *self._args, **self._kwargs)
        self.__dict__ = newself.__dict__
        return self


class DoiPrefixes(oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


DoiPrefixes({'DOI':'https://doi.org/',
             'doi':'https://doi.org/',})


class DoiId(OntId):
    _namespaces = DoiPrefixes

    class DoiMalformedError(Exception):
        """ WHAT HAVE YOU DONE!? """

    def __new__(cls, doi_in_various_states_of_mangling=None, iri=None):
        if doi_in_various_states_of_mangling is None and iri is not None:
            doi_in_various_states_of_mangling = iri

        normalize = idlib.Doi.normalize(doi_in_various_states_of_mangling)
        self = super().__new__(cls, prefix='doi', suffix=normalize)
        self._unnormalized = doi_in_various_states_of_mangling
        return self

    @property
    def valid(self):
        return self.suffix is not None and self.suffix.startswith('10.')

    def asInstrumented(self):
        return DoiInst(self)

    @property
    def handle(self):
        return self.suffix


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


class DoiInst(URIInstrumentation, DoiId):
    # TODO FIXME pull this into idlib or whatever we are calling it
    #def __new__(self, doi_thing):
        # FIXME autofetch ... hrm ... data vs metadata ...
        #return super().__new__(doi_thing)

    @property
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
        if resp.ok:
            return resp.json()
        else:
            resp.raise_for_status()  # TODO see if this is really a good idea or not

    @property
    def ttl(self):
        # both datacite and crossref produce in turtle
        resp = requests.get(self, headers={'Accept': 'text/turtle'})
        return resp.text

    @property
    def data(self):
        # FIXME TODO should the data associated with the doi
        # be the metadata about the object or the object itself?
        # from a practical standpoint derefercing the doi is
        # required before you can content negotiate on the
        # actual document itself, which is a practical necessity
        # if somewhat confusing
        return self.metadata

    @property
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


class OrcidPrefixes(oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


OrcidPrefixes({'orcid':'https://orcid.org/',
               'ORCID':'https://orcid.org/',})


class OrcidId(OntId):
    _namespaces = OrcidPrefixes

    class OrcidMalformedError(Exception):
        """ WHAT HAVE YOU DONE!? """

    class OrcidLengthError(OrcidMalformedError):
        """ wrong length """

    class OrcidChecksumError(OrcidMalformedError):
        """ failed checksum """

    @property
    def checksumValid(self):
        """ see
        https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier
        """

        try:
            *digits, check_string = self.suffix.replace('-', '')
            check = 10 if check_string == 'X' else int(check_string)
            total = 0
            for digit_string in digits:
                total = (total + int(digit_string)) * 2

            remainder = total % 11
            result = (12 - remainder) % 11
            return result == check
        except ValueError as e:
            raise self.OrcidChecksumError(self) from e


class _PioPrefixes(oq.OntCuries): pass
PioPrefixes = _PioPrefixes.new()
PioPrefixes({'pio.view': 'https://www.protocols.io/view/',
             'pio.edit': 'https://www.protocols.io/edit/',  # sigh
             'pio.private': 'https://www.protocols.io/private/',
             'pio.fileman': 'https://www.protocols.io/file-manager/',
             'pio.api': 'https://www.protocols.io/api/v3/protocols/',
})


class PioId(OntId):
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


class PioInst(URIInstrumentation, PioId):
    """ instrumented protocols """
    # FIXME defining this here breaks the import chain
    # since protocols.py imports from core.py (sigh)
    _wants_instance = '.protocols.ProtocolData'  # this is an awful pattern
    # but what do you want :/

    @property
    def doi(self):
        data = self.data
        if data:
            doi = data['doi']
            if doi:
                return DoiId(doi)

    @property
    def uri_human(self):  # FIXME HRM ... confusion with pio.private iris
        """ the not-private uri """
        data = self.data
        if data:
            uri = data['uri']
            if uri:
                return self.__class__(prefix='pio.view', suffix=uri)

    @property
    def data(self):
        if not hasattr(self, '_data'):
            blob = self._protocol_data.protocol(self.iri)
            self._status_code = blob['status_code']
            self._data = blob['protocol']

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


class PioUserId(OntId):
    _namespaces = PioUserPrefixes


class PioUserInst(URIInstrumentation, PioUserId):
    _wants_instance = '.protocols.ProtocolData'  # this is an awful pattern

    @property
    def uri_human(self):
        return self.__class__(prefix='pio.user', suffix=self.suffix)

    @property
    def uri_api(self):
        return self.__class__(prefix='pio.api.user', suffix=self.suffix)

    @property
    def data(self):
        if not hasattr(self, '_data'):
            uri = self.uri_api + '?with_extras=1'
            # FIXME this is a dumb an convoluted way to get authed api access
            blob = self._protocol_data.get(uri)
            self._status_code = blob['status_code']
            self._data = blob['researcher']

        return self._data

    @property
    def orcid(self):
        orcid = self.data['orcid']
        if orcid is not None:
            return OrcidId(prefix='orcid', suffix=orcid)


class _RorPrefixes(oq.OntCuries): pass
RorPrefixes = _RorPrefixes.new()
RorPrefixes({'ror': 'https://ror.org/',
             'ror.api': 'https://api.ror.org/organizations/',
})


class RorId(OntId):
    _namespaces = RorPrefixes
    # TODO checksumming
    # TODO FIXME for ids like this should we render only the suffix
    # since the prefix is redundant with the identifier type?
    # initial answer: yes


class RorInst(URIInstrumentation, RorId):

    @property
    def data(self):
        return self._data(self.suffix)

    @cache(Path(auth.get_path('cache-path'), 'ror_json'), create=True)
    def _data(self, suffix):
        # TODO data endpoint prefix ?? vs data endpoint pattern ...
        resp = requests.get(RorId(prefix='ror.api', suffix=suffix))
        if resp.ok:
            return resp.json()

    @property
    def name(self):
        return self.data['name']

    label = name  # map their schema to ours

    def asExternalId(self, id_class):
        eids = self.data['external_ids']
        if id_class._ror_key in eids:
            eid_record = eids[id_class._ror_key]
            if eid_record['preferred']:
                eid = eid_record['preferred']
            else:
                eid_all = eid_record['all']
                if isinstance(eid_all, str):  # https://github.com/ror-community/ror-api/issues/53
                    eid = eid_all
                else:
                    eid = eid_all[0]

            return id_class(eid)

    _type_map = {
        'Education': TEMP.Institution,
        'Healthcare': TEMP.Institution,
        'Facility': TEMP.CoreFacility,
        'Nonprofit': TEMP.Nonprofit,
        'Other': TEMP.Institution,
    }
    @property
    def institutionTypes(self):
        if 'types' in self.data:
            for t in self.data['types']:
                if t == 'Other':
                    log.info(self.label)

                yield self._type_map[t]

        else:
            log.critical(self.data)
            raise TypeError('wat')

    @property
    def synonyms(self):
        d = self.data
        # FIXME how to deal with type conversion an a saner way ...
        yield from [rdflib.Literal(s) for s in d['aliases']]
        yield from [rdflib.Literal(s) for s in d['acronyms']]
        yield from [rdflib.Literal(l['label'], lang=l['iso639']) for l in d['labels']]

    @property
    def triples_gen(self):
        """ produce a triplified version of the record """
        s = self.u
        a = rdf.type
        yield s, a, owl.NamedIndividual
        for o in self.institutionTypes:
            yield s, a, o

        yield s, rdfs.label, rdflib.Literal(self.label)
        for o in self.synonyms:
            yield s, NIFRID.synonym, o  # FIXME this looses information about synonym type

        # TODO also yeild all the associated grid identifiers


class IsniId(OntId):  # TODO
    prefix = 'http://isni.org/isni/'
    _ror_key = 'ISNI'


class AutoId:
    """ dispatch to type on identifier structure """
    def __new__(cls, something):
        if '10.' in something:
            if 'http' in something and 'doi.org' not in something:
                pass  # probably a publisher uri that uses the handle
            else:
                return DoiId(something)

        if 'orcid' in something:
            return OrcidId(something)

        if '/ror.org/' in something or something.startswith('ror:'):
            return RorId(something)

        if 'protocols.io' in something:
            return PioId(something)

        return OntId(something)


class AutoInst:
    def __new__(cls, something):
        return AutoId(something).asInstrumented()


def get_right_id(uri):
    # FIXME this is a bad way to do this ...
    if isinstance(uri, DoiId) or 'doi' in uri and '/doi/' not in uri:
        if isinstance(uri, DoiId):
            di = uri.asInstrumented()
        elif 'doi' in uri:
            di = DoiInst(uri)

        pi = di.resolve(PioId)

    else:
        if not isinstance(uri, PioId):
            pi = PioId(uri)  #.normalize()
        else:
            pi = uri

    return pi
