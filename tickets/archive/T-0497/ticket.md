---
id: T-0497
title: 'strata audit G6/G8-G12: default view coverage, THREAT005 KeyError risk, native-staleness
  mtime-only, LATENCY dead metric, per-repo BenignCapability allowlist'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/
- tests/unit/strata/test_threat.py
- tests/unit/test_claims_and_store_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: test coverage for the src/frob/strata/ G8/G11 fixes lives in these test
    files
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_claims_and_store_batch6.py
  reason: test coverage for the src/frob/strata/ G8/G11 fixes lives in these test
    files
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_effect_on_a_file_absent_from_owner_does_not_crash
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_latency_on_a_real_flow_is_refused_not_silently_refuted
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_latency_unknown_flow_fails_closed
designated_repro_test: null
threat: null
component: null
---
docs/audits/strata.md G6+G8-G12 (MEDIUM/LOW), from T-0401, grouped as smaller/lower-severity items for one dispatchable ticket (split further if a single agent finds the combined scope too broad): G6 DEFAULT_SECURITY_VIEWS is only owasp-top-10 (8 CWEs), cwe-top-25 is not a default -- a default frob sys audit proves exhaustiveness over 8 weaknesses and reports proved (_audit.py:109, _threat.py:653). G8 THREAT005 indexes binding.owner[effect.file] (_threat.py:1474) -- if extract_effects ever yields a FOREIGN file this KeyErrors (crash, not fail-closed); verify/harden. G9 native staleness is mtime-only (_native_staleness.py:89,160) -- a touch defeats it; consider a content digest. G10 FactBase.reachable/worst_age/propagated_demand (native Rust kernels) are trusted un-audited from Python; add differential/property tests against a pure-Python reference. G11 _eval_bound_latency_or_size (_claims.py:564) hardcodes declared to flow.size when metric is LATENCY -- LATENCY bounds can NEVER prove, always refute-as-missing; either support it or error instead of masquerading as a refutation. G12 load_repo_benign_capabilities (_threat.py:290) lets a consuming repo excuse ANY capability kind via frob.toml with just a reason string, no allowlist of excusable kinds.