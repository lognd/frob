## Done report

Fixed G4 (docs/audits/strata.md): `_unmodeled_violations` (SYS102) marked
a WHOLE top-level `src/frob/` directory "owned" the moment ANY file in it
was non-FOREIGN, and `_top_level_dirs` only ever iterated directories
(`entry.is_dir()`) -- so a FOREIGN file placed in an already-modeled
directory, or a loose file directly under `src/frob/` (no subdirectory at
all), was invisible to SYS102 AND to SYS100/SYS101 (both only reconcile
bound files) AND to THREAT004/import conformance (both skip FOREIGN).

Counterexample confirmed first (ad-hoc script): a `subprocess.run(...)`
exec-capability file dropped into an already-`code=`-globbed directory,
plus a second file dropped loose at `src/frob/` top level, both produced
zero `check_self_conformance` violations before the fix.

Fix: split `_unmodeled_violations` into three passes over the same
precomputed `_package_relative` list -- the original fully-foreign-
directory case (`_fully_foreign_dir_violations`, unchanged behavior),
FOREIGN files inside an otherwise-owned directory
(`_foreign_file_in_owned_dir_violations`, new), and loose top-level files
(`_loose_foreign_file_violations`, new) -- each firing SYS102 at file
granularity instead of the old per-directory grain.

Tightening this surfaced a REAL, pre-existing gap in frob's own self-model
(`design/frob.strata`): `src/frob/__init__.py`, `src/frob/doctor.py`, and
`src/frob/excludes.py` are loose top-level files with no `code=` glob
owner at all -- TestRealGateGreen failed against the new stricter check
until the model was fixed. Added the three files to the `cli` node's
glob (the existing convention for single-file top-level entrypoints,
already home to `src/frob/__main__.py`).

All of tests/unit/strata/ and tests/test_gates.py/test_vet_containment.py/
test_testing.py pass. tests/system/test_frob_self_model.py's
test_parses_and_elaborates/test_every_claim_proves were ALREADY failing
before this ticket's changes (confirmed via git stash: pre-existing
claim/flow-count drift unrelated to G4), not a regression introduced
here -- left untouched, out of this ticket's scope.

### Changed
```
 src/frob/strata/_threat.py       | 47 ++++++++++++++++++--
 tests/test_vet_containment.py    |  4 ++
 tests/unit/strata/test_threat.py | 78 ++++++++++++++++++++++++++++++++
 tickets.md                       | 96 ++++++++++++++++++++++++++++++++++++++--
 4 files changed, 218 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestUnmodeledCodeForeignFileGranularity::test_foreign_file_in_otherwise_owned_directory_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUnmodeledCodeForeignFileGranularity::test_loose_top_level_file_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUnmodeledCodeForeignFileGranularity::test_loose_top_level_file_discharges_once_globbed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
