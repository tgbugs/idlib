import re
from .core import ConventionsType


class ConvTypeBytesHeader(ConventionsType):
    """ bytes header type conventions
        this version is intended for headers that start at
        an unknown offset so pattern matching is required """

    def __init__(self, format, start, stop, sentinel):
        self.format = format
        self.start = start
        self.stop = stop
        self.sentinel = sentinel

    def _findElement(self, element, chunk):
        m = re.search(element, chunk)
        if m is not None:
            # FIXME icky api
            return m.start(), m.end()
        else:
            return None, None

    def findStart(self, chunk):
        return self._findElement(self.start, chunk)

    def findStop(self, chunk):
        return self._findElement(self.stop, chunk)

    def findSentinel(self, chunk):
        return self._findElement(self.sentinel, chunk)
