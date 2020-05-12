from .core import Identity


class QnameAsLocalHelper:
    """ hack for classmethod inheritance sigh """

    @classmethod
    def asLocal(cls, local_or_global):
        return cls.qname(local_or_global)
