---
id: T-0539
title: PII011/PII012 warn-pool calibration + burndown (336 findings)
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_pii_structural.py
- src/frob/vet/_capability.py
- tests/test_pii_structural_gate.py
- tickets.md
- tests/integration/test_gitlog.py
- tests/integration/test_interfaces.py
- tests/system/test_cli_gitlog.py
- tests/unit/test_app_runners.py
- tests/unit/test_app_runners_batch5.py
- tests/unit/test_gitlog.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_gitlog.py
  reason: PII011's remaining 9 non-reserved-domain fixture emails (after RFC2606 calibration
    covered 57/66) needed a frob:secret-fake marker at their exact sites in these
    6 test files -- not knowable until the calibrated check ran
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: PII011's remaining 9 non-reserved-domain fixture emails (after RFC2606 calibration
    covered 57/66) needed a frob:secret-fake marker at their exact sites in these
    6 test files -- not knowable until the calibrated check ran
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/system/test_cli_gitlog.py
  reason: PII011's remaining 9 non-reserved-domain fixture emails (after RFC2606 calibration
    covered 57/66) needed a frob:secret-fake marker at their exact sites in these
    6 test files -- not knowable until the calibrated check ran
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_app_runners.py
  reason: PII011's remaining 9 non-reserved-domain fixture emails (after RFC2606 calibration
    covered 57/66) needed a frob:secret-fake marker at their exact sites in these
    6 test files -- not knowable until the calibrated check ran
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_app_runners_batch5.py
  reason: PII011's remaining 9 non-reserved-domain fixture emails (after RFC2606 calibration
    covered 57/66) needed a frob:secret-fake marker at their exact sites in these
    6 test files -- not knowable until the calibrated check ran
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_gitlog.py
  reason: PII011's remaining 9 non-reserved-domain fixture emails (after RFC2606 calibration
    covered 57/66) needed a frob:secret-fake marker at their exact sites in these
    6 test files -- not knowable until the calibrated check ran
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: is_self_pattern_path gained a new suffixes parameter (T-0539 reuse) -- REL001
    requires a version bump + release stamp for the public API change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: is_self_pattern_path gained a new suffixes parameter (T-0539 reuse) -- REL001
    requires a version bump + release stamp for the public API change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: uv.lock's frob package version entry auto-synced with pyproject.toml's 0.59.0
    bump (REL001)
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_pii_structural_gate.py::TestReservedTestDomainEmails::test_example_com_does_not_fire
- tests/test_pii_structural_gate.py::TestReservedTestDomainEmails::test_lookalike_non_reserved_domain_still_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_frob_directive_comment_does_not_fire
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_ordinary_comment_mentioning_secret_still_fires
- tests/test_pii_structural_gate.py::TestGateIsGreenOnItself::test_corpus_detector_files_produce_no_finding[src/frob/gates/_secrets.py]
- tests/test_pii_structural_gate.py::TestGateIsGreenOnItself::test_own_module_source_produces_no_self_finding
designated_repro_test: null
threat: null
component: null
---
## Description

The pii_structural gate (PII010/PII011/PII012/SEC110) currently carries
~336 warn-pool findings, mostly PII012 (identifier/comment keyword-sweep
suggestions) and PII011 (email-shape), plus a few PII010. Frob is a
static-analysis tool: its own detector sources, pattern tables, registry
corpora, and test fixtures legitimately contain PII-keyword text, which is
expected to dominate the pool -- the same self-match class T-0253's
scan-evasion discriminator (`is_self_pattern_path` in
`src/frob/vet/_capability.py`) already solved for SYS100.

## Plan

1. Bucket the 336 findings by file+rule (`frob check --only pii_structural`
   output) and report the histogram.
2. Calibrate: extend/reuse `is_self_pattern_path`'s discriminator machinery
   (root-identity-gated path-suffix exclusion) to cover
   `_pii_structural.py` itself plus any other dominant detector-definition/
   corpus/fixture false-positive shape found in the histogram -- no second
   implementation of the self-match discriminator.
3. Burn down genuine residual findings: real hits get fixed/annotated in
   code; true-but-intended hits get a `frob:waive` with a specific reason.
   Target 0 unwaived PII011/PII012, or file a follow-up ticket with exact
   counts if the honest remainder exceeds this ticket's budget.