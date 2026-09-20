---
id: T-4766
title: Decompose the python types into a python base plus app-cli, github-ci, release-ci
  and docs-site facets
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4765
- T-4764
parent: T-4757
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/bases/python/**
- src/frob/scaffold/data/facets/app-cli/**
- src/frob/scaffold/data/facets/github-ci/**
- src/frob/scaffold/data/facets/release-ci/**
- src/frob/scaffold/data/facets/docs-site/**
- src/frob/scaffold/data/shared/python/**
- src/frob/scaffold/data/types/python-library/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.537.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given the python-library preset, when it is rendered, then its file set equals
    the manifest's declared set exactly
  evidence: []
- text: Given the python-tool preset, when its rendered tree is compared against the
    pre-refactor tree, then they match except where this story deliberately changed
    them
  evidence: []
- text: Given both python presets, when frob check runs in the rendered trees, then
    it is clean
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Decompose the python types into the python BASE plus facets, per audit 6.3.

python-library becomes python plus github-ci plus docs-site.
python-tool becomes python plus app-cli (the App, AppConfig and entry point
trio) plus github-ci plus docs-site plus release-ci.

The base owns: src layout, pyproject, the logging module, the frob.toml,
the gitignore, tests/unit plus tests/integration, docs/index.md. Everything
optional moves into a facet with a manifest, including the CI workflows,
which today are copied per type.

docs-site is a FACET, never a type: every existing type already renders a
docs/index.md and only needs a site generator bolted on. A project that is
only docs is not a thing.

Both current type names keep working as presets -- this is a refactor of how
they are built, not a change to what a user types, and the rendered output
of both must be byte-identical to the post-green-day-one output except where
this story deliberately changed it.

Positive controls:
1. rendering python-library through the preset produces exactly the file set
   the manifest declares, asserted as a set;
2. a golden test compares the preset's rendered tree against the pre-refactor
   tree, so an accidental drop (the failure mode that lost the refs block
   four times) fails the build;
3. frob check is clean on both rendered presets (the green-day-one test
   already covers this and must keep passing).
