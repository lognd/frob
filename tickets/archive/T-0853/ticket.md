---
id: T-0853
title: 'done-report: a narrative line consisting exactly of the Done-report heading
  defeats section-end detection'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_models.py
- tests/test_evidence_integrity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_evidence_integrity.py::TestDoneReportHeadingImpersonation::test_lookalike_heading_before_real_report_ignored
- tests/test_evidence_integrity.py::TestDoneReportHeadingImpersonation::test_lookalike_heading_without_changed_marker_not_real
designated_repro_test: null
threat: null
component: null
---
Found landing T-0848 itself: a --why-file narrative containing a line-wrapped quoted phrase that puts the literal heading text at a line start (the line is exactly the Done-report H2) is indistinguishable from the structural repeated-heading boundary that _done_report_section_end (post-T-0848) stops at. Rewriting then truncates the replaceable window mid-narrative and strands the tail as a phantom section (observed: T-0848's own block accumulated 3 heading lines). Fix direction: escape or reflow heading-identical narrative lines at render time (e.g. prefix a zero-width or backslash marker), or make the boundary check require the heading to be followed by the auto-generated Changed/Evidence structure. Coordinator hand-repaired the block this time.