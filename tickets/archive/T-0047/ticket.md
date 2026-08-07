---
id: T-0047
title: 'strata: provable system-design language (epic)'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/**
- src/frob/strata/**
- strata-core/**
- design/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/unit/strata/test_litmus_audit_hardened.py::TestAuditHardenedGolden::test_proves_clean_in_security_and_quality
designated_repro_test: null
threat: null
component: null
---
Umbrella for the strata language: deny-by-default architecture models, kernel of 6 primitives (Node/Flow/Boundary/Bound/Claim/Scenario), 3-way claim closure (proved/evidenced/assumed), evidence ladder L1-L5, refinement hierarchy, policy forms, work-order compiler. Charter: docs/strata/charter.md. Independent engine (own strata-core PyO3 crate, NOT lithos); lithos is inspiration only.
## Done report

The strata epic: phases 0 through 5 all shipped and reviewed --
kernel + prover (phase 0), surface language + std.trust (1),
std.infra + bounds + policy + boundaries (2), scenarios + crash +
atomic + breach (3), .strata as a frob.lang grammar + code binding +
effects + SYS gates + self-hosting design/frob.strata (4), and
std.secrets/std.deploy/sys plan|doc|audit|export + the full threat
catalog (5, with epic T-0109). frob now models, proves, plans,
audits, and exports its own architecture from a design file checked
like code. Verified at close: full suite green, frob check exit 0.