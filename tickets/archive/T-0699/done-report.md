## Done report

Implemented `frob.strata._contention` (T-0699): the SYS2xx
resource-contention rule family over the ALREADY-elaborated `std.host`
grammar (T-0261/T-0272) -- no grammar change, exactly as scoped.

Four rule ids, all registered in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`
(RULE:SUBTARGET waiver discipline, same as SYS100/SYS101):

- SYS200 duplicate port: two distinct nodes declare the same `listens`
  PORT. Hard conflict, no write-mode distinction needed.
- SYS201 overlapping path claim: two distinct nodes' `owns` (linux) or
  `acl` (windows) PATH atoms overlap by directory-segment prefix (not a
  bare string prefix -- `/var/lib/api` does not match `/var/lib/api2`).
  `write_capable=True` when either side's mode/rule expresses a
  write-capable grant (POSIX MODE write bit, or ACL RIGHTS
  Write/Modify/FullControl without `:deny`).
- SYS202 shared pipe: two distinct nodes bind the same `pipe` NAME.
- SYS203 shared store write: two or more distinct nodes have a `Flow`
  edge landing on the same store node. Explicitly MODE-BLIND (`Flow` has
  no read/write direction in the grammar today) -- honestly documented as
  such in both the module docstring and docs/strata/host.md; the
  mode-aware deepening is T-0700/T-0701, not duplicated here.
  `store_ids` (which node ids came from a `store` construct) is not a
  `KernelModel`-level fact (a store desugars into a plain `Node` with no
  surviving marker), so callers must pass `Module.stores`' ids in
  explicitly; empty (default) means SYS203 stays silent, never a guess.

Litmus fixtures (firing + clean pairs) under
tests/unit/strata/litmus/contention_*.strata, parsed through the real
`strata_core` parser end to end (same discipline as
test_litmus_host.py), covering: duplicate port (+ a one-sided-waiver
fixture proving the OTHER node's finding survives), owns-subtree overlap
(write-capable), read-only ACL overlap (fires, not write-capable), shared
pipe, and shared-store-write (+ empty-store_ids silence).

11/11 new tests green (tests/unit/strata/test_contention.py). Full
tests/unit/strata/ suite (267 tests minus the 3 pre-existing golden-export
failures below) stays green, including test_selfconform.py and
test_waive.py -- frob's own design/frob.strata model was checked against
SYS200-203 as part of that run and does NOT need any changes: it declares
no `listens`/`owns`/`acl`/`pipe` overlaps across distinct nodes today, and
SYS203 was not run against it (store_ids was not wired into any CLI caller
-- see below), so no self-conformance debt was introduced or discovered.

Public API added to `frob.strata` (`__init__.py`): `SYS_DUPLICATE_PORT`,
`SYS_OVERLAPPING_PATH`, `SYS_SHARED_PIPE`, `SYS_SHARED_STORE_WRITE`,
`RESOURCE_CONTENTION_RULES`, `ResourceContentionViolation`,
`ResourceContentionReport`, `check_resource_contention`. Each new
constant/class carries a `frob:doc` edge to a new "Resource contention
(SYS2xx, T-0699)" section in docs/strata/host.md (scope-added with a
recorded reason, since COV001 requires a real anchor and none existed).

CUT, disclosed: no CLI wiring (`frob sys audit` / `sys_runner.py`) --
`src/frob/app/**` is outside this ticket's declared scope
(`src/frob/strata/**`, `tests/unit/strata/`), so `check_resource_
contention` is a real, tested, importable entrypoint today but not yet
invoked by any command. Wiring it (plus threading `Module.stores`'
ids through to the CLI caller) is follow-up work, not silently dropped --
noted here rather than assumed done.

Found and filed (out of scope, NOT fixed here): T-0725 (ex-draft, id lost at land) --
tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s/
test_seccomp/test_iam fail on a clean worktree at main tip (e2f38a51),
unrelated to any T-0699 change -- design/frob.strata gained fleet
node/flows in a prior merge but the committed golden JSON fixtures were
never regenerated to match.

Gates: `uv run frob check --ticket T-0699` clean after fixing my own
ruff-check/ruff-format/COV001/gate:INV(waived) hits -- the only remaining
FAIL is `gate:REL` (REL001, public-API version bump), which per
docs/guides/agent-playbook.md / prior land-workflow precedent is the
coordinator's job at land time (pyproject.toml is outside this ticket's
scope), not left silently unaddressed.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_contention.py::TestDuplicatePort::test_two_nodes_same_port_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestDuplicatePort::test_distinct_ports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestDuplicatePort::test_one_sided_waiver_keeps_the_other_nodes_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestOverlappingPath::test_owns_subtree_overlap_fires_write_capable` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestOverlappingPath::test_disjoint_paths_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestOverlappingPath::test_readonly_acl_overlap_fires_but_not_write_capable` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedPipe::test_same_pipe_name_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedPipe::test_distinct_pipe_names_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_single_writer_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_empty_store_ids_is_silent` (pytest node id, verified passing when recorded)
