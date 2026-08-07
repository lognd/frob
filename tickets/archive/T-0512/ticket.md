---
id: T-0512
title: 'strata audit G6: make cwe-top-25 a default security view alongside owasp-top-10'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_audit.py
- src/frob/strata/_threat.py
- tests/unit/strata/test_audit.py
- docs/strata/threat.md
- src/frob/app/sys_runner.py
- tests/system/test_cli_sys_audit.py
- .frob-release.json
- CHANGELOG.md
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/sys_runner.py
  reason: the PROVED summary line frob sys audit prints must LOUDLY disclose narrower_than_baseline
    (the fix direction chosen for G6), and its integration test coverage lives in
    tests/integration
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/integration
  reason: the PROVED summary line frob sys audit prints must LOUDLY disclose narrower_than_baseline
    (the fix direction chosen for G6), and its integration test coverage lives in
    tests/integration
  actor: logan
  at: '2026-07-21'
- op: remove
  glob: tests/integration
  reason: narrowing to the actual CLI test file that exercises _print_audit_report;
    tests/integration had no relevant coverage
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/system/test_cli_sys_audit.py
  reason: narrowing to the actual CLI test file that exercises _print_audit_report;
    tests/integration had no relevant coverage
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: main advanced past T-0510's version bump during merge; re-resolving to next
    free version (0.57.0) after main's 0.56.0 tip requires touching these release
    files again
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: main advanced past T-0510's version bump during merge; re-resolving to next
    free version (0.57.0) after main's 0.56.0 tip requires touching these release
    files again
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: main advanced past T-0510's version bump during merge; re-resolving to next
    free version (0.57.0) after main's 0.56.0 tip requires touching these release
    files again
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: main advanced past T-0510's version bump during merge; re-resolving to next
    free version (0.57.0) after main's 0.56.0 tip requires touching these release
    files again
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_default_run_discloses_narrower_than_baseline
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_explicit_full_security_views_clears_the_disclosure
- tests/unit/strata/test_audit.py::TestGroupGaps::test_group_gaps_by_view
designated_repro_test: null
threat: null
component: null
---
Split from T-0497 (too large/architecturally entangled to rush inside that ticket's remaining budget). docs/audits/strata.md finding G6: DEFAULT_SECURITY_VIEWS = tuple(VIEWS) only ever contains 'owasp-top-10' (8 CWEs, CWE_CATALOG) -- cwe-top-25 (CWE_TOP_25_VIEWS, needs the COMBINED CWE_CATALOG+CWE_TOP_25_CATALOG per _threat.py's own module docstring rationale) is never included in a default frob sys audit run. A default audit therefore proves exhaustiveness and reports PROVED against only 8 weaknesses, not the full baseline the repo's catalogs define, without disclosing the narrower scope anywhere visible to the caller. Fix direction: either fold cwe-top-25 into a genuinely default multi-view audit run (wiring the combined catalog through _audit.py's default-view plumbing and sys_runner's caller), or make the narrower-than-full-baseline scope an explicit, loud disclosure in the audit's own PROVED report text instead of a silent omission. Counterexample-first: a default audit run today reports PROVED with zero mention that cwe-top-25 was never checked; the fix must make that either not true (genuinely checked) or not silent (disclosed).