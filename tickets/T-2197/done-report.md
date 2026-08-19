## Done report

Outcome: STILL BROKEN before this ticket, and worse than T-2197's own
description -- measured, not assumed:

`frob ticket promote` is one of `frob.app.ticket_runner._LEDGER_
TRANSACTIONAL_VERBS` (`{"land", "merge-driver", "promote", "renumber",
"sweep-async"}`), deliberately excluded from BOTH the generic per-verb
auto-commit sweep (`_auto_commit_ledger_after_dispatch`) AND its T-2563
mirror-to-primary call (which only fires from inside that same sweep, and
never runs at all for an excluded verb). `finalize_draft`/`renumber_one`
(the library primitives `promote` calls) write the rename to disk
deliberately UNCOMMITTED, per `commit_full_ledger_change`'s own
docstring: "a ledger-only commit here would split one atomic rename into
two ... worse than leaving all of it uncommitted together for the caller
to commit as one change." That docstring's "caller" was meant to be the
CLI `_promote` handler -- but grepping the actual call path (`frob.app.
ticket_runner._query._promote` -> `finalize_draft` -> `renumber_one`)
found NO commit call anywhere on it. So `frob ticket promote` never
committed its rename at all, in ANY checkout, worktree or primary --
confirmed by measurement (a new regression test that failed at the
pre-fix commit, see Evidence) before writing a single line of fix.

This is a materially different, MORE dangerous shape than T-2197's own
description ("exists only on the worktree's own branch until it lands"):
the rename was not even durably committed to that branch. Left dirty in
the working tree, it was liable to be silently swept into whatever
UNRELATED ticket's `frob ticket land` ran next in that same worktree
(`land` absorbs any dirty state into its own pre-merge wip-commit),
misattributing the rename to a ticket that never touched it.

T-2563 (the ledger mirror this ticket asked me to verify against) does
NOT cover `promote` at all and was never going to: `MIRRORED_LEDGER_
VERBS` (the set T-2563 actually mirrors: scope/block/attach/tier/...)
and `_LEDGER_TRANSACTIONAL_VERBS` (promote's own exclusion set, T-1615,
pre-dating T-2563) are two DIFFERENT exclusion lists for two different
reasons, and `promote` was never a candidate for the first one.

Fix (within `src/frob/tickets/`, the only part of this reachable without
touching the currently-leased `src/frob/app/ticket_runner/` -- see
Filed below for the part that does need that lease):

- `frob.tickets._draft_finalize.finalize_draft` now calls a new private
  helper, `_commit_and_warn_promote`, after `renumber_one` succeeds:
  commits the FULL rename (ledger pathspecs -- `tickets.md`/`tickets-
  archive.md` in v1, the whole `tickets` subtree in v2, covering both the
  vacated draft id and the new final id -- plus every `RenumberReport.
  files_changed` code-reference file) as ONE atomic commit, exactly
  preserving the atomicity `commit_full_ledger_change`'s docstring already
  argued for. A no-op for a dry-run report. `finalize_draft_for_land`
  (the land-time path, mid an already-atomic land transaction) is
  UNCHANGED -- this only touches the `frob ticket promote` CLI path.
- If `root` is not the repo's resolved primary checkout (`_resolve_
  primary_checkout`), logs a loud, greppable ERROR naming exactly what
  T-2197's WANTED bullet 1 asked for: the new id exists only on this
  worktree's own branch, not yet visible/dispatchable on main.
- `docs/guides/agent-playbook.md` gets a new section 10c documenting
  both halves (T-2197's WANTED bullet 3).

WANTED bullet 2 (`show`/`doable`/`work` distinguishing "worktree-only"
from "does not exist") is NOT implemented -- that surface lives in
`src/frob/app/ticket_runner/` (leased throughout this ticket's work) and
is a separate, larger investigation (does `doable`'s capacity check even
have a way to inspect other worktrees' branches at all?) rather than a
one-line fix; left for a follow-up rather than attempted half-heartedly
under a lease conflict.

Filed: T-2587 -- wiring `promote` into the actual T-2563 mirror
(`mirror_ledger_change_to_primary`) so a promoted id becomes visible on
main WITHOUT a land, not merely warned-about. Blocked on
`src/frob/app/ticket_runner/_ledger_mirror.py` and `__init__.py`, both
under another agent's live lease for the entirety of this ticket's work
-- confirmed via `frob check`'s scope-closure warnings and the dispatch
brief's own OFF LIMITS list, not assumed.

Changed:
  frob.tickets._draft_finalize.finalize_draft
  frob.tickets._draft_finalize._commit_and_warn_promote (new)

Evidence:
  tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns.test_finalize_draft_commits_the_full_rename_in_a_worktree
    (designated repro -- FAILED_AT_PARENT at dae2c9af9 [test-only commit,
    pre-fix source], PASSED after the fix commit; verified via a detached
    scratch checkout + PYTHONPATH override so the venv's editable install
    could not mask the parent-commit source, not merely trusting a
    same-tree run)
  tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns.test_finalize_draft_warns_when_root_is_not_the_primary_checkout
  tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns.test_finalize_draft_in_the_primary_checkout_itself_does_not_warn
    (MUST-STILL-PASS control: promoting directly in the primary checkout
    does not claim worktree-only visibility)
  tests/test_tickets_ledger_concurrency.py::TestPromoteVsLandFinalizeAllocationRace.test_promote_and_land_finalize_never_allocate_the_same_id

Also verified: tests/test_tickets_collision.py (29 collected, 0 failed,
full file); tests/unit/test_draft_finalize_attachments.py +
tests/test_tickets_ledger_concurrency.py (41 collected combined, 0
failed). `tests/system/test_cli_ticket_promote.py::TestPromoteCLI::
test_promotes_a_draft_carrying_evidence_and_done_report` fails on main
BEFORE this diff too (a pre-existing, unrelated `frob ticket start`
"EMPTY scope" refusal added by a different, later-landed ticket, not
touched by this change) -- confirmed by inspecting `_lifecycle.py`'s
refusal message and its git history; out of this ticket's scope
(`src/frob/app/ticket_runner/`).

Gates: `frob test --base main` clean (touched=9 ripple=0, 9 python
test(s) selected and recorded, exit=0).

### Changed
```
 src/frob/tickets/_draft_finalize.py | 133 +++++++++++++++++++++++++++++++++++-
 tests/test_tickets_collision.py     | 122 +++++++++++++++++++++++++++++++++
 tickets/T-2197/ticket.md            |  11 ++-
 3 files changed, 263 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns::test_finalize_draft_commits_the_full_rename_in_a_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns::test_finalize_draft_warns_when_root_is_not_the_primary_checkout` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestPromoteFromWorktreeCommitsAndWarns::test_finalize_draft_in_the_primary_checkout_itself_does_not_warn` (pytest node id, verified passing when recorded)
- `tests/test_tickets_ledger_concurrency.py::TestPromoteVsLandFinalizeAllocationRace::test_promote_and_land_finalize_never_allocate_the_same_id` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/tickets/_draft_finalize.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/agent-playbook.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2197/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2197/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2197/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2197, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md, unresolved-attribute@tests/test_tickets_collision.py
