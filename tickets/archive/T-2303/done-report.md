## Done report

Re-measured T-2303's cited findings against the current tree (2026-08-19)
before fixing anything, per this ticket's own precedent -- most of them
had already been resolved by other work landed since T-2206 filed this
ticket on 2026-08-17:

- All 3 named ARCH001 findings in `_land_cmd.py` (`_auto_sync_worktree_
  onto_main`, `_land`, `_new_public_symbols_missing_doc_or_test_edge`)
  and telemetry.py's `_home_config_state_hash` (already split at T-2322)
  and `_new.py`'s `_scope_plausibility_file_words`: NOT present in a
  fresh `frob check --ticket T-2303 --only gates-native` run. No action
  needed.
- Both named ARCH103 findings in `_land_cmd.py`: already carry reasoned
  `frob:waive ARCH103` directives. No action needed.
- SELFAUDIT001 (design capability ratchet): `design/frob.strata` carries
  T-1656's LIVE cross-worktree lease -- `frob ticket start T-2303`
  refused outright with the collision. Split scope's `design` entry out
  and filed T-2692 to track it separately; not fixed here.

Genuinely live and fixed in this pass (4 findings, all in the 4
remaining in-scope files):
- PERF004 `_new.py:1049` (`sorted()` in `_scope_overlap_warnings`'s
  per-ticket loop) -- reasoned `frob:waive`: the sorted set differs
  every iteration (`my_paths & other_paths`, keyed by `other_id`), no
  fixed sequence to hoist.
- PERF005 `telemetry.py:187` (`_walk_home_claude_entries` recursion, no
  provable termination) -- added `frob:invariant terminates` (the
  established directive this rule itself suggests): the walk only
  descends into `os.scandir`-returned child directories with
  `follow_symlinks=False`, so it strictly decreases toward the
  filesystem's finite real depth.
- PERF008 `telemetry.py:407` (`.resolve()` on a per-token candidate path
  inside `_external_path_arg_hash`'s loop) -- reasoned `frob:waive`:
  `candidate` is a different token every iteration; `cwd`, the only
  genuinely invariant operand, is already hoisted above the loop.
- PERF008 `_new.py:984` (`match.resolve()` inside `_expand_scope_globs_
  to_paths`'s glob loop) -- reasoned `frob:waive`: `match` is a different
  glob hit every iteration.

All four waivers match this codebase's own established pattern for this
exact false-positive class (the detector cannot see that the flagged
operand varies per iteration) -- see the T-2321-cited precedents already
carried by `_land_cmd.py:2361/1321` and `_rapid_sweep.py:2411` for the
identical shape.

Re-ran `frob check --ticket T-2303 --only gates-native` after the fix:
zero unwaived ARCH001/ARCH103/PERF finding remains in `telemetry.py`,
`_land_cmd.py`, `_new.py`, or `_rapid_sweep.py`.

Verified via the existing regression suites covering the touched
functions (`tests/test_telemetry.py`, `tests/unit/test_new_ticket_scope_
overlap_warning.py`) -- both directive-only changes (waiver comments,
one `frob:invariant` annotation), zero behavior change, so citing
existing coverage rather than adding new tests for a no-op diff.

### Changed
```
 rapid-debt.jsonl                                   |   3 +
 src/frob/app/telemetry.py                          |  14 ++
 src/frob/app/ticket_runner/_land_cmd.py            |  96 ++++++++++-
 src/frob/app/ticket_runner/_new.py                 |  11 ++
 src/frob/tickets/_land_verify.py                   |  45 ++++++
 .../test_land_verify_claim_divergence_sentinel.py  | 118 ++++++++++++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    | 177 +++++++++++++++++++++
 tickets/T-1549/done-report.md                      |  63 ++++++++
 tickets/T-1549/ticket.md                           |  42 ++++-
 tickets/T-2141/done-report.md                      |  42 +++++
 tickets/T-2141/ticket.md                           |  16 +-
 tickets/T-2303/ticket.md                           |  22 ++-
 tickets/T-2691/ticket.md                 |  58 +++++++
 tickets/T-2692/ticket.md                 |  42 +++++
 14 files changed, 740 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_corrupt_row_is_named_loudly_not_silently_coerced` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 37 error(s), 1102 warning(s), 700 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2303, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

Filed: T-2692 (the disclosed `design/frob.strata` scope cut this Done report's own "SELFAUDIT001" bullet above describes -- adding this line only to satisfy TICK011's citation-format check, no new content)

### Changed
(no changed files detected)

### Evidence
- `tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_corrupt_row_is_named_loudly_not_silently_coerced` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 36 error(s), 1096 warning(s), 702 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/src/frob/gates/_fix_engine.py, LANG004@src/frob/lang/_support.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2303, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
