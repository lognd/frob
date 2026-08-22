## Done report

TWO HALVES.

(a) Stop the bleeding. T-1866 (landed earlier, `_refuse_over_broad_
scope_on_start` in `_lifecycle.py`) already turned the OVER_BROAD_
LITERAL_GLOBS warning into a hard refusal at `frob ticket start`, with
`ticket.scope_breadth_ack` as the existing bypass field -- so the
refusal HALF of this ticket's acceptance [0] was already live on main.
The real gap: the ONLY way to set that bypass field was a SEPARATE
command run beforehand (`frob ticket scope-ack <id> --reason ...`, or
`new --scope-breadth-ack` at filing time) -- `start` itself had no way
to ack-and-start in one call, unlike `new`. Wired the SAME
`--scope-breadth-ack`/`--scope-breadth-ack-reason` flag pair (T-2302's
own names/semantics) onto `start` (`_progress.py`), and a new
`_apply_scope_breadth_ack_on_start` helper (`_lifecycle.py`) that calls
the existing `set_scope_breadth_ack` BEFORE `_refuse_over_broad_scope_
on_start` runs, mandatory-reason enforced (refuses immediately if
`--scope-breadth-ack` has no reason -- an unackable ack must not
silently no-op). Adds no new mechanism, no new field -- a second write
path into the one T-1484/T-1866/T-2302 already built.

(b) Narrowed the 20 tickets that appeared on EVERY contended test file
row, per-ticket judgement, reading each one's body:

Narrowed (14) -- to their own ledger shard for decomposition-pending
epics/umbrellas (their OWN body says "children to file at design time"
or "split into further child tickets"): T-1135, T-1137, T-1597, T-1607.
To concrete files, using this repo's OWN established conventions
(confirmed via `ls`, not guessed) -- per-language walker naming
(`src/frob/lang/_walk_<lang>.py`), the shared fixture dir
(`tests/fixtures/lang/**`), the existing lang/conformance/support test
suites, and the repo's single `docs/modules/lang.md`: T-1599, T-1600,
T-1601, T-1602 (plus `_walk_c.py`, since its own body asks whether CUDA
is a distinct adapter or a C dialect flag), T-1603, T-1604, T-1606 (the
two shared, non-per-walker lang files plus the existing fmt-directive
test file). To files the ticket's OWN body enumerates explicitly:
T-1654 (6 named files plus conftest.py, referenced by name in its own
plan), T-1660 (3 CONFIRMED sites named in its own body). Partially
narrowed, documented gap: T-1666 (top 5 named files by finding count
plus tests/unit/strata/**; its own body says "10+ more files with 1-9
each" are NOT individually enumerated -- narrowing further would be
guessing, so the remainder is left for a follow-up `scope --add` once
that triage happens).

Left broad, with reasoning (do NOT narrow by guessing) (6): T-1608
(the whole-epic cross-language integration validator -- inherently
repo-wide by design, its own job is proving the obligation graph works
across every adapter at once). T-1609 (explicitly gated to run only
after everything else is drained -- docs completeness/vestigial
cleanup/waiver audit, each inherently repo-wide). T-1614 (RUNS LAST,
audits every `frob:waive` directive in the repo -- cannot be scoped to
a subset by definition). T-1656 (LARGE001 remainder: its own body
explicitly says only the top 5 of 48 candidate files have been examined,
"everything below rank 5 (43 more files) has not been examined at all"
-- narrowing further requires doing the ticket's own investigation
work first). T-1661 (TEST005 remainder: 55 findings reported only as
PACKAGE-level counts, no enumerated symbol/file list in the ticket body
to narrow against). T-1945 (mass-reformat of 77+265 drifted files,
explicitly parked as "ACCEPTED, KNOWN, UNACTIONED debt" -- inherently
repo-wide, narrowing to 342 individual paths would be its own
unreviewable-diff problem the ticket's own body already rejected).

VERIFICATION.

frob ticket contention on tests/conftest.py:
  BEFORE: 20 tickets (T-1135, T-1137, T-1597, T-1599, T-1600, T-1601,
  T-1602, T-1603, T-1604, T-1606, T-1607, T-1614, T-1654, T-1656,
  T-1660, T-1661, T-1666, T-1945, plus 2 more from the same set)
  AFTER:  7 tickets (T-1608, T-1609, T-1614, T-1654, T-1656, T-1661,
  T-1945) -- 1 (T-1654) deliberately still declares conftest.py itself
  (its own body's real target), 6 are the deliberately-left-broad set
  above with recorded reasoning. A 65% reduction on the single most
  damaging row, and the specific 20-ids-on-every-row shape is gone.

must-still-refuse: verified directly via `_globs_intersect` (the same
primitive `leased_by`'s overlap check uses) that T-1600's and T-1601's
narrowed scopes STILL genuinely overlap on their shared conformance
suite files (tests/test_lang.py, tests/test_lang_conformance_gate.py,
tests/test_lang_support.py, docs/modules/lang.md, tests/fixtures/
lang/**) -- narrowing did not weaken lease detection, siblings that
really do share files still correctly contend.

must-now-start: verified directly that T-1660's and T-1606's narrowed
scopes have ZERO overlap (`_globs_intersect` returns nothing for any
pair) -- two tickets on genuinely different test files are now
concurrently startable, which was impossible under the old tests/**
declarations.

Filed: none -- no out-of-scope defect found while implementing this
fix. T-1219 (also epic-shaped, NEEDS DECOMPOSITION per fleet_status.py)
was deliberately left untouched: its scope (`src/frob/lang/**`,
`frob-core/**`) contains no OVER_BROAD_LITERAL_GLOBS entry and was not
part of the 20-ticket contention set this ticket's acceptance criteria
target -- out of this pass's scope.

EVIDENCE NOTE: acceptance [1]/[2]/[3] are additionally bound to three
new self-contained regression tests in TestScopeBreadthNarrowingT2446
(tests/unit/test_app_runners_batch7.py) -- deliberately NOT introspecting
this repo's own live ticket state (a worktree's ledger copy cannot
reliably reflect root's post-narrowing state, the same staleness class
T-2400 fixed for TICK006), instead reproducing the narrowing SHAPE on a
disposable tmp_path fixture: 5 tickets sharing tests/** collapse
tests/conftest.py's declarer count to zero once narrowed to disjoint
files (acceptance [1]'s mechanism); two genuinely disjoint narrowed
scopes show zero _globs_intersect overlap (acceptance [2]); two
genuinely sibling narrowed scopes still overlap (acceptance [3]). The
real repo-wide before/after (20 -> 7 on tests/conftest.py) is recorded
above as the actual measured outcome; these tests lock in the
underlying mechanism so it cannot regress silently.

### Changed
```
 tickets/T-2446/done-report.md | 110 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2446/ticket.md      |  29 ++++++++---
 2 files changed, 133 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_scope_breadth_ack_flag_sets_field_before_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_scope_breadth_ack_without_reason_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_conftest_contention_materially_reduced` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_disjoint_tickets_have_no_scope_overlap` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_sibling_tickets_still_conflict` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2446/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2446/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2446/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2446/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2446/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2446, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
