# frob v1 gates and rule inventory (input to the Rust v2 redesign)

Source of truth read: <frob-v1> (read-only). Main sources:
`src/frob/gates/_waive.py::_KNOWN_GATE_RULES` (rule registry),
`src/frob/gates/__init__.py` (`_ALL_GATES`, `_GATE_STAGE_GROUPS`,
`_build_process_jobs`, `REPO_WIDE_GATES`), `frob.toml [gates.severity]`,
`docs/modules/gates.md` (catalog + sections), `docs/guides/extending/gate-rule-families.md`,
`docs/design/gate-semantics-classification.md`, `docs/design/check-fix-engine.md`,
`docs/commands/check.md`, `docs/modules/tickets-verify-sweep.md`,
`docs/modules/land-profiles.md`, `docs/audits/check-performance.md`,
`docs/guides/agentic-time-profiling.md`.

## 0. Honest status line (denominator and coverage)

- Universe: 667 registered rule ids in `_KNOWN_GATE_RULES` (verified by AST
  extraction; 663 appear in the `frob:enumerates` list of gates.md, the other 4 -
  INVLVL001, LAYOUT001, LAYOUT002, LAYOUT003 - are registered but missing from it).
  Three of the 667 are ruff codes carried in the registry (E501, F401, I001). One more
  id, TIERBDEMO001, appears in the gates.md catalog but is a deliberately-never-emitted
  fixture id and is not in the registry literal.
- Only ~72 gate FUNCTIONS exist (`_ALL_GATES`); rule ids are emitted many-per-gate.
  The 667 ids split: ~418 "real v1 rules" (core + strata + vet + misc) and 249 ids
  in seven web-app families (WEBSEC 108, A11Y 35, SQL 30, SEO 27, COMPLY 27,
  WEBPERF 15, LAUNCH 7) whose catalog rows say "not yet implemented / reserved
  (T-5301)" even though `src/frob/webapp/` holds ~17k lines of per-family findings
  functions; only A11Y and LAYOUT have a gate wiring. Treat the web families as
  half-built; verify before porting anything.
- `[gates.severity]` in frob.toml overrides 580 of 667 ids (507 error, 66 warn,
  7 advisory). 87 ids have no toml entry and use the severity hard-coded at the
  emit site; those are marked `~` below. The toml value is this repo's override,
  not necessarily the in-code default.
- Every id below is accounted for exactly once (a script check against the registry
  was run after writing; result recorded at the end). Rows with a range list every
  id in the range explicitly or by `PREFIXnnn-mmm` expansion.
- Nothing pending, nothing blocked. Caveat: per-rule "what it detects" for ids
  documented only in a section body (not the catalog table) was read from the module
  docstring or emit site, not exhaustively from tests.

Legend. Inputs: G = graph snapshot (symbols, edges, directives), T = ticket ledger,
D = git diff / merge-base, C = coverage.xml + test collection, F = tracked-file walk
/ AST, M = markdown docs, S = strata design model, K = frob.toml config, R =
lock/registry/invariant files, X = external tool or git history/subprocess.
Cost: c = cheap (<1s), m = medium (1-10s), e = expensive (>10s or unbounded);
estimates come from docs/audits/check-performance.md (test 13.7s, archgate 11s, perf 9.5s,
sys 6.2s, coverage 5s, pii_structural 4.6s, dead_symbols 3.5s, secrets 2.9s, tickets 2.1s)
plus a shared ~3.3s graph-load tax per invocation.
Sev: e = error, w = warn, a = advisory, u = unresolved-capable, `~` = code default (no toml).
Rec: KEEP / MERGE (into another rule or a parametric rule) / DROP (from v2 core).

## 1. Gate registry structure

| Aspect | v1 fact |
|---|---|
| Registry | `_KNOWN_GATE_RULES` frozenset literal (667), generated/drift-locked by `_rule_id_scan.py` (regex scan of `rule=` literals) and a DOCENUM001 `frob:enumerates` list in gates.md; REG010/GATERULE001 close the loop |
| Gate unit | one function per family returning `tuple[Violation, ...]`; `_ALL_GATES` (name set) + `_CANONICAL_GATE_ORDER` + `_GATE_STAGE_GROUPS` all import-time-asserted equal |
| Violation | rule, severity, file, line, message, optional symref (exact-symbol waiver) and metric (ratchet-aware ceiling), `severity_pinned` flag |
| Severity enum | ERROR, WARN, UNRESOLVED (cannot-determine, never fails exit, own counter, T-1664), ADVISORY (always shown, never fails, never ratchets, T-5304) |
| Thread-pool gates | cheap/IO gates share one `ThreadPoolExecutor` (drift, coverage, invariant, test, policy, doclink, docanchor, docstatus, docmake, docseverity, fuzz, release, decisions, tickets, milestone, vmodel, refs, registry, docblocks, compliance, debt, deprecated, schema gates, ...) |
| Process-pool gates | `_ProcessJob` entries on a `ProcessPoolExecutor` (forkserver+preload, PDEATHSIG, worker count = min(jobs, cpu)): perf, clones, sys, secrets, taint, opaque, archgate, exhaustive_handling, ffi_boundary, pii_structural, walk_lint, cve_fingerprint_scan, render_lint, lexcheck, flag_coverage, 12 schema gates, dead_symbols, wire, cache, protocol_summary, bare_toolchain |
| Repo-wide (unscopable by `--files`) | tickets, milestone, release, cross_ticket_leakage, sys; tool stages arch, cycle, dup, exports |
| Stage groups | `lint` (ruff, ty); `static` (cycle, dup, arch, bind, exports); `gates-fast` (all thread gates, ~64 names); `gates-native` (archgate, clones, perf, exhaustive_handling); `gates-security` (sys, pii_structural, secrets, dead_symbols, protocol_summary, opaque, wire, cache, a11y) |
| Cacheable | thread gates on `_CACHEABLE_GATES` (drift, test, policy, parse_failures, debt, lang_conformance, affect_drift) keyed by touched-file hashes + membership + side-input fingerprints; all process gates on `_CACHEABLE_PROCESS_GATES` keyed by sha256 of `git ls-files -s` (whole-tree key, whole-gate granularity); store `.frob/gate-cache.db` |
| New-rule policy | adding an id to the registry forces a before-fails/after-passes bound acceptance criterion at ticket close (`_new_gate_rule_acceptance`), new rules start at warn for one release |
| Gate-semantics classes | (a) semantic (graph/AST/typed), (b) legitimately lexical (SEC001-004, EXCL001, directive wrap, rule-id scan, TICK011 trigger), (c) lexical-and-wrong; 8 class-(c) defects found and fixed; LEXCHECK001 is the standing guard |

## 2. Core graph / coverage / drift / scope (families DRIFT AFFECT COV PLACE PARSE CYCLE TODO DSL SCOPE PRE QUEUE)

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| DRIFT001 | acked doc/code digest moved without `frob ack` | e | G,R(frob.lock) | c | KEEP: the core drift contract |
| DRIFT002 | edge endpoint no longer resolves (rename/delete) | e | G | c | KEEP: core drift contract |
| AFFECT001 | diff-touched symbol's affects() closure names a doc anchor whose file was not touched | e | G,D | m | KEEP: impact analysis is the product |
| AFFECT002 | same closure names a dependent symbol (uses-contract) not touched | e | G,D | m | MERGE into AFFECT001 (one rule, target kind field) |
| COV001 | public symbol has no `frob:doc` edge | e | G | c | KEEP: coverage half of the model |
| COV002 | changed symbol has neither ticket edge nor covering open-ticket scope | e | G,D,T | c | KEEP: change accountability |
| COV003 | done ticket's evidence ids do not resolve to collected tests | e | T,C | m | KEEP: evidence must exist |
| COV004 | attachment sha256 mismatch or missing file | e | T,F | c | KEEP: cheap integrity |
| COV005 | directive rebound from public to private symbol by a diff | e | G,D | m | MERGE into binding rule (see PLACE001) |
| COV006 | `frob:tests` on private symbol with no callgraph reachability | w~ | G | m | DROP: callgraph false-edge prone, low signal |
| COV007 | `frob:doc` edge from a private src symbol | e~ | G | c | MERGE into COV001 (public-only rule) |
| COV008 | diff deletes/renames a test file ticket evidence still cites | e | D,T,C | m | KEEP: protects evidence |
| COV009 | diff touches one symbol of a shared doc-anchor group, not siblings | w~ | G,D | c | DROP: review-nag noise |
| COV010 | entrypoint (`__main__` guard) not covered as a symbol | e~ | G,F | c | MERGE into COV001 (entrypoints are symbols) |
| PLACE001 | `frob:` directive class-falls-back instead of binding nearest real symbol | w~ | G | c | MERGE into DSL001 (binding error in parser) |
| PARSE001 | tracked file unparseable, its symbols missing from graph | e | F | c | KEEP: unmeasured is not zero |
| PARSE002 | file salvaged around a syntax error (partial symbol set) | e | F | c | MERGE into PARSE001 (severity param) |
| CYCLE001 | import cycle, severity scales with size (2 info, 3-5 warn, 6+ error) | e | G | m | KEEP: cheap in Rust via petgraph SCC |
| TODO001 | bare TODO/FIXME comment in diff-touched file | e | F,D | c | KEEP: unaccounted work |
| TODO002 | `frob:todo` bound to closed/missing ticket | e | G,T | c | KEEP: dangling deferral |
| TODO003 | todo deferred under a version that has since shipped | e | G,T,R | c | MERGE into TODO002 (expiry variant) |
| DSL001 | `frob:` comment does not parse under the directive grammar | e | F | c | KEEP: grammar is the foundation |
| SCOPE001 | diff touches paths/symbols outside active ticket scope | e | D,T | c | KEEP: scope contract |
| SCOPE002 | scope-declaration-time doc/code/helper closure gap | w | G,T | m | MERGE into TICK009 (scope-quality lint) |
| PRE001 | ticket started without a fresh pre-work dup/xref sweep | e | T,X | c | DROP: slow ceremony, scope lease replaces it |
| QUEUE001 | ticket queue failed to load (malformed file, duplicate id) | e | T | c | KEEP: hard failure, not soft skip |

## 3. Invariants, tests, evidence (INV INVLVL TEST TESTMOCK TDD BUG RACE CLAIM GUARD FORBID ROUTE CONFIGPATH SUPPRESS)

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| INV001 | invariant has no evidence (test or policy) | e | R,C | c | KEEP: invariant model core |
| INV002 | invariant has no `frob:invariant` code anchor | e | R,G | c | KEEP: invariant model core |
| INV003 | doc claim-shaped exclusivity language ("only", "sole") | e | M | m | DROP: prose-lexical heuristic |
| INV004 | doc normative language (must/never/always) unbound | w | M | m | DROP: prose-lexical heuristic |
| INV005 | invariant evidence collects but never reaches anchor | w | G,C | m | MERGE into INV001 (reachability strength) |
| INV007 | `no_import` anchor's file imports forbidden module | e | G | c | KEEP: forbidden-import is structural |
| INV008 | `establishes` anchor with no property-kind test | e | G | c | MERGE into INV001 |
| INV009 | an `invariants/*.md` failed to load | e~ | R | c | MERGE into generic load-error rule |
| INV010 | time-stable invariant baseline run not measurable | u | C,X | e | DROP: multi-sample test reruns too costly |
| INV011 | entrypoint reaches guarded sink without referencing guard constant | e~ | G | m | MERGE into INV007 (reachability variant) |
| INV051 | design policy re-declares a rule less restrictively than container | e | S | c | KEEP: refinement soundness |
| INVLVL001 | invariant verified below its paired V-model level | e~ | R | c | DROP: V-model niche, ship in design pack |
| TEST001 | public symbol has no `frob:tests` unit edge | e | G | c | KEEP: test obligation core |
| TEST002 | fewer unit edges than `min_unit_cases` (UNMEASURED when coverage-only) | e | G,C | c | MERGE into TEST001 (count threshold) |
| TEST003 | interface package has fewer than `min_integration` integration edges | w | G,K | m | KEEP: tier obligations are the model |
| TEST004 | declared `[[system]]` has fewer than `min_e2e` e2e edges | e | G,K | c | MERGE into TEST003 (tier param) |
| TEST005 | measured coverage below per-symbol/module/system floor | e | C,K | m | KEEP: floors are real policy |
| TEST006 | coverage evidence missing or stale vs file hashes | w | C,F | c | KEEP: stale evidence is no evidence |
| TEST007 | cross-package uses-contract lacks pairwise integration test | e | G,K | m | MERGE into TEST003 (tier param) |
| TEST008 | coverage.xml has classes but none join any known path | e | C,F | c | KEEP: zero-join is silent-zero |
| TEST009 | `.strata` design file under `min_design_e2e` e2e edges | e | S,G | c | MERGE into TEST004 |
| TEST010 | `frob:tests kind=` not unit/integration/e2e | e | G | c | MERGE into DSL001 (attr validation) |
| TEST011 | coverage.xml older than a tracked source change | w | C,F | c | MERGE into TEST006 |
| TEST012 | `frob-coverage.lock.json` missing/drifted/producer abandoned | e | C,R,X | c | MERGE into generic lock-staleness rule |
| TEST013 | TEST001 credit rests only on c/cpp name-pattern fallback | e | G | c | DROP: heuristic fallback, fix inference instead |
| TEST014 | same leaf test-name shared across files via naming inference | w~ | G | c | DROP: heuristic fallback noise |
| TEST015 | TEST001 satisfied only by tests with no assertion evidence | e | G,F | m | KEEP: vacuous tests defeat the gate |
| TEST016 | ticket evidence killed zero mutants of in-scope diff | e | T,D,X | e | KEEP: opt-in mutation proof, async only |
| TEST017 | coverage.xml joins far fewer modules than snapshot (deflation) | e | C,G | c | MERGE into TEST006 |
| TEST018 | evidence replaced/weakened without recorded reason | e | T | c | KEEP: cheap evidence-audit trail |
| TEST019 | per-symbol deflated coverage (def hit, body zero) | e | C,G | c | MERGE into TEST006 |
| TESTMOCK001 | every `frob:tests` target mocks every collaborator of subject | e~ | G,F | m | DROP: AST heuristic, python-mock specific |
| TDD001 | implementation symbol introduced at/before its test (history) | e/u | G,X | e | DROP: git-history archaeology, costly |
| BUG002 | bug ticket's evidence test did not fail at parent commit | e | T,X | e | KEEP: proves defect repro; async/land only |
| BUG003 | `must-still-pass` control fails on fix or never passed at parent | e | T,X | e | KEEP: positive counterpart of BUG002 |
| RACE001 | read-check-write on shared key with no guard | w~ | F | m | DROP: python heuristic, linter territory |
| RACE002 | docstring claims cap/idempotent with no concurrent test | w~ | G,F | m | DROP: prose-claim heuristic |
| CLAIM001 | docstring never/always claim with no invariant binding | e~ | F,G | m | DROP: prose-lexical claim scan |
| GUARD001 | guard reads lockout flag with no reachable writer | e~ | G,F | m | DROP: consumer-specific pattern lint |
| FORBID001, FORBID002 | `forbid call` / `forbid import` policy violated in bound code | e~ | S,F | m | KEEP: strata policy enforcement |
| FORBID003 | forbid rule uncheckable (language/binding gap) | e~ | S,F | c | MERGE into UNRESOLVED outcome |
| ROUTE001 | decorated route returns bare dict, no response model | e~ | F | m | DROP: framework-specific, web pack |
| CONFIGPATH001 | pydantic `*_path` field default is a relative path | e~ | F | m | DROP: python-pydantic specific |
| SUPPRESS001 | suppression comment for one checker while another still errors | e | F,X | m | DROP: python tool dialect issue |
| POL000 | `[policy]` pattern rule matched zero nodes (config error) | e~ | K,F | c | KEEP: zero-match must be loud |
| POL* (user ids) | user-defined `[policy]` forbidden-import / pattern / norm rules | per-rule | G,F,D | m | KEEP: policy engine, tree-sitter queries |

## 4. Docs and narrative (DOC DOCARCH DOCENUM NEGEXIST PKG ENV ROOT NARR CPLACE DSTACK FMT LANDFMT LANDPARITY REF EXCL)

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| DOC001 | obligated doc has no describes/doc anchor and is unreachable from a root | e | M,G | c | KEEP: doc reachability |
| DOC002 | `frob:doc file#slug` target file/anchor does not resolve | e | M,G | c | KEEP: link integrity |
| DOC003 | `frob:claims <view>` names unknown or unproved baseline view | e | M,S | c | MERGE into DOC002 |
| DOC004 | fenced code block references own code surface and is stale | e | M,F | m | KEEP: doc-code drift, symbol-resolved |
| DOC005 | README command table out of sync with live subcommands | e | M,K | c | MERGE into DOC012 (command-table drift) |
| DOC006 | prose pointer (code span/link) of recognized shape unresolved | w~ | M,F | m | KEEP: unify with DOC004 as pointer resolver |
| DOC007 | `frob:tests` target in `path::Symbol` form not dotted node form | e | G | c | DROP: pytest node-id specific |
| DOC008 | inline markdown link or fragment does not resolve | e | M | c | MERGE into DOC002 |
| DOC009 | audit doc lacks dated Status header | e | M | c | DROP: repo-local convention, config-driven doc schema |
| DOC010 | `make <target>` citation is not a Makefile recipe | e | M,F | c | MERGE into DOC006 |
| DOC011 | doc mentions ticket id that does not resolve | e | M,T | c | MERGE into DOC006 |
| DOC012 | real top-level subcommand has no dedicated doc section | e | M,K | c | KEEP: command-doc drift lock |
| DOC013 | markdown severity-table row disagrees with live severity | e | M,K | c | MERGE into DOCENUM001 (table drift) |
| DOC014 | row/section registry table mismatch | e~ | M | c | MERGE into DOCENUM001 |
| DOCARCH001 | public docstring cites ticket id and reads as change narrative | w | F | c | DROP: prose-lexical narrative scan |
| DOCARCH002 | comment run or docstring over line cap, ratchet-pooled | w~ | F,K | c | DROP: style cap, content-blind |
| DOCENUM001 | `frob:enumerates` member list drifts from real members | e~ | M,F | c | KEEP: enumerated-doc drift lock |
| NEGEXIST001 | doc negative-existence claim now false, or code changed under it | e~ | M,F | m | DROP: niche claim lint |
| PKG001, PKG003 | readme embedded relative image / no declared readme | e/u | M,K | c | DROP: PyPI packaging, Python only |
| PKG002 | same relative image in other markdown | w~ | M | c | DROP: PyPI packaging, Python only |
| ENV001 | `FROB_*` constant documented nowhere | w~ | F,M | c | MERGE into DOC006 (symbol documented) |
| ROOT001 | repo-root dir with zero code references | w~ | F,K | c | DROP: repo hygiene, REF001 covers |
| NARR001 | `# T-####:` narrative comment block over 12 lines | w~ | F | c | DROP: style, narrative lives in tickets |
| CPLACE001 | waive reason prose spans more than 2 lines | w~ | F | c | DROP: style |
| CPLACE002 | ticket-citing docs paragraph over 15 words | w~ | M | c | DROP: style |
| DSTACK001 | run of 2+ same-kind directive lines above a symbol | w~ | F | c | DROP: use multi-target directive form |
| FMT001 | `frob:` directive line over configured line length | e | F | c | DROP: formatter job, `frob fmt` canonicalizes |
| FMT002 | stray noqa on directive lines | w | F | c | DROP: python noqa specific |
| LANDFMT001 | diff-touched `.py` file `ruff format --check` would rewrite | e~ | D,X | m | DROP: delegate to external formatter |
| LANDPARITY001 | new public symbol lacks doc/tests directive (land-time) | e | D,G | c | MERGE into COV001/TEST001 diff mode |
| LANDPARITY002 | modified function newly crosses ARCH001 long+complex threshold | e | D,F | m | MERGE into ARCH001 diff mode |
| REF001 | tracked file has zero inbound references (anti-orphan) | w | F,G | m | KEEP: orphan detection, resolve via graph |
| REF002 | tracked file has exactly one inbound reference | e~ | F,G | m | DROP: fragility nag |
| REF003 | `frob:used-by` consumer absent or does not reference back | e~ | F,G | m | MERGE into REF001 |
| EXCL001 | `.git/info/exclude` shadows tracked source (unwaivable) | e | F,X | c | DROP: repo-state hazard, doctor check |

## 5. Tickets, milestones, release, process hygiene (TICK MILE CROSSTICKET DEBT DEPR REL VERSION LEDGERV BUDGET BASE AUTOFIX CHECK CLAUDE SUBJECT GATES GATERULE TOOL BARETOOL WRAP DEPLOY PLATFORM PROFILE LEXCHECK PORT WIRE WALK RENDER CACHE)

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| TICK001 | ticket id in both active ledger and archive (unwaivable) | e | T | c | KEEP: id uniqueness |
| TICK002 | `T-draft-*` id survived onto default branch (unwaivable) | e | T | c | KEEP: id integrity |
| TICK003 | too many closed tickets un-archived | e~ | T | c | DROP: housekeeping, auto-archive |
| TICK004 | queued ticket past priority rot-day threshold | e~ | T | c | MERGE into TICK007 (staleness) |
| TICK005 | merge resurrected a closed ticket's state | w | T,X | c | KEEP: merge-safety, git2 cheap |
| TICK006 | Done report "filed T-####" claim resolves to no ticket | e | T | c | KEEP: claim must resolve |
| TICK007 | dispatchable critical/high ticket stale | w~ | T | c | MERGE into TICK004 (staleness) |
| TICK008 | ticket frontmatter has unknown extra fields | w | T | c | DROP: serde deny_unknown_fields handles |
| TICK009 | planned/in-progress scope over-broad | w | T | c | KEEP: scope quality |
| TICK010 | lease file whose worktree path no longer exists | e | X(fs) | c | MERGE into TICK015 (dead-owner) |
| TICK011 | Done report discloses cut work with no ticket id nearby | e | T | c | DROP: English phrase-scan heuristic |
| TICK012 | live lease records scope path no longer matching declared scope | w~ | T,X | c | MERGE into TICK015 |
| TICK013 | in-progress/planned ticket with empty scope, no opt-out | e | T | c | KEEP: empty scope is dangerous |
| TICK014 | done feature/bug ticket whose diff touches only ledger | w~ | T,D | c | KEEP: empty-close detector |
| TICK015 | in-progress ticket's worktree/branch/process judged dead | e~ | T,X | m | KEEP: lease liveness |
| MILE001 | open ticket blocked by one with later effective milestone | e | T | c | KEEP: milestone deadlock |
| MILE002 | open ticket has descendant with later milestone | e | T | c | MERGE into MILE001 |
| MILE003 | effective milestone unresolvable | e | T,K | c | KEEP: default milestone resolution |
| MILE004 | two `runs_last` tickets share milestone with ambiguous order | e | T | c | MERGE into MILE001 |
| CROSSTICKET001 | `--ticket` branch carries another in-progress ticket's work | e | T,D | m | KEEP: isolation, land-time |
| DEBT001 | `frob:debt` missing reason/ticket | e | G,T | c | MERGE into generic expiring-directive rule |
| DEBT002 | debt names non-open ticket | e | G,T | c | MERGE into generic expiring-directive rule |
| DEBT003 | debt `until` passed | e | G | c | MERGE into generic expiring-directive rule |
| DEPR001 | `frob:deprecated` missing/invalid sunset or ticket | e | G | c | MERGE into generic expiring-directive rule |
| DEPR002 | deprecated names non-open ticket | e | G,T | c | MERGE into generic expiring-directive rule |
| DEPR003 | deprecated inside warning window | w | G | c | MERGE into generic expiring-directive rule |
| DEPR004 | deprecated sunset passed | e | G | c | MERGE into generic expiring-directive rule |
| DEPR005 | new caller of deprecated symbol vs baseline lock | e | G,R | m | KEEP: no-new-callers ratchet |
| DEPR006 | deprecated-baseline lock producer abandoned | e | R,X | c | MERGE into generic lock-staleness rule |
| REL001 | release readiness (version, changelog, open debt/deprecation) | e | K,T,G | c | KEEP: release gate |
| REL002 | `.frob-release.json` disagrees with pyproject/uv.lock | e | K,F | c | KEEP: version coherence, rust Cargo |
| VERSION001 | frob version vs extras pins and native crate versions | e | K,F | c | MERGE into REL002 |
| LEDGERV1001 | legacy monofile ledger present (sunset-windowed) | e | T,F | c | DROP: migration residue, v2 has no monofile |
| BUDGET001 | `--budget` deferred stage groups (informational) | e | X | c | KEEP: budget must name what it skipped |
| BASE001 | ratchet pool live count exceeds committed baseline | e~ | R | c | KEEP: aggregate ratchet signal |
| AUTOFIX001 | abandoned `--fix` journal left tree half-rewritten | e | F,X | c | KEEP: crash-safe fix journal |
| DERIVED001 | corrupt derived-state artifact (`.frob/*.db`) found by pre-dispatch integrity check | e | F | c | KEEP: fail-closed cache integrity, any cache |
| NATIVE001 | declared `[[native]]` extension stale/unimportable (auto-rebuild self-heal) | e | K,X | m | DROP: pyo3 build staleness vanishes in Rust |
| CHECK001 | project type undetected, no toolchain mapped | e | F | c | KEEP: fail loudly not default |
| CLAUDE001 | managed `.claude` config differs from materialized copy | e | F | c | DROP: agent-config sync, not a gate |
| SUBJECT001 | enforcing gate examined zero subjects | e~ | X | c | KEEP: vacuous-pass guard |
| GATES001 | invariant loading problem made a hard failure | e~ | R | c | MERGE into generic load-error rule |
| GATERULE001 | gate rule id used but absent from registry (and reverse) | e | F | c | DROP: Rust enum registry makes impossible |
| TOOL001, TOOL002 | required external tool missing / reached but failed | e~ | X | c | KEEP: tool availability is UNRESOLVED |
| TOOL003 | bare `shutil.which` outside the tool registry | w | F | c | DROP: self-lint of frob source |
| BARETOOL001 | bare toolchain-name argv literal | e~ | F | m | DROP: self-lint of frob source |
| WRAP001, WRAP002, WRAP003 | scaffolded Makefile/make.bat drifted from `frob run` delegation | e~ | F,K | c | KEEP: derived-artifact drift (one rule) |
| DEPLOY001 | deploy scripts differ from regeneration | e | F,S | c | KEEP: generated-artifact drift |
| DEPLOY002 | deploy script mutation not declared in host manifest | e | F,S | m | KEEP: design conformance |
| DEPLOY003 | host manifest entry has no mutation in deploy scripts | e | F,S | m | MERGE into DEPLOY002 |
| PLATFORM001 | POSIX-only primitive degrades silently on win32 | e | F | m | DROP: Rust cfg/clippy covers |
| PLATFORM002 | `os.kill(pid, 0)` outside sanctioned probe | e | F | c | DROP: Python-specific self-lint |
| PROFILE001 | direct use of `ProfileName` outside profile module | e | F | c | DROP: self-lint of frob source |
| LEXCHECK001 | gate built from raw regex text with no symref | e | F | m | DROP: meta-lint of v1 gate code |
| PORT001, PORT001-PATH, PORT001-IDENT, PORT001-DEFAULT | gate source hardcodes frob's own package/path/default | e/w | F | m | DROP: portability self-lint of v1 |
| WIRE001 | new function with no non-test caller, unregistered rule literal, unwired CLI dest | e | G,D,T | m | KEEP: invoked-by-nothing guard (graph reachability) |
| WIRE002 | `frob:waive WIRE001` without follow_up ticket (unwaivable) | e | G,T | c | MERGE into WIRE001 |
| WIRE003 | hook/doc names a `frob` verb that does not exist | e | F,K | c | DROP: agent-hook drift, doc drift covers |
| WALK001 | unpruned directory traversal (`os.walk`/`rglob`) | e~ | F | m | DROP: python self-lint |
| RENDER001 | bare stdout write bypassing `frob.render` | e~ | F | m | DROP: python self-lint |
| CACHE001 | `@memoize_per_run` function reads input not in cache key | e | F | m | DROP: v1 memo design artifact |
| DEAD001 | private symbol with zero references | w~ | G | m | KEEP: reachability on graph, rust fast |
| OPAQUE001 | runtime-opaque construct (eval, non-literal getattr) | e | F | m | KEEP: unresolved-capability honesty |

## 6. Waivers (family WAIVE plus waiver-adjacent)

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| WAIVE001 | `frob:waive` missing reason | e | G | c | KEEP: waiver needs reason |
| WAIVE002 | waiver targets rule id that can never match (typo/unwaivable channel) | e | G,K | c | KEEP: dead waiver |
| WAIVE003 | package-scoped waiver reaches multiple packages via prefix | e | G | c | DROP: prefix matching removed in v2 |
| WAIVE004 | waiver matches zero findings (stale) | w~ | G,F | e | KEEP: only on full runs, cached |
| WAIVE005 | waiver `until=` passed | e | G | c | MERGE into generic expiring-directive rule |
| WAIVE006 | waiver bound to closed ticket | e | G,T | c | KEEP: waiver may not outlive ticket |
| WAIVE007 | waiver ticket ref dangling | e | G,T | c | MERGE into WAIVE006 |
| WAIVE008 | waiver on WIRE001 rescue-predicate symbol (dead waiver) | e | G | c | DROP: WIRE001-specific |
| WAIVE009 | waiver reason promises deferred/future work | e | G | c | DROP: English phrase scan |
| WAIVE010 | waiver reason reads temporary ("until", "for now") | w~ | G | c | DROP: English phrase scan |
| WAIVE011 | ratchet lock producer abandoned | e | R,X | c | MERGE into generic lock-staleness rule |
| WAIVE012 | premise-expiry predicate (`ticket-closed:T-##`) now true | e~ | G,T | c | KEEP: waiver expiry by predicate |
| RELWAIVE002 | strata reliability waiver issues | e | S | c | MERGE into SYSWAIVE (strata waiver rules) |
| SYSWAIVE002 | SYS2xx waiver matches zero findings (stale) | e | S | c | MERGE into WAIVE004 |
| SYSWAIVE003 | SYS104-106 waiver lacks expiry or is past it | e | S | c | MERGE into WAIVE005 |

## 7. Registry, decisions, compliance, threat (REG DEC COMPLIANCE THREAT CVEFP SEC-CVE-FINGERPRINT)

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| REG001 | registry entry disposition missing/pending/out_of_scope without reason | e | R | c | KEEP: exhaustiveness registries |
| REG002 | `handled_by:<rule>` names unknown rule id | e | R,K | c | KEEP: dangling enforcement ref |
| REG003 | `deferred:<ticket>` unresolvable or closed | e | R,T | c | KEEP: real deferral |
| REG004 | `duplicate_of` target missing / split entry empty | e | R | c | MERGE into REG002 |
| REG005 | declared total disagrees with entry count | e | R | c | MERGE into REG006 |
| REG006 | registry list item not a mapping / no id | e | R | c | KEEP: generic registry load error |
| REG007 | duplicate id across registries | e | R | c | KEEP: id collision |
| REG008 | `handled_by` entry has no `frob:enforces` edge | w | R,G | c | KEEP: claimed-but-unwired |
| REG009 | `frob:enforces` names unknown concept id | w | G,R | c | MERGE into REG002 |
| REG010 | live rule has no registry entry (reverse direction) | w | R,K | c | MERGE into REG008 (bidirectional) |
| REG011 | out_of_scope reason not substantive | w | R | c | DROP: prose-quality heuristic |
| REG012 | adopted registry dir deleted from tree (unwaivable) | e | R,X | c | MERGE into generic adopted-then-deleted rule |
| DEC000 | decisions records unreadable | e | R | c | MERGE into generic load-error rule |
| DEC001 | `frob:decision AD-###` points at missing record | e | G,R | c | KEEP: anchor resolution |
| DEC002 | accepted decision has no code anchor | e | G,R | c | KEEP: decision traceability |
| DEC003 | adopted decisions dir deleted (unwaivable) | e | R,X | c | MERGE into generic adopted-then-deleted rule |
| COMPLIANCE001 | regulation id in view has no catalog or out-of-scope entry | e | S,R | c | KEEP: deny-by-default completeness (design pack) |
| COMPLIANCE002 | fired regulatory obligation lacks discharging claim | e | S | c | KEEP: design pack |
| COMPLIANCE003 | collection flow field not in declared privacy policy | e | S | c | KEEP: design pack |
| COMPLIANCE004 | out-of-scope `caught_by` cites unknown control | e | R | c | MERGE into REG002 |
| COMPLIANCE005 | registry unit deferred/undispositioned | e | R | c | MERGE into REG001 |
| COMPLIANCE006 | adopted compliance registry deleted (unwaivable) | e | R,X | c | MERGE into generic adopted-then-deleted rule |
| COMPLIANCE007 | unit disposition self-references COMPLIANCE005 | w | R | c | DROP: vacuous-self-reference quirk |
| THREAT001 | CWE in baseline view lacks catalog/out-of-scope entry | e | S,R | c | KEEP: catalog completeness (design pack) |
| THREAT002 | `may` capability kind unclassified, no benign entry | e | S | c | KEEP: design pack |
| THREAT003 | fired weakness obligation lacks claim at required rung | e | S | c | KEEP: design pack |
| THREAT004 | observed sink with no declared `may` capability | e | S,F | m | KEEP: code-vs-design conformance |
| THREAT005 | observed sink kind unrecognized, no benign excuse | e | S,F | m | MERGE into THREAT002 |
| THREAT006 | `caught_by` references unresolved rule/CWE | e | R,K | c | MERGE into REG002 |
| CVEFP001 | CVE fingerprint cwe_id not in CWE catalog | e | R | c | DROP: self-consistency of bundled catalog (build-time test) |
| SEC-CVE-FINGERPRINT-001 | tracked source matches known vulnerable-usage needle | e | F | m | KEEP: cheap Aho-Corasick scan |

## 8. Config-schema, arch, language, performance, dup, fuzz, exhaust, ffi, proto

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| REFSCHEMA001, NATIVESCHEMA001, PROFILESCHEMA001, TOPSCALARSCHEMA001, TESTINGSCHEMA001, ARCHSCHEMA001, DOCBLOCKSSCHEMA001, GATESSCHEMA001, TESTRUNNERSCHEMA001, DUPSCHEMA001, GRAPHSCHEMA001 | unknown/misspelled key in one frob.toml table (11 per-table gates; UNRESOLVED if the project did not declare known keys) | e/u | K,F | c each | DROP: serde deny_unknown_fields makes it structural |
| FLAGCOV001 | CLI flag parses but never reaches its declared config model | e/u | F,K | m | DROP: self-lint of v1 CLI wiring |
| ARCH001 | long-AND-complex function (complexity-aware) | e | F | e | KEEP: native tree-sitter, cheap in Rust |
| ARCH101 | low-cohesion class (LCOM4, >=6 methods) | e | F | m | MERGE into ARCH102 (design-smell family) |
| ARCH102 | module exports partition into disjoint clusters (SRP) | e | F | m | DROP: subjective smell, advisory only |
| ARCH103 | function mixes I/O, formatting, and logic | e | F | m | DROP: subjective smell |
| ARCH104 | `[arch.layering]` dependency-direction violation | e~ | G,K | m | KEEP: layering is declared policy |
| CPPTHROW001 | C++ noexcept function may throw | e | F | m | DROP: language-pack niche |
| LARGE001 | file over `max_file_lines` | e~ | F | c | KEEP: one config-driven size cap |
| LANG001 | language adapter capability registry not fully accounted | e | K,F | c | DROP: adapter-registry self-check, Rust trait enforces |
| LANG002, LANG003 | project language-conformance findings (std.lang) | e/e~ | F,S | m | DROP: v1 adapter conformance |
| LANG004 | adapter claims IMPLEMENTED capability that fixture disproves | e | F | m | MERGE into build-time adapter tests |
| PERF001 | list-membership test in loop | e | F | m | DROP: clippy/perf linters cover |
| PERF002 | `.index`/`.count` in loop | e | F | m | DROP: clippy/perf linters cover |
| PERF003 | nested loops with equality scan | e | F | m | DROP: clippy/perf linters cover |
| PERF004 | sort inside loop | e | F | m | DROP: clippy/perf linters cover |
| PERF005 | recursion with unproven termination | e~ | F,G | m | DROP: heuristic |
| PERF006 | unbounded tail recursion | e | F,G | m | DROP: heuristic |
| PERF007 | call invoked from 2+ pipeline stages (redundant recompute) | e | G,K | m | DROP: needs `[[perf.heavy]]` config, niche |
| PERF008 | loop-invariant call transitively reaching effect | w~ | G,F | m | DROP: heuristic effect graph |
| PERF009 | perf regression-ratchet finding | e | R | c | KEEP: bench ratchet, via criterion |
| PERF010 | yaml load without C loader in hot path | e~ | F | c | DROP: Python-specific |
| PERF011 | full-repo-scan API called in loop over symbols | e~ | F | c | DROP: self-lint of v1 |
| PERF012 | duplicate spawn calls with same args in one function | e | G,F | m | DROP: heuristic |
| PERF013 | repeated `ast.walk` over same tree | e | F | c | DROP: Python-specific |
| PERF014 | `re.finditer` nested in pattern loop | e | F | c | DROP: Python-specific |
| PERF015, PERF016, PERF017, PERF018 | loop-variant effect calls, git spawn in loop, uncached negative branch, hoisted-then-recomputed value | w | G,F | m | DROP: heuristic self-lint |
| DUP001, DUP002 | diff introduces clone of existing symbol (opt-in `[dup].enforce`) | e | G,D,F | e | KEEP: clone detection is a product feature; native |
| DUP003 | dup enforce requested but native engine unavailable (fail closed) | e | K,X | c | MERGE into generic UNRESOLVED-substrate outcome |
| FUZZ001 | fuzz-obligated function lacks `kind="fuzz"` test edge | e | G,K | c | DROP: opt-in, rarely used |
| FUZZ002 | fuzz parameter type has no registered arbitrary | e | G,K | c | DROP: opt-in, rarely used |
| FUZZ003 | fuzz-obligated function never fuzzed / stamp stale | e | G,R | c | DROP: opt-in, rarely used |
| EXHAUST001, EXHAUST002 | ambiguous re-raise / confirmed exception leak (errors-as-values) | e/e~ | F,G | m | DROP: Python exception analysis |
| EXHAUST003, EXHAUST004 | unresolved re-raise type / unresolved subscript exception | w~ | F,G | m | DROP: Python exception analysis |
| FFI001, FFI002 | pyo3 boundary raised-type declarations mismatch | e | F | m | DROP: Python-Rust specific |
| PROTO001 | requires/transition summary poisoned (unresolved callee) | w | G | m | KEEP: typestate protocol, unresolved-aware |
| PROTO002, PROTO003 | required/precondition state never established | e | G | m | KEEP: typestate protocol |
| PROTO004 | call to `requires` callee before precondition on same sequence | e | G | m | KEEP: typestate protocol |
| PROTO005 | protocol declaration issue (see T-0747 section) | e | G | m | MERGE into PROTO002 |

## 9. Strata design-model rules (SYS REL LINT PII HOST KRB CAP VMOD MSCLOSE SELFAUDIT)

All S-input, run inside the `sys` process gate (`sys_gate`, 6s plus a repo-wide
`SELFAUDIT001` walk) except where noted. REL ids come in declared / unproven pairs: a
`REL2xx/3xx` "missing X attr" rule plus a sibling "attr declared but no bound code
contains an X-shaped token" rule; v2 should model this as ONE parametric obligation.

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| SYS001 | `frob:channel/boundary/secret` names construct absent from `.strata` model | e | S,G | c | KEEP: code-to-design binding |
| SYS002 | boundary/secret node has no code binding | e | S,G | c | KEEP: design-to-code binding |
| SYS003 | undeclared cross-component import between design-bound files | e | S,G | m | KEEP: conformance, graph-based |
| SYS004 | `.strata` file failed to parse/elaborate | e | S | c | MERGE into generic load-error rule |
| SYS100 | undeclared public interface symbol on node | e | S,F | m | MERGE into SYS110 |
| SYS101 | declared `may` capability has zero observed sites | w | S,F | m | KEEP: declared-but-unexercised grant |
| SYS102 | src top-level dir entirely unbound to any node | e | S,F | c | KEEP: coverage totality |
| SYS103 | FOREIGN file with observed capability effect | e | S,F | m | MERGE into SYS102 |
| SYS105 | node `purpose=` profile does not cover observed effect | e | S,F | m | DROP: niche profile concept |
| SYS106 | code laundered into unbound file reachable from bound node | e | S,F,G | m | KEEP: laundering detection |
| SYS107 | node binds more than N files with broad `may` | w | S,K | c | DROP: size nag |
| SYS108 | duplicated `interface=` symbol on node | e | S | c | DROP: DSL parse error instead |
| SYS109 | symbol-form `via` names symbol absent from bound files | e | S,F | c | MERGE into SYS113 |
| SYS110 | real public surface has symbol outside declared `interface=` | e | S,F | m | KEEP: surface-leak detection |
| SYS111 | capability ratchet regressed vs recorded baseline | e | S,R | c | KEEP: capability ratchet |
| SYS112 | ambient `may` grant with no `because` justification | e | S | c | KEEP: grants need reason |
| SYS113 | `code=`/`via` glob matches zero files | e~ | S,F | c | KEEP: zero-match must be loud |
| SYS114 | outbound flow to foreign node with unconstrained destination | e~ | S | c | KEEP: SSRF surface |
| SYS115 | outbound flow missing declared rate | e~ | S | c | MERGE into SYS114 |
| SYS116 | undeclared provenance (derived_from) | e~ | S | c | MERGE into PII-family obligations |
| SYS117 | trust-as-identity tag without carries | e~ | S | c | MERGE into PII-family obligations |
| SYS200 | two nodes declare same `listens` port | e | S | c | KEEP: resource contention |
| SYS201 | overlapping path ownership claims | e | S | c | KEEP: resource contention |
| SYS202 | two nodes bind same pipe name | e | S | c | MERGE into SYS201 (resource kind param) |
| SYS203 | multiple non-store nodes write one store | e | S | c | MERGE into SYS201 |
| SYS204 | arbitrated resource still has unserialized accessors | e | S | c | MERGE into SYS201 |
| SYS205 | bound code effect contradicts declared access mode | e | S,F | m | KEEP: mode conformance |
| SYS900 | branch/worktree-explicit SYS audit unmeasured | e~ | S,X | e | DROP: audit entry point, not a rule |
| SELFAUDIT001 | frob's own self-conformance roll-up (SYS1xx/2xx, REL2xx, compliance) | e | S,F | e | DROP: dogfooding of v1 repo, run as CI test |
| HOST001 | two service users share writable path / unguarded port | e | S | c | KEEP: host isolation proof |
| HOST002 | service user owns setuid/sudoers/root-with-low-trust paths | e | S | c | MERGE into HOST001 |
| HOST-BLAST | compromised-user blast-radius claim refuted | e | S | m | KEEP: scenario proof |
| KRB001 | node declares unconstrained delegation | e | S | c | DROP: Kerberos niche pack |
| KRB002 | node declares spn (roastable) | e | S | c | DROP: Kerberos niche pack |
| KRB003 | constrained delegation chain reaches higher-trust node | e | S | c | DROP: Kerberos niche pack |
| KRB004 | lower-trust realm reaches higher-trust realm via trust edge | e | S | c | DROP: Kerberos niche pack |
| CAP001 | node projected demand exceeds declared capacity | e | S | c | KEEP: capacity proof |
| LINT001 | foreign-sourced flow has no declared rate | e | S | c | MERGE into SYS114/115 (rate obligation) |
| LINT002 | inbound flow rates exceed node service rate (no cache) | e | S | c | MERGE into CAP001 |
| LINT003 | ScaleRate scenario with no nested BoundClaim | e | S | c | KEEP: scenario sanity |
| LINT004 | risky `may` capability with no kill-switch flag | e | S | c | KEEP: kill-switch obligation |
| LINT005 | total inbound rate exceeds service_rate * replicas | e | S | c | MERGE into CAP001 |
| PII001 | `carries` tag not in PII category vocabulary | e | S | c | KEEP: vocabulary check |
| PII002 | flow touching PII node has no protection claim | e | S | c | KEEP: PII flow obligation |
| PII003 | PII node has no retention/erasure | e | S | c | KEEP: retention obligation |
| PII004 | flow from PII node has no handling attr | e | S | c | MERGE into PII002 |
| PII005 | no_pii / carries contradiction | e | S | c | MERGE into PII001 |
| REL200, REL201 | flow lacks timeout / timeout declared but no bound timeout token | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL210, REL211 | long-lived node lacks health / unproven health | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL220, REL221, REL222 | retry flow lacks backoff_jitter / non-idempotent retry / unproven backoff | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL230, REL231 | external node lacks circuit_breaker / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL240, REL241 | critical node lacks fallback / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL250 | critical-flow dst is a structural singleton | e | S | c | MERGE into parametric declared+proven obligation |
| REL260, REL261 | queue/consumer lacks bounded_intake / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL270, REL271, REL272 | boundary flow lacks observability / unproven / multi-hop lacks correlation | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL280, REL281 | service lacks slo/error_budget / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL290, REL291 | multi-writer store lacks owner/reconciliation / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL300, REL301 | multi-store op lacks transaction/saga / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL303 | inbound-rate obligation on unauthenticated write into PII store | e~ | S | c | MERGE into parametric declared+proven obligation |
| REL310, REL311 | interactive node lacks bounded_cost / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL320, REL321 | event/queue lacks schema_version / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL330, REL331 | queue lacks/invalid delivery semantics / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL340 | synchronous hop chain exceeds max depth | e | S | c | KEEP: graph depth bound |
| REL350, REL351 | multi-downstream op lacks saga / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL360 | shared mutable node lacks shared_state declaration | e | S | c | MERGE into parametric declared+proven obligation |
| REL370, REL371, REL372 | clock_dependent flow lacks ordering_strategy / unproven / other | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL380, REL381 | serialization point over utilization / no capacity declared | e | S | c | MERGE into CAP001 |
| REL382 | read+write accessors, no alpha accessor (starvation) | e | S | c | DROP: advisory heuristic |
| REL383 | contended write access with no timeout attr | e | S | c | MERGE into REL200 |
| REL390, REL391 | kernel_interface lacks classification / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL392, REL393 | deployed_process lacks cgroup_bounds / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL394, REL395 | compiled_artifact lacks abi_compat_window / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| REL396, REL397 | boot_chain_stage lacks boot_attested / unproven | e | S,F | c | MERGE into parametric declared+proven obligation |
| VMOD001 | V-model requirement/spec/design/test graph not closed (opt-in) | e | S | c | KEEP: V-model closure over typed graph |
| MSCLOSE001 | milestone-scoped V-model artifact neither covered nor declared gap | e~ | S | c | MERGE into VMOD001 (milestone filter) |

## 10. Security, secrets, supply chain (SEC PII0xx structural VET)

| Rule | Detects | Sev | Inputs | Cost | Rec |
|---|---|---|---|---|---|
| SEC001 | tracked file contains credential-shaped text | e | F | m | KEEP: lexical-legit; Aho-Corasick + entropy |
| SEC002 | tracked `.env` / `.env.*` file | e | F | c | KEEP: trivial, high value |
| SEC003 | live Stripe key or PEM private-key header (unwaivable) | e | F | m | KEEP: unwaivable secrets |
| SEC004 | `frob:secret-fake` marker without reason | e | F | c | MERGE into WAIVE001 (reason-required) |
| SEC005 | repo-state value reaches argv sink without validator/`--` | e | F | m | DROP: taint heuristic, Python-centric |
| SEC110 | env-var read site (Python/TS/Rust) needing review | e | F | m | DROP: noisy inventory, not a defect |
| PII010 | model field name/type matches PII signature | e | F | m | KEEP: structural PII; cheap in Rust |
| PII011 | email-shaped string literal without fake marker | e~ | F | m | MERGE into SEC001 |
| PII012 | identifier/comment word resembles PII keyword | e | F | m | DROP: suggestion-tier noise |
| PII013 | client-storage write on `no_pii` node | e~ | F,S | m | MERGE into PII002 |
| VET001 | observed dependency has no `[vet.allow]` entry | e | F,K | e | KEEP: supply-chain allowlist |
| VET002 | observed capability not in package declaration | e | F,K | e | KEEP: capability scan of deps |
| VET003 | version bump adds capability vs stored verdict | e | F,R | e | KEEP: capability escalation |
| VET004 | obfuscation/decode-to-exec signals in dependency | e | F | e | KEEP: supply-chain risk |
| VET005 | osv advisories (opt-in osv-scanner) | e | X | e | KEEP: delegate to osv-scanner, offline cache |
| VET006 | CVE fingerprint needle matched in dependency | e | F | m | MERGE into SEC-CVE-FINGERPRINT-001 |
| VET007 | manifest dependency unpinned | e | F,K | c | KEEP: pinning policy |
| VET008 | setup data_files escapes package tree | e | F | c | DROP: Python packaging specific |
| VET009 | GitHub Action pinned to mutable ref | e | F | c | KEEP: cheap CI hygiene |
| VET010 | tracked binary blob (.whl/.so/.node/.wasm) | e | F | c | KEEP: cheap |
| VET011 | dependency newly published within cooldown window | e | X | m | KEEP: needs registry data, opt-in |
| VET012 | advisory data unavailable (no cache, no network) | e | X | c | MERGE into generic UNRESOLVED-substrate outcome |
| VET-JS | npm lifecycle script not allowlisted | e | F,K | m | KEEP: install-time exec (ecosystem pack) |
| VET-JS003 | npm name possible typosquat | e | F | c | KEEP: cheap |
| VET-JS004 | npm dep from non-registry source | e | F | c | KEEP: cheap |
| VET-PY001 | setup.py cmdclass | e | F | c | KEEP: ecosystem pack |
| VET-PY002 | `.pth` startup code | e | F | c | KEEP: ecosystem pack |
| VET-PY003 | pickle payload files | e | F | c | KEEP: ecosystem pack |
| VET-RS001 | `build.rs` exercises capabilities | e | F | m | KEEP: ecosystem pack |
| VET-RS002 | proc-macro crate dependency | e | F | c | KEEP: ecosystem pack |
| VET-SOURCE-UNAVAILABLE | dep source not locally available, scan never ran | e | F | c | MERGE into generic UNRESOLVED-substrate outcome |
| VET-TIMEOUT | per-package scan budget expired | e | F | c | MERGE into generic UNRESOLVED-substrate outcome |

## 11. Web-app families (249 ids; catalog says "reserved, not yet implemented")

Epic T-5140 (T-5141..T-5148), reserved by T-5301. All gated behind
`frob.webapp.detect_frameworks` (nextjs, vite, django, flask, fastapi, rails, laravel,
sveltekit, astro); a repo with no detected framework short-circuits past all of them.
Substrate modules exist (tree-sitter queries, per-family `*_findings` functions, ~17k
lines) but only A11Y (`_a11y_gate.py`, pkgutil hook discovery) and LAYOUT
(`_layout_gate.py`, gallery manifest) have a gate. frob.toml sets every one `error`
(SEO, WEBPERF `warn`, LAUNCH `advisory`). Inputs F (+ S for some), cost m each, cost grows
with web source tree size. Recommendation for ALL rows below: DROP from v2 core; if
wanted, ship as an out-of-tree rule pack on the same plugin ABI as VET ecosystems
(reason: product scope creep, half-built, delegates better to axe/semgrep/lighthouse).

| Rule ids | Family / topic | Count | Sev |
|---|---|---|---|
| WEBSEC101-125 | injection / XSS / SSRF / deserialization / sinks (T-5141..T-5144) | 25 | e |
| WEBSEC201-230 | authn/authz routes, sessions, JWT/OAuth, passwords, CSRF | 30 | e |
| WEBSEC301-334 | headers, CORS, TLS/random, logging, limits/bounds, config/debug | 34 | e |
| WEBSEC401-419 | supply chain, RLS, LLM-app risks | 19 | e |
| COMPLY101-127 | privacy, GDPR/CCPA, commerce, sector compliance (T-5145) | 27 | e |
| A11Y101-135 | WCAG structure, forms/contrast, interaction, statement (A11Y107-A11Y114 wired as content lint; T-5146) | 35 | e |
| SEO101-127 | tags, crawl, robots/sitemap/hreflang (T-5147) | 27 | w |
| WEBPERF101-115 | markup and server perf (T-5147) | 15 | w |
| SQL101-130 | SQL/ORM lint, squawk/sqlfluff adapters (T-5148) | 30 | e |
| LAUNCH101-107 | launch checklist content (advisory only) | 7 | a |
| LAYOUT001-003 | gallery entry unreviewed / stale source hash / no render artifact | 3 | e~ |
| SQLEXPLAIN001 | waiver of a SQL perf finding with no real EXPLAIN ANALYZE | 1 | e~ |

## 12. Pseudo and fixture ids

| Id | What | Rec |
|---|---|---|
| E501, F401, I001 | ruff codes carried in the registry so Tier-A/quarantine can name them | DROP: tool-diagnostic ids are not gate rules |
| TIERBDEMO001 | synthetic id for the Tier-B fix-engine demo fixture, never emitted, not in the registry | DROP: test fixture |

Id count by recommendation is in section 18.

## 13. How `frob check` is staged (v1 pipeline)

Entry: `src/frob/_cli_parsers/_check.py` -> `app/check_runner.py` -> `frob.check.run_check*`
(python) / `run_check_cpp` / `run_check_rust` / `run_check_ts`; project type from sentinel
files (Cargo.toml rust, CMakeLists.txt cpp, pyproject.toml python, package.json+tsconfig
typescript, else python fallback; unknown triggers CHECK001). Python mode order:

| Step | What happens | Notes |
|---|---|---|
| 0 refusal | bare `frob check` (no `--only`) under `FROB_AGENT` refuses (exit 1) unless `FROB_ALLOW_FULL_CHECK=1` | a full pass exceeds the ~120s agent foreground cap |
| 1 locks and admission | `derived_state_lock` SHARED for the whole run; `_admission_budget` registers a pid marker under `<git-common-dir-parent>/.frob/check-admission/`, admitted workers = max(1, min(cores, MemAvailable/300MB) / live concurrent checks), patches `os.cpu_count` for downstream pools | env: `FROB_CHECK_MAX_WORKERS` (0 = off), `FROB_CHECK_PER_WORKER_MEM_MB`; stale markers reaped by pid liveness; "degrade, never refuse" |
| 2 prechecks | sync, fail-closed, before any stage: DERIVED001 (corrupt `.frob` artifacts), NATIVE001 (stale native, auto-rebuild self-heal), AUTOFIX001 (abandoned `--fix` journal) | each short-circuits to a single-result CheckResult |
| 3 resolve | `--only` / `--skip` expanded; stage-group aliases are pure sugar; `--only` and `--skip` naming one stage refuses | `FROB_CHECK_STOP_BEFORE` = CI bisect knob (lock/detect/tasks/submit) |
| 4 memo scope | `run_memo_scope()` opens a per-run `memoize_per_run` cache (build_graph, analyze_project) keyed on call args only | never active outside a run |
| 5 task fan-out | one `ThreadPoolExecutor` runs: `ruff check`, `ruff format --check`, `ty check` (once per target platform linux/win32/darwin), cycle, dup, arch, bind, exports, optional PyCharm inspection, and the `gates` stage | repo-wide stages (arch, cycle, dup, exports) ignore `--files` |
| 6 gates stage | `run_gates(GateConfig)`: load inputs (graph snapshot, ticket queue, diff vs `--base`, coverage, lock, rules, systems) -> split selected gates into thread jobs and `_ProcessJob`s -> partition process jobs into cache hits/misses -> submit; thread-cache substitution for `_CACHEABLE_GATES` -> merge in `_CANONICAL_GATE_ORDER` (byte-identical output regardless of finish order) | forkserver pool with preload; env stamps carry log level, lock keys, parse-artifact cache path, PDEATHSIG |
| 7 post-process | `_assemble_gate_report`: apply `[gates.severity]` overrides (never to UNRESOLVED or `severity_pinned`), `_apply_waivers`, WAIVE-family audits, ratchet resolve, SUBJECT001, telemetry `gate_rule_counts` | waived findings kept in `waived` tuple |
| 8 tail | bare run only: deploy-drift, deploy-conformance (if `deploy/`), claude-config-drift (if hook present) | excluded by any `--only` |
| 9 output | errors, warnings, notes, TOOL SUMMARY (pass / FAIL / UNRES), per-gate `gate-summary` wall brackets, `--json` CheckResult, `--budget` key | exit code = errors only; WARN/UNRESOLVED/ADVISORY never fail |

Other modes: cpp (cmake build short-circuits tests, clang-tidy, clang-format, ctest,
optional valgrind), rust (cargo check, clippy, fmt --check, test, optional valgrind),
typescript (tsc, eslint, prettier, vitest; missing npx = soft skip).

### Flags and modes

| Flag / mode | Semantics |
|---|---|
| `--only X` (repeatable) | stage name (ruff, ty, cycle, dup, arch, bind, exports, gates), any individual gate name, or group alias; `--only list` prints groups |
| stage groups | `lint` ~1s, `static` ~18-23s, `gates-fast` ~31-37s, `gates-native` ~16-43s, `gates-security` ~12-13s on v1's own repo; sized for the 90s agent budget |
| `--skip STAGE` (T-4524) | unified repeatable comma-split flag (ruff, ruff-check, ruff-format, ty, arch, cycle, dup, bind, exports, gates, tests, build, clang-*, cargo-*, fmt, tsc, eslint, prettier); 20 hidden deprecated `--skip-<stage>` flags |
| `--files PATH` | scope ruff/ty/gates compute to a path set (land's rapid check passes diff + one-hop dependents); `REPO_WIDE_GATES` and `_REPO_WIDE_STAGES` stay unscoped, each logged INFO |
| `--ticket ID`, `--base REF` | scope/pre-work/land-parity context; diff base for drift/coverage |
| `--budget SECONDS` | self-selects and orders stage groups to fit using an EMA of past group wall times (`.frob/check-budget-timing.json`) and a min-of-window sample file for the post-land derived budget; persists the remainder (`.frob/check-budget-state.json`) as resume state; reports `BUDGET001` and a `budget` JSON key (`requested_seconds`, `executed_groups`, `skipped_groups`, `complete`); skipped = universe minus executed, not just this call's deferred list |
| `--delta`, `--stamp-baseline` | `.frob/baseline` holds finding fingerprints (rule + file + message digest) plus per-file content hashes; `--delta` reports only violations absent from the stamp; missing or stale baseline degrades to full set with a warning; agent-facing opt-in |
| `--stamp-coverage` | records coverage.xml as `.frob/coverage-stamp`; TEST006 compares it to the live snapshot |
| `--no-cache` / `FROB_NO_GATE_CACHE=1` | bypass the whole gate-result cache for one run |
| `--fix` | tiered auto-fix (below); bare `--fix` with neither `--ticket` nor `--fix-all` refuses; `--fix-ruff` is a separate raw `ruff --fix` + format write pass |
| `--land-parity` | runs LANDPARITY001/002 and the other land-time diff rules before a Done report |
| `--json`, `--type`, `--valgrind`, `--build-dir` | rendering, language override, memcheck, cmake dir |

### `--fix` tiers (docs/design/check-fix-engine.md)

| Tier | Contract | Handlers in v1 |
|---|---|---|
| A (deterministic) | pure rewrite or no-op, one rule id = one handler, never writes waivers/frob.toml/ratchet | DOC007, DOC002, FMT001, DSTACK001, FMT002, TEST010, SUPPRESS001, REG010, DOCENUM001, REL002, plus TICK002 renumber, TICK006 phantom refile, WAIVE004 stale-waiver removal, E501 merge-introduced wrap |
| B (apply-verify-commit/rollback) | snapshot bytes, apply ONE fix, re-run affected gates + bound tests, keep or revert; sequential | DEAD001 unreferenced-symbol removal (plus a demo fixture) |
| C (fix-it only) | never mutates; emits structured FixIt with optional proposed patch and reason_unfixable | TODO001 |
| manual | rule id in no table (default for new rules); fixability registry field is generated and drift-locked | everything else |

Blast radius: `--ticket T --fix` scopes every fix to the ticket's declared scope and lease
(same filter as land's pre-land Tier-A pass; out-of-scope edits are reverted and reported);
`--fix --fix-all` is the explicit repo-wide opt-in; an autofix manifest under `.frob/` is
written after each handler and cleared at completion so a killed run is detectable
(AUTOFIX001). After Tier A/B the gates stage is re-run once, then Tier C fix-its computed.

### Gate cache and derived state

| Store | Purpose |
|---|---|
| `.frob/gate-cache.db` | per-gate results: thread gates keyed by observed-read file hashes + tracked-membership key + side-input fingerprint (frob.lock, coverage, rules, queue, diff, current date/version); process gates keyed by sha256 of `git ls-files -s` (whole tree, whole gate) |
| `.frob/cache.db`, `.frob/parse-artifacts.db` | parsed graph and tree-sitter artifact caches (graph load costs ~3.3s warm) |
| `.frob/dup.db` | clone-detection index |
| `.frob/derived.lock` | cross-process flock; check holds SHARED for the whole run; writers take EXCLUSIVE only for the commit tail (T-3478), env stamp lets pool workers recognize inherited holds |
| `.frob/telemetry.jsonl` | cli/ticket/tool/dispatch events and `gate_rule_counts` per run (diagnostics only) |
| `.frob/check-admission/` | pid markers for concurrent check budgeting |

## 14. Profile system

| Aspect | v1 behavior |
|---|---|
| Config | `frob.toml [profile] profile = rapid / standard / fortress`; absent = `standard` (upgrading frob never silently relaxes a repo); `override_ratchet = true` keeps rapid past thresholds (this repo: rapid + override); `backpressure_max_depth` / `backpressure_max_age_s` tune standard |
| rapid | land-time check is SCOPED-synchronous (`--files` = diff + one-hop dependents) and still blocks the land; skips TEST016 on land, no pre-commit sweep, no baseline-snapshot worktree, REL001 off, light evidence for docs/chore; post-land full sweep is DEFERRED (detached, batched, files a ticket instead of reverting); unbounded backpressure ceilings; every skipped check appended to `.frob/rapid-debt.jsonl` |
| standard | unscoped-synchronous full `frob check` at land (25-45 min measured on v1's own ~4200 tickets / ~1400 files), synchronous revert-on-red post-land sweep, baseline thread; bounded backpressure depth/age |
| fortress | enum member only, no wiring except backpressure ceilings depth 0 / age 0 (fully synchronous verification); reused as the quarantine override shape |
| never relaxed in any profile | ledger integrity checks and LAND-PROOF verification |
| auto-ratchet | one-way: if rapid and any of file count >300, ticket count >200, live lease count >5 trips, persist `.frob/profile-ratchet.json` and force standard forever (only `downgrade_profile_ratchet` reverses it); scaffold writes `rapid` into new repos; `frob doctor`/scaffold advise rapid at 4200 tickets or 1400 files (a second, inconsistent threshold pair) |
| `LandProfileSettings` | one record resolves profile name into land-pipeline toggles so call sites never branch on the name (PROFILE001 enforces) |

## 15. Waiver model

| Aspect | v1 behavior |
|---|---|
| Forms | `frob:waive RULE reason="..."` source comment (symbol-bound via symref, otherwise file/line), `preset="name"` (reason from `WAIVE_PRESETS` table, explicit reason wins), strata `waive "RULE" reason=...` clause; policy rule ids waivable too |
| Optional attrs | `until="YYYY-MM-DD"` (WAIVE005), ticket binding (WAIVE006/007), `ceiling=N` for metric rules (ARCH001), `follow_up="T-####"` / `permanent="true"` for WIRE001, `until="ticket-closed:T-##"` premise predicates (WAIVE012) |
| Matching | `_match_waiver` against `Violation.rule` + symref/file; directory-prefix reach only for `_PACKAGE_SCOPED_RULES` (TEST003/004/007), policed by WAIVE003; waived findings move to `GateReport.waived`, never silently dropped |
| Unwaivable | `_UNWAIVABLE_RULES`: TEST008, SEC003, TICK001, TICK002, EXCL001, COMPLIANCE006, REG012, DEC003, WIRE002; plus rule ids only reachable via tool channels (arch categories other than long-function) are flagged WAIVE002 |
| Hygiene gates | WAIVE001 reason, WAIVE002 can-never-match, WAIVE003 over-breadth, WAIVE004 stale (full unscoped runs only, structurally unverifiable rules excluded), WAIVE005 expiry, WAIVE006/007 ticket state, WAIVE008-010 phrase/dead-waiver heuristics, WAIVE011 lock producer abandoned, WAIVE012 premise expiry; strata twins SYSWAIVE002/003, RELWAIVE002 |
| Audit | periodic honesty audit with a persisted commit watermark (`_waive_audit_watermark`), verdicts STILL NECESSARY / OBSOLETE / COP-OUT / PERMANENT BY DESIGN |
| Suppression of severity | `[gates.severity]` per-rule override (error/warn/advisory), never touches UNRESOLVED or `severity_pinned`; new rules start warn for one release |
| Design smell | a waiver is a comment in code, so waiver count (hundreds) and WAIVE004 full-run cost grow with repo; CPLACE001/DOCARCH/NARR rules exist only to police waiver-comment bloat |

## 16. Ratchet pools, baselines, quarantine, verify sweep, rapid debt

| Mechanism | v1 behavior |
|---|---|
| Ratchet pool (`frob.gates._ratchet`) | `frob-ratchet.lock.json` (committed) holds per-rule pools of baselined finding keys with dates; `resolve_ratchet_severity` = warn if baselined, error if new; opt-in via `[gates.ratchet] rules` (this repo: ARCH104, DOCARCH002); `frob pool snapshot RULE --key ...` merges, `frob pool clear RULE --key K --reason R` removes (reason mandatory); BASE001 reports pools whose live count exceeds committed baseline (wired late) |
| Baseline locks | `frob-coverage.lock.json`, `frob-ratchet.lock.json`, `frob-deprecated-baseline.lock.json`; `producer_status` flags ABANDONED when code-glob commits since last stamp pass a threshold, unless `pin {reason, ticket}`; surfaced by `frob status`, TEST012, DEPR006, WAIVE011; POSIX/Windows lock backends |
| Delta baseline | per-agent `.frob/baseline` (see section 13), not committed, advisory |
| Unresolved / advisory outcomes | UNRESOLVED = could not determine (own counter, rendered UNRES), ADVISORY = always shown, never fails, never ratchets, never raises quarantine |
| Verify watermark | durable verify queue (one intent per land) + watermark "main verified through commit X", independent of any worker (`.frob/` JSON, schema-versioned) |
| Coalescing worker | reads queue once, verifies ONLY the tip once per invocation (coalesce, never iterate); batch test selection runs the union touched-set in ONE pytest process |
| Attribution ladder | tier 1 symbolic (finding symbol reached by which commit's touched symbols via reference graph), tier 3 bisect (log2 N scoped re-verifications in detached snapshot worktrees); unmeasurable causes separated (T-3886) |
| Backpressure | bounds unverified window by depth and age; blocks (never fails) a land at the ceiling; per-profile ceilings |
| Quarantine circuit breaker | `.frob/quarantine.json` raised when a batch verification is red; while raised, deferred landing off (ceilings forced to depth 0); proportional filter drops trivial unattributed ruff I001/F401; clears ONLY via dispositions (filed ticket or dismissed reason) for every finding, never on green; unreadable store treated as raised |
| Verify sweep / drain | `frob verify` CLI (status, dispose, drain); rapid-profile automatic watermark drain (T-2310) with measured 49% refusal rate fixed by self-race exemption; resource budget so it never starves foreground agents |
| Deferred post-land sweep (rapid) | `frob ticket sweep-async <id> --commit <sha>` detached, runs the full check in a snapshot worktree (so it never holds root's derived lock; a 29-minute SHARED hold once blocked a land 25 min), files a regression ticket rather than reverting, keeps a rolling `.frob/rapid-sweep-baseline.json` |
| Rapid debt | `.frob/rapid-debt.jsonl` append-only audit log (gitignored since T-2997); an entry is LIVE until a later baseline write at the entry's commit or a descendant; `frob verify status` shows live entries and exits non-zero while any exist (unmeasured is not zero) |
| Land-time checks | land-parity, cross-ticket leakage, empty-diff close, new-gate-rule acceptance, BUG002/BUG003/TEST016 mutation evidence (sync for security kind only under standard) |

## 17. What makes `frob check` slow in v1

Evidence: docs/audits/check-performance.md (T-0928 and remediation logs),
docs/audits/perf.md, `frob.toml` timing comments (T-0399/T-0974), land-profiles.md,
tickets-verify-sweep.md, gates.md section "Per-gate result cache". docs/guides/agentic-time-profiling.md
is diagnostics-only (telemetry, footgun tips such as REDUNDANT_RERUN, FAST_EXIT1,
REPEATED_FAILURE, gate_rule_counts); it contains no check-cost data itself, but its
`kind="cli"` stream and `frob doctor --usage` are how retread cost was found.

1. Whole-repo work per invocation. A full pass measured 25-45 min unscoped at land on a
   ~4200-ticket / ~1400-file repo; a typical full gates run is ~90s summed across groups,
   dominated by `test` 13.7s, `archgate` 11s, `perf` 9.5s, the `static` bucket 23s, `sys` 6.2s,
   `coverage` 5s, `pii_structural` 4.6s, `dead_symbols` 3.5s, `secrets` 2.9s.
2. Many gates, each its own walk. ~72 gate functions; sys, secrets, pii_structural,
   walk_lint, render_lint, wire, cache, lexcheck, 12 schema gates each independently walk and
   re-read (and often re-parse) the tracked tree. No shared single-pass visitor; PERF007 could not
   see cross-gate duplicate walks (audit Finding 4). Reachability and callgraph rebuilt per consumer
   (COV006 once made ~2000 `parse_file` calls).
3. Graph load tax. Every invocation pays a warm `build_graph` (~3.3s) before any gate runs; the
   mandatory `--only` chunked loop (to fit the 120s agent cap) pays it 5x (~13s overhead).
4. Python concurrency model. Cheap gates share a GIL-bound thread pool; CPU-bound gates moved to
   a process pool (T-0415) which pays forkserver+preload cold start and pickling; cold-start
   variance of ~18s (35s vs 16.6s on back-to-back gates-native runs). Each worker cold-imports
   `frob`, `frob_core`, `strata_core`.
5. Cache granularity. Process-gate cache key is sha256 of the whole tracked-tree listing: any edit
   anywhere invalidates every root-scanning gate (whole-gate granularity, not per file). Thread-gate
   cache covers only 7 snapshot-only gates and needed side-channel fixes after a stale-DRIFT001 bug.
6. Lexical or heuristic gates with unbounded scans: PERF effect-graph BFS per candidate loop, TDD001
   git-history archaeology, TEST016/BUG002/BUG003/INV010 spawning real test subprocesses,
   dup R3-R5 native-call-per-symbol (>300s cold, left off), WAIVE004 needing a full run, REF001
   whole-repo reference search.
7. Subprocess and toolchain fan-out: ruff x2, ty x3 platforms (~1.2s each extra), optional PyCharm
   inspection, pytest for coverage evidence, osv/network in VET.
8. Locking. The run holds a SHARED derived-state lock end to end; a writer (land) waited 25 min on
   a 29-min sweep; fixed by running the sweep in a snapshot worktree. Pool workers needed inherited-lock
   env stamps to avoid deadlock; admission registry exists because 51 forkservers once used 14.5GB.
9. Profiling blind spot. cProfile and the stack sampler cannot see thread/process-pool gate work
   (audit Finding 0), so costs were attributed from per-gate wall brackets, slowing diagnosis.
10. Severity/waiver bookkeeping: 580 per-rule severity overrides, hundreds of waiver comments, and
    post-processing passes over every violation (waiver match, stale-waiver audit, ratchet) at the end.
11. Land-path ceremony multiplies it: pre-land check + merge-queue + post-land sweep + baseline worktree
    + mutation evidence; `rapid` exists only to dodge this, at the price of rapid-debt and a
    deferred-verification system (queue, watermark, worker, backpressure, quarantine, bisect) that is
    itself large machinery built to hide check latency.

## 18. v2 recommendation summary

Counts are rule-id counts by the Rec column in sections 2-12 (computed by script,
rows listing several ids count each).

| Section | KEEP | MERGE | DROP |
|---|---|---|---|
| 2 core graph/coverage/drift/scope | 15 | 8 | 3 |
| 3 invariants/tests/evidence | 17 | 14 | 15 |
| 4 docs/narrative | 7 | 11 | 18 |
| 5 tickets/release/process | 30 | 18 | 21 |
| 6 waivers | 5 | 6 | 4 |
| 7 registry/decisions/compliance/threat | 16 | 12 | 3 |
| 8 schema/arch/lang/perf/dup/fuzz/exhaust/ffi/proto | 10 | 4 | 44 |
| 9 strata design model | 24 | 64 | 10 |
| 10 security/secrets/vet | 21 | 7 | 4 |
| 11 web families (249) + LAYOUT (3) + SQLEXPLAIN001 (1) | 0 | 0 | 253 |
| 12 ruff pseudo ids (E501, F401, I001) | 0 | 0 | 3 |
| Total (667) | 145 | 144 | 378 |

KEEP ids are the v2 core rule candidates; MERGE ids fold into a surviving rule or a
parametric rule (so v2 rule count is roughly 145 plus a few dozen parametric survivors, not
667); DROP is 57 percent of ids but 249 of those are the unbuilt web packs.

Design guidance distilled for Rust v2:

- Core set worth rebuilding as typed Rust rules over one shared graph snapshot: DRIFT, AFFECT, COV001/002/003/004/008,
  PARSE, CYCLE, TODO001/002, DSL001 (parser-level), SCOPE001, QUEUE, INV001/002/007/051, TEST001/003/005/006/008/015/018,
  DOC001/002/004/006/012, DOCENUM, REF001, TICK core, MILE001/003, DEPR005, REL001/002, WAIVE001/002/004/006/012,
  REG core, DEC001/002, SEC001-003, PII010, DUP, DEAD001, OPAQUE001, PROTO, WIRE001, ARCH001/104, LARGE001, VET core.
- Make "declared plus proven" one parametric obligation instead of ~51 REL ids; make "adopted then deleted", "load error",
  "lock staleness", "expiring directive" and "UNRESOLVED substrate" one generic rule each.
- Drop all rules whose purpose is policing v1 itself or Python specifics (PORT, LEXCHECK, WIRE003, CLAUDE001, PERF
  lexical set, EXHAUST, FFI, SUPPRESS, CONFIGPATH, PKG, NATIVE, *SCHEMA via serde deny_unknown_fields).
- Keep the severity enum (error/warn/unresolved/advisory) and the principle "unmeasured is not zero" (SUBJECT001, PARSE,
  zero-match POL000/SYS113); put default severity in rule metadata, not in a 580-line toml override table.
- Replace the id-literal registry (667 strings, scanned by regex, asserted by three drift locks) with a Rust enum/inventory
  macro; GATERULE001, REG010, DOCENUM001-for-rule-lists then vanish by construction.
- Replace the many independent walkers with one shared file/AST pass feeding rule visitors; cache per-file facts content-hashed
  (not whole-tree keyed); keep the thread/process split unnecessary by using native parallelism (rayon).
- Keep fix tiers A/B/C, `--files` scoping, `--budget` self-chunking only if a full pass is still >30s (likely unnecessary),
  ratchet pools with mandatory-reason clear, quarantine-clears-only-on-disposition, waiver reason requirement and ticket-bound expiry.
- Web families (249 ids) and Kerberos/host/compliance strata packs should be optional plugin packs, never core.

## 19. Phase-2 coverage proof

- Registry denominator 667; script check after final edit: every one of the 667 ids from the
  `_KNOWN_GATE_RULES` AST extraction appears in sections 2-12 exactly once (411 individually or
  grouped in sections 2-10, 249 web-family ids by range in section 11, plus E501/F401/I001,
  LAYOUT001-003 and SQLEXPLAIN001); 0 missing, 0 duplicated in sections 2-10.
- Done 667, pending 0, blocked 0. Soft spots (not blocked, but read less deeply): per-rule
  detail for web-family ids (catalog says reserved; code under `src/frob/webapp/` not read rule by rule),
  and exact in-code default severities for the 87 `~` ids (taken from doc tier text, not every emit site).
- Not enumerated as rule ids because they are not in the registry: ruff/ty/cycle/dup/arch/bind/exports
  tool-stage diagnostics, gate-summary pseudo results, and user `[policy]` ids (POL*).
