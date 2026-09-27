---
id: T-draft-893f70cb
title: 'rust test runner: {ids} on a cargo runner splices one positional per test
  id, which cargo rejects; a rust-aware {filters} placeholder already exists but nothing
  steers or refuses the wrong one'
state: queued
kind: bug
origin: agent
created: '2026-09-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: 2
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
- src/frob/testing/_runners.py
- src/frob/app/config.py
- src/frob/scaffold/
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-27'
  old_length: 1472
  new_length: 1472
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the logand.app-v2 session (2026-09-27, frob 0.531.1.dev348-
351): `frob test --base sub-17-rust` built `cargo test <mod::tests::a>
<mod::tests::b>` from `command = ["cargo", "test", "{ids}"]` (cwd
wasm-engine); cargo accepts exactly ONE positional filter, so every
selection of two or more ids failed with "unexpected argument" and frob
tagged the ticket [REPEATED_FAILURE]. Verified on dev f0ff8dca20 in
`_runners.py::_expand_placeholder`: `{ids}` splices one argv element per
id, while `{filters}` is rust-aware (`_to_rust_filter`, joined into one
argument) and is what a cargo runner must use. Nothing steers a consumer
to it: the runner schema accepts `{ids}` for a rust runner, the docs do
not say which placeholder each language needs, and the scaffolded rust
runner template is not the source of this config.

Deliver (tiered safety): guaranteed-safe automatic: on a rust-language
runner (`language = "rust"` or argv[0] == cargo) `{ids}` is treated as
`{filters}` with one INFO line naming the substitution; explicit tier:
TESTRUNNERSCHEMA001 reports a placeholder/language mismatch at config
load with the exact replacement; docs/modules/testing.md gains a
per-language placeholder table; the scaffold's rust runner template
uses `{filters}`. Positive control: a fixture rust crate with two
selected tests and a `{ids}` runner runs both under one cargo
invocation and logs the substitution; a python runner with `{filters}`
still reports the mismatch.
