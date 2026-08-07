## Done report

Changed:
- src/frob/gates/_coverage.py::_resolve_class_root (new)
- src/frob/gates/_coverage.py::_build_class_maps (now resolves PER CLASS
  against `known_paths` instead of joining every class under one
  per-report "winning root")
- src/frob/gates/_coverage.py::_parse_classes (threads candidate_roots +
  known_paths through to _build_class_maps)

Root cause: `_select_join_root` computed a single aggregate-scored
"winning root" for the WHOLE coverage.xml report, then `_build_class_maps`
joined every `<class filename=...>` under that one root. With two declared
`<source>` roots (e.g. `scripts` and `tests`) whose subtrees each contain a
same-named package-relative path (`actgen/...`), a class that actually
lives under `scripts/` could still get labeled `tests/...` if `tests`
happened to win the aggregate per-report vote (more matching classes
elsewhere, or a tie broken by declaration order) -- the win was global,
not per-file. Fix: for each class, try each candidate root IN ORDER and
pick the first whose joined path is in `known_paths` (which only ever
contains paths to files that genuinely exist, per `_known_repo_paths`);
only fall back to the old aggregate `winning_root` when a class matches
none of the candidates (the existing TEST008 unjoined-root path, left
unchanged).

Evidence: `tests/test_gates.py::TestCoverageLoad::test_multi_root_resolves_each_class_to_its_real_root`
-- two declared `<source>` roots (`tests`, `scripts`, declared in THAT
order so the old code's tie-break would have picked `tests`), a 0%-covered
class `actgen/core.py` that exists only under `scripts/`, and a second
class `actgen/other.py` that exists only under `tests/`; asserts the first
resolves to `scripts/actgen/core.py` (not `tests/actgen/core.py`) and the
second to `tests/actgen/other.py`. Collected node id confirmed via
`uv run pytest tests/test_gates.py --collect-only -o addopts=""`.
Full existing `TestCoverageLoad` suite (30 tests, incl. the T-0148
single-root, repo-relative, multi-source-one-joins, and zero-join-is-loud
cases) still green: `uv run pytest tests/test_gates.py -k Coverage -q`.

Filed: none

Gates: `make coverage` + `uv run frob check` -> Tool summary `gates 0
errors, 0 warnings, 204 waived`; ruff-check/ruff-format/ty all pass (both
`uv run ruff`/`uv run ty` and bare `ruff`/`ty`); `git diff main
--diff-filter=D --stat` empty.
