---
id: T-1311
title: 'TEST005 burn-down: src/frob/_cli_parsers (6 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/**
- tests/unit/test_cli_parsers*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_cli_parsers.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/_cli_parsers.py
  reason: 'T-1431 relocated-symbols class: src/frob/_cli_parsers.py was split into
    a

    package src/frob/_cli_parsers/ (__init__.py, _check.py, _core.py, _misc.py,

    _reporting.py, _ticket/) after this ticket was filed. The old single-file

    glob no longer matches anything. Also tests/test_cli_parsers.py never

    existed as a dedicated file; tests for this area live scattered under

    tests/unit and tests/test_gates.py. Narrowing scope to the real package

    tree and the test files that actually reference _cli_parsers.

    '
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/test_cli_parsers.py
  reason: 'T-1431 relocated-symbols class: src/frob/_cli_parsers.py was split into
    a

    package src/frob/_cli_parsers/ (__init__.py, _check.py, _core.py, _misc.py,

    _reporting.py, _ticket/) after this ticket was filed. The old single-file

    glob no longer matches anything. Also tests/test_cli_parsers.py never

    existed as a dedicated file; tests for this area live scattered under

    tests/unit and tests/test_gates.py. Narrowing scope to the real package

    tree and the test files that actually reference _cli_parsers.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/**
  reason: 'T-1431 relocated-symbols class: src/frob/_cli_parsers.py was split into
    a

    package src/frob/_cli_parsers/ (__init__.py, _check.py, _core.py, _misc.py,

    _reporting.py, _ticket/) after this ticket was filed. The old single-file

    glob no longer matches anything. Also tests/test_cli_parsers.py never

    existed as a dedicated file; tests for this area live scattered under

    tests/unit and tests/test_gates.py. Narrowing scope to the real package

    tree and the test files that actually reference _cli_parsers.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_release_stamp_guard.py
  reason: 'T-1431 relocated-symbols class: src/frob/_cli_parsers.py was split into
    a

    package src/frob/_cli_parsers/ (__init__.py, _check.py, _core.py, _misc.py,

    _reporting.py, _ticket/) after this ticket was filed. The old single-file

    glob no longer matches anything. Also tests/test_cli_parsers.py never

    existed as a dedicated file; tests for this area live scattered under

    tests/unit and tests/test_gates.py. Narrowing scope to the real package

    tree and the test files that actually reference _cli_parsers.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_ticket_runner_land_cmd_flags.py
  reason: 'T-1431 relocated-symbols class: src/frob/_cli_parsers.py was split into
    a

    package src/frob/_cli_parsers/ (__init__.py, _check.py, _core.py, _misc.py,

    _reporting.py, _ticket/) after this ticket was filed. The old single-file

    glob no longer matches anything. Also tests/test_cli_parsers.py never

    existed as a dedicated file; tests for this area live scattered under

    tests/unit and tests/test_gates.py. Narrowing scope to the real package

    tree and the test files that actually reference _cli_parsers.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1431 relocated-symbols class: src/frob/_cli_parsers.py was split into
    a

    package src/frob/_cli_parsers/ (__init__.py, _check.py, _core.py, _misc.py,

    _reporting.py, _ticket/) after this ticket was filed. The old single-file

    glob no longer matches anything. Also tests/test_cli_parsers.py never

    existed as a dedicated file; tests for this area live scattered under

    tests/unit and tests/test_gates.py. Narrowing scope to the real package

    tree and the test files that actually reference _cli_parsers.

    '
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_cli_parsers*.py
  reason: 'T-1431 relocated-symbols class: src/frob/_cli_parsers.py was split into
    a

    package src/frob/_cli_parsers/ (__init__.py, _check.py, _core.py, _misc.py,

    _reporting.py, _ticket/) after this ticket was filed. The old single-file

    glob no longer matches anything. Also tests/test_cli_parsers.py never

    existed as a dedicated file; tests for this area live scattered under

    tests/unit and tests/test_gates.py. Narrowing scope to the real package

    tree and the test files that actually reference _cli_parsers.

    '
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/unit/test_release_stamp_guard.py
  reason: those files do not actually test _cli_parsers, closure warnings were false
    positives from shared fixture imports
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/unit/test_ticket_runner_land_cmd_flags.py
  reason: those files do not actually test _cli_parsers, closure warnings were false
    positives from shared fixture imports
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/test_gates.py
  reason: those files do not actually test _cli_parsers, closure warnings were false
    positives from shared fixture imports
  actor: logan
  at: '2026-08-03'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN the _cli_parsers package at the 75%/70% floors WHEN frob check --only
    test runs THEN it reports 0 TEST005 findings under src/frob/_cli_parsers/**
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: GIVEN a 0.0%-branch symbol in _cli_parsers WHEN it is judged dead code THEN
    it is routed to the DEAD gate/dup machinery or a removal ticket, never given an
    assert-True filler test
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: GIVEN a new test added to close a _cli_parsers TEST005 finding WHEN reviewed
    THEN it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
Package: src/frob/_cli_parsers (or the listed root modules).
TEST005 findings at current baseline: 6 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.