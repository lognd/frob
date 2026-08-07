## Done report

Implemented BUG002 (`frob.gates._mutation_evidence.bug_repro_violations`):
for a `bug`/`security`-kind ticket, its designated evidence test (the
FIRST pytest-node-id entry in `ticket.evidence`) must have genuinely FAILED
at the ticket's parent commit -- ERROR severity, always.

DESIGN DECISION -- new rule, not a TEST016 extension. TEST016 proves the
diff is mutation-detectable by its own bound evidence; BUG002 proves the
SAME evidence distinguishes parent-vs-fix. In all five real incidents
(T-1384/T-1399/T-1391/T-1239/T-1401) the new code WAS mutation-detectable
(TEST016 passed) but nothing called it in production, so TEST016 could not
see the gap -- an absent caller has no mutant to kill or survive. Folding
this into TEST016's own function would conflate "adversarial against my
diff" with "adversarial against the caller path", two different claims
with two different failure modes; kept as its own rule/function so each
can be waived, tested, and read independently.

MECHANISM. `_designated_repro_test` picks the ticket's first pytest-node-id
evidence entry (cheap, deterministic -- T-1421's cost constraint: ONE test
at ONE prior commit). `_bug_repro_outcome_at_ref` checks it out via a plain
`git worktree add --detach <scratch> <base_ref>` (no rebuild -- reuses the
calling worktree's already-built native extensions/venv; PYTHONPATH points
at the checkout's own src/ so the subprocess imports the PARENT COMMIT's
source, not the current editable install) and runs it with the current
interpreter. Exit 0 (passed at parent) -> BUG002 violation. Exit 1 (genuine
failure) -> permitted. Anything else (collection/import error -- the
expected shape for a parent-commit change that also touched compiled
native code the scratch checkout never rebuilt -- or the exec kill switch,
or a failed worktree add) -> NO_VERDICT, degrades honestly, never a false
violation or false pass (mirrors TEST016's own ExecDisabled posture, same
module).

COST MEASURED (acceptance [3]): `tests/test_gates_mutation_evidence.py::
TestBugRepro` (two real end-to-end fixtures, real git commits, no mocking
of the outcome function) -- both together measured 1.01s wall
(`time pytest ... ::TestBugRepro`), so each `_bug_repro_outcome_at_ref`
call (worktree add + one pytest run + worktree remove) is well under a
second for a small fixture. Only the SINGLE designated test is ever
re-run, never the bound evidence set or the suite, per the cost
constraint.

ESCAPE HATCH (acceptance [2]): `tickets.md` is excluded from
`frob.graph.build_graph`'s doc/source walk (`is_ledger`), so a waiver
comment placed in the ledger can never become a real `WAIVE` graph edge
`frob.gates._waive`'s matching spine could find -- the existing generic
mechanism structurally cannot reach a ledger-resident ticket. BUG002's
override is instead a plain regex scan of the ticket's OWN body text for
`frob:waive BUG002 reason="..."` (`_bug002_waiver_reason`), logged loudly
at WARNING every time it fires. A bare `frob:waive BUG002` with no
parseable reason is treated as ABSENT (the check still runs), matching
WAIVE001's existing "reason is mandatory" contract.

REGRESSION PAIR (both directions, real fixtures, no mocking):
`TestBugRepro::test_reconstructed_uncalled_guard_passes_at_both_is_refused`
reconstructs the T-1384/T-1391/T-1399 shape (a guard function added and
directly unit-tested in isolation -- passes at both the parent and fix
commit, since calling it in isolation always worked) and asserts BUG002
refuses it. `TestBugRepro::
test_reconstructed_wired_guard_fails_at_parent_is_permitted` reconstructs
the fixed shape (a caller-reaching test that fails until the caller is
actually wired to the guard) and asserts BUG002 permits it.

DISCLOSED CUT: `bug_repro_violations` has NO caller yet as of this ticket.
Wiring it into `frob ticket land`/`frob ticket close` (mirroring TEST016's
own `frob.tickets._land`/`frob.app.ticket_runner` callers) touches files
outside this ticket's declared scope (`src/frob/gates/
_mutation_evidence.py`, `tests/test_gates_mutation_evidence.py`,
`docs/modules/gates.md` only) -- also true of registering the "BUG002"
rule id in `frob.gates._KNOWN_GATE_RULES` (lives in
`src/frob/gates/__init__.py`, out of scope). Filed T-1427 (wire
bug_repro_violations into frob ticket land/close + register BUG002 in
_KNOWN_GATE_RULES) to close this gap -- until it lands, BUG002 exists,
is tested, and is documented, but does not yet gate a real close/land.
This is itself an instance of the exact class this ticket exists to name:
disclosed here rather than silently implied "done".

Gates: `frob check --ticket T-1421` (chunked --only: lint, static,
gates-native, docblocks, docanchor, doclink, scope, prework, fmt, refs)
introduces ZERO new violations -- the only pre-fix hit (ARCH103 on
`_bug_repro_outcome_at_ref` mixing I/O and branching) was split into
`_checkout_bug_repro_worktree` and re-verified clean. Every other
ARCH/DRIFT/DUP/REF finding in the repo-wide counts is pre-existing and
unrelated to this ticket's 3 files (verified by file path in each
finding).

### Changed
```
 docs/modules/gates.md                 |  79 +++++++++
 src/frob/gates/_mutation_evidence.py  | 309 +++++++++++++++++++++++++++++++++-
 tests/test_gates_mutation_evidence.py | 241 +++++++++++++++++++++++++-
 tickets.md                            | 120 ++++++++++++-
 4 files changed, 741 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestBugRepro::test_reconstructed_uncalled_guard_passes_at_both_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugRepro::test_reconstructed_wired_guard_fails_at_parent_is_permitted` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_reason_present_suppresses` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_non_bug_kind_never_checked` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_security_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_bug_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_findings_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_bare_directive_without_reason_does_not_suppress` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_no_directive_at_all` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestDesignatedReproTest::test_first_pytest_node_id_is_designated` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestDesignatedReproTest::test_no_pytest_evidence_is_none` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_exec_disabled_is_no_verdict` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_worktree_add_failure_is_no_verdict` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_no_pytest_evidence_no_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_waived_with_reason_no_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_passed_at_parent_is_error_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_failed_at_parent_no_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_no_verdict_no_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 19 passed (from 19 evidence id(s))
- gates: 11 error(s), 655 warning(s), 690 waived
- error-findings: ARCH001@src/frob/app/_config_external.py, DRIFT002@docs/guides/agentic-workflow.md, DRIFT002@docs/modules/arch.md, DRIFT002@tests/unit/test_arch.py, DRIFT002@tests/unit/test_ticket_runner_land_cmd_flags.py, INV006@src/frob/_cli_parsers/_ticket/__init__.py, INV006@src/frob/_cli_parsers/_ticket/_closeout.py, INV006@src/frob/_cli_parsers/_ticket/_metadata.py, INV006@src/frob/_cli_parsers/_ticket/_progress.py, INV006@src/frob/_cli_parsers/_ticket/_query.py, SELFAUDIT001@design
