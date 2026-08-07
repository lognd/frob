## Done report

Extracted the DUP001/DUP002/DUP003 clone-detection family (`dup_gate`,
`_dup_config`, `_dup_gate_violations`) out of `src/frob/gates/__init__.py`
into `src/frob/gates/_dup.py`, per the T-1072/T-1140/T-1159/T-1170
one-family-per-land discipline this ticket's residue list names --
`gates/__init__.py` drops from 8128 to 8015 lines (113 lines moved plus
a 3-line pointer comment left behind).

`dup_gate` remains importable/re-exported from `frob.gates` unchanged
(verified by grep before the move: `tests/test_gates.py`, `frob.dup.
_models`, `frob.app.config` all reference it by that path, not a
`gates._dup`-qualified one) -- imported at the top of `__init__.py` and
still listed in `__all__`. `_dup_config`/`_dup_gate_violations` stay
private to the new module; nothing else imports them.

Fixed the resulting DRIFT002 findings (docs/modules/gates.md's `frob:
describes` edge and 3 `frob:tests` edges in tests/test_gates.py that
pointed at `src/frob/gates/__init__.py::dup_gate`, now resolved to `src/
frob/gates/_dup.py::dup_gate`).

Only ONE family of the ~10 remaining ones the parent ticket named was
budget for this pass (SYS00x/DOC003, FUZZ00x, INV00x, TEST00x, REL00x,
PERF, COV00x, SCOPE/PREWORK, and the run_gates spine itself all remain);
filed a residue ticket for the rest rather than let this close with
silent scope cut, matching T-1170's own precedent.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestOptInGates::test_dup_gate_off_by_default` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 700 warning(s), 572 waived
- error-findings: none (measured, zero errors)
