## Done report

Added four Tier-A `--fix` handlers to `src/frob/gates/_fix_engine.py`
(T-1261 batch 2), continuing T-1138/T-1177's shape: none invents new
rewrite logic, each calls the remedy its own finding message already
names verbatim.

- `fix_fmt001_directive_wrap`: FMT001 (over-long `frob:` directive
  comment) -- calls `frob.gates._fmt_directives.format_paths` in write
  mode over `root` (already idempotent, so this IS the fix).
- `fix_reg010_registry_sync`: REG010 (missing `CHK-GATE-<rule>` registry
  entry) -- calls `frob.registry._staleness.sync_gate_rule_entries`
  directly (same function `frob registry audit --sync-gate-rules`
  wraps). REG008 (stale `handled_by:` cross-ref) is a different,
  genuinely Tier-C shape and stays unhandled.
- `fix_rel002_release_sync`: REL002 (derived release artifact disagrees
  with `.frob-release.json`) -- calls the existing `frob.release` sync
  functions (`authoritative_version`/`rewrite_pyproject_version`/
  `changelog_skeleton_entry`, plus `uv lock`), the same ones `frob
  release sync` dispatches to. Never writes `.frob-release.json` itself.
- `fix_waive004_stale_waiver`: WAIVE004 (a `frob:waive` matching 0
  findings) -- only ever trustworthy from a genuine full unscoped run
  (mirrors `_waive.py`'s own disclaimer), so independently re-runs
  `run_gates` itself rather than trusting the caller's scope, and
  refuses outright if invoked with `gates`/`ticket` set. Deletes only a
  bare single-physical-line waiver comment; a `\`-continued multi-line
  directive is left untouched.

`apply_tier_a_fixes`'s prior positional-call list is promoted to
`TIER_A_HANDLERS: dict[str, Callable[[Path, GraphSnapshot, TicketQueue],
list[FixApplied]]]`, keyed by rule id, per docs/design/check-fix-
engine.md's Fix-handler protocol section -- each handler whose own
signature differs from the uniform 3-arg shape is adapted via a thin
lambda at this call site only, never by changing the handler's own
signature. Dispatch order: DOC007/DOC002/INV006-carry/FMT001/REG010/
REL002 (pure rewrites, no ledger interaction) -> TICK002 (ledger) ->
WAIVE004 (runs last, re-invokes the gates suite over every prior
handler's own rewrites already applied).

Scope was extended twice, both via `frob ticket scope T-1261 --add`
with disclosed reasons before editing: `docs/modules/gates.md`
(AFFECT001/COV001 remedies for the new handler symbols require touching
the affects()-closure doc in the same diff) and `design/frob.strata`
(SYS104 interface= entries for the new public symbols).
docs/modules/gates.md's `--fix Tier-A deterministic auto-fix handlers`
section gained a full write-up of the four new handlers and
`TIER_A_HANDLERS`'s dispatch-table shape; its stale "CLI wiring is a
later batch, out of scope" scope-boundary note was corrected to reflect
that T-1260 already wired `--fix` into the CLI separately.

Changed:
src/frob/gates/_fix_engine.py::fix_fmt001_directive_wrap
src/frob/gates/_fix_engine.py::fix_reg010_registry_sync
src/frob/gates/_fix_engine.py::fix_rel002_release_sync
src/frob/gates/_fix_engine.py::fix_waive004_stale_waiver
src/frob/gates/_fix_engine.py::_is_single_line_waiver
src/frob/gates/_fix_engine.py::_remove_waiver_line
src/frob/gates/_fix_engine.py::_waive004_target_rule
src/frob/gates/_fix_engine.py::TIER_A_HANDLERS
src/frob/gates/_fix_engine.py::apply_tier_a_fixes

Evidence: tests/test_gates.py::TestFixEngineTierABatch2 (11 tests, all
green), bound via `frob ticket evidence --accepts` to acceptance indices
0-3 per this ticket's own GIVEN/WHEN/THEN criteria.

Filed: none (no out-of-scope work discovered beyond the two disclosed
scope extensions above).

Gates: `frob check --ticket T-1261 --only affect_drift --only coverage
--only scope --only docanchor --only doclink` -- AFFECT clean (0 errors,
was 5 before the docs.modules/gates.md write-up); every COV002/SCOPE001
finding remaining after that fix belongs entirely to
src/frob/app/check_runner.py, src/frob/app/config.py,
src/frob/_cli_parsers/_check.py, docs/design/check-fix-engine.md,
docs/modules/app.md, tests/test_check_runner.py -- T-1260's own
already-closed, already-correctly-scoped commit (c76b9995), sitting
unlanded ahead of T-1261 in this worktree. `frob check --ticket`
attributes the whole unlanded branch diff to the active ticket rather
than per-hunk, so a closed sibling ticket's own commit reads as
"unbound to an open ticket" / "outside T-1261's scope" until it lands to
main -- a known land-time artifact of stacked unlanded tickets in one
worktree, not something this ticket touched or should fix. Full
`pytest -q tests/test_gates.py -k TestFixEngineTierA` (21 tests, both
the T-1138/T-1177 batch and this ticket's batch 2) green.

### Changed
```
 design/frob.strata              |   9 ++
 docs/design/check-fix-engine.md |  14 ++
 docs/modules/app.md             |   7 +-
 docs/modules/gates.md           |  86 ++++++++---
 src/frob/_cli_parsers/_check.py |  14 ++
 src/frob/app/check_runner.py    | 146 +++++++++++++++++-
 src/frob/app/config.py          |   7 +
 src/frob/gates/_fix_engine.py   | 330 ++++++++++++++++++++++++++++++++++++++--
 tests/test_check_runner.py      | 186 ++++++++++++++++++++++
 tests/test_gates.py             | 286 ++++++++++++++++++++++++++++++++++
 tickets.md                      | 188 +++++++++++++++++++++--
 11 files changed, 1220 insertions(+), 53 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_already_canonical_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_files_missing_entries_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_already_in_sync_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_resyncs_pyproject_and_uv_lock_from_manifest` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_already_in_sync_touches_nothing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_removes_stale_waiver_on_a_full_unscoped_run` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_refuses_a_scoped_run` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_leaves_a_multi_line_continued_waiver_alone` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 1 error(s), 1128 warning(s), 683 waived
- error-findings: PRE001@tickets/T-1261
