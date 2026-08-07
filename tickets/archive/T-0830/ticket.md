---
id: T-0830
title: 'selfconform: merge _observed_extended_kinds_by_node/_observed_all_kinds_by_node
  into one scan_file_capabilities pass per file (H5)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
designated_repro_test: null
threat: null
component: null
---
T-0582 (perf audit re-measurement) re-verified docs/audits/perf.md's H5
finding against current main: STILL UNFIXED. `_observed_extended_kinds_by_
node` (src/frob/strata/_selfconform.py:296) and `_observed_all_kinds_by_
node` (src/frob/strata/_selfconform.py:319) each independently loop
`_sorted_owned_files(binding)` and call `scan_file_capabilities(path)` on
the SAME files -- two full passes over the owned-file set to compute two
views (the extended-kinds subset, and the `_KIND_MAP`-normalized full set)
of the same underlying capability scan.

Re-verification note (this is NOT the same cost H5 originally described):
T-0414 (landed after the original perf audit, before this ticket) already
generalized `frob.lang`'s per-run content-hash parse memo down to `_parse`
itself, which `raw_tree` (and therefore `scan_file_capabilities`) now goes
through -- so the double CALL no longer means a double PARSE. Measured
directly (T-0582): running `scan_file_capabilities` over every tracked .py
file in this repo shows `frob.lang.parse_cache_stats()` = exactly one miss
per unique (path, content) and the rest hits, confirming H4's "vet bypasses
the memo" concern is RESOLVED for `_parse`/`raw_tree` specifically.

What's still real: `scan_file_capabilities` itself does substantial
non-parse Python work per call (import/binding-aware resolution --
`_python_binding_capabilities`, `_collect_py_candidates`, `_resolve_py_
expr`, `_shadowing_scope` -- an O(candidates * capability-kinds * needles)
substring-match sweep over the resolved call/attribute sites). A full-repo
direct-call profile (592 .py files) spent ~23s of a 32s wall inside exactly
that resolution path, NOT inside parsing. Calling it twice per owned file
(H5's actual remaining cost) roughly doubles that portion. Measured on this
checkout's `frob sys audit` (286 bound files, smaller than the full repo):
6.15s wall end to end; a cProfile pass on `check_self_conformance` shows
`_capability.py`'s walk/visit/any functions as the internal-time dominators
network-wide, consistent with the double-call pattern.

Fix direction (matches perf.md's original H5 fix direction, still valid):
scan each owned file ONCE into `raw = scan_file_capabilities(path)`, then
derive `raw & _EXTENDED_KINDS` for the extended-kinds view and the
`_KIND_MAP`-normalized set for the all-kinds view from that single `raw`
result, instead of two independent full passes. One scan per file, two
cheap derived views.

Not fixed as part of T-0582: `src/frob/strata/_selfconform.py` is outside
T-0582's declared scope (src/frob/vet/, docs/audits/perf.md). This ticket
is the paired fix for H5's "verify... selfconform" mandate. See
docs/audits/perf.md's dated re-measurement section for the full T-0582
measurement table.