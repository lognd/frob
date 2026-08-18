---
id: T-2499
title: capability_test_discovery_status hardcodes language set, stale after T-2409
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/_support.py
- tests/test_lang_support.py
- docs/modules/lang.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_lang_support.py
  reason: T-2499's fix needs a regression test in the file that already covers _support.py's
    capability-status helpers, plus the doc anchor its docstring points at
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/lang.md
  reason: T-2499's fix needs a regression test in the file that already covers _support.py's
    capability-status helpers, plus the doc anchor its docstring points at
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/lang.md
  reason: 'AFFECT001: KNOWN_GAP_TRACKING_TICKETS edit needs its own affects-closure
    doc touched'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_kotlin_test_discovery_is_implemented
- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_test_discovery_known_gap_tracks_a_language_absent_from_registry
- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_test_discovery_known_gap_when_registry_entry_is_stale
designated_repro_test: tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_kotlin_test_discovery_is_implemented
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: cbde58e8a94a4b2a17ddb0ab8d7d1b744af9bbb5
---
T-2494 fixed `_capability_import_graph_status` (`src/frob/lang/_support.py`)
to derive its implemented-language set from `frob.lang._extract.
_IMPORT_WALKERS`'s own keys instead of a hardcoded membership literal --
the fix for the exact drift that let a real T-2408 walker keep reporting
KNOWN_GAP because nothing forced the hardcoded set and the real table to
stay in sync.

`_capability_test_discovery_status` (same file) has the identical shape
of bug: it hardcodes `{"python", "rust", "typescript", "c", "cpp"}`
rather than deriving from a real source of truth for "which languages
have a frob.testing collect_*_tests entrypoint". T-2409 added
`collect_kotlin_tests`, so this function's hardcoded set is now ALREADY
stale the same way T-2408 made `_capability_import_graph_status` stale --
kotlin will keep reporting KNOWN_GAP (citing T-2409, now closed) even
though a real collector exists.

Unlike `_capability_import_graph_status`, there is no single dict keyed
by language (`frob.testing` exposes four independent `collect_*_tests`
functions, not a `{language: collector}` table) -- so this fix likely
needs a small `_LANGUAGE_TEST_COLLECTORS: dict[str, Callable]`-shaped
registry introduced in `frob.testing` (or `frob.lang._support` itself)
that both `_capability_test_discovery_status` and any future dispatch
site can read, mirroring `_IMPORT_WALKERS`'s role for the import_graph
capability. Also retire the stale `KNOWN_GAP_TRACKING_TICKETS["T-2409"]`
entry once the registry reflects reality (same T-2494 pattern).