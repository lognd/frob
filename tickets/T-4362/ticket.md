---
id: T-4362
title: SCOPE001 cross-ticket exemption misses a promoted draft's pre-promotion filing
  commit
state: in-progress
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`_commit_exempts_file` (src/frob/gates/__init__.py)'s cross-ticket
SCOPE001 exemption (T-0108/T-3298) reads the ticket id out of a
blamed commit's SUBJECT via `_TICKET_REF_RE = re.compile(r"T-\d{4}")`.
For a ticket filed as a draft (`frob ticket new` on a non-default
branch, `T-draft-<hex>` id) and only later promoted to its real
`T-####` id (`frob ticket promote`), `git blame` on the promoted
ticket's `tickets/T-####/ticket.md` attributes every line to the
ORIGINAL pre-promotion filing commit (`chore(tickets): file
T-draft-<hex> <title>` -- a `git mv` in a later commit does not
retarget blame for lines unchanged since the file's creation), whose
subject names only the draft id, which `_TICKET_REF_RE` cannot match
(no digits). The exemption then falls through to a genuine SCOPE001 on
the promoting ticket's own branch, even though T-3298 explicitly
intended this exact "ticket B filed as a routine side effect of ticket
A's documented out-of-scope-discovery workflow" case to be exempt.

Measured directly this session (T-4353's own worktree): filed a draft
ticket, promoted it to T-4360, then `frob check --ticket T-4353`
still reported `SCOPE001: tickets/T-4360/ticket.md is outside T-4353's
declared scope` -- confirmed via `git blame -L 1,3 --porcelain --
tickets/T-4360/ticket.md`, which names the pre-promotion `chore(tickets):
file T-draft-...` commit, not the `chore(tickets): promote
T-draft-... -> T-4360` commit (whose OWN subject does carry the
matchable `T-4360` ref). Worked around by explicitly adding
`tickets/T-4360/**` to T-4353's own scope rather than fixing the gate.

Fix shape: `_commit_exempts_file`'s ticket-ref search over a commit's
own subject/parent subjects could ALSO check the commit's diff for a
rename from `tickets/T-draft-<hex>/` to `tickets/T-####/` and cross-
reference the draft id against the current ticket's own promotion
history (or a promote commit's subject could carry BOTH ids, e.g.
"chore(tickets): promote T-draft-<hex> (T-####) -> T-####", so a
future blame on either the pre- or post-promotion commit resolves).
Not fixed here: out of T-4353's tests/conftest.py-only scope.
