---
id: T-2843
title: Split frob.gates._doclink_docanchor's later-bolted docstatus/docmake/docseverity
  gates out
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2375
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_doclink_docanchor.py
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/gates/_docstatus.py
- frob.lock
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: the split needs to repoint frob:doc/frob:tests citations for the 3 extracted
    gates (docstatus/docmake/docseverity) plus any __init__.py re-exports; scope closure
    flagged these on filing
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_gates.py
  reason: the split needs to repoint frob:doc/frob:tests citations for the 3 extracted
    gates (docstatus/docmake/docseverity) plus any __init__.py re-exports; scope closure
    flagged these on filing
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/__init__.py
  reason: the split needs to repoint frob:doc/frob:tests citations for the 3 extracted
    gates (docstatus/docmake/docseverity) plus any __init__.py re-exports; scope closure
    flagged these on filing
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: 'reverting: __init__.py''s own scope closure surface is disproportionate
    (996 warnings, matching the same scope-closure tension documented elsewhere for
    docs/modules/gates.md) -- if a re-export move there proves necessary, it gets
    its own narrow follow-up rather than dragging this ticket''s whole closure surface
    into __init__.py'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_docstatus.py
  reason: 'T-2843: split introduces a new module (_docstatus.py) and updates frob.lock''s
    ack digests for the moved gates; both are part of this ticket''s own scoped work'
  actor: logan
  at: '2026-08-22'
- op: add
  glob: frob.lock
  reason: 'T-2843: split introduces a new module (_docstatus.py) and updates frob.lock''s
    ack digests for the moved gates; both are part of this ticket''s own scoped work'
  actor: logan
  at: '2026-08-22'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-2843: __init__.py''s import block moves for the three relocated gates
    -- in scope for this split'
  actor: logan
  at: '2026-08-22'
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
- tests/test_gates.py::TestDocstatusGate::test_missing_status_header_fires_doc009
- tests/test_gates.py::TestDocmakeGate::test_bogus_make_target_fires_doc010
- tests/test_gates.py::TestDocseverityGate::test_mismatched_severity_row_fires_doc013
- tests/test_gates.py::TestDocseverityGate::test_matching_severity_row_passes
designated_repro_test: null
acceptance:
- text: given frob.gates._doclink_docanchor.py after this lands, when its line count
    is read, then it is under frob.toml's max_file_lines=800 threshold, holding only
    doclink_gate/docanchor_gate (DOC001/DOC002)
  evidence:
  - tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
- text: given the new module holding docstatus_gate/docmake_gate/docseverity_gate,
    when frob check runs, then every existing frob:doc/frob:enforces/frob:tests citation
    for those three gates still resolves (repointed if their target changed, not broken)
  evidence:
  - tests/test_gates.py::TestDocstatusGate::test_missing_status_header_fires_doc009
  - tests/test_gates.py::TestDocmakeGate::test_bogus_make_target_fires_doc010
  - tests/test_gates.py::TestDocseverityGate::test_mismatched_severity_row_fires_doc013
- text: given the full test suite, when it runs after the split, then it passes unchanged
  evidence:
  - tests/test_gates.py::TestDocseverityGate::test_matching_severity_row_passes
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob.gates._doclink_docanchor.py (1035 lines) has a real, investigated seam,
but distinct from the module's own docstring: the docstring describes only
DOC001/DOC002 (doclink_gate/docanchor_gate, "Genuinely one cohesive family,
not two bolted together... both are pure read-only scans over
snapshot/the doc tree, with no shared runtime state between them beyond
the doc-file-reading posture itself"). That reasoning is sound for those
two gates -- but the file ALSO carries three more gates the docstring
never mentions, bolted on later without an update: docstatus_gate
(DOC009/DOC011, line 689), docmake_gate (DOC010, line 849), and
docseverity_gate (DOC013, line 982).

Line ranges:
  doclink_gate + docanchor_gate (the documented family): lines 1-527 (~527
    lines including header/imports)
  docstatus_gate + docmake_gate + docseverity_gate (undocumented later
    additions): lines 528-1035 (~507 lines)

Both halves land comfortably under frob.toml's max_file_lines=800 on their
own. This restores the module to what its own docstring already claims it
is (DOC001/DOC002 only) and gives the three later-bolted gates a home that
matches their own actual shared characteristic: all three are
docs/**/*.md status/freshness checks (a dated status header, a Makefile
target's freshness, a severity-table's currency) rather than the
doc-tree-reachability concern DOC001/DOC002 share.

Extraction was not done inside T-2828 (LARGE001 batch 1/2) for two reasons:

1. docstatus_gate carries its own live frob:waive AFFECT001 that names
   docs/modules/gates.md as under a DIFFERENT in-progress ticket's lease
   at the time it was written (T-1205) -- the same kind of doc-anchor
   cross-reference risk needs re-checking fresh (grep docs/modules/
   gates.md's own frob:describes/frob:enforces citations for all five
   gate names in this file) before moving any of the three, in case
   gates.md's own anchors need updating to point at a new module path.
2. `docanchor_gate`/`doclink_gate` are the only two names this file's own
   docstring says are externally imported (tests/test_gates.py, prose in
   _docblocks.py's own module docstring) -- but that grep predates the
   three later additions, so a fresh repo-wide check for docstatus_gate/
   docmake_gate/docseverity_gate's own external importers (frob.gates
   __init__.py re-exports, any direct `from frob.gates._doclink_docanchor
   import docstatus_gate` elsewhere) is needed before the extraction, not
   assumed from the stale docstring's namespace.

This is a legitimate real split (not a T-1651-style waive candidate) --
scope it explicitly (src/frob/gates/_doclink_docanchor.py, a new
src/frob/gates/_docstatus.py or similar, docs/modules/gates.md if its
anchors need repointing, src/frob/gates/__init__.py if re-exports move)
and land it as its own ticket, same shape as T-2833/T-2834.