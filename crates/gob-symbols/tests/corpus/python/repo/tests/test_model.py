from pkg import helper
from pkg.model import Thing


def test_go():
    t = Thing(1)
    assert t.go() == 3


class TestThing:
    def test_helper(self):
        assert helper(2) == 4
