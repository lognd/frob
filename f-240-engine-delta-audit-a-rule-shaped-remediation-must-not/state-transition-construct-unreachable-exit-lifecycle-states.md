+++
id = "01M1T07NY7WADPN0G6N1M6NZ7K"
title = "state/transition construct: unreachable-exit lifecycle states"
type = "story"
flavour = "quality_objective"
category = "todo"
priority = "low"
parent = "01M1T07NY4QCBYNNMPSJDNWN5E"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:22Z"
aliases = ["T-4039"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/strata/_models.py"]

[[acceptance]]
text = "given a design note for the state/transition construct's grammar (named states, required edges, terminal-state declaration), when this ticket's design step completes, then the note is attached before implementation, and it explicitly does not reuse or merge with the existing ten-instance no-exit class"
bound = false

[[acceptance]]
text = "given a declared state with no outgoing transition and no terminal declaration, when the reachability check runs, then it is flagged"
bound = false
+++

Item 6. VERIFIED: git grep for a state/lifecycle/transition construct across src/frob/strata/_models.py found nothing -- strata models nodes, flows and capabilities today, no state-machine/lifecycle concept at all. This is a genuinely new construct, not a duplicate.

FINDING THIS WOULD HAVE CAUGHT (two findings, one missing construct): a frame loop reaching a STOPPED state with no path back to RUNNING, and input latches reaching a HELD state with no path back to RELEASED -- in both cases a state machine with a state that structurally has no exit edge, discovered only by manual reading rather than any check. Proposed: a thin state/transition construct -- named states plus required edges -- checked for reachability (every declared state must have at least one outgoing transition, or be explicitly declared terminal).

A NOTE ON RESONANCE, DELIBERATELY NOT A MERGE, per the coordinator's explicit instruction: this queue separately tracks a "no-exit" class at ten instances (a RULE demanding an artifact the subject structurally cannot provide -- e.g. a waiver mechanism with no escape hatch for a legitimately-unfixable case). That is a DIFFERENT population from THIS item (a state machine lacking a transition edge in the SUBJECT's own design, nothing to do with a rule/waiver interaction). Shared abstraction ("no way out"), different subject and different detector. Do NOT treat the ten existing no-exit instances as evidence for this item's priority or design, and do not build one detector expecting it to cover both -- design this as its own construct against its own two motivating findings.
