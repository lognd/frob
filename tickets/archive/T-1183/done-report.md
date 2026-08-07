## Done report

Continuing the T-1072/T-1140/T-1159/T-1170/T-1174 one-family-per-land
discipline: extracted the FUZZ001/FUZZ002/FUZZ003 family (fuzz_gate plus
its private helpers _fuzz_enforce/_fuzz_gate_violations) into a new
src/frob/gates/_fuzz.py module, mirroring T-1174's _dup.py precedent
exactly (same docstring shape, same re-export-unchanged posture,
fuzz_gate imported at the top of gates/__init__.py and re-exported so
every existing frob.gates.fuzz_gate call site keeps working unchanged).
gates/__init__.py: 8015 -> 7960 lines.

Updated the frob:doc/frob:tests directive pointers that named
src/frob/gates/__init__.py::fuzz_gate to point at the symbol's new home
(src/frob/gates/_fuzz.py::fuzz_gate) in docs/modules/gates.md and
tests/test_gates.py, matching the T-1174 dup_gate precedent.

The new module's own docstring tripped INV006 (exclusivity-vocabulary
claim, "only"/"solely" phrasing describing its own already-implemented
split rationale) -- disposed via preset="split-carried-prose" (T-1176),
the same calibration-batch class every other first-turn-on INV006 site
in this repo uses.

Budget did not allow the other ~8 remaining families (SYS00x/DOC003,
INV00x, TEST00x, REL00x, PERF, COV00x, SCOPE/PREWORK, the run_gates
spine) in this pass. Filed as T-1187 (re-filed, not
re-derived from scratch, per TICK011) rather than let this ticket close
with silent residue.

### Changed
```
 docs/modules/gates.md      |  2 +-
 src/frob/gates/__init__.py | 63 ++------------------------------
 src/frob/gates/_fuzz.py    | 91 ++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_gates.py        |  2 +-
 tickets.md                 | 48 +++++++++++++++++++++++-
 5 files changed, 143 insertions(+), 63 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestOptInGates::test_fuzz_gate_off_by_default` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
