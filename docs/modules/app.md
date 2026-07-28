# frob app

`frob.app` is the CLI wiring layer: `__main__.py` builds the argparse parser,
`AppConfig` (pydantic) merges CLI args with `pyproject.toml` `[tool.frob]`
settings into one typed config object, and `App.__call__` dispatches on
`AppConfig.subcommand` to the matching `*_runner.run(cfg)`. Every runner is a
thin adapter: parse `cfg`, call the real library function in the matching
`frob.<module>`, print/log the result, set the exit code. This page documents
the CLI-facing seams; the actual logic lives in each library's own docs page
(docs/commands/map.md, docs/commands/outline.md, docs/modules/perf.md, ...).

## Usage

```
frob <subcommand> [args...]
```

See `frob <subcommand> --help` (via `src/frob/__main__.py::_build_parser`)
for the full flag catalog per subcommand.

## Entry point

<!-- frob:describes src/frob/__main__.py::main -->
<!-- frob:describes src/frob/app/app.py::App -->

```python
# frob/__main__.py
def main() -> None
    # Builds AppConfig from argv + pyproject.toml and runs App(cfg)();
    # this is the `frob` console-script entry point. An unhandled exception
    # from dispatch (T-1022) is logged and printed as `frob: <exc>` with
    # exit 1, never a raw traceback crossing the CLI boundary.

# frob/app/app.py
class App
    # Callable dispatcher: __call__() matches cfg.subcommand and invokes
    # the corresponding *_runner.run(cfg); unknown/missing subcommand logs
    # usage and exits 1.
```

`App.__call__` carries a `frob:waive ARCH103` (T-0977, docs/audits/
gates-quality.md's T-0977 section): the resolve-dispatch-or-usage-error
shape IS the dispatcher's one documented job above, not a separable
concern.

## Config

<!-- frob:describes src/frob/app/config.py::Subcommand -->
<!-- frob:describes src/frob/app/config.py::AppConfig -->
<!-- frob:describes src/frob/app/config.py::AppConfig.from_external -->
<!-- frob:describes src/frob/app/config.py::AppConfig.from_args -->

```python
# frob/app/config.py
class Subcommand(str, enum.Enum)
    # One member per `frob <name>` subcommand; the single source of truth
    # for valid subcommand names used by both the parser and App dispatch.

class AppConfig(BaseModel)
    # Flat pydantic model holding every subcommand's flags; only the fields
    # for the active `subcommand` are meaningful on a given run.

AppConfig.from_external(args: argparse.Namespace, file: Path) -> AppConfig
    # Merges [tool.frob] settings from `file` with parsed argparse flags
    # (CLI flags win); the general-purpose constructor used by tests to
    # inject an arbitrary pyproject.toml path.

AppConfig.from_args(args: argparse.Namespace) -> AppConfig
    # from_external() against the real "pyproject.toml" in the cwd; what
    # `main()` actually calls.
```

T-0628: `graph_max_depth`/`graph_max_nodes` (both `int | None`, default
`None`) are `frob graph affects`'s optional `--max-depth`/`--max-nodes`
overrides for `frob.graph.affects.affects`'s own bounds -- collected via
the ordinary int-field loop in `from_external`, same posture as
`perf_max_depth`.

T-1069: `ticket_tier_value` (`str | None`, default `None`) is `frob ticket
tier <id> <epic|story|ticket>`'s new-tier argument, collected via the
ordinary string-field loop in `from_external` -- same shape as
`ticket_priority_level`/`ticket_kind_value`'s precedents, kept distinct
from `ticket_tier` (already `frob ticket new --tier`'s set-at-creation
field).

T-1004: `check_budget` (`int | None`, default `None`) is `frob check
--budget SECONDS`'s int field, collected the same way -- `None` leaves
every other `check_*` behavior untouched; set, it routes `check_runner.run`
to `_run_budgeted_check` before the normal full/`--only` dispatch (see
docs/commands/check.md).

T-1011: `docs_sync_commands` (`bool`, default `False`) is `frob docs
--sync-commands`'s flag, collected via the ordinary bool-field loop in
`from_external` -- set, `docs_runner.run` regenerates `docs/modules/
cli.md`'s generated command-table block instead of the ordinary extract/
search/overview dispatch (`docs_path` is not required in this mode).

T-1057: `ticket_worktree` (`Path | None`, default `None`) is resolved to
an absolute path right after the ordinary `Path`-typed-field loop in
`from_external`, not left as whatever `--worktree` was spelled on the
command line. `frob ticket land <id> --worktree <RELATIVE path>` used to
fail with `[Errno 2]`: `ticket_runner._land`'s pre-`land()` spawn
(`_shared_check_spawn_fn`/`_python_for_tree`) joins `cfg.ticket_worktree`
with `.venv/bin/python` and runs it with `cwd=` set to that same path --
the OS resolves a relative executable argument against the CALLING
process's cwd, not the target `cwd=`, so a relative `--worktree` broke
before `frob.tickets._land.land()`'s own internal `worktree.resolve()`
ever ran. Resolving once here, at argument-parse time, makes every
downstream consumer of `cfg.ticket_worktree` see an absolute path
unconditionally.

T-1029: `ticket_accept_criterion` (`list[str]`, default `[]`, repeatable
`--criterion TEXT`) and `ticket_accept_criterion_file` (`Path | None`,
default `None`, `--criterion-file PATH`) are `frob ticket accept <id>`'s
fields -- collected via the ordinary multi-value-list-field / Path-field
loops in `from_external`, same shape as `ticket_label_add`/
`ticket_scope_reason_file`'s precedents. See docs/modules/tickets.md#frob-
ticket-accept-t-1029 for the command itself.

## Runners

Each runner exposes exactly one public function, `run(cfg: AppConfig) -> None`,
invoked by `App.__call__`. They are documented here one line each; flag
semantics live in `AppConfig` and in each subcommand's own docs page.

<!-- frob:describes src/frob/app/gitlog_runner.py::run -->
<!-- frob:describes src/frob/app/vet_runner.py::run -->
<!-- frob:describes src/frob/app/stats_runner.py::run -->
<!-- frob:describes src/frob/app/arch_runner.py::run -->
<!-- frob:describes src/frob/app/perf_runner.py::run -->
<!-- frob:describes src/frob/app/dup_runner.py::run -->
<!-- frob:describes src/frob/app/xref_runner.py::run -->
<!-- frob:describes src/frob/app/parse_runner.py::run -->
<!-- frob:describes src/frob/app/scaffold_runner.py::run -->
<!-- frob:describes src/frob/app/check_runner.py::run -->
<!-- frob:describes src/frob/app/ack_runner.py::run -->
<!-- frob:describes src/frob/app/ticket_runner/__init__.py::run -->
<!-- frob:describes src/frob/app/outline_runner.py::run -->
<!-- frob:describes src/frob/app/mutate_runner.py::run -->
<!-- frob:describes src/frob/app/exports_runner.py::run -->
<!-- frob:describes src/frob/app/docs_runner.py::run -->
<!-- frob:describes src/frob/app/release_runner.py::run -->
<!-- frob:describes src/frob/app/graph_runner.py::run -->
<!-- frob:describes src/frob/app/bind_runner.py::run -->
<!-- frob:describes src/frob/app/cycle_runner.py::run -->
<!-- frob:describes src/frob/app/map_runner.py::run -->
<!-- frob:describes src/frob/app/agent_runner.py::run -->

- `gitlog_runner.run` -- runs `frob.gitlog.git_log` over `cfg.gitlog_*` and
  prints text or JSON (docs/commands/gitlog.md).
- `vet_runner.run` -- runs `frob vet [path]` or `frob vet --hook`; hook mode
  exits 2 on a quarantine/typosquat block for a Claude Code PreToolUse hook.
- `stats_runner.run` -- renders the delivery snapshot (queue health + commit
  cadence) from `frob.stats.collect`.
- `arch_runner.run` -- runs the architectural linter (long functions, god
  classes) over `cfg.arch_path`.
- `perf_runner.run` -- dispatches `frob perf profile|heat` (docs/modules/perf.md).
- `dup_runner.run` -- runs `frob.dup.find_duplicates` over `cfg.dup_path`.
- `xref_runner.run` -- runs `frob.xref.xref` for `cfg.xref_symbol`
  (docs/commands/xref.md).
- `parse_runner.run` -- reads a tool's raw output (pytest/ruff/ty/clang/...)
  from stdin or a file and emits a compact structured summary.
- `scaffold_runner.run` -- lists project types or renders a new project
  scaffold (docs/commands/scaffold.md).
- `check_runner.run` -- runs the full `frob check` tool pipeline
  (docs/commands/check.md); `cfg.check_budget` set (T-1004) routes to
  `_run_budgeted_check` instead, self-selecting `--only` stage groups to
  fit the given second count.
- `ack_runner.run` -- builds/loads the graph, acknowledges refs, writes the
  lock file (docs/modules/graph.md).
- `ticket_runner.run` -- dispatches to the ticket subcommand named by
  `cfg.ticket_command` (docs/modules/tickets.md).
- `outline_runner.run` -- runs `frob.outline.outline_file`, falling back to
  `frob map` output for a directory target (docs/commands/outline.md).
- `mutate_runner.run` -- runs `frob.mutate.run_mutations` and reports which
  mutants survived the given test command.
- `exports_runner.run` -- runs `frob.exports.exports_package` over
  `cfg.exports_path` (docs/commands/exports.md).
- `docs_runner.run` -- runs `frob.docs` overview/search/extract over
  `cfg.docs_path`.
- `release_runner.run` -- dispatches to the release subcommand named by
  `cfg.release_command` (mechanical semver stamping/checking/`sync` --
  T-1009's single-source-of-truth regeneration, docs/modules/release.md).
- `graph_runner.run` -- dispatches build/query/why/affects based on
  `cfg.graph_command` (docs/modules/graph.md); `affects` (T-0628) reads
  `cfg.graph_max_depth`/`cfg.graph_max_nodes` (both optional, default to
  `frob.graph.affects.affects`'s own keyword defaults).
- `bind_runner.run` -- verifies BIND declarations against source signatures
  (docs/modules/bind.md); parses its own argv rather than taking `AppConfig`.
- `cycle_runner.run` -- runs `frob.cycle.graph.find_cycles` over
  `cfg.cycle_path` (docs/commands/cycle.md).
- `map_runner.run` -- runs `frob.map.map_project` over `cfg.map_path`
  (docs/commands/map.md).
- `agent_runner.run` -- `frob agent env [path]` (T-0574): prints
  `FROB_WORKTREE`/`FROB_AGENT` export lines for a worktree so dispatch
  tooling can inject the guard env mechanically; parses its own argv
  rather than taking `AppConfig`, dispatched the same way `bind_runner`
  is.

## Shared graph-snapshot helper (T-1085)

`frob.app._snapshot` centralizes the "load `root`'s cached graph snapshot,
building it fresh on a missing/stale cache, exit(1) on a hard build
failure" shape three runners (`debt_runner`, `deprecated_runner`,
`release_runner`) each carried as a byte-identical private copy before
T-1085's extraction (an `abstraction-opportunity` finding from the arch
package's own self-scan, T-0393/T-1067). `perf_runner`'s own
`_load_snapshot` deliberately stays separate -- it always rebuilds
unconditionally rather than trying the cache first, a genuinely different
freshness posture for `heat`, not an overlooked fourth duplicate.

<!-- frob:describes src/frob/app/_snapshot.py::load_or_build_snapshot -->
<!-- frob:describes src/frob/app/_snapshot.py::CACHE_REL -->

- `CACHE_REL` -- the shared `.frob/cache.db` relative path every
  graph-backed runner resolves its snapshot cache against.
- `load_or_build_snapshot(root, *, log_context)` -- try `frob.graph.
  load_graph(root / CACHE_REL)` first; on a miss/stale cache, `frob.graph.
  build_graph` fresh; `sys.exit(1)` on a hard build error, logging
  `log_context` (`"debt"`/`"deprecated"`/`"release"`) so each caller's own
  identity survives the shared code path.

## Shared styling helper (T-0179)

`frob.app._style` centralizes ANSI-color decisions for every runner's
human-facing output -- one palette, not ad hoc `paint()` calls scattered
per runner. Every function is a pure text -> text transform; the caller
always computes `color` from `frob.logging.color.should_color(stream)`
(the correct stream for the line -- stdout for INFO/DEBUG, stderr for
WARNING+) and passes it in, so `--json`/non-TTY output never gains an
escape code.

<!-- frob:describes src/frob/app/_style.py::STATE_STYLE -->
<!-- frob:describes src/frob/app/_style.py::style_ticket_id -->
<!-- frob:describes src/frob/app/_style.py::style_state -->
<!-- frob:describes src/frob/app/_style.py::style_ok -->
<!-- frob:describes src/frob/app/_style.py::style_fail -->
<!-- frob:describes src/frob/app/_style.py::style_warn -->
<!-- frob:describes src/frob/app/_style.py::style_header -->
<!-- frob:describes src/frob/app/_style.py::style_rule -->

- `STATE_STYLE` -- ticket-state -> SGR code map (`done`=green,
  `in_progress`=cyan, `planned`=yellow, `queued`/`dropped`=dim,
  `blocked`/`failed`=red).
- `style_ticket_id` -- bolds a ticket id (`T-0042`).
- `style_state` -- colors a ticket state word per `STATE_STYLE`.
- `style_ok` / `style_fail` / `style_warn` -- green/red/yellow for
  passed/failed/waived text (PROVED, GAP, WAIVED, FAIL/ok table cells).
- `style_header` -- bold section headers.
- `style_rule` -- cyan-highlights a rule/gate id (e.g. `THREAT002`).

## frob.docs library

The `frob docs` subcommand is backed by `frob.docs`, a small doc-search
library used to answer "what documentation exists / matches this symbol".

<!-- frob:describes src/frob/docs/__init__.py::Docstring -->
<!-- frob:describes src/frob/docs/__init__.py::DocEntry -->
<!-- frob:describes src/frob/docs/__init__.py::DocMatch -->
<!-- frob:describes src/frob/docs/__init__.py::extract_docstrings -->
<!-- frob:describes src/frob/docs/__init__.py::find_docs_dir -->
<!-- frob:describes src/frob/docs/__init__.py::overview -->
<!-- frob:describes src/frob/docs/__init__.py::search -->

```python
# frob/docs/__init__.py
class Docstring
    # One extracted docstring: symbol name, kind, first-sentence summary.

class DocEntry
    # One markdown doc file's path plus its extracted heading/anchor text.

class DocMatch
    # A search hit: which DocEntry/Docstring matched a query and why.

extract_docstrings(path: Path, symbol: str | None = None) -> list[Docstring]
    # Parses a source file and pulls out every (or one named) symbol's
    # docstring.

find_docs_dir(start: Path) -> Path | None
    # Walks upward from `start` to locate the project's docs/ directory
    # (or None if there isn't one).

overview(path: Path, symbol: str | None = None) -> list[DocEntry]
    # Renders a compact summary of docs/*.md headings under `path`, for
    # "what documentation exists here" without reading every file.

search(query: str, docs_dir: Path) -> list[DocMatch]
    # Searches docs/*.md under `docs_dir` for `query`, ranked by match.
```

## Shared exclude-glob logic

`src/frob/excludes.py` is the one place that reads `[graph] exclude` from
`frob.toml`; every file-walking surface (the graph build, `frob dup`,
`frob arch`, `frob cycle`) consults it so a repo declares generated/vendored
directories once.

<!-- frob:describes src/frob/excludes.py::load_exclude_globs -->
<!-- frob:describes src/frob/excludes.py::is_excluded -->
<!-- frob:describes src/frob/excludes.py::is_skipped_dir -->
<!-- frob:describes src/frob/excludes.py::BUILTIN_SKIP_DIRS -->
<!-- frob:describes src/frob/excludes.py::walk_pruned -->
<!-- frob:describes src/frob/excludes.py::iter_files -->

```python
# frob/excludes.py
load_exclude_globs(root: Path) -> tuple[str, ...]
    # Reads `[graph] exclude` glob patterns from frob.toml at `root`.

is_excluded(rel_path: str, exclude_globs: tuple[str, ...]) -> bool
    # True if `rel_path` (root-relative, POSIX) matches one of the globs.

is_skipped_dir(name: str) -> bool
    # True if a directory name is in the builtin always-pruned set
    # (__pycache__, .git, node_modules, ...), independent of frob.toml.

walk_pruned(root: Path, *, exclude_globs: tuple[str, ...] = ()) -> Iterator[Path]
    # os.walk that prunes dirnames in place (via _should_prune_dir) BEFORE
    # descending -- never enters .git/.venv/node_modules/.claude/worktrees/
    # build/dist/target/__pycache__.

iter_files(root: Path, *, suffix: str | None = None) -> tuple[Path, ...]
    # The one shared entry point for "give me every file under root,
    # pruned". Prefers a `git ls-files` fast path (tracked files only)
    # when root is a git work tree; falls back to walk_pruned otherwise.
```

`BUILTIN_SKIP_DIRS` is the frozenset backing `is_skipped_dir`: the
always-pruned directory names, additive to whatever `frob.toml` declares.

`walk_pruned`/`iter_files` (T-0471) are the shared prune-aware walk
primitives every traversal in `src/frob/` must route through --
`frob.gates._walk_lint`'s WALK001 statically flags any NEW raw
`Path.rglob`/`os.walk`/`glob.glob("**"...)` call that bypasses them (see
docs/modules/gates.md#walk001-unpruned-traversal-t-0471).

<!-- frob:invariant INV-005 -->

The "always computes `color` from the correct stream" claim above (Shared
styling helper) is a caller-side calling convention documented for
consistency, not something a gate statically enforces today -- no lint
walks every call site to confirm the stream argument matches the log
level. True as stated (`_style` itself is a pure function either way,
so a caller passing the wrong stream produces a rendering bug, not an
`_style` bug), but not mechanically provable at this granularity; INV-005
above covers the one claim in this file that a gate does check.
