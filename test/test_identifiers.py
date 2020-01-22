import hashlib
import unittest
from idlib import Doi
from idlib.from_oq import OrcidId  # FIXME naming etc.


class TestDoi(unittest.TestCase):
    def test_doi_format(self):
        d = Doi('https://doi.org/10.13003/5jchdy')
        d.identifier
        d.identifier_bound_metadata
        d.identifier_bound_version_metadata
        d.checksum(hashlib.blake2b)  # data or metadata? indication that there should be multiple probably
        d.headers()
        d.metadata()
        d.data()
        d.progenitor()  # or is it d.data.progenitor?

    def test_version_f1000(self):
        # this doesn't exist
        #d = Doi('https://doi.org/10.12688/f1000research.6555')
        #d = d.identifier_bound_version_metadata

        d1 = Doi('https://doi.org/10.12688/f1000research.6555.1')
        d1.identifier_bound_version_metadata
        # of course there is no linke between the two >_<
        d2 = Doi('https://doi.org/10.12688/f1000research.6555.2')
        d2.identifier_bound_version_metadata
        # has an 'update-to' field ... which points backwards
        # but how to see if there is something new?


class TestOrcidId(unittest.TestCase):
    def test_validate(self):
        orcids = ('https://orcid.org/0000-0002-1825-0097',
                  'https://orcid.org/0000-0001-5109-3700',
                  'https://orcid.org/0000-0002-1694-233X')
        ids = [OrcidId(orcid) for orcid in orcids]
        bads = [orcid for orcid in ids if not orcid.checksumValid]
        assert not bads, str(bads)
