# Slice C: v1 implemented features against v2 (MCP, daemon, editors, fleet, deploy, mutate, fuzz, cve, refactor, map, outline and the rest)

Researcher: exhaustive-researcher, 2026-10-04. v1 = v1/ (read-only), v2 = v2/ (read-only except this file). ASCII only. Statuses: BUILT, TICKETED, DESIGNED, DROPPED (on purpose, with a citation), MISSING.

## 0. Honest status line

Universe enumerated before any exploration: 46 v1 packages, 15 top-level modules, 13 scripts, 4 editor files, 2 native crates (24 Rust files), 255 docs files. Every one is accounted in the appendix (section 6) with 0 unmapped (checked by the generator that wrote this file). Findings: 118 rows = BUILT 31, TICKETED 15, DESIGNED 31, DROPPED 23, MISSING 18. Pending 0, blocked 0.

Depth limits, disclosed: gates/ (126 modules, 667 rule ids), tickets/ (51 modules), vet/ (50), webapp/ (38) and strata/ (90) are classified at feature-family level here and defer the per-id audit to slices A and B and to notes/v1/gates-and-rules.md; I read their module docstrings, docs pages and the v2 side of each family, not every function. No v1 command was run (one accidental `frob serve` from PATH, which is v1, ran for a moment and exited; `git status` of v2 stayed clean). Three behaviours were verified by running the v2 binary in throwaway repositories outside both trees: SB-1, SB-2, and that a tracked Python file with a bare `# TODO` is opaque F0 (TODO001 Unresolved, no finding on the line).

Headline findings that were not in the earlier notes:

1. Two structural bugs reproduced in v2 today: an unreadable (non-UTF-8) tracked file vanishes from analysis with only a stderr log line (SB-1, P-02), and `ticket close --outcome done` succeeds with unmerged work on the ticket branch while `ticket doctor` stays green (SB-2, P-01, the v1 'done but absent' incident class).
2. `frob serve` (the MCP server) is designed but has no crate and no ticket; only grimble-serve is ticketed (low). This session's own `frob` MCP server failed to connect. Measured MCP use is very thin (4 frob tool calls in 1,595 transcripts), so the proposal is a thin generated surface, not the v1 daemon (P-04).
3. The estate is Python/C++/TS (7 of 9 fleet repos Python-dominant) but v2 has only Rust/Markdown/TOML adapters and no ticket for first-party Python, TS or C-family adapters (P-03, high). Everything else in a Python repo reads as opaque F0 with Unresolved findings.
4. Features the notes did not list at all: predictive rebase-conflict warnings (C-12), cross-process heavy-step semaphore (C-17), automatic token accounting per ticket (C-48), CI failure clustering and result validity (C-50), stranded-branch analysis and done-ticket landing verification (C-55, C-56), global-binary skew guard (C-63), secrets scanner SEC001-003 (C-100, designed but unticketed), editor grammar generator (C-19).

## 1. Inventory (denominator)

Enumeration commands, run from the v1 root (all counts are of files or directories present at 2026-10-04):

```
find v1/src/frob -maxdepth 1 -mindepth 1 -type d ! -name __pycache__ ! -name .frob   # 46 packages
find v1/src/frob -maxdepth 1 -type f -name '*.py'                                      # 15 top-level modules
find v1/src/frob -name '*.py' | wc -l                                                   # 756 python files
ls v1/scripts | grep -v __pycache__                                                     # 13 entries (11 py, 1 hook, 1 guard)
find v1/editors -type f                                                                 # 4 files
find v1/frob-core/src v1/strata-core/src -name '*.rs'                                   # 9 + 15 = 24 files, 14.7k lines
find v1/docs -type f                                                                    # 255 files
```

| Group | Count | How accounted |
|---|---|---|
| v1/src/frob packages | 46 | appendix 6.1 |
| v1/src/frob top-level modules | 15 | appendix 6.2 |
| v1/scripts | 13 | appendix 6.3 |
| v1/editors | 4 | C-19, C-20 |
| v1/frob-core (9 .rs) and v1/strata-core (15 .rs) | 24 | appendix 6.4 |
| v1/docs: modules 85, commands 41, guides 21, guides/extending 22, design 28, design/registry 14, audits 19, strata 18, investigations 4, other 3 | 255 | appendix 6.5 |
| v1 user-facing verbs (docs/commands pages) | 41 | appendix 6.5 (commands) and section 2 |
| MCP tools registered by build_server | 10 | C-02 .. C-11 |
| Socket-only RPC methods | 5 (+2 lease, +1 subscribe) | C-13, C-16, C-17 |
| v2 ledger tickets read for cross-reference | 477 (227 done, 250 open) | `frob ticket list --json` |

v2 evidence base: docs/design (decision log D1-D87), the ticket ledger, crates/ (141,930 Rust lines). v2 verbs actually registered (from `register::<>` calls and `frob --help`): schema, doctor, init, config show|sync, lease list|widen, board, contention, ticket (new update link unlink comment close drop reopen show list doable brief fragment doctor merge-driver evidence), milestone, cycle, release (changelog notes status bump cut adopt), work, start, requeue, test, ack, graph (why affects), check, land. Not registered although designed: serve, hook, fleet, status, stats, clean, explore, vet, migrate, batch, fix, ticket wave|query|log|triage|attach|review, worktree, tui.

## 2. Deep dive: the MCP server, the daemon and editor integration

### 2.1 MCP tools: what each does and where v2 stands

| MCP tool | Question it answers | v2 equivalent | Status |
|---|---|---|---|
| frob_doable_tickets | what can I start | `frob ticket doable` | BUILT (C-02) |
| frob_stale_docs | which doc bindings drifted | `check --only DRIFT`, `graph why` | BUILT (C-03) |
| frob_check_scope | is my diff inside the ticket scope | `check --ticket` | BUILT (C-04) |
| frob_graph_query | edges of a symbol | `graph query` (designed, not registered) | DESIGNED (C-05) |
| frob_doc_for | which docs describe a symbol | `graph why` bindings | BUILT (C-06) |
| frob_affects | impact of changing a symbol | `graph affects` | BUILT (C-07) |
| frob_check_delta | what did my edit introduce | `check --delta` (designed); land ratchet built | DESIGNED (C-08) |
| frob_run_touched_tests | run the tests that reach my change | `frob test --base` | BUILT (C-09) |
| frob_perf_hot | which symbols are hot | none (`perf` removed) | DROPPED (C-10) |
| frob_daemon_status | did main go red after a land; will my branch conflict | land is synchronous; no predictive conflict check | DROPPED (C-11) and MISSING (C-12) |

Net: 6 of 10 tools already have a built v2 CLI equivalent, 2 are designed, 1 is dropped on purpose, 1 splits into a dropped half and a missing half. The wrapper that exposes them to an MCP client (C-01) is the unbuilt part. Usage evidence: see P-04 and OQ-1.

### 2.2 Daemon

v1 had two daemons: the in-process thread inside `frob serve` (post-land re-verify, rebase bot, coalescing verify worker, every 20 s) and an opt-in unix-socket daemon with a CLI auto-proxy (single-instance flock, idle timeout, version handshake on package version and source HEAD, six liveness states). v1's own docs call the socket daemon 'a net pessimization' and it is opt-in because it leaked forkserver children and competed for CPU (v1/docs/modules/serve.md T-1378). v2 stance: no daemon in milestone 1 (D36), 'warm' is a fresh process with a populated cache (architecture.md s2, goals.md), and a daemon is an optional milestone-2 optimization with transparent fallback (git-io.md s6). Verdict: the post-land verify job is obsolete (synchronous land), the rebase bot is worth keeping as a command (P-16), the semaphore is worth keeping as a file-lock feature (P-17), the socket daemon should not be ticketed until a measured need exists (C-15, SB-5).

### 2.3 Editor integrations

v1 shipped exactly one editor artifact: a TextMate grammar for .strata used by VS Code directly and by every JetBrains IDE through TextMate Bundles, drift-locked to the parser's keyword table, with an explicit statement that no LSP is planned. v2 keeps both halves in design (generated `editors/grimble.tmLanguage.json`; LSP a non-goal) but has no generator, no editors/ directory and no ticket (C-19, P-14). The editor-facing machine surfaces in v2 are SARIF and `check --files` (C-21, P-06), also unbuilt.

### 2.4 fleet, deploy, mutate, fuzz, cve, refactor, map, outline

| Feature | What a user gets | Verdict |
|---|---|---|
| fleet (C-24, C-25) | one reddest-first view of the 9-repo estate and cross-repo ticket routing | worth building (P-22); designed, unticketed |
| deploy (C-29, C-30) | host provisioning scripts compiled from a model, VM snapshot-diff proof | dropped on purpose; no action |
| mutate (C-31, C-32) | mutation score as honest test-quality evidence | verb dropped; evidence idea missing, low (P-24) |
| fuzz (C-33) | enforced property fuzzing, opt-in, off by default | missing, not worth a ticket |
| cve / vet (C-34, C-35, C-36) | advisories, capability diff, typosquat, install-hook guard | ticketed as grimble vet (~RPQKHAV); acceptance must include SB-8 |
| refactor (C-37, C-38) | move/rename carrying frob bookkeeping | verb dropped; one repair gap remains (P-21) |
| map, outline, xref, docs (C-39 .. C-42) | token-cheap orientation and uses | designed (frob-explore), unticketed, low use in v1 telemetry (P-07) |

## 3. Findings table

One row per user-facing feature or module family. 'Proposed' column points to section 4.

| ID | Item (what it does for a user) | v1 evidence | Status | v2 evidence | Proposed |
|---|---|---|---|---|---|
| C-01 | frob serve: stdio MCP server (FastMCP, optional mcp SDK, lazy import, read-only by INV-021). An MCP-aware agent calls enforcement queries directly instead of shelling out and parsing text. | v1/src/frob/serve/server.py, _tools.py; v1/docs/modules/serve.md; v1/.mcp.json | DESIGNED | v2/docs/design/architecture.md s7 (rmcp, tool list generated from Command metadata); boundaries.md gob-serve, frob-serve; cli.md `serve [--mcp\|--http]` milestone 2. No crates/frob-serve, no ticket (only ~VXAYFQJ grimble-serve). `frob --help` has no serve. | P-04 |
| C-02 | MCP tool frob_doable_tickets. Ordered list of tickets that can be started now. | v1/src/frob/serve/_tools.py::frob_doable_tickets | BUILT | `frob ticket doable` (v2/crates/frob/src/ticket/read.rs Doable); lease-aware via v2/crates/frob-lease/src/guard.rs. MCP wrapper is C-01. |  |
| C-03 | MCP tool frob_stale_docs (DRIFT001 stale acks, DRIFT002 dangling edges). Which doc/ack bindings drifted. | _tools.py::frob_stale_docs | BUILT | `frob check --only DRIFT` (v2/crates/frob-ack/src/rules.rs, DRIFT001-003); `frob graph why`. |  |
| C-04 | MCP tool frob_check_scope (is the working diff inside the ticket's scope globs). Scope-violation answer for one ticket. | _tools.py::frob_check_scope | BUILT | `frob check --ticket <h>` (v2/crates/frob-check/src/scope.rs, SCOPE001). |  |
| C-05 | MCP tool frob_graph_query (symbol, span, digests, in/out edges). Resolve a symref and see its edges. | _tools.py::frob_graph_query | DESIGNED | v2/docs/design/cli.md row `graph query` (frob-explore, milestone 2); code-model.md s9. Not in `frob graph --help` (only why, affects). No ticket. | P-07 |
| C-06 | MCP tool frob_doc_for (frob:doc and describes edges for a symbol). Which docs describe this symbol. | _tools.py::frob_doc_for | BUILT | `frob graph why <sym>` returns bindings (role, file, line, target, target_exists) and acks (v2/crates/frob-ack/src/cmd.rs WhyData). |  |
| C-07 | MCP tool frob_affects (docs, tests, transitive dependents; max_depth, max_nodes). North-star impact query before editing a public symbol. | _tools.py::frob_affects | BUILT | `frob graph affects` (v2/crates/frob-ack/src/cmd.rs GraphAffects, AffectsData files map). |  |
| C-08 | MCP tool frob_check_delta (violations new since the stamped baseline; verify=true cold cross-check). Fast agent loop: what did my edit introduce. | _tools.py::frob_check_delta; docs/modules/serve.md 'Staleness/correctness contract' | DESIGNED | v2/docs/design/rules.md s4 (`check [--delta] [--files]`) and s6 (per-checkout .frob/baseline fingerprints). Land-side equivalent BUILT: v2/crates/frob-land/src/ratchet.rs (~QAFRXM3). `check` flags built: --ticket --only --fix --fail-on --base --timing --explain; no --delta, no --files. No ticket. | P-06 |
| C-09 | MCP tool frob_run_touched_tests (select and run touched-set tests). Run only the tests that reach the change. | _tools.py::frob_run_touched_tests | BUILT | `frob test --base` (v2/crates/frob-tests/src/lib.rs touched_set, select_tests, run). |  |
| C-10 | MCP tool frob_perf_hot (persisted hot-graph sketch store ranked by p50xcount or p90). Rank symbols by sampled runtime heat. | _tools.py::frob_perf_hot; v1/src/frob/perf/_sketch_store.py | DROPPED | v2/docs/design/cli.md s4 'Removed from frob relative to v1: ... perf ...'; notes/v1/cli-surface.md s3.2 ('MCP frob_perf_hot also drops'). See P-18 and OQ-3: a Rust producer is an open owner call. | P-18 |
| C-11 | MCP tool frob_daemon_status: post-land delta+touched-tests verdict within 20 s of any land. Tells the coordinator whether main went red after a land. | serve/_daemon.py::_poll_post_land; serve.md 'Daemon jobs' | DROPPED | v2/docs/design/tickets.md s10 and rules.md s6: land runs the full check synchronously and is a ratchet (D8, D25); 'milestone 1 has no post-land red'. Deferred-verify machinery not built. |  |
| C-12 | Rebase bot: simulate merging main into every leased worktree branch (git merge-tree) and warn on conflict. Early warning that an in-flight agent branch will conflict with main. | serve/_daemon.py::_poll_rebase_bot; serve.md 'Daemon jobs' item 2 | MISSING | Searched v2 docs/design and crates for merge-tree, conflict, rebase, lease+conflict: only `frob work` reports base-merge conflicts at start (v2/crates/frob-worktree/src/verbs.rs `conflicts`). No predictive check on live leases. | P-16 |
| C-13 | Socket-only RPC methods frob_exports, frob_stats, frob_map, frob_version, frob_shutdown. Warm-process answers for map/stats; handshake and shutdown. | serve/_socketd.py; _tools.py::frob_map/frob_stats/frob_exports | DESIGNED | map/stats are C-39/C-44 (designed); exports dropped (C-69); version handshake is in the daemon design (C-15). |  |
| C-14 | Warm state: graph snapshot + baseline + test ids cached per root, keyed by git HEAD + status + (mtime,size). Repeated tool calls cost nothing; correct after any edit. | serve/_warm.py::_WarmState, _repo_dirty_key; property test 'rebuilds iff tree changed' | BUILT | Correct by construction: rules.md s4 steps 1-3 (digest every tracked file each run, artifacts keyed by content digest and parser identity), v2/crates/gob-cache (D30, D38). Warm check <1 s target is in-progress ~36ZXTMR. |  |
| C-15 | Per-repo unix-socket daemon: single-instance flock, idle timeout, version handshake (package version AND source HEAD), six liveness states, CLI auto-proxy, opt-in (FROB_DAEMON=1). Warm answers for the CLI; v1 measured it a net pessimization and opt-in only. | serve/_socketd.py, app/_daemon_proxy.py; serve.md 'Socket daemon', 'CLI daemon proxy' | DESIGNED | v2/docs/design/git-io.md s6 'Daemon option' (milestone 2 or later; handshake on binary+schema version, re-stat inputs before answering, transparent in-process fallback); architecture.md s2 'warm ... does not mean a daemon'; goals.md. No ticket; do not ticket until a measured need exists (see SB-5 for the v1 failure modes the design text omits). |  |
| C-16 | FS-watch push invalidation and subscribe events (graph-changed, coverage-fresh). Clients are told when derived state changed. | serve/_watch.py, _events.py | DESIGNED | v2/docs/design/gui.md s2 (notify watcher, debounced, SSE). Milestone 2 or later (D36). No ticket. |  |
| C-17 | Daemon-owned named resource leases/semaphores (coverage single-flight, released on connection drop). Serialize heavy shared steps across worktrees and agents; crash-safe release. | serve/_leases.py::ResourceLeaseManager; serve.md 'Resource leases/semaphores' | MISSING | Searched 'semaphore', 'single-flight', 'heavy', 'builder slot' in v2/docs/design and crates: gob-exec has an in-process semaphore only (v2/crates/gob-exec/src/semaphore.rs); [pm.wip] caps tickets not builds. Owner memory 'frob-v2-disk-guard' (two-builder limit, disk filled 3x) is the live need. | P-17 |
| C-18 | Bounded call that abandons a stuck parse/scan worker (daemon-thread timeout, SIGUSR1 stackdump). A pathological file cannot hang the run. | v1/src/frob/_daemon_timeout.py; testing/_stackdump.py | BUILT | v2/crates/gob-languages/src/parse.rs (size cap 2 MiB, 2 s timeout, never panics); gob-exec bounded spawns. |  |
| C-19 | Editor syntax: TextMate grammar for .strata shared by VS Code and JetBrains, drift-locked to the parser keyword table. Highlighting of design files in two editor families. | v1/editors/vscode-strata/*, editors/jetbrains/README.md; docs/guides/editors.md; tests/unit/test_strata_tmlanguage.py | DESIGNED | v2/docs/design/documentation.md s3 (`editors/grimble.tmLanguage.json` via `cargo dev gen editors`), grmb-spec.md s2.6 (keyword table is the single source). No generator in v2/crates/gob-dev/src, no editors/ directory, no ticket. | P-14 |
| C-20 | Language-server intelligence (completion, go-to-definition, hover). None: v1 explicitly never planned an LSP for .strata. | v1/docs/guides/editors.md 'What you get, honestly' | DROPPED | v2/docs/design/goals.md non-goals ('Code navigation/editing (LSP clients do that)'); consuming LSP/SCIP is deferred, boundaries.md. |  |
| C-21 | SARIF / CI annotations. Findings appear as annotations in editors and PRs. | v1 had no SARIF; notes/v1 recommend it | DESIGNED | v2/docs/design/rules.md s4 step 7 (`--sarif`, milestone 2); README D22. No ticket. | P-06 |
| C-22 | Shell completions, man pages, did-you-mean on typos. Ergonomics: tab completion, `man frob`, suggestions. | v1/src/frob/_cli_parsers (_SuggestingArgumentParser); docs/commands/cli-vocabulary.md | DESIGNED | Did-you-mean BUILT for config keys (v2/crates/gob-config/src/load.rs) and by clap for verbs. Completions and man pages: v2/docs/design/cli.md s5 and documentation.md s3 'milestone 2 or later'. No ticket. | P-27 |
| C-23 | Agent-harness hooks: one `frob hook <event>` binary (pre-tool guards, vet --hook pre-install check, telemetry hooks). Guards agent shell commands; records tool-call telemetry. | v1/.claude/hooks/* (14 files), scripts/frob-telemetry-hook; docs/guides/claude-hooks.md | DESIGNED | v2/docs/design/git-io.md s5; architecture.md s7; boundaries.md frob-hook ('`pre-tool` invokes `grimble vet --hook`'). Milestone 2 or later (D36); no ticket. Overlaps slice D. | P-23 |
| C-24 | frob fleet status: reddest-first rollup (git branch/dirty, gate error/warn counts, doable count) over fleet.toml. One command answers 'how red is the 9-repo estate'. | v1/src/frob/fleet/__init__.py; docs/modules/fleet.md; v1/fleet.toml (9 repos) | DESIGNED | v2/docs/design/cli.md `fleet status\|route` milestone 2; boundaries.md frob-fleet; migration.md ('fleet.toml unchanged shape'). No crate, no ticket. | P-22 |
| C-25 | frob fleet route: file a ticket into a named sibling repo's own ledger. Cross-repo findings routing without cd. | fleet/__init__.py::route_ticket | DESIGNED | Same rows as C-24. Needs a security review: v2 ledgers live on an orphan branch (D79) and a cross-repo write is a new privilege (D82). | P-22 |
| C-26 | Estate rollout recipes (capability spelling migration, native-build shim). Per-repo v1 migration instructions. | docs/guides/estate-capability-migration.md, estate-natives-build-rollout.md | DROPPED | Python-native build shim and .strata spellings: v2/docs/design/cli.md removes natives; grimble-model.md s2 drops host/deploy keywords; migration.md s1 `grimble migrate` handles .strata. |  |
| C-27 | scripts/fleet_status.py: root cleanliness, leases, worktree liveness, per-ticket dispatch readiness. Coordinator pre-dispatch check. | v1/scripts/fleet_status.py; docs/guides/coordinator-scripts.md | BUILT | `frob lease list`, `ticket contention`, `ticket doable`, `doctor` gc report, land guards E-LAND-DIRTY (v2/crates/frob-lease, frob-worktree/src/gc, frob-land). |  |
| C-28 | scripts/wait_for_land_slot.py: block until no land is in flight. Agents queue for the land lock quietly. | v1/scripts/wait_for_land_slot.py | BUILT | `frob land --wait <secs>` with bounded retry (v2/crates/frob-land/src/plan.rs RetryPolicy, lock.rs). FIFO fairness for lease waits is ticketed: ~3WMXBBJ. |  |
| C-29 | frob deploy generate: compile std.host manifests into idempotent install/status/uninstall bash and PowerShell, DEPLOY001-003 drift locks. Reproducible host provisioning from the design model. | v1/src/frob/deploy/_generate*.py; docs/modules/deploy.md; docs/commands/deploy.md | DROPPED | v2/docs/design/cli.md s4 removed list ('deploy'); grimble-model.md s2 (host, krb, deploy dropped from the grammar); notes/v1/cli-surface.md s5 ('DROP: VM deploy; out of scope'). |  |
| C-30 | frob deploy audit --vm: VirtualBox snapshot-diff proof that an install leaves no artifacts. Attestation of artifact-free install. | deploy/_audit.py, _vm_runner.py | DROPPED | Same as C-29. |  |
| C-31 | frob mutate FILE -- TEST-CMD: AST mutation testing (flip comparison, swap operator, negate bool, mutate return), crash-safe backup journal. Honest test-quality oracle: surviving mutants are test gaps. | v1/src/frob/mutate/; docs/modules/mutate.md | DROPPED | v2/docs/design/cli.md s4 removed list ('mutate'); notes/v1/ops-and-integrations.md s2 verdict MERGE then DROP in cli-surface. |  |
| C-32 | Mutation score as ticket evidence (TEST016, sweep queue, security tickets run it inline). Closing a security/bug ticket needs proof the tests would catch a regression. | v1/src/frob/tickets/_mutation_evidence.py, _mutation_sweep_queue.py; gates/_mutation_evidence.py | MISSING | Searched 'mutation', 'mutants', 'cargo-mutants' in v2 docs/design and crates: none. The `command` evidence provider (v2/crates/frob-evidence/src/provider.rs) could carry cargo-mutants but no provider, rule or guidance exists. | P-24 |
| C-33 | Enforced property fuzzing: FUZZ001-003, Arbitrary registry, .frob/fuzz-stamp.json. Fuzz obligation per invariant-anchored function. | v1/src/frob/fuzz/; docs/modules/fuzz.md | MISSING | Searched 'fuzz', 'proptest', 'property test' in v2 design: only proptest as a test tool (build-test-ci.md s2). Notes verdict DROP (opt-in, off by default, hypothesis-only) is in notes/v1/gates-and-rules.md s8 and ops-and-integrations.md s3.6 but not in the D1-D87 log. Not worth a ticket (see OQ-5). |  |
| C-34 | CVE Record v5 parser and cvelistV5 mirror walker. Offline CVE matching for dependencies. | v1/src/frob/cve/; docs/modules/cve.md | TICKETED | Advisories (OSV, RustSec) in grimble-vet: ~RPQKHAV; v2/docs/design/boundaries.md grimble-vet row. The local cvelistV5 mirror is dropped (notes/v1/ops-and-integrations.md verdict 'drop local mirror'). |  |
| C-35 | frob vet: dependency capability scan (exec/net/fs/env/ffi/install-hook/obfuscation), allowlist + age quarantine, typosquat, lifecycle scripts, lockfile conformance. Supply-chain defence by capability diff across versions. | v1/src/frob/vet/ (50 files, 20k lines); docs/modules/vet.md | TICKETED | ~RPQKHAV 'grimble vet'; boundaries.md grimble-vet row; cli.md `grimble vet [--hook]` milestone 2. Acceptance must include SB-8 (never approve unread source). |  |
| C-36 | frob vet --hook COMMAND: PreToolUse check of an install-shaped shell command. Blocks `npm i evil` before it runs. | vet/_hook.py | TICKETED | ~RPQKHAV (vet --hook mode in boundaries.md); the invoking `frob hook pre-tool` is C-23 (DESIGNED, unticketed). |  |
| C-37 | frob refactor: transactional move/rename/split that rewrites imports, frob:doc/tests directives, waiver symrefs, registry rows, prose anchors. A move does not orphan frob bookkeeping. | v1/src/frob/refactor/ (25 files, 6.9k lines); docs/design/refactor-verb.md | DROPPED | v2/docs/design/cli.md s4 removed list ('refactor'). Source rewrites are rust-analyzer's job (goals.md non-goal). |  |
| C-38 | Refactor residue: after a move, carry acks and repoint dangling frob: targets to the renamed symbol. Rename without re-acking everything. | refactor/_scan_repoint.py; graph/lock ack-carry rule | MISSING | Detection is DESIGNED (rules.md DRIFT 'dangling endpoint with rename candidates'; code-model.md s9 rename candidates; binding.md s5.4 grimble ack --rename). Repair is not: searched 'repoint', 'rename' in v2 crates: no machine fix for DRIFT002 or frob-owned directives. | P-21 |
| C-39 | frob map: whole-project structural map in about 200 tokens. Cheap orientation for agents. | v1/src/frob/map/, app/map_runner.py; docs/commands/map.md | DESIGNED | v2/docs/design/boundaries.md frob-explore row; cli.md `explore outline\|map\|xref\|docs` milestone 2. No ticket. | P-07 |
| C-40 | frob outline FILE: signatures, line numbers, first-sentence docstrings, no bodies. Skeleton reading instead of whole files. | v1/src/frob/outline/ | DESIGNED | Same as C-39. | P-07 |
| C-41 | frob xref SYMBOL: definition site and every referencing file/line. Find uses without an LSP. | v1/src/frob/xref/ (16 CLI calls in v1 telemetry) | DESIGNED | Same as C-39. | P-07 |
| C-42 | frob docs: docstring extraction, overview, full-text docs search, sync command pages. Query docs from the CLI; keep command pages generated. | v1/src/frob/docs/, app/docs_runner.py | DESIGNED | Search/overview: `explore docs` in cli.md (milestone 2). Generated command pages BUILT as `cargo dev gen cli` (v2/crates/gob-dev, documentation.md s3). | P-07 |
| C-43 | frob gitlog: git history summarized by conventional-commit type and granularity. Release-note-style history view. | v1/src/frob/gitlog/ | MISSING | Searched 'gitlog', 'conventional commit' in v2 docs/design and crates: only a commit-format convention (goals.md). Superseded for release notes by changelog fragments (`frob release changelog`). Not worth a ticket. |  |
| C-44 | frob stats: DORA-ish queue health and commit cadence (measurement only). Delivery trend view. | v1/src/frob/stats/; docs/modules/stats.md | DESIGNED | v2/docs/design/cli.md `stats` (frob-pm, milestone 2); architecture.md s5 ('frob stats mines it'). `cycle velocity` BUILT covers points per cycle. No ticket. | P-10 |
| C-45 | frob status: delta-first movement (findings burned/introduced, verification lag, landing velocity). What changed since yesterday. | v1/src/frob/app/status_runner.py; docs/commands/status.md | DESIGNED | v2/docs/design/cli.md `status` (frob-check, milestone 2). `frob board` and `release status` BUILT but cover other questions. No ticket. | P-10 |
| C-46 | Telemetry stream .frob/telemetry.jsonl (every invocation, redacted args, duration, exit, tree hash; gate rule firing counts). Evidence base for performance and usage analysis. | v1/src/frob/app/telemetry/, telemetry/__init__.py; docs/guides/agentic-time-profiling.md | BUILT | v2/crates/gob-check/src/telemetry.rs (`[check] telemetry`), gob-log redaction; architecture.md s5. Verb coverage beyond check is part of P-10. |  |
| C-47 | Footgun tips and `doctor --usage` (REDUNDANT_RERUN, FAST_EXIT1, REPEATED_FAILURE; top time sinks). Agent self-correction nudges from the local corpus. | app/telemetry; agentic-time-profiling.md 'Footgun detection' | MISSING | Searched 'retread', 'redundant', 'footgun', 'FAST_EXIT' in v2 docs/design and crates: none. Exit-code semantics (cli.md s2) remove the fast-exit-1 trap at source. Low value; fold into P-10. | P-10 |
| C-48 | Automatic per-ticket token accounting mined from harness transcripts at lease release (owner directive 2026-09-20). Cost per ticket without a model call. | v1/src/frob/tickets/_token_usage.py; tickets-lifecycle.md 'Automatic per-ticket token accounting (T-5137)' | MISSING | Searched 'token usage', 'tokens', 'cost' in v2 docs/design: pm-enforcement.md has points and velocity only; no usage field in v2/crates/frob-ledger model. No ticket. | P-09 |
| C-49 | Secret redaction of every stored command line, transcript and telemetry value. Secrets never reach logs, evidence or telemetry. | v1/src/frob/security/_redact.py | BUILT | v2/crates/gob-log/src/redact.rs; frob-evidence scrub (security.md s2.10). |  |
| C-50 | CI failure reporting and CI-result validity: gh seam, failures clustered by signature, NOT_RECOVERABLE never reads as zero, STILL_VALID/STALE/UNKNOWN per test against the current tree. 'What is failing' as a typed answer; a green run from three commits ago is never evidence for today. | v1/src/frob/ghio.py, ci_report.py, ci_validity.py; docs/modules/ghio.md etc. | MISSING | Only the tip-of-release slice exists: `release status` reads check runs through gh (v2/crates/frob-release/src/ci.rs, ~4PT3KZB). frob-gh HTTPS client ticketed (~YNC30Q8) for the mirror. Searched 'ci report', 'cluster', 'failure signature', 'stale evidence' in v2: none. v2 history shows the need (~AHBKXAZ, ~M4WWW00, ~RBF6057 CI-only failures). | P-15 |
| C-51 | Release: public-API semver class, stamp/check/sync/publish, changelog from fragments, version authority. Releases whose version and changelog are mechanically correct. | v1/src/frob/release/; docs/modules/release.md | BUILT | v2/crates/frob-release (bump, cut, changelog, status, adopt; REL001 tag provenance, REL002 lockstep, REL003 fragment). The API-diff-computed bump class (v1 REL001 'unbumped API') is DESIGNED only (rules.md REL row, code-model.md); not worth building before 1.0 (lockstep 0.x, releases.md). |  |
| C-52 | scripts/verify_release_ci_status.py: fail-closed CI status for the exact release SHA before upload. No release from a red or unknown tip. | v1/scripts/verify_release_ci_status.py | BUILT | v2/crates/frob-release/src/ci.rs (green/red/pending/unknown, unknown blocks unless `[release] require_ci = false`). |  |
| C-53 | scripts/artifact_smoke.py: built wheel installs, starts and reports healthy before upload. Catches packaging faults the source-tree CI cannot. | v1/scripts/artifact_smoke.py | BUILT | ~NWXQPMM done 'Artifact smoke script and fixture repository'; ~Y3S3WBF (five-target exit) todo. |  |
| C-54 | scripts/bump_version.py. Patch bump of the one version authority. | v1/scripts/bump_version.py | BUILT | `frob release bump` (v2/crates/frob-release/src/bump.rs, lockstep). |  |
| C-55 | scripts/branch_stranded_work_analysis.py: classify every local branch merged / ticket-done / stranded. Finds finished-but-never-landed agent work among ~1000 branches (188 stranded on 2026-08-25). | v1/scripts/branch_stranded_work_analysis.py; docs/audits/branch-stranded-work-2026-08-25.md; tickets/_unlanded.py | MISSING | v2 gc keeps a worktree whose branch holds commits that exist nowhere else (v2/crates/frob-worktree/src/gc/worktrees.rs) but only for ticket worktrees it still sees; branches without a worktree are never examined. Searched 'stranded', 'unlanded' in v2: none. | P-05 |
| C-56 | scripts/verify_lands.py and tickets/_unlanded.py: is a 'done' ticket's deliverable an ancestor of main. A Done report is not evidence; four tickets read done with nothing on main in v1. | v1/scripts/verify_lands.py; tickets/_unlanded.py; _journal.py | MISSING | CONFIRMED BY PROBE (SB-2): a ticket with a leased worktree branch holding an unmerged commit closed `done` via `frob ticket close`, `ticket doctor` stayed ok. Searched 'ancestor', 'merged', 'landed commit' in frob-ledger, frob-land, doctor: only gc and land check it. | P-01 |
| C-57 | frob clean: tiered, artifact-only cleanup (safe / --all / --deep), tracked files never removed. Reclaim disk without touching source. | v1/src/frob/clean/; docs/modules/clean.md | BUILT | ~BZXZK29 done: automatic GC (v2/crates/frob-worktree/src/gc: build output, worktrees, caches, artifacts; path jail; `doctor --fix`). No standalone `clean` verb; GC runs inside work/land/doctor. |  |
| C-58 | worktrees: disposable worktree sweep, `worktree sweep\|remove` with lease-aware liveness. No leaked scratch worktrees; never remove a live agent's checkout. | v1/src/frob/worktrees/; app/worktree_runner.py | BUILT | v2/crates/frob-worktree/src/gc/worktrees.rs (no --force, lease/dirty/unpushed checks, branch deleted only when merged). `worktree sweep\|remove` verbs in cli.md are not registered (gc is automatic). |  |
| C-59 | scaffold pool: pre-warmed worktrees with natives built. Leasing a worktree costs no build. | v1/src/frob/scaffold/_pool.py; docs/guides/worktree-pool.md | MISSING | Searched 'pool', 'warm worktree' in v2 design: none. Cost it addressed (maturin builds) is gone; sccache + shared cache make a fresh worktree ~58 s warm (owner memory). Not worth a ticket. |  |
| C-60 | scaffold managed boilerplate blocks + conformance, worktree lease hook install. Keep CONTRIBUTING/guide boilerplate in sync with the tool version. | v1/src/frob/scaffold/_managed.py | TICKETED | ~VFSTJNW 'Guide and .gitattributes installed from templates, refreshed on version change'; `frob init` BUILT (v2/crates/frob/src/init.rs). |  |
| C-61 | scaffold new TYPE NAME: project templates (python, cpp, ts, unity). Start a repo already wired for frob. | v1/src/frob/scaffold/project.py, data/ | MISSING | Searched 'scaffold', 'template' in v2 design: `init` adopts existing repos only. Not worth a ticket; `cargo new` + `frob init` covers Rust. |  |
| C-62 | Derived-state integrity: fingerprint every .frob artifact, refuse stale/corrupt caches before gates consume them. No confusing downstream findings from a corrupt cache. | v1/src/frob/derived_state.py, doctor.py | TICKETED | ~TX6YZZE in-progress (MAC'd store outside the work tree), ~H2DAC49, ~FSG8SMS; cache doctor in v2/crates/frob/src/doctor.rs CacheInfo. |  |
| C-63 | Global-binary skew guard: installed frob on PATH vs the repo's version/CLI surface, with remediation. A stale global binary cannot silently give wrong answers. | v1/src/frob/doctor.py::global_binary_skew; app/_version_guard.py; docs/guides/frob-version-policy.md (249-version gap) | MISSING | v2 doctor checks only the merge driver resolves to the running frob (v2/crates/frob/src/doctor.rs DriverCheck). Observed now: PATH `frob` is v1 0.531.1.dev351 inside the v2 repo. Searched 'min_version', 'required_version', 'skew' in v2: only tool-stage min_version (gob-check). | P-13 |
| C-64 | doctor: external tool inventory (REQUIRED / OPTIONAL / REQUIRED_FOR_FAMILY with version probes and remediation). One place that says which tool is missing and why it matters. | v1/src/frob/doctor.py::scan_external_tools; docs/modules/doctor.md | MISSING | v2 doctor reports toolchain, git, cache, config, ledger, driver, siblings, gc; a configured `[[check.tool]]` whose binary is absent surfaces as a TOOL finding (fixed by ~APQCEPT) but doctor does not inventory them. | P-13 |
| C-65 | doctor: Unity editor, venv shim drift, native-extension presence, lint-tool version lag. Python/Unity toolchain health. | v1/src/frob/doctor.py (Unity, venv, natives, PyPI/npm lag) | DROPPED | Python packaging and Unity: cli.md removes natives, whereis; notes/v1/cli-surface.md s5; B11 in binding.md defers the asmdef generator to packs. |  |
| C-66 | Land profiles (rapid / standard / fortress) and the one-way auto-ratchet. Small repos skip heavyweight land ceremony. | v1/src/frob/tickets/_profile.py; docs/modules/land-profiles.md | DESIGNED | v2/docs/design/rules.md s7 ('Profiles collapse'). ~YPHN173 is a different 'profile' (newcomer vs experienced). No ticket; low value while land takes seconds. |  |
| C-67 | frob run NAME / frob build: execute a frob.toml [commands] entry (unwired in v1). Named task runner. | v1/src/frob/app/run_runner.py | MISSING | Not wired in v1 and unused in telemetry; `cargo dev ci` is the v2 task runner (build-test-ci.md s4). Not worth a ticket. |  |
| C-68 | frob natives: maturin build of declared [[native]] crates with a shared target dir. Build Python extensions per worktree. | v1/src/frob/natives/ | DROPPED | v2/docs/design/cli.md s4 removed list ('natives'); no Python extensions in v2 (D87 ships prebuilt wheels). |  |
| C-69 | frob exports: generate __init__.py from public symbols. Python packaging convenience. | v1/src/frob/exports/ | DROPPED | cli.md s4 removed list ('exports'). |  |
| C-70 | frob process reap and process locks: orphaned multiprocessing forkserver cleanup, derived-state locks. Python process hygiene. | v1/src/frob/process/ (_reap, _lock, _guard); docs/modules/process.md | DROPPED | cli.md s4 removed list ('process'); rules.md ('forkserver' dropped); architecture.md ('no derived-state lock dance across worker processes'). |  |
| C-71 | Tool-output parsers (pytest, ruff, ty, clang, clang-tidy, eslint, tsc, cargo, junit, valgrind) normalizing to one finding shape; per-language lint/format/typecheck stages. frob check runs the language's own tools and reports them in one shape. | v1/src/frob/process/parsers/; check/_python.py, _native.py, _ts.py | DESIGNED | v2/docs/design/git-io.md s3 ([[check.tool]] for ruff, clippy, tsc, cargo doc, ...), cicd.md s6. Built parsers: zizmor and actionlint only (v2/crates/gob-check/src/tool_parse.rs). No ticket for cargo/clippy JSON, SARIF, junit parsers. | P-20 |
| C-72 | Language front end: Rust, Markdown, TOML adapters (tree-sitter, bounded). Parse-based symbols, edges, directives. | v1/src/frob/lang/ (22 files) | BUILT | v2/crates/gob-languages (default features rust, markdown, toml), gob-symbols (rust.rs, markdown.rs). |  |
| C-73 | Language front end: Python, TypeScript/JS, C/C++/CUDA, Java/Kotlin, C#, Zig, Bash, HTML/CSS/Vue walkers. Obligation gates (DOC/COV/DRIFT/AFFECT/TEST) on non-Rust repos; the estate is Python/C++/TS. | v1/src/frob/lang/_walk_*.py (14 walkers); estate evidence: 7 of 9 fleet repos are Python-dominant | DESIGNED | v2/docs/design/code-model.md s3 lists the grammar features (python, ts, c-family, jvm, dotnet, misc) but gob-languages ships only rust/markdown/toml and no ticket builds first-party adapters; the only related tickets are tier-4 WASM adapter packs (~8HJZ9MP low, ~AHY68NM low). On a Python repo v2 reports the files as opaque F0 (verified, SB-1 probe). | P-03 |
| C-74 | GitHub Actions and Dockerfile as languages. CI policy and CI-to-repo consistency rules. | v1 had none (v2 addition, listed for completeness) | TICKETED | ~83EFRF2, ~WHCDCMG, ~8886VJ4 (grimble-ci). |  |
| C-75 | Obligation graph: build, cache, digests, directive DSL, lock/acks, affects, reach, summary. The binding between code, docs, tests and tickets. | v1/src/frob/graph/ (16 files) | BUILT | v2/crates/gob-symbols, gob-directives, gob-lock, frob-ack (`ack`, `graph why\|affects`), frob-tests/src/reach.rs. |  |
| C-76 | frob cycle: import-cycle detection with cut-point hints. Find dependency cycles. | v1/src/frob/cycle/, graph/DependencyGraph | TICKETED | ~1QBHP7T G10 (grimble-arch: CYCLE, LARGE, DEAD). |  |
| C-77 | arch metrics core: long functions, god classes, nesting, coupling, large files, [arch.layering]. Structural size/complexity/layering limits. | v1/src/frob/arch/ (_python, _layering, _smells); docs/modules/arch.md | DESIGNED | v2/docs/design/boundaries.md grimble-arch ('metrics core (size, nesting, LCOM, coupling), layering contracts'), rules.md. G10 ~1QBHP7T title lists only CYCLE, LARGE, DEAD, so ARCH metrics and layering are unticketed. | P-19 |
| C-78 | arch design-pattern recommender, SOLID/SRP/OCP smells, abstraction opportunities. Advisory design hints. | arch/_patterns.py, _ocp.py, _srp.py, _solid.py | DROPPED | Subjective smells replaced by the NEAT family (D59, neatness.md); notes/v1/gates-and-rules.md s8 verdict DROP for ARCH102/103. |  |
| C-79 | arch concurrency, async hazards, lock ordering, shared-state race, may-raise and fallibility analysis, FFI declared-raises. Python/C++-specific concurrency and exception audits. | arch/_concurrency*.py, _async_hazards.py, _lock_ordering.py, _mayraise*.py, _ffi.py | DROPPED | v2/docs/design/rules.md ('Dropped from core: ... EXHAUST/FFI ...'; typestate PROTO unless a consumer commits); Rust's type system and clippy cover the class. |  |
| C-80 | dup: clone rungs R1 (exact), R2 (renamed), R1.5 (suffix array regions), R3 (canonical AST), R4 (winnowing + tree edit distance), R5 (WL graph kernel); frob-core native kernels; DUP001/002 enforcement. Duplicate-introduction gate that points at the thing to reuse. | v1/src/frob/dup/ (19 files); v1/frob-core/src (r3, r4, r5, exact_regions, callgraph); docs/modules/dup.md | DESIGNED | v2/docs/design/boundaries.md grimble-arch ('dup rungs R1-R5'), rules.md DUP family. No crate and no ticket (G10 excludes DUP). | P-19 |
| C-81 | dup R6 observational equivalence (executes candidate functions via importlib, no sandbox) and R7 bounded SMT. Type-4 clone evidence. | dup/_pipeline (R6, R7); docs/modules/dup.md | DROPPED | Not carried: rules.md lists R1-R5 only; executing repository code unsandboxed is excluded by D82 (security.md invariants). |  |
| C-82 | frob bind: cross-language signature binding (frob:binds), BIND family. Rust/Python (PyO3) signature drift. | v1/src/frob/bind/, app/bind_runner.py | DESIGNED | v2/docs/design/code-model.md s6 (binds edges), boundaries.md BIND row (graph). No ticket; needs a second language adapter first (C-73). |  |
| C-83 | perf: cProfile heat-map, sampler hot-graph, PERF001-018 lexical smells, bench ratchet PERF009. Find hot AND quadratic code. | v1/src/frob/perf/ (21 files); docs/modules/perf.md | DROPPED | cli.md s4 removed ('perf'); rules.md ('PERF lexical set' dropped). Criterion bench regression ratchet is in architecture.md s9 and CI (build-test-ci.md s4). |  |
| C-84 | policy: user-defined rules from frob.toml [policy] (forbidden-import, tree-sitter pattern, diff-shape norm, POL000 zero-match). Repo-specific rules without code. | v1/src/frob/policy/ | TICKETED | GRL epic ~D05GDWP and ~JDDEB70 (GPOL); `diff.changed` side relation in grl-spec.md s341; zero-match = Unresolved in grl-spec. |  |
| C-85 | registry: typed exhaustiveness registries (docs/design/registry/*.yaml), `registry audit`, REG gates. Prove a taxonomy (e.g. CWE, compliance) is fully dispositioned. | v1/src/frob/registry/; docs/design/registry/ (14 files) | DESIGNED | v2/docs/design/rules.md REG family ('enforces-site present'); no ticket. The v1 corpora themselves are not copied (OQ-6). |  |
| C-86 | narrative: NARR001 detector and `narrative move` migration of # T-####: comment blocks into the ticket. Keeps ticket narrative out of code. | v1/src/frob/narrative/; scripts/count_ticket_citations.py, strip_help_citations.py | DESIGNED | v2/docs/design/documentation.md s4 (NARR rules), cli.md `narrative move`. No ticket. | P-25 |
| C-87 | webapp families (WEBSEC 108, A11Y 35, SQL 30, SEO 27, COMPLY 27, LAYOUT, WEBPERF) and the frob.sql stub. Web-app security/accessibility/compliance checks. | v1/src/frob/webapp/ (38 files), sql/; docs/modules/webapp-*.md (40 pages) | DROPPED | v2/docs/design/rules.md ('Dropped from core: web families (249 ids)'); packs.md is the later home if a consumer commits. |  |
| C-88 | Design-model language and parser (.strata): grammar, lexer, elaboration, formatter. Architecture/threat model as code. | v1/strata-core/src/parse/*, lib.rs (14.7k Rust lines in both cores); v1/src/frob/strata/_parse.py | BUILT | v2/crates/grimble-model (G08 done: parser, printer, fmt, U adapter), grimble (G09 done); grmb-spec.md. |  |
| C-89 | Design-model kernel: closure, vmodel, claims, proof engine, counterexample paths. Prove or refute design claims. | v1/strata-core/src/graph/*; strata/_obligation_proof.py | TICKETED | ~QNDWNDM G16 'kernel port: CLAIM and VMOD families'. |  |
| C-90 | Capability matrix, deny-by-default, shrink (drop unobserved `may`). Declared-plus-proven capabilities. | v1/src/frob/strata/_shrink.py, vet/_capability*.py | TICKETED | ~V56RXG4 G14, ~71BAAE0 G15; D75. |  |
| C-91 | Catalogs as data: threat (CWE), compliance, PII, secrets, CVE fingerprints, benign capabilities. Obligation sets for the design model. | v1/src/frob/strata/_threat*.py, _compliance.py, _pii.py, _secrets.py; docs/guides/extending/* | TICKETED | ~HC9450N 'Tier-1 pack content'; packs.md atoms with CWE basis. |  |
| C-92 | Design-model host/krb/deploy/CDN/queue/cache grammar and `sys export` (k8s/seccomp/iam skeletons), `sys plan` ticket compiler. Deployment and infra modeling. | v1/src/frob/strata/_host*.py, _krb*.py, _deploy.py, _export.py, _plan.py | DROPPED | v2/docs/design/grimble-model.md s2 ('Dropped from grammar: host, krb, deploy ...'), binding.md B8 (`frob sys plan` frontier DROPPED). |  |
| C-93 | Migrate v1 .strata files. Adopt grimble on existing designs. | v1/design/frob.strata | TICKETED | ~T0GMFJA G18; migration.md s1 row `design/*.strata`. |  |
| C-94 | testing: touched-set selection (graph reach plus unique-name caller backstop). Run only tests that reach the change. | v1/src/frob/testing/_select.py | BUILT | v2/crates/frob-tests (select.rs, reach.rs, touched.rs, catalog.rs, lease.rs); D48. |  |
| C-95 | testing: coverage stamp/refresh/wait, incremental coverage, TEST005 floor ratchet, stamp freshness. Floors that only move up, proven by a coverage run. | v1/src/frob/testing/_coverage_*.py; gates/_coverage.py; docs/design/test005-ratchet-schedule.md | DESIGNED | v2/docs/design/rules.md TEST/TDD row ('binding resolves, floors, stamp freshness'); no coverage tool in frob-tests, no rule, no ticket. | P-11 |
| C-96 | testing: per-language runner registry ([[test.runner]]: pytest, jest, ctest, dotnet, kotlin, Unity batchmode). frob test works on non-Rust repos. | v1/src/frob/testing/_runners.py, _collect_*.py | MISSING | frob-tests drives nextest only; `command` provider can run anything but selection needs adapters. Depends on C-73. Folded into P-03. | P-03 |
| C-97 | testing: flake quarantine and verify sweep disposition. Ticket-bound quarantine instead of silent skip lists. | v1/src/frob/testing/_stability.py; verify/_quarantine.py | DESIGNED | v2/docs/design/rules.md s6 ('Quarantine ... milestone 2 or later', frob-quarantine.json, disposition verb); no ticket. | P-26 |
| C-98 | verify: deferred-verification queue, watermark, coalescing worker, bisect, backpressure, rapid debt. Land fast, verify after. | v1/src/frob/verify/ (9 files); docs/modules/tickets-verify-sweep.md | DROPPED | v2/docs/design/README.md D8; rules.md s6 and tickets.md s10 ('deferred-verify machinery ... is not built'). |  |
| C-99 | gates: --fix engine tiers A/B/C and fix-it hints. Mechanical fixes applied; the rest as structured fix-its. | v1/src/frob/gates/_fix_engine*.py; docs/design/check-fix-engine.md | TICKETED | ~R5QDX7H `check --fix`, ~DW4RJVG applicability, ~C63ZWCR interactive; v2/crates/frob-check Fix tier A BUILT (~NGE3P2T done). |  |
| C-100 | gates: secrets and PII structural scans (SEC001 credential text, SEC002 tracked .env, SEC003 unwaivable live keys, PII010/011). Never commit secrets; the owner's global rule is that .env is always gitignored. | v1/src/frob/gates/_secrets.py, _pii_structural.py; notes/v1/gates-and-rules.md s10 (KEEP) | DESIGNED | v2/docs/design/boundaries.md grimble-security row and rules.md SEC/PII row. No crate and no ticket; v2 only redacts (gob-log). Searched crates for 'PRIVATE KEY', '.env' tracked checks: only redaction. | P-12 |
| C-101 | gates: ratchet pool, baseline, `pool snapshot\|clear`, --census waive-rate, land-parity. One-way shrinking debt with mandatory reasons. | v1/src/frob/gates/_ratchet.py, _baseline.py; app/pool_runner.py | BUILT | Ratchet BUILT: v2/crates/frob-land/src/ratchet.rs (fingerprint ratchet vs base tip, ~QAFRXM3). The tracked baseline kind and pool verbs are DESIGNED as exceptions (exceptions.md, cli.md says `pool` is replaced by `exceptions`); `--census` is designed (rules.md s4 step 6), not built. |  |
| C-102 | gates: waivers (frob:waive), waiver audit, expiry, ticket-bound exits, live-tracker close guard. Honest, expiring exceptions; closing a ticket cannot orphan a deferral. | v1/src/frob/gates/_waive*.py; tickets/_live_tracker.py | TICKETED | EXC001/003/005/007 BUILT (D45, v2/crates/frob-obligations/src/exc.rs); ~B7VH1B4 until=, EXC016/017; exceptions.md. |  |
| C-103 | gates: DOC/COV/DRIFT/REF/TODO/INV/SCOPE/TICK/PM core rules and the ~667-id registry. The obligation graph's enforcement surface. | v1/src/frob/gates/ (126 modules); notes/v1/gates-and-rules.md | BUILT | Core subset BUILT: v2/crates/frob-obligations (COV, DOC, INV, REF, TODO), frob-ack (DRIFT, AFFECT), frob-check/src/scope.rs (SCOPE001), frob-pm (PM); decisions in notes/v1/gates-and-rules.md s18 (145 KEEP, 144 MERGE, 378 DROP). Slice B owns the per-id audit. |  |
| C-104 | gates: NEW-GATE-RULE acceptance (a rule needs a fixture that fails before and passes after through the production path). Rules that are actually wired. | v1/src/frob/tickets/_new_gate_rule_acceptance.py | TICKETED | Executable rule docs via gob-mdtest (BUILT, D51); ~VB2EYG6 example runner, ~QMW7215 `rule test`. |  |
| C-105 | tickets: land pipeline, intent journal, crash recovery, post-land verification. A killed land is recoverable. | v1/src/frob/tickets/_land*.py, _journal.py; docs/design/land-checkpoint-durability.md | BUILT | v2/crates/frob-land/src/land.rs (recover_stale: crash after CAS resumes with `frob land`), lock.rs; tickets.md s10. |  |
| C-106 | tickets: merge queue, land splice, test-then-impl commit split, ledger mirror commits. Serial drainer; curated history. | v1/src/frob/tickets/_land_queue.py, _land_splice.py | DROPPED | README D7, D25 (no merge queue daemon, no splice); ledger off the code branch (D79) removes bookkeeping commits, so ff-merge of the ticket branch keeps real history. |  |
| C-107 | tickets: worktree-lease guard (FROB_WORKTREE) against mutating the shared root checkout. A stray command cannot touch main's tracked state. | v1/src/frob/tickets/_worktree_guard.py | DESIGNED | D23: ledger commits are built from the ref's tree, never an index (README D23); source-edit guard is a harness hook (C-23). |  |
| C-108 | tickets: provisional draft ids, renumber, promote. Collision-proof ids across worktrees. | v1/src/frob/tickets/_provisional.py, _new_renumber.py | DROPPED | README D2, D24 (ULIDs, no counters, drafts, promote, renumber). |  |
| C-109 | tickets: sprint/flow analytics, velocity. Burn-down and throughput. | v1/src/frob/tickets/_flow.py, _sprint.py | BUILT | v2/crates/frob/src/cycle_cmd.rs (`cycle velocity`, plan, assign), frob-pm. |  |
| C-110 | tickets: append-shared registry files exempt from whole-file lease exclusivity. Parallel agents can append to the same registry file. | v1/src/frob/tickets/_registry_files.py | BUILT | `[lease] shared_files` (README D39; v2/crates/frob-lease/src/overlap.rs). |  |
| C-111 | tickets: attach files/clipboard images, wave partition, anchors, runs-last, archive, tokens, review verbs. Ticket ergonomics for agent fleets. | v1/src/frob/tickets/_reporting_attachments.py, _doable.py (wave), _archive.py | DESIGNED | v2/docs/design/tickets.md s11 and cli.md list `wave`, `attach`, `query`, `log`, `review`; none registered (v2/crates/frob/src/ticket/mod.rs registers new/update/link/unlink/comment/close/drop/reopen/show/list/doable/brief/fragment/doctor/merge-driver/evidence). No tickets. Slice A owns the ticket detail; `wave` is P-08. | P-08 |
| C-112 | render, color, logging, findings model, excludes, gitio, tomlio, yamlio, nodeid, repo_meta. Output, logging and substrate helpers. | v1/src/frob/render, logging, findings.py, excludes.py, gitio.py ... | BUILT | v2/crates/gob-cli (render.rs, --color, --format), gob-log, gob-diagnostics, gob-git, gob-walk; per-verb text renderers ~5GVGHPT todo. |  |
| C-113 | agent: `agent brief TICKET`, `agent env` (FROB_WORKTREE/FROB_AGENT exports). Dispatch brief and agent shell env. | v1/src/frob/agent/; docs/commands/agent.md | BUILT | `frob ticket brief` (v2/crates/frob/src/ticket/read.rs Brief); FROB_AGENT actor label (tickets.md s3); ~YSQ16NG brief hardening. |  |
| C-114 | frob-core Python-specific kernels: capability_python, arch_python, extract, callgraph name resolution. Native speedups for the Python engine. | v1/frob-core/src/{capability_python,arch_python,extract,callgraph}.rs | DROPPED | Replaced by gob-symbols over U (D56); Python engine gone. |  |
| C-115 | Packaging: abi3 wheels for frob + natives across five platforms, install/PATH skew docs. pip/uv install of one tool. | v1/docs/guides/install.md; .github/workflows/release.yml | BUILT | D87 and v2 release workflow (cargo-dist + wheels); ~0JTYGH0 crates.io first publish in-progress. |  |
| C-116 | Portability boundary (Windows advisory leg, macOS required leg) and Windows kill/lock handling. Works on three OSes. | v1/docs/design/windows-portability.md, macos-portability.md | BUILT | v2 CI matrix linux/macos/windows (build-test-ci.md s4), path discipline D86 (~ATR5EP7 todo), ~G5RJY40 done. |  |
| C-117 | Research corpora: CWE-1000 dispositions (944), compliance, supply-chain, secrets/PII, capability-evasion taxonomy, design-pattern and system-design catalogs, exhaustiveness registry. Denominators for packs and detectors. | v1/docs/design/*-corpus.md, cwe-1000-registry.md, capability-evasion-taxonomy.md; docs/design/registry/*.yaml | MISSING | Not copied into v2; v1 is to be archived as a `v1` branch (migration.md s2 step 4) so the corpora stay readable, but nothing in v2 links them as inputs of ~HC9450N tier-1 pack content or the detector work. See OQ-6. |  |
| C-118 | Python API reference and public-API-from-wheel test. Library users' import contract. | v1/docs/guides/python-api.md; tests/system/test_public_api_from_wheel.py | DROPPED | No Python library surface in v2 (goals.md non-goal 'Python interop in the core'). |  |

## 4. Proposed tickets

Priority scale follows the ledger (low, medium, high, critical). Types follow v2 (bug, task, story). All acceptance is Given/When/Then. Summary order by priority: P-01 (high), P-02 (high), P-03 (high), P-04 (medium), P-06 (medium), P-08 (medium), P-09 (medium), P-10 (medium), P-11 (medium), P-12 (medium), P-13 (medium), P-15 (medium), P-16 (medium), P-19 (medium), P-22 (medium), P-23 (medium), P-05 (low), P-07 (low), P-14 (low), P-17 (low), P-18 (low), P-20 (low), P-21 (low), P-24 (low), P-25 (low), P-26 (low), P-27 (low).

### P-01: ticket close refuses done while the ticket branch holds commits that are not on the base; doctor flags done tickets whose work is absent

- Type: bug. Priority: high. Covers: C-56, SB-2.
- Why: v1 incident: a ticket read `done` with its whole deliverable absent from main, four separate times (v1/scripts/verify_lands.py, tickets/_unlanded.py, T-1934 'finished-but-unlanded branch work'). Reproduced against v2 today: in a scratch repo, `frob work`, a commit on `ticket/<h>`, then `frob ticket close <h> --outcome done --no-changelog --reason x` from the root checkout succeeded and `frob ticket doctor` reported ok while the commit exists on no other ref. `land` is the only path that merges, but close does not require that path. Silent-zero class: a closed ticket is read as delivered.
- Acceptance:
  - Given a ticket with a live lease whose branch has a commit not reachable from the base, When `ticket close --outcome done` runs, Then it exits 3 with `E-CLOSE-UNLANDED` naming the commit count and the remedy `frob land <h>`, and no event is written.
  - Given the same ticket, When closed with `--abandon-branch --reason R`, Then an audited `branch-abandoned` event records R and the unmerged tip oid, and the close succeeds.
  - Given a done ticket whose recorded land commit (or lease branch tip) is not an ancestor of the base, When `ticket doctor` runs, Then it reports a TICK-family finding naming the ticket and the missing commit.
  - Given a ticket closed `wont-fix` or `invalid`, Then the guard does not apply.

### P-02: Unreadable (non-UTF-8) tracked files are an Unresolved finding, not a log line

- Type: bug. Priority: high. Covers: SB-1.
- Why: Reproduced against v2 today: a tracked `bad.md` containing invalid UTF-8 produces byte-identical `frob check --json` output (counts, fidelity, findings) to the repository without the file; the only trace is a stderr WARN `unreadable file skipped` from v2/crates/gob-symbols/src/pipeline.rs, whose `skipped` counter is computed and never reported. v1 audit docs/audits/graph.md and lang-check-docs.md name this exact class ('parse/IO failures silently erase findings', 'non-UTF-8 .md hard-crashes'); README principle 'unmeasured is not zero' (D62).
- Acceptance:
  - Given a tracked file that cannot be read as UTF-8, When `frob check` runs, Then one Unresolved finding per file (or one parametric finding listing them, capped) is emitted with the path and the reason, marked required so `[check] fail_on_unresolved = "required"` fails the gate.
  - Given the same repository, Then `fidelity` in the JSON data counts the file as `unreadable` and `files_examined` excludes it.
  - Given the file is listed in `[check] exclude`, Then no finding is emitted.
  - A regression test in v2/crates/gob-symbols compares output with and without the file and requires a difference.

### P-03: First-party Python adapter (U terms, F3) in gob-symbols, then TypeScript and C-family; per-language test runners follow

- Type: story. Priority: high. Covers: C-73, C-96.
- Why: The owner's estate is Python and C++ heavy (fleet.toml lists 9 repos; counted tracked files: lithos 567 py, feldspar 201, typani 68, lograder 253, aprog-public 302 py + 117 C++, aprog-private 146 py + 368 C++, logand.app 266 py + 106 ts, crunk 214 py). v2 ships rust/markdown/toml only; every other file is opaque F0 and DOC/COV/DRIFT/TEST/INV report Unresolved (verified in a scratch repo). code-model.md s3 already lists the grammar features but no ticket builds the adapters; ~8HJZ9MP and ~AHY68NM are low-priority WASM tier-4 packs. The rollout in migration.md s2 (run both on typani and crunk) cannot compare findings otherwise. v1 evidence: v1/src/frob/lang/_walk_python.py and 13 more walkers.
- Acceptance:
  - Given a Python repository with `frob:doc`/`frob:ticket` directives, When `frob check` runs, Then `fidelity.languages.python` is F3 or better and DRIFT/COV/TODO rules are Exact rather than Unresolved.
  - Given a function whose signature changed, When `frob ack` and `graph affects` run, Then dependents in Python files are listed with Must/May confidence.
  - Given `frob test --base`, When the changed symbol is reached by a pytest function, Then it is selected (requires the runner follow-up).
  - Split into children: python adapter, ts adapter, c-family adapter, pytest/jest/ctest runner entries.

### P-04: frob-serve: stdio MCP server generated from Command metadata, read-only by default, with a tool-parity set and its own telemetry

- Type: story. Priority: medium. Covers: C-01..C-09, C-13, SB-3, SB-12.
- Why: v1 exposes 10 tools through `frob serve` (v1/src/frob/serve/server.py) and the owner's MCP config launches it; this session's own `frob` MCP server failed to connect, and the v2 binary has no `serve` (cli.md lists it milestone 2, boundaries.md names frob-serve, architecture.md s7 promises tools generated from `#[derive(Command)]`). Only grimble-serve is ticketed (~VXAYFQJ, low). Measured use is thin: in the local Claude Code transcripts, tool_use calls to frob MCP tools number 4 across 1,595 transcript files (daemon_status 2, check_scope 1, check_delta 1) against about 600 tool-list mentions each; the same scan shows 1 call to a serena tool, so MCP use in general is low (OQ-1). Hence medium, and a thin generated surface rather than a daemon.
- Acceptance:
  - Given `frob serve --mcp`, When an MCP client lists tools, Then the list is generated from the registered Command metadata and contains at least: ticket doable, check (with ticket/base/only), test (base), graph why, graph affects, graph query, and a drift query.
  - Given a verb whose envelope declares `requires_human` (attest, trust prompt, proposals accept), Then it is never exposed as an MCP tool, and a mutating verb is exposed only when `[serve] mcp_write = [verbs]` names it.
  - Given two identical tool calls with no edit between them, Then the second does not re-parse any file (spawn/parse counters in `--timing`).
  - Given any tool call, Then an entry is appended to the telemetry stream (so MCP use is measurable, unlike v1 where the CLI telemetry could not see it).
  - Given the MCP client has no `mcp` runtime, Then the CLI is unaffected (the server is a separate crate and feature).

### P-05: doctor and a branch report: stranded ticket branches (unmerged, no worktree) and merged branches that can be deleted

- Type: task. Priority: low. Covers: C-55.
- Why: v1 audit: 1,092 local branches, 258 merged, 646 ticket-done, 188 stranded (docs/audits/branch-stranded-work-2026-08-25.md, scripts/branch_stranded_work_analysis.py). v2 gc removes a worktree and deletes its branch only for a closed, merged ticket and keeps worktrees with unique commits, but it never examines `ticket/*` branches that have no worktree, so finished work whose worktree was removed by hand is invisible. Related to P-01 (close-without-land).
- Acceptance:
  - Given a `ticket/<h>` branch with no worktree, When `doctor` runs, Then it is classified merged, ticket-terminal-unmerged or stranded, with counts and the first stranded oids.
  - Given `doctor --fix`, Then merged branches of closed tickets are deleted and stranded ones are never touched.
  - The classification uses the ledger (ticket category) and `git merge-base --is-ancestor`, never message text.

### P-06: check --delta, check --files and check --sarif

- Type: task. Priority: medium. Covers: C-08, C-21.
- Why: The fast agent/editor loop and CI annotations. v1: `frob check --delta` and the MCP tool frob_check_delta (new-since-baseline findings), `--files` (restrict compute), v1/src/frob/app/check_runner.py. v2 designs all three (rules.md s4 and s6: per-checkout `.frob/baseline` of fingerprints, `--files`, `--sarif`) but `frob check --help` shows only --ticket --only --fix --fail-on --base --timing --explain. The land ratchet (~QAFRXM3) already computes fingerprint differences, so --delta is mostly plumbing.
- Acceptance:
  - Given a recorded baseline, When `check --delta` runs after one edit, Then only findings whose fingerprint is absent from the baseline are reported and the exit code follows `--fail-on` for those alone.
  - Given `--files a.rs b.rs`, Then per-file rules run on those files plus their dependents and repo rules still run once, and the output says what was suppressed.
  - Given `--sarif`, Then the output validates against the SARIF 2.1.0 schema with rule ids, locations, fingerprints and fix hints.

### P-07: frob-explore: graph query, explore outline|map|xref|docs as thin views over the symbol graph

- Type: task. Priority: low. Covers: C-05, C-39..C-42.
- Why: v1 gave agents token-cheap orientation (`map` about 200 tokens, `outline` skeleton) and `xref` (16 recorded CLI calls; map/outline 0 CLI calls in v1 telemetry, so low priority). Designed in cli.md and boundaries.md (frob-explore, grimble also exposes them), unticketed. Cheap once gob-symbols exists; also gives frob_graph_query parity for P-04.
- Acceptance:
  - Given a Rust file, When `explore outline <file>` runs, Then public and private (with --all) items are listed with signature, line and first doc sentence, no bodies.
  - Given a directory, When `explore map` runs, Then files, line counts and top-level symbols print within a stated token budget.
  - Given a symbol name, When `explore xref` runs, Then the definition and every referencing file:line are listed from the resolved graph, not text search.
  - Given `graph query <symref>`, Then outgoing and incoming edges with confidence are printed.

### P-08: ticket wave --agents N: partition doable tickets into scope-disjoint groups

- Type: task. Priority: medium. Covers: C-111.
- Why: The owner dispatches waves of 8-10 parallel agents and picks non-overlapping scopes by hand (memory: frob-v2-disk-guard 'Pick non-overlapping scopes per wave'). v1 `ticket wave` (v1/src/frob/tickets/_doable.py wave/wave_result) did the partition with the lease-collision helpers. Designed in tickets.md s11, cli.md and pm-enforcement.md s (wave sizing), not registered in v2. Slice A overlap.
- Acceptance:
  - Given N doable tickets with declared scopes, When `ticket wave --agents 8` runs, Then it returns up to 8 groups whose scopes are pairwise non-overlapping under the same overlap function as lease acquisition, preferring rank order.
  - Given a ticket whose scope overlaps a live lease, Then it is excluded and listed with the holder.
  - The output is deterministic for the same ledger and lease state.

### P-09: Automatic per-ticket token and cost accounting from agent transcripts

- Type: task. Priority: medium. Covers: C-48.
- Why: Owner directive 2026-09-20 (v1 T-5137): usage is set automatically at lease release, costs no model call, handles interrupted sessions, and lives in one abstraction behind a harness adapter (v1/src/frob/tickets/_token_usage.py; cursor cache; 2 s collection budget). v2 has points and velocity only. Needed for forecasting cost per point (pm-enforcement.md) and for the owner's token-cost visibility.
- Acceptance:
  - Given a lease window and a harness adapter, When a ticket leaves in-progress, Then input/output/cache-read/cache-create tokens summed over the sessions of that window are recorded as an audit event (not a field the fold trusts for state).
  - Given a 100 MB transcript already collected, Then re-collection reads only bytes past the cached offset and stops at a wall-clock budget with `complete=false`.
  - Given no transcript is found, Then no usage is recorded and the verb does not fail.
  - Transcript paths are read only from a configured allowlist of harness directories and never written to the ledger (privacy, D82).

### P-10: frob status and frob stats (delta-first movement, DORA-style delivery, usage and retread report)

- Type: task. Priority: medium. Covers: C-44, C-45, C-46, C-47.
- Why: v1 `status` (findings burned/introduced, landing velocity) and `stats` (queue health, commit cadence) plus `doctor --usage` (time sinks, redundant reruns). Designed (cli.md `status`, `stats`; architecture.md s5 'frob stats mines it') but unticketed; the telemetry writer exists (v2/crates/gob-check/src/telemetry.rs) and covers only `check`. v1 telemetry showed `check` 98 percent exit-1 and land polling dominated; v2's contract removes the causes, so build the reader after the writer covers every verb.
- Acceptance:
  - Given telemetry for all verbs, When `frob stats` runs, Then it reports invocations, median and p90 time per verb, failure and refusal rates, and the top time sinks.
  - Given two check runs on one tree, When `frob status` runs, Then it reports findings introduced, resolved and still-open by fingerprint since the earlier run.
  - Given the same command with the same args and tree hash run twice in a row, Then `stats --usage` lists it as a redundant rerun with wasted wall-clock.

### P-11: Coverage floors: a coverage provider, floor ratchet and stamp freshness (TEST005 equivalent)

- Type: task. Priority: medium. Covers: C-95.
- Why: v1 TEST005 branch/line coverage floors that only move up were judged 'proved valuable after real incidents' (notes/v1/ops-and-integrations.md s2.5; v1/src/frob/testing/_coverage_*.py, docs/design/test005-ratchet-schedule.md). v2 rules.md lists 'floors, stamp freshness' under TEST/TDD but frob-tests has no coverage tool, rule or knob. Use cargo-llvm-cov as an evidence provider; floors live in the tracked ratchet file.
- Acceptance:
  - Given `[testing] unit_branch_cov = 75`, When coverage measured on the touched crates falls below it, Then a TEST finding is raised at the configured severity.
  - Given a measured value above the floor, When `frob test --stamp-coverage` runs, Then the floor may only be raised and the stamp records tool, version and tree hash.
  - Given the stamp's tree hash differs from HEAD for the touched files, Then the rule reports stale-stamp, never pass.

### P-12: Secrets scanner rules SEC001-SEC003 (credential-shaped text, tracked .env, unwaivable live keys)

- Type: task. Priority: medium. Covers: C-100.
- Why: v1 KEEP set (notes/v1/gates-and-rules.md s10): SEC001 credential-shaped text in tracked files (Aho-Corasick plus entropy), SEC002 a tracked `.env`/`.env.*` file (trivial, high value; the owner's global rule is that .env is always gitignored), SEC003 live Stripe key or PEM private-key header, unwaivable. v2 designs grimble-security (boundaries.md) but has only output redaction (v2/crates/gob-log/src/redact.rs); no rule scans the repository. Reuse the redaction pattern table as the single source.
- Acceptance:
  - Given a tracked file `.env`, When `check` runs, Then SEC002 is an Error with remedy `git rm --cached` and a `.gitignore` line.
  - Given a tracked file containing `-----BEGIN PRIVATE KEY-----`, Then SEC003 is an Error that no exception can suppress.
  - Given a documented fake credential marked with the fake-secret directive and a reason, Then SEC001 is not raised for that line.
  - Detector patterns are shared with gob-log redaction (one table).

### P-13: doctor: refuse or warn on a stale frob binary (repo-declared min version) and inventory configured external tools

- Type: task. Priority: medium. Covers: C-63, C-64, SB-6.
- Why: v1 doctor/GlobalBinarySkew and app/_version_guard.py exist because a 249-version-stale global `frob` answered for the repo and three tickets were filed on the false premise that verbs did not exist (T-3129, docs/guides/frob-version-policy.md). v2 binary is also named `frob`; inside the v2 repo today `which frob` is v1 0.531.1.dev351 while v2 lives under target/. v2 doctor detects only a merge-driver mismatch. Add a materialized `[frob] min_version` that every verb checks (cheap string compare) and a doctor section listing each `[[check.tool]]` stage tool with found version, min/max and remedy.
- Acceptance:
  - Given `[frob] min_version = "0.540.0"` and a running binary 0.531.1, When any verb runs, Then it exits 3 `E-FROB-TOO-OLD` with the exact upgrade command, except `doctor` and `--version`.
  - Given a PATH `frob` that differs from the running one, When `doctor` runs, Then both versions and paths are shown.
  - Given a tool stage whose binary is missing or outside min/max, Then `doctor` lists it with the stage name and remedy and `check` reports TOOL001 as today.

### P-14: cargo dev gen editors: .grmb TextMate grammar generated from the keyword table, with a drift check and install notes for VS Code and JetBrains

- Type: task. Priority: low. Covers: C-19.
- Why: v1 shipped one TextMate grammar for .strata consumed by VS Code and (via TextMate Bundles) all JetBrains IDEs, drift-locked bidirectionally against the parser keyword table (v1/editors/*, tests/unit/test_strata_tmlanguage.py). v2 designs `editors/grimble.tmLanguage.json` generated by `cargo dev gen editors` (documentation.md s3, grmb-spec.md s2.6) but there is no generator and no ticket.
- Acceptance:
  - Given the Keyword derive in grimble-model, When `cargo dev gen editors` runs, Then `editors/grimble.tmLanguage.json` lists every declaration and clause keyword and nothing else.
  - Given a keyword added to the parser without regenerating, Then `cargo dev gen --check` fails (GEN001).
  - A docs page explains loading the bundle in VS Code and JetBrains.

### P-15: frob ci report: typed CI failure report (clusters by signature) and CI-result validity against the current tree

- Type: task. Priority: medium. Covers: C-50.
- Why: v1 incident: 156 macOS failures hand-extracted from a raw job log, a ~100-failure cluster mis-attributed for a whole investigation because an ubuntu job had been cancelled (v1/src/frob/ci_report.py, ci_validity.py, ghio.py). v2 has repeated CI-only surprises (~AHBKXAZ, ~M4WWW00, ~RBF6057, ~G5RJY40) and only a tip-of-release CI read (v2/crates/frob-release/src/ci.rs). Build on frob-gh (~YNC30Q8) rather than spawning gh.
- Acceptance:
  - Given a run id or a sha, When `frob ci report` runs, Then jobs, test failures clustered by normalized signature, and cancelled/unrecoverable jobs are listed; an unreadable summary is `not_recoverable`, never zero failures.
  - Given a green run at commit A and the tree at B, When `frob ci report --validity` runs, Then each test is STILL_VALID, STALE or UNKNOWN by whether any changed symbol reaches it (frob-tests reach).
  - All output is JSON-first with the standard envelope.

### P-16: Predictive rebase-conflict check for live leases (merge-tree) in lease list and doctor

- Type: task. Priority: medium. Covers: C-12.
- Why: v1 daemon rebase bot simulated merging main into every leased worktree branch with `git merge-tree` and exposed conflicts through frob_daemon_status (v1/src/frob/serve/_daemon.py::_poll_rebase_bot). v2 runs 8-10 parallel agents (owner memory) and `land` fails late with E-LAND-CONFLICT/E-LAND-STALE; `work` reports conflicts only at start. A read-only simulation is cheap with gix or one `git merge-tree --write-tree`.
- Acceptance:
  - Given a live lease whose branch would conflict with the current base, When `frob lease list --conflicts` runs, Then the paths and holder are listed and nothing is modified.
  - Given a clean branch, Then it is reported `clean`; a branch that cannot be simulated is `unknown` with the reason.
  - `doctor` shows the same count; the check never checks out or writes.

### P-17: Machine-wide named heavy-step slots (cross-process semaphore) for builds, tests and checks

- Type: task. Priority: low. Covers: C-17.
- Why: v1 daemon resource leases serialized the coverage run across worktrees with release-on-crash (v1/src/frob/serve/_leases.py, T-1097) and `check` warned about concurrent runs (T-2473). v2 has an in-process pool only (v2/crates/gob-exec/src/semaphore.rs). The owner's disk filled three times from parallel cargo builds and relies on a user hook plus a two-builder rule (memory frob-v2-disk-guard). A file-lock slot manager under the git common dir (N slots, FIFO, stale-holder reclaim by pid+start time) lets `work`, `test` and tool stages cap concurrent heavy steps without a daemon.
- Acceptance:
  - Given `[exec] heavy_slots = 2`, When three `frob test` runs start together, Then two run and one waits in FIFO order, printing who holds the slots.
  - Given a holder killed with SIGKILL, Then its slot is reclaimed within one probe interval and no slot leaks.
  - Given `--wait 0`, Then a busy slot exits 3 retryable with `retry_after_ms`.

### P-18: Optional hot-path producer: sampled stacks (perf/samply collapsed format) mapped to symrefs, queried by `frob perf hot`

- Type: task. Priority: low. Covers: C-10.
- Why: The owner's MCP set includes frob_perf_hot, backed by v1's sampled hot-graph store (v1/src/frob/perf/_hotgraph.py, _sampler.py, _sketch_store.py). v2 removed `perf` (cli.md) with no Rust replacement. Decide first (OQ-3): if heat-by-symbol is wanted, ingest an external profiler's collapsed stacks (samply, perf script, cargo flamegraph) and join them onto symrefs, instead of building a profiler.
- Acceptance:
  - Given a collapsed-stack file and the symbol graph, When `frob perf hot --from <file>` runs, Then rows {symref, samples, share} are ranked and symbols not in the graph are reported as unmapped, not dropped.
  - Given no profile data, Then the verb says so and exits 0.

### P-19: grimble-arch: metrics core (size, nesting, coupling, layering) and dup rungs R1-R5 beyond G10

- Type: task. Priority: medium. Covers: C-77, C-80.
- Why: G10 (~1QBHP7T) names CYCLE, LARGE, DEAD only. boundaries.md and rules.md also carry ARCH metrics, `[arch.layering]` (v1 ARCH104, KEEP) and DUP001/002 clone rungs ('clone detection is a product feature', notes verdict KEEP; v1/src/frob/dup, v1/frob-core r3/r4/r5/exact_regions). Native Rust kernels are the point: v1 needed PyO3 for R3+.
- Acceptance:
  - Given two functions that differ only by identifier names, When `check` runs on the diff, Then DUP001 names the existing symbol to reuse (R2).
  - Given a restructured but AST-equal clone, Then R3 reports it; R4/R5 are behind `[dup] rungs`.
  - Given `[arch.layering]` forbidding a crate-to-crate edge, Then the edge is an Error with the call site.
  - Rungs are content-addressed per file in gob-cache and run in parallel.

### P-20: Tool-stage parsers: cargo/clippy JSON, SARIF, junit; compact agent-readable text

- Type: task. Priority: low. Covers: C-71.
- Why: git-io.md s3 and cicd.md list ruff, clippy, tsc, cargo doc, hadolint, checkov, tflint as bound tools, but gob-check parses only zizmor and actionlint (v2/crates/gob-check/src/tool_parse.rs ToolParser). v1 had ten parsers normalized to one shape with a compact text view for agents (v1/src/frob/process/parsers). With SARIF as a parser, most CI linters become bindable by config alone.
- Acceptance:
  - Given a stage with `parser = "cargo-json"`, When clippy emits diagnostics, Then each becomes a finding with file, line, code and the tool's own help text, mapped through `id_map`.
  - Given `parser = "sarif"`, Then results map to findings by ruleId with level to severity.
  - A tool exiting non-zero with unparseable output is a TOOL002 Unresolved finding, never a pass.

### P-21: DRIFT002 machine fix: repoint a dangling directive target to its unique rename candidate

- Type: task. Priority: low. Covers: C-38.
- Why: v1 `frob refactor` existed because moves orphaned frob:doc/tests/waiver symrefs, registry rows and prose anchors (v1/docs/design/refactor-verb.md; incidents: 3 INV006 waiver carries in one wave, PII012 re-keying on every move). v2 reports dangling endpoints 'with rename candidates' but offers no repair, and source renames are the LSP's job. Provide the Fix with applicability `maybe-incorrect` (D78) only when exactly one symbol has the same body digest and kind.
- Acceptance:
  - Given a `frob:doc` directive whose target symbol was renamed with an unchanged body, When `check --fix` runs, Then the directive target is rewritten and the ack carried.
  - Given two candidates, Then no fix is offered and both are listed.
  - Given a changed body, Then the finding stays and names the nearest candidate.

### P-22: frob fleet status|route over fleet.toml, routing through each repo's ledger ref

- Type: task. Priority: medium. Covers: C-24, C-25.
- Why: The owner coordinates a 9-repo estate (v1/fleet.toml). v1 `fleet status` (reddest-first: branch, dirty, gate errors/warnings, doable count; v1/src/frob/fleet) and `fleet route` (file a ticket in a sibling's ledger) replaced hand-coordination from memory files. Designed (cli.md, boundaries.md frob-fleet, migration.md) and unticketed. v2 constraints: ledgers live on an orphan branch (D79) and a cross-repo write is a new privilege, so `route` must go through the sibling's own configured ledger ref and refuse repos with no ledger instead of bootstrapping one (v1 refused too).
- Acceptance:
  - Given a fleet.toml, When `fleet status --skip-gates` runs, Then every repo shows branch, dirty, doable count, or an error row, sorted reddest first.
  - Given `fleet route --repo X --title T`, Then a ticket appears in X's ledger via its `[tickets] ref`, with origin `agent`; a repo without frob.toml is refused with `E-NO-CONFIG`.
  - The probe runs the same frob binary as the caller, never a PATH frob (v1 doc: stale global gave wrong counts).

### P-23: frob hook <event>: one small binary for agent-harness guards, vet pre-tool check and telemetry hooks

- Type: story. Priority: medium. Covers: C-23, C-36.
- Why: v1 ran 14 Python hook scripts (about 4.6k lines) per Bash call. v2 designs one `frob hook <event>` (git-io.md s5, architecture.md s7, boundaries.md frob-hook; `pre-tool` invokes `grimble vet --hook`) but nothing is ticketed; v1 hooks keep running meanwhile (git-io.md). Overlaps slice D, listed so the MCP/daemon/hook triple is not lost.
- Acceptance:
  - Given a PreToolUse JSON payload on stdin for a Bash command that installs a dependency, When `frob hook pre-tool` runs, Then it asks `grimble vet --hook` and exits with the harness's block code and a reason when the command is unsafe.
  - Given a PostToolUse payload, Then one telemetry record is appended.
  - Cold start of the hook binary is under 20 ms (measured, spawn-budget test).

### P-24: Mutation evidence for security and bug tickets via cargo-mutants (evidence provider)

- Type: task. Priority: low. Covers: C-31, C-32.
- Why: v1 TEST016 required mutation evidence on security tickets and queued it for others, with `bug` survivors filing a bug ticket (v1/src/frob/tickets/_mutation_evidence.py). The honest-oracle argument (coverage and counts are gameable) still holds for Rust. A `mutants` provider next to nextest/command/file in v2/crates/frob-evidence/src/provider.rs scoped to touched files keeps it affordable; off by default.
- Acceptance:
  - Given `[evidence] mutation = ["security"]`, When a security ticket closes, Then a mutants run over its touched files is recorded as measured evidence and survivors above `[evidence] max_survivors` refuse the close with the list.
  - Given a timeout or tool absence, Then the record is unmeasured, never passed.

### P-25: NARR rules and `frob narrative move`; citation counters for generated help

- Type: task. Priority: low. Covers: C-86.
- Why: v1 NARR001 flags `# T-####:` comment blocks and `narrative move` relocates the text into the ticket (v1/src/frob/narrative; scripts/count_ticket_citations.py). Designed (documentation.md s4, cli.md) and unticketed; D20 makes it a rule family.
- Acceptance:
  - Given a comment block narrating a ticket, When `check` runs, Then NARR001 fires with a machine fix that moves the text to the ticket body (ticket context only) and leaves a one-line directive.
  - Generated `--help` and docs contain no ticket ids (count test).

### P-26: Flake quarantine and CI-result ingestion (milestone 2 of rules.md s6)

- Type: task. Priority: low. Covers: C-97.
- Why: v1 quarantine kept a flaky test visible and ticket-bound instead of a silent skip list (v1/src/frob/testing/_stability.py, verify/_quarantine.py). rules.md s6 defers it with the needed pieces named (frob-gh ingestion, tracked `frob-quarantine.json`, a disposition verb). Depends on ~YNC30Q8 and P-15; ~CE69AVN (flaky gob-cache test) is the live example.
- Acceptance:
  - Given a test failing then passing on retry in CI, When ingested, Then it is listed as flaky with the run ids.
  - Given `frob quarantine add <test> --ticket T`, Then the test is excluded from the gate while T is open and the exclusion expires when T closes.

### P-27: Shell completions and man pages generated from Command metadata

- Type: task. Priority: low. Covers: C-22.
- Why: v1 had did-you-mean and completions for argparse; v2 promises completions and man pages (cli.md s5, documentation.md s3) 'milestone 2 or later' with no ticket. Generated by `cargo dev gen cli`, shipped in the release archive.
- Acceptance:
  - Given a release archive, Then `completions/` has bash, zsh, fish and PowerShell scripts and `man/frob*.1` pages generated from clap metadata and checked by `cargo dev gen --check`.

## 5. Structural bugs

Each entry: the failure mode v2 must prevent, and whether v2's current design or code already prevents it.

### SB-1: Silent erasure of an unreadable file (CONFIRMED in v2 code)

- v1 evidence: v1 audits: docs/audits/graph.md 'a non-UTF-8 .md hard-crashes frob check'; lang-check-docs.md 'parse/IO failures silently erase findings'. Failure mode: a file the tool could not read contributes nothing and is not reported, so the result reads as clean.
- v2: NOT PREVENTED. Probe: scratch repo with tracked `bad.md` holding bytes `ff fe`; `frob check --json` output with and without the file is identical (counts, fidelity, findings). v2/crates/gob-symbols/src/pipeline.rs logs `unreadable file skipped` and increments `skipped`, which no caller reads. Contrast: oversize or timed-out parses are bounded and reported (v2/crates/gob-languages/src/parse.rs). Ticket P-02.

### SB-2: A ticket can be closed done while its work is on no mainline ref (CONFIRMED in v2 code)

- v1 evidence: v1 incident: 'a ticket read done with its entire deliverable absent, four separate times' (v1/scripts/verify_lands.py, tickets/_unlanded.py, T-1934). Failure mode: completion recorded in the ledger without the code being delivered.
- v2: NOT PREVENTED. Probe: `frob work`, commit on `ticket/<h>`, `frob ticket close <h> --outcome done --no-changelog --reason x` from the root checkout succeeded; `ticket doctor` ok; `ticket/<h>` not merged. Land checks and merges, but nothing forces close to go through land. v2 gc protects the branch (it keeps worktrees with unique commits) only while a worktree exists. Ticket P-01 and P-05.

### SB-3: MCP exposes verbs that D82 reserves for humans

- v1 evidence: v1 MCP was read-only by invariant (INV-021, v1/docs/modules/serve.md). v2 README D29 says `frob serve` is read-write behind a per-launch token and the token model is an HTTP design; a stdio MCP server is by definition driven by an agent, and security.md (no prompt is the only defence, TTY-only attestation, `requires_human`) does not mention MCP at all (searched security.md, goals.md, git-io.md, tickets.md for 'mcp').
- v2: NOT ADDRESSED in design text. Required by P-04: tools generated from Command metadata must skip `requires_human` verbs, default to read-only, and mutate only through an explicit allowlist.

### SB-4: Stale warm answers after an edit

- v1 evidence: v1 needed a git-status + (mtime,size) dirty key and a property test 'rebuilds iff tree changed' (serve.md Warm state); a cache hit on a changed tree is the vacuous-pass class.
- v2: PREVENTED by design and code: every run digests tracked files and keys artifacts by content digest and parser identity (rules.md s4 steps 1-3, D30, D38, v2/crates/gob-cache; ~M4T7MXR fixed autocrlf digests). If a daemon is ever built, git-io.md s6 already requires re-stat of inputs before answering.

### SB-5: Daemon operational failure modes

- v1 evidence: v1: leaked forkserver children (T-1378), competing for CPU, wedged-but-listening process, orphaned socket, version skew after upgrade, atexit joins hanging shutdown (v1/src/frob/_daemon_timeout.py).
- v2: PARTLY. git-io.md s6 names version/schema handshake and re-stat; it omits single-instance lock, idle exit, the Orphaned/Wedged liveness states (never spawn a rival to a wedged daemon), crash-safe resource release and a hard opt-out. Add these to the acceptance of any future daemon ticket. Rust removes the forkserver and atexit classes.

### SB-6: Stale global binary answering for the repo

- v1 evidence: v1 T-3129: global `frob` 0.530.0 and the repo's `uv run frob` printed the same version with different CLI surfaces; three tickets were filed on a false premise; 249-version gap measured (docs/guides/frob-version-policy.md).
- v2: NOT PREVENTED. v2 keeps the binary name `frob`; inside the v2 repo today `which frob` resolves to v1 0.531.1.dev351. `init` and `doctor` detect only a differing merge-driver binary (v2/crates/frob/src/doctor.rs). Ticket P-13.

### SB-7: A tool stage that cannot run reports nothing

- v1 evidence: v1 'unmeasured is not zero' class; v2 history ~APQCEPT.
- v2: PREVENTED: ~APQCEPT done (a tool stage that cannot run is now reported), TOOL002 for unparseable output (v2/crates/gob-check/src/tool_parse.rs fallback).

### SB-8: Dependency vetting approves code it never read

- v1 evidence: v1 audit docs/audits/vet.md: 'source-unavailable = empty caps', only the first lockfile scanned, rename/whitespace-evadable needles.
- v2: NOT YET SPECIFIED. ~RPQKHAV (grimble-vet) and boundaries.md do not say how an unreadable or unavailable dependency source is reported. Acceptance for that ticket: source unavailable = required Unresolved naming the package; every lockfile scanned; needle evasions covered by the capability-evasion taxonomy (v1/docs/design/capability-evasion-taxonomy.md, see C-117).

### SB-9: Vacuous passes

- v1 evidence: v1 audits gates-vacuous.md, gates-accounting.md, tickets-testing.md: gates green on empty diff/empty scope/stale cache; evidence means a test exists, not that it passed or reaches the code.
- v2: LARGELY PREVENTED: Unresolved/polarity (D62), subjects_examined (G06 done), bound means measured passing evidence (tickets.md s9), selection reach (frob-tests). Residual seen in probe: closing a chore with no acceptance criteria passes with only a warning `criteria_evidenced passed vacuously` (by D48, chores are exempt; acceptable but worth stating in `ticket close` output).

### SB-10: Executing repository code during analysis

- v1 evidence: v1 dup R6 `--probe` imports and runs candidate functions via importlib with no sandbox (v1/docs/modules/dup.md).
- v2: PREVENTED: R6/R7 not carried (C-81); D82 forbids loading anything executable from where the repository can write.

### SB-11: N+1 process spawns and file reads in a hot read path

- v1 evidence: v1 docs/audits/frob-blindspots-2026-07-23.md H1: `doable` spawned `git rev-parse --git-common-dir` and re-read every lease file once per candidate ticket.
- v2: PREVENTED: v2/crates/frob-lease/src/guard.rs takes one lease snapshot per call; spawn counts are snapshot-tested (git-io.md s7).

### SB-12: Usage telemetry blind to the MCP channel

- v1 evidence: v1 telemetry (.frob/telemetry.jsonl) recorded CLI invocations only, so the notes' usage statistics (notes/v1/agent-usage.md) say nothing about MCP use; the 'verbs never used' list could not see tools used over MCP.
- v2: NOT ADDRESSED. P-04 acceptance requires telemetry for MCP calls so the next usage study is complete.

## 5b. Open questions

- OQ-1. Is the 'owner sessions use the frob MCP tools' premise measured? A scan of the local Claude Code transcripts shows 4 tool_use calls to frob MCP tools in 1,595 transcript files (daemon_status 2, check_scope 1, check_delta 1) and 1 call to a serena tool, against roughly 600 tool-list mentions each; the scan can undercount (tool results may be stored elsewhere). If the owner's interactive sessions use them more than the transcripts show, raise P-04 to high.
- OQ-2. Should v2 ever run a daemon? v1's own verdict was 'net pessimization' and v2's targets (<50 ms reads, <1 s warm check) make it unnecessary; the only unambiguous daemon-shaped value is push (SSE for the GUI), which gui.md already places in milestone 2. Recommendation: do not ticket C-15/C-16 until the warm check target is missed in the bench (~36ZXTMR is the leading indicator).
- OQ-3. Does the owner want heat-by-symbol (frob_perf_hot) at all in v2? It was dropped with `perf`; the MCP tool is in the owner's set. If yes, P-18 (ingest an external profiler) is the cheap path; if the tool is rarely invoked (transcripts: 0 calls) leave it dropped.
- OQ-4. Python/TS/C++ adapters: first-party in gob-symbols (P-03) or WASM tier-4 packs (~8HJZ9MP, low)? The design lists python/ts/c-family grammar features in gob-languages but plugins.md routes non-first-party languages through packs. The estate evidence says first-party for Python and C++ at least; owner call.
- OQ-5. fuzz and PROTO typestate were 'DROP' in the notes but fuzz is not in the D1-D87 log and PROTO is only 'dropped unless a consumer commits' (rules.md). Record fuzz as a decision (one line in the README log) so it stops reappearing as MISSING.
- OQ-6. v1 research corpora (CWE-1000 dispositions, compliance, supply-chain, secrets/PII, capability-evasion taxonomy, pattern and system-design catalogs, exhaustiveness registry; about 9,000 lines) are not carried into v2. They are inputs to ~HC9450N and to detector work. Archive them under v2/notes/research with a pointer, or declare the `v1` branch the home.
- OQ-7. `fleet route` writes into another repository's ledger. Under D79/D82 is that a new privilege that needs the trust store, or is it acceptable because the caller already has write access to the sibling checkout? P-22 assumes the latter plus refusal of un-initialised repos.
- OQ-8. Should `ticket close done` be allowed outside `land` at all for tickets with a lease branch? P-01 refuses unmerged work and offers `--abandon-branch`; an alternative is to make `land` the only path to done for leased tickets.
- OQ-9. The v1 `.claude/hooks` (14 files) and `claude`/`sync-skills` verbs are slice D; this report lists only the frob-side surface (C-23, P-23). Confirm slice D covers the harness-side behaviors (root-write guard, timeout guard, pending-background guard).

## 6. Appendix: accounting of every enumerated entry

### 6.1 Packages (46) -> finding rows

| Package | Py files | Rows |
|---|---|---|
| _cli_parsers | 22 | C-22, C-112 |
| agent | 2 | C-113 |
| app | 78 | C-01, C-46, C-63, C-112 |
| arch | 29 | C-77, C-78, C-79 |
| bind | 1 | C-82 |
| check | 5 | C-71 |
| clean | 4 | C-57 |
| cve | 3 | C-34 |
| cycle | 2 | C-76 |
| deploy | 8 | C-29, C-30 |
| docs | 2 | C-42 |
| dup | 19 | C-80, C-81 |
| exports | 1 | C-69 |
| fleet | 1 | C-24, C-25 |
| fuzz | 8 | C-33 |
| gates | 126 | C-99, C-100, C-101, C-102, C-103, C-104 |
| gitlog | 1 | C-43 |
| graph | 16 | C-75 |
| lang | 22 | C-72, C-73 |
| logging | 7 | C-112 |
| map | 1 | C-39 |
| mutate | 2 | C-31, C-32 |
| narrative | 4 | C-86 |
| natives | 2 | C-68 |
| outline | 1 | C-40 |
| perf | 21 | C-83, C-10 |
| policy | 2 | C-84 |
| process | 23 | C-70, C-71 |
| refactor | 25 | C-37, C-38 |
| registry | 4 | C-85 |
| release | 4 | C-51, C-54 |
| render | 6 | C-112 |
| scaffold | 6 | C-59, C-60, C-61 |
| security | 2 | C-49 |
| serve | 9 | C-01 .. C-18 |
| sql | 5 | C-87 |
| stats | 5 | C-44 |
| strata | 90 | C-88 .. C-93 |
| telemetry | 1 | C-46 |
| testing | 20 | C-94, C-95, C-96, C-97 |
| tickets | 51 | C-48, C-56, C-102, C-105 .. C-111 |
| verify | 9 | C-98 |
| vet | 50 | C-35, C-36 |
| webapp | 38 | C-87 |
| worktrees | 2 | C-58 |
| xref | 1 | C-41 |

Count check: 46 packages listed.

### 6.2 Top-level modules (15)

| Module | Rows |
|---|---|
| __init__.py | C-112 |
| __main__.py | C-22, C-112 |
| _daemon_timeout.py | C-18 |
| ci_report.py | C-50 |
| ci_validity.py | C-50 |
| derived_state.py | C-62 |
| doctor.py | C-62, C-63, C-64, C-65 |
| excludes.py | C-112 |
| findings.py | C-112 |
| ghio.py | C-50 |
| gitio.py | C-112 |
| nodeid.py | C-112 |
| repo_meta.py | C-63, C-112 |
| tomlio.py | C-112 |
| yamlio.py | C-112 |

Count check: 15 modules listed.

### 6.3 Scripts (13)

| Script | Rows |
|---|---|
| _require_python.py | C-118 (Python interpreter guard; no v2 analogue) |
| artifact_smoke.py | C-53 |
| branch_stranded_work_analysis.py | C-55 |
| bump_version.py | C-54 |
| check_summary.py | C-112 (envelope carries counts; SB-9) |
| count_ticket_citations.py | C-86 |
| fleet_status.py | C-27 |
| frob-telemetry-hook | C-23, C-47 |
| measure_evidence_reach.py | C-94 |
| strip_help_citations.py | C-86 |
| verify_lands.py | C-56 |
| verify_release_ci_status.py | C-52 |
| wait_for_land_slot.py | C-28 |

Count check: 13 scripts listed.

### 6.4 Editors (4) and native crates (24 Rust files)

| Entry | Rows |
|---|---|
| v1/editors/jetbrains/README.md | C-19, C-20 |
| v1/editors/vscode-strata/language-configuration.json | C-19, C-20 |
| v1/editors/vscode-strata/package.json | C-19, C-20 |
| v1/editors/vscode-strata/syntaxes/strata.tmLanguage.json | C-19, C-20 |
| v1/frob-core/src/arch_python.rs | C-114 |
| v1/frob-core/src/callgraph.rs | C-80 |
| v1/frob-core/src/capability_python.rs | C-114 |
| v1/frob-core/src/exact_regions.rs | C-80 |
| v1/frob-core/src/extract.rs | C-114 |
| v1/frob-core/src/lib.rs | C-80 |
| v1/frob-core/src/r3.rs | C-80 |
| v1/frob-core/src/r4.rs | C-80 |
| v1/frob-core/src/r5.rs | C-80 |
| v1/strata-core/src/graph/mod.rs | C-89 |
| v1/strata-core/src/graph/model.rs | C-89 |
| v1/strata-core/src/graph/query.rs | C-89 |
| v1/strata-core/src/graph/vmodel/closure.rs | C-89 |
| v1/strata-core/src/graph/vmodel/mod.rs | C-89 |
| v1/strata-core/src/lib.rs | C-88 |
| v1/strata-core/src/parse/grammar_core.rs | C-88 |
| v1/strata-core/src/parse/grammar_flow.rs | C-88 |
| v1/strata-core/src/parse/grammar_infra.rs | C-88 |
| v1/strata-core/src/parse/grammar_module.rs | C-88 |
| v1/strata-core/src/parse/grammar_node.rs | C-88 |
| v1/strata-core/src/parse/grammar_policy.rs | C-88 |
| v1/strata-core/src/parse/grammar_vmodel.rs | C-88 |
| v1/strata-core/src/parse/lexer.rs | C-88 |
| v1/strata-core/src/parse/mod.rs | C-88 |

### 6.5 Documentation files (255)

| Directory | Files | Mapping |
|---|---|---|
| docs/modules | 85 | see 6.5.1 |
| docs/commands | 41 | see 6.5.2 |
| docs/guides | 21 | see 6.5.3 |
| docs/guides/extending | 22 | see 6.5.4 |
| docs/design | 28 | see 6.5.5 |
| docs/design/registry | 14 | see 6.5.6 |
| docs/audits | 19 | see 6.5.7 |
| docs/strata | 18 | see 6.5.8 |
| docs/investigations | 4 | see 6.5.9 |
| docs (root) and docs/assets | 3 | index.md, rework.md: C-112; assets/frob-banner.svg: not a feature |
| Total | 255 | find v1/docs -type f gives 255 |

#### 6.5.1 docs/modules

agent-worktree.md -> C-113; app.md -> C-112; arch.md -> C-77, C-78; bind.md -> C-82; ci_report.md -> C-50; ci_validity.md -> C-50; clean.md -> C-57; cli.md -> C-22, C-112; cve.md -> C-34; decisions.md -> C-103; deploy.md -> C-29; docstrings.md -> C-103; doctor.md -> C-62, C-63, C-64; dup-sota-survey.md -> C-80; dup.md -> C-80; fleet.md -> C-24, C-25; fuzz.md -> C-33; gate-config-path-defaults.md -> C-103, C-104; gate-inv011-forbidden-constant-reachability.md -> C-103, C-104; gate-race001.md -> C-103, C-104; gate-registration.md -> C-103, C-104; gate-route-response-model.md -> C-103, C-104; gate-sys111-ratchet-auto-accept.md -> C-103, C-104; gate-testmock001.md -> C-103, C-104; gate-time-stable-invariant.md -> C-103, C-104; gates.md -> C-103, C-104; ghio.md -> C-50; graph.md -> C-75; land-profiles.md -> C-66; lang.md -> C-72, C-73; logging.md -> C-112; mutate.md -> C-31; perf.md -> C-83; process.md -> C-70, C-71; release.md -> C-51; render.md -> C-112; serve.md -> C-01 .. C-18; sql.md -> C-87; stats.md -> C-44; strata.md -> C-88 .. C-93; testing.md -> C-94 .. C-97; tickets-data-storage.md -> C-105 .. C-111, C-56; tickets-landing.md -> C-105 .. C-111, C-56; tickets-lifecycle.md -> C-105 .. C-111, C-56; tickets-merge-driver.md -> C-105 .. C-111, C-56; tickets-verify-sweep.md -> C-98; tickets.md -> C-105 .. C-111, C-56; verify-rapid-debt-visibility.md -> C-98; vet.md -> C-35; webapp-a11y-forms-contrast.md -> C-87; webapp-a11y-interaction.md -> C-87; webapp-a11y-structure.md -> C-87; webapp-a11y.md -> C-87; webapp-comply-commerce.md -> C-87; webapp-comply-gdpr.md -> C-87; webapp-comply-privacy.md -> C-87; webapp-comply-sector.md -> C-87; webapp-comply.md -> C-87; webapp-launch-checklist.md -> C-87; webapp-layout-structure.md -> C-87; webapp-layout.md -> C-87; webapp-seo-crawl.md -> C-87; webapp-seo-tags.md -> C-87; webapp-seo.md -> C-87; webapp-webperf-markup.md -> C-87; webapp-webperf-server.md -> C-87; webapp-websec-authz-routes.md -> C-87; webapp-websec-authz.md -> C-87; webapp-websec-bounds.md -> C-87; webapp-websec-csrf-session.md -> C-87; webapp-websec-debug-config.md -> C-87; webapp-websec-deser.md -> C-87; webapp-websec-headers-log.md -> C-87; webapp-websec-headers-rules.md -> C-87; webapp-websec-headers.md -> C-87; webapp-websec-injection.md -> C-87; webapp-websec-jwt-oauth.md -> C-87; webapp-websec-logging-limits.md -> C-87; webapp-websec-password.md -> C-87; webapp-websec-random-tls.md -> C-87; webapp-websec-rls-llm.md -> C-87; webapp-websec-session.md -> C-87; webapp-websec-supply-chain.md -> C-87; webapp-websec-xss.md -> C-87; webapp.md -> C-87

#### 6.5.2 docs/commands

ack.md -> C-75; agent.md -> C-113; check.md -> C-103, C-71; claude.md -> C-23 (claude config sync: dropped, cli.md s4); clean.md -> C-57; cli-vocabulary.md -> C-22; coverage.md -> C-95; cycle.md -> C-76; deploy.md -> C-29; doctor.md -> C-62, C-63, C-64; explore.md -> C-39, C-40, C-41, C-42; exports.md -> C-69; fleet.md -> C-24, C-25; format.md -> C-71; gitlog.md -> C-43; graph.md -> C-05, C-07, C-75; map.md -> C-39; mutate.md -> C-31; narrative.md -> C-86; natives.md -> C-68; outline.md -> C-40; parse.md -> C-71; perf.md -> C-83; pool.md -> C-101; process.md -> C-70; profile.md -> C-66; refactor.md -> C-37; registry.md -> C-85; release.md -> C-51; run.md -> C-67; scaffold.md -> C-60, C-61; serve.md -> C-01; status.md -> C-45; sync-skills.md -> C-23 (dropped, cli.md s4); sys.md -> C-92, C-88; test.md -> C-94; ticket.md -> C-111, C-102 (slice A); verify.md -> C-98; vet.md -> C-35; worktree.md -> C-58; xref.md -> C-41

#### 6.5.3 docs/guides

agent-playbook-appendix.md -> C-113; agent-playbook.md -> C-113, C-27; agentic-time-profiling.md -> C-46, C-47, C-48; agentic-workflow.md -> C-113, C-111; claude-hooks.md -> C-23; command-reference.md -> C-22; coordinator-scripts.md -> C-27, C-28, C-55, C-56; editors.md -> C-19, C-20; estate-capability-migration.md -> C-26; estate-natives-build-rollout.md -> C-26; exhaustive-research.md -> C-85 (method doc; no code); frob-toml.md -> C-112; frob-version-policy.md -> C-63; install.md -> C-115, C-63; landing.md -> C-105, C-106; python-api.md -> C-118; quickstart.md -> C-112; release.md -> C-51, C-52, C-53; testing.md -> C-94, C-18; unity.md -> C-65, C-96; worktree-pool.md -> C-59

#### 6.5.4 docs/guides/extending

README.md -> C-91; benign-capabilities.md -> C-91; capability-registry.md -> C-90; comment-dsl-directives.md -> C-75; compliance-registry.md -> C-91; cve-fingerprints.md -> C-34, C-91; design-lint-rules.md -> C-88; dup-detector-registry.md -> C-80; failure-injection-acceptance-criteria.md -> C-89; gate-rule-families.md -> C-103; language-grammar-handlers.md -> C-72, C-73; litmus-fixtures.md -> C-89; pii-categories.md -> C-91; prover-claim-kinds.md -> C-89; registry_of_registries.json -> C-85; scenario-kinds.md -> C-89; secrets-scan-providers.md -> C-100, C-91; strata-surface-grammar.md -> C-88; sys-export-formats.md -> C-92; test-runner-entries.md -> C-96; threat-catalog.md -> C-91; ticket-kinds-states.md -> C-111 (slice A)

#### 6.5.5 docs/design

architecture-check-catalog.md -> C-77, C-78, C-117; capability-evasion-taxonomy.md -> C-117; check-fix-engine.md -> C-99; cli-hygiene.md -> C-22; cli-regrouping.md -> C-22; coding-performance-corpus.md -> C-117, C-83; compliance-corpus.md -> C-117; cwe-1000-registry.md -> C-117; design-pattern-catalog.md -> C-117, C-78; design-pattern-traps-corpus.md -> C-117, C-78; gate-semantics-classification.md -> C-103; land-checkpoint-durability.md -> C-105; land-splice-test-then-impl.md -> C-106; language-adapter-tier-decision.md -> C-73; ledger-mirror-batching.md -> C-106; ledger-v2.md -> C-106 (v2 ledger design supersedes); macos-portability.md -> C-116; refactor-verb.md -> C-37; secrets-pii-corpus.md -> C-117, C-100; security-corpus.md -> C-117; structural-linter-adversarial-hardening.md -> C-117, SB-8; supply-chain-corpus.md -> C-117, C-35; system-design-corpus.md -> C-117; system-performance-corpus.md -> C-117, C-83; test005-ratchet-schedule.md -> C-95; ticket-strata-shared-graph-inventory.md -> C-88; tickets-package-scope-precedent.md -> C-111; windows-portability.md -> C-116

#### 6.5.6 docs/design/registry

EXHAUSTIVENESS-GATE.md -> C-85, C-117; README.md -> C-85, C-117; RECONCILIATION.md -> C-85, C-117; arch-checks.yaml -> C-85, C-117; capability-via-ratchet.lock.json -> C-85, C-117; check-coverage.yaml -> C-85, C-117; compliance.yaml -> C-85, C-117; evasion.yaml -> C-85, C-117; patterns.yaml -> C-85, C-117; pii.yaml -> C-85, C-117; secrets.yaml -> C-85, C-117; supply-chain.yaml -> C-85, C-117; system-design.yaml -> C-85, C-117; weaknesses.yaml -> C-85, C-117

#### 6.5.7 docs/audits

README.md -> SB-1, SB-2, SB-8; branch-stranded-work-2026-08-25.md -> C-55; check-performance.md -> C-14, C-83; coordination-churn.md -> C-105, C-106; docs-completeness-2026-08-06.md -> C-103; docs-staleness-2026-07-29.md -> C-103; frob-blindspots-2026-07-23.md -> SB-11, C-103; gates-accounting.md -> C-103, SB-9; gates-quality.md -> C-103; gates-vacuous.md -> C-103, SB-9; graph.md -> SB-1, C-75; lang-check-docs.md -> SB-1, C-72; perf.md -> C-83, C-14; strata.md -> C-88 .. C-92; test005-zero-classification-t1418.csv -> C-95; test005-zero-classification-t1418.md -> C-95; tickets-testing-round2.md -> C-94, SB-9; tickets-testing.md -> C-94, SB-9; vet.md -> C-35, SB-8

#### 6.5.8 docs/strata

boundary.md -> C-88; charter.md -> C-88; dataset-construct.md -> C-88; entity_architecture.md -> C-88; evidence.md -> C-89; graph.md -> C-89; host.md -> C-92; kernel.md -> C-89; krb.md -> C-92; policy.md -> C-88; provenance-trust-identity.md -> C-89; reliability.md -> C-91; roadmap.md -> C-88 .. C-93; selfconform.md -> C-88; surface.md -> C-88; threat.md -> C-91; vmodel.md -> C-89; waive.md -> C-102

#### 6.5.9 docs/investigations

T-2202-mega-cluster.md -> C-76; T-2782-land-serialization.md -> C-105; T-2790-check-stage-profile.md -> C-14; T-2796-backlog-reproduction.md -> C-105

### 6.6 Completeness verdict

Unmapped entries after the run: 0. 

Row ids cited in this appendix that do not exist in section 3: none.

Findings rows not cited by any enumerated entry (rows that came from the MCP tool surface or from cross-cutting design reading rather than a file): C-21, C-74.

