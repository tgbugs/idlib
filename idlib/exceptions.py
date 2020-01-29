

class IdlibError(Exception):
    """ base class for idlib errors """


class ResolutionError(Exception):
    """ something went wrong """


class MalformedIdentifierError(IdlibError):
    """ Your input cannot be determined to be of the
        type of the identifier you want, therefor we will
        NOT create an object of that type, it cannot exist. """


class IdentifierDoesNotDereferenceToDataError(IdlibError):
    """ Signal that the identifier in question does not
    dereference to data. Examples are physical sample ids,
    or cooluris, ontology class identifiers, etc.

    the ontology class ids are a bit tricky since they do
    dereference, but they do so via a 303, and their dereferenced
    metadata can itself have metadata and data substreams, however
    that should be implemented in the metadata class as we do with
    the ontology resources """
