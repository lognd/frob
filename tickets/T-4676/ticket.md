---
id: T-4676
title: 'SF-23: verify then scope COV002''s per-declaration frob:ticket demand inside
  .strata files (archive/T-0164''s boilerplate class)'
state: in-progress
kind: bug
origin: agent
created: '2026-09-19'
priority: low
parent: T-4666
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/gates/test_cov002_strata_declarations.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_tickets_gate.py
  reason: T-3899 holds active lease on _tickets_gate.py; cannot touch, per BRIEF do-not-touch-leased-elsewhere
    rule
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/unit/gates/test_cov002_strata_declarations.py::TestCov002StrataDeclarationsStandingRegression::test_module_edge_covers_several_declarations_no_per_decl_edges
- tests/unit/gates/test_cov002_strata_declarations.py::TestCov002StrataDeclarationsStillFiresWithNoEdgeAtAll::test_no_ticket_edge_anywhere_still_fires
designated_repro_test: null
acceptance:
- text: Given tickets/archive/T-0164/ticket.md already named the class 'COV002 demands
    per-declaration frob:ticket edges inside .strata files -- boilerplate', when this
    ticket starts, then T-0164 and its done-report are read FIRST and the premise
    is confirmed against HEAD c8f56ef10 before any change -- if T-0164's own fix already
    handled it, this closes as verified-with-evidence and no code changes.
  evidence:
  - tests/unit/gates/test_cov002_strata_declarations.py::TestCov002StrataDeclarationsStandingRegression::test_module_edge_covers_several_declarations_no_per_decl_edges
- text: Given the premise holds, when this lands, then a fixture .strata file with
    several declarations and NO frob:ticket directives is asserted to produce zero
    COV002 findings -- a positive control that fails at HEAD; the test stays as the
    standing regression either way.
  evidence:
  - tests/unit/gates/test_cov002_strata_declarations.py::TestCov002StrataDeclarationsStandingRegression::test_module_edge_covers_several_declarations_no_per_decl_edges
  - tests/unit/gates/test_cov002_strata_declarations.py::TestCov002StrataDeclarationsStillFiresWithNoEdgeAtAll::test_no_ticket_edge_anywhere_still_fires
acceptance_amendments:
- op: remove
  index: 3
  old_text: Given COV002 also lives in _fix_engine.py, _fix_engine_text.py, _fix_engine_sync.py
    and _waive.py, when the .strata path proves to be in one of those, then scope
    --add it and coordinate with T-4671 before touching _fix_engine_sync.py.
  new_text: null
  reason: 'conditional criterion whose premise did not hold: the .strata COV002 path
    lives in _tickets_gate.py only, so no scope into _fix_engine_sync.py was needed
    (see body PREMISE CHECK)'
  actor: logan
  at: '2026-09-20'
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
SF-23 (LOW). Leaf of story C (T-4666) under epic T-4662. Story points: 1.
IMMEDIATELY DISPATCHABLE -- no blockers.

EVIDENCE. tickets/archive/T-0164/ticket.md (planner-confirmed present, with a
done-report) is titled: "COV002 demands per-declaration frob:ticket edges inside
.strata files -- boilerplate". It is cited in the audit so this epic knows the
per-declaration-directive boilerplate pattern PREDATES the current self-model:
the same shape now shows up as SF-08 (33 identical assume lines) and SF-10
(15.4% literal duplicate declarations). The difference is that SF-08/SF-10 are
grammar questions for the owner (story D), while this one is a GATE
applicability question and can be settled now.

THE QUESTION THIS LEAF SETTLES
Whether COV002's per-declaration coverage demand applies to declarations inside
.strata files at all. A .strata declaration is a model statement, not a public
code symbol; demanding a frob:ticket edge per declaration produces exactly the
boilerplate T-0164 named, and it scales as (nodes x declarations) against a
self-model that already has 26 nodes, 119 flows, 162 attr and 113 via lines.

WHAT TO BUILD
Read tickets/archive/T-0164/ticket.md and its done-report FIRST -- per
memory/verify-premise-before-filing.md, confirm COV002 still demands this before
changing anything; if T-0164's own fix already handled it, close this leaf as
verified-with-evidence and say so, do not invent work. If it does still demand
it, scope COV002 so .strata declarations are not treated as coverage-bearing
public symbols.

POSITIVE CONTROL (the test that fails today)
A fixture .strata file carrying several declarations and NO frob:ticket
directives, asserted to produce zero COV002 findings. If the premise holds this
fails at HEAD; if it does not fail, that is the verified-premise outcome above
and the test stays as the standing regression either way.

SCOPE NOTE: COV002 is implemented across src/frob/gates/_tickets_gate.py,
_fix_engine.py, _fix_engine_text.py, _fix_engine_sync.py and _waive.py. This
leaf scopes _tickets_gate.py plus its test only, to stay disjoint from leaf A4
which owns _fix_engine_sync.py. If the .strata path proves to live in one of the
others, `frob ticket scope --add` it and coordinate with A4 before touching
_fix_engine_sync.py.