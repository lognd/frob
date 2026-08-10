---
id: T-2055
title: Land runs TWO full frob check spawns (T-0754 post-merge at 208.7s measured,
  plus T-1410 gate-claims unmeasured); measure the second, then thread the land diff
  into the first
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
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
