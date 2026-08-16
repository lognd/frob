---
id: T-2240
title: Wire 'make coverage' full-suite recipe to frob coverage --full, retire text-slicing
  tests
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: high
parent: T-1382
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'GIVEN the coverage: target in Makefile WHEN read THEN its recipe body is
    a single uv run frob coverage --full line, not the ~40-line inline crash-recovery/rerun/stamp
    shell block'
  evidence: []
- text: GIVEN tests/unit/test_makefile_coverage.py WHEN read THEN it no longer regexes
    Makefile text (_recipe_tail/_MAKEFILE slicing) and instead exercises frob.testing._coverage_refresh's
    --full path directly
  evidence: []
- text: GIVEN the node-down xdist-crash recovery path THEN it still triggers a full
    serial rerun and still refuses to promote partial coverage data on failure (T-1363
    guard), proven by a test, not just inspection
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Makefile's coverage: target (lines ~315-352) still carries its own ~40-line POSIX shell recipe (timeout, node-down grep, serial rerun, coverage combine, T-1363 promote-guard) even though frob.testing._coverage_refresh.native_coverage_refresh (T-1516/T-1677/T-1672) already reimplements the identical crash-recovery/rerun-deadline logic in pure Python and is reachable via 'uv run frob coverage --full' (frob/_cli_parsers/_misc.py). coverage-fast already made this switch (T-1525); coverage: was explicitly deferred (see Makefile comment near coverage-fast: 'coverage: below is NOT rewritten the same way'). This leaf closes that deferral: point the make target at 'uv run frob coverage --full', verify parity (crash recovery, node-down serial-rerun-with-full-data-recovery, T-1363 never-promote-partial-on-failure, final frob check --stamp-coverage gate), and retire tests/unit/test_makefile_coverage.py's Makefile-text-regex tests (924 lines, _recipe_tail()/_MAKEFILE slicing at lines 16-50+) in favor of tests against the Python implementation directly. First test that must fail today: assert the coverage: recipe body in Makefile is <=2 non-comment lines -- it is currently ~40. MUST-STILL-PASS: make coverage (and its frob coverage --full replacement) must still detect and fail on a genuinely broken test, still refuse to promote partial data on an xdist worker crash, and still run cross-platform (no bash -c, no backslash continuation, no POSIX-only tools) per T-1205 acceptance[3], which _coverage_refresh.py already claims -- verify that claim rather than assume it.