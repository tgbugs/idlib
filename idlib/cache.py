import json
import hashlib
import inspect
from pathlib import Path
from functools import wraps
from .utils import log

COOLDOWN = '__idlib.cache_cooldown'

_type_order = (
    bool, int, float, bytes, str, tuple, list, set, dict, object, type, None
)


def type_index(v):
    for i, _type in enumerate(_type_order):
        if isinstance(v, _type):
            return i

    return -1


def args_sort_key(kv):
    """ type ordering """
    k, v = kv
    return k, type_index(v), v


def cache_hash(pairs, cypher=hashlib.blake2s):
    pairs = sorted(pairs, key=args_sort_key)
    converted = []
    for k, v in pairs:
        if k == 'self':  # FIXME convention only ...
            v, _v = v.__class__, v
        converted.append(k.encode() + b'\x01' + str(v).encode())

    message = b'\x02'.join(converted)
    m = cypher()
    m.update(message)
    return m.hexdigest()


def argspector(function):
    argspec = inspect.getfullargspec(function)
    def spector(*args, **kwargs):
        for i, (k, v) in enumerate(zip(argspec.args, args)):
            yield k, v

        if argspec.varargs is not None:
            for v in args[i:]:
                yield argspec.varargs, v

        for k, v in kwargs.items():
            yield k, v

    return spector


def cache(folder, ser='json', clear_cache=False, create=False, return_path=False):
    """ outer decorator to cache output of a function to a folder

        decorated functions accept an additional keyword argument
        `_refresh_cache` that can be used to force refresh the cache """

    if ser == 'json':
        serialize = json.dump
        deserialize = json.load
        mode = 't'
    else:
        raise TypeError('Bad serialization format.')

    write_mode = 'w' + mode
    read_mode = 'r' + mode

    folder = Path(folder)
    if not folder.exists():
        if not create:
            raise FileNotFoundError(f'Cache base folder does not exist! {folder}')

        folder.mkdir(parents=True)

    if clear_cache:
        log.debug(f'clearing cache for {folder}')
        shutil.rmtree(folder)
        folder.mkdir()

    def inner(function):
        spector = argspector(function)
        fn = function.__name__
        @wraps(function)
        def superinner(*args, _refresh_cache=False, **kwargs):
            filename = cache_hash(spector(*args, ____fn=fn, **kwargs))
            filepath = folder / filename
            fe = filepath.exists()
            if fe and not _refresh_cache:
                log.debug(f'deserializing from {filepath}')
                with open(filepath, read_mode) as f:
                    output = deserialize(f)

            else:
                output = function(*args, **kwargs)
                if output is not None:
                    with open(filepath, write_mode) as f:
                        serialize(output, f)

            if isinstance(output, dict) and COOLDOWN in output:
                # a hack to put a dummy variable in the cache
                # to prevent retrying on a persistent failure case
                if fe:
                    reason = output[COOLDOWN]
                    log.debug('currently in cooldown for {args} {kwargs} due to {reason}')

                # TODO add timing or remove cooldowns function
                output = None

            if return_path:
                return output, filepath
            else:
                return output

        return superinner

    return inner
