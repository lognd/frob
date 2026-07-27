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
None of these carry a `frob:deprecated` directive.
