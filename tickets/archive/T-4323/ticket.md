---
id: T-4323
title: Land-path auto-apply for LANDFMT001 ruff format drift
state: done
kind: feature
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/_land_format.py
- tests/test_ticket_work_and_land_finish.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_land_format.py
  reason: T-4323's apply half touches _land_format.py's own module docstring/frob:todo,
    its dedicated absorption test suite, and the LANDFMT001 doc section it changes
    the design decision of
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: T-4323's apply half touches _land_format.py's own module docstring/frob:todo,
    its dedicated absorption test suite, and the LANDFMT001 doc section it changes
    the design decision of
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/gates.md
  reason: T-4323's apply half touches _land_format.py's own module docstring/frob:todo,
    its dedicated absorption test suite, and the LANDFMT001 doc section it changes
    the design decision of
  actor: logan
  at: '2026-09-08'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_ruff_format_half_rewrites_a_touched_drifted_file
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_ruff_format_half_leaves_an_out_of_scope_drifted_file_untouched
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_ruff_format_half_is_silent_on_a_clean_touched_file
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_ruff_format_half_leaves_the_file_alone_when_ruff_itself_fails
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4298's own module (src/frob/gates/_land_format.py) records a
frob:todo deferring the APPLY half of its design: REFUSE-vs-APPLY.
LANDFMT001 currently only refuses on ruff-format drift in a land's
touched Python files; it does not absorb-fix it the way
_fmt_pre_land_step already does for frob: directive line-wrapping.

T-4298's ticket deliberately left this out because
src/frob/app/ticket_runner/_land_cmd.py and _land.py carried a live
in-progress lease from T-4281 at the time T-4298 was scoped. T-4281
has since closed (done), so that lease is free.

The follow-up: extend _absorb_pre_land_fixes (or the equivalent
pre-land absorption step in _land_cmd.py) with a ruff format
on-touched-set step next to its existing frob fmt one, so a land
REWRITES LANDFMT001's drift instead of refusing on it, matching this
project's existing Tier-A auto-fix posture. See
src/frob/gates/_land_format.py's module docstring and its frob:todo
directive (originally bound to T-4298, rebound to this ticket by
T-4316) for the full design reasoning.