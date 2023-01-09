"""While the name of the class is Stream, the reality is much closer
to "a random block of data/code that may or may not be executable" in
the current runtime. The implication is mostly that it is possible to
serialize, save-lisp-and-die, etc. something and, given the right
receiving environment, recover it back to some Turing agentous state
if you so choose. Thus, in Python, Stream is just a regular old object
with a few restrictions on its structre.

Another reason why Stream is used as the name is because most of the
objects that are dereferenced to by persistent identifiers are readonly,
are only writeable by a select few people, or therwise change with a time
constant that is significantly longer than life cycle of code that consumes
them.
"""
# NOTE: at the moment, the implementaiton here is not fully homogenous.
# It is possible for methods to produce something other than another stream.
# pyontutils.core.OntRes is what we are shooting for, where an identifier
# identifies multiple streams collectively, they are most distingiushed by
# the particular type of substream, (e.g. metadata-free, data-homogenous)

from types import MappingProxyType
import idlib
from idlib import exceptions as exc
from idlib.utils import cache_result, StringProgenitor, log


# TODO it seems like there is a little dance going on between identifiers and local names
# and between identifiers and the actionable form
# local name < local conventions > canonical globally unique identifier < ??? > actionable form
# of course that global uniquesness is patently false, it is always global within some
# set of axioms, i.e. set of string translation rules

# Practically this suggests that it might be possible to set the 'action convetions'
# for identifiers in a way similar to the local conventions, maybe a set of sane
# defaults plus a 'get actionable form' or something?


class Stream:

    _id_class = None

    _progenitors = MappingProxyType({})  # this is a dict, but immutable to prevent accidents

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    _renew = __new__

    def __new__(cls, *args, **kwargs):
        Stream._setup(*args, **kwargs)
        Stream.__new__ = Stream._renew
        return super().__new__(cls)

    @staticmethod
    def _setup(*args, **kwargs):
        import requests  # resolver dejoure
        Stream._requests = requests

        from idlib.core import resolution_chain_responses
        Stream._resolution_chain_responses = staticmethod(resolution_chain_responses)

    @classmethod
    def fromJson(cls, blob):
        # TODO validation ...
        identifier = blob['id']
        if isinstance(identifier, cls):
            return identifier
        else:
            i = cls(identifier)
            i._progenitors = {}  # FIXME klobbered in self.data
            # TODO what is our term for the atomic part of a
            # stream into which no light may pass? it is different
            # than the homogenous data, it is more along the lines
            # of "this is some other data structure"
            i._progenitors['blob'] = blob
            return i

    @classmethod
    def fromIdInit(cls, *args, **kwargs):
        return cls(cls._id_class(*args, **kwargs))

    def __init__(self, identifier_or_id_as_string=None, *args, **kwargs):
        # FIXME or identifier, string, or another stream
        if isinstance(self, idlib.Identifier):
            # stream should always come last in the mro so it will hit object
            super().__init__() #identifier_or_id_as_string, *args, **kwargs)
            self._identifier = self._id_class(self)

        else:
            if isinstance(identifier_or_id_as_string, self._id_class):
                self._identifier = identifier_or_id_as_string
            else:
                if self._id_class == str and identifier_or_id_as_string is None:
                    # have to protect string identifiers because they can't type
                    # check their own inputs
                    raise TypeError('identifier_or_id_as_string may not be None')

                if isinstance(identifier_or_id_as_string, Stream):  # FIXME not quite right
                    self._identifier = identifier_or_id_as_string.identifier
                else:
                    self._identifier = self._id_class(identifier_or_id_as_string)

    @property
    def label(self):
        raise NotImplementedError('impl in subclass')

    @property
    def label_safe(self):
        try:
            return self.label
        except exc.RemoteError:
            return self.asStr()

    def asType(self, _class):
        # FIXME not quite ... but close
        if hasattr(self, '_id_class'):
            if self._id_class == str:
                return _class(self.identifier)
            else:
                return self.identifier.asType(_class)
        else:
            return _class(self.identifier)

    def asCell(self, sep='|'):
        """ As a cell in a table. """
        # TODO Distinct from asTabular in that asTabular is probably a row?
        if hasattr(self, '_id_class') and self._id_class:
            if self._id_class == str:
                local = self.identifier
            else:
                local = self.identifier.asLocal()
            try:
                if not self.label:
                    return local
            except (exc.ResolutionError, exc.RemoteError) as e:
                log.exception(e)
                return local
            except NotImplementedError as e:  # idlib.Identifier case
                log.error(f'self.label not implemented for {self.__class__}')
                log.exception(e)
                return local

            return self.label + sep + local

        else:
            # FIXME this needs some extension mechanism ...
            raise NotImplementedError('TODO as needed')

    def asDict(self, include_description=False):
        """ XXX this should NEVER allow an error to escape.
            Only return less information. """
        if hasattr(self, '_id_class') and self._id_class:
            out = {
                'type': 'identifier',
                'system': self.__class__.__name__,
                #'id': self.identifier,
                'id': self,  # XXX NOTE THE TRADEOFF HERE, this preserves stream access
                # 'alternate_identifiers': [],  # TODO
            }

            try:
                metadata = self.metadata()
            except exc.RemoteError as e:
                out['errors'] = [{'message': str(e)}]
                return out

            if metadata is not None:
                out['label'] = self.label
                if hasattr(self, 'category') and self.category:
                    out['category'] = self.category

                if hasattr(self, 'synonyms') and self.synonyms:
                    out['synonyms'] = self.synonyms

                if include_description and hasattr(self, 'description') and self.description:
                    out['description'] = self.description

            else:
                out['errors'] = [{'message': 'No metadata found.'}]

        # TODO other stream types e.g. pathlib.Path ... sigh CL MOP would be so useful here
        else:
            out = {'type': 'stream',
                   'system': self.__class__.__name__,  # FIXME key name ...
                   'id': self.identifier,}

        return out

    def __contains__(self, value):
        return value in self.identifier

    @property
    def identifier(self):
        """ Implicitly the unbound identifier that is to be dereferenced. """
        # FIXME interlex naming conventions call this a reference_name
        # in order to give it a bit more lexical distance from identity
        # which implies some hash function
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        raise NotImplementedError('You probably meant to set self._identifier?')  # probably should never allow this ...

    def asStr(self):
        """ Return the idlib string representation of the identifier """
        # FIXME we probably need a safe version of this that
        # errors if the identifier/stream is a local identifier
        if hasattr(self, '_id_class') and self._id_class is str:
            return self.identifier
        #elif not hasattr(self, '_id_class'):  # will probably need this
        else:
            return self.identifier.asStr()

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.identifier == other.identifier

    def __hash__(self):
        """ The hash here identifies the NAME of the stream
            NOT the STATE of the stream. Two streams have the
            same hash if they have the same identifier. If you
            want to know if there are two equal streams that
            are different objects use self `is' other instead. """
        return hash((self.__class__, self.asStr()))

    @property
    def identifier_actionable(self):
        """ The 'resolvable' or actionable form of an identifier
            where actionable is defined by specification of the system
            NOT of the current context in which an identifier is being used """

        # in URI based systems this will just be the identifier
        # decoupling this important for allowing identifiers to
        # have canonical regex that are resolver independent

        # TODO identifier_actionable_resolver(self, resolver) or similar
        raise NotImplementedError('Implement in subclass')

    def checksum(self, cypher=None):  # FIXME default cypher value
        if not hasattr(self, '__checksum'):  # NOTE can set __checksum on the fly
            self.__checksum = self._checksum(cypher)

        return self.__checksum

    identity = checksum  # FIXME the naming here is mathematically incorrect

    def _checksum(self, cypher):
        raise NotImplementedError

    def progenitor(self, *args, level=1, type=None, _type=type):
        """ return the reproductible progenitor object/stream at level n
            also includes progenitors that are not reproducible but that
            retain metadata about the substream in question, e.g a requests
            response object has information about the superstream for a
            text stream

            generators and filelike objects should not be included in
            the progenitor list since they do not represent stateless
            progenitors (i.e. a generator can only be expressed once)

            note that sometimes this may include a tuple if the information
            needed has more than one part, no conventions for this have
            been decided yet

            level == 0 -> returns self to break"""

        if args:
            raise TypeError('progenitor accepts keywords arguments only!')

        # FIXME probably makes more sense to store progenitors in a dict
        # with a controlled set of types than just by accident of ordering
        # this would allow us to keep everything along the way
        # of course watch out for garbage collection issues ala lxml etree

        # XXX NOTE: self._progenitors = [] should be set EVERY time data is retrieved
        # it should NOT be set during __init__
        # if not hasattr(self, '_progenitors'):  # TODO

        # TODO instrumenting all the other objects with
        # a progenitor method is going to be a big sigh
        if type is not None:
            return self._progenitors[type]  # FIXME need enum or something

        if level is not None and level == 0:
            return self
        else:
            if level < 0:
                level += 1  # compensate for reversed

            # HACK to retain a stack of progenitors manually for now
            # FIXME blased insertion order :/ implemnation details
            return list(self._progenitors.values())[-level]

    # superstream = progenitor  # it would be level=1 but not as useful as we would like

    def dereference_chain(self):
        raise NotImplementedError

    def dereference(self, asType=None):
        """ Many identifier systems have native dereferincing semantics

            This particular dereferencing refers ONLY to the dereferencing
            of one identifier into another identifier stream, NOT the contents
            of that stream. This is the "default" dereferencing behavior of the
            _system_ NOT of the identifier. """

        # FIXME pretty sure that the behavior of the
        # dereferencing here is inconsistent and incorrect
        # many systems cannot dereference to their referent

        # as defined this is mostly used in the context
        # of dereferncing DNS/url resolution chains
        # which is useful but mostly an implementation detail

        # having explicit classes for substreams may help here
        # by making it possible to dereference the identifier,
        # the metadata stream, the data stream, etc. independenly
        raise NotImplementedError

    def headers(self):
        """ Data from the lower level stream from which this stream is
            derived/differentiated """
        # FIXME naming ...
        # sometimes this is related to ...
        #  transport
        #  prior in time
        #  unbound metadata, or metadata that will be unbound in the target
        #  metadata kept by the stream management layer (e.g. file system)
        #  stream type
        #  stream size
        #  operational metadata
        #  summary information

        # if you are sending a file then populate all the info
        # needed by the server to set up the stream (even if that seems a bit low level)
        raise NotImplementedError
        return self.superstream.metadata

    #@headers.setter
    #def headers(self, value):
        #self._headers = value
        #raise NotImplementedError('If you override self.headers in the child '
                                  #'you need to reimplement this too.')

    def data(self, mimetype_accept=None):
        """ The primary opaque datastream that will be differentiated
            at the next level. Identifiers for classes and pysical samples
            should return None or error on these. """
        raise NotImplementedError

    def metadata(self, mimetype_accept=None):
        """ stream metadata, hopefully as a header

            technically this should be called metadata_bound
            since it is part of the same stream, it might
            make sense to invert this to have a variety of
            datasources external to a stream that contain
            additional relevant data using that id
        """
        if not hasattr(self, '_metadata'):
            self._metadata = self._metadata_class(self.identifier)

        return self._metadata

    # TODO warn about deprecation for pyontutils

    @property
    def identifier_bound(self):
        raise NotImplementedError
        return self.metadata.identifier_bound

    @property
    def identifier_version(self):
        """ implicitly identifier_bound_version """
        raise NotImplementedError
        return self.metadata.identifier_version


### see docs for the trasition grammer


class MetadataFree(Stream):
    # NOT the primary referent of the identifier type in question
    pass


class DataFree(Stream):  # aka DataHeterogeneous
    # the primary referent of the identifier type in question
    pass


class MetadataBound(Stream):
    pass


class DataHomogenous(Stream):
    pass


class HelperNoData:  # FIXME should be
    def data(self):
        raise exc.IdentifierDoesNotDereferenceToDataError(self)

    @property
    def id_bound_data(self):
        raise exc.IdentifierDoesNotDereferenceToDataError(self)

    @property
    def _prgn_metadata(self):
        if hasattr(self, '_resp_metadata'):
            return self._resp_metadata
        elif hasattr(self, '_path_metadata'):
            return self._path_metadata
        else:
            raise AttributeError('no progenitor for metadata')

    def progenitor(self):
        metadata = self.metadata()
        # metadata.progenitor  # FIXME really prefer this ...
        return self.dereference_chain(), self._prgn_metadata  # FIXME assumptions about uri ...


class HelpTestStreams:
    stream = None
    ids = tuple()
    ids_bad = tuple()

    @staticmethod
    def setUpClass():
        if not hasattr(HelpTestStreams, '_requests'):
            import pytest
            HelpTestStreams._pytest = pytest
            import requests
            HelpTestStreams._requests = requests
            import hashlib
            HelpTestStreams._hashlib = hashlib
            import copy
            HelpTestStreams._copy = copy
            import pickle
            HelpTestStreams._pickle = pickle
            from joblib import Parallel, delayed
            HelpTestStreams._Parallel = Parallel
            HelpTestStreams._delayed = delayed

    @classmethod
    def _lol_joblib(cls, d):
        """ HEY KIDS WATCH THIS """
        cls._Parallel(n_jobs=2)(cls._delayed(lambda d: d)(d) for d in (d,))

    def test_stream_sections(self):
        # TODO run each on of the properties/methods in
        # a separate loop?
        cypher = self._hashlib.blake2b
        bads = []
        for i in self.ids:
            d = self.stream(i)
            d.identifier
            if d.identifier and hasattr(d.identifier, 'prefix'):
                print(d.identifier)
                print(d.identifier.prefix)
                print(d.identifier.suffix)
                if d.identifier.prefix is None or d.identifier.suffix is None:
                    bads.append(d.identifier.__dict__)

            try:
                d.identifier_bound_metadata
                d.identifier_bound_version_metadata

                d.checksum(cypher)  # data or metadata? indication that there should be multiple probably
                d.dereference()  # XXX induces infinite recursion
                d.headers()
                d.metadata()

                if not isinstance(d, HelperNoData):
                    d.data()

                d.progenitor()  # or is it d.data.progenitor?

                # test pickling
                hrm = self._pickle.dumps(d)
                tv = self._pickle.loads(hrm)
                if tv.checksum(cypher) != d.checksum(cypher):
                    bads.append((tv, d))

                # test copying
                tv = self._copy.deepcopy(d)
                if tv.checksum(cypher) != d.checksum(cypher):
                    bads.append((tv, d))

            except self._requests.exceptions.ConnectionError as e:
                self._pytest.skip('Internet done goofed')

            # test joblib
            self._lol_joblib(d)

        assert not bads, bads

    def test_malformed(self):
        bads = []
        for i in self.ids_bad:
            try:
                d = self.stream(i)
                d.data()
                bads.append(d)
            except Exception as e:
                log.exception(e)
                pass

        assert not bads, bads

    def test_hash_eq_id(self):
        hrm = self.ids[0]
        i1 = self.stream(hrm)
        i2 = self.stream(hrm)

        # what did we decide about how to handle this?
        # stream is the same but the state might be different?
        # what are the design tradeoffs here? it means that the
        # stream cannot be used as a dictionary key, which is
        # extremely annoying, but would still have A is B => False

        # we decided (as of now) that all streams hash to their
        # class plus the string representation of their identifier
        # and that equality compares class and identifier equality

        # hash testing
        assert len({i1, i2}) == 1
        assert len({i1.identifier, i2.identifier}) == 1

        assert len({i1, i1.identifier}) == 2
        assert len({i1, i2.identifier}) == 2
        assert len({i1.identifier, i2}) == 2

        # equality testing
        assert i1 == i2
        assert i1.identifier == i2.identifier

        assert i1 != i1.identifier
        assert i1 != i2.identifier
        assert i1.identifier != i2

        # python object identity testing (confusingly)
        assert i1 is not i2
        assert i1.identifier is not i2.identifier

        assert i1 is not i1.identifier
        assert i1 is not i2.identifier
        assert i1.identifier is not i2

    def test_asDict(self):
        for id in self.ids:
            s = self.stream(id)
            try:
                d = s.asDict()
            except self._requests.exceptions.ConnectionError as e:
                self._pytest.skip('Internet done goofed')


class StreamUri(Stream):
    """ Implementation of basic methods for URI streams.

    Probably don't inherit from this class, just reassign them directly
    to any class those primary implementaiton uses uris.
    There are a couple of different ways to do this ...

    Of course then we can't use super() to provide additional information, sigh.
    """

    # TODO consider whether it makes more sense to invert this so that
    # actionable forms simply ask identifiers for their representation
    # in that form ... re: the little dance of asUri -> asUrl
    # asIdentifiersDotOrg, asN2T, asInterpretedByResolverX etc.

    _id_class = None  # NOTE asssigned to idlib.Uri in idlib.__init__


    @property
    def identifier(self):
        return self._identifier

    @property
    def identifier_actionable(self):
        return self.asUri()

    @property  # FIXME pretty sure this shouldn't be properties due to the accept_mimetypes ...
    def id_bound_metadata(self):
        # FIXME this can be id_bound_metadata_free or id_bound_metadata_bound
        # depending on the returned mime type
        # TODO check in on pyontutils.core.OntMetaIri
        raise NotImplementedError
        return self.metadata_free.identifier  # implicitly free?
        return self.data_free.metadata_bound.identifier

    identifier_bound_metadata = id_bound_metadata

    def id_bound_data(self):
        raise NotImplementedError

    _dereference_cache = {}  # FIXME real caching please lru here probably?
    @cache_result  # this is only per instance not globally
    def dereference_chain(self):
        # FIXME this is really dereference chain super
        dc = StreamUri._dereference_cache
        if not self.identifier_actionable in dc:
            try:
                dc[self.identifier_actionable] = tuple(
                    StringProgenitor(resp.url, progenitor=resp)
                    for resp in
                    self._resolution_chain_responses(self.identifier_actionable,
                                                     raise_on_final=False))
            except (exc.ResolutionError, exc.RemoteError) as e:
                # TODO
                # FIXME partial resolution is a complete nightmare
                # to handle >_< ... I don't want to include null
                # pointers here, but we can't just throw an error
                # for a partially resolved chain, I thinkwe have
                # raise with the partial chain as a value in the
                # error
                raise e

        return dc[self.identifier_actionable]

    @cache_result
    def dereference(self, asType=None):
        drc = self.dereference_chain()
        uri = drc[-1]
        if asType:
            nid = asType(uri)
            if isinstance(nid, idlib.Stream):
                if not isinstance(nid._progenitors, dict):
                    # FIXME is are these really progenitors in the way we usually
                    # think of them? ... maybe not?
                    nid._progenitors = {}

                # FIXME TODO do we want/need the full chain here?
                nid._progenitors['id-dereferenced-from'] = self
                # FIXME temporary bridge from StringProgenitor
                nid._progenitors['stream-http'] = uri._progenitor

            return nid
        else:
            # just return the strprg if no type is set
            # don't assume dereferencing is type preserving
            # if we wanted to be really strict about types then we would force
            # explicit conversion to a actionable form and then dereference
            # i.e. ident.actionable().dereference() but that is a pain since
            # the original stream object looses its connection, and the identifier
            # type itself needs to know how to make itself actionable, which it
            # can't quite do in a complete way, in a minimal way probably
            return uri

    def __old_progenitor(self):
        # FIXME there is no single progeneitor here ?
        # or rather, the stream is broken up into objects
        # long before we can do anything about it

        # also metadata headers and data headers are separate
        # possibly even more separate than desired, but of course
        # these aren't single streams, they are bundles of streams
        # so tuple ?
        #self.dereference()
        self.metadata()
        self.data()
        return self.dereference_chain(), self._resp_metadata, self._resp_data

    @cache_result
    def headers(self):
        uri = self.dereference()
        return uri.progenitor().headers

    def data(self, mimetype_accept=None):
        # FIXME TODO should the data associated with the doi
        # be the metadata about the object or the object itself?
        # from a practical standpoint derefercing the doi is
        # required before you can content negotiate on the
        # actual document itself, which is a practical necessity
        # if somewhat confusing
        self._progenitors = {}
        resp = self._requests.get(self.identifier)  # FIXME TODO explicit dereference
        self._progenitors['stream-http'] = resp
        return resp.content

    def asUri(self, asType=None):
        # FIXME this should probably be abstracted to asActionable
        # where actionability is defined by some resolver class
        # defaulting to the system specified default resolver
        # e.g. for doi, orcid, ror, etc. at the moment that is
        # the DNS system for resolving urls
        raise NotImplementedError('implement in subclass')
