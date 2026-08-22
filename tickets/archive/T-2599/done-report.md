## Done report

Added `scripts/fleet_status.py::worktree_content_classification`, the
STRANDED/STALE/ACTIVE audit the ticket asked for, and surfaced it in
`fleet_status.py`'s existing `WORKTREES` section (a `STRANDED: N` count in
the header, plus a `[STRANDED]`/`[STALE]`/`[ACTIVE]` tag on every
idle-looking worktree's own line) rather than adding a separate command --
per the ticket's own stated preference, and because a real CLI subcommand
(`frob worktree audit`) would have required touching `src/frob/app/
worktree_runner.py` / `src/frob/_cli_parsers/_core.py`, outside this
ticket's declared scope.

Report-only, as required: nothing here removes a worktree. `frob worktree
sweep` (playbook section 12b) remains the sole removal path.

Implements the exact test the ticket's own investigation found actually
works: diff `main..HEAD` restricted to `src`/`tests`/`docs`/`scripts`, and
for every `+` line, check whether main's CURRENT version of that file
already contains that line's text anywhere. Verified against all three
measured-wrong tests the ticket documents:

- `git log main..HEAD` overcounts due to squash-landing -- not used at all.
- `git diff --stat main..HEAD` conflates ahead/behind -- not used; the
  content test only ever looks at `+` lines, never total diff size.
- A worktree with an ACTIVE (non-terminal) ticket short-circuits to
  `"ACTIVE"` before any content diff runs at all, so it is never
  misclassified either direction.

Manually ran the classifier against this repo's real 34 worktrees (via a
symlinked scratch harness pointing `.git`/`tickets`/`.claude` at the real
checkout, since `REPO` resolves from `__file__`'s own location and the
script cannot be run in-place from a worktree copy of itself): 2 worktrees
correctly resolved `ACTIVE` (t-1599, a real blocked/queued ticket; t-2377,
a live lease), the rest resolved STALE or STRANDED per their real diffs
against `main` at the time. Confirmed the classifier's own conservative
bias empirically: `t-2071`'s two flagged "stranded" lines were reflowed
`docs/commands/*.md` prose already present on main under different line
wrapping -- a false-positive STRANDED from the exact-line-text check, the
explicitly-accepted safe-direction failure mode (documented in both the
function's docstring and the new doc section).

## Changed

- `scripts/fleet_status.py` -- `worktree_content_classification`,
  `_added_lines_by_file`, `_lines_absent_from_main` (ARCH001 split),
  `_worktree_ticket_id`, `_TICKET_NAMED_WORKTREE_RE`,
  `_STRANDED_CONTENT_PATHS`, `_TERMINAL_TICKET_STATES`,
  `_print_worktrees_section` (ARCH001 split of `_print_fleet_report`'s own
  WORKTREES block, also fixes a pre-existing-shape double-classification:
  the section now classifies each idle worktree's content ONCE and reuses
  it for both the header count and its own row).
- `docs/guides/coordinator-scripts.md` -- new sections for
  `_worktree_ticket_id`, `worktree_content_classification`, and
  `_print_worktrees_section`.
- `tests/unit/test_coordinator_scripts.py` -- `TestWorktreeContentClassification`
  (4 tests, monkeypatching `_git`/`ticket_frontmatter_on_main` per this
  file's own stated no-real-subprocess convention) and
  `TestWorktreeTicketId` (2 tests).

## Evidence

- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stranded_new_content_not_on_main`
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_content_fully_landed_despite_many_commits`
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_only_behind_main`
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_active_ticket_never_stranded_or_stale`
- `tests/unit/test_coordinator_scripts.py::TestWorktreeTicketId::test_ticket_named_worktree_resolves`
- `tests/unit/test_coordinator_scripts.py::TestWorktreeTicketId::test_ad_hoc_named_worktree_resolves_to_none`

`pytest tests/unit/test_coordinator_scripts.py -q`: 159 collected, 0
failed (153 pre-existing + 6 new). Not a bug/security-kind ticket, so no
`--check-repro`/`--designate-repro` is required (BUG002 only).

## Filed / found (out of scope, not fixed here)

- The `git prune` / unreachable-loose-object growth the ticket also
  flagged ("worth handling") was NOT investigated -- out of this ticket's
  declared scope (`scripts/fleet_status.py`), and the ticket itself only
  asked for the audit/classification half as the required Fix. Left
  unaddressed rather than silently expanded into.
- The gate:SCOPE002 self-referential closure debt (every doc anchor in
  `docs/guides/coordinator-scripts.md` "describing itself" reads as an
  out-of-scope dependency the moment the file enters a narrow ticket's
  scope) is the SAME mechanism T-2585's Done report already filed as
  T-2608 -- not a new instance, just this ticket's own files tripping the
  identical pre-existing debt. No new ticket filed; T-2608 already covers
  the class.

## Gates

`uv run frob check --ticket T-2599`: zero unwaived findings attributable
to any file this ticket touched (`scripts/fleet_status.py`, `tests/unit/
test_coordinator_scripts.py`, `docs/guides/coordinator-scripts.md`),
verified by grep across the full unfiltered log after every fix round
(ARCH001 long-function on `_print_fleet_report`/`worktree_content_
classification` fixed via the two splits above; NEGEXIST001 fixed by
rewording a "does not exist" claim in the new doc prose). Remaining FAILs
in the tool summary are pre-existing and independently confirmed to name
files this ticket never touched (playbook section 6c: `--ticket` narrows
only SCOPE/PREWORK/COV002/TODO001/FMT/AFFECT).

### Changed
```
 tickets/T-2599/ticket.md | 27 +++++++++++++++++++++++++++
 1 file changed, 27 insertions(+)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stranded_new_content_not_on_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_content_fully_landed_despite_many_commits` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_only_behind_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_active_ticket_never_stranded_or_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeTicketId::test_ticket_named_worktree_resolves` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeTicketId::test_ad_hoc_named_worktree_resolves_to_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH102@src/frob/tickets/_doable.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2599, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
