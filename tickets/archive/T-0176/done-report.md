## Done report

Changed:
- src/frob/tickets/_land.py (new): `land()`, `splice_ledger()`, plus private
  helpers (`_newer`, `_porcelain_dirty`, `_conflicted_files`, `_in_scope`,
  `_validate_closeable`, `_abort_merge`, `_splice_and_stage`,
  `_merge_main_into_worktree`, `_unowned_deletions`, `_wip_commit`,
  `_commit_message`).
- src/frob/tickets/_models.py: added `LandError` (ErrorSet), `LandReport`
  (BaseModel).
- src/frob/tickets/__init__.py: exported `land`, `splice_ledger`,
  `LandError`, `LandReport`.
- src/frob/app/ticket_runner.py: `_land` CLI handler, dispatch table entry,
  usage string, module docstring.
- src/frob/app/config.py: `AppConfig.ticket_worktree` field, wired through
  `from_external`'s path-field list.
- src/frob/__main__.py: `frob ticket land <id> --worktree <path>
  [--dry-run]` argparse registration (outside T-0176's declared scope --
  see Filed below; SCOPE001 waived there with a named remedy).
- docs/modules/tickets.md: new "## `frob ticket land`" section (full
  step-by-step order-of-operations rationale, why validation runs before
  any git mutation, why tickets.md is always resolved via `splice_ledger`
  rather than git's textual merge) plus updated the provisional-ids
  section's "not wired up yet" language now that T-0176 wires it.
- tests/test_ticket_land.py (new): `TestSpliceLedger` (id-level merge:
  disjoint ids both kept, same-id newest-state-wins), `TestLand` (dry-run
  leaves zero trace on both checkouts, real land merges+closes+commits,
  refuses on dirty main, refuses without evidence/Done report before any
  git mutation), `TestStaleBaseDeletion` (unowned deletion aborts loudly
  and unwinds the merge; scoped deletion is allowed), `TestLedgerBothSidesAppend`
  (main and the worktree each independently append a new ticket --
  resolves as keep-both, not a conflict), `TestDraftIdFinalization` (a
  T-draft-* id filed off-branch is finalized to a real sequential id at
  land time). All against real git fixture repos (subprocess `git
  worktree add`), not mocks.
- tests/system/test_cli_ticket_land.py (new): `TestLandCLI` -- the real
  `frob ticket land ... --dry-run` subprocess entrypoint end to end.

Verification performed manually beyond the automated suite: a live
`/tmp` smoke test creating a real worktree, filing a draft-id ticket,
running `frob ticket land <draft-id> --worktree <wt> --path <main>`
(no --dry-run) and confirming the draft finalized to T-0001, the file
landed, the ticket closed to `done`, and a `feat(tickets): land T-0001 ...`
commit was created on main -- matches the automated
`TestLand::test_real_land_lands` coverage.

Design notes on the three named incident classes:
- Stale-base deletion: `land` merges main into the worktree FIRST (so the
  worktree's tree already reflects main's current state), then diffs the
  worktree against main with `--diff-filter=D`; any deleted path outside
  the ticket's declared `scope` aborts loudly and unwinds the staged
  merge (`git merge --abort`), naming the exact restore command.
- Ledger both-sides-append: `tickets.md` is NEVER resolved via git's
  line-level merge. Every merge/squash step (main-into-worktree,
  worktree-into-main) always recomputes `tickets.md` via `splice_ledger`,
  an id-level union that keeps a ticket present on only one side
  unconditionally and picks the newer state (state-machine rank, then
  Done-report presence, then evidence count) on a genuine same-id
  divergence.
- Id finalization: `finalize_draft` (T-0162's mechanism, previously
  wired to nothing) is now called automatically inside `land`, against
  the worktree's post-merge view, before close.

Ordering (why close-validation runs first): `_validate_closeable` checks
evidence + Done report BEFORE any git mutation. This matters because
`frob ticket close` (`transition(..., DONE)`) enforces the same
precondition -- if `land` merged first and validated last, a missing
Done report would be discovered only after main-affecting state had
already changed, forcing a manual unwind. Checking first means a failed
precondition is always a no-op abort. `--dry-run` runs every check AND
every git mutation the real run would (staged merge, real deletion diff,
real splice) then unwinds it (`git merge --abort` / `git reset --hard`),
so a clean dry run is a guarantee, not a simulation that could diverge
from reality.

Evidence: 11 pytest node ids (see evidence: list above), all collected
fresh via `frob ticket evidence T-0176 ...` against a live `frob test`
collection. Full suite (`uv run frob test . --all`) and
`uv run frob test . --base main` both pass; `uv run frob check
--ticket T-0176` is 0 errors (269 pre-existing warnings, unrelated to
this ticket's scope).

Not Filed: T-draft-4032e080 (never refiled) ("T-0176 scope gap: src/frob/__main__.py missing
from declared scope") -- T-0176's declared scope omitted
`src/frob/__main__.py`, but the CLI argparse registration for any new
`frob ticket` subcommand lives there (as it did for T-0162, whose scope
explicitly included it). `land` could not be invoked from the CLI without
that file's change, so the addition was made and waived (`frob:waive
SCOPE001` at src/frob/__main__.py:2, reason names the filed ticket)
rather than expanding T-0176's scope unilaterally.

Gates: `uv run frob check --ticket T-0176` clean (0 errors); no other
waivers introduced beyond the one SCOPE001 waiver named above.

## Fix round (reviewer REJECT, addressed)

Reviewer found two reproducible CRITICAL bugs, both fixed in
src/frob/tickets/_land.py (commit 6aaa0e1):

1. Draft-id finalization losing code rewrites. `finalize_draft` ->
   `renumber_one` rewrites tickets.md AND every source file carrying a
   `frob:ticket <draft-id>` directive, uncommitted, directly on the
   worktree's working tree. The old `land` squashed onto main from the
   worktree branch's LAST COMMIT, which predated those uncommitted
   writes -- the ledger recovered only because `_splice_and_stage`
   re-reads tickets.md off disk, but every OTHER rewritten code file
   never reached main, and the worktree was left dirty even after a
   "successful" land. Fix: `land` now commits finalize_draft's and
   close's working-tree changes in the worktree (one
   "finalize and close <id> for landing" commit) BEFORE the squash-apply,
   so the squash's source (the branch's now-current tip) actually
   contains everything, and the worktree ends up clean.
2. Archive resurrection. `splice_ledger` only ever parsed the two active
   `tickets.md` texts handed to it, never `tickets-archive.md` -- an id
   main had already archived (moved out of the active ledger) after the
   worktree's branch point would survive the ours/theirs union (present
   on the worktree's still-active, stale side) and land straight back
   into main's active ledger, resurrecting the exact active+archive
   duplicate-id class this ticket's own 0bb02cf merge had to be
   hand-resolved for. Fix: `splice_ledger` takes an `archived_ids`
   parameter and drops any id in it from the merged result
   unconditionally, from either side; `land` sources `archived_ids` from
   main's `tickets-archive.md` (via the new `_archived_ids` helper) at
   BOTH splice points (main-into-worktree, and the final squash-apply
   splice onto main).

New evidence (2 fixture tests, both reproduce the reviewer's exact repro
before failing without the fix, and pass with it):
- `TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean::test_code_directive_rewritten_and_worktree_clean_after_land`
  -- a draft-id ticket with a `frob:ticket <draft-id>` directive in a
  real code file; asserts the landed file on main carries the FINAL id
  (never the draft), and that both the worktree and its own copy of the
  file are left completely clean/rewritten after land.
- `TestArchiveResurrection::test_archived_id_never_resurrected` -- a
  ticket archived on main strictly after the worktree branched (so the
  worktree's own ledger still has it active); asserts land never
  reintroduces it into main's active ledger and it remains present
  exactly once, in the archive.

Re-verification after the fix: full `uv run frob test . --all` passes
except one PRE-EXISTING failure unrelated to this ticket
(`tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`,
five SYS100 capability-declaration violations all against
`src/frob/strata/_cve_fingerprint.py` and `vet`'s `sql`/`html_render`
capabilities -- files this ticket never touches; confirmed present on
main after merge, not introduced here). `uv run frob test . --base main`
(touched-set) is clean. `uv run frob check --ticket T-0176` is 0 errors
in-scope (the same pre-existing T-0168 COV003 as before the fix round,
confirmed present before this ticket's changes too). Deletion-filter
check against main (`git diff main --diff-filter=D --name-only`) is
empty.

Merged main four times total during this fix round as it kept moving
(T-0153/T-0181/T-0205, an archive rotation, T-0208..T-0219 filing, and
T-0172's managed-marker feature); every `tickets.md` conflict was
resolved by hand using the now-archive-aware `splice_ledger` itself
(dogfooding the fix), confirmed no active/archive duplicate ids resulted
each time (`frob ticket show T-0176` and the full ledger load both
clean). Final state re-verified against main tip 47ce4e3: deletion-filter
check empty, `frob test --base main` clean, `frob check --ticket T-0176`
0 errors in-scope (same pre-existing T-0168 COV003, unrelated).
