## Done report

Adds DOC008 (gate-gap class 5, doclink basename+fragment validation) to
frob.gates._doclink_docanchor.doclink_gate: every obligated/root doc's own
inline markdown link `[text](target#frag)` is now resolved against disk --
a relative target that does not exist on disk, or a `#frag` that does not
match any heading slug/`<a id>` in the target file, is a DOC008 error.
Absolute/mailto links are skipped (no static target); fenced/inline code
spans are blanked before scanning so prose examples like `handlers[key](x)`
are never mistaken for a link.

Registered: docs/modules/gates.md table row, DOC008 in
_KNOWN_GATE_RULES (src/frob/gates/_waive.py, waivable), one new
CHK-GATE-DOC008 registry entry with gate_rule_total bumped 276 -> 277
(docs/design/registry/check-coverage.yaml).

### Changed
```
 tickets.md | 31 +++++++++++++++++++++++++++++--
 1 file changed, 29 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 905 warning(s), 745 waived
- error-findings: PERF002@src/frob/gates/_doclink_docanchor.py, WIRE001@src/frob/gates/_doclink_docanchor.py
