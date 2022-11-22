

class IdlibError(Exception):
    """ base class for idlib errors """


class LocalError(IdlibError):
    """ Something went wrong locally and we can do something about it. """


class ConfigurationError(LocalError):
    """ Something went wrong with local configuration. """


class CouldNotReachError(IdlibError):
    """ Could not reach a remote. """
    # FIXME vs UnreachableError, unreachable seems like
    # a more permanent condition

    # consider Aristotle's Comedics
    # permanently unreachable barring another miraculous find of a
    # cache of parchments in a basement
    # that is a no-longer-exists or used-to-exist error
    # where it is in the index but we ...


class CouldNotReachIndexError(CouldNotReachError):
    """ Failure on the way to remote index. """


class CouldNotReachReferentError(CouldNotReachError):
    """ Failure on the way to remote referent.

        This happens after reaching the index and
        the index returns a positive result.

        Note that in a system that is not based on redirects
        this is an error that could be returned by the index
        but it would appear as an referent unknown error. """

    # but its supertype is ReferentUnknown or ReferentUnreachable


class NullReferentError(IdlibError):
    """ You reach some system that gives a difinitive does not
        exist error for a referent that the index says exists.

        This is more or less your friendly null pointer error
        with slightly fewer nasal demons. """


class InbetweenError(IdlibError):
    """ We couldn't get to the remote for some reason. """


class ResolutionError(IdlibError):
    """ something went wrong """
    # FIXME this will be confusing and I'm fairly certain that
    # we should split into NetworkError/TimeoutError
    # and then have RemoteError, because Resolution error is
    # ambiguous, it is the superclass for all of them I think


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
    # 303 see other


class RemoteError(IdlibError):
    """ idlib normalized classes for remote errors """


class ExistenceUnknownError(RemoteError):
    """ For whatever reason the remote cannot provide an
        answer right now. """
    # this abstracts away a whole bunch of implementation details
    # that the user really doesn't need to know about other than
    # maybe check back later


class IdDoesNotExistError(RemoteError):
    """ A record corresponding to the requested identifier does
        not exist on the remote system right now. """
    # 404 not found

class UsedToExistError(RemoteError):
    """ A record corresponding to the requested identifier used
        to exist and will probably never exist again in the future. """
    # 410 gone


class IdExistsButError(RemoteError):
    """ convenience class used to close the space of errors
        where we know the remote exists """


class NotAuthorizedError(IdExistsButError):
    """ the current requesters permissions on the remote system are
        insufficient to grant access to this resource, and what to
        do about it maybe? """
    # this is 403 only NOT 401
    # FIXME 401 =/> that an id exists but 403 does? 401 is you cannot ask that question level/unknown
    # Don't be conused by the fact that HTTP calls these client errors
    # the client didn't do anything wrong


class AccessLimitError(RemoteError):
    """ the remote endpoint is feeling overwhelmed right now or
        you have too many books checked out from the library """
    # 429 too many requests and other such nonsense
