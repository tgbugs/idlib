class Conventions:
    """ local or type conventions """


class Identity(Conventions):

    @staticmethod
    def asLocal(identifier):
        if not isinstance(identifier, str):
            return Identity.asLocal(identifier.identifier)
        else:
            return identifier


class ConventionsType(Conventions):
    """ type conventions """


class ConventionsLocal(Conventions):
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
