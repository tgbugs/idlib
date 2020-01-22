class Stream:

    @property
    def identifier(self):
        """ Implicitly the unbound identifier that is to be dereferenced. """
        # FIXME interlex naming conventions call this a reference_name
        # in order to give it a bit more lexical distance from identity
        # which implies some hash function
        raise NotImplementedError

    @identifier.setter
    def identifier(self, value):
        raise NotImplementedError  # probably should never allow this ...

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

    @property
    def identifier_bound(self):
        raise NotImplementedError
        return self.metadata.identifier_bound

    @property
    def identifier_version(self):
        """ implicitly identifier_bound_version """
        raise NotImplementedError
        return self.metadata.identifier_version


