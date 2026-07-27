# frob CLI command tiers

T-0580 audited actual CLI usage (this session, 1035 CLI events) to decide,
per command, whether it earns its ongoing doc/test/export/coverage
maintenance tax. Full per-runner docs stay in docs/modules/app.md#runners
and each command's own docs/commands/*.md page; this page is the tier
ledger, not a duplicate of flag semantics.

## Navigation commands -- DEPRECATED (T-0580)

`frob map`, `frob outline`, `frob xref`, and `frob docs --search` are
deprecated as of 2026-07-23, sunset 2026-10-01 (`frob:deprecated` on each
runner's `run`/`_run_search`, bound to T-0580). Rationale: across 1035 CLI
events in this session, map/outline/xref invocations were virtually all
their own test suites (pytest tmp paths) -- zero organic use by the
coordinator or the ~30 agents working this repo. Navigation is owned by
Serena and native editor tools in agentic use, not by frob's own CLI.

Each deprecated command keeps working, unchanged, until its sunset date;
every invocation now logs a WARNING naming the sunset date and pointing at
Serena/native navigation and T-0580. `frob check`'s DEPR003/DEPR004 gates
track the sunset window and escalate to an error once it passes
(docs/modules/gates.md).

- `frob map` -- src/frob/app/map_runner.py (docs/commands/map.md)
- `frob outline` -- src/frob/app/outline_runner.py (docs/commands/outline.md)
- `frob xref` -- src/frob/app/xref_runner.py (docs/commands/xref.md)
- `frob docs --search` -- src/frob/app/docs_runner.py's `_run_search`;
  the bare `frob docs <path>` extract path and `--overview` stay as they
  are -- this decision covers `--search` specifically

## Exports-consumers surface (T-0858)

2026-07-23 reevaluation of the navigation-command sunset above, before
T-0802 executes it: telemetry backs deprecating the standalone `frob xref`
porcelain (zero organic invocation), but the underlying question it
answers -- "who imports this symbol" -- is recurring, gate-driven work
(T-0600/T-0601/T-0588 all leaned on it), and grep/ad-hoc search answers it
wrong in both directions (misses real references, false-positives on
comment/prose mentions). Decision: keep `frob xref` deprecated per its
existing sunset, and fold the surviving capability into the `exports`
library surface instead of deleting it with the porcelain.

<!-- frob:describes src/frob/exports/__init__.py::ConsumerRef -->
<!-- frob:describes src/frob/exports/__init__.py::ConsumersResult -->
<!-- frob:describes src/frob/exports/__init__.py::exports_consumers -->

```python
# frob/exports/__init__.py
class ConsumerRef(BaseModel)
    file: str
    line: int
    context: str

class ConsumersResult(BaseModel)
    symbol: str
    consumers: list[ConsumerRef]
    def as_text(self) -> str
    def as_json(self) -> str

def exports_consumers(
    symbol: str, root: Path, *, lang: str | None = None,
) -> Result[ConsumersResult, ExportsError]
    # Reuses frob.xref.xref's parsed usages, then narrows to lines that
    # parse as an import statement -- real import-consumers only, not
    # every textual mention of the symbol name.
```

This is a library-only surface today (`from frob.exports import
exports_consumers`); no `frob exports --consumers` CLI flag exists yet --
wiring one into `frob exports`'s parser/config/runner is out of this
ticket's scope and tracked as a follow-on (see the drafted ticket below).
Re-check organic `frob xref` telemetry again at the 2026-10-01 sunset
before T-0802 executes it, per the caveat that most worktree telemetry
dies with worktree removal (absence-of-evidence there is weak).

## frob natives build (T-0864)

`frob natives build` is frob's own native-crate build subcommand: it reads
`frob.toml`'s `[[native]]` entries (`frob.testing._runners.load_natives`,
already existed for T-0333's collection fingerprinting) and, for each
declared RUST native with a matching crate directory on disk
(`strata_core` <-> `strata-core/Cargo.toml`, the same underscore/hyphen
convention `frob.strata._native_staleness` already checks), runs `maturin
develop --uv --release` against it. Every crate shares one
`CARGO_TARGET_DIR`, keyed off the clone's git-common-dir
(`frob.gitio.git_common_dir`) rather than the calling worktree's own path
-- T-0732's verified design, moved here from a per-repo Makefile recipe so
every repo declaring `[[native]]` crates gets the shared-cache mechanism
"for free" by using this subcommand, not by hand-copying Makefile logic
(T-0865 tracks the sibling scaffold-template + drift-check follow-on).
Concurrent builds from separate worktrees of the same clone are safe via
cargo's own target-dir file locking, not a new lock this subcommand adds.

<!-- frob:describes src/frob/natives/_build.py::NativesError -->
<!-- frob:describes src/frob/natives/_build.py::CrateBuildResult -->
<!-- frob:describes src/frob/natives/_build.py::BuildReport -->
<!-- frob:describes src/frob/natives/_build.py::build_natives -->
<!-- frob:describes src/frob/app/natives_runner.py::run -->

```python
# frob/natives/_build.py
class NativesError(ErrorSet):
    NoNatives, LoadFailed, NotAGitRepo, ExecDisabled

class CrateBuildResult(BaseModel):
    name: str
    crate_dir: str
    returncode: int
    stdout: str
    stderr: str
    @property
    def ok(self) -> bool  # returncode == 0

class BuildReport(BaseModel):
    cargo_target_dir: Path
    results: list[CrateBuildResult]
    @property
    def ok(self) -> bool  # all(r.ok for r in results)

def build_natives(root: Path) -> Result[BuildReport, NativesError]
    # Err only for an infra-level failure that stops the whole run before
    # any crate is attempted (no declared natives, unparseable frob.toml,
    # root not a git checkout, exec kill switch refused). A per-crate
    # build failure is recorded in the returned Ok(BuildReport) instead --
    # BuildReport.ok is False when any attempted crate failed. A missing
    # toolchain (no uvx/cargo on PATH) is a best-effort skip, matching the
    # old make core recipe's own posture -- not a hard failure.
```

This repo's own `Makefile` `core:` target is now the one-line shim `uv run
frob natives build` -- no cache logic lives in the Makefile anymore.

## Plumbing tier -- kept, unchanged (T-0580)

`frob parse`, `frob exports`, `frob gitlog`, and `frob serve` were
evaluated in the same audit and kept as-is: `parse` is an adapter used by
pipelines, `exports` powers the `exports` gate stage, `gitlog` powers
`frob stats`/changelog generation, and `serve` (MCP) is valuable for
no-shell contexts even though it goes unused when an agent has a shell.

## Generated command reference (T-1011)

Everything between the two marker comments below is written by `frob docs
--sync-commands` from the live top-level argparse registry (the same
`[[docblocks.commands]]`-configured factory DOC004/DOC005 already walk) --
never hand-edited. `frob check`'s DOC005 gate verifies this block stays
byte-fresh against a live regeneration (`generate_cli_command_table`,
`src/frob/gates/_docblocks.py`); a stale block is an ERROR, not advisory.

<!-- frob:describes src/frob/gates/_docblocks.py::CLI_COMMAND_TABLE_START -->
<!-- frob:describes src/frob/gates/_docblocks.py::CLI_COMMAND_TABLE_END -->
<!-- frob:describes src/frob/gates/_docblocks.py::generate_cli_command_table -->
<!-- frob:describes src/frob/gates/_docblocks.py::sync_cli_command_table -->

<!-- frob:generated-start cli-commands T-1011 -->

| Command | Description |
| --- | --- |
| `frob ack` | acknowledge current digests for one or more symbol refs |
| `frob agent` | print/export the dispatched-agent guard env (T-0574) |
| `frob arch` | arch analysis: long functions, god classes, coupling |
| `frob bind` | verify binding declarations match source signatures |
| `frob check` | aggregate quality gate: ruff, ty, frob cycle/dup/arch/bind/exports; errors first, easy to hand to subagents |
| `frob clean` | remove build/test/cache artifacts (tiered, dry-run by default) |
| `frob cycle` | detect dependency cycles |
| `frob debt` | list outstanding frob:debt entries (rule, site, ticket, until) |
| `frob deploy` | compile std.host manifests into install/status/uninstall bash |
| `frob deprecated` | list outstanding frob:deprecated entries (symref, since, sunset, ticket, status) |
| `frob docs` | extract docstrings or search docs/ for a file/symbol |
| `frob doctor` | verify native extensions (frob_core, strata_core) are installed |
| `frob dup` | detect duplicate/clone code segments (Type 1 exact, Type 2 renamed) |
| `frob exports` | generate __init__.py from public symbols in a package directory |
| `frob fleet` | cross-repo status, gate rollup, and ticket routing over a fleet.toml manifest of sibling repos (T-0573) |
| `frob fmt` | canonicalize frob: directive comment line-wrapping (T-0441) |
| `frob gitlog` | summarize git history by type/granularity (conventional commits) |
| `frob graph` | obligation graph: build cache, query symbols, explain drift |
| `frob map` | [DEPRECATED, sunset 2026-10-01, see T-0580] show whole-project structural map (symbols + line counts) |
| `frob mutate` | mutation testing: perturb a file, see which mutants survive |
| `frob natives` | build declared [[native]] crates (T-0864: frob-owned maturin develop, shared CARGO_TARGET_DIR) |
| `frob outline` | [DEPRECATED, sunset 2026-10-01, see T-0580] show structural skeleton of a file (classes, functions, line numbers) |
| `frob parse` | parse tool output (pytest/ruff/ty/clang/junit) into compact summary |
| `frob perf` | profile a command/test suite and inspect its heat-map |
| `frob pool` | ratchet-pool baseline management (T-0569): warn-rule findings frozen as a tracked baseline, new findings error |
| `frob registry` | unified design-knowledge registry (T-0407) |
| `frob release` | mechanical semver from the public-API graph (REL001) |
| `frob scaffold` | scaffold a new project from a template |
| `frob serve` | MCP stdio adapter exposing frob's enforcement queries as tools |
| `frob stats` | delivery measurement: queue health + commit cadence |
| `frob sys` | strata design-model applications (plan, doc, export, ...) |
| `frob test` | select and run tests for the touched set (or --all) |
| `frob ticket` | the statically-checkable ticket queue |
| `frob vet` | dependency-vetting: lockfile allow conformance, quarantine, typosquat, lifecycle scripts, osv advisories |
| `frob worktree` | manage dispatched-agent git worktrees (T-0836) |
| `frob xref` | [DEPRECATED, sunset 2026-10-01, see T-0580] find where a symbol is defined and every file that uses it |

<!-- frob:generated-end cli-commands T-1011 -->
None of these carry a `frob:deprecated` directive.
