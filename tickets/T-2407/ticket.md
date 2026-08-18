---
id: T-2407
title: Burn down the final 8 SYS003 findings (X -> cli coupling), then promote to
  error
state: done
kind: bug
origin: agent
created: '2026-08-18'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- src/frob/doctor.py
- src/frob/derived_state.py
- src/frob/tickets/_leases.py
- src/frob/gates/_sys.py
- docs/guides/install.md
- docs/strata/surface.md
- tests/test_gates.py
- tests/unit/strata/test_sys003_calibration.py
evidence_scope:
- tests/unit/strata/test_sys003_calibration.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/doctor.py
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/derived_state.py
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_sys.py
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/guides/install.md
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/strata/surface.md
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_gates.py
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/strata/test_sys003_calibration.py
  reason: 'T-2407 scope: file this ticket''s SYS003 burn-down actually touched'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__genuine_undeclared_production_cross_import
- tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design
designated_repro_test: tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design
acceptance:
- text: given a fresh frob check --only sys --json, when SYS003 findings are counted,
    then the count is zero
  evidence:
  - tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design
- text: given src/frob/gates/_sys.py, when SYS003's severity is read, then it is ERROR
    not WARNING
  evidence:
  - tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__genuine_undeclared_production_cross_import
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 51cf648d58efa946e176dbcf6bb9d997e94b4c7b
---
T-2403 (SYS003 burn-down) reduced the 133 genuine post-calibration findings
to 8, resolved via a mix of judgment, matching the coordinator's explicit
"do not default to declaring everything" directive:

- 114 findings: DECLARED as legitimate architecture (each pair verified
  against real import sites before declaring -- see design/frob.strata's
  T-2403 comment block and T-2403's Done report for specifics).
- 8 findings (the original 8 bare `from frob import gitio/excludes`
  misattributions): FIXED via import-style correction (`import frob.X as
  X`), no model change needed.
- 3 findings (`frob.app.config.load_arch_config`, checker+gates callers):
  FIXED by physically relocating `src/frob/app/_config_meta.py` ->
  `src/frob/repo_meta.py` and reclassifying it from node `cli` to node
  `core` -- the same misplaced-leaf-utility shape T-2380 already fixed
  for excludes.py/yaml_io.py/tomlio.py, confirmed by the file's own
  docstring ("orthogonal to AppConfig... a real seam distinct from the
  class itself... Pure move, no behavior change").
- 1 finding (`gates -> cli` via `frob.__main__._build_parser`, the
  WIRE001/WIRE003 gate's genuine need to introspect the live CLI
  dispatch table): DECLARED, but only after the load_arch_config fix
  above -- Flow declarations are per NODE PAIR, not per import site, so
  declaring gates -> cli for WIRE's need would have ALSO silently
  permitted the (then-still-real) load_arch_config drift under the same
  edge. Fixing that first made the declaration safe.

The remaining 8 are ALL "X -> cli" -- something depending on the `cli`
node, which is otherwise (after T-2403) depended upon by nothing else in
this 25-node model except the one justified WIRE exception above. Unlike
the load_arch_config cluster, these are NOT self-contained leaf utilities
-- each is genuine coupling into large, deeply CLI-integrated modules
(doctor.py 1249 lines, telemetry.py 1134 lines, _daemon_proxy.py 562
lines, _rapid_sweep.py 2545 lines, _land_cmd.py 5195 lines), where a
same-day extraction risks either breaking real CLI/daemon-lifecycle
behavior or just relocating the smell without fixing it (e.g.
`frob.app._snapshot.load_or_build_snapshot` calls `sys.exit(1)` directly
-- genuinely CLI-appropriate process-termination behavior, not a
misplaced leaf utility).

Re-measure with `uv run frob check --only sys --json` before starting --
do not hand-count.

Current 8 findings (file:line -> imported symbol):
- src/frob/check/__init__.py:49 -> frob.doctor.verify_derived_state
- src/frob/release/_cli.py:64 -> frob.app._snapshot.load_or_build_snapshot
- src/frob/serve/_tools.py:106 -> frob.app.ticket_runner._rapid_sweep.revalidate_dispatchable_sweep_tickets
- src/frob/telemetry/__init__.py:41 -> frob.app.telemetry.append_event, iso_now
- src/frob/testing/_coverage_wait.py:163 -> frob.app._daemon_proxy.release_daemon_lease, try_daemon_lease
- src/frob/verify/_drain.py:124 -> frob.app.ticket_runner._rapid_sweep._detached_sweep_env
- src/frob/verify/_worker.py:487 -> frob.app.ticket_runner._land_cmd._unscoped_error_findings
- src/frob/verify/_worker.py:610 -> frob.app.ticket_runner._rapid_sweep._file_regression_ticket

For EACH, decide with real judgment (per T-2403's precedent, not a bulk
pass): extract the specific needed function to a lower-layer module (the
repo_meta.py pattern, when the function is genuinely self-contained), OR
declare the specific node-pair edge if, on inspection, the coupling turns
out to be architecturally sound and narrow enough not to mask anything
else under the same pair (re-check for other undeclared imports sharing
the same pair before declaring, per T-2403's own near-miss). Two of the
`verify -> cli` sites and one `serve -> cli` site call PRIVATE
(underscore-prefixed) functions in ticket_runner modules -- that is
itself worth flagging: verify calling private internals of the module
that dispatches it is real coupling that may deserve a proper public seam
rather than either a Flow or a relocation.

Closure is two-part per the epic (T-0969): (1) zero SYS003 findings
(verified via the same `frob check --only sys --json` command), AND
(2) SYS003 promoted from WARN to ERROR severity in
`src/frob/gates/_sys.py::_sys003_one_model` -- this ticket owns the
promotion once it, not T-2403, reaches zero (T-2403 deliberately did NOT
promote, since 8 real findings were still open at its own close -- see
its Done report).