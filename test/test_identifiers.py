import hashlib
import unittest
import pytest
import idlib


class HelperStream:
    stream = None
    ids = tuple()
    def test_stream_sections(self):
        # TODO run each on of the properties/methods in
        # a separate loop?
        for i in self.ids:
            d = self.stream(i)
            d.identifier
            d.identifier_bound_metadata
            d.identifier_bound_version_metadata
            d.checksum(hashlib.blake2b)  # data or metadata? indication that there should be multiple probably
            d.dereference()
            d.headers()
            d.metadata()

            if not isinstance(d, idlib.HelperNoData):
                d.data()

            d.progenitor()  # or is it d.data.progenitor?

    def test_asDict(self):
        for id in self.ids:
            s = self.stream(id)
            d = s.asDict()


@pytest.mark.skip('Not ready.')
class TestStreamUri(HelperStream, unittest.TestCase):
    stream = idlib.StreamUri
    ids = [
        'https://github.com',
    ]
    def test_wat(self):
        ic = self.stream._id_class
        i = ic(self.ids[0])


@pytest.mark.skip('Not ready.')
class TestArk(HelperStream, unittest.TestCase):
    stream = idlib.Ark
    ids = [
        'https://doi.org/10.13003/5jchdy',
    ]


class TestDoi(HelperStream, unittest.TestCase):
    stream = idlib.Doi
    ids = [
        'https://doi.org/10.13003/5jchdy',
    ]
    def test_version_f1000(self):
        # this doesn't exist
        #d = idlib.Doi('https://doi.org/10.12688/f1000research.6555')
        #d = d.identifier_bound_version_metadata

        d1 = idlib.Doi('https://doi.org/10.12688/f1000research.6555.1')
        d1.identifier_bound_version_metadata
        # of course there is no linke between the two >_<
        d2 = idlib.Doi('https://doi.org/10.12688/f1000research.6555.2')
        d2.identifier_bound_version_metadata
        # has an 'update-to' field ... which points backwards
        # but how to see if there is something new?


class TestOrcid(HelperStream, unittest.TestCase):
    stream = idlib.Orcid
    ids = [
        'https://orcid.org/0000-0002-1825-0097',
        'https://orcid.org/0000-0001-5109-3700',
        'https://orcid.org/0000-0002-1694-233X',
    ]
    def test_validate(self):
        ids = [self.stream._id_class(orcid) for orcid in self.ids]
        bads = [orcid for orcid in ids if not orcid.checksumValid]
        assert not bads, str(bads)

    def test_asType(self):
        import rdflib
        from idlib.formats import rdf as _bind_rdf
        o = idlib.Orcid(self.ids[0])
        nt = o.asType(rdflib.URIRef)
        # still haven't decided if this is a good idea or not
        assert str(o) != str(nt), 'string representation of streams should not match id ???'


class TestRor(HelperStream, unittest.TestCase):
    stream = idlib.Ror
    ids = [
        'https://ror.org/0168r3w48',
        'https://ror.org/02dqehb95',
        'https://ror.org/051fd9666',
    ]

    def test_init(self):
        ic = idlib.Ror._id_class
        r = idlib.Ror._id_class(prefix='ror.api', suffix='0168r3w48')
        assert type(r.identifier) is str

    def test_validate(self):
        for id in self.ids:
            s = self.stream(id)
            assert s.checksumValid, f'oops, {id}'

    def test_triples(self):
        from idlib.formats import rdf as _bind_rdf
        r = idlib.Ror(self.ids[0])
        trips = list(r.triples_gen)

    def test_asType(self):
        import rdflib
        from idlib.formats import rdf as _bind_rdf
        r = idlib.Ror(self.ids[0])
        nt = r.asType(rdflib.URIRef)
        assert str(r) != str(nt), 'string representation of streams should not match id'
