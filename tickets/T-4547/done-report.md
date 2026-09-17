## Done report

T-4547 -- rapid land --files scope diffs against the resolved land target, not a hardcoded "main"

What changed:
- src/frob/app/ticket_runner/_land_cmd.py
  - _land_touched_paths(worktree, ticket_id, *, target_branch="main"): now
    diffs against target_branch (via working_diff(worktree, target_branch))
    instead of a hardcoded "main". Default stays "main" so every pre-existing
    caller that does not pass target_branch is byte-for-byte unchanged.
  - _rapid_check_scope_files(worktree, ticket_id, touched_paths, *,
    target_branch="main"): now logs target_branch in its INFO summary line,
    and, when direct_dependent_count == 0, logs a second INFO line
    explaining that affects()/_dependents_of() only follows explicit
    `frob:uses-contract` directive edges (not a general call graph), so a
    0 count is the expected value whenever none of the touched files'
    symbols is the target of such a directive elsewhere in the tree -- not
    evidence of a broken walk.
  - _land_core_invoke: resolves the actual land target via T-3787's
    _resolve_land_target_branch(root, cfg.ticket_id, cfg.ticket_land_branch)
    before computing the rapid scope, and threads that resolved branch into
    both _land_touched_paths and _rapid_check_scope_files. A resolution
    failure (e.g. an invalid configured target) degrades to "main" here --
    land() itself, called right after, is the one place that actually
    refuses the land on an invalid target branch; this scoping step must
    not duplicate that refusal.

- tests/unit/test_check_scoped_files.py
  - New test (TestRapidLandFilesWiring.
    test_land_touched_paths_against_main_includes_unrelated_dev_commit):
    builds a real tmp git repo where a `dev` branch has an unrelated commit
    ahead of `main`, then a ticket branch off `dev` with its own single-file
    commit. Diffing against target_branch="main" (the default, i.e. today's
    pre-fix behavior) includes the unrelated dev commit's file; diffing
    against target_branch="dev" (the fix, when dev is the resolved land
    target) excludes it. This is the exact 252-vs-6-file shape measured in
    the T-4511 land log, reproduced at unit scale.

Root cause (confirmed): _rapid_check_scope_files (T-4413) computed its
"touched" file set via _land_touched_paths(worktree, ticket_id), which
called working_diff(worktree, "main") -- a literal string, not the resolved
land target. On this repo, `dev` (not `main`) is the actual land target and
has diverged from `main` by 200+ commits, so merge-base(worktree, "main")
sits far behind every already-landed sibling ticket's own commit on dev.
Every one of those sibling commits' files therefore appeared in the "diff
since merge-base" touched set, even though none of them is actually touched
by the ticket being landed -- the "scoped" check was, in practice, an
unscoped check with extra overhead.

Fix: thread the resolved land target branch (T-3787's own
_resolve_land_target_branch / cfg.ticket_land_branch, the same resolution
land() itself already applies) through as the diff base instead of the
literal "main". When the target genuinely is "main" (unconfigured
ticket_land_branch, root checked out on main), _resolve_land_target_branch
returns "main" and behavior is byte-for-byte unchanged -- verified by the
existing test_rapid_check_scope_files_includes_touched_and_dependents test,
which still passes unmodified with the new target_branch parameter
defaulting to "main".

Direct-dependents-came-back-as-0 investigation: read frob/graph/affects.py.
_dependents_of()/affects() walk ONLY `frob:uses-contract` directive edges
(a reverse "who declares uses-contract on this symbol" edge), not a general
call graph / import graph. This means a 0 direct-dependent count for a
252-file touched set is not evidence of a broken graph walk -- it is the
expected value whenever none of those 252 files' symbols happens to be
named in a frob:uses-contract directive anywhere else in the tree, which is
the common case (uses-contract is a deliberately-declared, sparse edge, not
an automatically-inferred one). No code defect found in the affects() walk
itself; added an INFO log line explaining this mechanism specifically for
the 0-count case, so a future operator does not have to re-derive this from
reading affects.py from scratch.

Measured numbers:
- New/changed unit tests: 20 passed in tests/unit/test_check_scoped_files.py
  (PYTHONPATH=<WT>/src .venv/bin/python -m pytest -q -p no:cacheprovider
  -p no:xdist tests/unit/test_check_scoped_files.py)
- Regression check: 98 passed in tests/test_ticket_work_and_land_finish.py
  (same runner)
- ruff check + ruff format --check: clean on both changed files
- ty check: "All checks passed!" on both changed files
- BUG002 repro: the new test was committed ALONE first (commit 715415fa8),
  confirmed FAILED_AT_PARENT via
  `frob ticket evidence T-4547 --designate-repro <node> --base-ref 715415fa8`
  and re-confirmed via `--check-repro --base-ref 715415fa8` (both report
  FAILED_AT_PARENT -- "a real repro, this is what BUG002 wants"). The fix
  itself landed in a separate commit (c4e88a2e7) immediately after.

Why --base-ref 715415fa8 rather than --base-ref dev: dev's own tip (the
worktree's actual merge-base parent before the fix) already contains this
ticket's `frob ticket work`/`start` ledger-transition commits but NOT the
test file at all (T-2025's structural squash-history limitation: a
freshly-added test file does not exist in ANY ancestor of the ticket's own
history until the ticket's own commit adds it). Per docs/modules/
tickets.md#check-repro-post-land-limitation-t-2025 and the tool's own
guidance, the test-only commit's own sha is the correct --base-ref for a
pre-land, in-worktree BUG002 verdict.

Out of scope, not fixed here (nothing found requiring a new ticket):
- No other caller of _land_touched_paths/_rapid_check_scope_files exists
  outside _land_core_invoke, so no other hardcoded-"main" callers needed
  updating.
- affects()'s uses-contract-only semantics is existing, intentional,
  documented behavior (see its own module docstring); not a defect, so no
  ticket filed against it.

Evidence bound (frob ticket evidence T-4547):
- criterion [1] (touched set is diff against land target, not main):
  tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::
  test_land_touched_paths_against_main_includes_unrelated_dev_commit
- criterion [2] (behavior byte-for-byte today's when target is main):
  tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::
  test_rapid_check_scope_files_includes_touched_and_dependents
- designated repro (kind=bug, BUG002): same node as criterion [1],
  confirmed FAILED_AT_PARENT at commit 715415fa8.

Worktree: /home/logan/projects/frob/.claude/worktrees/t-4547
Branch: t-4547
HEAD: 83c2228f1 (chore(tickets): record evidence for T-4547)
git -C <WT> status --short: empty (clean)

Status: READY. Ticket not landed, per instructions ("Do not land").

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py | 83 +++++++++++++++++++++++++++++----
 tests/unit/test_check_scoped_files.py   | 53 +++++++++++++++++++++
 tickets/T-4547/ticket.md                | 13 ++++--
 3 files changed, 135 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_land_touched_paths_against_main_includes_unrelated_dev_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_rapid_check_scope_files_includes_touched_and_dependents` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
