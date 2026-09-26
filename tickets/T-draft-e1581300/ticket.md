---
id: T-draft-e1581300
title: 'frob scaffold: multi-project JS/TS + Kotlin repo type and root project-type
  detection for polyglot monorepos'
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.536.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/scaffold/
- src/frob/lang/_project_detect.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names external or future-facing paths (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-26'
  old_length: 993
  new_length: 1205
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26): `frob scaffold list` on dev
b41443f46d offers python-library, python-tool, cpp-library, cpp-tool,
pybind11-library, pyo3-library, web-app. A repo holding several JS/TS
packages plus a Kotlin app has no type; root project-type auto-detection
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->fails there, so frob.toml was hand-written and `frob check --type typescript
<subdir>` had to be run per subproject (crunk-testbed local T-0003).

Deliver: (1) `_project_detect` recognises a polyglot root (multiple
package.json / build.gradle.kts under subdirectories, no single root
manifest) and reports each subproject with its type; (2) a `monorepo`
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->scaffold type that writes a frob.toml with one `[[project]]` entry per
detected subproject; (3) `frob check` at the root walks every detected
subproject with its own type without per-subdir invocations. Positive
control: a fixture monorepo with one TS package and one Kotlin module;
detection lists both; a single root check produces findings from both.
