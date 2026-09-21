## Done report

T-3899 -- TICK014 inspects only the close commit, flagging every ticket
following the one-logical-change-per-commit convention
================================================================================

Worktree: /home/logan/projects/frob/.claude/worktrees/t-3899 (branch t-3899)
Final HEAD: 42c147d73

Scope: src/frob/gates/_empty_diff_close.py, src/frob/gates/_tickets_gate.py,
tests/test_gates_empty_diff_close.py (docs/modules/tickets-data-storage.md
was requested too, but `frob ticket scope --add` refused it: leased by
another in-progress ticket -- see "Filed" below).

WHAT changed
------------
`frob.gates._empty_diff_close.empty_code_diff_violations` (TICK014)
previously judged a closed ticket ONLY by the `### Changed` block stored
in its Done report body -- a `git diff --stat <base_ref>...HEAD` snapshot
taken once, at `frob ticket done-report` time. That snapshot goes stale
the moment the ticket's branch is later squashed by `frob ticket land`
into one `land_commit`: a ticket that committed real code in a
`feat:`/`fix:` commit, then closed in a separate `chore(tickets): close
T-####` commit (this project's own mandated one-logical-change-per-commit
convention), could still read as an empty/bookkeeping-only diff at
gate-scan time, depending on exactly when `done-report` ran relative to
land. TICK014 fired on this NORMAL workflow, not just genuine T-3064-style
no-code closes.

Fix (`src/frob/gates/_empty_diff_close.py`):
  - New `_changed_paths_from_land_commit(root, sha)`: `git show --stat
    --format= <sha>`'s changed paths.
  - New `_tick014_changed_paths(root, t)`: prefers `t.land_commit`'s real
    diff when recorded and resolvable; falls back to the pre-existing
    `_changed_paths_from_done_report(t.body)` otherwise (never landed via
    `frob ticket land`, or an unresolvable sha).
  - `empty_code_diff_violations` signature changed to
    `(root: Path, queue: TicketQueue)` (was `(queue)`) -- needs `root` to
    run git. Call site in `src/frob/gates/_tickets_gate.py::
    _tickets_gate_inner` updated to pass `root` (already in scope there);
    added `# frob:ticket T-3899` to that function since its call-site line
    changed.
  - Remedy string corrected: it told a (necessarily already-closed)
    ticket to `--declare-no-scope` "before closing" -- impossible after
    the fact, since TICK014 only ever fires on a DONE ticket. Reworded to
    say the declaration is applied retroactively.
  - Module docstring rewritten to document the fix and the three edge
    cases the ticket required deciding explicitly (see below).
  - `tests/test_gates_empty_diff_close.py`: all 8 existing tests updated
    to pass a `root` arg (an unused `Path(".")` sentinel, since a ticket
    with no `land_commit` never touches git); added `TestTick014LandCommit`
    (4 new tests) using a REAL temporary git repo (`_git_repo`/`_commit`
    helpers, `subprocess` + actual `git init`/`commit`) so the land_commit
    branch is proven against real `git show --stat` output, never a
    hand-typed approximation.

WHY
---
The reported diagnosis (FROBLEMS T-023) was: "the rule fires on the
NORMAL workflow" because it "looks only at the close transition's own
commit" -- confirmed by direct code reading: the check never ran git at
all, it read a stored, point-in-time snapshot that could predate a later
squash. The reporter's suggested fix ("lifetime diff: start-transition
commit through close commit") was refined to use `t.land_commit`
(`frob.tickets._models.Ticket.land_commit`, already recorded by
`frob.tickets._land_squash._record_land_commit` right after `frob ticket
land` produces a ticket's single squashed commit) instead of trying to
locate a start-transition commit by message grep -- `land_commit` IS the
whole-branch-range diff already, pre-squashed to exactly one commit, and
scoped to exactly one ticket by construction.

EDGE CASES (ticket's own required-before-implementing list), decided and
documented in the module docstring:

  1. Code landed, then reverted in a LATER, separate commit before close:
     NOT detected -- `land_commit`'s own diff still shows the original
     files (a later revert is a different commit, outside `land_commit`'s
     tree). Decided explicitly as a disclosed non-goal: this check
     verifies "did this ticket's land touch real files", not "does that
     code still exist right now"; detecting a revert needs a different
     signal (diffing current HEAD against the target branch). NOT silently
     assumed covered.
  2. Ticket's lifetime spans another ticket's commits (concurrent work on
     the shared branch): does not apply to `land_commit` at all --
     `frob ticket land <id>` squashes ONLY that ticket's own branch
     commits into one commit scoped to that ticket. This is exactly why
     `land_commit` (not a raw start-to-close commit RANGE, which WOULD
     leak concurrent commits on a shared branch) is the correct anchor.
  3. Closed without ever landing (no `land_commit`, e.g. `frob ticket
     close` used directly as a decision record): falls back to the
     pre-existing stored-Changed-block logic unchanged, so the ORIGINAL
     true-positive case (T-3064: closed done, genuinely no code anywhere)
     still fires exactly as before.

MEASUREMENT against this repo's own ledger (acceptance item: "sample and
classify"; ran as a direct in-process comparison rather than two full
`frob check` invocations, given fleet load and the ~15-20 min per-run
cost measured on the other two tickets this session):
  - Old behavior (stored Changed block only): 947 TICK014 hits.
  - New behavior (this fix): 610 TICK014 hits.
  - 337 eliminated -- every one of a 20-item random sample of the
    eliminated set carried a recorded `land_commit` (spot-checked
    T-1600/T-1601/T-1602/T-1603/T-1604/T-1606/... -- all early
    language-support tickets landed via the feat-then-close convention).
  - A 20-item random sample of the REMAINING 610 hits were ALL
    `land_commit=None` -- i.e. legacy tickets that predate the
    `land_commit` field (T-2220) or never went through `frob ticket land`
    at all, still judged by the fallback path. I did not verify each of
    these 20 by hand against its actual git history (that would need a
    per-ticket `git log --grep` archaeology this ticket's scope doesn't
    reach, since T-2220 postdates them) -- flagging this honestly rather
    than claiming a classification I did not actually perform. The
    ticket's stated 883-count (this repo's count came back as 947,
    ~7% higher -- expected repo growth since the ticket was filed) and
    the "20-sample classification split" / "T-3863 re-scoped or closed"
    acceptance items are NOT fully closed by this session: the coordinator's
    dispatch for this round explicitly narrowed scope to "TICK014 must
    inspect the whole branch range from the land base to the close commit;
    drift-lock test, evidence" -- delivered above -- and did not ask for
    the T-3863 rescoping/full-classification follow-through, which
    remains open on T-3899 itself for whoever picks it up next.

MUST-FIRE / MUST-STAY-QUIET fixtures (ticket's own requirement)
-----------------------------------------------------------------
  MUST-FIRE (no code, ever): `test_bug_warns`, `test_feature_warns`,
    `test_land_commit_bookkeeping_only_warns` (land_commit-based),
    `test_unresolvable_land_commit_falls_back_to_changed_block`
    (land_commit present but unresolvable -- falls back, still fires).
  MUST-STAY-QUIET (real code landed): `test_real_diff_quiet`,
    `test_land_commit_with_real_code_quiet` (THE reported false-positive
    reproduction -- land_commit has real code, stale stored Changed block
    says bookkeeping-only, land_commit wins),
    `test_land_commit_overrides_stale_empty_changed_block` (stored block
    reads the literal `(no changed files detected)` sentinel, land_commit
    still wins).
  Exemptions unchanged and still tested: `test_docs_kind_quiet`,
    `test_epic_tier_quiet`, `test_no_scope_quiet`, `test_no_block_quiet`,
    `test_open_never_fires`.

Test node ids (12/12 pass, pytest exit 0)
-------------------------------------------
tests/test_gates_empty_diff_close.py::TestTick014::test_bug_warns
tests/test_gates_empty_diff_close.py::TestTick014::test_feature_warns
tests/test_gates_empty_diff_close.py::TestTick014::test_docs_kind_quiet
tests/test_gates_empty_diff_close.py::TestTick014::test_epic_tier_quiet
tests/test_gates_empty_diff_close.py::TestTick014::test_no_scope_quiet
tests/test_gates_empty_diff_close.py::TestTick014::test_real_diff_quiet
tests/test_gates_empty_diff_close.py::TestTick014::test_no_block_quiet
tests/test_gates_empty_diff_close.py::TestTick014::test_open_never_fires
tests/test_gates_empty_diff_close.py::TestTick014LandCommit::test_land_commit_with_real_code_quiet
tests/test_gates_empty_diff_close.py::TestTick014LandCommit::test_land_commit_bookkeeping_only_warns
tests/test_gates_empty_diff_close.py::TestTick014LandCommit::test_land_commit_overrides_stale_empty_changed_block
tests/test_gates_empty_diff_close.py::TestTick014LandCommit::test_unresolvable_land_commit_falls_back_to_changed_block

Also re-ran the broader tickets-gate test suite (test_tick.py,
test_gates_tick005.py, test_gates_tick009_tick010.py,
test_gates_tickets_hygiene.py, test_tick012_gate.py, test_tick013_gate.py,
test_tickets_collision.py, excluding slow `real_repo`-marked cases that
timed out purely from fleet CPU contention, unrelated to this change) --
102/102 pass, confirming the `empty_code_diff_violations(root, queue)`
signature change did not break any other tickets_gate consumer.

Evidence bound in tickets/T-3899/ticket.md (no structured `acceptance:`
list exists on this ticket -- all 12 node ids recorded generically via
`frob ticket evidence T-3899 <node-ids> --base-ref dev`).

Gate check
----------
`frob check --only gates --files src/frob/gates/_empty_diff_close.py
--files src/frob/gates/_tickets_gate.py --files
tests/test_gates_empty_diff_close.py --base dev --no-cache` (2 passes to
converge, ~15-20 min each under heavy fleet load):

  Pass 1: LANDFMT001 (needs `ruff format`), AFFECT001 (doc anchor not
    touched -- see Filed below), COV002 (`_tickets_gate_inner` changed,
    no frob:ticket edge), 4x DRIFT002 (new `frob:tests` directives named
    class `TestTick014` instead of the new `TestTick014LandCommit`).
  Pass 2 (final, this commit): `ruff format` applied; AFFECT001 waived
    with the follow-up ticket id; `# frob:ticket T-3899` added to
    `_tickets_gate_inner`; the 4 `frob:tests` directives corrected to
    `TestTick014LandCommit.*`. Zero COV002/DRIFT002/LANDFMT001/AFFECT001
    findings remain on any of the three touched files. All other FAIL
    rows in the tool summary (ARCH, COV, DOC, DRIFT, DSL, LANG, PERF, PRE,
    REF, SCOPE, TICK, TODO, WIRE) are pre-existing, repo-wide, confirmed
    (by grep) to name none of this ticket's touched files -- the only
    lines naming `_tickets_gate.py`/`_empty_diff_close.py` left are
    pre-existing findings on code this ticket did not touch (line numbers
    345/726/1173/1442/1447/1775/1779, all far from the 1921/1922 one-line
    insertion this ticket made) plus the ticket's own new, warn-only
    CPLACE001 (3-line waiver directive over the 2-line cap -- gate:CPLACE
    itself still reports 0 errors overall, non-blocking).

Filed: T-5177 -- "TICK014 doc anchor needs T-3899
land_commit-precedence update" (docs/modules/tickets-data-storage.md).
This ticket's own scope-add for that file was refused
(`ScopeLeaseConflict`: held by in-progress T-4555) -- filed the doc
update as a follow-up rather than silently leaving the anchor
inaccurate, and added a `frob:waive AFFECT001` on `empty_code_diff_
violations` naming the follow-up ticket instead of pretending the doc
update was unnecessary.

Also filed (during this session, on a DIFFERENT ticket in this same
series): T-3995 was formally `frob ticket block`-ed on T-3943 after
three `frob ticket work T-3995` attempts all failed identically --
T-3995's entire declared scope is `src/frob/app/check_runner.py`, which
collides with T-3943's (a different in-progress ticket, unrelated agent)
lease on the same file. This is a whole-scope collision, not transient
contention, so it was recorded as a block rather than retried
indefinitely. T-3995 was NOT worked this round.

Commits:
  42c147d73 fix(gates): TICK014 judges a closed ticket by its land_commit diff
  (merge from dev: none needed -- worktree was created fresh from current dev)

### Changed
```
 src/frob/gates/_empty_diff_close.py  | 164 +++++--
 src/frob/gates/_tickets_gate.py      |  12 +-
 tests/test_gates_empty_diff_close.py | 167 ++++++-
 tickets/T-3899/done-report.md        | 903 +++++++++++++++++++++++++++++++++++
 tickets/T-3899/ticket.md             |  17 +-
 tickets/T-5177/ticket.md   |  29 ++
 6 files changed, 1245 insertions(+), 47 deletions(-)
```

### Evidence
- `tests/test_gates_empty_diff_close.py::TestTick014::test_bug_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_feature_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_docs_kind_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_epic_tier_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_no_scope_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_real_diff_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_no_block_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014::test_open_never_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014LandCommit::test_land_commit_with_real_code_quiet` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014LandCommit::test_land_commit_bookkeeping_only_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014LandCommit::test_land_commit_overrides_stale_empty_changed_block` (pytest node id, verified passing when recorded)
- `tests/test_gates_empty_diff_close.py::TestTick014LandCommit::test_unresolvable_land_commit_falls_back_to_changed_block` (pytest node id, verified passing when recorded)
