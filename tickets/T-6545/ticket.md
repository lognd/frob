---
id: T-6545
title: 'test runners: ''typescript'' and ''ts'' (and js/javascript) are not aliased,
  so vitest evidence never binds; one canonical language table + loader refusal'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: critical
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
worktree: /home/logan/projects/frob
branch: dev
scope:
- src/frob/testing/_collect.py
- tests/unit/test_runner_language_aliases.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/testing/_runners.py
  reason: T-5782 holds the lease on _runners.py; deferring the files/names vitest
    split (item 4) until it frees, per coordinator instruction
  actor: logan
  at: '2026-09-26'
- op: remove
  glob: src/frob/app/config.py
  reason: T-6590 has an in-progress claim on config.py (worktree=root, branch=dev);
    deferring the TESTRUNNERSCHEMA001 loader-refusal wiring until it clears
  actor: logan
  at: '2026-09-26'
triage_changes:
- field: priority
  old_value: high
  new_value: critical
  reason: a consumer repo has no path to vitest evidence until this lands (logand
    T-0443/T-0445 parked)
  actor: logan
  at: '2026-09-26'
body_changes:
- mode: append
  reason: 'peer follow-ons: vitest {files} renders the full id; select_tests hardcodes
    ''typescript'''
  actor: logan
  at: '2026-09-26'
  old_length: 956
  new_length: 2012
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Source: logand.app-v2 FROBLEMS.md F-410 (peer coordinator report, 2026-09-26, frob 0.531.1.dev332).

The vitest collector keys TypeScript as 'ts' in LANGUAGE_COLLECTORS, while frob.toml files (and the docs since 0.530) use `[[test.runner]] language = "typescript"`. Nothing aliases the two, so every vitest evidence bind fails with "language 'ts' has selected tests but no runner" followed by EvidenceNotPassing, even though the collector does find the ids (.frob/vitest-collect.json). Deliver: (1) one canonical language-name table shared by the collectors, the runner config and frob.lang (typescript/ts, javascript/js, python/py, csharp/cs, rust/rs) with aliases resolved at config load; (2) the frob.toml loader refuses an unknown `language` key with the canonical name and the accepted aliases in the message; (3) positive control: a frob.toml with language = "typescript" binds a vitest id, and one with language = "tsx" is refused with the pointer.


Follow-ons from the same report (logand F-410, after switching to language = "ts"):

4. Vitest verification always FAILS: `_expand_placeholder("{files}", ...)` in testing/_runners.py renders the full evidence id (`path::describe > name`) into the vitest argv; vitest treats it as a file filter, exits 1, and `_verify_one_bucket_passing` reports FAILED -- exactly the `{files}` shape docs/modules/testing.md documents for TS, so no granular vitest evidence can ever verify. Deliver: split a vitest/jest id into the file path plus `-t "<describe > name>"` (or add a `{names}` placeholder rendered per runner), with a positive control that a `path::describe > name` id passes verification against a fixture vitest project and a wrong name fails.

5. `select_tests`'s suite-wide fallback hardcodes "typescript" in its language list, so after the key change a frob.toml-only diff selects no TS runner: the canonical table from (1) must feed this list too; positive control: a frob.toml-only change in a fixture with language = "ts" selects the vitest runner.
