## Done report

Measured the win32 CI leg's INTERNALERROR (KeyError: <WorkerController gw5>) directly
from the saved job log (run 34240795928) rather than reasoning about it. The partial
failing set named two mechanisms, not one:

1. tests/system/test_public_api_from_wheel.py::test_advertised_public_api_imports_
   from_a_built_wheel -- a REAL, reproducible bug in this ticket's own scope: the
   test hardcoded `venv_dir / "bin" / "python"` (posix-only), so `uv pip install`
   failed on win32 with "No virtual environment or system Python installation
   found" since that path never exists on Windows (Scripts/python.exe does). Fixed
   with the same sysconfig-derived pattern test_scaffold_dx.py already uses
   (T-4234's `_venv_console_script`) -- added `_venv_python` and switched the one
   call site. Verified locally (toolchain available here): all 3 tests in the file
   pass under `pytest -p no:xdist`.

2. tests/system/test_frob_self_model.py's two OOM-killed self-scan tests (gw0,
   gw2, ~300s each) -- a DIFFERENT mechanism from T-3754/T-3757 (both read fully
   before starting: those fixed per-test TIMEOUT kills; this is an OOM kill, well
   under even the pre-T-3757 120s default). Root cause: `tests/conftest.py`'s
   `_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` list, which serializes full-repo-scan tests
   onto one shared xdist worker to prevent exactly this OOM shape, is MISSING the
   `test_frob_self_model.py` siblings of the one test it does list -- so two
   independent full-repo `build_graph` scans ran concurrently on separate workers.
   Both workers dying mid-schedule is what corrupts xdist's loadscope scheduler
   bookkeeping and produces the `KeyError: <WorkerController gw5>` INTERNALERROR
   that aborts the whole session. This is out of T-4322's scope (tests/conftest.py,
   not tests/system/test_public_api_from_wheel.py) -- filed as T-4329
   with the full analysis and the specific fix (add the missing test names, or key
   the grouping off fixture use instead of a hand-maintained name list) rather than
   fixed here.

CONCLUSION FOR THE TICKET'S OWN QUESTION (regression / outgrown / never covered):
the OOM-crash mechanism was NEVER COVERED by T-3754/T-3757 -- those addressed a
different failure mode (timeout kills) entirely, and their fix (skipif + raised
timeout) does not touch memory pressure. This is not a regression of either prior
fix; it is a new instance of the SAME general "full-repo scan test missing from
the heavy grouping" defect class T-1433 first found, now recurring in a sibling
file the original T-1433 audit did not enumerate.

Given the OOM root cause remains open (T-4329, out of scope here), the
win32 suite will most likely still abort on its next run even with this fix
landed -- this ticket's own ONE bug (the wheel-install path) is fixed and
verified, but "a completed run" as the overall success criterion depends on the
follow-up ticket also landing. Said plainly so the next Windows ticket is not
mis-scoped against a false "should be green now" premise.

### Changed
tests/system/test_public_api_from_wheel.py (added `_venv_python`, switched
`venv_python` assignment to it)

Filed: T-4329

### Changed
```
 tests/system/test_public_api_from_wheel.py | 25 +++++++-
 tickets/T-4322/done-report.md              | 70 +++++++++++++++++++++++
 tickets/T-4322/ticket.md                   | 13 +++++
 tickets/T-4329/ticket.md         | 92 ++++++++++++++++++++++++++++++
 4 files changed, 199 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_public_api_from_wheel.py::test_advertised_public_api_imports_from_a_built_wheel` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4681 warning(s), 953 waived
- error-findings: none (measured, zero errors)
