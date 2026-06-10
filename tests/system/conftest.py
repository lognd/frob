"""
Shared helpers for system (CLI end-to-end) tests.
"""

import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]
FIXTURES = Path(__file__).parent.parent / "fixtures"


def run(*args, input=None, cwd=None):
    return subprocess.run(
        FROB + list(args),
        capture_output=True,
        text=True,
        input=input,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Shared Python fixture source (matches tests/conftest.py PY_SAMPLE)
# ---------------------------------------------------------------------------

PY_FIXTURE = """\
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

CPP_FIXTURE = """\
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
