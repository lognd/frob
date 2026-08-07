---
id: T-1153
title: 'tickets-archive.md: T-1145''s land reverted T-1143''s parse.rs->parse/mod.rs
  evidence fix (40 occurrences back)'
state: done
kind: docs
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:python3 -c "import sys; t=open('tickets-archive.md',encoding='utf-8').read();
  n=t.count('strata-core/src/parse.rs::'); print('stale-citations:',n); sys.exit(1
  if n else 0)" exit=0 sha256=51847bc6527b
designated_repro_test: null
threat: null
component: null
---
T-1143 fixed the remaining 40 stale `strata-core/src/parse.rs::tests::X`
evidence citations in tickets-archive.md (T-1099's parse.rs -> parse/mod.rs
migration residue), landing clean at ce0d0753 with 0 COV003 violations.

T-1145's land (bc834b95, immediately after T-1143 in main's history)
reintroduced all 40 stale `parse.rs::tests::` occurrences in
tickets-archive.md -- `git show bc834b95 -- tickets-archive.md` shows 40
insertions of the exact `parse.rs::tests::` pattern and 0 removals of it,
a straight revert of T-1143's fix. This looks like T-1145's landing
worktree branched from a `main` before T-1143 merged forward and its own
stale tickets-archive.md snapshot won a merge/land conflict resolution,
per the playbook's "ledger-conflict splice guidance" hazard class
(section 10), applied here to tickets-archive.md rather than tickets.md.

Confirmed present on main right now:
`git show main:tickets-archive.md | grep -c "strata-core/src/parse.rs::tests::"`
-> 40.

Fix: re-apply the same mechanical path-only substitution T-1143 already
verified works (`strata-core/src/parse\.rs::tests::` ->
`strata-core/src/parse/mod.rs::tests::`), re-verify 0 COV003 findings
afterward, and (if feasible) look at whether the tickets-archive.md
merge/land path needs a splice-guard the way tickets.md already has
(frob ticket merge-driver) to prevent this class of regression from
recurring for any future ledger-adjacent file.