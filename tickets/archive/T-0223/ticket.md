---
id: T-0223
title: THREAT003 CWE-78 discharge impossible in foreign-less library models
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestLibraryModeForeignlessDischarge::test_foreign_less_library_model_discharges_cwe_78_by_absence
- tests/unit/strata/test_threat.py::TestLibraryModeForeignlessDischarge::test_real_foreign_source_reaching_the_sink_still_fires
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 8 (medium-high): a library repo with no foreign node (feldspar) declaring may exec cannot discharge CWE-78 -- the demanded claim form is NoFlow(foreign src -> node) and no foreign source exists; frob sys plan --apply then mints permanently unclosable tickets (feldspar T-0009/T-0010 left queued as evidence). Add a library-mode discharge form: an argv-confinement assume against the outermost caller, or an explicit no-foreign-sources model-level fact that discharges the foreign-path obligation family with a written reason.