## Done report

T-1451 delivers the advisory rule the T-1440 landing deferred: SYS107
(src/frob/strata/_selfconform.py::_via_less_large_node_violations) fires
one finding per node whose `code=` glob(s) bind more than
`_LARGE_NODE_FILE_THRESHOLD` (20) real files AND declare at least one
via-less `may` grant (judged per node, not per atom -- size is a node
property). Empty `node.may_grants` (a hand-built `Node` fixture) is
treated as "every declared `may` is via-less", matching `MayGrant.via=()`
's pre-T-1440 meaning.

WARN by default (an advisory nudge, not a new hard requirement on
existing declarations). `[strata] require_may_scope = true` in
`frob.toml` escalates it to ERROR -- a new `_scope_config.py` module
(`StrataScopeConfig`/`load_strata_scope_config`, following the exact
`frob.perf._sketch_store.load_sketch_config` fail-open shape T-0861
established) reads the `[strata]` table. Wired into SELFAUDIT001's own
severity, not into `check_self_conformance`'s violation shape:
`frob.gates._sys_selfaudit._selfaudit_severity` special-cases the
"SYS107" sub_rule string, every other sub-rule (SYS100-106/SYS2xx/REL2xx)
keeps the original unconditional ERROR.

Registered end to end (WIRE001/T-1428 discipline): "SYS107" added to
`_KNOWN_GATE_RULES` (`src/frob/gates/_waive.py`), one new
`CHK-GATE-SYS107` entry in `docs/design/registry/check-coverage.yaml`,
`gate_rule_total` 275 -> 276. New
`docs/modules/strata.md#sys107-via-less-may-on-a-large-node-advisory-t-1451`
section (matching the SYS104/105/106 precedent already there);
`docs/strata/surface.md#may-scope`'s "Not yet built" disclosure updated
to record SYS101-per-via (T-1450) and SYS107 (this ticket) as delivered,
leaving only argument-level scoping as still-deferred.

New public symbols (SYS_VIA_LESS_LARGE_NODE, StrataScopeConfig,
load_strata_scope_config, plus the new test classes) required
`frob sys sync-interface` to add their `interface=` attrs to
`design/frob.strata`'s `stratamod`/`testsuite` nodes (SYS104 is
mandatory) -- ran the tool, it wrote the fix.

Scope was widened via `frob ticket scope --add` (each with a written
reason) to `src/frob/gates/_sys_selfaudit.py` (the severity wiring),
`src/frob/gates/_waive.py` (rule registration), `docs/strata/surface.md`
/`docs/modules/strata.md` (doc coverage), `design/frob.strata` (the
sync-interface fix), and the new test files -- `tests/unit/strata/
test_selfconform.py` itself was NOT touched because sibling ticket
T-1450 (same worktree) held its lease; new SYS107 tests live in
`tests/unit/strata/test_sys107_via_scope_advisory.py` instead.

DISCLOSED: landing T-1451 alone (before T-1453) turns
`TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`
red against this repo's OWN design/frob.strata (8 real large nodes have
via-less grants) -- this is the exact "worst offender" state the wave
brief names testsuite as. T-1453 (this same session) fixes it; land the
two together or in immediate sequence.

Evidence: 12 new unit tests across
tests/unit/strata/test_sys107_via_scope_advisory.py,
tests/unit/strata/test_scope_config.py, and
tests/unit/gates/test_sys_selfaudit.py -- all pass. Scoped
`frob check --ticket T-1451 --only sys` and `--only gates-native`: 0
errors on both (measured after the T-1453 via-migration commit landed in
the same worktree, since SYS107 needed that to go green against the real
repo).

LAND-REPAIR ADDENDUM (post-T-1456 sweep): no direct changes to T-1451's
own scope in this pass; re-verified alongside T-1450/T-1453's fixes
(E501 wrap, ruff format, T-1453 scope add) on the same shared worktree.
`frob check --only sys --only gates-native --only docblocks` and
`--only ruff --only sys` both re-run clean (0 errors) after those
sibling fixes landed on this branch.

### Changed
```
 design/frob.strata                                 |   6 +
 docs/design/registry/check-coverage.yaml           |   6 +-
 docs/modules/gates.md                              |   6 +-
 docs/modules/graph.md                              |   4 +-
 docs/modules/strata.md                             |  24 ++
 docs/strata/surface.md                             |  43 ++-
 src/frob/gates/_sys_selfaudit.py                   |  39 +-
 src/frob/gates/_waive.py                           |   3 +
 src/frob/strata/__init__.py                        |   5 +
 src/frob/strata/_mutation_audit.py                 |  19 +-
 src/frob/strata/_scope_config.py                   |  70 ++++
 src/frob/strata/_selfconform.py                    | 321 ++++++++++++++---
 tests/unit/gates/test_sys_selfaudit.py             |  51 +++
 tests/unit/strata/test_scope_config.py             |  46 +++
 tests/unit/strata/test_selfconform.py              |  68 ++++
 .../unit/strata/test_sys107_via_scope_advisory.py  | 117 ++++++
 tickets.md                                         | 399 ++++++++++++++++++++-
 17 files changed, 1146 insertions(+), 81 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grant_on_large_node_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grant_on_small_node_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_scoped_grant_on_large_node_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_node_with_no_may_never_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_scope_config.py::TestStrataScopeConfig::test_missing_frob_toml_returns_defaults` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_scope_config.py::TestStrataScopeConfig::test_parses_strata_table` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_scope_config.py::TestStrataScopeConfig::test_malformed_toml_falls_back_to_defaults` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_scope_config.py::TestStrataScopeConfig::test_wrong_typed_strata_table_falls_back_to_defaults` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_defaults_to_warn` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_escalates_to_error_under_require_may_scope` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_other_sub_rules_stay_error_regardless_of_config` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_selfaudit_violation_carries_sys107_warn_severity` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
