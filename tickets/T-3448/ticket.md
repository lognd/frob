---
id: T-3448
title: '.gitattributes attachment CRLF-suppression glob is too broad: unrelated text
  files escape autocrlf'
state: queued
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .gitattributes
- tests/unit/test_gitattributes_merge.py
- src/frob/tickets/_archive.py
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
MEASURED on GitHub Actions run 33282540898 (ubuntu-latest, HEAD b94cea5d0, 2026-08-30) -- the first run that completed to 100% (20 failures of 12689). This failure is in the cross-platform set (fails on macOS too unless noted). Reproduce locally by node id with -p no:xdist first; if it passes locally, the defect is an environment dependency (git identity, tmp path shape, missing tool, timing) and the fix must make the test hermetic, not skip it.

FAILING: tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_unrelated_text_file_still_gets_autocrlf_conversion
    unrelated file unexpectedly escaped autocrlf conversion -- the attachment glob is too broad
The .gitattributes attachment pattern (ticket attachments must not get autocrlf) matches unrelated text files. Narrow the glob to the attachments directory shape the tickets package actually writes (see src/frob/tickets for the attachment path convention) and keep the must-stay-quiet test for real attachments.
