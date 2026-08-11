## Done report

Added ROOT001 (`frob.gates._root_asset_dirs.root_asset_dir_gate`, gate
name `root_asset_dirs`, WARN severity, waivable), mechanizing the
verification that only ever happened by hand in the T-1611/T-1767/T-1772
agents/skills incident: for every repo-root top-level directory owning
at least one tracked file, excluding `src/`/`tests/` (structural), the
ticket's own named allowlist (`docs/`, `tickets/`, `design/`), and any
directory literally referenced in the repo-root Makefile, requires at
least one of (a) a literal path-token reference anywhere under
`src/frob/**` (covers both real code and `frob.scaffold`'s own
non-Python data assets), (b) a mention in `pyproject.toml`, or (c) an
explicit `<!-- frob:external-reader dir="name" reason="..." -->`
declaration in a tracked markdown file. A directory satisfying none of
these is flagged, never auto-deleted.

Wired into `src/frob/gates/__init__.py` (import, both stage-name lists,
the gate dispatch table, `__all__`) and `src/frob/gates/_waive.py`'s
`_KNOWN_GATE_RULES` registry. Documented in `docs/modules/gates.md`
(rule-catalog row plus a full "ROOT001 (T-1784)" section mirroring
EXCL001's own).

Evidence protocol (BUG002/T-0756 new-gate-rule acceptance): committed
`TestRootAssetDirGate::test_unreferenced_root_directory_fires` alone
first (2a80fd7c2) -- at that commit `frob.gates._root_asset_dirs` did
not exist, so the test's import fails with `ModuleNotFoundError`,
confirmed via `frob ticket evidence T-1784 --check-repro
tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires
--base-ref 2a80fd7c2`: FAILED_AT_PARENT. The gate implementation +
wiring + docs + remaining 7 fixture tests landed in a separate commit
(cba76ea23). Acceptance criterion 0 added
(`frob ticket accept T-1784 --criterion ...`) with explicit FAIL/PASS
markers per the T-0756 new-gate-rule policy, bound to the repro test via
`--accepts 0`.

Verified:
- `uv run pytest tests/test_gates.py::TestRootAssetDirGate -o addopts=""
  -q`: 8 passed.
- `uv run pytest tests/test_gates.py -o addopts="" -q` (full file, all
  pre-existing tests plus these 8 new ones): 719 passed, 0 failed --
  confirms the `_KNOWN_GATE_RULES` drift-lock tests
  (`TestKnownGateRuleIds`) still pass with ROOT001 added.
- `uv run frob ticket evidence T-1784 --check-repro ... --base-ref
  2a80fd7c2`: FAILED_AT_PARENT (genuine repro).
- `uv run python3 -c "import frob.gates; print(frob.gates.root_asset_dir_gate)"`
  resolves -- confirms the `__all__` export wiring.

Not folded in (out of scope, disclosed): promoting the
`frob:external-reader` directive into the full `frob.graph.dsl` edge
machinery (currently a dedicated regex this gate alone recognizes) --
noted in both the module docstring and docs/modules/gates.md as a
reasonable follow-up if repo-root directory audits become frequent
enough to justify it, not attempted here.

Update: `frob check --ticket T-1784 --only gates-fast` initially found
DOCENUM001 (the rule-catalog's `frob:enumerates` members= list in
docs/modules/gates.md needed ROOT001 added) -- fixed in a follow-up
commit (e0b782682), re-verified clean afterward for that gate. The only
remaining FAIL in that scoped run is gate:TICK (TICK004, T-0969 rotting
past its 7-day threshold) -- pre-existing repo-wide ticket-ledger rot
unrelated to this ticket's own diff (T-1784 does not touch tickets.md
content beyond its own block), confirmed unaffected by this change.

### Changed
```
 docs/modules/gates.md              |  49 +++++++++-
 src/frob/gates/__init__.py         |  10 ++
 src/frob/gates/_root_asset_dirs.py | 195 +++++++++++++++++++++++++++++++++++++
 src/frob/gates/_waive.py           |   4 +
 tests/test_gates.py                | 106 ++++++++++++++++++++
 tickets/T-1784/done-report.md      |  77 +++++++++++++++
 tickets/T-1784/ticket.md           |  59 ++++++++++-
 7 files changed, 496 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_directory_referenced_under_src_frob_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_directory_referenced_in_pyproject_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_directory_with_external_reader_declaration_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_makefile_referenced_directory_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_allowlisted_directories_are_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-2098/src/frob/gates/_root_asset_dirs.py, SELFAUDIT001@design, TICK004@tickets.md
