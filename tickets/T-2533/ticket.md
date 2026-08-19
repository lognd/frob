---
id: T-2533
title: DOC006 CLI-invocation walker misses several _dispatch_*-bypassed verbs' real
  subcommands
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_docblocks_refs.py
- tests/test_docptr_gate.py
- docs/modules/tickets-landing.md
- docs/modules/tickets-lifecycle.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: regression tests for the DOC006 CLI-invocation bypass-subtree fix
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: remove the T-2374 frob:waive DOC006 sites this fix makes dead weight, per
    this ticket's own body
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: remove the T-2374 frob:waive DOC006 sites this fix makes dead weight, per
    this ticket's own body
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_docptr_gate.py::TestDoc006Cli::test_dispatch_bypassed_worktree_remove_not_flagged
- tests/test_docptr_gate.py::TestDoc006Cli::test_dispatch_bypassed_worktree_release_lease_not_flagged
- tests/test_docptr_gate.py::TestDoc006Cli::test_dispatch_bypassed_release_publish_not_flagged
- tests/test_docptr_gate.py::TestDoc006Cli::test_worktree_subcommand_still_genuinely_nonexistent_flagged
- tests/test_docptr_gate.py::TestDoc006Cli::test_release_subcommand_still_genuinely_nonexistent_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2374 (DOC004/DOC006 burn-down to zero + promote to ERROR).

DOC006's CLI-invocation tier resolves a doc's frob <verb> <subcommand...> pointer against
_console_trees/_subparser_tree (src/frob/gates/_docblocks_refs.py), which walks
_build_parser()'s (src/frob/__main__.py) decorative add_subparsers registration.

Several verbs are dispatched directly via a _dispatch_* bypass (src/frob/__main__.py:
_dispatch_worktree -> frob.app.worktree_runner.run, _dispatch_release_publish -> its own
dedicated argparse.ArgumentParser) that NEVER goes through _build_parser()'s tree at
argv-parse time. _build_parser()'s own registration of these verbs (used only for the
grouped frob --help overview) is a separate, incomplete mirror -- confirmed via direct
Python inspection:

    from frob.__main__ import _build_parser
    p = _build_parser()
    # worktree choices: ['sweep']  -- real: sweep, remove, release-lease
    # release choices: ['stamp', 'check', 'sync']  -- real also has: publish

Confirmed the REAL commands work (frob worktree remove --help, frob worktree
release-lease --help, frob release publish --help, frob worktree sweep --force --help
all resolve cleanly), while DOC006 flags every doc pointer naming them as "does not resolve
to a known subcommand" -- a false positive, not stale documentation. T-2374 waived the 6
affected sites (docs/modules/tickets-landing.md, tickets-lifecycle.md) with a disclosed
frob:waive DOC006 reason rather than silently rewriting the docs.

FIX OPTIONS (pick one, not both):
(a) Make _dispatch_*-bypassed verbs register their REAL subparser tree into _build_parser()
    too (so frob --help's grouped overview and DOC006's walker both see reality), or
(b) Give DOC006's CLI walker an explicit per-verb override table pointing at each bypassed
    verb's own dedicated parser-factory (worktree_runner's own argparse builder, release._cli's
    add_release_publish_parser), the same way [[docblocks.commands]] already lets a doc
    project declare an alternate parser factory per prog.

Either way: after the fix, the 6 frob:waive DOC006 sites T-2374 added (grep
"gate walker gap, not stale doc, tracked separately") should be revisited -- if the underlying
resolution now succeeds, the waivers are dead weight and should be removed.
