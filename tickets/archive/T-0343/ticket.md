---
id: T-0343
title: 'exhaustiveness drift-lock: corpus DENOMINATOR MANIFEST -> registered-check
  coverage meta-test (fail until EVERYTHING is addressed or reasoned-deferred)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/gates/**
- src/frob/arch/**
- tests/**
- docs/design/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_undispositioned_entry_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes
- tests/test_registry_exhaustiveness.py::TestDisposition::test_deferred_to_closed_ticket_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_deferred_to_missing_ticket_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_deferred_to_open_ticket_passes
- tests/test_registry_exhaustiveness.py::TestDisposition::test_fully_dispositioned_fixture_passes
- tests/test_registry_exhaustiveness.py::TestDisposition::test_bare_addressed_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_duplicate_of_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_out_of_scope_no_reason_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_severity_is_error
- tests/test_registry_exhaustiveness.py::TestTotalDrift::test_total_mismatch_fails
- tests/test_registry_exhaustiveness.py::TestTotalDrift::test_split_entries_key_total_checked
- tests/test_registry_exhaustiveness.py::TestTotalDrift::test_no_declared_total_not_checked
- tests/test_registry_exhaustiveness.py::TestSplitReconciliation::test_documented_split_with_empty_cross_refs_fails
- tests/test_registry_exhaustiveness.py::TestSplitReconciliation::test_documented_split_with_cross_refs_passes
- tests/test_registry_exhaustiveness.py::TestMissingDir::test_missing_registry_dir_returns_empty
designated_repro_test: null
acceptance:
- text: given each design corpus (architecture-check-catalog, design-pattern-catalog,
    design-pattern-traps-corpus, system-design-corpus, capability-evasion-taxonomy)
    exposes a machine-readable DENOMINATOR MANIFEST (stable id + checkability tag
    per entry + TOTAL line), when the exhaustiveness meta-test runs, then EVERY manifest
    entry must map to >=1 registered check/recommender-rule/obligation OR carry an
    explicit reasoned deferral (advisory / not-checkable / ticketed) -- the test FAILS
    if any entry is both un-addressed and un-deferred
  evidence: []
- text: the mapping is N:M -- many semantic checks may register to one design pattern,
    and one detector (e.g. the single-implementer-interface fingerprint) may cover
    many denominator entries; the test must reconcile counts as (addressed union deferred)
    == TOTAL accounting for N:M, so nothing is silently dropped and nothing is double-counted
    into false completeness
  evidence: []
- text: 'the meta-test is a DRIFT-LOCK like the CVE-catalog / capability-matrix /
    dup-exhaustiveness (T-0199) locks: adding a new corpus entry with no mapping fails
    immediately, and a check whose denominator entry vanishes fails immediately --
    corpus and registry can never silently desync'
  evidence: []
threat: null
component: null
---
User mandate (2026-07-20): 'write exhaustiveness tests (does the total number of entries match the total number expected, accounting for the fact that different semantic patterns might need to be registered to the same design pattern) so that when the ticket gets implemented, it MUST address EVERYTHING that the exhaustive researcher found.' This is the binding mechanism that makes the design corpora (docs/design/*, ~4150 lines, cited) ENFORCEABLE: the arch epic T-0330, strata-systems T-0331, pattern recommender T-0332, sound capability may-analysis T-0339, and conformance totality T-0341 each carry a subset of the corpus denominator; this ticket builds the shared exhaustiveness-drift-lock framework they all use -- a manifest parser + an N:M coverage meta-test + a reasoned-deferral registry -- so no implementing ticket can close while leaving a researched entry unaddressed. Mirrors the existing CVE-fingerprint catalog drift-lock and the T-0199 dup exhaustiveness matrix. The DENOMINATOR MANIFEST format is produced by the corpora themselves (Playwright gap-fill pass appends a '## DENOMINATOR MANIFEST' section with stable ids + TOTAL to each doc).

STRENGTHENED (2026-07-20, user critique 'guarantee tickets address EVERYTHING; no prose-only or split-across-files misses'): T-0343 binds to the UNIFIED REGISTRY built by T-0346 (docs/design/registry/), not the per-doc manifests directly. The meta-test requires EVERY registry entry to carry a DISPOSITION (addressed-by-check <ids> | reasoned-deferral | duplicate-of <id> | out-of-scope(<named-missing-concept>)) -- an entry with disposition 'pending' or missing FAILS. It also consumes registry/RECONCILIATION.md: any prose-only entry (a corpus table row with no registry id) or split-across-files entry (same item, two unlinked ids) is a hard failure. 'seems like spam so I skipped it' is impossible: a bulk-skip leaves entries undispositioned, which fails the lock.

LINCHPIN / ANTI-LIE MANDATE (2026-07-20, user: 'this is exactly the kind of lying frob is meant to detect... how do we prevent this from ever happening again'). ROOT CAUSE of the breach: the docs/design/registry/*.yaml manifests are read by ZERO code (verified: 0 references in src/ + tests/) -- orphaned documentation -- while the corpus campaign was represented as a delivered, enforced 'unified machine-readable registry'. Catalogued != enforced, and no gate was watching the gap. THIS TICKET IS THE PREVENTION and must be built FIRST (every registry-reconciliation ticket T-0384..T-0392 is now blocked_by it). Hard requirements beyond the meta-test above: (1) it is a FAIL-CLOSED GATE wired into `frob check` at ERROR severity (a real Violation family, e.g. REG001), NOT merely a pytest -- so a build cannot go green while a manifest entry is unaccounted; a `--only`-skippable or advisory-only implementation is a REJECT. (2) `enforced_by: <rule-id>` in a disposition must be VERIFIED to name a real, registered gate/rule/check that actually exists in the code (cross-check against the live rule registry) -- you cannot write `enforced_by: SEC999` unless SEC999 fires; a dangling enforcement reference is a hard failure. (3) `deferred: <ticket-id>` must name an OPEN ticket (a deferral pointing at a closed/nonexistent ticket is a lie and fails). (4) out-of-scope dispositions route through Area-2's verified `caught_by` (T-0382). (5) On first turn-on the gate WILL be red for ~2500 undispositioned entries -- that red is the honest current state and MUST NOT be suppressed/waived wholesale; it is driven green only by T-0384..T-0392 doing the real reconciliation. Acceptance additions: `frob check` shows a REG001 (or equivalent) family with per-entry unaccounted findings; a fixture manifest with a dangling `enforced_by`/closed `deferred` fails; adding a catalogued entry with no disposition reds the build immediately.