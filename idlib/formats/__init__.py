

class Rdf:

    def _triples_gen(self,
                     rdflib=None,
                     **kwargs,):
        # add the names you want bound as an explicit kwarg
        raise NotImplementedError

    @classmethod
    def bindRdf(cls, **kwargs):
        cls._triples_gen_kwargs = kwargs

    @property  # FIXME pretty sure this can't be a property if we do this right
    def triples_gen(self):  # FIXME how to do this without rdflib live ... re: pysercomb
        yield from self._triples_gen(**self._triples_gen_kwargs)
