---
id: T-2970
title: 'frob-dup: narrow the tests/ renamed-detector threshold (fixture-repetition
  false positives)'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/dup/**
evidence_scope:
- tests/unit/test_dup.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_dup.py::TestTestsDirectoryFloor::test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group
- tests/unit/test_dup.py::TestTestsDirectoryFloor::test_genuine_helper_duplicate_at_20_lines_still_fires
designated_repro_test: null
acceptance:
- text: given the tests/ frob-dup cluster and a chosen narrowing (directory-scoped
    min_lines or a fixture-shape heuristic), when implemented with a positive-control
    test proving a real duplicate is still caught, then re-measuring the tests/ cluster
    shows a measured reduction with the before/after counts and retired-group list
    reported
  evidence:
  - tests/unit/test_dup.py::TestTestsDirectoryFloor::test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group
  - tests/unit/test_dup.py::TestTestsDirectoryFloor::test_genuine_helper_duplicate_at_20_lines_still_fires
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2955's triage of the tests/ frob-dup cluster (479 unaccounted
groups, unscoped, measured 2026-08-26) spot-checked 4 large/varied
groups (tests/unit/test_arch.py x2, tests/unit/strata/
test_litmus_waive.py vs test_litmus_waive_store.py, tests/test_gates.py,
tests/test_dup.py) and found all 4 to be deliberate fixture/arrange-
block repetition, not shared-logic debt -- see T-2955's done report
for the full per-group reasoning.

The recommended fix is a detector-level change, not per-group waivers
at this volume (479 near-identical waiver comments is its own debt)
and not a blanket `tests/` exclusion (would blind frob-dup to real
test-helper duplication, which DOES exist per T-0375's own history).

Two candidate narrowings, either is acceptable, pick based on
implementation cost once you're in the code:

1. A directory-scoped `min_lines` override: `frob.dup._legacy.
   find_duplicates` currently takes one repo-wide `min_lines: int = 6`.
   Add a path-prefix override (e.g. `tests/` gets a higher floor, maybe
   20-30 lines based on re-measuring what floor would have retired the
   4 sampled groups without losing real positives) so short structural
   echoes in test arrange-blocks stop registering as their own groups.

2. A fixture-shape heuristic: a function body that is majority string-
   literal/dict-literal construction (the `write_text(...)`-heavy
   arrange-block shape common to all 4 samples) is a weak signal for
   "this is fixture setup, not logic" -- the exact/renamed detectors
   already parse the AST, so this is measurable without a new pass.

REQUIRED before landing either: a positive-control check (per the
playbook's "positive control or it proves nothing" -- appendix,
positive-control-or-it-proves-nothing.md) -- plant a genuine test-
helper duplicate (two DIFFERENT test files calling the exact same
non-trivial assertion sequence, a real desync risk) and confirm the
narrowed detector STILL catches it after the change. Re-measure the
tests/ cluster before/after; report the delta and which specific
groups the narrowing retired vs left standing.

Re-measure via: uv run frob check --json --only static, filter
tool=="frob-dup", filter messages where every location starts with
"tests/".