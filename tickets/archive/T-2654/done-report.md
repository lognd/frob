## Done report

Added `blocked_in_progress_leases()` to scripts/fleet_status.py: flags a
`state: in-progress` ticket whose `blocked_by` still names an open
(not done/dropped) blocker -- the T-2377 shape (in-progress, blocked by
a still-queued blocker, holding a live write lease for nine hours) --
distinct from and independent of T-2651's no-worktree LEAK detection.

Shares the directory-walk-plus-parse loop with
`in_progress_ticket_scope_leases` via a new `_iter_in_progress_ticket_
frontmatter` generator (extracted after `frob check --only clones`
flagged DUP001 at 95% similarity between the two functions).

Wired into the LEASES section: `_print_fleet_report`'s own LEASES block
was pulled into `_leases_report` (pure gather: computes header + row
strings) and `_print_leases_section` (pure I/O: prints them) -- two
splits were needed (ARCH001/ARCH103 fired twice during this ticket: once
on `_print_fleet_report` itself at 96 lines against a 60-line threshold
after adding the blocked-open branch inline, and again on the first
`_print_leases_section` extraction, which still mixed I/O, string-
formatting, and 4 decision points). A shared `_lease_row` row-formatter
is used by both loops in `_leases_report`. The LEASES header now
reports a `blocked-open` count alongside `live`/`leaked`, and any
flagged row gets a `[BLOCKED-OPEN: <ids>]` suffix distinct from `[LEAK]`.

Also fixed: `ty` flagged `invalid-argument-type` on the extracted
`_lease_row` call (`record.get("ticket_id")` is `Any | None` against a
`str` param) -- coerced with `str(...)` at the call site.

Both-direction controls (all as pytest, see Evidence):
- Positive: in-progress + blocked_by a queued (open) blocker -> flagged,
  naming the open blocker id.
- Negative: in-progress with no blocked_by at all -> not flagged.
- Negative: in-progress whose only blocker is `done` -> not flagged.
- Negative: queued ticket blocked by an open blocker -> not flagged (a
  lease binds only at in-progress, T-0453).
- Integration: a held lease for a blocked in-progress ticket prints
  `[BLOCKED-OPEN: ...]` in the LEASES section and the header count
  reflects it.

Scope was widened to add tests/unit/test_coordinator_scripts.py and
docs/guides/coordinator-scripts.md (SCOPE002 required both once the
test file and doc anchors were touched).

Verification: `frob check --ticket T-2654 --only scope --only prework`
clean; `--only coverage` clean for both changed files (COV002/COV002
after adding frob:ticket T-2654 edges to the two symbols the DUP001/
ARCH refactors modified: `in_progress_ticket_scope_leases` and
`_print_fleet_report`); `--only archgate --only clones --only ty` clean
for scripts/fleet_status.py. `frob check --land-parity` (repo-wide, run
three times across this ticket as the fix evolved) showed 46-60
unscoped errors at various points, none naming scripts/fleet_status.py
or tests/unit/test_coordinator_scripts.py in the FINAL run --
remaining findings are pre-existing repo-wide (DRIFT001 on unrelated
files, COV001/COV003/COV004 on unrelated files, SEC110, WIRE002/003,
etc.), not caused by this change.

No new tickets filed -- this was scoped exactly to T-2654's own body.
Confirmed no overlap with T-2665 (worktree-name resolution false
positive the coordinator flagged mid-ticket): this change never calls
`ticket_lease()`, `_resolve_worktree_for_in_progress_ticket()`, or
`worktrees_touching_ticket()` -- it reads ticket state/blocked_by
directly from ledger frontmatter only.

### Changed
```
 docs/guides/coordinator-scripts.md     |  66 +++++++++-
 scripts/fleet_status.py                | 220 ++++++++++++++++++++++++++++-----
 tests/unit/test_coordinator_scripts.py | 108 +++++++++++++++-
 tickets/T-2654/done-report.md          |  66 ++++++++++
 4 files changed, 429 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_in_progress_with_open_blocker_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_in_progress_with_no_blockers_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_in_progress_with_only_terminal_blockers_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_queued_ticket_with_open_blocker_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_leases_section_flags_blocked_open_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
