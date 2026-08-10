---
id: T-2033
title: Extend frob-suggest to cover hand-rolled coordinator measurement (successor
  to T-2031, dropped in error)
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
## Successor to T-2031 (dropped in error by the coordinator)

T-2031 described this work correctly and was DROPPED ON A FALSE PREMISE. The
coordinator concluded the `frob-suggest` hook lived only at
`~/.claude/hooks/frob-suggest.py` (user scope, outside any tracked repo) and
so had nothing to land. That was wrong: `.claude/hooks/frob-suggest.py` IN
THIS REPO is the source of truth, and `uv run frob claude sync` materializes
it into `~/.claude/` (T-1808). Editing the materialized copy created drift,
which `frob` reported within one command:

    Claude config DRIFT: 1 managed file(s) differ from ~/.claude,
    0 source(s) missing -- reconcile with `frob claude sync`

`frob ticket requeue` cannot recover a dropped ticket ("T-2031 is dropped,
not in-progress -- only an in-progress ticket can be requeued"), so this
successor carries the work. Read `tickets/T-2031/ticket.md` for the full
measured evidence, the "Do NOT fix it this way" section, and criteria 1-5;
all still apply unchanged.

## The work

Add two rules to `_RULES` in `.claude/hooks/frob-suggest.py` (the REPO copy):

- `handrolled-floor-count` -- a `frob check` piped into `grep`, suggesting
  `uv run frob check --json | python3 scripts/check_summary.py`. Exempt when
  `check_summary` already appears in the command.
- `handrolled-fleet-probe` -- fires only when BOTH a `git status --porcelain`
  AND one of `ps aux` / `pgrep` / `git worktree list` appear in one command,
  suggesting `python3 scripts/fleet_status.py`. Exempt when `fleet_status`
  already appears.

Working, tested regexes (12/12 including negatives) are in
`~/.claude/hooks/frob-suggest.py`; treat them as a starting point, not gospel.

## The disarmed-guard finding (put this in a CODE COMMENT, not just a report)

The gap character classes must be `[^|;]*`, NOT `[^|;&]*`. The first attempt
excluded `&`, which cannot cross the `2>&1` present in nearly every real
invocation, so the rule matched NOTHING while looking correct. It surfaced
only because the positive case was actually executed rather than the regex
eyeballed. A guard never exercised against a real input is indistinguishable
from one that does not exist.

## Do NOT fix it this way

- Do NOT edit `~/.claude/hooks/frob-suggest.py`. It is a derived artifact;
  the next `frob claude sync` overwrites it. Two people made this exact
  mistake within one hour, which is itself worth noting in the writeup.
- Do NOT add documentation instead. Documentation is what already failed
  here twice in one hour.
- Do NOT widen the rules to fire on ordinary `frob check` usage. An
  over-firing hook trains everyone to bypass it and protects nothing.

## Acceptance criteria

1. All of T-2031's criteria 1-5, unchanged. Criterion 1's test MUST FAIL
   before the fix; watch it fail and record the output.
2. Negative cases that must stay QUIET: `uv run frob check --only gates`
   alone; `uv run frob check --only sys 2>&1 | tail -30`;
   `git grep -n foo | grep bar`; a bare `git status --porcelain`.
3. Positive cases that must FIRE: `uv run frob check --only gates 2>&1 |
   grep -E "^(ERROR|FAIL)"`; `git status --porcelain | wc -l; ps aux | grep
   frob`.
4. State whether a drift check between the repo source and the materialized
   copy ALREADY exists (the drift warning implies one does). If it exists,
   cite it; do not duplicate it. If it does not, say so.
