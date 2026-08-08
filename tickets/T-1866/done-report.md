## Done report

Promoted T-1645's WARN-only over-broad-scope nudge to a hard refusal at
frob.app.ticket_runner._lifecycle._refuse_over_broad_scope_on_start,
called after the already-in-progress check and before the transition to
IN_PROGRESS (before the lease is taken, not after). Adds no new
mechanism: reuses large_glob_warnings/scope_breadth_context unchanged
(T-0453 -- decides "mega-glob" from what a glob MATCHES, never the
literal `**` in its spelling) and reuses frob ticket scope-ack
(ticket.scope_breadth_ack, T-1484) wholesale as the escape hatch. A
QUEUED ticket is never checked here by construction -- start always
transitions out of queued/planned.

T-1866's own declared scope named src/frob/tickets/_scope_breadth.py,
which does not exist; the real breadth machinery lives in
src/frob/tickets/_doable.py. Swapped via `frob ticket scope --remove/
--add --reason-file` before touching code.

Renamed test_start_warns_on_over_broad_scope to
test_start_refuses_over_broad_scope (behavior changed from warn to
refuse) and added test_start_over_broad_scope_ack_bypasses_refusal.
T-1645's own Done report cited the renamed test as evidence for its own
claim; rebound via `frob ticket evidence T-1645 --replace ... --reason
... --archived` to the still-valid ack-bypass test covering the same
code path, so T-1645 stays evidenced against real code instead of a
deleted test name -- disclosed here rather than silently mutating a
closed ticket's evidence.

No CLI verb exists to amend a filed ticket's description/body prose
(new/scope/scope-ack/accept/done-report are all append-only or
structured-field channels) -- the coordinator's corrected 39-of-72
census (independently re-measured here via scope_breadth_context/
large_glob_warnings against the live queue) is recorded in
docs/modules/tickets.md's own T-1866 section instead of hand-edited into
tickets.md's filed body, and that limitation is called out explicitly in
the new doc section rather than silently worked around with a raw edit.
The breakdown-by-glob numbers in the doc differ from the originally
filed ticket's own table because the queue has moved under concurrent
dispatch since filing -- both measurements are point-in-time, and the
doc section says so.

Filed: none -- no unfinished remainder disclosed by this ticket itself.

### Changed
```
 tickets/T-1866/ticket.md         |  40 +++++++++++-
 tickets/archive/T-1645/ticket.md | 127 ++++++++++++++++++++++++++++++++++++++-
 2 files changed, 163 insertions(+), 4 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 1087 warning(s), 743 waived
- error-findings: none (measured, zero errors)
