---
id: T-0511
title: 'strata audit G12: restrict load_repo_benign_capabilities to genuinely excusable
  kinds'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- tests/unit/strata/test_threat.py
- docs/guides/extending/benign-capabilities.md
- docs/strata/threat.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/guides/extending/benign-capabilities.md
  reason: load_repo_benign_capabilities's frob.toml shape gained a mandatory family
    field; both frob:doc-anchored docs describing that shape need updating to avoid
    DRIFT001
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/strata/threat.md
  reason: load_repo_benign_capabilities's frob.toml shape gained a mandatory family
    field; both frob:doc-anchored docs describing that shape need updating to avoid
    DRIFT001
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_missing_family_is_malformed
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_unrecognized_family_value_is_malformed
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_excuse_already_classified_in_named_security_family_is_rejected
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_excuse_already_classified_in_named_quality_family_is_rejected
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_client_storage_excused_for_quality_only_stays_accepted
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_client_storage_excused_for_security_family_is_rejected
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_repo_declared_excuse_resolves_threat002
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_declared_entry_is_loaded
designated_repro_test: null
threat: null
component: null
---
Split from T-0497 (attempted and REVERTED inside that ticket -- a naive 'reject any kind already in CWE_CATALOG union QUALITY_CATALOG' fix breaks the legitimate T-0017 cross-family excuse pattern: e.g. client_storage IS catalogued under CWE_CATALOG (CWE-922/312) but has NO QUALITY_CATALOG entry, so excusing it for the QUALITY loop specifically is a real, load-bearing use case test_repo_declared_excuse_resolves_threat002 already covers -- rejecting ANY catalogued-in-either-family kind would break that). docs/audits/strata.md finding G12: load_repo_benign_capabilities lets a consuming repo excuse ANY capability kind string via frob.toml with just a reason, no allowlist -- currently functionally inert against a truly dangerous excuse ONLY because every consuming call site (check_capability_completeness, check_effect_completeness) independently guards 'if kind not in known and kind not in excused', so an excuse for an already-catalogued-in-THAT-family kind is already a structural no-op -- but that safety property lives in the CALLERS, not in load_repo_benign_capabilities itself, and is not verified/enforced at load time. Needs a fix that is precise about WHICH catalog (CWE_CATALOG vs QUALITY_CATALOG, not their union) an excuse would apply against, since the same kind can be legitimately excusable in one family and illegitimately excusable in the other -- likely needs a per-family scoping mechanism on repo-declared excuses (mirroring DEFAULT_BENIGN_CAPABILITIES' own per-family commentary), not a single flat kind allowlist. Counterexample-first: prove client_storage-for-quality-only stays excusable after the fix (regression guard) AND prove a genuinely both-families-catalogued kind (or a kind catalogued in the SAME family the excuse targets) is rejected.