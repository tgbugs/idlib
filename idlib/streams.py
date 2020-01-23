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

import requests
import idlib
from idlib import exceptions as exc
from idlib.utils import cache_result, resolution_chain_responses, StringProgenitor


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

    def __init__(self, identifier_or_id_as_string=None, *args, **kwargs):
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

                self._identifier = self._id_class(identifier_or_id_as_string)

    def asType(self, _class):
        # FIXME not quite ... but close
        return _class(self.identifier)

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
        raise NotImplementedError("You probably meant to set self._identifier?")  # probably should never allow this ...

    def checksum(self, cypher=None):  # FIXME default cypher value
        if not hasattr(self, '__checksum'):  # NOTE can set __checksum on the fly
            self.__checksum = self._checksum(cypher)

        return self.__checksum

    identity = checksum  # FIXME the naming here is mathematically incorrect

    def _checksum(self, cypher):
        raise NotImplementedError

    @property
    def progenitor(self):
        """ the lower level stream from which this one is derived """
        # could also, confusingly be called a superstream, but
        # the superstream might have a less differentiated, or simply
        # a different type or structure (e.g. an IP packet -> a byte stream)

        # unfortunately the idea of a tributary, or a stream bed
        # breaks down, though in a pure bytes representation
        # technically the transport headers do come first
        raise NotImplementedError

    superstream = progenitor

    def dereference_chain(self):
        raise NotImplementedError

    def dereference(self, asType=None):
        """ Many identifier systems have native dereferincing semantics """
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
        raise exc.IdentifierDoesDereferenceToDataError(self)

    @property
    def id_bound_data(self):
        raise exc.IdentifierDoesDereferenceToDataError(self)

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

    @cache_result
    def dereference_chain(self):
        # FIXME this is really dereference chain super
        return tuple(StringProgenitor(resp.url, progenitor=resp)
                     for resp in
                     resolution_chain_responses(self.identifier,
                                                raise_on_final=False))

    @cache_result
    def dereference(self, asType=None):
        drc = self.dereference_chain()
        uri = drc[-1]
        if asType:
            return asType(uri)
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

    def progenitor(self):
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
        return uri.progenitor.headers

    def data(self, mimetype_accept=None):
        # FIXME TODO should the data associated with the doi
        # be the metadata about the object or the object itself?
        # from a practical standpoint derefercing the doi is
        # required before you can content negotiate on the
        # actual document itself, which is a practical necessity
        # if somewhat confusing
        self._resp_data = requests.get(self.identifier)  # FIXME TODO
        return self._resp_data.content
