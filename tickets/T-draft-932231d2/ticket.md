---
id: T-draft-932231d2
title: 'TICK ledger burn-down: TICK006 phantom filings, TICK015 dead worktree, TICK003
  archive backlog, TICK004 rot'
state: queued
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- tickets.md
- tickets-archive.md
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
Found draining CI run 35951365410 (windows-latest self-gate, dev 9e0c89bb19).
Not Windows-specific (TICK gates read tickets.md/tickets-archive.md content
and wall-clock age; reproduces on this Linux checkout at the same commit).

TICK006 (phantom Done-report filing trail, 11 hits, win-selfgate.txt:7763-7774):
Done reports on T-4030/T-4112/T-4118/T-4240/T-4596/T-4607/T-4659(x2)/T-4710/
T-4713/T-4764 claim a T-draft-* id was filed that resolves to no block in
either ledger file; T-5321's Done report similarly claims T-5448 was filed
but T-5448 doesn't resolve. These are historical draft-loss cases (the
T-0707/T-0615 incident class this rule exists to catch) -- per the
T-5127..T-5129 precedent, each gets read individually: if the cited work
genuinely never got a real ticket, correct the Done report to name reality
or waive TICK006 per-citation with an honest "historical draft-loss,
disclosed" reason; do not silently re-file phantom tickets for years-old
closed work.

TICK015 (1 hit): T-5335 is in-progress but its worktree
(.claude/worktrees/t-5335) no longer exists -- run `frob ticket fail
T-5335` to requeue it via the real verb (never hand-edit).

TICK003 (1 hit): 175 closed tickets sitting un-archived (threshold 10) --
run `frob ticket archive` in a quiet window with no in-flight worktrees.

TICK004 (1 hit relevant to this drain's captured snapshot; the ledger is
live and this count will have drifted by the time this ticket is worked --
re-run `frob check --only gates --files tickets.md` to get the CURRENT
rot list rather than trusting the captured one): rotting queued tickets
past their priority's age threshold -- each gets `frob ticket priority`,
work, or `frob ticket drop`, per ticket, with a reason.

All four sub-rules are live-ledger-state gates: by the time this ticket is
actually worked the specific ids will differ from this capture. Read the
CURRENT gate output, not this list, before acting on any one finding.

frob:tests tests/unit/test_tick_gates.py (or wherever TICK003/004/006/015 evidence lives -- confirm via frob explore)
