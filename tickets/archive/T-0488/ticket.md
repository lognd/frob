---
id: T-0488
title: 'release: bump version + CHANGELOG entry for T-0263 KRB001-004 API'
state: dropped
kind: docs
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Dropped (2026-07-21): absorbed -- REL001 satisfied by the coordinator landing pass (version 0.36.0, frob release stamp run at land; frob release check reports OK).

T-0263 added public API (KrbMovementViolation, evaluate_krb_movement_waived, evaluate_unconstrained_delegation, evaluate_roastable_spn, evaluate_constrained_delegation_blast_radius, evaluate_cross_realm_containment, KRB_MOVEMENT_CATALOG/_OUT_OF_SCOPE/_VIEWS, KRB_MULTI_INSTANCE_WAIVER_FAMILIES, build_compromised_krb_scenario) to frob.strata, which frob check's REL001 gate flags as a minor API change needing a version bump (>= 0.36.0) plus a CHANGELOG.md entry and frob release stamp. T-0263's own scope glob does not include pyproject.toml/CHANGELOG.md/.frob-release.json, so this is filed as separate follow-on release-management work rather than silently widening T-0263's scope.