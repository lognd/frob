## Done report

Fixed `worktree_content_classification`'s ACTIVE short-circuit: previously
ANY non-terminal ticket state (queued/planned/in-progress) read identically
as ACTIVE, so a worktree for a merely QUEUED ticket with nobody holding a
lease anywhere read the same as one genuinely being worked. Measured
instance: t-1599's worktree flagged ACTIVE while T-1599 was queued with no
worktree activity (T-2617's own investigation).

Fix: consult `ticket_lease(ticket_id)` in addition to state.
`in-progress`/`planned` (or any other non-terminal, non-queued state) keep
the ACTIVE short-circuit unconditionally; a `queued` ticket that DOES hold
a live lease record also stays ACTIVE (the safe direction, never proposed
for removal); only a `queued` ticket with NO lease record falls through to
the ordinary content test below it. STRANDED/STALE classification for
every case T-2617 already got right is unchanged -- all four of T-2617's
existing live-git tests (TestWorktreeContentClassificationLiveGit) were
re-run and still pass.

Both-direction controls (all as pytest, see Evidence):
- Positive: queued ticket WITH a live lease record -> still ACTIVE.
- Negative: queued ticket with NO lease record and a stranded-shaped
  diff -> falls through to the content test, correctly STRANDED (mocked
  fixture version).
- Negative (live git, T-1599's own real shape): a queued ticket with no
  lease and genuinely new content on a real git worktree ->
  STRANDED, exercising real `git diff`/`git show` rather than mocks
  (per the T-2617 precedent that unit-mocked fixtures alone missed a
  real defect once already).
- Unchanged-case control: in-progress ticket -> still ACTIVE
  unconditionally, content test never runs.
- Regression: T-2617's own 4 live-git STALE/STRANDED tests re-run and
  pass unmodified (superseded-symbol/land_commit-ancestry,
  genuinely-new-symbol/STRANDED, far-behind-main/deletion-dominant).

Scope was widened to add tests/unit/test_coordinator_scripts.py and
docs/guides/coordinator-scripts.md (SCOPE002 required both). The scope
widen's mirror-to-main step was refused mid-ticket by a concurrent land
in flight (LandInProgress) -- the worktree-local ledger updated
correctly regardless (confirmed: tickets/T-2625/ticket.md carries the
widened scope), and gate:SCOPE reads 0 errors against it locally; the
mirror will catch up automatically on the next successful land per
T-2563's own mirror mechanism.

Verification: `frob check --ticket T-2625 --only scope` 0 errors,
`--only coverage` COV002 clean for both changed files, `--only ty`
clean, `--only archgate --only clones` clean for scripts/fleet_status.py
(2 unrelated ARCH103 errors elsewhere in the repo, not caused by this
change), `--only prework` clean after a resweep.

No overlap with T-2654 (the prior ticket in this series, already
landed) or T-2665 (the worktree-name-resolution false-positive the
coordinator flagged): this fix touches only `worktree_content_
classification`'s own ACTIVE branch, reading `ticket_lease` (existence
check only) -- it never touches `_resolve_worktree_for_in_progress_
ticket`'s pruned-lease-file fallback logic that T-2665 is about.

No new tickets filed -- scoped exactly to T-2625's own body.

### Changed
```
 docs/guides/coordinator-scripts.md     |  15 +++++
 scripts/fleet_status.py                |  24 ++++++--
 tests/unit/test_coordinator_scripts.py | 108 +++++++++++++++++++++++++++++++++
 tickets/T-2625/ticket.md               |  39 +++++++++++-
 4 files changed, 178 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_queued_ticket_with_live_lease_still_active` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_queued_ticket_with_no_lease_falls_through_to_content_test` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_active_ticket_never_stranded_or_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_queued_ticket_no_lease_falls_through_to_real_content_test` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_superseded_symbol_with_landed_terminal_ticket_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_genuinely_new_symbol_absent_from_main_is_stranded` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_far_behind_main_with_no_ticket_is_stale` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
