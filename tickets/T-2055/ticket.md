---
id: T-2055
title: Land runs TWO full frob check spawns (T-0754 post-merge at 208.7s measured,
  plus T-1410 gate-claims unmeasured); measure the second, then thread the land diff
  into the first
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
evidence_scope:
- tests/unit/test_ticket_close_gate_claims_t1410.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_no_gate_claim_criterion_skips_the_check
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Problem

Every land runs TWO independent, comparably-sized synchronous `frob check`
subprocesses inside the land path. T-1344 measured the first at 208.7s. The
second has never been measured.

1. `_shared_check_spawn_fn` (`src/frob/app/ticket_runner/_verify.py`), the
   T-0754 post-merge re-verification: `python -m frob check --ticket <id>
   --json` against the merged tree, inside the land lock. Measured 208.7s.
2. `_land_gate_claims_fn` (`src/frob/app/ticket_runner/_land_cmd.py`, T-1410),
   the acceptance-criteria claim check: a second `frob check --only gates`
   spawn, run against `worktree` rather than `root`. **Unmeasured.**

T-2053 established, with measurements, that no safe wall-clock reduction
exists inside `_verify.py` alone. Both remaining levers need `_land.py` /
`_land_cmd.py`, which is where this ticket lives.

## Measured evidence from T-2053 (do not re-derive; do sanity-check)

- `--only`/family-skipping on spawn 1 is UNSAFE: `_parse_error_findings_from
  _json` counts an `error`-severity diagnostic from ANY `ToolResult` -- ruff,
  ty, `frob-arch`, `frob-exports`, `frob-cycle`, `frob-dup` -- toward the
  compared claim, not just `gate:*` families. Skipping any stage silently
  narrows what T-0754 verifies.
- `--delta` does NOT reduce wall clock: `check/_python.py` applies delta
  filtering to the already-computed violation list, after every check has run
  in full.
- The T-1346 gate cache WORKS: two consecutive runs on an identical unchanged
  tree went 231s -> 150s (35%), with archgate 32.5s->0.0s, perf 44.8s->0.0s,
  dead_symbols 12.8s->0.0s, pii_structural 11.9s->0.0s, clones 13.0s->0.0s.
  But the land spawn always runs against a FRESHLY MERGED tree that has never
  been measured, and the costliest gates read broadly enough that almost any
  land's diff intersects their tracked file set -- a structural near-always
  miss even though the mechanism is sound.
- The residual ~150s floor on a fully warm cache is spent entirely in the
  ruff/ty/`frob-arch`/`frob-cycle`/`frob-dup`/`frob-exports` lint/static layer
  in `check/_python.py`, which the T-1346 cache never covers.

## The two levers

**A. Thread the land's own diff into spawn 1 as an explicit family selection.**
The land already computes `pre_land_tip` in `_land.py`/`_land_cmd.py`. A small
diff would then re-verify only families it could plausibly touch, flipping the
near-always-miss into a near-always-hit. This is the change T-2053 identified
as most likely to matter and could not make from `_verify.py`.

**B. Measure spawn 2, then decide.** Quantify `_land_gate_claims_fn` the same
way T-1344 quantified spawn 1 -- real timing, per-stage breakdown. If it is
comparable, lands are paying roughly double, and the two spawns may be
shareable (same tree, overlapping stages) or one may be reducible.

DO B FIRST. It is a measurement, it is cheap, and it determines whether A is
even the biggest remaining lever. Do not implement A before knowing B's size.

## Do NOT fix it this way

- Do NOT weaken what either spawn verifies to save time. T-2053 proved
  family-skipping on spawn 1 is unsound as things stand; any narrowing must be
  DERIVED from the land's actual diff, never a fixed allowlist.
- Do NOT simply delete the second spawn because the first exists. They check
  different things (post-merge error parity vs acceptance-criteria claims) and
  run against different trees (`root` vs `worktree`). Prove equivalence before
  merging them, or do not merge them.
- Do NOT raise `_LAND_LOCK_TIMEOUT_S` or the shell cap. Separately, note the
  existing mismatch: `_LAND_LOCK_TIMEOUT_S = 600.0` EXCEEDS the playbook's
  mandated 540-580s wrapper, so a genuinely long land is SIGKILLed with no
  diagnostic before its own timeout can report. That is worth fixing, but by
  making the land FASTER or by aligning the numbers downward -- not by
  extending the cap.
- Do NOT cache across trees without a digest key that includes the merge
  result. A stale cache reporting green is strictly worse than a slow land.

## BUG002 waiver

<!-- frob:waive BUG002 reason="this ticket's own deliverable is a
measurement (spawn 2's timing) plus a verdict on sharing work, not a
code fix -- there is no defect in THIS ticket's own diff to repro. The
bound evidence cites an existing test covering the function that was
measured, per the docs-only-ticket evidence precedent
(docs/guides/agent-playbook.md section 5). The two real defects this
investigation surfaced (the _LAND_LOCK_TIMEOUT_S/shell-wrapper mismatch,
and the open question about what tree check_gates' spawn actually
measures) are filed as their own bug tickets with their own repro
requirements, not folded into this one." -->

## Acceptance criteria

1. A measured per-stage timing of `_land_gate_claims_fn`'s spawn, in the same
   form T-1344 reported for spawn 1. State the tree it ran against and the
   total. THIS IS THE PRIMARY DELIVERABLE.
2. A stated verdict on whether the two spawns can share work, with the reason.
   "They cannot, because X" is a complete answer.
3. If lever A is implemented: before/after wall-clock on a real land, plus
   evidence that the narrowed selection still catches a finding the full run
   would have caught. The first test must FAIL before the fix.
4. Report whether the `_LAND_LOCK_TIMEOUT_S` vs shell-cap mismatch is fixed
   here or needs its own ticket. Do not fix it silently as a side effect.

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
