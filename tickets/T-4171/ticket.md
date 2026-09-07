---
id: T-4171
title: 'the no-sync fix for a mutating tool spawn broke the gate that must import
  the target project''s modules: one setting serving two incompatible callers'
state: in-progress
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_project_tool.py
- tests/unit/test_check.py
- tests/test_coverage.py
- tests/unit/test_flag_coverage_gate.py
- src/frob/gates/_flag_coverage.py
- docs/modules/process.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_flag_coverage.py
  reason: T-4171's own body requires distinguishing the two spawn kinds at the flag-coverage
    resolver call site (CAUSE TWO), which lives in this file; the ticket's declared
    scope list omitted it
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/process.md
  reason: 'AFFECT001: project_tool_argv/project_import_argv changed and their frob:doc
    target lives here; update the doc in the same change'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001: new real-exec test fixtures (uv run/uv sync spawns) require
    declaring the exec capability for tests/unit/test_check.py and tests/unit/test_flag_coverage_gate.py
    in the testsuite node'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: 'SYS111 ratchet: two files (test_check.py, test_flag_coverage_gate.py) gained
    new exec via-list entries for real uv subprocess fixtures'
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given a read-only tool spawn, when it runs against a target project, then
    nothing in that project's tree is created or modified
  evidence: []
- text: given a gate that must import the target project's modules, when the environment
    cannot provide them, then it reports unmeasured rather than clean and does not
    mutate the target tree
  evidence: []
- text: given the argv the helper builds for each spawn kind, when the assertions
    run, then they match
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
SEVEN UBUNTU FAILURES, ALL IN THE TOOLCHAIN-ROUTING WORK, AND THE SECOND CAUSE IS
A GENUINE DESIGN TENSION RATHER THAN AN OVERSIGHT. CI run 34117841048:
collected=13653, failed=7. Two distinct causes.

CAUSE ONE -- AN ARGV SHAPE CHANGED AND ITS ASSERTIONS DID NOT (3 tests):

    tests/test_coverage.py::TestComputeWorkerCount
      ::test_pytest_argv_routes_through_project_env
    tests/unit/test_check.py::TestRunRuffRealPaths
      ::test_invokes_ruff_via_project_tool_argv_not_bare_ruff
    tests/unit/test_check.py::TestRunRuffAutofix
      ::test_success_runs_fix_then_format_via_project_tool_argv

    expected  ['uv', 'run', '--project', <root>, 'ruff', ...]
    actual    ['uv', 'run', '--no-sync', '--project', <root>, 'ruff', ...]

T-4163 added `--no-sync` to fix a real bug (the spawn was lazily syncing the
TARGET project's environment, writing an untracked lock file and virtualenv into
its tree, which a later gate then refused on). The tests asserting the argv were
written by the earlier tickets and were not updated. This is the FIFTH time in
this drive that a landed change broke a consumer of the thing it changed, and the
fourth where the ticket verified its own files and not the neighbours that assert
against them. Fix the assertions; they are pinning a shape that is now wrong.

CAUSE TWO IS NOT AN OVERSIGHT AND MUST NOT BE FIXED BY EDITING THE TEST (4 tests):

    tests/unit/test_flag_coverage_gate.py -- all four
    FLAGCOV001: parser=... failed to resolve in its own project environment:
    ModuleNotFoundError("No module named 'pydantic'") -- flag-coverage is
    UNMEASURED for this command tree, not clean

THE FIX FOR ONE BUG IS THE CAUSE OF THE OTHER. The flag-coverage gate resolves a
consumer's parser BY IMPORTING IT inside the target project's environment -- that
was T-4147's whole point, so a consumer's dependency at a different version no
longer breaks the import. With `--no-sync`, that environment is never populated,
so the import fails and the gate correctly reports UNMEASURED. Both behaviours are
right in isolation:

    syncing    correct for a gate that must IMPORT the target's code
               wrong because it mutates the target's working tree
    not syncing correct for a read-only lint spawn
               wrong for a gate that needs the target's dependencies present

So `project_tool_argv` currently has one setting for two incompatible callers.
Resolve it deliberately rather than by flipping the flag back:
  - Give the helper an explicit choice at the call site, named for the REASON
    rather than the flag -- a spawn that only runs a tool binary versus one that
    must import the project's own modules.
  - For the importing case, prefer a mode that uses an ALREADY-PRESENT environment
    without creating or mutating one, and report UNMEASURED honestly when none
    exists. An unmeasured flag-coverage result is a correct answer; a silently
    synced target tree is not.
  - Whatever is chosen, the read-only lint spawns must keep `--no-sync`. The bug
    it fixed was a gate failing on a file it had itself written, which is worse
    than an unmeasured gate.

NOTE WHAT THE GATE DID RIGHT, because it should survive the fix: faced with an
environment it could not import from, it reported UNMEASURED and said so in the
message rather than reporting clean. That is exactly the posture this queue keeps
asking for elsewhere. Do not lose it while fixing the environment question.

MUST-FIRE FIXTURE:   a read-only tool spawn does not create or modify anything in
                     the target project's tree.
MUST-STAY-QUIET:     a gate that must import the target's modules either resolves
                     them or reports UNMEASURED -- never reports clean, and never
                     mutates the target tree to succeed.
THIRD FIXTURE:       the argv assertions match the argv the helper actually
                     builds, for both spawn kinds.

ACCEPTANCE
- The three argv assertions updated to the current shape.
- The two spawn kinds distinguished at the call site, named by reason not by flag.
- The read-only spawns still non-mutating, proven by a fixture.
- The unmeasured-not-clean posture preserved.
- All three fixtures committed.
