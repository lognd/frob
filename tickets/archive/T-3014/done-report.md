## Done report

Changed:
- src/frob/gates/__init__.py -- import narrative_blocks_gate; add "narrative_blocks"
  to _ALL_GATES, _CANONICAL_GATE_ORDER, and the _build_thread_jobs GATE_RUNNERS dict
  (mirroring "excludehazard" immediately above each site); add "narrative_blocks_gate"
  to __all__.
- src/frob/gates/_waive.py -- add "NARR001" to _KNOWN_GATE_RULES.
- docs/modules/gates.md -- add NARR001 to the frob:enumerates members list and add
  its rule-catalog table row.
- src/frob/gates/_narrative_blocks.py -- remove the now-satisfied WIRE001 waiver on
  narrative_blocks_gate; retarget the SELFAUDIT001 waiver's follow_up to the new
  draft ticket (design/frob.strata is currently T-2989-leased, not T-2986).

Reachability proof: `frob check --only narrative_blocks` runs (previously refused
with "unknown --only stage(s): ['narrative_blocks']") and reports:
  pass  gate:NARR  0 errors, 121 warnings, 0 unresolved, 0 waived
121 is the repo-wide NARR001 finding count at the shipped WARN severity and the
12-line threshold. Full output captured in the ticket's work session; command was
`timeout 540 uv run frob check --only narrative_blocks`.

Waivers revisited (per T-2994 doctrine, no permanent residue):
- WIRE001 on narrative_blocks_gate -- REMOVED. It cited T-3014 as the follow-up
  that would wire the gate in; that wiring is now done.
- SELFAUDIT001 on narrative_blocks_gate -- KEPT. It needs narrative_blocks_gate's
  own fs.read declared on the "gates" strata node in design/frob.strata, which is
  currently leased by T-2989 (not T-2986, which is done and released) for the
  whole of this ticket's own work window -- the identical shape of constraint
  T-2993 hit. Retargeted its follow_up from T-3014 to the new draft ticket below.
- DUP001 on _dispatch_narrative (src/frob/__main__.py) -- NOT revisited: its
  reason has nothing to do with the T-2986/T-3014 lease chain (it is about
  refactor/'s own body being a different ticket's live work area), so it carries
  no follow_up="T-3014" tag and is out of this ticket's scope.
- SYS003 on _dispatch_narrative (src/frob/__main__.py) -- NOT resolved in this
  ticket: frob.narrative has no strata component/node of its own at all (unlike
  frob.refactor's "node refactor" + "flow f_t2403_cli_refactor : cli -> refactor"),
  so closing it means registering a new strata node, a real design addition, not
  a one-line fix within T-3014's declared scope (src/frob/gates/__init__.py,
  docs/modules/gates.md). Filed as part of the same follow-up ticket below.

Threshold: left at the shipped 12 lines, per the owner's explicit instruction not
to change it in this ticket absent further direction; none was seen.

Filed: T-3020 ("Register frob.narrative as a strata component; close
its SELFAUDIT001/SYS003 waivers") -- scope design/frob.strata,
src/frob/gates/_narrative_blocks.py, src/frob/__main__.py. Renumbers at land;
verify its real id on main before citing it further.

Evidence: tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_must_fire_long_archaeology_block,
tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_must_stay_quiet_short_keep_block,
tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_socketd_t2961_block_stays_quiet_at_default_threshold,
tests/test_narrative_blocks.py::TestNarrativeBlocksGateRepoScan::test_fires_on_a_tracked_file_with_a_long_block
-- all 5 tests in the file collected and passed (`pytest tests/test_narrative_blocks.py -q`, exitstatus=0
collected=5 failed=0) after the wiring/waiver changes.

Gates: `frob check --only narrative_blocks` (unbudgeted, gate-summary present) shows
gate:NARR clean (0 errors, 121 warnings, 0 unresolved, 0 waived). The same invocation
also reports gate:DRIFT FAIL (21 pre-existing DRIFT002 errors, all in files this
ticket never touched -- app/check_runner.py, app/doctor_runner.py, ci_report.py,
ghio.py, and several self-referential test-collect-form frob:tests directives in
tests/unit/test_app_runners_batch6.py, tests/unit/test_check.py,
tests/unit/test_doctor_runner_t1276.py, tests/unit/test_logging_module.py) -- this
is baseline noise unrelated to NARR001 wiring, not something this ticket's scope
covers or caused.

### Changed
```
 docs/modules/gates.md               |  3 ++-
 src/frob/gates/__init__.py          | 14 +++++++++++
 src/frob/gates/_narrative_blocks.py | 15 ++++++-----
 src/frob/gates/_waive.py            |  6 +++++
 tickets/T-3014/ticket.md            | 33 +++++++++++++++++++++++-
 tickets/T-3020/ticket.md  | 50 +++++++++++++++++++++++++++++++++++++
 6 files changed, 111 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_must_fire_long_archaeology_block` (pytest node id, verified passing when recorded)
- `tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_must_stay_quiet_short_keep_block` (pytest node id, verified passing when recorded)
- `tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_socketd_t2961_block_stays_quiet_at_default_threshold` (pytest node id, verified passing when recorded)
- `tests/test_narrative_blocks.py::TestNarrativeBlocksGateRepoScan::test_fires_on_a_tracked_file_with_a_long_block` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 55 error(s), 1168 warning(s), 855 waived
- error-findings: AFFECT001@src/frob/gates/_narrative_blocks.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t3014-series/tests/test_narrative_migrate.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3014, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md
