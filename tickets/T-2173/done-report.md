## Done report

SCOPE CORRECTION (recorded per coordinator's request, so nobody re-derives
this): T-2173 was originally filed scoped to src/frob/tickets/_land_git_ops.py.
That file has zero rebase-related code at all (git grep -c "rebase" ->
0). The real mechanism lives in src/frob/app/ticket_runner/_land_cmd.py
::_auto_rebase_worktree_onto_main (T-1720). This is the SECOND time in
one session the coordinator's declared scope was a plausible-sounding
guess from the module name rather than a grep of the actual failing log
line/symbol (T-2157 was scoped to _land_git_ops.py too, when the real
site was _land_squash.py) -- recording the pattern here per the
coordinator's own request, not to relitigate it.

MECHANISM THEORY, ALSO CORRECTED (a second falsification, this one mine):
my own first-pass theory, after noticing tickets.md/tickets-archive.md
register a custom `merge=frob-ledger` driver in .gitattributes, was
"git rebase does not invoke registered merge drivers during its
per-commit replay, so the ledger's own conflict-resolution logic is
simply never in the loop." TESTED DIRECTLY and FALSIFIED: registered a
real merge driver on a throwaway file, created a genuine conflicting
edit on both sides, ran both `git merge` and `git rebase` -- both
invoked the driver identically (same output, both succeeded, no
conflict either way). Git DOES invoke a registered merge driver during
rebase's replay. This was never the actual mechanism.

REAL MECHANISM, CONFIRMED: the classic "rebase a branch after its own
content was already squash-merged" conflict class, independent of any
merge driver. Reproduced directly with NO driver registered at all
(see tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::
test_squash_then_rebase_conflicts_but_merge_does_not, and a separate
ad-hoc script run against the OLD, unrenamed
_auto_rebase_worktree_onto_main directly -- both confirm the same
result): a worktree branch making several separate commits that walk
one file through a sequence of states (mirroring the auto-commits
`frob ticket scope`/`start`/`evidence`/`done-report` each make), then
main receiving the SAME final state as ONE squash-applied commit
(exactly what `frob ticket land`'s own squash-apply does) -- `git merge`
from the worktree branch: exit 0, correct content, no conflict (one
3-way diff of final-vs-final finds nothing real to resolve); `git
rebase main` from the same branch: CONFLICT on the FIRST replayed
commit, even though the two branches' final content is byte-identical
-- rebase replays each of the worktree's original, now-superseded
intermediate commits one at a time against main's already-final
post-squash tip, and the first one disagrees with that final state on
its own terms. Deterministic, not a race -- explains why this failed on
every affected land (four for four, across three worktrees) rather than
occasionally: every `frob ticket land` squash-applies.

FIX: renamed _auto_rebase_worktree_onto_main to
_auto_sync_worktree_onto_main, rewrote its body around `git merge
--no-edit <main>` instead of `git rebase <main>` (structurally immune to
the conflict class above by construction -- one 3-way diff of final
states, never a replay of superseded intermediates), and added a
cleanliness check (`git status --porcelain` empty) BEFORE ever
attempting the merge -- merging into a dirty worktree could destroy an
agent's own uncommitted in-progress edits, which this function has no
way to distinguish from "safe to auto-sync" any more than a human
checking by hand would need to; a dirty worktree is now skipped
silently at DEBUG, same posture as the pre-existing detached-HEAD skip.
The merge commit runs under `_land_internal_git_env()` (T-0731) since
main's post-land tip can carry a REL001 version bump the scaffolded
pre-commit hook would otherwise refuse a worktree commit touching.
Updated the one stale `frob:describes` doc anchor in
docs/modules/tickets.md and the pre-existing unit test file (renamed
class/references, kept its two original tests working under the new
name, added the acceptance repro plus a dirty-worktree safety test).

VERIFIED (BUG002 repro discipline, playbook 0.6): repro test committed
ALONE first (9b219e56e), confirmed FAILING there (ImportError, since the
new test references the not-yet-existing renamed symbol) -- separately
confirmed the UNDERLYING defect directly, not just the import mismatch,
by calling the OLD rebase-based function against the exact repro shape
in a standalone script: `is_ancestor(main, HEAD)` came back False, i.e.
the worktree was genuinely left behind main, matching the real incident.
Then the fix committed separately (3dc0a3d92), confirmed all 4 tests
pass: `pytest tests/unit/test_land_auto_rebase.py` ->
SUITE-RESULT: exitstatus=0 collected=4 failed=0, 4 passed. Designated
the acceptance test as repro via --designate-repro (validated
FAILED_AT_PARENT at designate time).

`frob check --only lint --json --ticket T-2173` (FROB_NO_GATE_CACHE=1):
one pre-existing ruff-check I001 finding at _land_cmd.py:3450 confirmed
via `git blame` to predate this ticket by four days (2026-08-07,
unrelated code) -- not a regression here. `tests/test_land_cmd_
backpressure.py`'s "would reformat" flag is the same repo-wide
frob-fmt-vs-raw-ruff-format drift already documented in this session's
other Done reports (T-2157/T-2156), not new.

Ran the wider tests/test_ticket_work_and_land_finish.py suite as a
regression check: 5 failures in TestLandProofAndFinish, ALL confirmed
PRE-EXISTING and unrelated to this change -- reproduced identically
against the root checkout's own HEAD (a8109c7bb, no worktree changes
involved at all): an AttributeError
('types.SimpleNamespace' object has no attribute 'ticket_id') at
_land_cmd.py:1319 inside _print_land_proof's claims-outcome lookup,
`git blame`-dated to 2026-08-10 23:02, five days before and completely
unrelated to this ticket's own diff. Not filing a new ticket for it
myself -- flagging here for the coordinator's triage since it is
already broad (5 tests) and clearly a different defect in the same file
family.

### Changed
```
 docs/modules/tickets.md                 |  82 ++++++++++-----
 src/frob/app/ticket_runner/_land_cmd.py | 165 +++++++++++++++++++++++--------
 tests/unit/test_land_auto_rebase.py     | 170 ++++++++++++++++++++++++--------
 tickets/T-2173/ticket.md                |  41 +++++++-
 4 files changed, 351 insertions(+), 107 deletions(-)
```

### Evidence
- `tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_merges_the_worktree_onto_the_new_main_tip` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_squash_then_rebase_conflicts_but_merge_does_not` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_dirty_worktree_is_skipped_rather_than_merged_into` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/graph/callgraph.py, ARCH103@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1720, DOC002@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2173, SELFAUDIT001@design, TEST001@src/frob/graph/callgraph.py, TEST001@src/frob/tickets/_land_git_ops.py, TICK004@tickets.md
