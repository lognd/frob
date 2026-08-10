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
