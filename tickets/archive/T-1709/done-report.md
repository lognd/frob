## Done report

Fixed the two real, unscoped `frob check --land-parity` findings T-1700's
land introduced (caught immediately post-land, before starting the next
ticket):

- INV006: src/frob/gates/_markdown_scan.py's module docstring uses
  exclusivity language with no bound invariant. Added
  `frob:waive INV006 preset="split-carried-prose"`, the same convention
  every other design-rationale-heavy module in this package already
  carries (_compliance.py, _arch.py, ...).
- PII012: tests/unit/gates/test_markdown_scan.py's
  test_line_wrapped_inline_span_is_blanked_as_one_token matched the
  PII-shaped keyword heuristic on the substring "token" (category
  credentials). Waived with a reason explaining "token" here means a
  single lexical unit of markdown, not a credential -- same convention
  already used at src/frob/gates/_tickets_gate.py:682/690 and
  src/frob/gates/_todo_fmt.py:263 for the identical false-positive shape.

Also investigated two ty-check findings `--land-parity` reported at the
same tree state (invalid-parameter-default in
tests/unit/test_ticket_runner_gate_findings.py, unresolved-attribute in
tests/test_ticket_work_and_land_finish.py) -- neither reproduced after a
native rebuild (`make core`), and neither file was touched by T-1700 or
this ticket; both were transient native-staleness artifacts, not real
regressions. `frob check --land-parity` is clean (0 unscoped errors)
after the two real fixes above.

Verified with:
- `uv run pytest tests/unit/gates/test_markdown_scan.py -p no:cacheprovider -q` -- 9 passed.
- `uv run ruff check`/`ruff format --check` -- clean.
- `uv run frob check --only invariant --only pii_structural` -- both
  findings gone (INV006 absent entirely; PII012 shows `[waived: ...]`).
- `uv run frob check --land-parity` -- clean, 0 unscoped errors.

frob:no-behavior-change reason="waiver-comment-only fix (frob:waive INV006/PII012 directives) -- no production logic changed, so the existing test correctly passes both before and after"

### Changed
```
 tickets.md | 233 +++++++++++++++++++++++++++++++++++++++++--------------------
 1 file changed, 158 insertions(+), 75 deletions(-)
```

### Evidence
- `tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_line_wrapped_inline_span_is_blanked_as_one_token` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 123 warning(s), 716 waived
- error-findings: none (measured, zero errors)
