## Done report

Decision: added a third detection shape, PORT001-DEFAULT, as its own
rule id (not folded into PORT001-PATH's builder, though it shares
PORT001-PATH's promotion class -- see below), in the SAME WARN->ERROR
promotion class as PORT001-PATH (behavioral: a wrong default on a
differently-named host repo is a silent behavior change, not just a
misleading maintainer-facing string the way PORT001-IDENT's advisory
class is).

Detection: `_default_value_hit` matches a bare `"src/<pkg>"` string
constant used as a plain module-level assignment (`Assign`/`AnnAssign`)
value or a function-parameter default (`ast.arguments.defaults`/
`kw_defaults`) -- exactly the `_DEFAULT_COV_TARGET = "src/frob"` shape
(FROBLEMS.md F-011) that motivated PORT001's own creation but that
neither PORT001-PATH (needs a `.startswith(...)` call) nor PORT001-IDENT
(needs a Tuple/List/JoinedStr wrapper) can catch. Deliberately does NOT
match a bare `_PKG = "frob"` assignment (package name alone, no `src/`
prefix) -- that shape is the declared-identity case
`_identity_literal_hit`'s own docstring already excludes as reviewable-
at-its-own-declaration, not path-building logic.

Registration: PORT001-DEFAULT added to `_waive.py`'s `_KNOWN_GATE_RULES`
(out-of-scope widening, same one-line-allowlist pattern every prior
PORT001-family/EXHAUST-family rule id needed -- UnregisteredGateRuleConstructed
otherwise refuses the land).

Evidence:
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_bare_default_value_is_flagged_t3435 (MUST-FIRE)
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_bare_pkg_name_assignment_stays_quiet_t3435 (MUST-STAY-QUIET)
- Full tests/unit/gates/ (141/141) and tests/test_registry_exhaustiveness.py (43/43) pass under -p no:xdist
- frob test --base main: touched=11 selected, run_selected python exit=0

### Changed
```
 tickets/T-3435/ticket.md | 27 ++++++++++++++++++++++++++-
 1 file changed, 26 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_bare_default_value_is_flagged_t3435` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_bare_pkg_name_assignment_stays_quiet_t3435` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 16 error(s), 4361 warning(s), 856 waived
- error-findings: AFFECT001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3435, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
