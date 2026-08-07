---
id: T-0424
title: 'REFLEXIVE completeness: frob''s own check-coverage is an exhaustible registry
  + continuous self-audit (so the AUDITOR is not the user)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- docs/audits/
- src/frob/
- frob.toml
- docs/design/registry/
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/
  reason: T-0424's reflexive check-coverage registry is a docs/design/registry/*.yaml
    instance (check-coverage.yaml), same home T-0407 unified; also updates README.md/EXHAUSTIVENESS-GATE.md
    to document the new instance
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 required a version bump (0.60.0 -> 0.61.0) for T-0424's check-coverage.yaml
    addition to REGISTRY_FILES; mechanical release-stamp artifacts
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 required a version bump (0.60.0 -> 0.61.0) for T-0424's check-coverage.yaml
    addition to REGISTRY_FILES; mechanical release-stamp artifacts
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 required a version bump (0.60.0 -> 0.61.0) for T-0424's check-coverage.yaml
    addition to REGISTRY_FILES; mechanical release-stamp artifacts
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 required a version bump (0.60.0 -> 0.61.0) for T-0424's check-coverage.yaml
    addition to REGISTRY_FILES; mechanical release-stamp artifacts
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_is_in_registry_files
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_loads_without_error
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_concern_family_entries_are_deferred_or_handled
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_no_malformed_entries
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_audit_reports_exhausted
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
designated_repro_test: null
threat: null
component: null
---
Root-cause analysis (user, 2026-07-20: "why do I have to keep making these requests?"). Every gap the user caught this session is one of: catalogued-not-enforced, present-not-verified, written-not-wired, done-not-maintained, resolved-looking-but-owed, correct-but-wasteful. Two-layer root: (L1) frob checks that a thing EXISTS, not that it DOES ITS JOB (existence != efficacy) -- it was built to track/account, never to check completeness/truth/efficiency/honesty/maintenance of its own guarantees; (L2) frob has NO check-for-missing-checks: its own coverage (the set of "kinds of badness it enforces") is an un-exhausted, un-enforced registry whose ONLY draining process is the users eyeballs -- so the user IS the adversarial efficacy-auditor frob lacks, and each request adds one entry to an implicit "checks frob should have" list. SYSTEMIC FIX (the session-wide principle turned reflexively on frob itself): (1) make frobs CHECK-COVERAGE a first-class EXHAUSTIBLE REGISTRY (an instance of T-0407) -- a living taxonomy of the correctness/quality/security/perf/UX/maintenance concerns frob should enforce, each dispositioned (implemented gate id | open ticket | out-of-scope+reason); the docs/audits/ findings are its first draft; an exhaustiveness gate reds until every known concern is dispositioned, so GAPS are enumerated and driven to zero by the PROCESS. (2) Move the adversarial efficacy-auditing from the USER to the CONTINUOUS pessimistic auditors: schedule the audit-until-empty loop as a STANDING converging process across all subsystems AND reflexively on frobs own efficacy (does each gate actually catch what it claims, not just exist), so new gaps are found by auditors before the user would notice. (3) The meta-principle already in memory ("every got-away-with is a frob enforcement gap -> file the gate") is the DISPOSITION RULE for this registry. Acceptance: a named check-coverage registry exists with per-concern dispositions; a new un-dispositioned concern reds the exhaustiveness gate; the pessimistic-auditor loop runs on a schedule and its findings auto-file as dispositioned entries; measurably, the user stops being the one who finds the gaps.