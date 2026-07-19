"""Shim used by tests/system/test_cli_native_missing.py (T-0316) to simulate
a `uv tool install frob` with no natives, at real subprocess granularity.

Placed first on `PYTHONPATH` for the subprocess under test, this shadows the
real compiled `strata_core` extension: any `import strata_core` finds THIS
module instead and gets a raised `ImportError`, exactly matching what a
standalone install with no natives produces. `frob.strata._parse` and
`frob.strata._facts` both guard their `import strata_core` in a bare
`try/except ImportError`, so this reproduces the real degrade path
end-to-end through a real CLI invocation, not just a monkeypatched unit
test.
"""

raise ImportError(
    "simulated: strata_core native extension not installed (T-0316 litmus)"
)
