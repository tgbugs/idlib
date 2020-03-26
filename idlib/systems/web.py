import ontquery as oq  # temp
import idlib
from idlib import families


class Iri(oq.OntId, idlib.Identifier):  # FIXME OntId is only temporary
    """ """
    _family = families.IETF


class Uri(Iri):
    """ """
    _family = families.IETF

    # FIXME code duplication

    # canonicalize the uri


class CompactifiedTemplate(Uri):
    _local_conventions = idlib.ConventionsLocal()
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


