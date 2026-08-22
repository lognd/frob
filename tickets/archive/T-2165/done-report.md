## Done report

Replaced the doable-revalidation cache's key from T-2089's whole-tree
signature (_tree_state_key: committed HEAD sha + git status --porcelain
digest) to a new identity-scoped key (_identity_scoped_state_key)
covering only the files actually named in the candidate (rule, file)
pairs being revalidated.

ROOT CAUSE (per the ticket body): the whole-tree key changes on
essentially every land in a busy multi-agent session, so a cache HIT was
structurally almost unreachable even when nothing relevant to the
CANDIDATE set had changed -- confirmed already in T-2106's own Done
report (UNMEASURABLE instead of a cache hit, on a tree that had not
moved relative to the candidate files).

FIX: _identity_scoped_state_key(root, pairs) reads the CURRENT on-disk
CONTENT of every distinct file named in pairs directly (no git spawn,
no blob lookup) and hashes it. This is deliberately content-based, not
commit-based: it changes the instant a named file's content differs,
whether that difference is committed or still sitting uncommitted in
the working tree -- satisfying the ticket's own non-negotiable
soundness requirement ("the narrowing has to be identity-scoped, not
blanket-relaxed... an agent's own uncommitted fix ... must not be
masked"). A file that does not exist degrades to a stable sentinel
entry rather than raising. Never returns None (unlike _tree_state_key,
which can fail on a non-repo) since it does no git spawn.

_reproducing_identities_cached now calls this instead of
_tree_state_key; the None-handling branch it used to need is gone since
the new key is always available.

Positive controls, all three verified:
1. Cache HITS across a HEAD move when candidate files are unchanged:
   test_unchanged_files_same_key_across_a_head_move (unit, key-level)
   and test_cache_hits_across_a_head_move_when_candidate_files_are_unchanged
   (end-to-end through revalidate_dispatchable_sweep_tickets: 2 calls,
   1 intervening unrelated committed land, exactly 1 spawn total --
   this is the exact scenario T-2089's key could never hit).
2. Must-still-pass, soundness: editing a NAMED file (committed or not)
   still changes the key / still forces a respawn:
   test_editing_a_named_file_changes_the_key,
   test_uncommitted_edit_to_a_named_file_changes_the_key (key-level),
   test_uncommitted_edit_to_candidate_file_still_forces_a_respawn
   (end-to-end: 2 calls, uncommitted edit to the candidate's own file
   in between, exactly 2 spawns -- confirms the cache never masks a
   genuine fix). test_second_call_same_tree_reuses_cache_no_second_spawn
   (T-2089's own pre-existing test) still passes unchanged.
3. Editing an UNRELATED file (not named in pairs) does not change the
   key: test_editing_an_unrelated_file_does_not_change_the_key.
   test_missing_file_has_a_stable_sentinel_digest covers the edge case
   of a candidate file that no longer exists.

All 123 tests in tests/unit/test_rapid_sweep.py pass (23 in the
directly-touched classes, 123 total for the file).

Lease note: this ticket's sole scope file
(src/frob/app/ticket_runner/_rapid_sweep.py) was reported contended all
evening in the dispatch brief; checked read-only immediately before
starting and it was genuinely clear at that time (no
.git/frob-leases/*.json entry named it). A stale orphaned branch
`t-2165` (a same-glob no-op scope probe from an earlier, abandoned
session, no live worktree registered) blocked `frob ticket work` on
first attempt; deleted it (git branch -D, not checked out anywhere,
merge-base with main, no real work) and retried successfully.

### Changed
```
 tickets/T-2165/ticket.md | 13 ++++++++++++-
 1 file changed, 12 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_unchanged_files_same_key_across_a_head_move` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_editing_a_named_file_changes_the_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_editing_an_unrelated_file_does_not_change_the_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_uncommitted_edit_to_a_named_file_changes_the_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey::test_missing_file_has_a_stable_sentinel_digest` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_second_call_same_tree_reuses_cache_no_second_spawn` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_cache_hits_across_a_head_move_when_candidate_files_are_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_uncommitted_edit_to_candidate_file_still_forces_a_respawn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2165/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2165, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
