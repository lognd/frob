---
id: T-1586
title: 'test isolation: scrub inherited FORCE_COLOR/NO_COLOR in conftest'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/conftest.py
- docs/modules/logging.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
should_color honors FORCE_COLOR and NO_COLOR, and a CLI subprocess a test spawns inherits the whole environment. A shell exporting FORCE_COLOR=3 (Claude Code and several CI images do) embeds ANSI escapes in every CLI output a test asserts on: 5 system tests failed here purely from the ambient shell while the same commit passes elsewhere. An autouse conftest fixture now deletes both per test (delete, not force NO_COLOR, so color-path tests can still monkeypatch either one). Needs a regression test asserting a spawned CLI produces escape-free output with FORCE_COLOR set in the parent env.