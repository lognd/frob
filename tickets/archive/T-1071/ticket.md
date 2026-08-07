---
id: T-1071
title: 'ESTATE migration: sibling repos adopt net.connect/net.listen precise capability
  spelling (T-0573 fleet routing)'
state: done
kind: docs
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/**
- docs/guides/**
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/guides/**
  reason: 'Declared scope (docs/design/registry/**) does not cover the ticket''s own

    described deliverable: filing per-repo migration tickets via T-0573 fleet

    routing and documenting the per-repo recipe. docs/design/registry holds

    the unrelated design-knowledge corpus registry (arch checks, patterns,

    CWEs, ...), nothing about capability vocabulary or fleet migration.

    Adding docs/guides/** for a new estate-migration recipe guide, matching

    where every other agent-facing process doc in this repo already lives

    (agent-playbook.md, worktree-pool.md, ...). No sibling-repo or vet-code

    edit is being made from this repo; routing itself uses the existing

    frob.fleet CLI (T-0573), which writes into each sibling''s own ledger, not

    this repo''s tree.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/index.md
  reason: 'gate:DOC (DOC001) requires the new docs/guides/estate-capability-migration.md

    be linked from somewhere, matching every other docs/guides/*.md entry --

    they are all listed in docs/index.md''s "Getting started" section. Adding

    one line there is the minimal, idiomatic fix, not a new content addition.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- cmd:uv run frob check --ticket T-1071 --only gates-fast exit=0 sha256=9ab894d95b1e
designated_repro_test: null
threat: null
component: null
---
T-0771 wired net (WIRED_MODE_FAMILIES + _KIND_MAP net-connect/net-listen -> net.connect/net.listen) ahead of the T-0717 fs-write/fs-read alias sunset (2026-10-20). Per T-0717's mandate point 3 (ESTATE migration), file per-repo tickets (route via T-0573 fleet routing) for the 8 sibling repos' own capability declarations to adopt net.connect/net.listen precise spellings where they currently use bare net or (post-sunset) the legacy fs-write/fs-read hyphenated forms. Coordinate with the fs-write/fs-read sunset date so both migrations land in the same sweep per repo rather than two separate touches.