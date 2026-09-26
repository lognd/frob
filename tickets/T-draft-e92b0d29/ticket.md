---
id: T-draft-e92b0d29
title: 'test runners: ''typescript'' and ''ts'' (and js/javascript) are not aliased,
  so vitest evidence never binds; one canonical language table + loader refusal'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/testing/_collect.py
- src/frob/testing/_runners.py
- src/frob/app/config.py
- tests/unit/test_runner_language_aliases.py
- docs/modules/testing.md
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
Source: logand.app-v2 FROBLEMS.md F-410 (peer coordinator report, 2026-09-26, frob 0.531.1.dev332).

The vitest collector keys TypeScript as 'ts' in LANGUAGE_COLLECTORS, while frob.toml files (and the docs since 0.530) use `[[test.runner]] language = "typescript"`. Nothing aliases the two, so every vitest evidence bind fails with "language 'ts' has selected tests but no runner" followed by EvidenceNotPassing, even though the collector does find the ids (.frob/vitest-collect.json). Deliver: (1) one canonical language-name table shared by the collectors, the runner config and frob.lang (typescript/ts, javascript/js, python/py, csharp/cs, rust/rs) with aliases resolved at config load; (2) the frob.toml loader refuses an unknown `language` key with the canonical name and the accepted aliases in the message; (3) positive control: a frob.toml with language = "typescript" binds a vitest id, and one with language = "tsx" is refused with the pointer.
