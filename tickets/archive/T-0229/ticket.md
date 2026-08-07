---
id: T-0229
title: polyglot check-type default silently skips gates then reports clean PASS
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/process/**
- tests/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
- tests/system/test_cli_check.py::TestCheckPolyglot::test_pinned_check_type_reports_skipped_line
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 14 (HIGH -- a repo can look enforced while unenforced): lithos frob check warned 'python checks (gates included) NOT running' then printed [PASS] 0 errors 0 warnings exit 0 -- the obligation system never ran. Fix: run all detected stages by default in polyglot repos; if that is too slow, the unpinned-polyglot state must be a FAILING finding, not a warning contradicted by the PASS line. Regression: polyglot fixture repo, unpinned -> nonzero exit or all stages run.