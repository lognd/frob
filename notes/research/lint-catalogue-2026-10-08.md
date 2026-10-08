# Lint catalogue: evidence-weighted synthesis of the lint evidence study (2026-10-08)

Ticket ~J9V1JDE (epic ~WY08EWT). Synthesis only: no repository was modified and no ticket
was filed. ASCII only. Inputs, all staged for notes/research/ (cited below by short name):

- MR = mining-report-2026-10-08.md (Strand A: 1005 repositories, 4,203 labelled human review
  comments on non-AI PRs, 427 AI-reviewer and 350 human-on-AI-PR comments, 800 refactor and
  800 fix/revert commits, CodeReviewer and ManySStuBs4J cross-checks).
- CS = creators-systems-2026-10-08.md, CG = creators-games-2026-10-08.md,
  CW = creators-web-2026-10-08.md (Strand B: vetted practitioner corpora, ADV/GADV/WADV ids).
- DS = deslop-research-2026-10-08.md (front-end visual tells, SLOP/CRAFT).
- Existing catalogue: notes/research/lint-requirements.md (R01-R37), notes/research/neatness.md,
  docs/design/{rules,neatness,cohesion,crunk,dotnet-unity,universal-model,rule-authoring,plugins,boundaries}.md,
  crates/gob-check/src/tool_parse.rs (only zizmor and actionlint parsers exist today), and the
  ticket ledger (frob ticket list --json, 1532 tickets, read 2026-10-08).

## 0. Honesty block

- Every number in the catalogue is either copied from MR/CS/CG/CW or computed from them by the
  formula in section 1. Values marked [J] are this synthesis's judgement (specificity shares,
  detectable fractions, precision priors, costs); they are stated so the coordinator can
  reweight. The script that computes the table is reproduced in the session scratchpad
  (cat/rows.py); changing a [J] value and rerunning reorders the build list.
- No detector was built or run. Detectable fractions (delta) are estimates from comment
  categories, not measured on diffs (MR 0.3: diff hunks were not stored).
- Rows are rule families or rule bundles, not single ids, where the evidence does not separate
  them (a mined category such as SIMPLIFY-IDIOM maps to dozens of bound tool rules).

## 1. Method

### 1.1 One score per row

    E     = M x s x C x A                (evidence)
    E_det = E x delta                    (evidence a mechanical rule at the row's tier can act on)
    rank  = E_det x P / cost             (build order)

- M, mined score (Strand A), reused unchanged from MR section 7 so it is reproducible against
  the report: `M = r x (1 + 2B - N) + 0.5 f + 0.25 m`, where r is the post-stratified share (in
  percent) of human thread-opening comments on non-AI PRs in the candidate (MR 3.6), B and N the
  shares of those comments marked blocking and nit, f the share of `fix` commits whose class maps
  to the candidate (MR 6.1, denominator 600) and m the share of genuine refactorings whose
  motivation maps to it (MR 5.1, denominator 491). Severity therefore enters through
  (1 + 2B - N): a category that reviewers mark blocking 60 percent of the time counts 2.2 times
  its frequency, one marked nit 67 percent of the time (formatting) counts 0.53 times.
  One correction: MR mapped all of R-DESIGN-STRUCTURE (20 percent of refactors) to C23 (mixed
  concerns); most of that motivation is human-tier decomposition, so this synthesis assigns a
  quarter of it to C23 (M for C23 1.83 instead of 5.5) [J].
- s, share: when one mined candidate feeds several rows (C02 local unused vs cross-file dead,
  C16 nesting vs idiom rewrites), s splits it so no evidence is counted twice [J].
- C, practitioner consensus factor (Strand B), in [0.25, 2.5]:
  - best corpus ratio q = min(1, w / w_ref), where w = flag + 0.5 cond - 1.5 oppose is the
    corpus's own weighted-voice score (PASS 1.0, PASS-W 0.5, organisations 1.0, unvetted 0;
    section 4 of CS, CG and CW) and w_ref normalises corpus size: 15 for CS (its top items score 12-17),
    5 for CG (top 3-5.5), 8 for CW (top 5-9);
  - C = 1 + q, plus 0.25 for each further corpus that independently flags the item with q >= 0.3
    (at most +0.5), plus 0.25 when a cited source carries measured data (Yuan et al. via Luu for
    swallowed errors, Google flakiness data for tests, Dunstan and Muratori measurements for hot
    paths, WebAIM Million and the Web Almanac for accessibility);
  - no practitioner coverage: C = 1.0 (neutral, not zero: absence of opinion is not evidence
    against); contested (credible voices on both sides, CS 4.2-4.3, CG 4.2, CW 4.2-4.3): C = 0.5
    and the rule may ship only as Advisory or off; opposed-dominant: C = 0.25.
- A, agentic modifier: 1.1 when the category's share on AI-authored PRs is at least 1.4 times
  its share on human PRs (MR 4.2: CONCURRENCY 2.3, DEPENDENCY-BUILD 1.7, ERROR-HANDLING 1.6,
  CONSISTENCY, TEST-MISSING and TEST-QUALITY 1.5, PERFORMANCE and SCOPE-PROCESS 1.4), else 1.0.
  Reason: the owner runs agents; these are the mistakes humans flag more often in agent code.
  The ratios rest on n=350 and are hypotheses, hence a small modifier.
- delta, detectable fraction at the row's tier [J]: the share of the category's comments that a
  rule at that tier would have raised. Human-tier rows get delta near 0 and are kept in the table
  only to show what is NOT lintable.
- P, precision prior [J]: 0.95-1.0 compiler or formatter facts, 0.8-0.9 bound linter rules and
  declared-structure rules, 0.6-0.7 heuristics with Bounds, 0.3-0.5 known noisy shapes. It enters
  the build rank only, following Google's Tricorder rule that only low-false-positive checks
  are deployed (CS 5.2).
- cost, story points [J] of the remaining work: bind rows exclude the one-off parser
  infrastructure (tickets N01-N04), which is ranked first as an enabler because every bind row
  depends on it.

### 1.2 How each source is discounted

- AI-reviewer comments (139,846 thread openers, 38 percent of all) carry weight 0 in M. They are
  used only as a comparison population (section 3.4). The 37 AI-template comments that leaked
  into the human sample (0.9 percent, MR 0.2) are not removed; their effect is below the CIs.
- Human comments on AI-authored PRs carry weight 0 in M and enter only through A.
- Practitioner opinion without data is bounded: C multiplies M, so opinion can at most
  double-and-a-half a mined signal and cannot create one. Items with no mined counterpart (Unity,
  React, game UX) are scored on conditional evidence (1.3) with an explicit [J] specificity, so
  the corpus alone never pushes a rule to the top.
- Contested items are kept with both sides cited (C = 0.5) and appear in the do-not-lint list or
  as Advisory/off rules; they never get Warn by default.

### 1.3 Conditional evidence for domain packs

Unity and web rows apply only where the pack applies. Their M is the parent category's share in
the matching stratum of MR (C# file language n=246, TypeScript/JS n=549, games domain n=297, web
frontend n=260; MR 3.4 and 3.5) times a specificity share [J], so they rank fairly against
general rules for a repository where they apply (hullbreach has both). They are flagged
"conditional" and ranked in the same build list.

### 1.4 Limits (read before trusting the order)

1. Single labeller. All 4,980 labels are one model's judgement; the independent second labeller
   (also a model) agreed at kappa 0.756 on 250 comments, 0.683 on severity (MR 0.2). Categories
   that were confused (DEAD-CODE vs SUGGESTION-ONLY, DESIGN vs ALTERNATIVE) are less certain;
   the severity term (1 + 2B - N) is the noisiest part of M.
2. The local classifier is weak (44 percent accuracy on 30 classes, MR 0.2), so frequencies are
   design-based estimates over the labelled sample, not over the 207k population; small
   categories (SECURITY, RESOURCE, CONCURRENCY at about 1 percent) have wide relative CIs.
3. The PR sample is the 40 most-commented PRs per repository, biased to contentious PRs; shares
   are comparable, absolute rates are not population rates.
4. Commit evidence is message intent, not diffs; 34 percent of `refactor` and 32 percent of `fix`
   commits are not what the word says (MR 5, 6.1). RefactoringMiner was not run.
5. CS is C++-heavy (701 of 2,483 items) and Rust/Java-light; CG has no talk transcripts (0 of 92,
   YouTube blocked) and its Unity consensus is largely one source family (Unity docs plus two
   analyzer vendors that derive from them, CG 0); CW has no talks either.
6. Strand B is opinion-dominated: 68 of 2,483 CS items, about 100 of 1,981 CW items cite data.
   "Consensus" is shared expert opinion. The strongest-consensus item (hidden global state, CS
   ADV001, 18 voices) is among the least flagged in review (C24, 0.2 percent): consensus and
   review frequency measure different things, and this synthesis does not let one stand in for
   the other.
7. delta, P, s and cost are judgement. Each of the top three rows stays in the top six when any
   one of its [J] values is halved (checked by rerunning cat/rows.py); positions below ten swap
   freely under such changes and should be read as tiers, not an order.
8. DS (de-slop) has no defect data at all; its tells are convergence and vendor observation
   (DS 0). It contributes no M and is scored only as context (section 3.3).

## 2. The unified catalogue

Column key: M mined score (MR 7 formula); s share of the mined candidate used by this row;
C consensus factor; A agentic modifier; E = M s C A; delta detectable fraction; E_det = E delta.
Mining ids are MR candidate ids (C01-C50) and commit classes (F-*, R-*); corpus slugs are
CS ADVnnn, CG GADVnnn, CW WADVnnn. Status uses ticket handles from the ledger; "new" means no
v2 ticket covers it. Tiers follow universal-model.md 4.4 (syntax, structure with Bounds, types,
effects) plus render and human; "tool" means the fact comes from a bound external tool.

### 2.1 General code rules (population evidence, all languages)

| Row | Candidate | Mining ids | Corpus slugs | M | s | C | A | E | delta | E_det | Owner (own or bind) | Applies | Tier and capability | Default sev | FP risk | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| K01 | Swallowed or ignored error: empty handler, discarded fallible result, catch-all that neither rethrows nor logs | C30; F-ERROR-HANDLING | ADV015, ADV049, ADV031 | 5.4 | 1 | 2.02 | 1.1 | 12.0 | 0.4 | 4.8 | grimble (new ERR family) + bind ruff BLE001/E722/S110, clippy let_underscore_must_use, rustc unused_must_use, ts-eslint no-floating-promises, Roslyn CA1031/CA1806, errcheck | universal (syntax); types for discarded Result | syntax; types where the adapter has type_of | Warn | low (explicit discard only) | new (v1 ~0FPQXHD is the consumer-audit shape) |
| K02 | Unused import, variable, parameter (local) | C02 (local part); R-DEAD-CODE | ADV076, WADV024 | 10.2 | 0.6 | 1.88 | 1.0 | 11.51 | 0.9 | 10.36 | bind: rustc/clippy unused_*, ruff F401/F841/ARG, ts-eslint no-unused-vars, Roslyn IDE0051/IDE0052/IDE0060/CS0168/CS0219 (+ Unity USP suppressors), staticcheck U1000 -> DEAD ids | languages (per bound tool) | syntax (tool) | Warn | low | new (bind) |
| K03 | Dead symbol across files (no reference from any root) | C02 (cross-file part); R-DEAD-CODE | ADV076, WADV024 | 10.2 | 0.4 | 1.88 | 1.0 | 7.67 | 0.6 | 4.6 | grimble-arch DEAD | universal | structure with Bounds (references_to hi empty; entrypoints) | Warn | medium (reflection, engine roots -> Unresolved) | ticketed ~1QBHP7T |
| K04 | Nesting depth and cognitive complexity | C16 (structural part), C15 | ADV011 | 10.5 | 0.3 | 1.78 | 1.0 | 5.61 | 0.5 | 2.8 | grimble NEAT004 (own); NEAT005 bound (clippy cognitive_complexity, ruff C901, eslint complexity) | universal | syntax | Advisory | medium | ticketed ~GFWC6QP (NEAT004) |
| K05 | Simplification and idiom: use the standard API or the simpler form | C16 (rest), C17; R-SIMPLIFY | ADV024, ADV007 (contested: raw loops) | 9.35 | 1 | 1.67 | 1.0 | 15.61 | 0.3 | 4.68 | bind: clippy style/complexity, ruff SIM/C4/UP/PIE/RET, ts-eslint stylistic-type-checked, Roslyn IDE00xx, staticcheck S1xxx, clang-tidy modernize/readability | languages | syntax/types (tool) | Advisory | low per tool rule | new (bind) |
| K06 | Missing null, empty or boundary handling | C29; F-NULL-EDGE | web ts-zod-parse-boundary, WADV ts strict family | 8.0 | 1 | 1.25 | 1.0 | 10.0 | 0.35 | 3.5 | bind type checkers in strict mode (~7TYG963, ~69D9E89, Roslyn nullable CS86xx); own TYPECFG001 strictness-disabled config rule | languages ts, csharp, python | types (bound checker); syntax for config | Warn | low | new (TYPECFG001); type facts ticketed |
| K07 | CI, build and dependency hygiene (pinning, permissions, vetting) | C36; F-BUILD-DEPS-CI | ADV051 | 8.3 | 1 | 1.43 | 1.1 | 13.06 | 0.5 | 6.53 | grimble-ci CI001-015, DK; grimble-vet VET; zizmor/actionlint bound | project (manifests, workflows) | syntax over manifests | Warn/Error | low | ticketed ~8886VJ4, ~RPQKHAV; zizmor bound ~XX6K71R done |
| K08 | Bound perf micro-idioms (clone in loop, needless collect, string concat in loop) | C33; R-PERFORMANCE | ADV003, ADV050 (contested), GADV075 (contested) | 6.4 | 1 | 1.2 | 1.0 | 7.68 | 0.2 | 1.54 | bind clippy perf, ruff PERF, Roslyn CA18xx | languages | types (tool) | Advisory | low per tool rule | new (bind) |
| K09 | Layering and code in the wrong module or layer | C20, C23 (recomputed); R-DESIGN-STRUCTURE (quarter share) | ADV028 (human), ADV005 | 3.5 | 1 | 1.3 | 1.0 | 4.55 | 0.4 | 1.82 | grimble SYS004 (declared flows), ARCH layering | universal | structure with Bounds over owners | Warn | low when declared | implemented SYS004 (~FS8AX88); ARCH in ~1QBHP7T scope |
| K10 | One job per function (COH001-004) | C23, C21; R-READABILITY | COH sources (5 voices, no data) | 2.3 | 1 | 1.33 | 1.0 | 3.06 | 0.2 | 0.61 | grimble COH | universal | def-use, effects, apply_targets | Warn (COH004 Advisory) | medium | ticketed ~X5ECTEM, ~8GMB58A, ~7T5Y51S, ~BH9BHQ5 |
| K11 | Typos in identifiers, comments and docs | C09; F-DOC-TYPO | none | 5.5 | 1 | 1.0 | 1.0 | 5.5 | 0.7 | 3.85 | bind typos (crate-ci) -> SPELL001 | universal (text) | syntax | Advisory | medium (allowlist) | new (bind; this repo runs typos pass/fail only) |
| K12 | Hidden global or singleton state (NEAT012) | C24 | ADV001, GADV034 | 0.4 | 1 | 2.25 | 1.0 | 0.9 | 0.7 | 0.63 | grimble NEAT012 | universal | scope graph | Warn | medium | ticketed ~GFWC6QP |
| K13 | Ambient clock/rng/env/fs call outside the shell (NEAT013) | C24 (share) | ADV091 | 0.2 | 1 | 1.23 | 1.0 | 0.25 | 0.8 | 0.2 | grimble NEAT013 | universal | callee vocabulary | Warn | low | implemented |
| K14 | Naming convention (case, prefix) | C14 | ADV002, GADV015, WADV113 (conditional) | 0.7 | 1 | 2.25 | 1.0 | 1.57 | 0.9 | 1.42 | bind ruff N8xx, rustc non_*_case, Roslyn IDE1006, ts-eslint naming-convention, revive | languages | syntax (tool) | Advisory | low | new (bind) |
| K15 | Unclear or generic names (util, common, stutter) | C13; R-NAMING | ADV027 (human), ADV041, ADV093 | 5.1 | 1 | 1.67 | 1.0 | 8.52 | 0.05 | 0.43 | not owned (human); later NAME002 generic-module-name Advisory | universal | human; syntax for the generic-name slice | Advisory | high | new candidate, deferred |
| K16 | Exact and renamed clones (DUP R1-R3), three or more occurrences | C03; R-DUPLICATION | ADV018; ADV120, WADV087 (contested threshold) | 4.4 | 1 | 1.7 | 1.0 | 7.48 | 0.35 | 2.62 | grimble-arch DUP | universal (R1-R3) | syntax digests | Advisory | medium | designed (rules.md R1-R5); no v2 ticket -> new |
| K17 | Type weakness: any, unchecked casts, string-typed values | C40; R-TYPE-SAFETY | ADV004, ADV019, web TS family | 4.3 | 1 | 2.18 | 1.0 | 9.37 | 0.4 | 3.75 | bind ts-eslint no-explicit-any/no-unsafe-*, ruff ANN401, pyright reportUnknown*, clippy as_conversions (opt-in), clang-tidy cppcoreguidelines-pro-type-*; own NEAT020-026 later | languages | types (tool) | Warn (any), Advisory (casts) | low | new (bind); NEAT020-026 designed |
| K18 | Change outside the ticket's scope (scope creep) | C25 | none (process) | 4.1 | 1 | 1.0 | 1.1 | 4.51 | 0.5 | 2.25 | frob SCOPE001 | project (tickets+diff) | diff + lease | Error | low | implemented |
| K19 | Injection, secrets, authz, unsafe input | C34; F-SECURITY | WADV018/019/021/022/039 | 4.0 | 1 | 1.69 | 1.0 | 6.76 | 0.35 | 2.37 | grimble-websec WEBSEC/SEC; bind ruff S, eslint no-implied-eval, react/no-danger | languages + universal taint | effects/taint | Error/Warn | medium (v1 measured ~5% TP: ~GR4ZPYH) | ticketed ~8998PBE, ~RD56D5R |
| K20 | Test hygiene: no assertion, sleep/clock/rng in tests, logic in tests, shared state | C28; F-TEST | ADV060, ADV082, ADV096, WADV010, WADV043 | 3.5 | 1 | 2.25 | 1.1 | 8.66 | 0.3 | 2.6 | grimble new TESTQ family + bind ruff PT, jest/vitest/testing-library plugins | universal (test_items) | test_items + callee vocabulary | Warn (no-assert), Advisory (logic) | medium | new |
| K21 | Platform portability (host paths, OS assumptions) | C37; F-PLATFORM-COMPAT | none | 3.4 | 0.4 | 1.0 | 1.0 | 1.36 | 0.5 | 0.68 | grimble PATH | universal | syntax + const_value | Warn | low | ticketed ~21PHK3V |
| K22 | State initialised or ordered wrongly, two-phase init | C49; F-STATE-INIT | ADV033 | 3.2 | 1 | 1.62 | 1.0 | 5.18 | 0.1 | 0.52 | grimble NEAT027 (later); Unity lifecycle rows | universal | effects | Advisory | high | designed (NEAT027) |
| K23 | Concurrency: lock across await, floating promise, async void, blocking in async, task leak | C32; F-CONCURRENCY | ADV025, ADV066, ADV073 | 3.2 | 1 | 1.67 | 1.1 | 5.88 | 0.3 | 1.76 | bind clippy await_holding_lock, ruff ASYNC, ts-eslint no-floating-promises/no-misused-promises, VSTHRD002/100/103/110, go vet copylocks/lostcancel; own lock-across-await later | languages | types (tool) | Warn | low | new (bind) |
| K24 | Missing test for new behaviour | C27 | ADV104 (coverage contested) | 3.1 | 1 | 1.0 | 1.1 | 3.41 | 0.5 | 1.71 | frob COV001, TEST001 | universal | test_items + reach | Warn | medium | implemented |
| K25 | Magic numbers and literals | C18 (F-CONFIG-DEFAULT mapping inflates) | Insomniac vs sentinels (games contested) | 2.8 | 1 | 0.75 | 1.0 | 2.1 | 0.3 | 0.63 | bind ruff PLR2004 off by default; own only colour (crunk COLOR001) and path (PATH001) literals | languages | syntax | Advisory (off) | high | designed NEAT009 (bound only) |
| K26 | Acquisition without release on the teardown path (resources, subscriptions, timers, handles) | C31; F-RESOURCE | ADV008, GADV031, GADV079, WADV013 | 2.6 | 1 | 2.3 | 1.0 | 5.98 | 0.35 | 2.09 | grimble PAIR001 universal with per-language vocabularies; bind Roslyn CA2000, ruff SIM115, go vet lostcancel | universal (vocabulary packs) | structure with Bounds over def-use and teardown roots | Warn | medium (escaping handle -> Unresolved) | ticketed ~4CESXMT (v1 wording; re-scope) |
| K27 | Formatting and import order | C12; R-TOOLING-LINT | ADV017, ADV026 | 2.0 | 1 | 1.77 | 1.0 | 3.54 | 0.95 | 3.36 | bind rustfmt, ruff format, prettier, dotnet format/csharpier, gofmt, clang-format -> FMT001 (fix tier A) | languages | tool | Warn | none | new (bind; cargo fmt stage has no id) |
| K28 | Wrong or swapped argument at a call site | C48; ManySStuBs SWAP_ARGUMENTS, OVERLOAD_* | ADV032 | 1.5 | 1 | 1.63 | 1.0 | 2.44 | 0.25 | 0.61 | grimble NEAT022 (declaration side); call-site name-mismatch later | universal | types | Advisory | high | designed (NEAT022) |
| K29 | Stale or contradictory doc and comment, broken links | C06, C10 | ADV099 | 2.3 | 1 | 1.2 | 1.0 | 2.76 | 0.5 | 1.38 | frob DRIFT, DOC002 | universal | digests + doc graph | Warn | low | implemented; ~Q576RV4 ticketed |
| K30 | Non-exhaustive match or switch over a closed set | C50; F-MISSING-CASE | ADV070 | 1.3 | 1 | 1.33 | 1.0 | 1.73 | 0.7 | 1.21 | bind clippy wildcard_enum_match_arm, ts-eslint switch-exhaustiveness-check, Roslyn IDE0010/IDE0072/CS8509, pyright reportMatchNotExhaustive | languages | types (tool) | Warn | low | new (bind); NEAT026 designed |
| K31 | Public item without documentation | C05 | ADV013 | 1.2 | 1 | 1.78 | 1.0 | 2.14 | 0.8 | 1.71 | frob DOC001 (C# and Python readers ticketed) | universal | visibility + doc | Warn | low | implemented; ~MY9A7AX, ~TCKEFKF |
| K32 | Breaking public API without version bump or deprecation | C35 | ADV012, ADV023 | 1.2 | 1 | 1.78 | 1.0 | 2.14 | 0.8 | 1.71 | bind cargo-semver-checks, PublicApiAnalyzers RS0016/RS0017, api-extractor, griffe -> VERSION001 | languages | tool (API diff) | Error | low | new (bind); VERSION designed |
| K33 | Visibility wider than its uses | C19; ManySStuBs CHANGE_MODIFIER | ADV023, ADV020 | 0.6 | 1 | 1.68 | 1.0 | 1.01 | 0.6 | 0.6 | grimble-arch VIS001; bind rustc unreachable_pub | universal | visibility + references_to with Bounds | Advisory | medium | new |
| K34 | Leftover debug output and commented-out code | C01 | ADV076 | 0.6 | 1 | 1.3 | 1.0 | 0.78 | 0.8 | 0.62 | bind ruff T20/ERA001, eslint no-console/no-debugger, clippy dbg_macro/print_stdout | languages | syntax (tool) | Warn | low | new (bind); TODO001/NARR implemented |
| K35 | Boolean flag and too many parameters | C22 | ADV016, ADV032 | 0.3 | 1 | 1.77 | 1.0 | 0.53 | 0.9 | 0.48 | grimble NEAT002 (implemented), NEAT003 | universal | syntax | Advisory | low | implemented NEAT002; NEAT003 ~GFWC6QP |
| K36 | Function too long | C21 | ADV101 (contested), GADV325 (opposed) | 0.5 | 1 | 0.5 | 1.0 | 0.25 | 0.9 | 0.23 | NEAT001 bound only, Advisory, high default | universal | syntax | Advisory (off) | high | implemented (keep advisory) |
| K37 | Comment policy: redundant or missing why-comments | C07, C08 | ADV052 (contested), ADV030 (human) | 1.0 | 1 | 0.5 | 1.0 | 0.5 | 0.2 | 0.1 | do not lint beyond DOC001 and NARR | - | human | - | high | do-not-lint |
| K38 | Changelog fragment missing | C11 | none | 0.3 | 1 | 1.0 | 1.0 | 0.3 | 1.0 | 0.3 | frob REL003 | project | diff | Warn | none | implemented |
| K39 | Logic error (wrong condition, value, identifier) | C42; F-LOGIC; ManySStuBs CHANGE_IDENTIFIER | none | 26.0 | 1 | 1.0 | 1.0 | 26.0 | 0.05 | 1.3 | bind tool correctness groups (clippy correctness/suspicious, ruff B/PLE/PLW, eslint no-constant-binary-expression/no-self-compare/no-dupe-else-if, Roslyn CA2245); frob value is test reach and evidence | languages | types (tool) | Error (correctness) | low | new (bind); ~RFX8DJX comparison idiom |
| K40 | Documentation prose quality | C46; DOCS-CHANGELOG | none | 9.5 | 1 | 1.0 | 1.0 | 9.5 | 0.0 | 0.0 | not linted (typos and links are K11, K29) | - | human | - | - | do-not-lint |
| K41 | Logging level and content | C39 | Chromium/Linux vs owner rule (contested) | 1.1 | 1 | 0.5 | 1.0 | 0.55 | 0.1 | 0.06 | not linted; secrets in logs are SEC | - | human | - | high | do-not-lint |

### 2.2 Unity pack (conditional evidence: given a Unity project)

| Row | Candidate | Mining ids | Corpus slugs | M | s | C | A | E | delta | E_det | Owner (own or bind) | Applies | Tier and capability | Default sev | FP risk | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| U01 | UnityEngine.Object null bypass (??, ?., is null on a destroyable object) | C29 in C# stratum (x0.25) | GADV012 | 1.08 | 1 | 1.6 | 1.0 | 1.73 | 0.9 | 1.56 | bind Microsoft.Unity.Analyzers UNT0007/0008/0023/0029 + USP0001/0002 | languages csharp (unity pack) | types (tool) | Warn | low | new (bind) |
| U02 | Managed allocation in hot code (new collections, closures, boxing, array-returning Unity APIs) | C33 in C# stratum (x0.3) | GADV009, GADV035 (contested target) | 1.89 | 1 | 1.95 | 1.0 | 3.69 | 0.5 | 1.84 | grimble unity pack (own: needs hot context); bind UNT0045 where present | languages csharp (unity pack) | effects + hot-context reach | Advisory | medium | new |
| U03 | Lookup in hot code (GetComponent, Find*, Camera.main, Transform.Find) | C33 in C# stratum (x0.2) | GADV010 | 1.26 | 1 | 1.7 | 1.0 | 2.14 | 0.8 | 1.71 | grimble unity pack (own: hot context is cross-method) | languages csharp (unity pack) | structure: hot-context reach + callee vocabulary | Advisory | low | new |
| U04 | Unity API idioms: CompareTag, cached property ids, NonAlloc, generic GetComponent, empty or misspelt messages, string dispatch, new MonoBehaviour, SerializeField hygiene | PERFORMANCE and LOGIC-BUG in C# stratum [J] | GADV022-030, GADV017, GADV024, GADV037, GADV041, GADV042 | 2.0 | 1 | 1.6 | 1.0 | 3.2 | 0.9 | 2.88 | bind Microsoft.Unity.Analyzers (UNT0001/2/6/10/11/12/13/16/21/24/26/28/33/38/41/46) with the USP suppressor set | languages csharp (unity pack) | types (tool) | Warn/Advisory per id | low | new (bind) |
| U05 | Unity paired lifecycle (+= in OnEnable without -= in OnDisable, RegisterCallback, action Enable/Disable, Addressables Load/Release) | C31 in C# stratum (x0.5) | GADV031, GADV079 | 0.9 | 1 | 1.5 | 1.0 | 1.35 | 0.5 | 0.68 | grimble PAIR001 unity vocabulary | languages csharp (unity pack) | structure with Bounds | Warn | medium | new (vocabulary on ~4CESXMT) |
| U06 | Legacy Input or hard-coded KeyCode/device reads in an Input System project | USER-FACING in games domain [J] | GADV004, GADV005 | 0.8 | 1 | 1.9 | 1.0 | 1.52 | 0.9 | 1.37 | grimble unity pack; crunk GX remap coverage | languages csharp (unity pack) | syntax + project settings | Warn | low | new |
| U07 | Fixed-timestep misuse: physics forces or Rigidbody moves in Update, frame time into integration | F-LOGIC in games domain [J] | GADV002, GADV101 | 1.0 | 1 | 2.0 | 1.0 | 2.0 | 0.4 | 0.8 | grimble unity pack (UNT0004 covers only fixedDeltaTime in Update) | languages csharp (unity pack) | types + lifecycle roots | Warn | medium | new |
| U08 | asmdef and Resources hygiene, material instancing | [J] thin | GADV080, GADV069, GADV065 | 0.3 | 1 | 1.3 | 1.0 | 0.39 | 0.6 | 0.23 | grimble unity pack (later) | project | syntax over JSON | Advisory | low | new candidate, deferred |

### 2.3 Web front end (conditional evidence: given a TS/JS front end)

| Row | Candidate | Mining ids | Corpus slugs | M | s | C | A | E | delta | E_det | Owner (own or bind) | Applies | Tier and capability | Default sev | FP risk | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W01 | JSX accessibility: labels, alt text, accessible names, button vs link, ARIA misuse, keyboard support, tabindex, autocomplete | C38 in TS/JS stratum (x0.35); F-UI-RENDER | WADV001/003/004/005/007/015/016/023/026/033/044, GADV006 | 2.4 | 1 | 2.5 | 1.0 | 6.0 | 0.7 | 4.2 | bind eslint-plugin-jsx-a11y under A11Y ids; crunk-web GRL only for HTML/Vue/USS and cross-file rules | languages tsx/jsx | syntax (tool) | Warn | low | designed (A11Y101-128 v1), ~SHGXWRT; new (bind) |
| W02 | React rules: hooks order, effect deps, derived state in effect, purity, index keys, dangerouslySetInnerHTML, button type, error boundaries | LOGIC-BUG and USER-FACING in TS/JS stratum [J] | WADV002/008/017/038/040/041/048/050/059 | 1.5 | 1 | 2.0 | 1.0 | 3.0 | 0.7 | 2.1 | bind eslint-plugin-react-hooks (v6 compiler lints) and eslint-plugin-react | languages tsx/jsx | syntax/structure (tool) | Warn | low | new (bind) |
| W03 | Effect starts a request, timer or subscription without cleanup or abort | C31/C32 in TS/JS stratum [J] | WADV013, ADV008 | 0.8 | 1 | 2.05 | 1.0 | 1.64 | 0.6 | 0.98 | grimble PAIR001 React vocabulary | languages tsx/jsx | structure with Bounds | Warn | medium | new (vocabulary on ~4CESXMT) |
| W04 | Route component or heavy dependency imported eagerly into the entry bundle | PERFORMANCE in TS/JS stratum [J] | WADV006 | 0.5 | 1 | 2.12 | 1.0 | 1.06 | 0.5 | 0.53 | grimble-websec WEBPERF-server/ROUTE over gob-frameworks routes + import graph | languages ts/tsx | structure (route table + imports) | Advisory | medium | new |
| W05 | Client route change without title update or focus/announcement | C38 in TS/JS stratum (x0.05) | WADV045, WADV058 | 0.35 | 1 | 1.5 | 1.0 | 0.52 | 0.4 | 0.21 | crunk-web A11Y over routes | languages tsx/jsx | effects over route handlers | Advisory | medium | new |
| W06 | Generic CSS hygiene: specificity wars, id selectors, !important | USER-FACING [J] | WADV025, WADV031, WADV051 (contested) | 0.5 | 1 | 1.75 | 1.0 | 0.88 | 0.8 | 0.7 | bind stylelint under crunk ids | languages css | syntax (tool) | Advisory | low | new (bind) |
| W07 | Network data cast to a type without validation (res.json() as T) | TYPE-SAFETY in TS/JS stratum [J] | web ts-zod-parse-boundary, ts-assertion-as | 0.5 | 1 | 1.25 | 1.0 | 0.62 | 0.6 | 0.38 | grimble (types capability) Advisory | languages ts, python | types | Advisory | medium | new |
| W08 | Secrets in bundles, CSRF, cookie flags, CSP | C34 in web [J] | WADV018/019/022/054 | 0.8 | 1 | 1.69 | 1.0 | 1.35 | 0.5 | 0.68 | grimble-websec | languages + config | structure/config | Error/Warn | medium | ticketed ~8998PBE (v1 WEBSEC done) |

### 2.4 Ranking by build value (E_det x P / cost), unbuilt rows only

| # | Row | Candidate (short) | E_det | P | cost | rank value | Owner | Tier | Delivered by |
|---|---|---|---|---|---|---|---|---|---|
| 1 | K02 | Unused import, variable, parameter (local) | 10.36 | 0.95 | 2 | 4.919 | bind: rustc/clippy unused_*, ruff F401/F841/ARG, ts-eslint n | syntax (tool) | N02-N05 (profiles) |
| 2 | K05 | Simplification and idiom: use the standard API or the simpler form | 4.68 | 0.8 | 1 | 3.747 | bind: clippy style/complexity, ruff SIM/C4/UP/PIE/RET, ts-es | syntax/types (tool) | N02-N05 |
| 3 | K17 | Type weakness: any, unchecked casts, string-typed values | 3.75 | 0.85 | 1 | 3.187 | bind ts-eslint no-explicit-any/no-unsafe-*, ruff ANN401, pyr | types (tool) | N03, N04 (N02 opt-in) |
| 4 | W01 | JSX accessibility: labels, alt text, accessible names, button vs link, | 4.2 | 0.85 | 2 | 1.785 | bind eslint-plugin-jsx-a11y under A11Y ids; crunk-web GRL on | syntax (tool) | N04 |
| 5 | W02 | React rules: hooks order, effect deps, derived state in effect, purity | 2.1 | 0.85 | 1 | 1.785 | bind eslint-plugin-react-hooks (v6 compiler lints) and eslin | syntax/structure (tool) | N04 |
| 6 | K27 | Formatting and import order | 3.36 | 1.0 | 2 | 1.681 | bind rustfmt, ruff format, prettier, dotnet format/csharpier | tool | N07 |
| 7 | K06 | Missing null, empty or boundary handling | 3.5 | 0.9 | 2 | 1.575 | bind type checkers in strict mode (~7TYG963, ~69D9E89, Rosly | types (bound checker); syntax for config | N14 + ~7TYG963, ~69D9E89 |
| 8 | K23 | Concurrency: lock across await, floating promise, async void, blocking | 1.76 | 0.85 | 1 | 1.499 | bind clippy await_holding_lock, ruff ASYNC, ts-eslint no-flo | types (tool) | N02-N05 |
| 9 | K11 | Typos in identifiers, comments and docs | 3.85 | 0.75 | 2 | 1.444 | bind typos (crate-ci) -> SPELL001 | syntax | N06 |
| 10 | U01 | UnityEngine.Object null bypass (??, ?., is null on a destroyable objec | 1.56 | 0.9 | 1 | 1.4 | bind Microsoft.Unity.Analyzers UNT0007/0008/0023/0029 + USP0 | types (tool) | N01 + N05 |
| 11 | K14 | Naming convention (case, prefix) | 1.42 | 0.9 | 1 | 1.276 | bind ruff N8xx, rustc non_*_case, Roslyn IDE1006, ts-eslint  | syntax (tool) | N02-N05 |
| 12 | K08 | Bound perf micro-idioms (clone in loop, needless collect, string conca | 1.54 | 0.8 | 1 | 1.229 | bind clippy perf, ruff PERF, Roslyn CA18xx | types (tool) | N02-N05 |
| 13 | U04 | Unity API idioms: CompareTag, cached property ids, NonAlloc, generic G | 2.88 | 0.85 | 2 | 1.224 | bind Microsoft.Unity.Analyzers (UNT0001/2/6/10/11/12/13/16/2 | types (tool) | N01 + N05 |
| 14 | K39 | Logic error (wrong condition, value, identifier) | 1.3 | 0.9 | 1 | 1.17 | bind tool correctness groups (clippy correctness/suspicious, | types (tool) | N02-N05 |
| 15 | K04 | Nesting depth and cognitive complexity | 2.8 | 0.8 | 2 | 1.121 | grimble NEAT004 (own); NEAT005 bound (clippy cognitive_compl | syntax | ~GFWC6QP |
| 16 | K30 | Non-exhaustive match or switch over a closed set | 1.21 | 0.9 | 1 | 1.089 | bind clippy wildcard_enum_match_arm, ts-eslint switch-exhaus | types (tool) | N02-N05 |
| 17 | K01 | Swallowed or ignored error: empty handler, discarded fallible result,  | 4.8 | 0.9 | 5 | 0.864 | grimble (new ERR family) + bind ruff BLE001/E722/S110, clipp | syntax; types where the adapter has type | N10 |
| 18 | K07 | CI, build and dependency hygiene (pinning, permissions, vetting) | 6.53 | 0.8 | 8 | 0.653 | grimble-ci CI001-015, DK; grimble-vet VET; zizmor/actionlint | syntax over manifests | ~8886VJ4, ~RPQKHAV |
| 19 | U06 | Legacy Input or hard-coded KeyCode/device reads in an Input System pro | 1.37 | 0.9 | 2 | 0.616 | grimble unity pack; crunk GX remap coverage | syntax + project settings | N19 |
| 20 | W06 | Generic CSS hygiene: specificity wars, id selectors, !important | 0.7 | 0.8 | 1 | 0.56 | bind stylelint under crunk ids | syntax (tool) | N09 |
| 21 | K32 | Breaking public API without version bump or deprecation | 1.71 | 0.9 | 3 | 0.513 | bind cargo-semver-checks, PublicApiAnalyzers RS0016/RS0017,  | tool (API diff) | N08 |
| 22 | K34 | Leftover debug output and commented-out code | 0.62 | 0.8 | 1 | 0.499 | bind ruff T20/ERA001, eslint no-console/no-debugger, clippy  | syntax (tool) | N02-N04 |
| 23 | U03 | Lookup in hot code (GetComponent, Find*, Camera.main, Transform.Find) | 1.71 | 0.8 | 3 | 0.457 | grimble unity pack (own: hot context is cross-method) | structure: hot-context reach + callee vo | N17 + N18 |
| 24 | K16 | Exact and renamed clones (DUP R1-R3), three or more occurrences | 2.62 | 0.8 | 5 | 0.419 | grimble-arch DUP | syntax digests | N12 |
| 25 | K20 | Test hygiene: no assertion, sleep/clock/rng in tests, logic in tests,  | 2.6 | 0.8 | 5 | 0.416 | grimble new TESTQ family + bind ruff PT, jest/vitest/testing | test_items + callee vocabulary | N11 |
| 26 | K03 | Dead symbol across files (no reference from any root) | 4.6 | 0.7 | 8 | 0.403 | grimble-arch DEAD | structure with Bounds (references_to hi  | ~1QBHP7T |
| 27 | W03 | Effect starts a request, timer or subscription without cleanup or abor | 0.98 | 0.75 | 2 | 0.369 | grimble PAIR001 React vocabulary | structure with Bounds | N21 on ~4CESXMT |
| 28 | K26 | Acquisition without release on the teardown path (resources, subscript | 2.09 | 0.7 | 5 | 0.293 | grimble PAIR001 universal with per-language vocabularies; bi | structure with Bounds over def-use and t | ~4CESXMT (re-scope, section 4.3) |
| 29 | U05 | Unity paired lifecycle (+= in OnEnable without -= in OnDisable, Regist | 0.68 | 0.7 | 2 | 0.236 | grimble PAIR001 unity vocabulary | structure with Bounds | N20 on ~4CESXMT |
| 30 | U02 | Managed allocation in hot code (new collections, closures, boxing, arr | 1.84 | 0.6 | 5 | 0.221 | grimble unity pack (own: needs hot context); bind UNT0045 wh | effects + hot-context reach | N17 + N18 |
| 31 | K25 | Magic numbers and literals | 0.63 | 0.3 | 1 | 0.189 | bind ruff PLR2004 off by default; own only colour (crunk COL | syntax | none (bound, off by default) |
| 32 | U07 | Fixed-timestep misuse: physics forces or Rigidbody moves in Update, fr | 0.8 | 0.7 | 3 | 0.187 | grimble unity pack (UNT0004 covers only fixedDeltaTime in Up | types + lifecycle roots | N19 |
| 33 | K19 | Injection, secrets, authz, unsafe input | 2.37 | 0.6 | 8 | 0.177 | grimble-websec WEBSEC/SEC; bind ruff S, eslint no-implied-ev | effects/taint | ~8998PBE, ~RD56D5R |
| 34 | K12 | Hidden global or singleton state (NEAT012) | 0.63 | 0.8 | 3 | 0.168 | grimble NEAT012 | scope graph | ~GFWC6QP |
| 35 | K33 | Visibility wider than its uses | 0.6 | 0.7 | 3 | 0.141 | grimble-arch VIS001; bind rustc unreachable_pub | visibility + references_to with Bounds | N13 |
| 36 | K21 | Platform portability (host paths, OS assumptions) | 0.68 | 0.8 | 5 | 0.109 | grimble PATH | syntax + const_value | ~21PHK3V |
| 37 | W04 | Route component or heavy dependency imported eagerly into the entry bu | 0.53 | 0.6 | 3 | 0.106 | grimble-websec WEBPERF-server/ROUTE over gob-frameworks rout | structure (route table + imports) | N22 |
| 38 | K28 | Wrong or swapped argument at a call site | 0.61 | 0.5 | 3 | 0.102 | grimble NEAT022 (declaration side); call-site name-mismatch  | types | later (NEAT022) |
| 39 | W07 | Network data cast to a type without validation (res.json() as T) | 0.38 | 0.7 | 3 | 0.087 | grimble (types capability) Advisory | types | N15 |
| 40 | W08 | Secrets in bundles, CSRF, cookie flags, CSP | 0.68 | 0.6 | 5 | 0.081 | grimble-websec | structure/config | ~8998PBE |
| 41 | K10 | One job per function (COH001-004) | 0.61 | 0.6 | 5 | 0.073 | grimble COH | def-use, effects, apply_targets | ~X5ECTEM, ~8GMB58A, ~7T5Y51S, ~BH9BHQ5 |
| 42 | K22 | State initialised or ordered wrongly, two-phase init | 0.52 | 0.5 | 5 | 0.052 | grimble NEAT027 (later); Unity lifecycle rows | effects | later (NEAT027) |
| 43 | W05 | Client route change without title update or focus/announcement | 0.21 | 0.6 | 3 | 0.042 | crunk-web A11Y over routes | effects over route handlers | N23 |

### 2.5 Reading the catalogue

- The largest mined signals are not lintable: logic errors (C42, M 26, 41 percent of escaped
  mistakes), documentation prose (C46, M 9.5), design discussion (C43) and suggestion-only
  comments (C47). Together they are about a third of human review effort (MR 3.1). The lintable
  remainder is dominated by evolvability: dead code, simplification, nesting, duplication,
  naming, types, formatting.
- Bound tools already decide most of the high-E_det rows (K02, K05, K17, K14, K27, K30, K23,
  K39, W01, W02, U01, U04). frob/grimble's own value is concentrated where a single-file linter
  cannot see: cross-file dead code (K03), clones (K16), error handling as a family with one
  policy across languages (K01), paired acquisition and teardown (K26, U05, W03), hot-context
  reach (U02, U03), layering against the declared model (K09), scope of change (K18), doc drift
  (K29) and test reach (K24).
- Escaped UI rendering bugs (F-UI-RENDER, 11.3 percent [8.6-14.7] of mistake fixes, MR 6.2) are
  the second largest escaped class. They support crunk's T1 layout and T2 visual checks (LAYOUT,
  RESP, VIS) far more than the SLOP tells, which have no defect data (DS 0).
- Consensus and frequency disagree for hidden global state (K12: C 2.25, M 0.4), naming
  convention (K14: C 2.25, M 0.7) and boolean flags (K35: C 1.77, M 0.3). These are cheap and
  uncontroversial, so they ship, but they will not move review load much.

## 3. Decisions recommended

### 3.1 Build first (rank by E_det x P / cost; enablers first)

Enablers (no score of their own; every bind row depends on them):
E1 N01 SARIF 2.1.0 parser; E2 N02 cargo JSON parser (clippy, rustc); E3 N03 ruff JSON parser;
E4 N04 ESLint JSON parser; E5 N16 per-rule precision ledger (needed before any new rule defaults
to Warn).

Then, in order (owner; tier):

| # | Row | Item | Owner | Tier | Delivered by |
|---|---|---|---|---|---|
| 1 | K02 | local unused import/variable/parameter | bind rustc/clippy, ruff, ts-eslint, Roslyn -> DEAD | syntax (tool) | N02-N05 |
| 2 | K05 | simplification and idiom groups | bind clippy, ruff SIM/UP/C4, ts-eslint, Roslyn IDE -> LINT | syntax/types (tool) | N02-N05 |
| 3 | K17 | explicit any, unsafe any flow, unchecked casts | bind ts-eslint, ruff ANN401, pyright -> TYPING | types (tool) | N03, N04 |
| 4 | W01 | JSX accessibility (labels, alt, names, roles, keyboard) | bind jsx-a11y -> A11Y (crunk) | syntax (tool) | N04 |
| 5 | W02 | React hooks and render rules | bind react-hooks, eslint-plugin-react -> REACT | structure (tool) | N04 |
| 6 | K27 | formatting | bind formatters -> FMT001 (frob), fix tier A | tool | N07 |
| 7 | K06 | null/boundary: strict type checking | bind checkers + own TYPING001 (grimble) | types; syntax for config | N14, ~7TYG963, ~69D9E89 |
| 8 | K23 | lock across await, floating promise, async void | bind clippy, ruff ASYNC, ts-eslint, VSTHRD -> CONC | types (tool) | N02-N05 |
| 9 | K11 | typos | bind typos -> SPELL001 (frob) | syntax | N06 |
| 10 | U01 | Unity null bypass | bind Microsoft.Unity.Analyzers -> UNITY1xx | types (tool) | N05 |
| 11 | K14 | naming convention | bind ruff N, rustc, IDE1006, ts-eslint -> NAME | syntax (tool) | N02-N05 |
| 12 | K08 | perf micro-idioms (Advisory) | bind clippy perf, ruff PERF, CA18xx -> LINT1xx | types (tool) | N02-N05 |
| 13 | U04 | Unity API idioms (CompareTag, NonAlloc, messages, SerializeField) | bind Unity analyzers + USP suppressors | types (tool) | N05 |
| 14 | K39 | correctness/suspicious groups | bind clippy correctness, ruff B/PLE, eslint, CA -> LOGIC | types (tool) | N02-N05 |
| 15 | K04 | nesting depth (NEAT004) | grimble NEAT | syntax | ~GFWC6QP |
| 16 | K30 | non-exhaustive match | bind clippy, ts-eslint, Roslyn -> NEAT026 | types (tool) | N02-N05 |
| 17 | K01 | swallowed or ignored errors | grimble ERR (own) + bind | syntax; types | N10 |
| 18 | K07 | CI and dependency hygiene | grimble CI, VET | syntax over manifests | ~8886VJ4, ~RPQKHAV |
| 19 | U06 | legacy Input / hard-coded device reads | grimble unity pack | syntax + project settings | N19 |
| 20 | W06 | CSS hygiene (Advisory) | bind stylelint -> crunk | syntax (tool) | N09 |
| 21 | K32 | breaking public API | bind semver checkers -> VERSION001 (frob) | tool (API diff) | N08 |
| 22 | K34 | leftover debug output, commented-out code | bind ruff T20/ERA, eslint, clippy -> LINT | syntax (tool) | N02-N04 |
| 23 | U03 | lookup in hot code | grimble unity pack (own) | structure: hot reach | N17, N18 |
| 24 | K16 | exact and renamed clones | grimble-arch DUP (own) | syntax digests | N12 |
| 25 | K20 | test hygiene (no assertion, sleep, clock) | grimble TESTQ (own) + bind | test_items + vocabulary | N11 |

Next by rank: K03 DEAD cross-file (~1QBHP7T), W03 React effect cleanup (N21), K26 PAIR (~4CESXMT),
U05 Unity paired lifecycle (N20), U02 hot allocation (N18), U07 fixed timestep (N19), K12
NEAT012 (~GFWC6QP), K33 VIS001 (N13), W04 route splitting (N22), W07 boundary cast (N15).
If the owner prefers to build own rules first, order by E_det among own rows: K01 ERR 4.8,
K03 DEAD 4.6, K04 NEAT004 2.8, K16 DUP 2.6, K20 TESTQ 2.6, K26 PAIR 2.1, U02/U03 hot rules 1.8/1.7.

### 3.2 Bind rather than own

Policy: when a maintained tool has a documented rule for the shape, bind it through a
`[[check.tool]]` stage with an id map (rules.md 4) and own only (a) the cross-file or universal
version the model sees better, (b) languages with no such tool, (c) rules needing frob context
(tickets, leases, the grimble model, hot roots). CW 5.6 adds: run type-aware linters in a
separate, slower stage outside the 2 s budget.

| Ecosystem | Tool and rules to bind | Maps to |
|---|---|---|
| Rust | rustc lints (unused_*, dead_code, unused_must_use, unreachable_pub opt-in, non_*_case); clippy groups correctness, suspicious, complexity, style, perf (default) plus opt-in await_holding_lock, wildcard_enum_match_arm, dbg_macro, print_stdout, let_underscore_must_use, cognitive_complexity, too_many_arguments, as_conversions | DEAD, LOGIC, LINT, CONC, NEAT002/005/026, ERR002, VIS001, NAME |
| Python | ruff F401/F841/ARG (DEAD), N8xx (NAME), SIM/UP/C4/PIE/RET (LINT), PERF (LINT1xx), B/PLE/PLW (LOGIC), BLE001/E722/S110/TRY (ERR), ASYNC (CONC), PT (TESTQ), T20/ERA001 (LINT5xx debug), S (SEC), ANN401 (TYPING), C901/PLR0913 (NEAT005/002); PLR2004 off; ty or pyright for types (~7TYG963) | as listed |
| TypeScript/JS | ESLint core (no-unused-vars, no-constant-binary-expression, no-self-compare, no-dupe-else-if, no-console, no-debugger, no-implied-eval, complexity); typescript-eslint (no-floating-promises, no-misused-promises, no-explicit-any, no-unsafe-*, switch-exhaustiveness-check, naming-convention; type-aware stage); eslint-plugin-jsx-a11y (recommended); eslint-plugin-react-hooks (rules-of-hooks, exhaustive-deps, v6 compiler lints); eslint-plugin-react (no-array-index-key, no-danger, button-has-type, no-direct-mutation-state); testing-library, jest or vitest plugins; tsc --strict (~69D9E89) | DEAD, LOGIC, CONC, TYPING, NEAT026, NAME, A11Y, REACT, TESTQ, SEC |
| C# / .NET | Roslyn IDE (IDE0051/52/60 unused, IDE1006 naming via .editorconfig, IDE0010/0072 exhaustive), CA rules (CA1031 catch-all, CA1806 ignored result, CA2000 dispose, CA18xx perf, CA2245), nullable warnings CS86xx with Nullable enable; Microsoft.VisualStudio.Threading.Analyzers (VSTHRD002/100/103/110); Microsoft.CodeAnalysis.PublicApiAnalyzers (RS0016/17) | DEAD, NAME, NEAT026, ERR, PAIR, LINT1xx, LOGIC, CONC, VERSION001 |
| Unity | Microsoft.Unity.Analyzers UNT rules (UNT0001 empty message, 0002 CompareTag, 0006 wrong signature, 0007/0008/0023/0029 null bypass, 0010/0011 new MonoBehaviour/ScriptableObject, 0012 coroutine not started, 0013 SerializeField, 0016 string Invoke, 0024/0026/0028 allocation and NonAlloc, 0038 cached WaitForSeconds, 0041/0046 property ids) and its USP suppressor set, so stock IDE rules stop firing on engine-called messages and serialized fields | UNITY1xx, plus suppressions |
| CSS | stylelint (no-descending-specificity, selector-max-id, selector-max-compound-selectors; declaration-no-important Advisory) | crunk ids |
| Text | typos (crate-ci), honouring typos.toml | SPELL001 |
| Formatters | rustfmt, ruff format, prettier, dotnet format or csharpier, gofmt, clang-format, all in check mode | FMT001 (fix tier A) |
| Public API | cargo-semver-checks, PublicApiAnalyzers, api-extractor, griffe | VERSION001 |
| CI | zizmor, actionlint (bound, ~XX6K71R done) | CI |

A native suppression of a bound rule without a frob exception is EXC017 (~B7VH1B4); CW lists
eslint-disable abuse as a consensus smell, so EXC017 should land with the first bind profile.

### 3.3 Do not lint (and why)

| Item | Evidence | Disposition |
|---|---|---|
| Function length (NEAT001 low limits) | C21 0.5 percent, 0 percent blocking (MR 3.6); contested CS ADV101 (Martin, Fowler, Metz vs Ousterhout, Google, matklad, Wayne), opposed in hot code CG GADV325 (Carmack, Muratori) | NEAT001 stays bound-only, Advisory, high default; never claim evidence for a low limit |
| Comment policy: comment ratio, redundant comments, mandatory why-comments | C07 and C08 0.5 percent each, 0 percent blocking; contested CS ADV052 | keep DOC001 (public docs exist) and NARR only |
| Name length and abbreviation rules | contested CS ADV043; Wayne cites a controlled study with no fault-finding difference | no rule; naming convention only through bound tools |
| Unclear or misleading names | C13 4.4 percent but human tier (CS ADV027, CG GADV028) | review, not lint |
| Raw loops in general (NEAT006 as written) | contested CS ADV007 (Parent vs Sutter, Pike, Boccara) | only loops whose body matches a known algorithm shape, Advisory |
| Duplication below three occurrences or near-miss abstractions | contested CS ADV120, CW WADV087 (Metz, Cheney, Bloch, Dorfmeister) | DUP exact/renamed clones only, Advisory |
| Magic numbers in general | C18 1.2 percent; high FP; CG Insomniac split | off; own only colour (COLOR001) and path (PATH001) literals |
| Coverage percentage targets, test pyramid shape, mock counting | contested CS ADV104, ADV112, ADV055 | reach (COV001) and changed-line evidence only |
| Exceptions vs Result, auto/var, pass by value, forward declarations, DI containers, single exit | contested CS 4.2-4.3 | per-language policy knobs, not rules |
| Premature memoization, god components, double-submit by disabled button, CSS !important, real browser for tests | contested CW 4.2 | off or Advisory |
| Logging level and volume | C39 0.8 percent, human; Chromium and Linux style guides conflict with the owner's log-everything rule (CS 4.2) | no rule; secrets in logs stay in SEC |
| Documentation prose quality | C46 8.9 percent but human | typos and links only |
| Design choices: ECS vs OOP, enum switch vs State pattern, event bus vs direct calls | contested CG C01, C09, C10 | review |
| Zero allocation as a global target; LINQ or foreach outside hot code; UNT0005 deltaTime in FixedUpdate | CG C14, C07, C06 (version-bound), C13 (retired upstream) | only under hot context, Advisory; type-keyed, version-gated |
| Whole-screen colour-blind filters | opposed by GAG (CG C12) | lint colour-only meaning instead |
| SLOP tells as blocking | no defect data (DS 0); tells decay | Advisory only, as DS 6 and ~10FRR8N already say |

### 3.4 What the AI-reviewer comparison implies for frob

- AI reviewers spend 68.6 percent of their comments on functional defects vs 29.0 percent for
  humans, and over-flag LOGIC-BUG (4.6x), SECURITY (3.5x), CONCURRENCY (3.1x), EDGE-CASE (2.8x),
  ERROR-HANDLING (2.7x) (MR 4.1). Their threads are resolved at the human rate but the commented
  line changes less often (outdated 56 vs 75 percent): a lower acted-on rate, consistent with
  plausible but often wrong defect hypotheses. frob should not compete there with heuristics;
  its answer is evidence (tests that reach the change, COV001, TEST binding) and honest
  Unresolved instead of guesses.
- Humans flag what AI reviewers miss: DESIGN-STRUCTURE (AI/human 0.2), SIMPLIFY-IDIOM (0.2),
  SCOPE-PROCESS (0.3), MAGIC-CONFIG (0.3), NAMING (0.4), DEAD-CODE (0.5), DUPLICATION (0.6),
  DOC-COMMENT (0.7), FORMAT-STYLE (0.7), API-COMPAT (0.7). These need project context or taste.
- Mechanically checkable among them, with the frob/grimble mechanism:
  dead code (bound unused + DEAD cross-file over references_to, K02/K03), simplification and
  idiom (bound groups, K05), duplication (DUP exact clones, K16), naming convention (bound,
  K14), formatting (FMT, K27), scope of change (SCOPE001 against the ticket lease: no AI reviewer
  has the lease, K18), design structure against a declared model (SYS004, ARCH layering, K09),
  API compatibility (VERSION001 from semver checkers, K32), doc staleness (DRIFT, K29), and
  project conventions (GPOL policy rules written in GRL, MR C44). Magic values are checkable
  only in their colour and path forms.
- Not checkable: design judgement, unclear names, PR splitting advice, docs wording. Here frob's
  value is process: the ticket, the lease and the evidence make the reviewer's question
  ("why is this here, what tests it") answerable without a comment.
- On AI-authored PRs humans flag more concurrency, dependency/build, error handling, consistency,
  test and scope problems (MR 4.2). frob already enforces scope (SCOPE001), test reach and
  evidence; the gaps the study exposes are ERR (N10), bound concurrency rules (N02-N05), VET
  (~RPQKHAV) and test hygiene (N11). These are the agent-facing priorities.

### 3.5 Family names for the new rows (for the coordinator to confirm)

Own families: ERR (error handling, grimble-lints), TESTQ (test-body hygiene, grimble-lints),
PAIR (acquire/release on teardown paths, grimble-lints), VIS (visibility vs uses, grimble-arch),
TYPING (type strictness and boundary casts, grimble-lints; not TYPE, which is crunk's
typography family). Bound-only families: FMT and SPELL (frob, frob-check registry), NAME and LINT
(grimble namespace; LINT ranges 0xx idiom, 1xx perf idiom, 2xx correctness, 3xx concurrency,
5xx leftover debug; CONC may be split out of LINT3xx if the owner prefers), REACT (grimble web
pack), UNITY1xx (bound Unity analyzers; UNITY0xx stays .meta/GUID, UNITY2xx own hot-context,
UNITY3xx input and physics). Check before allocating: v1 FMT001/FMT002 were directive-format ids
folded into PARSE (lint-requirements R14); docs/migration/rule-ids.md must not alias them to the
new FMT001. v2 PERF001 is engine timing (R27), hence LINT1xx rather than PERF for bound perf.

## 4. Proposed tickets (new items only)

Evidence lines cite the staged files by name; they move to notes/research/ with this catalogue.
Points use 1/2/3/5/8. Scopes are crate globs (new crates named by the design: grimble-lints,
grimble-arch, grimble-websec). All tickets also take changelog.d/** as in file-batch4.sh.

### 4.1 New epic

EB "Bind before own: tool-stage parsers and id maps for the evidence-ranked external linters"
(parent ~0BTGRT5, priority high). Outcome: the top-ranked rows of the catalogue arrive as frob
findings with frob ids, severities and exceptions, before any re-implementation.

### 4.2 Tickets

| Id | Title | Parent | Pri | Pts | Scope | Evidence (body) | Acceptance (Given/When/Then) |
|---|---|---|---|---|---|---|---|
| N01 | gob-check: SARIF 2.1.0 tool parser with a per-tool id map and source_rule | EB | high | 3 | crates/gob-check/** | catalogue 3.1 E1; enables U01, U04, K32 (Roslyn, Unity analyzers, PublicApiAnalyzers emit SARIF); rules.md 4 | Given a SARIF log with results, suppressions and an unknown ruleId, when the stage runs, then mapped results become frob findings with source_rule, suppressed results are visible to EXC017, the unknown id falls back to TOOL002 and unreadable output is a required TOOL001 Unresolved |
| N02 | gob-check: cargo JSON diagnostics parser for rustc and clippy with the Rust id map | EB | high | 3 | crates/gob-check/**, frob.toml | catalogue rows K02, K05, K08, K14, K23, K30, K39; MR 3.6 C02/C16/C17; the cargo clippy stage today is pass/fail only | Given cargo clippy --message-format=json output, when the stage runs, then unused_* map to DEAD, too_many_arguments to NEAT002, the correctness group to LOGIC and unmapped lints to LINT with source_rule; given this repository, then frob check reports the same counts as cargo clippy |
| N03 | Python profile: ruff JSON parser, id map and frob init stage template | EB | high | 3 | crates/gob-check/**, crates/frob/** | rows K02, K05, K14, K17, K20, K23, K34, K39; MR 3.4 Python strata | Given ruff check --output-format=json output, when parsed, then F401 maps to DEAD, BLE001/E722/S110 to ERR, ASYNC to CONC, PT to TESTQ and PLR2004 is off; given frob init in a pyproject repository, then the stage is written with a pinned version range |
| N04 | Web profile: ESLint JSON parser; stages for eslint, typescript-eslint (type-aware, separate), jsx-a11y, react-hooks, eslint-plugin-react | EB | high | 5 | crates/gob-check/**, crates/frob/** | rows W01 (CW WADV001-005, score 7-9), W02 (WADV002/008/038/059), K17, K23; CW 5.6 type-aware stage outside the 2 s budget | Given eslint -f json output, when parsed, then jsx-a11y ids map to A11Y, react-hooks to REACT, no-floating-promises to CONC and no-explicit-any to TYPING; given the type-aware stage, when frob check runs, then its time is reported separately and outside the check budget |
| N05 | .NET and Unity profile: dotnet build SARIF with Roslyn CA/IDE, VSTHRD and Microsoft.Unity.Analyzers, USP suppressors on | ~GJVPDC0 | high | 5 | crates/gob-check/**, crates/frob/** | rows U01 (CG GADV012, rank 1 in CG 5.1), U04 (GADV017/022-030/037/041/042), K02, K14, K23; CG 5.6 rules plus suppressions | Given a Unity fixture with a ?. on a MonoBehaviour field and an empty Update, when frob check runs the dotnet stage, then UNITY findings appear with source_rule UNT0008 and UNT0001; given an engine-called private message, then no IDE0051 dead-code finding is reported |
| N06 | typos JSON parser mapped to SPELL001 (Advisory) honouring typos.toml | EB | medium | 2 | crates/gob-check/**, crates/frob/** | row K11: MR C09 1.9 percent of review comments, F-DOC-TYPO 9.2 percent of fix commits; typos already runs pass/fail in cargo dev ci (~19X37CZ) | Given typos --format json output, when parsed, then each typo is a SPELL001 finding with the correction in the remedy; given an allowlisted word in typos.toml, then no finding |
| N07 | Formatter check stages mapped to FMT001 with a tier A fix that runs the formatter within the ticket scope | EB | medium | 3 | crates/gob-check/**, crates/frob/** | row K27: MR C12 2.7 percent, 67 percent nit; CS ADV017/ADV026 automate, do not discuss | Given rustfmt, ruff format, prettier and dotnet format in check mode reporting a file, when frob check runs, then one FMT001 per file is reported; when frob check --fix --ticket runs, then only files inside the ticket scope are rewritten |
| N08 | Public API checkers mapped to VERSION001: cargo-semver-checks, PublicApiAnalyzers, api-extractor, griffe | EB | medium | 3 | crates/gob-check/**, crates/frob-obligations/** | row K32: MR C35 67 percent blocking; CS ADV012 (Hyrum), ADV023 | Given a removed public function and an unchanged version, when frob check --base runs the semver stage, then VERSION001 is an Error naming the item; given a major bump, then no finding |
| N09 | stylelint JSON parser and crunk id map for generic CSS hygiene (Advisory) | ~X0SN72M | low | 2 | crates/gob-check/**, crates/crunk-check/** | row W06: CW WADV025/031 (6 and 5 voices), WADV051 contested | Given stylelint --formatter json output, when crunk check runs the stage, then findings carry crunk ids and declaration-no-important is Advisory |
| N10 | ERR001-ERR003: empty error handler, discarded fallible result, catch-all that neither rethrows nor logs | ~0BTGRT5 | high | 5 | crates/grimble-lints/**, crates/gob-ir/** | row K01: MR C30 2.5 percent, 29 percent blocking, F-ERROR-HANDLING; CS ADV015/049 (only data-backed family: Yuan et al. via Luu, 92 percent of catastrophic failures from mishandled errors); AI-PR ratio 1.6; supersedes the v2 need behind ~0FPQXHD | Given Rust, Python, TS and C# fixtures with an empty catch, let _ = on a Result, except: pass and catch (Exception) {} , when grimble check runs, then each fires once; given a handler that logs or rethrows, then clean; given a callee whose fallibility is Unknown, then ERR002 is Unresolved, never Warn |
| N11 | TESTQ001-TESTQ003: test without assertion, sleep or wall clock or unseeded rng in a test, control flow in a test body (Advisory) | ~0BTGRT5 | medium | 5 | crates/grimble-lints/**, crates/gob-ir/** | row K20: MR C28 0.9 percent with 28 percent blocking, F-TEST 4.5 percent; CS ADV060/082/096, CW WADV010; Google flakiness data (CS 5.1 rank 9); AI-PR ratio 1.5 | Given a test item with no assertion-vocabulary call and no helper that may assert, when checked, then TESTQ001 fires; given a helper whose body is Unknown, then Unresolved; given time.sleep or thread::sleep in a test, then TESTQ002; TESTQ003 is off by default |
| N12 | DUP R1-R3 in grimble-arch: exact and alpha-renamed token clones above min_tokens with three or more occurrences (Advisory) | ~0BTGRT5 | medium | 5 | crates/grimble-arch/** | row K16: MR C03 2.2 percent, R-DUPLICATION 7.9 percent of refactors; CS ADV018 (10.5); threshold contested (ADV120, WADV087) | Given three copies of a 60-token block in two languages, when grimble check runs, then one DUP finding lists all sites; given two copies, then no finding at the default min_occurrences = 3 |
| N13 | VIS001: item visibility wider than its uses (Advisory), binding rustc unreachable_pub where present | ~0BTGRT5 | low | 3 | crates/grimble-arch/** | row K33: MR C19 0.5 percent; ManySStuBs CHANGE_MODIFIER 7.8 percent of Java one-statement fixes; CS ADV023, ADV020 | Given a pub item whose references_to hi set lies inside its own package, when checked, then VIS001 fires; given an Unknown edge from outside, then Unresolved; given an item re-exported from the crate root, then clean |
| N14 | TYPING001: strict null or type checking disabled in project configuration (tsconfig, csproj Nullable, pyright/ty/mypy settings) | ~VDX2WPZ | medium | 2 | crates/grimble-lints/**, crates/gob-symbols/** | row K06: MR C29 2.9 percent, 40 percent blocking, F-NULL-EDGE 8.1 percent of escaped mistakes; cohesion.md 2.2 types that lie | Given a tsconfig with strict false or a csproj without Nullable enable, when grimble check runs, then TYPING001 is Advisory with the exact key to set; given strict settings, then clean and [types] trust may be checked |
| N15 | TYPING004: network or file data cast to a declared type without validation (res.json() as T, json.loads into a TypedDict) (Advisory) | ~VDX2WPZ | low | 3 | crates/grimble-lints/**, crates/gob-ir/** | row W07: CW 5.2 item 10 (Zod docs, Pocock); MR TYPE-SAFETY | Given await res.json() as User with no parse call on the value, when checked, then TYPING004 fires; given schema.parse(await res.json()), then clean |
| N16 | Rule precision ledger: per-rule accept, waive, dismiss and fix counts and a not-useful rate in check --json and explain; Warn-by-default needs measured precision | ~0BTGRT5 | high | 3 | crates/gob-rules/**, crates/gob-check/** | CS 5.2 (Tricorder: not-useful rate cut from 80 to about 15 percent by tuning); ~GR4ZPYH measured about 5 percent true positives for v1 web rules; DS 4.8 verdict eval loop | Given exceptions and fixes recorded for a rule over a window, when frob check --json runs, then the rule reports its counts and not-useful rate; given a rule above the configured not-useful ceiling, then doctor recommends demotion |
| N17 | hot-context capability: region reachable (Must/May) from vocabulary-declared hot roots; Unknown edges give Unresolved | ~GJVPDC0 | high | 5 | crates/gob-ir/**, crates/gob-symbols/**, crates/gob-caps/** | rows U02, U03 (CG 5.1 ranks 2-3: Unity docs, MS analyzers, JetBrains performance-critical context, Dunstan); JetBrains' hot context is IDE-only, so this is frob-only value | Given a MonoBehaviour whose Update calls a helper that calls GetComponent, when hot(region) is queried, then the helper call is Must-hot; given a call through an interface with unknown targets, then May; given the unity pack disabled, then NotApplicable |
| N18 | UNITY2xx hot-path rules: lookup in hot code (GetComponent, Find*, Camera.main) and managed allocation in hot code, Advisory | ~GJVPDC0 | medium | 5 | crates/grimble-lints/**, crates/gob-ir/** | rows U02, U03: CG GADV009 (3.5 voices, Dunstan measured), GADV010 (3.5); contested as a global target (CG C14), hence hot-context gated and Advisory | Given GetComponent<T>() in a method reachable from Update, when checked, then UNITY201 is Advisory with the cache-in-Awake remedy; given the same call in Awake, then clean; given new List<T>() in FixedUpdate, then UNITY202 |
| N19 | UNITY3xx input and physics rules: legacy Input/KeyCode in an Input System project; Rigidbody forces or Transform moves of a Rigidbody in Update | ~GJVPDC0 | medium | 3 | crates/grimble-lints/**, crates/gob-ir/** | rows U06 (CG GADV004/005, 4-4.5 voices, GAG remap is basic tier), U07 (GADV002 fixed timestep, 5.5 voices; UNT0004 covers only fixedDeltaTime in Update) | Given activeInputHandler set to the Input System and Input.GetKey(KeyCode.Space) in code, when checked, then UNITY301 fires; given Rigidbody.AddForce in Update, then UNITY302; given the same in FixedUpdate, then clean |
| N20 | PAIR001 Unity vocabulary: += in OnEnable without -= in OnDisable or OnDestroy, RegisterCallback, Input action Enable/Disable, Addressables Load/Release | ~GJVPDC0 | medium | 2 | crates/gob-ir/** | row U05: CG GADV031 (Nystrom lapsed listener, Hipple, Unity docs), GADV079; depends on the re-scoped ~4CESXMT | Given event += in OnEnable and no -= on any teardown root, when checked, then PAIR001 fires naming both sites; given a lambda subscription, then Unresolved |
| N21 | PAIR001 React vocabulary: useEffect that starts fetch, setInterval/setTimeout, addEventListener or subscribe without a returned cleanup or AbortController | ~N134SE7 | medium | 2 | crates/gob-ir/**, crates/gob-frameworks/** | row W03: CW WADV013 (6 voices: Abramov, React docs, Remix, Solid, Svelte, Vue), no ESLint rule exists (CW 5.2 item 1); depends on ~4CESXMT | Given useEffect(() => { const id = setInterval(f, 100) }, []), when checked, then PAIR001 fires; given a returned clearInterval, then clean |
| N22 | Route component or heavy dependency imported eagerly into the entry bundle (Advisory), over gob-frameworks routes and the import graph | ~N134SE7 | low | 3 | crates/grimble-websec/**, crates/gob-frameworks/** | row W04: CW WADV006 (7 voices incl. Web Almanac data); no linter does route-aware checks (CW 5.2 item 2) | Given a react-router route whose component is imported statically from the entry module, when checked, then the finding names the route; given lazy(() => import(...)), then clean |
| N23 | Client route change without document.title update or focus move/announcement (crunk-web A11Y, Advisory) | ~N134SE7 | low | 3 | crates/crunk-check/**, crates/gob-frameworks/** | row W05: CW WADV045, WADV058 (Sutton, O'Hara, Pickering, de Vries, W3C); hullbreach applies (CW 5.3) | Given routes that render without setting the title or moving focus, when crunk check runs, then one finding per route; given a route-level title and focus handler, then clean |
| N24 | GX catalogue additions: separate volume channels, haptics toggle, time limits scalable to 10x, subtitle 2 lines and 38-40 characters, text baked into images, Unicode glyph icons | ~APVX45C | low | 2 | crates/crunk-spec/**, crates/crunk-check/** | CG 5.2 observation (two or more voices each: GAG, XAG, IGDA); not in the crunk.md 6 GX row | Given gx-a11y.toml coverage keys, when crunk check runs on a game profile lacking a volume-channel declaration, then a GX finding names the guideline; given every key declared, then clean |
| N25 | Apply the lint-catalogue-2026-10-08 design changes (section 5) to rules.md, boundaries.md, neatness.md, cohesion.md, crunk.md, dotnet-unity.md, universal-model.md, plugins.md, rule-authoring.md, lint-requirements.md | ~WY08EWT | high | 2 | docs/design/**, notes/research/** | catalogue section 5 | Given the change list, when the docs are updated, then each listed section carries the change, frob check reports no DRIFT or SYNC finding, and the new families appear in the boundaries.md 2.5 table |

Counts by parent: EB (new epic) 7 (N01-N04, N06-N08); ~GJVPDC0 5 (N05, N17-N20);
~0BTGRT5 5 (N10-N13, N16); ~VDX2WPZ 2 (N14, N15); ~N134SE7 3 (N21-N23); ~X0SN72M 1 (N09);
~APVX45C 1 (N24, crunk phase 6, inside the crunk tree); ~WY08EWT 1 (N25). Total 25 plus 1 epic.

### 4.3 Updates to existing tickets (not new; in the script as comments and updates)

- ~4CESXMT (v1 wording, "unpaired resource acquisition: known acquire/release API table"):
  re-scope to v2 PAIR001 in grimble-lints, universal over U with per-language vocabulary packs,
  P+ on a Must acquisition with no release on any teardown root, Unresolved when the handle
  escapes; re-parent to ~0BTGRT5, priority medium. Evidence: row K26 (CS ADV008 12 voices,
  CG GADV031, CW WADV013; MR C31 60 percent blocking).
- ~0FPQXHD (v1 consumer audit, empty catch with no logging): comment that N10 is the v2 rule.
- ~QY70Q62 (LAYOUT and RESP at T1) and ~R149H7C (VIS): comment with F-UI-RENDER 11.3 percent of
  escaped mistakes (MR 6.2); raise ~QY70Q62 to high.
- ~10FRR8N (SLOP T0): comment that DS has no defect data; keep Advisory and never gating.
- ~SHGXWRT (crunk-web A11Y in GRL): comment: bind jsx-a11y for JSX/TSX (N04); write GRL only for
  HTML, Vue, USS and cross-file rules.
- ~GFWC6QP (NEAT first ten): comment with the evidence order NEAT004 (K04 E_det 2.8), NEAT003,
  NEAT012 (consensus high, mined low), NEAT031, NEAT030; NEAT006 and NEAT007 have the weakest
  support (ADV007 contested; no source for section comments beyond Smith).
- ~1QBHP7T (CYCLE, LARGE, DEAD): comment that local unused findings come from bound tools
  (N02-N05) and DEAD here is the cross-file rule.
- ~GR4ZPYH (v1 web precision pass, about 5 percent true positives): comment linking N16.

## 5. Design-doc changes for the coordinator

1. rules.md 1 and 4: state the bind-before-own policy (3.2) with the three own conditions; add
   the parser list (SARIF 2.1.0, cargo JSON, ruff JSON, ESLint JSON, typos JSON, formatter check
   mode, stylelint JSON); correct the owner of tool parsers: they live in
   crates/gob-check/src/tool_parse.rs, not frob-check; say type-aware linters run as a separate
   stage outside the 2 s budget; add a "precision before Warn" rule: a new rule ships Advisory
   until the precision ledger (N16) shows its not-useful rate under the ceiling.
2. rules.md 3 family table and boundaries.md 2.5: add rows ERR, TESTQ, PAIR, TYPING
   (grimble-lints), VIS (grimble-arch), FMT and SPELL (frob, frob-check registry, bound only),
   NAME and LINT with ranges (grimble, bound only), REACT (grimble web pack), UNITY1xx-3xx
   ranges (unity pack); note the FMT v1 id collision check and that bound perf idioms are LINT1xx
   because PERF001 is engine timing.
3. neatness.md 4: add an evidence column (catalogue E_det and C) and re-order "first ten" by
   evidence (NEAT004, NEAT003, NEAT012, NEAT031, NEAT030 before NEAT006/NEAT007); mark NEAT001,
   NEAT006 and NEAT009 contested or low-evidence (Advisory, bound only). Fix the numbering split:
   the design table names NEAT026 exhaustive-match while notes/research/neatness.md 6 names
   NEAT026 must-use-missing and NEAT041 enum-glob-in-match; MR used the design numbering.
4. cohesion.md 1: COH has weak support (5 voices, no data; C21 0.5 percent, C23 0.4 percent of
   review comments); change COH001-003 from Warn by default to Advisory until measured precision
   (N16), keeping the Bounds design unchanged.
5. universal-model.md 4.4: add capabilities `hot(region)` (reach from vocabulary-declared hot
   roots with Bounds; N17), `teardown_roots` (lifecycle exits for PAIR: Drop, using/Dispose,
   OnDisable/OnDestroy, effect cleanup, defer) and a `fallible(apply)` answer under type_of for
   ERR002 (does the callee return an error-carrying type: Exact, May, Unknown).
6. dotnet-unity.md 3 and 5: add step 3b "bind Roslyn and Microsoft.Unity.Analyzers through dotnet
   build SARIF with the USP suppressor set" before own Unity rules; add the UNITY ranges, the hot
   context, and a version gate read from ProjectSettings/ProjectVersion.txt (Find* and foreach
   behaviour changed across versions, CG 5.6).
7. crunk.md 6 and 9: A11Y row: JSX/TSX through bound jsx-a11y, GRL for HTML/Vue/USS and
   cross-file; GX row: add the N24 items; build order: put T1 LAYOUT/RESP and VIS ahead of SLOP
   with the F-UI-RENDER evidence; SLOP stays Advisory (as DS 6 already says).
8. plugins.md 4 and 10: record that tool id maps and default configurations are pack content
   (vocabulary packs carry the map from tool ids to frob ids), so a third party can bind a new
   linter without a release.
9. rule-authoring.md 2: add a required `evidence` field (or an Evidence section in the rule page)
   naming the catalogue row and its E_det, and require `default = off | advisory` for rules whose
   row is contested (C = 0.5).
10. lint-requirements.md 2: add rows R38 ERR, R39 TESTQ, R40 PAIR (relates to R20 PROTO), R41
    VIS, R42 TYPING with their facts; note under R33 that lexical perf is bound (LINT1xx) and the
    own perf rules need hot context.
11. lint-evidence-study.md: append the method of section 1 as the synthesis method actually used
    (formula, weights, discounts) so a rerun with new mining data is mechanical.
