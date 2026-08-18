---
id: T-2519
title: 'confinement census: give parameter-position credit to close 727 of 740 UNKNOWN
  sites'
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: high
parent: T-2501
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/summary.py
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
T-2504's census (landed 5f01c7b01, numbers in
docs/modules/graph.md#path-confinement-census) measured the confinement
lattice over tests/**: 608 files, 11545 functions, 2989 recognized
fs.write call sites.

    ROOTED   2248  (75%)
    ESCAPED     1
    UNKNOWN   740  (25%)

The risk this ticket exists to close: 727 of those 740 UNKNOWN (98%) are
a SINGLE disclosed precision limit, not genuine unprovability. A helper
that writes directly to its own plain-named `Path` parameter, without
returning it, gets no interprocedural credit -- so every call site
flowing through such a helper reads UNKNOWN even when the caller passed a
provably ROOTED path. `tests/test_ticket_land.py` alone accounts for 208
of the 727.

By contrast, actual poison propagation from unresolved callees -- the
failure mode T-2504 was explicitly told to watch for, and the one that
would have made this whole approach untenable -- is only 13 sites across
5 helpers. It did not materialize.

DELIVERABLE: give parameter-position confinement credit. A function whose
`Path`-typed parameter is written to, and which does not escape that
parameter, should summarize as "param_N confined => writes confined", so
callers passing a ROOTED value get ROOTED credit at the call site. This
is the same bottom-up summary shape `frob.graph.summary` already computes
for protocol state; it needs a parameter-indexed lattice entry, not a new
traversal.

WHY THIS MATTERS FOR THE GATE DECISION: at 75% ROOTED with the remainder
concentrated in one fixable gap, path confinement is TRACTABLE as a gate.
If this lands and converts the bulk of the 727, the UNKNOWN tail becomes
small enough to burn down or waive individually, and `confined to`
(T-2501 epic) can move from report-only to enforced.

ESCAPED is already actionable at 1 site: that verdict class can ship at
ERROR severity independently of this ticket, since a provably-escaping
write is a real bug and there is exactly one.

CONSTRAINTS CARRIED FROM T-2504, non-negotiable:
- Do NOT weaken the lattice to improve the numbers. A site that genuinely
  cannot be proven must stay UNKNOWN. The point of the three-state result
  is that UNKNOWN never renders as a pass (T-2391 fail-loudly doctrine).
- Re-run the census after the change and report the NEW numbers against
  the old ones. A precision improvement that cannot show its delta has
  not demonstrated anything.
- Positive controls both directions still apply: an absolute literal must
  stay ESCAPED, a tmp_path-derived write must stay ROOTED, and a helper
  that DOES escape its parameter (writes it to an absolute path, or
  reassigns from os.environ) must NOT receive credit.
