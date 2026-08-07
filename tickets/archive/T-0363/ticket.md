---
id: T-0363
title: 'perf: fix PERF004 sorted-in-loop (8 unwaived) and re-audit existing waivers'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_three_member_group_folds_to_one_shared_skeleton
designated_repro_test: null
threat: null
component: null
---
T-0204 family 5: PERF004 sorted-in-loop has 8 unwaived findings -- fix or waive with reason. Additionally re-verify every existing perf frob:waive still holds now that T-0161's heuristic fixes have landed (waivers written against the old heuristic may no longer be accurate or may now be fixable). Acceptance: 0 unwaived PERF004 findings; every existing perf waiver re-verified and still justified (or fixed and waiver removed); honest summary line.