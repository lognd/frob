---
id: T-4114
title: 'H3-5: a config path field''s relative-path default should be flagged'
state: in-progress
kind: bug
origin: human
created: '2026-09-06'
priority: critical
parent: T-4109
tier: ticket
sprint: v0.538.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_config_path_defaults.py
- tests/gates_suite/test_config_path_defaults.py
- docs/modules/gate-config-path-defaults.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/gate-config-path-defaults.md
  reason: docs/modules/gates.md is leased by T-4111; CONFIGPATH001's frob:doc anchor
    and docs row go in a new standalone doc file instead
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.541.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-13'
- field: sprint
  old_value: v0.541.0
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-307 H3-5 (verbatim, quoted at the bottom of T-4109's body). No gate today
compares an AppConfig default filesystem path against the deployment's
filesystem, because there is no deployment manifest on main to compare
against. Proposed rule, deliberately cheaper than a real deployment-manifest
comparison: flag a pydantic Field(default=...) on a field whose name matches
a *_path convention whose default VALUE is a relative path -- config paths
should be absolute or None, since a relative default silently resolves
against whatever the process's cwd happens to be at start time, which is a
real deployment footgun independent of any manifest.

Work:
- an AST/pydantic-model lint over every Field(...) call (or python-typani/
  pydantic Field-shaped default, per this repo's own conventions -- confirm
  the exact model shape used in the consumer's report is representative of
  a general pydantic pattern before hardcoding to one library's exact
  call shape) whose target field name ends in _path (or is annotated Path/
  PathLike -- check code for the more reliable of the two signals) and whose
  default is a string/Path literal that is not absolute and is not None
- WARN-tier finding (advisory, matching this repo's own posture for a
  lint that cannot always be certain a relative default is wrong -- some
  are deliberately relative-to-package-root)
- waivable with the standard frob:waive mechanism for a legitimate
  relative-to-package default

Fixture note: this one DOES fire cleanly in frob's own tree -- frob has its
own AppConfig-pattern pydantic models with path fields
(~/.claude/refs/python-app.md's App/AppConfig pattern is exactly this
shape, and frob's own config models are real pydantic BaseModel subclasses
under src/frob/app/). Prefer a fixture built from a small synthetic pydantic
model in the test file over grepping frob's real config classes for a
naturally-occurring instance (a real instance may not exist, or may change
out from under this test) -- a synthetic model class in the test module
itself, with:
- must-fire: Field(default="relative/dir/state.json") on a *_path field
- must-stay-quiet: Field(default="/abs/dir/state.json") on a *_path field,
  and Field(default=None) on a *_path field
- third: a *_path field with no default at all (required field) -- must
  stay quiet, nothing to evaluate

frob:ticket T-4109