---
id: T-0798
title: 'dup: verdict cache serves stale results across rule changes (.frob/dup.db
  keyed by content digest only)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- tests/test_dup.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_dup_code_fingerprint_change_invalidates_cached_verdict
- tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_unchanged_dup_code_fingerprint_still_serves_cached_verdict
designated_repro_test: null
acceptance:
- text: GIVEN a dup rule/normalization change WHEN frob check runs the dup gate THEN
    cached verdicts computed under the old rules are invalidated (cache key includes
    a rules/version fingerprint) and results reflect current rules; a test proves
    a rule change flips a cached verdict
  evidence:
  - tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_dup_code_fingerprint_change_invalidates_cached_verdict
  - tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_unchanged_dup_code_fingerprint_still_serves_cached_verdict
threat: null
component: null
---
T-0785 reviewer-mandated filing: during T-0785 the .frob/dup.db verdict cache silently served pre-rule-change results until manually cleared -- a gate-integrity hole (the dup gate can report stale verdicts as current). Key the cache by (content digest, rules fingerprint) or invalidate on frob.dup code-digest change.