---
id: T-draft-6d585d1b
title: register src/frob/agent as a cli-owned module glob in design/frob.strata
state: queued
kind: docs
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
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
- design/frob.strata
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
found while working T-draft-df99eb2d: frob.agent (src/frob/agent/_brief.py, new) is not covered by any design/frob.strata code owner, so SYS003 fires (undeclared cross-component import frob.agent) at its two import sites (src/frob/app/agent_runner.py, tests/unit/agent/test_brief.py). The fix is a one-line addition of "src/frob/agent/**" to the cli node's existing code glob list (design/frob.strata, node cli, the code clause around its 'src/frob/app/**' entry) so frob.agent becomes an intra-component module of cli, matching agent_runner.py's own existing membership -- no new Flow/component needed. Could not do this within T-draft-df99eb2d itself: design/frob.strata was under an active cross-worktree lease held by T-draft-4ad886c1 (frob coord status) at the time, which also touches this same file for its own new frob.coord component -- sequence after that lease clears. T-draft-df99eb2d carries an interim frob:waive SYS003 citing this ticket at both import sites.