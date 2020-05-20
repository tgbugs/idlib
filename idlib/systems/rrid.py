import re
import requests  # resolver dejoure
import idlib
from idlib import formats
from idlib import exceptions as exc
from idlib import conventions as conv
from idlib.cache import cache, COOLDOWN
from idlib.utils import cache_result, log
from idlib.config import auth


class RridId(idlib.Identifier):

    canonical_regex = 'RRID:([A-Z]+)_([A-Za-z0-9_:-]+)'
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


class Rrid(formats.Rdf, idlib.Stream):

    _id_class = RridId

    _resolver_template = 'https://scicrunch.org/resolver/{id}'

    _COOLDOWN = False

    @property
    def id_bound_metadata(self):  # FIXME bound_id_metadata bound_id_data
        metadata = self.metadata()
        # wouldn't it be nice if all the metadata schemas had a common field called 'identifier' ?
        id = metadata['item']['curie']
        return self._id_class(id)

    identifier_bound_metadata = id_bound_metadata

    @cache_result
    def metadata(self):
        metadata, path = self._metadata(self.identifier)
        # oh look an immediate violation of the URI assumption ...
        if metadata is not None:
            self._path_metadata = path
            source = metadata['hits']['hits'][0]['_source']
            return source

    def _cooldown(self):
        self._COOLDOWN = True
        metadata, path = self._metadata(self.identifier)
        return metadata

    @cache(auth.get_path('cache-path') / 'rrid_json', create=True, return_path=True)
    def _metadata(self, identifier):
        idq = self._resolver_template.format(id=identifier)
        #self._resp_metadata = requests.get(idq, headers={'Accept': 'application/json'})  # issue submitted
        self._resp_metadata = requests.get(idq + '.json')
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
