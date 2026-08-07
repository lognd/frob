## Done report

Audited all 19 gate:WAIVE004 findings from a full unscoped `frob check`
(before: 19, after: 0). Every one classified (a) obsolete -- the
underlying finding is confirmed gone on the current tree, not a
scoping/matching artifact -- and removed. No rule was enrolled in
_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES; none of the 19 needed it
(DEAD001/DEPR005/REF002/ARCH*/EXHAUST* all evaluate full current state
per run, matching the T-1577 comment's own prior audit of those three
rule classes).

Per-waiver classification:
- src/frob/_cli_parsers/_core.py:82 DEAD001 (_add_outline_parser): (a)
  the symbol now carries a real frob:tests edge (added by a later
  ticket), so dead_symbol_gate's DECLARED-referenced check exempts it
  outright -- it can never produce a DEAD001 finding again, waiver moot.
- src/frob/app/ticket_runner/_land_cmd.py:1835 ARCH103 (_land): (a) the
  function no longer trips ARCH103 at all (confirmed: 0 ARCH findings for
  this function in a full run) -- refactored/shortened since the waiver
  was written.
- src/frob/doctor.py:324 EXHAUST003 (scan_live_land_processes): (a) no
  EXHAUST003 finding for this function currently; the resolver-visibility
  gap the waiver described is gone.
- src/frob/gates/__init__.py:7067 ARCH001 (_run_combined_jobs): (a) no
  ARCH001 finding for this function currently -- consistent with the
  waiver's own reason text ("executable body is a dozen lines").
- src/frob/release/__init__.py:17 ARCH102 (module-level): (a) the whole
  module carries zero ARCH findings now.
- src/frob/serve/_events.py:154 EXHAUST002 (subscribe_and_wait): (a) the
  waiver's own reason text says the JSONDecodeError case "is now
  explicitly caught inline (T-1062)" -- self-documented as already fixed;
  confirmed only EXHAUST003 (a different, still-waived finding on the
  same function) fires now.
- strata-core/src/parse/lexer.rs:4 REF002 (whole file): (a) lexer.rs now
  has 2 inbound references (parse/mod.rs's `mod` decl plus
  grammar_policy.rs), not the single reference the waiver was written
  against.
- tests/system/test_cli_sys_audit.py:9, tests/test_ticket_leases.py:34,
  tests/unit/test_app_clean_runner_branches_t1400.py:10 -- 3x DEPR005
  (resolver name-collision on run()): (a) verified src/frob/app/
  xref_runner.py::run / outline_runner.py::run / map_runner.py::run no
  longer carry any frob:deprecated directive at all -- they were
  un-deprecated since these waivers were written, so DEPR005 (which only
  evaluates live frob:deprecated edges) can structurally never fire for
  them again.
- 8x DEAD001 on pytest autouse fixtures (tests/system/test_spawn_budget.py:43,
  tests/test_dup_cross_lang.py:75, tests/test_serve_daemon.py:55,
  tests/unit/perf/test_persist_run_cli.py:23,
  tests/unit/perf/test_serial_pools.py:45, tests/unit/test_dup_cache.py:16,
  tests/unit/test_land_release_coherence.py:44,
  tests/unit/test_perf_runner_t1400.py:36): (a) T-1651 (already landed on
  main, see git log) added an `@pytest.fixture(autouse=True)` exemption
  directly into dead_symbol_gate's own DECLARED/REFERENCED check
  (src/frob/gates/_dead_symbols.py's module docstring documents this:
  "_is_autouse_pytest_fixture ... DEAD001 lacked this exemption entirely
  before T-1651 and flagged 5 of this repo's own autouse fixtures as
  dead"). Every autouse fixture in the tree is now exempted at the gate
  level, permanently -- confirmed via a full run's gate:DEAD diagnostics
  (38 findings, zero of them autouse fixtures). These 8 waivers are dead
  weight from before that gate fix landed.
- tests/unit/perf/test_serial_pools_import_failure.py:99 DEAD001 (bare
  `_ = _serial_pools` statement, not a def): (b) this waiver was never
  attached to a real DEAD001-shaped target -- DEAD001 only scans
  function/class/method definitions (private-symbol dead-code), never
  bare module-level import-usage statements, so this waiver's site could
  never produce a matching DEAD001 finding under exact-symref matching
  even in principle. It most likely only ever "worked" pre-T-1652 via the
  file-scope fallback (coincidentally forgiving some other real DEAD001
  finding in this file, if one ever existed) -- confirmed the file
  currently has zero DEAD001 findings of any kind.

No rule needed WAIVE004's structurally-unverifiable-rule escape hatch --
every one of the 19 evaluated real, current, full-run state and read
correctly as "genuinely gone," not "diff-scoped noise."

Symref audit of other gates (requested alongside this ticket): arch_gate
(ARCH001/101-103/CPPTHROW001/LARGE001) and exhaustive_handling_gate
(EXHAUST001-003) both already carry symref correctly -- confirmed by
direct source read, not assumption. Two gates do NOT and structurally
look like the same DEAD001-class shape (a per-symbol finding built from a
resolved function/site name that never gets threaded into
Violation(symref=...)): CACHE001 (src/frob/gates/_cache_gate.py,
site.func_name resolved but unused for symref) and OPAQUE001
(src/frob/gates/_opaque.py, finding resolved per-site but no symref) --
OPAQUE001 is the higher-stakes one, carrying 166 live waived findings
repo-wide right now, all running on file-scope matching unverified. Filed
as T-1659 (out of this ticket's scope: src/frob/gates/_cache_gate.py
and src/frob/gates/_opaque.py are not in this ticket's declared scope).
PERF001-014/PII011-012/SEC005(taint_gate) were spot-checked (symref
present in only a minority of their source files) but not fully audited --
disclosed in T-1659's body as a recommended follow-up sweep,
not silently dropped.

Deletions (DELETION RULE, one per line, file + rule id):
src/frob/_cli_parsers/_core.py DEAD001
src/frob/app/ticket_runner/_land_cmd.py ARCH103
src/frob/doctor.py EXHAUST003
src/frob/gates/__init__.py ARCH001
src/frob/release/__init__.py ARCH102
src/frob/serve/_events.py EXHAUST002
strata-core/src/parse/lexer.rs REF002
tests/system/test_cli_sys_audit.py DEPR005
tests/test_ticket_leases.py DEPR005
tests/unit/test_app_clean_runner_branches_t1400.py DEPR005
tests/system/test_spawn_budget.py DEAD001
tests/test_dup_cross_lang.py DEAD001
tests/test_serve_daemon.py DEAD001
tests/unit/perf/test_persist_run_cli.py DEAD001
tests/unit/perf/test_serial_pools.py DEAD001
tests/unit/test_dup_cache.py DEAD001
tests/unit/test_land_release_coherence.py DEAD001
tests/unit/test_perf_runner_t1400.py DEAD001
tests/unit/perf/test_serial_pools_import_failure.py DEAD001

Verification: full unscoped `frob check` (foreground, timeout-wrapped)
before this change: gate:WAIVE 0 errors, 19 warnings, 0 waived. After:
gate:WAIVE line no longer printed at all (0 errors, 0 warnings, 0
waived) -- confirmed via both the plain-text summary and the --json
diagnostics array (no WAIVE004 entries). Total gate-summary warnings
dropped 128 -> 108 in the same run (the 19 WAIVE004 plus a 1-count
unrelated TICK fluctuation). No other gate family's counts changed except
TICK (15 -> 14, unrelated ledger-state drift, not caused by this change).
ruff-check flagged one incidental import-sort issue this edit's blank-line
removal left in tests/test_ticket_leases.py; fixed with `ruff check --fix`
and re-verified `ruff check .` -> "All checks passed!".

Filed: T-1659 (out-of-scope symref audit finding: CACHE001 and
OPAQUE001 lack Violation.symref, same class of bug as T-1652's DEAD001
fix; OPAQUE001 has 166 live waived findings currently unverified against
exact-symbol matching).

Gates: `frob check --only test --ticket T-1658` clean (0
errors, 9 warnings, 3 waived, all pre-existing/unrelated). Full unscoped
`frob check` clean: 0 errors repo-wide (gate-summary), same as before
this change except gate:WAIVE dropping to 0. Ruff/ty/format all pass.

### Changed
```
 tickets.md | 121 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 121 insertions(+)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 669 warning(s), 848 waived
- error-findings: none (measured, zero errors)
