"""Models."""

from . import util
from .util import helper


class Base:
    def run(self):
        return 1


class Thing(Base):
    """A thing."""

    def __init__(self, n):
        self.n = n

    def go(self):
        return self.step() + helper(self.n)

    def step(self):
        return util.helper(1)
