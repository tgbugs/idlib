import idlib


class PmidId(idlib.Identifier, idlib.Stream):
    canonical_regex = '^PMID:[0-9]+'


class Pmid(idlib.Stream):
    """ PubMed identifier. """

    _id_class = PmidId
