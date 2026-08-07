---
id: T-0403
title: 'AUDIT: accounting gates verify truth not existence (docs/audits/gates-accounting.md)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/graph/
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: unit tests for TEST006/REL001 fixes made by this audit ticket
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestTestGate::test_test006_stale_on_new_file_not_in_stamp
- tests/test_gates.py::TestTestGate::test_changelog_mentions_rejects_substring_in_prose
- tests/test_gates.py::TestTestGate::test_changelog_mentions_accepts_real_heading_entry
designated_repro_test: null
threat: null
component: null
---
See docs/audits/gates-accounting.md. HIGH: the one blocking per-symbol test gate clears on a vacuous name-matching test while TEST002/005 are non-blocking WARN; DRIFT001 default sig facet is blind to body/behavior rewrites so a documented lie passes; TS/C/C++ frob:tests edges require NO execution evidence. Plus: coverage/stamp/baseline/prework chain is gitignored-local so CI cannot trust it. RIGHT-WAY fix: strengthen test-presence to reject vacuous tests + make it blocking; DRIFT over body/doc facets not just sig; execution evidence for non-Python; make CI-critical signals trackable. Then re-audit until empty. MED/LOW in the doc.