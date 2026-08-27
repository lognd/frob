## Done report

Corrected a false premise before fixing anything. The ticket claimed
this was "a genuine WIRE001 false positive against the test's fixture,
not test staleness." MEASURED the opposite: T-2348 (landed 31c1e197d,
2026-08-17) deliberately replaced WIRE001 case 3's raw text-membership
scan with an AST-parsed one (_config_external_forwarded_dest_names),
which collects dest names ONLY from string literals that are actual
elements of a module-level tuple/list/set/frozenset(...) ASSIGNMENT --
by design, to close a real false-negative hole (a dest string merely
mentioned in a comment/docstring used to silently read as "wired").
T-2348's own test suite (tests/unit/gates/test_wire001_cli_dest_
semantic.py) already covers and passes the correctly-wired case using a
real tuple-assignment fixture.

The failing test in tests/test_gates.py predates T-2348 (git log shows
T-2348's own commit never touched it) and writes only a bare orphan
string fragment into _config_external.py -- syntactically a standalone
tuple expression, but not an ast.Assign, so the new AST-based check
correctly does not recognize it as wired. This is test staleness against
a deliberate, already-tested tightening, not a wire_gate regression.

Corrected scope from src/frob/gates/_wire.py (no fix belongs there) to
tests/test_gates.py, with the reason recorded via `frob ticket scope`.

Fix: updated the fixture to write a real module-level tuple assignment
('_STRING_FIELDS = (\n    "ticket_accept_amend_index",\n)\n') instead of
the bare fragment, matching the shape T-2348's own semantic tests
already use and matching how _config_external.py's real _STRING_FIELDS/
_PATH_FIELDS/etc. tuples are actually written.

Verified: all 32 tests in TestWireGate pass, including this one and its
pre-existing must-fire sibling (test_new_cli_dest_missing_from_config_
external_is_flagged, unchanged, still fires correctly on a genuinely
unwired dest). ruff check on the changed file is clean.

BUG002 note: this is not a new-guarded-behavior repro in the traditional
sense -- confirmed the failure was real and reproducible at the parent
commit before touching anything (ran the exact failing node id first,
read the AssertionError diff directly: the CHECKED literal's "manual"
scan direction, i.e. wire_gate output, disagreed with the fixture, not
the other way the ticket claimed). The fix corrects the test's own
fixture to match already-correct, already-tested production behavior.

### Changed
```
 tests/test_gates.py      |  10 ++++-
 tickets/T-3149/ticket.md | 102 ++++++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 110 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
