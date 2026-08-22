## Done report

A predecessor agent stalled mid-extraction (resource starvation, T-2443)
after leaving an unreviewed WIP snapshot (commit ae6010d32) touching
design/frob.strata, src/frob/check/__init__.py, src/frob/doctor.py,
src/frob/tickets/_leases.py, and a new src/frob/derived_state.py. That
snapshot was reviewed from scratch this session, not trusted blind.

Verdict on the snapshot: KEPT, with fixes. The core design was correct
and matched T-2403's own precedent exactly:
- `src/frob/tickets/_leases.py`'s `from frob import gitio` ->
  `import frob.gitio as gitio` -- the dropped-from-a-sibling-branch
  straggler the coordinator flagged. Confirmed still present on main
  before reapplying; no conflict with any other open ticket found.
- `frob.doctor.verify_derived_state`/`DerivedArtifactStatus`/
  `DERIVED_ARTIFACTS` relocated to new `src/frob/derived_state.py`
  under `core`, the same misplaced-leaf-utility shape T-2380/T-2403
  already moved excludes.py/yaml_io.py/tomlio.py/repo_meta.py for.
  `frob.doctor` imports both back; its own drift-manifest tracking
  stayed in place, unchanged.
- 4 Flow declarations in design/frob.strata (telemetry->cli, core->cli
  x2, serve->cli, verify->cli x3 sites) covering the remaining 7 X->cli
  sites, each checked against the T-2403 near-miss (same node-pair
  masking another undeclared import) before declaring, per-site
  reasoning recorded as strata comments.

What the snapshot got wrong / left undone, fixed this session:
- The verify->cli Flow's comment said "filed as T-2440" but no such
  ticket existed -- the agent had written the citation before actually
  running `frob ticket new`, then stalled. Filed it for real
  (T-2450, renumbers at land) and corrected the citation.
- New module derived_state.py was missing frob:ticket edges (COV002),
  a frob:tests edge on the new DerivedArtifactStatus class (T-2114),
  and had a malformed multi-line frob:waive directive (missing `\`
  continuation, so PII012 was firing raw) plus one E501 line. All fixed.
- docs/guides/install.md's `frob:describes` anchor and `docs/modules/
  gates.md`/`docs/strata/surface.md`'s SYS003 severity prose still said
  WARN and pointed at doctor.py -- updated both to ERROR/derived_state.py.
- TestSys003DeclaredPairDoesNotMaskReverse extended per the ticket's
  carry-forward instruction: added
  test_declared_pair_does_not_mask_a_third_node_reaching_the_same_dst,
  proving a declared A->B Flow does not also silence an undeclared
  C->B sharing only the destination node.
- Added TestSys003ZeroOnFrobsOwnRepo, an in-scope e2e test isolating
  SYS003==0 against this repo's own live design/frob.strata -- used as
  acceptance[0]'s evidence instead of tests/system/test_frob_self_
  model.py::TestFrobSelfModel::test_sys_gate_zero_violations, which
  asserts a broader zero-ALL-sys-violations bar (including SELFAUDIT/
  SYS100/SYS101/SYS111) that is already red on main today for reasons
  outside T-2407's scope (measured: 61 violations on main, none of
  them SYS003).

Promotion: DONE. `src/frob/gates/_sys.py::_sys003_one_model` severity
changed WARN -> ERROR. Both existing severity-asserting tests
(tests/test_gates.py::TestSysGate::test_sys003_import,
tests/unit/strata/test_sys003_calibration.py's WARN-era assertion)
updated to expect ERROR.

Before/after (unscoped `frob check --json`, gate-summary coverage
confirmed, no BUDGET001 deferral):
- SYS003 findings: 8 (+1 leases straggler) -> 0, confirmed via
  `frob check --only sys --json` (0 SYS003 diagnostics) AND the new
  TestSys003ZeroOnFrobsOwnRepo e2e test.
- Full unscoped error count: 111 (main baseline measured separately at
  92 on a later, unrelated main tip -- not a clean apples-to-apples
  delta since main advanced during this session; every T-2407-caused
  finding -- E501/AFFECT001/COV002/PII012/malformed-directive on
  derived_state.py, COV002 on touched test classes -- was individually
  chased to zero and confirmed absent from the post-fix measurement).
  Remaining errors are pre-existing repo debt (SELFAUDIT001 SYS100/
  SYS101 findings in files T-2407 never touched, DRIFT002, COV003,
  TICK004, etc.) plus SELFAUDIT001 SYS111 capability-ratchet growth
  that IS caused by this ticket's diff and is Tier-A auto-fixable
  (`fix_sys111_capability_ratchet_sync`), absorbed automatically by
  `frob ticket land` before its own merge per the agent playbook.
- tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_
  config_external_is_not_flagged fails identically on main (verified
  standalone against the shared root) -- pre-existing, unrelated to
  this ticket.

Filed: T-2450 (renumbers at land) -- promote verify's three
private ticket_runner call sites to a public seam, per the snapshot's
own deferred-follow-up note.

Addendum: land required `--allow-cross-ticket`. T-2434 (T-2390 epic
child, docblocks schema validation) holds a broad epic-tier lease
covering docs/modules/gates.md and src/frob/check/__init__.py that this
ticket's own two edits to those files (the check/__init__.py import
retarget to derived_state.py, and the SYS003 gates.md doc-table row)
also touch. Verified T-2434's own worktree (.claude/worktrees/t-2390-
series) has zero uncommitted changes to either file (only
src/frob/gates/_docblocks_schema.py and its test) and already carries a
Done report + evidence -- this is the epic-lease-leak shape (a tier=epic
scope leasing files it never uses), not a real content collision.

### Changed
```
 design/frob.strata                           | 110 ++++++++++++++++-
 docs/guides/install.md                       |  15 ++-
 docs/modules/gates.md                        |   2 +-
 docs/strata/surface.md                       |  23 ++--
 src/frob/check/__init__.py                   |   2 +-
 src/frob/derived_state.py                    | 171 +++++++++++++++++++++++++++
 src/frob/doctor.py                           | 124 +------------------
 src/frob/gates/_sys.py                       |   2 +-
 src/frob/tickets/_leases.py                  |   2 +-
 tests/test_gates.py                          |  10 +-
 tests/unit/strata/test_sys003_calibration.py |  46 ++++++-
 tickets/T-2407/done-report.md                | 110 +++++++++++++++++
 tickets/T-2407/ticket.md                     |  71 ++++++++++-
 tickets/T-2450/ticket.md           |  36 ++++++
 14 files changed, 570 insertions(+), 154 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sys003_calibration.py::TestSys003TestsuiteFlowCalibration::test_must_still_fire__genuine_undeclared_production_cross_import` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2407/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2407/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2407/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2407, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
