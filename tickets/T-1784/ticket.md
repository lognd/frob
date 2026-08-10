---
id: T-1784
title: 'New rule: flag repo-root asset directories with zero code references'
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1611 classification: today's session produced the "root agents/
skills/ are live-read by the dispatching harness" incident. T-1767's
audit concluded KEEP, reporting the 13 tracked SKILL.md files
"empirically confirmed live-read" because their prose content happened
to match this very session's own system-prompt role definitions and
available-skills roster near-verbatim -- a coincidence of AUTHORSHIP
(the harness's real ~/.claude/agents, ~/.claude/skills were almost
certainly seeded FROM these files at some point), misread as proof of a
LIVE LOAD PATH. T-1772 corrected it: `grep` across src/frob/** for
`agents/`/`skills/` path references returns nothing, pyproject.toml
packages `src/` only, `frob scaffold` does not emit either directory --
nothing in this repo's own code reads either tree. Deleted.

Classified as NO RULE EXISTS for this obligation. This is not a
misfire of DEAD001 or REF002 -- both are scoped to Python
symbols/`.strata` fixture files respectively; neither one's domain
covers "a whole repo-root directory of markdown assets that a doc or
ticket claims is read by some process." The verification that settled
T-1772 (grep the tree for path references, confirm packaging config,
confirm scaffold does not emit it) was manual and ad hoc; nothing
mechanizes it, so the same wrong "must be live, the names match" READ
can recur on the next repo-root directory someone audits.

Add a rule: for each repo-root top-level directory NOT under `src/`,
`tests/`, `.git/`, or an explicit allowlist (docs/, tickets/, design/,
scripts a Makefile target actually invokes, etc.), verify at least one
of (a) `src/frob/**` references its path literally, (b)
`pyproject.toml`'s package/data-files config includes it, (c)
`frob scaffold`'s own data emits it, or (d) an explicit
`frob:external-reader reason="..."` doc-side declaration names the
external process that reads it (the harness-config case: a real,
checkable claim instead of an inferred one). A directory satisfying
none of the four is flagged -- not auto-deleted, just surfaced, so the
next audit starts from a measured "zero code references" fact instead
of re-deriving it from scratch and getting fooled by name-matching
again.
