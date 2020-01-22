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


class Identifier(str):  # TODO decide if str should be base ...
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

    @staticmethod
    def normalize(identifier):
        raise NotImplementedError
        return identifier

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def exists(self):
        raise NotImplementedError

    def metadata(self):
        raise NotImplementedError

    def data(self):
        raise NotImplementedError

    def asLocal(self, conventions=None):
        if conventions is None:
            conventions = self._local_conventions

        return conventions(self)


# IETF


class Urn(Identifier):
    """ """
    _family = families.IETF


class Iri(Identifier):
    """ """
    _family = families.IETF


class Uri(Iri):
    """ """
    _family = families.IETF

    # FIXME code duplication

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


class CompactifiedTemplate(Uri):
    _local_conventions = LocalConventions()
    # maybe simpler to implement as a
    # lifting rule over local conventions
    # which raises them to have a global status
    # when parsing strings?
    def __new__(cls, local_or_global):
        # if short make long
        # if long make short etc.
        # probably take from ontquery
        local = local_or_global  # TODO
        global_ = local_or_global  # TODO
        self = super().__new__(cls, global_)
        self.local = local
        # FIXME this is all shorthand that should be rewritten


class Url(Uri):  # FIXME probably just remove this ...
    """ """
    _family = families.IETF


# NAAN


class Ark(Identifier):
    """ """
    _family = families.NAAN


# Other


class ISNI(Uri):
    """ """


class ORCID(Uri):  # TODO Uri or hasUriRepresentation ?
    """ """
    # wiki has claims that Orcids are Isnis
    # but I would need more information ...


class Ror(Uri):
    """ """


class RRID(Identifier):
    """ """


