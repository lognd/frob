---
id: T-2761
title: Wire frob fmt callers to per-language resolve_line_length (T-1606 follow-up)
state: queued
kind: feature
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/fmt_runner.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_todo_fmt.py
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
T-1606 built `resolve_line_length(path, root) -> int | None` (per-language
width resolution: rustfmt.toml/max_width, prettier config/printWidth,
.clang-format/ColumnLimit, Python unchanged via ruff) and wired it into
`format_paths`/`_format_one_path` as the DEFAULT when no explicit `limit`
override is passed -- but four callers, all outside T-1606's declared
scope, currently pre-resolve a single project-wide limit via
`read_line_length(root)` ONCE and pass that fixed int to `format_paths`
as an explicit override, which defeats the new per-file resolution
entirely (an explicit `limit` short-circuits per-file resolution by
design, so these callers still wrap every language against ruff's number
exactly as before T-1606):

- src/frob/app/fmt_runner.py:52-53 (`frob fmt` CLI entrypoint)
- src/frob/app/ticket_runner/_land_cmd.py:243,245,253 (land's absorbed
  `frob fmt` step)
- src/frob/gates/_fix_engine_text.py:98,132,134,137 (the Tier-A auto-fix
  handler `frob check`/`frob ticket land` both run)
- src/frob/gates/_todo_fmt.py:426 (TODO-comment formatting)

Fix: each of these should stop calling `read_line_length(root)` and
passing its result as `format_paths(..., limit=<that value>)`; either
drop the `limit=` kwarg entirely (letting `format_paths`'s own default
resolve per file) or pass `limit=None` explicitly. Until this lands,
T-1606's capability exists and is tested but is not reachable through any
of frob's own real entrypoints -- every practical `frob fmt` run still
wraps Rust/TS/JS/C-family files against ruff's line-length.

Acceptance: `frob fmt` (and land's absorbed fmt step) run over a fixture
tree with a `rustfmt.toml`/`.prettierrc`/`.clang-format` each declaring a
width different from `pyproject.toml`'s ruff `line-length`, and the
resulting wrap width for each language's own files matches ITS config,
not ruff's.
