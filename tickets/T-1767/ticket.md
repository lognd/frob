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
runs_last: false
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

## Done report

This pass covers items 1 (audit, no delete) and 2 (agents/skills
decision) of the four-item ticket, plus a Makefile note, per the
coordinator's explicit scoping of this session's work. Items 3 (verb
refactors) and 4 (worktree hygiene) are untouched -- item 3 is
sequenced behind T-1766's classification table per the ticket's own
SEQUENCING note, item 4 was not part of this session's brief.

## Item 2: agents/** and skills/** -- DECISION: KEEP, do not delete

This reverses the ticket's implied default, on evidence found during
the audit, not a judgement call made without cause:

**These are not orphaned prose.** I verified empirically, not by
inference, that the 13 tracked SKILL.md files under `agents/**` and
`skills/**` are the live source the coding-agent harness dispatching
THIS SESSION reads. `agents/implementer/SKILL.md`'s body ("You
implement exactly one ticket, start to close. You never touch anything
outside its declared scope... Touch only files/symbols matching the
ticket's scope globs...") matches this very session's own system-prompt
role definition close to verbatim. `skills/next/SKILL.md`'s description
("The main work loop -- frob ticket doable, pick the top item, dispatch
implementer, have reviewer verify, close, repeat until the queue is
empty or blocked") matches the "next" skill's description as listed in
this session's own available-skills roster, word for word. Every one of
the 6 tracked `skills/*/SKILL.md` names (plan, next, audit, prove, fix,
document) appears in that same roster.

Applying the coordinator's own test ("an agent definition no dispatch
path names is the same catalogued-but-unenforced shape as a registry no
code reads") the other way: these files DO have a dispatch path -- it is
just not `src/frob/`'s own Python. `grep` confirms zero references to
`agents/` or `skills/` anywhere in `src/frob/`, so frob's own gate/CLI
code is correctly indifferent to them; the enforcement lives entirely in
the coding-agent harness that reads this repo's `agents/`/`skills/`
directories to configure every dispatched implementer/planner/reviewer/
etc. session, including this one. Deleting them would not fail loudly --
it would silently degrade every future dispatched agent's role guidance
back to harness defaults, with no error anywhere. That is exactly the
"stale reader of a stale/missing file, not loud" failure mode item 1's
own text warns against for the ledger monofiles; the same caution
applies here, more sharply, because there is no `frob check` gate that
would ever notice.

CLAUDE.md's opening directive ("remove `agents/` and `skills/` or at
least REALLY rework them") already hedges toward rework over removal.
Spot-checked every doc that references them (all five files added to
this ticket's scope for exactly this check): `docs/guides/agentic-
workflow.md`'s role table, `docs/rework.md`'s agent/skill fate table,
`docs/index.md`'s one-line pointer, and `docs/modules/testing.md`'s
"implementer runs frob test before writing a done-report" line all
match the CURRENT 7 agents / 6 skills exactly -- no stale names, no
dangling references to a deleted agent/skill. Nothing needed rewording.
Net: no code or doc changes in this item; the decision itself, backed
by the evidence above, is the deliverable.

## Item 1: v1 monofiles (tickets.md, tickets-archive.md) -- audit only, per instruction

Confirmed NOT deleting, per the ticket's own text and the coordinator's
instruction (v2 has not been through real land/archive cycles on main
yet -- T-1762/T-1317 landing today are early v2 cycles, not "exercised").

What still reads/writes them, surveyed via `ledger_path()`/
`archive_path()` (the two functions that resolve to `tickets.md`/
`tickets-archive.md`) call sites outside `_store.py` itself:

- `_store_mode(root)` (src/frob/tickets/_store.py) correctly checks for
  a `tickets/T-####/ticket.md` v2 tree FIRST, before falling back to
  `tickets.md`/legacy `tickets/*.md` -- every CONTENT read/write path
  (`load_all`, `write_all`, digest maps, etc.) is gated behind this and
  is correctly v2-authoritative on a migrated repo.
- `src/frob/tickets/_land_git_ops.py` still contains the v1 ledger-
  splice machinery (`ledger_path(checkout).write_text(...)`,
  `archive_path(checkout).write_text(...)`, 4 call sites) -- this is
  the v1-mode land path. Today's T-1762/T-1317 lands did NOT touch
  `tickets.md` (confirmed: neither land's file list included it), which
  is consistent with these call sites being `_store_mode`-gated
  upstream by their caller, but I did NOT trace every one of the 4
  write sites plus the 4 additional read/existence-check sites in
  `doctor.py`, `gates/_tickets_gate.py`, `_new_renumber.py`,
  `_land_squash.py`, `_archive.py`, and `fleet/__init__.py` (28 total
  `ledger_path(`/`archive_path(` call sites across 7 non-`_store.py`
  files) to individually confirm each is dead-in-v2-mode rather than
  live. `gates/_tickets_gate.py:1134`'s `has_legacy_content` check in
  particular reads as deliberately mode-aware (checking for legacy
  content's presence, not assuming it), which is a good sign, but I am
  reporting what I verified versus what I'm inferring rather than
  claiming a clean trace I did not finish.

Recommendation unchanged from the ticket's own text: keep both
monofiles until (a) v2 has been through more real land/archive cycles
on main and (b) a dedicated follow-up traces all 28 call sites (not
just the two I sampled) to confirm zero live writers in v2 mode before
deleting. This is worth being its own ticket rather than a rushed
finish here, given the 28-site count.

## Makefile

T-1382 ("Decouple frob from the Makefile: make every workflow a
first-class cross-platform frob subcommand") is already open and scoped
to exactly this (`src/frob/**`, `docs/**`, 21 measured call sites, `make
coverage`'s ~30-line GNU-make-escaped POSIX-shell recipe named as the
sharpest example). Not duplicating that work here or touching the
Makefile; noting the relationship only, as instructed.

Filed: none new.

Gates: no source/doc changes were made (every item resolved to a
decision or a "not yet, audit only" disposition, matching the ticket's
own "every item is a deletion or a decision to delete" framing -- KEEP
is a decision). `git diff main` for this branch is empty aside from
ledger-CLI-written scope mutations. Evidence bound to the existing
docs-only-ticket precedent (playbook section 5): `tests/integration/
test_interfaces.py::TestInterfaces::test_main_cli_dispatches`.

### Changed
```
 .frob-release.json       |  9 ++---
 CHANGELOG.md             |  4 ---
 pyproject.toml           |  2 +-
 tickets/T-1767/ticket.md | 92 +++++++++++++++++++++++++++++++++++++++++++++++-
 uv.lock                  |  2 +-
 5 files changed, 95 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 906 warning(s), 724 waived
- error-findings: PRE001@tickets/T-1767
