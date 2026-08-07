---
id: T-1778
title: Re-home a dangling WIRE001 follow_up citation off T-1743
state: queued
kind: docs
origin: human
created: '2026-08-07'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_land_finish_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
tests/unit/test_land_finish_guard.py:70's WIRE001 waiver cites follow_up=T-1743, which is closing -- re-point to this ticket instead so the waiver keeps a live tracker.