---
id: T-2191
title: REDUNDANT_RERUN asserts 'this run could not have produced a different result'
  from the repo tree hash alone, but verbs like claude sync --check read state outside
  the repo and legitimately change verdict
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Reproduced live: ''frob claude sync --check'' reported 1 drifted; ''frob
    claude sync'' then wrote ~/.claude/refs/agent-playbook.md; the next ''frob claude
    sync --check'' emitted REDUNDANT_RERUN claiming ''nothing has changed since --
    this run could not have produced a different result'' and then reported ''6 file(s)
    in sync''. The verdict changed. src/frob/app/telemetry.py:489 keys the rule on
    (subcommand, args_head, tree_hash) where tree_hash covers the REPO tree only,
    while this verb''s inputs live in ~/.claude. This test MUST fail against current
    main.'
  evidence: []
- text: 'Derive the answer from what the verb actually READS, not from a repo-wide
    hash: a verb whose inputs are not covered by tree_hash must be excluded from the
    rule, or the rule must incorporate that verb''s own input digest. Do NOT fix this
    by softening the message wording to ''may not have changed'' -- the value of REDUNDANT_RERUN
    is that it is a definite claim, and a hedged version is noise everyone learns
    to ignore. Do NOT hardcode a name list of exempt subcommands; that rots the moment
    a verb gains an out-of-repo input.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
