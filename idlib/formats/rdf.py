import idlib
import rdflib
from pyontutils.namespaces import rdf, rdfs, owl, NIFRID, TEMP
# FIXME this is clearly backwards, pyontutils should be importing from here

locs = locals()
kwargs = {n:locs[n] for n in
          ['rdflib',
           'rdf',
           'rdfs',
           'owl',
           'NIFRID',
           'TEMP',]}

# bindRdf to any class that needs it
idlib.Ror.bindRdf(**kwargs)
