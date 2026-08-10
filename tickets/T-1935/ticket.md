---
id: T-1935
title: Rapid post-land sweep undercounts new-error identities (T-1923 said 6, measured
  19)
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-1923 (post-land sweep regression from T-1916).
T-1923's own ticket body, filed by the deferred rapid-profile post-land
sweep, reported "6 new error(s) (COV003, F401)". A full unscoped
measurement of the same two gate families
(`uv run frob check --only coverage --only ruff`) on the exact same
commit found 19: 18 COV003 (5 archived tickets' evidence ids, all
pointing at a test file T-1916 deleted) + 1 F401, not 6.

The rolling baseline the sweep persists (`rapid-debt.jsonl` /
`.frob/rapid-sweep` mechanics, T-1684) evidently records only whichever
new-error IDENTITIES it happens to observe first per (rule, file) pair
rather than every distinct finding -- in this case it looks like it
recorded one COV003 per distinct FILE (5 archived ticket files) plus
something that summed to 6, undercounting the true per-finding count
(18 distinct evidence ids across those 5 files) by roughly 3x. This
matters because a ticket filed off the sweep's own undercount can look
"smaller" than the real fix, and an agent trusting the ticket body's
count without re-measuring (exactly the failure mode section 6c of the
agent playbook warns about, generalized to sweep-authored tickets, not
just human-filed ones) would under-scope its own verification.

Investigate whether the rolling-baseline sweep is meant to count
per-(rule, file) IDENTITIES (in which case 6 for T-1923's shape -- 5
files x COV003 plus 1 F401 file -- might be intentional and the ticket
body's parenthetical "N new error(s)" phrasing is simply misleading
about what N counts) or per-finding (in which case it under-recorded
and should read 19). Either fix the counting logic or fix the ticket
body's phrasing so "N new error(s)" means what a reader would assume it
means. Not fixed as part of T-1923 itself -- that ticket's scope was
the 5 archived tickets plus `_fix_engine_sync.py`, not the sweep
counting mechanism.
