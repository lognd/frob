---
id: T-4541
title: 'testing: LANGUAGE_COLLECTORS keys vitest as ''ts'' but [[test.runner]] language
  is ''typescript'', so vitest evidence is never verified'
state: queued
kind: bug
origin: human
created: '2026-09-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
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
`frob.testing.LANGUAGE_COLLECTORS` (frob.testing._collect) registers the
vitest collector under the key `"ts"`. `frob.lang.language_for_extension`
-- the canonical extension->language mapping `frob.testing._select`'s
`extension_language` uses for `frob test`'s own selection, and which a
project's `[[test.runner]] language = "..."` entry is documented to match
-- returns `"typescript"` for both `.ts` and `.tsx` (see
`frob/lang/__init__.py`'s `_EXTENSION_TABLE`, entries `.ts` and `.tsx`
both map to `"typescript"` as the second tuple element).

This means:
- `frob test` (via `frob.testing._select.select_tests` /
  `frob.testing._runners.run_selected`) buckets a touched `.ts`/`.tsx`
  file under language `"typescript"`, matches a `[[test.runner]]
  language = "typescript"]` entry, and runs it correctly.
- `frob ticket evidence` / `frob ticket close` (via
  `frob.app.ticket_runner._verify._verify_ids_passing`, which iterates
  `LANGUAGE_COLLECTORS` to bucket ids) buckets that SAME id under
  `"ts"`, finds no `[[test.runner]] language = "ts"]` entry (since the
  project correctly declared `"typescript"` to match `frob test`'s own
  convention), and fails every time with:

  `run_selected: language 'ts' has selected tests but no runner -- add a
  [[test.runner]] entry with language = 'ts' to frob.toml`

  even though the exact same node id passes under `frob test`/`npx
  vitest run`. This makes it impossible to record passing evidence for
  ANY vitest test, or close a ticket bound to one, without adding a
  second `[[test.runner]]` block whose only purpose is to duplicate the
  typescript entry under the key `"ts"`.

Repro (any repo with a `[[test.runner]] language = "typescript"` entry
and a passing vitest test):
```
frob ticket evidence T-XXXX "path/to/File.test.tsx::describe > test name" --accepts N
# WARNING: run_selected: language 'ts' has selected tests but no runner ...
# ERROR: ticket evidence failed: EvidenceNotPassing
```

Adding a second `[[test.runner]] language = "ts"` block (same command)
as a workaround surfaces a SECOND, distinct bug: the runner's `{ids}`
placeholder expands a selected item via `_to_node_id`, which for a
`path::name` item with a space-bearing vitest title (the documented
"quoted target" convention `frob.graph.dsl`'s
`_tests_quoted_title_error` itself recognizes, e.g. `"src/x.test.ts
describes a thing"`) just returns the item unchanged -- so the rendered
command is
`npx vitest run "path/to/File.test.tsx::describe > test name"`.
vitest's `run <pattern>` positional is a FILE filter, not a
`file::testname` node id (that syntax is pytest's, not vitest's); vitest
correctly reports:

```
No test files found, exiting with code 1
filter: path/to/File.test.tsx::describe > test name
```

So even with the language-key workaround in place, `frob ticket
evidence` still cannot verify a specific vitest test by node id -- only
a bare file path (no `::`) would render a valid `npx vitest run <file>`
invocation, but `frob ticket evidence`'s own id-resolution step refuses
a bare file path with `UnknownEvidence: Evidence id does not resolve to
a collected test` (it requires exact `tests.node_ids` membership, and
`collect_ts_tests` only ever collects fully-qualified `file::name`
ids, never the bare file). The `{filters}`/`{regex}` placeholders don't
help either: `{regex}` joins raw items (still including the
`file::` prefix) rather than stripping to just the test-name segment
vitest's `--testNamePattern`/`-t` expects.

Net effect: as of 0.531.0, there is no way to record `frob ticket
evidence` for a vitest test, or close a ticket whose acceptance
criterion is bound to one, without either a custom test-runner wrapper
script (not currently documented) or an upstream fix in frob itself.

Suggested fix direction: either (a) key `LANGUAGE_COLLECTORS` by
`"typescript"` to match `language_for_extension`'s canonical string (a
one-line rename, least invasive), and (b) add a placeholder (or make
`{ids}` render per-item as separate `-t <name>`/file argv pairs for
languages whose collector node ids are not natively single-token CLI
selectors, e.g. vitest's file+`-t` split) or a documented per-language
render hook, so `_render_command` can produce `["npx", "vitest", "run",
"<file>", "-t", "<name>"]` instead of a single positional carrying the
whole node id.

Discovered while implementing T-0044 in project-hullbreach-platform
(sibling repo); reported by the coordinating agent's request.
