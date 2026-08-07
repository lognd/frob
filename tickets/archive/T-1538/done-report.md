## Done report

Verified this ticket's premise no longer holds: the stale doc anchor it
describes (docs/modules/gates.md's frob:describes pointer for the moved
redaction engine) was already corrected in T-1318's own land (commit
a579f23e0..., see `git log -S "src/frob/security/_redact.py::_redact" --
docs/modules/gates.md`) -- before this refile of the ledger-corrupted
T-1538 draft was even created. The live anchor already reads
`<!-- frob:describes src/frob/security/_redact.py::_redact -->`, matching
exactly what this ticket asks for.

Confirmed with a fresh, unscoped-family gate run against the file:
`uv run frob check --only docanchor --only doclink --only drift --only
docblocks --ticket T-1538` reports 0 errors and 4 warnings, all four
pre-existing and unrelated (DOC006 findings in tickets.md, not
gates.md).

Dropped via `frob ticket drop T-1538 --reason ...` rather than closed
done, since there is no code/doc change left to make -- the described
defect does not exist on this branch.

### Changed
```
 tickets.md | 9 ++++++++-
 1 file changed, 8 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
