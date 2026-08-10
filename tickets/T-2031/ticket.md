---
id: T-2031
title: frob-suggest does not cover hand-rolled coordinator measurement, so scripts/check_summary.py
  and fleet_status.py are bypassed and their known failure modes re-hit
state: dropped
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

The coordinator loop keeps hand-rolling measurements that purpose-built
scripts in `scripts/` already encode correctly, and keeps hitting the exact
failure mode those scripts were written to prevent. The scripts exist, are
documented (`docs/guides/coordinator-scripts.md`), carry `frob:doc` anchors
and tests -- and are still bypassed, because nothing surfaces them at the
moment the wrong command is typed.

`scripts/check_summary.py`'s own module docstring records the prior incident:

    `frob check --json` nests severity two levels deep
    (`results[].diagnostics[].severity`, NOT a top-level `findings` list),
    and reading it at the wrong level silently reports zero -- which
    happened, and produced two false "0 errors" reports before it was
    caught. This encodes the correct traversal once instead of re-deriving
    it inline each time.

## Measured recurrences (2026-08-10, one coordinator hour)

1. Floor measurement. Ran
   `uv run frob check --only gates 2>&1 | grep -E "^(ERROR|FAIL|gate:|Summary|[0-9]+ error)" | tail -25`.
   Output was EMPTY and the pipeline reported `EXIT=1`. An empty grep result
   from an ERRORED command is indistinguishable from a genuine zero. This was
   caught only because the operator happened to recall the footgun; the
   correct tool (`scripts/check_summary.py`) was not used. Re-running with
   full output captured showed the real answer: 4 errors, 946 warnings.

2. Root-dirtiness diagnosis. Diagnosing a `DirtyMain` deadlock took roughly
   six hand-rolled tool calls (`git status --porcelain`, `ps aux | grep`,
   `git diff --stat`, `git log`) to establish root cleanliness, whether a land
   was in flight, and which worktrees were idle. `scripts/fleet_status.py`
   answers exactly this in one invocation and says so in its docstring: "This
   is the one-shot check that answers 'is it safe to dispatch, and which
   worktrees are actually idle?'".

Both are the same class: a documented mechanism exists, and the operator
re-derives it inline and inherits a known failure mode.

## Why the written rule is not the fix

`docs/guides/coordinator-scripts.md` already documents these scripts. The
guidance is written down and was not followed. Per the standing
repeated-mistake procedure, when a mistake recurs despite a written rule, the
rule is not the fix -- find what enforces it.

There is already a mechanism in this repo that demonstrably works on this
exact operator: the `frob-suggest` hook. It fired twice in the same hour and
was obeyed both times:

- blocked a direct `uv run ruff check ...` with "[raw-linters] Prefer
  `uv run frob check` ... A single linter passing is not the repo being clean."
- blocked `make coverage` with "[make-target] Prefer the `uv run frob ...`
  subcommand ... Workflows belong in frob subcommands, not GNU-make recipes."

Both blocks changed the command actually run. That is tier (a) enforcement --
refusal at the moment the mistake is made -- and it already exists; it simply
does not cover coordinator measurement commands.

## Proposed fix

Extend the `frob-suggest` hook with a rule class covering hand-rolled
coordinator measurement:

- A `frob check` invocation piped into `grep`/`awk`/`head`/`tail` for the
  purpose of counting findings -> suggest
  `uv run frob check --json | python3 scripts/check_summary.py`.
- A hand-rolled root-state probe (`git status --porcelain` combined with
  `ps aux | grep frob`, or a `git worktree list` sweep) -> suggest
  `python3 scripts/fleet_status.py`.

The hook's existing block-once-then-allow semantics are the right strictness:
the operator can still run the raw command when it is genuinely correct, but
cannot do so unknowingly.

## Do NOT fix it this way

- Do NOT add another line to `docs/guides/coordinator-scripts.md` or to the
  agent playbook. Documentation is what already failed here, twice, in one
  hour. Another sentence is not enforcement.
- Do NOT make the scripts louder (banner output, warnings on the wrong
  invocation). The problem is that the scripts are never invoked at all --
  output they never produce cannot warn anyone.
- Do NOT delete or rewrite the scripts to be "more discoverable" by folding
  them into frob subcommands as part of THIS ticket. That may be worth doing
  (T-1808 folded `sync-claude-config.py` into a real verb, so there is
  precedent), but it is a separate, larger change and does not by itself stop
  a hand-rolled `grep` pipeline from being typed.
- Do NOT make the hook refuse outright with no escape. A coordinator
  sometimes genuinely needs the raw command; block-once-then-allow preserves
  that while removing the "I did not know" failure mode.

## Acceptance criteria

1. A test that runs a `frob check ... | grep ...` style command through the
   hook and asserts it is blocked with a message naming
   `scripts/check_summary.py`. THIS TEST MUST FAIL BEFORE THE FIX -- confirm
   it fails first and record the observed failure output.
2. A test that a hand-rolled root-state probe is blocked with a message
   naming `scripts/fleet_status.py`.
3. A test that the SECOND identical invocation is allowed through, preserving
   block-once-then-allow.
4. A test that an ordinary `uv run frob check --only gates` with no counting
   pipeline is NOT blocked -- the rule must not fire on normal use.
5. Report the denominator: enumerate the coordinator measurement commands
   used this session and state how many the new rules would have caught.
   Do not claim coverage that was not measured.

## Drop reason
- 2026-08-10: Fix applied, but NOT as a repo change: the frob-suggest hook lives at ~/.claude/hooks/frob-suggest.py (user scope, outside any frob-tracked repo), so there is nothing for a frob worktree to land. Added two rules there directly with user authorisation: handrolled-floor-count (frob check piped into grep -> scripts/check_summary.py) and handrolled-fleet-probe (git status --porcelain AND ps aux/pgrep/git worktree list in one command -> scripts/fleet_status.py). 12/12 test cases pass including the negative cases this ticket required: plain 'frob check --only gates', '| tail -30', 'git grep | grep', and bare 'git status --porcelain' all stay quiet. Testing caught a disarmed-guard bug: the first pattern used [^|;&]* between 'frob check' and the pipe, which cannot cross the & in 2>&1, so it matched nothing while looking correct.
