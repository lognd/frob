# frob CLI command tiers

T-0580 audited actual CLI usage (this session, 1035 CLI events) to decide,
per command, whether it earns its ongoing doc/test/export/coverage
maintenance tax. Full per-runner docs stay in docs/modules/app.md#runners
and each command's own docs/commands/*.md page; this page is the tier
ledger, not a duplicate of flag semantics.

## Navigation commands -- regrouped under `frob explore` (T-1238, supersedes T-0580/T-0802)

`frob map`, `frob outline`, `frob xref`, and `frob docs --search` were
deprecated 2026-07-23 (T-0580 decision, T-0802 tracking ticket) on the
theory that navigation is owned by Serena/native editor tools in agentic
use, not frob's own CLI. The 2026-07-29 user directive rescinded that
sunset: `frob` is intimidating with a flat ~35-entry top-level surface,
and the fix is grouping related verbs together, not deleting the ones
telemetry showed low top-level use for. T-1238 is the CLI regrouping
epic this section now tracks; `docs/design/cli-regrouping.md` is its
taxonomy design doc.

All four navigation members now also live as `frob explore` subcommands
(`frob explore map`/`outline`/`xref`/`docs-search`) -- un-deprecated, no
`frob:deprecated` directive, no sunset warning. Their standalone
top-level forms (`frob map`, `frob outline`, `frob xref`, `frob docs
--search`) are kept as PERMANENT aliases onto the identical runner code,
not a time-boxed transition shim -- every old invocation keeps working
unchanged, indefinitely.

- `frob map` / `frob explore map` -- src/frob/app/map_runner.py (docs/commands/map.md)
- `frob outline` / `frob explore outline` -- src/frob/app/outline_runner.py (docs/commands/outline.md)
- `frob xref` / `frob explore xref` -- src/frob/app/xref_runner.py (docs/commands/xref.md)
- `frob docs --search` / `frob explore docs-search` -- src/frob/app/docs_runner.py's
  `_run_search`, reused directly by `frob.app.explore_runner._run_docs_search`;
  the bare `frob docs <path>` extract path and `--overview` are unaffected
  by this regrouping -- `frob explore` covers `--search` specifically

## Exports-consumers surface (T-0858)

2026-07-23 reevaluation of the navigation-command sunset above, before
T-0802 executed it: telemetry backed deprecating the standalone `frob
xref` porcelain (zero organic invocation), but the underlying question it
answers -- "who imports this symbol" -- is recurring, gate-driven work
(T-0600/T-0601/T-0588 all leaned on it), and grep/ad-hoc search answers it
wrong in both directions (misses real references, false-positives on
comment/prose mentions). Decision at the time: keep `frob xref`
deprecated per its existing sunset, and fold the surviving capability
into the `exports` library surface instead of deleting it with the
porcelain. T-1238 (2026-08) superseded that sunset -- `frob xref` is
un-deprecated and regrouped under `frob explore xref` (previous section)
-- but `exports_consumers` remains the narrower, gate-driven answer for
"import consumers only" and is unaffected by this reversal.

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

A `frob exports --consumers` CLI flag now exists (T-0858,
`src/frob/_cli_parsers/_core.py`), wired into `frob exports`'s parser/
config/runner alongside the library-only surface (`from frob.exports
import exports_consumers`) this section originally shipped with.
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

**T-2805: each successful crate build attests itself to `stale_natives`.**
`maturin --release` is a deterministic build -- rebuilding unchanged
source always reproduces byte-identical output. `frob.strata.
_native_staleness.stale_natives`'s own T-0513 content-digest check
(docs/modules/testing.md#public-api) used this fact against itself: once
its content-digest branch latched (artifact bytes unchanged, source
digest changed since the last observation), a genuine rebuild could never
clear it, because "genuinely rebuilt, byte-identical output" and "never
rebuilt at all" are indistinguishable from mtime/bytes alone -- the tool's
own documented remediation (`frob natives build`) could not fix what it
broke. `build_natives` now calls `record_native_build_attempt` immediately
after each crate's `maturin develop` exits ZERO (never on a failed build),
which records the source digest that build ran against; `stale_natives`
checks that record before latching and refreshes its stamp when it
matches, instead of re-flagging a rebuild that already, genuinely,
happened. A bare `touch` on the artifact still latches exactly as before
-- only a real, exit-zero `build_natives` call can ever populate that
record. See docs/modules/testing.md#public-api for
`record_native_build_attempt`/`stale_natives`'s own side of this.

## frob coverage (T-1525)

`frob coverage` is the user-facing CLI verb over
`frob.testing._coverage_refresh.native_coverage_refresh` (T-1516): the
frob-native, cross-platform (Linux/macOS/Windows, no `Makefile`/shell
dependency) coverage refresh orchestration T-1205 introduced as a library
function with no entrypoint of its own. Default (no flag): a touched-set
incremental refresh through `run_coverage_wait`'s existing single-flight
lock and freshness check (T-1095/T-1516/T-1126) -- a caller racing another
worktree on the same tree digest adopts its settled result instead of
re-running. `--full`: bypasses that freshness check entirely and calls
`native_coverage_refresh(..., full=True)` directly, for a caller who
explicitly wants a whole-suite run regardless of what is already cached.
`--base REF` (T-1572, the old `make coverage-fast BASE=<ref>` shell
recipe's replacement): overrides the git ref the touched-set incremental
refresh diffs against (default `HEAD`), threaded through `run_coverage_
wait`/`native_coverage_refresh`'s own `base` kwarg -- has no effect with
`--full`, which always runs the whole suite regardless of any touched-set
base.

```
frob coverage            # touched-set incremental refresh (or a no-op if already fresh)
frob coverage --full     # whole-suite run under coverage, unconditionally
```

**Decision: `frob check` does not auto-trigger this refresh, for any
caller, agent or not (T-1525).** T-1516's own Done report already ruled
this out for a dispatched worktree agent specifically (`FROB_AGENT=1`,
`docs/guides/agent-playbook.md` section 3b's foreground-timeout contract
-- auto-spawning a coverage refresh from inside every `frob check` call
would reintroduce the exact auto-background stall class that section
exists to prevent). T-1525 had to settle the OTHER half: should a
non-agent (human/CI) `frob check` invocation, where that specific
constraint does not apply, auto-trigger a refresh anyway? The answer is
still no, for a reason that is not agent-specific: running the test suite
(even touched-set-scoped) is a categorically different, much slower and
more failure-prone operation than every other gate `frob check` runs, and
hiding it as an implicit side effect of a command whose whole contract is
"tell me what's wrong, fast" would surprise every caller, not just a
dispatched agent watching a clock. `frob check` keeps reporting
staleness via TEST011/TEST017 (`docs/modules/gates.md`'s "TEST011/TEST017"
section) rather than fixing it; `frob coverage` (this verb) and `frob
test --wait-coverage` (`frob.app.test_runner`'s existing, already-wired
call into `run_coverage_wait`, T-1516) are the two places a refresh is
expected to run from, both explicit, neither hidden inside a check.

## Plumbing tier -- kept, unchanged (T-0580)

`frob parse`, `frob exports`, `frob gitlog`, and `frob serve` were
evaluated in the same audit and kept as-is: `parse` is an adapter used by
pipelines, `exports` powers the `exports` gate stage, `gitlog` powers
`frob stats`/changelog generation, and `serve` (MCP) is valuable for
no-shell contexts even though it goes unused when an agent has a shell.

## `frob doctor`: global-vs-local frob binary skew (T-1719)

`frob doctor` (`src/frob/doctor.py`) reports whether the on-PATH global
`frob` binary agrees with this checkout's own `uv run frob` version. The
motivating measurement: `frob` on PATH read 0.184.0 while this repo's
`uv run frob` was 0.361.0 -- 177 versions apart -- with nothing surfacing
the gap short of a human running both `--version` by hand. Every gate
number and ledger splice the global binary produces against this tree is
wrong while the two disagree; this is the same class of incident
`stale_binary_warning` (`docs/modules/app.md#entry-point`, T-1218) already
covers for a declared `min_frob_version` floor violation, but reports ANY
disagreement, floor or no floor -- even a NEWER global binary reading an
older checkout can disagree on gate logic.

`DoctorReport.global_binary` (a `GlobalBinarySkew`) carries the raw
`global_version`/`local_version` strings and a `skewed` bool; `skewed=True`
makes the overall report `healthy=False` and folds a remediation line
naming both versions and the exact fix (`uv run frob ...`, or `uv tool
upgrade frob` to reconcile) into `DoctorReport.remediation`. An
unmeasurable comparison (no global `frob` on PATH at all) reports
`global_version=None, skewed=False` and never counts against `healthy` --
absence of a comparison is not evidence of skew.

This mirrors the measurement `.claude/hooks/frob-suggest.py`'s own
`_frob_version_skew` already performs to nudge a raw `frob` invocation
(same spawn-strip-compare shape) -- that hook is a standalone script with
no `frob` package import available to it, so this is a parallel
implementation of the identical check rather than a shared function call.
Fully unifying the two surfaces (e.g. having the hook shell out to a
`frob doctor --json` call and read this field back) is a larger change to
the hook-loader boundary, out of this ticket's own scope -- see the
Done report for the follow-up ticket filed for that.

## `frob claude sync` (T-1808)

T-1719 identified two more items past the binary-skew check above: (1)
fold `.claude/hooks/sync-claude-config.py` into a real frob verb, and (2)
gate its drift in `frob check` (T-1809). This section covers (1).

`frob claude sync [--check]` (`src/frob/app/claude_runner.py`) materializes
this repo's git-tracked Claude config (hooks, `docs/guides/agent-
playbook.md`) out to the operator's `~/.claude/`, replacing the manual
`python3 .claude/hooks/sync-claude-config.py` invocation as the frob-native
entry point. `--check` reports drift without writing and exits 1 if
anything differs or a managed source is missing; the default writes each
destination behind a do-not-edit banner, atomically, and never syncs
`~/.claude/` back into the repo.

NO DUPLICATION: `.claude/hooks/sync-claude-config.py` stays the single
canonical, dependency-free (stdlib-only) implementation of the plan/write
logic, because the `SessionStart` hook in `.claude/settings.json` invokes
it with a bare `python3` before any `frob` venv is necessarily on
`PYTHONPATH`. `frob claude sync` is a thin adapter (`frob.app.
claude_runner`) that loads that script by file path (its hyphenated name
blocks a normal `import`) and calls its public `MANAGED`/`plan()`/`main()`
directly -- there is exactly one implementation, not two that can drift
apart from each other.

STANDING DESIGN DIRECTIVE this verb answers to: "a command requires
knowledge of the command." `frob claude sync` is the MECHANISM, not the
user-facing answer -- an operator who never knew this verb existed still
gets told about drift, because `frob.app.claude_runner.drift_warning` is
wired into `frob.__main__.main()` next to `stale_install_warning`/
`stale_binary_warning` (`docs/modules/app.md#entry-point`): every `frob`
invocation runs a cheap read-only drift check and prints one loud line to
stderr naming the exact fix if anything has drifted. Detection is
automatic and surfaced where an operator already looks; the WRITE stays
this explicit verb on purpose -- auto-writing into `~/.claude/` on every
invocation would be a destructive-ish mutation of the operator's home
directory from a command run constantly, exactly the "stupid consequence"
the directive's own escape clause calls out. T-1809 adds the pre-land
enforcement half of the same signal as a `frob check` gate.

## `frob ticket migrate --to v2` (T-1492)

`frob ticket migrate` collapses legacy `tickets/*.md` into a single
`tickets.md` ledger by default (unchanged). Passing `--to v2` instead
dispatches to `migrate_v1_to_v2` (`src/frob/tickets/_store.py`, T-1259):
a one-shot, reversible migrator that writes a monofile-mode ledger's
tickets into per-ticket `tickets/T-####/ticket.md` (+ `done-report.md`,
+ moved attachments) WITHOUT deleting `tickets.md`/`tickets-archive.md`
in the same call. See `docs/design/ledger-v2.md` section 7 for the full
migration design and `docs/modules/tickets-data-storage.md#migration-to-v2-t-1259-docsdesignledger-v2md-section-7`
for the storage-internals writeup.

## frob ack

`frob ack [ref ...] [--facet {sig,body,doc}] [--path DIR] [--reason TEXT
| --reason-file PATH] [--list]` re-verifies one or more `path::Qualified.
Name` refs against their current graph-recorded digest, clearing the
drift the DRIFT family gates would otherwise flag -- `--facet` narrows
which digest (signature, body, or doc) is being re-verified when a ref
has drifted on more than one facet independently; `--reason`/
`--reason-file` is required and records WHAT was re-verified and why the
doc is still true (the file form exists for the same shell-safety reason
`docs/guides/agent-playbook.md` section 1d documents for ticket prose).
`--list` shows the append-only ack audit trail instead of acking
anything -- read-only, no ref required.

## frob agent

`frob agent env WORKTREE-PATH` prints the two `export` lines a dispatched
agent's shell needs before running `pytest`/`frob` directly against a
worktree: `FROB_WORKTREE=<path>` and `FROB_AGENT=1` (T-0574) -- exactly
the env `docs/guides/agent-playbook.md` section 1b's `eval "$(frob agent
env ...)"` recipe sources. `env` is currently the only subcommand.

## frob debt

`frob debt [--path DIR] [--json]` reports open technical-debt markers
(`frob:todo`/deprecation entries and similar) under `path` (default: the
repo root); `--json` swaps the printed report for a machine-readable
one. Measurement only -- see `frob deprecated` below for the related,
but distinct, expiring-deprecation view.

## frob deprecated

`frob deprecated [--path DIR] [--json]` reports every live
`frob:deprecated`-style marker under `path` (default: the repo root)
along with its expiry state, the same data REL001's open-debt half
checks at land time; `--json` swaps the printed report for a
machine-readable one.

## frob design

`frob design {sys,registry,docs,graph,exports} ...` groups the
design-knowledge subcommands under one umbrella: `sys` applies/queries
the strata design model (plan, doc, export, ...); `registry` reads the
unified design-knowledge registry (T-0407); `docs` extracts docstrings
from a file/symbol in overview form (for full-text search across `docs/`
use `frob explore docs-search` instead, not this); `graph` is the same
obligation-graph build/query/why surface `frob graph` (see above)
exposes directly, reachable here too for discoverability; `exports`
generates a package's `__init__.py` from its public symbols. Each
subcommand has its own `--help`; this entry exists so <!-- frob:waive DOC006 reason="frob design ... is self-referential DOC012 prose about this very entry existing, not a literal invocation -- the trailing ... is not real CLI syntax" -->`frob design ...`
itself resolves to something documented, per DOC012.

## frob docs

`frob docs [PATH] [symbol] [--overview] [--search QUERY] [--json]
[--sync-commands]` inspects a file or symbol's documentation coverage:
`frob docs` given a plain path (and optionally a symbol) shows relevant `docs/` headings and
summaries touching that path/symbol; `--overview` is the same view
without narrowing to a symbol; `--search QUERY` full-text searches
`docs/` (also reachable as `frob explore docs-search`); `--sync-commands`
regenerates this very file's "Generated command reference" block (below)
from the live argparse registry (T-1011) instead of inspecting anything
-- the two modes are mutually exclusive with `path`/`symbol`.

## frob explore

`frob explore {map,outline,xref,docs-search} ...` groups the
navigation/read-only-inspection subcommands (T-1238, supersedes T-0580/
T-0802): `map` prints the whole-project structural map (symbols + line
counts); `outline FILE` prints one file's structural skeleton (classes,
functions, line numbers); `xref SYMBOL` finds a symbol's definition plus
every referencing file through the call graph -- the preferred
alternative to a raw recursive `grep` for a known symbol name, per this
repo's own `frob-suggest` hook; `docs-search QUERY` full-text searches
`docs/`. See "Navigation commands" above for the historical regrouping
context.

## frob ops

`frob ops {release,natives,doctor,clean,fleet,deploy,scaffold,gitlog,
stats} ...` is a second-tier umbrella grouping operational subcommands
that are each also independently useful; most (`clean`, `fleet`,
`stats`) are documented in their own dedicated sections elsewhere in
this file or under `docs/modules/`. The remaining ones reachable only
through this umbrella: `release` computes the mechanical semver bump
from the public-API graph (REL001, land-owned per
`docs/guides/agent-playbook.md` section 4b -- never run by hand in a
worktree); `natives` builds every declared `[[native]]` crate (T-0864,
see "frob natives build" above); `doctor` verifies `frob_core`/
`strata_core` are actually installed (see "`frob doctor`" above);
`deploy` compiles `std.host` manifests into install/status/uninstall
bash; `scaffold` scaffolds a new project from a template.

## frob pool

`frob pool {snapshot,clear} ...` manages a rule's ratchet baseline pool:
`snapshot --key KEY RULE` baselines a given key as WARN for `RULE`, so
anything else of that rule still reports at error severity (a targeted
escape hatch for a known, accepted finding rather than a blanket
waiver); `clear --key KEY RULE --reason TEXT` removes one baselined key
from the pool, always requiring a reason -- the same "every ratcheted
finding eventually needs a disposition" posture `docs/guides/
agent-playbook.md` section 7 describes for `frob:waive`.

## frob profile

`frob profile {show,downgrade} ...` inspects and manages the RAPID/
standard land-profile auto-ratchet (T-1575, see the "profile: ... is
running RAPID" warnings `frob ticket land` prints): `show` reports the
configured profile, the effective profile after any auto-ratchet, and
any persisted ratchet state; `downgrade` explicitly clears a persisted
rapid-to-standard auto-ratchet -- the ONLY way back once ratcheted,
never automatic.

## `frob status` (T-2911)

`frob status [--path DIR] [--json] [--only GATE] [--tickets]
[--no-tickets]` is a delta-first movement summary: findings HEALED/
INTRODUCED since the last `frob check --stamp-baseline` stamp,
verification lag against the T-1686 watermark, and (opt-in, see below)
ticket landing velocity -- built so a large absolute finding count does
not read as "no progress" on its own (a newcomer seeing a four-figure
`frob check` warning count has no way to tell that number is shrinking
without this). Default output is fast: well under a second on this
repo's own tree.

Reuses three existing stores as its single sources of truth, adding no
parallel counter: `.frob/baseline` (`frob.gates.load_baseline`/
`is_baseline_stale`/`violation_fingerprint` -- the exact identity `--delta`
already uses), `frob.app.verify_runner.build_status` (the same function
`frob verify status` calls), and, when requested, `frob.tickets.
ticket_flow` (the same function `frob ticket flow` calls).

**Findings-movement honesty rule**: a missing OR stale baseline reports
`measured: false` with an explicit reason, never a fabricated delta --
motivated directly by a real incident where a 53-commit-stale watermark
produced a confident-but-wrong result elsewhere in this repo's own
history. `--only` selects which gate(s) to scan for the current side of
the diff (default: the same `gates-fast` stage group `frob check --only
gates-fast` already defines).

**Ticket movement is opt-in (T-2950)**: `ticket_flow` mines the WHOLE
ledger's git history -- one `git log` subprocess pair per ticket id,
active AND archived -- and measured at 5m41s wall clock on this repo's
own ~1000-ticket archive, well past a newcomer-facing surface's 200s
foreground budget. `frob status` therefore does NOT compute this section
by default; pass `--tickets` to include it (and accept the wait on a
large/old repo). The default human/JSON output still reports this
section explicitly as "not measured" (naming `--tickets` as the remedy),
never a silent omission or a fabricated zero. `--no-tickets` is a
deprecated no-op kept only so a pre-T-2950 script/CI invocation that
already passes it does not break.

**Baseline-locks section (T-2999)**: always populated (no opt-out flag,
unlike ticket movement -- three `git log`/`git rev-list` calls, well
under a second) -- one line per `frob.gates._lock_producer.KNOWN_LOCKS`
entry (`frob-coverage.lock.json`, `frob-ratchet.lock.json`,
`frob-deprecated-baseline.lock.json`), showing each lock's measured
producer verdict: `FRESH`, `PINNED` (with its stated reason),
`ABANDONED` (unpinned, with the code churn since last stamp that makes
the case), or `UNMEASURED` (no committed lock, or git history for it
could not be read). See docs/modules/gates.md#baseline-lock-producer-staleness-t-2999
for the full mechanism, including the LOUD `TEST012` gate finding a
genuinely `ABANDONED` coverage-lock producer also fires.

## frob quality

`frob quality {check,test,dup,arch,bind,cycle,mutate,perf} ...` is a
second CLI surface over several gates/tools also reachable through their
own top-level subcommands (`frob dup`, `frob arch`, `frob mutate`, `frob
perf`, all documented in their own sections above): `check` runs an
aggregated quality gate (ruff, ty, cycle/dup/arch/bind/exports) with
errors surfaced first, sized to hand directly to a subagent; `test`
selects and runs tests for the touched set (or `--all`); `bind` verifies
binding declarations match source signatures; `cycle` detects dependency
cycles. Prefer this umbrella when you want several quality checks
narrated together; prefer the standalone top-level command when you want
just one.

## frob registry

`frob registry {audit,add} ...` manages the design-knowledge registry
`frob design registry` (above) reads: `audit` reports per-registry-file
disposition accounting (handled/deferred/out-of-scope/unaccounted);
`add` appends a new pending entry to a registry file's universe corpus,
the T-0429 exhaustive-research emit path.

## frob test

`frob test [path] [--all] [--fuzz] [--collect] [--wait-coverage] [--base
REF] [--lang L] [--fallback {package,suite,warn}] [--json]` selects and
runs tests for the touched set under `path` (or the whole suite with
`--all`); `--fuzz` property-tests fuzz-obligated pydantic models and
stamps the result (T-0002); `--collect` drops and rebuilds the pytest
collection cache, then exits (T-0333) -- the fix for a fresh worktree's
`ModuleNotFoundError` per `docs/guides/agent-playbook.md` section 1
step 2; `--wait-coverage` blocks in the foreground, single-flight across
concurrent callers, until the coverage stamp is fresh, then exits -- the
definitive-result alternative to backgrounding `make coverage` and
stalling on a notification that structurally cannot arrive (T-0322, see
section 6b of the playbook); `--base REF` sets the diff base for
touched-set selection; `--fallback` controls what happens when the
touched set cannot be resolved (fall back to the whole package, the
whole suite, or just warn).

## frob worktree

`frob worktree {sweep,remove,release-lease} ...` manages dispatched-agent
git worktrees: `sweep [path] [--dry-run] [--min-age HOURS]` is the
lease-aware bulk cleanup `docs/guides/agent-playbook.md` section 12b
mandates over a raw `git worktree remove` loop (T-0836); `remove` safely
removes a single worktree with T-1739's liveness check (T-1779); `release-
lease TICKET-ID` releases one ticket's cross-worktree lease, but only if
it is confirmed orphaned -- its recorded worktree path no longer exists
(T-1779 finding 7).

## Generated command reference (T-1011)

<!-- frob:invariant INV-045 -->

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
| `frob claude` | sync this repo's tracked Claude config to ~/.claude/ (T-1808) |
| `frob clean` | remove build/test/cache artifacts (tiered, dry-run by default) |
| `frob coverage` | refresh coverage.xml / the coverage stamp via native_coverage_refresh (T-1516/T-1525) -- touched-set incremental by default |
| `frob cycle` | detect dependency cycles |
| `frob debt` | list outstanding frob:debt entries (rule, site, ticket, until) |
| `frob deploy` | compile std.host manifests into install/status/uninstall bash |
| `frob deprecated` | list outstanding frob:deprecated entries (symref, since, sunset, ticket, status) |
| `frob design` | design-knowledge surfaces: sys/registry/docs/graph/exports grouped under one verb (T-1568) |
| `frob docs` | extract docstrings or search docs/ for a file/symbol |
| `frob doctor` | verify native extensions (frob_core, strata_core) are installed |
| `frob dup` | detect duplicate/clone code segments (Type 1 exact, Type 2 renamed) |
| `frob explore` | navigation: map/outline/xref/docs-search grouped under one verb (T-1238) |
| `frob exports` | generate __init__.py from public symbols in a package directory |
| `frob fleet` | cross-repo status, gate rollup, and ticket routing over a fleet.toml manifest of sibling repos (T-0573) |
| `frob fmt` | canonicalize frob: directive comment line-wrapping (T-0441) |
| `frob format` | ruff check --fix + ruff format, write mode (T-2251) |
| `frob gitlog` | summarize git history by type/granularity (conventional commits) |
| `frob graph` | obligation graph: build cache, query symbols, explain drift |
| `frob map` | show whole-project structural map (symbols + line counts) -- also available as `frob explore map` (T-1238) |
| `frob mutate` | mutation testing: perturb a file, see which mutants survive |
| `frob narrative` | migrate a T-#### narrative comment block |
| `frob natives` | build declared [[native]] crates (T-0864: frob-owned maturin develop, shared CARGO_TARGET_DIR) |
| `frob ops` | release/fleet/infra plumbing: release, natives, doctor, clean, fleet, deploy, scaffold, gitlog, stats (T-1569) |
| `frob outline` | show structural skeleton of a file (classes, functions, line numbers) -- also available as `frob explore outline` (T-1238) |
| `frob parse` | parse tool output (pytest/ruff/ty/clang/junit) into compact summary |
| `frob perf` | profile a command/test suite and inspect its heat-map |
| `frob pool` | ratchet-pool baseline management (T-0569): warn-rule findings frozen as a tracked baseline, new findings error |
| `frob profile` | development profile (rapid/standard/fortress) status and the one-way auto-ratchet's explicit downgrade (T-1575) |
| `frob quality` | correctness/hygiene gates: check/test/dup/arch/bind/cycle/mutate/perf grouped under one verb (T-1567) |
| `frob refactor` | transactional symbol move/rename/split |
| `frob registry` | unified design-knowledge registry (T-0407) |
| `frob release` | mechanical semver from the public-API graph (REL001) |
| `frob scaffold` | scaffold a new project from a template |
| `frob serve` | MCP stdio adapter exposing frob's enforcement queries as tools |
| `frob stats` | delivery measurement: queue health + commit cadence |
| `frob status` | delta-first movement summary: findings burned/introduced since the last baseline, verification lag, ticket landing velocity -- reuses frob check --stamp-baseline/frob verify status/frob ticket flow's own data, invents no new counter |
| `frob sync-skills` | bidirectionally sync agents/ and skills/ into ~/.claude (T-2241) -- replaces the old Makefile sync-skills: bash recipe |
| `frob sys` | strata design-model applications (plan, doc, export, ...) |
| `frob test` | select and run tests for the touched set (or --all) |
| `frob ticket` | the statically-checkable ticket queue |
| `frob verify` | the T-1686 unverified window: depth/age/quarantine status, force a drain, explain an attribution, dispose a quarantined finding |
| `frob vet` | dependency-vetting: lockfile allow conformance, quarantine, typosquat, lifecycle scripts, osv advisories |
| `frob worktree` | manage dispatched-agent git worktrees (T-0836) |
| `frob xref` | find where a symbol is defined and every file that uses it -- also available as `frob explore xref` (T-1238) |

<!-- frob:generated-end cli-commands T-1011 -->
None of the four (`map_runner.py`, `outline_runner.py`, `xref_runner.py`,
`docs_runner.py`) carry a `frob:deprecated` directive any more -- T-1238
removed it from all four when they regrouped under `frob explore`
(section above).
