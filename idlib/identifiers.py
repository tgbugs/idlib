"""Identifiers are the smallest possible unit of a stream. Their
fundamental property is that they come equipped with an equality
operation. Not all equality operations are as simple as string= or
numberical equality. These must employ a true identity function that
does not reduce the amount of data that is compared. That is,
identifiers are distinguished from other pieces of data in the sense
that the family of functions that implement 'sameness' requires direct
comparison of every byte of two streams with an allowance for
conversion to a canonical form which may include reordering and
deduplication of elements of the identifier that follow set equality
rather than string equality for example composite primary keys in a
database may be rearranged into a preferred order for further byte to
byte comparison between rows, but the characters in a word cannot be
sorted prior to comparison if we are interested in the equality of two
ordered strings of chars.

Note that under the defintion provided above the ONLY requirement for
an identifier is that it come equipped with an identity function. This
means that whole computer programs can be identifiers as long as the
comparison function is defined. Then there is a question of the robustness
of that identity function to a change in context, specifically defined
as the failures of the equiality of identifiers to correctly imply the
equality of what they dereference to.

There is a tradeoff between robustness of reference and usefulness for
human communication. And for better or for worse the IRBs and IACUCs of
the world tend to frown upon shoving subjects through hash functions.

"""

import idlib


class Identifier(idlib.Stream):  # TODO decide if str should be base ...
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
    local_regex = None  # an unqualified, likely non-unique regex for the system local identifier
    canonical_regex = None  # but really '.+'
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

        return conventions.asLocal(self)
