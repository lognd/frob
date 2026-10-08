# Lint evidence study, Strand A: repository mining report (2026-10-08)

Miner: Claude agent (Sonnet 5.5). Code and data pipeline: ~/projects/goblin-mining (git, uv, SQLite; raw JSON under data/ is git-ignored).
All numbers below are produced by that pipeline from GitHub data fetched on 2026-10-08. Where a claim is not from the pipeline it carries a citation or [unsourced].

## 0. Honesty block

### 0.1 Denominators

- Universe: 2688 candidate repositories examined; **1005 included** (95 curated, 910 from the star ranking). Selection query: GitHub REST `search/repositories` with `language:"L" stars:>300 archived:false fork:false sort:stars`, top 200 per language for 13 languages (Rust, Python, TypeScript, JavaScript, C#, Go, Java, Kotlin, C, C++, Ruby, PHP, Swift), plus a topic query for Unity (`topic:unity|unity3d language:C#`), plus 95 curated well-reviewed projects (rust-lang, CPython, TypeScript, Roslyn, Kubernetes, React, Django, LLVM and others; list in src/goblin_mining/curated.py). Queried 2026-10-08. Per-language quotas then applied (Rust 80, Python 100, TypeScript 90, JavaScript 80, C# 80, Go 90, Java 80, Kotlin 40, C 60, C++ 80, Ruby 40, PHP 50, Swift 40); realised counts below. universe.csv lists every candidate with status and exclusion reason.
| primary language | included repos |
|---|---|
| Python | 113 |
| Go | 102 |
| TypeScript | 98 |
| Rust | 94 |
| C++ | 90 |
| JavaScript | 87 |
| C# | 87 |
| Java | 86 |
| C | 63 |
| PHP | 54 |
| Ruby | 45 |
| Swift | 43 |
| Kotlin | 41 |
| LLVM | 1 |
| Groovy | 1 |

Exclusions (of 1683 candidates not included):

| reason | repos |
|---|---|
| fewer than 30 merged PRs in window (mirror/no-PR/dormant) | 809 |
| beyond per-language quota | 531 |
| list/tutorial/book heuristic | 343 |

- PRs: **39,849 closed PRs** (merged 29,181) from 1005 repositories, created 2024-10-08 to 2026-10-08, **cap 40 per repo chosen as the most-commented** (GitHub search `sort:comments-desc`, bot authors dependabot/renovate/github-actions excluded). This sample is biased toward contentious PRs; absolute rates of CHANGES_REQUESTED and of comments per PR are NOT population rates, category shares are the object of study.
- Review comments: **584,692** fetched (first 3 comments of up to 30 threads per PR; PRs with more threads are truncated); **371,362 thread-opening comments**. By author type (all comments): ai_reviewer 155,072, bot 13,979, human 415,641.
- AI-authored PRs detected: **2,636** of 39,849 (6.6%); basis: body-marker 1185, branch 967, login 484.
- Labelled by careful reading (one labeller, the miner agent): **4,980 review comments** = 4,203 human comments on non-AI PRs (the primary sample), 427 AI-reviewer comments, 350 human comments on AI-authored PRs; plus a 300-comment pilot used for open coding of the codebook (labels/pilot_*.txt, not used in estimates); **1,600 refactor/fix/revert commits**.
- Primary frequencies and the candidate ranking use HUMAN comments on non-AI-authored PRs only (coordinator instruction 2026-10-08).

### 0.2 Reliability and validity

- Second labelling, same labeller, 498 comments (10 percent, random, relabelled from the text without displaying the first label): exact agreement 95.4 percent, Cohen's kappa 0.951 on 30 categories (0.941 on 4 coarse groups, 0.974 on severity). **This is NOT independent**: the first labels were in my context window, so this is an upper bound (intra-rater, memory-contaminated).
- Independent check: a fresh-context Sonnet subagent labelled 250 of those comments from the codebook alone (it saw no labels, no database): exact agreement with my first pass 76.8 percent, **Cohen's kappa 0.756** (30 categories), 0.744 (4 coarse groups), 0.683 (severity mark). Main disagreements: DEAD-CODE vs SUGGESTION-ONLY, TEST-QUALITY vs QUESTION-UNDERSTAND, DESIGN-STRUCTURE vs ALTERNATIVE-DISCUSS. Both labellers are language models; no human annotator took part. Treat category shares as model-judged, with kappa about 0.75.
- Local classifier (TF-IDF words+chars, logistic regression, repo-grouped 5-fold CV over 4980 labelled comments): accuracy 44.5% all strata, **44.2% on the human stratum** (majority-class baseline 8.9%), macro-F1 0.378; accuracy on the 4 coarse groups (human) 64.3%. It is a weak classifier. Extrapolation therefore uses a DESIGN-BASED estimator on the labelled sample (post-stratified to the population by repo language x PR-has-CHANGES_REQUESTED, 95 percent CI by repo-cluster bootstrap, 300 resamples); the classifier is used as a cross-check only. The adjusted classify-and-count (confusion-matrix inversion) was tried and rejected: unstable for small classes (e.g. SECURITY 0.4 percent raw vs 3.4 percent adjusted).
- Cross-corpus check: the same model trained on the human stratum applied to 8,006 CodeReviewer review comments (Li et al. 2022, test split, nine languages, 209 projects; ids repeat so 8,006 of 10,169 rows are distinct) gives evolvability 50.5%, functional 26.9%, testing 5.2%, other 17.4%; mined corpus (post-stratified): evolvability 49.4%, functional 29.0%, testing 4.3%, other 17.3%.
- AI-comment detection: author type from account (Bot typename or login regex over known AI-review apps: copilot, coderabbit, codex connector, cubic, greptile, cursor/bugbot, gemini-code-assist, devin, sourcery, codeant, augment, ...) plus a text heuristic (template markers such as robot emoji, [P1], diffray, 'Should Fix', 'AI-Generated Review') for unlabelled accounts. Text heuristic: on 40,000 comments from login-identified AI reviewers it fires on 29.4% (recall of the text rule alone is low; the login rule carries detection). Precision of the text rule: I read 50 random text-basis comments and judged all 50 machine-generated or machine-assisted. Residual leak: 37 of the 4,203 human-stratum sample comments (0.9%) carried an AI-review template that neither rule caught; not removed (flagged in rationale). AI-authored PR detection (login, branch prefix such as copilot/ codex/ claude/, body marker such as 'Generated with Claude Code') has no recall measure.
- Language of a comment is the language of the commented file (extension map), not the repo's primary language; domain is a keyword heuristic over repo name, description and topics (10 domains + other) and is unvalidated.
- Commit signals: GitHub commit search (30 requests/min, 100 results per query) for the words refactor, cleanup, revert, fix, committer-date >= 2024-10-08, non-merge. Scanned 788 of 1005 repositories before the time box (141,730 commits retained; first 440 repos in star order, the rest random order, so the unscanned remainder is a random subset of the lower-star repos). Each query returns at most the 100 most recent matches, so repos with many matches are truncated to their latest 100 per word. The word 'fix' is matched anywhere in a message.
- Labels are model judgements about stated intent; commit messages carry intent, not diffs. Murphy-Hill and others (cited in Silva et al. 2016) found commit messages do not reliably indicate refactoring; I measured the false-positive rate of the word 'refactor' on my sample (section 5).
### 0.3 Blocked or not done

- RefactoringMiner / refactoring oracle on a Java subset: not run (needs full clones and a JVM tool run per commit; recorded in TODO.md). Refactoring types below come from message text, not from diff detection.
- BugsInPy and Defects4J: not used (no commit-level category labels in the data); ManySStuBs4J (63,923 single-statement Java bug fixes from 634 projects, Karampatsis and Sutton, Zenodo 3653444) and CodeReviewer used as external evidence instead.
- GH Archive / BigQuery: not used (GraphQL and REST were sufficient).
- Revert-to-original linkage and time-to-fix survival: not done; Q3 uses messages of fix and revert commits, not a reviewed-then-fixed join.
- Severity proxies: reviewer-explicit marks (blocking/nit/question) from my reading, CHANGES_REQUESTED on the PR, and thread resolved/outdated flags. Later revert/fix per category was not measured per category (no join).
- Diff hunks of review comments were not stored (to bound response size), so detectability tiers come from comment text and file extension, not from the code.
- Rate limits: GraphQL points were exhausted once (waited for reset); commit search hit the secondary limit and was slowed; the API's own `used` counters are unreliable in this environment.

### 0.4 Sources fetched in this session (for the codebook seeds)

- Silva, Tsantalis, Valente, 'Why We Refactor? Confessions of GitHub Contributors', FSE 2016, arXiv 1607.02459 (fetched 2026-10-08): 44 motivations for 12 refactoring types; refactoring driven mainly by requirement changes, not code smells; 11 motivations for Extract Method.
- Bacchelli and Bird, 'Expectations, Outcomes, and Challenges of Modern Code Review', ICSE 2013 (PDF fetched 2026-10-08 from sback.it): in a card sort of 200 threads / 570 comments, code improvements 29 percent (165), defects 14 percent (78, of which 65 logic, 6 high-level, 5 security, 3 exception handling), understanding the dominant theme in interviews.
- Sadowski, Soederberg, Church, Sipko, Bacchelli, 'Modern Code Review: A Case Study at Google', ICSE-SEIP 2018 (research.google page fetched 2026-10-08): 12 interviews, 44 survey respondents, 9 million reviewed changes; used for the readability/consistency/design seed categories.
- Maentylae and Lassenius, 'What Types of Defects Are Really Discovered in Code Reviews?', IEEE TSE 35(3), 430-448, 2009, DOI 10.1109/TSE.2008.71 (bibliographic data seen via search results; the evolvability vs functional split and documentation/visual representation/structure subclasses are used as seed categories; their percentages were not re-read here).
- Beller, Bacchelli, Zaidman, Juergens, 'Modern Code Reviews in Open-Source Projects: Which Problems Do They Fix?', MSR 2014, pp. 202-211 (bibliographic data and the headline split about 75 percent maintainability vs 25 percent functional seen via a search-result summary, not re-read in the paper; treat the numbers as secondhand).
- AlOmar, Mkaouer, Ouni, 'Can refactoring be self-affirmed? An exploratory study on how developers document their refactoring activities in commit messages', IWoR 2019, pp. 51-58 (bibliographic data via search results); used for the idea of classifying self-affirmed refactoring from messages.
- Li et al., 'Automating Code Review Activities by Large-Scale Pre-Training' (CodeReviewer), Zenodo 6900648, 2022 (Comment_Generation test split downloaded and analysed).
- Karampatsis and Sutton, 'How Often Do Single-Statement Bugs Occur? The ManySStuBs4J Dataset', MSR 2020, Zenodo 3653444, published 2020-02-07 (sstubsLarge downloaded and analysed).

## 1. Method in brief

1. Universe (above) -> `python -m goblin_mining universe`. 2. Fetch PRs by GraphQL search (`repo:X is:pr is:closed sort:comments-desc created:>=window`, 10 PRs per request, 4 workers, cached gz JSON per repo) and commit signals by REST commit search. 3. Pilot of 300 random comments open-coded; codebook seeded from the papers above and extended (SUGGESTION-ONLY, ALTERNATIVE-DISCUSS and the AI-author split came from the pilot). 4. Stratified samples (language x PR has CHANGES_REQUESTED, at most 12 comments per repo) labelled in batches of 100 by reading; each label = primary code + severity mark (N nit, S suggestion, B blocking/bug, Q question, P praise) + a short candidate tag + a few-word rationale, stored in SQLite and in labels/*.txt. 5. Estimation (post-stratified), local classifier cross-check, external-corpus cross-check. 6. Every category mapped to candidate lint rules, a detectability tier and an existing rule id (catalogue read: docs/design/neatness.md NEAT001-037, cohesion.md COH001-004, documentation.md NARR001-005, docs/reference/rules/*.md landed ids, notes/research/lint-requirements.md families R01-R37).

## 2. Codebook (review comments)

Seeds are named per row; SUGGESTION-ONLY and the AI-author split were added by open coding on the 300-comment pilot (labels/pilot_*.txt). Default tier is the detectability of the category as a whole; the candidate table (section 7) refines it. Share = post-stratified estimate over human thread-opening comments on non-AI PRs, 95 percent CI by repo-cluster bootstrap; k = labelled human comments.

| id | definition | seed | tier | k | share [95% CI] |
|---|---|---|---|---|---|
| NAMING | rename identifier, misleading or unclear name | Mantyla:documentation/naming; Sadowski:readability | human | 207 | 5.0% [4.4-5.7] |
| DOC-COMMENT | missing, wrong or stale code comment or docstring/API doc | Mantyla:documentation | structural | 251 | 6.3% [5.4-7.1] |
| FORMAT-STYLE | whitespace, formatting, import order, line length, lint-able style | Mantyla:visual representation | syntax | 107 | 2.5% [2.0-3.2] |
| DEAD-CODE | unused code/vars/imports, commented-out code, leftover debug, stale TODO | Mantyla:structure/dead code; Bacchelli:remove unneeded code | structural | 256 | 6.0% [5.2-6.9] |
| DUPLICATION | repeated code or reinventing an existing helper/API | Mantyla:structure/duplication; Silva:remove duplication | structural | 109 | 2.8% [2.2-3.3] |
| SIMPLIFY-IDIOM | simplify expression/control flow or use the idiomatic/standard API | Bacchelli:better code practices; Sadowski:readability | structural | 254 | 6.3% [5.5-7.4] |
| DESIGN-STRUCTURE | decomposition, abstraction, responsibility, layering, where code lives, API shape | Mantyla:structure/solution approach; Bacchelli:design | human | 387 | 9.2% [8.3-10.1] |
| CONSISTENCY | match existing conventions or patterns elsewhere in the codebase | Sadowski:consistency | human | 78 | 1.9% [1.4-2.3] |
| MAGIC-CONFIG | magic literal, hard-coded value, configurable constant | open coding | structural | 45 | 1.0% [0.7-1.3] |
| TYPE-SAFETY | types, annotations, nullability, generics, casts, unsafe typing | open coding; Mantyla:check | types | 119 | 2.7% [2.1-3.3] |
| LOGIC-BUG | wrong condition, off-by-one, incorrect behaviour or algorithm | Mantyla:logic; Beller:functional | human | 281 | 6.4% [5.4-7.4] |
| EDGE-CASE | unhandled null/empty/boundary/invalid input or state | Mantyla:check | types | 101 | 2.4% [2.0-2.9] |
| ERROR-HANDLING | swallowed or missing error handling, panic/unwrap/throw, error message quality | Mantyla:check; Bacchelli:exception handling | effects | 104 | 2.6% [2.0-3.2] |
| RESOURCE-LIFETIME | leaks, ownership, lifetime, close/dispose, memory | Mantyla:resource | effects | 30 | 0.8% [0.5-1.1] |
| CONCURRENCY | races, locks, async/await misuse, ordering, thread safety | Mantyla:timing/synchronisation | effects | 42 | 1.0% [0.7-1.4] |
| PERFORMANCE | algorithmic cost, needless allocation or work, caching | open coding | effects | 125 | 3.0% [2.4-3.6] |
| SECURITY | injection, secrets, validation, authz, unsafe operations | Bacchelli:security | effects | 51 | 1.1% [0.7-1.5] |
| API-COMPAT | breaking change, deprecation, backward compatibility, ABI, versioning | Mantyla:interface | types | 93 | 2.1% [1.7-2.6] |
| DEPENDENCY-BUILD | dependencies, versions, build config, CI, feature flags | Mantyla:support | structural | 123 | 2.8% [2.4-3.4] |
| PLATFORM-PORTABILITY | OS, arch, browser or runtime-version differences | open coding | human | 32 | 0.7% [0.5-1.0] |
| LOGGING-OBS | logging, metrics, diagnostics and their content | open coding | structural | 33 | 0.9% [0.6-1.1] |
| TEST-MISSING | add or extend tests, coverage gap | Sadowski:testing | structural | 60 | 1.4% [1.1-1.7] |
| TEST-QUALITY | flaky/over-mocked tests, weak assertions, test design | Sadowski:testing | human | 124 | 2.9% [2.4-3.5] |
| USER-FACING | UI text, a11y, i18n, styling, user-visible behaviour | open coding | render | 154 | 3.3% [2.5-4.3] |
| DOCS-CHANGELOG | user docs, README, changelog, release notes | Mantyla:documentation | structural | 317 | 7.5% [6.3-8.8] |
| SCOPE-PROCESS | PR scope, split the PR, commit message, process, licensing, ownership | Bacchelli:social/process | human | 119 | 2.8% [2.2-3.4] |
| QUESTION-UNDERSTAND | reviewer asks why/what/how to understand the change | Bacchelli:understanding | human | 165 | 4.2% [3.5-4.9] |
| ALTERNATIVE-DISCUSS | design discussion or alternative approach with no concrete defect | Bacchelli:design/knowledge transfer | human | 0 | 0 |
| PRAISE-ACK | approval, thanks, acknowledgement, no action | Bacchelli:social | human | 16 | 0.4% [0.2-0.6] |
| SUGGESTION-ONLY | a code suggestion block with no stated reason (pilot open coding) | open coding | human | 288 | 6.5% [5.7-7.5] |
| NOISE-OTHER | bot output, empty, unclear, off topic | Beller:no change | human | 132 | 3.4% [2.8-4.1] |

Severity marks recorded per label: N explicit nit / optional; S suggestion; B blocking, must change or a bug; Q question; P praise or acknowledgement.

Commit codebooks (Silva et al. 2016 motivations for R-*; ManySStuBs4J and Mantyla classes for F-*):

| id | definition | seed | tier |
|---|---|---|---|
| R-READABILITY | improve readability/understandability, decompose a long function | Silva:improve readability | human |
| R-DUPLICATION | remove duplicated code | Silva:remove duplication | structural |
| R-REUSE-EXTRACT | extract helper/module to enable reuse | Silva:extract reusable method | structural |
| R-DESIGN-STRUCTURE | move/split/merge classes or modules, layering, ownership | Silva:decompose class, move | human |
| R-NAMING | rename for clarity or consistency | Silva:rename | human |
| R-DEAD-CODE | remove unused or obsolete code, flags, dependencies | Silva:remove dead code | structural |
| R-SIMPLIFY | simplify logic or conditions, fewer branches | AlOmar:simplify | structural |
| R-TESTABILITY | make code testable, dependency injection | Silva:improve testability | human |
| R-ENABLE-CHANGE | prepare for a feature or fix | Silva:facilitate extension | human |
| R-API-MIGRATION | migrate to new/deprecated API, modernize language usage, upgrade | Silva:backward compatibility | types |
| R-PERFORMANCE | refactor for speed or memory | open coding | effects |
| R-TYPE-SAFETY | stronger types, remove casts/any, nullability | open coding | types |
| R-TOOLING-LINT | forced by linter, formatter, warning, or static analysis | open coding | syntax |
| R-ERROR-HANDLING | restructure error handling or logging | open coding | effects |
| R-CONSISTENCY | align with conventions elsewhere | Sadowski:consistency | human |
| R-NOT-REFACTOR | message says refactor but the change is a feature, fix or docs | Murphy-Hill via Silva | human |
| F-LOGIC | wrong condition or algorithm, off-by-one | ManySStuBs4J: operator/operand/if | human |
| F-NULL-EDGE | null/None/undefined/empty/boundary input not handled | ManySStuBs4J | types |
| F-ERROR-HANDLING | missing or wrong error/exception path | Mantyla:check | effects |
| F-RESOURCE | leak, lifetime, use-after-free, overflow | Mantyla:resource | effects |
| F-CONCURRENCY | race, deadlock, async ordering, stale state | Mantyla:timing | effects |
| F-TYPE-CAST | type confusion, wrong cast, numeric overflow, wrong unit | open coding | types |
| F-API-MISUSE | wrong function/argument/arg order, wrong identifier | ManySStuBs4J: identifier/args/swap | types |
| F-STATE-INIT | wrong initialisation, lifecycle or ordering of state | open coding | effects |
| F-PERF | performance regression or hang | open coding | effects |
| F-SECURITY | security vulnerability fix | open coding | effects |
| F-PLATFORM-COMPAT | OS, browser, version or toolchain incompatibility | open coding | human |
| F-BUILD-DEPS-CI | build, dependency, packaging or CI breakage | Mantyla:support | structural |
| F-TEST | fix a broken or flaky test | open coding | human |
| F-DOC-TYPO | typo, doc or comment fix | Mantyla:documentation | syntax |
| F-UI-RENDER | rendering, layout, UI text or UX bug | open coding | render |
| F-CONFIG-DEFAULT | wrong default, flag or configuration value | open coding | structural |
| F-MISSING-CASE | unhandled variant/feature gap/incomplete implementation | Mantyla:function | types |
| F-REGRESSION-REVERT | revert of a change that broke something | open coding | human |
| F-OTHER | unclear or not a mistake (feature/chore) | open coding | human |

## 3. Q1: what reviewers flag, by language and domain, and how severe

Denominator for every table in this section unless stated: **4,203 labelled human comments** on non-AI-authored PRs (drawn from 207,083 human thread-opening comments in the corpus); 139,846 AI-reviewer, 12,972 bot and 5,971 human-on-AI-PR thread openers are excluded (section 4).

### 3.1 Category frequencies (all 30 categories)

| category | share [95% CI] | k | classifier share (cross-check) | blocking mark | nit mark | question | on CHANGES_REQUESTED PR | thread resolved |
|---|---|---|---|---|---|---|---|---|
| DESIGN-STRUCTURE | 9.2% [8.3-10.1] | 387 | 12.6% | 12% | 3% | 16% | 45% | 73% |
| DOCS-CHANGELOG | 7.5% [6.3-8.8] | 317 | 8.4% | 9% | 3% | 7% | 50% | 83% |
| SUGGESTION-ONLY | 6.5% [5.7-7.5] | 288 | 8.4% | 0% | 1% | 0% | 51% | 91% |
| LOGIC-BUG | 6.4% [5.4-7.4] | 281 | 7.8% | 65% | 1% | 14% | 55% | 70% |
| SIMPLIFY-IDIOM | 6.3% [5.5-7.4] | 254 | 6.6% | 2% | 20% | 11% | 42% | 79% |
| DOC-COMMENT | 6.3% [5.4-7.1] | 251 | 5.8% | 8% | 15% | 9% | 45% | 81% |
| DEAD-CODE | 6.0% [5.2-6.9] | 256 | 6.4% | 9% | 5% | 19% | 50% | 78% |
| NAMING | 5.0% [4.4-5.7] | 207 | 4.7% | 8% | 20% | 5% | 52% | 83% |
| QUESTION-UNDERSTAND | 4.2% [3.5-4.9] | 165 | 4.7% | 0% | 0% | 97% | 38% | 70% |
| NOISE-OTHER | 3.4% [2.8-4.1] | 132 | 2.8% | 0% | 0% | 1% | 30% | 58% |
| USER-FACING | 3.3% [2.5-4.3] | 154 | 3.0% | 16% | 14% | 4% | 55% | 77% |
| PERFORMANCE | 3.0% [2.4-3.6] | 125 | 2.3% | 22% | 9% | 18% | 47% | 74% |
| TEST-QUALITY | 2.9% [2.4-3.5] | 124 | 3.4% | 17% | 2% | 15% | 55% | 69% |
| DEPENDENCY-BUILD | 2.8% [2.4-3.4] | 123 | 2.4% | 27% | 1% | 22% | 52% | 76% |
| SCOPE-PROCESS | 2.8% [2.2-3.4] | 119 | 2.7% | 42% | 1% | 18% | 62% | 72% |
| DUPLICATION | 2.8% [2.2-3.3] | 109 | 2.1% | 7% | 6% | 17% | 39% | 72% |
| TYPE-SAFETY | 2.7% [2.1-3.3] | 119 | 2.7% | 15% | 6% | 14% | 53% | 72% |
| ERROR-HANDLING | 2.6% [2.0-3.2] | 104 | 2.5% | 30% | 2% | 18% | 46% | 73% |
| FORMAT-STYLE | 2.5% [2.0-3.2] | 107 | 2.0% | 9% | 70% | 0% | 53% | 79% |
| EDGE-CASE | 2.4% [2.0-2.9] | 101 | 2.0% | 41% | 0% | 28% | 47% | 74% |
| API-COMPAT | 2.1% [1.7-2.6] | 93 | 1.5% | 31% | 4% | 17% | 49% | 76% |
| CONSISTENCY | 1.9% [1.4-2.3] | 78 | 1.6% | 10% | 13% | 4% | 51% | 74% |
| TEST-MISSING | 1.4% [1.1-1.7] | 60 | 1.1% | 22% | 0% | 12% | 42% | 85% |
| SECURITY | 1.1% [0.7-1.5] | 51 | 0.4% | 63% | 0% | 12% | 67% | 65% |
| MAGIC-CONFIG | 1.0% [0.7-1.3] | 45 | 0.6% | 9% | 2% | 18% | 60% | 73% |
| CONCURRENCY | 1.0% [0.7-1.4] | 42 | 0.5% | 62% | 5% | 17% | 52% | 69% |
| LOGGING-OBS | 0.9% [0.6-1.1] | 33 | 0.4% | 24% | 6% | 0% | 48% | 76% |
| RESOURCE-LIFETIME | 0.8% [0.5-1.1] | 30 | 0.2% | 60% | 0% | 10% | 40% | 70% |
| PLATFORM-PORTABILITY | 0.7% [0.5-1.0] | 32 | 0.3% | 56% | 0% | 22% | 44% | 56% |
| PRAISE-ACK | 0.4% [0.2-0.6] | 16 | 0.1% | 0% | 0% | 0% | 44% | 69% |

Baselines: 36.6% of human comments sit on PRs that received a human CHANGES_REQUESTED review (post-stratified; the PR sample is the most-commented, so this is inflated relative to all PRs); 17.6% of labelled human comments carry a blocking/bug mark, 7.5% an explicit nit, 14.9% a question. 'Thread resolved' is GitHub's isResolved flag (76 percent of all human thread openers are resolved, 75 percent outdated).

### 3.2 Four coarse groups and comparison with the literature

Groups: evolvability (naming, comments, formatting, dead code, duplication, simplification, design, consistency, magic values, docs, logging), functional (logic, edge cases, error handling, resources, concurrency, performance, security, API compat, types, portability, build, user-facing), testing, other (process, questions, suggestion-only, praise, noise).

| group | mined share [95% CI] | CodeReviewer corpus (our classifier) |
|---|---|---|
| evolvability | 49.4% [47.7-51.5] | 50.5% |
| functional | 29.0% [27.0-31.0] | 26.9% |
| testing | 4.3% [3.7-4.9] | 5.2% |
| other | 17.3% [15.9-18.8] | 17.4% |

The mined evolvability:functional ratio (about 2:1 among comments with a code-level concern, 49 vs 29 percent of all comments) is consistent with Beller et al. 2014 (about 75 percent maintainability vs 25 percent functional of the fixed issues, secondhand figure) and with Bacchelli and Bird 2013 (code improvements 29 percent of comments, defects 14 percent, verified in the paper). Our functional share is higher than Bacchelli and Bird's defect share because our functional group also contains performance, security, portability, build and user-facing concerns that their taxonomy places elsewhere.

### 3.3 By language of the commented file (coarse groups)

| file language | labelled n | evolvability | functional | testing | other |
|---|---|---|---|---|---|
| C/C++ | 565 | 53.9% [49.5-57.9] | 26.4% [22.5-31.4] | 2.0% [0.8-3.1] | 17.8% [13.8-21.4] |
| TypeScript/JS | 549 | 41.6% [37.3-46.7] | 30.1% [25.0-35.1] | 6.3% [4.3-8.6] | 21.9% [17.9-25.9] |
| Docs | 405 | 79.5% [74.6-83.4] | 4.8% [2.6-7.3] | 1.0% [0.0-2.2] | 14.7% [11.4-19.2] |
| Rust | 346 | 50.9% [46.4-56.9] | 33.2% [26.7-38.9] | 2.5% [1.3-4.0] | 13.4% [9.3-17.7] |
| Go | 344 | 46.2% [41.4-50.5] | 30.7% [26.5-35.6] | 8.1% [5.8-10.4] | 15.0% [11.2-19.2] |
| Python | 307 | 44.6% [38.2-50.4] | 34.3% [27.7-40.7] | 4.5% [1.9-7.2] | 16.6% [12.8-21.0] |
| Java | 271 | 48.1% [41.7-55.2] | 31.7% [26.5-36.9] | 6.9% [3.7-9.8] | 13.3% [9.0-18.5] |
| Config/Build | 261 | 31.3% [25.6-37.8] | 44.9% [36.5-54.5] | 1.8% [0.3-4.0] | 22.1% [16.1-28.1] |
| C# | 246 | 46.8% [41.6-53.4] | 32.5% [26.0-39.1] | 5.6% [2.9-8.7] | 15.0% [9.5-19.5] |
| other | 240 | 44.9% [36.3-53.1] | 27.3% [20.3-34.3] | 7.0% [3.6-10.5] | 20.8% [16.1-26.0] |
| Kotlin | 188 | 54.0% [47.1-60.7] | 23.2% [18.6-28.2] | 2.4% [0.9-4.2] | 20.3% [14.1-26.9] |
| Swift | 170 | 40.9% [32.1-52.1] | 38.9% [27.8-49.8] | 6.4% [2.6-12.4] | 13.7% [7.5-18.2] |
| PHP | 156 | 40.2% [30.7-48.1] | 44.7% [37.3-52.0] | 2.5% [0.4-4.9] | 12.6% [7.6-19.2] |
| Ruby | 155 | 37.8% [29.3-46.5] | 29.5% [22.5-34.9] | 4.8% [1.5-9.0] | 27.9% [19.3-37.7] |

### 3.4 By language: leading categories (post-stratified share, 95 percent CI)

| category | C/C++ (n=565) | TypeScript/JS (n=549) | Docs (n=405) | Rust (n=346) | Go (n=344) | Python (n=307) | Java (n=271) | C# (n=246) | Kotlin (n=188) | Swift (n=170) | PHP (n=156) | Ruby (n=155) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DESIGN-STRUCTURE | 9.4 (8-11) | 7.3 (5-10) | 4.2 (2-6) | 10.6 (8-14) | 9.9 (7-13) | 11.6 (8-17) | 9.7 (7-14) | 15.7 (12-20) | 12.8 (9-19) | 11.1 (7-15) | 10.7 (5-15) | 13.9 (8-19) |
| DOCS-CHANGELOG | 0.1 (0-0) | 0.8 (0-2) | 67.6 (62-73) | 1.2 (0-2) | 0.6 (0-2) | 2.2 (1-4) | 0 | 0.7 (0-2) | 0.4 (0-1) | 1.8 (0-4) | 0 | 0 |
| SUGGESTION-ONLY | 7.9 (5-11) | 6.2 (4-8) | 8.3 (5-11) | 4.4 (2-7) | 3.8 (2-6) | 4.6 (2-8) | 5.1 (3-8) | 6.6 (3-10) | 9.5 (5-16) | 5.1 (2-9) | 6.3 (3-12) | 14.9 (7-26) |
| LOGIC-BUG | 6.7 (5-9) | 10.2 (7-13) | 0.6 (0-2) | 8.1 (4-13) | 6.5 (4-10) | 8.5 (5-13) | 7.7 (5-11) | 8.5 (4-13) | 6.1 (3-9) | 6.4 (2-10) | 6.3 (4-10) | 4.6 (2-9) |
| SIMPLIFY-IDIOM | 9.3 (7-11) | 6.8 (5-10) | 0.2 (0-1) | 9.3 (6-13) | 10.7 (8-15) | 4.9 (2-8) | 5.0 (2-8) | 6.2 (4-8) | 6.2 (3-11) | 8.4 (3-14) | 6.2 (3-11) | 4.7 (1-9) |
| DOC-COMMENT | 7.5 (6-10) | 5.5 (4-7) | 4.0 (2-6) | 8.7 (6-12) | 8.2 (5-11) | 5.0 (2-8) | 8.8 (5-12) | 5.8 (3-8) | 7.5 (4-11) | 2.4 (0-6) | 4.4 (1-8) | 5.5 (2-9) |
| DEAD-CODE | 7.2 (5-9) | 6.7 (5-9) | 1.9 (0-3) | 5.6 (3-9) | 4.7 (3-7) | 6.4 (4-10) | 6.9 (4-10) | 5.6 (3-9) | 8.5 (3-14) | 5.7 (2-12) | 5.9 (3-8) | 4.0 (1-8) |
| NAMING | 6.0 (4-8) | 3.8 (2-5) | 0.4 (0-1) | 8.4 (6-11) | 3.8 (2-6) | 5.1 (3-8) | 6.9 (5-10) | 6.6 (4-10) | 8.6 (4-14) | 3.9 (1-7) | 3.1 (1-6) | 7.5 (2-15) |
| QUESTION-UNDERSTAND | 4.2 (3-6) | 6.1 (3-9) | 0.8 (0-2) | 2.9 (1-5) | 3.8 (2-6) | 7.6 (5-11) | 3.2 (1-5) | 5.4 (2-10) | 5.1 (2-8) | 5.7 (3-10) | 2.5 (1-5) | 3.0 (0-6) |
| NOISE-OTHER | 2.7 (1-5) | 6.2 (4-9) | 3.4 (2-5) | 3.3 (2-5) | 3.7 (2-6) | 1.8 (1-4) | 2.5 (1-6) | 1.3 (0-3) | 4.7 (2-8) | 0.6 (0-2) | 1.3 (0-3) | 6.3 (2-11) |
| USER-FACING | 1.1 (0-2) | 5.2 (3-9) | 0.8 (0-2) | 1.4 (0-3) | 2.0 (1-4) | 2.0 (0-4) | 0.3 (0-1) | 4.4 (2-7) | 2.7 (1-6) | 6.0 (1-11) | 7.5 (4-13) | 1.8 (0-5) |
| PERFORMANCE | 3.7 (2-6) | 2.4 (1-4) | 0 | 5.9 (4-8) | 2.0 (1-3) | 4.9 (3-8) | 4.7 (2-8) | 4.6 (2-8) | 1.0 (0-3) | 4.6 (2-7) | 4.4 (1-8) | 0.3 (0-1) |
| TEST-QUALITY | 1.1 (0-2) | 4.3 (3-6) | 1.0 (0-2) | 1.9 (1-3) | 5.2 (3-8) | 3.6 (1-7) | 4.9 (2-7) | 4.8 (2-8) | 1.6 (0-3) | 3.6 (1-8) | 1.3 (0-4) | 1.3 (0-3) |
| DEPENDENCY-BUILD | 0.3 (0-1) | 1.1 (0-2) | 1.9 (1-3) | 0.4 (0-1) | 0.4 (0-1) | 0.9 (0-2) | 0.6 (0-1) | 0.3 (0-1) | 2.7 (1-5) | 0.6 (0-2) | 0 | 6.2 (0-13) |

Cells with n below about 150 have wide intervals (shown); differences between languages are suggestive only unless intervals separate. Classifier-extrapolated version of this matrix over all 207k human comments, with CIs, is in data/results_comments.json (pop_by_lang).

### 3.5 By repository domain (heuristic domain labels)

| domain | labelled n | evolvability | functional | testing | other |
|---|---|---|---|---|---|
| other-library-app | 670 | 48.2% [44.2-52.5] | 28.5% [24.9-32.6] | 4.2% [2.8-5.5] | 19.1% [15.8-23.3] |
| ml-data | 645 | 51.1% [46.5-57.2] | 30.5% [25.0-35.5] | 3.5% [2.3-4.7] | 14.8% [12.2-17.5] |
| infra-cloud | 599 | 49.7% [46.8-53.7] | 30.2% [25.8-34.9] | 5.3% [3.3-7.3] | 14.9% [12.4-17.4] |
| compilers-langs | 498 | 52.9% [46.5-58.4] | 25.6% [20.8-30.3] | 5.9% [3.6-8.6] | 15.6% [12.5-19.5] |
| web-backend | 429 | 44.9% [39.7-50.3] | 31.7% [26.0-37.7] | 5.0% [3.0-7.0] | 18.4% [14.0-23.5] |
| games | 297 | 51.1% [45.2-58.2] | 29.4% [21.6-37.1] | 1.6% [0.4-3.3] | 17.9% [14.1-23.1] |
| mobile | 288 | 48.5% [40.6-58.6] | 29.3% [21.2-38.1] | 3.0% [1.1-5.0] | 19.3% [13.6-26.8] |
| web-frontend | 260 | 46.3% [36.7-54.5] | 27.7% [19.0-36.7] | 5.1% [2.1-9.7] | 20.9% [15.3-26.0] |
| database | 188 | 52.6% [45.2-61.9] | 27.8% [21.5-33.6] | 5.3% [2.8-7.7] | 14.3% [8.4-20.7] |
| devtools-cli | 172 | 51.4% [45.1-58.0] | 22.2% [18.6-27.0] | 1.3% [0.0-3.2] | 25.2% [16.5-33.1] |
| systems-embedded | 157 | 40.9% [30.0-51.2] | 34.7% [26.5-42.9] | 5.1% [1.0-8.7] | 19.3% [12.2-29.0] |

Top categories by domain (share, 95 percent CI):

| category | other-library-app (n=670) | ml-data (n=645) | infra-cloud (n=599) | compilers-langs (n=498) | web-backend (n=429) | games (n=297) | mobile (n=288) | web-frontend (n=260) | database (n=188) |
|---|---|---|---|---|---|---|---|---|---|
| DESIGN-STRUCTURE | 6.6 (5-9) | 11.9 (9-15) | 10.3 (8-12) | 8.5 (6-11) | 7.4 (5-10) | 10.3 (7-14) | 9.5 (6-14) | 6.6 (4-9) | 8.4 (5-14) |
| DOCS-CHANGELOG | 10.8 (7-17) | 6.6 (4-9) | 7.9 (5-11) | 8.7 (5-13) | 5.4 (2-9) | 3.6 (2-6) | 5.5 (1-10) | 9.0 (4-17) | 10.1 (3-19) |
| SUGGESTION-ONLY | 7.3 (5-9) | 4.5 (3-6) | 4.4 (2-7) | 6.7 (5-9) | 6.7 (3-12) | 9.2 (6-14) | 11.2 (6-17) | 7.3 (3-11) | 5.2 (2-10) |
| LOGIC-BUG | 5.5 (4-7) | 8.6 (6-11) | 6.2 (4-8) | 5.2 (3-8) | 8.4 (5-11) | 6.5 (3-11) | 5.6 (2-10) | 3.7 (2-6) | 5.4 (2-8) |
| SIMPLIFY-IDIOM | 4.4 (3-6) | 6.5 (4-9) | 6.1 (4-8) | 5.9 (4-8) | 7.2 (5-11) | 8.7 (5-13) | 8.7 (4-14) | 5.4 (2-10) | 6.5 (4-9) |
| DOC-COMMENT | 6.8 (5-9) | 5.4 (4-7) | 7.0 (5-10) | 7.4 (5-9) | 5.8 (4-8) | 8.4 (5-12) | 5.9 (3-9) | 4.0 (2-6) | 8.4 (5-13) |
| DEAD-CODE | 7.0 (5-9) | 6.6 (4-9) | 6.0 (4-8) | 5.5 (3-8) | 5.1 (3-8) | 6.0 (4-8) | 4.2 (2-7) | 5.2 (3-9) | 7.6 (3-14) |
| NAMING | 4.3 (3-6) | 5.4 (4-7) | 5.0 (3-7) | 5.3 (3-8) | 4.3 (2-7) | 4.6 (2-8) | 4.7 (3-7) | 6.6 (4-9) | 3.5 (1-6) |
| QUESTION-UNDERSTAND | 4.6 (3-7) | 3.1 (2-4) | 3.9 (2-6) | 4.6 (3-7) | 4.4 (3-7) | 2.6 (0-7) | 3.2 (1-6) | 4.5 (2-7) | 3.9 (2-6) |
| NOISE-OTHER | 3.5 (2-5) | 4.0 (3-6) | 3.5 (2-5) | 2.9 (2-5) | 5.0 (2-8) | 1.9 (1-3) | 2.1 (1-4) | 5.0 (2-8) | 1.1 (0-3) |

### 3.6 Canonical lint candidates mined from review comments

Each labelled comment's (category, candidate tag) maps to one canonical candidate (src/goblin_mining/rulemap.py). Share = post-stratified over human comments incl. non-lintable ones. Blocking = share tagged B; nit = share tagged N; CR = share on a PR with CHANGES_REQUESTED; acted = thread resolved or outdated.

| id | candidate | share [95% CI] | k | blocking | nit | CR | tier | existing rule / status |
|---|---|---|---|---|---|---|---|---|
| C46 | documentation prose quality (wording, structure, examples) | 8.9% [7.8-10.0] | 366 | 6% | 5% | 50% | human | n/a (prose lint bound tools) |
| C47 | code suggestion block with no stated reason | 6.5% [5.7-7.5] | 288 | 0% | 1% | 51% | human | n/a |
| C43 | design discussion or alternative approach (no concrete defect) | 6.5% [5.8-7.3] | 270 | 11% | 3% | 47% | human | n/a |
| C02 | unused import / variable / parameter / function | 5.7% [5.0-6.7] | 246 | 7% | 6% | 50% | structural | DEAD (v2 designed; v1 DEAD001); compiler/linter unused warnings |
| C42 | logic error: wrong condition, wrong value, regression | 5.4% [4.5-6.2] | 234 | 63% | 1% | 55% | human | none mechanical (tests/review); bound analyzers catch subsets |
| C16 | needlessly complex expression or control flow; simplify | 5.0% [4.3-5.8] | 203 | 1% | 18% | 41% | structural | NEAT005 (cognitive complexity), bound linters |
| C13 | unclear, misleading or inconsistent identifier name | 4.4% [3.7-5.1] | 183 | 7% | 20% | 52% | human | new candidate (name-vs-behaviour is judgement) |
| C45 | question: reviewer asks why / what / how | 4.2% [3.5-4.9] | 165 | 0% | 0% | 38% | human | n/a |
| C33 | needless work in a hot path: N+1, clone/alloc, repeated lookup, work per frame | 3.0% [2.4-3.6] | 124 | 23% | 9% | 47% | effects | PERF001-018 v1 lexical perf (R33) |
| C29 | missing null/empty/boundary/invalid-input handling | 2.9% [2.4-3.5] | 127 | 40% | 0% | 51% | types | new candidate (nullability and bounds lint; bound tools: clippy, TS strict, mypy) |
| C36 | CI/build/dependency: unpinned version, wrong version, permissions, cache key | 2.8% [2.4-3.4] | 123 | 27% | 1% | 52% | structural | CI001 (pinned-ref), CI003, CI006/007/010, VET001-012 (supply chain) |
| C12 | formatting, indentation, whitespace, blank line, import order, line length | 2.7% [2.2-3.3] | 116 | 10% | 67% | 54% | syntax | bound formatter/linter (FMT001/002 v1; TOOL001 stages) |
| C38 | user-visible string untranslated, hard-coded or accessibility label missing | 2.7% [2.0-3.6] | 126 | 19% | 6% | 55% | render | A11Y (v1 web families), crunk; i18n new candidate |
| C30 | error swallowed, ignored, mis-propagated or panic instead of error | 2.5% [2.0-3.1] | 103 | 29% | 2% | 46% | effects | EXHAUST001-004 (v1 Python-semantic, R34); new candidate generally |
| C25 | unrelated change in the PR; scope creep; should be split or reverted | 2.3% [1.8-2.8] | 100 | 40% | 1% | 63% | human | R05 diff accountability (COV002/COV008 v1); SCOPE001 is lease-based; new for scope-of-diff |
| C03 | duplicated logic or copy-paste | 2.2% [1.7-2.7] | 85 | 8% | 7% | 39% | structural | DUP001-003 (clone ladder R19) |
| C40 | type weakness: any/object/unchecked cast, string-typed, optional where required | 2.1% [1.6-2.7] | 92 | 17% | 8% | 53% | types | NEAT020-026 (type rules, designed); bound tools |
| C09 | typo, grammar or wording error in text | 1.9% [1.4-2.4] | 79 | 0% | 52% | 44% | syntax | new candidate (spell checker bound tool) |
| C27 | missing test for new behaviour or a covered branch | 1.4% [1.1-1.7] | 60 | 22% | 0% | 42% | structural | COV001 (untested-public-function), TEST001, R04 test reach |
| C44 | consistency with existing conventions elsewhere in the codebase | 1.4% [1.0-1.8] | 57 | 12% | 11% | 49% | human | n/a (project-specific convention rules via policy patterns) |
| C41 | public-API design shape: argument shape, builder, accessor, naming of API | 1.4% [1.0-1.8] | 58 | 16% | 3% | 40% | human | new candidate |
| C20 | code placed in the wrong file, module or layer | 1.4% [1.0-1.7] | 59 | 14% | 3% | 47% | structural | ARCH104 layering (R17), INV002 forbidden-import, CYCLE001 |
| C18 | magic number, hard-coded string/path/colour that should be a constant or config | 1.2% [0.9-1.5] | 50 | 12% | 2% | 58% | syntax | NEAT009 (magic-value) |
| C34 | security: injection, secret in log, missing authz, unsafe input handling | 1.1% [0.7-1.5] | 51 | 63% | 0% | 67% | effects | SEC001-003/SEC110 (lexical secrets, R21); WEBSEC; new candidate for injection |
| C04 | reinvents an existing helper, constant or library API | 1.1% [0.7-1.4] | 45 | 7% | 0% | 53% | types | new candidate |
| C32 | concurrency: race, lock misuse, blocking in async, stale closure | 0.9% [0.7-1.2] | 38 | 58% | 5% | 50% | effects | RACE001/002 (v1, R34); new candidate |
| C28 | test does not exercise the fix, asserts weakly, or tests a mock | 0.9% [0.6-1.2] | 36 | 28% | 6% | 53% | human | R06 test tiers/evidence (partly); new candidate for vacuous asserts |
| C05 | missing or inadequate docstring / API doc comment | 0.8% [0.6-1.2] | 34 | 24% | 0% | 50% | structural | DOC001 (undocumented-public-item) |
| C39 | logging: wrong level, noisy, sensitive content, log vs return | 0.8% [0.6-1.1] | 32 | 22% | 6% | 47% | human | new candidate |
| C06 | stale, inaccurate or contradictory comment or doc | 0.8% [0.6-1.1] | 33 | 39% | 6% | 52% | structural | DRIFT001-004 (doc-binding drift) for bound docs; otherwise new |
| C31 | resource leak, missing cleanup, ownership or lifetime error | 0.8% [0.5-1.1] | 30 | 60% | 0% | 40% | effects | new candidate (RAII/leak lint; bound tools) |
| C14 | identifier violates the naming convention (case, prefix, plural) | 0.7% [0.5-1.0] | 29 | 10% | 21% | 52% | syntax | bound linter (ruff N8xx, clippy style); new candidate for frob |
| C37 | platform portability: OS-specific path, API or version assumption | 0.7% [0.4-1.0] | 31 | 55% | 0% | 45% | types | new candidate (cfg/ifdef gating) |
| C10 | broken link, stale reference or missing doc entry | 0.7% [0.5-1.0] | 29 | 17% | 3% | 31% | structural | DOC002 (broken-markdown-link), DRIFT002 |
| C17 | use the idiomatic standard-library or language feature | 0.7% [0.4-1.0] | 24 | 4% | 33% | 38% | types | bound linters (clippy, ruff UP/SIM, clang-tidy modernize) |
| C49 | state initialised or ordered wrongly (lifecycle, init order, stale state) | 0.6% [0.4-0.8] | 26 | 77% | 4% | 54% | effects | new candidate |
| C35 | breaking public API change or missing deprecation | 0.5% [0.3-0.8] | 24 | 67% | 0% | 62% | types | DEPR001-006 (R24), BIND001/002 (R30); new candidate for API diff |
| C08 | missing why-comment or unexplained magic behaviour | 0.5% [0.3-0.8] | 24 | 0% | 0% | 42% | human | NARR004 (rationale must reference decisions) partly |
| C07 | redundant, verbose or obvious comment | 0.5% [0.3-0.7] | 21 | 0% | 0% | 52% | syntax | NARR001/NARR004 (comment hygiene) |
| C21 | function or class too long or doing too much; extract | 0.5% [0.2-0.8] | 20 | 0% | 0% | 30% | structural | NEAT001 (function-too-long), COH001-004 |
| C19 | visibility wider than needed (pub, public, exported) | 0.5% [0.3-0.7] | 25 | 20% | 4% | 56% | structural | new candidate (vis vs references_to) |
| C23 | mixed concerns or abstraction levels; coupling across layers | 0.4% [0.2-0.6] | 16 | 25% | 6% | 44% | structural | COH003 (mixed abstraction levels), COH001, ARCH104 |
| C26 | PR hygiene: commit structure, license header, process requirement | 0.4% [0.1-0.6] | 12 | 42% | 0% | 42% | structural | new candidate (license header exists in v1 policy families) |
| C15 | deep nesting; use early return, guard or continue | 0.4% [0.2-0.6] | 15 | 0% | 33% | 40% | structural | NEAT004 (nesting-depth), NEAT005 |
| C48 | wrong function, wrong argument, swapped arguments or wrong identifier used | 0.3% [0.1-0.5] | 11 | 64% | 9% | 27% | types | new candidate (arity/type check; param-name vs argument-name lint) |
| C22 | too many parameters, boolean flag parameter, or options-object missing | 0.3% [0.1-0.4] | 11 | 0% | 0% | 45% | syntax | NEAT002 (param count), NEAT003 (boolean flag) |
| C01 | commented-out code or leftover debug output | 0.3% [0.1-0.4] | 12 | 58% | 0% | 50% | syntax | NARR001-005 (comment hygiene), TODO001/002 |
| C50 | incomplete handling of a variant, enum case or input class (non-exhaustive) | 0.2% [0.1-0.3] | 6 | 33% | 0% | 33% | types | NEAT026 (exhaustive-match, designed); bound compilers |
| C11 | changelog, release note or changeset missing or in wrong category | 0.2% [0.0-0.4] | 9 | 22% | 0% | 89% | structural | REL003 (changelog-fragment-required) |
| C24 | global or shared mutable state; mutation of arguments | 0.2% [0.1-0.3] | 9 | 67% | 0% | 67% | effects | NEAT012 (hidden-state-read), NEAT013 |

## 4. AI reviewers and AI-authored PRs (separate populations)

Thread-opening comments by author type: human 213,054 (of which 5,971 on AI-authored PRs), **AI reviewer 139,846 (38.2% of all thread openers)**, other bots 12,972. In this 2024-10 to 2026-10 window, review of popular repositories is dominated by AI reviewers by volume.

| population | thread openers | resolved | outdated (code changed) | acted on (resolved or outdated) |
|---|---|---|---|---|
| human | 207,083 | 76.0% | 74.9% | 90.0% |
| ai_reviewer | 139,846 | 72.8% | 56.0% | 83.0% |
| bot | 12,972 | 59.5% | 55.8% | 76.5% |
| human_on_ai_pr | 5,971 | 70.1% | 73.6% | 89.6% |

Reading: AI-reviewer threads are resolved at about the human rate (73 vs 76 percent) but far fewer are outdated (56 vs 75 percent), i.e. the reviewed line changes less often after an AI comment; 'acted on' is therefore lower for AI reviewers (83 vs 90 percent). Resolution is a weak proxy: resolving a thread can mean dismissal. The measure is per PR with up to 30 threads.

### 4.1 What AI reviewers flag versus humans (labelled samples)

| group | AI reviewer (n=427) | human (post-strat, n=4203) |
|---|---|---|
| evolvability | 24.4% [20.5-28.6] | 49.4% [47.7-51.5] |
| functional | 68.6% [64.1-72.8] | 29.0% [27.0-31.0] |
| testing | 5.9% [4.0-8.5] | 4.3% [3.7-4.9] |
| other | 1.2% [0.5-2.7] | 17.3% [15.9-18.8] |

Category ratios (AI share / human share, smoothed, categories with at least 8 labelled comments across both populations):

| category | AI k | AI share | human k | human share (sample) | ratio |
|---|---|---|---|---|---|
| LOGIC-BUG | 131 | 30.7% | 281 | 6.7% | 4.6 |
| SECURITY | 18 | 4.2% | 51 | 1.2% | 3.5 |
| CONCURRENCY | 13 | 3.0% | 42 | 1.0% | 3.1 |
| EDGE-CASE | 28 | 6.6% | 101 | 2.4% | 2.8 |
| ERROR-HANDLING | 28 | 6.6% | 104 | 2.5% | 2.7 |
| RESOURCE-LIFETIME | 6 | 1.4% | 30 | 0.7% | 2.1 |
| USER-FACING | 25 | 5.9% | 154 | 3.7% | 1.6 |
| TEST-QUALITY | 20 | 4.7% | 124 | 3.0% | 1.6 |
| CONSISTENCY | 11 | 2.6% | 78 | 1.9% | 1.4 |
| PLATFORM-PORTABILITY | 4 | 0.9% | 32 | 0.8% | 1.4 |
| TYPE-SAFETY | 12 | 2.8% | 119 | 2.8% | 1.0 |
| LOGGING-OBS | 3 | 0.7% | 33 | 0.8% | 1.0 |
| DEPENDENCY-BUILD | 12 | 2.8% | 123 | 2.9% | 1.0 |
| PRAISE-ACK | 1 | 0.2% | 16 | 0.4% | 0.9 |
| TEST-MISSING | 5 | 1.2% | 60 | 1.4% | 0.9 |
| PERFORMANCE | 10 | 2.3% | 125 | 3.0% | 0.8 |
| DOCS-CHANGELOG | 25 | 5.9% | 317 | 7.5% | 0.8 |
| DOC-COMMENT | 18 | 4.2% | 251 | 6.0% | 0.7 |
| FORMAT-STYLE | 7 | 1.6% | 107 | 2.5% | 0.7 |
| API-COMPAT | 6 | 1.4% | 93 | 2.2% | 0.7 |
| DUPLICATION | 6 | 1.4% | 109 | 2.6% | 0.6 |
| DEAD-CODE | 13 | 3.0% | 256 | 6.1% | 0.5 |
| NAMING | 9 | 2.1% | 207 | 4.9% | 0.4 |
| MAGIC-CONFIG | 1 | 0.2% | 45 | 1.1% | 0.3 |
| SCOPE-PROCESS | 3 | 0.7% | 119 | 2.8% | 0.3 |
| DESIGN-STRUCTURE | 7 | 1.6% | 387 | 9.2% | 0.2 |
| SIMPLIFY-IDIOM | 4 | 0.9% | 254 | 6.0% | 0.2 |
| NOISE-OTHER | 1 | 0.2% | 132 | 3.1% | 0.1 |
| QUESTION-UNDERSTAND | 0 | 0.0% | 165 | 3.9% | 0.0 |
| SUGGESTION-ONLY | 0 | 0.0% | 288 | 6.9% | 0.0 |

AI reviewers over-flag LOGIC-BUG, ERROR-HANDLING, EDGE-CASE, SECURITY, CONCURRENCY and RESOURCE-LIFETIME (behavioural defects, often with an invented-looking scenario) and under-flag NAMING, DESIGN-STRUCTURE, QUESTION-UNDERSTAND, SUGGESTION-ONLY, SCOPE-PROCESS, DOC wording, and style, i.e. what needs project context or taste. Humans spend their comments on design, naming, docs and process; machines on local defect hypotheses.

### 4.2 Comments on AI-authored PRs (humans reviewing agents)

2,636 of 39,849 PRs are AI-authored (detection above); human reviewers left 5,971 thread openers on them. Labelled sample n=350.

| group | human on AI-authored PRs | human on human PRs (post-strat) |
|---|---|---|
| evolvability | 41.7% [36.7-46.9] | 49.4% [47.7-51.5] |
| functional | 37.1% [32.2-42.3] | 29.0% [27.0-31.0] |
| testing | 6.9% [4.7-10.0] | 4.3% [3.7-4.9] |
| other | 14.3% [11.0-18.3] | 17.3% [15.9-18.8] |
| category | k (AI PRs) | share on AI PRs | share on human PRs (sample) | ratio |
|---|---|---|---|---|
| CONCURRENCY | 9 | 2.6% | 1.0% | 2.3 |
| DEPENDENCY-BUILD | 18 | 5.1% | 2.9% | 1.7 |
| ERROR-HANDLING | 14 | 4.0% | 2.5% | 1.6 |
| CONSISTENCY | 10 | 2.9% | 1.9% | 1.5 |
| TEST-MISSING | 8 | 2.3% | 1.4% | 1.5 |
| TEST-QUALITY | 16 | 4.6% | 3.0% | 1.5 |
| PERFORMANCE | 15 | 4.3% | 3.0% | 1.4 |
| SCOPE-PROCESS | 14 | 4.0% | 2.8% | 1.4 |
| PRAISE-ACK | 2 | 0.6% | 0.4% | 1.3 |
| LOGIC-BUG | 29 | 8.3% | 6.7% | 1.2 |
| EDGE-CASE | 9 | 2.6% | 2.4% | 1.1 |
| USER-FACING | 14 | 4.0% | 3.7% | 1.1 |
| DOCS-CHANGELOG | 29 | 8.3% | 7.5% | 1.1 |
| DUPLICATION | 9 | 2.6% | 2.6% | 1.0 |
| SIMPLIFY-IDIOM | 22 | 6.3% | 6.0% | 1.0 |
| DOC-COMMENT | 18 | 5.1% | 6.0% | 0.9 |
| API-COMPAT | 7 | 2.0% | 2.2% | 0.9 |
| FORMAT-STYLE | 7 | 2.0% | 2.5% | 0.8 |
| DESIGN-STRUCTURE | 27 | 7.7% | 9.2% | 0.8 |
| TYPE-SAFETY | 8 | 2.3% | 2.8% | 0.8 |
| RESOURCE-LIFETIME | 2 | 0.6% | 0.7% | 0.8 |
| PLATFORM-PORTABILITY | 2 | 0.6% | 0.8% | 0.8 |
| SUGGESTION-ONLY | 19 | 5.4% | 6.9% | 0.8 |
| NOISE-OTHER | 9 | 2.6% | 3.1% | 0.8 |
| SECURITY | 3 | 0.9% | 1.2% | 0.7 |
| NAMING | 10 | 2.9% | 4.9% | 0.6 |
| DEAD-CODE | 12 | 3.4% | 6.1% | 0.6 |
| MAGIC-CONFIG | 2 | 0.6% | 1.1% | 0.6 |
| QUESTION-UNDERSTAND | 6 | 1.7% | 3.9% | 0.5 |

On AI-authored PRs reviewers lean toward scope/process (PR hygiene, unrelated changes), dependency/build and test concerns, and correctness of generated code; the per-category ratios have wide intervals at n=350 and should be read as hypotheses. PRs by AI agents get fewer CHANGES_REQUESTED (11.6 vs 19.6 percent of PRs; most-commented sample) and more threads (15.2 vs 13.9 per PR).

## 5. Q2: refactorings and the smell or need that motivated them

Denominator: 800 sampled commits whose message matched `refactor` (650) or `cleanup` (150); labelled by reading the message. **491 are genuine refactorings by their message (61.4%)**, 144 are features or mixed changes that merely use the word (R-NOT-REFACTOR), 165 are really fixes, tests, dependency or data changes. Genuine rate with 95 percent CI: `refactor` word 65.8% [62-69], `cleanup` word 42.0% [34-50]. This is the measured false-positive rate of keyword-based refactoring detection (cf. Murphy-Hill et al. as cited in Silva et al. 2016).

### 5.1 Motivation table (genuine refactorings, sample shares with Wilson 95 percent CI)

| motivation | definition | k | share of 491 [95% CI] | tier | seed |
|---|---|---|---|---|---|
| R-DESIGN-STRUCTURE | move/split/merge classes or modules, layering, ownership | 98 | 20.0% [16.7-23.7] | human | Silva:decompose class, move |
| R-DEAD-CODE | remove unused or obsolete code, flags, dependencies | 79 | 16.1% [13.1-19.6] | structural | Silva:remove dead code |
| R-READABILITY | improve readability/understandability, decompose a long function | 71 | 14.5% [11.6-17.8] | human | Silva:improve readability |
| R-SIMPLIFY | simplify logic or conditions, fewer branches | 51 | 10.4% [8.0-13.4] | structural | AlOmar:simplify |
| R-DUPLICATION | remove duplicated code | 39 | 7.9% [5.9-10.7] | structural | Silva:remove duplication |
| R-API-MIGRATION | migrate to new/deprecated API, modernize language usage, upgrade | 30 | 6.1% [4.3-8.6] | types | Silva:backward compatibility |
| R-PERFORMANCE | refactor for speed or memory | 28 | 5.7% [4.0-8.1] | effects | open coding |
| R-TESTABILITY | make code testable, dependency injection | 22 | 4.5% [3.0-6.7] | human | Silva:improve testability |
| R-ENABLE-CHANGE | prepare for a feature or fix | 20 | 4.1% [2.7-6.2] | human | Silva:facilitate extension |
| R-NAMING | rename for clarity or consistency | 18 | 3.7% [2.3-5.7] | human | Silva:rename |
| R-TYPE-SAFETY | stronger types, remove casts/any, nullability | 17 | 3.5% [2.2-5.5] | types | open coding |
| R-TOOLING-LINT | forced by linter, formatter, warning, or static analysis | 10 | 2.0% [1.1-3.7] | syntax | open coding |
| R-ERROR-HANDLING | restructure error handling or logging | 5 | 1.0% [0.4-2.4] | effects | open coding |
| R-CONSISTENCY | align with conventions elsewhere | 3 | 0.6% [0.2-1.8] | human | Sadowski:consistency |

Comparison with Silva et al. 2016 (arXiv 1607.02459, 44 motivations over 12 refactoring types, mostly Java): their headline is that refactoring is driven mainly by requirement changes rather than code smells; for Extract Method the three most frequent motives they report after reuse are readability (21 instances), facilitating extension (15) and removing duplication (14), then testability (6). Our message-based codes are coarser, but the picture matches: design restructuring, dead-code removal, readability and simplification dominate; explicit duplication removal is a minority (about 8 percent); R-ENABLE-CHANGE (prepare for a feature or fix) is only 4 percent here because commit messages rarely say it, while Silva et al. obtained it by asking the developers directly. Refactors motivated by a linter, formatter or compiler warning (R-TOOLING-LINT) are 2 percent: tool-forced refactoring is rare in the history.

What the table says for linting: three of the top five motivations (dead code 16 percent, duplication 8 percent, simplification 10 percent) are mechanically detectable smells that maintainers later remove by hand; naming (4 percent) and type-safety (3.5 percent) refactors are the cheap-to-detect remainder.

Typical size (median of the commits whose diff stats were fetched; additions, deletions, files):

| motivation | n with stats | median additions | median deletions | median files |
|---|---|---|---|---|
| R-READABILITY | 44 | 47.0 | 51.5 | 3.0 |
| R-DUPLICATION | 17 | 49 | 51 | 4 |
| R-DESIGN-STRUCTURE | 39 | 210 | 94 | 7 |
| R-NAMING | 12 | 29.0 | 22.5 | 4.5 |
| R-DEAD-CODE | 38 | 13.0 | 51.0 | 5.0 |
| R-SIMPLIFY | 28 | 29.5 | 37.0 | 2.0 |
| R-TESTABILITY | 11 | 61 | 22 | 3 |
| R-ENABLE-CHANGE | 17 | 142 | 49 | 6 |
| R-API-MIGRATION | 19 | 34 | 25 | 4 |
| R-PERFORMANCE | 14 | 118.0 | 20.5 | 2.0 |
| R-TYPE-SAFETY | 10 | 89.0 | 62.5 | 3.0 |
| R-NOT-REFACTOR | 86 | 325.5 | 63.5 | 9.0 |

By repository primary language (genuine refactorings, top motivations):

| language | n | top motivations (k) |
|---|---|---|
| Rust | 45 | R-DESIGN-STRUCTURE 12; R-READABILITY 7; R-DEAD-CODE 6; R-ENABLE-CHANGE 3; R-PERFORMANCE 3 |
| C++ | 44 | R-READABILITY 9; R-DEAD-CODE 8; R-DESIGN-STRUCTURE 8; R-API-MIGRATION 5; R-DUPLICATION 3 |
| PHP | 42 | R-READABILITY 12; R-SIMPLIFY 7; R-TESTABILITY 5; R-DEAD-CODE 4; R-DESIGN-STRUCTURE 4 |
| Java | 41 | R-DEAD-CODE 6; R-DESIGN-STRUCTURE 5; R-READABILITY 5; R-PERFORMANCE 5; R-API-MIGRATION 5 |
| C | 40 | R-DUPLICATION 7; R-DESIGN-STRUCTURE 7; R-PERFORMANCE 6; R-DEAD-CODE 5; R-NAMING 3 |
| Kotlin | 36 | R-DESIGN-STRUCTURE 9; R-READABILITY 6; R-ENABLE-CHANGE 6; R-SIMPLIFY 4; R-API-MIGRATION 3 |
| JavaScript | 36 | R-SIMPLIFY 9; R-DESIGN-STRUCTURE 7; R-READABILITY 5; R-DEAD-CODE 4; R-PERFORMANCE 3 |
| TypeScript | 36 | R-DEAD-CODE 8; R-DESIGN-STRUCTURE 7; R-DUPLICATION 4; R-SIMPLIFY 4; R-READABILITY 4 |
| Go | 34 | R-DESIGN-STRUCTURE 8; R-READABILITY 5; R-SIMPLIFY 4; R-DEAD-CODE 4; R-DUPLICATION 3 |
| Ruby | 33 | R-DUPLICATION 7; R-DEAD-CODE 7; R-SIMPLIFY 6; R-READABILITY 5; R-DESIGN-STRUCTURE 3 |
| C# | 33 | R-DEAD-CODE 8; R-READABILITY 7; R-DESIGN-STRUCTURE 6; R-NAMING 3; R-SIMPLIFY 2 |
| Swift | 30 | R-DESIGN-STRUCTURE 11; R-DEAD-CODE 7; R-SIMPLIFY 2; R-TOOLING-LINT 2; R-TESTABILITY 2 |
| Python | 26 | R-DESIGN-STRUCTURE 9; R-DEAD-CODE 3; R-TESTABILITY 3; R-SIMPLIFY 2; R-API-MIGRATION 2 |

## 6. Q3: mistakes that escape review (fix and revert commits)

Denominator: 600 sampled commits whose message matched `fix`, and 200 matching `revert`; frame = 683 repositories (57,720 fix, 20,157 revert, 29,023 refactor and 19,189 cleanup commits retained; at most the 100 latest per repo and word). A message only shows intent: whether the mistake had passed code review is NOT known; these are mistakes that were merged and later fixed. The word `fix` also matches fixes that are not mistakes (docs, build, tests).

### 6.1 What `fix` commits fix (sample shares, Wilson 95 percent CI)

| category | definition | k | share of 600 [95% CI] | class |
|---|---|---|---|---|
| F-LOGIC | wrong condition or algorithm, off-by-one | 167 | 27.8% [24.4-31.6] | mistake |
| F-DOC-TYPO | typo, doc or comment fix | 55 | 9.2% [7.1-11.7] | non-mistake |
| F-BUILD-DEPS-CI | build, dependency, packaging or CI breakage | 48 | 8.0% [6.1-10.4] | non-mistake |
| F-UI-RENDER | rendering, layout, UI text or UX bug | 46 | 7.7% [5.8-10.1] | mistake |
| F-OTHER | unclear or not a mistake (feature/chore) | 34 | 5.7% [4.1-7.8] | non-mistake |
| F-NULL-EDGE | null/None/undefined/empty/boundary input not handled | 33 | 5.5% [3.9-7.6] | mistake |
| F-TEST | fix a broken or flaky test | 27 | 4.5% [3.1-6.5] | non-mistake |
| F-PLATFORM-COMPAT | OS, browser, version or toolchain incompatibility | 24 | 4.0% [2.7-5.9] | mistake |
| F-STATE-INIT | wrong initialisation, lifecycle or ordering of state | 20 | 3.3% [2.2-5.1] | mistake |
| F-SECURITY | security vulnerability fix | 18 | 3.0% [1.9-4.7] | mistake |
| F-CONFIG-DEFAULT | wrong default, flag or configuration value | 17 | 2.8% [1.8-4.5] | mistake |
| F-CONCURRENCY | race, deadlock, async ordering, stale state | 15 | 2.5% [1.5-4.1] | mistake |
| F-ERROR-HANDLING | missing or wrong error/exception path | 14 | 2.3% [1.4-3.9] | mistake |
| F-MISSING-CASE | unhandled variant/feature gap/incomplete implementation | 12 | 2.0% [1.1-3.5] | mistake |
| R-NOT-REFACTOR | message says refactor but the change is a feature, fix or docs | 12 | 2.0% [1.1-3.5] | non-mistake |
| F-API-MISUSE | wrong function/argument/arg order, wrong identifier | 11 | 1.8% [1.0-3.3] | mistake |
| F-PERF | performance regression or hang | 11 | 1.8% [1.0-3.3] | mistake |
| F-RESOURCE | leak, lifetime, use-after-free, overflow | 10 | 1.7% [0.9-3.0] | mistake |
| F-TYPE-CAST | type confusion, wrong cast, numeric overflow, wrong unit | 9 | 1.5% [0.8-2.8] | mistake |
| R-DEAD-CODE | remove unused or obsolete code, flags, dependencies | 5 | 0.8% [0.4-1.9] | non-mistake |
| R-DESIGN-STRUCTURE | move/split/merge classes or modules, layering, ownership | 3 | 0.5% [0.2-1.5] | non-mistake |
| F-REGRESSION-REVERT | revert of a change that broke something | 2 | 0.3% [0.1-1.2] | non-mistake |
| R-DUPLICATION | remove duplicated code | 2 | 0.3% [0.1-1.2] | non-mistake |
| R-API-MIGRATION | migrate to new/deprecated API, modernize language usage, upgrade | 2 | 0.3% [0.1-1.2] | non-mistake |
| R-NAMING | rename for clarity or consistency | 1 | 0.2% [0.0-0.9] | non-mistake |
| R-SIMPLIFY | simplify logic or conditions, fewer branches | 1 | 0.2% [0.0-0.9] | non-mistake |
| R-TYPE-SAFETY | stronger types, remove casts/any, nullability | 1 | 0.2% [0.0-0.9] | non-mistake |

**407 of 600 `fix` commits (67.8%, 95 percent CI 64-71) fix a genuine code mistake**; the rest are docs/typos, build and dependency bumps, test fixes, data additions and feature work labelled as fixes.

### 6.2 The escaped-mistake table (mistake fixes only)

| fixed mistake | definition | k | share of 407 [95% CI] | candidate | tier | existing rule / status |
|---|---|---|---|---|---|---|
| F-LOGIC | wrong condition or algorithm, off-by-one | 167 | 41.0% [36.4-45.9] | C42 | human | none mechanical (tests/review); bound analyzers catch subsets |
| F-UI-RENDER | rendering, layout, UI text or UX bug | 46 | 11.3% [8.6-14.7] | C38 | render | A11Y (v1 web families), crunk; i18n new candidate |
| F-NULL-EDGE | null/None/undefined/empty/boundary input not handled | 33 | 8.1% [5.8-11.2] | C29 | types | new candidate (nullability and bounds lint; bound tools: clippy, TS strict, mypy) |
| F-PLATFORM-COMPAT | OS, browser, version or toolchain incompatibility | 24 | 5.9% [4.0-8.6] | C37 | human | new candidate (cfg/ifdef gating) |
| F-STATE-INIT | wrong initialisation, lifecycle or ordering of state | 20 | 4.9% [3.2-7.5] | C49 | effects | new candidate |
| F-SECURITY | security vulnerability fix | 18 | 4.4% [2.8-6.9] | C34 | effects | SEC001-003/SEC110 (lexical secrets, R21); WEBSEC; new candidate for injection |
| F-CONFIG-DEFAULT | wrong default, flag or configuration value | 17 | 4.2% [2.6-6.6] | C18 | structural | NEAT009 (magic-value) |
| F-CONCURRENCY | race, deadlock, async ordering, stale state | 15 | 3.7% [2.2-6.0] | C32 | effects | RACE001/002 (v1, R34); new candidate |
| F-ERROR-HANDLING | missing or wrong error/exception path | 14 | 3.4% [2.1-5.7] | C30 | effects | EXHAUST001-004 (v1 Python-semantic, R34); new candidate generally |
| F-MISSING-CASE | unhandled variant/feature gap/incomplete implementation | 12 | 2.9% [1.7-5.1] | C50 | types | NEAT026 (exhaustive-match, designed); bound compilers |
| F-API-MISUSE | wrong function/argument/arg order, wrong identifier | 11 | 2.7% [1.5-4.8] | C48 | types | new candidate (arity/type check; param-name vs argument-name lint) |
| F-PERF | performance regression or hang | 11 | 2.7% [1.5-4.8] | C33 | effects | PERF001-018 v1 lexical perf (R33) |
| F-RESOURCE | leak, lifetime, use-after-free, overflow | 10 | 2.5% [1.3-4.5] | C31 | effects | new candidate (RAII/leak lint; bound tools) |
| F-TYPE-CAST | type confusion, wrong cast, numeric overflow, wrong unit | 9 | 2.2% [1.2-4.1] | C40 | types | NEAT020-026 (type rules, designed); bound tools |

Most common specific mistakes inside the classes (labelled tag -> count): F-NULL-EDGE: out-of-bounds 2, unaligned-access 1, unknown-locale 1, index-out-of-bounds 1; F-STATE-INIT: environment-clearing 1, stale-error-state 1, conditional-registration 1, quit-handling 1; F-CONCURRENCY: hello-rejection 1, overwriting-mode 1, cache-races 1, blocking-read 1; F-ERROR-HANDLING: theme-access-guard 1, warning-exception 1, hook-config 1, failure-preservation 1; F-RESOURCE: fd-leak 1, eager-copy 1, fsync-directory 1, disconnect-websocket 1; F-SECURITY: dependency-cve 3, ssrf 1, leak-block 1, build-isolation 1.

By repository primary language (mistake share of fix commits and top classes):

| language | n fix commits | mistake share | top classes |
|---|---|---|---|
| C# | 46 | 67% | F-LOGIC 14; F-DOC-TYPO 5; F-UI-RENDER 5; F-BUILD-DEPS-CI 3 |
| JavaScript | 46 | 76% | F-LOGIC 12; F-DOC-TYPO 5; F-UI-RENDER 4; F-PERF 4 |
| Python | 46 | 74% | F-LOGIC 15; F-BUILD-DEPS-CI 4; F-CONFIG-DEFAULT 4; F-TEST 3 |
| C++ | 46 | 57% | F-LOGIC 10; F-DOC-TYPO 6; F-TEST 4; F-STATE-INIT 4 |
| Rust | 46 | 78% | F-LOGIC 22; F-STATE-INIT 4; R-NOT-REFACTOR 3; F-UI-RENDER 3 |
| Java | 46 | 61% | F-LOGIC 12; F-DOC-TYPO 8; F-OTHER 4; F-BUILD-DEPS-CI 3 |
| TypeScript | 46 | 74% | F-LOGIC 13; F-UI-RENDER 8; F-BUILD-DEPS-CI 5; F-DOC-TYPO 3 |
| C | 46 | 67% | F-LOGIC 11; F-BUILD-DEPS-CI 7; F-NULL-EDGE 5; F-RESOURCE 4 |
| Go | 45 | 78% | F-LOGIC 18; F-NULL-EDGE 4; F-DOC-TYPO 4; F-SECURITY 2 |
| Swift | 45 | 56% | F-LOGIC 7; F-UI-RENDER 6; F-DOC-TYPO 6; F-OTHER 5 |
| Ruby | 45 | 60% | F-LOGIC 11; F-BUILD-DEPS-CI 8; F-TEST 4; F-OTHER 4 |
| PHP | 44 | 73% | F-LOGIC 12; F-SECURITY 5; F-CONFIG-DEFAULT 4; F-DOC-TYPO 4 |
| Kotlin | 43 | 58% | F-LOGIC 8; F-OTHER 7; F-PLATFORM-COMPAT 5; F-DOC-TYPO 4 |

### 6.3 Reverts

156 of 200 `revert` commits (78.0% [72-83]) are real reverts of an earlier change; the rest merely contain the word (e.g. a revert inside a squashed feature or a revert-and-reapply). Only 37.0% of revert messages state a reason at all (words such as breaks, fails, regression, crash, CI), so the reason for most reverts cannot be mined from messages; where stated the reasons are build or CI breakage, a regression in another feature, and premature or unwanted merge. Median revert touches 2.0 files (+13.0 / -21.0 lines). A revert is a late signal that the review and CI gates both passed a bad change.

### 6.4 Single-statement bug patterns in 1000 Java projects (ManySStuBs4J)

Source: Karampatsis and Sutton 2020 (Zenodo 3653444, sstubsLarge): 63,923 single-statement bug fixes from 634 Java projects (these are Java-only, mined from fix commits that change exactly one statement, so they are a lower bound on the share of trivial one-token mistakes).

| bug type | meaning | k | share [95% CI] | projects | tier (miner judgement) |
|---|---|---|---|---|---|
| CHANGE_IDENTIFIER | wrong variable/field/name used | 22668 | 35.5% [35.1-35.8] | 528 | types or human |
| DIFFERENT_METHOD_SAME_ARGS | wrong method called with same arguments | 10179 | 15.9% [15.6-16.2] | 425 | human |
| CHANGE_NUMERAL | wrong numeric constant | 5447 | 8.5% [8.3-8.7] | 329 | human |
| OVERLOAD_METHOD_MORE_ARGS | wrong overload (more arguments) | 5100 | 8.0% [7.8-8.2] | 328 | types |
| CHANGE_MODIFIER | wrong modifier (final/static/visibility) | 5011 | 7.8% [7.6-8.1] | 302 | structural |
| LESS_SPECIFIC_IF | condition weakened/relaxed | 2813 | 4.4% [4.2-4.6] | 238 | human |
| MORE_SPECIFIC_IF | condition strengthened | 2381 | 3.7% [3.6-3.9] | 234 | human |
| CHANGE_OPERATOR | wrong binary operator | 2241 | 3.5% [3.4-3.7] | 268 | human |
| SWAP_BOOLEAN_LITERAL | true/false swapped | 1842 | 2.9% [2.8-3.0] | 186 | human |
| OVERLOAD_METHOD_DELETED_ARGS | wrong overload (fewer arguments) | 1588 | 2.5% [2.4-2.6] | 192 | types |
| CHANGE_CALLER_IN_FUNCTION_CALL | wrong receiver object | 1504 | 2.4% [2.2-2.5] | 213 | types or human |
| CHANGE_UNARY_OPERATOR | wrong unary operator | 1016 | 1.6% [1.5-1.7] | 188 | human |
| CHANGE_OPERAND | wrong operand | 807 | 1.3% [1.2-1.4] | 160 | human |
| SWAP_ARGUMENTS | arguments swapped | 612 | 1.0% [0.9-1.0] | 116 | types (param/arg name mismatch) |
| DELETE_THROWS_EXCEPTION | throws clause removed | 508 | 0.8% [0.7-0.9] | 43 | types |
| ADD_THROWS_EXCEPTION | throws clause added | 206 | 0.3% [0.3-0.4] | 49 | types |

Read with 6.2: the dominant one-statement mistakes are the wrong name (identifier 35 percent, method 16 percent, receiver 2 percent) and the wrong value (numeral 9 percent, operator and boolean 8 percent combined); wrong-arity overloads (10 percent) and swapped arguments (1 percent) are type-checkable. This supports candidate C48 (wrong function / argument / identifier), whose automatable part is arity and parameter-name-versus-argument-name checks.

## 7. Ranked candidate list

Evidence score (heuristic, documented so the coordinator can reweight; practitioner consensus is the coordinator's factor): `score = review_share_pct x (1 + 2*B - N) + 0.5 * fix_share_pct + 0.25 * refactor_share_pct`, where review_share is the post-stratified share of human review comments (section 3.6), B and N are the shares of that candidate's comments carrying a blocking or nit mark, fix_share is the share of mistake-fixing commits whose class maps to the candidate, refactor_share is the share of genuine refactorings whose motivation maps to it. Tier is the miner's judgement; 'exists' means the frob-v2 catalogue already has a rule id.

### 7.1 All candidates ranked

| rank | id | candidate | score | review % | blocking | fix % | refactor % | tier | existing rule / status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C42 | logic error: wrong condition, wrong value, regression | 26.0 | 5.4% | 63% | 27.8 | 0.0 | human | none mechanical (tests/review); bound analyzers catch subsets |
| 2 | C16 | needlessly complex expression or control flow; simplify | 10.5 | 5.0% | 1% | 0.0 | 24.8 | structural | NEAT005 (cognitive complexity), bound linters |
| 3 | C02 | unused import / variable / parameter / function | 10.2 | 5.7% | 7% | 0.0 | 16.1 | structural | DEAD (v2 designed; v1 DEAD001); compiler/linter unused warnings |
| 4 | C46 | documentation prose quality (wording, structure, examples) | 9.5 | 8.9% | 6% | 0.0 | 0.0 | human | n/a (prose lint bound tools) |
| 5 | C36 | CI/build/dependency: unpinned version, wrong version, permissions, cache key | 8.3 | 2.8% | 27% | 8.0 | 0.0 | structural | CI001 (pinned-ref), CI003, CI006/007/010, VET001-012 (supply chain) |
| 6 | C29 | missing null/empty/boundary/invalid-input handling | 8.0 | 2.9% | 40% | 5.5 | 0.0 | types | new candidate (nullability and bounds lint; bound tools: clippy, TS strict, mypy) |
| 7 | C43 | design discussion or alternative approach (no concrete defect) | 7.8 | 6.5% | 11% | 0.0 | 0.0 | human | n/a |
| 8 | C38 | user-visible string untranslated, hard-coded or accessibility label missing | 7.4 | 2.7% | 19% | 7.7 | 0.0 | render | A11Y (v1 web families), crunk; i18n new candidate |
| 9 | C47 | code suggestion block with no stated reason | 6.5 | 6.5% | 0% | 0.0 | 0.0 | human | n/a |
| 10 | C33 | needless work in a hot path: N+1, clone/alloc, repeated lookup, work per frame | 6.4 | 3.0% | 23% | 1.8 | 5.7 | effects | PERF001-018 v1 lexical perf (R33) |
| 11 | C23 | mixed concerns or abstraction levels; coupling across layers | 5.5 | 0.4% | 25% | 0.0 | 20.0 | structural | COH003 (mixed abstraction levels), COH001, ARCH104 |
| 12 | C09 | typo, grammar or wording error in text | 5.5 | 1.9% | 0% | 9.2 | 0.0 | syntax | new candidate (spell checker bound tool) |
| 13 | C30 | error swallowed, ignored, mis-propagated or panic instead of error | 5.4 | 2.5% | 29% | 2.3 | 1.0 | effects | EXHAUST001-004 (v1 Python-semantic, R34); new candidate generally |
| 14 | C13 | unclear, misleading or inconsistent identifier name | 5.1 | 4.4% | 7% | 0.0 | 3.7 | human | new candidate (name-vs-behaviour is judgement) |
| 15 | C03 | duplicated logic or copy-paste | 4.4 | 2.2% | 8% | 0.0 | 7.9 | structural | DUP001-003 (clone ladder R19) |
| 16 | C40 | type weakness: any/object/unchecked cast, string-typed, optional where required | 4.3 | 2.1% | 17% | 1.5 | 3.5 | types | NEAT020-026 (type rules, designed); bound tools |
| 17 | C45 | question: reviewer asks why / what / how | 4.2 | 4.2% | 0% | 0.0 | 0.0 | human | n/a |
| 18 | C25 | unrelated change in the PR; scope creep; should be split or reverted | 4.1 | 2.3% | 40% | 0.0 | 0.0 | human | R05 diff accountability (COV002/COV008 v1); SCOPE001 is lease-based; new for scope-of-diff |
| 19 | C34 | security: injection, secret in log, missing authz, unsafe input handling | 4.0 | 1.1% | 63% | 3.0 | 0.0 | effects | SEC001-003/SEC110 (lexical secrets, R21); WEBSEC; new candidate for injection |
| 20 | C28 | test does not exercise the fix, asserts weakly, or tests a mock | 3.5 | 0.9% | 28% | 4.5 | 0.0 | human | R06 test tiers/evidence (partly); new candidate for vacuous asserts |
| 21 | C37 | platform portability: OS-specific path, API or version assumption | 3.4 | 0.7% | 55% | 4.0 | 0.0 | types | new candidate (cfg/ifdef gating) |
| 22 | C49 | state initialised or ordered wrongly (lifecycle, init order, stale state) | 3.2 | 0.6% | 77% | 3.3 | 0.0 | effects | new candidate |
| 23 | C32 | concurrency: race, lock misuse, blocking in async, stale closure | 3.2 | 0.9% | 58% | 2.5 | 0.0 | effects | RACE001/002 (v1, R34); new candidate |
| 24 | C27 | missing test for new behaviour or a covered branch | 3.1 | 1.4% | 22% | 0.0 | 4.5 | structural | COV001 (untested-public-function), TEST001, R04 test reach |
| 25 | C18 | magic number, hard-coded string/path/colour that should be a constant or config | 2.8 | 1.2% | 12% | 2.8 | 0.0 | syntax | NEAT009 (magic-value) |
| 26 | C31 | resource leak, missing cleanup, ownership or lifetime error | 2.6 | 0.8% | 60% | 1.7 | 0.0 | effects | new candidate (RAII/leak lint; bound tools) |
| 27 | C17 | use the idiomatic standard-library or language feature | 2.0 | 0.7% | 4% | 0.0 | 6.1 | types | bound linters (clippy, ruff UP/SIM, clang-tidy modernize) |
| 28 | C12 | formatting, indentation, whitespace, blank line, import order, line length | 2.0 | 2.7% | 10% | 0.0 | 2.0 | syntax | bound formatter/linter (FMT001/002 v1; TOOL001 stages) |
| 29 | C41 | public-API design shape: argument shape, builder, accessor, naming of API | 1.8 | 1.4% | 16% | 0.0 | 0.0 | human | new candidate |
| 30 | C44 | consistency with existing conventions elsewhere in the codebase | 1.7 | 1.4% | 12% | 0.0 | 0.6 | human | n/a (project-specific convention rules via policy patterns) |
| 31 | C20 | code placed in the wrong file, module or layer | 1.7 | 1.4% | 14% | 0.0 | 0.0 | structural | ARCH104 layering (R17), INV002 forbidden-import, CYCLE001 |
| 32 | C48 | wrong function, wrong argument, swapped arguments or wrong identifier used | 1.5 | 0.3% | 64% | 1.8 | 0.0 | types | new candidate (arity/type check; param-name vs argument-name lint) |
| 33 | C06 | stale, inaccurate or contradictory comment or doc | 1.4 | 0.8% | 39% | 0.0 | 0.0 | structural | DRIFT001-004 (doc-binding drift) for bound docs; otherwise new |
| 34 | C50 | incomplete handling of a variant, enum case or input class (non-exhaustive) | 1.3 | 0.2% | 33% | 2.0 | 0.0 | types | NEAT026 (exhaustive-match, designed); bound compilers |
| 35 | C05 | missing or inadequate docstring / API doc comment | 1.2 | 0.8% | 24% | 0.0 | 0.0 | structural | DOC001 (undocumented-public-item) |
| 36 | C35 | breaking public API change or missing deprecation | 1.2 | 0.5% | 67% | 0.0 | 0.0 | types | DEPR001-006 (R24), BIND001/002 (R30); new candidate for API diff |
| 37 | C04 | reinvents an existing helper, constant or library API | 1.2 | 1.1% | 7% | 0.0 | 0.0 | types | new candidate |
| 38 | C39 | logging: wrong level, noisy, sensitive content, log vs return | 1.1 | 0.8% | 22% | 0.0 | 0.0 | human | new candidate |
| 39 | C10 | broken link, stale reference or missing doc entry | 0.9 | 0.7% | 17% | 0.0 | 0.0 | structural | DOC002 (broken-markdown-link), DRIFT002 |
| 40 | C14 | identifier violates the naming convention (case, prefix, plural) | 0.7 | 0.7% | 10% | 0.0 | 0.0 | syntax | bound linter (ruff N8xx, clippy style); new candidate for frob |
| 41 | C26 | PR hygiene: commit structure, license header, process requirement | 0.7 | 0.4% | 42% | 0.0 | 0.0 | structural | new candidate (license header exists in v1 policy families) |
| 42 | C19 | visibility wider than needed (pub, public, exported) | 0.6 | 0.5% | 20% | 0.0 | 0.0 | structural | new candidate (vis vs references_to) |
| 43 | C01 | commented-out code or leftover debug output | 0.6 | 0.3% | 58% | 0.0 | 0.0 | syntax | NARR001-005 (comment hygiene), TODO001/002 |
| 44 | C08 | missing why-comment or unexplained magic behaviour | 0.5 | 0.5% | 0% | 0.0 | 0.0 | human | NARR004 (rationale must reference decisions) partly |
| 45 | C07 | redundant, verbose or obvious comment | 0.5 | 0.5% | 0% | 0.0 | 0.0 | syntax | NARR001/NARR004 (comment hygiene) |
| 46 | C21 | function or class too long or doing too much; extract | 0.5 | 0.5% | 0% | 0.0 | 0.0 | structural | NEAT001 (function-too-long), COH001-004 |
| 47 | C24 | global or shared mutable state; mutation of arguments | 0.4 | 0.2% | 67% | 0.0 | 0.0 | effects | NEAT012 (hidden-state-read), NEAT013 |
| 48 | C22 | too many parameters, boolean flag parameter, or options-object missing | 0.3 | 0.3% | 0% | 0.0 | 0.0 | syntax | NEAT002 (param count), NEAT003 (boolean flag) |
| 49 | C11 | changelog, release note or changeset missing or in wrong category | 0.3 | 0.2% | 22% | 0.0 | 0.0 | structural | REL003 (changelog-fragment-required) |
| 50 | C15 | deep nesting; use early return, guard or continue | 0.2 | 0.4% | 0% | 0.0 | 0.0 | structural | NEAT004 (nesting-depth), NEAT005 |

### 7.2 Top 30 machine-detectable candidates (tiers syntax, structural, types, effects)

| # | id | candidate | score | tier | status | rule mapping |
|---|---|---|---|---|---|---|
| 1 | C16 | needlessly complex expression or control flow; simplify | 10.5 | structural | exists | NEAT005 (cognitive complexity), bound linters |
| 2 | C02 | unused import / variable / parameter / function | 10.2 | structural | exists | DEAD (v2 designed; v1 DEAD001); compiler/linter unused warnings |
| 3 | C36 | CI/build/dependency: unpinned version, wrong version, permissions, cache key | 8.3 | structural | exists | CI001 (pinned-ref), CI003, CI006/007/010, VET001-012 (supply chain) |
| 4 | C29 | missing null/empty/boundary/invalid-input handling | 8.0 | types | new candidate | new candidate (nullability and bounds lint; bound tools: clippy, TS strict, mypy) |
| 5 | C33 | needless work in a hot path: N+1, clone/alloc, repeated lookup, work per frame | 6.4 | effects | exists | PERF001-018 v1 lexical perf (R33) |
| 6 | C23 | mixed concerns or abstraction levels; coupling across layers | 5.5 | structural | exists | COH003 (mixed abstraction levels), COH001, ARCH104 |
| 7 | C09 | typo, grammar or wording error in text | 5.5 | syntax | new candidate | new candidate (spell checker bound tool) |
| 8 | C30 | error swallowed, ignored, mis-propagated or panic instead of error | 5.4 | effects | new candidate | EXHAUST001-004 (v1 Python-semantic, R34); new candidate generally |
| 9 | C03 | duplicated logic or copy-paste | 4.4 | structural | exists | DUP001-003 (clone ladder R19) |
| 10 | C40 | type weakness: any/object/unchecked cast, string-typed, optional where required | 4.3 | types | exists | NEAT020-026 (type rules, designed); bound tools |
| 11 | C34 | security: injection, secret in log, missing authz, unsafe input handling | 4.0 | effects | new candidate | SEC001-003/SEC110 (lexical secrets, R21); WEBSEC; new candidate for injection |
| 12 | C37 | platform portability: OS-specific path, API or version assumption | 3.4 | types | new candidate | new candidate (cfg/ifdef gating) |
| 13 | C49 | state initialised or ordered wrongly (lifecycle, init order, stale state) | 3.2 | effects | new candidate | new candidate |
| 14 | C32 | concurrency: race, lock misuse, blocking in async, stale closure | 3.2 | effects | new candidate | RACE001/002 (v1, R34); new candidate |
| 15 | C27 | missing test for new behaviour or a covered branch | 3.1 | structural | exists | COV001 (untested-public-function), TEST001, R04 test reach |
| 16 | C18 | magic number, hard-coded string/path/colour that should be a constant or config | 2.8 | syntax | exists | NEAT009 (magic-value) |
| 17 | C31 | resource leak, missing cleanup, ownership or lifetime error | 2.6 | effects | new candidate | new candidate (RAII/leak lint; bound tools) |
| 18 | C17 | use the idiomatic standard-library or language feature | 2.0 | types | partial | bound linters (clippy, ruff UP/SIM, clang-tidy modernize) |
| 19 | C12 | formatting, indentation, whitespace, blank line, import order, line length | 2.0 | syntax | exists | bound formatter/linter (FMT001/002 v1; TOOL001 stages) |
| 20 | C20 | code placed in the wrong file, module or layer | 1.7 | structural | exists | ARCH104 layering (R17), INV002 forbidden-import, CYCLE001 |
| 21 | C48 | wrong function, wrong argument, swapped arguments or wrong identifier used | 1.5 | types | new candidate | new candidate (arity/type check; param-name vs argument-name lint) |
| 22 | C06 | stale, inaccurate or contradictory comment or doc | 1.4 | structural | exists | DRIFT001-004 (doc-binding drift) for bound docs; otherwise new |
| 23 | C50 | incomplete handling of a variant, enum case or input class (non-exhaustive) | 1.3 | types | exists | NEAT026 (exhaustive-match, designed); bound compilers |
| 24 | C05 | missing or inadequate docstring / API doc comment | 1.2 | structural | exists | DOC001 (undocumented-public-item) |
| 25 | C35 | breaking public API change or missing deprecation | 1.2 | types | new candidate | DEPR001-006 (R24), BIND001/002 (R30); new candidate for API diff |
| 26 | C04 | reinvents an existing helper, constant or library API | 1.2 | types | new candidate | new candidate |
| 27 | C10 | broken link, stale reference or missing doc entry | 0.9 | structural | exists | DOC002 (broken-markdown-link), DRIFT002 |
| 28 | C14 | identifier violates the naming convention (case, prefix, plural) | 0.7 | syntax | new candidate | bound linter (ruff N8xx, clippy style); new candidate for frob |
| 29 | C26 | PR hygiene: commit structure, license header, process requirement | 0.7 | structural | new candidate | new candidate (license header exists in v1 policy families) |
| 30 | C19 | visibility wider than needed (pub, public, exported) | 0.6 | structural | new candidate | new candidate (vis vs references_to) |

### 7.3 Not lintable (tier human or render) but frequent: signals for review automation or docs

| id | candidate | review % | tier | note |
|---|---|---|---|---|
| C42 | logic error: wrong condition, wrong value, regression | 5.4% | human | largest functional class |
| C46 | documentation prose quality (wording, structure, examples) | 8.9% | human | residual |
| C43 | design discussion or alternative approach (no concrete defect) | 6.5% | human | not lintable |
| C38 | user-visible string untranslated, hard-coded or accessibility label missing | 2.7% | render | render/markup tier |
| C47 | code suggestion block with no stated reason | 6.5% | human | content unknown |
| C13 | unclear, misleading or inconsistent identifier name | 4.4% | human | only convention part is mechanical |
| C45 | question: reviewer asks why / what / how | 4.2% | human | signal of missing explanation |
| C25 | unrelated change in the PR; scope creep; should be split or reverted | 2.3% | human | diff-level |
| C28 | test does not exercise the fix, asserts weakly, or tests a mock | 0.9% | human | judgement; some patterns lexical |
| C41 | public-API design shape: argument shape, builder, accessor, naming of API | 1.4% | human | design judgement |
| C44 | consistency with existing conventions elsewhere in the codebase | 1.4% | human | needs project patterns |
| C39 | logging: wrong level, noisy, sensitive content, log vs return | 0.8% | human | level choice is judgement; secrets-in-log lexical |

### 7.4 Diff against the existing catalogue

Of the top-30 detectable candidates, 14 have no covering rule id in the frob-v2 catalogue read for this study (docs/design/neatness.md, cohesion.md, documentation.md, docs/reference/rules/, notes/research/lint-requirements.md): C29 (missing null/empty/boundary/invalid-inpu), C09 (typo, grammar or wording error in text), C30 (error swallowed, ignored, mis-propagated), C34 (security: injection, secret in log, miss), C37 (platform portability: OS-specific path, ), C49 (state initialised or ordered wrongly (li), C32 (concurrency: race, lock misuse, blocking), C31 (resource leak, missing cleanup, ownershi), C48 (wrong function, wrong argument, swapped ), C35 (breaking public API change or missing de), C04 (reinvents an existing helper, constant o), C14 (identifier violates the naming conventio), C26 (PR hygiene: commit structure, license he), C19 (visibility wider than needed (pub, publi). Covered or partly covered families: dead code (DEAD), duplication (DUP001-003), doc coverage (DOC001), doc drift (DRIFT001-004), comment hygiene (NARR001-005, TODO001/002), size and nesting (NEAT001-006), flag parameters (NEAT003), magic values (NEAT009), hidden state (NEAT012-013), layering (ARCH104, INV002), test reach (COV001, TEST001), changelog fragments (REL003), CI hardening (CI001 ff.), supply chain (VET). Frequent reviewer concerns that the catalogue treats as out of scope or delegates to bound tools: formatting and import order (C12), naming convention (C14), typos (C09), idiomatic API use (C17).

## 8. Reproduction and files

- Pipeline: ~/projects/goblin-mining (git). `uv run python -m goblin_mining universe | fetch-prs | fetch-commits | sample | show | import | classify | analyze-comments | analyze-external | analyze-commits`; report: `python -c 'from goblin_mining import report; report.write()'`.
- Data (git-ignored): data/mining.sqlite (repo, pr, comment, commit_, label, sample, pred), data/raw/prs/*.json.gz (graphQL pages per repo), data/external (CodeReviewer, ManySStuBs4J), data/results_*.json.
- Labels (committed, text only, no comment bodies or usernames): labels/pilot_*.txt, c_*.txt (comments), m_*.txt (commits), r2_*.txt and mr2_*.txt (second pass). universe.csv lists every candidate repository with status and exclusion reason.
- PR links: every labelled comment has a GitHub URL in the comment table (data/mining.sqlite); example links per category are in section 9 (no usernames).