---
id: T-0522
title: INV003/INV004 doc-side frob:waive detection can self-match illustrative example
  text in gates.md's own prose
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: regression test for fix lives here
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestInv003Gate::test_illustrative_example_reason_does_not_self_waive
designated_repro_test: null
threat: null
component: null
---
Found while working T-0515: _DOC_WAIVE_MARKER_RE (frob.gates.__init__) matches any '<!-- frob:waive INV003|INV004 reason="..." -->' text found anywhere in a file's raw text, with no distinction between a REAL waiver marker and an ILLUSTRATIVE example demonstrating the syntax in prose. docs/modules/gates.md's own INV003/INV004 documentation necessarily spells out the marker syntax as a literal example, e.g. reason="..." (literal three dots) -- which is non-empty and satisfies the regex, so gates.md has silently self-waived its own INV003 and INV004 findings since T-0509/T-0515, never appearing in the residual list despite having plenty of exclusivity/normative prose. Fix direction: either scan for the marker only outside fenced/inline code (the same _strip_markdown_noise pass find_exclusivity_claims/find_normative_claims already apply, which would not help here since these examples are NOT inside code fences), or require the reason text to not be a placeholder ellipsis/generic string, or accept this as a known limitation and document it explicitly in docs/modules/gates.md's INV003/INV004 sections. Low priority since it only affects gates.md's own meta-documentation of the gate today, but the same trap would silently hit ANY doc that ever explains the waiver syntax by literal example.