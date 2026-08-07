---
id: T-0108
title: SCOPE001 flags files already committed by earlier tickets on the same branch
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestScopePrework::test_scope001_exempts_file_committed_by_earlier_ticket
- tests/test_gates.py::TestScopePrework::test_scope001_still_flags_uncommitted_out_of_scope_edit
- tests/test_gates.py::TestScopePrework::test_scope001_does_not_exempt_when_referenced_ticket_lacks_scope
designated_repro_test: null
threat: null
component: null
---
Discovered while batching T-0102/T-0095/T-0101 on one branch with per-ticket commits: scope_gate diffs unconditionally against --base (default 'main'), so once ticket A commits a change to file X, every later ticket B on the same branch sees X in its diff and gets a false SCOPE001. Session workaround: explicit --base <prior-commit> per invocation -- fragile. Consider defaulting --ticket checks' base to the ticket's own prework-sweep commit. (Renumbered from branch-local T-0105 at merge.)