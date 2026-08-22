## Done report

Root cause confirmed by reading the code (matches the ticket's own
inference): `_tier_a_pre_land_step` resolves TICK006's phantom-citation
check via `load_active(worktree)` -- the worktree's OWN pre-merge ledger
-- and this whole step runs strictly BEFORE `frob ticket land`'s merge
into main. A citation naming a ticket a sibling agent or the coordinator
filed on main after this worktree's cut is invisible to that read and
gets treated as phantom.

Fix: `fix_tick006_phantom_refile` now accepts an optional
`merge_target_ids: MergeTargetKnownIds | None` parameter, threaded
through `apply_tier_a_fixes`/`TIER_A_HANDLERS` alongside the existing
T-1548 `ticket_id` parameter (every OTHER handler ignores it, same
uniform-signature precedent). `frob ticket land`'s own call site
(`_tier_a_pre_land_step`, `_absorb_pre_land_fixes`) now resolves it via
a new `_resolve_merge_target_known_ids(root)` -- a plain disk read of
`root` (the land's actual merge target, already the resolved primary
checkout by this point per T-1884) taken BEFORE this land's own merge
touches it, since only one land runs against a given root at a time.

Both mandatory controls:
- must-still-fire: a citation absent from BOTH the worktree's own
  ledger/archive AND the merge target still files a recovery ticket
  (test_tick006_genuinely_nonexistent_id_still_fires_with_merge_target).
- must-now-be-silent: a citation present in `merge_target_ids.ids` (i.e.
  filed on main after the worktree was cut) files nothing
  (test_tick006_id_on_merge_target_but_not_worktree_is_silent).
- NOT_MEASURED: `_resolve_merge_target_known_ids` sets `measured=False`
  (not a guessed-empty set) whenever EITHER the merge target's active
  ledger OR its archive fails to load (an archived-on-main id is just as
  capable of looking phantom as a genuinely nonexistent one) --
  `fix_tick006_phantom_refile` then files NOTHING for the whole pass
  rather than risk a false positive (doctrine T-2391)
  (test_tick006_not_measured_merge_target_files_nothing,
  test_unloadable_active_ledger_is_not_measured,
  test_unloadable_archive_is_not_measured).

A bare `frob check --fix` (no land context) passes `merge_target_ids=
None` and is byte-identical to pre-T-2400 behavior
(test_tick006_known_id_is_never_touched,
test_tick006_refiles_and_rewrites_citation both still pass unchanged).

PORTABILITY (T-2384): no hardcoded repo layout/package name -- reuses
`load_active`/`load_archive`, the same storage-mode-agnostic primitives
every other caller in this module already uses.

Filed: none -- no out-of-scope defect found while implementing this fix.

### Changed
```
 tickets/T-2400/ticket.md | 33 +++++++++++++++++++++++++++++----
 1 file changed, 29 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_id_on_merge_target_but_not_worktree_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_nonexistent_id_still_fires_with_merge_target` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_not_measured_merge_target_files_nothing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_measured_unions_active_and_archived_ids` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_active_ledger_is_not_measured` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_archive_is_not_measured` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/gates/_fix_engine.py, ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2400/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2400/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2400/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2400, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
