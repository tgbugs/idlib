

class IdlibError(Exception):
    """ base class for idlib errors """


class ResolutionError(Exception):
    """ something went wrong """


class MalformedIdentifierError(IdlibError):
    """ Your input cannot be determined to be of the
        type of the identifier you want, therefor we will
        NOT create an object of that type, it cannot exist. """
