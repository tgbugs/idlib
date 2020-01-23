from idlib.core import families
from idlib.streams import (Stream,
                           HelperNoData,
                           StreamUri,)
from idlib.identifiers import (Identifier,)
from idlib.local_conventions import (LocalConventions,
                                     Curies,
                                     QNames,)
from idlib.from_oq import (PioId,  # FIXME name
                           PioInst, # FIXME name and impl
                           PioUserInst, # FIXME name and impl
)
from idlib.systems import (Ark,
                           Doi,
                           Handle,
                           Orcid,
                           Ror,
                           Rrid,
                           Uri,
                           Urn,)

# assign default identifier classes to streams
StreamUri._id_class = Uri

def get_right_id(uri):
    # FIXME this is a bad way to do this ...
    if isinstance(uri, Doi) or 'doi' in uri and '/doi/' not in uri:
        if isinstance(uri, Doi):
            di = uri
        elif 'doi' in uri:
            di = Doi(uri)

        pi = di.dereference(PioId)

    else:
        if not isinstance(uri, PioId):
            pi = PioId(uri)  #.normalize()
        else:
            pi = uri

    return pi


__version__ = '0.0.1.dev1'
