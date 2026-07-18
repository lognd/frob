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
    # this is the `frob` console-script entry point.

# frob/app/app.py
class App
    # Callable dispatcher: __call__() matches cfg.subcommand and invokes
    # the corresponding *_runner.run(cfg); unknown/missing subcommand logs
    # usage and exits 1.
```

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
<!-- frob:describes src/frob/app/ticket_runner.py::run -->
<!-- frob:describes src/frob/app/outline_runner.py::run -->
<!-- frob:describes src/frob/app/mutate_runner.py::run -->
<!-- frob:describes src/frob/app/exports_runner.py::run -->
<!-- frob:describes src/frob/app/docs_runner.py::run -->
<!-- frob:describes src/frob/app/release_runner.py::run -->
<!-- frob:describes src/frob/app/graph_runner.py::run -->
<!-- frob:describes src/frob/app/bind_runner.py::run -->
<!-- frob:describes src/frob/app/cycle_runner.py::run -->
<!-- frob:describes src/frob/app/map_runner.py::run -->

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
  (docs/commands/check.md).
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
  `cfg.release_command` (mechanical semver stamping/checking).
- `graph_runner.run` -- dispatches build/query/why based on
  `cfg.graph_command` (docs/modules/graph.md).
- `bind_runner.run` -- verifies BIND declarations against source signatures
  (docs/modules/bind.md); parses its own argv rather than taking `AppConfig`.
- `cycle_runner.run` -- runs `frob.cycle.graph.find_cycles` over
  `cfg.cycle_path` (docs/commands/cycle.md).
- `map_runner.run` -- runs `frob.map.map_project` over `cfg.map_path`
  (docs/commands/map.md).

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

```python
# frob/excludes.py
load_exclude_globs(root: Path) -> tuple[str, ...]
    # Reads `[graph] exclude` glob patterns from frob.toml at `root`.

is_excluded(rel_path: str, exclude_globs: tuple[str, ...]) -> bool
    # True if `rel_path` (root-relative, POSIX) matches one of the globs.

is_skipped_dir(name: str) -> bool
    # True if a directory name is in the builtin always-pruned set
    # (__pycache__, .git, node_modules, ...), independent of frob.toml.
```

`BUILTIN_SKIP_DIRS` is the frozenset backing `is_skipped_dir`: the
always-pruned directory names, additive to whatever `frob.toml` declares.
