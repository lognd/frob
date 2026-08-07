---
id: T-0555
title: 'lang: usable-tree parse threshold lets partially-broken files drop symbols
  silently (T-0404 finding 9)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0404
tier: ticket
sprint: null
scope:
- src/frob/lang/
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: REL001 version bump + changelog + release stamp required for T-0555's new
    public frob.lang API
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version bump + changelog + release stamp required for T-0555's new
    public frob.lang API
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version bump + changelog + release stamp required for T-0555's new
    public frob.lang API
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: uv.lock's frob version entry auto-updates to 0.60.0 alongside the pyproject.toml
    bump
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_lang.py::TestParseCache::test_reset_clears_counters
designated_repro_test: null
threat: null
component: null
---
docs/audits/lang-check-docs.md finding 9. _parse (lang/__init__.py) treats a tree as usable whenever root_node.child_count >= 1, even with has_error=True. A file with a broken region parses into a partial tree; symbols inside the error region silently don't extract, with no COV001/exports/drift signal for them. Ruff/ty catch this for Python via syntax errors, but Rust/C++/TS have no gates stage at all (finding 1) so nothing catches it there. Fix direction: when root_node.has_error, emit a warning-or-error gate signal naming the file so silent symbol loss is visible.