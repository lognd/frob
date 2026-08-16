---
id: T-2242
title: Add frob release publish subcommand; retire Makefile upload bash recipe
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: T-1382
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/release/**
- scripts/bump_version.py
- Makefile
- docs/modules/release.md
- docs/commands/release.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/release.md
  reason: release/** module already has extensive existing doc obligations to docs/modules/release.md
    and docs/commands/release.md; include them so this leaf's scope closes without
    narrowing release/** itself, since the new publish verb genuinely lives alongside
    stamp/check/sync in the same module
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/commands/release.md
  reason: release/** module already has extensive existing doc obligations to docs/modules/release.md
    and docs/commands/release.md; include them so this leaf's scope closes without
    narrowing release/** itself, since the new publish verb genuinely lives alongside
    stamp/check/sync in the same module
  actor: logan
  at: '2026-08-16'
designated_repro_test: null
acceptance:
- text: 'GIVEN a repo with no Makefile WHEN a maintainer wants to cut a release THEN
    ''uv run frob release publish'' bumps the version, stamps/syncs the release, commits
    pyproject.toml/uv.lock/CHANGELOG.md/.frob-release.json, pushes, builds, and publishes
    -- the same net effect as today''s upload: recipe'
  evidence: []
- text: GIVEN the workflow needs a real secret (PyPI token) THEN it is loaded via
    python-dotenv's load_dotenv(), never bash 'set -a && . ./.env && set +a' sourcing
  evidence: []
- text: GIVEN --dry-run THEN the subcommand reports the version it would bump to and
    the files it would touch/push/publish without mutating anything, so this workflow
    is provable in CI/tests without a real git push or PyPI publish
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Makefile's upload: target (lines ~623-631) is a 9-line bash recipe: bash-specific dotenv sourcing (set -a && . ./.env && set +a), a version bump via scripts/bump_version.py (run today with bare 'uv run python', not 'uv run python scripts/bump_version.py' -- consistent with the bare-python3 pitfall T-2236 already tracks, verify this script itself does not assume python3.10), frob release stamp/sync, a git add/commit/push, then uv build && uv publish. No frob subcommand exists for this today (uv run frob release --help lists only stamp/check/sync -- no publish verb). This is real, high-blast-radius orchestration logic (git push + PyPI publish), not a trivial alias, so build it as a first-class Python subcommand with a mandatory --dry-run acceptance path so the migration itself can be proven without ever actually publishing during development/testing. First test that must fail today: 'uv run frob release publish --help' (no such subcommand exists). MUST-STILL-PASS: frob release stamp/sync/check (already-landed verbs this leaf composes, not replaces) keep their existing standalone behavior; a --dry-run run must not create a git commit, must not push, must not run uv build/uv publish. SAFETY NOTE for whoever implements/tests this: never actually run the real publish path against the real PyPI index or push to the real remote during this ticket's own verification -- prove parity via --dry-run and, if needed, a fully mocked git/uv layer.