## Done report

Implements REL22x (T-0641): REL220 missing backoff/jitter on a `retry` flow, REL221
non-idempotent retry with no `idempotency_key`/`idempotent` dst marker, REL222
declared-but-unproven backoff (proof-against-code, T-0331 PROVABILITY CONSTRAINT),
mirroring `_reliability.py`'s T-0640 REL200/REL201 TIMEOUT structure exactly
(Report/Violation pydantic pair, RULE:SUBTARGET waiver discipline in
MULTI_INSTANCE_WAIVER_FAMILIES, deny-by-default).

New module `src/frob/strata/_obligation_proof.py` promotes the owner-index/
bound-code/token-scan trio `_reliability.py` built privately for T-0640 into ONE
shared home (owner_index, node_has_bound_code, files_evidence_token,
bound_endpoints) so this ticket's REL222 proof-against-code reuses it rather than
re-copying the pattern; `_reliability.py` itself is left unchanged (already
shipped). Sibling tickets T-0642/T-0643 (circuit-breaker/fallback) are expected to
reuse this same shared module -- noted in both modules' docstrings.

Docs: docs/strata/reliability.md gets a new "REL22x: RETRY obligation (T-0641)"
section plus a "Shared proof-against-code plumbing (T-0641)" section describing
_obligation_proof.py's promotion.

Tests: tests/unit/strata/test_retry.py (9 tests, REL220/REL221/REL222
firing/clean/waived/uncheckable) and tests/unit/strata/test_obligation_proof.py
(10 direct-call tests for the 4 promoted helpers, satisfying TEST001 on public
symbols that test_retry.py only exercises indirectly).

Verification: `uv run pytest tests/unit/strata/test_retry.py
tests/unit/strata/test_obligation_proof.py tests/unit/strata/test_reliability.py
-p no:cacheprovider -q` -> 34 passed. `frob check --only lint/static/gates-fast/
gates-native/gates-security --ticket T-0641` all clean except two pre-existing
repo-wide DRIFT002/TICK006 findings in unrelated files
(src/frob/tickets/_mutation_evidence.py, tickets.md's T-0711 Done report) --
neither touches this ticket's scope, confirmed pre-existing baseline debt.

Cuts: none against the ticket's declared plan. `retry`/`backoff_jitter`/
`idempotency_key` are bare presence-only markers (same grammar-data ceiling
T-0640 disclosed for `timeout`) since strata-core's parser cannot lex a
digit-led attr value and strata-core is out of this ticket's scope.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_retry.py::TestMissingBackoff::test_retry_flow_without_backoff_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestMissingBackoff::test_discharged_and_non_retry_flows_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestMissingBackoff::test_waiver_on_one_flow_keeps_sibling_flow_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestNonIdempotentRetry::test_retry_into_unguarded_dst_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestNonIdempotentRetry::test_idempotent_dst_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestNonIdempotentRetry::test_idempotency_key_dst_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestUnprovenBackoff::test_declared_backoff_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestUnprovenBackoff::test_declared_backoff_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestUnprovenBackoff::test_declared_backoff_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestOwnerIndex::test_inverts_file_to_node_map` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestNodeHasBoundCode::test_true_when_files_present` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestNodeHasBoundCode::test_false_when_absent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken::test_matches_a_real_token` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken::test_no_match_returns_false` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken::test_unreadable_file_skipped_not_treated_as_proof` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints::test_both_endpoints_bound_src_first` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints::test_only_dst_bound` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints::test_self_loop_deduped` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints::test_neither_bound_empty` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 19 passed (from 19 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
