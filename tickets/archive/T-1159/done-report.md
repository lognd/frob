## Done report

Changed:
src/frob/gates/_decisions_compliance.py (new: decisions_gate, compliance_gate, _compliance005_violation, verbatim move)
src/frob/gates/__init__.py (removed the moved block; import + re-export decisions_gate/compliance_gate; __all__ += compliance_gate)
tests/test_decisions.py (frob:tests back-reference updated to the new file path)
docs/modules/decisions.md, docs/modules/gates.md (frob:describes anchors updated to the new file path)
docs/design/registry/EXHAUSTIVENESS-GATE.md (AFFECT001: compliance_gate's own affects()-closure doc, one-sentence note on the new file location)
design/frob.strata (sys sync-interface: +compliance_gate, newly present in gates.__all__)

Extracted the DEC00x/COMPLIANCE00x family (decisions_gate, compliance_gate,
_compliance005_violation) verbatim into a new module,
src/frob/gates/_decisions_compliance.py, per the T-1072/T-1077/T-1140
discipline this ticket's own Description names: byte-identical function
bodies/docstrings/directives moved, lazy call-time imports preserved
as-is, only decisions_gate + compliance_gate re-exported (verified by a
repo-wide grep -- _compliance005_violation is never imported elsewhere),
design/frob.strata synced via `frob sys sync-interface` (not hand-edited).
gates/__init__.py: 8554 -> 8349 lines.

One cohesive family per land, per the ticket's own instruction -- this
land does DEC00x/COMPLIANCE00x only. The ~11 remaining families named in
T-1159's own acceptance criterion (SCOPE/PREWORK, INV00x, TEST00x,
SYS00x/DOC00x, DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates
spine, COV00x) are NOT done -- gates/__init__.py is still 8349 lines,
well above the acceptance criterion's 800-line target. Filed as residue:
T-1170 ("arch: split remaining ~11 gate families out of
src/frob/gates/__init__.py (8349 lines) -- T-1159 residue"), naming each
remaining family and the same one-family-per-land discipline to follow.

Evidence:
tests/test_decisions.py::test_dec001_dangling_decision_edge
tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes
15/15 relevant tests pass: `pytest tests/test_decisions.py tests/test_gates.py -k "Compliance or decision" -q` (measured: "...............  [100%]").
Acceptance [0] left UNBOUND -- this land only partially satisfies it
(one family of ~12, disclosed above and in the residue ticket), not a
false claim of completion.

Filed: T-1170 (residue for the remaining ~11 families)

Gates: `frob check --ticket T-1159` chunked (gates-fast, gates-native,
gates-security, lint, static) -- gates-native/gates-security/static all
0 errors. gates-fast shows 2 PRE-EXISTING INV006 errors in
strata-core/src/parse/grammar_flow.rs and lexer.rs -- neither file is
touched by this diff, neither is in T-1159's scope, and they are absent
from frob-ratchet.lock.json (unbaselined, unrelated to this ticket's
work). lint shows pre-existing ruff-check/ruff-format findings entirely
in unrelated files (src/frob/_cli_parsers/**, src/frob/tickets/__init__.py,
src/frob/vet/**, src/frob/serve/_socketd.py, src/frob/doctor.py, none
touched by this diff); my six touched files (src/frob/gates/
_decisions_compliance.py, src/frob/gates/__init__.py, tests/
test_decisions.py, docs/modules/decisions.md, docs/modules/gates.md,
docs/design/registry/EXHAUSTIVENESS-GATE.md) are ruff-check/ruff-format
clean.
`uv run frob sys sync-interface` run and committed (compliance_gate
newly exported) -- `--check` clean after.

### Changed
```
 tickets.md | 101 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 98 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_decisions.py::test_dec001_dangling_decision_edge` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
