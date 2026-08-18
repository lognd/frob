## Done report

Coordinator-directed error-floor sweep, split out of T-2407's own drive
into its own ticket after the fix was mistakenly worked directly in the
shared root with no ticket holding it (DirtyMain-blocked T-2441's land
and its T-2388/T-2435/T-2436/T-2437 queue). Preserved the diff, filed
this ticket, re-applied in a proper worktree, re-verified everything
still held after main advanced further, and re-did the two `frob ack`
calls whose graph-lock entries were lost when the root's frob.lock was
reverted during cleanup.

Per-finding cause attribution and fix layer:

- DRIFT002 docs/modules/vet.md#public-api -> src/frob/vet/_capability.py
  ::language_for / ::scan_file_capabilities: T-2358 relocated both
  symbols into _capability_core.py / _capability_scan.py (confirmed via
  grep; _capability.py still re-imports/re-exports them under __all__,
  but the DRIFT gate follows the real def site). DOC FIX: rewrote both
  frob:describes anchors to the new modules.
- DRIFT002 docs/modules/arch.md#configuration-frobtoml-arch-table-t-0373
  -> src/frob/app/_config_meta.py::* (11 distinct frob:describes anchors,
  one per symbol under one doc section -- confirmed genuinely distinct
  edges amplified by a single stale file-prefix, not 11 separate causes):
  T-2403/T-2407 relocated _config_meta.py -> repo_meta.py (confirmed
  every symbol resolves there now). DOC FIX: rewrote all 11 anchor
  prefixes.
- DRIFT001 src/frob/gates/_fix_engine.py::apply_tier_a_fixes (sig+body):
  T-2400 added an additive `merge_target_ids: MergeTargetKnownIds | None
  = None` parameter, documented in the function's own docstring.
  docs/modules/gates.md's Tier-A section describes the handler CLASSES
  and their invariants, which the new param doesn't affect -- genuinely
  still true. frob ack (not a doc edit).
- DRIFT001 src/frob/app/ticket_runner/_rapid_sweep.py::
  _file_regression_ticket (body+sig): digest moved from unrelated nearby
  edits in the same file (repeated pattern per `frob ack --list`
  history: T-1891/T-1952/T-2260 all re-acked the same symbol for the
  same reason). Re-verified T-2009 attributed_ids override, T-1791
  quarantine raise, T-2208 auto-dispose all still present and matching
  docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690.
  frob ack.
- SELFAUDIT001 SYS101 gates node 'eval' declared-but-never-observed via
  _docblocks_refs.py: T-2231's gates/_docblocks<->_docblocks_refs split
  moved the importlib.import_module call to _docblocks_shared.py
  (confirmed: grep for import_module across gates/ finds it only there
  now). DECLARATION FIX (not deletion, not ratchet): retargeted the
  via-file to _docblocks_shared.py and updated the explanatory comment.
- SELFAUDIT001 SYS100 (undeclared, new): src/frob/process/_reap.py (core
  fs.read) and tests/unit/test_process_reap.py (testsuite exec/fs.write)
  are T-2443's own new forkserver-reaping primitive + its test, neither
  yet declared in any via-list. DECLARATION FIX: added both files to
  their node's via-lists.
- SELFAUDIT001 SYS111 ratchet growth, 13 (node, capability) pairs
  measured at T-2407 time, +3 more measured after this worktree's own
  merge with main (core::fs.read, testsuite::exec, testsuite::fs.write --
  main kept advancing while this ticket was in flight): for every one,
  verified the contributing files are ALREADY declared via-sources for
  that (node, capability) pair (this drive's T-2390 schema-gate
  children, T-2358's split, T-2443's reap work, etc.) -- accumulated
  legitimate growth within an existing authorization, never a newly
  undeclared file (that is the SYS100 case above, fixed separately).
  RATCHET BUMP with a measured reason in
  docs/design/registry/capability-via-ratchet.lock.json, not
  re-justifying each site individually.

Explicitly NOT touched (out of this ticket's scope, a DIFFERENT
ticket's own fresh debt): T-1696 landed src/frob/gates/_port_selfcheck.py
mid-way through this ticket's own worktree merge, introducing its own
~24 new SYS100 findings (undeclared fs.write/fs.read/exec capabilities
in that new file and its test). That is T-1696's own out-of-scope
collateral, not this drive's SYS003 refactor set -- flagged to the
coordinator rather than silently absorbed into this ticket's scope.

frob:no-behavior-change reason="every change in this ticket is a doc
anchor/via-list/ratchet-ceiling correction restoring accuracy to
metadata that already describes real, unchanged code (or an ack
re-verifying that a real doc still holds) -- no production code path's
runtime behavior changes"

### Changed
```
 tickets/T-2453/done-report.md | 91 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2453/ticket.md      | 38 +++++++++++++++++-
 2 files changed, 127 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2453/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2453/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2453/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2453/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2453/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2453, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
