---
id: T-2080
title: 'gate-gap class 4 (non-python doc targets): frob.toml severity + remaining
  config surfaces still unanchored'
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/audits/docs-staleness-2026-07-29.md
- src/frob/gates/_doclink_docanchor.py
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
- docs/modules/gates.md
- tests/test_gates.py
- tickets/T-2766/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrow package glob to the specific files docseverity_gate (DOC013) actually
    touches
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: narrow package glob to the specific files docseverity_gate (DOC013) actually
    touches
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/gates/__init__.py
  reason: narrow package glob to the specific files docseverity_gate (DOC013) actually
    touches
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/check/__init__.py
  reason: narrow package glob to the specific files docseverity_gate (DOC013) actually
    touches
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/gates.md
  reason: narrow package glob to the specific files docseverity_gate (DOC013) actually
    touches
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_gates.py
  reason: narrow package glob to the specific files docseverity_gate (DOC013) actually
    touches
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tickets/T-2766/**
  reason: filed follow-up ticket for the live arch.md severity-table drift the new
    DOC013 gate found
  actor: logan
  at: '2026-08-20'
evidence:
- tests/test_gates.py::TestDocseverityGate::test_mismatched_severity_row_fires_doc013
- tests/test_gates.py::TestDocseverityGate::test_matching_severity_row_passes
- tests/test_gates.py::TestDocseverityGate::test_no_override_is_a_noop
- tests/test_gates.py::TestDocseverityGate::test_ambiguous_doc_word_is_never_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-1226 (measured 2026-08-10). Gate-gap class 4 (NON-PYTHON
TARGETS, docs/audits/docs-staleness-2026-07-29.md) is only partially
closed: T-1230 shipped DOC010, which resolves `` `make <target>` ``
citations against real Makefile targets
(`src/frob/gates/_doclink_docanchor.py::docmake_gate`, wired).

Still open, no dedicated mechanism:
- frob.toml severity claims in prose (e.g. "ARCH101 is a report, not a
  gate" when frob.toml declares it error) have no anchor -- DOC006's
  kind 3 (CONFIG REFERENCE) only resolves <!-- frob:waive DOC006 reason="[section]/[section.key] here is _docptr's own generic placeholder shape describing DOC006's kind-3 grammar, not a real config reference" -->`[section]`/`[section.key]`
  existence, not a claimed VALUE against the real one.
- pyproject.toml entries, tmLanguage grammar lists, and other non-Rust,
  non-Makefile config surfaces still have no graph node at all.
- Rust file layout/symbol citations are now covered incidentally by
  class 2's T-1228 FILE::SYMBOL kind (<!-- frob:waive DOC006 reason="path.rs::name is a generic placeholder shape illustrating the FILE::SYMBOL grammar, not a real file citation" -->`path.rs::name`), not by a
  dedicated class-4 mechanism -- worth confirming that coverage is
  sufficient before scoping new work here, rather than re-deriving it.

Suggested first step: measure how many of the original finding's
non-Makefile NON-PYTHON TARGETS instances (docs/audits/docs-staleness-
2026-07-29.md's own "Non-python targets" section, 3 items) are now
already caught incidentally by T-1228's Rust FILE::SYMBOL kind before
designing new mechanism work -- the denominator may already be smaller
than the original finding implies.