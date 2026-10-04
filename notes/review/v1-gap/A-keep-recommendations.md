# v1 gap analysis, slice A: recommendations in v2/notes/v1/*.md

Verdict on completeness: all 7 files enumerated, 0 pending, 0 blocked. 677 items classified; every KEEP or MERGE row of the three table-driven notes is individually accounted for (CLI 164 of 164, rules 261 of 261, ops verdict rows 60 of 60). Files without verdict columns (agent-usage, tickets, strata, graph-lang-dsl) were enumerated from their own recommendation sections (needs, differentiators, hints, KEEP lists, v2 recommendations), see Inventory.

Status totals: BUILT 267, TICKETED 61, DESIGNED 286, DROPPED-ON-PURPOSE 40, MISSING 23.

Conventions: `v1/` = the Python frob at the sibling checkout, `v2/` = this repository. v1 evidence cites the slice note and section or line (the notes themselves cite v1 tickets and files). A status is exactly one of BUILT, TICKETED, DESIGNED, DROPPED-ON-PURPOSE, MISSING; where a row mixes statuses it is split or the weakest is shown with the rest in the evidence. A `~xxxxxxx` is a v2 ticket handle. ASCII only.

## 1. Inventory

Enumeration commands, run from v2/ (the notes are v2/notes/v1/*.md):

```
wc -l notes/v1/{cli-surface,gates-and-rules,agent-usage,ops-and-integrations,tickets,strata,graph-lang-dsl}.md
grep -cE 'KEEP|MERGE' notes/v1/<file>.md          # lines mentioning a verdict
grep -ciE 'v2 must|lesson' notes/v1/<file>.md      # explicit must/lesson statements
# table rows: parse every markdown table row whose last column starts KEEP|MERGE|DROP
#   cli-surface.md    -> 223 rows: 120 KEEP, 44 MERGE, 59 DROP
#   gates-and-rules.md-> 362 rows: 140 KEEP, 121 MERGE, 101 DROP (sections 2-10)
```

| File | Lines | grep KEEP/MERGE | grep must/lesson | Items classified here | Basis |
|---|---|---|---|---|---|
| cli-surface.md | 577 | 167 | 0 | 169 | 164 KEEP/MERGE table rows (all verbs, flags, MCP tools); DROP rows checked for reversals |
| gates-and-rules.md | 724 | 264 | 0 | 294 | 261 KEEP/MERGE rule rows + 33 guidance/lesson statements (sections 13-18) |
| agent-usage.md | 646 | 0 | 0 | 42 | every 'Need' (6.1-6.8), the 10 design implications (7), hand-edit gaps (4), actor (5); no verdict column |
| ops-and-integrations.md | 896 | 52 | 1 | 60 | 60 KEEP/MERGE verdict rows plus perf verdict and 7 cross-cutting lessons |
| tickets.md | 596 | 1 | 0 | 47 | 13 differentiators (8.2), 9 redesign hints (8.3), 25 Jira-gap rows (8.1 'what v2 needs'); the 25-row pain-point table (7) is in Structural bugs |
| strata.md | 900 | 1 | 1 | 31 | 12 KEEP bullets (10.3), 7 design changes, 4.3 proposal A-F, rule-macro 5.5; CUT/DEFER list = DROP |
| graph-lang-dsl.md | 848 | 0 | 2 | 34 | 8.1 keep (15), 8.2 simplify (8), 8.4 add (6), 2 lessons, reversal check |

DROP rows (cli 59, gates 101) need no work; they were checked for later v2 reversals (section 6). Gates DROP rows include the 249 web ids, which v2 explicitly keeps out of core (rules.md l.172).

Coverage reconciliation by group and status:

| Group | BUILT | TICKETED | DESIGNED | DROPPED-ON-PURPOSE | MISSING | Total |
|---|---|---|---|---|---|---|
| A. cli-surface.md | 60 | 5 | 74 | 17 | 13 | 169 |
| B. gates-and-rules.md (rule rows) | 59 | 40 | 145 | 12 | 5 | 261 |
| C. gates-and-rules.md (guidance, lessons) | 22 | 0 | 9 | 2 | 0 | 33 |
| D. ops-and-integrations.md | 29 | 5 | 21 | 3 | 2 | 60 |
| E. agent-usage.md | 31 | 2 | 6 | 1 | 2 | 42 |
| F. tickets.md | 25 | 0 | 18 | 3 | 1 | 47 |
| G. strata.md | 16 | 9 | 5 | 1 | 0 | 31 |
| H. graph-lang-dsl.md | 25 | 0 | 8 | 1 | 0 | 34 |
| **All** | 267 | 61 | 286 | 40 | 23 | 677 |

Phase-2 check: CLI table rows enumerated 164, classified 169 (split rows count once per part: 164 rows -> 169 findings); rule rows enumerated 261, classified 261; ops verdict rows enumerated 60, classified 60. A script asserted that every enumerated row has an entry and no entry lacks a row. Soft spots: statuses cite design docs and the `frob` debug binary at the working-tree commit; rule semantics were matched by reading v2 rule pages and design text, not by running both tools on a corpus.

## 2. Findings

### 2.1 Summary of what the numbers say

- Foundations are BUILT and match the v1 recommendations: ULID ledger with events, leases, evidence guards, synchronous land with fingerprint ratchet, touched-set tests, drift/ack, release, PM objects, grimble binding SYS001-012, sibling contract, envelope/exit codes, remedies, schema.
- The largest block is DESIGNED but UNTICKETED: a long list of cli.md M2 verbs and rule families (status/stats/clean/wave/explore/fleet/serve/hook/batch/query, ARCH/DUP, SEC/PII, doc-consistency, TEST floors, most EXC ids, MILE, SYS013/014). Milestone 2 is ordered in build-test-ci.md but the ledger holds tickets for only part of it (GRL, packs, plugins, mirror, navigation, security, G10, G14-G19, NEAT, CI).
- A few KEEP recommendations are MISSING outright: TEST016 mutation evidence, TEST015 vacuous-test detection, COV008 evidence-protection, INV011, task runner, SEC-CVE-FINGERPRINT, actor on telemetry.
- Three KEEP statements are asserted as 'kept' in v2 text but have no mechanism: bug repro-at-parent (tickets.md l.240, l.451), `ticket done-report` (cli.md, boundaries.md), LAND-PROOF (cli.md l.165). Structural findings S-1, S-6, S-7.
- v2 reuses v1 rule ids with different meanings and never wrote the map it promises (S-10).

### 2.2 A. cli-surface.md: KEEP and MERGE rows

| Id | v1 item | v1 evidence (line: v1 judgement) | Status | v2 evidence |
|---|---|---|---|---|
| C-79-listnew | scaffold [list/new] | cli-surface l.79: KEEP (small) | DROPPED-ON-PURPOSE | v2/docs/design/boundaries.md 2.6: scaffold templates dropped for the product; `frob init` is the apply path (BUILT, v2/crates/frob/src/init.rs) |
| C-79-apply | scaffold [apply] | cli-surface l.79: KEEP (small) | BUILT | v2/crates/frob/src/init.rs (`frob init`: knobs, .gitignore, merge driver) |
| C-80 | explore | cli-surface l.80: MERGE-INTO map/outline/xref flat | DESIGNED | v2/docs/design/cli.md section 4 row `graph query`, `explore outline\|map\|xref\|docs` (M2, crate frob-explore); code-model.md l.416; no ticket |
| C-81 | outline, map, xref | cli-surface l.81: KEEP as `explore`-style readers | DESIGNED | same row; also `grimble explore outline\|map\|xref`; no ticket, no code |
| C-82-cycle | cycle, dup, arch [cycle] | cli-surface l.82: MERGE-INTO check | TICKETED | ~1QBHP7T G10 grimble-arch: CYCLE, LARGE, DEAD; cli.md l.272 says cycle lives in grimble |
| C-82-dup, | cycle, dup, arch [dup, arch] | cli-surface l.82: MERGE-INTO check | DESIGNED | rules.md section 3 CYCLE/ARCH/LARGE/DEAD/DUP row, section 8 crate grimble-arch; G10 ticket names only CYCLE, LARGE, DEAD, so ARCH and DUP have no ticket |
| C-87 | docs | cli-surface l.87: MERGE-INTO explore | DESIGNED | cli.md row `explore ... docs`; no ticket |
| C-89 | bind | cli-surface l.89: MERGE-INTO check | DESIGNED | rules.md BIND family (cross-language sig mismatch); code-model.md l.323 replaces `frob bind`; no ticket and no BIND rule in code |
| C-90-agent | agent [agent env] | cli-surface l.90: MERGE-INTO ticket | DESIGNED | `agent env` need is the root-write guard + holder identity: frob-hook (cli.md `hook <event>` M2, git-io.md 5) and tickets.md l.289 FROB_AGENT as actor label; no verb planned, no ticket |
| C-90-agent | agent [agent brief] | cli-surface l.90: MERGE-INTO ticket | BUILT | `frob ticket brief` (v2/crates/frob-ledger/src/brief.rs) replaces `agent brief` |
| C-91 | worktree | cli-surface l.91: MERGE-INTO ticket | BUILT | stale-worktree cleanup is automatic: ~BZXZK29 (done) v2/crates/frob-worktree/src/gc/worktrees.rs, `frob doctor --fix`; explicit `worktree sweep\|remove` verbs are cli.md M2 row, unticketed |
| C-94 | narrative | cli-surface l.94: MERGE-INTO check | DESIGNED | cli.md row `narrative move` (M2, frob-obligations); documentation.md NARR001-003; no ticket |
| C-95 | check | cli-surface l.95: KEEP (core) | BUILT | v2/crates/frob-check, `frob check` |
| C-96-gitlog | gitlog, stats, debt, deprecated [gitlog] | cli-surface l.96: KEEP (as explore subverbs) | MISSING | searched `gitlog`, `conventional commit`, `git log` in design/tickets/code: nothing; v1 notes disagree (cli-surface KEEP, ops-and-integrations DROP). Changelog is fragment-based (REL003), so low value |
| C-96-stats | gitlog, stats, debt, deprecated [stats] | cli-surface l.96: KEEP (as explore subverbs) | DESIGNED | cli.md row `stats` (M2, frob-pm); architecture.md 5 telemetry mined by `frob stats`; no ticket |
| C-96-debt, | gitlog, stats, debt, deprecated [debt, deprecated] | cli-surface l.96: KEEP (as explore subverbs) | DESIGNED | `exceptions list` (cli.md M1 row, not in binary) + exceptions.md 3; deprecated sunset = DEPR family in rules.md 3; no ticket |
| C-97 | graph | cli-surface l.97: KEEP | BUILT | `frob graph why\|affects` built (v2/crates/frob-ack); `graph query` is the cli.md M2 row |
| C-98 | ack | cli-surface l.98: KEEP (core) | BUILT | `frob ack` (v2/crates/frob-ack, gob-lock) |
| C-99 | pool | cli-surface l.99: KEEP (ratchet baseline) | DESIGNED | baseline kind of exceptions (exceptions.md 2, 3; rules.md 6) replaces `pool`; cli.md l.272 lists pool as removed; land ratchet by fingerprint BUILT (~QAFRXM3) but no committed `frob-ratchet.lock.json` verb |
| C-100 | profile | cli-surface l.100: KEEP | DROPPED-ON-PURPOSE | rules.md 7: no one-way ratchet, one `[check] strictness` knob; cli.md l.4 profile maps in `frob migrate config` |
| C-101 | registry | cli-surface l.101: MERGE-INTO check | DESIGNED | REG, DEC rows in rules.md 3 (narrowed to enforces-site/decision-implemented); no ticket; v1 per-file disposition registries have no v2 form |
| C-102 | ticket | cli-surface l.102: KEEP (core) | BUILT | v2/crates/frob-ledger, `frob ticket ...` |
| C-103 | test | cli-surface l.103: KEEP | BUILT | `frob test` (v2/crates/frob-tests: touched-set selection, evidence) |
| C-104 | vet | cli-surface l.104: KEEP | TICKETED | ~RPQKHAV grimble vet (designed in cli.md, not implemented); cli.md l.273 vet lives in grimble |
| C-106 | release | cli-surface l.106: KEEP (reduced) | BUILT | `frob release changelog\|notes\|status\|bump\|cut\|adopt` (v2/crates/frob-release) |
| C-108 | serve | cli-surface l.108: KEEP (core) | DESIGNED | cli.md row `serve [--mcp\|--http]`, architecture.md l.375 (rmcp); frob-serve crate absent; only grimble serve has a ticket (~VXAYFQJ G19) |
| C-112 | fleet | cli-surface l.112: KEEP (multi-repo; defer) | DESIGNED | cli.md row `fleet status\|route` (M2, frob-fleet); migration.md l.21 fleet.toml unchanged; no ticket |
| C-113 | doctor | cli-surface l.113: KEEP | BUILT | `frob doctor` (v2/crates/frob/src/doctor.rs; --languages, --fix) |
| C-114 | clean | cli-surface l.114: KEEP | DESIGNED | boundaries.md 2.6: `frob clean` in gob-cache, M2; only GC pass (~BZXZK29) built; no ticket |
| C-115 | fmt, format | cli-surface l.115: MERGE-INTO check --fix | BUILT | `check --fix` tier A (v2/crates/gob-check/src/fix.rs, ticket ~NGE3P2T done); directive canonicalizer = cli.md `fix` row (M1, not in binary) |
| C-118 | coverage | cli-surface l.118: MERGE-INTO test | DESIGNED | cli.md row `coverage` (M2, frob-tests); no ticket |
| C-119 | status | cli-surface l.119: KEEP | DESIGNED | cli.md row `status` (M2, frob-check) and exceptions.md l.95; no ticket |
| C-120 | verify | cli-surface l.120: KEEP | DROPPED-ON-PURPOSE | boundaries.md 2.6: `verify dispose`, flake quarantine dropped with deferred verification; rules.md 6; D8, D25 |
| C-122 | run, build | cli-surface l.122: MERGE-INTO check (command runner) | MISSING | searched `frob run`, `[commands]`, `task runner`, `make wrapper` in design/tickets/code: nothing. v2 has `[[check.tool]]` stages and `cargo dev` for this repo only; consumer repos get no named-command runner |
| C-134 | frob explore | cli-surface l.134: KEEP as namespace | DESIGNED | cli.md `explore` namespace row; no ticket |
| C-135 | frob explore outline FILE | cli-surface l.135: KEEP (tree-sitter multi-lang) | DESIGNED | cli.md `explore outline`; no ticket |
| C-136 | frob explore map [PATH] | cli-surface l.136: KEEP | DESIGNED | cli.md `explore map`; no ticket |
| C-137 | frob explore xref SYMBOL [PATH] | cli-surface l.137: KEEP | DESIGNED | cli.md `explore xref`; no ticket |
| C-138 | frob explore docs-search PATH QUERY | cli-surface l.138: KEEP (ripgrep-class) | DESIGNED | cli.md `explore docs`; no ticket |
| C-139 | frob explore gitlog [PATH] | cli-surface l.139: KEEP (feeds status/flow) | MISSING | see l.96 gitlog |
| C-140 | frob explore stats | cli-surface l.140: MERGE-INTO status | DESIGNED | cli.md `status`/`stats` rows (M2); `cycle velocity` built covers the points half |
| C-141 | frob explore graph-query REF | cli-surface l.141: MERGE-INTO graph | DESIGNED | cli.md `graph query` (M2, frob-explore); no ticket |
| C-142 | frob explore graph-why REF | cli-surface l.142: MERGE-INTO graph | BUILT | `frob graph why` (v2/crates/frob-ack) |
| C-143 | frob explore graph-affects REF | cli-surface l.143: MERGE-INTO graph | BUILT | `frob graph affects` (v2/crates/frob-ack) |
| C-144 | frob explore debt | cli-surface l.144: KEEP (debt ledger) | DESIGNED | `exceptions list` / DEBT folded into EXC `defer` (exceptions.md 6); no ticket for frob side |
| C-145 | frob explore deprecated | cli-surface l.145: KEEP | DESIGNED | DEPR sunset in rules.md 3 carried row; no ticket |
| C-168 | --type {python,cpp,rust,typescript} | cli-surface l.168: KEEP (language detect) | BUILT | language by file extension through gob-languages adapters; `doctor --languages` for fidelity |
| C-169 | --only STAGE (repeat) | cli-surface l.169: KEEP | BUILT | `frob check --only <FAMILY>` (family or id, not stage groups) |
| C-170 | --skip STAGE (repeat, comma-split) | cli-surface l.170: KEEP (drop the 20 legacy flags) | MISSING | no `--skip` in `frob check --help`, rules.md 4 signature, or any ticket; `[rules.<id>]` override is the only disable. Low value now that a scoped run is under 1 s |
| C-172 | --list-stages | cli-surface l.172: KEEP | TICKETED | ~QMW7215 rule test, rule check, rule catalog and rule fmt verbs (catalog replaces stage listing) |
| C-173 | --ticket ID | cli-surface l.173: KEEP (core loop) | BUILT | `frob check --ticket` (~NGE3P2T, ~V92VDGB) |
| C-174 | --base REF | cli-surface l.174: KEEP | BUILT | `frob check --base` |
| C-175 | --files PATH (repeat) | cli-surface l.175: KEEP | DESIGNED | rules.md 4 signature `--files F..`; not in `frob check --help`; no ticket |
| C-176---fix | --fix / --fix-all [--fix] | cli-surface l.176: KEEP (auto-fix engine) | BUILT | `check --fix` built; `--fix-all` not built (rules.md 4 says unscoped --fix needs --fix-all); scoped fix = ~R5QDX7H todo |
| C-177 | --fix-ruff | cli-surface l.177: MERGE-INTO --fix (per-language formatter) | MISSING | no per-language formatter write pass in design or code; clippy/rustfmt are `[[check.tool]]` stages without fix routing |
| C-178 | --stamp-baseline / --delta | cli-surface l.178: KEEP (ratchet) | DESIGNED | rules.md 6: `--delta` over per-checkout `.frob/baseline`; not built; the land ratchet (~QAFRXM3) is built; no ticket for `--delta` |
| C-179 | --stamp-coverage | cli-surface l.179: MERGE-INTO test | DESIGNED | cli.md `coverage` row (M2) |
| C-180 | --land-parity | cli-surface l.180: KEEP (land parity) | BUILT | `land` runs the same unscoped check at head and base (rules.md 6, ~QAFRXM3); parity holds by construction |
| C-181 | --census | cli-surface l.181: KEEP (rule telemetry) | DESIGNED | rules.md 4 step 6 `census` and sibling-contract.md; no ticket, not in code |
| C-182 | --budget SECONDS | cli-surface l.182: KEEP (agents have timeouts) | DROPPED-ON-PURPOSE | rules.md 4: `--budget` self-chunking removed; reconsidered only if a real repo exceeds 30 s cold. REVERSAL WATCH: ~AKMV3C3 (cold check 29 s on this repo) |
| C-183 | --no-cache | cli-surface l.183: KEEP | MISSING | no `--no-cache` flag (grep `no-cache` in crates/design: none). Cache keys are content and engine digests (D85, ~1EZ3QHP) so need is lower, but no escape hatch exists |
| C-184 | --json, -v | cli-surface l.184: KEEP | BUILT | `--json`, `-v` global flags (gob-cli) |
| C-196 | frob test [PATH] | cli-surface l.196: KEEP (touched-set selection is core) | BUILT | `frob test` (frob-tests select.rs, touched.rs) |
| C-197 | frob coverage [PATH] | cli-surface l.197: MERGE-INTO test | DESIGNED | cli.md `coverage` (M2) |
| C-198 | frob dup [PATH] | cli-surface l.198: MERGE-INTO check | DESIGNED | see l.82: DUP in grimble-arch, no ticket |
| C-199 | frob arch [PATH] | cli-surface l.199: MERGE-INTO check | DESIGNED | see l.82: ARCH in grimble-arch, no ticket |
| C-200 | frob cycle [PATH] | cli-surface l.200: MERGE-INTO check | TICKETED | ~1QBHP7T G10 |
| C-201 | frob bind [PATH] | cli-surface l.201: MERGE-INTO check | DESIGNED | see l.89: BIND family, no ticket |
| C-209-pool | frob pool snapshot RULE [pool snapshot] | cli-surface l.209: KEEP (ratchet pool) | DESIGNED | exceptions.md `baseline` kind; `pool` removed (cli.md l.272); no ticket for baseline pools |
| C-210-pool | frob pool clear RULE [pool clear] | cli-surface l.210: KEEP | DESIGNED | exceptions.md `exceptions prune`/baseline RETIRED; reason mandatory (exceptions.md 5); no ticket |
| C-211 | frob profile show | cli-surface l.211: KEEP | DROPPED-ON-PURPOSE | rules.md 7 (no profiles) |
| C-212 | frob profile downgrade | cli-surface l.212: KEEP | DROPPED-ON-PURPOSE | rules.md 7 (no one-way ratchet to downgrade) |
| C-213 | frob fmt [PATH] | cli-surface l.213: MERGE-INTO format | DESIGNED | cli.md `fix` row (M1) listed but absent from binary; documentation drift |
| C-214 | frob format [PATH] | cli-surface l.214: MERGE-INTO check --fix | BUILT | `check --fix` (tier A); ruff-format half is a non-goal for Rust |
| C-215 | frob status | cli-surface l.215: KEEP | DESIGNED | cli.md `status` (M2) |
| C-216 | frob verify status | cli-surface l.216: KEEP (also `status`-adjacent) | DROPPED-ON-PURPOSE | rules.md 6: deferred verification not built; D8 |
| C-217 | frob verify now | cli-surface l.217: KEEP | DROPPED-ON-PURPOSE | same |
| C-218 | frob verify explain RULE:FILE[:LINE] | cli-surface l.218: KEEP | DROPPED-ON-PURPOSE | attribution ladder is deferred verification; `graph why` explains a finding instead (BUILT) |
| C-219 | frob verify dispose | cli-surface l.219: KEEP | DROPPED-ON-PURPOSE | boundaries.md 2.6 row `verify dispose`: dropped |
| C-220 | frob verify drain-async | cli-surface l.220: KEEP internal (not user verb) | DROPPED-ON-PURPOSE | D8, D25; internal verb of deferred verification |
| C-232 | frob graph build [PATH] | cli-surface l.232: KEEP (core) | DESIGNED | no `graph build` verb: rules.md 4 step 3 builds and memoizes the snapshot inside `check`; D10 |
| C-233 | frob graph query REF | cli-surface l.233: KEEP as `graph show` | DESIGNED | cli.md `graph query` (M2) |
| C-234 | frob graph why REF | cli-surface l.234: KEEP | BUILT | `frob graph why` |
| C-235 | frob graph affects REF | cli-surface l.235: KEEP | BUILT | `frob graph affects` |
| C-236 | frob ack REF... | cli-surface l.236: KEEP (core) | BUILT | `frob ack` (mandatory reason, ~V4E149M) |
| C-237 | frob docs PATH [SYMBOL] | cli-surface l.237: MERGE-INTO explore (sync flags -> check) | DESIGNED | cli.md `explore docs`; doc sync flags -> SYNC family (doc-consistency.md, D84, ~2NAP90Y docs done, no implementation ticket) |
| C-239 | frob registry audit | cli-surface l.239: MERGE-INTO check (exhaustiveness lock) | DESIGNED | REG/DEC rows rules.md 3; documentation.md DEC004; no ticket |
| C-240 | frob registry add | cli-surface l.240: KEEP (as exhaustive-research emit) or DROP; defe | MISSING | no v2 form for registry add (exhaustive-research emit); v1 note itself says defer |
| C-263-release | frob release stamp [release stamp] | cli-surface l.263: KEEP (REL001 semver-from-API; reduced to Rust pu | DESIGNED | cli.md `release ... stamp` row (M2); boundaries.md l.88 semver from public-API graph; built release verbs use lockstep version (REL001/REL002/REL003), no API-diff stamp; no ticket |
| C-264 | frob release check | cli-surface l.264: KEEP | DESIGNED | REL001 built is release-without-cut, not API-vs-version; API-vs-version check unbuilt, unticketed |
| C-265 | frob release sync | cli-surface l.265: KEEP (Cargo.toml instead) | BUILT | `frob release bump` (lockstep Cargo/wheel version; ~WSY4VA5) |
| C-266 | frob release publish [PATH] | cli-surface l.266: MERGE-INTO release (optional) | BUILT | `frob release cut` + cargo dev publish + release workflow (~BZ9EG10, ~6N2KET1, ~DR38G0G) |
| C-267 | frob release status [PATH] | cli-surface l.267: KEEP | BUILT | `frob release status` (~2YECX6Q) |
| C-268 | frob doctor | cli-surface l.268: KEEP (install/derived-state health) | BUILT | `frob doctor` |
| C-270 | frob clean [PATH] | cli-surface l.270: KEEP | DESIGNED | see l.114 |
| C-271-list | frob scaffold list [list] | cli-surface l.271: KEEP (minimal) | DROPPED-ON-PURPOSE | boundaries.md 2.6 scaffold templates dropped |
| C-272-new | frob scaffold new TYPE NAME [new] | cli-surface l.272: KEEP | DROPPED-ON-PURPOSE | same |
| C-273 | frob scaffold apply | cli-surface l.273: KEEP (frob init) | BUILT | `frob init` (~7R0EMJ4, ~VA936C5) |
| C-275-pool | frob scaffold pool warm N [pool warm] | cli-surface l.275: MERGE-INTO ticket work (worktree pool) | MISSING | worktree pool not designed; v1 ops note DROPs it (Rust shared target); cli-surface said MERGE. Needs an explicit drop record |
| C-276-pool | frob scaffold pool lease [pool lease] | cli-surface l.276: MERGE-INTO ticket work | MISSING | same |
| C-277-pool | frob scaffold pool status [pool status] | cli-surface l.277: MERGE-INTO ticket work | MISSING | same |
| C-279-fleet | frob fleet status [fleet status] | cli-surface l.279: KEEP (defer) | DESIGNED | see l.112 |
| C-280-fleet | frob fleet route [fleet route] | cli-surface l.280: KEEP (defer) | DESIGNED | see l.112; tickets.md l.250 cross-repo links via fleet manifest M2 |
| C-285 | frob run NAME | cli-surface l.285: MERGE-INTO check (task runner) | MISSING | see l.122 `frob run` |
| C-286 | frob build | cli-surface l.286: MERGE-INTO check (task runner) | MISSING | see l.122 `frob build` |
| C-295 | frob agent [env] [PATH] | cli-surface l.295: MERGE-INTO ticket work | DESIGNED | see l.90 |
| C-296 | frob agent brief TICKET | cli-surface l.296: MERGE-INTO ticket brief (duplicate) | BUILT | `ticket brief` |
| C-297 | frob worktree sweep [PATH] | cli-surface l.297: KEEP | BUILT | automatic GC (~BZXZK29); explicit verb is cli.md M2 row |
| C-298 | frob worktree remove PATH | cli-surface l.298: KEEP | BUILT | same (jail + liveness in gc/worktrees.rs) |
| C-299 | frob worktree release-lease ID | cli-surface l.299: MERGE-INTO ticket (admin) | DESIGNED | tickets.md l.317-320: stale lease taken with `--steal` and a reason (BUILT in `start`/`work`); leases release on terminal transition and `requeue` (BUILT); no separate release verb (a remedy test ~992AN0Q forbids naming one) |
| C-318 | ticket new | cli-surface l.318: KEEP (trim sprint/tier/origin/threat) | BUILT | `ticket new` with type/priority/class/scope/links/acceptance/idempotency-key; sprint/tier/origin/threat trimmed as recommended |
| C-319 | ticket list | cli-surface l.319: KEEP | BUILT | `ticket list` |
| C-320 | ticket show ID | cli-surface l.320: KEEP | BUILT | `ticket show` |
| C-321 | ticket doable | cli-surface l.321: KEEP (core; MCP mirror) | BUILT | `ticket doable` |
| C-322 | ticket wave | cli-surface l.322: KEEP (parallel dispatch) | DESIGNED | cli.md `ticket wave` (M2, frob-lease); tickets.md l.328; no ticket |
| C-323 | ticket contention | cli-surface l.323: KEEP | BUILT | `ticket contention` |
| C-324 | ticket board | cli-surface l.324: MERGE-INTO ticket list | BUILT | `frob board` (~4XZVMNC) |
| C-325 | ticket epic ID | cli-surface l.325: MERGE-INTO ticket show | BUILT | `ticket show` lists children (checked in binary); no done/total rollup count on show, milestone/cycle show have rollups |
| C-326 | ticket brief ID | cli-surface l.326: KEEP | BUILT | `ticket brief` built, but lacks the concurrent-lease do-not-touch list and verify commands v1 brief had (brief.rs: title, body, acceptance, scope, links, events). See finding S-5 |
| C-327 | ticket flow | cli-surface l.327: MERGE-INTO status | DESIGNED | `forecast`/`stats` rows (cli.md M2); `cycle velocity` built (~0AN408B) |
| C-334 | ticket plan ID | cli-surface l.334: MERGE-INTO ticket start | BUILT | categories todo/in-progress/done (tickets.md 3); no `planned` state |
| C-335 | ticket start ID | cli-surface l.335: KEEP | BUILT | `frob start` (idempotent per holder, --steal, D26/D47) |
| C-336 | ticket work ID | cli-surface l.336: KEEP (core agent entry) | BUILT | `frob work` (~901RTA2); `--cluster` has no v2 form (see S-9) |
| C-337 | ticket requeue ID | cli-surface l.337: KEEP | BUILT | `frob requeue` |
| C-338 | ticket sweep ID | cli-surface l.338: MERGE-INTO ticket scope | BUILT | `frob lease widen` (~KDR4ZBR) |
| C-340 | ticket close ID | cli-surface l.340: KEEP | BUILT | `ticket close` (guards: outcome, evidence, done_requires) |
| C-341 | ticket fail ID | cli-surface l.341: MERGE-INTO ticket body | DESIGNED | tickets.md l.268: `fail` is an `attempt` event plus requeue; event kind parses as Other (event.rs l.5) but no verb; cli.md l.268 lists `fail` as removed. Doc conflict |
| C-342 | ticket drop ID | cli-surface l.342: KEEP | BUILT | `ticket drop` |
| C-343 | ticket reopen ID | cli-surface l.343: KEEP | BUILT | `ticket reopen` |
| C-344 | ticket reverify ID | cli-surface l.344: KEEP (as verify) | MISSING | no re-run of close verification on a done ticket; `ticket evidence list` shows effective status only. Tied to done-report (see l.357) |
| C-345 | ticket land ID | cli-surface l.345: KEEP (core; simplify) | BUILT | `frob land` (~MGK5MMK) synchronous; see S-1..S-4 for dropped v1 land guards |
| C-346 | ticket promote DRAFT-ID | cli-surface l.346: KEEP (draft ids in worktrees) | DROPPED-ON-PURPOSE | D2: ULID ids, no drafts, no promote; cli.md l.268 |
| C-347 | ticket merge-driver %O %A %B | cli-surface l.347: KEEP (ledger merge) | BUILT | `merge-driver` (~N6A18DJ, ~JD0NPX1) |
| C-348 | ticket archive | cli-surface l.348: KEEP | DESIGNED | tickets.md l.31 and l.416: archive is a view/query; no verb; ticket-branch layout (D81) covers by-month indexes (~CDPXYZD) |
| C-349 | ticket restore ID / admin restore ID | cli-surface l.349: KEEP (one spelling) | DESIGNED | same |
| C-350 | ticket attach ID PATH | cli-surface l.350: MERGE-INTO ticket body | DESIGNED | cli.md `ticket attach` (M2); tickets.md 3 attachments/ dir; no ticket |
| C-356 | ticket evidence ID NODE-ID | cli-surface l.356: KEEP (core: evidence binding) | BUILT | `ticket evidence add\|list\|fetch` (v2/crates/frob-evidence) |
| C-357 | ticket done-report ID | cli-surface l.357: KEEP | DESIGNED | cli.md row + boundaries.md 2.6 say frob-evidence owns `ticket done-report`; absent from binary and from all tickets (grep done-report in tickets: only M1 acceptance text) |
| C-358 | ticket review ID | cli-surface l.358: KEEP (optional) | DESIGNED | cli.md `ticket review` (M2); `review` event kind parses as Other; no ticket |
| C-359 | ticket accept ID | cli-surface l.359: KEEP | BUILT | `ticket update --add-acceptance/--remove-acceptance` (~09P2DKX) |
| C-360-waive-audit | ticket waive-audit scan [waive-audit scan] | cli-surface l.360: KEEP (waiver honesty) | DESIGNED | `exceptions audit` (exceptions.md 3, M2); cli.md l.272 `waive audit` removed in favour of it; no ticket |
| C-361-waive-audit | ticket waive-audit complete [waive-audit complete] | cli-surface l.361: KEEP | DESIGNED | same |
| C-371 | ticket set ID FIELD VALUE | cli-surface l.371: KEEP | BUILT | `ticket update --set key=value` |
| C-372 | ticket priority / kind / component / tier / milestone | cli-surface l.372: MERGE-INTO ticket set | BUILT | folded into `update` (cli.md l.267) |
| C-373 | ticket label ID | cli-surface l.373: KEEP (via set) | BUILT | `update --add-label/--remove-label` |
| C-374 | ticket points ID N | cli-surface l.374: KEEP (via set) | BUILT | `update --points` |
| C-375 | ticket tokens ID | cli-surface l.375: KEEP (agent cost telemetry) | DESIGNED | boundaries.md 2.6: folded from `cost` events, producer frob-hook (M2); cost event parses as Other; no ticket |
| C-376 | ticket body ID | cli-surface l.376: KEEP | DESIGNED | `ticket body` listed in cli.md row; `ticket update` has no --body/--append flag in binary (only `new --body`); no ticket. See S-6 |
| C-377 | ticket scope ID | cli-surface l.377: KEEP (core: scope = write lease) | BUILT | `update --add-scope/--remove-scope`, `lease widen` |
| C-378 | ticket scope-ack ID | cli-surface l.378: KEEP | DESIGNED | tickets.md l.372: mega-glob refusal and one-flag ack not built (M2); no ticket |
| C-379 | ticket anchor ID | cli-surface l.379: KEEP | DROPPED-ON-PURPOSE | exceptions.md l.9: anchor tickets replaced by permanent `accept`; migration/v1-import.md drops `anchor` |
| C-380 | ticket block ID / unblock ID | cli-surface l.380: KEEP | BUILT | `ticket link blocks\|blocked-by`, `unlink` (blocked derived) |
| C-381 | ticket set-parent ID PARENT | cli-surface l.381: KEEP | BUILT | `ticket new --parent`; `update` via parent link (tickets.md 4 single parent) |
| C-382 | ticket runs-last ID on | cli-surface l.382: KEEP (milestones) | DESIGNED | boundaries.md 2.6 runs-last/MILE001-004, M2; v1-import.md drops runs_last; no ticket |
| C-389 | ticket reconcile / admin reconcile | cli-surface l.389: KEEP (one spelling) | DESIGNED | cli.md `ticket reconcile\|doctor` (M1 'yes'); only `ticket doctor` built; reconcile of stale holds is partly lease TTL + GC; no ticket |
| C-390 | ticket renumber [OLD NEW] / admin renumber | cli-surface l.390: KEEP (one spelling) | DROPPED-ON-PURPOSE | D2 no renumber |
| C-392 | ticket admin | cli-surface l.392: KEEP as namespace | DROPPED-ON-PURPOSE | tickets.md l.619: ~35 verbs, no admin namespace |
| C-408 | frob vet [PATH] | cli-surface l.408: KEEP (Cargo-focused: lockfile allow-list, adviso | TICKETED | ~RPQKHAV |
| C-414 | frob serve [PATH] | cli-surface l.414: KEEP (core agent interface) | DESIGNED | see l.108 |
| C-421 | frob_doable_tickets | cli-surface l.421: KEEP | DESIGNED | MCP surface is generated from `#[derive(Command)]` metadata (architecture.md l.375-377), so doable is a tool once serve exists; no ticket |
| C-422 | frob_stale_docs | cli-surface l.422: KEEP | DESIGNED | same; stale-docs = DRIFT findings over `check` |
| C-423 | frob_graph_query(symref) | cli-surface l.423: KEEP | DESIGNED | same; needs `graph query` |
| C-424 | frob_doc_for(symref) | cli-surface l.424: KEEP | DESIGNED | same; doc_for has no v2 verb |
| C-425 | frob_affects(symref, max_depth, max_nodes) | cli-surface l.425: KEEP | DESIGNED | same; `graph affects` exists |
| C-426 | frob_check_scope(ticket_id) | cli-surface l.426: KEEP | DESIGNED | same; `check --ticket` exists |
| C-427 | frob_check_delta(ticket_id, base, verify) | cli-surface l.427: KEEP | DESIGNED | same; `--delta` not built |
| C-428 | frob_run_touched_tests(base) | cli-surface l.428: KEEP | DESIGNED | same; `test` exists |
| C-430 | frob_daemon_status | cli-surface l.430: KEEP if v2 has a daemon | DESIGNED | git-io.md 6 daemon option M2; no ticket |
| C-454 | frob narrative [move] FILE LINE | cli-surface l.454: MERGE-INTO check (narrative gate stays; mover is | DESIGNED | see l.94 |

### 2.3 B. gates-and-rules.md: KEEP and MERGE rule rows (one row per v1 table row; MERGE rows are judged on the merged behaviour)

Reading note: v2 designs rules by family (rules.md section 3 'Carried (from KEEP + MERGE in the notes)'), not by id. A row is DESIGNED when its family is carried but no per-rule design, ticket or code exists; that is a weaker claim than a design page. BUILT means a v2 rule or mechanism with the same intent exists, even when the v2 id differs (see S-10 for id collisions).

| Id | v1 rule id(s) | v1 evidence | Status | v2 evidence |
|---|---|---|---|---|
| G-001 | DRIFT001 | gates sec.2: KEEP: the core drift contract | BUILT | v2 DRIFT001 doc-binding-drift (crates/frob-ack); v2 DRIFT003 stale-ack, DRIFT004 reattest |
| G-002 | DRIFT002 | gates sec.2: KEEP: core drift contract | BUILT | v2 DRIFT002 dangling-doc-target; rename candidates are SYS008 in grimble (binding.md 11.3) |
| G-003 | AFFECT001 | gates sec.2: KEEP: impact analysis is the product | BUILT | v2 AFFECT001 dependents-not-updated (frob-ack, ~AFX52KA) |
| G-004 | AFFECT002 | gates sec.2: MERGE into AFFECT001  | BUILT | covered by v2 AFFECT001 (dependents re-acked); single rule as recommended |
| G-005 | COV001 | gates sec.2: KEEP: coverage half of the model | BUILT | public-symbol documentation = v2 DOC001 undocumented-public-item; v2 COV001 now means untested-public-function (id meaning moved, see Structural S-10) |
| G-006 | COV002 | gates sec.2: KEEP: change accountability | DESIGNED | rules.md 3 COV row 'unticketed change'; no v2 rule id in code or tickets |
| G-007 | COV003 | gates sec.2: KEEP: evidence must exist | BUILT | v2 COV003 is registered as an alias of TEST001 (docs/reference/rules/COV003.md); evidence-id resolution is `ticket evidence add` validation |
| G-008 | COV004 | gates sec.2: KEEP: cheap integrity | DESIGNED | attachments are cli.md M2 (`ticket attach`); no integrity rule designed, no ticket |
| G-009 | COV005 | gates sec.2: MERGE into binding rule  | BUILT | binding of directives is gob-directives bind.rs (~18X6CDT); public-to-private rebinding by diff has no rule |
| G-010 | COV007 | gates sec.2: MERGE into COV001  | BUILT | v2 DOC001 is public-only by construction |
| G-011 | COV008 | gates sec.2: KEEP: protects evidence | MISSING | searched `evidence still cites`, `deleted test`, `orphaned evidence` in design/tickets/code: nothing. v1 T-1946 incident class is open |
| G-012 | COV010 | gates sec.2: MERGE into COV001  | DESIGNED | entrypoint-as-symbol not designed explicitly; target rule built (DOC001/COV001) |
| G-013 | PLACE001 | gates sec.2: MERGE into DSL001  | BUILT | gob-directives binding rules + PARSE001/DSL001 (~18X6CDT) |
| G-014 | PARSE001 | gates sec.2: KEEP: unmeasured is not zero | BUILT | unparseable/partial files become Unresolved/NotApplicable via FileInfo (~5NFTK3H); v2 PARSE001 is malformed-directive, a different rule |
| G-015 | PARSE002 | gates sec.2: MERGE into PARSE001  | BUILT | same mechanism (partial-parse = opaque F0 / hole) |
| G-016 | CYCLE001 | gates sec.2: KEEP: cheap in Rust via petgraph SCC | TICKETED | ~1QBHP7T G10 (grimble-arch CYCLE) |
| G-017 | TODO001 | gates sec.2: KEEP: unaccounted work | BUILT | v2 TODO001 (frob-obligations todo.rs) |
| G-018 | TODO002 | gates sec.2: KEEP: dangling deferral | BUILT | v2 TODO002 |
| G-019 | TODO003 | gates sec.2: MERGE into TODO002  | DESIGNED | version-expiry variant: EXC014 until= (exceptions.md 6), ticket ~B7VH1B4 evaluates until= for defers; `frob:todo` shipped-version form has no design |
| G-020 | DSL001 | gates sec.2: KEEP: grammar is the foundation | BUILT | v2 DSL001 unknown-directive-verb, DSL002 abbreviated id |
| G-021 | SCOPE001 | gates sec.2: KEEP: scope contract | BUILT | v2 SCOPE001 path-outside-lease (frob-check scope.rs) |
| G-022 | SCOPE002 | gates sec.2: MERGE into TICK009  | DESIGNED | TICK009 scope quality is M2 (tickets.md l.372 mega-glob); closure-gap check has no design |
| G-023 | QUEUE001 | gates sec.2: KEEP: hard failure, not soft skip | DESIGNED | rules.md 3 'queue hygiene'; `ticket doctor` (BUILT) reports fold/frontmatter failures, but no QUEUE rule id; hard-failure semantics unverified |
| G-024 | INV001 | gates sec.3: KEEP: invariant model core | DESIGNED | v1 INV001 = invariant has no evidence (test/policy); v2 INV001 means invariant-without-anchor (v1 INV002's job). Evidence half: rules.md 3 INV row 'without anchor/evidence'; evidence rule not built, no ticket |
| G-025 | INV002 | gates sec.3: KEEP: invariant model core | BUILT | v2 INV001 invariant-without-anchor (frob-obligations inv.rs) |
| G-026 | INV005 | gates sec.3: MERGE into INV001  | DESIGNED | reachability strength of invariant evidence: no design beyond INV row |
| G-027 | INV007 | gates sec.3: KEEP: forbidden-import is structural | BUILT | v2 INV002 forbidden-import via `[invariants] forbid_imports` (id renumbered) |
| G-028 | INV008 | gates sec.3: MERGE into INV001 | DESIGNED | `property test required` in rules.md 3 INV row; not built, no ticket |
| G-029 | INV009 | gates sec.3: MERGE into generic load-error rule | DESIGNED | generic load-error rule: no v2 id yet (see G-F3) |
| G-030 | INV011 | gates sec.3: MERGE into INV007  | MISSING | reachability variant of forbidden import (entrypoint reaches sink): no design found (searched `guard constant`, `sink`) |
| G-031 | INV051 | gates sec.3: KEEP: refinement soundness | DESIGNED | grimble refinement: `refine` is DROPPED from .grmb (grmb-spec.md l.55, binding.md B8), so this rule has no v2 target; revisit as DROP |
| G-032 | TEST001 | gates sec.3: KEEP: test obligation core | BUILT | v2 TEST001 tests-target-missing + COV001 untested-public-function (reach, frob-tests/rule.rs) |
| G-033 | TEST002 | gates sec.3: MERGE into TEST001  | DESIGNED | rules.md 3 TEST row 'floors'; count threshold not built, no ticket |
| G-034 | TEST003 | gates sec.3: KEEP: tier obligations are the model | DESIGNED | tier obligations (min_integration/e2e): no design beyond family name; no ticket |
| G-035 | TEST004 | gates sec.3: MERGE into TEST003  | DESIGNED | same |
| G-036 | TEST005 | gates sec.3: KEEP: floors are real policy | DESIGNED | coverage floors: rules.md 3 TEST row; `frob coverage` is cli.md M2; no ticket; v1 note calls floors the proven ratchet (ops 2.5) |
| G-037 | TEST006 | gates sec.3: KEEP: stale evidence is no evidence | DESIGNED | 'stamp freshness' in rules.md 3 TEST row; depends on `frob coverage` (M2); no ticket |
| G-038 | TEST007 | gates sec.3: MERGE into TEST003  | DESIGNED | pairwise integration test: no design beyond TEST family; no ticket |
| G-039 | TEST008 | gates sec.3: KEEP: zero-join is silent-zero | DESIGNED | zero-join = silent zero: needs coverage ingestion (M2); no ticket |
| G-040 | TEST009 | gates sec.3: MERGE into TEST004 | DESIGNED | design-file e2e edges: grimble territory, no design |
| G-041 | TEST010 | gates sec.3: MERGE into DSL001  | BUILT | directive attribute validation: gob-directives Directive derive (enum attrs) + PARSE001 |
| G-042 | TEST011 | gates sec.3: MERGE into TEST006 | DESIGNED | see TEST006 |
| G-043 | TEST012 | gates sec.3: MERGE into generic lock-staleness rule | DESIGNED | lock-staleness generic rule (G-F3) not built |
| G-044 | TEST015 | gates sec.3: KEEP: vacuous tests defeat the gate | MISSING | vacuous tests (no assertion evidence): no design or ticket; searched `assertion`, `vacuous` |
| G-045 | TEST016 | gates sec.3: KEEP: opt-in mutation proof, async only | MISSING | mutation evidence: no design anywhere (searched `mutation`, `mutant`, `TEST016`); cli.md l.270 removes `mutate`. v1 note marks it KEEP (opt-in, async only) |
| G-046 | TEST017 | gates sec.3: MERGE into TEST006 | DESIGNED | see TEST006 |
| G-047 | TEST018 | gates sec.3: KEEP: cheap evidence-audit trail | BUILT | evidence is append-only events with latest-per-provider/ref/criterion binding (tickets.md 9); weakening is visible, but no reason-required rule exists |
| G-048 | TEST019 | gates sec.3: MERGE into TEST006 | DESIGNED | see TEST006 |
| G-049 | BUG002 | gates sec.3: KEEP: proves defect repro; async/land only | DESIGNED | tickets.md l.240,451 state 'bug needs a repro that fails at the parent commit'; no mechanism, rule, code or ticket (grep repro/at parent in crates: none) |
| G-050 | BUG003 | gates sec.3: KEEP: positive counterpart of BUG002 | DESIGNED | same sentence only; positive control not designed |
| G-051 | FORBID001, FORBID002 | gates sec.3: KEEP: strata policy enforcement | TICKETED | user policy forbid call/import: GPOL via ~JDDEB70 G17 and GRL epic ~D05GDWP; strata `forbid` itself has no .grmb form |
| G-052 | FORBID003 | gates sec.3: MERGE into UNRESOLVED outcome | BUILT | Unresolved outcome mechanism (~6KPBWD1, ~KKR84AW) |
| G-053 | POL000 | gates sec.3: KEEP: zero-match must be loud | TICKETED | GRL001 unknown-name checks make zero-match typos loud (D80); tickets ~E8Q56WW; frob-side `[[policy]]` POL has no ticket |
| G-054 | POL* (user ids) | gates sec.3: KEEP: policy engine, tree-sitter queries | TICKETED | GRL epic ~D05GDWP, G17 ~JDDEB70, rules.md 3 POL/GPOL tiers |
| G-055 | DOC001 | gates sec.4: KEEP: doc reachability | DESIGNED | v1 DOC001 = obligated doc reachability; v2 DOC001 is a different rule. Reachability = doc-consistency.md/navigation (~XCH7F2D SUMMARY coverage check is todo). Doc-reachability rule itself undesigned |
| G-056 | DOC002 | gates sec.4: KEEP: link integrity | BUILT | v2 DOC002 broken-markdown-link (frob-obligations doc.rs) |
| G-057 | DOC003 | gates sec.4: MERGE into DOC002 | BUILT | folded into DOC002 / DRIFT002 |
| G-058 | DOC004 | gates sec.4: KEEP: doc-code drift, symbol-resolved | DESIGNED | doc-consistency.md D84 'checked facts in code spans' + SYNC family; no implementation ticket |
| G-059 | DOC005 | gates sec.4: MERGE into DOC012  | DESIGNED | same (CLI verbs and flags checked in code spans) |
| G-060 | DOC006 | gates sec.4: KEEP: unify with DOC004 as pointer resolver | DESIGNED | same (pointers in prose resolve) |
| G-061 | DOC008 | gates sec.4: MERGE into DOC002 | BUILT | DOC002 covers inline links and fragments |
| G-062 | DOC010 | gates sec.4: MERGE into DOC006 | DESIGNED | D84 checked facts (paths, verbs); no ticket |
| G-063 | DOC011 | gates sec.4: MERGE into DOC006 | DESIGNED | D84; ticket ids in docs: DSL002/REF001 cover directives only |
| G-064 | DOC012 | gates sec.4: KEEP: command-doc drift lock | DESIGNED | D84 checked facts: CLI verbs; generated CLI reference (GEN001) built for this repo only |
| G-065 | DOC013 | gates sec.4: MERGE into DOCENUM001  | DESIGNED | D84 generated summaries; no ticket |
| G-066 | DOC014 | gates sec.4: MERGE into DOCENUM001 | DESIGNED | same |
| G-067 | DOCENUM001 | gates sec.4: KEEP: enumerated-doc drift lock | DESIGNED | enumerates claim shapes designed (~BPF9F9E, ~3RFYPND done docs); no implementation ticket; `frob:enumerates` verb exists in gob-directives |
| G-068 | ENV001 | gates sec.4: MERGE into DOC006  | DESIGNED | D84 checked facts: config keys and env names documented; no ticket |
| G-069 | LANDPARITY001 | gates sec.4: MERGE into COV001/TEST001 diff mode | BUILT | land runs the full check and refuses new findings (~QAFRXM3) |
| G-070 | LANDPARITY002 | gates sec.4: MERGE into ARCH001 diff mode | BUILT | same |
| G-071 | REF001 | gates sec.4: KEEP: orphan detection, resolve via graph | DESIGNED | v1 REF001 = file with zero inbound references; v2 REF001 is dangling-ticket-ref. Orphan-file rule: rules.md REF row 'references back'; GRMB MDL019 orphan .grmb exists; no general orphan rule or ticket |
| G-072 | REF003 | gates sec.4: MERGE into REF001 | DESIGNED | same |
| G-073 | TICK001 | gates sec.5: KEEP: id uniqueness | BUILT | ULIDs make duplicate ids unrepresentable (D2); v2 TICK001 is frontmatter-differs-from-fold (ledger integrity) |
| G-074 | TICK002 | gates sec.5: KEEP: id integrity | DROPPED-ON-PURPOSE | D2: no draft ids; v1 TICK002 has no analogue (v2 TICK002 = ticket-not-on-base) |
| G-075 | TICK004 | gates sec.5: MERGE into TICK007  | DESIGNED | staleness alarms (critical 4h/high 24h): pm-enforcement.md stale/WIP; PM033 replenish built; undispatched alarm not designed explicitly; no ticket |
| G-076 | TICK005 | gates sec.5: KEEP: merge-safety, git2 cheap | BUILT | merge driver unions events and re-folds (~N6A18DJ, ~JD0NPX1): resurrection impossible by fold; v2 TICK005 is private-term, different rule |
| G-077 | TICK006 | gates sec.5: KEEP: claim must resolve | DESIGNED | phantom 'Filed:' claim needs done-report (absent) or `discovered-from` links (BUILT, links validated) |
| G-078 | TICK007 | gates sec.5: MERGE into TICK004  | DESIGNED | see TICK004 |
| G-079 | TICK009 | gates sec.5: KEEP: scope quality | DESIGNED | tickets.md l.372 mega-glob refusal M2, not built |
| G-080 | TICK010 | gates sec.5: MERGE into TICK015  | BUILT | lease TTL/stale reporting (tickets.md 3; `lease list`); gc jail |
| G-081 | TICK012 | gates sec.5: MERGE into TICK015 | BUILT | lease widen refreshes holder lease (~KDR4ZBR) |
| G-082 | TICK013 | gates sec.5: KEEP: empty scope is dangerous | BUILT | `frob work` warns on empty scope (v2/crates/frob-worktree/src/work.rs:237) instead of refusing; v1 refused at start (weaker, see S-8) |
| G-083 | TICK014 | gates sec.5: KEEP: empty-close detector | DESIGNED | empty-close detector (done feature with ledger-only diff): not designed, not built; see S-7 |
| G-084 | TICK015 | gates sec.5: KEEP: lease liveness | BUILT | lease expiry + liveness (`[lease] ttl_secs`, heartbeat) in frob-lease |
| G-085 | MILE001 | gates sec.5: KEEP: milestone deadlock | DESIGNED | boundaries.md 2.6: MILE001-004 frob-obligations M2; v2 milestone rules are PM001/PM002/PM034 (different); no ticket |
| G-086 | MILE002 | gates sec.5: MERGE into MILE001 | DESIGNED | same |
| G-087 | MILE003 | gates sec.5: KEEP: default milestone resolution | DESIGNED | same; default milestone resolution |
| G-088 | MILE004 | gates sec.5: MERGE into MILE001 | DESIGNED | same |
| G-089 | CROSSTICKET001 | gates sec.5: KEEP: isolation, land-time | DESIGNED | rules.md 3 CROSSTICKET row, boundaries.md l.142; not built; lease overlap + SCOPE001 reduce exposure; see S-2 |
| G-090 | DEBT001 | gates sec.5: MERGE into generic expiring-directive rule | BUILT | EXC001 reason checker (exceptions.md 5) |
| G-091 | DEBT002 | gates sec.5: MERGE into generic expiring-directive rule | BUILT | EXC003/EXC007 defer ticket terminal/missing (built) |
| G-092 | DEBT003 | gates sec.5: MERGE into generic expiring-directive rule | TICKETED | EXC014 `until=` expiry: ~B7VH1B4 |
| G-093 | DEPR001 | gates sec.5: MERGE into generic expiring-directive rule | DESIGNED | DEPR family carried (rules.md 3) as 'sunset'; no ticket, no `frob:deprecated` rule in code |
| G-094 | DEPR002 | gates sec.5: MERGE into generic expiring-directive rule | BUILT | EXC003/007 apply once deprecated is a defer |
| G-095 | DEPR003 | gates sec.5: MERGE into generic expiring-directive rule | DESIGNED | sunset warning window: no design detail |
| G-096 | DEPR004 | gates sec.5: MERGE into generic expiring-directive rule | TICKETED | ~B7VH1B4 until= evaluation |
| G-097 | DEPR005 | gates sec.5: KEEP: no-new-callers ratchet | DESIGNED | no-new-callers ratchet over a deprecated baseline: baseline kind M2, not built |
| G-098 | DEPR006 | gates sec.5: MERGE into generic lock-staleness rule | DESIGNED | generic lock-staleness rule not designed (G-F3) |
| G-099 | REL001 | gates sec.5: KEEP: release gate | BUILT | v2 REL001 release-without-cut + `release status` readiness (~PKJ5AVG, ~2YECX6Q); v1 version-vs-API check missing, see l.263 |
| G-100 | REL002 | gates sec.5: KEEP: version coherence, rust Cargo | BUILT | v2 REL002 lockstep-version-mismatch for Cargo.toml (~9K9K8V5) |
| G-101 | VERSION001 | gates sec.5: MERGE into REL002 | BUILT | REL002 covers crate/wheel pins |
| G-102 | BUDGET001 | gates sec.5: KEEP: budget must name what it skipped | DROPPED-ON-PURPOSE | `--budget` removed (rules.md 4), so the rule has no subject; revisit with ~AKMV3C3 |
| G-103 | BASE001 | gates sec.5: KEEP: aggregate ratchet signal | DESIGNED | baseline pools growth rule: exceptions.md 4 'pool can never gain a key'; no rule built |
| G-104 | AUTOFIX001 | gates sec.5: KEEP: crash-safe fix journal | DESIGNED | gob-fix journal listed in boundaries.md l.61; gob-check fix.rs has no abandoned-journal detection (grep journal: none); no ticket |
| G-105 | DERIVED001 | gates sec.5: KEEP: fail-closed cache integrity, any cache | TICKETED | ~TX6YZZE derived state outside the work tree with MAC and atomic writes (in progress); ~H2DAC49 |
| G-106 | CHECK001 | gates sec.5: KEEP: fail loudly not default | DESIGNED | `check` without frob.toml teaches `frob init` (~ANDZXZ4 done); undetected-language Unresolved via adapters (doctor --languages); no rule id |
| G-107 | SUBJECT001 | gates sec.5: KEEP: vacuous-pass guard | BUILT | required Unresolved for must_measure rules examining zero subjects (cli.md 2, D62, ~6KPBWD1) |
| G-108 | GATES001 | gates sec.5: MERGE into generic load-error rule | DESIGNED | generic load-error rule: no v2 id (G-F3) |
| G-109 | TOOL001, TOOL002 | gates sec.5: KEEP: tool availability is UNRESOLVED | BUILT | v2 TOOL001/TOOL002 (frob-check tools.rs, ~APQCEPT) |
| G-110 | WRAP001, WRAP002, WRAP003 | gates sec.5: KEEP: derived-artifact drift  | DESIGNED | generated-artifact drift: GEN001 `cargo dev gen --check` for this repo only (build-test-ci.md 3); consumers have no managed Makefile blocks |
| G-111 | DEPLOY001 | gates sec.5: KEEP: generated-artifact drift | DROPPED-ON-PURPOSE | cli.md l.270: deploy removed; HOST/deploy generators CUT (strata.md 10.3) |
| G-112 | DEPLOY002 | gates sec.5: KEEP: design conformance | DROPPED-ON-PURPOSE | same |
| G-113 | DEPLOY003 | gates sec.5: MERGE into DEPLOY002 | DROPPED-ON-PURPOSE | same |
| G-114 | WIRE001 | gates sec.5: KEEP: invoked-by-nothing guard  | DESIGNED | DEAD family (G10 ~1QBHP7T) covers private symbols with zero references; new-public-function-with-no-caller (invoked-by-nothing) has no rule |
| G-115 | WIRE002 | gates sec.5: MERGE into WIRE001 | DESIGNED | exceptions.md l.9: anchors replaced by `accept`/`defer`; follow_up requirement is EXC003/007 |
| G-116 | DEAD001 | gates sec.5: KEEP: reachability on graph, rust fast | TICKETED | ~1QBHP7T G10 (DEAD) |
| G-117 | OPAQUE001 | gates sec.5: KEEP: unresolved-capability honesty | DESIGNED | D57 annotate-or-be-opaque; required Unresolved case (b) in cli.md 2; U opaque nodes built in gob-ir (~PXY6QQV); rule over eval/getattr not built |
| G-118 | WAIVE001 | gates sec.6: KEEP: waiver needs reason | BUILT | v2 EXC001 (reason checker) |
| G-119 | WAIVE002 | gates sec.6: KEEP: dead waiver | DESIGNED | EXC002 designed M2; no ticket |
| G-120 | WAIVE004 | gates sec.6: KEEP: only on full runs, cached | DESIGNED | EXC013 stale-exception designed M2; no ticket |
| G-121 | WAIVE005 | gates sec.6: MERGE into generic expiring-directive rule | TICKETED | EXC014 until= : ~B7VH1B4 |
| G-122 | WAIVE006 | gates sec.6: KEEP: waiver may not outlive ticket | BUILT | v2 EXC003 defer-ticket-terminal |
| G-123 | WAIVE007 | gates sec.6: MERGE into WAIVE006 | BUILT | v2 EXC007 defer-ticket-missing |
| G-124 | WAIVE011 | gates sec.6: MERGE into generic lock-staleness rule | DESIGNED | generic lock-staleness (G-F3) |
| G-125 | WAIVE012 | gates sec.6: KEEP: waiver expiry by predicate | TICKETED | EXC014 metric/date/premise predicates: ~B7VH1B4 |
| G-126 | RELWAIVE002 | gates sec.6: MERGE into SYSWAIVE  | DESIGNED | grimble exceptions: four kinds on .grmb (D28, D71); `grimble exceptions list` built (~EHPFVKD); reliability waiver rule has no v2 form |
| G-127 | SYSWAIVE002 | gates sec.6: MERGE into WAIVE004 | DESIGNED | EXC013 over grimble: not built |
| G-128 | SYSWAIVE003 | gates sec.6: MERGE into WAIVE005 | TICKETED | ~B7VH1B4 / EXC014 |
| G-129 | REG001 | gates sec.7: KEEP: exhaustiveness registries | DESIGNED | REG family carried (rules.md 3) as 'enforces-site present'; v1 disposition registries (docs/design/registry/*.yaml) have no v2 counterpart; no ticket |
| G-130 | REG002 | gates sec.7: KEEP: dangling enforcement ref | DESIGNED | same |
| G-131 | REG003 | gates sec.7: KEEP: real deferral | DESIGNED | same; deferral to open ticket = EXC defer |
| G-132 | REG004 | gates sec.7: MERGE into REG002 | DESIGNED | same |
| G-133 | REG005 | gates sec.7: MERGE into REG006 | DESIGNED | same |
| G-134 | REG006 | gates sec.7: KEEP: generic registry load error | DESIGNED | same |
| G-135 | REG007 | gates sec.7: KEEP: id collision | DESIGNED | same |
| G-136 | REG008 | gates sec.7: KEEP: claimed-but-unwired | DESIGNED | same ('enforces-site present') |
| G-137 | REG009 | gates sec.7: MERGE into REG002 | DESIGNED | same |
| G-138 | REG010 | gates sec.7: MERGE into REG008  | BUILT | rule registry is the inventory (D3, ~69X5BSZ); reverse drift impossible by construction |
| G-139 | REG012 | gates sec.7: MERGE into generic adopted-then-deleted rule | DESIGNED | generic adopted-then-deleted rule: no design |
| G-140 | DEC000 | gates sec.7: MERGE into generic load-error rule | DESIGNED | generic load-error: no v2 id |
| G-141 | DEC001 | gates sec.7: KEEP: anchor resolution | DESIGNED | documentation.md DEC rules (DEC004 named); ADR bound to invariants; no ticket |
| G-142 | DEC002 | gates sec.7: KEEP: decision traceability | DESIGNED | same |
| G-143 | DEC003 | gates sec.7: MERGE into generic adopted-then-deleted rule | DESIGNED | generic adopted-then-deleted: no design |
| G-144 | COMPLIANCE001 | gates sec.7: KEEP: deny-by-default completeness  | DESIGNED | v1 strata.md 10.2 calls compliance 'thin data, no consumers' and CUTs it; v2 packs.md has no compliance pack; treat as DROP candidate |
| G-145 | COMPLIANCE002 | gates sec.7: KEEP: design pack | DESIGNED | same |
| G-146 | COMPLIANCE003 | gates sec.7: KEEP: design pack | DESIGNED | same |
| G-147 | COMPLIANCE004 | gates sec.7: MERGE into REG002 | DESIGNED | same |
| G-148 | COMPLIANCE005 | gates sec.7: MERGE into REG001 | DESIGNED | same |
| G-149 | COMPLIANCE006 | gates sec.7: MERGE into generic adopted-then-deleted rule | DESIGNED | same |
| G-150 | THREAT001 | gates sec.7: KEEP: catalog completeness  | DESIGNED | threat catalogs as pack data: packs.md tier-1 content (~HC9450N todo); grimble-model.md l.337 cwe in detectors; claim ids `weakness:CWE-78:vet` carried (grmb-spec l.187) |
| G-151 | THREAT002 | gates sec.7: KEEP: design pack | DESIGNED | same; benign/excuse templates = matrix-build templates (D75) |
| G-152 | THREAT003 | gates sec.7: KEEP: design pack | DESIGNED | same |
| G-153 | THREAT004 | gates sec.7: KEEP: code-vs-design conformance | TICKETED | CAP001 observed-use-without-grant (D75) + ~V56RXG4 G14 grimble-capabilities |
| G-154 | THREAT005 | gates sec.7: MERGE into THREAT002 | DESIGNED | same as THREAT002 |
| G-155 | THREAT006 | gates sec.7: MERGE into REG002 | DESIGNED | same |
| G-156 | SEC-CVE-FINGERPRINT-001 | gates sec.7: KEEP: cheap Aho-Corasick scan | MISSING | searched `fingerprint`, `needle`, `Aho` in design: no CVE vulnerable-usage scan; SEC family only named (boundaries l.145 grimble-security) |
| G-157 | ARCH001 | gates sec.8: KEEP: native tree-sitter, cheap in Rust | DESIGNED | rules.md 3 'small metric core (size, nesting, LCOM, coupling, layering)' in grimble-arch; G10 ticket omits ARCH |
| G-158 | ARCH101 | gates sec.8: MERGE into ARCH102  | DESIGNED | same (LCOM) |
| G-159 | ARCH104 | gates sec.8: KEEP: layering is declared policy | DESIGNED | layering as declared flows (grimble SYS013, unticketed) or `[invariants] forbid_imports` (built) |
| G-160 | LARGE001 | gates sec.8: KEEP: one config-driven size cap | TICKETED | ~1QBHP7T G10 (LARGE) |
| G-161 | LANG004 | gates sec.8: MERGE into build-time adapter tests | BUILT | adapter conformance corpora in gob-languages/gob-symbols tests (build-test-ci.md 2 'language conformance'); `doctor --languages` |
| G-162 | PERF009 | gates sec.8: KEEP: bench ratchet, via criterion | DESIGNED | benches exist (criterion in gob-walk, gob-ir, gob-symbols; ~B6VY10G) but no committed baseline ratchet rule; v2 PERF001 is check-over-budget, a different rule |
| G-163 | DUP001, DUP002 | gates sec.8: KEEP: clone detection is a product feature; native | DESIGNED | DUP in grimble-arch (rules.md 3, R1-R5 rungs); no ticket |
| G-164 | DUP003 | gates sec.8: MERGE into generic UNRESOLVED-substrate outcome | BUILT | Unresolved outcome mechanism |
| G-165 | PROTO001 | gates sec.8: KEEP: typestate protocol, unresolved-aware | DROPPED-ON-PURPOSE | rules.md l.175-176: typestate PROTO dropped from core unless a consumer commits (reverses v1 KEEP) |
| G-166 | PROTO002, PROTO003 | gates sec.8: KEEP: typestate protocol | DROPPED-ON-PURPOSE | same |
| G-167 | PROTO004 | gates sec.8: KEEP: typestate protocol | DROPPED-ON-PURPOSE | same |
| G-168 | PROTO005 | gates sec.8: MERGE into PROTO002 | DROPPED-ON-PURPOSE | same |
| G-169 | SYS001 | gates sec.9: KEEP: code-to-design binding | BUILT | v2 SYS001 SYS-UNOWNED / SYS004 empty-selector (grimble-bind, ~EG1XSWC); v1 SYS001 (dangling directive) = SYS003 dangling-operand |
| G-170 | SYS002 | gates sec.9: KEEP: design-to-code binding | BUILT | v2 SYS009 flow-end-unbound / directive checks (~EG1XSWC) |
| G-171 | SYS003 | gates sec.9: KEEP: conformance, graph-based | DESIGNED | v1 SYS003 undeclared-import conformance (reflexion model) = v2 SYS013, reserved by binding.md 11.3 and given to G12, but G12 shipped SYS006-008 only; SYS013 has no ticket and no code. See S-11 |
| G-172 | SYS004 | gates sec.9: MERGE into generic load-error rule | BUILT | MDL family well-formedness (~63XJMC3 G08) |
| G-173 | SYS100 | gates sec.9: MERGE into SYS110 | BUILT | v2 CAP001 observed use without grant (D75; capabilities deny by default); crate grimble-capabilities (~V56RXG4 G14 todo) |
| G-174 | SYS101 | gates sec.9: KEEP: declared-but-unexercised grant | TICKETED | ~71BAAE0 G15 grimble shrink |
| G-175 | SYS102 | gates sec.9: KEEP: coverage totality | BUILT | v2 SYS001 SYS-UNOWNED / FOREIGN (~EG1XSWC) |
| G-176 | SYS103 | gates sec.9: MERGE into SYS102 | BUILT | same |
| G-177 | SYS106 | gates sec.9: KEEP: laundering detection | DESIGNED | laundering through unbound files: SYS001/SYS005 partial; no explicit design |
| G-178 | SYS109 | gates sec.9: MERGE into SYS113 | BUILT | SYS004 empty selector |
| G-179 | SYS110 | gates sec.9: KEEP: surface-leak detection | DESIGNED | surface leak = v2 SYS014, reserved (binding.md 11.3), unticketed, no code |
| G-180 | SYS111 | gates sec.9: KEEP: capability ratchet | TICKETED | capability ratchet: grimble.lock (~T9R1B70 done) + ~V56RXG4 G14; ratchet-with-reason for may growth not confirmed built |
| G-181 | SYS112 | gates sec.9: KEEP: grants need reason | TICKETED | grants need `because`: grmb-spec may clause; ~V56RXG4 |
| G-182 | SYS113 | gates sec.9: KEEP: zero-match must be loud | BUILT | SYS004 empty-selector, zero-match loud |
| G-183 | SYS114 | gates sec.9: KEEP: SSRF surface | DESIGNED | outbound flow unconstrained destination (SSRF): no v2 design found (searched `SSRF`, `unconstrained`) |
| G-184 | SYS115 | gates sec.9: MERGE into SYS114 | DESIGNED | same |
| G-185 | SYS116 | gates sec.9: MERGE into PII-family obligations | DESIGNED | provenance/PII family: no v2 design (PII rules not designed) |
| G-186 | SYS117 | gates sec.9: MERGE into PII-family obligations | DESIGNED | same |
| G-187 | SYS200 | gates sec.9: KEEP: resource contention | DESIGNED | resource contention (listens/path ownership): not in grmb-spec (host/resource constructs dropped, grmb-spec l.55) |
| G-188 | SYS201 | gates sec.9: KEEP: resource contention | DESIGNED | same |
| G-189 | SYS202 | gates sec.9: MERGE into SYS201  | DESIGNED | same |
| G-190 | SYS203 | gates sec.9: MERGE into SYS201 | DESIGNED | same |
| G-191 | SYS204 | gates sec.9: MERGE into SYS201 | DESIGNED | same |
| G-192 | SYS205 | gates sec.9: KEEP: mode conformance | DESIGNED | same |
| G-193 | HOST001 | gates sec.9: KEEP: host isolation proof | DROPPED-ON-PURPOSE | host/krb/deploy CUT (strata.md 10.3); grmb-spec l.55 non-goals |
| G-194 | HOST002 | gates sec.9: MERGE into HOST001 | DROPPED-ON-PURPOSE | same |
| G-195 | HOST-BLAST | gates sec.9: KEEP: scenario proof | DROPPED-ON-PURPOSE | same |
| G-196 | CAP001 | gates sec.9: KEEP: capacity proof | TICKETED | v1 CAP001 = capacity proof over flow rates; v2 CAP001 means capability exceeded (id collision, S-10). Capacity belongs to `bound` claims: ~QNDWNDM G16 kernel port (CLAIM family) |
| G-197 | LINT001 | gates sec.9: MERGE into SYS114/115  | TICKETED | ~QNDWNDM G16 (rate obligations as claims) |
| G-198 | LINT002 | gates sec.9: MERGE into CAP001 | TICKETED | same |
| G-199 | LINT003 | gates sec.9: KEEP: scenario sanity | DESIGNED | ScaleRate scenarios dropped from .grmb (grmb-spec l.55) |
| G-200 | LINT004 | gates sec.9: KEEP: kill-switch obligation | DESIGNED | kill-switch obligation: no v2 design |
| G-201 | LINT005 | gates sec.9: MERGE into CAP001 | TICKETED | ~QNDWNDM G16 |
| G-202 | PII001 | gates sec.9: KEEP: vocabulary check | DESIGNED | no PII rule design in v2 (grimble-security SEC PII named in boundaries.md l.145; `carries` dropped, grmb-spec l.1457) |
| G-203 | PII002 | gates sec.9: KEEP: PII flow obligation | DESIGNED | same |
| G-204 | PII003 | gates sec.9: KEEP: retention obligation | DESIGNED | same |
| G-205 | PII004 | gates sec.9: MERGE into PII002 | DESIGNED | same |
| G-206 | PII005 | gates sec.9: MERGE into PII001 | DESIGNED | same |
| G-207 | REL200, REL201 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-208 | REL210, REL211 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-209 | REL220, REL221, REL222 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-210 | REL230, REL231 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-211 | REL240, REL241 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-212 | REL250 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-213 | REL260, REL261 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-214 | REL270, REL271, REL272 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-215 | REL280, REL281 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-216 | REL290, REL291 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-217 | REL300, REL301 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-218 | REL303 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-219 | REL310, REL311 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-220 | REL320, REL321 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-221 | REL330, REL331 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-222 | REL340 | gates sec.9: KEEP: graph depth bound | DESIGNED | sync hop depth bound: kernel/claim `bound` (G16 ~QNDWNDM) could host it; not designed as a rule |
| G-223 | REL350, REL351 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-224 | REL360 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-225 | REL370, REL371, REL372 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-226 | REL380, REL381 | gates sec.9: MERGE into CAP001 | TICKETED | ~QNDWNDM G16 (capacity bound claims) |
| G-227 | REL383 | gates sec.9: MERGE into REL200 | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-228 | REL390, REL391 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-229 | REL392, REL393 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-230 | REL394, REL395 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-231 | REL396, REL397 | gates sec.9: MERGE into parametric declared+proven obligation | DESIGNED | reliability families: binding.md B7 'MOVED' to a reliability pack (G04 docs done, pack content ~HC9450N todo); parametric declared-plus-proven obligation is the recommended shape, no rule designed yet |
| G-232 | VMOD001 | gates sec.9: KEEP: V-model closure over typed graph | TICKETED | ~QNDWNDM G16 kernel port: CLAIM and VMOD families; SYS011 vmodel-link-broken already built (~EG1XSWC) |
| G-233 | MSCLOSE001 | gates sec.9: MERGE into VMOD001  | TICKETED | same |
| G-234 | SEC001 | gates sec.10: KEEP: lexical-legit; Aho-Corasick + entropy | DESIGNED | SEC family only named (boundaries.md l.145 grimble-security); no design detail beyond cli.md exceptions example; no ticket |
| G-235 | SEC002 | gates sec.10: KEEP: trivial, high value | DESIGNED | same |
| G-236 | SEC003 | gates sec.10: KEEP: unwaivable secrets | DESIGNED | same; unwaivable flag exists in the Rule derive (waivable=false) |
| G-237 | SEC004 | gates sec.10: MERGE into WAIVE001  | BUILT | EXC001 reason requirement covers `secret-fake` markers once they exist |
| G-238 | PII010 | gates sec.10: KEEP: structural PII; cheap in Rust | DESIGNED | no PII rule design |
| G-239 | PII011 | gates sec.10: MERGE into SEC001 | DESIGNED | same |
| G-240 | PII013 | gates sec.10: MERGE into PII002 | DESIGNED | same |
| G-241 | VET001 | gates sec.10: KEEP: supply-chain allowlist | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-242 | VET002 | gates sec.10: KEEP: capability scan of deps | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-243 | VET003 | gates sec.10: KEEP: capability escalation | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-244 | VET004 | gates sec.10: KEEP: supply-chain risk | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-245 | VET005 | gates sec.10: KEEP: delegate to osv-scanner, offline cache | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-246 | VET006 | gates sec.10: MERGE into SEC-CVE-FINGERPRINT-001 | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-247 | VET007 | gates sec.10: KEEP: pinning policy | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-248 | VET009 | gates sec.10: KEEP: cheap CI hygiene | BUILT | CI001 pinned-ref (v2, built, ~XX6K71R: zizmor binding) covers mutable GitHub Action refs |
| G-249 | VET010 | gates sec.10: KEEP: cheap | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-250 | VET011 | gates sec.10: KEEP: needs registry data, opt-in | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-251 | VET012 | gates sec.10: MERGE into generic UNRESOLVED-substrate outcome | BUILT | Unresolved outcome mechanism; advisory-unavailable -> Unresolved in grimble-vet design |
| G-252 | VET-JS | gates sec.10: KEEP: install-time exec  | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-253 | VET-JS003 | gates sec.10: KEEP: cheap | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-254 | VET-JS004 | gates sec.10: KEEP: cheap | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-255 | VET-PY001 | gates sec.10: KEEP: ecosystem pack | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-256 | VET-PY002 | gates sec.10: KEEP: ecosystem pack | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-257 | VET-PY003 | gates sec.10: KEEP: ecosystem pack | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-258 | VET-RS001 | gates sec.10: KEEP: ecosystem pack | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-259 | VET-RS002 | gates sec.10: KEEP: ecosystem pack | TICKETED | ~RPQKHAV grimble vet (designed in cli.md and boundaries.md grimble-vet; M2); per-rule scope of the ticket not stated |
| G-260 | VET-SOURCE-UNAVAILABLE | gates sec.10: MERGE into generic UNRESOLVED-substrate outcome | BUILT | same |
| G-261 | VET-TIMEOUT | gates sec.10: MERGE into generic UNRESOLVED-substrate outcome | BUILT | same (budget Unresolved) |

### 2.4 C. gates-and-rules.md: design guidance, profile, waiver, ratchet and slowness lessons

| Id | Statement | v1 evidence | Status | v2 evidence |
|---|---|---|---|---|
| GX-01 | Core set rebuilt as typed Rust rules over one shared graph snapshot | gates 18 guidance | BUILT | gob-rules, frob-obligations, gob-check pipeline (rules.md 4) |
| GX-02 | 'Declared plus proven' one parametric obligation instead of ~51 REL ids | gates 9, 18 | DESIGNED | binding.md B7 + packs.md reliability pack (G04 docs); no rule/pack content yet (~HC9450N) |
| GX-03 | One generic rule each for adopted-then-deleted, load-error, lock-staleness, expiring-directive, UNRESOLVED substrate | gates 18 | DESIGNED | UNRESOLVED substrate B (TOOL001/SIB001/vacuous); expiring-directive = EXC014 (~B7VH1B4); load-error, adopted-then-deleted and lock-staleness generic rules have no design |
| GX-04 | Keep severity enum (error/warn/unresolved/advisory); default severity in rule metadata, not a 580-line override table | gates 18 | BUILT | gob-rules Severity; `[rules.<id>]` override only where differing (migration.md l.17) |
| GX-05 | Principle: unmeasured is not zero (SUBJECT001, PARSE, zero-match POL000/SYS113) | gates 18 | BUILT | D62 required Unresolved (c), subjects_examined (~KKR84AW) |
| GX-06 | Replace id-literal registry with Rust enum/inventory macro | gates 18 | BUILT | D3; ~69X5BSZ |
| GX-07 | Replace independent walkers with one shared pass; per-file content-hashed facts; rayon instead of thread/process split | gates 18, 17 | BUILT | rules.md 4 steps 2-5; ~A8AMNGF; cold-path regression ~AKMV3C3 (20 of 29 s in file rules) and warm graph ~36ZXTMR are open |
| GX-08 | Fix tiers A/B/C | gates 13, 18 | BUILT | tier A built (gob-check fix.rs); B (apply-verify-commit) and C (fix-it only) are rules.md 4 text; ~DW4RJVG, ~R5QDX7H, ~C63ZWCR cover applicability and scoped apply |
| GX-09 | `--files` scoping | gates 18 | DESIGNED | rules.md 4 signature only (see CLI l.175) |
| GX-10 | Ratchet pools with mandatory-reason clear | gates 16, 18 | DESIGNED | exceptions baseline kind; land ratchet built; pool verbs not |
| GX-11 | Quarantine clears only via dispositions, never on green | gates 16, 18 | DROPPED-ON-PURPOSE | rules.md 6: quarantine M2 and needs a tracked store and disposition verb if ever built |
| GX-12 | Waiver reason required, ticket-bound expiry | gates 18, 15 | BUILT | EXC001, EXC003, EXC007 built; EXC014 until= ~B7VH1B4 |
| GX-13 | Web families (249 ids) and Kerberos/host/compliance packs optional plugin packs, never core | gates 11, 18 | DROPPED-ON-PURPOSE | rules.md l.172-176 dropped from core; D76 packs/plugins |
| GX-14 | Profile: never relax ledger integrity checks and LAND-PROOF in any profile | gates 14 | BUILT | no profiles; integrity (TICK001/doctor) always on; LAND-PROOF output itself unbuilt (S-1) |
| GX-15 | Waiver unwaivable set (TEST008, SEC003, TICK001/2, EXCL001, REG012, DEC003, WIRE002) | gates 15 | BUILT | `waivable = false` in the Rule derive; EXC008 designed M2 |
| GX-16 | Waivers always reported (`excepted` section), never silently dropped | gates 15 | BUILT | rules.md 5; gob-check report |
| GX-17 | New rules ship Warn for one release; acceptance criterion forced at close for a new gate rule | gates 1 | DESIGNED | `[check] new_rule_warn_releases` design only; before-fails/after-passes acceptance guard has no v2 form |
| GX-18 | Waiver audit with persisted commit watermark (honesty review) | gates 15 | DESIGNED | `exceptions audit` (exceptions.md 3, M2); no ticket |
| GX-19 | Delta baseline per checkout, advisory | gates 16 | DESIGNED | rules.md 6 `--delta`; unbuilt |
| GX-20 | Ratchet producer-abandoned detection for baseline locks | gates 16 | DESIGNED | generic lock-staleness rule undesigned |
| GX-21 | Land-time checks: land-parity, cross-ticket leakage, empty-diff close, new-gate-rule acceptance, BUG002/TEST016 | gates 16 | DESIGNED | land check built; the listed guards are not (S-2, S-7, S-1) |
| GX-22 | Lesson: 'a check stays on the land critical path only if its failure damages someone other than the author' | tickets 6 (T-1686) | BUILT | D8: land runs the full check synchronously because it is sub-second; ratchet limits blocking to new findings |
| GX-23 | Lesson 17.1 whole-repo work per invocation (25-45 min land) | gates 17.1 | BUILT | cached per-file facts; land base check cached per base oid (~TSK0M4Y done) |
| GX-24 | Lesson 17.2 many gates each walking the tree | gates 17.2 | BUILT | one walk, one snapshot (rules.md 4) |
| GX-25 | Lesson 17.3 graph load tax per invocation (3.3 s warm) | gates 17.3 | BUILT | warm path cache; ~A8AMNGF done; ~36ZXTMR in progress (0.7 s warm) |
| GX-26 | Lesson 17.4 Python concurrency model (GIL, forkserver cold start) | gates 17.4 | BUILT | Rust, rayon |
| GX-27 | Lesson 17.5 cache granularity: whole-tree key invalidates every root-scanning gate | gates 17.5 | BUILT | per (file digest, rule id, rule version, side-input digest) (D30); repo-rule keyed by input digests incl. engine (~1EZ3QHP) |
| GX-28 | Lesson 17.6 heuristic/unbounded gates (TDD001 archaeology, effect-graph BFS, test reruns) | gates 17.6 | BUILT | dropped from core (rules.md l.172); BUT NARR/PRE/TDD/NEGEXIST reintroduced at family level (reversal list R-1) |
| GX-29 | Lesson 17.7 subprocess/toolchain fan-out | gates 17.7 | BUILT | `[[check.tool]]` stages concurrent through gob-exec pool, outside the 2 s budget (rules.md 4) |
| GX-30 | Lesson 17.8 locking: shared derived-state lock held end to end blocked a land 25 min | gates 17.8 | BUILT | no derived-state lock; SQLite WAL readers; land lock separate. Open: ~CE69AVN flaky two-process cache test |
| GX-31 | Lesson 17.9 profiling blind spot (pools invisible) | gates 17.9 | BUILT | tracing span per rule, `--timing` (architecture.md 5, ~NGE3P2T) |
| GX-32 | Lesson 17.10 severity/waiver bookkeeping cost | gates 17.10 | BUILT | metadata defaults; exceptions evaluated once |
| GX-33 | Lesson 17.11 land-path ceremony multiplies cost; deferred-verification machinery hides latency | gates 17.11 | BUILT | D8 not rebuilt |

### 2.5 D. ops-and-integrations.md: verdict rows and lessons

| Id | Item | v1 evidence | Status | v2 evidence |
|---|---|---|---|---|
| O-01 | Telemetry: one timer from process start to exit, every verb | ops 1 verdict; ops 9.6 | BUILT | architecture.md 5 designs it; gob-check/telemetry.rs writes one line per `check` run only (stage ms, files, findings): verbs other than check are not instrumented, no process-start timer, no exit code. See S-12 |
| O-02 | Ticket read under 50 ms, mutation under 100 ms (v1 show 2.7 s) | ops 1.6 | BUILT | goals.md goal 1; SQLite index (D38, ~N6A18DJ); scheduled bench ~B6VY10G; measured only by design docs, not by a CI gate on `ticket show` |
| O-03 | Touched-set selection (pure function over graph and diff) | ops 2.1 KEEP | BUILT | v2/crates/frob-tests select.rs, touched.rs, reach.rs (~WGQY08T) |
| O-04 | Runner registry: fold [[native]] and runners into one language table | ops 2.2 MERGE | DESIGNED | tickets.md 9 evidence providers trait (pytest, cargo test, ctest, vitest, junit, command); M1 ships nextest/command/file only; no per-language runner table, no ticket |
| O-05 | Collectors: one content-addressed store, not six JSON files | ops 2.3 MERGE | BUILT | frob-tests catalog.rs over gob-cache (SQLite, D38) |
| O-06 | Coverage stamp/refresh: single measure-once pipeline | ops 2.4 MERGE | DESIGNED | cli.md `coverage` (M2); no ticket; see TEST005/006 |
| O-07 | TEST005 one-way coverage floors (KEEP: proven after incidents) | ops 2.5 KEEP | DESIGNED | rules.md 3 TEST 'floors'; no design of lock file or ratchet; no ticket |
| O-08 | Flake quarantine: ticket-bound quarantine, never a silent skip list | ops 2.6 KEEP | DROPPED-ON-PURPOSE | boundaries.md 2.6 'verify dispose, flake quarantine: dropped' |
| O-09 | `frob mutate` kept as optional tool, pytest parts out | ops 2.7 MERGE | DROPPED-ON-PURPOSE | cli.md l.270 removes mutate; no mutation tool in design (see TEST016 finding) |
| O-10 | vet scan + capability diff across versions, native Rust scanners | ops 3 KEEP | TICKETED | ~RPQKHAV grimble vet; cli.md l.255; boundaries.md grimble-vet |
| O-11 | vet hook mode: pre-install check with a real hook installer | ops 3 KEEP | DESIGNED | git-io.md 5: `frob hook pre-tool` invokes `grimble vet --hook`; frob-hook crate absent, no ticket for hook or installer |
| O-12 | allowlist + age quarantine (declaration-as-waiver) | ops 3 KEEP | TICKETED | ~RPQKHAV (scope of ticket does not enumerate `[vet.allow]`) |
| O-13 | one advisory client (OSV), drop local cvelistV5 mirror | ops 3 MERGE | TICKETED | ~RPQKHAV; no design of the advisory client found |
| O-14 | secret redaction for telemetry and logs | ops 3 KEEP | BUILT | gob-log redactor (~SFBR9ZG), applied by gob-exec to captured output; architecture.md 5 |
| O-15 | MCP tools: thin typed query surface | ops 4 KEEP | DESIGNED | architecture.md l.375 rmcp, tools generated from Command metadata; frob-serve crate absent, no ticket (grimble-serve G19 ~VXAYFQJ only) |
| O-16 | socket daemon: resident process, Rust fixes startup | ops 4 KEEP | DESIGNED | git-io.md 6 daemon option (M2); build-test-ci.md l.11,78 defers; no ticket |
| O-17 | warm state + watcher: one incremental graph store, drop git-status poller | ops 4 MERGE | DESIGNED | D10 salsa (M2); ~36ZXTMR (in progress) caches the assembled graph on the warm path; ~A8AMNGF done |
| O-18 | daemon background jobs (rebase bot, post-land verify) as scheduler tasks | ops 4 MERGE | MISSING | no rebase-bot or scheduler design: `land --wait` re-merges a moved base only inside land (~VMHTBE7); post-land verify is dropped (D8). Needs an explicit drop record |
| O-19 | leases/events: one RPC for multi-agent coordination | ops 4 MERGE | BUILT | frob-lease store + `lease list\|widen` (~901RTA2); subscribe/events need the daemon (M2) |
| O-20 | telemetry: evidence base, time from process start, include every verb | ops 4 KEEP | BUILT | partial: check-only telemetry line (see O-01 and S-12) |
| O-21 | manifest + semver derived from the public-API graph | ops 5.1-5.2 KEEP | DESIGNED | boundaries.md l.88 frob-release 'semver from the gob-symbols public-API graph, stamp'; cli.md `release stamp` M2; built REL001/REL002 do lockstep and cut checks only; no ticket |
| O-22 | UnbumpedApiChange: refuse stamp when version is short, reasoned override | ops 5.3 KEEP | DESIGNED | depends on the stamp above; override audit = events; no ticket |
| O-23 | changelog.d fragments (collision-free), drop per-land CHANGELOG rewrite | ops 5.4 KEEP | BUILT | `ticket fragment`, `release changelog`, REL003 (~HE2EX99, ~AR7X0X0, ~3TXB8SR) |
| O-24 | publish verb folded into CI release workflow | ops 5.5 MERGE | BUILT | release.yml via cargo-dist and trusted publishing (~XHT82FS, ~DR38G0G, ~6N2KET1) |
| O-25 | deprecated baseline generalised into one expiry-ratchet with debt | ops 5.6 MERGE | DESIGNED | exceptions.md baseline + defer; DEPR family named in rules.md; not built, no ticket |
| O-26 | ghio: typed gh seam as a library | ops 5.7 KEEP | TICKETED | D15 forbids shelling out to `gh`; replaced by frob-gh HTTPS client: ~YNC30Q8 and its error/status children (~05XQ12K, ~BCW6PWV); `release status` still reaches CI via gh (~4PT3KZB done) with Unresolved fallback |
| O-27 | ci_report folded into ghio, keep SUITE-RESULT contract | ops 5.7 MERGE | MISSING | cli.md l.270 removes `ci`; no per-job failure report designed; v2 CI uses nextest junit (build-test-ci.md l.239) |
| O-28 | ci_validity: staleness of CI evidence via affects graph | ops 5.7 KEEP | DESIGNED | boundaries.md 2.6: frob-gh, M2; no ticket |
| O-29 | fleet status/route reuse the ledger API | ops 6.1 KEEP | DESIGNED | cli.md `fleet status\|route` M2, frob-fleet; no ticket |
| O-30 | scaffold templates slimmed to fewer types | ops 6.3 KEEP | DROPPED-ON-PURPOSE | boundaries.md 2.6 scaffold templates dropped; `frob init` covers adoption (~7R0EMJ4, ~VA936C5) |
| O-31 | managed blocks: one marker mechanism for hooks, Makefile, gitignore | ops 6.3 MERGE | TICKETED | ~VFSTJNW guide and .gitattributes from templates; ~X0YT2P0 generator framework with three-layer marker; `frob init` writes .gitignore and merge driver (built) |
| O-32 | claude sync: one hook-install command, no home-dir copies | ops 6.4 MERGE | DESIGNED | git-io.md 5 one `frob hook <event>`; no install command designed (settings.json registration by hand) |
| O-33 | .claude hooks: collapse 8 python spawns into one Rust hook binary | ops 6.5 MERGE | DESIGNED | git-io.md 5 and architecture.md l.382 design it (M2); no ticket; v1 hooks keep running; the root-write guard has no v2 replacement yet (S-13) |
| O-34 | one typed config with derived schema, no *_schema pointers | ops 7.2 MERGE | BUILT | gob-config ConfigTable derive, deny unknown fields, `frob schema` (~BX9JBTT) |
| O-35 | profile ratchet kept as explicit config, not auto | ops 7.4 MERGE | DESIGNED | rules.md 7 `[check] strictness`/`[land] verify`; knobs not present in code (grep strictness: none), no ticket |
| O-36 | excludes: one prune-aware walker honoring gitignore | ops 7.5 KEEP | BUILT | gob-walk (`ignore` crate, `[check] exclude`, ~J7SYPA5) |
| O-37 | agent/worktree verbs: env export and sweep in one worktree subcommand | ops 7.6 MERGE | DESIGNED | see CLI l.90, l.297: GC built, explicit verbs M2 |
| O-38 | logging: structured tracing, stdout stays clean for JSON | ops 7.7 MERGE | BUILT | gob-log tracing (~SFBR9ZG), logs on stderr, envelope on stdout (cli.md 2) |
| O-39 | process guard (typed spawn seam) + tool-output parsers | ops 7.8 KEEP | BUILT | gob-exec allowlist/PROC001 (~SCTJS3K); parsers for zizmor and actionlint only (gob-check/tool_parse.rs); ruff/clippy/cargo/tsc parsers absent; ~S0S9G93 env allowlist todo |
| O-40 | derived-state locks: one transactional store replaces flock web | ops 7.8 MERGE | BUILT | SQLite with busy_timeout (D30, D38); ~TX6YZZE derived state with MAC in progress |
| O-41 | render: add SARIF and JUnit emitters, keep plain-canonical rule | ops 7.9 MERGE | DESIGNED | rules.md 4 `--sarif` M2 and 9 (decided in 2.0); boundaries.md 2.6 JUnit emitter M2; no ticket |
| O-42 | findings model: four-way severity incl. unresolved | ops 7.10 KEEP | BUILT | gob-rules Severity + Unresolved gate (~69X5BSZ, ~6KPBWD1) |
| O-43 | doctor slimmed to env checks | ops 7.11 KEEP | BUILT | `frob doctor` toolchain/git/cache/config/ledger/siblings (~31VNQP7) |
| O-44 | clean: one tiered `frob clean` over single store dir | ops 7.11 MERGE | DESIGNED | boundaries.md 2.6 (M2); only GC pass built (~BZXZK29) |
| O-45 | stats folded into telemetry reporting | ops 7.11 MERGE | DESIGNED | architecture.md 5 `frob stats`; cli.md `stats` M2; no ticket |
| O-46 | parse: tool-output normalization as a library | ops 7.12 KEEP | BUILT | gob-check tool_parse.rs (~XX6K71R, ~APQCEPT); cli.md l.270 removes the verb |
| O-47 | docs extraction folded into graph symbol docs | ops 7.12 MERGE | DESIGNED | code-model.md l.416 `explore docs`; no ticket |
| O-48 | format/fmt: keep directive canonicalizer only | ops 7.12 MERGE | DESIGNED | cli.md `fix` row (M1) absent from binary; `grimble fmt` for .grmb is built (~63XJMC3) |
| O-49 | ci.yml 3-OS matrix (cross-platform proof) | ops 8.1 KEEP | BUILT | ci.yml runs ubuntu and windows tests; macOS only in build-smoke.yml artifact smoke. Partial: no macOS unit/clippy run (open question Q-2) |
| O-50 | self-gate + lock-drift steps replaced by one `frob check` step | ops 8.1 MERGE | BUILT | `cargo dev ci` (~AHBKXAZ) and `frob check` in CI (~DFTJSB7) |
| O-51 | standalone-install job: binary works with no extras | ops 8.1 KEEP | BUILT | artifact smoke fixture loop (~NWXQPMM, ~DH63PV1) |
| O-52 | toolchain and SHA pinning, keep Dependabot | ops 8.1 KEEP | BUILT | CI001 over this repo's workflows (~XX6K71R), .github/dependabot.yml, rustup-init hash pin (~J84QNJ9) |
| O-53 | release.yml: single-artifact Rust release replacing 3 PyPI dists | ops 8.2 MERGE | BUILT | cargo-dist (~XHT82FS) plus one wheel set per product (~TPHS84G, D87) |
| O-54 | Lesson 1: startup and per-verb latency dominate; native binary with resident store hits tens of ms | ops 9.1 | BUILT | Rust binary, SQLite index; resident daemon deferred (git-io 6) |
| O-55 | Lesson 2: fast core first, then drop the queues (43 percent of hours were deferred work) | ops 9.2 | BUILT | D8, D25: land synchronous; no queue, sweep, watermark, quarantine |
| O-56 | Lesson 3: concurrency scaffolding is a tax of many agents on one checkout | ops 9.3 | BUILT | lease store with one lock, WIP knobs; forkserver/xdist/admission gone. Lease waits unfair: ~3WMXBBJ todo |
| O-57 | Lesson 4: state sprawl, want one embedded transactional store | ops 9.4 | BUILT | D38: two SQLite files (cache, ticket index); derived state moving out of the tree (~TX6YZZE) |
| O-58 | Lesson 5: config sprawl (432 flat fields, two config files) | ops 9.5 | BUILT | one frob.toml, per-verb typed args (Command derive) |
| O-59 | Lesson 6: observability gaps; time from process start, record every verb | ops 9.6 | BUILT | designed (architecture.md 5), partially built (S-12) |
| O-60 | Lesson 7: CI was red 93 percent and 2 h green; gate on a fast scoped check, sweep separately | ops 9.7 | BUILT | land check is the gate (ratchet, ~QAFRXM3); CI wall time measured in ~B6VY10G; no separate sweep by design |

### 2.6 E. agent-usage.md: agent needs and design implications

| Id | Need or implication | v1 evidence | Status | v2 evidence |
|---|---|---|---|---|
| U-01 | 6.1a One structured envelope (status, code, retryable, next step, ids) on every verb | agent-usage 6.1 Need | BUILT | gob-cli Envelope (`verb`, `already`, `ok`, `data`, `findings`, `warnings`, `error`, schema_version; ~H093BQT, ~31VNQP7); `next` and `elapsed_ms` not modelled (cli.md 2) |
| U-02 | 6.1b Nonzero exit only for failure; check/verify/queue statuses split from tool errors | 6.1 Need; 7.1 | BUILT | cli.md 2 exit table (D27, D41, ~H093BQT): findings give exit 0 unless --fail-on; RefusalClass |
| U-03 | 6.1c JSON by default off-TTY, text on TTY | 6.1; 7.7 | BUILT | `--format auto` (D40) |
| U-04 | 6.1d Never mislabel an informational notice as ERROR | 3.2 row 1; 6.1 | BUILT | severity-labelled diagnostics; tickets.md 8 'never mislabel severity'; ~PJH50MJ in progress for escaping |
| U-05 | 6.2a Every mutating verb safe to repeat, returns prior result with already:true | 6.2 Need; 7.2 | BUILT | D13/D26; `already` in envelope; evidence in ticket close/drop/milestone verbs |
| U-06 | 6.2b `work` on an in-progress ticket returns the existing lease | 6.2 (285 of 319 failures) | BUILT | D26: same holder gets the lease back (frob-worktree work.rs) |
| U-07 | 6.2c Client idempotency key for `new` | 6.2 Need | BUILT | `ticket new --idempotency-key` (D34) |
| U-08 | 6.2d Bounded retry / retry_after_ms instead of agents inventing retry scripts | 6.2 Need | BUILT | `--wait <secs>` exists on `land` only (`work`/`start` have none: ~3WMXBBJ); E-LEASE-HELD is exit 3 retryable with holder and since (frob-lease error.rs); retry_after_ms generic field not modelled (cli.md l.46) |
| U-09 | 6.3a Cheap, transactional preview: plan token consumed by apply | 6.3 Need | DESIGNED | D34/cli.md 3 `--dry-run` + `--apply <plan>` E-PLAN-STALE; `--dry-run` built on land/ack/test; plan tokens and `--apply` not built (only `cycle plan --apply`); no ticket |
| U-10 | 6.3b Preview covers creates, scope changes | 6.3 Need | DESIGNED | `ticket new --dry-run` absent (checked help); no ticket |
| U-11 | 6.4a Ids allocated at creation, no rename step | 6.4 Need | BUILT | D2/D24 ULID, ~handle |
| U-12 | 6.4b Stable alias surviving promotion; atomic `new --and-start` | 6.4 Need | MISSING | aliases built (`--alias`, D46); no single new-and-start verb (agents call new then work); v1 asked for it. Low priority |
| U-13 | 6.5a Lease as a first-class queryable resource (holder, expiry) | 6.5 Need | BUILT | `lease list\|widen`, lease TOML under common dir (D47), E-LEASE-HELD names holder/since/overlap |
| U-14 | 6.5b Queued acquisition with notification, not polling | 6.5 Need | TICKETED | ~3WMXBBJ bug: lease waits unfair, add `frob work --wait` with a FIFO waiter queue |
| U-15 | 6.5c Overlap shown once in the refusal with holder ticket and age | 6.5 Need | BUILT | error.rs E-LEASE-HELD: holder, since, overlap |
| U-16 | 6.5d Automatic expiry on dead worktrees | 6.5 Need | BUILT | `[lease] ttl_secs`, heartbeat, GC (~BZXZK29) |
| U-17 | 6.5e Scope declared at `new`, amended by diff (add and remove in one call) | 6.5 Need ('command once per glob' 67 refusals) | BUILT | `ticket new --scope` (repeatable), `ticket update --add-scope --remove-scope` |
| U-18 | 6.6a Land as a job: submit, wait, status | 6.6 Need | DROPPED-ON-PURPOSE | D25: land synchronous, no jobs; `--wait` bounds lock wait only |
| U-19 | 6.6b No global ledger lock held for minutes; reads lock-free | 6.6; 7.8 | BUILT | reads from index without locks (cli.md 3); ledger writes by CAS; land lock separate (tickets.md 10) |
| U-20 | 6.6c Non-landing writes allowed concurrently with a land | 6.6 Need | BUILT | ledger CAS with bounded retry (D23); land lock is separate from ledger writes |
| U-21 | 6.7a One `update` with a patch: many fields, one commit, one lock | 6.7 Need; 7.6 | BUILT | `ticket update --set k=v ... --add-label --add-scope` one commit (cli.md 3) |
| U-22 | 6.7b Batch mode: JSON lines on stdin, all or nothing | 6.7 Need | DESIGNED | cli.md `batch` row M2, D34; no ticket |
| U-23 | 6.7c Commit-free reads under 100 ms | 6.7 Need | BUILT | index reads (D38); goals.md goal 1 |
| U-24 | 6.8a Small closed verb set | 6.8 Need | BUILT | tickets.md l.619 ~35 verbs; cli.md section 4 removes v1 groups/aliases |
| U-25 | 6.8b `--schema` printing flags/inputs/outputs | 6.8 Need | BUILT | `--schema` per verb (D40, ~09E3K2T) |
| U-26 | 6.8c Errors carry the exact corrected command | 6.8 Need | BUILT | `remedy` field, remedy test against CLI registry (~992AN0Q); ~S4GVE49 todo makes remedies structured |
| U-27 | 6.8d No flag prefix abbreviation | 6.8 Need | BUILT | gob-cli `infer_long_args(false)` (cli.rs l.187) |
| U-28 | 6.9 Hot path of ~14 verbs covered first | 6.9; 7 | BUILT | show, new, work/start, update, evidence, land, check, close built; `done-report` and `body` of the 14 are NOT built (S-6, CLI l.357) |
| U-29 | 7.1 Exit codes separate tool failure from domain state | 7.1 | BUILT | same as 6.1b |
| U-30 | 7.2 Every verb idempotent and cheaply retryable | 7.2 | BUILT | same as 6.2a |
| U-31 | 7.3 Kill draft ids and promote | 7.3 | BUILT | D2 |
| U-32 | 7.4 Replace `land --status` polling with a blocking call | 7.4 | BUILT | D25 synchronous land; `--wait` |
| U-33 | 7.5 Leases first-class and queued | 7.5 | TICKETED | first-class B; queueing = ~3WMXBBJ |
| U-34 | 7.6 One update call for metadata instead of nine setters | 7.6 | BUILT | `ticket update` |
| U-35 | 7.7 Default structured output with a schema; text only on TTY | 7.7 | BUILT | D40 |
| U-36 | 7.8 Remove global ledger lock from reads and unrelated writes | 7.8 | BUILT | as 6.6b |
| U-37 | 7.9 Actor attribution (agent id, session, worktree, human flag) on every telemetry record | 7.9; 5 | MISSING | architecture.md 5 telemetry shape is (command, args shape, duration, exit, repo hash) with no actor; gob-check telemetry.rs line has no actor; ledger events do carry actor (tickets.md 2). Needs a field and a source (FROB_AGENT/identity) |
| U-38 | 7.10 Instrument every verb in telemetry | 7.10; ops 1.1 | DESIGNED | designed (architecture.md 5), built for `check` only (S-12) |
| U-39 | Hand-edit gap 1: draft-id reconciliation inside a worktree | 4 gap (1) | BUILT | no drafts (D2) |
| U-40 | Hand-edit gap 2: merge conflicts in ticket.md the driver did not cover | 4 gap (2); 58 repairs | BUILT | per-event files + union merge driver (D23, ~N6A18DJ); `ticket doctor` re-folds; real same-key conflicts remain possible |
| U-41 | Hand-edit gap 3: Done-report authoring through a verb | 4 gap (3); 28 direct Write/Edit | DESIGNED | `ticket done-report` designed (boundaries.md 2.6) but not built or ticketed (S-6) |
| U-42 | Hand-edits to ticket files outside the CLI are detected and discouraged | 4; ops 6.5 frob-suggest hand-edit-ledger rule | DESIGNED | TICK001 frontmatter-differs-from-fold detects after the fact (built); preventive hook is `frob hook` M2 (unbuilt) |

### 2.7 F. tickets.md: differentiators, redesign hints and Jira gaps

| Id | Item | v1 evidence | Status | v2 evidence |
|---|---|---|---|---|
| K-01 | Differentiator: in-repo, git-native, offline, diffable ticket history | tickets 8.2 #1 | BUILT | tickets/<ulid>/ticket.md + events (D23/D33) |
| K-02 | Differentiator: evidence-bound closure (resolvable, passing, scope-covering evidence, criteria binding) | 8.2 #2 | BUILT | close guards EvidenceGuard/DoneGuard (`done_requires`), providers nextest/command/file/attestation |
| K-03 |   sub: mutation-evidence (TEST016) as optional proof | 8.2 #2 | MISSING | TEST016 row; no design |
| K-04 |   sub: bug repro fails at parent commit (BUG002) with positive control | 8.2 #2 | DESIGNED | tickets.md l.240,451 sentence only (BUG002 row) |
| K-05 |   sub: re-verification of evidence at close and land | 8.2 #2 | DESIGNED | tickets.md 9 'passes at the closing commit'; land runs the check but does not re-run bound evidence (frob-land has no evidence re-run; grep evidence in land.rs not confirmed). Treat as DESIGNED |
| K-06 | Differentiator: scope as an enforced write lease (glob-overlap proof, TTL, wave, contention, mega-glob refusal) | 8.2 #3 | BUILT | frob-lease overlap (~8C6Y5DZ), TTL, contention built; wave and mega-glob are M2 (cli.md; tickets.md l.372) unticketed |
| K-07 | Differentiator: worktree-per-ticket and land transaction (disposable compose, CAS publish, deletion filter, passenger detection, LAND-PROOF) | 8.2 #4 | BUILT | work/land built, CAS publish built; deletion filter, passenger, LAND-PROOF printing, completeness assertion not built (S-1..S-4) |
| K-08 | Differentiator: append-only audited changes with mandatory reasons; force-overrides record | 8.2 #5 | BUILT | field events with old/new, `--reason` on update/close/drop/reopen, evidence-bypass and changelog-exempt events (tickets.md 9) |
| K-09 | Differentiator: auto-composed Done report (Changed from git, Evidence from record, claims from a real run) | 8.2 #6 | DESIGNED | not built, not ticketed (S-6) |
| K-10 | Differentiator: anchors and live-tracker citation (close refuses while a waiver cites the ticket) | 8.2 #7 | BUILT | anchors replaced by `accept` (exceptions.md l.9, X); citation guard = EXC003 over the land check (built) |
| K-11 | Differentiator: failure memory (failure log so a dead end is not retried) | 8.2 #8 | DESIGNED | tickets.md l.268 `attempt` event + requeue; event kind parses as Other, no verb; cli.md l.268 lists `fail` removed (doc conflict, Q-3) |
| K-12 | Differentiator: runs-last and milestone gating gates (MILE001-004) | 8.2 #9 | DESIGNED | boundaries.md 2.6 M2; no ticket |
| K-13 | Differentiator: fleet/agent ergonomics (brief with do-not-touch list, cluster dispatch, agent env, wave, token accounting) | 8.2 #10 | DESIGNED | brief built without lease/hazard sections; wave, cluster, tokens, agent env unbuilt (CLI rows) |
| K-14 | Differentiator: draft ids and land-time finalize (collision-free concurrent filing) | 8.2 #11 | BUILT | ULIDs make it unnecessary (D2) |
| K-15 | Differentiator: integrity machinery (content-loss guard, post-splice check, TICK gates over the ledger, doctor scans) | 8.2 #12 | BUILT | events append-only, fold equality (TICK001), `ticket doctor`, privacy scrub (~6JTAH9Q, ~2GXRW72) |
| K-16 | Differentiator: cost accounting (tokens per ticket, points-per-hour) | 8.2 #13 | DESIGNED | `cost` events designed, producer frob-hook M2; no ticket |
| K-17 | Hint: keep per-ticket directory; ONE writer story instead of ledger+mirror+lease channel+display overlay | 8.3 #1 | BUILT | D23 ledger ref CAS; leases in common dir; no mirror (D7) |
| K-18 | Hint: state transitions as first-class events with who/when/from/to/reason | 8.3 #2 | BUILT | event table tickets.md 2a (create, field, transition, ...) |
| K-19 | Hint: replace drifted freeform strings (sprint, milestone, component, labels) with declared registries | 8.3 #3 | BUILT | milestone and cycle objects built (frob-pm); labels declared in config; component registry is cli.md `ticket component` M2 |
| K-20 | Hint: keep lease model (glob-overlap proof, TTL, staleness, same-worktree exemption, additive-only carve-out); consider symbol-level leases | 8.3 #4 | BUILT | overlap/TTL/shared_files built; same-worktree exemption by holder; symbol-level and `scope_mode=append` M2 (tickets.md l.368-370) |
| K-21 | Hint: `blocked` derived from open blockers, not a state | 8.3 #5 | BUILT | tickets.md 3 derived; `doable` excludes blocked |
| K-22 | Hint: typed links, assignee, comments, query language early | 8.3 #6 | BUILT | links/comments/assignee built; `ticket query` is M2 (unticketed) |
| K-23 | Hint: evidence-provider interface so Rust-only and docs-only tickets close | 8.3 #7 | BUILT | providers nextest/command/file/attestation; pytest/ctest/vitest/junit M2 |
| K-24 | Hint: reduce land to validate, compose out-of-tree, CAS publish, resync, record; other checks pluggable | 8.3 #8 | BUILT | frob-land (~MGK5MMK); gc and ratchet added |
| K-25 | Hint: derived rebuildable index from day one | 8.3 #9 | BUILT | `.frob/tickets.sqlite` (D38) |
| K-26 | Jira gap: custom issue types / per-type workflow | 8.1 | BUILT | type enum + per-type evidence policy (tickets.md 3); custom types M2 |
| K-27 | Jira gap: first-class assignee/reporter/owner | 8.1 | BUILT | `--assignee`, reporter field |
| K-28 | Jira gap: boards with WIP limits | 8.1 | BUILT | `frob board` (~4XZVMNC), `[pm.wip]` |
| K-29 | Jira gap: backlog ranking | 8.1 | DESIGNED | fractional rank designed M2; no ticket |
| K-30 | Jira gap: sprint objects with dates, goal, carry-over, velocity | 8.1 | BUILT | cycles (frob-pm): new/assign/plan/close/velocity |
| K-31 | Jira gap: roadmap/timeline, epic progress by points | 8.1 | DESIGNED | no design beyond `status`/`forecast`; no ticket |
| K-32 | Jira gap: component registry with owner | 8.1 | DESIGNED | tickets.md 3; `ticket component` M2 |
| K-33 | Jira gap: release object (state, date, notes) | 8.1 | BUILT | milestone objects + release verbs (D83) |
| K-34 | Jira gap: typed custom fields | 8.1 | DESIGNED | `[tickets.custom_fields]` designed (tickets.md 3), not built |
| K-35 | Jira gap: typed issue links with inverses | 8.1 | BUILT | `ticket link\|unlink` (tickets.md 4) |
| K-36 | Jira gap: comments and discussion | 8.1 | BUILT | `ticket comment` typed events |
| K-37 | Jira gap: watchers and notifications | 8.1 | DROPPED-ON-PURPOSE | tickets.md 7 'Explicitly not adopted: notification schemes'; hook/webhook M2 |
| K-38 | Jira gap: time tracking (no manual hours) | 8.1 | DESIGNED | measured cost from events (M2) |
| K-39 | Jira gap: query language, saved filters, full-text search | 8.1 | DESIGNED | `ticket query` M2, saved queries M2; index is SQLite; no ticket |
| K-40 | Jira gap: dashboards/reports (flow, cumulative flow, cycle-time) | 8.1 | DESIGNED | `stats`, `forecast`, GUI (M2); `cycle velocity` built |
| K-41 | Jira gap: declarative automation rules | 8.1 | DESIGNED | policy rules `[[policy]]` POL (rules.md 3), hooks M2; no ticket |
| K-42 | Jira gap: permissions/roles/issue security | 8.1 | DROPPED-ON-PURPOSE | tickets.md 7 'issue security levels' not adopted; agent capability flags in config (security.md) |
| K-43 | Jira gap: attachments with previews | 8.1 | DESIGNED | `ticket attach` M2 |
| K-44 | Jira gap: import/export/REST/webhooks | 8.1 | DESIGNED | envelope is the API; MCP/HTTP serve M2; `migrate tickets --from-github` M2 |
| K-45 | Jira gap: multi-project / cross-project | 8.1 | DESIGNED | fleet M2; cross-repo links `repo:` prefix M2 |
| K-46 | Jira gap: service-desk SLA/queues | 8.1 | DROPPED-ON-PURPOSE | tickets.md 7: not adopted (hosted multi-tenant) |
| K-47 | Jira gap: concurrency model (branch-local state makes truth ambiguous) | 8.1 'main architectural debt' | BUILT | D23 one ledger ref; ticket branch D79 epic ~P7WC0WS todo |

### 2.8 G. strata.md: what carries into v2

| Id | Item | v1 evidence | Status | v2 evidence |
|---|---|---|---|---|
| ST-01 | KEEP: deny-by-default model (node trust/clearance, flow label/rate/age, boundary endorse/declassify, claims noflow/reach/bound); closure + SCC longest-path + summed demand port to Rust | strata 10.3 #1 | TICKETED | grmb-spec parser/printer built (~63XJMC3); kernel computations: ~QNDWNDM G16 kernel port (CLAIM, VMOD) |
| ST-02 | KEEP: three-way verdicts (PROVED/EVIDENCED/ASSUMED) with quantifiers and counterexample witnesses; assume owned, expiring, overdue fails | strata 10.3 #2 | TICKETED | `assume ... owner ... review` in .grmb (grimble-model.md l.50); verdict kernel ~QNDWNDM; SYS010 claim-without-evidence built (~EG1XSWC) |
| ST-03 | KEEP: capability ceilings with shrink-only automation (`may`+scope, SYS100/101/111/113/109); never auto-widen | strata 10.3 #3 | TICKETED | CAP001 deny-by-default (D75) in ~V56RXG4 G14; shrink ~71BAAE0 G15; lock ratchet via grimble.lock (~T9R1B70 done); binding.md B2 CHANGED |
| ST-04 | KEEP: reflexion-model import-flow conformance (SYS003), extended to all languages | strata 10.3 #4; 4.3D UNDECLARED_FLOW | DESIGNED | binding.md B6, SYS013 reserved and assigned to G12, but G12 delivered SYS006-008; no ticket, no code (S-11) |
| ST-05 | KEEP: waivers with exact (node, rule, sub-target) triples, mandatory reason, stale-waiver failure, WAIVED always printed | strata 10.3 #5 | DESIGNED | grimble exceptions (D28, D71, D75; MDL018); `grimble exceptions list` built (~EHPFVKD); stale detection EXC013 M2 unticketed |
| ST-06 | KEEP: V-model spec graph as a generic typed graph kernel with construction-time refusals, paired levels, closure rules, milestone known_gaps | strata 10.3 #6 | TICKETED | vmodel entity in .grmb (G08 built); SYS011 built; closure kernel ~QNDWNDM G16 |
| ST-07 | KEEP: invariant triple (INV md + `frob:invariant` anchor + test id) with INV001/002/005 gates | strata 10.3 #7 | DESIGNED | anchor half built (v2 INV001, INV002 forbidden-import); evidence half (v1 INV001/INV005) not built and not ticketed |
| ST-08 | KEEP: entity/architecture/configuration intent-vs-implementation split IF paired with a verifier edge | strata 10.3 #8 | DROPPED-ON-PURPOSE | grmb-spec.md l.55 and 1457: `entity/architecture/configuration` not in the language (the condition 'IF paired with a verifier edge' was not met) |
| ST-09 | KEEP: registry drift-lock grammar (handled_by live / deferred open ticket / duplicate_of / out_of_scope with caught_by) and DENOMINATOR MANIFEST | strata 10.3 #9a | TICKETED | packs.md registry drift-lock (G04 docs done); PACK001-008 ~E0F1YSP todo; frob REG family narrowed (REG rows) |
| ST-10 | KEEP: enumerate-before-explore doctrine | strata 10.3 #9b | BUILT | practice, plus doc-consistency `frob:enumerates` claim shapes (design done) |
| ST-11 | KEEP: pair-fixture (vuln fires / hardened discharges) doctrine; positive control for every rule | strata 10.3 #9c; 9.2 | BUILT | gob-mdtest firing and non-firing controls (~K8MNYRD); ~VB2EYG6 example runner; acceptance corpora ~0HC06TD, ~ACSP6CZ |
| ST-12 | KEEP: ship-WARN-then-ratchet for new rules | strata 10.3 #9d | DESIGNED | rules.md 6 `[check] new_rule_warn_releases`; knob and strictness not built (grep none) |
| ST-13 | KEEP: data-registry shape for dangerous operations (language, library, pattern, capability_kind, cwe_links, rationale, safer_alternative, severity) with empty-cell-must-be-excused matrix | strata 10.3 #10 | TICKETED | packs.md detectors, matrix-build excuse templates (D75); ~HC9450N tier-1 pack content, ~V56RXG4 matrix |
| ST-14 | KEEP: obligation/discharge model for threats; catalogs as data in a registry file | strata 10.3 #11 | TICKETED | claim ids `weakness:CWE-78:vet` carried (grmb-spec l.187); catalog data = packs ~HC9450N |
| ST-15 | Design change 1: one substrate (per-language SymbolGraph) read by every rule | strata 10.3 DC1 | BUILT | gob-symbols/gob-ir (D56, ~PXY6QQV, ~CBP0KHT) |
| ST-16 | Design change 2: typed attr values (numbers with units) from day one | strata 10.3 DC2 | BUILT | grmb-spec 2 units as types (`req/s`) |
| ST-17 | Design change 3: parser returns spans for every construct | strata 10.3 DC3 | BUILT | grmb-model span.rs (~63XJMC3) |
| ST-18 | Design change 4: rule declaration as data so id, docs, registry rows, fixtures cannot drift | strata 10.3 DC4 | BUILT | Rule derive + inventory (D3, ~69X5BSZ), gob-dev gen (~DXP0E6B) |
| ST-19 | Design change 5: opt-in per-node strictness with a measured migration set | strata 10.3 DC5 | BUILT | SYS005 opt-in by `modeled` selector (binding.md 6) |
| ST-20 | Design change 6: multi-file design model keyed by stable ids | strata 10.3 DC6 | BUILT | includes + roots (D65, D77, ~B5XVMKR) |
| ST-21 | Design change 7: name the one thing (typed spec graph + code binding); threats/reliability/host as optional packs | strata 10.3 DC7 | BUILT | D6, D76 packs; grmb-spec l.55 non-goals |
| ST-22 | 4.3A Identity layer: SymbolId plus sig/body hash triple and optional stable anchor | strata 4.3 A | BUILT | D56/D64 stable identities and five-facet digests; anchors in binding.md 5.1 |
| ST-23 | 4.3B Model side: `owns` selectors with specificity, `may ... at`, flow `via` producer/consumer/contract selectors, `surface`, verified-by | strata 4.3 B | BUILT | grmb-model + grimble-bind owner function (~63XJMC3, ~EG1XSWC); `surface` check = SYS014 (D) |
| ST-24 | 4.3C Code side: `frob:anchor`, `frob:node`, `channel/boundary/secret` with role, `frob:effect ... because` | strata 4.3 C | BUILT | `grimble:binds`, `grimble:channel/boundary` (binding.md 4), `frob:effects` claims (~SF903MG) |
| ST-25 | 4.3D drift: UNRESOLVED/AMBIGUOUS/UNMODELED/UNIMPLEMENTED_FLOW/CHANGED/RENAMED/CONTRACT_SKEW | strata 4.3 D | BUILT | SYS004, SYS002, SYS005, SYS009, SYS007, SYS008, SYS006 built (~EG1XSWC, ~T9R1B70) |
| ST-26 | 4.3D drift: EXCEEDS_CEILING and STALE_GRANT (shrink-only fix) | strata 4.3 D | TICKETED | ~V56RXG4 G14, ~71BAAE0 G15 |
| ST-27 | 4.3D drift: UNDECLARED_FLOW and UNDECLARED_SURFACE | strata 4.3 D | DESIGNED | SYS013 / SYS014 reserved, unticketed (S-11) |
| ST-28 | 4.3E Cross-language: one resolver per language; declared FFI flows with contract fingerprints; downgrade to binding-only and say so | strata 4.3 E | BUILT | fidelity levels F0-F4 and `doctor --languages` (D56); only Rust/markdown adapters exist (M2 others) |
| ST-29 | 4.3E Effect detection via typed call-site patterns in a data registry, not substring needles | strata 4.3 E | TICKETED | packs detectors (query/callee/attribute) ~HC9450N; GRL epic |
| ST-30 | 4.3F Cost control: fingerprints/edges cached by content hash; read-only snapshot | strata 4.3 F | BUILT | gob-cache keyed by content+engine (D30, D38, D85) |
| ST-31 | 5.5 Rule macro captures id, family, severity ladder, inputs, unit of finding, waiver shape, fires_when, discharge, catalog join, controls, registry row, telemetry liveness | strata 5.5 | BUILT | Rule derive carries polarity, needs, must_measure, version, since, waivable (rules reference); liveness telemetry (rules that never fire) D: not designed |

### 2.9 H. graph-lang-dsl.md: keep, simplify, add, lessons

| Id | Item | v1 evidence | Status | v2 evidence |
|---|---|---|---|---|
| L-01 | 8.1 symref grammar `path::Qual.Name`, `path#slug`, opaque bracket suffix | graph-lang 8.1 | BUILT | gob-symbols symrefs (~CBP0KHT); D43 impl-member spelling `Type.method`, locator forms (code-model.md 2) |
| L-02 | 8.1 three-facet digests over normalized leaf tokens, formatting-insensitive, CRLF-normalized | 8.1 | BUILT | changed: scheme 2 canonical facet stream, five facets, BLAKE3 (D56, D64, ~M4T7MXR raw-bytes bug fixed) |
| L-03 | 8.1 lock semantics: endpoint-only, always include body, mandatory reason with boilerplate refusal, append-only ack_log, sorted atomic JSON | 8.1 | BUILT | gob-lock (~WKASW54), mandatory ack reason (~V4E149M), reason checker EXC001 |
| L-04 | 8.1 drift = stale ack + dangling edge with rename candidates | 8.1 | BUILT | DRIFT001/002/003/004, SYS008 renamed |
| L-05 | 8.1 directive grammar `frob:verb target key="value"`, binding rule (following within 2 lines beats enclosing), never silently drop a malformed line | 8.1 | BUILT | gob-directives (~18X6CDT; PARSE001, DSL001; ~8Z6EXFW stacked directives) |
| L-06 | 8.1 backslash continuation with empty-string join and first-line reporting | 8.1 | DESIGNED | code-model.md l.193 promises it; no continuation handling in gob-directives (grep: none); no ticket |
| L-07 | 8.1 `frob:quote(...)` mention escape | 8.1 | DESIGNED | code-model.md l.193; no implementation (grep quote in gob-directives: none); no ticket |
| L-08 | 8.1 markdown HTML-comment form with code-span blanking and GitHub slugs, test-side `frob:tests` canonical reorientation | 8.1 | BUILT | gob-symbols markdown.rs slugs; ~RSYVF9C code-span fix; scan.rs reorientation |
| L-09 | 8.1 verbs doc, describes, uses-contract, invariant, ticket, todo, waive/debt/deprecated, tests, enforces, enumerates, until | 8.1 | DESIGNED | built: doc, ticket, todo, tests, invariant, accept, defer. Designed unbuilt: describes, uses-contract, deprecated, enforces, enumerates, until, decision, hotfix (code-model.md l.227); waive/debt replaced by exceptions |
| L-10 | 8.1 waiver principle: reasoned, bounded, expiring; matching modes symbol-exact / file / package | 8.1 | BUILT | exceptions.md; matching in frob-obligations apply_exceptions; package mode via `waive_scope = Package` |
| L-11 | 8.1 affects() reverse-walk with doc/test collection and truncated flag; why output shape | 8.1 | BUILT | `graph affects`, `graph why` |
| L-12 | 8.1 content-verified ack-immune checks (DOCENUM, NEGEXIST) as a separate category | 8.1 | DESIGNED | doc-consistency.md checked facts and enumerates claim shapes; NEGEXIST rule has no design file beyond family names; no implementation ticket |
| L-13 | 8.1 fail-loud capability registries: per-language facet cells accounted for, behavioural conformance fixtures, self-disclosed degraded analyses | 8.1 | BUILT | fidelity/capability matrix and `doctor --languages` (D56, universal-model.md 3.3); conformance corpora per adapter |
| L-14 | 8.1 normalized code model + LanguageAdapter protocol (write each check once) | 8.1 | BUILT | U terms + adapter registry (~PXY6QQV, ~M691F69) |
| L-15 | 8.1 cache design: content-addressed, derived-only, delete-safe, per-file incremental, stat-then-hash | 8.1 | BUILT | gob-cache (D30, D38); stat-then-hash in gob-walk |
| L-16 | 8.1 mutation journal safety; per-file size cap and parse timeout; salvage-but-report partial parses | 8.1 | BUILT | `[check] size_cap` (D39); partial parse -> Unresolved/hole (~5NFTK3H); mutation journal moot (no mutate) |
| L-17 | 8.1 dup rung ladder R1-R5 (+R1.5), APTED, winnowing, WL hash, suffix-array regions, anti-unification | 8.1 | DESIGNED | rules.md 3 DUP 'clone rungs R1-R5'; grimble-arch; no ticket (G10 omits DUP) |
| L-18 | 8.2 one language registry as data (extension, grammar, walker, publicness, comment types, imports, tests, runner template) | 8.2 | BUILT | adapter registry (~M691F69) in gob-symbols; Cargo features per grammar |
| L-19 | 8.2 single typed directive schema (verb -> required/optional attrs); one parser; docs table generated | 8.2 | BUILT | Directive derive (D3, ~18X6CDT), generated directives page (~DXP0E6B) |
| L-20 | 8.2 unify qualname rules and fix quirks (cpp namespace free functions, rust trait-impl qualnames, kotlin partial-tree zero symbols) | 8.2 | BUILT | D43 container model; zero symbols with ERROR nodes is a conformance failure (code-model.md l.183); only Rust/markdown/toml adapters today |
| L-21 | 8.2 fold call-graph variants into one resolver, import verification on, confidence on each edge, public callees are real edges | 8.2 | BUILT | Must/May/Unknown edges (D56); ~S404RDJ cross-crate call resolution; ~EHMQCXV call qualifiers; v2 COV001 poison |
| L-22 | 8.2 cache key = hash of parser build id + grammar versions + schema | 8.2; T-4484 | BUILT | D85/~1EZ3QHP engine-scoped caches; gob-cache keyed by content, parser identity, schema |
| L-23 | 8.2 typed edge endpoints (Symbol, Doc, Ticket, Invariant, Rule, Text) | 8.2 | DESIGNED | gob-symbols edges are symbol/doc; ticket and rule endpoints as typed refs not confirmed (directive attrs typed via TicketRef etc.); mark designed |
| L-24 | 8.2 test-shaped detection as one trait on the language record | 8.2 | BUILT | tests detected by attribute scan/tests module (D48) |
| L-25 | 8.2 docs/code drift avoided by generating prose tables | 8.2; 9 | BUILT | gob-dev gen + GEN001 (~DXP0E6B); D84 doc consistency (design) |
| L-26 | 8.4 first-class cross-language binding edge `frob:binds` with per-mode adapters and normalized signature | 8.4 | DESIGNED | code-model.md 6 `binds`, BIND family (rules.md 3); no ticket, no code |
| L-27 | 8.4 normalized cross-language signature so sig digests compare across languages | 8.4 | DESIGNED | Contract facet (D74) is the cross-language comparable part; BIND family unbuilt |
| L-28 | 8.4 typed test evidence per language with explicit UNKNOWN | 8.4 | BUILT | evidence Passed\|Failed\|Unmeasured; frob-tests reach with Unknown edges |
| L-29 | 8.4 confidence-annotated call edges (certain / import-verified / name-only) | 8.4 | BUILT | Must/May/Unknown (D56) |
| L-30 | 8.4 parser-identity-keyed caches from day one | 8.4 | BUILT | as 8.2 cache key |
| L-31 | 8.4 self-describing language registry driven by test fixtures, run in CI for the Rust binary | 8.4 | BUILT | adapter conformance corpora; `doctor --languages` |
| L-32 | Lesson (T-4484): cache key must be a hash of extraction code/grammar set, not a package version | graph-lang 5.3 | BUILT | same; binary embeds build id |
| L-33 | Lesson: FFI-per-symbol calls lose to pure Python; only batch kernels win | graph-lang 6.1 | BUILT | moot: single Rust codebase, rayon batch (D16) |
| L-34 | Reversal check: 8.3 DROP 'protocol/typestate DSL' vs v1 gates KEEP PROTO001-005 | 8.3 vs gates 8 | DROPPED-ON-PURPOSE | rules.md l.175: dropped from core unless a consumer commits (consistent with 8.3; v1 gates note disagreed with itself) |

## 3. Proposed tickets

Ordered by priority. Types and priorities are proposals for the owner; none was filed.

### PT-1 Write docs/migration/rule-ids.md and make `frob migrate exceptions` refuse ambiguous v1 ids

Type: task. Priority: high.

Why: Slice evidence: gates-and-rules.md lists 667 v1 ids; ~290 are KEEP/MERGE. v2 reuses many ids with a different meaning (COV001, DOC001, REF001, INV001/002, TICK002/004/005, REL001, CAP001), and the promised map file does not exist (migration.md l.17, rules.md l.106). A consumer's `frob:waive COV001` would convert to a v2 rule with another meaning. Also settle the v2-internal TICK004-007 reuse between built rules and tickets ~943BQYB, ~3X7KVWM, ~17Q0SQ9, ~BQF97FD.

Acceptance: Given every v1 id in notes/v1/gates-and-rules.md; When the map is generated (cargo dev gen, GEN001-checked); Then each id has exactly one of: v2 id, merged-into id, or dropped, and `frob migrate exceptions` on a fixture with `frob:waive COV001` yields `accept DOC001`-or-refusal per the map, never a same-spelled rule with other semantics; and no two v2 rules (built or ticketed) share an id.

### PT-2 `ticket done-report`: auto-composed Changed and Evidence sections, brief parity

Type: task. Priority: high.

Why: v1 hot path (agent-usage 1.5: 2,383 agent calls, 18.7% help-seeking); tickets 2.10 'single write path'; boundaries.md 2.6 assigns it to frob-evidence; cli.md lists it M1; the binary has no such verb and no ticket exists (agents wrote 28 done-report files by hand in v1). Include the missing `brief` sections (concurrent leases to avoid, verify commands) from tickets 5.

Acceptance: Given a leased ticket with a diff and bound evidence; When `frob ticket done-report <id> [--why TEXT]` runs; Then a decision event records Changed (git diff --stat vs base) and Evidence (records, no re-run) plus the narrative, a repeat is `already`, and `ticket brief` for another ticket lists this lease under do-not-touch.

### PT-3 Close guards: no_open_blockers and empty-diff close detection

Type: bug. Priority: high.

Why: v1 incidents T-3064/T-3087/T-3092 (done while blocked, land touching zero source files) and BlockerOpenAtClose; tickets.md 3 names the guards but default guards are Outcome/Evidence/Done only (frob-ledger guards.rs, frob-evidence done.rs).

Acceptance: Given ticket A blocked-by open ticket B; When `ticket close A --outcome done`; Then exit 3 `E-CLOSE-BLOCKED` with remedy naming B. Given a `task` whose land diff touches only tickets/ and changelog.d; When `land`; Then refusal naming the empty-diff guard unless closed with `--no-evidence --reason`.

### PT-4 Bug repro-at-parent evidence (BUG002/BUG003) and an explicit decision on mutation evidence (TEST016)

Type: task. Priority: high.

Why: tickets.md 9 says 'bugs need a repro that fails at the parent commit' (kept from v1 BUG002/BUG003, T-1670, T-1616 gate-gaming), but there is no mechanism, rule, code or ticket; TEST016 has no design and cli.md removes `mutate`. Without it a bug ticket can close with a test that never failed.

Acceptance: Given a `bug` ticket with evidence ref R; When `ticket evidence add --repro R`; Then frob runs R in a detached worktree at the merge-base and records Failed-at-parent, closing is refused when R passes at parent (`E-REPRO-PASSES-AT-PARENT`), and `--no-behavior-change --reason` inverts it. TEST016: either a design section (opt-in, off by default) or a `dropped` ticket with reason.

### PT-5 Land guards: LAND-PROOF output, deletion filter, passenger directives, already-landed-on-main, cross-ticket leakage

Type: task. Priority: high.

Why: cli.md l.165 promises LAND-PROOF and tickets.md 10 lists 'passenger directives, deletion filter' as validations; frob-land implements neither (LandOutcome has only `commit`). v1 evidence: T-0167, T-1618 (deleted 55 waivers), T-1946, AlreadyLandedOnMain.

Acceptance: Given a branch whose diff deletes a path outside its scope; When `land`; Then `E-LAND-UNOWNED-DELETE`. Given a branch adding a `frob:ticket <other>` directive; Then `E-LAND-PASSENGER`. Given a landed ticket; When land repeats; Then `already: true`. Always: output includes `proof {commit, is_ancestor_of_base, state_on_base, verified}`.

### PT-6 grimble-bind SYS013 undeclared-flow and SYS014 surface rules

Type: task. Priority: high.

Why: v1 SYS003 was the heavily adopted core of strata (strata.md 10.1: 'ERROR since T-2407 after calibration 4834 -> 133 -> 0'); strata.md 10.3 KEEP #4 and 4.3D want it for every language; binding.md 11.3 reserves SYS013 and SYS014 for G12 but G12 shipped SYS006-008.

Acceptance: Given a model with `flow A -> B` only and a Rust import edge B->A between their owners; When `grimble check`; Then SYS013 Error naming the edge and both owners; a public symbol outside `surface` yields SYS014; an edge with an Unknown owner is Unresolved.

### PT-7 Ticket body edit through a verb (`ticket update --body/--append-body`) with structural-heading protection

Type: bug. Priority: high.

Why: body was the 9th hottest v1 verb (agent-usage 1.5) and its refusals (BodyTextAmbiguousSection 212) show structural headings are ledger syntax; cli.md lists `body` under update but the binary has no flag, so agents hand-edit ticket.md.

Acceptance: Given a ticket; When `ticket update <id> --append-body-file F --reason R`; Then one `field` event records old/new digests, `ticket.md` equals the fold, and text containing a reserved heading is refused with the exact corrected command.

### PT-8 Telemetry for every verb from process start, with exit code and actor; `frob stats`

Type: task. Priority: medium.

Why: ops 1.1/9.6 and agent-usage 7.9-7.10: v1 had no timing for test/graph/format and no human-vs-agent marker. Built telemetry is check-only with no exit or actor (gob-check telemetry.rs).

Acceptance: Given any verb; When it exits; Then one redacted line {verb, duration_ms from process start, exit, actor, worktree hash} is appended unless `[telemetry] enabled=false`; `frob stats --by verb` reports medians.

### PT-9 Read-model verbs: `status`, `stats`, `ticket query|log`, `forecast`

Type: story. Priority: medium.

Why: cli.md rows M2 with no tickets: status (exceptions + queue), stats, ticket query/log, forecast; v1 `status` was the human-facing movement view (cli-surface 3.2) and `flow` MERGEd into it.

Acceptance: Given a ledger with cycles and exceptions; When `frob status`; Then counts by category, WIP, exceptions by kind/age, velocity and a burndown ETA appear in one envelope; `ticket query 'blockedBy(X)'` returns the set.

### PT-10 `ticket wave` and `work --cluster` dispatch planning

Type: task. Priority: medium.

Why: v1 KEEP (cli-surface 7.1 wave, 7.2 work); tickets.md l.328 'wave --agents N partitions'; unbuilt, unticketed; agent-usage says agents rarely read contention, so a pre-partitioned plan removes lease refusals.

Acceptance: Given N doable tickets; When `ticket wave --agents 3`; Then up to 3 scope-disjoint groups plus a remainder naming the blocking glob, deterministic.

### PT-11 `frob check` scoping and cache flags: --files, --delta, --skip, --no-cache, --fix-all

Type: task. Priority: medium.

Why: cli-surface 3.1 KEEP rows; rules.md 4 and 6 specify --files, --delta, --fix-all; none are in `frob check --help`; agents used --only/--files/--budget/--base in v1 (agent-usage 1.3).

Acceptance: Given a dirty tree; When `frob check --files a.rs --delta`; Then only a.rs and one hop of dependents run and only fingerprints absent from `.frob/baseline` are reported; `--no-cache` bypasses all caches.

### PT-12 `frob batch` and plan tokens (`--dry-run` + `--apply <plan>` with E-PLAN-STALE)

Type: task. Priority: medium.

Why: agent-usage 6.3/6.7: 31% of v1 land attempts were dry runs whose result was stale by the real call; D34 designs batch and plan tokens; only `cycle plan --apply` exists.

Acceptance: Given a mutating verb with --dry-run; When `--apply <plan>` after an input changed; Then exit 3 E-PLAN-STALE; `batch` of ledger-only verbs is all-or-nothing in one commit.

### PT-13 `frob hook <event>`: root-write guard, directive guard, suggest, telemetry in one process

Type: task. Priority: medium.

Why: ops 6.5/6.6: v1 hooks encode five failure classes from incidents (raw commands bypassing accounting, long commands backgrounded, root dirtied, unwatched pollers, lost telemetry) at 8 python spawns per call; git-io.md 5 designs one binary; no ticket; v1 hooks are the only guard.

Acceptance: Given PreToolUse JSON for a Write into the primary checkout while a ticket worktree is leased; When `frob hook pre-tool`; Then deny with the exact `frob work` remedy within 50 ms; one process per event.

### PT-14 `frob serve --mcp` (and --http) from Command metadata

Type: epic. Priority: medium.

Why: ops 4 KEEP MCP tools 'agents prefer it to shelling out'; architecture.md l.375 designs generation from Command metadata; only grimble-serve (~VXAYFQJ) is ticketed.

Acceptance: Given the frob binary; When `frob serve --mcp`; Then every read verb is an MCP tool with the verb's schema and mutating verbs require the launch token.

### PT-15 grimble-arch: ARCH metric core and DUP rungs (extend G10)

Type: task. Priority: medium.

Why: rules.md 3/8 put ARCH and DUP in grimble-arch; G10 (~1QBHP7T) names CYCLE, LARGE, DEAD only; v1 KEEP ARCH001, ARCH104, DUP001/002 (gates 8).

Acceptance: Given a Rust fixture with a long-and-complex function and an exact clone; When `grimble check`; Then ARCH001 and DUP001 fire with remedies; both have non-firing controls.

### PT-16 SEC001-003, SEC002 and PII010 in grimble-security

Type: task. Priority: medium.

Why: gates 10 KEEP SEC001-003 (credential text, tracked .env, unwaivable live keys) and PII010; boundaries.md l.145 names grimble-security but no ticket or design detail exists.

Acceptance: Given a tracked `.env`; When check; Then SEC002 Error; a PEM private-key header is SEC003 and cannot be accepted (`waivable=false`).

### PT-17 Implement doc-consistency: SYNC family, checked facts, DOCENUM, REF orphan rule

Type: epic. Priority: medium.

Why: ~2NAP90Y delivered the design (D84) but there are no implementation tickets; v1 KEEP DOC004/005/006/010-014, DOCENUM001, ENV001, REF001/003 (gates 4) depend on it; code has only DOC001/DOC002.

Acceptance: Given a doc with a code span naming a removed verb; When check; Then a SYNC/DOC finding names the verb and its source of truth; enumerates claims diff against the real enum.

### PT-18 `frob coverage` and TEST005/006/008 floors

Type: task. Priority: medium.

Why: ops 2.4-2.5 KEEP (floors proven after incidents; stamp freshness; zero-join = silent zero); cli.md `coverage` M2; no ticket.

Acceptance: Given a coverage report older than the tracked source; When check; Then TEST006 stale; a floor can only rise without `--allow-decrease --reason`; zero-join is Unresolved, never clean.

### PT-19 Exceptions beyond M1: `exceptions` verbs, EXC002/004/006/008-013/015, baseline pools, budgets, audit

Type: epic. Priority: medium.

Why: exceptions.md lists the M2 set; v1 KEEP WAIVE002/004, DEPR005/006, pool verbs, waive-audit, BASE001; only ~B7VH1B4 (until=, EXC016/017) is ticketed.

Acceptance: Given a stale `accept`; When `frob exceptions prune`; Then it re-evaluates the rule over the file in a fresh full run and removes only STALE or RETIRED entries; baseline pools never gain a key.

### PT-20 Release: semver from the public-API graph with stamp and unbumped-API refusal

Type: task. Priority: medium.

Why: ops 5.2-5.3 KEEP ('stamp alone silently rebaselined' was a real footgun); boundaries.md l.88 designs it; built REL001/REL002 check cuts and lockstep versions only.

Acceptance: Given a changed public signature and an unchanged version; When `release stamp`; Then refusal naming the removed/changed symbols unless `--allow-unbumped --reason`, recorded as an event.

### PT-21 Mega-glob refusal, scope-ack and TICK009

Type: task. Priority: low.

Why: v1 T-1866/T-2302 (mega-globs on 39 of 72 queued tickets); tickets.md l.372 'stays', M2; unbuilt.

Acceptance: Given scope matching more than `[tickets] mega_glob_files`; When start; Then refusal unless acked with a reason.

### PT-22 Tool-output parsers for ruff, clippy, cargo, tsc, junit in gob-check

Type: task. Priority: low.

Why: ops 7.12 KEEP parse as a library; boundaries.md 2.6 assigns frob-check; tool_parse.rs has zizmor and actionlint only.

Acceptance: Given a `[[check.tool]]` clippy stage; When it emits JSON; Then findings carry mapped ids and `source_rule`; unreadable output is TOOL001 tool-failed.

### PT-23 MILE001-004 and runs-last (milestone tails)

Type: task. Priority: low.

Why: boundaries.md 2.6 M2; v1 T-5133 milestone deadlock checks (gates 5).

Acceptance: Given an open ticket blocked by a later-milestone ticket; When check; Then MILE001 Error.

### PT-24 Record explicit drop decisions for items with no v2 owner

Type: chore. Priority: low.

Why: Items with no design and weak value: gitlog verb, warm worktree pool, ci_report, registry add, `frob run`/`build` task runner (decide), rebase bot, `--type`, `--fix-ruff`, INV051 (refine dropped), COMPLIANCE001-006 (v1 CUT), SEC-CVE-FINGERPRINT-001. Goals.md rule: cut scope is recorded as a dropped ticket.

Acceptance: Given each listed item; When the ledger is read; Then a `dropped` ticket with a reason exists, or a live ticket replaces it.

### PT-25 Align cli.md with what is built (fix, ticket done-report, exceptions list, reconcile, fail)

Type: docs. Priority: low.

Why: cli.md marks `fix`, `ticket done-report`, `exceptions list`, `ticket reconcile` as M1 but the binary lacks them; tickets.md says `fail` is an attempt event while cli.md l.268 lists `fail` as removed.

Acceptance: Given cli.md section 4; When compared with `frob --help` by a SYNC check; Then no M1 verb is absent from the binary.

### PT-26 Cost events and `ticket tokens` producer (frob-hook)

Type: task. Priority: low.

Why: v1 `ticket tokens`, usage accounting (tickets 2.2); boundaries.md l.180 folds from `cost` events, producer frob-hook M2.

Acceptance: Given a harness hook reporting tokens; When the session ends; Then a `cost` event folds into ticket cost fields.

### PT-27 CI: run unit tests on macOS or record the exception

Type: task. Priority: low.

Why: ops 8.1 KEEP 3-OS matrix; ci.yml runs ubuntu+windows; macOS only in artifact smoke (build-smoke.yml).

Acceptance: Given CI; When a PR touches Rust; Then macOS runs clippy+tests, or a decision records why not.

### PT-28 Crash-safe fix journal and AUTOFIX001

Type: task. Priority: low.

Why: gates 5 KEEP AUTOFIX001; boundaries.md l.61 gob-fix journal; gob-check fix.rs has no abandoned-journal detection.

Acceptance: Given a killed `--fix` run; When the next check starts; Then AUTOFIX001 Error names the half-written files.

## 4. Structural bugs (failure modes v2 must prevent)

The v1 pain-point table (tickets.md 7), the failure families (agent-usage 3.3) and the slowness causes (gates 17) were each reduced to a failure mode. 'Prevents' states whether v2's current design (D) and code (C) already prevent it.

| Id | Failure mode (v1 evidence) | Does v2 prevent it? |
|---|---|---|
| S-1 | Land publishes from a stale base and silently reverts landed features; no proof the landed commit is on main (v1 T-0167, T-0976; LAND-PROOF 'verified' is the definition of landed, tickets 4.1) | PARTLY. Merge-then-fast-forward land plus E-LAND-STALE re-merge prevents the squash-from-stale-base revert structurally (frob-land land.rs l.755). The designed deletion filter (tickets.md 10) and the LAND-PROOF line (cli.md l.165: commit, ancestor of main, state on main, verified) are NOT built: LandOutcome returns only `commit` (plan.rs l.113). Not ticketed. See PT-5 |
| S-2 | Passenger and cross-ticket code: a dropped or reverted sibling's `frob:ticket` code rides along and deleted 55 live waivers (v1 T-1618); a branch carries another in-progress ticket's work (CROSSTICKET001) | PARTLY. Lease overlap refusal and SCOPE001 (path-outside-lease) bound what a branch may touch, but a passenger inside this ticket's own scope is undetected; the design lists 'passenger directives' in land validation (tickets.md 10) and CROSSTICKET in rules.md; nothing built or ticketed. PT-5 |
| S-3 | Manual or partial change-set drops an untracked file at land (v1 T-0448, IncompleteLand) | YES. v2 land requires a clean worktree (E-LAND-DIRTY) and fast-forwards committed history, so an untracked file cannot silently go missing; no completeness assertion needed |
| S-4 | A ledger write during a land moves the tip and strands staged files (v1 T-1619) | YES. Ledger commits are built from the ref tree and published by CAS with bounded retry (D23); the land lock is separate; a lost CAS is exit 3 retryable |
| S-5 | Agent brief contract: v1 brief carried concurrent-lease do-not-touch list, hazards, verify commands (tickets 5) | NO. `ticket brief` prints title, body, acceptance, scope, links, last events only (brief.rs). Not a data-loss bug, but the v1 KEEP content is missing; fold into PT-2 |
| S-6 | Verbs missing from the hot path push agents to hand-edit ledger files (v1 agent-usage 4: 444 hand-edit events; done-report 28 direct writes; body 1,314 calls, BodyTextAmbiguousSection 212) | NO. `ticket done-report` and body edit (`update --body`/append) are designed (cli.md, boundaries.md 2.6) but absent from the binary and unticketed; TICK001 only detects divergence after the fact. PT-2, PT-7 |
| S-7 | Falsely closed tickets: done while a blocker is open, or a 'feature' closed with a ledger-only diff (v1 T-3064, T-3087, T-3092; BlockerOpenAtClose, TICK014) | NO in code. tickets.md 3 names guards `no_open_blockers`, `children_terminal`, `has_evidence`; default_close_guards() is OutcomeGuard only, EvidenceGuard/DoneGuard add evidence, criteria, children, fragment; no blocker guard and no empty-diff detector exist (grep blockers in guards/done: none). PT-3 |
| S-8 | Empty scope accepted at start (v1 refused: 406 refusals; scope-less tickets block the queue) | DIFFERENT. `frob work` warns (work.rs l.237) and SCOPE001 flags every changed file at land: failure moves from start to land. Acceptable only if intended; record the decision (Q-8) |
| S-9 | Cluster dispatch: one worktree and union lease for an epic's dispatchable descendants (v1 `work --cluster`) | NO design. Not a data-loss bug; listed because the KEEP row for `ticket work` implied it. Open question Q-7 |
| S-10 | Rule-id reuse: v2 reuses v1 ids with different meanings, so a converted v1 `frob:waive RULE` silently suppresses the wrong v2 rule. Collisions found: COV001 (v1 undocumented symbol; v2 untested public function), DOC001, REF001, INV001/INV002, TICK002/004/005, REL001, CAP001 (v1 capacity; v2 capability exceeded), SYS001-009 (renumbered by binding.md 11.3). v2 even collides with itself: built TICK004 absolute-home-path and TICK005 private-term vs todo tickets ~943BQYB TICK004 ledger-path-reference, ~3X7KVWM TICK005 reindex-not-pure, ~17Q0SQ9 TICK006, ~BQF97FD TICK007 | NO. migration.md l.17 and rules.md l.106 promise `docs/migration/rule-ids.md`; the file does not exist (docs/migration holds only v1-import.md) and no ticket builds it or the `migrate exceptions` rewrite (M2). Design rule 'family names unchanged, ids mapped' (migration.md 3) cannot hold while ids are reused. PT-1 |
| S-11 | Reflexion-model conformance (v1 SYS003, 'used, ERROR, calibrated 4834 -> 0'): code imports between owners with no declared flow, and public surface outside the declared surface (v1 SYS110) | NO. binding.md 11.3 reserves SYS013 (undeclared flow) and SYS014 (surface) and assigns them to G12, but G12 shipped SYS006-008 only; no ticket, no code mentions SYS013/SYS014. PT-6 |
| S-12 | Telemetry blind spots: no timing for test/graph/format/coverage, duration excluded process start, no actor field (v1 ops 1.1, agent-usage 5) | PARTLY. architecture.md 5 designs per-invocation (command, args shape, duration from process start, exit, repo hash); built telemetry is one line per `check` (stage ms, files, hits, finding counts), no exit, no actor, no other verb. PT-8 |
| S-13 | Agents write into the shared primary checkout (v1 root-write-guard: 184 refusals, 'writes to the primary checkout default-DENIED'; T-2850) and backgrounded/long commands lose notifications | PARTLY. Land and ledger commits do not use the primary index/worktree (D23), so root dirt matters less, but nothing stops code edits in the primary checkout; `frob hook` (guards) is M2 and unbuilt, v1 hooks are the only guard. PT-13 |
| S-14 | SQLite cache lock contention under concurrent agents (v1: 'database is locked' 209 records; graph cache lock never released) | PARTLY. Per-worktree SQLite with busy_timeout and best-effort writes (D30); but ~CE69AVN (todo) records a flaky two-process fresh-cache write test, so lossless concurrent first-open is not yet proven |
| S-15 | Parser identity not part of cache key: stale parse artifacts after a directive-folding change (v1 T-4484: 10 phantom errors only `clean --deep` cleared) | YES. D85 / ~1EZ3QHP (done): repo-level results keyed by engine; boundaries gob-cache keyed by content, parser identity, schema; ~TX6YZZE adds MAC'd engine-scoped rows (in progress) |
| S-16 | CLI flag parsed but silently dropped before reaching config (v1: two incidents; find_dropped_cli_flags ratchet) | YES by construction. Command derive types every flag; `deny_unknown_fields` on config; remedy-vs-registry test (~992AN0Q) |
| S-17 | Stale global `frob` registered as merge driver reintroduced a fixed bug (v1 T-1443) | YES. ~JD0NPX1 (done): driver written as running executable's absolute path unless PATH frob is the same binary; `doctor` reports skew; D87 sibling lookup |
| S-18 | Content loss: replacing non-empty evidence/done report with empty; stale-snapshot wholesale writes reverting done tickets to queued (v1 T-1637, T-0680, T-1588) | YES. Append-only events, frontmatter = fold (TICK001), CAS publish; no wholesale rewrite path |
| S-19 | Gate gaming: change kind after evidence to dodge BUG002; weaken acceptance; rebind evidence silently (v1 T-1616, T-1422, T-1733) | PARTLY. Field/acceptance/evidence changes are events with old and new values and removing a bound criterion reports its evidence (tickets.md 3); no rule flags a type change after evidence exists because BUG002 itself is unbuilt (PT-4) |
| S-20 | Lease leaks: fail left in-progress holding a lease; drop from another checkout left lease file; terminal ticket's lease blocked the queue (v1 T-1050, T-4684, T-2031) | YES. Leases release on every terminal transition and requeue; TTL+heartbeat; GC; ~KDR4ZBR scope change refreshes lease. Unfair waiting remains: ~3WMXBBJ |
| S-21 | Cross-worktree blindness: doable/scope could not see siblings' starts (v1 T-0473, T-1868) | YES within a clone: leases live in the git common dir shared by worktrees (D47). Cross-clone: ledger CAS + SCOPE001 at land only |
| S-22 | Silent zero / invisible effect: verb success true but effect unreachable; field validated but not persisted; missing verb-table entry crashed after write (v1 T-2563, T-2197, T-2681, T-3081) | YES. One declaration generates schema, serde and docs (TicketField derive, ~A7J9FD5); fold-equality integrity; Command registry |
| S-23 | Evidence hazards: collected-but-failing test bound; 0-based --accepts bound the wrong criterion; runner timeout reported all evidence FAILED (v1 T-0398, T-3837, T-2569) | YES. Passed\|Failed\|Unmeasured (Unmeasured never reads as Failed), 1-based criteria, ~28XNB4W fixed the renumbering rebind bug, ~PFY7RCD/~XR3342F ref parsing |
| S-24 | Mirror/commit churn: 109 of last 300 main commits were ledger commits (v1 T-3542, T-3550) | PARTLY. Ledger commits go to `[tickets] ref` (default trunk) so churn on trunk persists until the ticket-branch epic ~P7WC0WS (D79, todo) lands |
| S-25 | Hot shared files serialized 5-8 agents (v1 T-4650 registry-file carve-out); mega-globs on 39 of 72 queued tickets (T-1866) | PARTLY. `[lease] shared_files` for lockfiles (built, ~CTKE1J4); `scope_mode=append`, symbol-level scopes and mega-glob refusal are M2 and unticketed |
| S-26 | Rust-only/docs-only repos cannot close tickets without a Python test collector (v1 T-0215, T-3156) | YES. Provider trait with nextest/command/file/attestation |
| S-27 | `doable` took >120 s on 1.2k tickets (v1 T-0938) | YES by design: SQLite index (D38); not measured at that scale here (bench ticket ~B6VY10G covers suite time) |
| S-28 | Informational notice prefixed ERROR dominated agent-visible output (854 occurrences) | YES. Severity-labelled diagnostics, envelope separates warnings from errors |
| S-29 | Falsely green via missing tool: a stage that cannot run reports nothing (v1 TOOL001/002) | YES. ~APQCEPT (done): TOOL001 tool-failed required Unresolved |
| S-30 | Reversal watch: `--budget` removed on the premise a cold full check stays under 30 s (rules.md 4); cold check here is 29 s (~AKMV3C3 todo, 20 s in file rules; ~Z9C6V0F) | AT RISK. The design says `--budget` is reconsidered above 30 s cold on a real repo. Track ~AKMV3C3; no action unless it regresses |

## 5. KEEP items v2 overturned on purpose

| v1 KEEP | v1 source | v2 decision |
|---|---|---|
| PROTO001-005 (typestate) | gates KEEP | rules.md l.175: dropped from core unless a consumer commits |
| profile verbs, one-way ratchet (`profile show\|downgrade`) | cli KEEP, ops MERGE | rules.md 7: one strictness knob, no ratchet |
| verify status/now/explain/dispose/drain-async, quarantine, flake quarantine | cli KEEP, ops KEEP | boundaries.md 2.6, rules.md 6, D8, D25 |
| scaffold list/new templates | cli KEEP, ops KEEP | boundaries.md 2.6; `frob init` only |
| anchor tickets, WIRE002, `ticket anchor` | cli KEEP, tickets 8.2 | exceptions.md l.9: permanent `accept` |
| renumber, promote, admin namespace | cli KEEP | D2 ULIDs; cli.md l.268 |
| `--budget`, BUDGET001 | cli KEEP, gates KEEP | rules.md 4 (watch ~AKMV3C3) |
| entity/architecture/configuration verifier edge | strata KEEP (conditional) | grmb-spec l.55 |
| DEPLOY001-003, HOST001/002, HOST-BLAST | gates KEEP | cli.md l.270 deploy removed; strata 10.3 CUT |
| COMPLIANCE001-006 | gates KEEP (design pack) | no pack; strata 10.2 CUT |
| `waive-audit`, `pool` verbs | cli KEEP | replaced by `exceptions` (cli.md l.272) |

## 6. DROP items that a later v2 decision reversed

| Id | v1 DROP | v2 decision and consequence |
|---|---|---|
| R-1 | NARR001 (v1 DROP: style, narrative lives in tickets) | v2/docs/design/documentation.md section 4: NARR001 comment blocks over 6 lines or citing more than one ticket; same intent as v1 DOCARCH002/NARR001 caps. Reversal of the drop with a tighter threshold. Not built, not ticketed. |
| R-2 | DOCARCH001/TICK011/WAIVE009/010 (v1 DROP: English phrase scans) | documentation.md NARR002 history words (`used to`, `previously`, `regression`, `incident`) is a prose-lexical scan of the kind v1 marked DROP; exceptions.md 5 reason checker restates-the-rule and boilerplate deny-list is milder. Decide whether NARR002 stays. |
| R-3 | PRE001 (v1 DROP: slow ceremony; scope lease replaces it) | rules.md section 3 SCOPE, PRE, QUEUE row carries 'pre-work sweep'. Contradicts the drop reason; no PRE rule exists in code or tickets. |
| R-4 | TDD001 (v1 DROP: git-history archaeology, costly) | rules.md section 3 TEST, TDD row carries 'commit-order'; boundaries.md l.140 lists TDD under frob-obligations. |
| R-5 | NEGEXIST001 (v1 DROP: niche claim lint) | rules.md section 3 DOC row 'absence claims expire'; boundaries.md l.140 lists NEGEXIST; no design file. |
| R-6 | COV006 (v1 DROP: callgraph false-edge prone) | rules.md section 3 COV row 'private-reach warning (with public callees now real edges)': justified reversal (the v1 reason is fixed by Must/May/Unknown edges). |
| R-7 | `frob ci report` / ci wrappers (v1 DROP: never wired; gh dependency) | partial reintroduction: `release status` reads CI conclusion (~4PT3KZB), ci_validity KEEP in boundaries.md 2.6, frob-gh HTTPS client (~YNC30Q8). Consistent with D15 (no `gh`), but not with the cli-surface 'DROP ci'. |
| R-8 | `sys` verbs (v1 DROP: strata is a separate product) | reintroduced as the grimble product by D11; consistent with the note's own caveat. Listed for completeness. |

Other DROP rows were checked: no v2 design or ticket reintroduces PERF lexical rules, EXHAUST/FFI, SUPPRESS, CONFIGPATH, PKG, NATIVE, PORT, LEXCHECK, CLAUDE, WIRE003, `*SCHEMA001`, the web families, FUZZ, mutate, refactor, deploy, natives, process, sync-skills, exports, whereis, or the deprecated shims (rules.md l.172-176, cli.md l.268-273).

## 7. Open questions

- Q-1: Conflicting v1 verdicts inside this slice: gitlog (cli-surface KEEP vs ops DROP), parse (cli DROP vs ops KEEP), warm pool (cli MERGE vs ops DROP), narrative (cli MERGE vs ops DROP), PROTO (gates KEEP vs graph-lang 8.3 drop). v2 sided with the drop in each case except narrative; confirm each in PT-24.
- Q-2: Is the macOS unit-test gap intended (artifact smoke only)? PT-27.
- Q-3: `fail`: tickets.md keeps an `attempt` event and requeue; cli.md lists `fail` as removed. Which wins? Is `requeue --reason` supposed to write the attempt event?
- Q-4: Task runner (`frob run`, `[commands]`): v1 replaced Makefiles with it (cli-surface 5, ops 7.1). v2 has `[[check.tool]]` stages only. Drop or design? CLAUDE.md says frob verbs are the interface; consumer repos may still need a named-command runner.
- Q-5: Strata compliance/threat/CWE catalogs: v1 cut them (strata 10.2) yet gates marks COMPLIANCE001-003 and THREAT001-006 KEEP. v2 packs allow them as data; confirm whether any ship in the std pack (~HC9450N).
- Q-6: INV051 (refinement soundness) depends on `refine`, which .grmb dropped (binding.md B8). Drop the rule?
- Q-7: Cluster dispatch (`work --cluster`, brief --cluster): needed for epics, or does `wave` replace it?
- Q-8: Empty-scope tickets: warn at `work` (current) or refuse (v1, 406 refusals avoided late failures)? See S-8.
- Q-9: Should `frob check --budget` stay removed given ~AKMV3C3 (29 s cold)? Threshold in rules.md 4 is 30 s.
- Q-10: v1 CAP001 (capacity) vs v2 CAP001 (capability exceeded): which id keeps capacity checks (G16 claim `bound`)? Part of PT-1.
- Q-11: LAND-PROOF 'verified' semantic: v2 land is a fast-forward; is proof still needed or is the `land` event enough? Decide before PT-5.

