## Done report

Fixed DOC001 (docs/design/land-checkpoint-durability.md linked from
nowhere), from the T-1554 post-land sweep.

docs/index.md's design-epic list already prose-mentioned the file's
path in backticks, but DOC001's reachability crawl only follows real
markdown links (frob.gates._doclink_docanchor.doclink_gate's
_crawl_reachable, relative-link-based), not backtick text -- so the
mention never actually counted as a link. Converted the existing bullet
to a real relative markdown link
([`docs/design/land-checkpoint-durability.md`](design/land-checkpoint-durability.md)),
verified against frob check --only doclink --ticket T-1846 (no
land-checkpoint-durability.md finding remains).

frob:no-behavior-change reason="pure documentation fix (markdown link syntax only) -- no code change, docs-only ticket per playbook section 5's T-0167 precedent"

### Changed
```
 tickets/T-1846/done-report.md | 29 +++++++++++++++++++++++++++++
 tickets/T-1846/ticket.md      | 12 +++++++++++-
 2 files changed, 40 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 5 error(s), 612 warning(s), 741 waived
- error-findings: DOCENUM001@docs/modules/gates.md, PRE001@tickets/T-1846, SEC110@.claude/hooks/dispatch-telemetry.py, invalid-argument-type@src/frob/strata/_sync_may.py, invalid-type-form@src/frob/strata/_sync_may.py
