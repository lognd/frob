## Done report

Implements the T-0755 diff-scoped adversarial evidence obligation as
TEST016: a bounded mutation pass over a ticket's own diff-touched,
in-scope Python files, using the ticket's own bound pytest evidence ids
as the kill oracle. Reuses `frob.mutate` exclusively (no parallel
mutation engine) -- `run_mutations` gained an optional `max_mutants` cap
(first N mutation points in source order, deterministic) so the check
stays bounded.

New module `frob.tickets._mutation_evidence` (`evidence_test_ids`,
`touched_python_files`, `check_ticket_mutation_evidence`) does the
selection + orchestration: `.py` files under the ticket's scope that
`frob.gitio.working_diff` shows changed against `base_ref`, excluding
test files themselves (mutating a test and re-running the SAME test as
oracle is a self-referential no-op), capped at 3 files x 8 mutants x 90s
timeout each. A file where every mutant survives becomes a
`ConfirmatoryFinding`.

New module `frob.gates._mutation_evidence` (`mutation_evidence_violations`)
turns findings into `TEST016` `Violation`s: WARN by default, ERROR for
security/bug-kind tickets (T-0569 kind-based ratchet the ticket text
calls for) -- NOT the `frob.gates._ratchet` baseline-pool mechanism,
since no retroactive concern applies: the check only ever runs at a
ticket's own close/land time, never re-scanning an already-closed
ticket's evidence, so this cannot turn a past close red on landing.

Wired into `frob ticket land` (`_land.py::_check_mutation_evidence`,
called from `_land_precheck` right after resolving main's branch name,
before any git mutation): a security/bug-kind ticket with an
ERROR-severity finding refuses the land (new `LandError.
EvidenceConfirmatoryOnly`); every other kind's WARN finding is logged,
non-blocking.

Deviations / disclosed choices:

- `frob.check`'s own gate pipeline (`_ALL_GATES`/`_STAGE_GROUPS`,
  `src/frob/check/**`) is NOT wired to run TEST016 -- `frob.check` was
  outside this ticket's declared scope, and every other TEST rule is a
  pure function of the graph snapshot cheap enough for every `frob
  check`; this rule spawns real bounded subprocesses per ticket, which
  would violate the ticket's own PERF guard if it ran unconditionally
  there. `mutation_evidence_violations` has exactly one caller today:
  `frob.tickets._land`.
- `frob ticket close` (the direct, non-land close path through
  `frob.app.ticket_runner`, also out of scope) is NOT wired -- filed as
  a follow-up ticket (draft id T-0844, finalizes at land) so a
  security/bug ticket closed without landing is not silently exempt
  forever.
- Landing-safety: satisfied structurally, not via the ratchet-pool
  mechanism the ticket text mentions as one option -- the check only
  ever evaluates the CURRENT ticket at its own close/land time, so an
  already-closed ticket's evidence is never re-scanned and this rule
  cannot retroactively redden a past close.
- v1 is Python-only, matching `frob.mutate`'s own existing v1 scope.

Gate state: `frob check --ticket T-0755` chunked (lint/static/gates-fast/
gates-native/gates-security) all PASS, 0 errors, 0 waivers added beyond
one `frob:waive INV006` on `gates/_mutation_evidence.py`'s module
docstring (design-rationale prose hit, T-0585 calibration precedent).
`git diff main --diff-filter=D --stat` is empty.


Reviewer round 2 (4 findings, all addressed):

1. CRITICAL, changed-lines scoping: file-wide mutation-point selection
   let an unrelated pre-existing line supply every mutant for a tiny
   diff. `generate_mutants`/`run_mutations` gained `line_ranges`;
   `check_ticket_mutation_evidence` now derives per-file changed-line
   spans from the diff and mutates ONLY those spans. A file whose
   changed lines admit zero mutable points is skipped, never flagged.
2. Real-repo self-test: `test_self_check_t0755_own_diff_zero_error_
   findings` runs the actual obligation against this worktree's own
   T-0755 diff (base_ref=main) and asserts zero ERROR findings.
3. Large-file skip honesty: an unmutable changed region in a large file
   is a skip, not a finding (test added).
4. Documented escape hatch: `frob ticket land --skip-mutation-evidence`
   (AppConfig `ticket_skip_mutation_evidence`, default False) logs the
   TEST016 finding at WARNING but does not refuse the land; for genuine
   false positives only.

Incident found and fixed while landing round 2: the round-2 self-check
test (finding 2) made the evidence suite self-referential -- the check
re-runs the ticket's evidence per mutant, and that evidence now
contained the self-check itself, so each mutant run re-entered the
harness and the suite became a self-sustaining fork bomb (observed
2026-07-23: orphaned full-suite pytest processes respawning after their
drivers died; killed by hand). Fix: `_run_mutants` now stamps
`MUTATION_RUN_ENV` (`FROB_MUTATION_RUN=1`) into every spawned test
process's environment, and the self-check skips under that sentinel.
Guarding inside `check_ticket_mutation_evidence` instead was rejected:
a vacuous early-return under the sentinel would make the tmp-fixture
unit tests fail-on-env rather than fail-on-behavior, fabricating kill
scores -- the same refusal-is-not-a-verdict posture as T-0803. The
sentinel is itself adversarially evidenced
(`test_run_mutations_sets_mutation_run_sentinel_in_child_env`: the kill
oracle exits 0 iff the sentinel is present, so a harness that stopped
stamping it kills the probe mutant and the test fails).

### Changed
```
 docs/modules/mutate.md                  |  17 +-
 docs/modules/tickets.md                 |  81 +++++++++
 src/frob/__main__.py                    |  12 ++
 src/frob/app/config.py                  |   6 +
 src/frob/app/ticket_runner.py           |  10 ++
 src/frob/gates/__init__.py              |   5 +
 src/frob/gates/_mutation_evidence.py    | 110 ++++++++++++
 src/frob/mutate/__init__.py             | 148 +++++++++++++---
 src/frob/tickets/_land.py               | 112 +++++++++++-
 src/frob/tickets/_models.py             |   5 +
 src/frob/tickets/_mutation_evidence.py  | 294 ++++++++++++++++++++++++++++++
 tests/test_gates_mutation_evidence.py   |  88 +++++++++
 tests/test_mutate.py                    | 112 ++++++++++++
 tests/test_ticket_land.py               | 170 ++++++++++++++++++
 tests/test_tickets_mutation_evidence.py | 253 ++++++++++++++++++++++++++
 tickets.md                              | 305 +++++++++++++++++++++++++++++++-
 16 files changed, 1700 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/test_mutate.py::test_run_mutations_max_mutants_caps_points_explored` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestEvidenceTestIds::test_filters_non_node_id_entries` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_filters_to_scope_and_python` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_empty_when_nothing_touched` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_no_test_evidence_is_ok_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_exec_disabled_is_err` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_security_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_bug_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_findings_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_security_kind_error_finding_blocks` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_feature_kind_warn_finding_does_not_block` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_no_findings_is_ok` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_generate_mutants_line_ranges_filters_to_changed_lines` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_generate_mutants_line_ranges_no_match_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_line_ranges_scopes_to_changed_lines` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_large_file_unmutable_changed_lines_is_skipped_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_skip_flag_bypasses_error_finding_but_still_logs` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_parses_to_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_omitted_defaults_false` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_sets_mutation_run_sentinel_in_child_env` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 24 passed (from 24 evidence id(s))
- gates: 6 error(s), 1211 warning(s), 210 waived
