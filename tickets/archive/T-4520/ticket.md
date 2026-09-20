---
id: T-4520
title: generate the explore/quality/design/ops group parsers from the flat parsers
  so they cannot diverge (design sys mirrors 4 of sys's 9 subverbs today)
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: high
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_design.py
- src/frob/_cli_parsers/_ops.py
- src/frob/_cli_parsers/_quality.py
- src/frob/_cli_parsers/_explore.py
- src/frob/_cli_parsers/_root.py
- docs/design/cli-regrouping.md
- tests/unit/test_cli_group_parity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_cli_group_parity.py::TestDesignGroupParity::test_sys_carries_every_flat_subverb
- tests/unit/test_cli_group_parity.py::TestDesignGroupParity::test_full_member_matches_its_flat_twin
- tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_process_reap_has_a_flat_twin
designated_repro_test: null
acceptance:
- text: GIVEN a subverb or flag added to a flat verb (sys, graph, registry, release,
    natives, perf, check, ...) WHEN the group parser is built THEN it appears under
    its group with identical help, flags and dispatch, without any edit to the group
    module, proven by a parity test that walks _build_parser and compares every group
    leaf to its flat twin
  evidence:
  - tests/unit/test_cli_group_parity.py::TestDesignGroupParity::test_sys_carries_every_flat_subverb
- text: GIVEN frob design sys capacity WHEN invoked THEN it behaves identically to
    frob sys capacity, and ops process reap and explore docs-search (the two group-only
    leaves) get flat twins so the mapping is total
  evidence:
  - tests/unit/test_cli_group_parity.py::TestDesignGroupParity::test_full_member_matches_its_flat_twin
- text: 'GIVEN docs/design/cli-regrouping.md WHEN read THEN it records the owner decision
    of 2026-09-16: groups are kept for approachability and are DERIVED from the flat
    parsers, never hand-mirrored'
  evidence:
  - tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_process_reap_has_a_flat_twin
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16 (CLI surface audit, parser tree introspected via _root._build_parser): 47 top-level verbs, 218 subverbs; 30 subverbs are verbatim duplicates created by the explore/quality/design/ops groups (T-1567/1568/1569/1238) as SEPARATE ArgumentParser objects. Usage: sys audit 266 doc / 28 commit refs vs design sys audit 0 / 0; natives build 121/4 vs ops natives build 0/0; release stamp 120/7 vs ops release stamp 0/0; 19 group leaves have zero references anywhere. docs/design/cli-regrouping.md:117-127 declares the flat verbs PERMANENT aliases (T-0580/T-0802 rescinded a sunset). The groups are the unused half. Divergence bug: sys has plan export doc audit trace threats capacity shrink init; design sys has only the first four (_design.py:57-58 wires two of the sys populate helpers). OWNER DECISION 2026-09-16: keep the groups (approachable CLI) and GENERATE them from the flat parser definitions (option b); do not delete. Also: 7 self-hosting verbs (sync-skills, claude, natives, doctor, whereis, fleet, deploy) could be hidden from the top-level --help listing via _GroupedHelpFormatter (_root.py:287) rather than re-nested.