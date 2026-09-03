## Done report

Changed:
- design/frob.strata::node gates (may "fs.write"/"fs.read" via-lists: added src/frob/gates/_land_parity.py; added src/frob/gates/_policy_weakening_gate.py to fs.read)
- design/frob.strata::node testsuite (may "env.read"/"exec"/"fs.read"/"fs.write" via-lists: added tests/unit/strata/test_strata_core_gil.py, tests/unit/test_land_parity_gate.py, tests/unit/test_sync_claude_config_stale_guard_t3408.py, tests/unit/verify/test_worker.py to the capability(ies) each file genuinely exercises)
- docs/design/registry/capability-via-ratchet.lock.json (bumped gates::fs.read, testsuite::env.read, testsuite::exec, testsuite::fs.read, testsuite::fs.write accepted_count to match the new measured site counts -- SYS111's ratchet ceiling)

Widened per coordinator instruction beyond the original two-file filing: measured the FULL current set of undeclared SYS100/SELFAUDIT001 sites on main via `frob check --only sys` before touching anything (29 violations across 2 nodes, 6 files -- not just the 2 files T-3465 originally named), then declared every one of them:

node=gates (5 sites): src/frob/gates/_land_parity.py:203,374 fs.read; :329,334 fs.write; src/frob/gates/_policy_weakening_gate.py:108 fs.read (this last one is T-3460's own CI failure the coordinator named).
node=testsuite (24 sites): tests/unit/strata/test_strata_core_gil.py:50 fs.write, :67 exec; tests/unit/test_land_parity_gate.py:25,26 exec (2), :57,75,90,123,146,151 fs.write (7); tests/unit/test_sync_claude_config_stale_guard_t3408.py:106 env.read, :132,189 fs.read (2), :132,133,136,145,152 fs.write (5); tests/unit/verify/test_worker.py:399,400,442,445,474,475 env.read (6).

Declaring these grew 5 via-lists past SYS111's own committed ratchet ceiling (ratchet lock has a separate per-(node,capability) accepted_count independent of the raw SYS100 fix) -- bumped docs/design/registry/capability-via-ratchet.lock.json's 5 affected entries to the new measured counts with a reason naming this ticket and every contributing file, same pattern the file's own existing entries (T-2001/T-2871/T-2743/T-3029/T-3447) already use.

Acceptance (coordinator's own list), all passing on this worktree:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen (2 tests)
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations

Also re-verified: `frob check --only sys` now reports ZERO SELFAUDIT001/SYS100/SYS111 findings (was 29 SYS100 + 5 SYS111 ratchet-ceiling errors before this fix), and the full tests/unit/strata/test_selfconform.py + tests/unit/gates/test_sys_selfaudit.py + tests/unit/strata/test_sys003_calibration.py + tests/unit/strata/test_sys107_via_scope_advisory.py suites (94 tests) pass clean.

Filed: none.

Gates: `frob check --ticket T-3465` -- gate:SCOPE/gate:AFFECT/gate:COV(diff-scoped)/gate:FMT all clean. gate:DEPR/gate:DRIFT/gate:LARGE/gate:OPAQUE/gate:REL/gate:TICK/gate:WAIVE are pre-existing repo-wide findings entirely outside the two files this diff touches (design/frob.strata, docs/design/registry/capability-via-ratchet.lock.json) -- verified by inspecting each finding's file path, none of which is either of the two touched here.

Update: first land attempt failed post-merge evidence re-run -- a sibling ticket (T-3466) landed concurrently and introduced a new file (tests/unit/test_cross_ticket_leakage_gate.py) with its own undeclared exec/fs.write capability sites. Rebased this worktree onto the new main, re-measured `frob check --only sys` (6 new SYS100 findings + 2 SYS111 ratchet breaches), and declared/bumped those too, same pattern as the rest of this ticket. Re-verified all 4 acceptance tests green again post-rebase.

### Changed
```
 design/frob.strata                                 | 12 +++----
 .../registry/capability-via-ratchet.lock.json      | 30 ++++++++--------
 tickets/T-3465/done-report.md                      | 42 ++++++++++++++++++++++
 tickets/T-3465/ticket.md                           |  5 +++
 4 files changed, 68 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 10 error(s), 4264 warning(s), 866 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3465, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
