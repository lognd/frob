import pytest


PY_SAMPLE = b"""\
import os
from pathlib import Path

def helper(x: int) -> str:
    return str(x) + "hello"

def another() -> None:
    do_something()
    do_more()

class MyClass:
    def process(self, data: bytes) -> list:
        return data.decode().splitlines()

    def _private(self) -> None:
        do_something()
        do_more()

class Other:
    def method(self) -> int:
        return 42
"""

CPP_SAMPLE = b"""\
#include <vector>
#include "local.h"

void helper(int x) {
    return;
}

class Engine {
public:
    void run(int cycles) {
        for (int i = 0; i < cycles; i++) {}
    }

    int status() {
        return 0;
    }
};
"""


@pytest.fixture
def py_sample():
    return PY_SAMPLE


@pytest.fixture
def cpp_sample():
    return CPP_SAMPLE
