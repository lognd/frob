---
id: T-0258
title: 'deploy conformance: script<->manifest bidirectional verification (DEPLOY gates)'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0256
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/deploy/**
- src/frob/gates/**
- src/frob/strata/**
- src/frob/app/**
- tests/**
- docs/**
- tickets.md
- CHANGELOG.md
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/deploy/test_conform.py::TestEvasion::test_bare_word
- tests/unit/deploy/test_conform.py::TestEvasion::test_evasion_fires_through_full_check
- tests/unit/deploy/test_conform.py::TestEvasion::test_env_wrapper
designated_repro_test: null
threat: tampering
component: null
---
T-0254 child 4. Hand edits to deploy scripts must be DETECTABLE through the checker even when someone bypasses regeneration: parse the committed scripts' mutation surface (useradd/groupadd/install/cp/mkdir/chown/chmod/systemctl/rm invocations and their targets -- structured extraction, not naive grep, honoring the generated check-then-apply shapes) and verify bidirectionally against HostManifest: DEPLOY002 = script mutation not declared in the manifest (the red-team-relevant direction: a smuggled extra user/path/unit fails check); DEPLOY003 = manifest entry no mutation implements (incomplete install/uninstall). Fire/discharge litmus incl. a tampered-script fixture. This is the tie that makes the scripts part of the provable architecture rather than artifacts beside it.