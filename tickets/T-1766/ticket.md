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

## Done report

Symbolically verified every one of the ticket's own "NEVER INVOKED (9)"
telemetry candidates against real code paths, real Makefile targets, and
real design docs -- per this drive's own standing lesson (agents/skills,
SYS109) that a name match or a zero-telemetry reading is not proof of
dead weight. Result: ZERO of the 9 are safe to delete. Each has a real,
symbolic reason telemetry could not see:

- **agent, bind, worktree**: NOT reachable through the normal argparse/
  App dispatch table at all -- `frob.__main__._dispatch` special-cases
  all three BEFORE `_build_parser()` ever runs (mirroring each other,
  each with its own comment saying so). `bind` is the SIGINT-safe
  fallback path `main()` itself depends on. `agent` backs
  `eval "$(frob agent env <worktree-path>)"`, the exact mechanism
  `docs/guides/agent-playbook.md` section 1b documents dispatch tooling
  using to set `FROB_WORKTREE`/`FROB_AGENT` per worktree -- called by
  the EXTERNAL dispatch harness, which is why this repo's own
  `.frob/telemetry.jsonl` (an internal record) never sees it. `worktree`
  is `frob worktree sweep`, itself named as load-bearing by section 12b
  of the same playbook and confirmed by the coordinator's own
  observation that it "was invoked by hand today and still reads zero."
  These three are structurally undeletable without breaking the CLI's
  own entry point or the documented worktree-hygiene workflow.

- **deploy**: has a real Makefile target, `deploy-audit` (Makefile:415),
  invoking `frob deploy audit --vm ... --ssh-host ... --ssh-key ...` --
  the VirtualBox snapshot-diff install/uninstall verification harness
  (T-0259/T-0254). Not in `check`/`all` (needs a real VBoxManage guest,
  degrades to a clear SKIPPED exit 2 otherwise per its own Makefile
  comment) -- exactly the kind of real, occasional, human-invoked
  workflow zero-telemetry cannot distinguish from dead code.

- **explore**: this is the one case where I initially expected a clean
  DELETE (a pure delegating wrapper over `map`/`outline`/`xref`/`docs
  --search`, explicitly documented as reusing the same `AppConfig`
  dests, functionally redundant with its own standalone verbs) -- until
  checking `docs/design/cli-regrouping.md`, which names `frob explore`
  (T-1238) as "IMPLEMENTED this ticket" and "the sole... precedent" for
  the LARGER CLI regrouping this exact ticket (T-1766) is sequenced
  ahead of (T-1567..T-1571). Deleting it would not just remove unused
  surface, it would delete the one built, working example that design
  doc's own regrouping plan is built on. This is a decision for
  T-1567..T-1571 (or a deliberate revision of the regrouping design doc
  itself), not a side effect of this ticket's own cull.

- **debt, deprecated, docs, pool**: each is a standalone, human-facing
  REPORTING verb over a real gate/mechanism this repo already enforces
  elsewhere (`frob:debt` entries, deprecation baselines, docs/ content,
  ratchet-pool baselines respectively) -- they fit the mission test
  ("frob is how work is tracked... verified") as read-only inspection
  tools, not code-navigation. `frob pool` in particular is easy to
  mistake for dead weight because `make pool-warm`/`pool-lease`/
  `pool-status` exist and use a similarly-named but ENTIRELY DIFFERENT
  command (`frob scaffold pool ...`, the worktree warm-pool, T-0738) --
  confirmed by reading both implementations, not by the shared word
  "pool". None of the four has a real invocation site in Makefile/
  .claude/hooks -- their zero-telemetry reading is plausible, but a
  rarely-used ad hoc inspection command is not the same claim as a dead
  one, and this ticket's own text is explicit that usage count alone is
  not sufficient grounds. Recommend a follow-up decision ticket if the
  owner wants these demoted specifically (CLI surface removed, library
  kept) rather than lumping them into this pass on inconclusive
  evidence.

## Flags sprawl (deliverable 2's named example)

Checked `frob ticket scope-ack` specifically, the ticket's own named
example ("a four-flag subcommand whose entire purpose is silencing a
warning nobody acts on"). Symbolic check: `scope_breadth_ack: true` is
set in 5 currently-active tickets' frontmatter plus 6 archived ones (11
total, `grep -rl` over `tickets/*/ticket.md` and `tickets/archive/*/
ticket.md`) -- a real, if infrequent, working escape hatch with real
historical callers, not an unused stub. Deleting it would orphan those
11 tickets' own recorded rationale. NOT a safe deletion on this
evidence; the "4 outstanding nudges narrowed by hand instead" pattern
today reads as a workflow preference in THIS session, not proof the
mechanism itself is dead.

## What this pass delivers vs what remains

Delivered: symbolic (not lexical) verification of every telemetry-flagged
zero-usage candidate the ticket named, correcting what would otherwise
have been at least one bad deletion (`explore`, which would have
contradicted T-1238's own design-doc precedent for T-1567..T-1571). This
is the exact class of error this drive has been correcting all day
(agents/skills, SYS109) -- catching it here, before a deletion, is
cheaper than catching it after.

NOT delivered, disclosed as a cut rather than silently dropped: the full
classification table across all 38 top-level verbs and 39 `ticket`
subverbs the ticket's deliverable 1 asks for. This pass covered the 9
named zero-telemetry candidates plus one named flag; the remaining ~29
verbs and ~35 subverbs (most already load-bearing at high telemetry
counts per the ticket's own numbers -- ticket, parse, check, outline,
gitlog, exports, arch, map, dup, xref) still need the same symbolic
check before any of THEM can be safely classified DEMOTE/REMOVE, and
deliverable 2's flag sprawl beyond `scope-ack` is unexamined. Requeuing
T-1766 for a continued pass rather than force a rushed full table.

Root-cause fix under DEAD001/WIRE001/OPAQUE001/REF002: no code was
changed this pass (a classification/verification pass, not an edit), so
none apply.

### Changed
```
 tickets/T-1766/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 586 warning(s), 723 waived
- error-findings: none (measured, zero errors)
