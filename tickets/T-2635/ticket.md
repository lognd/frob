---
id: T-2635
title: 'test_exports.py: frob-exports reports missing symbols in src/frob, red on
  main'
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_exports.py
- src/frob/__init__.py
- src/frob/arch/__init__.py
- src/frob/lang/__init__.py
- src/frob/scaffold/__init__.py
- src/frob/testing/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/__init__.py
  reason: 'Investigation (see ticket body) established this is a genuine export gap,

    not a stale baseline: 12 public symbols across 5 packages are real,

    cross-module-referenced public API never re-exported through their

    package __init__.py. The fix is adding each symbol to its package''s

    __init__.py import block and __all__ list -- narrowing scope to exactly

    those 5 files plus the originating test file.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/arch/__init__.py
  reason: 'Investigation (see ticket body) established this is a genuine export gap,

    not a stale baseline: 12 public symbols across 5 packages are real,

    cross-module-referenced public API never re-exported through their

    package __init__.py. The fix is adding each symbol to its package''s

    __init__.py import block and __all__ list -- narrowing scope to exactly

    those 5 files plus the originating test file.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/lang/__init__.py
  reason: 'Investigation (see ticket body) established this is a genuine export gap,

    not a stale baseline: 12 public symbols across 5 packages are real,

    cross-module-referenced public API never re-exported through their

    package __init__.py. The fix is adding each symbol to its package''s

    __init__.py import block and __all__ list -- narrowing scope to exactly

    those 5 files plus the originating test file.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/scaffold/__init__.py
  reason: 'Investigation (see ticket body) established this is a genuine export gap,

    not a stale baseline: 12 public symbols across 5 packages are real,

    cross-module-referenced public API never re-exported through their

    package __init__.py. The fix is adding each symbol to its package''s

    __init__.py import block and __all__ list -- narrowing scope to exactly

    those 5 files plus the originating test file.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/testing/__init__.py
  reason: 'Investigation (see ticket body) established this is a genuine export gap,

    not a stale baseline: 12 public symbols across 5 packages are real,

    cross-module-referenced public API never re-exported through their

    package __init__.py. The fix is adding each symbol to its package''s

    __init__.py import block and __all__ list -- narrowing scope to exactly

    those 5 files plus the originating test file.

    '
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-2623's tests/unit/ red-test sweep (measured at main sha
5a15dbd92, 18 red of 5237 collected).

tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
fails: "frob-exports still reports missing symbols: {'src/frob': [...]}" --
the exports policy tool is reporting real missing-symbol residue against
src/frob. Needs investigation to determine whether this is a genuine
public-API export gap (fix the export) or the residue baseline the test
compares against is stale (update the baseline) -- read both sides before
choosing.

Not fixed in T-2623 due to a time-boxed land window (T-2611 draining the
fleet for a repo-wide renormalization land).
