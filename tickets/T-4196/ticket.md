---
id: T-4196
title: 'allow several ticket ids in one frob:ticket directive: 217 stacks of three
  or more exist, two of them fourteen lines deep'
state: queued
kind: feature
origin: human
created: '2026-09-07'
priority: medium
parent: null
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
- text: given a directive naming several ticket ids, when it is parsed, then the symbol
    binds to all of them and each resolves as it would alone
  evidence: []
- text: given an existing single-id directive, when it is parsed, then behaviour is
    identical to today
  evidence: []
- text: given a renumber of one ticket, when it rewrites a multi-id directive, then
    the other ids on that line are undisturbed
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ALLOW SEVERAL TICKET IDS IN ONE `frob:ticket` DIRECTIVE, so a symbol touched by
many tickets does not accumulate a stack of near-identical comment lines above it.
Owner request.

MEASURED ACROSS EVERY TRACKED PYTHON FILE, counting runs of consecutive
`frob:ticket` comment lines:

    run length   occurrences
        1            7979
        2             760
        3             143
        4              48
        5              19
        6               2
        7               2
        9               1
       14               2

    stacks of three or more: 217
    worst offenders: 14 consecutive lines in the waiver gate module and 14 in
                     the application config module, 9 in the sys runner,
                     7 in the land module and 7 in the CLI entry point

Collapsing every multi-id stack to one line removes roughly 1,300 lines of pure
bookkeeping from the source. That is the quality-of-life case, and it is real: a
reader scrolling past fourteen consecutive directive lines to reach a function is
being taxed for the tool's convenience.

WHAT TO BUILD
  1. Accept several ids after the verb, space separated. Decide explicitly
     whether commas are also accepted and say so -- this repo already has a
     defect where one separator was defended and another silently was not, and
     the inconsistency produced a scope entry that matched nothing.
  2. Keep the single-id form working unchanged. Nearly eight thousand existing
     directives use it and none should need touching.
  3. MAKE THE MARKDOWN FORM AGREE. The markdown variant is parsed by its own
     pattern that captures exactly one id. If the comment form learns multiple
     ids and the markdown form does not, the two spellings of the same directive
     diverge -- which is the desync this project exists to prevent.

THE PART MOST LIKELY TO BE MISSED, AND IT IS THE DANGEROUS ONE: the renumber path
rewrites ticket ids inside directives, matching on the directive keyword. If it
is not taught about multiple ids on one line, renumbering will either miss the
trailing ids or corrupt the line. This repo has a recorded incident where a bare
renumber invocation rewrote every ticket id in the queue, so this path deserves
its own fixture rather than an assumption. Check every consumer that parses or
rewrites these directives, not only the reader.

DO NOT SHIP AN AUTO-COLLAPSE OF EXISTING STACKS IN THIS TICKET. A separate open
ticket records that the land's auto-fix currently rewraps directive comments and
SPLIT A NODE ID ACROSS A LINE BREAK, silently breaking the binding while the
comment still reads correctly. Until that is fixed, a bulk rewrite of directive
comments is the last thing this repository should run. Land the parser support
first; collapse the stacks later, deliberately, once the wrapper is safe.

MUST-FIRE FIXTURE:   a directive naming several ids binds the symbol to all of
                     them, and each id resolves exactly as it would alone.
MUST-STAY-QUIET:     every existing single-id directive behaves identically, and
                     a stack of single-id directives still works -- this is
                     additive, not a migration.
THIRD FIXTURE:       renumbering a ticket rewrites its id inside a multi-id
                     directive without disturbing the other ids on that line.

ACCEPTANCE
- Several ids accepted in one directive, with the separator question decided
  explicitly.
- The markdown form accepts the same shape as the comment form.
- Every parser and rewriter of this directive enumerated and updated, renumber
  included, each with a fixture.
- No bulk auto-collapse of existing stacks in this ticket.
- All three fixtures committed.
