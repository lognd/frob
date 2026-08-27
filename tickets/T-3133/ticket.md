---
id: T-3133
title: 'frob ticket evidence individual-reverify: run_selected path never applies
  fleet xdist bound'
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_runners.py
- tests/test_testing.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_testing.py
  reason: added a unit test covering _run_one_runner's new apply_agent_env call (SCOPE002)
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_testing.py::TestRunners::test_applies_fleet_xdist_bound_before_spawning
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3a76e12252d34771bf508476c947a7bb046b5a71
---
UNCONFIRMED (reproducible via one specific code path, not via any manual
reconstruction): `frob ticket evidence`'s individual-reverify path
(`run_selected` with `fallback="evidence-verify-individual"`, in
src/frob/app/ticket_runner/_verify.py) consistently reported
`tests/test_refactor_corpus.py::TestRefactorCorpus::test_split_moves_symbols_across_every_call_site_shape`
FAILED (3x in a row, `frob ticket evidence T-3119 <4 ids>`), while every
manual reproduction of the SAME test passed cleanly and repeatably:

    uv run pytest tests/test_refactor_corpus.py -q -o addopts=""          # pass
    uv run pytest "tests/...::test_split_moves_symbols_across_every_call_site_shape" -q -o addopts=""   # pass
    uv run pytest -q "tests/...::test_split_moves_symbols_across_every_call_site_shape"   # pass, real pyproject addopts (xdist, -n auto)
    uv run pytest -q <all 4 evidence ids together>   # pass
    COVERAGE_PROCESS_START=<real rc> uv run pytest -q <id>   # pass
    frob test --base main   # exit=0, recorded 5 outcomes green, twice

Also `frob ticket evidence`'s own log did not show a stderr/traceback for
the individual failure at any log level I tried (INFO/WARNING only), so
I could not capture the actual assertion/exception text -- only that
`VerifyStatus.FAILED` was recorded for this one id.

## Candidate mechanism (not verified)

`_run_pytest_directly` (the no-`[[test.runner]]`-declared fallback path)
explicitly calls `apply_agent_env(root)` before spawning, with a
docstring citing T-3099: "apply the T-3094 fleet-aware xdist bound to
THIS process's own os.environ... closes the gap the eval-only export
left (T-3094's own diagnosis: nothing applied the printed export, so 0
of 40 live workers ever saw the bound)". The OTHER path -- `run_selected`
via a declared `[[test.runner]]` (frob.toml DOES declare one for
python, so this IS the path actually taken here, not the fallback) --
does NOT call `apply_agent_env` anywhere I could find in
`_run_one_runner`/`_run_language`/`run_selected`. If that is correct,
`PYTEST_XDIST_AUTO_NUM_WORKERS` is never fleet-bounded (the printed "6"
from `frob ticket work`'s own startup message) for this path, so
`-n auto` in `pyproject.toml`'s addopts auto-detects ALL host CPUs
instead. Under the same heavy concurrent host load this session
independently measured elsewhere (T-3130: cache lock errors under ~6
concurrent `frob check` runs), an unbounded xdist worker pool
overcommitting against an already-loaded host is a plausible mechanism
for a subprocess-heavy test (my new corpus test's
`_assert_all_py_files_importable` spawns ~8 extra real subprocess
imports, on top of `run_split`'s own internal `verify_module_import`
subprocess calls -- T-3119's own change) to genuinely fail or time out
specifically in this one code path, while a bounded/interactive run
never hits the same resource pressure.

## What I could NOT do

Confirm the mechanism -- I could not get `frob ticket evidence` to
surface the actual failure detail (stdout/stderr/traceback), and every
attempt to replicate the SAME command shape manually passed. This is
filed as a real, tool-reproducible symptom with a plausible but
UNVERIFIED cause, not a confirmed diagnosis.

## Plan

Check whether `_run_one_runner`/`run_selected`'s python branch should
also call `apply_agent_env(root)` (or an equivalent) before spawning,
matching `_run_pytest_directly`'s own T-3099 fix -- if so this is the
same class of gap T-3099 closed for the other code path, just left open
here. If reproduced with the mechanism confirmed, that is the fix; if
not reproducible after applying it, downgrade/close with the
non-reproduction noted the same way T-3131 was.