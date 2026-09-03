---
id: T-3575
title: extend T-3324 land-time selfaudit gate to catch SYS111 ratchet growth and DOC006
  doc-pointer drift
state: done
kind: feature
origin: agent
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_sys.py
- src/frob/tickets/_land_squash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_sys111_finding_in_touched_files_refuses_and_unwinds
- tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_docptr_finding_in_touched_files_refuses_and_unwinds
- tests/gates_suite/test_sys.py::TestSys111FindingsTouching::test_ratchet_trip_in_declaring_file_is_returned
- tests/gates_suite/test_sys.py::TestDocptrFindingsTouching::test_finding_in_touched_doc_is_returned
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3574 root-caused why T-3324's land-time selfaudit gate (selfaudit_findings_touching in src/frob/gates/_sys.py, called from _refuse_if_selfaudit_findings_in_touched_files in src/frob/tickets/_land_squash.py) missed 3 SYS111 ratchet trips + 1 DOC006 stale doc-pointer that only surfaced on the next full-repo CI run (33376126399), not at land time:

1. SYS111 gap: selfaudit_findings_touching filters SELFAUDIT001 findings by a plain substring test of each Violation.message against the land's own touched files. SYS111 ratchet-growth messages ('self-audit family SYS111 node=testsuite: exec via-list on testsuite grew to 235 site(s), above the committed ratchet ceiling of 234') are an AGGREGATE count keyed by design node + capability name, with NO source file path anywhere in the text -- structurally, no diff's touched-files set can ever match this message's substring test, so every land that grows a via-list ratchet is invisible to T-3324's filter regardless of which files it touched. Fixing this needs a different attribution strategy for SYS111 specifically: e.g. re-run the capability via-list scan restricted to (or diffed against) the land's own touched files and compare the site delta directly, rather than message-substring matching.

2. DOC006 gap: selfaudit_findings_touching only evaluates _selfaudit_violations, which covers SYS100-107/SYS2xx/SYS205/REL2xx (SELFAUDIT001 rule family) -- DOC006 (docblocks/docptr gate family) was never in scope for T-3324's land-time check at all, a different gate module entirely (frob.gates._docptr, not frob.gates._sys). Extending coverage means adding a second diff-scoped land-time check for the docptr family (or generalizing _refuse_if_selfaudit_findings_in_touched_files to accept additional gate families), analogous to but structurally separate from the SELFAUDIT001 mechanism.

Both are real design work (a new attribution strategy per family, not a one-line fix) -- T-3574 declined to do this inline (declared scope was the ratchet declarations + doc fix, not a land-gate redesign) and filed this instead per its own body's own escape hatch.
