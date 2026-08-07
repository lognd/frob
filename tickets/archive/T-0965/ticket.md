---
id: T-0965
title: COV002 scope-coverage grace window missing for same-diff closed ticket
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov002_scope_grace_covers_ticket_created_and_closed_in_same_diff
- tests/test_gates.py::TestCoverageGate::test_cov002_scope_grace_without_same_diff_close_still_fires
- tests/test_gates.py::TestCoverageGate::test_open_scopes_grace_requires_both_root_and_diff
designated_repro_test: null
threat: null
component: null
---
Found while working T-0962 in a worktree that had already closed a prior
ticket (T-0960) earlier in the same session/branch.

`_bound_to_open_ticket` (src/frob/gates/__init__.py) has a same-diff grace
window (T-0214/T-0320/T-0590) for a symbol covered by a DIRECT
`frob:ticket` edge to a ticket that closes to DONE within the same
uncommitted/unlanded diff. But `_cov002_check_symref`'s OTHER coverage
path -- scope-based coverage via `_scope_covers(record.id.path,
open_scopes, active_ticket)` -- has NO equivalent grace: `open_scopes` is
built only from tickets currently in `_OPEN_STATES`
(`_open_scopes(queue)`), so the instant a ticket that covered a whole
file/module by SCOPE (not a per-symbol `frob:ticket` edge) closes to
DONE, every symbol in that scope that lacks its own direct `frob:ticket`
edge starts failing COV002 -- even though the closing ticket's own commit
is still sitting, unlanded, in the very same branch diff against main
that COV002 evaluates.

Concretely: T-0960 added `src/frob/strata/_process_bounds.py` with one
`frob:ticket T-0960` directive on its main entrypoint function only
(the established convention every sibling obligation-family module in
this repo uses -- see `_backpressure.py`/`_interactive_cost.py`, neither
of which annotates every private helper/constant individually). While
T-0960 was open, `_scope_covers` accounted for every other symbol in the
file via T-0960's declared `scope` glob. The moment T-0960 closed (in the
same worktree, before landing to main), `frob check --ticket T-0962`
(a sibling ticket touching unrelated files) started reporting ~20 fresh
COV002 errors against `_process_bounds.py`'s and its test file's symbols
-- a false positive: nothing about those symbols changed, and the
covering ticket's DONE transition is still part of the exact same
unlanded diff COV002 is evaluating, the precise shape T-0214's edge-based
grace window already exists to accept.

Suggested fix: extend `_base_state_permits_grace`/`_ticket_marker_in_diff_
hunk`'s reasoning to the scope-coverage path too -- when computing
`open_scopes` for COV002 purposes, also include a ticket's scope if that
ticket is DONE, its own close transition is inside this diff's `tickets.
md` hunk(s) (`_ticket_marker_in_diff_hunk`), and its base-commit state
permits grace (`_base_state_permits_grace`) -- mirroring
`_bound_to_open_ticket`'s existing edge-based grace exactly, just applied
to `_open_scopes`'s ticket set instead of a single edge target.

Scope: src/frob/gates/__init__.py (`_open_scopes`, `_cov002_check_symref`,
`_scope_covers` call site), tests/test_gates.py (a
TestCoverageGate case mirroring test_cov002_grace_covers_ticket_created_
and_closed_in_same_diff but for scope coverage instead of a direct edge).