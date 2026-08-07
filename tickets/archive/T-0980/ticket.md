---
id: T-0980
title: Burn down remaining ARCH102 god-module findings (11) and promote
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gitio.py
- src/frob/graph/__init__.py
- src/frob/graph/cache.py
- src/frob/lang/__init__.py
- src/frob/perf/_sketch_store.py
- src/frob/render/_elements.py
- src/frob/stats/_sketch.py
- src/frob/strata/_sysdoc.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_models.py
- frob.toml
- docs/audits/gates-quality.md
- tests/unit/test_arch_srp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_arch_srp.py
  reason: covering test for check_god_module/ARCH102 mechanics that all 11 module-level
    frob:waive ARCH102 additions and the frob.toml promotion depend on; no new symbols
    were added in this ticket's own scope files (waivers/config only), so route-2
    evidence binding (test file directly in scope) is used per the docs-only-ticket
    convention
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_arch_srp.py::TestGodModule::test_unrelated_export_clusters_trigger_god_module
- tests/unit/test_arch_srp.py::TestGodModule::test_related_exports_do_not_trigger_god_module
designated_repro_test: null
threat: null
component: null
---
T-0977 fixed ARCH102's clustering heuristic's most severe unsoundness (a
module of many zero-method / pure-data classes, e.g. a conventional
_models.py, was always maximally fragmented and false-fired regardless of
real cohesion -- data-only classes are now excluded from the export/cluster
count in frob.arch._srp._export_name_and_prefix). That dropped live
findings from 23 to 11 (measured via chunked frob check --only
gates-native --json, 2026-07-27).

The remaining 11 are genuine module-level SRP candidates:
gates/__init__.py (302 exports/3 clusters), tickets/__init__.py (111/7),
graph/__init__.py, graph/cache.py, gitio.py, lang/__init__.py,
perf/_sketch_store.py, render/_elements.py, stats/_sketch.py,
strata/_sysdoc.py, tickets/_models.py.

Burning these down means either a real module split or an honest
per-module frob:waive ARCH102 (bind the waiver to the bare file path,
since ARCH102 findings carry no symref -- module-level only). Promote
[gates.severity] ARCH102 to error once at zero live unwaived findings,
mirroring ARCH001/ARCH101/ARCH103's precedent.