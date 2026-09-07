---
id: T-4244
title: 'Windows path-shape class: four failures where a backslash-rendered path is
  compared against a forward-slash string'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: T-4236
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/ticket_land_suite/test_land_core.py
- tests/unit/arch_suite/test_misc.py
- tests/unit/rapid_sweep_suite/test_filing.py
- tests/unit/test_lang_primitives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given each of the four comparisons, when run on linux and on Windows, then
    both platforms agree
  evidence: []
- text: given the linux behaviour of each, when the fix lands, then it is unchanged
  evidence: []
- text: given the path conversion, when it is applied, then it routes through the
    existing shared helper rather than a new spelling
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FOUR WINDOWS FAILURES, ONE MECHANISM: a Windows path rendered with backslashes
compared against a forward-slash string. Fix as ONE shared change, not four
per-test corrections.

    ticket_land_suite/test_land_core.py::TestRecordLandCommit
      ::test_record_land_commit_never_absorbs_a_bystanders_dirty_file
      a stringified path checked for membership in git's own forward-slash output

    unit/arch_suite/test_misc.py::TestCppSymrefCanonicalization
      ::test_symref_matches_dsl_waiver_binding_exactly
      a violation symref and a waiver source differing only in separator

    unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile
      ::test_absolute_outside_root_is_kept_and_logged
      an absolute path checked for membership in a log message

    unit/test_lang_primitives.py::test_symbol_tree_covers_span
      a span comparison that ALSO differs by a trailing newline -- line endings
      as well as separators, so separators alone will not fix this one

THE RULE: producers emit POSIX, comparisons are against POSIX. A shared
conversion helper already exists for this class in the duplicate-detection
module, where three sites were routed through one helper rather than three
spellings. Extend that pattern; do not add a fourth.

VERIFY ON REAL WINDOWS. A global winrun script syncs this repo to a Windows
mirror and runs natively there -- measured working, and it reports win32 with a
backslash separator and a forward-slash altsep. Reproduce each failing comparison
there BEFORE changing anything and re-measure after. Two of these four depend on
library behaviour derived from the platform separator, which is exactly what
cannot be reasoned about from a linux shell. Three times in this drive a Windows
claim was reasoned out here and was wrong, including a replacement fixture
written to fix the first instance.

MUST-FIRE FIXTURE:   each of the four comparisons behaves identically on linux
                     and on Windows, proven by running it on both.
MUST-STAY-QUIET:     the linux behaviour of each is unchanged.
THIRD FIXTURE:       the conversion goes through the existing shared helper, not
                     a new per-site spelling.

ACCEPTANCE
- The four fixed by one shared mechanism.
- Each assertion measured on real Windows before and after.
- No fourth conversion spelling introduced.
- All three fixtures committed.
