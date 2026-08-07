## Done report

_DOC_WAIVE_MARKER_RE (frob.gates.__init__) matched a literal
<!-- frob:waive INV003/INV004 reason="..." --> marker anywhere in a
file's raw text, with no distinction between a genuine waiver and an
ILLUSTRATIVE example demonstrating the syntax in prose. docs/modules/
gates.md's own INV003/INV004 documentation necessarily spells out the
marker syntax with a literal reason="..." placeholder, so gates.md was
silently self-waiving its own INV003/INV004 findings.

Added _DOC_WAIVE_PLACEHOLDER_RE and treat a reason consisting only of a
"..." ellipsis (2+ dots) the same as an empty reason in
_file_has_reasoned_doc_waiver -- a placeholder reason no longer counts
as a real, reasoned waiver. Verified this actually surfaces gates.md's
own findings post-fix (frob check --only invariant now reports INV003
and INV004 on docs/modules/gates.md, both WARN-severity, non-blocking).

Added a regression test using the exact gates.md example text.

### Changed
```
 src/frob/gates/__init__.py  | 20 +++++++++++++++++++-
 src/frob/tickets/_models.py | 25 ++++++++++++++++++++++---
 tests/test_gates.py         | 19 +++++++++++++++++++
 tests/test_tickets.py       |  9 +++++++++
 tickets.md                  | 45 +++++++++++++++++++++++++++++++++++++++------
 5 files changed, 108 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInv003Gate::test_illustrative_example_reason_does_not_self_waive` (pytest node id, verified passing when recorded)
