import os
import pickle
import hashlib
import unittest
import pytest
import requests
from joblib import Parallel, delayed
import idlib

skipif_ci = pytest.mark.skipif('CI' in os.environ, reason='API key required')


def lol(d):
    """ HEY KIDS WATCH THIS """
    Parallel(n_jobs=2)(delayed(lambda d: d)(d) for d in (d,))


class HelperStream:
    stream = None
    ids = tuple()
    ids_bad = tuple()

    def test_stream_sections(self):
        # TODO run each on of the properties/methods in
        # a separate loop?
        cypher = hashlib.blake2b
        bads = []
        for i in self.ids:
            d = self.stream(i)
            d.identifier
            if d.identifier and hasattr(d.identifier, 'prefix'):
                print(d.identifier)
                print(d.identifier.prefix)
                print(d.identifier.suffix)
                if d.identifier.prefix is None or d.identifier.suffix is None:
                    bads.append(d.identifier.__dict__)

            try:
                d.identifier_bound_metadata
                d.identifier_bound_version_metadata

                d.checksum(cypher)  # data or metadata? indication that there should be multiple probably
                d.dereference()  # XXX induces infinite recursion
                d.headers()
                d.metadata()

                if not isinstance(d, idlib.HelperNoData):
                    d.data()

                d.progenitor()  # or is it d.data.progenitor?

                # test pickling
                hrm = pickle.dumps(d)
                tv = pickle.loads(hrm)
                if tv.checksum(cypher) != d.checksum(cypher):
                    bads.append((tv, d))

            except requests.exceptions.ConnectionError as e:
                pytest.skip('Internet done goofed')

            # test joblib
            lol(d)

        assert not bads, bads

    def test_malformed(self):
        bads = []
        for i in self.ids_bad:
            try:
                d = self.stream(i)
                d.append(bads)
            except:
                pass

        assert not bads, bads

    def test_hash_eq_id(self):
        hrm = self.ids[0]
        i1 = self.stream(hrm)
        i2 = self.stream(hrm)

        # what did we decide about how to handle this?
        # stream is the same but the state might be different?
        # what are the design tradeoffs here? it means that the
        # stream cannot be used as a dictionary key, which is
        # extremely annoying, but would still have A is B => False

        # we decided (as of now) that all streams hash to their
        # class plus the string representation of their identifier
        # and that equality compares class and identifier equality

        # hash testing
        assert len({i1, i2}) == 1
        assert len({i1.identifier, i2.identifier}) == 1

        assert len({i1, i1.identifier}) == 2
        assert len({i1, i2.identifier}) == 2
        assert len({i1.identifier, i2}) == 2

        # equality testing
        assert i1 == i2
        assert i1.identifier == i2.identifier

        assert i1 != i1.identifier
        assert i1 != i2.identifier
        assert i1.identifier != i2

        # python object identity testing (confusingly)
        assert i1 is not i2
        assert i1.identifier is not i2.identifier

        assert i1 is not i1.identifier
        assert i1 is not i2.identifier
        assert i1.identifier is not i2

    def test_asDict(self):
        for id in self.ids:
            s = self.stream(id)
            try:
                d = s.asDict()
            except requests.exceptions.ConnectionError as e:
                pytest.skip('Internet done goofed')


@pytest.mark.skip('Not ready.')
class TestStreamUri(HelperStream, unittest.TestCase):
    stream = idlib.StreamUri
    ids = [
        'https://github.com',
    ]
    ids_bad = ['lol not an identifier']
    def test_wat(self):
        ic = self.stream._id_class
        i = ic(self.ids[0])


@pytest.mark.skip('Not ready.')
class TestArk(HelperStream, unittest.TestCase):
    stream = idlib.Ark
    ids = [
        'https://doi.org/10.13003/5jchdy',
    ]
    ids_bad = ['lol not an identifier']


class TestDoi(HelperStream, unittest.TestCase):
    stream = idlib.Doi
    ids = [
        'https://doi.org/10.13003/5jchdy',
    ]
    ids_bad = ['lol not an identifier']
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
    ids_bad = []
    for __i in ids:  # LOL PYTHON class scope list comprehensions
        ids_bad.append(__i.replace('https', 'http'))
    del __i

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
    ids_bad = []
    for __i in ids:  # LOL PYTHON class scope list comprehensions
        ids_bad.append(__i.replace('https', 'http'))
    del __i

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


class TestRrid(HelperStream, unittest.TestCase):
    stream = idlib.Rrid
    ids = [
        'RRID:AB_1234567',
        'RRID:IMSR_JAX:000664',
        'RRID:SCR_001337',
        'RRID:RGD_10395233',
        'RRID:Addgene_19640',
        #'RRID:NCBITaxon_9606',  # TODO not in resolver yet
    ]
    ids_bad = ['lol not an identifier']


@skipif_ci
class TestPio(HelperStream, unittest.TestCase):
    stream = idlib.Pio
    ids = [
        'https://www.protocols.io/view/reuse-pc3diyn',
        'https://www.protocols.io/private/8DAE4D2451D5FE18A421D102BC2BEB39',

        #'https://www.protocols.io/view/103',
        #'https://www.protocols.io/view/106',

        'https://www.protocols.io/view/113',
        # changeover happens 128 maybe?
        'https://www.protocols.io/view/136',

        #'https://www.protocols.io/view/622',

        'https://www.protocols.io/view/650',

        'https://www.protocols.io/view/651',
        # changover somewhere in here
        'https://www.protocols.io/view/671',

        'https://www.protocols.io/view/2080',
        # changeover likely at a -> b 2081 -> 2082
        'https://www.protocols.io/view/2088',
    ]
    ids_bad = ['lol not an identifier']

    def test_users(self):
        for i in self.ids:
            d = self.stream(i)
            print(d.creator.orcid)
            for a in d.authors:
                if hasattr(a, 'orcid'):
                    print(a.orcid)

    def test_id_int(self):
        bads = []
        for i in self.ids:
            un = self.stream(i)
            uh = un.uri_human
            if un.identifier.is_int():
                assert uh.identifier_int == un.identifier.identifier_int

            if uh.identifier_int != uh.identifier.identifier_int:
                bads.append(uh.identifier)

        assert not bads, bads
            


@skipif_ci
class TestPioUser(HelperStream, unittest.TestCase):
    stream = idlib.PioUser
    ids = [
        'pio.user:tom-gillespie',
    ]
