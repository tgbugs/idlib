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

    def _findElement(self, element, chunk, prev):
        to_search = prev + chunk
        m = re.search(element, to_search)
        if m is not None:
            lp = len(prev)
            # FIXME icky api
            return m.start() - lp, m.end() -lp
        else:
            return None, None

    def findStart(self, chunk, prev):
        return self._findElement(self.start, chunk, prev)

    def findStop(self, chunk, prev):
        return self._findElement(self.stop, chunk, prev)

    def findSentinel(self, chunk, prev):
        return self._findElement(self.sentinel, chunk, prev)
