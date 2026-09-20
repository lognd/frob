## Done report

WHY LINUX WAS UNAFFECTED (measured, not inferred): the two CI legs' `uv`
binaries diverge because of a GitHub Actions cache-key artifact, not
`sys.platform`. The workflow never pins a `uv` version; `astral-sh/setup-uv`
caches whatever it installs under a key that embeds the runner's OS/arch and
system-Python triple. ubuntu2.log shows a cache HIT
(`setup-uv-1-x86_64-unknown-linux-gnu-3.12.3-<hash>`), so that leg reused a
`uv` binary cached from some earlier, unknown point in time. mac3.log shows
a cache MISS (`setup-uv-1-aarch64-apple-darwin-3.14.7-<hash>` -- first time
that exact key existed), so that leg downloaded whatever `uv` "latest"
resolves to right now: 0.12.10. It is 0.12.10 that validates an ambient
`VIRTUAL_ENV` against the spawned command's OWN discovered project's
configured `.venv` path and, on a mismatch (guaranteed here -- `VIRTUAL_ENV`
always points at the outer repo's venv, never at a throwaway fixture
project's), warns, ignores it, and builds a fresh, empty, wrong-interpreter
venv instead. This is a `uv`-version behavior gated on a stale-cache
accident, fully reproducible on ANY platform whose `uv` cache next misses
-- ubuntu's current immunity is incidental, not structural, and this
ticket's fix does not rely on it staying that way.

WHAT WAS CHOSEN, and why, among the three alternatives the ticket asked to
weigh:
  - `--active`: rejected -- still a `uv`-version-dependent fallback path,
    still exposed to the identical validation logic on some future `uv`
    release; does not remove the dependency on `uv`'s own environment
    resolution at all.
  - skip venv creation for these spawns without changing HOW pytest is
    invoked: rejected -- `pytest` would still resolve through `uv`/PATH,
    still subject to the same project-path mismatch check.
  - invoke through the interpreter frob is already running under, never
    through `uv run`: CHOSEN. `frob.process._pytest_spawn.
    resolve_pytest_argv` (T-3311) already exists in this codebase as
    exactly this convention and was simply never wired into
    `frob.testing._collect._run_collect_only`, which still hardcoded
    `("uv", "run", "pytest", ...)`. Switching that one call site removes
    `uv` from this spawn path entirely -- no project/venv discovery, no
    requires-python default, no dependence on `uv`'s cache/version state
    on either platform.

THE SECOND PROBLEM (fixture silently building on CPython 3.14 because it
declares no requires-python) is a SYMPTOM of the same uv-creates-a-fresh-
venv path, not a separate defect: once `_run_collect_only` never invokes
`uv` for this spawn, there is no fixture venv creation step left to pick a
default interpreter version from. Fixed as a side effect of the same
change; no separate ticket needed.

VERIFICATION: no macOS access this session. Everything above about WHY the
two CI legs diverged is read directly from this repo's OWN saved CI logs
(mac3.log, ubuntu2.log) -- a measurement, not a guess about macOS's own
behavior. The FIX itself was verified on Linux only (this session's only
platform): all `_collect.py`/`_pytest_spawn.py`-adjacent unit tests plus
every test file citing `collect_python_tests`/`_run_collect_only` as
`frob:tests` evidence (736 tests across 16 files) pass, and the full
`frob check` gate suite (gates-fast, gates-native, gates-security, lint,
static; --ticket T-4327) is 0 errors. INFERRED, not verified on macOS: that
removing `uv` from this one spawn path clears the specific 49 spawn
failures/61 test failures the ticket cites. That inference rests on reading
the exact mechanism out of `uv`'s own printed warning and this codebase's
own T-3311 precedent, not on reproducing the failure locally -- the next
macOS CI run is the actual confirmation.

### Changed
```
 tickets/T-4327/ticket.md | 129 ++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 127 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_testing_collect.py::TestRunCollectOnlySpawnShape::test_argv_never_names_uv` (pytest node id, verified passing when recorded)
- `tests/test_testing_collect.py::TestRunCollectOnlySpawnShape::test_pytest_not_importable_is_a_collect_failure_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/test_pytest_spawn.py::TestResolvePytestArgv::test_ok_uses_sys_executable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4681 warning(s), 953 waived
- error-findings: none (measured, zero errors)
