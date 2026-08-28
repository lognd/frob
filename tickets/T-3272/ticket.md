---
id: T-3272
title: 'Ledger v2 must be the default for new repos: all six scaffold manifests still
  emit the v1 single-file tickets.md'
state: in-progress
kind: feature
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/project.py
- src/frob/scaffold/data/shared/python/tickets.md.j2
- tests/unit/test_scaffold_project.py
- docs/commands/scaffold.md
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/data/shared/python/tickets.md.j2
  reason: removing the dead tickets.md.j2 seed template and its manifest entries,
    plus unit fixtures and docs for the v2-default flip
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_scaffold_project.py
  reason: removing the dead tickets.md.j2 seed template and its manifest entries,
    plus unit fixtures and docs for the v2-default flip
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/commands/scaffold.md
  reason: removing the dead tickets.md.j2 seed template and its manifest entries,
    plus unit fixtures and docs for the v2-default flip
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/design/ledger-v2.md
  reason: removing the dead tickets.md.j2 seed template and its manifest entries,
    plus unit fixtures and docs for the v2-default flip
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/scaffold/data/shared/python/tickets.md.j2
  reason: removing the dead tickets.md.j2 seed template and its manifest entries,
    plus unit fixtures and docs for the v2-default flip
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_scaffold_project.py
  reason: removing the dead tickets.md.j2 seed template and its manifest entries,
    plus unit fixtures and docs for the v2-default flip
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/commands/scaffold.md
  reason: removing the dead tickets.md.j2 seed template and its manifest entries,
    plus unit fixtures and docs for the v2-default flip
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/design/ledger-v2.md
  reason: removing the dead tickets.md.j2 seed template and its manifest entries,
    plus unit fixtures and docs for the v2-default flip
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-08-28: ledger v2 must be the DEFAULT for new repos.

MEASURED: every scaffold type ships the v1 single-file ledger. All six
manifests in `src/frob/scaffold/project.py` (lines 45, 95, 169, 203, 232, 265)
carry the same entry:

    _ManifestEntry("shared/python/tickets.md.j2", "tickets.md")

So every project scaffolded by frob starts on the LEGACY ledger and can only
reach v2 by running the one-shot migrator in
`src/frob/tickets/_store_migrate.py`. v2 is detected structurally --
`_v2_glob` looks for `tickets/T-*/ticket.md` (`_store.py:573`) -- so a repo is
v1 purely because that tree does not exist.

WHY THIS IS WORTH FIXING RATHER THAN DOCUMENTING. v2 is not a preference, it
is the design this project actually runs on: per-ticket files, per-ticket
locks, a separate next-id lock, and `git mv` archival instead of whole-file
rewrites (docs/design/ledger-v2.md). The single-file ledger is the reason this
repo has a standing rule never to hand-edit it -- one bad character in
tickets.md has taken every gate down here before. Shipping new users onto the
format we ourselves migrated away from, at the moment they are most likely to
edit it by hand, is backwards. The owner is preparing a PyPI release, so this
is the format every new frob user will meet first.

WHAT TO BUILD:
  1. New repos start in v2. Decide and STATE whether that means the scaffold
     emits a `tickets/` tree (with what seed content -- an empty directory is
     not tracked by git, so something must exist), or whether v2 becomes the
     mode a repo with NO ledger at all initialises into on first
     `frob ticket new`. The second may be cleaner; argue it either way.
  2. v1 repos keep working, unchanged. This is a default change, not a
     removal. The migrator stays; existing consumers must not be forced.
  3. Whatever detection change you make, `_v2_glob`'s structural test must
     still be the source of truth -- do not add a second, config-declared way
     to be "in v2 mode" that can disagree with the tree. Two sources of truth
     for the same fact is the desync bug this repo already knows well.

CHECK FIRST, DO NOT ASSUME: verify whether anything else in the scaffold
depends on `tickets.md` existing (the frob.toml template, the Makefile
targets, the CI workflow's `frob check` step, docs). A scaffold that starts in
v2 but whose CI or Makefile still references tickets.md is worse than either
consistent choice.

MUST-FIRE FIXTURE: a freshly scaffolded project is detected as v2 and
`frob ticket new` in it writes `tickets/T-0001/ticket.md`.
MUST-STAY-QUIET FIXTURE: an existing v1 repo (tickets.md present, no
tickets/T-*/ tree) is still detected as v1 and behaves exactly as today.
THIRD FIXTURE: the migrator still works on a v1 repo after this change.

ACCEPTANCE
- Every scaffold type covered, not just python-tool -- there are six manifests
  and they each carry the entry independently.
- Docs updated in the same change (docs/design/ledger-v2.md and any scaffold
  or tickets doc that describes what a new repo gets).
- A stated answer on the seed-content question, since an empty directory
  cannot be committed.
