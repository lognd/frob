---
id: T-1576
title: 'frob scaffold: default brand-new repos to profile=rapid'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1575
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/_cli_parsers/**
- docs/**
- tests/**
- src/frob/scaffold/data/**/frob.toml.j2
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/data/**/frob.toml.j2
  reason: 'T-1576: the actual frob.toml scaffold templates live under src/frob/scaffold/data/,
    missing from the ticket''s original scope'
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_scaffold_project.py::test_render_project_all_types_default_to_rapid_profile
designated_repro_test: null
threat: null
component: null
---
Once T-1575 lands profiles, frob scaffold (new-repo init) should write profile = "rapid" into the generated frob.toml -- a brand-new repo is exactly the under-threshold case rapid exists for, and the one-way auto-ratchet upgrades it to standard the moment it grows past the thresholds. Existing repos are untouched: absent key still means standard.