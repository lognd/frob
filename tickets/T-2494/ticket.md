---
id: T-2494
title: capability_import_graph_status hardcodes language set, stale after T-2408
state: queued
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
T-2408 added `_imports_typescript`/`_imports_rust`/`_imports_kotlin` walkers
to `src/frob/lang/_extract.py`'s `_IMPORT_WALKERS` table, so
`frob.lang.extract_imports` now has real coverage for these three languages.

`src/frob/lang/_support.py::_capability_import_graph_status` was out of
T-2408's declared scope (`src/frob/lang/_extract.py` only) and still
hardcodes a `{"python", "c", "cpp"}` membership check to decide
IMPLEMENTED vs KNOWN_GAP, rather than reading `_IMPORT_WALKERS`'s own keys
-- so the capability-conformance registry (LANG004,
`derive_capability_registry`) will keep reporting typescript/rust/kotlin's
import_graph capability as KNOWN_GAP (citing T-2408, now closed) even
though the walkers exist and work.

Update `_capability_import_graph_status` to derive its implemented-language
set from `frob.lang._extract._IMPORT_WALKERS` directly (or an equivalent
single source of truth) instead of the hand-maintained membership set, and
retire the now-stale `KNOWN_GAP_TRACKING_TICKETS["T-2408"]` entry once the
registry reflects reality.
