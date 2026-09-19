---
id: T-draft-f4a30f8e
title: Promote DOCARCH002 from WARN to ERROR once the eight cluster leaves land (and
  decide the docstring/citation halves on the record)
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
blocked_by:
- T-4693
- T-4709
- T-4770
- T-4722
- T-4767
- T-4719
- T-4723
- T-4715
- T-4718
parent: T-4691
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a clean dev tree with all eight clusters landed, when DOCARCH002 is
    ERROR and frob check runs, then it exits 0
  evidence: []
- text: given a deliberately planted 20-line over-cap comment run, when frob check
    runs, then it FAILS -- the positive control without which a green check proves
    nothing
  evidence: []
- text: given the 22 files excluded from the clusters for being leased on 2026-09-19,
    when this leaf closes, then they are either swept or filed as a ninth cluster,
    not waived
  evidence: []
- text: given check 1 also caps docstrings (1055 measured over 20 lines) and check
    2 covers 2303 citations, when this leaf closes, then the ticket states on the
    record which halves are ERROR and which stay WARN
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Final leaf of T-4691, per T-2994's fifth constraint ("IT MUST NOT REGROW"): ship
the gate WARN, burn it down, THEN promote to ERROR. The WARN-then-ERROR sequence
is the TICK011/T-2372 precedent T-2994 cites by name; a sweep without the ERROR
promotion is a temporary cleanup, not a fix.

WHAT: flip DOCARCH002 (T-4693) from WARN to ERROR for the `src/frob/**` surface
once the eight cluster leaves have landed and the ratchet pool baseline is down
to the residue.

BLOCKED BY all eight cluster leaves plus the gate leaf itself. It cannot be taken
earlier: promoting to ERROR while 507 findings are outstanding fails the build for
every agent in the fleet on code they did not write.

RESIDUE THIS LEAF MUST ACCOUNT FOR, not silently absorb:
- The 22 files excluded from every cluster because they were leased by
  in-progress tickets on 2026-09-19 (~95 runs, ~2,288 lines). By the time this
  leaf is takeable those leases have released. Either sweep them here or file a
  ninth cluster; do not promote to ERROR with them still over-cap and waived.
- Docstrings >20 lines: 1,055 of them, 38,964 lines. The cluster leaves cover
  COMMENT runs only. Check 1 of DOCARCH002 caps docstrings too, so ERROR
  promotion for the docstring half needs its own burn-down (T-4623..T-4632 cover
  the test-suite docstrings, not src). State explicitly whether this leaf
  promotes check 1's COMMENT half only and leaves the DOCSTRING half at WARN --
  that is the likely correct answer, and it must be a decision on the record
  rather than an oversight.
- Check 2 (T-#### citations): 2,303 measured blocks. Same question, same
  requirement that the answer be explicit.

ACCEPTANCE IS A MEASUREMENT, NOT A FLAG FLIP. The leaf is done when the rule is
ERROR, `frob check` over a clean dev tree exits 0, and a deliberately planted
over-cap comment run FAILS the check (positive control -- a green check proves
nothing on its own; see the standing "positive control or it proves nothing"
lesson).
