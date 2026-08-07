---
id: T-0003
title: 'REL001 release gate: semver-correct version bump from graph digests'
state: dropped
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Public sig digests changed vs the last release tag must require a version bump of the right class (semver, mechanically derived from the graph); frob gitlog drafts the changelog from conventional commits (release-manager role). Phase 9 (0.2.x).

Delivered under T-0035.