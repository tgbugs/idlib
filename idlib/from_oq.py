import json
from datetime import datetime
#import requests
import orthauth as oa
import ontquery as oq  # temporary implementation detail
import idlib
from idlib import apis
from idlib import streams
from idlib import exceptions as exc
from idlib import conventions as conv
from idlib.cache import cache, COOLDOWN
from idlib.utils import (log,
                         TZLOCAL,
                         cache_result,
                         base32_pio_encode,
                         base32_pio_decode)
from idlib.config import auth


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


class URIInstrumentation(oq.terms.InstrumentedIdentifier):  # XXX unused

    @property
    def headers(self):
        """ request headers """
        if not hasattr(self, '_headers'):
            resp = self._requests.head(self.iri)  # TODO status handling for all these
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


class _PioPrefixes(conv.QnameAsLocalHelper, oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


_PioPrefixes({'pio.view': 'https://www.protocols.io/view/',
              'pio.edit': 'https://www.protocols.io/edit/',  # sigh
              'pio.run': 'https://www.protocols.io/run/',  # sigh
              'pio.private': 'https://www.protocols.io/private/',
              'pio.fileman': 'https://www.protocols.io/file-manager/',
              'pio.api': 'https://www.protocols.io/api/v3/protocols/',
})


class PioId(oq.OntId, idlib.Identifier, idlib.Stream):
    _namespaces = _PioPrefixes
    _local_conventions = _namespaces
    canonical_regex = '^https://www.protocols.io/(view|edit|private|file-manager|api/v3/protocols)/'

    _slug_0_limit = 128  # 113 < ??? < 136
    _slug_0_m = 8
    _slug_0_b = 66010867

    _slug_1_limit = 671  # 651 < ??? < 671
    _slug_1_m = 8
    _slug_1_b = 280510195

    _slug_2_limit = 2082  # 2080 < 2082 < 2088
    _slug_2_m = 1024 ** 2 + 8  # 1048584
    _slug_2_b = 2111848180

    def __new__(cls, curie_or_iri=None, iri=None, prefix=None, suffix=None):
        if curie_or_iri is None and iri:
            curie_or_iri = iri

        if isinstance(curie_or_iri, idlib.Stream):
            normalized = curie_or_iri.identifier.identifier
        elif isinstance(curie_or_iri, idlib.Identifier):
            normalized = curie_or_iri.identifier
        elif curie_or_iri is not None:
            # FIXME trailing nonsense for abstract etc
            normalized = curie_or_iri.replace('://protocols.io', '://www.protocols.io')
        else:
            normalized = None

        self = super().__new__(cls,
                               curie_or_iri=normalized,
                               iri=iri,
                               prefix=prefix,
                               suffix=suffix)

        self._unnormalized = curie_or_iri if curie_or_iri else self.iri
        if self.prefix not in self._local_conventions:
            raise exc.MalformedIdentifierError(
                f'Not a protocols.io id: {self}')
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

    @property
    def slug_tail(self):
        if self.is_int():
            id = self.identifier_int
            if id < self._slug_0_limit:
                # the change happens somewhere between 113 and 136
                # superstition tells me that it is probably at 128 or 127
                # depending on the indexing used
                m = self._slug_0_m
                b = self._slug_0_b  # 66010867
                return base32_pio_encode(id * m + b)
            elif id < self._slug_1_limit:
                # the change happens somewhere between 651 and 671
                #m = 8
                #b = 280510195
                m = self._slug_1_m
                b = self._slug_1_b  # 66010867
                return base32_pio_encode(id * m + b)
            if id < self._slug_2_limit:
                # old impl that chops out the middle a
                m = self._slug_2_m
                b = self._slug_2_b - 1
                #full = base32_pio_encode(id * self._slug_2_m + self._slug_2_b - 1)
                full = base32_pio_encode(id * m + b)
                return full[:3] + full[-3:]
            else:
                m = self._slug_2_m
                b = self._slug_2_b
                return base32_pio_encode(id * m + b)
        else:
            return self.slug.rsplit('-', 1)[-1]  # FIXME private issue ...

    @property
    def identifier_int(self):
        if self.is_int():
            return int(self.suffix)

        elif not self.is_private():
            st = self.slug_tail
            if len(st) == 6:
                if st.startswith('b88'):  # FIXME magic number
                    m = self._slug_0_m
                    b = self._slug_0_b
                elif st.startswith('ims'):  # FIXME magic number
                    m = self._slug_1_m
                    b = self._slug_1_b
                elif st.startswith('mw9'):  # FIXME magic number
                    raise NotImplementedError('lacking examples')
                    #m = self._slug_1?_m
                    #b = self._slug_1?_b
                elif st.startswith('kx3'):  # FIXME magic number
                    raise NotImplementedError('lacking examples')
                    #m = self._slug_1?_m
                    #b = self._slug_1?_b
                elif st.startswith('iwg'):  # FIXME magic number
                    raise NotImplementedError('lacking examples')
                    #m = self._slug_1?_m
                    #b = self._slug_1?_b
                elif st.startswith('kva'):  # FIXME magic number
                    # FIXME make params accessible
                    m = 8
                    b = 355483379
                else:
                    # old impl that removes the middle a
                    # this affects identifiers < 2082
                    st = st[:3] + 'a' + st[3:]
                    m = self._slug_2_m
                    b = self._slug_2_b - 1
            else:
                m = self._slug_2_m
                b = self._slug_2_b

            # y = mx + b
            d, r = divmod((base32_pio_decode(st) - b), m)
            if r:  # we are in the strange low number regiem ?
                msg = ("Haven't figured out the equation for slugs of the form "
                       f'{st}. d = {d} r = {r}. The id may also be malformed.')
                raise NotImplementedError(msg)
                #breakpoint()

            return d

    @property
    def uri_api_int(self):
        pid = self.__class__(prefix='pio.api', suffix=str(self.identifier_int))
        if not isinstance(pid._progenitors, dict):
            # FIXME is are these really progenitors in the way we usually
            # think of them? ... maybe not?
            pid._progenitors = {}

        pid._progenitors['id-converted-from'] = self
        return pid

    def _checksum(self, cypher):
        m = cypher()
        m.update(self.identifier.encode())
        return m.digest()

    def is_private(self):
        return self.prefix == 'pio.private'

    def is_int(self):
        return self.prefix == 'pio.api' and self.suffix.isdigit()


def setup(cls, creds_file=None):
    """ because @classmethod only ever works in a single class SIGH """
    if creds_file is None:
        try:
            creds_file = auth.get_path('protocols-io-api-creds-file')
        except KeyError as e:
            raise TypeError('creds_file is a required argument'
                            ' unless you have it in secrets') from e

    _pio_creds = apis.protocols_io.get_protocols_io_auth(creds_file)
    cls._pio_header = oa.utils.QuietDict(
        {'Authorization': 'Bearer ' + _pio_creds.token})


class Pio(idlib.Stream):
    """ instrumented protocols """

    _id_class = PioId
    # FIXME defining this here breaks the import chain
    # since protocols.py imports from core.py (sigh)
    _wants_instance = '.protocols.ProtocolData'  # this is an awful pattern
    # but what do you want :/

    identifier_actionable = streams.StreamUri.identifier_actionable
    dereference_chain = streams.StreamUri.dereference_chain
    dereference = streams.StreamUri.dereference
    progenitor = streams.StreamUri.progenitor
    headers = streams.StreamUri.headers

    _setup = classmethod(setup)

    def __new__(cls, *args, **kwargs):
        # sadly it seems that this has to be defined explicitly
        return super().__new__(cls)

    __new__rest = __new__

    def __new__(cls, *args, **kwargs):
        """ self mutating call once setup style """
        cls._setup()
        cls.__new__ = cls.__new__rest
        return cls(*args, **kwargs)

    def __getnewargs_ex__(self):
        # LOL PYTHON
        # Oh you're approaching __new__ ?!
        # apparently using this pattern with __new__
        # breaks the way that loky deserializes things
        return ((self.identifier,), {})

    def __gt__(self, other):
        if isinstance(other, idlib.Stream):
            return self.identifier > other.identifier
        else:
            return False  # FIXME TODO

    @property
    def slug(self):
        return self.identifier.slug

    @property
    def slug_tail(self):
        return self.identifier.slug_tail

    @property
    def doi(self):
        data = self.data()
        if data:
            doi = data['doi']
            if doi:
                return idlib.Doi(doi)

    @property
    @cache_result  # caching this cuts time in half for 2 calls etc. 5s / 10s over 25k calls
    def uri_human(self):  # FIXME HRM ... confusion with pio.private iris
        """ the not-private uri """
        data = self.data()
        if data:
            uri = data['uri']
            if uri:
                return self.fromIdInit(prefix='pio.view', suffix=uri)

    id_bound_metadata = uri_human  # FIXME vs uri field
    identifier_bound_metadata = id_bound_metadata

    # I think this is the right thing to do in the case where
    # the identifier is the version identifier and versioning
    # is tracked opaquely in the data/metadata i.e. that there
    # is no collection/conceptual identifier
    id_bound_ver_metadata = id_bound_metadata
    identifier_bound_version_metadata = id_bound_ver_metadata

    @property
    def identifier_int(self):
        try:
            return self.data()['id']
        except exc.RemoteError as e:
            try:
                return self.identifier.identifier_int
            except NotImplementedError as e2:
                # internally it is not implemented
                # externally it is a bad id
                # raise the remote error since that is what consumers of this
                # property expect
                try:
                    raise e from exc.MalformedIdentifierError(self.identifier)
                except Exception as e3:
                    raise e3 from e2

    @property
    def uri_api_int(self):
        pid = self.fromIdInit(prefix='pio.api', suffix=str(self.identifier_int))
        if not isinstance(pid._progenitors, dict):
            # FIXME is are these really progenitors in the way we usually
            # think of them? ... maybe not?
            pid._progenitors = {}

        pid._progenitors['id-converted-from'] = self
        return pid

    def data(self, fail_ok=False):
        if not hasattr(self, '_data'):
            if not isinstance(self._progenitors, dict):
                # XXX careful about the contents going stale
                self._progenitors = {}

            apiuri = self.identifier.uri_api
            blob, path = self._get_data(apiuri)
            if 'stream-http' not in self._progenitors:
                self._progenitors['path'] = path

            if blob is None:
                with open(path, 'rt') as f:
                    blob = json.load(f)

                message = blob[COOLDOWN]
                if 'pio_status_code' not in blob:
                    log.critical(blob)
                    path.unlink()
                    raise NotImplementedError('asdf')

                sc = blob['pio_status_code']
                if sc == 212:  # Protocol does not exist
                    if fail_ok: return
                    raise exc.IdDoesNotExistError(message)
                elif sc in (250, 205):  # access requested, not authorized
                    if fail_ok: return
                    raise exc.NotAuthorizedError(message)
                else:
                    msg = f'unhandled pio status code {sc}\n' + message
                    raise NotImplementedError(msg)
            else:
                self._status_code = blob['status_code']
                self._data = blob['protocol']

        return self._data

    @cache(auth.get_path('cache-path') / 'protocol_json', create=True, return_path=True)
    def _get_data(self, apiuri):
        """ use apiuri as the identifier since it is distinct
            from other views of the protocol e.g. uri_human etc. """

        # TODO progenitors
        log.debug('going to network for protocols')
        resp = self._requests.get(apiuri, headers=self._pio_header)
        #log.info(str(resp.request.headers))
        self._progenitors['stream-http'] = resp
        if resp.ok:
            try:
                j = resp.json()  # the api is reasonably consistent
                return j
            except Exception as e:
                log.exception(e)
                raise e
        else:
            try:
                j = resp.json()
                sc = j['status_code']
                em = j['error_message']
                msg = (f'protocol issue {self.identifier} {resp.status_code} '
                       f'{sc} {em}')
                self._failure_message = msg  # FIXME HACK use progenitor instead
                return {COOLDOWN: msg,
                        'http_status_code': resp.status_code,
                        'pio_status_code': sc,
                        'error_message': em,}
                # can't return here because of the cache
            except Exception as e:
                log.exception(e)

    metadata = data  # FIXME

    @cache_result
    def _checksum(self, cypher):
        m = cypher()
        # FIXME TODO hasing of python objects ...
        metadata = self.metadata()
        #m.update(self.identifier.checksum(cypher))
        # XXX self.identifer cannot be included because
        # it makes it impossible to dealias tha various different referents
        m.update(self.id_bound_metadata.identifier.checksum(cypher))
        #m.update(self.version_id)  # unix epoch -> ??
        m.update(self.updated.isoformat().encode())  # in principle more readable
        #m.update(self.updated.timestamp().hex())
        return m.digest()

    @property
    def hasVersions(self):
        return bool(self.data()['has_versions'])

    @property
    def versions(self):
        yield from self.data()['versions']  # TODO ...

    @property
    def created(self):
        # FIXME I don't think this is TZLOCAL for any reason beyond accident of circumstances
        # I think this is PDT i.e. the location of the protocols.io servers
        tzl = TZLOCAL()
        return datetime.fromtimestamp(self.data()['created_on'], tz=tzl)

    @property
    def updated(self):
        tzl = TZLOCAL()
        return datetime.fromtimestamp(self.data()['changed_on'], tz=tzl)

    @property
    def title(self):
        data = self.data()
        if data:
            title = data['title']
            if title:
                return title

    label = title

    @property
    def creator(self):
        return PioUser('pio.user:' + self.data()['creator']['username'])

    @property
    def authors(self):
        class Author:
            def __init__(self, blob):
                self.blob = blob
                self.name = blob['name']

        for u in self.data()['authors']:
            yield Author(u)
            continue
            # FIXME TODO
            _username = u['username']
            username = (_username
                        if _username is not None else
                        (u['name'].replace(' ', '-') + 'FAKE'))
            uid = PioUserId(prefix='pio.user', suffix=username)
            pu = PioUser(uid)
            if _username is None:
                def metadata(self, __asdf=u):
                    return __asdf

            yield pu

    def asUri(self, asType=None):
        return (self.identifier.iri
                if asType is None else
                asType(self.identifier.iri))

    def asDict(self, include_description=False, include_private=True):
        if self.identifier.is_int():
            out = super().asDict(include_description)
            out['uri_human'] = self.uri_human.identifier  # prevent double embedding
            doi = self.doi
            if doi is not None:
                out['doi'] = doi
            return out
        else:
            try:
                uri_api_int = self.uri_api_int
                out = uri_api_int.asDict(include_description)
                if include_private and self.identifier.is_private():
                    out['uri_private'] = self.identifier  # FIXME some way to avoid leaking these if needed?
                return out
            except exc.RemoteError as e:
                # we don't have any metadata but we will return what little info we have
                return super().asDict(include_description)


class _PioUserPrefixes(conv.QnameAsLocalHelper, oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


_PioUserPrefixes({'pio.user': 'https://www.protocols.io/researchers/',
                  'pio.api.user': 'https://www.protocols.io/api/v3/researchers/',
})


class PioUserId(oq.OntId, idlib.Identifier, idlib.Stream):
    _namespaces = _PioUserPrefixes
    _local_conventions = _namespaces

    _checksum = PioId._checksum

    @property
    def uri_human(self):
        return self.__class__(prefix='pio.user', suffix=self.suffix)

    @property
    def uri_api(self):
        return self.__class__(prefix='pio.api.user', suffix=self.suffix)


class PioUser(idlib.HelperNoData, idlib.Stream):
    _id_class = PioUserId

    _get_data = Pio._get_data
    asUri = Pio.asUri
    _setup = classmethod(setup)

    identifier_actionable = streams.StreamUri.identifier_actionable
    dereference_chain = streams.StreamUri.dereference_chain
    dereference = streams.StreamUri.dereference
    progenitor = streams.StreamUri.progenitor
    headers = streams.StreamUri.headers

    def __new__(cls, *args, **kwargs):
        # sadly it seems that this has to be defined explicitly
        return object.__new__(cls)

    __new__rest = __new__

    def __new__(cls, *args, **kwargs):
        """ self mutating call once setup style """
        cls._setup()
        cls.__new__ = cls.__new__rest
        return cls(*args, **kwargs)

    def __getnewargs_ex__(self):
        # LOL PYTHON
        # Oh you're approaching __new__ ?!
        # apparently using this pattern with __new__
        # breaks the way that loky deserializes things
        return ((self.identifier,), {})

    @property
    def uri_human(self):
        return self.__class__(self.identifier.uri_human)

    @property
    def uri_api(self):
        return self.__class__(self.identifier.uri_api)

    id_bound_metadata = uri_human
    identifier_bound_metadata = id_bound_metadata
    id_bound_ver_metadata = id_bound_metadata
    identifier_bound_version_metadata = id_bound_ver_metadata

    @property
    def _id_act_metadata(self):
        """ the actionalble identifier that is directly used to
            retrieve metadata from the resolver

            TODO there is a better way to implement this which is
            split the metadata streams into their own classes
            where the metadata is now treated as data """
        # FIXME this isn't actuall the id_act
        # it is really just a convenient way to
        # skip dealing with the send_* arguments for
        # metadata and data, namely that the query argument
        # that we append here should be explicit either
        # as a default kwarg or something similar
        # the fact that query parameters can sometimes
        # be part of the identity of a thing vs used to
        # modify exactly which parts of a thing are returned
        # is problematic, but is also something that needs
        # to be tracked
        return self.uri_api.asUri() + '?with_extras=1'

    @cache_result
    def metadata(self):
        self._progenitors = {}
        blob, path = self._get_data(self._id_act_metadata)
        if 'stream-http' not in self._progenitors:
            self._progenitors['path'] = path

        if blob is not None:
            self._status_code = blob['status_code']
            return blob['researcher']
        else:
            return {'name': ''}

    def _metadata_refresh(self):
        # FIXME nasty code reuse issues here especially
        # around the fact that _refresh_cache can't be
        # passed along the scope unless the decorated function
        # does it manually, which kinda defeats the point

        self._progenitors = {}
        blob, path = self._get_data(self._id_act_metadata, _refresh_cache=True)
        return self.metadata()

    @cache_result  # FIXME XXX cache_result currently does not work if there are arguments!
    def _checksum(self, cypher):
        m = cypher()
        metadata = self.metadata()
        m.update(self.identifier.checksum(cypher))
        m.update(self.id_bound_metadata.identifier.checksum(cypher))
        orcid = self.orcid
        if orcid is not None:
            # use orcid.identifier.checksum to prevent
            # changes to the orcid record from causing
            # changes in the identity of the user record
            m.update(orcid.identifier.checksum(cypher))

    @property
    def orcid(self):
        orcid = self.metadata()['orcid']
        if orcid is not None:
            return idlib.Orcid.fromIdInit(prefix='orcid', suffix=orcid)

    @property
    def name(self):
        return self.metadata()['name']

    label = name

    @property
    def bio(self):
        return self.metadata()['bio']

    description = bio


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

        return oq.OntId(something)
        return OntTerm(something)  # use the better local version of OntTerm
