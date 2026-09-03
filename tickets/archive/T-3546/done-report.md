## Done report

Changed:
- docs/design/land-splice-test-then-impl.md (new -- the design deliverable)
- src/frob/tickets/_land_squash.py (classify_test_then_impl_paths, _compose_pathset_commit, compose_test_then_impl_commits -- new, UNWIRED)
- tests/unit/test_land_splice_test_then_impl.py (new)

Per the coordinator's brief and the T-3550 precedent (design first,
gated implementation second): this ticket lands the FULL design --
split algorithm, why it is safe against T-3053/T-3088/T-3089's compose-
out-of-tree + single-CAS-publish model, and all four listed
consequences (--check-repro becomes verifiable post-land via
`derive_land_commit_by_grep`-style dual-match resolution rather than a
new Ticket field, since T-3543 already removed the old land_commit
second-commit mechanism this design would otherwise have depended on;
the bisect story via `Land-Splice-Role` commit trailers; CI-on-main
semantics needing no change since GitHub Actions triggers per ref-move
event, not per commit; and the mechanical fallback-to-single-squash
precondition) -- plus the MECHANICAL, UNWIRED primitives
(`classify_test_then_impl_paths`, `compose_test_then_impl_commits`),
proven against a scratch git repo including a check that the split's
final tree is byte-identical to what today's single-commit
`compose_tree_out_of_tree` squash would produce.

Deliberately NOT implemented here: wiring these primitives into
`_fold_publish_and_resync`/`_publish_squash_apply`, this repo's own
highest-incident-density land code path (T-3066, T-3114, T-3121,
T-3163 all root-caused in this exact function family). Filed as T-3564,
blocked by T-3546 (owner sign-off on the design), matching the T-3550
precedent's own two-ticket shape exactly.

Evidence:
- tests/unit/test_land_splice_test_then_impl.py::TestClassifyTestThenImplPaths::{test_mixed_paths_split_into_two_groups,test_no_test_paths_returns_none,test_no_impl_paths_returns_none} (pytest node ids, verified passing)
- tests/unit/test_land_splice_test_then_impl.py::TestComposeTestThenImplCommits::{test_two_commits_chain_correctly,test_final_tree_matches_full_squash} (pytest node ids, verified passing)

Filed: T-3564 (wiring implementation, blocked by T-3546)

Gates: `uv run pytest -p no:xdist tests/unit/test_land_splice_test_then_impl.py`
(6 passed) plus `tests/unit/test_land_compose.py` and
`tests/unit/test_land_record_commit.py` (18 passed, confirming the new
`_land_squash.py` imports did not regress the existing compose/CAS
machinery). Scoped `frob check --ticket T-3546 --only affect_drift
--only coverage --only fmt` clean on this ticket's own touched-set
concerns after an `frob fmt` pass fixed two FMT001 directive-wrap
findings on the new functions; repo-wide FAIL lines from other
families are pre-existing per the run's own scope note.
