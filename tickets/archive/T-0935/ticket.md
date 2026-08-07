---
id: T-0935
title: gates-native stage-group test hardcodes gate set, breaks on every new gate
  (T-0688 regression)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping
designated_repro_test: null
threat: null
component: null
---
Found while working T-0715 (unrelated to its scope, filed instead of
fixed): `tests/unit/test_app_runners_batch6.py::TestCheckRunner::
test_stamp_baseline_only_chunk_records_without_stamping` hard-codes the
expected `--only gates-native` gate-name set as
`frozenset({"archgate", "clones", "perf"})`. T-0688 (landed on main,
`feat: exhaustive-exception gate + errors-as-values advisory`) added a
new `exhaustive_handling` gate into that same stage group without
updating this test's expected set, so it now fails on `main` itself
(confirmed via `git show main:tests/unit/test_app_runners_batch6.py`
before touching anything) -- not something my worktree's merge
introduced.

Acceptance: GIVEN `main` as it stands WHEN
`test_stamp_baseline_only_chunk_records_without_stamping` runs THEN it
passes, either by widening the expected set to include
`exhaustive_handling` or by asserting membership/count instead of an
exact literal set (so the next gate added to `gates-native` doesn't
require a matching test edit every time).