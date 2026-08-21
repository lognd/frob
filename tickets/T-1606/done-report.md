## Done report

Design decisions recorded (T-1606 was design-led, per dispatch brief):

- Before this ticket, `read_line_length(root)` was the ONE width source
  `format_paths` used for every language in a walk. `resolve_line_length
  (path, root)` (src/frob/gates/_fmt_directives.py) is the new per-file
  replacement: Rust (rustfmt.toml/.rustfmt.toml -> max_width, default
  100), TS/JS (.prettierrc* or package.json's `prettier` key ->
  printWidth, default 80), C-family (.clang-format -> ColumnLimit,
  default 80) each read from that tool's own config, nearest-ancestor-
  wins (`_find_nearest_config`, matching how the real tools resolve a
  monorepo). Python is UNCHANGED: `.py`/`.pyi` still resolve via
  `read_line_length` (ruff stays the sole owner).
- `None` is a first-class return value for "this formatter has no width
  concept at all" (Go/Zig/Bash -- none of which are registered `_MARKERS`
  languages yet, so this is proven at the `canonicalize_text`/
  `_canonical_lines` level via `TestResolveLineLength.test_no_limit_
  language_never_wraps`, not through `resolve_line_length` itself until
  such an adapter is added). `canonicalize_text`'s `limit` parameter is
  now `int | None`; `None` converts internally to `_EFFECTIVELY_UNLIMITED`
  (10**9) so the existing int-only wrap math needs no Optional handling.
- `.strata` (frob's own DSL, no external formatter) deliberately keeps
  falling back to the ruff-derived value -- a documented decision, not an
  oversight; it has no formatter of its own to defer to, unlike Go/Zig/
  Bash which have a real tool that just lacks a width knob.
- `format_paths(root, *, limit=None, ...)`: `limit=None` (the new
  default) now resolves EACH FILE's own width via `resolve_line_length`
  -- a single walk over a mixed-language tree wraps each file against its
  own tool's config. An explicit `limit=<int>` still overrides uniformly
  for the whole walk (unchanged, used by existing tests/callers).

SCOPE-FLAGGED gap, NOT fixed here (filed as a follow-up, see below): four
callers outside T-1606's declared scope (`src/frob/app/fmt_runner.py`,
`src/frob/app/ticket_runner/_land_cmd.py`,
`src/frob/gates/_fix_engine_text.py`, `src/frob/gates/_todo_fmt.py`) each
pre-resolve a single `read_line_length(root)` value and pass it to
`format_paths` as an explicit `limit=` override, which bypasses the new
per-file resolution entirely. Until that follow-up lands, every real
`frob fmt` invocation still wraps every language against ruff's number,
same as before T-1606 -- the new capability exists and is tested but is
not yet reachable end-to-end. This is a scope boundary, not an oversight:
none of those four files are in T-1606's declared scope, and widening
scope mid-ticket to also rewire four unrelated call sites was judged out
of proportion to this ticket's own deliverable.

Positive control checked: `TestResolveLineLength.test_rust_uses_rustfmt_
toml`/`test_prettier_uses_prettierrc`/`test_clang_format_uses_config` (a
declared config is honored, differing from the ruff default) and
`test_rust_falls_back_to_tool_default`/`test_prettier_falls_back_to_tool_
default`/`test_clang_format_falls_back_to_tool_default` (no config -> the
tool's OWN documented default, not ruff's) both pass; `test_no_limit_
language_never_wraps` proves `limit=None` never wraps regardless of text
length; `test_unregistered_suffix_falls_back_to_ruff_derived_default`
proves `.strata` keeps its pre-T-1606 behavior unchanged.

Changed:
- src/frob/gates/_fmt_directives.py::resolve_line_length (new)
- src/frob/gates/_fmt_directives.py::canonicalize_text (limit: int -> int | None)
- src/frob/gates/_fmt_directives.py::_format_one_path (limit: int -> int | None, per-file resolution)
- src/frob/gates/_fmt_directives.py::format_paths (docstring: limit=None default now per-file)
- src/frob/gates/_fmt_directives.py::_find_nearest_config (new)
- src/frob/gates/_fmt_directives.py::_resolve_rust_width (new)
- src/frob/gates/_fmt_directives.py::_resolve_prettier_width (new)
- src/frob/gates/_fmt_directives.py::_resolve_clang_format_width (new)
- docs/modules/gates.md (frob-fmt-directive-canonicalization-t-0441 section)

Evidence: 11 pytest node ids under
tests/test_gates_fmt_directives.py::TestResolveLineLength (bound via
`frob ticket evidence`).

Filed: T-2761 (renumbers at land) -- "Wire frob fmt callers to
per-language resolve_line_length (T-1606 follow-up)", scoped to the four
out-of-scope callers above.

Gates: `frob check --ticket T-1606 --no-cache` clean of every finding
this ticket's own diff introduced (verified via scripts/check_summary.py
across two iterations: fixed a ruff E501 and a PERF003 false-positive in
`_find_nearest_config`, extended scope to `docs/modules/gates.md` for
AFFECT001's doc-drift requirement and to `frob.lock` for the `frob ack`
digest writes on `canonicalize_text`/`_format_one_path`, re-ran `frob
ticket sweep T-1606` to clear PRE001). Remaining errors in the unscoped
run (CYCLE001, ARCH103 on _close_cmd.py, COV001/COV003/DOC011 on
unrelated files, DRIFT001/DRIFT002 on unrelated symbols, SEC110, TEST001,
TICK003/004, CLAUDE001) are pre-existing baseline findings on files this
ticket never touched.

### Changed
```
 tickets/T-1606/ticket.md           | 32 ++++++++++++++++++-
 tickets/T-2761/ticket.md | 63 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 94 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_python_uses_ruff_config` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_rust_uses_rustfmt_toml` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_rust_falls_back_to_tool_default` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_prettier_uses_prettierrc` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_prettier_uses_package_json_key` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_prettier_falls_back_to_tool_default` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_clang_format_uses_config` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_clang_format_falls_back_to_tool_default` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_nearest_config_wins_over_root_config` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_unregistered_suffix_falls_back_to_ruff_derived_default` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestResolveLineLength::test_no_limit_language_never_wraps` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 17 error(s), 1177 warning(s), 708 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
