

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

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def exists(self):
        raise NotImplementedError

    def metadata(self):
        raise NotImplementedError

    def data(self):
        raise NotImplementedError


# IETF


class Urn(Identifier):
    """ """


class Iri(Identifier):
    """ """


class Uri(Iri):
    """ """

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


class Handle(Identifier):
    """ """


# ISO


class DOI(Uri, Handle):
    """ """


# NAAN


class ARK(Identifier):
    """ """


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


