---
id: T-1767
title: 'Repo cleanup: retire the v1 monofiles, cull .claude skills and agents, land
  the verb refactors, fix worktree hygiene'
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
- docs/modules/tickets.md
- agents/**
- skills/**
- docs/guides/agentic-workflow.md
- Makefile
- docs/rework.md
- docs/index.md
- docs/modules/testing.md
- src/frob/_cli_parsers/_ticket/_query.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: agents/**
  reason: the ROOT agents/ and skills/ dirs are the ones CLAUDE.md names for removal-or-rework,
    not .claude/'s -- 13 tracked SKILL.md files, referenced by docs/guides/agentic-workflow.md,
    docs/rework.md, docs/index.md, docs/modules/testing.md and a doc anchor in _cli_parsers/_ticket/_query.py,
    so removal requires updating those rather than a bare delete. Makefile added because
    the cross-platform directive says workflows belong in frob subcommands, not GNU-make
    recipes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: skills/**
  reason: the ROOT agents/ and skills/ dirs are the ones CLAUDE.md names for removal-or-rework,
    not .claude/'s -- 13 tracked SKILL.md files, referenced by docs/guides/agentic-workflow.md,
    docs/rework.md, docs/index.md, docs/modules/testing.md and a doc anchor in _cli_parsers/_ticket/_query.py,
    so removal requires updating those rather than a bare delete. Makefile added because
    the cross-platform directive says workflows belong in frob subcommands, not GNU-make
    recipes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/guides/agentic-workflow.md
  reason: the ROOT agents/ and skills/ dirs are the ones CLAUDE.md names for removal-or-rework,
    not .claude/'s -- 13 tracked SKILL.md files, referenced by docs/guides/agentic-workflow.md,
    docs/rework.md, docs/index.md, docs/modules/testing.md and a doc anchor in _cli_parsers/_ticket/_query.py,
    so removal requires updating those rather than a bare delete. Makefile added because
    the cross-platform directive says workflows belong in frob subcommands, not GNU-make
    recipes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: Makefile
  reason: the ROOT agents/ and skills/ dirs are the ones CLAUDE.md names for removal-or-rework,
    not .claude/'s -- 13 tracked SKILL.md files, referenced by docs/guides/agentic-workflow.md,
    docs/rework.md, docs/index.md, docs/modules/testing.md and a doc anchor in _cli_parsers/_ticket/_query.py,
    so removal requires updating those rather than a bare delete. Makefile added because
    the cross-platform directive says workflows belong in frob subcommands, not GNU-make
    recipes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/rework.md
  reason: 'Deleting agents/** and skills/** requires updating every doc that

    references them, not just docs/guides/agentic-workflow.md (already in

    scope): docs/rework.md, docs/index.md, and docs/modules/testing.md each

    name agents/*/SKILL.md or skills/*/SKILL.md paths directly, and

    src/frob/_cli_parsers/_ticket/_query.py carries a code comment citing

    agentic-workflow.md''s #skills/next and #skills/plan anchors. Leaving any

    of these pointing at deleted files is exactly the stale-reader-of-a-

    deleted-path failure the ticket''s own item 1 section warns against.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/index.md
  reason: 'Deleting agents/** and skills/** requires updating every doc that

    references them, not just docs/guides/agentic-workflow.md (already in

    scope): docs/rework.md, docs/index.md, and docs/modules/testing.md each

    name agents/*/SKILL.md or skills/*/SKILL.md paths directly, and

    src/frob/_cli_parsers/_ticket/_query.py carries a code comment citing

    agentic-workflow.md''s #skills/next and #skills/plan anchors. Leaving any

    of these pointing at deleted files is exactly the stale-reader-of-a-

    deleted-path failure the ticket''s own item 1 section warns against.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/testing.md
  reason: 'Deleting agents/** and skills/** requires updating every doc that

    references them, not just docs/guides/agentic-workflow.md (already in

    scope): docs/rework.md, docs/index.md, and docs/modules/testing.md each

    name agents/*/SKILL.md or skills/*/SKILL.md paths directly, and

    src/frob/_cli_parsers/_ticket/_query.py carries a code comment citing

    agentic-workflow.md''s #skills/next and #skills/plan anchors. Leaving any

    of these pointing at deleted files is exactly the stale-reader-of-a-

    deleted-path failure the ticket''s own item 1 section warns against.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_query.py
  reason: 'Deleting agents/** and skills/** requires updating every doc that

    references them, not just docs/guides/agentic-workflow.md (already in

    scope): docs/rework.md, docs/index.md, and docs/modules/testing.md each

    name agents/*/SKILL.md or skills/*/SKILL.md paths directly, and

    src/frob/_cli_parsers/_ticket/_query.py carries a code comment citing

    agentic-workflow.md''s #skills/next and #skills/plan anchors. Leaving any

    of these pointing at deleted files is exactly the stale-reader-of-a-

    deleted-path failure the ticket''s own item 1 section warns against.

    '
  actor: logan
  at: '2026-08-07'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Owner directive: clean up the repo. Four distinct pieces, sequenced.

**1. RETIRE THE v1 MONOFILES.** T-1631 migrated 1748 tickets into
per-ticket `tickets/T-####/` directories and deliberately left
`tickets.md` and `tickets-archive.md` in place as rollback insurance --
the migrator never deletes them. They are now dead weight: ~3MB of
duplicate records that no code reads as authoritative, that every
worktree still copies, and that git still merges line-wise. Retiring them
is most of the point of migrating.

DO NOT delete them until the v2 store has been exercised through real
land and archive cycles on main. Then delete both, and audit for anything
still reading them: `ledger_path`/`archive_path` callers, the merge
driver's ledger paths, `.gitattributes`, the T-0731 land-owned-file hook,
and any doc that names them. A stale reader of a deleted file fails
loudly, which is fine -- a stale reader of a stale file does not, which
is the state to avoid.

**2. `.claude/skills/` AND `.claude/agents/`.** The project's own
CLAUDE.md opens by saying these should be removed or seriously reworked.
Only two files are tracked (`agents/exhaustive-researcher.md`,
`skills/exhaustive-research/SKILL.md`); the rest of `.claude/` is either
ignored or now tracked config (hooks, settings.json). Decide per file:
does it describe a workflow frob actually enforces, or is it aspirational
prose nobody executes? Delete the aspirational ones. Anything kept must
be reachable -- an agent definition no dispatch path names is the same
"catalogued but not enforced" shape as a registry no code reads.

**3. THE VERB REFACTORS.** T-1766 delivers the classification table (38
top-level verbs, 39 ticket subverbs, KEEP/DEMOTE/REMOVE per verb);
T-1567..T-1571 then regroup what survives. They are already sequenced
behind it. This ticket does not duplicate them -- it exists to make sure
the executions actually happen rather than the table becoming another
catalogued-but-unenforced artifact. Track the follow-up drafts T-1766
filed (`explore` removal, `scope-ack` removal paired with a TICK009 fix,
the deploy/perf/docs/map-outline-xref owner decisions) through to landed.

**4. WORKTREE HYGIENE.** 13 live worktrees accumulated during one drive,
including four `t-####` checkouts created by `frob ticket work` that no
pinned subagent can operate from -- two agents hit that trap, and a third
had its checkout removed underneath it during cleanup (its branch
survived, so nothing was lost, but only because it had committed).
`frob worktree sweep` now has a liveness guard (T-1739), but that guard
protects the tool's own path and not a raw `git worktree remove`. Decide
whether `frob ticket work` should create worktrees at all given nothing
can use them; T-1766 already flagged its row.

SEQUENCING: item 2 and item 4 are independent and can go first. Item 1
waits on real v2 exercise. Item 3 waits on T-1766's table.

Nothing here should add a mechanism. Every item is a deletion or a
decision to delete.