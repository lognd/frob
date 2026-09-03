---
id: T-3678
title: 'self-gate floor (d): COV007/REF002/OPAQUE001/TEST001 singletons'
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_capacity.py
- src/frob/process/_lock_msvcrt.py
- src/frob/app/_config_external.py
- src/frob/strata/_models.py
- tests/unit/strata/test_capacity.py
- tests/unit/test_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 remedy: comment/waiver/test-only fix'
  actor: logan
  at: '2026-09-01'
  old_length: 1537
  new_length: 1675
evidence:
- tests/unit/strata/test_capacity.py::TestGrowthPeriodSeconds::test_resolves_known_time_unit
- tests/unit/strata/test_capacity.py::TestGrowthPeriodSeconds::test_unknown_unit_is_err
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Self-gate floor bucket (d), part 1: COV007 (private-symbol frob:doc anchors).

src/frob/strata/_capacity.py::_resolve_population_scale (lines 96, 106)
and ::_resolve_elapsed_seconds (lines 120, 129) each carry a duplicated
frob:doc directive (one immediately before the def, one repeated inside
the body) pointing at docs/strata/reliability.md /
docs/strata/kernel.md anchors that the PUBLIC caller project_capacity
(lines 196-197) already carries. Fix: drop the 4 redundant private-
symbol frob:doc directives; the doc anchor stays covered via
project_capacity, per COV007's own remedy ("move it onto the public
caller").

Also in scope, same bucket (d), unrelated files:
- src/frob/process/_lock_msvcrt.py -- REF002, single inbound reference
  (src/frob/process/_lock.py). Genuinely a fresh split module with one
  anchor; waivable per the bucket-list body's own guidance.
- src/frob/app/_config_external.py:690 -- OPAQUE001, getattr(subprocess,
  ...) with a non-literal name; resolve statically if a small change,
  else waive with a real justification.
- src/frob/strata/_models.py::Growth.period_seconds -- TEST001, public
  with no unit test; add a minimal test + frob:tests directive.

OUT OF SCOPE (owned by another series): PERF003 at
src/frob/refactor/_scan.py:772 -- refactor/** belongs to another
series per fleet discipline; not touched here.

Evidence: `timeout 540 uv run frob check --only coverage` for the
_capacity.py COV007 findings; targeted checks for REF002/OPAQUE001/
TEST001 (gate families: refs, opaque, test).


frob:no-behavior-change reason="doc-anchor dedup, waiver comments, and a new test for pre-existing behavior -- no runtime logic changed"