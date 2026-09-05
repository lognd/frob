---
id: T-3916
title: bump_patch_version does not rewrite frob-core/strata-core pins, only [project].version
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/release/__init__.py
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
found while working T-3903 (VERSION001 pin-matching fix).

MEASURED 2026-09-05: bump_patch_version (src/frob/release/__init__.py:409) calls rewrite_pyproject_version, which only rewrites root pyproject.toml's 'version = "..."' line via _PYPROJECT_VERSION_RE. Nothing in the bump path touches the frob-core/strata-core pins now living in TWO sites ([project].dependencies and [project.optional-dependencies].native), nor bumps frob-core/pyproject.toml or strata-core/pyproject.toml's own version fields.

This is the deeper defect T-3903 was asked to surface: VERSION001 (after T-3903) will now correctly CATCH the resulting skew after a bump, but catching it after the fact is not sufficient. Every release's bump step will manually fail VERSION001 and require a hand edit to all four pin/version sites -- exactly the kind of chore that eventually gets skipped (this is the same failure shape as typani's T-026, and T-2884's git-SHA precedent for why version strings alone need mechanical enforcement, not just gating).

WHAT TO DO: extend the bump path (bump_patch_version / rewrite_pyproject_version, or a new helper alongside them) to also rewrite every frob-core/strata-core pin in root pyproject.toml to the new version, and to bump frob-core/pyproject.toml and strata-core/pyproject.toml's own version fields to match, so a bump produces a VERSION001-clean tree instead of a guaranteed-red one.

Cross-ref: T-3903 (VERSION001 pin-matching fix that surfaced this), typani T-026 (same defect class: a bump script that updates some but not all coupled version strings).