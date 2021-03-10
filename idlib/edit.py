"""
This is ill specified right now. Some thoughts.

The objective is that I have distinguishable content
that is dereferencable from a certain identifier, and
I would like to be able to change some or all of the
content that is returned on dereference.

The underlying semantics for this are extremely diverse.
And there are countless layers of abstraction that you
might have to wade through in order to get to the actual
source of truth.

- Source of truth
  - file on disk mutable
  - file on disk read only but can do an atomic mv/swap
  - file on disk on copy on write file system
  - named path in a git repository at a given ref/rev e.g.
    git-local[conventions]:repo:branch:path/to/file.ext
  - immutable blob in an object store at a given name
  - database (wow this is actually really scary ... it is just
    whatever it is)
- Edit mechanisms
  - Change out the whole source stream behind the scenes
  - Mutate the source stream (what are the atomicity guarantees?)
- Sort of edit
  - Update a known mutable pointer to point to a different immutable pointer.
  - Update a known mutable pointer that is listed in the metadata for
    each immutable pointer.
- Not really edit mechanisms
  - Tell everyone else in the world to change the identifier they use.
  - Add one more pointer to an ever growing deference chain after
    changing the previous referent from a stream to another pointer.
- Stores
  - Mutable store
    - Modify bits in place on a file on a single hard disk.
    - Modify the bits of a "file" in a distributed system,
      if you can do this the abstraction of the distributed
      system is almost surely leaky.
  - Immutable store
    - Update the indirect pointer.
    - Point to a different underlying stream.
    - Change the inode that a particular filename points to.

Furthermore, sometimes you don't actually want to edit the underlying
stream, you just want to update an identifier that is known to point
to a latest version. The issue is that there is a subtle difference in
semantics. Specifically, that in the pure "edit" case there is no
intervening metadata and no recoverable version information, thins
like that. If I have a doi whose type says it dereferences to the
"latest version" of series of dois that dereference immutably.

"""

import idlib


class Stream(idlib.Stream):
    """ example ... """

    def asEditable(self):
        # TODO need a way to set the branch, obtain the repo, find the local file, etc. etc.
        return self._editable_type(self.identifier_editable)

    # in some cases the api for editing/overwriting is simply
    # LocalPath('blah').data = ('lolololol' for _ in range(1))


class EditViaPullRequest:
    pass


class EditViaPush:
    pass


class EditViaApi:
    pass


class EditViaSsh:
    pass


class EditViaRsync:
    pass


class EditViaWebDAV:
    pass


class StreamEdit:
    """ some times you want to edit the contents of a stream
        whose source you may or may not control """

    # XXX just like streams have headers/metadata, we need/want
    # Stream.asEditable or something like that that can capture
    # the process needed to edit/modify the contents of the stream
    # for some types of streams that is always going to be impossible
    # i.e. for immutable streams, others, like files, may simply be a
    # call to open, some might require kicking off a long running process
    # like a pull request and thus need some persistent store to track
    # the the state of the process
    def __init__(self, editable_identifier, static_identifier=None):
        # static identifier would be the source iri
        pass
