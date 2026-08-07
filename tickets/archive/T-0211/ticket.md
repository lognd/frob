---
id: T-0211
title: selfconform warns '<repo>/src/frob does not exist' in every non-frob repo
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestUnmodeledCodeMissingPackageRoot::test_missing_package_root_produces_no_warning
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (all 3 repos): the warning prints in every sibling repo while self-conformance PROVED still appears; the checks DO run (verified by falsifiability probes) but the stale frob-self path assumption reads as 'this proof is vacuous' -- trust-eroding. The SYS102 unmodeled join is frob-self-specific (_PACKAGE_ROOT); it should detect it is not in the frob repo and skip silently (one DEBUG line), not warn.