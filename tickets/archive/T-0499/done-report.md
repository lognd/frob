## Done report

Added `frob.gates.known_gate_rule_ids()` as the public accessor over
`_KNOWN_GATE_RULES`, and threaded it into both production callsites named
in the ticket: `frob.app.sys_runner._evaluate_audit` now passes it into
`evaluate_exhaustiveness(..., known_rule_ids=known_gate_rule_ids())`, and
`frob.strata._audit._compliance_pii_lint_fingerprint_gaps` (called from
`_collect_all_family_gaps`) now forwards the same `known_rule_ids` into
`evaluate_compliance(..., known_rule_ids=known_rule_ids)` -- so both
THREAT006 and COMPLIANCE004's `caught_by` verification can resolve a
rule-id-shaped reference against the live gate-rule-id set instead of
always defaulting to empty (fail-closed on every reference).

Counterexample-first note: this gap was dormant (no current `caught_by`
entry names a rule-id-shaped token), so there is no existing litmus that
flips from vuln to hardened here. Verified the wiring itself directly: a
mock.patch spy on `evaluate_compliance` proves `evaluate_exhaustiveness`'s
`known_rule_ids` kwarg reaches every `evaluate_compliance` call it makes
(`test_known_rule_ids_reaches_compliance_caught_by_check`), and two direct
unit tests exercise `known_gate_rule_ids()` itself.

REL001: new public symbol `frob.gates.known_gate_rule_ids` triggered a
minor version bump, 0.42.0 -> 0.43.0 (pyproject.toml, uv.lock, CHANGELOG.md,
.frob-release.json via `frob release stamp`).

Not Filed T-draft-94774bc5 (never refiled) (out-of-scope discovery): `_audit.py` never threads
a compliance `out_of_scope` catalog into `evaluate_compliance` at all (no
`COMPLIANCE_OUT_OF_SCOPE` constant exists, unlike the security/quality
families) -- so COMPLIANCE004 stays vacuous in production regardless of
this ticket's known_rule_ids fix. Same root shape as this ticket, but a
distinct gap (out_of_scope threading vs known_rule_ids threading), left
for a follow-up ticket rather than folded in here.

Full targeted suite run: `uv run pytest tests/unit/strata -q` (all ~800,
minus one pre-existing unrelated failure --
`test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`,
confirmed failing identically on a clean checkout of these same files
before this ticket's edits, i.e. not caused by this change) stayed green.
`uv run frob check --ticket T-0499` is clean: 0 errors (374 warnings, 95
waived, unchanged from the pre-work baseline stamp).

### Changed
```
 .frob-release.json              |  3 +-
 CHANGELOG.md                    | 16 ++++++++++
 docs/modules/gates.md           |  7 +++++
 pyproject.toml                  |  2 +-
 src/frob/app/sys_runner.py      |  9 +++++-
 src/frob/gates/__init__.py      | 14 +++++++++
 src/frob/strata/_audit.py       | 17 +++++++---
 tests/test_gates.py             | 18 +++++++++++
 tests/unit/strata/test_audit.py | 27 ++++++++++++++++
 tickets.md                      | 70 +++++++++++++++++++++++++++++++++++++++++
 uv.lock                         |  2 +-
 11 files changed, 177 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_audit.py::TestExhaustiveness::test_known_rule_ids_reaches_compliance_caught_by_check` (pytest node id, verified passing when recorded)
