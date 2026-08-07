---
id: T-0216
title: graph build never names the malformed file
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestMalformedFileVisibility::test_cache_hit_rebuild_still_names_malformed_file
- tests/test_graph.py::TestMalformedFileVisibility::test_fresh_build_names_malformed_file
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private: malformed=1 in build output, persists across cache flush, no way to find WHICH file (no verbosity flag on the subcommand). Print path + parse error at WARN when malformed>0. Trivial but blocks users from fixing their own files.