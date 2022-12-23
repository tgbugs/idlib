import re
from pathlib import Path
import ontquery as oq  # temp implementation detail
import idlib
from idlib import formats
from idlib import streams
from idlib import exceptions as exc
from idlib import conventions as conv
from idlib.cache import cache
from idlib.utils import cache_result, log, base32_crockford_decode
from idlib.config import auth


class _RorPrefixes(conv.QnameAsLocalHelper, oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


_RorPrefixes({'ror': 'https://ror.org/',
             'ror.api': 'https://api.ror.org/organizations/',})


class RorId(oq.OntId, idlib.Identifier):
    _namespaces = _RorPrefixes
    _local_conventions = _namespaces
    # TODO FIXME for ids like this should we render only the suffix
    # since the prefix is redundant with the identifier type?
    # initial answer: yes

    local_regex = r'^0([0-9a-z]{6})([0-9]{2})$'
    canonical_regex = '^https://ror.org/0[0-9a-z]{6}[0-9]{2}$'

    class RorMalformedError(exc.IdlibError):
        """ WHAT HAVE YOU DONE!? """

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        if self.prefix is None or self.suffix is None:
            raise cls.RorMalformedError(self)
        return self

    @property
    def checksumValid(self):
        """ <https://github.com/ror-community/ror-api/blob/4f91dcb1c4cdeb1c44c92c8c82dc984081585293/
            rorapi/management/commands/convertgrid.py#L11> """

        match = re.match(self.local_regex, self.suffix)
        if match is None:
            return False

        chars, checksum = match.groups()
        number = base32_crockford_decode(chars)
        check = 98 - ((number * 100) % 97)
        return check == int(checksum)

    def _checksum(self, cypher):
        m = cypher()
        m.update(self.identifier.encode())  # down to strings we go!
        return m.digest()


class Ror(formats.Rdf, idlib.HelperNoData, idlib.Stream):

    _id_class = RorId

    identifier_actionable = streams.StreamUri.identifier_actionable
    dereference_chain = streams.StreamUri.dereference_chain
    dereference = streams.StreamUri.dereference
    #progenitor = streams.StreamUri.progenitor
    headers = streams.StreamUri.headers
    #data = idlib.NoDataDereference.data
    #id_bound_data = idlib.NoDataDereference.id_bound_data  # FIXME reuse the Meta and Data from OntRes

    @property
    def checksumValid(self):
        return self._id_class(self.identifier).checksumValid

    @property
    def id_bound_metadata(self):  # FIXME bound_id_metadata bound_id_data
        metadata = self.metadata()
        # wouldn't it be nice if all the metadata schemas had a common field called 'identifier' ?
        id = metadata['id']
        return self._id_class(id)

    identifier_bound_metadata = id_bound_metadata

    @property
    def id_bound_ver_metadata(self):
        return

    identifier_bound_version_metadata = id_bound_ver_metadata

    @cache_result  # FIXME very much must cache these
    def _checksum(self, cypher):  # FIXME unqualified checksum goes to ... metadata ???
        m = cypher()
        metadata = self.metadata()
        name = metadata['name']
        m.update(self.identifier.checksum(cypher))
        m.update(self.id_bound_metadata.checksum(cypher))
        m.update(name.encode())  # unix epoch -> ??
        return m.digest()

    @cache_result
    def metadata(self):
        suffix = self.identifier.suffix
        metadata, path = self._metadata(suffix)
        # oh look an immediate violation of the URI assumption ...
        self._path_metadata = path
        return metadata

    @cache(auth.get_path('cache-path') / 'ror_json', create=True, return_path=True)
    def _metadata(self, suffix):
        # TODO data endpoint prefix ??
        # vs data endpoint pattern ...
        prefix = 'ror.api'  # NOTE THE CHANGE IN PREFIX
        idq = self._id_class(prefix=prefix, suffix=suffix)
        self._resp_metadata = self._requests.get(idq)
        if self._resp_metadata.ok:
            blob = self._resp_metadata.json()
            if len(blob) == 1 and 'errors' in blob:
                errors = blob['errors']
                if len(errors) == 1:
                    error = errors[0]
                    if 'does not exist' in error:
                        # FIXME pretty sure this should be a used to
                        # exist error in the example that causes this
                        raise exc.IdDoesNotExistError(self.identifier)
                    else:
                        raise exc.RemoteError(error)
                else:
                    raise exc.RemoteError(' '.join(errors))
            else:
                return blob
        else:
            try:
                self._resp_metadata.raise_for_status()
            except BaseException as e:
                # FIXME may not be a resolution error
                # if we are raising for status then it is definitely a RemoteError of some kind
                # or the remote telling us that we are in error
                raise exc.RemoteError(self.identifier) from e

    @property
    def name(self):
        return self.metadata()['name']

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
        'Education':  'Institution',
        'Healthcare': 'Institution',
        'Facility':   'CoreFacility',
        'Nonprofit':  'Nonprofit',
        'Other':      'Institution',
    }
    @property
    def institutionTypes(self):
        metadata = self.metadata()
        if 'types' in metadata:
            for t in metadata['types']:
                if t == 'Other':
                    log.info(self.label)

                yield self._type_map[t]

        else:
            log.critical(metadata)
            raise TypeError('wat')

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
        a = rdf.type
        yield s, a, owl.NamedIndividual  # this goes first in the event the rest fail
        for osuffix in self.institutionTypes:
            o = TEMP[osuffix]
            yield s, a, o

        yield s, rdfs.label, rdflib.Literal(self.label)
        for o in self.synonyms_rdf(rdflib):
            yield s, NIFRID.synonym, o  # FIXME this looses information about synonym type

        # TODO also yeild all the associated grid identifiers

    # normalized fields

    label = name  # map their schema to ours

    def synonyms_rdf(self, rdflib):  # FIXME annoying
        d = self.metadata()
        # FIXME how to deal with type conversion an a saner way ...
        yield from [rdflib.Literal(s) for s in d['aliases']]
        yield from [rdflib.Literal(s) for s in d['acronyms']]
        yield from [rdflib.Literal(l['label'], lang=l['iso639']) for l in d['labels']]

    @property
    def synonyms(self):
        out = []
        m = self.metadata()
        for a in m['aliases'] + m['acronyms']:
            out.append(a)

        for l in m['labels']:
            out.append(l['label'])

        return out

    # alternate representations

    def asUri(self, asType=None):
        return (self.identifier.iri
                if asType is None else
                asType(self.identifier.iri))
