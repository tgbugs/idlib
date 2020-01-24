from pathlib import Path
import requests  # resolver dejoure
import ontquery as oq  # temp implementation detail
from pyontutils.namespaces import TEMP  # FIXME VERY temp
import idlib
from idlib import formats
from idlib import streams
from idlib import exceptions as exc
from idlib.utils import cache_result, log

try:
    from sparcur.utils import cache  # temp
    from sparcur.config import auth as sauth  # temp
except ImportError as e:
    def cache(*args, return_path=False, **kwargs):
        def inner(*args, **kwargs):
            if return_path:
                return None, None
            else:
                return None

        return inner


    class _Sauth:
        def get_path(*args, **kwargs):
            return ''

    sauth = _Sauth()


class _RorPrefixes(oq.OntCuries): pass
RorPrefixes = _RorPrefixes.new()
RorPrefixes({'ror': 'https://ror.org/',
             'ror.api': 'https://api.ror.org/organizations/',
})


class RorId(oq.OntId, idlib.Identifier):
    _namespaces = RorPrefixes
    # TODO checksumming
    # TODO FIXME for ids like this should we render only the suffix
    # since the prefix is redundant with the identifier type?
    # initial answer: yes

    def _checksum(self, cypher):
        m = cypher()
        m.update(self.identifier.encode())  # down to strings we go!
        return m.digest()


class Ror(formats.Rdf, idlib.HelperNoData, idlib.Stream):

    _id_class = RorId

    dereference_chain = streams.StreamUri.dereference_chain
    dereference = streams.StreamUri.dereference
    #progenitor = streams.StreamUri.progenitor
    headers = streams.StreamUri.headers
    #data = idlib.NoDataDereference.data
    #id_bound_data = idlib.NoDataDereference.id_bound_data  # FIXME reuse the Meta and Data from OntRes

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

    @cache(Path(sauth.get_path('cache-path'), 'ror_json'), create=True, return_path=True)
    def _metadata(self, suffix):
        # TODO data endpoint prefix ??
        # vs data endpoint pattern ...
        prefix = 'ror.api'  # NOTE THE CHANGE IN PREFIX
        idq = self._id_class(prefix=prefix, suffix=suffix)
        self._resp_metadata = requests.get(idq)
        if self._resp_metadata.ok:
            return self._resp_metadata.json()

    @property
    def name(self):
        return self.metadata()['name']

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
        metadata = self.metadata()
        if 'types' in metadata:
            for t in metadata['types']:
                if t == 'Other':
                    log.info(self.label)

                yield self._type_map[t]

        else:
            log.critical(metadata)
            raise TypeError('wat')

    def synonyms(self, rdflib):
        d = self.metadata()
        # FIXME how to deal with type conversion an a saner way ...
        yield from [rdflib.Literal(s) for s in d['aliases']]
        yield from [rdflib.Literal(s) for s in d['acronyms']]
        yield from [rdflib.Literal(l['label'], lang=l['iso639']) for l in d['labels']]

    def _triples_gen(self,
                     rdflib=None,
                     rdf=None,
                     rdfs=None,
                     owl=None,
                     NIFRID=None,
                     **kwargs):
        """ produce a triplified version of the record """
        s = self.asType(rdflib.URIRef)
        a = rdf.type
        yield s, a, owl.NamedIndividual
        for o in self.institutionTypes:
            yield s, a, o

        yield s, rdfs.label, rdflib.Literal(self.label)
        for o in self.synonyms(rdflib):
            yield s, NIFRID.synonym, o  # FIXME this looses information about synonym type

        # TODO also yeild all the associated grid identifiers


