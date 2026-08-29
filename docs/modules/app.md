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

See `frob <subcommand> --help` (via `src/frob/_cli_parsers/_root.py::_build_parser`)
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
    #
    # T-2443: installs a SIGTERM reaper (frob.process.install_sigterm_
    # reaper) FIRST, before any dispatch -- see docs/modules/process.md
    # #forkserver-reaping-t-2443 for the leaked-forkserver defect this
    # closes. Every real invocation is a fresh process, so this is the one
    # place that reliably runs once per invocation regardless of subcommand.

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

T-1697 added `Subcommand.verify` (`frob verify status|now|explain|
dispose`, docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697) to
`_SUBCOMMAND_RUNNER_NAMES`/`_RUNNER_MODULE_NAMES` alongside every other
uniform `run(AppConfig)` runner -- no special-casing in `App.__call__`
itself, same as any other subcommand that is not `bind`.

T-1218/T-3129: `_dispatch` (the argv-to-`App` step inside `main`) prints
THREE independent stale-binary warnings to stderr before building
`AppConfig`, all string-or-`None` probes:

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
- `binary_fingerprint_warning` (T-3129, `frob.app._version_guard.binary_
  fingerprint_warning`): content-identity check, distinct from both checks above -- neither
  compares GIT HEAD sha, only version strings, so a stale global binary
  whose declared version was never bumped past its last release is
  invisible to `stale_install_warning`'s exact-match check (the
  precipitating incident: the globally installed `frob` and this repo's
  own `uv run frob` both reported the SAME version string while exposing DIFFERENT
  CLI surfaces -- `refactor`, `narrative`, `status`, `-v/--verbose`,
  `ticket unblock`, and `refactor move-module` all present in one, absent
  in the other). Only fires inside frob's own source checkout (same
  `is_frob_own_repo` guard as `stale_install_warning`). Resolves the
  running package's own git HEAD sha (walking up from its `__init__.py`
  for a `.git` ancestor, same shape as `frob.app._daemon_proxy._client_
  source_sha`'s T-2884 precedent) and compares it against `repo_root`'s
  own `git rev-parse HEAD` -- quiet only when both resolve AND match, or
  when the running package IS repo_root's own src/frob/__init__.py exactly.
  Fail-safe-to-stale (T-2884's direction, reapplied): an unresolvable sha
  on EITHER side (e.g. a packaged wheel install with no `.git` ancestor
  at all) warns rather than silently trusting an indeterminate match.

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
`ticket_scope_reason_file`'s precedents. See
docs/modules/tickets-data-storage.md#frob-ticket-accept-t-1029 for the
command itself.

T-2004 ("tested is not reached"): `from_external`'s six `_apply_*_fields`
type-group tuples (`_STRING_FIELDS`/`_PATH_FIELDS`/`_INT_FIELDS`/
`_FLOAT_FIELDS`/`_LIST_FIELDS`/`_BOOL_FLAGS`) plus a small ad-hoc set
(`_AD_HOC_FORWARDED_FIELDS`: `subcommand`/`no_color`/`ticket_worktree`/
`parse_exit_code`/`check_budget`/`ticket_body`/`fleet_body`/
`exports_exclude`) are the ONLY names `from_external` ever forwards from
a parsed `argparse.Namespace` into `AppConfig`. A flag that parses
correctly, has a matching `AppConfig` field, and is simply absent from
every one of those sets is silently dropped: the field stays at its
pydantic default forever, no error, no warning -- and a unit test that
constructs `AppConfig` directly (bypassing argparse and `from_external`
both) passes regardless, because it never exercises the wiring at all.
Two real, independent incidents hit this in one week: T-1995's
`--ack-related` (missing from `_STRING_FIELDS`) and T-1927's
`sys_threats_boundary` positional (missing from every tuple). Both had
full, passing unit coverage; neither worked end-to-end.

`frob.app._config_external.find_dropped_cli_flags(parser, config_cls)`
is the static check this class of bug needed: it walks the REAL argparse
parser tree (`_all_parser_dests`, recursing through every
`_SubParsersAction`) for every `dest`, intersects that with `config_cls.
model_fields` (a flag with no matching model field -- e.g. `bind`/
`agent`/`worktree sweep`'s own flags, which bypass `AppConfig` entirely
by design, dispatched directly in `frob.__main__._dispatch`, docs/
modules/app.md above -- was never meant to reach the model and is
correctly invisible here), and subtracts `_all_forwarded_field_names()`
(the union of the same six tuples plus the ad-hoc set, read directly off
this module's own live source, never a hand-typed mirror -- a second
list would just be a second place to forget). Both sides of the
comparison are the ACTUAL live parser and the ACTUAL forwarding
declarations; nothing here is a third list a maintainer must remember to
keep in sync. `tests/unit/test_app_config_flag_coverage.py::
TestFindDroppedCliFlags.test_current_tree_has_zero_dropped_flags` runs
this against the real `frob` parser and the real `AppConfig` as a
ratchet -- MEASURED, not assumed: 317 CLI flags examined (every dest
with a matching `AppConfig` field), 0 dropped, after T-2004 itself found
and fixed 6 real, live-broken flags on the tree at measurement time
(`ticket_anchor_reason`, `ticket_anchor_reason_file`, `ticket_anchor_
set`, `ticket_anchor_clear`, `ticket_doable_show_anchors`, and this very
series' own `sys_threats_boundary`).

## Runners

Each runner exposes exactly one public function, `run(cfg: AppConfig) -> None`,
invoked by `App.__call__`. They are documented here one line each; flag
semantics live in `AppConfig` and in each subcommand's own docs page.

T-2582: the human-mode query runners (`debt`/`exports`/`gitlog`/`mutate`/
`outline`/`xref`, plus `deprecated`/`fleet`) now quiet stdout-bound
DEBUG/INFO chatter by DEFAULT in both `--json` and human mode, via
`frob.logging.quiet.quiet_query_stdout` (docs/modules/logging.md#public-api)
-- previously only `--json` mode was quieted, so a bare human-mode
invocation could drown a short answer under thousands of parse-diagnostic
lines. `FROB_VERBOSE=1` restores the full diagnostic stream.

<!-- frob:describes src/frob/app/gitlog_runner.py::run -->
<!-- frob:describes src/frob/app/vet_runner.py::run -->
<!-- frob:describes src/frob/app/stats_runner.py::run -->
<!-- frob:describes src/frob/app/arch_runner.py::run -->
<!-- frob:describes src/frob/app/perf_runner.py::run -->
<!-- frob:describes src/frob/app/dup_runner.py::run -->
<!-- frob:describes src/frob/app/explore_runner.py::run -->
<!-- frob:describes src/frob/app/quality_runner.py::run -->
<!-- frob:describes src/frob/app/design_runner.py::run -->
<!-- frob:describes src/frob/app/ops_runner.py::run -->
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
<!-- frob:describes src/frob/app/pyfmt_runner.py::run -->
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
- `design_runner.run` -- dispatches `frob design <sys|registry|docs|
  graph|exports>` (T-1568, `cfg.design_command`) straight into
  `sys_runner`/`registry_runner`/`docs_runner`/`graph_runner`/
  `exports_runner`, the same code the standalone top-level commands run
  (docs/design/cli-regrouping.md, docs/modules/cli.md).
- `ops_runner.run` -- dispatches `frob ops <release|natives|doctor|clean|
  fleet|deploy|scaffold|gitlog|stats>` (T-1569, `cfg.ops_command`)
  straight into `release_runner`/`natives_runner`/`doctor_runner`/
  `clean_runner`/`fleet_runner`/`deploy_runner`/`scaffold_runner`/
  `gitlog_runner`/`stats_runner`, the same code the standalone top-level
  commands run (docs/design/cli-regrouping.md, docs/modules/cli.md).
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
  is untouched by this, byte-identical to before T-1260. T-2486: every
  risky `--json`-mode span in this runner (stage running, the daemon-
  delta RPC probe, `--land-parity`, `--census`, `--fix`'s ruff re-run)
  is wrapped in `_guard_json_stdout_writes` -- a structural boundary that
  redirects ANY stray stdout write (not just a misleveled log call) to
  stderr for the guarded span's duration, closed before this runner's own
  final JSON payload emission. T-2492 promoted that guard (and its
  `_StderrRedirectStdout` proxy) out of this file into the shared
  `src/frob/app/_json_guard.py` -- `check_runner.py` now imports it
  rather than defining it, byte-identical behavior -- and, having
  execution-verified all 26 other `--json`-bearing runners against this
  repo, applied the same guard to the 8 that were genuinely leaking:
  `bind_runner`, `clean_runner`, `docs_runner`, `fmt_runner`,
  `graph_runner` (`query`/`why`/`affects`), `map_runner`, `test_runner`,
  and `vet_runner`.
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
- `graph_runner.run` -- dispatches build/query/why/affects/select-batch-
  tests based on `cfg.graph_command` (docs/modules/graph.md); `affects`
  (T-0628) reads `cfg.graph_max_depth`/`cfg.graph_max_nodes` (both
  optional, default to `frob.graph.affects.affects`'s own keyword
  defaults). `select-batch-tests` (T-1689) reads the current verify queue
  and runs its union touched-set in ONE pytest process per language via
  `frob.verify._selection.run_batch_selected_tests` -- see
  docs/modules/tickets-verify-sweep.md#batch-test-selection-t-1689.
- `bind_runner.run` -- verifies BIND declarations against source signatures
  (docs/modules/bind.md); parses its own argv rather than taking `AppConfig`.
- `cycle_runner.run` -- runs `frob.cycle.graph.find_cycles` over
  `cfg.cycle_path` (docs/commands/cycle.md). T-2588: `cfg.cycle_path` is
  resolved to its nearest enclosing `pyproject.toml` (falling back to the
  git repo root) before the import graph is built, rather than trusting
  whatever directory the caller happened to point at -- resolving edges
  relative to the wrong root silently dropped every absolute intra-project
  edge and could report a false "no cycles found". Exit code is now
  load-bearing: 0 when the graph is clean, 1 when real cycles are found,
  2 when `cfg.cycle_path` cannot be resolved to a project root at all (an
  unmeasured tree, never reported as clean) -- previously this always
  exited 0 regardless of outcome.
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
- `pyfmt_runner.run` -- `frob format [path] [--select-imports-only]`
  (T-2251): write-mode `ruff check --fix` + `ruff format`, the frob-native
  replacement for the Makefile's `format`/`lint-fix`/`all` targets. Default
  (no flag) delegates to `frob.check._python._run_ruff_autofix` (T-2320/
  T-2252, also `frob check --fix-ruff`'s own entry point); `--select-
  imports-only` narrows the `ruff check --fix` stage to `--select I`.
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
- `ticket_runner._waive_audit.run` -- `frob ticket waive-audit {scan,
  complete}` (T-2467): see "Waive audit (T-2467)" below.

## Waive audit (T-2467)

T-1614's `frob:waive` honesty audit used to be `runs_last` --
undispatchable while any other ticket in the repo was queued/in-progress,
a precondition that structurally never holds in a repo with continuous
ticket inflow. T-2467 reshaped it into a periodic, watermark-scoped pass:

- `frob.gates._waive_audit_watermark` -- persisted progress marker.
  `WaiveAuditWatermark` (`commit_sha`, `audited_at`, `waivers_audited`,
  `catchup_remaining`, `catchup_covered`) round-trips through
  `waive-audit-watermark.json` via `load_watermark`/`save_watermark`,
  both returning a typani `Result` keyed on `WaiveAuditWatermarkError`
  (`NotFound` vs `Malformed` vs `WriteFailed` -- kept distinct so a
  genuinely unreadable watermark is never treated as "never audited").
  `watermark_path`/`utc_now` are the two small seams (path resolution,
  injectable clock) the rest of the module builds on.
  **T-2721: this file is GIT-TRACKED, deliberately, not `.frob/`
  scratch.** It used to live at `.frob/waive-audit-watermark.json` --
  since `.frob/` is repo-gitignored, that state was per-checkout only,
  and agents run this audit from DISPOSABLE worktrees
  (`.claude/worktrees/<id>`) that get deleted on cleanup. This was
  caught live, not theoretically: T-1614's own first pass classified 100
  waiver directives inside a worktree; the primary checkout's own copy
  of the watermark was simply ABSENT, `waive-audit scan` from the
  primary reported `not_covered=967` before the worktree's file was
  copied across by hand and `not_covered=867` after -- proof the 100
  classifications were genuinely gone from everywhere the fleet actually
  looks, and silently so (nothing warned that progress was about to be
  discarded; the next scan would simply have re-reported the old
  denominator). A periodic, incremental audit over a large backlog only
  works if progress accumulates ACROSS passes -- a gitignored,
  per-checkout watermark defeated that on every single agent-run pass.
  The fix moved the watermark to a plain file at the repo ROOT
  (`waive-audit-watermark.json`, `.gitignore`'s `!`-negated the same way
  `rapid-debt.jsonl` already is) and made `save_watermark` commit it --
  in `root` itself, and, when `root` is a worktree, ALSO mirror-and-
  commit it onto the primary checkout immediately (reusing `frob.
  tickets._land._resolve_primary_checkout`/`frob.tickets._leases.
  refuse_if_land_in_progress`, the same primitives `frob.app.
  ticket_runner._ledger_mirror`'s T-2563 worktree-ledger-mirror shape
  already established for exactly this "a worktree edit must be visible
  fleet-wide immediately, not only once its ticket lands" need).
  `waive-audit` is `NOT_TICKET_SCOPED` in `LEDGER_VERB_STRATEGY`, so
  without this mirror a worktree's watermark commit would never reach
  `main` on its own at all, even after that worktree's ticket eventually
  lands. Both halves (commit in `root`, mirror onto `primary`) are
  best-effort and never raise: a git/lock failure degrades to a loud
  `_log.error` (matching `_ledger_mirror._log_mirror_unavailable`'s
  posture) rather than failing the audit pass -- the watermark write to
  disk already succeeded by that point, and refusing the call would
  throw away real, already-computed audit progress over a git plumbing
  hiccup. **Do not "clean this up" back into `.frob/` or `.gitignore`**
  -- that reintroduces exactly the silent-loss failure mode this section
  documents; if the root-level file feels like clutter, the fix is a
  better location for tracked state, never an untracked one. T-2485:
  `catchup_covered` is the set of `"file:line:rule"` waiver identities
  (`_waiver_identity` in the runner module) a BANKED PARTIAL catch-up
  pass has already reviewed -- it lets the next bounded scan's window
  advance past them instead of re-offering the same leading slice of the
  corpus forever, and it is cleared the moment `catchup_remaining` hits
  0 (the covered-set means nothing once catch-up mode itself ends).
- `frob.app.ticket_runner._waive_audit` -- the CLI-facing runner.
  `run_scan` is the read-only `scan` subcommand: it determines the scan
  set (incremental-since-watermark, or a bounded first-run/continuing
  catch-up pass capped at `_CATCHUP_BOUND`, skipping any waivers already
  recorded in `catchup_covered`) and returns a `WaiveAuditScanReport`
  carrying an `AuditVerdict` -- `WATERMARK_UNREADABLE` /
  `NO_NEW_WAIVERS` / `NEEDS_REVIEW` / `CLEAN` /
  `PARTIAL_PROGRESS_BANKED`, deliberately kept as DISTINCT states (a
  `scan` can never itself report `CLEAN` -- only `complete` can, since
  only a human/agent reviewer's classification against T-1614's own
  rubric can establish that; and neither `scan` nor a plain `complete`
  can ever report `PARTIAL_PROGRESS_BANKED` -- only `complete --partial`
  can, and it can NEVER report `CLEAN`, even when the reviewed batch
  itself had zero cop-outs). `complete_pass` records a finished pass
  (refusing on a reviewed-count mismatch, and refusing an incomplete
  catch-up UNLESS `partial=True`) and advances the watermark to current
  HEAD via `frob.gitio`.
- T-2485: `complete --partial` (`complete_pass(..., partial=True)`) is
  the fix for a real gap T-1614's own first live pass against this
  repo's corpus (100 scanned, 857 not covered) surfaced -- before this,
  a bounded catch-up pass could NEVER bank progress: `complete_pass`
  refused unconditionally whenever `not_covered_count > 0`, and nothing
  ever wrote a watermark with nonzero `catchup_remaining`, so the only
  way to ever advance the watermark was reviewing the entire backlog in
  one sitting (exactly what bounding the pass to `_CATCHUP_BOUND` was
  meant to avoid). `--partial` is required explicitly, never inferred,
  so a caller cannot bank a partial pass by accident while believing
  they completed the audit; the resulting watermark's
  `catchup_remaining`/`catchup_covered` make a banked-but-incomplete
  pass structurally indistinguishable-from-complete impossible to
  produce (T-2391 fail-loudly doctrine).
- Each `ScannedWaiver` surfaced by `scan` names the file/line/rule/reason/
  follow_up a human/agent classifies per T-1614's original rubric (STILL
  NECESSARY AND HONEST / OBSOLETE / COP-OUT / PERMANENT BY DESIGN) --
  this module supplies the SCOPE and PERSISTENCE, not the judgment.
- T-2493: `find_collision_suspects(waivers, kept_violations, root=...)` --
  the SOUND half of "is a waiver inert", built after re-deriving (and
  rejecting) the exact reasoning that shipped once as T-1579's
  `_rule_has_live_finding` escape and deleted 55 live waivers ("the rule
  fired somewhere this run" does not prove the ONE waived site was
  re-examined). This function never reasons from absence at all: it
  flags a `frob:waive` only when a `GateReport.violations` (the KEPT,
  UNSUPPRESSED set) entry for the SAME rule sits in the SAME
  repo-relative file -- a direct, present counter-example that the
  waiver failed to suppress an active finding, the general form of the
  two real matching bugs this repo has found and fixed this way (T-2314
  absolute-vs-relative path shape, T-2438 hand-rolled C++ symref
  spelling). `CollisionSuspect` is the reported shape. Deliberately
  disclosed blind spot: a waiver whose site has ZERO current violations
  ANYWHERE (a hardened guard behaving exactly like a genuinely inert
  waiver) is invisible to this check by construction -- closing that
  gap needs the per-site analysis-coverage proof `frob.gates.
  _coverage_sites` (T-1921/T-1943) only provides for five gate families
  and was itself deliberately left unwired everywhere; extending it into
  a general per-waiver verdict is a materially larger, multi-file
  capability outside this ticket's single-file scope. Pure/side-effect-
  free (report-only, per the T-2493 brief: never mutates a waiver, never
  gates a check or land -- see the function's own T-2493 section
  docstring in `_waive_audit.py` for the full incident history and
  reasoning).
- T-2496: `frob ticket waive-audit scan --check-collisions` wires
  `find_collision_suspects` into the CLI, opt-in and additive only.
  `_render_collision_suspects` runs a fresh, unscoped `frob check` gate
  pass (so expect this to cost roughly what a full `frob check` costs --
  it is not the default), feeds the resulting `GateReport.violations`
  plus the current waiver corpus to `find_collision_suspects`, and
  prints whatever it flags as a SEPARATE report section below `scan`'s
  own watermark-scoped output -- never folded into `scan`'s
  `AuditVerdict`, never mutates a waiver, and never changes this
  command's own exit status; a reported collision is input for a
  human/agent's own T-1614 classification pass. `find_collision_
  suspects`'s disclosed blind spot (a waiver whose site has ZERO current
  violations anywhere is invisible to this check) is restated in the
  flag's own `--help` text and in this command's rendered output, not
  hidden. Deliberately did NOT add an "and clean up"/auto-drop mode in
  this wiring -- that decision needs its own separate review, per the
  T-2493 brief this ticket inherited.
- T-2740: `classify_waiver_liveness(waiver, report, root)` -- the missing
  half T-2493's own docstring names above: NOT "is this waiver honest",
  NOT "does an active violation collide with it", but "does this
  waiver's own RULE even scan the FILE it sits in at all". T-2719 found
  11 `frob:waive RENDER001` directives in `.claude/hooks/` and `scripts/
  fleet_status.py` that were individually honest AND collision-free
  (nothing to collide with, since RENDER001's scan pathspec was
  hardcoded to `src/frob` and never reached those files) -- T-1614's own
  audit classified all 100 directives it reviewed as "still necessary
  and honest", 11 of which were provably doing nothing. Three states,
  deliberately not the same three T-1614's honest/cop-out rubric uses:
  `WaiverLiveness.NECESSARY` (this run's own `GateReport.waived` --
  `_apply_waivers`'s real output, a direct observation -- shows the
  waiver actively suppressing a violation), `INERT` (the waiver's rule
  has a registered structural scan-membership predicate in
  `_LIVENESS_SCAN_CHECKERS`, e.g. RENDER001's own `render001_scans`
  re-exported from `frob.gates._render_lint` rather than re-hardcoded
  here, and the waiver's file falls outside it), and `UNVERIFIED` (the
  honest default -- deliberately never "obsolete": claiming a finding no
  longer reproduces from one run's absence is exactly the T-1579
  `_rule_has_live_finding` reasoning that deleted 55 live waivers, and
  this module does not repeat it; a real OBSOLETE verdict needs a
  by-hand synthetic-diff measurement per this repo's own waiver-removal
  discipline, e.g. T-2739's own). `frob ticket waive-audit scan
  --check-liveness` wires this into the CLI, same report-only, additive,
  opt-in posture as `--check-collisions` immediately above (its own
  fresh unscoped `frob check` gate pass, never gates this command's exit
  status, never mutates a waiver) -- `_render_waiver_liveness` prints
  necessary/inert/unverified counts plus every INERT site by name, and
  frames an INERT verdict explicitly as a lead on the GATE's own scan
  pathspec too, not only the waiver (exactly how T-2719 was found: by
  widening a scan, not by deleting a waiver).

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
  `in_progress`=cyan, `planned`=yellow, `queued`=dim, `dropped`=magenta,
  `blocked`/`failed`=red). `dropped` is deliberately neither dim nor red
  (T-2084): dim is `queued`, and confusing terminal work with work still
  waiting to be picked up is the one collision that matters here, since a
  drop cannot be undone -- `frob ticket requeue` refuses it. Red stays
  reserved for states that want attention.
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

T-2486: the unscoped gate run itself is the risky span for `--json`
output, so it runs inside `_guard_json_stdout_writes()` (T-2492: now
`src/frob/app/_json_guard.py`, imported rather than defined locally in
`check_runner.py`) -- the guarded `with` block closes before this
function's own `_print_census`/JSON payload write, so a stray write
anywhere in that whole-tree gate run reaches stderr, never corrupts the
report.

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
