## Done report

T-0788 left two disclosed gaps: the 17 CMPL_REGISTRY_UNIT_IDS entries in
docs/design/registry/compliance.yaml still carried T-0607's out_of_scope
dispositions, and docs/modules/gates.md had no COMPLIANCE005 row/section.

1. Flipped all 17 entries from out_of_scope:... to disposition:
   "handled_by:COMPLIANCE005". The original plan text (a trailing " --
   reason" suffix appended to the handled_by value) broke REG001's
   `_HANDLED_BY_RE = re.compile(r"^handled_by:(?P<rule>\S+)$")` grammar
   (18 REG001 "no disposition" errors on first pass) -- fixed by keeping
   the disposition value bare (`"handled_by:COMPLIANCE005"`) and moving
   the T-0607/T-0833 provenance/reasoning prose that used to live inline
   in the out_of_scope string to a `#` comment on the line directly above
   each entry's `disposition:` key, preserving the information without
   breaking the parser. REG002 and COMPLIANCE005 both stay green (17/17
   CMPL_REGISTRY_UNIT_IDS entries now dispositioned handled_by:
   COMPLIANCE005; 0 REG001/REG002/COMPLIANCE005 violations).

2. Added the COMPLIANCE005 rule catalog row and a "### COMPLIANCE005
   (T-0788)" detail section to docs/modules/gates.md, following the
   TICK007 (T-0820) precedent: same row shape in the table, same
   `<!-- frob:describes ... -->` + prose + "Where it runs." structure in
   the section.

Verification: chunked `uv run --frozen frob check --only <stage> --ticket
T-0833` across gates-fast, gates-native, gates-security, lint, static all
report 0 errors after the fix (gates-fast: 0 errors, 1109 warnings, 158
waived; the pre-existing CHK-GATE-COMPLIANCE005 REG008 warning and the
frob-exports static warning are unrelated pre-existing debt, not new).
tests/test_gates.py::TestComplianceGate (5 tests, including
test_compliance005_silent_on_handled_by_and_out_of_scope) all pass.
`git diff main --diff-filter=D --stat` is empty.

No code changes, no new tests -- docs/registry-only ticket per the
ticket's own framing; bound the existing acceptance test as evidence.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestComplianceGate::test_compliance005_silent_on_handled_by_and_out_of_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 1152 warning(s), 207 waived
