from idlib import exceptions as exc
from idlib.utils import families
from idlib.streams import (Stream,
                           HelperNoData,
                           StreamUri,)
from idlib.identifiers import (Identifier,)

import idlib.conventions.type  # LOL PYTHON
import idlib.conventions.local  # LOL PYTHON
from idlib.conventions.core import ConventionsLocal
from idlib.conventions.local import (Curies,
                                     QNames,)
from idlib.from_oq import (Auto,
                           Pio,
                           PioUser,)
from idlib.systems import (Ark,
                           Doi,
                           Handle,
                           Orcid,
                           Pmid,
                           Ror,
                           Rrid,
                           Uri,
                           Urn,)

# assign default identifier classes to streams
StreamUri._id_class = Uri

def get_right_id(uri):
    # FIXME this is a bad way to do this ...
    class StreamUriTemp(StreamUri):
        def asUri(self):
            return self.identifier

    if isinstance(uri, Doi) or 'doi' in uri and '/doi/' not in uri:
        if isinstance(uri, Doi):
            di = uri
        elif 'doi' in uri:
            di = Doi(uri)

        try:
            pi = di.dereference(Pio)
        except exc.MalformedIdentifierError:
            pi = di.dereference(StreamUriTemp)

    else:
        if not isinstance(uri, Pio):
            try:
                pi = Pio(uri)  #.normalize()
            except exc.MalformedIdentifierError:
                pi = StreamUriTemp(uri)
        else:
            pi = uri

    return pi


__version__ = '0.0.1.dev19'
