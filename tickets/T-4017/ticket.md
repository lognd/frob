---
id: T-4017
title: 'F-231: close reports AcceptanceUnbound for an evidence-cmd containing a comma,
  though show and the YAML both read it as bound'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
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
Consumer logand.app-v2 F-231, 2026-09-06, with a clean controlled experiment.

WHAT THEY OBSERVED. On T-0199 they bound
`--evidence-cmd "python3 -c \"...,...\"" --accepts 1`. The evidence was recorded,
and `frob ticket show` displayed it as bound under acceptance [1] -- visible
correctly in the ticket's YAML as one multi-line evidence id string. Then
`frob ticket close` reported AcceptanceUnbound for that exact criterion.
REBINDING A SECOND, COMMA-FREE evidence-cmd made close succeed immediately with
no other change.

THAT IS A CONTROLLED EXPERIMENT AND IT IS THE STRONGEST PART OF THE REPORT: one
variable changed (a comma in the command text), outcome flipped. Their suspected
cause is that close's matcher splits the evidence-cmd string on commas.

I NARROWED IT BEFORE FILING, AND THEIR SUSPECT IS PROBABLY THE WRONG HALF.
`unbound_acceptance` in src/frob/tickets/_models.py:768 does an EXACT set
membership test:

    evidence_set = set(ticket.evidence)
    ... if not any(e in evidence_set for e in c.evidence)

No splitting, no tokenising, no normalisation. So the comparison is not where a
comma can do damage. The desync must be UPSTREAM: either the criterion's own
`c.evidence` list is populated from a comma-joined string when `--accepts` is
applied, or the id is serialised/deserialised differently on the two sides. START
THERE -- specifically at how `--accepts` writes the binding, and at the YAML
round-trip for a multi-line scalar -- rather than at the matcher.

NOTE WHAT THE SYMPTOM IMPLIES: `show` and the YAML both display the binding
correctly, and only `close` disagrees. So the stored state is right and one
READER of it is wrong, which points at a second, divergent way of reconstructing
the criterion's evidence list. That is the same shape as several defects already
in this queue -- two code paths answering one question, one of them re-deriving
instead of reusing.

WHY THIS DESERVES MORE THAN ITS "friction" SEVERITY. A silent false negative on
CLOSE means correctly-evidenced work is refused, and the failure names the
criterion rather than the mechanism, so the user has no path to the cause. They
found it by luck and a rebind. Worse, the workaround they landed on -- "use a
comma-free evidence-cmd" -- is invisible tribal knowledge that will not survive
into the next repo. They avoided it cleanly on T-0193 only because they already
knew.

CONNECTED: T-4000 (F-215) covers evidence-cmd recording an empty-output no-op as
genuine evidence, and notes there is NO WAY TO REMOVE a bad cmd: entry. That
compounds here -- the remedy in this incident was to bind a SECOND evidence-cmd,
leaving the first, comma-bearing one permanently in the ledger. Read the two
together; a fix for one should not assume the other's state is retractable.

MUST-FIRE FIXTURE: an evidence-cmd whose command text contains a literal comma
binds to an acceptance criterion AND satisfies close.
MUST-STAY-QUIET: a genuinely unbound acceptance criterion is still reported at
close.
THIRD FIXTURE: `show`, the YAML, and `close` agree on whether a criterion is
bound -- for a comma-bearing id, a multi-line id, and a plain node id. That
three-way agreement is the real invariant and the reason this bug was invisible.

ACCEPTANCE
- The divergent reader identified, with the exact-membership comparison in
  _models.py:768 ruled in or out by measurement rather than assumption.
- Whatever re-derives the criterion's evidence list made to reuse one code path.
- All three fixtures committed.