---
id: T-1031
title: 'frob natives build: estate rollout of the Makefile core one-line shim across
  sibling repos'
state: done
kind: docs
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/estate-natives-build-rollout.md
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: T-1031's bare docs/** glob collides with every docs-touching agent this
    wave; narrow to the single new precedent-recipe guide this ticket actually writes,
    mirroring docs/guides/estate-capability-migration.md's T-1071 shape
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/guides/estate-natives-build-rollout.md
  reason: T-1031's bare docs/** glob collides with every docs-touching agent this
    wave; narrow to the single new precedent-recipe guide this ticket actually writes,
    mirroring docs/guides/estate-capability-migration.md's T-1071 shape
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/index.md
  reason: DOC001 requires the new guide be linked from docs/index.md (or carry a frob:describes/frob:doc
    anchor) -- mirroring how estate-capability-migration.md is already linked there
  actor: logan
  at: '2026-07-28'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob check --ticket T-1031 --only docblocks exit=0 sha256=382bff877fb0
designated_repro_test: null
threat: null
component: null
---
T-0735's user directive named "estate rollout via fleet at close" as part of
the natives-build epic: every sibling repo's Makefile core target should be
converted to the one-line `uv run frob natives build` shim (T-0864's landed
subcommand) via `frob scaffold apply` (T-0865's landed scaffold template +
drift check), removing any lingering per-repo CARGO_TARGET_DIR/maturin-develop
cache logic at the wrong layer (the exact T-0732 drift class this epic exists
to retire).

This repo itself is already compliant (Makefile `core:` is the one-line shim,
verified at T-0735's close: `uv run frob natives build` runs successfully
using the git-common-dir-keyed shared CARGO_TARGET_DIR).

Fleet-level rollout across the other frob-enabled repos is out of THIS repo's
own scope -- draft follow-up for whichever fleet-facing ticket/process
actually walks the sibling-repo list and runs `frob scaffold apply` +
`frob doctor` per repo, plus a short docs note pointing at T-0864/T-0865/
T-0735 as the design precedent for anyone doing that rollout by hand in the
meantime.