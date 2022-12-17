import json
from datetime import datetime
import orthauth as oa
import ontquery as oq  # temporary implementation detail
import idlib
from idlib import apis
from idlib import formats
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


_PioPrefixes({'pio.view': 'https://www.protocols.io/view/',  # XXX TODO .html !!! FINALLY
              'pio.edit': 'https://www.protocols.io/edit/',  # sigh
              'pio.run': 'https://www.protocols.io/run/',  # sigh
              'pio.private': 'https://www.protocols.io/private/',
              #'pio.fileman': 'https://www.protocols.io/file-manager/',  # XXX bad semantics
              #'pio.folders.api': 'https://www.protocols.io/api/v3/folders/',  # XXX bad semantics
              'pio.api': 'https://www.protocols.io/api/v3/protocols/',
              'pio.api1': 'https://www.protocols.io/api/v1/protocols/',
})


class PioId(oq.OntId, idlib.Identifier, idlib.Stream):
    _namespaces = _PioPrefixes
    _local_conventions = _namespaces
    canonical_regex = '^https://www.protocols.io/(view|edit|private|api/v3/protocols)/'

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

        try:
            self = super().__new__(cls,
                                   curie_or_iri=normalized,
                                   iri=iri,
                                   prefix=prefix,
                                   suffix=suffix)
        except PioId.Error as e:
            raise exc.MalformedIdentifierError((normalized, iri, prefix, suffix)) from e

        self._unnormalized = curie_or_iri if curie_or_iri else self.iri
        if self.prefix not in self._local_conventions:
            # protocols io fileman folders are not citable artifacts
            raise exc.MalformedIdentifierError(
                f'Not a protocols.io id: {self}')
        return self

    @property
    def uri_human(self):
        return self.__class__(prefix='pio.view', suffix=self.slug)

    @property
    def uri_api(self):
        #if self.prefix == 'pio.fileman':
            #prefix = 'pio.folders.api'  # XXX prefix won't work here, requires a suffix /ids SIGH
        #else:
            #prefix = 'pio.api'
        return self.__class__(prefix='pio.api', suffix=self.slug)

    @property
    def uri_api1(self):
        return self.__class__(prefix='pio.api1', suffix=self.slug)

    def normalize(self):
        return self

    @property
    def slug(self):
        if self.suffix is None:
            breakpoint()

        if self.suffix == 'None':
            log.warning(f'You have a Pio suffix that is the string \'None\'')

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

        elif self.is_private():
            # NOTE private ids are NOT random (which is likely bad)
            # and further more show consecutive behavior
            # which means that one is guessable from other (very bad)
            msg = ("Haven't figured out the equation for private -> id")
            raise NotImplementedError(msg)

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
        elif len(st) >= 12:  # new slug format and version nonsense
            raise NotImplementedError(f'not reverse engineered yet {st!r}')
            if st == 'yxmvmno69g3p':  # XXX the doi slug uses the old way, but internally they have some new way
                # 55784 'b2qgqdtw' 'yxmvmno69g3p' ''
                # 55789 'b2qmqdu6' '14egnzrrzg5d' 'v3' # next public
                # 55798 'b2qwqdxe' '8epv51pz5l1b' 'v5' # new slug used in the doi
                'https://www.protocols.io/view/55790'
                'https://www.protocols.io/view/protocol-for-chronic-implantation-of-patch-electro-yxmvmno69g3p/v1'
                breakpoint()
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
        return self.prefix in ('pio.api', 'pio.view') and self.suffix.isdigit()


def setup(cls, creds_file=None):
    """ because @classmethod only ever works in a single class SIGH """
    if creds_file is None:
        try:
            creds_file = auth.get_path('protocols-io-api-creds-file')
        except KeyError as e:
            raise TypeError('creds_file is a required argument'
                            ' unless you have it in secrets') from e

    try:
        _pio_creds = apis.protocols_io.get_protocols_io_auth(creds_file)
        cls._pio_header = oa.utils.QuietDict(
            {'Authorization': 'Bearer ' + _pio_creds.token})
    except exc.ConfigurationError as e:
        log.warning(e)
        cls._pio_header = None

    if not hasattr(idlib.Stream, '_requests'):
        idlib.Stream.__new__(cls)


class Pio(formats.Rdf, idlib.Stream):
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

    #_checked_whether_data_is_not_in_error = False
    #_data_is_in_error = True
    # we MUST assume that data is in error for all instances by
    # default until they prove otherwise HOWEVER the problem is that
    # you now also need another parameter which is whether you have
    # checked to see if it is NOT in error, sigh maybe in error? sigh
    # this becomes hasattr(self, '_data_in_error) and self._data_in_error

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
        try:
            if len(self.slug_tail) >= 12:
                hrm = self.__class__(self.identifier.uri_human)
                data = hrm.data1(noh=True)
            else:
                data = self.data3()  # XXX data1 cannot bootstrap itself right now
        except exc.RemoteError as e:
            data = None
            try:
                proj = self.progenitor(type='id-converted-from')
                # it should not be the case that we somehow find a
                # private id here because data would have traversed
                # and found it already and gotten the metadata
                # FIXME doi, other int, private should all not be here
                if not proj.identifier.is_int():
                    return proj
                else:
                    raise e
            except KeyError as e2:
                raise e
        if data:
            uri = data['uri']
            if uri:
                return self.fromIdInit(prefix='pio.view', suffix=uri)

    @property
    def uri_human_html(self):
        return self.fromIdInit(prefix='pio.view', suffix=f'{self.identifier_int}.html')

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
        idint = self.identifier_int

        if not isinstance(idint, int):
            raise TypeError(f'what the {idint}')

        pid = self.fromIdInit(prefix='pio.api', suffix=str(idint))

        if not isinstance(pid._progenitors, dict):
            # FIXME is are these really progenitors in the way we usually
            # think of them? ... maybe not?
            pid._progenitors = {}

        pid._progenitors['id-converted-from'] = self
        return pid

    # XXXXX WARNING IF YOU CHANGE THIS CLEAR THE CACHE OF v1 urls!
    fields = '?fields[]=' + '&fields[]='.join(
        ( # FIXME TODO need to match this list up to other things we need
            'doi',
            'protocol_name',
            'protocol_name_html',
            'creator',
            'authors',
            'description',
            'link',
            'created_on',
            'last_modified',
            'public',
            'doi_status',
            'materials',
            #'materials_text',
            'version',
            'keywords',
            'steps',
            'child_steps',
            )
    )

    def _get_direct(self, apiuri):#, cache=True):
        if not isinstance(self._progenitors, dict):
            # XXX careful about the contents going stale
            self._progenitors = {}

        # XXX this can only get public protocols because
        # we don't have a sane way to log in as a users
        # to get a logged in bearer token
        resp1 = self._requests.get(self.asUri())
        user_jwt = self._get_user_jwt(resp1)
        headers = {'Authorization': f'Bearer {user_jwt}'}
        # XXX the new version slugs have /v1 and /v3 tails >_< AAAAAAAAAAAAAAAAA
        # XXX this substitution may not work as expected
        gau = (apiuri
               #.replace('www', 'go')
               .replace('/v3/', '/v1/'))
        #if cache:
            #oph = self._pio_header
            #try:
                #self._pio_header = headers
                #return self._get_data(gau + self.fields)
            #finally:
                #self._pio_header = oph
        #else:
        resp = self._requests.get(gau + self.fields, headers=headers)
        return resp


    def _data_direct(self, noh=False):
        if noh:
            # XXX noh assumes that the originating form was a uri_human use at own risk
            return self._get_direct(self.identifier.uri_api)
        else:
            return self.uri_human._get_direct(self.identifier.uri_api)

    def data1(self, fail_ok=False, noh=False):
        # FIXME this depends on data3 for uri_human and cannot be used alone at the moment
        # FIXME also only seems to work for public protocols at the moment?

        # FIXME needs robobrowser or similar to function without issues
        # because there is no oauth for it
        # get data from the api/v1 endpoint which is is needed for unmangled steps
        resp = self._data_direct(noh=noh)
        j = resp.json()
        if 'protocol' not in j:  # FIXME SIGH
            if 'status_code' in j and j['status_code'] in (250, 205):
                message = j['text'] + ' ' + self.identifier.asStr()
                raise exc.NotAuthorizedError(message)

            return None

        data = j['protocol']
        return data

    def data3(self, fail_ok=False):
        if not hasattr(self, '_data'):
            self._data_in_error = True
            if not isinstance(self._progenitors, dict):
                # XXX careful about the contents going stale
                self._progenitors = {}

            apiuri = self.identifier.uri_api
            # FIXME XXX the v3 api is completely busted and is missing a ton of
            # information, for example it contains no information about substeps
            # they seemingly appear at random without indication on the ui
            # FIXME the better way is to use
            # /v1/protocols/{private-token} which gets us what we need more easily
            # however this is not trivial to retrive
            # the /v3/protocols/{id} endpoint returns bad/mangled data and we need
            # the /v1/ data to be able to actually render to org
            blob, path = self._get_data(apiuri)
            if 'stream-http' not in self._progenitors:
                self._progenitors['path'] = path

            if blob is None:
                # XXX NOTE this assumes that path.exists() == True
                # XXX whiiich turns out to be a bad assumption ...
                if not path.exists():
                    msg = f'assumption violation cache {path} dne for {self}'
                    log.critical(msg)
                    # TODO raise error or something, or figure out the
                    # conditions under which this assumption goes bad
                    return

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
                    try:
                        # there might be a private id in the progenitor chain
                        nself = self.progenitor(type='id-converted-from')
                        # FIXME TODO this works, but it would be nice if we
                        # could use this to populate the cache for the public
                        # api identifier as well
                        return nself.data(fail_ok=fail_ok)
                    except KeyError as e:
                        pass

                    if fail_ok: return
                    raise exc.NotAuthorizedError(message)
                elif sc in (429,):  # too many requests
                    if fail_ok: return
                    path.unlink()  # hopefully works next time?
                    raise exc.AccessLimitError(message)
                elif sc in (400,):
                    # probably trying to get a pio.view:*.json url
                    # their api is returning nonsense with 400 since
                    # there is nothing wrong with the request ...
                    if fail_ok: return
                    raise exc.NotAuthorizedError(message)
                else:
                    msg = f'unhandled pio status code {sc}\n' + message
                    raise NotImplementedError(msg)
            else:
                if 'status_code' in blob and 'protocol' in blob:
                    self._status_code = blob['status_code']
                    self._data = blob['protocol']
                elif 'id' in blob:  # not via the api
                    self._status_code = 200
                    self._data = blob
                else:
                    log.error(blob)
                    raise exc.RemoteError('no idea what is going on here')

            self._data_in_error = False

            if self._pio_header is None and not self.identifier.is_int():
                # XXX out of band load the uri api int value
                _uai = self.uri_api_int.identifier.uri_api
                self._hack_hash_value = blob
                self._get_data(_uai)

        return self._data

    # data = data3  # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

    def data(self, fail_ok=False):
        if not self.identifier.is_private() and len(self.slug_tail) >= 12:
            # FIXME this inverts what should be happening, which is
            # using this information to return the real uri_human and
            # then using that normalized uri instead of the crazy
            # version slug thing, however, we still want provenance
            # for how we got there, even if we toss the crazy slugs
            self._progenitors = {}  # FIXME yes this blasts progens every time
            uh = self.uri_human
            uai = uh.uri_api_int
            d3 = uai.data3(fail_ok=fail_ok)
            self._progenitors['id-converted-to'] = uai
            if 'path' in uai._progenitors:
                self._progenitors['path'] = uai._progenitors['path']
            elif 'stream-http' in uai._progenitors:
                self._progenitors['stream-http'] = uai._progenitors['stream-http']

            return d3
        else:
            return self.data3(fail_ok=fail_ok)

    def asOrg(self):
        from bs4 import BeautifulSoup

        def ct(text):
            return (text
                    .replace('\xa0', ' ')  # non breaking space, our old friend
                    .replace('\u202F', ' ')  # narrow no break space aka '\xe2\x80\xaf'
                    )

        sections = {}
        def hac(soup, cls):
            return soup.has_attr('class') and cls in soup.attrs['class']
        def hasty(soup, sty):
            return soup.has_attr('style') and sty in soup.attrs['style']

        def convert(soup, ind):
            if isinstance(soup, str):
                return soup.replace('\n', f'\n{ind}')

            tag = soup.name
            attrs = soup.attrs

            if tag == '[document]':
                return '\n'.join(convert(c, ind) for c in soup.children)
            if tag == 'html':
                return '\n'.join(convert(c, ind) for c in soup.children)
            if tag == 'head':
                return ''  # html5lib adds this section
                # raise NotImplementedError(f'well this is awkward\n{soup}')
            if tag == 'body':
                return '\n'.join(convert(c, ind) for c in soup.children)

            if tag == 'div' and hac(soup, 'text-blocks'):
                return '\n'.join(convert(c, ind) for c in soup.children)

            if (tag == 'div' and hac(soup, 'text-block')):
                return ''.join(convert(c, ind) for c in soup.children)

            if tag == 'div':
                # XXX watch out here may skip important div info
                return ''.join(convert(c, ind) for c in soup.children)

            if tag == 'img':
                # FIXME TODO need correct typesetting for these
                return f'{ind}[[imgl:{soup.get("src")}]]'
                #return f'\n{ind}#+attr_html: :style float: center; width: 50%;\n{ind}[[imgl:{soup.get("src")}]]'

            if tag == 'br':
                #return ' '
                return '\n'

            if tag == 'a':
                text = soup.text.strip()
                href = soup.get("href")
                if text:
                    return f'[[{href}][{soup.text}]]'
                elif href == '#':
                   return '{{{empty-link}}} '
                else:
                    breakpoint()
                    return f'[[{href}]]'

            if tag == 'ol':
                #bul = f'{ind}0. '
                #sep = f'\n{bul}'
                return ''.join(
                    f'\n{ind}{i + 1}. ' + convert(c, ind)
                    for i, c in enumerate(soup.children))

            if tag == 'ul':
                bul = f'{ind}- '
                sep = f'\n{bul}'
                return '- ' + sep.join(convert(c, ind) for c in soup.children)

            if tag == 'li':
                return ''.join(convert(c, ind) for c in soup.children)

            if tag == 'table':
                return '\n'.join(convert(c, ind) for c in soup.children)
            if tag == 'tbody':
                return '\n'.join(convert(c, ind) for c in soup.children)
            if tag == 'tr':
                return '| ' + ' | '.join(convert(c, ind) for c in soup.children)
            if tag == 'td':
                return ''.join(convert(c, ind) for c in soup.children).replace('\n', ' ')

            if tag == 'sup':
                text = ''.join(convert(c, ind) for c in soup.children)
                return '^{' + text + '}'  # FIXME this needs to be preceeded by something else

            if tag == 'style':
                return ''

            if tag == 'b':
                text = ''.join(convert(c, ind) for c in soup.children)
                ts = text.strip()
                if ts:
                    return '*' + ts + '*'
                else:
                    return ''

            if tag == 'span':
                childs = list(soup.children)
                text = ''.join(convert(c, ind) for c in childs)
                # FIXME combo
                mu = ''
                if hasty(soup, 'font-weight:bold'):
                    mu += '*'
                if hasty(soup, 'font-style:italic'):
                    mu += '/'
                if mu:
                    ts = text.strip()
                    if ts:
                        # FIXME the bane of trailing whitespace
                        return mu + ts + mu[::-1] + ' '
                    else:
                        return ' '

                return text

            if tag in ('o:p', 'pre', 'code'):
                # FIXME ignoring pre and code for now because what the heck are they doing
                # in the free text of protocols ?!
                # I have no idea what the heck this o:p thing is?
                # TODO skip tags group for other apparently empty tags?
                text = ''.join(convert(c, ind) for c in soup.children)
                if tag in ('pre', 'code'):
                    return f'#+html: <{tag}>\n{text}\n#+html: </{tag}>'
                else:
                    return text

            sigh = 'activation', 'simulation'  # FIXME hardcoded workaround
            # protocols.io does not properly escape/render angle brackets in text
            if tag in sigh:
                text = soup.text.replace('\n', f'\n{ind}')
                return ('\n' + ind +
                        '# WARNING THIS TEXT IS MANGLED DUE TO BAD OUTPUT FROM UPSTREAM\n' +
                        f'{ind}#+begin_mangled :tag {tag}\n{ind}{text}\n{ind}#+end_mangled')

            breakpoint()
            raise NotImplementedError((tag, soup))

        def block(type, source, ind):
            s = BeautifulSoup(source['body'], 'html5lib')
            # XXX protocols.io v3 produces malformed html sigh
            _text = convert(s, ind)
            text = _text.replace('\n', f'\n{ind}')  # FIXME see why we still need this? no?
            return f'{ind}#+begin_{type}\n{ind}{text}\n{ind}#+end_{type}'

        stitle = None
        def format_comp(comp, n, ind='  '):
            nonlocal stitle  # sigh
            title = comp['title']
            type_id = comp['type_id']
            source = comp['source']
            order_id = comp['order_id']

            if type_id == 1:  # description
                desc = source['description']
                s = BeautifulSoup(desc, 'html5lib')
                html = ('\n#+begin_export html\n' +
                        desc.replace('<', '\n<') +
                        '\n#+end_export')
                if order_id == 1:
                    tbs = s.find_all('div', 'text-block')
                    converted = [convert(b, ind) for b in tbs]
                    if not converted:
                        log.warning(f'empty?? {comp}')
                    if not sections[stitle]:
                        sections[stitle] = True
                        counter_set = f'[@{n}] '
                    else:
                        counter_set = ''

                    return f'{n}. {counter_set}' + '\n  '.join(converted)  # + html
                else:
                    return convert(s, ind)

                #ul = s.find_all('ul')
                #if ul:
                    #tbs = s.find_all('div', 'text-block')
                    #[b.find_all('li') if  for b in tbs]
                    #breakpoint()
                #return '0. ' + ct(s.text) + html

            elif type_id == 3:  # amount
                inp = source['title']
                unit = source['unit']
                amount = source['amount']
                return ind + f'{amount} {unit} {inp}'  # FIXME embed

            elif type_id == 4:  # duration
                duration = source['duration']
                unit = 'seconds'  # XXX I assume this is in seconds? no unit given
                return ind + f'{duration} {unit}'  # FIXME embed

            elif type_id == 6:  # section
                stitle = source['title']
                if stitle not in sections:
                    sections[stitle] = False
                    return f'** {stitle}'
                else:
                    return ''

            elif type_id == 7:  # external link
                breakpoint()
                raise NotImplementedError(comp)
            elif type_id == 8:  # software package
                name = source['name']
                dev = source['developer']
                dev = dev if dev else ''
                repo = source['repository']
                repo = repo if repo else ''
                return ind + '{{{software(' + ','.join((name, dev, repo)) + ')}}}'
            elif type_id == 9:  # dataset package
                breakpoint()
                raise NotImplementedError(comp)

            elif type_id == 13:  # comment
                #s = BeautifulSoup(source['body'], 'html5lib')
                #text = convert(s.find_all('div', {'class': 'text-blocks'})[0])
                breakpoint()
                raise NotImplementedError(comp)
                text = None # .replace('\n', f'\n{ind}')
                type = 'comment'  # FIXME TODO block type for typesetting
                return f'{ind}#+begin_{type}\n{ind}{text}\n{ind}#+end_{type}'  # FIXME indent

            elif type_id == 15:  # command package
                name = source['name']
                cname = source['command_name']
                cmd = source['command']
                os_name = source['os_name']
                os_version = source['os_version']
                osl = {'MATLAB': 'octave',}
                lang = osl[os_name] if os_name in osl else os_name

                out = (f'{ind}#+caption: {cmd}\n'
                       f'{ind}#+begin_src {lang} :runtime {os_name} :runtime-version {os_version}\n'
                       f'{ind}{name}\n{ind}#+end_src\n')
                _jd = json.dumps(source, indent=2)
                jd = _jd.replace('\n', f'\n{ind}')
                debug = f'\n{ind}#+begin_src json\n{jd}\n{ind}#+end_src\n'
                return out  # + debug

                breakpoint()
                raise NotImplementedError(comp)

            elif type_id == 17:  # expected result
                return block('expected_result', source, ind)

            elif type_id == 18:  # protocol
                # TODO account for these to see if there are
                # ones that are referenced that we don't already have ...
                # TODO on the site these are embedded directly into
                # the protocol, the issue of course is that I haven't
                # implemented intentation level yet, and transclusion
                # probably makes more sense anyway, also it is quite
                # a bit eaiser to understand what is going on when a
                # repeated protocol is not materialized into the page
                # it also reduces duplicate annotation
                _pid = self.identifier.__class__(
                    prefix='pio.api', suffix=str(source['id']))
                return ind + f'[[{_pid.asStr()}][{source["title"]}]]'

            elif type_id == 19:  # safety
                s = BeautifulSoup(source['body'], 'html5lib')
                _text = convert(s, ind)
                text = _text.replace('\n', f'\n{ind}').strip()  # FIXME see why we still need this?
                type = 'safety'  # FIXME TODO block type for typesetting
                return f'{ind}#+begin_{type}\n{ind}{text}\n{ind}#+end_{type}'

            elif type_id == 20:  # reagent
                name = source['name'].strip().replace('\n', ' ').replace(',','\\,')
                url = source['url']
                sku = source['sku']  # sometimes rrid lurks here
                rrid = source['rrid']
                vendor = source['vendor']
                if 'RRID:' in sku:
                    rrid = sku
                if rrid:
                    # may pop vendor info out elsewhere into materials or something?
                    return ind + '{{{' + f'rrid({name},{rrid})' + '}}}'
                    #return f'[[{url}][{name} ({rrid})]]'  # FIXME proper citation etc.

                vname = vendor['name']  # TODO put in materials section I think
                #vurl = vendor['url']

                # FIXME macro need to escape ,
                if sku and url:
                    return ind + '{{{reagent_skurl(' + name + ',' + sku + ',' + url + ')}}}'
                if url:
                    return ind + '{{{reagent_url(' + name + ',' + url + ')}}}'
                if sku:
                    return ind + '{{{reagent_sku(' + name + ',' + sku + ')}}}'

                if vname == 'Contributed by users':
                    return ind + '{{{reagent(' + name + ')}}}'  # TODO markup

                return ind + '{{{reagentv(' + ','.join((name, vname)) + ')}}}'

            elif type_id == 21:  # step cases
                breakpoint()
                raise NotImplementedError(comp)

            elif type_id == 22:  # goto previous step (ouch)
                breakpoint()
                raise NotImplementedError(comp)

            elif type_id == 23:  # file
                url = source['source']
                name = source['original_name']
                return f'{ind}[[{url}][{name}]]'  # TODO render file type somehow?

            elif type_id == 24:  # temperature
                unit = source['unit']
                value = source['temperature']
                if unit == 'Room temperature':
                    return ind + 'room temperature'
                elif unit == 'On ice':
                    # XXX FIXME on ice and ice cold are NOT always the same thing
                    # ice code has a fuzzy quantity associated with it, but
                    # on ice can mean something quite different in some circumstances
                    return ind + 'ice cold'  # FIXME embed
                elif unit == '°C':
                    return ind + f'{value} {unit}'  # FIXME embed

            elif type_id == 25:  # concentration
                _unit = source['unit']
                if _unit == 'Molarity (M)':
                    unit = 'mol/l'
                elif _unit == 'Micromolar (µM)':
                    unit = 'µmol/l'
                elif _unit == 'Nanomolar (nM)':
                    unit = 'nmol/l'
                elif _unit == 'Mass Percent':
                    unit = '% mass'
                elif _unit == 'Volume Percent':
                    unit = '% volume'
                elif _unit == 'Mass/Volume Percent':
                    # what in the name of all unholy dimensionalities is this !?!?
                    unit = '% mass/volume'
                else:
                    log.warning(f'unhandled unit {_unit}')
                    unit = _unit

                value = source['concentration']
                return ind + f'{value} {unit}'  # FIXME embedding :/

            elif type_id == 26:  # notes
                s = BeautifulSoup(source['body'], 'html5lib')
                _text = convert(s.find_all('div', {'class': 'text-blocks'})[0], ind)
                text = _text.replace('\n', f'\n{ind}')
                type = 'note'  # FIXME TODO block type for typesetting
                return f'{ind}#+begin_{type}\n{ind}{text}\n{ind}#+end_{type}'

            elif type_id == 28:  # equipment
                brand = source['brand']
                _sku = source['sku']
                sku = '' if _sku == 'N/A' or not _sku else _sku + ' '
                name = source['name']
                # TODO markup somehow maybe ?
                return ind + f'{name} ({sku}{brand})'

                breakpoint()
                raise NotImplementedError(comp)

            elif type_id == 30:  # centrifuge
                # TODO apparently there is a units field that can
                # be pulled back from a public protocol that is needed
                # to translate this section (WAT)
                if not hasattr(self.__class__, '_pio_units'):
                    # FIXME a bit more systematic approach perhaps
                    resp = self._requests.get(
                        'https://www.protocols.io/api/v3/units',
                        headers=self._pio_header)
                    j = resp.json()
                    self.__class__._pio_units = j['units']

                value = source['centrifuge']
                unit_id = source['unit']
                unit = 'times-earth-gravity' if unit_id == 34 else '???'

                # why the heck did they create yet another thing that
                # has an embedded temperature !?
                temp_unit_id = source['temperatureUnit']
                temp_unit = 'K' if temp_unit_id == 10 else '???'
                # there is no good way to do this ... 1000 m/s2
                return ind + f'{value} {unit}'

            breakpoint()
            raise NotImplementedError(comp)

        def format_step(step, n):
            comps = []
            for c in sorted(step['components'], # reverse=True,
                            key=lambda c: c['order_id']):
                fc = format_comp(c, n)
                comps.append(fc)

            # FIXME big problems here
            return '\n'.join(comps)

        def format_mats(mats):
            # TODO molecular weight?
            hs = 'name', 'sku', 'vendor name', 'chemical name', 'cas number', 'rrid', 'url'
            table = '\n| ' + ' | '.join(hs) + '\n|-'
            for m in mats:
                vs = (m['name'], m['sku'], m['vendor']['name'],
                      m['linfor'],  # FIXME is this really chemical name?
                      m['cas_number'], m['rrid'], m['url'])
                row = [v.strip() if isinstance(v, str) else '' for v in vs]
                table += '\n| ' + ' | '.join(row)

            return table

            #return ('\n#+begin_src json\n' +
                    #json.dumps(mats, indent=2) +
                    #'\n#+end_src')
            #for mat in mats:

        import htmlfn as hfn
        data = self.data()
        # FIXME may encounter anchoring issuse if we do this
        # will likely need to adjust accordingly
        lrc = f'<link rel="canonical" href="{self.uri_api_int.asStr()}">'
        doi = self.doi
        if doi:
            metas = (
                dict(name='dc.identifier', content=doi.asStr()),
                dict(name='DOI', content=doi.asStr()),
                    )
        else:
            metas = tuple()

        metas += (
            dict(name='og.url', content=self.uri_human.asStr()),
        )

        helper = [s for s in data['steps'] # debug
                  if [c for c in s['components'] if c['type_id'] in (24, 4, 3)]]

        _war = data['warning']
        _waf = convert(BeautifulSoup(_war, 'html5lib'), '').strip() if _war else ''
        warnings = ('\n* Warnings\n' + _waf if _waf else '')

        _gls = data['guidelines']
        _glf = convert(BeautifulSoup(_gls, 'html5lib'), '').strip() if _gls else ''
        guidelines = ('\n* Guidelines\n' + _glf if _glf else '')

        _mat = data['materials']
        # TODO add additional materials accumulated from inline content
        # no idea why pio doesn't do that automatically itself ...
        materials = ('\n* Materials\n' + format_mats(_mat).strip()
                     if _mat else '')

        body = (
            f'\n\n[[{self.uri_human.asStr()}][Original on protocols.io]]\n' +
            # guidelines warnings materials metadata
            warnings +
            guidelines +
            materials +
            '\n* Steps\n' +
            '\n'.join(format_step(s, i + 1) for i, s in enumerate(data['steps'])))

        title = data['title']

        options = (
            '\n#+options: ^:nil'
            '\n'
        )

        # TODO probably want a span macro
        macros = (
            '\n#+macro: empty-link *ERROR-UPSTREAM* '
            '\n#+macro: rrid =$1 ($2)='
            '\n#+macro: reagent_skurl =$1 ($2)= @@comment: $3@@'
            '\n#+macro: reagent_sku =$1 ($2)='
            '\n#+macro: reagent_url =$1= @@comment: $2@@'
            '\n#+macro: reagentv =$1 ($2)='
            '\n#+macro: reagent =$1='
            '\n#+macro: software [[$3][$1]] @@comment: $2@@'
            '\n'
        )

        doc = (
            f'#+title: {title}\n' +
            options +
            macros +
            '#+html_head: <style>img { float: center; width: 50%; }</style>\n'
            f'#+html_head: {lrc}\n' +
            '\n'.join(['#+html_head: ' + hfn.metatag(**md) for md in metas]) +
            body)

        return ct(doc)

        #return hfn.htmldoc(body,
                           #title=data['title'],
                           #other=(lrc,),
                           #metas=metas,
                           #styles=tuple(),)

    @staticmethod
    def _get_user_jwt(resp):
        """ an aweful way to get this that surely will break """
        text = resp.text
        before, after = text.split('USER_JWT')
        eq, user_jwt, rest = after.split('"', 2)
        return user_jwt

    @cache(auth.get_path('cache-path') / 'protocol_json', create=True, return_path=True)
    def _get_data(self, apiuri):
        """ use apiuri as the identifier since it is distinct
            from other views of the protocol e.g. uri_human etc. """

        if hasattr(self, '_hack_hash_value') and self._hack_hash_value is not None:
            # make it possible to cache an arbitrary value without
            # actually retrieving it
            v = self._hack_hash_value
            self._hack_hash_value = None
            return v

        # TODO progenitors
        log.debug('going to network for protocols')
        if self._pio_header is None and isinstance(self, Pio):
            # the hacks in this branch only apply to the Pio class
            # otherwise always use apiuri in the other branch
            if self.identifier.is_private():
                resp = self._get_direct(apiuri)#, cache=False)
            else:
                if self.identifier == self.identifier.uri_api_int:
                    try:
                        prog = self.progenitor(type='id-converted-from')
                        # FIXME pretty sure this should return None instead of error?
                    except KeyError as e:
                        msg = 'no protocols io api credentials'
                        raise exc.NotAuthorizedError(msg) from e

                    slug = prog.slug
                else:
                    slug = self.slug

                hack = self._id_class(
                    prefix='pio.view',
                    suffix=slug).asStr() + '.json'
                resp = self._requests.get(hack)
        else:
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
            except Exception as e:
                sc = resp.status_code
                em = resp.reason

            msg = (f'protocol issue {self.identifier} {resp.url} '
                   f'{resp.status_code} {sc} {em}')
            self._failure_message = msg  # FIXME HACK use progenitor instead
            return {COOLDOWN: msg,
                    'http_status_code': resp.status_code,
                    'pio_status_code': sc,
                    'error_message': em,}

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
    def label_safe(self):
        """don't fail if data access is missing """
        try:
            return self.label
        except exc.RemoteError:
            return self.identifier.slug

    @property
    def creator(self):
        username = self.data()['creator']['username']
        if username is not None:
            return PioUser('pio.user:' + username)

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
        """ XXX this should NEVER allow an error to escape.
            Only return less information. """
        if self.identifier.is_int():
            out = super().asDict(include_description)

            try:
                out['uri_human'] = self.uri_human.identifier  # prevent double embedding
            except exc.RemoteError as e:
                pass

            if hasattr(self, '_data_in_error') and self._data_in_error:
                return out

            # NOTE if you started from a doi then it seems extremely unlikely
            # that you would be in a sitution where data retrieval could fail
            # which means that really only the uri_human case can fail and
            # there still be a chance that there is a uri_human we can use
            doi = self.doi
            if doi is not None:
                out['doi'] = doi
            return out
        else:
            try:
                uri_api_int = self.uri_api_int
                if uri_api_int is None:
                    # This should trigger a remote error, if not, we want to
                    # know because something very strange is going on
                    self.data()

                out = uri_api_int.asDict(include_description)
                if include_private and self.identifier.is_private():
                    out['uri_private'] = self.identifier  # FIXME some way to avoid leaking these if needed?
                return out
            except exc.RemoteError as e:
                # we don't have any metadata but we will return what little info we have
                return super().asDict(include_description)

    def _triples_gen(self,
                     rdflib=None,
                     rdf=None,
                     rdfs=None,
                     owl=None,
                     NIFRID=None,
                     TEMP=None,
                     **kwargs):

        s = self.asType(rdflib.URIRef)

        yield s, rdf.type, owl.NamedIndividual

        if self.uri_human:
            # XXX dereference checks should not be run here, they
            # should be conduceded centrally during
            yield s, TEMP.hasUriHuman, self.uri_human.asType(rdflib.URIRef)

        if self.label:
            yield s, rdfs.label, rdflib.Literal(self.label)

        doi = self.doi
        if doi is not None:
            yield s, TEMP.hasDoi, doi.asType(rdflib.URIRef)


class _PioUserPrefixes(conv.QnameAsLocalHelper, oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


_PioUserPrefixes({'pio.user': 'https://www.protocols.io/researchers/',
                  'pio.api.user': 'https://www.protocols.io/api/v3/researchers/',
                  'pio.api1.user': 'https://www.protocols.io/api/v1/researchers/',
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

    @property
    def uri_api1(self):
        return self.__class__(prefix='pio.api1.user', suffix=self.suffix)


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

    @property
    def uri_api1(self):
        return self.__class__(self.identifier.uri_api1)

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
        return self.uri_api1.asUri() + '?with_extras=1'

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

        _old_prog = self._progenitors
        self._progenitors = {}
        for k in ('id-converted-from',): # TODO generalize to persistent progs
            if k in _old_prog:
                self._progenitors[k] = _old_prog[k]

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

        try:
            return oq.OntId(something)
            return OntTerm(something)  # use the better local version of OntTerm
        except oq.OntId.Error as e:
            raise exc.MalformedIdentifierError(something) from e

