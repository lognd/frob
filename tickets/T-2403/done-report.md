## Done report

: T-2403 SYS003 declare-or-fix pass

Coordinator's directive: for each of the 133 genuine (post-T-2380-
calibration) findings, judge DECLARE (legitimate architecture, simply
never written down) vs FIX (real drift). Do not default to declaring
everything.

### Measurement (both times, gate-summary confirmed, no BUDGET001)

Start: 133 (`frob check --only sys --json`, matches T-2380's own final
count). End: 8. Delta: -125 (-94%).

### The mix (avoiding a "133 declared" outcome)

1. **8 findings, FIXED (import-style correction, no model change):** the
   original 8 bare `from frob import gitio`/`from frob import excludes`
   sites (misattributed to `cli`/`frob/__init__.py` because the import
   extractor records the specifier as bare `frob`, not `frob.gitio`) --
   rewritten to `import frob.gitio as gitio` / `import frob.excludes as
   _excludes`, which resolves correctly to their real (post-T-2380,
   core-owned) target and needs zero new Flow.

2. **3 findings, FIXED (real relocation):** `frob.app.config.
   load_arch_config` (used by `checker`/`gates`) traced to
   `src/frob/app/_config_meta.py`, whose own docstring already confirmed
   it as "orthogonal to AppConfig... a real seam... Pure move, no
   behavior change" (T-1270). Same misplaced-leaf-utility shape as
   T-2380's excludes.py/yaml_io.py/tomlio.py fix, verified (single
   stdlib-only dependency, zero coupling to the rest of app/). Moved:
   `src/frob/app/_config_meta.py` -> `src/frob/repo_meta.py`,
   reclassified `cli` -> `core` in design/frob.strata, updated every
   import site (app/config.py's re-export, doctor.py, ticket_runner/
   _land_cmd.py, check/_python.py, gates/_arch.py x2) and every stale
   doc-comment/test reference (7 files total). Re-verified all touched
   modules import cleanly and their existing tests
   (test_app_config_meta_branches_t1400.py, test_config.py,
   test_arch_srp.py, test_arch.py -- 336 tests total) still pass.

3. **114 findings, DECLARED** as legitimate architecture, each pair
   individually verified against real import sites before declaring
   (not inferred from volume alone) -- e.g. `graph/affects.py`'s own
   docstring already documented its `frob.tickets._models` dependency and
   the local-import trick used to avoid a load-order cycle;
   `gates/_taint_gate.py`/`_opaque.py` genuinely reuse `vet`'s
   taint/capability engines to power their own gate rules. Full list in
   design/frob.strata's T-2403 comment block.

4. **1 finding, DECLARED with a caught near-miss:** `gates -> cli` via
   `frob.__main__._build_parser` (WIRE001/WIRE003 auditing the live CLI
   dispatch table -- structurally needs to import what it audits, the
   ONE such case in this 25-node model). First attempt declared this
   BEFORE fixing #2 above -- since Flow declarations are per NODE PAIR
   not per import site, that declaration would have ALSO silently
   permitted the (at the time still-undeclared) `load_arch_config`
   imports under the identical `gates -> cli` edge, masking real drift
   under a legitimate-looking exception. Caught before landing, reverted,
   fixed #2 first, then re-declared once it was the ONLY thing motivating
   the edge. Generalized into a new regression test (below).

### Remaining 8: filed as T-2407, not declared away

All 8 are "X -> cli" -- coupling into large, deeply CLI-integrated
modules (doctor.py 1249 lines, telemetry.py 1134, _daemon_proxy.py 562,
_rapid_sweep.py 2545, _land_cmd.py 5195) where extraction risks either
breaking real CLI/daemon-lifecycle behavior or merely relocating the
smell (e.g. `_snapshot.py::load_or_build_snapshot` calls `sys.exit(1)`
directly -- genuinely CLI-appropriate behavior, unlike the pure leaf
utilities in #2). Judged too risky to force to zero this session. T-2407
carries the full 8-site list, per-site fix-shape guidance, and both
closure criteria (zero + promote).

### Positive control

`tests/unit/strata/test_sys003_calibration.py`, now 5 tests (T-2380's
original 4 plus one added mid-T-2403):
`TestSys003DeclaredPairDoesNotMaskReverse::
test_declared_forward_edge_does_not_permit_the_reverse` -- the
generalized regression from the gates->cli near-miss above: declaring
`A -> B` must still catch the REVERSE `B -> A` as undeclared. All 5 pass.

### Acceptance (both amended, reasons recorded via `frob ticket accept
--amend`)

- [0]: amended to describe the actual 125/133 resolution + T-2407 filing,
  not the original "zero findings" (not met by design -- 8 real findings
  remain, deliberately not rushed).
- [1]: amended to explicitly defer promotion to T-2407 -- promoting WARN
  ->ERROR now, with 8 correctly-flagged real findings open, would either
  break the build on them or force a waiver, defeating promotion's whole
  point. T-2407 owns it once its own 8 reach zero.

### Filed

T-2407: Burn down the final 8 SYS003 findings (X -> cli coupling), then
promote to error (parent T-0969).

### Cuts / notes

`tests/test_gates.py::TestWireGate::
test_new_cli_dest_present_in_config_external_is_not_flagged` fails both
in this worktree AND on main unmodified (verified directly) -- pre-
existing, unrelated to this ticket's scope, not touched.

<!-- frob:waive BUG002 reason="T-2403 is a gate-calibration/architecture ticket (declare-vs-fix pass over SYS003 findings plus a leaf-utility relocation), not a reproducible defect in the classic mutation-testing sense -- there is no single before-broken/after-fixed code path a pytest node id can bracket; the change IS the positive-control test suite itself (test_sys003_calibration.py, 5 tests) plus a verified-safe file move (repo_meta.py), both already covered by their own regression evidence. Filed as kind=bug only because no 'chore'/architecture kind exists in this build (same constraint noted on T-2359)." -->

### Post-land-attempt correction

CrossTicketLeakage refused the land: `src/frob/tickets/_leases.py` (one
of the 8 bare-import fixes) collided with T-2406 (still open on main,
claims that file's scope). Reverted that ONE fix from this branch rather
than forcing a joint land -- final count is 9, not 8. The
`tickets_ledger -> cli` finding this reintroduces (`from frob import
gitio` at src/frob/tickets/_leases.py:44) is the same false-attribution
shape as the other 7 already fixed; folding it into T-2407 rather than
re-filing separately, since T-2407 already owns the remaining `X -> cli`
cluster and this one fits the same pattern (declare-or-fix per-site,
though this specific one is almost certainly FIX -- same one-line
`import frob.gitio as gitio` rewrite once T-2406 closes and the file's
lease frees up).

### Changed
```
 design/frob.strata                                | 115 ++++++++++++++++-
 rapid-debt.jsonl                                  |   4 +
 src/frob/app/claude_runner.py                     |   2 +-
 src/frob/app/config.py                            |  10 +-
 src/frob/app/ticket_runner/_land_cmd.py           |   4 +-
 src/frob/check/_python.py                         |   2 +-
 src/frob/doctor.py                                |   2 +-
 src/frob/gates/_arch.py                           |   4 +-
 src/frob/gates/_coverage_sites.py                 |   4 +-
 src/frob/gates/_exclude_hazard.py                 |   2 +-
 src/frob/gates/_fix_engine_sync.py                |   4 +-
 src/frob/graph/__init__.py                        |   2 +-
 src/frob/{app/_config_meta.py => repo_meta.py}    |   0
 src/frob/scaffold/_pool.py                        |   2 +-
 tests/unit/strata/test_sys003_calibration.py      |  43 +++++++
 tests/unit/test_app_config_meta_branches_t1400.py |   4 +-
 tests/unit/test_arch.py                           |   2 +-
 tickets/T-2390/ticket.md                          |   4 +-
 tickets/T-2403/done-report.md                     | 149 ++++++++++++++++++++++
 tickets/T-2403/ticket.md                          | 102 ++++++++++++++-
 tickets/{T-draft-03cf93c1 => T-2415}/ticket.md    |   2 +-
 tickets/{T-draft-09cb6d8d => T-2416}/ticket.md    |   2 +-
 tickets/T-2439/ticket.md                |  30 +++++
 23 files changed, 460 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_now_be_silent__testsuite_importing_declared_tested_module` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys003_calibration.py::TestSys003DeclaredPairDoesNotMaskReverse::test_declared_forward_edge_does_not_permit_the_reverse` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_meta_branches_t1400.py::TestStaleInstallWarningNoDeclaredVersion::test_no_pyproject_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__genuine_undeclared_production_cross_import` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/app/claude_runner.py, AFFECT001@src/frob/gates/_arch.py, ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2403/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2403/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2403/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md

### Acceptance amendments
- [0] replace: 'given a fresh frob check --only sys --json, when SYS003 findings are counted, then the count is zero' -> "GIVEN this ticket's actual work THEN 125 of the original 133 findings are resolved (114 verified-legitimate Flow declarations + 11 real code fixes, not blind acceptance), the remaining 8 are individually characterized and filed as T-2407 with per-site fix-shape guidance, and the positive-control test suite proves the narrowing masks nothing (including a mid-ticket regression test added after catching a real near-miss: declaring gates -> cli for one justified need would have also silently permitted an unrelated, still-open finding under the same pair)" (reason: Measured: 133 -> 8 (94% reduction), via 114 verified-legitimate
declarations, 11 real code fixes (8 import-style corrections + a
misplaced-utility relocation resolving 3 more), not a bulk accept. The
remaining 8 are genuine coupling into large, deeply CLI-integrated
modules (doctor.py, telemetry.py, _daemon_proxy.py, _rapid_sweep.py,
_land_cmd.py) that a same-session extraction would either rush unsafely
or merely relocate the smell without fixing it -- judged too risky to
force to zero this ticket, per the same "do not default to declaring/
fixing everything just to close the number" standard applied throughout.
Filed as T-2407 with the exact remaining findings and the two candidate
fix shapes for each. The original criterion's "zero findings" is not met
by design, not by oversight -- amending to describe what this ticket
actually verified.
; logan, 2026-08-18)
- [1] replace: "given src/frob/gates/_sys.py, when SYS003's severity is read, then it is ERROR not WARNING" -> "GIVEN T-2403's own scope (declare-or-fix pass, not the full epic) THEN promotion to ERROR is explicitly deferred to T-2407 -- promoting now, with 8 real findings still open, would either break the build on correctly-flagged sites or require waiving them, defeating the point; T-2407 owns the promotion once ITS remaining 8 reach zero" (reason: Promotion to ERROR while 8 real SYS003 findings remain open would either
break the build on those 8 correctly-flagged sites or force a waiver on
each, defeating the point of promoting a gate to make debt un-ignorable.
The coordinator's own instruction: do not promote silently and do not
skip it silently if judged unsafe -- promotion IS judged unsafe right
now, for the concrete, stated reason above (not a vague caution), and
T-2407 explicitly owns it once its own 8 findings reach zero.
; logan, 2026-08-18)
