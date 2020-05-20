from pathlib import Path
import requests
import ontquery as oq  # temporary implementation detail
import idlib
from idlib import streams
from idlib import conventions as conv
from idlib.cache import cache
from idlib.utils import cache_result, log
from idlib.config import auth


# wiki has claims that Orcids are Isnis
# but I need more information ...


class OrcidPrefixes(conv.QnameAsLocalHelper, oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


OrcidPrefixes({'orcid': 'https://orcid.org/',
               'ORCID': 'https://orcid.org/',
               'orcid.pub.3': 'https://pub.orcid.org/v3.0/',})


class OrcidId(oq.OntId, idlib.Identifier):
    _namespaces = OrcidPrefixes
    _local_conventions = _namespaces
    canonical_regex = ('^https://orcid.org/0000-000(1-[5-9]|2-[0-9]|3-'
                       '[0-4])[0-9][0-9][0-9]-[0-9][0-9][0-9]([0-9]|X)$')

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

    def _checksum(self, cypher):
        m = cypher()
        m.update(self.identifier.encode())
        return m.digest()


class Orcid(idlib.HelperNoData, idlib.Stream):

    _id_class = OrcidId

    identifier_actionable = streams.StreamUri.identifier_actionable
    dereference_chain = streams.StreamUri.dereference_chain
    dereference = streams.StreamUri.dereference
    #progenitor = streams.StreamUri.progenitor
    headers = streams.StreamUri.headers

    @cache_result
    def metadata(self):
        suffix = self.identifier.suffix
        metadata, path = self._metadata(suffix)
        # oh look an immediate violation of the URI assumption ...
        self._path_metadata = path
        return metadata

    @cache(auth.get_path('cache-path') / 'orcid_json', create=True, return_path=True)
    def _metadata(self, suffix):
        # TODO data endpoint prefix ??
        # vs data endpoint pattern ...
        prefix = 'orcid.pub.3'  # NOTE THE CHANGE IN PREFIX
        idq = self._id_class(prefix=prefix, suffix=suffix)
        headers = {'Accept': 'application/orcid+json'}
        self._resp_metadata = requests.get(idq, headers=headers)
        if self._resp_metadata.ok:
            return self._resp_metadata.json()

    @property
    def id_bound_metadata(self):  # FIXME bound_id_metadata bound_id_data
        metadata = self.metadata()
        # wouldn't it be nice if all the metadata schemas had a common field called 'identifier' ?
        id = metadata['orcid-identifier']['uri']
        return self._id_class(id)

    identifier_bound_metadata = id_bound_metadata

    @property
    def id_bound_ver_metadata(self):
        # TODO
        return

    identifier_bound_version_metadata = id_bound_ver_metadata

    @cache_result  # FIXME very much must cache these
    def _checksum(self, cypher):  # FIXME unqualified checksum goes to ... metadata ???
        # TODO this is a bad checksum
        m = cypher()
        metadata = self.metadata()
        ts_submission = metadata['history']['submission-date']
        m.update(self.identifier.checksum(cypher))
        m.update(self.id_bound_metadata.checksum(cypher))
        m.update(str(ts_submission).encode())  # unix epoch -> ??
        return m.digest()

    # normalized fields

    @property
    def first_name(self):
        m = self.metadata()
        name = m['person']['name']
        if name:  # FIXME cull?
            gn = name['given-names']
            if gn:
                return gn['value']

    @property
    def last_name(self):
        m = self.metadata()
        name = m['person']['name']
        if name:  # FIXME cull?
            fn = name['family-name']
            if fn:
                return fn['value']

    @property
    def label(self):
        return ' '.join([n for n in (self.first_name, self.last_name) if n is not None])

    @property
    def synonyms(self):
        m = self.metadata()
        out = []
        for on in m['person']['other-names']['other-name']:
            out.append(on['content'])

        return out

    def asUri(self, asType=None):
        return (self.identifier.iri
                if asType is None else
                asType(self.identifier.iri))
