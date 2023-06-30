import os
import unittest
import pytest
import idlib
from idlib.streams import HelpTestStreams

skipif_ci = pytest.mark.skipif('CI' in os.environ, reason='API key required')
SKIP_NETWORK = ('SKIP_NETWORK' in os.environ or
                'FEATURES' in os.environ and 'network-sandbox' in os.environ['FEATURES'])
skipif_no_net = pytest.mark.skipif(SKIP_NETWORK, reason='Skipping due to network requirement')


@pytest.mark.skip('Not ready.')
class TestStreamUri(HelpTestStreams, unittest.TestCase):
    stream = idlib.StreamUri
    ids = [
        'https://github.com',
    ]
    ids_bad = ['lol not an identifier']
    def test_wat(self):
        ic = self.stream._id_class
        i = ic(self.ids[0])


@pytest.mark.skip('Not ready.')
class TestArk(HelpTestStreams, unittest.TestCase):
    stream = idlib.Ark
    ids = [
        'https://doi.org/10.13003/5jchdy',
    ]
    ids_bad = ['lol not an identifier']


class TestDoi(HelpTestStreams, unittest.TestCase):
    stream = idlib.Doi
    ids = [
        'https://doi.org/10.13003/5jchdy',
        'https://doi.org/10.1101/2020.10.19.343129',  # crossref 500 error
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


class TestOrcid(HelpTestStreams, unittest.TestCase):
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


class TestRor(HelpTestStreams, unittest.TestCase):
    stream = idlib.Ror
    ids = [
        'https://ror.org/0168r3w48',
        'https://ror.org/02dqehb95',
        'https://ror.org/051fd9666',
    ]
    ids_bad = [
        'https://ror.org/05ht4p406',  # used to exist but api won't tell you that
    ]
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

    @skipif_no_net
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


class TestRrid(HelpTestStreams, unittest.TestCase):
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
class TestPio(HelpTestStreams, unittest.TestCase):
    stream = idlib.Pio
    ids = [
        'https://www.protocols.io/view/protocol-for-chronic-implantation-of-patch-electro-b2qgqdtw',
        # api v3 fails for these slugs?
        'https://www.protocols.io/view/protocol-for-chronic-implantation-of-patch-electro-yxmvmno69g3p',
        #'https://www.protocols.io/view/protocol-for-chronic-implantation-of-patch-electro-yxmvmno69g3p/v1',

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

        'https://www.protocols.io/view/19358',

        'https://www.protocols.io/view/25122',

        'https://www.protocols.io/view/21417',
        'https://www.protocols.io/api/v3/protocols/21417',
        'https://www.protocols.io/api/v4/protocols/21417',

        'pio.view:human-islet-microvasculature-immunofluorescence-in-y3tfynn/materials',

    ]
    ids_bad = [
        'lol not an identifier',
        'https://www.protocols.io/view/18980',  # deleted
        'https://www.protocols.io/api/v3/protocols/18980',  # deleted
    ]

    @skipif_no_net
    def test_users(self):
        for i in self.ids:
            d = self.stream(i)
            if d.creator is not None:
                print(d.creator.orcid)
            for a in d.authors:
                if hasattr(a, 'orcid'):
                    print(a.orcid)

    @skipif_no_net
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
            
    @skipif_no_net
    def test_org(self):
        #p = idlib.Pio('pio.api:30899')  # not public ?
        #p = idlib.Pio('pio.api:19174')
        #p = idlib.Pio('pio.api:31399')
        p = idlib.Pio('pio.api:25122')  # is public

        #dd = p._data_direct()
        #j = dd.json()['protocol']

        #p1 = idlib.Pio('pio.api1:19174')
        d = p.data()
        d1 = p.data1()
        #breakpoint()
        print(p.asOrg())
        with open('/tmp/ptc.org', 'wt') as f:
            f.write(p.asOrg())


@skipif_ci
class TestPioUser(HelpTestStreams, unittest.TestCase):
    stream = idlib.PioUser
    ids = [
        'pio.user:tom-gillespie',
    ]


@skipif_ci
def test_stochastic_timeout():
    i = 'pio.view:human-islet-microvasculature-immunofluorescence-in-y3tfynn/materials'
    sigh = idlib.Pio(i)
    wat = sigh.identifier.uri_api
    sigh2 =  idlib.Pio(wat.curie)
    d2 = sigh2.data()
    d = sigh.data()
    # FIXME this should aways try to go through the uri_api_int right ?!?!?!?
    # or no? we decided that if you want the int form you should use that?
