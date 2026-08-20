---
id: T-2705
title: DOC010 only resolves make targets against the root Makefile, missing nested
  project Makefiles
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by a downstream consumer repo (aprog-public) on frob 0.530.0,
2026-08-20.

## Symptom

    slidegen/docs/scripts.md:231  DOC010: `make preview` is not a real
    Makefile target (no `preview:` recipe)

`preview:` IS a real target -- at `slidegen/Makefile:38`. `slidegen` is a
nested uv project with its own Makefile, and `slidegen/docs/scripts.md`
documents that nested project, so a bare `make preview` in that file
correctly resolves against `slidegen/Makefile`, not the repo root.

DOC010 only consults the ROOT Makefile.

## Fix direction

Resolve a `make <target>` claim against the NEAREST Makefile, walking up
from the documenting file, then fall back to the repo-root Makefile.

## Note on the standing cross-platform direction

This repo is deliberately moving workflows OUT of GNU-make recipes and
into frob subcommands, because make is not available everywhere frob has
to run. That direction does NOT make this bug moot: DOC010 exists to
validate CONSUMER repos' docs, and consumers legitimately use nested
Makefiles. Fix the resolution; do not resolve this by deprecating DOC010.

## Positive controls, both directions

- `make preview` in `slidegen/docs/scripts.md` resolves against
  `slidegen/Makefile` and does NOT fire
- a `make <target>` naming a target that exists in NEITHER the nearest nor
  the root Makefile STILL fires
- a doc at repo root continues to resolve against the root Makefile
  (no regression for the single-Makefile case)
- a nested Makefile that does NOT contain the target, where the root one
  does, must resolve via the root fallback rather than firing
