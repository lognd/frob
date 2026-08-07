## Done report

Changed:
- src/frob/dup/_models.py::DupConfig.native_rungs_enabled (new field, default True for direct API callers)
- src/frob/dup/_pipeline.py::_fingerprint_symbol (gates R3/R4/R5 behind native_rungs_enabled)
- src/frob/gates/__init__.py::_dup_config (returns (enforce, threshold, region_kernel, native_rungs); reads [dup].native_rungs from frob.toml, default false)
- src/frob/gates/__init__.py::dup_gate / _dup_gate_violations (thread native_rungs through to DupConfig)
- frob.toml ([dup].enforce = true is now this repo's real, permanent setting -- not a temporary measurement block)
- docs/modules/dup.md ("[dup].native_rungs" section, updated with the deadlock/fix history and final measured numbers)
- docs/modules/gates.md (dup_gate docstring update, satisfies AFFECT001)
- tests/test_dup_native_rungs.py (new)

Approach (two-round ticket, resumed after a coordinator-landed fix):

Round 1: T-0399 measured `[dup].enforce=true` blowing past the ~150s
foreground budget. I profiled the cold path and found R3/R4/R5
(native-call-per-symbol) dominate; added `DupConfig.native_rungs_enabled`
(threaded from a new `[dup].native_rungs` toml key) so the gate could run
R1/R2 only. That split alone did not make it safe to flip the default:
re-measuring the R1/R2-only path uncovered a genuine cross-process
DEADLOCK -- `frob check`'s main process holds `derived_state_lock`
SHARED for its whole run while `dup_gate` runs in a `ProcessPoolExecutor`
worker (T-0415), and `find_clones`'s `derived_state_write_lock`
reentrancy check (`_process_already_holds`) is a same-process in-memory
registry blind to the pool's fork boundary -- confirmed live via
`lslocks` (READ held by the main process, WRITE* blocked on the worker,
same `.frob/derived.lock`). I left `[dup].enforce` false, filed a
blocking bug (T-0981, later found to duplicate an audit-filed T-0982),
and blocked T-0974 on it rather than force a close.

Round 2 (this session): the coordinator's T-0982 landed the actual fix
(`_open_process_pool` now stamps `FROB_DERIVED_LOCK_HELD_KEYS` with the
parent's held-lock keys before constructing the pool; a worker's
`derived_state_write_lock` treats a matching canonical root key as an
inherited hold instead of taking a real cross-process flock -- proven by
a real-pool regression test in `tests/unit/test_process_lock.py`). I:
1. `git merge main --no-edit` to bring the fix in, rebuilt natives.
2. Dropped T-0981 as a duplicate of T-0982 (both filed the same finding;
   T-0982 is the one that actually landed the fix), then re-ran
   `frob ticket start T-0974` -- it started clean once both blockers
   were terminal (T-0982 done, T-0981 dropped).
3. Re-measured `[dup].enforce=true` under the fixed lock, timeout-wrapped:
   - `native_rungs=true` (full R1-R5 ladder), cold (no `.frob/dup.db`):
     exceeded a 300s foreground cap -- the lock fix resolved the
     DEADLOCK, but the raw native-call-per-symbol compute cost of R3-R5
     at whole-snapshot scale is still real and still over budget. Kept
     `native_rungs=false` as the shipped default; this rung tier stays
     opt-in (a follow-up candidate: incremental per-file re-index or a
     narrower default snapshot scope, not attempted this pass).
   - `native_rungs=false` (R1/R2 only), cold: `frob check --only clones`
     = 33.9s wall; `frob check --only gates-native` (the real dispatched-
     agent chunk shape, alongside archgate/perf/exhaustive_handling) =
     43.5s wall, no timeout, no deadlock.
   - `native_rungs=false`, warm (cache populated by the prior run):
     `gates-native` settles at ~40-45s total, clones itself ~20-22s --
     comfortably inside the ~90s per-stage foreground budget in both the
     cold and warm case.
4. Flipped `frob.toml`'s `[dup].enforce = true` on for real (removed the
   "temporary measurement block" framing from round 1's frob.toml
   comment; this is now the repo's permanent setting), left
   `native_rungs` at its false default.
5. Verified repo-wide with `frob check --ticket T-0974` across all five
   chunked stage groups (`lint`, `static`, `gates-fast`, `gates-native`,
   `gates-security`, per `frob check --only list`): 0 errors in every
   group. (`static`/`gates-fast` etc. carry pre-existing WARN-tier
   findings unrelated to this ticket, same as before -- not a regression.)
6. Re-ran the full existing dup test suite (test_dup.py, test_dup_rungs.py,
   test_dup_region.py, test_dup_smart.py, test_dup_cross_lang.py,
   test_dup_inline.py, test_dup_prefilter.py, test_dup_exhaustiveness.py,
   test_dup_r5_multilang.py) plus test_dup_native_rungs.py,
   tests/test_gates.py::TestOptInGates, and tests/unit/test_process_lock.py
   together: all green.

Default flipped: YES. `[dup].enforce = true` in this repo's own
`frob.toml`, `native_rungs` left at its default `false` (R1/R2 only).
DUP001/DUP002 (exact + alpha-renamed clone detection) are now live on
every `frob check` run in this repo; R3-R5's deeper semantic ladder stays
opt-in pending a follow-up on its own cold-cost affordability.

Before/after numbers (all measured, timeout-wrapped, this session):
- Before (status quo entering this ticket): `[dup].enforce` absent/false;
  clones stage = 0.00s (no-op).
- `native_rungs=true` cold: still > 300s (timeout-killed) -- NOT shipped.
- `native_rungs=false` cold: clones alone 33.9s; full `gates-native`
  chunk 43.5s.
- `native_rungs=false` warm: `gates-native` chunk ~40-45s, clones ~20-22s.
- Shipped default (`enforce=true`, `native_rungs=false`) repo-wide check:
  0 errors across lint/static/gates-fast/gates-native/gates-security.

Test evidence (pytest --collect-only confirmed, then run green):
- tests/test_dup_native_rungs.py::TestNativeRungsDefaultsOnForDirectCallers::test_default_config_still_reports_native_rungs
- tests/test_dup_native_rungs.py::TestNativeRungsOffWhenDisabled::test_explicit_false_reports_no_native_rungs
- tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r4_gapped_clone
- tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r5_dataflow_clone
- tests/test_gates.py::TestOptInGates::test_dup_gate_off_by_default
- tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing

Filed: T-0981 (duplicate of T-0982's already-landed fix, dropped this
session with a reason) -- otherwise nothing new; the deadlock this ticket
originally would have filed was already independently found and fixed as
T-0982 by the time this ticket resumed.

Gates: `frob check --ticket T-0974` clean (0 errors) across all five
chunked stage groups (`lint`, `static`, `gates-fast`, `gates-native`,
`gates-security`). PRE001 refreshed via `frob ticket sweep T-0974`
before closing.

State: T-0974 CLOSED. The deadlock blocker (T-0982) landed and is done;
its duplicate (T-0981) is dropped; `[dup].enforce=true` is shipped as
this repo's default with `native_rungs=false`.

### Changed
(no changed files detected)

### Evidence
- `tests/test_dup_native_rungs.py::TestNativeRungsDefaultsOnForDirectCallers::test_default_config_still_reports_native_rungs` (pytest node id, verified passing when recorded)
- `tests/test_dup_native_rungs.py::TestNativeRungsOffWhenDisabled::test_explicit_false_reports_no_native_rungs` (pytest node id, verified passing when recorded)
- `tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r4_gapped_clone` (pytest node id, verified passing when recorded)
- `tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r5_dataflow_clone` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_dup_gate_off_by_default` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 4879 warning(s), 307 waived
- error-findings: none (measured, zero errors)
