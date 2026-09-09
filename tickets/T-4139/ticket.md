---
id: T-4139
title: a frob:doc pointer at a non-existent anchor resolved to nothing for as long
  as it was landed, with no finding, contradicting DOC002's own stated contract
state: in-progress
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_doclink_docanchor.py
- tests/gates_suite/test_doc.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates_suite/test_doc.py
  reason: 'T-4139: DOC002/DOC014 fixtures live in the shared gates_suite doc test
    file; evidence for this ticket''s own new code'
  actor: logan
  at: '2026-09-09'
- op: remove
  glob: tests/gates_suite/test_doc.py
  reason: 'T-4139: reverting -- moving new fixtures to a dedicated test file instead
    to avoid dragging the whole shared test_doc.py''s cross-referenced symbols into
    scope closure'
  actor: logan
  at: '2026-09-09'
- op: add
  glob: tests/gates_suite/test_doc.py
  reason: 'T-4139: doclink_gate/docanchor_gate''s pre-existing frob:tests directives
    already point here; DOC002/DOC014 fixtures for this ticket''s own change live
    in this shared gates_suite doc test file'
  actor: logan
  at: '2026-09-09'
- op: add
  glob: frob.lock
  reason: 'T-4139: frob ack of doclink_gate writes here'
  actor: logan
  at: '2026-09-09'
evidence:
- tests/gates_suite/test_doc.py::TestDocanchorGate::test_unresolvable_anchor_fires_identically_python_and_typescript
- tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_real_anchor_still_passes
- tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_row_with_no_matching_section_fires
- tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_section_with_no_matching_row_fires
- tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_reported_once_per_document_not_per_row
- tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_table_not_named_component_symbol_or_section_is_ignored
designated_repro_test: null
acceptance:
- text: given a doc directive whose target slug has no heading and no anchor tag in
    the target file, when gate DOC runs, then a DOC002 error is reported at the pointer
  evidence: []
- text: given the same broken pointer attached to a python symbol and to a non-python
    symbol, when gate DOC runs, then both are reported identically
  evidence: []
- text: given a component table row with no matching section, when the document is
    checked, then it is reported once at the document rather than once per inbound
    pointer
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A DOC POINTER AT AN ANCHOR THAT DOES NOT EXIST RESOLVED TO NOTHING, SILENTLY,
FOR AS LONG AS IT HAS BEEN LANDED. Reported as logand.app-v2 F-341: a component
was given a table row but no heading section, so every doc pointer aimed at that
component's slug has pointed at nothing since it landed, with NO finding
reported. Their agent root-caused it only while chasing something else.

THIS CONTRADICTS DOC002'S OWN STATED CONTRACT, and that contradiction -- not the
missing heading -- is what this ticket is about. Our module docstring in
src/frob/gates/_doclink_docanchor.py says plainly that DOC002 enforces "that
every frob:doc edge's own file-hash-slug target actually resolves to a real
anchor in that file". The anchor extractor `_doc_anchor_slugs` (same file, around
line 430) collects markdown heading slugs plus explicit anchor-id tags. A table
row is neither. So DOC002 SHOULD have fired here, loudly, with the nearest-match
suggestion its message builder already produces.

It did not. Either the rule has a hole, or the edge never reached it. FIND OUT
WHICH BEFORE CHANGING ANYTHING -- they need opposite fixes, and a fix for one
applied to the other leaves the defect in place while looking resolved.

A HYPOTHESIS TO TEST FIRST, EXPLICITLY LABELLED AS A HYPOTHESIS BECAUSE I HAVE
NOT MEASURED IT: the reporting repo's surface is largely TypeScript, and this
repo has an open finding that no symbol is emitted for some TypeScript
constructs, plus seven recorded instances of code paths that assume python. If
the doc edge is attached to a symbol the collector never emits, DOC002 has
nothing to check and its silence is structurally guaranteed rather than a rule
bug. That would make this the same class as the TEST002 finding filed as T-4138,
where a non-python stack produced no measurement and the absence was rendered as
a clean result. TEST THIS BY CONSTRUCTION: point a doc directive at a
non-existent anchor from a python symbol and from a TypeScript symbol in the same
repo, and compare what DOC002 says about each. If they differ, the collector is
the defect, not the gate.

WHY THIS RANKS ABOVE ITS APPARENT SIZE. A doc edge is one of the three bindings
this entire tool is built on. If a binding can point at nothing and still count
as satisfied, then the obligation graph reports coverage it does not have, and
every doc-coverage number computed from it is an overcount of unknown size. That
is the "catalogued is not enforced" failure applied to frob's own core promise.
Note the reporter found this by accident; nothing in the system was ever going to
tell them.

THE SECOND ASK IS ALSO RIGHT AND IS CHEAPER: check the row/section pairing in
both directions -- a table row with no section, and a section with no row. That
catches the authoring mistake at the document rather than at each pointer, and it
is a bounded, local check.

THERE IS A CAUSAL CHAIN WITH T-4127 WORTH SEEING BEFORE EITHER IS FIXED. This
rule requires a heading per component for a pointer to resolve. Honouring it
produces exactly the document shape T-4127 is about: one file carrying many
anchors, each bound to a different symbol -- which then makes scope closure
demand every one of those symbols in any ticket touching one row. So the doc rule
pushes authors toward the file shape the scope rule punishes. Fixing either in
isolation risks making the other worse; whoever works the second one should read
the first one's outcome.

MUST-FIRE FIXTURE:   a doc directive whose target slug has no heading and no
                     anchor tag in the target file produces a DOC002 error at the
                     pointer, and does so identically for a python symbol and a
                     non-python one.
MUST-STAY-QUIET:     a directive pointing at a real heading anchor still passes,
                     and a slug differing only in case or punctuation resolves
                     the way it does today.
THIRD FIXTURE:       a component table row with no matching section, and a
                     section with no matching row, are each reported once at the
                     document rather than once per inbound pointer.

ACCEPTANCE
- Determined and recorded whether DOC002 has a hole or never received the edge,
  proven by the python-versus-non-python comparison above.
- A pointer at a non-existent anchor is an error at the pointer.
- Row/section pairing checked in both directions.
- The interaction with T-4127 stated rather than left for the next reader.
- All three fixtures committed.
