# frob v1 inventory: ops, integrations, config, and performance evidence

Scope: everything in v1 (Python, <frob-v1>, read-only) that is NOT tickets, gates, graph/lang, strata,
or the CLI-surface inventory. Written for the Rust redesign. ASCII only. Sources: src/frob/, docs/modules,
docs/guides, docs/commands, .claude/hooks, .github/workflows, .frob/telemetry.jsonl.

## 0. Coverage ledger (denominator and status)

Universe = the 8 task sections, expanded at Phase 0 into 54 subsystem nodes, all enumerated before any was explored.
Status at report time: 54 done, 0 pending, 0 blocked. "Done" means inventoried at module-doc plus module-docstring
depth, NOT read line by line. The v1 tree is 362,549 Python lines; the in-scope subsystems below are roughly 105k of
them (app/ alone is 46,736; vet/ 20,491).

Known depth limits (disclosed, not hidden):
- vet/ detectors (about 40 modules) are catalogued by family, not enumerated per detector or per needle table.
- app/config.py AppConfig has 432 fields; they are described structurally, not listed.
- gates/ internals (the *_schema modules, coverage stamp helpers) were read only where they define a frob.toml key or
  the TEST005 ratchet.
- Telemetry has NO records for `frob test` or `frob graph build` in its cli stream (see section 1); I could not
  measure those two and did not guess.

Per-section node list (the frontier I drained; the numbers are the task's section numbers, the document below is
ordered perf, testing, vet, serve, release, ops, app, CI):

| Task sec | Nodes | Count |
|---|---|---|
| 1 testing | selection, runner registry, collectors, coverage stamp+refresh, TEST005 ratchet, flake quarantine, mutation sweep queue + mutate, xdist/agent env | 8 |
| 2 vet etc | vet scan, hook mode, allowlist+quarantine, capability scan, advisories+cve, security/redact, fuzz | 7 |
| 3 serve | MCP tools, socket daemon, background daemon jobs, telemetry | 4 |
| 4 release | manifest+semver, changelog fragments, publish+dev bump, deprecated baseline, ghio, ci_report, ci_validity | 7 |
| 5 ops | fleet, deploy, scaffold+managed blocks, claude sync, .claude hooks, skills sync | 6 |
| 6 app | AppConfig, frob.toml, [tool.frob], profile ratchet, excludes, worktree+agent verbs, logging, process, render, findings, doctor, clean, natives, stats, gitlog, parse, narrative, docs, format/fmt | 19 |
| 7 CI | ci.yml, release.yml | 2 |
| 8 perf | telemetry analysis | 1 |

## 1. Performance evidence (the "frob is sluggish" case)

### 1.1 What the data is

`.frob/telemetry.jsonl`: 145,586 lines, 32 MB, 2026-09-15 to 2026-09-27 (12 days, one repo, heavy multi-agent use).
Record kinds:

| kind | count | writer | notes |
|---|---|---|---|
| tool | 112,263 | .claude/hooks/tool-call-telemetry.py (Pre+PostToolUse) | one line per Claude tool call; Bash 96,240, Edit 7,713, Read 2,231, Write 1,783; fields tool, phase pre/post, head_sha, dispatch_id, command_shape, verb/subverb, output_tokens_est. No duration field. |
| cli | 30,467 | frob.app.telemetry.timed_call, wired in app/app.py | the only timing evidence; fields subcommand, subverb, args_head (secret-redacted), duration_ms, exit, tree_hash, home_config_hash, external_path_hash |
| dispatch | 1,828 | dispatch-telemetry.py (SessionStart/Stop) | 18 start, 1,810 end events |
| ticket | 807 | ticket runner | created 763, started 24, requeued 13, done 7 |
| gate_rule_counts | 221 | frob.telemetry (one per gates-stage run) | rule -> count; median 6,693 findings (waived included) and 72 distinct rules per run |

Measurement caveats that matter for v2:
- duration_ms is measured around the runner dispatch inside the process (timed_call at src/frob/app/app.py line 414).
  It EXCLUDES interpreter start, `import frob`, argparse construction, and the stale-binary/drift probes in `main()`.
  `ticket land --status` shows a 1.5 ms median, which is clearly not the wall time an agent paid. All numbers below
  are therefore a LOWER bound on user wall time.
- Only 15 subcommands appear in the cli stream: ack, arch, check, claude, clean, doctor, explore, natives, scaffold,
  serve, status, ticket, verify, vet, xref. `test` (18 tool-hook sightings), `coverage` (8), `graph` (1) and `format`
  (82) have ZERO cli records. I could not determine why (argparse early exit, or a dispatch path that bypasses
  timed_call); treat as an observability gap in v1.
- 5,785 of 30,467 cli rows have no subverb (pre-T-4689 shape), so "ticket" with no subverb is a real bucket of 4,189
  rows.
- "async" verbs (`verify drain-async`, `ticket sweep-async`) are by name detached workers; I did not verify
  detachment, so their hours are CPU/queue cost, not necessarily blocked-agent time.

### 1.2 Aggregate

- 30,467 timed invocations, 393.5 hours of recorded in-process time in 12 days (about 33 h/day; agents run in
  parallel).
- 16,078 invocations (53%) are under 100 ms and 16,278 (53%) under 1 s; 14,189 (47%) exceed 1 s and 5,496 (18%) exceed
  10 s. The distribution is bimodal: a huge mass of trivial polls and a heavy tail of multi-minute runs.
- 15,224 of the 30,467 (50%) are `ticket land --status T-N` polls (median 1.5 ms in-process): agents poll land status
  in a loop, so one in two frob invocations is a status poll that each pays a full Python process start (not
  captured).
- Time by day peaked at 50-55 recorded hours on 09-19 and 09-21 to 09-23, so load is sustained, not bursty.

### 1.3 Per subcommand (median / p90 / total), all 15 recorded

| subcommand | n | median s | p90 s | max s | total h |
|---|---|---|---|---|---|
| ticket | 26,681 | 0.00 | 27.69 | 14,427.8 | 248.11 |
| verify | 3,277 | 4.29 | 26.00 | 3,485.2 | 81.23 |
| check | 443 | 219.76 | 1,324.17 | 3,594.4 | 64.07 |
| explore | 12 | 13.67 | 35.10 | 70.6 | 0.07 |
| natives | 13 | 7.78 | 14.04 | 14.7 | 0.03 |
| doctor | 2 | 31.81 | 40.95 | 41.0 | 0.02 |
| status | 2 | 13.90 | 15.89 | 15.9 | 0.01 |
| ack | 3 | 1.70 | 25.77 | 25.8 | 0.01 |
| clean | 1 | 13.05 | 13.05 | 13.0 | 0.00 |
| arch | 2 | 2.86 | 2.87 | 2.9 | 0.00 |
| serve | 1 | 0.35 | 0.35 | 0.4 | 0.00 |
| claude | 2 | 0.09 | 0.13 | 0.1 | 0.00 |
| xref | 16 | 0.00 | 0.00 | 0.0 | 0.00 |
| vet | 9 | 0.00 | 0.01 | 0.0 | 0.00 |
| scaffold | 3 | 0.00 | 0.00 | 0.0 | 0.00 |

### 1.4 Top 15 by total time (subcommand + subverb)

| rank | command | n | median s | p90 s | max s | total h |
|---|---|---|---|---|---|---|
| 1 | ticket land (all forms) | 17,043 | 0.00 | 0.00 | 14,427.8 | 102.61 |
| 2 | check | 443 | 219.76 | 1,324.17 | 3,594.4 | 64.07 |
| 3 | ticket (no subverb recorded) | 4,189 | 8.34 | 108.23 | 2,305.2 | 63.68 |
| 4 | verify drain-async | 231 | 337.16 | 1,812.00 | 3,485.2 | 57.21 |
| 5 | ticket sweep-async | 122 | 640.75 | 4,253.40 | 10,670.6 | 56.14 |
| 6 | verify (no subverb) | 1,372 | 4.63 | 11.15 | 2,161.9 | 21.22 |
| 7 | ticket work | 304 | 80.94 | 159.24 | 441.1 | 7.52 |
| 8 | ticket new | 1,159 | 6.74 | 46.96 | 916.7 | 6.98 |
| 9 | verify status | 1,609 | 3.34 | 10.04 | 48.6 | 2.27 |
| 10 | ticket promote | 704 | 5.28 | 13.17 | 333.6 | 2.14 |
| 11 | ticket scope | 272 | 12.31 | 47.67 | 759.4 | 1.89 |
| 12 | ticket points | 478 | 6.60 | 14.78 | 314.4 | 1.28 |
| 13 | ticket body | 231 | 11.23 | 20.45 | 151.0 | 0.86 |
| 14 | ticket show | 946 | 2.71 | 4.15 | 60.2 | 0.78 |
| 15 | ticket sprint | 356 | 4.82 | 9.80 | 440.7 | 0.71 |

Rank 1 decomposes (ticket land): `--status` polls 15,224 runs, 0.01 h total (median 0 s, max 0.9 s); `--drain` 281
runs, median 356 s, p90 1,983 s, max 14,428 s, 57.84 h; all other land forms (per-ticket land, --dry-run) 1,538 runs,
median 20.2 s, p90 300.7 s, max 1,853 s, 44.76 h.

### 1.5 The four questions asked

| Question | Answer |
|---|---|
| How long does `check` take? | 443 runs. Median 219.8 s (3.7 min), p90 1,324 s (22 min), max 3,594 s (60 min). 167 of 443 (38%) exceeded 10 minutes. Exit status: 436 of 443 exited 1 (red) and only 7 exited 0, so 98% of recorded checks were non-green. Scoped forms are much cheaper: `--only gates` median 32 s (n 17), `--only arch` 101 s (3), `--only coverage` 48 s (2), `--only perf` 56 s, `--only docanchor` 127 s, `--ticket` 156 s (3); `--only TEST` 0.46 s. Full (no --only) checks are 415 of 443 runs, median 243 s, p90 1,337 s, 63.65 h. |
| Per-stage cost inside one check? | `.frob/check-budget-timing.json` (last stored sample, 2026-09-23): static 87.0 s, gates-native 66.7 s, gates-fast 56.1 s, gates-security 25.1 s, narrative 23.2 s, lint 4.8 s; stages sum to about 263 s, consistent with the 243 s full-check median. |
| How long does `test` take? | NOT MEASURABLE. Zero cli records. Only 18 `frob test` and 8 `frob coverage` invocations were seen by the tool hook in 12 days versus 716 `frob check` and 1,605 `ticket show`: agents almost never ran `frob test` directly (presumably the land pipeline and coverage stamp run tests implicitly; not verified). The test-side cost shows up instead in CI (section 8: full green run 92-129 min). |
| How long does `graph build` take? | NOT MEASURABLE. One `graph why` tool-hook sighting, zero cli records. Graph build is hidden inside check (`static` stage) and inside every ticket verb that loads the snapshot. Disk evidence: `.frob/parse-artifacts.db` is 270 MB and `.frob/cache.db` 26 MB, so v1 leans on big derived caches to hide parse cost. |
| How long do `ticket *` verbs take? | Excluding `land` and `sweep-async`: 9,516 runs, median 6.4 s, p90 66.6 s, 89.4 h total. Even excluding runs over 100 s (8,867 runs) the median is 5.8 s and p90 27.9 s. Read-only `ticket show` (946 runs) has median 2.7 s, p90 4.1 s, p10 1.3 s; `ticket list` (85) median 0.27 s. Mutating verbs: new 6.7 s, promote 5.3 s, points 6.6 s, scope 12.3 s, body 11.2 s, set 6.6 s, block 5.1 s, work 80.9 s, start 14.6 s, done-report 188 s, evidence 39.5 s, close 15.3 s (p90 537 s), doable 146.6 s (n 3). |

### 1.6 Other findings that explain the sluggishness

- A 2.7 s median for a read-only `ticket show` (and 6.4 s for a metadata edit) means every verb pays a graph/ledger
  load; a 270 MB parse cache and a 49 MB `tickets-index.json` (the ticket index, rebuilt by v1) are the compensating
  mechanisms. v2 target: a ticket read should be sub-50 ms.
- Background churn is huge: `verify drain-async` (57.2 h) plus `ticket sweep-async` (56.1 h) plus `ticket land
  --drain` (57.8 h) = 171 of 393 recorded hours (43%) is deferred verification/queue work that exists to keep the
  foreground land fast (rapid-sweep state alone is 474 MB in .frob/rapid-sweep).
- Hook tax: every Bash call fans out to up to 6 PreToolUse python3 processes (timeout-guard, pgrep-guard,
  frob-suggest, root-write-guard, directive-guard, tool-call-telemetry) plus 2 PostToolUse (cleanliness detector,
  telemetry). With 96,240 Bash calls in 12 days that is roughly 770k hook process spawns; Edit calls spawn 4. Hook
  timeouts are 10 s except frob-suggest at 120 s.
- Scale of work per check: median 6,693 findings (incl. waived) over 72 distinct rules per gates run; the first
  recorded run fired 53 rules (CPLACE002 1,326, CPLACE001 964, TICK014 946, DOCARCH001 535).
- Concurrency pathologies are documented in-tree: 12 concurrent `frob check` processes at 0.5-1.1 GB each drove swap
  2.1 -> 7.8 GB and lands/hour DOWN as agents went up (docs/modules/process.md "Concurrent check advisory"); 94
  orphaned forkserver processes held 17.3 GB swap (forkserver reaping).
- Derived state on disk in the shared root: 920 MB total in .frob (rapid-sweep 474 MB, parse-artifacts.db 270 MB,
  tickets-index.json 49 MB, verify-drain 36 MB, telemetry 32 MB, cache.db 26 MB, gate-cache.db 23 MB).

Verdict (perf): KEEP the telemetry idea, MERGE into one process-start-to-exit timer. Reason: v1 measured only
dispatch, and missed test/graph entirely.

## 2. testing/ (7,496 lines) and mutate/ (1,228)

Doc: docs/modules/testing.md (1,389 lines), docs/guides/testing.md.

### 2.1 Touched-set selection (`frob test`, testing/_select.py, pure)

Pipeline: working_diff(root, base) = committed-since-merge-base + staged + unstaged -> hunks resolved to symrefs
against the graph snapshot -> direct tests (every TESTS edge whose tested-source endpoint is the touched symbol, its
class, file or package; the test endpoint is whichever side lives in a test file) -> contract ripple (up to 4
`uses-contract` hops) -> touched test files always run -> fallback for touched files with zero bindings via
`--fallback package|suite|warn` (a CLI knob, not a frob.toml key). Special cases: non-language files (.toml/.json/.md)
degrade to a suite-wide run; a module-level edit in a tracked file forces `package` even under `warn`; `--all` skips
selection; a subdirectory path argument scopes to the python runner only (T-2319); `.strata` files run `frob sys
audit` in process with no runner entry. Outputs: SelectionReport per language -> run_selected.

### 2.2 Per-language runner registry (`[[test.runner]]`)

Keys (known set TEST_RUNNER_KNOWN_KEYS): language, command, all_command, cwd, collector, timeout_s. Exactly one
placeholder per command: `{ids}` (node ids), `{files}`, `{filters}` (cargo-style, path prefix reduced to a::b),
`{regex}` (ctest alternation). A language with selected tests but no runner is a hard error (no vacuous pass).
Multiple same-language runners are routed by cwd-prefix of the item's file (T-0128); zero or >1 match is UnroutedItem.

Languages in v1 collection/runner code: python (pytest), rust (cargo test --lib, needs PYO3_PYTHON probing
python3.13..3.11 and LD_LIBRARY_PATH), typescript (`npx vitest list --json` / `vitest run`), cpp (`ctest
--show-only=json-v1` from an already-configured build dir), csharp (static tree-sitter NUnit/Unity collection; `dotnet
test --filter` with TRX parsing in _dotnet_runner.py; Unity `-batchmode -runTests` NUnit3 XML in _unity_batchmode.py,
editor path via `[tool.frob] unity_editor`), kotlin (reads existing gradle JUnit XML; never builds), strata (native,
no subprocess). Frob's own frob.toml declares 9 runners: python, rust x2 (strata-core, frob-core), strata, and FIVE
dummy entries (bash, csharp, java, cuda, zig) that all just re-run two pytest files with a `{files}` tail - a
workaround to satisfy "language with tests needs a runner", i.e. config smell.

### 2.3 Collection caches (all under .frob/)

| File | Producer | Key |
|---|---|---|
| pytest-collect.json | `pytest --collect-only`, nested runner cwds unioned | test-file content hash + fingerprint of compiled artifacts (.so/.pyd/.dylib) of each declared `[[native]]` |
| cargo-collect.json | `cargo test -- --list` per Cargo.toml | crate sources |
| ctest-collect.json | ctest json-v1 per CMake project | build dir state |
| csharp-nunit-collect.json | static C# parse | source hash |
| kotlin-junit-collect.json | existing JUnit XML | report mtime/content |
| (ts) | vitest list --json per package.json | source hash |

`[[native]]` keys (NATIVE_KNOWN_KEYS): name (python import name), build_cmd, language. Unbuilt natives are reported by
COV003 with the build command. `frob test --collect` drops the pytest cache. Escape hatch is rarely needed after the
native fingerprint was added (T-0333).

### 2.4 Coverage stamp and refresh

- Artifacts: coverage.xml, `.frob/coverage-stamp`, repo-root `frob-coverage.lock.json` (committed floors),
  `.frob/coverage-file-cache.json` (path -> content_hash + line_pct, merged not replaced), `.frob/coverage-run.json`
  (degraded, pytest_exit_code, pytest_ran, worker_crash), `.frob/coverage-lock-audit.log`.
- `native_coverage_refresh` decides cold-full vs touched-set-incremental vs nothing-to-do, spawns pytest/coverage
  directly, ends with stamp_coverage. cov target defaults to the scanned repo's own pyproject name (src-layout),
  falling back to src/frob.
- Hardening accreted from incidents: red suite still keeps the artifact (T-1676); wall-clock deadline plus no-progress
  watchdog on the pytest subprocess (T-1677; FROB_COVERAGE_WALLCLOCK_DEADLINE_S,
  FROB_COVERAGE_NO_PROGRESS_DEADLINE_S); xdist worker-crash signature (`INTERNALERROR>` / WorkerController) -> one
  serial retry with `-p no:xdist`; memory-aware worker sizing `min(cpu, MemAvailable /
  FROB_COVERAGE_PER_WORKER_MEM_MB(1536))` or pin via FROB_COVERAGE_MAX_WORKERS (0 = opt out); a `pytest11` entry point
  strips leftover xdist tokens from addopts; optional SIGUSR1 stack dump (FROB_COVERAGE_STACKDUMP).
- `run_coverage_wait`: single-flight under `.frob/coverage.lock`, plus a cross-worktree content-addressed cache under
  `<git-common-dir>/frob-coverage-shared` keyed by sha256 over tracked *.py/*.rs/*.ts/*.tsx file hashes; the daemon
  also offers a named `coverage` lease (capacity 1).
- `frob coverage [--full]` is the CLI verb (T-1525).

### 2.5 TEST005 ratchet

TEST005 = measured coverage below threshold: per-symbol branch (`unit_branch_cov`), per-module line
(`module_line_cov`), per-system line (`system_line_cov`). `[testing]` keys = TestPolicy fields: min_unit_cases,
min_integration, unit_branch_cov, module_line_cov, system_line_cov, pair_integration (code defaults
3/1/90/85/80/false; frob's own frob.toml sets min_unit_cases 1 and recalibrated 75/70 coverage floors; scaffolds start
at 1/1/50/50/50). Ratchet mechanics in `write_coverage_lock`: a committed module floor can only move up (drop >
tolerance is clamped back; `allow_decrease=True` is the explicit re-baseline), except an exact 0.0 measurement is
never clamped (T-1401). stamp refuses to write when module_join_fraction < 0.5 (CoverageDeflated) or a canary module
(src/frob/__main__.py) reads exactly 0%. TEST012 compares the committed lock to live; TEST011/TEST017 gate on stamp
freshness/deflation. `exclude_filtered_coverage` applies `[graph] exclude`. The ratchet pool (`[gates.ratchet] rules`,
`frob pool`) is the gates agent's inventory.

### 2.6 Flake quarantine

`.frob/test-stability.json`: per-test P/F history (bounded), is_flaky rule, quarantine always carries a real ticket id
(never a silent skip list); quarantined tests still run and report but do not fail the gate; alarms for stale
quarantine and hard regressions (`track_python_stability`).

### 2.7 Mutation: `frob mutate` and the TEST016 sweep queue

`frob mutate FILE [--path DIR] [--json] [-- TEST-CMD]`: Python-only AST mutations (flip comparison, swap operator,
negate bool, mutate return), runs bound tests per mutant, exit 1 on survivors. Crash safety: backup journal under
`.frob/mutate-backup` with cross-process lock, PID-liveness and content-verified stale restore (doctor reports stale
journals). TEST016 (mutation evidence) was moved OFF the per-land critical path (T-1518): only `security`-kind tickets
run it inline; others enqueue a SweepEntry (ticket_id, base_ref, kind) to `.frob/mutation-sweep-queue.json` (own
lock), drained by `ticket land --run-mutation-sweep` or a merge-queue drain; `bug`-kind survivors file a new bug
ticket; budget FROB_MUTATION_SWEEP_BUDGET_S. The `rapid` profile skips TEST016 entirely.

### 2.8 xdist and agent env

`frob agent env <worktree>` prints exports for `eval`: FROB_WORKTREE, FROB_AGENT=1, PYTHONPATH=<worktree>/src, and
(only when other live leases exist) PYTEST_XDIST_AUTO_NUM_WORKERS = max(1, cpu // (leases+1)). Repo pyproject addopts
force `-n auto --timeout=120 --timeout-method=thread`; tests marked `heavy_subprocess` get their own xdist_group so
they serialize on one worker.

Verdicts (testing):

| Node | Verdict | Reason |
|---|---|---|
| selection algorithm | KEEP | core value; pure function over graph and diff |
| runner registry | MERGE | fold [[native]] and runners into one language table |
| collectors | MERGE | one content-addressed artifact store, not six JSON files |
| coverage stamp/refresh | MERGE | single measure-once pipeline; drop Makefile and shell parity |
| TEST005 ratchet | KEEP | one-way floors proved valuable after real incidents |
| flake quarantine | KEEP | ticket-bound quarantine beats silent skip lists |
| mutation sweep queue | DROP | exists only because land was slow; run inline |
| mutate verb | MERGE | keep as optional tool; pytest-specific parts out |
| xdist/agent env | DROP | pytest-tuning workarounds; keep only worktree env contract |

## 3. vet/ (20,491 lines), security/, cve/, fuzz/

Docs: docs/modules/vet.md (1,519 lines), cve.md, fuzz.md.

### 3.1 `frob vet [path] [--hook CMD] [--json] [--cve-mirror DIR] [--timeout S] [--jobs N]`

Posture: allowlist conformance, capability DIFFING across versions. Inputs are lockfiles: uv.lock/poetry.lock,
Cargo.lock, package-lock.json, pnpm-lock.yaml (yarn.lock and bun.lockb not parsed); `scan_tree` handles every lockfile
found at the root (polyglot). Dependency source comes from local caches first (uv/pip cache, cargo registry,
node_modules), network only with consent. Verdict cache: `.frob/vet.db` sqlite, content-addressed by artifact hash
(immutable, shared-safe), plus osv_cache (24 h TTL) and registry publish-date cache; NVD CWE lookups cached 7 days.
`--jobs N>1` is best-effort (sqlite write races disclosed); per-package timeout gives VET-TIMEOUT instead of a hang.
Transitive tree is vetted.

### 3.2 Hook mode (`--hook COMMAND`)

Not a tree scan: parses a single install-shaped shell command (uv add, uv pip install, pip/pip3 install, npm
install/i, pnpm add, yarn add, npx, cargo add) into (ecosystem, name, version) and runs the pre-lockfile checks: age
quarantine, typosquat distance, advisory, unverified. HookVerdict.verdict in {ok, quarantine, typosquat, advisory,
unverified}. Intended as a Claude PreToolUse hook; frob's own .claude/settings.json does NOT register it (only the
global ~/.claude config might).

### 3.3 Allowlist and age quarantine (frob.toml `[vet]`)

Keys read by vet/_allow.py: enforce, advisories (OSV on by default, T-5138; legacy alias `osv`), advisory_max_age_days
(7), quarantine_days (14), plus table `[vet.allow]` = package -> list of capability names (net, env, exec, eval,
native, ...). Cooldown quarantine VET011: ERROR when a locked version was published inside the window. Pyproject
`[tool.frob] vet_cve_mirror` or `--cve-mirror` selects a local cvelistV5 clone.

| Rule | Meaning |
|---|---|
| VET001 | dependency has no allow entry |
| VET002 | observed capability not declared |
| VET003 | version bump adds a capability |
| VET004 | obfuscation or undeclared install hook (never declarable) |
| VET005 / VET012 | advisory present / advisory data unobtainable (stale cache over max age) |
| VET006 | lockfile and manifest disagree |
| VET007-010 | project-tree checks: unpinned deps, bad data_files, unpinned CI action (non-SHA `uses:`), opaque binary artifact |
| VET011 | quarantine (new release) |
| VET-JS / JS003 / JS004 | npm lifecycle scripts, typosquat, non-registry source |
| VET-PY001-003 | sdist cmdclass, .pth files / import-time capability, pickle/marshal data |
| VET-RS001/002 | build.rs body capability-scanned (not denied outright) / proc-macro crates carry compile-time exec |
| VET-TIMEOUT, VET-SOURCE-UNAVAILABLE | honest non-answers |

### 3.4 Capability scan

tree-sitter over frob.lang grammars; python, rust, c/cpp, csharp, kotlin, typescript scanners (vet/_capability_*.py)
plus a `_capability_registry` package (kinds, matrices, per-language dangerous-op needle tables, dotnet BCL and Unity
API tables). Taxonomy about 26 kinds: exec, eval, net (connect/listen/mutate), fs read and write, env read/write,
process-control, ffi, native, install-hook, obfuscation, embedded_code, and c-cpp-excused kinds (sql, html_render,
fetch_url, deserialize, client_storage). Extras: obfuscation ensemble (entropy, shape, bidi/zero-width, packer
fingerprints), closed-world import accounting, one-hop cross-file wrapper resolution, taint (SEC005), typosquat with
bundled popular-package lists (pypi/npm/cargo), supply-chain structural checks. External adapters: OSV.dev HTTPS batch
(no binary), GuardDog, OpenSSF Scorecard, sigstore (aspirational); doctor reports cargo-audit as a relevance-gated
optional tool.

### 3.5 security/ and cve/

security/_redact.py (613 lines): provider-secret regex plus entropy detector and redactor, extracted out of gates so
telemetry can redact every args_head without importing the gates package (it cost about 257 ms per CLI call before
T-1318). cve/ (370 lines): pydantic models and parser for CVE Record Format v5, mirror walker; extra=ignore, missing
required fields are Err, broken records yielded as Err never skipped. Matching lives in vet/_cve.py.

### 3.6 fuzz/ (996 lines)

Enforced property fuzzing. Types become generatable by derivation (pydantic), `__fuzz__()` classmethod, or
`frob.fuzz.register` (hypothesis; Rust/TS planned). Rules FUZZ001 (no kind="fuzz" binding), FUZZ002 (no generator),
FUZZ003 (stale `.frob/fuzz-stamp.json`, body-digest keyed). frob.toml `[fuzz]`: enforce (off default |
invariant-anchored | public), budget_s (60), max_reject_rate (0.99).

Verdicts (vet and friends):

| Node | Verdict | Reason |
|---|---|---|
| vet scan + capability diff | KEEP | genuine differentiator; rewrite scanners natively in Rust |
| hook mode | KEEP | cheap pre-install check; ship a real hook installer |
| allowlist + quarantine | KEEP | declaration-as-waiver is simple and auditable |
| advisories (OSV) + cve | MERGE | one advisory client; drop local cvelistV5 mirror |
| security/redact | KEEP | secret redaction needed by telemetry and logs |
| fuzz | DROP | opt-in, off by default, Python-hypothesis-only today |

## 4. serve/ (3,690 lines), telemetry, daemon

Docs: docs/modules/serve.md (1,267 lines). Repo `.mcp.json` registers four MCP servers: serena, frob (`frob serve`),
fetch (uvx mcp-server-fetch), arxiv.

### 4.1 MCP tools (`frob serve`, FastMCP over stdio, read-only; `mcp` SDK is optional and lazily imported)

`build_server` registers 10 tools. Tool layer is plain `Result[dict, ServeError]` functions in serve/_tools.py, shared
with the socket daemon (one core, two transports).

| Tool | Inputs | Output |
|---|---|---|
| frob_doable_tickets | none | list of full Ticket model dumps, oldest first (revalidates sweep-filed tickets like the CLI) |
| frob_stale_docs | none | {stale: DRIFT001 entries, dangling: DRIFT002 entries} from frob.lock vs graph |
| frob_graph_query | symref | ref, span, digests, outgoing and incoming edges (full edge dumps) |
| frob_doc_for | symref | ref, doc anchors, described_by [{src, facet}] |
| frob_affects | symref, max_depth?, max_nodes? | north-star query: docs, tests, transitive dependents (uses-contract chain) |
| frob_check_scope | ticket_id | {ticket, in_scope, violations[rule,file,message]} via scope gate only |
| frob_perf_hot | top?, by="p50xcount" or "p90" | rows {section_key, kind, label, p50, p90, sample_count} from the sketch store |
| frob_check_delta | ticket_id?, base="main", verify=false | new-since-baseline violations plus check_result (same shape as `check --only gates --delta --json`); verify=true cross-checks a cold rerun |
| frob_run_touched_tests | base="main" | selects and runs touched-set tests on the warm snapshot; returns run report |
| frob_daemon_status | none | {post_land verdict, rebase_warnings[], last_poll_at} |

Socket-only RPC methods (not MCP tools): frob_exports(pkg_dir, include_private, exclude_modules),
frob_stats(window_days), frob_map(depth), frob_version, frob_shutdown, frob_lease_acquire, frob_lease_release,
subscribe. ServeError members include GraphUnavailable, LockUnavailable, GateFailed, GitFailed, RunnersUnavailable,
ExportsFailed, StatsFailed, MapFailed.

### 4.2 Socket daemon (`.frob/daemon.sock`, `.frob/daemon.lock`)

Standalone unix-socket, newline-delimited JSON-RPC process, per project root. Single-instance via
flock(LOCK_EX|LOCK_NB); idle-timeout exit; version handshake (`frob_version`) compares package version AND git HEAD
sha of the source (T-2884) and gracefully replaces a stale daemon; six liveness states (Live, NoSocket, Orphaned,
Wedged, VersionSkew, PlatformUnsupported - Windows never uses it, AF_UNIX only). Probe budget 0.5 s. Warm state
(serve/_warm.py): graph snapshot, baseline, test ids cached and validated by a `git status` dirty-key; FS "watch" is a
fast poller of that same key (no inotify) that pre-warms; push events `graph-changed` and `coverage-fresh` over
`subscribe`; named resource leases bound to a connection (freed on disconnect). The CLI proxies a set of commands
through it (`frob perf hot --json`, `exports --json`, `stats --json`, `map --json`, ...). It is OPT-IN: FROB_DAEMON=1
enables, FROB_NO_DAEMON=1 always wins, because it leaked forkserver children and competed for CPU (T-1378) and "is a
net pessimization" per its own doc.

### 4.3 Background daemon thread (`frob serve`, _daemon.py)

Every 20 s (DEFAULT_POLL_INTERVAL_S): (1) post-land re-verify when `main` HEAD moves (delta check plus touched tests),
(2) rebase bot: `git merge-tree` simulation of main into every leased worktree branch, conflict = `<<<<<<<` in output,
(3) coalescing verify worker tick. `_daemon_timeout._run_bounded` runs a callable on a plain daemon thread with a
wall-clock budget (used by lang parse and vet package scans) because ThreadPoolExecutor's atexit join made abandoned
workers hang interpreter shutdown.

### 4.4 Telemetry (`.frob/telemetry.jsonl`)

Local only, gitignored, opt-out FROB_NO_TELEMETRY=1; one JSON line per event; secrets redacted via security/_redact.
Record shapes are in section 1.1. cli rows carry tree_hash (git short hash), home_config_hash and external_path_hash
(so repeated identical commands on identical trees are detectable as "retreads"). Consumers: `frob stats --agentic`
(FROB_STATS_AGENTIC=1: time by category, top sinks, retread candidates, per-ticket cycle time, dispatch cost join of
tool/ticket/dispatch events), `frob doctor usage` (SubcommandTimeSink ranking), footgun tips ([FAST_EXIT1],
[REDUNDANT_RERUN], [REPEATED_FAILURE]; opt-out FROB_NO_FOOTGUN_TIPS / FROB_SUPPRESS_TIPS), diagnosis-nudge.py (reads
it to see whether a turn filed a ticket). Gate firing counts are a third kind (`gate_rule_counts`).

Verdicts (serve):

| Node | Verdict | Reason |
|---|---|---|
| MCP tools | KEEP | thin typed query surface; agents prefer it to shelling out |
| socket daemon | KEEP | v2 core should be a resident process; Rust fixes startup |
| warm state + watcher | MERGE | one incremental graph store; drop git-status poller |
| daemon background jobs | MERGE | rebase bot and post-land verify become scheduler tasks |
| leases/events | MERGE | needed for multi-agent coordination; fold into one RPC |
| telemetry | KEEP | evidence base; time from process start, include every verb |

## 5. release/ (1,530), ghio, ci_report, ci_validity

Docs: docs/modules/release.md, docs/guides/release.md (707 lines), ghio.md, ci_report.md, ci_validity.md.

### 5.1 `.frob-release.json` is the one version authority

Manifest = {version, api{symref -> signature digest}}. pyproject `[project].version`, uv.lock's package version and
CHANGELOG headings are DERIVED; `frob release sync` regenerates them (pyproject line, re-runs `uv lock`, CHANGELOG
skeleton). REL002 (unconditional, ERROR) flags a hand-edited derived artifact. `frob release
stamp|check|sync|publish`.

### 5.2 Semver from the public-API graph

diff_class(manifest, snapshot): removed or changed public signature = MAJOR; added public symbol = MINOR; bodies/docs
only = NONE. BumpClass ordered NONE<PATCH<MINOR<MAJOR. "Public" excludes tests and underscore/dotted-private symbols.
Signature digests, not bodies. REL001 (opt-in until a manifest exists) fails when the declared version does not cover
the class, or CHANGELOG lacks an entry. PEP 440 ordering via packaging.version (T-4270).

### 5.3 UnbumpedApiChange

`stamp` runs REL001's own computation first and returns Err(ReleaseError.UnbumpedApiChange) writing NOTHING when the
version is short (stamp alone used to silently rebaseline). Override `--allow-unbumped` requires
`--reason`/`--reason-file` (else UnbumpedReasonMissing) and appends a ForceOverrideEntry to repo-root
`force-overrides.jsonl` plus a WARNING log. All release writes are atomic (temp + fsync + rename). Other errors:
NoManifest, Malformed, BadVersion, WriteFailed, MajorVersionAckRequired, GitAdd/Commit/Push/ Build/PublishFailed.

### 5.4 CHANGELOG and changelog.d ownership

Each land writes a unique `changelog.d/T-####.md` fragment (collision-free); CHANGELOG.md's unreleased section is
regenerated deterministically from the whole fragment set under land.lock. Both are land-owned: a worktree pre-commit
hook refuses hand-edits. Measured motivation: 6 of 7 lands touched both CHANGELOG.md and the pyproject version.
Current state: 1,542 fragments in the working tree and the pyproject and the manifest read 0.531.1.dev356 (356 dev
bumps since the last cut; CHANGELOG heads an unreleased 0.532.0); 19,211 commits in the repo.

### 5.5 Dev-version bump and publish

Every land rewrites pyproject to the next PEP 440 dev version (X.Y.Z -> X.Y.(Z+1).dev1, .devN -> .dev(N+1)) when the
explicit release-cut callback returned nothing; toggle `[tool.frob] dev_version_bump` and major-boundary guard
`dev_version_major_ack`; read from the root's git object at the pre-land tip. `frob release publish [--dry-run]` =
bump patch, stamp, sync, git add/commit/push, `uv build`, `uv publish`, argv-only subprocess, .env via python-dotenv
only on a real run. Release branch flow (docs/guides/release.md): every ticket lands on `dev`, main frozen at the
released green commit, dev merged into main at the sprint cut (`[tool.frob] ticket_land_branch = "dev"`).

### 5.6 Deprecated baseline

`frob:deprecated` directive plus DEPR001-006 gates; `frob deprecated` lists them (listing only, no --apply; orphaned =
owning ticket closed); repo-root `frob-deprecated-baseline.lock.json` is the ratchet. Verb-level deprecations use the
same machinery (`ops` alias sunset 2026-12-01; `fmt`, `gitlog` also sunset 2026-12-01).

### 5.7 ghio, ci_report, ci_validity

- ghio.py (490): the one typed seam for the `gh` CLI. preflight, list_runs, view_run, job_log (via job-scoped `gh api
  .../actions/jobs/ID/logs`, because `gh run view --log` refuses while the run is in progress). GhError: NotInstalled,
  NotAuthenticated, CredentialsExpired, NoRemote (normal off GitHub), RateLimited, NetworkUnreachable, NotFound,
  EmptyLog, RunInProgress, GhFailed. JobLog carries explicit empty and truncated (cancelled run) booleans. Tests fake
  run_argv.
- ci_report.py (422), CLI `frob ci report <run-id>`: parses job logs into TestFailure / FailureCluster / JobReport /
  RunReport. Never positional (xdist interleaves); prefers this repo's own `SUITE-RESULT:` / `SUITE-RESULT-FAILED:`
  lines from tests/conftest.py, with ISO-timestamp-prefix tolerance, falling back to vanilla pytest summary blocks;
  otherwise "not_recoverable".
- ci_validity.py (352): classifies each test outcome as STILL_VALID, STALE or UNKNOWN against the current tree by
  diffing from the run's head_sha and walking affects() closure; truncated walks are UNKNOWN, never STILL_VALID.
- CI tie-in: release.yml's verify-ci-status job (scripts/verify_release_ci_status.py) fail-closed resolves ci.yml's
  conclusion for the exact commit (GREEN/RED/ UNDETERMINED; override needs a reason).

Verdicts (release and CI integration):

| Node | Verdict | Reason |
|---|---|---|
| manifest + semver from API graph | KEEP | unique, mechanical, and cheap once graph exists |
| UnbumpedApiChange refusal | KEEP | stamp-alone footgun was real; keep reasoned override |
| changelog.d fragments | KEEP | collision-free by construction; drop per-land CHANGELOG rewrite |
| per-land dev-version bump | DROP | dev356 counter rewrites shared files every land |
| publish verb | MERGE | thin wrapper; fold into CI release workflow |
| deprecated baseline | MERGE | generalize to one expiry-ratchet mechanism with debt |
| ghio | KEEP | typed gh seam, useful in v2 as a library |
| ci_report | MERGE | fold into ghio; keep SUITE-RESULT contract |
| ci_validity | KEEP | affects-graph staleness of CI evidence is novel |

## 6. fleet/, deploy/, scaffold/, claude sync, .claude/hooks, skills sync

### 6.1 fleet/ (413 lines) and fleet.toml

`fleet.toml` = `[[repo]] name, path` entries (path relative to the MANIFEST's directory); override with `--manifest`
or `[tool.frob] fleet_manifest`. frob's own manifest lists the 9-repo estate (frob, lithos, feldspar, graphite,
typani, lograder, aprog-public, aprog-private, logand.app). Verbs: `frob fleet status [--manifest] [--json]
[--skip-gates]` and `frob fleet route --repo NAME --title T [--kind K] [--priority P] [--scope G] [--body]`.
- collect_status per repo: branch and dirty via `git status --porcelain=v2 --branch`; gate counts via `uv run
  --project <repo> frob check --json` with a 120 s timeout (never a bare PATH `frob`, which is a known stale global);
  doable count read directly from that repo's ledger. Every failure degrades to a zeroed row, never aborts the rollup.
  rollup sorts reddest-first (errors, warns, doable).
- route_ticket files a TicketSpec (origin=agent) directly into the sibling's ledger through frob.tickets.new_ticket
  (no second process); refuses with RouteFailed when the target has no ledger at all (would otherwise silently
  bootstrap one). FleetError: ManifestNotFound, ManifestMalformed, RepoNotFound, RepoPathMissing, RouteFailed. No
  automatic classifier of which repo owns a finding.
- Related loose script: scripts/fleet_status.py (coordinator probe: root cleanliness, leases, worktree liveness,
  per-ticket readiness), referenced by a frob-suggest rule.

### 6.2 deploy/ (2,928 lines): host manifest compiler

`std.host` HostManifest facts (strata design model: service user `runs_as`, `owns` paths/modes, `listens` ports, `may`
capabilities, windows platform, service account, ACLs, pipes, binPath, krb SPNs/delegation) are compiled to
`deploy/install.sh`, `status.sh`, `uninstall.sh` (Linux/systemd) and `install.ps1`, `status.ps1`, `uninstall.ps1`
(Windows) by `frob deploy generate [--check] [--out-dir] [path]`. Scripts are check-then-apply (idempotent), systemd
units hardened (NoNewPrivileges, ProtectSystem=strict, PrivateTmp, CapabilityBoundingSet from `may`, SystemCallFilter
from the strata seccomp exporter). Gates wired as extra check stages (not in the gates job table): DEPLOY001 digest
drift lock (`# frob-deploy-manifest-digest` header over all six filenames), DEPLOY002 (script mutates something
undeclared), DEPLOY003 (declared but absent) by parsing the script's mutation surface. `frob deploy audit --vm NAME
--ssh-host --ssh-user --ssh-key --base-snapshot --output` drives VirtualBox (VBoxManage plus ssh) through restore ->
install -> reinstall -> uninstall with state captures and four proofs; skipped (never faked) when VBoxManage is
absent; env FROB_VM, FROB_VM_SSH_HOST, FROB_VM_SSH_KEY. Disclosed v0 cuts: empty windows privilege set, no deny-logon
rights, no RBCD delegation.

### 6.3 scaffold/ (2,793 lines): templates and managed blocks

`frob scaffold list | new <type> <name> [--output DIR] [--force] | unity-project DIR [--force] | pool
warm|lease|status`. Jinja2 templates under scaffold/data/{shared, types}. Types: python-tool, python-library,
pyo3-library (maturin + cargo workspace), web-app (Vite/React/TS/Vitest), cpp-library, cpp-tool (CMake/ctest,
CI+release+branch-protection workflows), pybind11-library. Python types ship App/AppConfig pattern, house logging,
frob.toml (profile rapid), invariants/, .env.example (gitignored), Makefile, CI. NO tickets seed (ledger starts v2).
`unity-project` scaffolds onto an existing Unity dir: frob.toml with Unity excludes, `dotnet test` runner,
design/frob.strata plus one fragment per .asmdef. The first-run sequence needs a commit between `frob check
--stamp-coverage` and the re-check or PRE001/SCOPE001 fire by design.

Managed blocks (scaffold/_managed.py, BEGIN/END marker pairs, drift-checked by doctor `scaffold_blocks` and
`scaffold_conformance_status`, installed by `apply_managed_blocks`): `makefile-core-shim` (Makefile), a Makefile
wrapper block and a make.bat wrapper block derived from `frob run` commands, `gitignore-standard` (.gitignore), git
hooks `pre-commit` and `pre-merge-commit` (worktree-lease guard; bodies also forbid land-owned files and raw ticket
merges), and a stash guard. Content outside markers is never touched; staleness is measured against what frob would
install now (no stamp file). Warm worktree pool (scaffold/_pool.py): pre-built worktrees with natives compiled and
main merged, manifest at `<git-common-dir>/frob-pool/manifest.json`, warm_pool/lease_worktree (background
refill)/pool_status.

### 6.4 claude sync (`frob claude [--check]`, `frob claude sync`)

Thin adapter (app/claude_runner.py) over the stdlib-only canonical script `.claude/hooks/sync-claude-config.py`. REPO
IS CANONICAL: it copies a `MANAGED` list into ~/.claude/ behind a do-not-edit banner, atomically; `--check` reports
drift, exit 1; never syncs home -> repo. MANAGED (11 entries): _shellscan, frob-suggest, frob-timeout-guard,
root-write-guard, _root_write_guard_lib, _agent_context, root-cleanliness-detector, diagnosis-nudge,
pgrep-self-match-guard, dispatch-telemetry, and docs/guides/agent-playbook.md -> ~/.claude/refs/. NOT in MANAGED (so
not materialized, run only from this repo's path): frob-directive-guard, pending-background-guard,
tool-call-telemetry. T-3408 stale-source guard refuses to sync a file whose worktree copy is behind `main`. Drift
surfaces three ways: a SessionStart hook prints a systemMessage, `drift_warning` on stderr of every frob invocation,
and a `frob check` gate (T-1809).

### 6.5 .claude/ hooks (14 files, 4,636 lines; registered in .claude/settings.json)

settings.json also sets `worktree.baseRef = head` and hard-codes absolute paths
(<frob-v1>/.claude/hooks/...). Registration: PreToolUse 6 entries, PostToolUse 2, SessionStart 2, Stop
3. Hooks run under system python3 (3.10), so they import nothing from frob.

| Hook | Event / matcher | What it intercepts and does |
|---|---|---|
| frob-timeout-guard.py | PreToolUse Bash | DENY when command position runs `frob ticket land/done-report/work/new`, `frob check` or `frob test` with Bash tool timeout < 300000 ms; also DENY any `run_in_background=true` (harness auto-backgrounds at 120 s and agents then stall) |
| pgrep-self-match-guard.py | PreToolUse Bash | DENY `pgrep -f <literal>` and `ps ... \| grep <literal>` (matches its own bash -c shell, poll loops never exit); names `pgrep -x`, variable pattern, `[f]oo` recipes |
| frob-suggest.py | PreToolUse Bash\|Edit | block-once nudge toward the frob equivalent; identical re-run allowed; 3rd+ identical run in 12 h TTL needs FROB_SUGGEST_ACK. 11 regex rules: make-target, hand-edit-ledger (tickets.md redirects/sed -i/tee), unscoped-pytest (bare pytest w/o path or ::), raw-linters (ruff/mypy/ty check|format), raw-worktree (`git worktree add`), raw-coverage (`coverage run`, `pytest --cov`), recursive-grep (grep -r), unscoped-symbol-search (git grep w/o `-- path`), raw-find-name (find -name), handrolled-floor-count (`frob check \| grep`), handrolled-fleet-probe. Plus an Edit rule: rewriting an existing import of the same module in 2+ distinct files within the TTL (rename shape). State in ~/.claude/hooks/state/frob-suggest |
| root-write-guard.py (+ _root_write_guard_lib.py) | PreToolUse Write\|Edit\|NotebookEdit\|Bash | DENY any write into the shared primary checkout unless an explicit positive marker or measured exemption applies (default inverted by T-2850); infers Bash write targets from redirects, tee, sed -i, `frob ticket <verb>` with no cd/--path; fail-open on unparseable input |
| frob-directive-guard.py | PreToolUse Write\|Edit\|NotebookEdit\|Bash | DENY a `frob:tests` target using pytest's `Class::method` (second `::`) instead of file::dotted.qualname (pre-empts DOC007/DRIFT002) |
| tool-call-telemetry.py | PreToolUse and PostToolUse, all tools | append `kind="tool"` rows (tool, phase, head_sha, dispatch_id, command_shape, parsed frob verb/subverb, output_tokens_est on post) to .frob/telemetry.jsonl |
| root-cleanliness-detector.py | PostToolUse Bash | REPORT-only: after an agent's Bash call, `git status --porcelain` on the shared root; warns when dirty |
| dispatch-telemetry.py | SessionStart and Stop | write `kind="dispatch"` start (worktree, branch, cold_start) and end events keyed by session id |
| diagnosis-nudge.py | Stop | non-blocking systemMessage when the turn states a diagnosis (word-boundary regex phrases) but no `frob ticket new` appears in telemetry; respects stop_hook_active; rate-limited |
| pending-background-guard.py | Stop | BLOCK ending a turn that strands a pending background Bash task |
| sync-claude-config.py | SessionStart (`--check`) | prints "Claude config DRIFT" message when ~/.claude copies differ; also the sync tool itself |
| _shellscan.py, _agent_context.py, _root_write_guard_lib.py | libraries | command-position regex (POS), quote/heredoc stripping, segment splitting; agent-vs-coordinator discriminator; worktree-fact helpers |

Cross-cutting: the hooks encode five recurring failure classes (raw commands that bypass accounting, backgrounded long
commands, agents dirtying the shared root, unwatched pollers, lost telemetry). Documented in
docs/guides/claude-hooks.md.

### 6.6 skills/agents sync (`frob sync-skills [path] [--claude-dir DIR] [--force]`)

Bidirectional pathlib/shutil sync of repo `agents/` and `skills/` dirs into ~/.claude/agents and ~/.claude/skills
(replaced a Makefile bash recipe). Provenance manifest `<claude_dir>/.frob-sync-manifest.json` keyed by repo root
records which entries each repo installed: removal only for entries this repo installed; collisions with
hand-maintained or other-repo entries are skipped unless `--force` (SyncCollision). Note: the frob v1 checkout
currently has no `agents/` or `skills/` directory at root; skills are delivered via ~/.claude and the MCP `serena`
server.

Verdicts (ops):

| Node | Verdict | Reason |
|---|---|---|
| fleet status/route | KEEP | cheap cross-repo rollup; reuse ledger API directly |
| deploy generate/audit | DROP | niche strata-host compiler; ship as separate tool |
| scaffold templates | KEEP | onboarding path; slim to fewer types |
| managed blocks | MERGE | one marker mechanism for hooks, Makefile, gitignore |
| warm worktree pool | DROP | Rust-native builds and shared target dir remove need |
| claude sync | MERGE | one hook-install command; stop home-dir copies |
| .claude hooks | MERGE | collapse 8 python spawns per call into one Rust hook binary |
| skills sync | DROP | provenance manifest complexity; use plain install-on-init |

## 7. app/, config, process, render, and small ops verbs

### 7.1 app/ (46,736 lines; AppConfig 1,536 + _config_external 981)

Entry: `frob.__main__.main` installs a SIGTERM reaper first, runs three stale-binary probes on stderr (version
mismatch vs repo pyproject, `min_frob_version` floor from frob.toml, git-sha fingerprint of running package vs repo
HEAD), a concurrent-check advisory, claude drift warning, then builds `AppConfig` from argv plus `pyproject.toml
[tool.frob]` and runs `App(cfg)()`. Unhandled exceptions print `frob: <exc>` exit 1. `App.__call__` lazily imports
only the one `*_runner` module needed (PEP 562 lazy aliases) because eager import of about 30 runners made every CLI
call pay the whole import graph.

AppConfig design (the v1 anti-pattern to avoid): ONE flat pydantic model with 432 fields holding every flag of every
subcommand; `Subcommand` StrEnum has 45 members (one per verb plus the group verbs). Group verbs
explore/quality/design/ops exist only to consolidate (ops is deprecated, sunset 2026-12-01). Direct-dispatch verbs
bypass AppConfig entirely: bind, agent, worktree, sync-skills, refactor, release publish. `from_external` forwards
argparse values into the model through six hand-maintained field-name tuples (string, path, int, float, list, bool)
plus an ad-hoc set; a flag missing from every tuple was SILENTLY dropped (two real incidents), so a static check
`find_dropped_cli_flags` ratchets it (317 flags examined, 0 dropped). Enum-valued fields have validators that list
legal values. Precedence: CLI flag beats `[tool.frob]`. The pyproject path resolves from `--path`/ticket
worktree/FROB_ROOT or cwd.

Runner modules: about 50 `app/*_runner.py` files (one per verb, plus the `ticket_runner/` package), and also `frob
whereis`, `frob check --census`, waive audit, and `frob run` (named commands that replaced Makefile recipes).

### 7.2 frob.toml tables and keys (v1 reality)

Every `*_schema` table points to a `module:symbol` known-key set; PROFILESCHEMA001 et al report UNRESOLVED (not clean)
if the declaration is missing or broken, and since T-3273 several default to frob's own set when undeclared. A
project's scaffolded frob.toml carries only: check_base, [profile], [testing], [[test.runner]], [gates.severity],
[tickets], [[refs.entrypoint]].

| Table / key | Keys (known set) | Meaning |
|---|---|---|
| top-level scalars | check_base, min_frob_version | diff base branch; floor that triggers stale-binary warning |
| [profile] | profile, override_ratchet | rapid or standard (fortress reserved); ratchet override |
| [testing] | min_unit_cases, min_integration, unit_branch_cov, module_line_cov, system_line_cov, pair_integration | TEST floors |
| [[test.runner]] | language, command, all_command, cwd, collector, timeout_s | per-language runner |
| [[native]] | name, build_cmd, language | compiled extension modules |
| [graph] | exclude | glob list read by every walker |
| [arch] | max_function_lines, max_class_methods, max_local_imports, max_nesting_depth, max_file_lines, plus god-module / LCOM4 / mixed-concern thresholds (10 keys) | structural limits |
| [arch.layering.layers] / [arch.layering.allow] | free-form layer map | DIP layering contract |
| [dup] | enforce, threshold, region_kernel, native_rungs | clone detection |
| [gates] | dstack_threshold | misc gate threshold |
| [gates.docs] | comment_run_max, docstring_max | doc-volume caps |
| [gates.severity] | rule -> error/warn/advisory/... | per-rule override |
| [gates.ratchet] | rules (e.g. ARCH104, DOCARCH002) | pool-baselined ratchet rules |
| [tickets] | default_milestone, registry_files | ticket defaults |
| [refs] / [[refs.entrypoint]] | path (glob ok), reason | REF001/002 exceptions (37 entries in frob's own) |
| [[docblocks.commands]] | prog, parser, config, forwarded | doc-block command checks |
| [vet], [vet.allow] | see section 3 | dependency policy |
| [fuzz] | enforce, budget_s, max_reject_rate | fuzzing |
| [strata] | design_dir | design directory (default design/) |
| [tool_registry] | allow_missing | tolerated missing external tools |
| [ty] | target_platforms | typecheck platforms |
| *_schema tables | known_keys / entrypoint_schema / ratchet_known_keys | module:symbol pointers (schema-of-the-config checks) |

frob's own frob.toml is 1,486 lines, mostly `frob:` exceptions and rationale comments in these tables; the scaffold
default is about 40 lines.

### 7.3 `[tool.frob]` in pyproject.toml

Any AppConfig field name can be set here (CLI wins), but the keys with real semantics are: dev_version_bump,
dev_version_major_ack, ticket_land_branch, ticket_land_default ("queue" turns a bare `land --worktree` into a queue
enqueue; the docstring spelling `land_default` is NOT read - T-5106), ticket_points_required, vet_cve_mirror,
fleet_manifest, unity_editor, land_silent_phase_dump_s, done_report_check_budget_s. frob's own sets
dev_version_bump=true, ticket_land_branch="dev", ticket_land_default="queue".

### 7.4 Profile ratchet (tickets/_profile.py)

`rapid` (default for scaffolds) / `standard` (default when absent) / `fortress` (enum only). One-way auto-ratchet
rapid -> standard when any of: repo files >= 300, total tickets >= 200, concurrent leases >= 5
(`.frob/profile-ratchet.json`; `frob profile show|downgrade` is the only way back). rapid relaxes: no TEST016 on land,
single post-land sweep, no baseline-snapshot worktree, light evidence for docs/chore, REL001 off; since T-4413 it runs
a SCOPED synchronous check (diff files plus one hop of dependents) and defers the repo-wide sweep (batched, T-4414),
with CI authoritative (T-4415). Never relaxed: ledger integrity and land-proof.

### 7.5 Excludes

excludes.py (459 lines) is the single reader of `[graph] exclude`; BUILTIN_SKIP_DIRS (a floor: __pycache__, .git,
.venv, venv, node_modules, target, build, dist, .frob, .worktrees, caches, .claude/worktrees, ...) plus conditional
UNITY_EXCLUDE_GLOBS (Library/**, Temp/**, Logs/**, obj/**, *.meta). `walk_pruned` / `iter_files` prune before
descending and prefer `git ls-files`; WALK001 flags raw rglob/os.walk.

### 7.6 worktree and agent verbs

- `frob agent env [path]` (default action), `frob agent brief <ticket>`: env export lines (FROB_WORKTREE, FROB_AGENT,
  PYTHONPATH, bounded xdist workers) with ALL logging forced to stderr so `eval "$(frob agent env)"` is safe; brief
  composes the playbook's section-0 contract plus ledger fields. 650 `agent` tool-hook sightings in 12 days (1,269
  `agent env` rows): it is a per-command ritual.
- `frob worktree sweep [--dry-run] [--min-age-hours]`, `remove <path> [--dry-run]`, `release-lease <id>`: lease-aware
  stale-worktree cleanup with a liveness check (a raw `git worktree remove` once deleted a live agent's checkout).
- worktrees/ package: sweeps disposable `git worktree add` scratch dirs in /tmp left by killed land/BUG002 runs
  (pid-file liveness).
- `frob doctor` flags PYTHONPATH import-source mismatch (running `import frob` resolves from root src instead of the
  worktree).

### 7.7 logging/ (523 lines) and the house standard

~/.claude/refs/logging.md standard: `get_logger(__name__)` per module, no print() except intentional CLI output;
package layout logging/{__init__, logger, formatter, filter, config.toml}; dictConfig from TOML; stdout handler
DEBUG-level with a below-WARNING filter and message-only formatter; stderr handler WARNING+ with a LEVELNAME prefix;
root DEBUG; package-data must include config.toml.

v1 follows it and adds: lazy stdout/stderr handlers that re-read sys.stdout each emit (pytest capture safety), default
stdout level INFO (DEBUG hidden; `-v` or FROB_VERBOSE=1 or FROB_LOG_LEVEL=NAME restores), `quiet_stdout_logs` /
`stdout_log_level` / `quiet_query_stdout` context managers that mute stdout logs around `--json` payloads, color via
should_color/paint (NO_COLOR, FORCE_COLOR, TTY). Volume: 4,529 log call sites in src (warning 1,424; error 1,210; info
1,204; debug 687; exception 4). Pain points visible in the data: logs and human output share stdout, so JSON paths
must mute logging; the process-wide handler swap is documented as not thread-safe; FROB_WORKER_STDOUT_LOG_LEVEL exists
for pool workers.

### 7.8 process/ (4,699 lines) and derived-state locks

- process/_guard: `guarded_subprocess_run` returns Result with ExecDisabled (FROB_DISABLE_EXEC kill switch), Timeout,
  SpawnFailed; FROB_DISABLE_NET declared but with no real call site. Every tool runner (ruff, ty, pytest, cargo,
  tsc...) spawns through it.
- process/parsers/ (12 parsers, section 7.12) normalize tool output.
- _lock.py: portable_flock_acquire/release (fcntl on POSIX, msvcrt exclusive-only on Windows, loud refusal otherwise)
  - the one primitive behind ledger_lock, land.lock, land-queue lock, mutation-sweep lock, coverage lock, daemon
    singleton. `derived_state_lock(root, exclusive)` over `.frob/derived.lock`: every check holds SHARED for its whole
    run; writers (graph build, dup) take EXCLUSIVE via the process-aware `derived_state_write_lock`; a past deadlock
    came from a ProcessPoolExecutor worker needing EXCLUSIVE while the parent held SHARED. derived_state.py
    fingerprints DERIVED_ARTIFACTS (manifest at `.frob/derived-state-manifest.json`) so checks fail early on corrupt
    caches.
- Process pools: gates run in a forkserver ProcessPoolExecutor; `_reap` installs a SIGTERM reaper (killed `frob check`
  leaked forkserver trees, 94 procs / 17.3 GB swap measured), counts concurrent checks (WARN at 4+), pid liveness
  checks (_pid_liveness), pytest-spawn resolution, project-scoped toolchain spawns (_project_tool), cross-platform tty
  check, FROB_CHECK_MAX_WORKERS and FROB_CHECK_PER_WORKER_MEM_MB for check pool sizing, `.frob/check-admission`. Both
  the pool and the locks exist mostly to survive many concurrent frob processes sharing one checkout.

### 7.9 render/ (747 lines) and output formats

Renderer.for_stream(stream): color resolved ONCE (--no-color / --color=never, --color=always, NO_COLOR, FROB_NO_COLOR,
CLICOLOR_FORCE, TERM=dumb, isatty). Five semantic colors (good, warn, critical, muted, accent), colorblind-safe
(critical is bold). Elements via `r.write`: heading, subhead, kv, status, count_summary, path, ticket_id, table, tree,
count_deltas, severity shortcuts, plus TTY-only ephemeral progress. Plain form is canonical and deterministic. Output
formats in v1: text via Renderer and `--json` (pydantic model_dump) per verb; `frob sys export --format` (seccomp
etc.) is the only other `--format`. NO SARIF, NO JUnit-XML, NO GitHub annotation output exists (grep found zero). The
`--json` flag is per-verb and payload shapes are model dumps, with parity tests against the daemon.

### 7.10 findings.py (114 lines): the Finding model

v1 has no class named Finding; the model is `Violation` (frozen pydantic): rule, severity, file, line, message, waived
(WaiverRef: site, reason), symref (per-symbol waiver precision), metric (for waiver `ceiling=N`), severity_pinned.
Severity is a four-way StrEnum: error (fails check), warn, unresolved (check could not decide; never counted as error,
never dropped), advisory (reported, never affects exit or ratchet). DebtEntry (rule, site, ticket, until, expired).
`frob:waive`, `frob:debt` and `frob:deprecated` directives are the suppression language.

### 7.11 doctor (2,503 lines), clean, natives, stats, gitlog

- doctor: DoctorReport = frob_version, native extension status, derived-state fingerprints and drift, scaffold
  managed-block conformance, stale mutate journals, malformed ticket edges, stale ticket leases, venv shims, external
  tools, stale_binary, global_binary skew, live land process, import_source mismatch, unity project/editor,
  profile_recommendation, healthy, remediation. External tool categories REQUIRED (python, git, uv, ty), OPTIONAL
  (cargo, npm, ctest), OPTIONAL_FOR_GATE (axe-core, pa11y, lighthouse), REQUIRED_FOR_FAMILY (sqlfluff, squawk for SQL;
  crunk for LAYOUT, relevance by repo content), relevance-gated cargo-audit. Measured: 2 runs, median 31.8 s.
- clean: tiered, artifact-only: SAFE (.coverage fragments, __pycache__, .pytest_cache), ALL (+ build/, dist/,
  egg-info, target/, caches, coverage.xml), DEEP (+ frob's own .frob/ state and FROBLEMS.md; protects
  rapid-debt.jsonl). Preview by default, `-y` to execute, `--json`.
- natives: `frob natives build` runs `maturin develop --uv --release` per declared rust [[native]] with
  CARGO_TARGET_DIR keyed on the git common dir (shared across worktrees); reuses a byte-identical build from another
  checkout (a rebuild cost 70-190 s per land before T-5808); .frob/native-content-stamps.json,
  native-build-attempts.json; FROB_NO_NATIVE_AUTOREBUILD. 571 `natives build` tool sightings in 12 days: native build
  is a constant tax of the Rust/PyO3 split that v2 (all Rust) removes.
- stats: `frob stats [--path] [--days N] [--json]` tickets (state/kind counts, failure-log entries) and commit
  cadence; `--agentic` over telemetry; quantile sketches (stats/_sketch.py) back `frob perf hot`. Measurement only,
  never a gate.
- gitlog: conventional-commit history filter (levels major, changelog, user, full; --since, -n, --all, --json);
  deprecated in favor of `frob explore gitlog`.

### 7.12 parse, narrative, docs, format

- parse: `frob parse <tool> [--exit-code N] [--passthrough] [--json]` reads stdin or file. Tools: pytest, ruff (text
  or JSON), ty, cargo (JSON or text), clang-tidy, valgrind (text or XML), clang/clang++/gcc/g++, junit/gtest/catch2
  (JUnit XML), tsc, eslint (JSON). Common ToolResult / Diagnostic / TestCase / Measurement models; unparsable output
  is never silence (tool_parse_failure_result), and measured vs not_measured is first-class so a gate that could not
  run is not a pass.
- narrative: `frob narrative move FILE LINE [--keep-file] --reason T [--dry-run]` relocates the history half of a `#
  T-####:` comment block into the named ticket body (idempotent marker; directive lines always kept); plus a detector
  and bulk tools (NARR001). Doctrine: code carries utility, tickets carry narrative; land may check, never rewrite.
  Related docstring standard (docs/modules/docstrings.md): the "would this help a reader reuse this" purpose test,
  absence is valid, narrative in tickets, DOCARCH001 enforces the mechanical half.
- docs (frob.docs, 448 lines): docstring extraction (Docstring, DocEntry, DocMatch) and markdown overview/search for
  `frob docs` / `frob explore docs-search`; `--sync-commands` regenerates the docs/modules/cli.md command table and
  `--sync-command-pages` (T-4702) regenerates docs/commands/*.md stubs from the live argparse tree.
- format/fmt: `frob format [--code] [--directives] [--check] [--select-imports-only] [--json] [paths...]`: ruff check
  --fix plus ruff format, and canonical-form rewriting of `frob:` directive comments. `frob fmt` is a deprecated alias
  (sunset 2026-12-01). 82 `format` sightings, zero cli records.

Verdicts (app and small verbs):

| Node | Verdict | Reason |
|---|---|---|
| AppConfig god-model | DROP | per-verb typed args; no 432-field flat struct |
| group verbs (explore/quality/design/ops) | DROP | consolidation hack; design the verb tree once |
| frob.toml + schema-of-config tables | MERGE | one typed config with derived schema, no *_schema pointers |
| [tool.frob] in pyproject | DROP | one config file; avoid two precedence layers |
| profile ratchet | MERGE | keep rapid/standard idea as explicit config, not auto |
| excludes | KEEP | single prune-aware walker, honor gitignore |
| agent/worktree verbs | MERGE | fold env export and sweep into one worktree subcommand |
| logging | MERGE | structured tracing crate; keep stdout-clean-for-JSON rule |
| process guard + parsers | KEEP | typed spawn seam and normalized tool results |
| derived-state locks | MERGE | single store with transactions replaces flock web |
| render | MERGE | add SARIF and JUnit emitters; keep plain-canonical rule |
| findings model | KEEP | four-way severity incl. unresolved is a good idea |
| doctor | KEEP | slim to env checks; drop v1 cache-drift work |
| clean | MERGE | one `frob clean` with tiers over single store dir |
| natives | DROP | pure-Rust v2 has no maturin builds |
| stats | MERGE | fold into telemetry reporting |
| gitlog | DROP | already deprecated; git-cliff covers it |
| parse | KEEP | tool-output normalization is useful as a library |
| narrative | DROP | policy tooling for v1 comment habits |
| docs extraction | MERGE | fold into graph symbol docs |
| format/fmt | MERGE | thin wrapper; keep directive canonicalizer only |

## 8. CI: .github/workflows/ci.yml (1,237 lines) and release.yml (444 lines)

### 8.1 ci.yml

Triggers: push to main and dev, and pull_request. Permissions `contents: write` (the self-gate step may push a filed
regression ticket, push events only). Concurrency group per ref with cancel-in-progress. Env pins: UV 0.11.19, Rust
1.98.0, maturin 1.7.4 (manual pins, outside Dependabot; added after an unpinned uv cache-hit/miss split produced 68
phantom macOS failures).

| Job | Runs on | Timeout | What it does |
|---|---|---|---|
| build (matrix, fail-fast off) | ubuntu-latest, windows-latest, macos-latest | 150 min job; ubuntu pytest step `timeout -s ABRT 40m` with stack dump | checkout, setup-uv, Rust toolchain, print resolved versions, cargo cache (key = os + arch + Cargo.lock + kernel pyproject), `uv sync --all-extras --all-groups`, `make core` (maturin develop frob-core and strata-core), `make core-wheels`, `cargo test --lib` in both kernels, `ruff check src tests`, `ty check src`, per-OS full pytest (`-n auto`, 120 s per-test thread timeout) writing SUITE-RESULT lines into the step summary, self-gate (fresh collection + diagnostics, then `frob check` on frob itself, job summary, files a ticket on self-gate regression), TEST012 lock-drift check, coverage-stamp and delta-baseline "measurable and clean" check |
| standalone-install | ubuntu-latest | default | build abi3-py311 frob-core, frob-strata and bare wheels, install into a clean venv, `frob --help` must not crash without natives, `frob check` on a tiny fixture repo must not crash |

Pins and update path: every third-party `uses:` is pinned to a 40-hex commit SHA with a version comment (T-3922;
VET009 enforces); `.github/dependabot.yml` runs the github-actions ecosystem weekly with target-branch dev.
windows-latest was advisory until 2026-09-13 (T-3512) and is now blocking.

Observed durations (gh, last 100 ci.yml runs, 2026-09-07 to 2026-09-27, all push to dev):

| Conclusion | Runs | Median min | p90 min | Range min |
|---|---|---|---|---|
| success | 7 | 123 | 129 | 92-129 |
| failure | 64 | 69 | 106 | 6-127 |
| cancelled | 29 | 44 | 95 | 0-116 |

So 7% of recent CI runs were green and each green run cost about two hours of wall-clock on the slowest leg; the
150-minute job ceiling sits within 21 minutes of the green median. Cancellations are likely supersession by the next
push (cancel-in-progress; not verified per run). The lock-drift and self-gate steps are v1 frob checking itself inside
CI.

### 8.2 release.yml

Manual `workflow_dispatch` ONLY (no push/tag/schedule trigger; a test asserts it), inputs override_red_ci and
override_reason (override is refused without a reason), concurrency group `release` without cancel. Three PyPI
distributions publish via trusted publishing (`id-token: write`, pypa/gh-action-pypi-publish pinned by SHA, one GitHub
environment each): frob-core (env pypi-frob-core), frob-strata (env pypi-frob-strata; the `strata-core` crate dir
kept, distribution renamed in T-4485), and frob (env pypi; needs both kernels).

Jobs: verify-ci-status (fail-closed GREEN/RED/UNDETERMINED for the exact commit via
scripts/verify_release_ci_status.py; not a gate on building), build (maturin wheels for both kernels over 5 targets:
manylinux 2_28 x86_64, manylinux 2_28 aarch64 cross, macOS x86_64 cross, macOS arm64, windows x86_64; 60 min),
build-sdists, artifact-smoke (matrix; installs the built wheels into a clean venv; 60 min), upload-frob-core,
upload-frob-strata, upload-frob. Recent history (gh, 10 runs 2026-09-13 to 2026-09-15): 1 success (7 min), 6 failures
(median 6 min), 3 cancelled (median 62 min, max 258 min).

Verdicts (CI):

| Node | Verdict | Reason |
|---|---|---|
| ci.yml 3-OS matrix | KEEP | cross-platform proof matters; shrink via Rust speed |
| self-gate + lock-drift steps | MERGE | one `frob check --ci` step replaces four custom steps |
| standalone-install job | KEEP | proves binary works with no native extras |
| toolchain and SHA pinning | KEEP | measured incidents justify pins; keep Dependabot |
| release.yml | MERGE | cargo-dist style single-artifact Rust release replaces 3 PyPI dists |

## 9. Cross-cutting lessons for v2 (from this inventory)

1. Startup and per-verb latency dominate: 53% of invocations are polls under 1 s that still pay interpreter start; a
   read-only `ticket show` costs 2.7 s median. A native binary with a resident store should hit tens of milliseconds.
2. Much of v1's machinery exists to hide slowness from the foreground (rapid sweeps, async drains, deferred mutation
   queue, warm daemon, 270 MB parse cache); about 43% of recorded hours are deferred background work. Fast core first,
   then drop the queues.
3. Concurrency scaffolding (flock web, forkserver reaping, xdist sizing, admission, leases, worktree pool, SIGTERM
   reaper) is a tax of many agents on one checkout.
4. State sprawl: about 50 files under .frob plus root-level lock files; v2 wants one embedded transactional store.
5. Config sprawl: AppConfig 432 flat fields, 6 forwarding tuples, `*_schema` pointer tables, two config files with
   different precedence.
6. Observability gaps: no timing for `test`, `graph`, `format`, `coverage`; duration excludes process start; tool-hook
   rows have no duration. Time from process start and record every verb.
7. CI is red 93% of recent runs and 2 hours when green; gate on a fast scoped check, sweep separately.
