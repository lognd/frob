---
id: T-1226
title: 'docs integrity: close the silent-miss classes from the 2026-07-29 staleness
  sweep'
state: done
kind: docs
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- docs/audits/docs-staleness-2026-07-29.md
- tickets/T-2080/**
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/docs-staleness-2026-07-29.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_doclink.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_docanchor.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/graph/**
  reason: 'narrow to the audit doc alone: this pass corrects the gate-gap-class status
    table against current main (5 of 6 classes shipped, catalogued and re-verified
    as wired not just present), no gate mechanism code touched this pass; those files
    also no longer exist under these names (merged into _doclink_docanchor.py)'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/gates/_doclink.py
  reason: 'narrow to the audit doc alone: this pass corrects the gate-gap-class status
    table against current main (5 of 6 classes shipped, catalogued and re-verified
    as wired not just present), no gate mechanism code touched this pass; those files
    also no longer exist under these names (merged into _doclink_docanchor.py)'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/gates/_docanchor.py
  reason: 'narrow to the audit doc alone: this pass corrects the gate-gap-class status
    table against current main (5 of 6 classes shipped, catalogued and re-verified
    as wired not just present), no gate mechanism code touched this pass; those files
    also no longer exist under these names (merged into _doclink_docanchor.py)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2080/**
  reason: residue ticket filed by this ticket's own investigation pass, needed for
    the land's touched-set
  actor: logan
  at: '2026-08-10'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
121-doc staleness sweep (docs/audits/docs-staleness-2026-07-29.md): 2 class-A gate-flagged findings, ~140 class-B silent misses, 6 gate-gap classes, a drift-lock candidate list, and one code-side bug. Every silent miss indicts a frob gate gap: each gap class becomes a mechanism ticket, plus a fix campaign for the doc content itself.

## Done report

Re-measured all six 2026-07-29 gate-gap classes against current main
(2026-08-10), by reading the wired gate registry
(src/frob/gates/__init__.py's `docblocks`/`doclink`/`docanchor`/
`docstatus`/`docmake` lambdas), not by trusting a module's mere existence
on disk -- a first grep pass for `docenum_gate`/`negexist_gate` found
nothing and would have wrongly reported classes 1/3 as still-unwired
dead code; re-checked against the actual exported names
(`docenum001_gate`, `negexist001_gate`) and both are wired.

Results: classes 1 (T-1227, DOCENUM001), 2 (T-1228, DOC006 file::symbol +
bare-identifier kinds), 3 (T-1229, NEGEXIST001), 5 (T-1231, DOC008), and
6 (sub-items 1/2/3 per the audit doc's own prior status) are DONE. Class
4 is PARTIAL: T-1230 shipped only the Makefile-target-citation sub-case
(DOC010); frob.toml-severity and other non-Makefile config surfaces
remain open, split out as T-2080.

Updated docs/audits/docs-staleness-2026-07-29.md's "Gate-gap classes"
section to record this status per-class, with the ticket id and wiring
evidence for each -- the section previously read as if all six were
still open design work, which was stale.

Not done in this pass (disclosed, not silently dropped): the ~140
class-B doc-content findings themselves (the fix campaign the mechanism
work exists to prevent from recurring) are untouched -- that is separate,
much larger scope than this ticket's own declared files.

### Changed
```
 tickets/T-1226/ticket.md           | 33 ++++++++++++++++++++++----
 tickets/T-2080/ticket.md | 48 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 77 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, PERF004@src/frob/tickets/_land.py, PII012@src/frob/testing/_coverage_refresh.py, SELFAUDIT001@design
