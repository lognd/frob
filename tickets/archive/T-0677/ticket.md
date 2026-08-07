---
id: T-0677
title: 'registry: system-design-corpus.md manifest-extraction-artifact cleanup (119
  stated vs 105 genuine)'
state: done
kind: docs
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0392
parent: T-0346
tier: ticket
sprint: null
scope:
- docs/design/system-design-corpus.md
- docs/design/registry/system-design.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- 'cmd:test "$(grep -c "^- id: " docs/design/system-design-corpus.md)" = 119 && test
  "$(grep -c "^- id: .*artifact: true" docs/design/system-design-corpus.md)" = 14
  exit=0 sha256=e3b0c44298fc'
designated_repro_test: null
acceptance:
- text: Given system-design-corpus.md after the fix, when its manifest is parsed,
    then TOTAL reflects only genuine entries or artifact rows are machine-distinguishable
    without a hardcoded exclusion list
  evidence:
  - 'cmd:test "$(grep -c "^- id: " docs/design/system-design-corpus.md)" = 119 &&
    test "$(grep -c "^- id: .*artifact: true" docs/design/system-design-corpus.md)"
    = 14 exit=0 sha256=e3b0c44298fc'
threat: null
component: null
---
RECONCILIATION.md finding (d): 14 of the doc's 119 manifest ids are mechanical-extraction artifacts (repeated table-header cells / repeated cell values counted as distinct rows), inflating the doc's own stated TOTAL. Correct the source doc's manifest generation/TOTAL (105 genuine) or add a machine-checkable annotation distinguishing artifact rows from real ones, so future manifest parses do not need an exclusion-list special case. Depends on T-0392 (system-design domain reconciliation) landing first.