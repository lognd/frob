---
id: T-2311
title: 'DOC006: repair remaining docs/modules/tickets-*.md pointers (tickets.md-adjacent
  contended family)'
state: in-progress
kind: docs
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-data-storage.md
- docs/modules/tickets-landing.md
- docs/modules/tickets-lifecycle.md
- docs/modules/tickets-verify-sweep.md
evidence_scope:
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_docptr_gate.py::TestDoc006Symbol::test_real_symbol_passes
- tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Residue from T-2135. 10 DOC006 findings remain in the docs/modules/tickets-*.md family (docs/modules/tickets-data-storage.md:189,927; docs/modules/tickets-landing.md:173,527,1460,1466,1603; docs/modules/tickets-lifecycle.md:435,450; docs/modules/tickets-verify-sweep.md:524), deliberately NOT fixed by T-2135 -- these files are the same tickets.md-adjacent contended family T-2135's own ticket body flagged (see T-1899/T-1952/T-1996/T-1973/T-1860, all queued against docs/modules/tickets.md itself), and this ticket's coordinator brief explicitly warned against locking files four other agents need. Coordinate scope before starting; several findings are the same shape T-2135 already fixed elsewhere (frob sys sync-interface / frob.strata._sync_interface -- deleted, needs a frob:waive DOC006 like docs/guides/agent-playbook.md and docs/modules/strata.md got; frob worktree release-lease / frob worktree remove -- verify whether these subcommands are real-but-invisible-to-argparse like frob refactor/release publish, or genuinely renamed/removed and need a text fix; #tick003 and #git-merge-driver are dead doc anchors needing the real target heading found; --force on frob worktree sweep and xdist/plugin.py need direct verification against current CLI/tree).