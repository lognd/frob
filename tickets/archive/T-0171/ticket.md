---
id: T-0171
title: THREAT002 fires in quality views lacking the sink taxonomy security views have
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_taxonomy_param_classifies_beyond_the_narrower_catalog
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_security_only_capability_does_not_fire_threat002_in_quality_view
designated_repro_test: null
threat: null
component: null
---
logand.app pilot: THREAT002 (capability kind matches no sink taxonomy entry) fires against quality-family audit views because views do not share the capability-to-CWE mapping the security views carry -- the same signal that hit frob's own T-0150 work (DEFAULT_BENIGN_CAPABILITIES was the frob-repo patch, but external repos hit the raw gap). Decide the principled fix: the sink taxonomy and benign-capability excuse table should be single-sourced across view families, not re-declared per view; a capability genuinely irrelevant to a quality view must not demand a per-repo excuse. Regression-test against a fixture reproducing the pilot's shape.