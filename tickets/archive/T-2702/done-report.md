## Done report

Found and fixed why T-2690's phantom-refile fix still re-filed duplicates
in production (T-2699, T-2701) despite its own four unit tests passing.

Investigation method (per instruction: instrument the real land path,
do not reason from the unit tests): checked out the actual pre-land tree
state at T-2141's own land parent commit (33ed66b3f) in a scratch
worktree and called the real `fix_tick006_phantom_refile` directly,
scoped by `ticket_id="T-2141"` exactly like `_tier_a_pre_land_step`
does. Confirmed T-2141's own Done report never cited the phantom draft
at all (0 hits in both `ticket.md` and `done-report.md`), which ruled
out `ticket_id` scoping as the mechanism. Traced every real call site
of `apply_tier_a_fixes`/`fix_tick006_phantom_refile` in
`_land_cmd.py` and confirmed all thread `ticket_id` correctly.

Root cause A: `_resolve_via_git_rename`'s docstring EXPLICITLY defended
collapsing "git spawn failed/timed out" into the same `None` a genuine
non-rename returns ("exactly like a genuinely nonexistent id") --
directly contradicting this same module's own T-2391 doctrine
(`MergeTargetKnownIds.measured=False` refuses to file rather than risk
a false positive). Confirmed the rename commit (a44f96e60, R099
tickets/T-draft-be1e79b5 -> tickets/T-2678) WAS reachable via `git log
--all` well before both mis-filings, and a fresh call resolves it
correctly today -- consistent with a TRANSIENT git-spawn failure/
timeout under the exact concurrent-land contention this drive measured
(background auto-gc packing + "too many unreachable loose objects" on
every commit, multiple exit-143s, 3-5 simultaneous lands).

Root cause B (T-2701 specifically): `_find_exact_duplicate`'s
`load_all(root)` read only the CALLING land's own worktree ledger --
`root` for the pre-land Tier-A step is the worktree, not the merge
target. T-2251's own worktree ledger was cut before T-2141's land
(running concurrently, ~31 minutes earlier, different worktree) filed
its own byte-identical recovery ticket, so the duplicate check never
saw it. Reproduced this exact race in
`test_tick006_two_lands_citing_same_draft_produce_at_most_one_ticket`
using two independent git checkouts (a "main" and a "worktree_b" clone
taken before the first land's own filing).

Fix: `_resolve_via_git_rename_measured` returns `(resolved_id,
measured)`; `measured=False` (any git spawn failed/timed out/exited
nonzero) now refuses to file anything for that citation this pass,
same posture as the top-level `merge_target_ids.measured=False` check.
`MergeTargetKnownIds` gains a `root` field (the merge target's own
checkout path, already resolved by `_resolve_merge_target_known_ids`);
`_tick006_try_resolve_without_filing`'s duplicate check now ALSO reads
that root fresh, in addition to the caller's own (possibly stale)
`root`, closing the concurrent-land race.

Mandatory controls (all real, not mocked-away): (1) a land citing a
RENAMED draft still files nothing and resolves correctly once the
transient failure clears (`test_tick006_git_rename_lookup_failure_
files_nothing_never_treated_as_confirmed_non_rename` +
`test_tick006_lookup_failure_then_clean_retry_recovers_correctly`);
(2) a land citing a GENUINELY lost draft still recovers (pre-existing
`test_tick006_genuinely_lost_draft_still_caught_no_rename_no_
duplicate`, unmodified and still passing -- confirms this fix did not
trade a false-positive for a false-negative); (3) two lands citing the
same draft in quick succession produce at most one ticket
(`test_tick006_two_lands_citing_same_draft_produce_at_most_one_ticket`).

The third control is designated as this bug's own repro (T-1929):
committed the test alone first (e91058cd0), confirmed
FAILED_AT_PARENT via `--check-repro`, then committed the fix on top.

Also fixed incidentally: ARCH001 (split
`_resolve_via_git_rename_measured`'s candidate-commit scan into
`_tick006_check_rename_candidate`), DOC007 (my own `frob:tests`
directives used pytest's `Class::method` form instead of this repo's
dotted `Class.method` convention -- also moved them off the test
methods themselves onto the production functions they cover, where
they belong), AFFECT001 (added a T-2702 paragraph to
docs/modules/gates.md's TICK006 section).

Gates: `frob check --ticket T-2702` clean of any finding in this
ticket's own files (Errors section shows nothing under _fix_engine.py/
_land_cmd.py/test_gates.py/gates.md; remaining errors are pre-existing
repo-wide baggage, e.g. the import-cycle warning, unrelated to this
change).

### Changed
```
 docs/modules/gates.md                   |  18 ++
 src/frob/app/ticket_runner/_land_cmd.py |   4 +-
 src/frob/gates/_fix_engine.py           | 269 ++++++++++++++++++++++------
 tests/test_gates.py                     | 301 ++++++++++++++++++++++++++++++++
 4 files changed, 533 insertions(+), 59 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_git_rename_lookup_failure_files_nothing_never_treated_as_confirmed_non_rename` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_lookup_failure_then_clean_retry_recovers_correctly` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_two_lands_citing_same_draft_produce_at_most_one_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 38 error(s), 1972 warning(s), 703 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2703/ticket.md, DOC006@tickets/T-2704/ticket.md, DOC006@tickets/T-2705/ticket.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2702, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
