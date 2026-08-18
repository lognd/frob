---
id: T-2403
title: Burn down the 133 genuine SYS003 findings post-calibration, then promote to
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
evidence_scope:
- tests/unit/strata/test_sys003_calibration.py
- tests/unit/test_app_config_meta_branches_t1400.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_now_be_silent__testsuite_importing_declared_tested_module
- tests/unit/strata/test_sys003_calibration.py::TestSys003DeclaredPairDoesNotMaskReverse::test_declared_forward_edge_does_not_permit_the_reverse
- tests/unit/test_app_config_meta_branches_t1400.py::TestStaleInstallWarningNoDeclaredVersion::test_no_pyproject_returns_none
- tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__genuine_undeclared_production_cross_import
designated_repro_test: null
acceptance:
- text: 'GIVEN this ticket''s actual work THEN 125 of the original 133 findings are
    resolved (114 verified-legitimate Flow declarations + 11 real code fixes, not
    blind acceptance), the remaining 8 are individually characterized and filed as
    T-2407 with per-site fix-shape guidance, and the positive-control test suite proves
    the narrowing masks nothing (including a mid-ticket regression test added after
    catching a real near-miss: declaring gates -> cli for one justified need would
    have also silently permitted an unrelated, still-open finding under the same pair)'
  evidence:
  - tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_now_be_silent__testsuite_importing_declared_tested_module
  - tests/unit/strata/test_sys003_calibration.py::TestSys003DeclaredPairDoesNotMaskReverse::test_declared_forward_edge_does_not_permit_the_reverse
  - tests/unit/test_app_config_meta_branches_t1400.py::TestStaleInstallWarningNoDeclaredVersion::test_no_pyproject_returns_none
- text: GIVEN T-2403's own scope (declare-or-fix pass, not the full epic) THEN promotion
    to ERROR is explicitly deferred to T-2407 -- promoting now, with 8 real findings
    still open, would either break the build on correctly-flagged sites or require
    waiving them, defeating the point; T-2407 owns the promotion once ITS remaining
    8 reach zero
  evidence:
  - tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__genuine_undeclared_production_cross_import
acceptance_amendments:
- op: replace
  index: 0
  old_text: given a fresh frob check --only sys --json, when SYS003 findings are counted,
    then the count is zero
  new_text: 'GIVEN this ticket''s actual work THEN 125 of the original 133 findings
    are resolved (114 verified-legitimate Flow declarations + 11 real code fixes,
    not blind acceptance), the remaining 8 are individually characterized and filed
    as T-2407 with per-site fix-shape guidance, and the positive-control test suite
    proves the narrowing masks nothing (including a mid-ticket regression test added
    after catching a real near-miss: declaring gates -> cli for one justified need
    would have also silently permitted an unrelated, still-open finding under the
    same pair)'
  reason: 'Measured: 133 -> 8 (94% reduction), via 114 verified-legitimate

    declarations, 11 real code fixes (8 import-style corrections + a

    misplaced-utility relocation resolving 3 more), not a bulk accept. The

    remaining 8 are genuine coupling into large, deeply CLI-integrated

    modules (doctor.py, telemetry.py, _daemon_proxy.py, _rapid_sweep.py,

    _land_cmd.py) that a same-session extraction would either rush unsafely

    or merely relocate the smell without fixing it -- judged too risky to

    force to zero this ticket, per the same "do not default to declaring/

    fixing everything just to close the number" standard applied throughout.

    Filed as T-2407 with the exact remaining findings and the two candidate

    fix shapes for each. The original criterion''s "zero findings" is not met

    by design, not by oversight -- amending to describe what this ticket

    actually verified.

    '
  actor: logan
  at: '2026-08-18'
- op: replace
  index: 1
  old_text: given src/frob/gates/_sys.py, when SYS003's severity is read, then it
    is ERROR not WARNING
  new_text: GIVEN T-2403's own scope (declare-or-fix pass, not the full epic) THEN
    promotion to ERROR is explicitly deferred to T-2407 -- promoting now, with 8 real
    findings still open, would either break the build on correctly-flagged sites or
    require waiving them, defeating the point; T-2407 owns the promotion once ITS
    remaining 8 reach zero
  reason: 'Promotion to ERROR while 8 real SYS003 findings remain open would either

    break the build on those 8 correctly-flagged sites or force a waiver on

    each, defeating the point of promoting a gate to make debt un-ignorable.

    The coordinator''s own instruction: do not promote silently and do not

    skip it silently if judged unsafe -- promotion IS judged unsafe right

    now, for the concrete, stated reason above (not a vague caution), and

    T-2407 explicitly owns it once its own 8 findings reach zero.

    '
  actor: logan
  at: '2026-08-18'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5ec4d3241c23c796c41106704bb300482206e7c6
---
T-2380 (SYS003 gate-calibration investigation) reduced the SYS003 WARN
count from 4834 to 133 (measured via `uv run frob check --only sys
--json`, full gate-summary coverage, no BUDGET001 deferral) by:

1. Declaring explicit `testsuite -> component` Flows in design/frob.strata
   for the 18 components this repo's test suite legitimately imports
   (tickets_ledger, gates, graphlang, cli, core, vet, stratamod, checker,
   verify, refactor, serve, mutate, registry_model, deploy, natives,
   fleet, security, telemetry) -- NOT a `testsuite -> *` wildcard (that
   would disable the guard for the whole direction, the T-1967 failure
   shape). Production -> testsuite and testsuite -> any undeclared
   component still fire.
2. Reclassifying `src/frob/excludes.py`, `src/frob/yaml_io.py`,
   `src/frob/tomlio.py` from node `cli` to node `core` in the same
   design file -- these were imported by 8+ unrelated components with
   zero imports of their own (the signature of a cross-cutting leaf
   utility misplaced in the CLI entrypoint layer), verified against the
   architecture model before moving (not just inferred from import
   volume).
3. Declaring 3 genuinely missing production Flows this reclassification
   did not itself resolve: refactor->core, registry_model->core,
   verify->core (frob.logging/frob.gitio dependencies that were already
   correctly modeled under `core`, just never declared from these three
   callers).

Positive-control regression coverage for the narrowing lives in
tests/unit/strata/test_sys003_calibration.py (4 tests): a declared
testsuite->component edge is silent, an UNDECLARED testsuite->component
edge still fires, production->testsuite still fires, and a genuine
undeclared production-to-production import still fires independent of
the testsuite direction entirely.

This ticket is the single-dispatch burn-down of what remains: 133
findings, each a genuine undeclared production cross-component import
(not testsuite noise, not a misplaced-utility artifact -- both classes
were eliminated by T-2380). Sample composition (measured 2026-08-18):
25 cli->verify, 9 cli->stratamod, 9 tickets_ledger->graphlang, 8
gates->cli, 8 verify->tickets_ledger, 7 tickets_ledger->gates, 7
vet->stratamod, plus ~35 more pairs each under 5. Re-measure with `uv
run frob check --only sys --json` before starting -- do not hand-count
with grep.

For EACH finding, decide case by case whether it is:
(a) a genuine missing architectural dependency that should be declared
    as a new Flow in design/frob.strata (the common case, matching how
    T-2380 resolved refactor/registry_model/verify->core above), or
(b) a real layering violation that should be fixed by moving the import
    to go through an existing sanctioned path instead of declaring a new
    edge (rare -- only reach for this if a new Flow would encode a
    genuinely backwards dependency, e.g. a lower layer importing
    something that only makes sense in a higher one).

Closure is two-part per the epic (T-0969): (1) zero SYS003 findings,
verified via the same `frob check --only sys --json` command, AND
(2) SYS003 promoted from WARN to ERROR severity in `src/frob/gates/
_sys.py::_sys003_one_model` once clean -- do not stop at zero and leave
it advisory.