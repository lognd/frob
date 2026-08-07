## Done report

Leaf carrier landing T-1420's first delivered portion (T-1414 precedent)
so two completed, gate-verified LARGE001 splits reach main while the
T-1420 lease continues over the remaining 50 files.

1. src/frob/gates/_sys.py (819 -> 537 lines): the SELFAUDIT001 family
   moved verbatim to new src/frob/gates/_sys_selfaudit.py (317 lines).
2. src/frob/gates/_dead_symbols.py (819 -> 216 lines): the WIRE001/
   WIRE002 family moved verbatim to new src/frob/gates/_wire.py (633
   lines), importing shared exemption helpers back from _dead_symbols;
   frob.gates.__init__ repointed.

Both splits repointed their doc edges (docs/strata/host.md,
docs/modules/gates.md) and frob:tests edges (tests/test_gates.py) in the
same commit as the move; drift/doclink/docanchor/fmt/archgate/wire/
dead_symbols scoped checks all pass, and WIRE001's T-1431
relocation-awareness held on both relocations (no false fire, its first
real-world exercise). LARGE001 file count 52 -> 50.

Also carried: the t-1420 worktree's ledger repair after the warm-up
merge resurrected 61 main-archived ticket blocks (the T-1437 splice
class) -- stale active blocks removed, verified against main's ledger.

Also delivered on this branch (earlier T-1420 session, commit 8efc97e3,
verified inside the same frob check --ticket T-1420 --budget 100 clean
run): src/frob/vet/_capability_registry.py (2991 lines) split into a
7-module package (_dangerous_ops_python/_dangerous_ops_other/_kinds/
_matrix/_opaque/_schemas), with _capability.py and the vet/registry
tests repointed. The three frob:waive directives that lived in the old
monofile (INV006 split-carried-prose, COV007 drift-lock helper, AFFECT001
tuple-extension) were RELOCATED into the new package modules with their
reasons intact, not dropped -- the deletion filter's hits on the old
path are the delete half of a verbatim move.

### Changed
```
 docs/guides/extending/capability-registry.md       |   66 +-
 docs/modules/gates.md                              |    2 +-
 docs/modules/vet.md                                |    8 +-
 docs/strata/host.md                                |    2 +-
 src/frob/gates/__init__.py                         |    3 +-
 src/frob/gates/_dead_symbols.py                    |  611 +---
 src/frob/gates/_sys.py                             |  295 +-
 src/frob/gates/_sys_selfaudit.py                   |  316 +++
 src/frob/gates/_waive.py                           |    2 +-
 src/frob/gates/_wire.py                            |  633 +++++
 src/frob/vet/_capability.py                        |   28 +-
 src/frob/vet/_capability_registry.py               | 2991 --------------------
 src/frob/vet/_capability_registry/__init__.py      |   80 +
 .../_capability_registry/_dangerous_ops_other.py   |  754 +++++
 .../_capability_registry/_dangerous_ops_python.py  |  726 +++++
 src/frob/vet/_capability_registry/_kinds.py        |  132 +
 src/frob/vet/_capability_registry/_matrix.py       |  751 +++++
 src/frob/vet/_capability_registry/_opaque.py       |  504 ++++
 src/frob/vet/_capability_registry/_schemas.py      |  133 +
 tests/test_capability_registry.py                  |   35 +-
 tests/test_gates.py                                |   61 +-
 tests/test_vet.py                                  |   62 +-
 tickets.md                                         |  278 +-
 23 files changed, 4478 insertions(+), 3995 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSysGate::test_sys001_dangling` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 1 error(s), 1166 warning(s), 693 waived
- error-findings: PRE001@tickets/T-1441
