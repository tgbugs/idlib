import re
import idlib
from idlib import formats
from idlib import streams
from idlib import exceptions as exc
from idlib import conventions as conv
from idlib.cache import cache, COOLDOWN
from idlib.utils import cache_result, log
from idlib.config import auth


class RridId(idlib.Identifier):

    canonical_regex = 'RRID:([A-Za-z]+)_([A-Za-z0-9_:-]+)'
    # NOTE: the canonical regex fails to capture a couple
    # of legacy cases e.g. RRID:WB-STRAIN_ and RRID:MGI:
    # yes I understand why MGI doesn't want RRID:MGI_MGI:
    # but what other identifier namespaces do they use?
    _variant_regex = 'RRID:([A-Z]+):([A-Za-z0-9_:-]+)'  # legacy
    _local_conventions = conv.Identity

    def __init__(self, rrid):
        self._identifier = rrid
        self.authority, self.authority_local_identifier = self.validate()

    def __str__(self):
        return self.identifier

    def validate(self):
        match = re.match(self.canonical_regex, self.identifier)
        if match is None:
            raise exc.MalformedIdentifierError(self.identifier)

        authority, authority_local_identifier = match.groups()
        return authority, authority_local_identifier

    def _checksum(self, cypher):
        m = cypher()
        m.update(self.identifier.encode())
        return m.digest()


class Rrid(formats.Rdf, idlib.HelperNoData, idlib.Stream):

    _id_class = RridId

    _resolver_template = 'https://scicrunch.org/resolver/{id}'

    _COOLDOWN = False

    identifier_actionable = streams.StreamUri.identifier_actionable
    dereference_chain = streams.StreamUri.dereference_chain
    dereference = streams.StreamUri.dereference
    headers = streams.StreamUri.headers

    @property
    def id_bound_metadata(self):  # FIXME bound_id_metadata bound_id_data
        metadata = self.metadata()
        # wouldn't it be nice if all the metadata schemas had a common field called 'identifier' ?
        ids = set(m['rrid']['curie'] for m in metadata)
        assert len(ids) == 1, ids
        id = next(iter(ids))
        return self._id_class(id)

    identifier_bound_metadata = id_bound_metadata

    @property
    def id_bound_ver_metadata(self):
        # RRID records do not have a version at the moment
        # there is a UUID of ambiguous provenace and usefulness
        # but not formal version of the record
        return None

    identifier_bound_version_metadata = id_bound_ver_metadata

    @cache_result
    def metadata(self):
        metadata, path = self._metadata(self.identifier)
        # oh look an immediate violation of the URI assumption ...
        if metadata is not None:
            self._path_metadata = path
            self._progenitor_metadata_blob = metadata
            self._total_hits = metadata['hits']['total']
            source = [h['_source'] for h in metadata['hits']['hits']]
            return source

        return []

    def _cooldown(self):
        self._COOLDOWN = True
        metadata, path = self._metadata(self.identifier)
        return metadata

    @cache(auth.get_path('cache-path') / 'rrid_json', create=True, return_path=True)
    def _metadata(self, identifier):
        idq = self._resolver_template.format(id=identifier)
        #self._resp_metadata = self._requests.get(idq, headers={'Accept': 'application/json'})  # issue submitted
        self._resp_metadata = self._requests.get(idq + '.json')
        if self._resp_metadata.ok:
            return self._resp_metadata.json()
        elif self._COOLDOWN and self._resp_metadata.status_code == 404:
            msg = f'RRID failure: {self._resp_metadata.status_code} {self.asUri()}'
            return {COOLDOWN: msg,}
        else:
            try:
                self._resp_metadata.raise_for_status()
            except BaseException as e:
                raise exc.ResolutionError(identifier) from e

    @cache_result
    def _checksum(self, cypher):
        # FIXME unqualified checksum goes to ... metadata ???
        # TODO figure out what actuall constitues
        # the identity of the RRID record ...
        m = cypher()
        metadata = self.metadata()
        proper_citations = sorted([m['rrid']['properCitation'] for m in metadata])
        m.update(self.identifier.checksum(cypher))
        m.update(self.id_bound_metadata.checksum(cypher))
        for proper_citation in proper_citations:
            m.update(proper_citation.encode())

        return m.digest()

    @property
    def vendorUris(self):
        metadata = self.metadata()
        if 'vendors' in metadata:  # FIXME SCR continues to be a bad citizen >_<
            return [v['uri'] if 'uri' in v else None for v in metadata['vendors']]
        else:
            return []

    @property
    def name(self):
        ms = self.metadata()
        if ms:
            names = set(m['item']['name'] for m in ms)
            return sorted(names, key=len, reverse=True)[0]

    label = name

    @property
    def synonyms(self):
        ms = self.metadata()
        out = set()
        for m in ms:
            it = m['item']
            fs = 'label', 'name', 'nomenclature', 'synonyms', 'abbreviations'
            for f in fs:
                if f in it:
                    thing = it[f]
                    if isinstance(thing, list):
                        for v in thing:
                            if type(v) is dict:
                                if 'name' in v:
                                    for sigh in v['name'].split('. '):
                                        syn = sigh.strip()
                                        if syn:
                                            out.add(syn)
                                else:
                                    breakpoint()
                                    raise NotImplementedError(f'TODO {v}')
                            else:
                                out.add(v)
                    else:
                        out.add(thing)

        return sorted(out)

    @property
    def description(self):
        ms = self.metadata()
        if ms:
            descs = set(m['item']['description'] for m in ms if 'description' in m['item'])
            if descs:
                return sorted(descs, key=len, reverse=True)[0]

    def proper_citation(self):
        ms = self.metadata()
        if ms:
            cites = set(m['rrid']['properCitation'] for m in ms if 'rrid' in m and 'properCitation' in m['rrid'])
            if cites:
                return sorted(cites, key=len, reverse=True)[0]

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
        s = self.asUri(rdflib.URIRef)
        yield s, rdf.type, owl.NamedIndividual
        try:
            pc = self.proper_citation()
            if pc:
                yield s, TEMP.properCitation, rdflib.Literal(pc)
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

    def asDict(self):
        out = super().asDict()
        pc = self.proper_citation()
        if pc:
            out['proper_citation'] = pc

        return out

    def asUri(self, asType=None):
        # TODO n2t, identifiers.org
        # TODO TODO having an explicit model for resolver/metadata services
        # seems like it would subsume the SciGraph/ontquery services
        # along with a bunch of other things ... it would provide
        # proper separation between the implementation details of
        # the identifier classes and their various resolver services
        # this would allow us to sandbox the resolver de jour problem
        uri_string = self._resolver_template.format(id=self.identifier)
        return uri_string if asType is None else asType(uri_string)
