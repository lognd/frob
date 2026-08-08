---
id: T-1766
title: 'Cull the CLI surface against the mission test: 38 verbs, 9 never invoked,
  39 ticket subverbs'
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/**
- src/frob/app/__init__.py
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
frob exposes 38 top-level verbs and 39 `ticket` subverbs. The owner's
directive: remove everything that is not load-bearing to frob's mission.

THE MISSION TEST comes from this repo's own CLAUDE.md and is the whole
basis for this ticket:

  "frob is the enforcement layer for agentic development: an obligation
   graph over the code, a git-tracked ticket queue, and gates that make
   unaccounted-for work a build failure. Reading/navigating code is
   Serena's and native tools' job; frob is how work is tracked, gated,
   and verified."

So the test for every verb is: **does it track, gate, or verify work?**
If it reads or navigates code, that is explicitly someone else's job and
the CLI surface is not earning its keep.

MEASURED USAGE, from `.frob/telemetry.jsonl` (8.3MB of recorded CLI
invocations):

  NEVER INVOKED (9): agent, bind, debt, deploy, deprecated, docs,
                     explore, pool, worktree
  <=20 INVOCATIONS (6): coverage(3), scaffold(3), stats(3),
                        registry(4), serve(7), fmt(13)
  HIGHEST: ticket(8768), parse(5187), check(3187), outline(2424),
           gitlog(2301), exports(2228), arch(1886), map(1614),
           dup(1429), xref(1402)

TREAT THE TELEMETRY AS A SIGNAL, NOT PROOF. It is incomplete: `frob
worktree sweep` was invoked by hand today and still reads zero, so the
stream does not capture every path. Use it to RANK candidates, never as
sole grounds for deletion. Confirm each removal against real call sites.

Also note the high counts are misleading in the other direction: `parse`
at 5187 is largely frob's own graph builder invoking itself, not a person
choosing to run it. **A verb's usage count is not its user-facing value**
-- separate internal substrate from CLI surface before concluding
anything.

THE CENTRAL DISTINCTION, and the reason this is safe: REMOVING A VERB IS
NOT REMOVING CODE. Most of these are thin CLI wrappers over library
capability that frob's own gates depend on. `parse`, `graph`, `dup`,
`arch`, `exports` are load-bearing SUBSTRATE with an incidental
command-line surface. Deleting the verb while keeping the module removes
maintenance burden (help text, argparse wiring, docs, tests of the CLI
path, T-1725's verb-reference coupling) at zero functional cost.

DELIVERABLE, in this order:

1. A CLASSIFICATION TABLE covering all 38 verbs and all 39 `ticket`
   subverbs. For each: mission verdict (tracks/gates/verifies vs
   code-navigation vs ops), recorded invocations, whether the underlying
   module is used internally, and a verdict of KEEP / DEMOTE (drop the
   CLI surface, keep the library) / REMOVE.
   Enumerate from the parser definitions, never a hand-written list -- a
   hand list is how the next verb gets missed.
2. The same for FLAGS, which is where the sprawl actually compounds:
   `frob ticket scope-ack` is a four-flag subcommand whose entire purpose
   is silencing a warning nobody acts on (TICK009 has reported the same
   4 outstanding nudges all day while scopes were narrowed BY HAND).
   Every flag that exists to suppress a finding is a candidate for
   deletion ALONGSIDE the finding it suppresses -- see T-1763, which
   removes three rules that produce 406 waivers and zero findings.
3. Execute the uncontroversial removals in the same pass: the 9
   never-invoked verbs, minus any proven load-bearing by real call sites.

WHAT THIS TICKET MUST NOT DO: propose a rewrite, add a compatibility
shim layer, or invent a plugin system. Delete, or demote to library.
Sprawl is not fixed by adding an abstraction for managing sprawl.

SEQUENCING: this lands BEFORE T-1567..T-1571 (the CLI regrouping), which
are already blocked on T-1764. Regrouping cruft yields organised cruft --
decide what survives before anyone rearranges the survivors. Note the
owner has ranked this second overall, behind the v2 ledger migration
(T-1583 -> T-1631).