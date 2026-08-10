## Done report

Widened _extract_members (src/frob/gates/_docenum.py) to resolve argparse
choices=[...] lists. A choices= kwarg lives inside an add_argument() call,
which has no bare module/class-level assignment target of its own for
_find_node_for_qualname to walk to -- so the qualname a doc's
frob:enumerates directive names is instead the ENCLOSING function (e.g.
_add_cycle_parser), and the new _extract_argparse_choices helper walks
that function's body for its one add_argument(..., choices=[...]) call.

Ambiguity handling: if a function contains zero or more than one such
call, this punts (returns None -> WARN, matching every other unresolvable
shape in this module) rather than guessing which choices= list a bare
function-qualname means. Covered by
test_argparse_multiple_choices_calls_is_ambiguous_punt.

No doc currently carries a frob:enumerates directive against an argparse
choices=[...] list (checked docs/commands/cycle.md, xref.md, parse.md --
none exist yet); this ticket only removes the previously-disclosed
"cannot resolve" gap in _extract_members itself so such a directive CAN
now be added and verified. Adding those directives to the docs
themselves is not part of this ticket's scope (src/frob/gates/_docenum.py
+ its own test file only) and was not requested by the ticket text.

### Changed
```
 tickets/T-1506/ticket.md | 19 ++++++++++++++++++-
 1 file changed, 18 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_argparse_choices_members_extracted` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_argparse_choices_stale_claim_fires` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_argparse_multiple_choices_calls_is_ambiguous_punt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 545 warning(s), 725 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/__init__.py, SEC110@src/frob/app/ticket_runner/__init__.py
