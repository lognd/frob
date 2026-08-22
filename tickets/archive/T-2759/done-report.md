## Done report

Changed:
- docs/modules/tickets-verify-sweep.md:1030 (wrapped the T-2736 citation in backticks)

DOC011 fired on `docs/modules/tickets-verify-sweep.md:1030` because that
line's T-2736 citation (T-2744's own doc update, narrating the phantom-
ticket incident by name) was bare prose text, not inside a code span --
DOC011/`frob.gates._markdown_scan.strip_code_spans` exempts a ticket-id-
shaped token only when it is inside inline `` `code` `` (T-1700). The
line 1000 citation of the same id was already inside a backtick span and
never fired. Fixed by wrapping the line 1030 citation in single
backticks, matching the existing convention already used one paragraph
above it -- NOT by an inline `frob:waive DOC011` HTML comment (tried
first, but confirmed a no-op: `frob ticket land`'s own malformed-
directive warning names the exact set of rules markdown waivers are read
for, and DOC011 is not among them: `['BUG002', 'DOC004', 'DOC006',
'INV003', 'INV004', 'REF001', 'REF002']`).

Evidence: none applicable -- doc-only single-line fix, no code/test
surface changed. Verified directly against the real production code path
(`frob.gates._markdown_scan.strip_code_spans`, the same stripper DOC011
itself uses): `'T-2736' in strip_code_spans(Path(...).read_text())` is
`False` after the fix (`True` before it).

Filed: none.

Gates: DOC011 false positive at docs/modules/tickets-verify-sweep.md:1030
resolved, confirmed against the gate's own stripping primitive.

### Changed
```
 tickets/T-2759/done-report.md | 36 +++++++++++++++++++++++++++++++++
 tickets/T-2759/ticket.md      | 30 +++++++++++++++++++++++++++
 2 files changed, 66 insertions(+)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 21 error(s), 904 warning(s), 705 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@tickets/T-2742/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2759, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
