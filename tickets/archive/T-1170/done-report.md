## Done report

Extracted the DOC001/DOC002 doclink/docanchor gate family (doclink_gate,
docanchor_gate, and their private helpers -- doclink config/obligated-set/
crawl/hint, the DOC001 violation builder, anchor-slug resolution, the
DOC002 violation/mismatch-message builders, and the per-edge anchor
checker) verbatim into src/frob/gates/_doclink_docanchor.py
(gates/__init__.py 8401 -> 8128 lines), following the T-1072/T-1140/
T-1159 one-family-per-land discipline: directives carried intact, a
top-level (not lazy) import back into __init__.py matching the
_decisions_compliance precedent, design/frob.strata interface= synced
via frob sys sync-interface.

Three cross-module private helpers needed explicit re-export rather than
staying opaque-private: _doclink_config/_obligated_docs (consumed by a
docblock-fence scan still in __init__.py) and _docanchor_check_edge
(consumed by a doc-completeness check still in __init__.py) are named in
the new module's __all__ and imported at __init__.py's top level.
_doc_anchor_slugs (consumed by _fix_engine.py's DOC002 Tier-A auto-fix
handler via a lazy call-time import) was repointed to import directly
from its new home instead of routing back through frob.gates, avoiding
an unnecessary re-export.

Requeued the remaining ~10 families honestly as residue: T-1174
(re-titled to name only what's still remaining after this land, per
TICK011 -- budget for this wave allowed exactly one cohesive family).

### Changed
```
 tickets.md | 67 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 65 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocanchorGate::test_resolvable_heading_and_explicit_anchor_pass` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_doc002_unique_fuzzy_candidate_rewritten_and_reverifies_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 935 warning(s), 497 waived
- error-findings: none (measured, zero errors)
