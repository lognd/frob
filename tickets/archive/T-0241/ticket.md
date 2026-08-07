---
id: T-0241
title: 'ticket scope parsing: comma-joined strings match nothing, dir/ prefixes dont
  glob, ledger not implicit'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- tests/**
- docs/modules/tickets.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestScopeMatching::test_comma_joined_entry_splits
- tests/test_tickets.py::TestScopeMatching::test_comma_joined_entry_matches_split_paths
- tests/test_tickets.py::TestScopeMatching::test_dir_prefix_globs_recursively
- tests/test_tickets.py::TestScopeMatching::test_ledger_always_in_scope
- tests/test_tickets.py::TestScopeMatching::test_new_ticket_normalizes_comma_joined_scope
- tests/test_gates.py::TestScopePrework::test_scope001_comma_joined_entry_splits_and_matches
- tests/test_gates.py::TestScopePrework::test_scope001_dir_prefix_globs_recursively
- tests/test_gates.py::TestScopePrework::test_scope001_ledger_implicitly_in_scope
designated_repro_test: null
threat: null
component: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH correctness -- same class as T-0181 round-1 incident): a scope entry 'a/,b/,c/' is treated as ONE fnmatch glob matching nothing -- SCOPE001 fired on every touched file and prior sweeps recorded against ZERO files (digest sha256 of empty; dup/xref vacuous pass). Also 'design/' does not match (needs design/**), and tickets.md itself is flagged out-of-scope though frob edits it on every ticket op. Fix: reject or split comma-joined entries at frob ticket new (loud validation), treat dir/ as dir/**, make tickets.md implicitly in-scope for every ticket. Regression tests for all three.