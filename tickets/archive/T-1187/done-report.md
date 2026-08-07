## Done report

Extracted the SYS00x/DOC003/SELFAUDIT001 family (sys_gate + its private
helpers: _load_systems/_load_test_config, _design_dir, _sys001-004,
_selfaudit_violation(s), _claims_markers and friends, _log_sys_gate_summary)
into src/frob/gates/_sys.py, following the _fuzz.py (T-1183) precedent.
gates/__init__.py: 7960 -> 7309 lines. sys_gate and _load_test_config are
re-exported from frob.gates unchanged; _DEFAULT_DESIGN_DIR, _claims_markers,
and _design_dir are also re-exported (tests/test_gates.py's direct-call
surface plus _waive_comments.py's existing `from frob.gates import
_design_dir` cross-reference).

DRIFT002 fallout from the move (5 tests/test_gates.py `frob:tests` comments
plus one docs/strata/surface.md `frob:describes` marker pointing at the
old __init__.py::sys_gate location) fixed by updating the symref text in
place, same as T-1183's precedent for _fuzz.py. docs/strata/surface.md was
not in T-1187's original scope; added it via `frob ticket scope --add`
(SCOPE001's own suggested remedy) since the 1-line fix is a direct,
unavoidable consequence of this ticket's own file move, not new work.

Only ONE family extracted this land (one-family-per-land discipline
continues); the other 7 named in T-1187's body (INV00x, TEST00x, REL00x,
PERF, COV00x, SCOPE/PREWORK, run_gates spine) are still outstanding.
Re-filed as a fresh residue ticket per TICK011 rather than closed silently.

### Changed
```
 docs/strata/surface.md     |   2 +-
 src/frob/gates/__init__.py | 659 +------------------------------------------
 src/frob/gates/_sys.py     | 690 +++++++++++++++++++++++++++++++++++++++++++++
 tests/test_gates.py        |  10 +-
 tickets.md                 |  16 +-
 5 files changed, 718 insertions(+), 659 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestSysGate::test_noop_no_design_dir` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSysGate::test_sys001_dangling` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 672 warning(s), 679 waived
- error-findings: none (measured, zero errors)
