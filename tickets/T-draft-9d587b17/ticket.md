---
id: T-draft-9d587b17
title: 'Gate stages are not verbs: fold dup arch cycle bind perf mutate coverage parse
  pool profile narrative debt deprecated into frob check --only'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4690
parent: T-4687
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/app/check_runner.py
- src/frob/app/dup_runner.py
- src/frob/app/arch_runner.py
- src/frob/app/cycle_runner.py
- src/frob/app/bind_runner.py
- src/frob/app/exports_runner.py
- src/frob/app/perf_runner.py
- src/frob/app/mutate_runner.py
- src/frob/app/coverage_runner.py
- src/frob/app/parse_runner.py
- src/frob/app/pool_runner.py
- src/frob/app/profile_runner.py
- src/frob/app/debt_runner.py
- src/frob/app/deprecated_runner.py
- tests/unit/test_check_only_stages.py
- tests/fixtures/check_stages/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a committed fixture tree containing a planted duplicate block, when
    frob check --only dup runs on it, then it reports that duplicate -- the same finding
    frob dup reported before the fold (golden comparison, not a no-crash assertion)
  evidence: []
- text: Given frob check --list-stages, when it runs, then every folded stage name
    is printed and each printed name is accepted by frob check --only
  evidence: []
- text: Given the exports generate mode, when the check half folds into frob check
    --only exports, then the generate half is reachable under its new home and a test
    exercises it
  evidence: []
threat: null
component: cli
labels:
- cli-debloat
- points-3
anchor: false
anchor_reason: null
land_commit: null
---
POINTS: 3. Parent story T-4687. blocked_by T-4689 (needs the shim helper, and
shares _core.py/_misc.py/_reporting.py/__main__.py with it).

PRINCIPLE: a gate stage is not a verb. `frob check` already runs these stages;
having each one ALSO be a top-level verb doubles the surface for zero new
capability, and it is why `frob --help` lists 51 entries.

FOLD INTO `frob check --only <stage>`:
  dup arch cycle bind perf mutate coverage parse pool profile narrative
  debt deprecated
Each keeps a one-minor-version shim (the T-4689 helper) that prints
`frob check --only <stage>` and exits non-zero after the sunset date.

ADD `frob check --list-stages`: prints every stage name, one per line, so the
shims' suggested spelling is discoverable and testable. `--only` already exists
on `frob check`; verify it accepts every folded stage name before deleting the
verb, and add the stage if it does not.

`exports` IS THE EXCEPTION: its help string is "generate __init__.py from public
symbols in a package directory" -- a GENERATE mode, not a check. Keep the
generate mode, but move it to `frob refactor exports` or `frob scaffold exports`
(pick whichever the existing runner's shape fits with less code; say which in
the Done report). Its CHECK half still folds into `frob check --only exports`.

POSITIVE CONTROL (acceptance): a golden test on a committed fixture tree that
plants a real duplicate block, asserts `frob dup` and `frob check --only dup`
produce IDENTICAL findings on it before the deletion, and after the deletion
asserts `frob check --only dup` still reports the planted duplicate. A test that
only asserts "no crash" does not close this ticket -- the fixture must contain a
finding the tool is REQUIRED to report.

FILES (declared scope):
  src/frob/_cli_parsers/_core.py, _misc.py, _reporting.py, _check.py
  src/frob/__main__.py
  src/frob/app/check_runner.py
  src/frob/app/dup_runner.py, arch_runner.py, cycle_runner.py, bind_runner.py,
  exports_runner.py, perf_runner.py, mutate_runner.py, coverage_runner.py,
  parse_runner.py, pool_runner.py, profile_runner.py, debt_runner.py,
  deprecated_runner.py
  tests/unit/test_check_only_stages.py (new), tests/fixtures/check_stages/ (new)
