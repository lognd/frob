## Done report

Changed:
scripts/fleet_status.py::worktree_content_classification
scripts/fleet_status.py::_is_ancestor_of_main
scripts/fleet_status.py::_is_deletion_dominant
scripts/fleet_status.py::_parse_ticket_frontmatter_text
scripts/fleet_status.py::ticket_frontmatter_on_main (docstring only, land_commit field)
scripts/fleet_status.py::_DELETION_DOMINANT_RATIO

Fix: two more precise short-circuits now run before the T-2599 per-line
presence check that reproduced false STRANDED verdicts on real data:
(1) a terminal ticket whose `land_commit` is an ancestor of main's
current tip is STALE unconditionally (exact, ticket-linked); (2) a
diff at least 3x deletion-dominant is STALE (magnitude, for worktrees
with no ticket to consult, e.g. `gate-internals`). Root cause of the
original false positives: a symbol renamed by the code that superseded
it (`_write_baseline` -> `_write_baseline_cas`) has no byte-identical
counterpart line on main, so exact-line-text matching alone misread
fully-landed work as stranded.

Evidence:
tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_superseded_symbol_with_landed_terminal_ticket_is_stale  (designated BUG002 repro, FAILED_AT_PARENT verified against 0a76c49c8)
tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_genuinely_new_symbol_absent_from_main_is_stranded
tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_far_behind_main_with_no_ticket_is_stale
tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_terminal_ticket_land_commit_is_ancestor_of_main
tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stranded_survives_terminal_ticket_with_unlanded_land_commit
tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_deletion_dominant
tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stranded_survives_a_small_mostly_additive_diff

The Live-Git test class runs `worktree_content_classification` UNMOCKED
against a real `git init` fixture repo with genuine commits, `git
worktree add`, and real subprocess `git diff`/`git show`/`git
merge-base` output -- not hand-written diff-text fixtures -- per the
ticket's mandatory requirement that at least one check exercise real
git plumbing, since the ORIGINAL T-2599 unit tests all passed while the
shipped behavior was wrong.

Real-repo measurement (mandatory positive control, run against the
actual fleet worktrees under /home/logan/projects/frob/.claude/worktrees,
same idle-600s threshold, via `_print_worktrees_section`):

  BEFORE (T-2617 filed, T-2599's shipped code): STRANDED: 18
  AFTER (this fix):                             STRANDED: 1

  t-2576 (landed T-2576):        STRANDED -> STALE   (correct: landed)
  t-2593 (landed/dropped T-2593): STRANDED -> STALE   (correct: landed)
  gate-internals (13448m idle, no ticket): STRANDED -> STALE (deletion-dominant fallback)
  t-1599 (queued, no lease):     ACTIVE (unchanged -- see follow-up filed below)
  t2602-t2603 (ad-hoc name, no ticket resolves): remains STRANDED
    (274 deletions / 93 insertions = ratio 2.9, below the 3.0 threshold;
    its diff touches src/frob/app/ticket_runner/_rapid_sweep.py +
    tests/unit/test_rapid_sweep.py, neither in either underlying
    ticket's declared scope -- a legitimate, not obviously false,
    STRANDED call an operator should look at)

Filed: T-2625 ("worktree classifier: ACTIVE verdict does not
distinguish queued-idle from a live lease") -- T-1599's own ACTIVE
false-comfort case from this ticket's body; needs a second signal
(`ticket_lease`) beyond what this fix already reads, and mixing it into
this STRANDED bug fix would have obscured BUG002 evidence binding for
two unrelated failure modes.

Gates: `frob check --ticket T-2617` -- gate:SCOPE 0 errors (was 3
SCOPE001 before scope was widened to cover the docs/tests files this
fix also touched); gate:ARCH 0 errors attributable to this change (the
one ARCH001 finding on `worktree_content_classification` from an
earlier draft, 91 lines vs threshold 60, was fixed by trimming the
docstring to summary + doc-file pointer, now 44 lines; the remaining 2
repo-wide gate:ARCH errors are pre-existing, in src/frob/release/_cli.py
and src/frob/tickets/_store.py, untouched by this ticket). No other
gate family shows a finding inside scripts/fleet_status.py or
docs/guides/coordinator-scripts.md attributable to this diff (checked
gate:DOC/DRIFT/DOCENUM/PERF/RENDER/PII/SEC/WIRE/PRE for both file
names -- only pre-existing PERF008 findings at unrelated line
numbers 668/938/1650/1655 in the same file, untouched by this ticket).
`uv run frob test --base main`: touched-set run (17 python tests,
tests/unit/test_coordinator_scripts.py) exit=0 after fixing 3
pre-existing `TestTicketFrontmatterOnMain` tests whose expected dict
needed the new `land_commit` key added.

### Changed
```
 docs/guides/coordinator-scripts.md     |  87 ++++++---
 scripts/fleet_status.py                | 193 +++++++++++++------
 tests/unit/test_coordinator_scripts.py | 342 ++++++++++++++++++++++++++++++++-
 tickets/T-2617/ticket.md               |  75 +++++++-
 tickets/T-2625/ticket.md     |  58 ++++++
 5 files changed, 668 insertions(+), 87 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_superseded_symbol_with_landed_terminal_ticket_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_genuinely_new_symbol_absent_from_main_is_stranded` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_far_behind_main_with_no_ticket_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_terminal_ticket_land_commit_is_ancestor_of_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stranded_survives_terminal_ticket_with_unlanded_land_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_deletion_dominant` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stranded_survives_a_small_mostly_additive_diff` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2617, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
