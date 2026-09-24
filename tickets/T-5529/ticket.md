---
id: T-5529
title: 'SEC110 burn-down: 13 unmapped os.environ reads (strata effects, gates, hooks,
  tests)'
state: in-progress
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5529
branch: t-5529
scope:
- src/frob/strata/_effects.py
- src/frob/gates/_inv.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: .claude/hooks/pgrep-self-match-guard.py
  reason: T-5440 has a live lease on this file; leaving its SEC110 site (line 117)
    for T-5440 own owner to fix
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: BUG002 needs the opposite-direction check since this is metadata-only
  actor: logan
  at: '2026-09-24'
  old_length: 1394
  new_length: 1523
evidence:
- tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_land_lock_root_sets_env_for_the_in_process_gate_call
- tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_no_land_lock_root_leaves_env_untouched
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found draining CI run 35951365410 (windows-latest self-gate, dev 9e0c89bb19).
Not Windows-specific (SEC110 is a static os.environ-read pattern check;
reproduces on this Linux checkout at the same commit). 13 hits, all from
win-selfgate.txt:

- .claude/hooks/pgrep-self-match-guard.py:117
- src/frob/gates/_inv.py:599
- src/frob/strata/_effects.py:1445
- src/frob/strata/_effects.py:1446
- src/frob/strata/_effects.py:1475
- src/frob/strata/_effects.py:1476
- src/frob/strata/_effects.py:1453
- src/frob/strata/_effects.py:1483
- src/frob/strata/_effects.py:1523
- src/frob/strata/_effects.py:1824
- tests/test_ticket_work_and_land_finish.py:3148
- tests/test_ticket_work_and_land_finish.py:3173
- tests/test_ticket_work_and_land_finish.py:3203

Each reads os.environ.get(...)/os.environ[...] without mapping it to a
declared std.secrets node (T-0082). Fix per site: route through the
repo's config seam where one already exists for that variable, or
`frob:waive SEC110 reason="..."` (one line, naming why this specific var
carries no secret) where the read IS the config seam itself (e.g.
src/frob/strata/_effects.py is very likely the effects-evaluation module
that legitimately reads env vars as part of implementing the std.secrets
mapping/effects system -- verify before waiving wholesale).

frob:tests tests covering the touched sites' env-var handling (bind concrete ids once identified)


frob:no-behavior-change reason="comment-only fix: adds one-line frob:waive SEC110 directives per site, no runtime code changed"