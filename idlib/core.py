import idlib

# families (mostly a curiosity)
class families:
    IETF = object()
    ISO = object()
    NAAN = object()


# local conventions


class LocalConventions:
    """ Base class for all types of local conventions.
        for identifiers local conventions usually convert
        a local identifer into a globally unique identifier
        by providing some additional context.

        Beyond their use for globalizing local identifiers,
        local conventions are information that an be specified
        dynamically, as part of a single stream and that is
        requried in order to correctly interpret information
        that was originally encoded according to those local
        conventions.  """


class Curies(LocalConventions):
    """ """


class QNames(LocalConventions):
    """ """


# identifiers


class Identifier(str, idlib.Stream):  # TODO decide if str should be base ...
    """ Base class for all Identifiers """
    # all identifiers mapped to idlib should have a string representation
    # or be representable as strings in as unambiguous a way as possible
    # this means that distinctions based on types e.g. MyId('1') and YourId('1')
    # need stringify in such a way that they do not colide e.g. myid:1 yourid:1
    # within the expected context of their expansion
    # local:?:myid:1 local:?:yourid:1 could represent the space of local identifiers
    # with unknown local conventions, maintaining a record of all local conventions
    # seems likely to be a giant pain, so local:?: ids would be ephemoral and would
    # probably have to be marked with a source as a kind of best guess maximal domain
    # for assuming similarity, though in some documents every instance of a local:?:id
    # should probably be assumed to be different under expansion

    # as a result of this, it is still not entirely clear whether
    # str is quite the right option, but since normalization can
    # occur before stringification, it is probably ok ...
    # e.g. hello:world -> local:?:hello:world in cases where
    # a local identifier is used without conventions
    # same with local:?:1, local:?:2, local:?:3, local:?:4

    _id_class = str
    #@staticmethod
    #def normalize(identifier):
        #raise NotImplementedError
        #return identifier

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    #def exists(self):
        # bad identifiers are not allowed to finish __init__
        #raise NotImplementedError

    def metadata(self):
        raise NotImplementedError

    def data(self):
        raise NotImplementedError

    def asLocal(self, conventions=None):
        if conventions is None:
            conventions = self._local_conventions

        return conventions(self)


# Other


'''
class ISNI(idlib.Uri):
    """ """


class ORCID(idlib.Uri):  # TODO Uri or hasUriRepresentation ?
    """ """
    # wiki has claims that Orcids are Isnis
    # but I would need more information ...




'''
