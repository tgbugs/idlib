test_clean_cache = True

if test_clean_cache:
    import os
    import atexit
    import shutil
    from tempfile import gettempdir
    from pathlib import Path
    import orthauth as oa
    import idlib
    from idlib import config
    import importlib

    _pid = os.getpid()
    _uid = os.getuid()

    temp_path = Path(gettempdir())
    test_cache_path =  temp_path / f'{_uid}-idlib-test-cache-path-{_pid}'
    test_cache_path.mkdir()
    atexit.register(lambda : shutil.rmtree(test_cache_path))

    ablob = config.auth._blob
    ublob = config.auth.user_config._blob
    if 'auth-variables' not in ublob:
        ublob['auth-variables'] = {}
    ublob['auth-variables']['cache-path'] = test_cache_path.as_posix()
    config.auth = oa.AuthConfig.runtimeConfig(ablob, ublob)

    # we have to reload all of these modules so that the updated value of auth
    # will be used to populate the @cache decorators that run at import time
    importlib.reload(idlib.from_oq)
    importlib.reload(idlib.systems.doi)
    importlib.reload(idlib.systems.ror)
    importlib.reload(idlib.systems.orcid)
    importlib.reload(idlib.systems.rrid)
    # must also reload these otherwise pickling errors due to duplicate classes
    importlib.reload(idlib.systems)
    importlib.reload(idlib)
