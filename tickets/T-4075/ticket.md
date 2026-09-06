---
id: T-4075
title: 'M-2: invariant binding two L5 rows for cross-row consistency'
state: queued
kind: invariant
origin: agent
created: '2026-09-06'
priority: medium
parent: T-4071
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_inv.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the existing frob:invariant binding format, when this ticket's design
    step runs, then it reports whether binding two independent anchors (a route guard
    and an L5 spec row) to one invariant is already supported or requires new surface
  evidence: []
- text: given a route guard's actual role check diverging from its L5 spec row's stated
    role dispatch, when frob check runs, then the bound invariant fails
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
M-2 (F-273). VERIFIED: no gate compares two L5 spec rows against each other today -- SYS100 is about capabilities, COV/DOC are about doc edges (a symbol's frob:doc anchor resolving), neither compares the CONTENT of two rows for mutual consistency.

FINDING THIS WOULD HAVE CAUGHT: an admin role that cannot reach /portal (COMP-1805's role dispatch) despite a separate L5 row stating admin should have access -- two individually-consistent rows that contradict each other, invisible because nothing ever reads them together. Proposed: a frob:invariant bound to the actual guard code stating which roles may reach a route (e.g. /portal), with the L5 row describing the role dispatch (COMP-1805) bound to the SAME invariant -- so a change to either the code or the spec row that breaks the pairing becomes a failing invariant rather than two rows that each individually look fine.

SCOPE NOTE: this needs the existing frob:invariant binding machinery (src/frob/gates/_inv.py) to support binding TWO separate sources (a route guard's code and an L5 spec row) to one invariant rather than the current one-invariant-one-anchor shape -- verify during design whether the existing binding format already supports multiple anchors on one invariant id, or whether that is itself new surface this ticket must add.
