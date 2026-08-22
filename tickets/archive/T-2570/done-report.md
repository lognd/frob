## Done report

### What changed

Measured, rather than guessed, whether native git 3-way merge actually
conflicts on this repo's ledger v2 (`tickets/T-####/` directories).
Reproduced two scenarios in a scratch clone:

1. Two branches editing DIFFERENT keys of the same `ticket.md` from a
   common base: native 3-way merges cleanly, zero conflict.
2. Two branches each creating `done-report.md` fresh (an add/add, the
   shape of the real incident this ticket was filed from -- main writing
   land's `error-findings:` claims, the worktree writing its own
   narrative): native 3-way DOES conflict, with real conflict markers.

Investigating case 2 further (reading `_ledger_mirror.py` rather than
stopping at the git-level repro) found the SHARPER, silent variant: the
T-2563 mirror (`mirror_ledger_change_to_primary`) copies the WHOLE
`tickets/T-####/` directory via `shutil.copytree(..., dirs_exist_ok=
True)` for every metadata verb (`scope`/`block`/`priority`/...), even
though `done-report.md` is explicitly `GENERIC_COMMIT_UNMIRRORED` for
its own verb and separately owned by `land`'s `OWN_TRANSACTION` write.
An unrelated `scope`/`block` mirror therefore silently overwrote main's
own `done-report.md` with whatever stale copy sat in the mirroring
worktree -- no conflict markers, just quiet data loss, worse than the
conflict case above.

Decision: **option (c)**, reduce the second writer, implemented at the
mirror's own pathspec/copy boundary rather than a new merge driver.
`_UNMIRRORED_TICKET_FILENAMES = frozenset({"done-report.md"})` is now
excluded from both `_copy_ledger_paths`'s copy step and the mirrored
commit's `git add`/`git commit` pathspecs
(`_mirror_commit_pathspecs`) for `mirror_ledger_change_to_primary`
specifically. `mirror_promote_to_primary` is deliberately left
untouched -- a promote's whole-ticket rename legitimately carries any
existing done report with it, it is not a second writer racing anything.

Rejected (a) native-3-way-is-sufficient-as-is: false as measured above
for the add/add case, and the silent-overwrite variant is not a merge
conflict at all (the mirror writes and commits directly on the primary,
outside any `git merge`), so "resolve conflicts by hand" cannot catch it.

Rejected (b) a dedicated merge driver (built-in or custom): the
`union` driver's precedent (`rapid-debt.jsonl`) is append-only-log
shaped; `done-report.md`/`ticket.md` are not -- a union merge on
conflicting YAML/prose would either produce invalid content or silently
interleave two different narratives. No built-in driver fits this
file's actual semantics, so (c) is strictly better here: it removes the
race by construction instead of trying to merge it well after the fact.

Corrected `docs/guides/agent-playbook.md` section 10 and
`docs/modules/tickets-lifecycle.md`'s "Worktree ledger mirror (T-2563)"
section -- both still told agents to register the retired `frob ticket
merge-driver` once per clone, which predates the ledger v2 migration and
now contradicts `.gitattributes`' documented retirement of that driver
for this repo.

Live instance during this ticket's own work: merged `main` twice while
this ticket was in flight (main moved substantially today across
T-2668/2669/2670/2625/2654/2653/2672/2673 and others) -- both merges
resolved with ZERO conflicts on `tickets/T-2570/*`, because no other
writer touched this ticket's own files during that window. No live
two-writer conflict on my own ticket's files was observed; the
constructed repro above is the evidence for the conflict shape itself.

### Filed

- `T-2675` (renumbers at land): `test_derived_match`'s
  hardcoded `MIRRORED_LEDGER_VERBS` expected set is stale after T-2624
  added `"runs-last-parallel-safe"` -- pre-existing, unrelated to this
  ticket, confirmed by reproducing it against a clean `main` merge
  before any of my own edits.

### Evidence

- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorCarriesNothingElse::test_mirror_does_not_clobber_primarys_own_done_report`
  -- the repro, designated via `--designate-repro` against commit
  `0309d33fe` (the repro-test-only commit, before the fix commit
  `46a20e3bb`): `FAILED_AT_PARENT`, confirmed.
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_attachment_file_reaches_primary`
  -- positive control: attachments still mirror (the exclusion is
  filename-scoped, not directory-scoped).
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_scope_edit_from_worktree_is_visible_on_primary`
  -- positive control: an ordinary `scope` mirror still reaches main.
- Full targeted file: `uv run pytest tests/unit/test_ticket_runner_ledger_mirror.py`
  -- 19/20 pass; the 1 failure is the pre-existing, out-of-scope
  `test_derived_match` drift filed above (reproduces identically before
  any of my edits).

### Gates

`frob check --ticket T-2570 --budget 500`: `gate:SCOPE`/`gate:PRE`
(the two families this flag actually scopes) show findings that predate
this ticket's diff (repo-wide contention noise, per the run's own
`gate:scope-note`); `frob check --land-parity` (run once, before the
final main merge) reported exactly 2 unscoped errors -- `CLAUDE001
.claude/hooks/sync-claude-config.py` and `CYCLE001
src/frob/__init__.py` -- both pre-existing repo-wide conditions
unrelated to this ticket's 4-file diff (the `Claude config DRIFT`
banner and this cycle finding are present on every command this
session, before and after my changes). Not waived, not fixed here:
outside this ticket's declared scope.

### Changed
```
 docs/guides/agent-playbook.md                  | 74 ++++++++++++++++++-------
 docs/modules/tickets-lifecycle.md              | 35 +++++++++---
 src/frob/app/ticket_runner/_ledger_mirror.py   | 75 ++++++++++++++++++++++----
 tests/unit/test_ticket_runner_ledger_mirror.py | 45 ++++++++++++++++
 tickets/T-2570/ticket.md                       |  6 ++-
 tickets/T-2675/ticket.md             | 40 ++++++++++++++
 6 files changed, 239 insertions(+), 36 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorCarriesNothingElse::test_mirror_does_not_clobber_primarys_own_done_report` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_attachment_file_reaches_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_scope_edit_from_worktree_is_visible_on_primary` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 41 error(s), 777 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV005@src/frob/app/ticket_runner/_ledger_mirror.py, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2570, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
