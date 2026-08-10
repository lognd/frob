## Done report

Design doc delivered: docs/design/land-checkpoint-durability.md.

Audited every step of frob ticket land's post-commit tail
(_finish_land_after_success, src/frob/app/ticket_runner/_land_cmd.py)
against the two options T-1523's body left open. Finding: the gap is
narrower than "Option A: everything durable" implies -- the post-land
sweep already has its own durability (T-1694's in-flight marker, reused
unchanged) and LAND-PROOF's print is read-only/idempotent, so neither
needs new mechanism. The one real, unmarked, untested-against-a-real-
SIGTERM gap is --finish/--retire-on-proof's two git mutations
(_finish_worktree, _delete_worktree_branch).

Recommended: a narrow land-finish-pending marker (T-1523's own pattern,
one more instance) around just that step, with Option B (a --verify-only
CLI entrypoint) scoped as a later, thin reader of that marker rather than
a competing mechanism -- filed as a follow-up (see Filed below) so it
does not race to define the marker shape independently.

No code changes -- design-only ticket, per its own body's instruction
("needs its own design doc before implementation").

### Changed
```
 tickets/T-1554/ticket.md           | 24 ++++++++++++++++++++---
 tickets/T-1837/done-report.md      | 40 ++++++++++++++++++++++++++++++++++++++
 tickets/T-1837/ticket.md           | 20 ++++++++++++++++++-
 tickets/T-1845/ticket.md | 38 ++++++++++++++++++++++++++++++++++++
 4 files changed, 118 insertions(+), 4 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 4 error(s), 605 warning(s), 739 waived
- error-findings: DOC001@docs/design/land-checkpoint-durability.md, DOCENUM001@docs/modules/gates.md, PRE001@tickets/T-1554, SEC110@.claude/hooks/dispatch-telemetry.py
