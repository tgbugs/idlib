import ontquery as oq  # temporary implementation detail
import idlib


# wiki has claims that Orcids are Isnis
# but I need more information ...


class OrcidPrefixes(oq.OntCuries):
    # set these manually since, sigh, factory patterns
    _dict = {}
    _n_to_p = {}
    _strie = {}
    _trie = {}


OrcidPrefixes({'orcid':'https://orcid.org/',
               'ORCID':'https://orcid.org/',})


class OrcidId(oq.OntId, idlib.Identifier):
    _namespaces = OrcidPrefixes

    class OrcidMalformedError(Exception):
        """ WHAT HAVE YOU DONE!? """

    class OrcidLengthError(OrcidMalformedError):
        """ wrong length """

    class OrcidChecksumError(OrcidMalformedError):
        """ failed checksum """

    @property
    def checksumValid(self):
        """ see
        https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier
        """

        try:
            *digits, check_string = self.suffix.replace('-', '')
            check = 10 if check_string == 'X' else int(check_string)
            total = 0
            for digit_string in digits:
                total = (total + int(digit_string)) * 2

            remainder = total % 11
            result = (12 - remainder) % 11
            return result == check
        except ValueError as e:
            raise self.OrcidChecksumError(self) from e


class Orcid(idlib.HelperNoData, idlib.Stream):
    _id_class = OrcidId
