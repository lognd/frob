## Done report

T-1154 fixed the wrong-side-merge tiebreak for `land`'s own internal
`splice_ledger` call by threading a `base_text` (true 3-way merge-base)
param through, but the git merge-driver entry point
(`frob.app.ticket_runner._land_cmd._merge_driver`) already receives git's
own `%O` merge-base argument (`cfg.ticket_merge_base`) and discarded it --
`splice_ledger` was called with only `ours`/`theirs` text, so a LIVE git
merge through the registered driver had no such protection (T-1154's own
Done report named this exact incident, observed live during its own
worktree warm-up: a bare merge-driver invocation reverted T-1111 from
done to queued).

Read `cfg.ticket_merge_base`'s file content (git's own resolved
merge-base -- no `git merge-base` shell-out needed, unlike `land`'s
internal `_true_merge_base`) and thread it through as `splice_ledger`'s
`base_text` param. A missing/unreadable base file degrades to the
pre-T-1165 `_newer`-only tiebreak (OSError caught, `base_text=None`)
rather than refusing the merge -- git always supplies `%O` for a
registered driver, but this is a defensive posture matching
`splice_ledger`'s own optional-base contract.

Regression test (mirroring T-1154's own `test_ticket_land.py` pattern,
per the ticket's own instruction) added to
tests/test_ticket_merge_driver.py::TestMergeDriverHandler:
`test_base_o_arg_prevents_wrong_side_merge_via_live_driver` reproduces
T-1154's exact tie shape (both sides state=done, same evidence count) at
the merge-driver's own base/ours/theirs file boundary -- `ours` makes a
real content edit since `base`, `theirs` is byte-identical to `base` --
and asserts `ours`'s edit survives the splice (pre-fix, the tier-3
`b`-wins tiebreak would have reverted it in favor of `theirs`'s untouched
copy). A second test,
`test_missing_base_file_degrades_to_newer_only_tiebreak`, locks the
defensive-degrade path.

docs/modules/tickets.md#git-merge-driver updated to describe the new
`base_text` threading (AFFECT001).

Also fixed, as a small separate ticket in the same worktree (evidence/
scope kept independent, see its own Done report): T-1152's evidence-
family split moved `_run_evidence_command` into
src/frob/tickets/_evidence.py without re-exporting it from the package --
tests/test_tickets_evidence_cli.py imports it directly
(`from frob.tickets import _run_evidence_command`), predating the split,
and broke with ImportError. Found via a broad `frob test --base main`
touched-set run while finishing T-1165 in this worktree; the remaining
handful of failures that same run surfaced (test_doctor.py,
test_registry_exhaustiveness.py, test_effects.py, test_exports.py) are
unrelated pre-existing repo debt (verified: test_exports.py's failure
lists doctor/serve/vet symbols, nothing tickets-related; test_doctor.py's
failure did not reproduce in isolation).

Gates: `frob check --ticket T-1165` clean across gates-native,
gates-security, test, and the full drift/coverage/invariant/... --only
chunk list. `frob sys sync-interface --check`: no drift.
`tests/test_ticket_merge_driver.py`: 7/7 passed.

### Changed
```
 docs/modules/tickets.md                 |  23 ++++---
 src/frob/app/ticket_runner/_land_cmd.py |  44 ++++++++++----
 tests/test_ticket_merge_driver.py       | 103 +++++++++++++++++++++++++++++++-
 tickets.md                              |  46 +++++++++++++-
 4 files changed, 194 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_disjoint_ids_both_survive_the_splice` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_same_id_newer_state_wins_and_is_written_back` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_malformed_theirs_exits_nonzero_and_leaves_ours_untouched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_missing_args_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_base_o_arg_prevents_wrong_side_merge_via_live_driver` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_missing_base_file_degrades_to_newer_only_tiebreak` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 761 warning(s), 498 waived
- error-findings: none (measured, zero errors)
