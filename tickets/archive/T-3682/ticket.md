---
id: T-3682
title: 'self-gate floor: format src/frob/check/__init__.py (deferred from T-3680)'
state: done
kind: docs
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_true_only_for_the_matching_point
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3680's repo-wide ruff-format sweep excluded this file: reformatting it trips COV001 (FROB_CHECK_STOP_BEFORE_ENV, public, no frob:doc edge) and COV002 (_check_stop_before changed with no frob:ticket edge) own-diff obligations that are pre-existing gaps unrelated to formatting, just newly visible because ruff-format touches the file. Fix: either close those two gaps (add a frob:doc anchor / frob:ticket edge) in the same change as reformatting it, or add the doc/ticket edges first in a small prep ticket, then format.