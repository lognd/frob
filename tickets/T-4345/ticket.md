---
id: T-4345
title: Playbook doc edge names the moved stage-group mapping and no longer resolves
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/agent-playbook-appendix.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A DOCUMENTATION EDGE POINTS AT A SYMBOL THAT MOVED, AND IT IS THE ONLY ERROR LEFT
IN THE TREE.

MEASURED ON MAIN. An unscoped gate run reports exactly one error, and this is it:
a guide's enumerates-edge names the stage-group mapping in the check module, which
no longer resolves. The rule reports no candidate replacement, so it cannot guess
the intended target.

THE CAUSE IS KNOWN AND RECENT, WHICH MAKES THIS CHEAP. A ticket landed earlier
today moved the single declaration of gate stage-group membership out of the check
module and into the gates module, deriving the check module's view from it lazily
behind a module-level attribute hook. That was the right change and is not in
question. The consequence is that the old name is no longer statically resolvable,
so a documentation edge naming it dangles. The same land updated several docs for a
related rule but this edge was missed.

REPOINT THE EDGE AT THE REAL DECLARATION SITE rather than at whatever restores a
green run. The authoritative mapping now lives in the gates module; the check
module's version is derived. A doc edge should name the thing that actually
declares the data, so that a future reader following it lands on the source of
truth and not on a derived view.

WHILE YOU ARE THERE, READ THE SURROUNDING PROSE. The passage enumerates stage
groups for an audience following a playbook. If the recent change altered how
membership is declared -- and it did, membership is now mandatory at declaration
and enforced at import time -- then a paragraph describing the old two-list
arrangement is stale in substance and not only in its edge target. Fix what is
actually wrong; do not repoint a link above a paragraph that now misdescribes the
system.

CHECK FOR SIBLINGS. If one edge named the moved symbol, others may too. Search for
remaining references to the old location across docs and code comments and say
what you found, even if the answer is none.

VERIFY WITH AN UNSCOPED RUN and quote the exact error count; the target is zero.
Measure with `uv run frob check --json` parsed for error severity, or via
`python3 scripts/check_summary.py` -- not by grepping text output, since an absent
errors section is indistinguishable from a clean one and has produced false zero
reports here.

ONE CAVEAT ON MEASUREMENT, because it will otherwise mislead you: the unscoped gate
has been observed returning DIFFERENT error sets for the same commit under
concurrent load (filed as T-4343). If you get a surprising result, re-run before
believing it, and prefer checking the specific rule against the specific file
directly over trusting a single whole-gate run.
