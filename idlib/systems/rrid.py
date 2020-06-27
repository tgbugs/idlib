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
        id = metadata['rrid']['curie']
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
            source = metadata['hits']['hits'][0]['_source']
            return source

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
        proper_citation = metadata['rrid']['properCitation']
        m.update(self.identifier.checksum(cypher))
        m.update(self.id_bound_metadata.checksum(cypher))
        m.update(proper_citation.encode())
        for vuri in self.vendorUris:
            m.update(vuri.encode())

        return m.digest()

    @property
    def vendorUris(self):
        metadata = self.metadata()
        if 'vendors' in metadata:  # FIXME SCR continues to be a bad citizen >_<
            return [v['uri'] for v in metadata['vendors']]
        else:
            return []

    @property
    def name(self):
        m = self.metadata()
        if m is not None:
            return m['item']['name']

    label = name

    @property
    def synonyms(self):
        m = self.metadata()['item']
        fs = 'label', 'synonyms', 'abbreviations'
        out = []
        for f in fs:
            if f in m:
                for v in m[f]:
                    out.append(v)

        return out

    @property
    def description(self):
        return self.metadata()['item']['description']

    # alternate representations

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
