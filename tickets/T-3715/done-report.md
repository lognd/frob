## Done report

T-3715: the hook's age-based quarantine verdict (_age_based_verdict) never
read cfg.allow back, contradicting its own block message ("add to
[vet.allow] after review"), and blocked installs even with no [vet] table
present at all (advisory-only mode was logged but the age gate still
blocked and the CLI exited 2). Both confirmed by apollo FROBLEMS.md
2026-09-03.

Fix: a [vet.allow] entry for the package now short-circuits the age gate
(new _allow_listed_verdict helper); with no [vet] table (cfg.present is
False) the age gate now returns an "advisory" verdict (blocked=False,
warns) instead of "quarantine" (blocked=True). check_package's typosquat
branch is unchanged -- that security signal was never the complaint and
stays unconditional.

--check-repro confirmed a genuine pre-fix failure at commit 9bbbce7a9
(test-only commit, committed before the fix commit) for
TestVetAllowNotAgeBlocked.test_allow_listed_package_not_age_blocked.

Filed alongside this ticket (apollo FROBLEMS.md triage): T-3714 (vet hook
overreach/delta vetting -- current source already appears delta-scoped,
root cause not reproduced, needs follow-up investigation), T-3716
([vet.allow] enforced-mode cliff -- NOT fixed here, its root cause is in
src/frob/vet/_scan.py's advisory_only/severity computation, out of this
ticket's _hook.py-scoped ownership per fleet briefing), T-3717 (VET004
false positives), T-3718 (vet source scanner misses .venv), T-3719
(scaffold self-conformance), T-3720 (ROOT001 remedy vs DSL001), T-3721
(TEST006 remedy stale), T-3722 (frob test xdist message), T-3723 (frob
coverage --full), T-3724 (DOC006 scans scope-change reason strings).

Gates: frob check --ticket T-3715 clean except gate:DEPR (DEPR006,
repo-wide deprecated-baseline staleness, pre-existing, unrelated to this
diff's touched set). gate:PRE clean after re-running the pre-work sweep
following the scope widen.

### Changed
```
 src/frob/vet/_hook.py            |  50 ++++++++++++++++--
 tests/vet_suite/test_lockfile.py | 109 +++++++++++++++++++++++++++++++++++++++
 tickets/T-3715/ticket.md         |   6 +++
 3 files changed, 161 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/vet_suite/test_lockfile.py::TestVetAllowNotAgeBlocked::test_allow_listed_package_not_age_blocked` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_lockfile.py::TestVetAllowNotAgeBlocked::test_allow_listed_with_reasons_not_age_blocked` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_lockfile.py::TestAdvisoryHookDoesNotBlock::test_no_vet_table_not_age_blocked` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_lockfile.py::TestAdvisoryHookDoesNotBlock::test_frob_toml_without_vet_section_not_age_blocked` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_lockfile.py::TestQuarantine::test_fresh_package_blocked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4328 warning(s), 916 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
