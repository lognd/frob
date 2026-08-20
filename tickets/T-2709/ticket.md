---
id: T-2709
title: Single-mode test coverage for set_body's archive routing (T-2678 successor)
state: queued
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_ticket_store.py
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
T-2678 fixed set_body's archived-ticket write routing and added v2-mode
tests (the mode this repo actually runs, per _store_mode's fresh-repo
default). single mode's branch of _ticket_currently_archived (a full
load_all/load_archive membership check, since single mode has no
per-ticket path to test cheaply) has no direct unit test of its own --
only the v2-mode path was exercised end-to-end. Add a single-mode
fixture test (pin single mode explicitly the way
TestWriteArchivedTicket.test_single_mode_splices_into_archive_file
does) covering set_body against an archived single-mode ticket.
