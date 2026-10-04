+++
id = "01KZCRA1QJA2Y8XGEXB17Y63PH"
title = "Re-home a dangling WIRE001 follow_up citation off T-1743"
type = "docs"
category = "triage"
priority = "low"
reporter = "human"
created = "2026-08-07T00:00:00Z"
updated = "2026-08-07T00:00:01Z"
aliases = ["T-1778"]
labels = ["milestone:1.0.0", "v1-cluster:F1"]
scope = ["tests/unit/test_land_finish_guard.py"]
+++

tests/unit/test_land_finish_guard.py:70's WIRE001 waiver cites follow_up=T-1743, which is closing -- re-point to this ticket instead so the waiver keeps a live tracker.

## Failure log
- 2026-08-08 attempt 1: This ticket's re-point work is already on main; it now anchors its own WIRE001 waiver (follow_up=T-1778) and must stay non-terminal forever per T-1856 -- recording as a fail attempt (not a real work failure) is the only existing mechanism land() has to publish a non-terminal ledger record; see T-1868 filed for the missing anchor skip-close path
