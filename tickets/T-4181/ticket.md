---
id: T-4181
title: the version bumper has no argument parsing, so asking it for help mutates the
  manifest and dirties the shared checkout
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/bump_version.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the script invoked with a help flag, when it runs, then it prints usage
    and changes nothing
  evidence: []
- text: given the script invoked with no arguments, when it runs, then it bumps the
    patch version exactly as today
  evidence: []
- text: given the script invoked with an unrecognised argument, when it runs, then
    it refuses and changes nothing
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE VERSION BUMPER MUTATES THE REPOSITORY WHEN ASKED WHAT IT DOES. Found by
walking into it: I ran the script with the universal help flag to learn its
interface, and it bumped the version instead, leaving the manifest modified in
the shared checkout.

    $ <the bump script> --help
    bumped -> 0.530.1
    0.530.1

    $ git status --porcelain
     M pyproject.toml

THE CAUSE IS THAT IT HAS NO INTERFACE AT ALL. The script is a handful of lines
that import the canonical bump function and call it at module scope. There is no
argument parsing, so every invocation is a bump: with a help flag, with a typo,
with a stray argument copied from another command. It cannot decline, because
nothing looks at what it was asked.

WHY A HELP FLAG SPECIFICALLY IS THE WORST CASE. Asking a program what it does is
the one invocation a user expects to be free. Every convention in the ecosystem
treats it as read-only, which is exactly why it is the first thing anyone types
at an unfamiliar script. A mutating response inverts that contract, and it
punishes the careful behaviour rather than the careless one.

THE SECOND-ORDER COST IS REAL IN THIS REPOSITORY. The mutation lands in the
PRIMARY CHECKOUT's manifest, and a dirty shared root blocks every concurrent
agent land. So an operator satisfying their curiosity can stall a fleet, with the
cause invisible in the agents' own output. Two agents were mid-ticket when I did
this; I noticed and reverted within the same minute, but only because I check
root cleanliness by habit.

WHAT TO DO
  1. Give it an argument parser that accepts no positional arguments, prints a
     usage line for a help flag, and REFUSES anything unrecognised. The refusal
     matters as much as the help text -- an unrecognised argument must not fall
     through to the mutation.
  2. Consider whether it should refuse to run against a dirty tree, or against
     the primary checkout at all. This repo already has a guard that refuses
     non-ledger writes in the primary checkout for exactly this reason; check
     whether this script bypasses it, and if so, why.
  3. Audit the other scripts under the same directory for the same shape: a
     module-scope side effect with no argument handling. This one was found by
     accident; the pattern is easy to repeat and easy to miss in review because
     the file is short and reads as obviously correct.

MUST-FIRE FIXTURE:   invoking the script with a help flag prints usage and
                     changes nothing.
MUST-STAY-QUIET:     invoking it with no arguments still bumps the patch version
                     exactly as today.
THIRD FIXTURE:       invoking it with an unrecognised argument refuses and
                     changes nothing.

ACCEPTANCE
- A help flag and unrecognised arguments both leave the tree untouched.
- The no-argument bump behaviour is unchanged.
- Sibling scripts audited for module-scope side effects with no argument
  handling, with the findings reported either way.
- All three fixtures committed.
