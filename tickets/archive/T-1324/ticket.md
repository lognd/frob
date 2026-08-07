---
id: T-1324
title: 'docs: correct compliance-corpus.md FROB-CATALOG-ENTRIES count 6 -> 7 (PRIVACY-NOTICE)'
state: done
kind: docs
origin: agent
created: '2026-07-29'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/design/compliance-corpus.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- 'cmd:grep -c ''count: 7'' docs/design/compliance-corpus.md exit=0 sha256=4355a46b19d3'
designated_repro_test: null
acceptance:
- text: GIVEN this ticket closes WHEN docs/design/compliance-corpus.md's FROB-CATALOG-ENTRIES
    manifest row and TOTAL_LEAF_CONTROLS_ENUMERATED are inspected THEN both reflect
    COMPLIANCE_CATALOG's real 7 entries (count 6 -> 7, TOTAL_LEAF_CONTROLS_ENUMERATED
    599 -> 600), matching docs/design/registry/compliance.yaml's already-corrected
    CMPL-FROB-CATALOG-ENTRIES row (T-1250)
  evidence:
  - 'cmd:grep -c ''count: 7'' docs/design/compliance-corpus.md exit=0 sha256=4355a46b19d3'
threat: null
component: null
---
Found while working T-1250: T-1314 added a 7th RegulationEntry (PRIVACY-NOTICE) to COMPLIANCE_CATALOG. T-1250 corrected docs/design/registry/compliance.yaml's CMPL-FROB-CATALOG-ENTRIES leaf_count (6->7) and total_leaf_controls_enumerated (599->600), but docs/design/compliance-corpus.md is the upstream source manifest that row derives from and is out of T-1250's scope (not in its scope globs) -- it still reads count:6 and TOTAL_LEAF_CONTROLS_ENUMERATED:599. No gate currently cross-checks the registry yaml against this corpus doc (confirmed: REG005 only checks declared total: against entries: list length, not leaf_count/corpus consistency), so this is a real but not gate-visible drift.