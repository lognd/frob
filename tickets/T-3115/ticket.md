---
id: T-3115
title: WIRE003 reports the working 'frob refactor' verb as unresolvable; the verb
  is also missing from frob --help
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the measured false positive, the real discoverability gap, and the
    warning not to fix it by silencing the hook
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3234
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27 on a full `frob check` of main. WIRE003 fires seven times:

    WIRE003: .claude/hooks/frob-suggest.py references frob verb 'refactor',
             which does not resolve against the live CLI dispatch
    (x5 for 'refactor', x2 for 'rename')

THE CLAIM IS FALSE. `frob refactor --help` exits 0 and prints
`usage: frob refactor [-h] {move,rename,split} ...`. The verb resolves and
works -- three tickets used it successfully today (T-3066, T-3105, and the
yamlio rename).

WHAT IS ACTUALLY TRUE, and it is a real and separate defect: `refactor` is
ABSENT from `frob --help`'s subcommand list. The advertised dispatch table runs
`{scaffold,cycle,explore,quality,design,ops,outline,map,xref,parse,dup,arch,
docs,exports,bind,agent,worktree,check,gitlog,graph,ack,debt,deprecated,pool,
profile,registry,ticket,test,vet,perf,release,mutate,stats,serve,sys,deploy,
fleet,doctor,clean,fmt,format,claude,natives,coverage,verify,sync-skills}` --
no `refactor`. So the verb is real but UNDISCOVERABLE from the CLI's own help.

TWO DEFECTS, BOTH IN SCOPE:

(1) WIRE003 RESOLVES VERBS AGAINST THE WRONG SOURCE. It evidently consults the
    advertised help/subcommand listing rather than the actual dispatch, so a
    working-but-unlisted verb reads as broken. That is a false positive in a
    gate whose entire job is to catch references to things that do not exist --
    and a gate that cries wolf on a working verb trains readers to ignore it.
    This is the same class as today's other measurement-integrity findings: the
    check answers a slightly different question than its message claims.

(2) `refactor` SHOULD BE DISCOVERABLE. An agent cannot be expected to use a
    verb that `frob --help` does not mention. This repo has a standing
    directive to prefer `frob refactor` over hand-editing imports, and a hook
    (T-3069, landed today) that actively nudges agents toward it -- while the
    CLI's own help denies it exists. Fix the listing, or if it is deliberately
    hidden, say why in the code and make WIRE003 aware of the hidden set.

Note the interaction that makes this urgent: T-3069's nudge hook now tells
agents to run `frob refactor`. If WIRE003 is "fixed" by editing the HOOK to
stop naming the verb, the nudge is destroyed and the standing directive loses
its enforcement. Do not take that shortcut -- the hook is right and the gate is
wrong.

ALSO CHECK: whether other real verbs are missing from the advertised listing,
and whether `move-module` (referenced in tickets and prose from earlier work)
still exists -- `frob refactor --help` lists only `{move,rename,split}`.
Report what you find; a verb cited in ticket bodies that no longer exists is
its own problem.

ACCEPTANCE
- WIRE003 no longer fires on `refactor`/`rename`, and does so because it now
  resolves against real dispatch -- not because the hook stopped naming them.
  Must-stay-quiet fixture on a working-but-unlisted verb.
- WIRE003 still fires on a genuinely non-existent verb. Must-fire fixture -- do
  not solve this by weakening the gate.
- `frob --help` lists `refactor`, or the deliberate omission is documented and
  WIRE003 knows about it.
- The audit of missing verbs and of `move-module`'s existence is reported.
