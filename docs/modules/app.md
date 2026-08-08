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

T-1218: `_dispatch` (the argv-to-`App` step inside `main`) prints TWO
independent stale-binary warnings to stderr before building `AppConfig`,
both string-or-`None` probes from `frob.app._config_meta`:

- `stale_install_warning` (T-0358): exact-version mismatch between the
  RUNNING `frob` package and THIS repo's own declared `pyproject.toml`
  version -- only fires inside frob's own source checkout (a repo whose
  `pyproject.toml` names the `frob` project itself), and only when the
  running package resolves outside that checkout's `src/frob/` (a stale
  globally `uv tool install`ed binary).
- `stale_binary_warning` (T-1218): ordering check against ANY repo's own
  `frob.toml` `min_frob_version` floor -- applies to any repo that USES
  frob (not just frob's own checkout) and warns whenever the invoked
  version is strictly below the declared floor. This is the fix for the
  2026-08-02 incident: a `git` merge-driver invoked a stale globally
  installed `frob` (0.9.0) against a repo whose in-tree code had advanced
  to 0.277.0, silently mis-splicing `tickets.md` with no warning at all.
  `frob doctor` (`DoctorReport.stale_binary`,
  `docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319`)
  reports the same check as a finding that makes `healthy` False, same
  class as `venv_shims`/`stale_ticket_leases`.

T-1216: `App.__call__` resolves and imports ONLY the one `*_runner`
module the invoked subcommand needs (`_resolve_runner`), and
`frob.app`'s package `__init__.py` resolves its `<name>_runner_run`
re-export aliases lazily via `__getattr__` (PEP 562) rather than
importing every runner module up front. Before this, `import frob.app`
(triggered by every CLI invocation, since `frob.__main__` imports
`App`/`AppConfig` from here) eagerly imported all ~30 runner modules
regardless of which one subcommand actually ran, paying for
`deploy_runner -> frob.strata -> frob.vet -> frob.gates`'s import graph
even on a plain `frob ticket list`.

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

T-1271: every `AppConfig` field that carries a ticket-model `StrEnum` value
(`ticket_state`, `ticket_kind`, `ticket_kind_value`, `ticket_tier`,
`ticket_tier_value`, `ticket_priority_level`, `ticket_origin`,
`ticket_review_verdict`) has a `field_validator` that rejects an
unrecognized value with EVERY legal value named inline -- e.g. `'open' is
not a valid ticket state; valid values are: queued, planned, in-progress,
blocked, done, dropped` -- instead of letting a bare `TicketState(v)` call
downstream raise its own terser `ValueError` with no indication of what
would have been valid. This was mined from real agent usage: `frob ticket
list --status open` used to surface exactly that terser message with
nothing to correct it from. `None` always passes through unchanged (these
are all optional filters/inputs); an already-legal value is returned as-is.
The CLI's top-level `except Exception` in `frob.__main__.main` prints the
resulting `pydantic.ValidationError` as `frob: <message>` and exits 1 --
still one command's worth of noise, not a raw traceback, but see the
`--verbose`/warning-collapse and porcelain-verb halves of T-1271's
acceptance criteria (mining a broader "hidden-argument hell" sweep) for
what this ticket's own narrow scope (`app/config.py` plus this doc; not
`_cli_parsers/**`) could NOT reach -- tracked separately, see this
section's cli-hygiene draft-ticket note in `tickets.md`.

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

T-1130: `ticket_no_commit` (`bool`, default `False`) is `frob ticket
new/drop/fail --no-commit`'s opt-out flag (`action="store_true"` in the
parser, one field shared across all three subcommands the way
`ticket_json`/`ticket_force` already are) -- `True` skips
`frob.tickets._leases.commit_ticket_ledger_change`'s auto-commit of that
verb's own ledger write entirely (see docs/modules/tickets.md
#newdropfail-auto-commit-t-1130).

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
<!-- frob:describes src/frob/app/explore_runner.py::run -->
<!-- frob:describes src/frob/app/quality_runner.py::run -->
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
<!-- frob:describes src/frob/app/clean_runner.py::run -->
<!-- frob:describes src/frob/app/debt_runner.py::run -->
<!-- frob:describes src/frob/app/deploy_runner.py::run -->
<!-- frob:describes src/frob/app/deprecated_runner.py::run -->
<!-- frob:describes src/frob/app/doctor_runner.py::run -->
<!-- frob:describes src/frob/app/fleet_runner.py::run -->
<!-- frob:describes src/frob/app/fmt_runner.py::run -->
<!-- frob:describes src/frob/app/natives_runner.py::run -->
<!-- frob:describes src/frob/app/pool_runner.py::run -->
<!-- frob:describes src/frob/app/registry_runner.py::run -->
<!-- frob:describes src/frob/app/serve_runner.py::run -->
<!-- frob:describes src/frob/app/sys_runner.py::run -->
<!-- frob:describes src/frob/app/test_runner.py::run -->
<!-- frob:describes src/frob/app/worktree_runner.py::run -->

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
- `explore_runner.run` -- dispatches `frob explore <map|outline|xref|
  docs-search>` (T-1238, `cfg.explore_command`) straight into
  `map_runner`/`outline_runner`/`xref_runner`/`docs_runner._run_search`,
  the same code the standalone top-level commands run
  (docs/design/cli-regrouping.md, docs/modules/cli.md).
- `quality_runner.run` -- dispatches `frob quality <check|test|dup|arch|
  bind|cycle|mutate|perf>` (T-1567, `cfg.quality_command`) straight into
  `check_runner`/`test_runner`/`dup_runner`/`arch_runner`/`cycle_runner`/
  `mutate_runner`/`perf_runner`, the same code the standalone top-level
  commands run (docs/design/cli-regrouping.md, docs/modules/cli.md).
  `bind` is the one exception: `frob quality bind` is dispatched by
  `frob.__main__._dispatch` directly, never through this runner, since
  `bind_runner.run` takes raw argv rather than an `AppConfig`.
- `xref_runner.run` -- runs `frob.xref.xref` for `cfg.xref_symbol`
  (docs/commands/xref.md).
- `parse_runner.run` -- reads a tool's raw output (pytest/ruff/ty/clang/...)
  from stdin or a file and emits a compact structured summary.
- `scaffold_runner.run` -- lists project types or renders a new project
  scaffold (docs/commands/scaffold.md).
- `check_runner.run` -- runs the full `frob check` tool pipeline
  (docs/commands/check.md); `cfg.check_budget` set (T-1004) routes to
  `_run_budgeted_check` instead, self-selecting `--only` stage groups to
  fit the given second count. `cfg.check_fix` (T-1260) routes the
  post-stage tail through `_apply_tier_a_and_reverify`: apply every
  registered Tier-A auto-fix, re-run the gates stage once, and splice a
  `fixed`/`rolled_back`/`fixits` `fix` report into the summary/JSON output
  (docs/design/check-fix-engine.md) -- a plain `frob check` (no `--fix`)
  is untouched by this, byte-identical to before T-1260.
- `ack_runner.run` -- builds/loads the graph, acknowledges refs, writes the
  lock file (docs/modules/graph.md); requires `--reason`/`--reason-file`
  (refuses otherwise) and appends an `AckAuditEntry` per acked `(ref,
  facet)`, or with `--list` renders the audit trail instead of acking
  (T-1317, docs/modules/gates.md#ack-accountability-t-1317).
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
  (docs/commands/map.md). T-1479: `--json` against the daemon's own root
  (`cfg.map_path` unset or `.`) tries the daemon proxy (`frob_map`,
  docs/modules/serve.md#frob-map---json-t-1479) first via
  `_try_map_via_daemon`, falling through to the in-process call above on
  any miss or a non-root target.
- `agent_runner.run` -- `frob agent env [path]` (T-0574): prints
  `FROB_WORKTREE`/`FROB_AGENT` export lines for a worktree so dispatch
  tooling can inject the guard env mechanically; parses its own argv
  rather than taking `AppConfig`, dispatched the same way `bind_runner`
  is.
- `clean_runner.run` -- `frob clean [--all|--deep] [-y]` (T-0457,
  docs/modules/clean.md).
- `debt_runner.run` -- `frob debt`: lists outstanding `frob:debt` entries (T-0412).
- `deploy_runner.run` -- `frob deploy`: compiles `std.host` `HostManifest`
  facts into Linux/systemd and Windows install/status/uninstall scripts
  (T-0257/T-0264, docs/commands/deploy.md).
- `deprecated_runner.run` -- `frob deprecated`: lists outstanding
  `frob:deprecated` entries (T-0638).
- `doctor_runner.run` -- `frob doctor`: native-extension/scaffold/ticket-
  lease/venv-shim diagnosis (T-0319, docs/guides/install.md). T-1634: on the
  otherwise-healthy path, also surfaces a confirmed-dead land.lock holder
  as a plain-text info line (self-healing, no longer a health failure --
  see docs/guides/install.md's "Orphaned (dead-holder) land.lock is
  self-healing" section).
- `fleet_runner.run` -- `frob fleet status`/`frob fleet route` (T-0573):
  cross-repo status/gate rollup and ticket routing (docs/modules/fleet.md).
- `fmt_runner.run` -- `frob fmt [path] [--check] [--json]` (T-0441):
  directive canonicalization.
- `natives_runner.run` -- `frob natives build`: frob-owned native crate
  builds (T-0864/T-0735).
- `pool_runner.run` -- `frob pool snapshot|clear` (T-0569): ratchet-pool
  baseline commands over `frob.gates._ratchet`.
- `registry_runner.run` -- `frob registry audit` (T-0407): per-registry-file
  disposition accounting over `docs/design/registry/*.yaml`.
- `serve_runner.run` -- `frob serve`: the stdio MCP adapter (docs/modules/serve.md).
- `sys_runner.run` -- `frob sys`: strata design-model applications
  (docs/commands/sys.md).
- `test_runner.run` -- `frob test [--all] [--base REF] [--lang L]
  [--fallback MODE]` (docs/modules/testing.md).
- `worktree_runner.run` -- `frob worktree sweep [--dry-run] [--min-age
  HOURS] [--force]` (T-0836): lease-aware stale-worktree cleanup. T-1739
  added `--force` and the `kept:live` verdict -- see docs/modules/
  tickets.md#worktree-liveness-scan-t-1715-t-1739 for the liveness scan
  this now runs before the dirty/lease/age gates.

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

## T-1124: abstraction-opportunity remainder disposition

T-1085 filed the arch package's `src/frob/app/**`-scoped
abstraction-opportunity remainder as T-1124: `check_runner.py`'s two
`ToolResult`-builder groups, `deploy_runner.py`'s repeated-`_design_dir`-
name group, and `perf_runner.py`'s `_heat`/`_collect` pair. Each was
checked on its own merits rather than extracted uniformly:

- **`perf_runner.py` -- genuine extraction.** `_heat`/`_collect` carried
  byte-identical `--json`-implies-quiet-stdout-logs wrapper bodies
  (`import contextlib; ctx = quiet_stdout_logs() if cfg.perf_json else
  contextlib.nullcontext(); with ctx: <body>(cfg)`). Extracted into
  `_run_quiet_if_json(cfg, body)`; both callers now pass their own body
  function through it.
- **`check_runner.py` -- genuine extraction for the two in-file
  members.** Of the 7-member `(Path) -> ToolResult | None` group, only
  `_deploy_drift_result`/`_deploy_conformance_result` live in
  `check_runner.py` itself (the other 5 -- `_derived_state_integrity_result`,
  `_run_clang_format`, `_run_cargo_fmt_check`, `_run_cargo_valgrind`,
  `_run_bind` -- live in `src/frob/check/**`, outside this ticket's
  `scope`). The two in-file members shared an identical "opt-in on
  `deploy/` existing, call a violations function, wrap the result" shape;
  extracted into `_opt_in_deploy_stage_result(root, violations_fn,
  wrap_fn)`. The 5-member `(str, str) -> ToolResult` group has only ONE
  member in `check_runner.py` (`_skip_note_result`) -- the rest
  (`_missing_tool_result`, `tool_unavailable_result`,
  `tool_disabled_result`, `parse_junit_xml`) live in `src/frob/check/_ts.py`
  and `src/frob/process/parsers/**`, also outside `scope`; nothing to
  extract within one file for this group. Both groups keep firing from
  `frob check --only arch` (unwaivable, `abstraction-opportunity` is
  never `frob:waive`-able per docs/modules/arch.md) because the shared
  signature carries a specific domain type (`ToolResult`) -- the finding
  is not resolvable without a cross-subsystem consolidation reaching into
  `src/frob/check/**`/`src/frob/process/parsers/**`, out of this ticket's
  `scope`; filed as a follow-up.
- **`deploy_runner.py` -- grounded disposition, not extracted.**
  `_design_dir`'s repeated-name pair is `deploy_runner.py`'s own copy and
  `sys_runner.py`'s own copy (leased by a concurrent ticket this wave,
  out of `scope` either way) -- both already carry docstrings citing each
  other and `frob.gates`'s own third copy as a deliberate,
  previously-reviewed duplication (a two-line `frob.toml` read judged not
  worth a cross-module import, T-0084). The group's other 4 members
  (`_read_ledger_text_or_empty`/`_read_archive_text_or_empty` in
  `src/frob/tickets/_land.py`, `_read_text_or_empty` x2 in
  `src/frob/vet/_ecosystem.py`/`_supplychain.py`) are absent from
  `deploy_runner.py` at all -- a coincidental cross-subsystem signature
  collision, not a `deploy_runner.py` duplicate.

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

## `frob check --census` (T-1764)

`frob check --census` (`src/frob/app/check_runner.py::_run_census`) runs
every gate, unscoped, over the whole tree, then prints one row per rule
id (`frob.gates._waive.RuleCensusEntry`, built by `census_gate_rules`):
how many findings still surface (`fired`), how many a `frob:waive`
suppresses (`waived`), the resulting waive-rate, and how many of those
waivers are DEAD (`WAIVE004` -- a directive matching zero live findings
this run, pure decay).

The methodological correction T-1763 forced: a rule only ever evaluated
against a DIFF (`frob.gates._waive._WAIVE004_STRUCTURALLY_UNVERIFIABLE_
RULES` -- currently `DUP001`/`DUP002`/`AFFECT001`/`AFFECT002`/`WIRE001`/
`SCOPE001`) reads `fired=0` on a clean-tree snapshot as its EXPECTED
healthy signature, not evidence it is dead. `--census` classifies every
rule `corpus_wide` vs not FIRST, and prints `n/a (diff-scoped)` for a
non-corpus-wide rule's rate instead of computing one from this single
snapshot -- the exact number that would have recommended deleting two
working detectors (INV006 was correctly deleted at 338 waivers/0
findings only because it IS corpus-wide; AFFECT001/DUP001 sit at the
same 0-findings shape but are diff-scoped, and T-1763 kept them).

This is deliberately a REPORT, not a gate: a high waive-rate is not
itself a `frob check` failure today (the ticket's own acceptance
criteria: start advisory, do not make it blocking until the top
offenders are dealt with, or day one produces a waiver ON the
waive-rate warning). `--json` emits the same rows as a JSON array.
