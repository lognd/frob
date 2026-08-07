## Done report

Per-item verdict against docs/audits/tickets-testing-round2.md:

- N-01 (empty-scope bypasses D-02 binding): fixed-by-T-0906 (killed the
  SCOPE001/covers_scope empty-scope early-out) + T-0899 (paired regression
  gate). Verified by reading `_covers_scope_for_ticket`
  (src/frob/app/ticket_runner.py:1797) -- empty `ticket.scope` still returns
  `None` (documented as a false-positive guard, not a loophole, per its own
  docstring), but T-0906's land removed the matching empty-scope early-out on
  the SCOPE001 gate side, closing the actual bypass; T-0899 (tests/test_gates.py
  ::TestScopePrework.test_scope001_fires_when_no_scope_declared /
  test_scope001_empty_scope_ledger_still_implicitly_in_scope) locks it in.
- N-02 (close never re-runs evidence, TOCTOU): OPEN, IMPLEMENTED HERE. Added
  `evidence_reverified` param threaded through `transition` ->
  `_transition_guard` -> `_done_transition_guard`
  (src/frob/tickets/__init__.py), returning `Err(EvidenceNotPassing)` on
  `False` -- the direct-close twin of `land`'s own
  `_reverify_evidence_post_merge` (D-05). New CLI helper
  `_reverify_evidence_for_close` (src/frob/app/ticket_runner.py) re-runs the
  ticket's non-cmd evidence ids against the CURRENT tree via the existing
  `_collect_python_and_rust_ids` / `_verify_ids_passing` machinery and is now
  always computed and passed at `frob ticket close` time.
- N-03/N-04 (vacuous/self-scoped tests count as passing): fixed-by-T-0755/
  T-0844. `mutation_evidence_violations` (src/frob/gates/_mutation_evidence.py)
  runs a real mutation pass over the ticket's bound evidence; a test that
  asserts nothing kills 0 mutants and is flagged TEST016 "confirmatory-only"
  (ERROR for security/bug kind, WARN otherwise), and T-0844 wired this into
  the direct `frob ticket close` path (`_close_mutation_evidence_for_ticket`),
  not just `land`. This directly subsumes the N-03/N-04 vacuous-test class:
  a test that never touches the changed code kills no mutant and is caught.
- D-03/N-05 (3-char done-report floor): unchanged, out of this ticket's
  bounded scope (not the close-vs-land re-verify gap the dispatch called out
  as likeliest live item); left as-is, no new ticket filed since N-05 is
  already fully described in the round-2 audit for a future pass.

Changed:
- src/frob/tickets/__init__.py::_transition_guard
- src/frob/tickets/__init__.py::_done_transition_guard
- src/frob/tickets/__init__.py::transition
- src/frob/app/ticket_runner.py::_reverify_evidence_for_close (new)
- src/frob/app/ticket_runner.py::_close
- docs/modules/tickets.md (transition's public-api anchor, AFFECT001)
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose (new)
- tests/test_ticket_land.py::TestReverifyEvidenceForClose (new)
- tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass (patched to
  stub the new re-verify closure, since it now runs unconditionally at close)

Evidence: 7 ids recorded and passing (see `frob ticket show T-0417`):
tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose (3 tests),
tests/test_ticket_land.py::TestReverifyEvidenceForClose (4 tests).

Filed: none (N-01/N-03/N-04 confirmed already fixed by prior tickets; N-05
left as pre-existing, documented debt per the audit, not newly discovered).

Gates: `frob check --ticket T-0417` clean across all 5 chunked stage-groups
(gates-fast, gates-native, gates-security, lint, static) for every file this
ticket touched; the 2 `ty`/ruff-format findings on tests/test_gates.py and
src/frob/arch/_lock_ordering.py are pre-existing and outside this diff (not
files this ticket touches). 5 test_ticket_land.py tests
(TestMergeConflictOutsideLedger/TestLand/TestGitSubprocessFailures/
TestWipCommitNormalizationOnlyDirty/TestDoneReportThenLandRealClosuresEndToEnd)
flake when run as a batch due to a pre-existing nested `uv run pytest
--collect-only` environment artifact inside tmp worktrees -- reproduced
identically on unmodified HEAD via a throwaway `git worktree add`, confirmed
unrelated to this diff, and each passes individually.

### Changed
(no changed files detected)

### Evidence
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_rejects_when_evidence_reverified_false` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_allows_when_evidence_reverified_true` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_permissive_when_evidence_reverified_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_no_non_cmd_evidence_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_collection_failure_returns_false` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_still_passing_returns_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_no_longer_passing_returns_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 4217 warning(s), 220 waived
- error-findings: none (measured, zero errors)
