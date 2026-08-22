## Done report

Changed:
- src/frob/strata/_host_isolation.py (facade: waiver plumbing,
  compromised-owner catalog, re-exports)
- src/frob/strata/_host_isolation_shared.py (new: HostIsolationViolation,
  _PathClaim, identity/ACL/mode-parsing utilities, and the extracted
  _shared_writable_paths helper)
- src/frob/strata/_host_isolation_lateral.py (new: HOST001,
  evaluate_lateral_isolation)
- src/frob/strata/_host_isolation_vertical.py (new: HOST002,
  evaluate_vertical_isolation)
- src/frob/strata/_host_isolation_movement.py (new: host_movement_flows)
- tests/unit/strata/test_host_isolation.py (frob:tests directives
  repointed to each symbol's new file)
- docs/strata/host.md (two stale file::symbol pointers repointed to the
  moved symbols' new files: host_movement_flows,
  HOST_MULTI_INSTANCE_WAIVER_FAMILIES)

Seam verification: the seam T-2826 found genuinely held on inspection --
lateral (HOST001), vertical (HOST002), and movement (host_movement_flows)
each have their own violation-computation cluster with no cross-calls,
sharing only HostIsolationViolation/_PathClaim and the identity/ACL/
mode-parsing utilities, which now live in a leaf module
(_host_isolation_shared.py) with no import of any sibling
_host_isolation_* module, matching the _selfconform_models.py precedent
(T-2729) for the identical reason: avoiding an import-direction cycle.
Verified this holds under BOTH the normal facade-first import path and a
standalone direct import of each new submodule (no ordering-dependent
circular import risk).

Via-list / capability grants: NONE changed. Verified before splitting
(git grep for "_host_isolation" across design/frob.strata) that this
module makes zero capability-gated calls (no fs/exec/net) -- it is pure
HostManifest model logic -- so none of the new files needs a capability
grant either. stratamod's interface= attr is a symbol-name list, not a
per-file one, so the split needed no edit there. code
"src/frob/strata/**" already covers new files under this directory.
This is the T-2729 precedent's OTHER branch: that split's may "fs.read"
via-list update only applied because a real capability-gated call
(path.read_text) moved to a new filename -- this split moves zero such
calls, so no via-list touch was warranted (and none was made).

Gate findings the split itself introduced (fixed, not waived away
blindly): F401 (unused re-export imports -- noqa'd with a reason,
matching this repo's existing re-export convention), I001 (import sort
order in two new files), ruff-format drift in the facade, AFFECT001 (one
frob:waive per moved symbol, T-2729-precedent wording: verbatim move, no
behavior change), DOC006 (docs/strata/host.md's two file::symbol
pointers repointed to the symbols' new homes), and a real DUP002 --
`_shared_writable_path_violations` (lateral) and
`_writable_path_movement_flows` (movement) had copy-pasted the identical
shared-writable-paths set computation; extracted into
`_host_isolation_shared.py::_shared_writable_paths` instead of waiving,
per the no-duplication principle. Three findings are waived, each
because a ticket-scoped gate attributes a MOVED (not new) function's
file as "new in this diff": REF002 (single inbound reference -- the
facade is the ONE by-design consumer, T-2729 sibling-module precedent),
PERF004 (sort-in-nested-loop, pre-existing code unchanged by the move),
and DUP001 (`_acl_ace_of` vs pre-existing, unrelated
`_contention.py::_acl_rule_write_capable` -- confirmed via `git show` on
main that this pair's code was already unchanged/pre-existing before
this ticket).

Gates: `frob check --ticket T-2844` -- 109 pre-existing repo-wide errors
remain (COV/DOC/DRIFT/DSL/OPAQUE/PERF/PRE/REF/REG/SEC/SELFAUDIT/SYS/
TEST/TICK gates, frob-cycle, ruff-format, claude-config-drift), verified
NONE of them are attributed to any of the 5 host_isolation files --
grepped every line mentioning "host_isolation" across two full check
runs and confirmed each either carries a `[waived: ...]` suffix or is
one of this ticket's own SCOPE002 informational warnings (not errors;
gate:SCOPE itself reports 0 errors). Direct measurement via
`frob.gates._arch.arch_gate()`/`frob.gates._waive._apply_waivers()`
against a live `build_graph()` snapshot: zero active AND zero waived
ARCH findings against any of the 5 host_isolation files -- the split
introduced no ARCH violations, and LARGE001 was not promoted (that is
T-2831, out of scope here).

Evidence: full tests/unit/strata/test_host_isolation.py (36 tests) +
tests/unit/strata/test_litmus_host_isolation.py (2 tests) +
tests/integration/test_deploy_malmberg_pilot.py +
tests/unit/strata/test_threat.py + tests/unit/strata/test_scenarios.py +
tests/unit/strata/test_audit.py all pass (226 tests total) run directly
against the split (re-verified after the gate-finding fixes above), 
unchanged from pre-split behavior. Four representative pytest node ids
bound as evidence, one per moved cluster (lateral, shared ACL-join
utility, waiver-plumbing facade, end-to-end litmus).

Pre-existing unrelated floor (NOT introduced by this change, reproduced
identically on unmodified main root): test_export_golden.py (date-drift
golden fixtures), test_selfconform.py::TestRealGateGreen/
TestCoverageTotality, test_conform_eval_needle.py, and
test_sys003_calibration.py fail with SYS100/SYS003 findings pointing at
src/frob/check/__init__.py and src/frob/tickets/_land.py -- entirely
unrelated files/nodes to this ticket's scope, confirmed unrelated by
reproducing the identical failures against main directly (not this
worktree, no changes applied).

Filed: none. T-2846, the sibling in this series, was already landed by
another agent while this ticket was in progress (confirmed via `git log`
on main, commit 71951858f, with its own post-land regression already
filed as T-2855 by the rapid sweep -- unrelated to this ticket).

Gates: frob check --only static clean of NEW findings; frob check
--ticket T-2844 clean of any unwaived host_isolation finding (pre-
existing 109-error repo-wide floor reproduces unmodified, confirmed by
per-line attribution).

### Changed
```
 docs/strata/host.md                         |   4 +-
 src/frob/strata/_host_isolation.py          | 986 ++--------------------------
 src/frob/strata/_host_isolation_lateral.py  | 210 ++++++
 src/frob/strata/_host_isolation_movement.py | 196 ++++++
 src/frob/strata/_host_isolation_shared.py   | 444 +++++++++++++
 src/frob/strata/_host_isolation_vertical.py | 235 +++++++
 tests/unit/strata/test_host_isolation.py    |  78 ++-
 tickets/T-2844/done-report.md               | 102 +++
 tickets/T-2844/ticket.md                    |  15 +
 9 files changed, 1301 insertions(+), 969 deletions(-)
```

### Evidence
- `tests/unit/strata/test_host_isolation.py::TestLateralIsolation::test_skips_below_two_users` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestHostIsolationWaivers::test_vuln_model_fires_unwaived` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_litmus_host_isolation.py::TestHostIsolationVulnLitmus::test_shared_user_model_fires_host001_and_host002` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 46 error(s), 740 warning(s), 797 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@frob-core/src/callgraph.rs, COV001@frob-core/src/exact_regions.rs, COV001@frob-core/src/lib.rs, COV001@frob-core/src/r3.rs, COV001@frob-core/src/r4.rs, COV001@frob-core/src/r5.rs, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/dup-sota-survey.md, DOC006@docs/modules/dup.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/dup.md, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@frob-core/src/lib.rs, DRIFT002@tests/test_arch_near_duplicate_native.py, DRIFT002@tests/unit/test_dup_core.py, DSL001@tests/unit/test_coordinator_scripts.py, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2844, REF001@frob-core/src/callgraph.rs, REF001@frob-core/src/exact_regions.rs, REF001@frob-core/src/r3.rs, REF001@frob-core/src/r4.rs, REF001@frob-core/src/r5.rs, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@frob-core/src/exact_regions.rs, TEST001@frob-core/src/lib.rs, TEST001@frob-core/src/r3.rs, TEST001@frob-core/src/r4.rs, TEST001@frob-core/src/r5.rs, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
