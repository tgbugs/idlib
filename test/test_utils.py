from time import sleep
from idlib.utils import timeout


def test_timeout():
    def slps(n):
        sleep(n)
        return True

    asdf = timeout(1)(slps)
    out = asdf(2)
    assert out is None, 'oops'
