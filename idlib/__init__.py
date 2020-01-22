from idlib.core import (Identifier,
                        Uri,
                        Curies,)
from idlib.from_oq import (Ror,
                           OrcidId,  # FIXME name
                           PioId,  # FIXME name
                           PioInst, # FIXME name and impl
                           PioUserInst, # FIXME name and impl
)
from idlib.core import families
from idlib.streams import Stream
from idlib.systems.handle import Handle
from idlib.systems.doi import Doi


def get_right_id(uri):
    # FIXME this is a bad way to do this ...
    if isinstance(uri, Doi) or 'doi' in uri and '/doi/' not in uri:
        if isinstance(uri, Doi):
            di = uri.asInstrumented()
        elif 'doi' in uri:
            di = DoiInst(uri)

        pi = di.resolve(PioId)

    else:
        if not isinstance(uri, PioId):
            pi = PioId(uri)  #.normalize()
        else:
            pi = uri

    return pi


__version__ = '0.0.1.dev1'
