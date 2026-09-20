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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense ALL_CATALOG union rationale into T-0171 body
  actor: logan
  at: '2026-09-19'
  old_length: 646
  new_length: 2316
evidence:
- tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_taxonomy_param_classifies_beyond_the_narrower_catalog
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_security_only_capability_does_not_fire_threat002_in_quality_view
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
logand.app pilot: THREAT002 (capability kind matches no sink taxonomy entry) fires against quality-family audit views because views do not share the capability-to-CWE mapping the security views carry -- the same signal that hit frob's own T-0150 work (DEFAULT_BENIGN_CAPABILITIES was the frob-repo patch, but external repos hit the raw gap). Decide the principled fix: the sink taxonomy and benign-capability excuse table should be single-sourced across view families, not re-declared per view; a capability genuinely irrelevant to a quality view must not demand a per-repo excuse. Regression-test against a fixture reproducing the pilot's shape.

<!-- narrative-moved:src/frob/strata/_threat_catalog_quality.py:179:T-0171 -->
: T-0171: the union sink taxonomy across EVERY family catalog this module
: ships (`CWE_CATALOG`/`CWE_TOP_25_CATALOG`/`QUALITY_CATALOG`) -- the
: single home `check_capability_completeness` classifies a `may`
: capability kind against, regardless of which family's VIEW is being
: audited. Before this, `_audit.py::_evaluate_family` passed each family's
: OWN narrower catalog to `check_capability_completeness`, so a capability
: kind classified in `CWE_CATALOG` (security) but absent from `QUALITY_
: CATALOG` (e.g. `exec`, `deserialize`, `fetch_url` -- QUALITY_CATALOG has
: no entry mapped to those kinds at all, comment above `DEFAULT_BENIGN_
: CAPABILITIES`) fired THREAT002 against every quality-family view too,
: demanding a per-repo `BenignCapability` excuse for a capability that is
: NOT unclassified -- it is simply irrelevant to the quality family's
: obligation table. Classification ("is this kind a recognized sink
: ANYWHERE in the taxonomy") and relevance ("does THIS family's catalog
: fire an obligation for it") are different questions; THREAT001/THREAT003
: still resolve per-family (a family's obligations are only the entries
: its own catalog declares), but THREAT002 -- "every capability kind is
: classified" (threat.md#the-exhaustiveness-proof-the-point, item 2) --
: was never meant to mean "classified by THIS family's subset of the
: taxonomy"; the taxonomy itself is one thing, split into per-family
: catalogs only for view-membership bookkeeping (docs/strata/
: threat.md#beyond-security-the-anti-pattern-families).
frob:doc docs/strata/threat.md#phasing