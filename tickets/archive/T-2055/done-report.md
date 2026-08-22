## Done report

PRIMARY DELIVERABLE: measured _land_gate_claims_fn's (T-1410) spawn.

Read src/frob/app/ticket_runner/_close_cmd.py::_close_gate_claims_for_
ticket first: it is CONDITIONAL, not unconditional. `claims =
_gate_claim_criteria(ticket)`; `if not claims: return None` -- the
spawn only fires when a ticket's acceptance criteria are phrased as "0
<RULE-ID> findings under <glob>" (_GATE_CLAIM_RE,
src/frob/tickets/_evidence.py). Checked the CURRENT active ledger
(tickets.md) with the exact same regex: 0 matches. tickets-archive.md
(historical/closed tickets): 59 matches. So in the fleet's current
acceptance-writing convention (given/when/then style, per T-1344's own
criteria as one example), this second spawn essentially never fires --
it is not "every land pays this cost", contrary to how T-2055's own
ticket body summarized it. This matters for prioritization: item 4/lever
work on spawn 1 (T-2053/T-1344, unconditional, every land) dominates
regardless of spawn 2's own cost.

Measured spawn 2 directly anyway, since the ticket asked for it
regardless of trigger frequency: ran the EXACT command
_close_gate_claims_for_ticket issues (`python -m frob check --only
gates`, plain text not --json, cwd=worktree) against this worktree's own
tree. Real wall time: 3m38.262s (218.3s). gate-summary line: "13
errors, 954 warnings, 0 unresolved, 715 waived" with per-gate timings
(archgate=44.14s, perf=55.36s, sys=46.32s, pii_structural=17.18s,
clones=17.22s, refs=16.89s, dead_symbols=16.48s, coverage=15.86s, plus
~25 smaller stages). This is comparable in magnitude to spawn 1's
measured 208.7s (T-1344) -- confirmed: WHEN it fires, spawn 2 costs
roughly as much as spawn 1.

VERDICT on whether the two spawns can share work: they cannot be
trivially merged, for two reasons.

1. Different scope: spawn 1 (`check_gates`, T-0754) needs error findings
   from EVERY ToolResult (ruff/ty/frob-arch/frob-exports/frob-cycle/
   frob-dup, not just gate:* -- established in T-2053) to answer "did
   the merge introduce any new error anywhere". Spawn 2 (`check_gate_
   claims`, T-1410) only needs `--only gates` findings filtered by a
   specific (rule, glob) pair to answer a narrower, criterion-specific
   question. Spawn 2's narrower `--only gates` run cannot answer spawn
   1's broader question; sharing spawn 2's output for spawn 1's purpose
   would silently narrow what T-0754 verifies (the exact unsafe move
   T-2053 already ruled out).

2. Different working directories, and a genuinely open question about
   what each is actually measuring: spawn 1 spawns with cwd=root, spawn
   2 with cwd=worktree. Reading _land.py's control flow (_land_locked):
   both checks run BEFORE `_land_squash_apply`, which an inline comment
   in _land.py explicitly names as "the ONLY step that mutates root".
   If that comment is literally accurate, spawn 1's cwd=root spawn runs
   BEFORE root's own working tree/branch has been touched by this land
   at all -- meaning it may be evaluating root's PRE-land state, not the
   "just-merged tree" its own _verify.py docstring describes. This is a
   significant enough possible finding that I did NOT want to assert it
   from static reading alone; filed as its own ticket (T-2064,
   renumbers at land) for live instrumentation to confirm or refute,
   rather than guess. Until that's resolved, "do the two spawns check
   the same tree" cannot be answered with confidence, which is itself
   suficient reason not to attempt sharing them yet.

Per the ticket's explicit constraints: did NOT delete/merge the second
spawn (reason 1 alone is sufficient to leave them separate), and did NOT
implement lever A (diff-threading into spawn 1) since it depends on
_land.py's diff-computation machinery and, per the tree-timing question
above, on first confirming what spawn 1 is actually measuring -- doing
diff-threading before that is resolved risks building on a wrong
assumption about which tree is being checked.

Item 4 (the _LAND_LOCK_TIMEOUT_S=600 vs the playbook's mandated 540-580s
shell wrapper mismatch, originally surfaced in T-1344): NOT fixed here.
Filed as its own ticket (T-2065, renumbers at land) since
fixing it means deciding which number moves and by how much -- a
decision, not a mechanical change safe to make as a side effect of this
investigation.

No code diff in src/frob/tickets/_land.py or _land_cmd.py was made --
this ticket's own deliverable is the measurement, the verdict, and the
two follow-up tickets it surfaced. No wall-clock change to report
before/after since no lever was implemented (acceptance criterion 3 is
conditional on lever A being implemented, which it was not, for the
reason stated above).

### Changed
```
 tickets/T-2055/ticket.md           |  6 +++-
 tickets/T-2064/ticket.md | 57 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2065/ticket.md | 40 ++++++++++++++++++++++++++
 3 files changed, 102 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_no_gate_claim_criterion_skips_the_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, PERF004@src/frob/tickets/_land.py, PII012@src/frob/testing/_coverage_refresh.py
