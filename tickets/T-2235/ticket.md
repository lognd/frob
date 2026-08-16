---
id: T-2235
title: 'frob check --budget silently drops whole gate families and exits normally:
  41 errors became 3 with no skip signal anywhere in the JSON'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/_check_chunking.py
- src/frob/app/check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'A --json --budget run that cannot execute every planned gate emits an explicit
    record of which gates were NOT run, by name (fails today: JSON has only path and
    results)'
  evidence: []
- text: A run that executed everything reports that positively -- an empty skipped-list
    must be distinguishable from an absent field
  evidence: []
- text: 'MUST-STILL-PASS: unbudgeted frob check --json and a sufficient budget both
    produce current results unchanged (findings, ordering, exit codes)'
  evidence: []
- text: 'Exit-code semantics unchanged: a partial run with no findings must not start
    reporting failure'
  evidence: []
- text: Stderr/summary states in human-readable form that gates were skipped, without
    requiring JSON parsing
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# `frob check --budget` silently drops whole gate families and exits normally, so a partial run reads as a dramatic improvement

## Measured evidence (2026-08-16)

Two runs of the SAME command, same budget, ~90 minutes apart, on the same repo:

    timeout 540 uv run frob check --json --budget 480

    run 1: exit=1   52 results   41 errors
    run 2: exit=1   15 results    3 errors

Run 2 exited with code 1, NOT 124 -- it was not killed by the shell timeout. It
terminated normally having run 15 of the 52 gates.

What run 2 silently omitted: `gate-summary`, `gate:ARCH`, `gate:COV`, and every
other `gate:*` family. It ran only the standalone tools (`frob-cycle`,
`frob-dup`, `frob-arch`, `claude-config-drift`, and the 11 `frob-exports(...)`
entries).

Consequently the error count fell 41 -> 3, which reads as a 93% improvement.
It is fiction: TICK004 (9 rot findings), COV004 (4), DOC011 (2), DRIFT001 (3),
ARCH001, TEST010 and COV001 were all still present and simply never evaluated.
I came within one sentence of reporting a floor drop that had not happened.

## The output gives a consumer no way to detect this

`--json` emits exactly two top-level keys:

    top-level keys: ['path', 'results']

Every element of `results` carries only `tool`, `exit_code`, `diagnostics`,
`tests`, `summary`. There is no budget record, no skipped/unrun marker, no
expected-total, and no `gate-summary` entry whose ABSENCE is itself the only
available hint. Nothing in stderr says a family was dropped either -- grepping
the stderr for `budget|truncat|exhaust` returns 0 matches, because those words
are never emitted.

So a consumer cannot distinguish "15 gates ran and the repo is clean" from
"15 of 52 ran and 37 were dropped". Both look identical, and the dropped case
looks BETTER because it reports fewer findings.

## Why this matters beyond one measurement

The budgeted path is not a niche flag. It is how the coordinator measures the
error floor and how post-land sweeps assess a tree. A mechanism whose failure
mode is "reports fewer errors, exits normally, says nothing" is the exact shape
that produces a false green -- and this repo has already paid for that shape
twice: T-1928 (FMT gate passing in 0.00s while `frob fmt --check` would rewrite
267 files) and T-1664, which established the governing rule that a check must
report UNRESOLVED rather than silently pass when it cannot analyse. That rule
is enforced for individual semantic checks but NOT for the runner's own
budget-driven gate selection.

## Do NOT fix it this way

- **Do NOT just raise the default budget.** That changes when the silence
  happens, not that it is silent. The defect is the missing signal.
- **Do NOT make `--budget` hard-fail when it cannot run everything.** Budgeted
  quick loops are legitimate and agents depend on them; turning a partial run
  into an error would break `--only` workflows and land-time checks.
- **Do NOT infer completeness by counting results and comparing to a
  hardcoded 52.** That number changes with `--only`, with per-package
  `frob-exports` expansion, and as gates are added. Completeness must be
  reported by the runner, which knows what it planned and what it skipped --
  not reconstructed by the reader.
- **Do NOT fix this only in `scripts/check_summary.py`.** A coordinator script
  papering over it leaves every other consumer (sweeps, land-time checks, other
  agents) still blind. The JSON is the contract; fix it there. Teaching
  check_summary to SURFACE the new field is fine as a follow-on.

## Acceptance criteria

1. (MUST FAIL FIRST) A `--json --budget N` run that cannot execute every
   planned gate emits an explicit record of what was NOT run -- names, not just
   a count. Fails today: the JSON has only `path` and `results`, with no such
   field anywhere. Confirm `--check-repro` reads FAILED_AT_PARENT.
2. A run that DID execute everything reports that fact positively (an empty
   skipped-list is not the same as an absent one, and a consumer must be able
   to tell "nothing skipped" from "this build of frob does not report skips").
3. MUST-STILL-PASS CONTROL: an unbudgeted `frob check --json` and a budget
   large enough to finish must both still produce their current results
   unchanged. A fix that alters findings, ordering, or exit codes on the
   complete path is out of scope and worse than the bug.
4. The exit code semantics do not change: a partial run with no findings must
   not start reporting failure. This is a REPORTING fix.
5. Stderr or the summary states plainly, in human-readable form, that gates
   were skipped -- an operator reading a terminal must see it without parsing
   JSON.

## Scope note

`--budget` is consumed at `src/frob/app/check_runner.py:1028-1029`, which
delegates to `_run_budgeted_check` in `src/frob/app/_check_chunking.py` -- that
is where the plan-vs-executed knowledge lives. Verified by reading the call
site, not inferred from module names. If the skip decision turns out to live
elsewhere, widen scope with a measured reason rather than guessing.
