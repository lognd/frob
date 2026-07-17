---
id: T-0003
title: 'REL001 release gate: semver-correct version bump from graph digests'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
evidence: []
attachments: []
---
Public sig digests changed vs the last release tag must require a version bump of the right class (semver, mechanically derived from the graph); frob gitlog drafts the changelog from conventional commits (release-manager role). Phase 9 (0.2.x).