# frob v1 CLI surface inventory (for the Rust v2 redesign)

Source of truth: <frob-v1> (branch dev), read-only.
Method: the live argparse tree was dumped by importing
`frob.__main__._build_parser` (243 parser nodes), then cross-checked
against `frob.__main__._dispatch` (direct-dispatch verbs that bypass the
tree), `frob.app.app._SUBCOMMAND_RUNNER_NAMES` / `_DEPRECATED_SPELLINGS`,
README.md's command table, docs/guides/command-reference.md and
docs/commands/*.md.

Abbreviations: `P:` = parser module under src/frob/_cli_parsers/;
`R:` = runner under src/frob/app/; "pkg" = implementing package under
src/frob/. `--path DIR` / positional `path` (repo root, default cwd) is
omitted from flag lists unless it is the only argument. `--json` is
present on almost every read verb and is only listed when notable.

v2 judgement vocabulary: KEEP / MERGE-INTO <x> / DROP (reason <=10 words).
v2 scope assumed: Rust, in-repo project management (tickets, scope
leases, worktrees) plus enforcement (gates, obligation graph, acks,
verify window, vet).

## 0. Headline findings

1. Completeness verdict: README table (50 rows) vs parser registry (51
   top-level names) differ by exactly ONE: `process` is registered in the
   parser and dispatched but has no README row (and no docs/commands
   page). Every other README row maps to a parser node; no README row is
   stale. See section 12 for the full cross-check.
2. The "seven verb groups" are NOT seven in `--help`. Only four are
   presented as groups (`_VERB_GROUP_NAMES` = explore, ticket, vet,
   serve). `quality`, `design`, `ops` exist as hidden (==SUPPRESS==)
   parsers whose invocation prints a deprecation shim (T-4690, sunset
   2026-12-01) pointing at the flat verbs. Real surface = flat verbs.
3. Parser/dispatch split: 12 argv shapes are dispatched BEFORE the argparse tree
   (`run`, `build`, `bind`, `quality bind`, `agent`, `worktree`,
   `whereis`, `sync-skills`, `release publish`, `release status`,
   `refactor`, `narrative`). Their real parsers live in the runner and
   are only partly mirrored in `--help`; flags below come from the real
   runner parsers.
4. Unwired/hidden-from-help reachable verbs: `run`, `build` (T-4759, not
   in `_build_parser`, T-4811 pending), `release publish`, `release
   status`, `worktree remove`, `worktree release-lease`.
5. Dead-registered: `ci report` has a parser builder (`P: _ci.py`) and a
   runner (`R: ci_runner`) but `_add_ci_parser` is never called; `frob ci`
   is NOT reachable from the CLI (argparse rejects it). Only `Subcommand.ci`
   exists in the runner table.
6. Doc drift found (docs/guides/command-reference.md vs parser): the guide
   lists `explore` as map/outline/xref/docs-search only; parser also has
   gitlog, stats, graph-query, graph-why, graph-affects, debt, deprecated.
   The guide places `gitlog`/`stats` under `ops`; they were folded into
   `explore` (T-4695) with `ops gitlog`/`ops stats` kept as shims.
   `ops` in the guide omits `process`.
7. Deprecation shim inventory (T-4690/4692/4695/4690): ~25 spellings are
   pure aliases with a sunset notice. v2 should ship none of them.
8. Gate scale: `frob check` fronts 73 registered gates
   (`frob.gates._ALL_GATES`, stage groups gates-fast / gates-native /
   gates-security) plus tool stages (ruff, ty, cycle, dup, arch, bind,
   exports, narrative, multi-language build/lint stages). The gate
   catalogue is out of scope here (see gates inventory); this file only
   covers the CLI.

Global flags (root parser, P: _root.py): `--version`,
`--color {auto,always,never}`, `--no-color`, `-v/--verbose` (sets
FROB_VERBOSE=1 by raw argv scan so direct-dispatch verbs see it too).
Cross-cutting behaviour in `main()`: SIGINT -> exit 130; SIGTERM reaper
installed (orphan forkserver cleanup); `_SuggestingArgumentParser`
did-you-mean on typos (docs/commands/cli-vocabulary.md); startup stderr
warnings (stale install/binary skew, claude-config drift, native
degrade). v2 judgement: KEEP did-you-mean and --json/--color; DROP the
install-skew/forkserver/VIRTUAL_ENV machinery (Python-packaging artefacts).

## 1. Standalone and flat verbs: summary map

Where every v1 top-level name lives and its v2 disposition. Detail tables
follow in sections 2-11.

| v1 top-level | Section | Hidden? | v2 |
|---|---|---|---|
| scaffold | 5 | no | KEEP (small) |
| explore | 2 | group | MERGE-INTO map/outline/xref flat |
| outline, map, xref | 2 | shim | KEEP as `explore`-style readers |
| cycle, dup, arch | 3 | shim | MERGE-INTO check |
| quality | 3 | hidden group | DROP (empty alias group) |
| design | 4 | hidden group | DROP (empty alias group) |
| ops | 5 | hidden group | DROP (empty alias group) |
| parse | 11 | no | DROP (Python tool output parsers) |
| docs | 4 | shim | MERGE-INTO explore |
| exports | 4 | shim | DROP (Python __init__ generator) |
| bind | 3 | shim | MERGE-INTO check |
| agent | 6 | no | MERGE-INTO ticket |
| worktree | 6 | no | MERGE-INTO ticket |
| whereis | 11 | shim | DROP (Python interpreter probe) |
| refactor | 11 | no | DROP (Python-only symbol rewriter) |
| narrative | 11 | no | MERGE-INTO check |
| check | 3 | no | KEEP (core) |
| gitlog, stats, debt, deprecated | 2 | shim | KEEP (as explore subverbs) |
| graph | 4 | no | KEEP |
| ack | 4 | no | KEEP (core) |
| pool | 3 | no | KEEP (ratchet baseline) |
| profile | 3 | no | KEEP |
| registry | 4 | no | MERGE-INTO check |
| ticket | 7 | group | KEEP (core) |
| test | 3 | no | KEEP |
| vet | 8 | group | KEEP |
| perf | 3 | no | DROP (cProfile heat-map; Python) |
| release | 5 | no | KEEP (reduced) |
| mutate | 3 | no | DROP (Python mutation tester) |
| serve | 9 | group | KEEP (core) |
| sys | 4 | no | DROP (strata design model, separate product) |
| process | 5 | no | DROP (Python forkserver cleanup) |
| deploy | 5 | no | DROP (VM deploy; out of scope) |
| fleet | 5 | no | KEEP (multi-repo; defer) |
| doctor | 5 | no | KEEP |
| clean | 5 | no | KEEP |
| fmt, format | 3 | shim/no | MERGE-INTO check --fix |
| claude | 10 | no | DROP (Claude-config sync; separate tool) |
| natives | 5 | no | DROP (maturin build; Python-specific) |
| coverage | 3 | no | MERGE-INTO test |
| status | 3 | no | KEEP |
| verify | 3 | no | KEEP |
| sync-skills | 10 | no | DROP (Claude skills sync) |
| run, build | 5 | unwired | MERGE-INTO check (command runner) |
| ci | 11 | dead | DROP (never reachable; gh wrapper) |

## 2. explore group (read-only navigation and listing)

Group parser: `P: _explore.py`, runner `R: explore_runner` (delegates to
the same runners as the flat spellings). Hidden flat aliases `outline`,
`map`, `xref`, `gitlog`, `stats`, `debt`, `deprecated`,
`graph query|why|affects` all print a shim notice and route here.

| Verb path | Purpose | Key flags | v1 module | v2 |
|---|---|---|---|---|
| `frob explore` | group; bare form prints usage | - | P:_explore.py R:explore_runner | KEEP as namespace |
| `frob explore outline FILE` | structural skeleton: classes, funcs, line numbers | `--json`, `--all` (include private) | pkg outline/, R:outline_runner | KEEP (tree-sitter multi-lang) |
| `frob explore map [PATH]` | project tree with sizes, symbol and line counts | `--depth N`, `--all`, `--json` | pkg map/, R:map_runner | KEEP |
| `frob explore xref SYMBOL [PATH]` | definition site plus every referencing file | `--lang`, `--cross-file`, `--json` | pkg xref/, R:xref_runner | KEEP |
| `frob explore docs-search PATH QUERY` | full-text search of docs/ | `--json` | pkg docs/, R:docs_runner | KEEP (ripgrep-class) |
| `frob explore gitlog [PATH]` | git history by conventional-commit type/granularity | `--level`, `--since`, `--until`, `-n/--limit`, `--all`, `--json` | pkg gitlog/, R:gitlog_runner | KEEP (feeds status/flow) |
| `frob explore stats` | DORA-ish queue health + commit cadence | `--days N`, `--json` | pkg stats/, R:stats_runner | MERGE-INTO status |
| `frob explore graph-query REF` | resolve symbol ref, show its edges | `--json` | pkg graph/, R:graph_runner | MERGE-INTO graph |
| `frob explore graph-why REF` | explain drift/ack status and remedy | `--json` | pkg graph/ | MERGE-INTO graph |
| `frob explore graph-affects REF` | transitive uses-contract dependents + docs/tests | `--max-depth`, `--max-nodes`, `--json` | pkg graph/ | MERGE-INTO graph |
| `frob explore debt` | list outstanding `frob:debt` entries | `--json` | R:debt_runner | KEEP (debt ledger) |
| `frob explore deprecated` | list `frob:deprecated` entries and sunset status | `--json` | R:deprecated_runner | KEEP |

Flat explore-era spellings (all DROP in v2: shim aliases, sunset
2026-12-01): `frob outline`, `frob map`, `frob xref`, `frob gitlog`,
`frob stats`, `frob debt`, `frob deprecated`, `frob graph query`,
`frob graph why`, `frob graph affects`, `frob ticket debt`,
`frob ticket deprecated` (the last two are also duplicates parked under
ticket; DROP).

## 3. quality verbs (correctness, hygiene, gates)

Hidden group `frob quality` (P:_quality.py, R:quality_runner) re-exposes
check, test, dup, arch, bind, cycle, mutate, perf. DROP the group; every
member also exists flat.

### 3.1 check -- the aggregate gate (v2 core)

`frob check [PATH]` -- P:_check.py (517 lines), R:check_runner +
_check_chunking*.py, pkgs check/ (ruff/ty/native/ts stage drivers) and
gates/ (73 gates). One verb with by far the largest flag surface.

| Flag | Meaning | v2 |
|---|---|---|
| `--type {python,cpp,rust,typescript}` | project type override (default auto-detect) | KEEP (language detect) |
| `--only STAGE` (repeat) | run only these stages or stage-group aliases (lint, static, narrative, gates-fast, gates-native, gates-security) | KEEP |
| `--skip STAGE` (repeat, comma-split) | skip stages; replaces ~20 per-stage `--skip-*` flags | KEEP (drop the 20 legacy flags) |
| `--skip-tests/ruff/ruff-check/ruff-format/ty/arch/cycle/dup/bind/exports/gates/build/clang-tidy/clang-format/cargo-check/clippy/fmt/tsc/eslint/prettier` | legacy per-stage skips (hidden, superseded by `--skip`) | DROP |
| `--list-stages` | print foldable stage names (dup arch cycle bind narrative exports) | KEEP |
| `--ticket ID` | scope the check to one ticket: undeclared change, scope, drift, coverage | KEEP (core loop) |
| `--base REF` | diff base for touched-set/scope | KEEP |
| `--files PATH` (repeat) | restrict compute to files (repo-wide gates still run) | KEEP |
| `--fix` / `--fix-all` | apply Tier-A deterministic auto-fixes and re-run; unscoped `--fix` refuses without `--fix-all` | KEEP (auto-fix engine) |
| `--fix-ruff` | genuine ruff check --fix + format write pass | MERGE-INTO --fix (per-language formatter) |
| `--stamp-baseline` / `--delta` | record violation baseline / report only new-since-baseline | KEEP (ratchet) |
| `--stamp-coverage` | record coverage.xml as current stamp | MERGE-INTO test |
| `--land-parity` | run exactly land's unscoped, uncached error evaluation | KEEP (land parity) |
| `--census` | per-rule waive-rate table | KEEP (rule telemetry) |
| `--budget SECONDS` | self-chunk stage groups to fit a time budget, with persisted resume | KEEP (agents have timeouts) |
| `--no-cache` | bypass .frob/gate-cache.db | KEEP |
| `--json`, `-v` | machine output / diagnostics | KEEP |
| `--valgrind`, `--build-dir DIR` | C++ memcheck / build dir | DROP (language drivers out of v2 core) |

Startup side effects (R:check via `_dispatch_default`): reap orphaned
forkservers; advisory count of concurrent `frob check` processes (T-2473).
v2: DROP the forkserver reaper (no Python pools), KEEP an advisory
concurrency note if parallel agents remain a use case.

### 3.2 other quality verbs

| Verb path | Purpose | Key flags | v1 module | v2 |
|---|---|---|---|---|
| `frob test [PATH]` | select and run tests for the touched set (or all) | `--all`, `--base REF`, `--lang L`, `--fallback {package,suite,warn}`, `--collect` (rebuild collection cache), `--wait-coverage` (single-flight until coverage stamp fresh), `--fuzz` (pydantic model fuzz), `--json` | P:_misc.py R:test_runner, pkg testing/ | KEEP (touched-set selection is core) |
| `frob coverage [PATH]` | refresh coverage.xml / stamp, touched-set incremental by default | `--full`, `--fail-on-degraded`, `--base REF` | R:coverage_runner | MERGE-INTO test |
| `frob dup [PATH]` | clone detection (Type 1 exact, Type 2 renamed) | `--min-lines N`, `--probe A B`, `--json` | R:dup_runner, pkg dup/ | MERGE-INTO check |
| `frob arch [PATH]` | long functions, god classes, coupling | `--max-function-lines N`, `--max-class-methods N` | R:arch_runner, pkg arch/ | MERGE-INTO check |
| `frob cycle [PATH]` | import-cycle detection | `--lang`, `--suggest` (cut-point hints) | R:cycle_runner, pkg cycle/ | MERGE-INTO check |
| `frob bind [PATH]` | verify binding declarations match source signatures | `--list-bindings`, `--list-sources`, `--json` | R:bind_runner (raw argv), pkg bind/ | MERGE-INTO check |
| `frob mutate FILE -- TEST-CMD` | mutation testing: perturb file, report surviving mutants | `--path`, `--json` | R:mutate_runner, pkg mutate/ | DROP (Python mutation engine) |
| `frob perf profile -- ARGV` | run under cProfile, store artifact | `--tests` | R:perf_runner, pkg perf/ | DROP (Python profiler) |
| `frob perf heat` | heat-map ranked by cumulative time | `--ref SHA`, `--smells`, `--top N`, `--annotate FILE` | pkg perf/ | DROP |
| `frob perf collect -- ARGV` | resolve perf/V8/JFR/py-sampler profile into hot-graph deciles | `--file`, `--format`, `--sampler`, `--interval-s`, `--max-depth`, `--top` | pkg perf/ | DROP |
| `frob perf hot` | query hot-graph sketch store | `--top N`, `--by` | pkg perf/ | DROP (MCP `frob_perf_hot` also drops) |
| `frob quality ...` (check/test/dup/arch/bind/cycle/mutate/perf, `quality perf *`) | hidden group alias of the flat verbs | same | P:_quality.py | DROP |
| `frob quality bind` | bind via quality group (direct dispatch) | same as bind | R:bind_runner | DROP |
| `frob pool snapshot RULE` | baseline every `--key` as warn for RULE; others stay error | `--key KEY` (repeat) | R:pool_runner | KEEP (ratchet pool) |
| `frob pool clear RULE` | remove one baselined key; always needs reason | `--key KEY`, `--reason TEXT` | R:pool_runner | KEEP |
| `frob profile show` | configured vs effective profile (rapid/standard/fortress) and ratchet state | `--json` | R:profile_runner | KEEP |
| `frob profile downgrade` | the only way to clear the one-way rapid->standard auto-ratchet | `--reason`, `--reason-file`, `--json` | R:profile_runner | KEEP |
| `frob fmt [PATH]` | canonicalize `frob:` directive comment wrapping | `--check`, `--include-test-corpora`, `--json` | R:fmt_runner (shim) | MERGE-INTO format |
| `frob format [PATH]` | ruff check --fix + ruff format, plus directive format; write mode default | `--code`, `--directives`, `--check`, `--select-imports-only`, `--json` | R:pyfmt_runner | MERGE-INTO check --fix |
| `frob status` | delta-first movement: findings burned/introduced, verification lag, landing velocity | `--only GATE`, `--tickets` (opt in, slow ledger mining), `--json` | P:_status.py R:status_runner | KEEP |
| `frob verify status` | unverified-window depth/age/quarantine | `--json` | P:_verify.py R:verify_runner, pkg verify/ | KEEP (also `status`-adjacent) |
| `frob verify now` | drain and verify the queue synchronously | `--json` | R:verify_runner | KEEP |
| `frob verify explain RULE:FILE[:LINE]` | attribution reachability path for one finding | `--json` | R:verify_runner | KEEP |
| `frob verify dispose` | dispose quarantined findings (file ticket or dismiss with reason) | `--file-ticket R:F:L=T`, `--dismiss R:F:L=REASON`, `--reason`, `--actor`, `--retire-unidentifiable` | R:verify_runner | KEEP |
| `frob verify drain-async` | one bounded automatic watermark drain round; spawned by `ticket land` | - | R:verify_runner | KEEP internal (not user verb) |

Notes: `frob verify status` is also a shim to top-level `status`
(T-4690 table). `frob fleet status` likewise.

## 4. design verbs (the model code is checked against)

Hidden group `frob design` (P:_design.py, R:design_runner): sys, registry,
docs, graph, exports. DROP the group; members exist flat.

| Verb path | Purpose | Key flags | v1 module | v2 |
|---|---|---|---|---|
| `frob graph build [PATH]` | (re)build obligation-graph cache | - | P:_core.py R:graph_runner, pkg graph/ | KEEP (core) |
| `frob graph query REF` | symbol ref resolution + edges (hidden) | `--json` | R:graph_runner | KEEP as `graph show` |
| `frob graph why REF` | drift/ack status and remedy | `--json` | R:graph_runner | KEEP |
| `frob graph affects REF` | transitive dependents + affected docs/tests | `--max-depth`, `--max-nodes`, `--json` | R:graph_runner | KEEP |
| `frob ack REF...` | acknowledge current digest for symbol refs (doc-drift) | `--facet` (e.g. sig), `--reason`, `--reason-file`, `--list`, `--path` | P:_core.py R:ack_runner | KEEP (core) |
| `frob docs PATH [SYMBOL]` | extract docstrings / `--overview`; also search | `--overview`, `--search QUERY`, `--sync-commands`, `--sync-command-pages` | R:docs_runner, pkg docs/ | MERGE-INTO explore (sync flags -> check) |
| `frob exports PATH` | generate ready-to-paste `__init__.py` from public symbols | `--all`, `--exclude MODULE`, `--write`, `--consumers SYMBOL`, `--lang`, `--json` | R:exports_runner, pkg exports/ | DROP (Python packaging) |
| `frob registry audit` | per-file disposition accounting over docs/design/registry/*.yaml (handled/deferred/out-of-scope/unaccounted) | `--sync-gate-rules`, `--json` | R:registry_runner, pkg registry/ | MERGE-INTO check (exhaustiveness lock) |
| `frob registry add` | append a pending entry to a registry universe corpus | `--file`, `--key`, `--id`, `--name`, `--source-doc` | R:registry_runner | KEEP (as exhaustive-research emit) or DROP; defer |
| `frob sys plan [PATH]` | compile obligation frontier into a ticket tree (idempotent) | `--apply` | R:sys_runner, pkg strata/ + strata-core | DROP (strata separate product) |
| `frob sys export FILE` | render k8s/seccomp/iam skeleton from a design | `--format` | pkg strata/ | DROP |
| `frob sys doc` | per-family threat-catalog audit matrix | `--view` | pkg strata/ | DROP |
| `frob sys audit` | full per-family exhaustiveness conjunction | - | pkg strata/ | DROP |
| `frob sys trace FROM TO` | influence-closure witness path | `--through-barriers` | pkg strata/ | DROP |
| `frob sys threats [BOUNDARY]` | THREAT001-005 violations | - | pkg strata/ | DROP |
| `frob sys capacity` | CAP001: demand exceeds capacity, optionally projected | `--population`, `--since`, `--at` | pkg strata/ | DROP |
| `frob sys shrink` | drop declared-but-unobserved `may` capabilities (SYS101) | `--check` | pkg strata/ | DROP |
| `frob sys init` | derive starting .strata skeleton; refuses if one exists | `--check` | pkg strata/ | DROP |
| `frob design sys|registry|docs|graph|exports ...` | hidden group aliases | same | P:_design.py | DROP |

Judgement note on `sys`: strata is a separate design-model language with a
Rust kernel (strata-core). If v2 wants an in-repo design-model feature it
belongs to its own crate; none of its verbs are needed by the PM core.

## 5. ops verbs (release, infra, repo plumbing)

Hidden group `frob ops` (P:_ops.py, R:ops_runner) re-exposes release,
natives, doctor, clean, fleet, deploy, scaffold, gitlog, stats, process.

| Verb path | Purpose | Key flags | v1 module | v2 |
|---|---|---|---|---|
| `frob release stamp` | record current public API + version to .frob-release.json | `--allow-unbumped`, `--reason`, `--reason-file` | P:_ops.py R:release_runner, pkg release/ | KEEP (REL001 semver-from-API; reduced to Rust public API) |
| `frob release check` | verify version bump covers the public-API change | - | R:release_runner | KEEP |
| `frob release sync` | regenerate pyproject version, uv.lock, CHANGELOG skeleton from .frob-release.json | - | R:release_runner | KEEP (Cargo.toml instead) |
| `frob release publish [PATH]` | patch bump, stamp/sync, commit, push, build, publish (direct dispatch, unwired) | `--dry-run` | pkg release/_cli.py | MERGE-INTO release (optional) |
| `frob release status [PATH]` | version, dev-bump toggle/ack (direct dispatch) | - | pkg release/_cli.py | KEEP |
| `frob doctor` | verify native extensions (frob_core, strata_core); derived-state health | `--json`, `--usage`, `--whereis` | R:doctor_runner, pkg doctor.py | KEEP (install/derived-state health) |
| `frob whereis` | interpreter/site-packages path (shim -> `doctor --whereis`) | `--json` | __main__._dispatch_whereis | DROP |
| `frob clean [PATH]` | tiered artifact removal, dry-run by default | `--all` (tier 2), `--deep` (tier 3, .frob caches), `-y/--yes`, `--sweep-disposable-worktrees`, `--json` | R:clean_runner, pkg clean/ | KEEP |
| `frob scaffold list` | list project templates | - | P:_core.py R:scaffold_runner, pkg scaffold/ | KEEP (minimal) |
| `frob scaffold new TYPE NAME` | create project from template | `--output DIR`, `--force` | R:scaffold_runner | KEEP |
| `frob scaffold apply` | apply template to current repo | - | R:scaffold_runner | KEEP (frob init) |
| `frob scaffold unity-project DIR` | Unity project skeleton | `--force` | pkg scaffold/ | DROP (Unity specific) |
| `frob scaffold pool warm N` | pre-warm a ratchet/lease pool of N worktrees | - | pkg scaffold/ | MERGE-INTO ticket work (worktree pool) |
| `frob scaffold pool lease` | lease a warmed worktree | - | pkg scaffold/ | MERGE-INTO ticket work |
| `frob scaffold pool status` | pool state | - | pkg scaffold/ | MERGE-INTO ticket work |
| `frob scaffold exports PATH` | alias to `frob exports` | same as exports | pkg scaffold/ | DROP |
| `frob fleet status` | cross-repo status and gate rollup over fleet.toml (also shim -> `status`) | `--manifest PATH`, `--skip-gates`, `--json` | R:fleet_runner, pkg fleet/ | KEEP (defer) |
| `frob fleet route` | file a ticket into a named sibling repo's ledger | `--manifest`, `--repo`, `--title`, `--kind`, `--priority`, `--scope GLOB`, `--body` | R:fleet_runner | KEEP (defer) |
| `frob deploy generate [PATH]` | compile std.host manifest to install/status/uninstall bash | `--out-dir`, `--check` | R:deploy_runner, pkg deploy/ | DROP (host deploy proofs, out of scope) |
| `frob deploy audit [PATH]` | VirtualBox snapshot-diff harness proving artifact-free install | `--vm`, `--ssh-host/user/key`, `--base-snapshot`, `--output` | pkg deploy/ | DROP |
| `frob natives [build]` | build declared `[[native]]` crates (maturin develop --release) | `--path` | R:natives_runner, pkg natives/ | DROP (maturin/PyO3 specific) |
| `frob process reap` | SIGTERM orphaned multiprocessing forkservers (ancestry-checked) | `--json` | R:process_runner, pkg process/ | DROP (Python-only) |
| `frob run NAME` | execute a frob.toml `[commands]` entry by name (unwired, direct dispatch) | `--dry-run` | R:run_runner, P:_run.py | MERGE-INTO check (task runner) |
| `frob build` | alias that resolves the `build` command entry (unwired) | `--dry-run` | R:run_runner | MERGE-INTO check (task runner) |
| `frob ops ...` (release, natives, doctor, clean, fleet, deploy, scaffold, gitlog, stats, process) | hidden group aliases | same | P:_ops.py | DROP |

## 6. Agent and worktree verbs (dispatch plumbing)

Direct-dispatched; real parsers inside the runners, not the central tree.

| Verb path | Purpose | Key flags | v1 module | v2 |
|---|---|---|---|---|
| `frob agent [env] [PATH]` | print FROB_WORKTREE/FROB_AGENT export lines for guard env (bare form implied `env`, T-4546) | positional path | R:agent_runner, pkg agent/ | MERGE-INTO ticket work |
| `frob agent brief TICKET` | dispatch brief for one ticket (playbook contract + ledger fields) | `--path` | R:agent_runner | MERGE-INTO ticket brief (duplicate) |
| `frob worktree sweep [PATH]` | lease-aware stale-worktree cleanup | `--dry-run`, `--min-age HOURS`, `--force` (override liveness gate) | R:worktree_runner, pkg worktrees/ | KEEP |
| `frob worktree remove PATH` | safe single-worktree removal with liveness check (unlisted in tree) | `--dry-run`, `--force` | R:worktree_runner | KEEP |
| `frob worktree release-lease ID` | release one ticket lease if confirmed orphaned (unlisted in tree) | `--force` (needs `--reason`/`--reason-file`) | R:worktree_runner | MERGE-INTO ticket (admin) |

## 7. ticket group (the project-management core)

`frob ticket <verb>`; parser package `P: _ticket/` (7 files, ~3.2k lines:
__init__, _new, _query, _progress, _metadata, _closeout,
_closeout_evidence), runner package `R: app/ticket_runner/` (_new, _query,
_lifecycle, _close_cmd, _land_cmd, _archive, _attach_backfill, _mutate,
_verify, _rapid_sweep, _waive_audit, _ledger_mirror), domain pkg
`tickets/`, plus worktrees/, gates/ (TICK*, MILE*, etc.). 65 parser nodes
(group nodes and `admin`/`sprint`/`waive-audit` aliases included). Group flag: `-v`. Universal flags on nearly all
mutating verbs: `--path DIR`, `--no-commit` (suppress ledger auto-commit),
`--reason TEXT` / `--reason-file PATH` (audit text; file form for shell
quoting safety), `--wait SECONDS` (ledger lock wait).

### 7.1 create and query

| Verb path | Purpose | Key flags | v2 |
|---|---|---|---|
| `ticket new` | create ticket | `--title`, `--kind`, `--acceptance` (repeat) / `--acceptance-file`, `--threat`, `--priority`, `--origin`, `--scope` (repeat glob), `--blocked-by`, `--parent`, `--tier`, `--sprint`, `--milestone`, `--points N`, `--component`, `--label`, `--finding RULE:FILE`, `--body` / `--body-file`, `--evidence NODE-ID`, `--ack-related`, `--scope-breadth-ack(+--reason)`, `--runs-last-parallel-safe(+--reason)`, `--json` | KEEP (trim sprint/tier/origin/threat) |
| `ticket list` | list tickets | `--state/--status`, `--stats`, `--json` | KEEP |
| `ticket show ID` | one ticket | `--json` | KEEP |
| `ticket doable` | doable set: queued/planned, no open blockers, scope-lease-safe | `--show-blocked`, `--ignore-lease`, `--sprint`, `--milestone`, `--by-parent`, `--show-anchors`, `--json` | KEEP (core; MCP mirror) |
| `ticket wave` | partition doable set into N scope-disjoint groups | `--agents N`, `--ignore-lease`, `--json` | KEEP (parallel dispatch) |
| `ticket contention` | files claimed by 2+ open tickets, ranked, with batching hint | `--json` | KEEP |
| `ticket board` | priority-ordered state-column board | `--component`, `--label`, `--json` | MERGE-INTO ticket list |
| `ticket epic ID` | descendant subtree with done/total rollup | `--json` | MERGE-INTO ticket show |
| `ticket brief ID` | full agent mission briefing: body, acceptance, scope, rules, verify cmds, gate baseline | `--cluster EPIC-OR-STORY` | KEEP |
| `ticket flow` | filed/day vs landed/day, burn-down ETA | `--json` | MERGE-INTO status |
| `ticket sprint assign ID LABEL` / `sprint show LABEL` / `sprint migrate` | sprint labels and rollup; migrate semver labels to milestone | `--json` | DROP (milestone covers it) |

### 7.2 lifecycle transitions

| Verb path | Purpose | Key flags | v2 |
|---|---|---|---|
| `ticket plan ID` | queued -> planned | - | MERGE-INTO ticket start |
| `ticket start ID` | -> in-progress; takes scope lease; backgrounds pre-work sweep | `--foreground`, `--steal` (take lease), `--scope-breadth-ack`, `--unsized-ack REASON`, `--require-points` | KEEP |
| `ticket work ID` | one-verb worktree setup: create/reuse, merge main, build natives, then start | `--worktree PATH`, `--cluster`, `--foreground`, `--steal` | KEEP (core agent entry) |
| `ticket requeue ID` | in-progress -> queued, releases lease | `--reason` | KEEP |
| `ticket sweep ID` | re-record pre-work sweep after widening scope | - | MERGE-INTO ticket scope |
| `ticket sweep-async ID` | background sweep entry (hidden internal) | `--commit SHA` | DROP (internal impl detail) |
| `ticket close ID` | -> done; requires evidence + Done report | `--evidence NODE-ID` (repeat), `--evidence-cmd`, `--cwd`, `--accepts INDEX`, `--strict`, `--skip-mutation-evidence`, `--no-behavior-change(+reason)` | KEEP |
| `ticket fail ID` | record failed attempt in failure log | `--summary` | MERGE-INTO ticket body |
| `ticket drop ID` | -> dropped with dated reason (never delete) | `--reason`, `--absorbed-by T-####` | KEEP |
| `ticket reopen ID` | done -> queued (audited undo of a false close) | `--reason` | KEEP |
| `ticket reverify ID` | re-run close verification, refresh recap, no transition | same as close, `--base-ref` | KEEP (as verify) |
| `ticket land ID` | one-command land: merge-check-splice-close-commit worktree onto checkout; queue/drain modes | `--worktree`, `--branch/--onto`, `--plan`, `--dry-run`, `--push`, `--queue`, `--drain`, `--status ID`, `--finish`, `--retire-on-proof`, `--run-mutation-sweep`, `--skip-mutation-evidence`, `--allow-cross-ticket`, `--force(+reason)` | KEEP (core; simplify) |
| `ticket promote DRAFT-ID` | allocate real T-#### for a draft id and rewrite every code reference atomically | - | KEEP (draft ids in worktrees) |
| `ticket merge-driver %O %A %B` | git merge driver for the ledger | - | KEEP (ledger merge) |
| `ticket archive` | move done/dropped to archive | `--force`, `--reason` | KEEP |
| `ticket restore ID` / `admin restore ID` | move back from archive | `--reason` | KEEP (one spelling) |
| `ticket attach ID PATH` | attach file/clipboard image | `--caption`, `--remove`, `--remove-all`, `--backfill-drafts`, `--apply` | MERGE-INTO ticket body |

### 7.3 evidence and closeout

| Verb path | Purpose | Key flags | v2 |
|---|---|---|---|
| `ticket evidence ID NODE-ID` | append/replace/remove structured test evidence; designate repro; check repro | `--evidence-cmd`, `--cwd`, `--base-ref`, `--replace OLD NEW`, `--remove`, `--archived`, `--accepts`, `--designate-repro(+reason,--force)`, `--check-repro`, `--repro-timeout-s`, `--criterion(+file)`, `--amend` | KEEP (core: evidence binding) |
| `ticket done-report ID` | atomically write Done report (Changed + Evidence auto-composed) | `--why/--body` / `--why-file`, `--base-ref`, `--no-check` | KEEP |
| `ticket review ID` | record structured adversarial-review verdict | `--verdict`, `--reviewer`, `--findings-file`, `--commit` | KEEP (optional) |
| `ticket accept ID` | append/amend/remove acceptance criteria | `--criterion(+file)`, `--amend INDEX`, `--text`, `--remove INDEX`, `--evidence-cmd`, `--accepts`, `--evidence` | KEEP |
| `ticket waive-audit scan` | read-only list of `frob:waive` needing classification since watermark | `--check-collisions`, `--check-liveness`, `--json` | KEEP (waiver honesty) |
| `ticket waive-audit complete` | record pass verdict, advance watermark | `--reviewed-count`, `--cop-outs`, `--partial` | KEEP |

### 7.4 metadata mutation (many are thin setters)

`ticket set ID FIELD VALUE` already folds priority, kind, component,
tier, milestone, sprint (its own help says so); the standalone setters
remain as parsers. v2: keep one `ticket set`.

| Verb path | Purpose | Key flags | v2 |
|---|---|---|---|
| `ticket set ID FIELD VALUE` | set priority/kind/component/tier/milestone/sprint | `--reason` | KEEP |
| `ticket priority` / `kind` / `component` / `tier` / `milestone` | standalone setters (priority also level) | `--reason` | MERGE-INTO ticket set |
| `ticket label ID` | add/remove freeform labels | `--add`, `--remove` | KEEP (via set) |
| `ticket points ID N` | story points | - | KEEP (via set) |
| `ticket tokens ID` | record measured token spend | `--tokens-in/-out/-cache-read` | KEEP (agent cost telemetry) |
| `ticket body ID` | amend free-text body (validated door) | `--append(-file)`, `--set(-file)`, `--reason`, `--wait` | KEEP |
| `ticket scope ID` | expand/reduce declared scope + tree lease; fails on overlap with another in-progress lease | `--add GLOB`, `--remove GLOB`, `--demote-to-evidence-only GLOB`, `--declare-no-scope`, `--reason` | KEEP (core: scope = write lease) |
| `ticket scope-ack ID` | acknowledge intentionally broad scope (exempts TICK009) | `--reason` | KEEP |
| `ticket anchor ID` | mark/unmark permanent anchor ticket (never lands; hidden from doable) | `--set`, `--clear` | KEEP |
| `ticket block ID` / `unblock ID` | add/remove blocker edge | `--by`, `--reason` (unblock) | KEEP |
| `ticket set-parent ID PARENT` | set/clear parent; refuses cycles, tier inversion, self | `--clear` | KEEP |
| `ticket runs-last ID on|off` | mark runs-last (milestone tail ticket) | - | KEEP (milestones) |
| `ticket runs-last-parallel-safe ID` | MILE004 escape hatch | `--reason` | DROP (niche) |

### 7.5 maintenance and admin

| Verb path | Purpose | Key flags | v2 |
|---|---|---|---|
| `ticket reconcile` / `admin reconcile` | heal ticket-worktree binding drift (stale holds, orphan worktrees) | `--apply`, `--remove-orphans`, `--strip-stale-fields`, `--no-commit`, `--wait` | KEEP (one spelling) |
| `ticket renumber [OLD NEW]` / `admin renumber` | rewrite one id everywhere, or compact all ids | `--dry-run` | KEEP (one spelling) |
| `ticket migrate` | collapse legacy tickets/*.md into single ledger | `--to`, `--fill-gaps` | DROP (v1 format migration) |
| `ticket admin` | disaster-recovery namespace | - | KEEP as namespace |
| `ticket debt` / `ticket deprecated` | duplicates of explore debt/deprecated | `--json` | DROP |

Notes: ledger is tickets/T-####/ticket.md plus mirrored tickets.md and
archive; the `--no-commit` flag exists on ~35 verbs because v1 auto-commits
ledger edits. v2 should treat the auto-commit as a ledger-store policy, not
a per-verb flag.

## 8. vet (dependency vetting)

Single verb, no subcommands. P:_misc.py? R:vet_runner,
pkg vet/ (capability scanners per language, CVE/OSV/NVD matching,
typosquat, lifecycle scripts, lockfile allow-list, hook mode).

| Verb path | Purpose | Key flags | v2 |
|---|---|---|---|
| `frob vet [PATH]` | lockfile allow conformance, quarantine, typosquat, lifecycle-script and OSV/CVE checks, capability scan | `--hook COMMAND` (PreToolUse install-command guard), `--cve-mirror DIR` (cvelistV5), `--timeout SECONDS`, `--jobs N`, `--json` | KEEP (Cargo-focused: lockfile allow-list, advisories, typosquat; drop per-language capability scanners beyond Rust) |

## 9. serve (MCP stdio adapter)

| Verb path | Purpose | Flags | v2 |
|---|---|---|---|
| `frob serve [PATH]` | MCP stdio server exposing enforcement queries | positional path only | KEEP (core agent interface) |

MCP tools (R:serve_runner, pkg serve/server.py + _tools.py + _warm.py +
_daemon.py + _socketd.py + _leases.py + _watch.py + _events.py):

| Tool | Mirrors | v2 |
|---|---|---|
| `frob_doable_tickets` | `ticket doable` | KEEP |
| `frob_stale_docs` | doc-drift query | KEEP |
| `frob_graph_query(symref)` | `graph query` | KEEP |
| `frob_doc_for(symref)` | docs-for-symbol | KEEP |
| `frob_affects(symref, max_depth, max_nodes)` | `graph affects` | KEEP |
| `frob_check_scope(ticket_id)` | scope check for a ticket | KEEP |
| `frob_check_delta(ticket_id, base, verify)` | incremental check on warm graph | KEEP |
| `frob_run_touched_tests(base)` | touched-set test run | KEEP |
| `frob_perf_hot(top, by)` | `perf hot` | DROP (perf dropped) |
| `frob_daemon_status` | warm-daemon health | KEEP if v2 has a daemon |

The daemon/socket/watch/lease modules mean `serve` is also the warm-state
host; v2 may promote that to a first-class `frobd` while keeping `serve`
as the MCP shim.

## 10. Claude/agent-host integration verbs

| Verb path | Purpose | Key flags | v1 module | v2 |
|---|---|---|---|---|
| `frob claude [sync]` | materialize tracked .claude config into ~/.claude, or `--check` drift (bare form implied `sync`, T-4522) | `--check` | R:claude_runner | DROP (host-config sync; not PM/enforcement) |
| `frob sync-skills [PATH]` | bidirectionally sync agents/ and skills/ into ~/.claude | `--claude-dir`, `--force` | pkg scaffold/_skills_sync.py (direct dispatch) | DROP |

(`frob agent` and `frob worktree` are in section 6.)

## 11. Remaining standalone verbs

| Verb path | Purpose | Key flags | v1 module | v2 |
|---|---|---|---|---|
| `frob parse TOOL FILE` | normalize pytest/ruff/ty/clang/junit output into compact summary | `--exit-code N`, `--passthrough`, `--json`, `--verbose` | R:parse_runner, pkg (parse in lang/ or check/) | DROP (v2 owns its own runners) |
| `frob refactor move SRC DST` | transactional Python symbol move, rewriting references | `--alias-conflict`, `--full-repo-collect`, `--skip-check-delta` | pkg refactor/ (direct dispatch) | DROP (Python-specific; revisit for Rust) |
| `frob refactor rename SRC DST` | rename symbol | same | pkg refactor/ | DROP |
| `frob refactor split SRC` | split N symbols into a new module | `--symbols`, `--into`, `--chunk-size`, `--skip-pytest-collect`, `--skip-check-delta` | pkg refactor/ | DROP |
| `frob refactor move-module SRC DST` | move/rename a module file | `--allow-existing-destination`, `--full-repo-collect` | pkg refactor/ | DROP |
| `frob narrative [move] FILE LINE` | move a `# T-####:` narrative comment block into its ticket, leaving a one-line reference (bare form implied `move`) | `--keep-file`, `--reason`, `--dry-run` | pkg narrative/ (direct dispatch) | MERGE-INTO check (narrative gate stays; mover is author-only) |
| `frob ci report RUN-ID` | per-job/platform failing nodes and clusters for one gh run | `--path`, `--json` | R:ci_runner, P:_ci.py (UNREACHABLE: builder never registered) | DROP (never wired; gh dependency) |
| `frob whereis` | see section 5 | `--json` | __main__ | DROP |

## 12. Completeness cross-check

### 12.1 Counts

| Measure | Count |
|---|---|
| Top-level names in live parser (including hidden/shim) | 51 |
| README command-table rows | 50 |
| docs/commands/*.md pages | 41 (40 verb pages + cli-vocabulary) |
| Parser nodes enumerated (all depths, incl. group-alias duplicates) | 243 |
| Direct-dispatch-only verbs not in `_build_parser` | `run`, `build`, `release publish`, `release status`, `worktree remove`, `worktree release-lease` (plus `quality bind` bypass) |
| Registered in runner table but unreachable | `ci` |
| `frob ticket` parser nodes | 65 (incl. group nodes, `admin *`, `sprint *`, `waive-audit *`) |

### 12.2 README vs parser

Method: `comm` of README rows (`| \`frob X\` |`) against top-level
parser names.

- README rows with no parser node: none.
- Parser top-level names with no README row: `process` (parser:
  `frob process reap`; also reachable as `frob ops process reap`).
- README rows are accurate for hidden verbs (README lists `quality`,
  `design`, `ops`, `explore`, `ticket`, `vet`, `whereis`, `fmt`, `dup`,
  `arch`, `exports`, `bind`, `debt`, `deprecated`, `gitlog`, `stats` and
  so on even though many print deprecation shims).
- README group rows name members that match the parser: `design` =
  sys/registry/docs/graph/exports (matches `_design.py`); `quality` =
  check/test/dup/arch/bind/cycle/mutate/perf (matches `_quality.py`);
  `ops` row lists release/natives/doctor/clean/fleet/deploy/scaffold/
  gitlog/stats (parser ALSO has `process`: mismatch, same as above);
  `explore` row lists map/outline/xref/docs-search (parser has seven more
  members: mismatch).

### 12.3 docs/commands vs parser

- Pages with no parser node: `cli-vocabulary` (cross-cutting, not a verb),
  `run` (verb exists only via direct dispatch, unwired).
- Parser top-level names with no page: arch, bind, debt, deprecated,
  design, docs, dup, fmt, ops, quality, stats, whereis. All are either
  hidden group aliases or deprecated flat shims; none is a surprise.
- `claude`, `natives`, `status`, `verify`, `sync-skills`, `profile`,
  `pool`, `coverage`, `process`: page presence confirmed for all except
  `process` (no page; also not in README).

### 12.4 docs/guides/command-reference.md vs parser

- Group memberships agree for quality and design.
- `ops` omits `process`; places `gitlog` and `stats` under ops although
  `explore` now owns them (ops keeps shim copies).
- `explore` lists 4 members; parser has 11 (gitlog, stats, graph-query,
  graph-why, graph-affects, debt, deprecated omitted).
- `ticket`, `vet`, `serve` entries are prose-only (no verb table for vet
  or serve; the ticket table covers about 10 of 65 nodes).

### 12.5 Registry vs runner table vs dispatch

- `Subcommand` enum / `_SUBCOMMAND_RUNNER_NAMES` has 44 entries including
  `ci` (unreachable) and excluding `bind`, `agent`, `worktree`,
  `refactor`, `narrative`, `sync-skills`, `run`, `build`, `whereis`,
  `process` (handled by `process_runner` separately), and `release
  publish/status` (own parsers).
- `whereis` and `fmt` call `announce_shim` from their own code; all other
  shims are keyed in `_DEPRECATED_SPELLINGS` (quality, design, ops groups;
  outline/map/xref; verify status; fleet status; dup/arch/cycle ->
  `check --only X`; exports -> `scaffold exports`; gitlog/stats/debt/
  deprecated/graph query|why|affects -> explore).
- `bind` shim: folded into `check --only bind` (T-4692), still a working
  command through the sunset window.

Verdict: the parser registry, README and dispatch table reconcile except
for the items above (process without README row, unwired run/build/ci,
doc-guide explore/ops membership drift). No top-level verb exists in the
README that is absent from the parser.

## 13. v2 CLI shape suggested by this inventory

Surviving verb set (about 20 top-level, vs 51 in v1):

| v2 verb | Absorbs |
|---|---|
| `ticket` (about 30 verbs) | v1 ticket minus sprints/board/epic/setters/migrate/sweep-async; plus agent, worktree, scaffold pool |
| `check` | cycle, dup, arch, bind, registry audit, narrative gate, format/fmt, run/build task runner, coverage stamp |
| `test` | coverage |
| `graph` | explore graph-*, docs |
| `ack` | - |
| `explore` | outline, map, xref, docs-search, gitlog, debt, deprecated |
| `status` | stats, ticket flow, fleet status |
| `verify` | status/now/explain/dispose/drain-async |
| `pool`, `profile` | ratchet baseline and rapid/standard/fortress |
| `vet` | - |
| `serve` | MCP adapter (plus daemon) |
| `release` | stamp/check/sync/publish/status |
| `doctor`, `clean`, `worktree` | install health, artifact cleanup, stale worktree sweep |
| `fleet` | defer to post-v2.0 |
| `scaffold` | list/new/apply only |

Dropped outright: parse, refactor, mutate, perf, sys, deploy, natives,
process, claude, sync-skills, exports, whereis, ci, quality/design/ops
groups, all deprecated shims.

## 14. Parser-file index (where each verb is registered)

| Parser module (src/frob/_cli_parsers/) | Verbs registered |
|---|---|
| _root.py | root parser, grouped help, did-you-mean, `_add_analysis_subparsers`, `_add_workflow_subparsers`, `_VERB_GROUP_NAMES` |
| _core.py | scaffold, cycle, outline, map, xref, parse, dup, arch, docs, exports, bind, agent, worktree, whereis |
| _check.py | check |
| _explore.py | explore group |
| _quality.py | quality group (hidden) |
| _design.py | design group (hidden) |
| _ops.py | ops group (hidden), process |
| _reporting.py | gitlog, graph, ack, debt, deprecated, pool, profile, registry, fleet |
| _misc.py | test, vet, perf, release, mutate, stats, doctor, clean, fmt, format, claude, natives, coverage, sync-skills, serve, sys, deploy |
| _status.py / _verify.py | status / verify |
| _run.py | run, build (defined but NOT registered, T-4811) |
| _ci.py | ci (defined but NOT registered; dead) |
| _shims.py | `announce_shim` deprecation notice helper |
| _ticket/ (7 files) | ticket and all subverbs |
| Runner-local parsers (not in tree) | agent_runner, worktree_runner, bind_runner, run_runner, release/_cli.py, refactor/_cli.py, narrative/_cli.py, scaffold/_skills_sync.py |
