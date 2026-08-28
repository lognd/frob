# frob.gates -- enforcement gates, policy, and invariants

One sentence: the checks that join the obligation graph, the ticket queue,
docs, and policy rules, and turn every unaccounted-for change -- and every
unaccounted-for *absence* of change -- into a `frob check` failure.

Two enforcement halves (see `docs/rework.md`): the drift half (nothing
declared is silently broken) and the coverage half (nothing new escapes
declaration).

## Rule catalog

<!-- frob:enumerates src/frob/gates/_waive.py::_KNOWN_GATE_RULES members="AFFECT001,AFFECT002,ARCH001,ARCH101,ARCH102,ARCH103,ARCHSCHEMA001,BUDGET001,BUG002,BUG003,CACHE001,CAP001,CHECK001,CLAUDE001,COMPLIANCE001,COMPLIANCE002,COMPLIANCE003,COMPLIANCE004,COMPLIANCE005,COMPLIANCE006,COMPLIANCE007,COV001,COV002,COV003,COV004,COV005,COV006,COV007,COV008,CPLACE001,CPLACE002,CPPTHROW001,CVEFP001,CYCLE001,DEAD001,DEBT001,DEBT002,DEBT003,DEC000,DEC001,DEC002,DEC003,DEPLOY001,DEPLOY002,DEPLOY003,DEPR001,DEPR002,DEPR003,DEPR004,DEPR005,DERIVED001,DOC001,DOC002,DOC003,DOC004,DOC005,DOC006,DOC007,DOC008,DOC009,DOC010,DOC011,DOC012,DOC013,DOCBLOCKSSCHEMA001,DOCENUM001,DRIFT001,DRIFT002,DSL001,DUP001,DUP002,DUP003,DUPSCHEMA001,E501,ENV001,EXCL001,EXHAUST001,EXHAUST002,EXHAUST003,EXHAUST004,F401,FFI001,FFI002,FLAGCOV001,FMT001,FUZZ001,FUZZ002,FUZZ003,GATERULE001,GATESSCHEMA001,GRAPHSCHEMA001,HOST-BLAST,HOST001,HOST002,I001,INV001,INV002,INV003,INV004,INV005,INV007,INV008,INV051,KRB001,KRB002,KRB003,KRB004,LANG001,LANG002,LANG003,LANG004,LARGE001,LEDGERV1001,LEXCHECK001,LINT001,LINT002,LINT003,LINT004,LINT005,MILE001,MILE002,MILE003,MILE004,NARR001,NATIVE001,NATIVESCHEMA001,NEGEXIST001,OPAQUE001,PARSE001,PARSE002,PERF001,PERF002,PERF003,PERF004,PERF005,PERF006,PERF007,PERF008,PERF009,PERF010,PERF011,PERF012,PERF013,PERF014,PII001,PII002,PII003,PII004,PII010,PII011,PII012,PLACE001,PLATFORM001,PORT001,PORT001-IDENT,PORT001-PATH,PRE001,PROFILE001,PROFILESCHEMA001,PROTO001,PROTO002,PROTO003,PROTO004,PROTO005,QUEUE001,REF001,REF002,REF003,REFSCHEMA001,REG001,REG002,REG003,REG004,REG005,REG006,REG007,REG008,REG009,REG010,REG011,REG012,REL001,REL002,REL200,REL201,REL210,REL211,REL220,REL221,REL222,REL230,REL231,REL240,REL241,REL250,REL260,REL261,REL270,REL271,REL272,REL280,REL281,REL290,REL291,REL300,REL301,REL310,REL311,REL320,REL321,REL330,REL331,REL340,REL350,REL351,REL360,REL370,REL371,REL372,REL380,REL381,REL382,REL383,REL390,REL391,REL392,REL393,REL394,REL395,REL396,REL397,RELWAIVE002,RENDER001,ROOT001,SCOPE001,SCOPE002,SEC-CVE-FINGERPRINT-001,SEC001,SEC002,SEC003,SEC004,SEC005,SEC110,SELFAUDIT001,SUPPRESS001,SYS001,SYS002,SYS003,SYS004,SYS100,SYS101,SYS102,SYS103,SYS105,SYS106,SYS107,SYS108,SYS109,SYS110,SYS111,SYS112,SYS200,SYS201,SYS202,SYS203,SYS204,SYS205,SYSWAIVE002,SYSWAIVE003,TEST001,TEST002,TEST003,TEST004,TEST005,TEST006,TEST007,TEST008,TEST009,TEST010,TEST011,TEST012,TEST013,TEST014,TEST015,TEST016,TEST017,TEST018,TEST019,TESTINGSCHEMA001,TESTRUNNERSCHEMA001,THREAT001,THREAT002,THREAT003,THREAT004,THREAT005,THREAT006,TICK001,TICK002,TICK003,TICK004,TICK005,TICK006,TICK007,TICK008,TICK009,TICK010,TICK011,TICK012,TICK013,TODO001,TODO002,TODO003,TOPSCALARSCHEMA001,VET-JS,VET-JS003,VET-JS004,VET-PY001,VET-PY002,VET-PY003,VET-RS001,VET-RS002,VET-SOURCE-UNAVAILABLE,VET-TIMEOUT,VET001,VET002,VET003,VET004,VET005,VET006,VET007,VET008,VET009,VET010,VET011,WAIVE001,WAIVE002,WAIVE003,WAIVE004,WAIVE005,WAIVE006,WAIVE007,WAIVE008,WAIVE009,WAIVE010,WALK001,WIRE001,WIRE002,WIRE003" -->

| Rule | Gate | Fails when |
|---|---|---|
| DRIFT001 | drift | acked digest moved without re-ack (`frob ack`) |
| DRIFT002 | drift | edge endpoint no longer resolves (rename/delete) |
| AFFECT001 | affect_drift | a diff-touched symbol's `affects()` closure names a dependent doc anchor whose file was not also touched in this diff -- see "AFFECT001/AFFECT002 (T-0628)" below |
| AFFECT002 | affect_drift | a diff-touched symbol's `affects()` closure names a dependent symbol (`uses-contract`) whose file was not also touched in this diff -- see "AFFECT001/AFFECT002 (T-0628)" below |
| COV001 | coverage | public symbol has no `doc` edge (docstring counts via `doc` facet only if policy says so) |
| COV002 | coverage | changed symbol has neither a `frob:ticket` edge to an open ticket NOR an open ticket whose `scope` glob covers its file (so one scoped ticket accounts for a whole refactor, not a per-symbol directive). A `frob:ticket` edge to a ticket that just closed to `DONE` in this same uncommitted diff (`tickets.md` itself touched) also counts -- T-0214's grace window, see design decisions below |
| COV003 | coverage | ticket in state done with evidence ids that do not resolve to collected tests (never verifies PASS/FAIL, nor scope-binding -- see the T-0398 note below the table; node-, file-, and directory-level evidence ids all resolve, T-0298 below) |
| COV004 | coverage | attachment sha256 mismatch or file missing |
| COV005 | coverage | a diff-touched file's `frob:` directive now binds a PRIVATE symbol whose span overlaps this diff's hunks, where the same `(kind, target)` directive bound a PUBLIC symbol in that file at the diff's base revision -- a displaced obligation (T-0297), see design decisions below |
| COV006 | coverage | (warn) a `frob:tests` edge bound to a PRIVATE symbol whose test has no `frob.graph.callgraph` reachability to it -- see "COV006/COV007 (T-0483)" below, including a disclosed known false-positive shape |
| COV007 | coverage | (error, T-2866/T-2873/T-2874) a `frob:doc` edge whose src symbol is PRIVATE -- see "COV006/COV007 (T-0483)" below |
| COV008 | coverage | a diff deletes or renames a test file some ticket's evidence (open OR done) still cites, and that evidence no longer resolves against the current collected set -- see "COV008 (T-2688)" below |
| PLACE001 | coverage | (warn) a `frob:` directive that genuinely class-falls-back (not a directive that correctly resolved via `following` straight to a class it precedes) where a nearby real symbol looks plausibly missed -- see "PLACE001 (T-0504)" below |
| PARSE001 | parse_failures | `frob.lang.parse_file` could not parse/read a tracked source file at all -- its entire symbol/edge set is missing from this build (`GraphSnapshot.parse_failures`, T-0558/T-0561) |
| PARSE002 | parse_failures | `frob.lang.partial_parse_files()` names a file whose tree-sitter parse was SALVAGED around a syntax error (`has_error=True` but usable structure) -- every symbol after the error region is silently missing from this build (T-0905); graph-excluded paths (frob.toml [graph].exclude, e.g. deliberately-broken parser fixtures) are skipped, since they contribute no symbols and in-file waivers cannot bind there (T-0942) |
| CYCLE001 | cycle | (T-2364) `frob.check._python`'s import-cycle detector (tree-sitter import graph) found a cycle; severity SCALES with cycle size -- a 2-node mutual import is `info`, 3-5 nodes is `warning`, 6+ nodes (a structural cycle) is `error`. The finding's `file` is the cycle's deterministic lowest-sorted node (a stable representative for baseline-diff/waiver identity, not necessarily "the" culprit) -- waivable per-representative-file like any other file-scoped rule (T-2584) |
| TODO001 | coverage | bare TODO/FIXME comment (not `frob:`-prefixed) in a diff-touched file -- work marked but not accounted for at all |
| TODO002 | coverage | `frob:todo` edge bound to a non-open (closed or missing) ticket -- work accounted for, but the reference is dangling |
| SCOPE001 | scope | diff touches paths/symbols outside the active ticket's `scope` |
| SCOPE002 | scope | (warn, T-0998) scope-DECLARATION-time doc/code/private-helper closure gap -- see "SCOPE002 (T-0998)" below |
| PRE001 | pre-work | ticket moved to in-progress without a recorded pre-work sweep |
| INV001 | invariant | invariant has no evidence (test or policy rule) |
| INV002 | invariant | invariant has no code anchor (`frob:invariant`) |
| INV003 | invariant | (warn) a doc file under `INV003_SPEC_DIRS` (`docs/modules`, `docs/strata`) makes a claim-shaped exclusivity/normative assertion (`only`, `sole`/`solely`, `exclusively`, `nothing else`, `never...except`, `at most/exactly one`, verb required in the same sentence) with no `<!-- frob:invariant INV-### -->` marker naming a real (loaded) invariant, and no reasoned `<!-- frob:waive INV003 reason="..." -->` marker -- see "INV003 (T-0462)" below |
| INV004 | invariant | (warn, advisory) a `docs/**.md` section uses claim-shaped normative language (`must`, `must not`, `never`, `always`, `shall`, `guarantees`, `ensures`, `requires`, plus INV003's exclusivity vocabulary) but anchors ZERO `frob:invariant` markers and carries no reasoned `<!-- frob:waive INV004 reason="..." -->` marker -- see "INV004 (T-0452)" below |
| INV005 | invariant | (warn, T-0543/B12) an invariant's evidence collects (satisfies INV001) but is never shown, via a `frob:tests` edge or same-file trust to the anchor, to actually reach its `frob:invariant`-anchored symbol -- a name-match-only existence check proves nothing about which invariant a test covers; see "INV005 (T-0543)" below |
| INV007 | invariant | (T-0757) a `frob:invariant ... no_import="pkg[,pkg2,...]"` anchor whose own file actually imports the forbidden module or one of its submodules -- see "INV007 and INV008 (T-0757)" below |
| INV008 | invariant | (T-0757) a `frob:invariant ... establishes="..."` anchor with no `frob:tests ... kind="property"` edge bound to it -- see "INV007 and INV008 (T-0757)" below |
| INV051 | policy_weakening | (T-1482/T-1843) a `design/` policy whose scope is a strict subset of a containing policy's, but which re-declares `confine_use`/`at_call_require_arg`/`mediate` less restrictively than the parent already required for the same target |
| MILE001 | milestone | (error, T-2580) an OPEN ticket `blocked_by` another OPEN ticket whose EFFECTIVE milestone (`frob.tickets._doable.effective_milestone`, real semver order) is LATER than the blocked ticket's own -- a provable release deadlock: the earlier milestone can never ship while it depends on work scheduled for a later one. A terminal blocker, an unresolved `blocked_by` id, or either side's milestone failing to resolve at all (MILE003's concern) never fires |
| MILE002 | milestone | (error, T-2580) an OPEN ticket has an OPEN descendant (any depth via `parent`) whose EFFECTIVE milestone is LATER than the ancestor's own -- the same deadlock as MILE001, reached through the ticket hierarchy instead of `blocked_by`: `_done_transition_guard` already forbids an ancestor closing DONE while any descendant is open, so the ancestor's earlier milestone can never ship first either |
| MILE003 | milestone | (error, T-2576/T-2580 redesign) an OPEN ticket (any tier, including epics/stories) whose EFFECTIVE milestone cannot be resolved at all: no `milestone` declared on the ticket itself, none on any ancestor, and no repo `[tickets].default_milestone` configured. This is the ONLY enforcement mechanism for the milestone field -- nothing backfills the ledger to make it vacuously pass. Terminal (done/dropped) tickets never fire |
| MILE004 | milestone | (error, T-2579) a PAIR of OPEN `runs_last` tickets share the same effective milestone with their order left ambiguous -- neither a real `blocked_by` edge between them (either direction) nor both sides explicitly declaring `runs_last_parallel_safe=True` (a one-sided declaration does not count) |
| TICK006 | tickets | a Done report's affirmative "filed" claim (`Filed: T-####`, `filed as T-####`, `Filed T-draft-<hex>`, ...) whose id resolves to no block in `tickets.md` or `tickets-archive.md` -- see "TICK006 (T-0726)" below |
| TICK007 | tickets | (warn) a dispatchable (unblocked, unleased) CRITICAL/HIGH ticket has sat past its `frob.tickets.undispatched_stale` threshold -- see "TICK007 (T-0820)" below |
| TICK008 | tickets | (warn) a ticket in the checked ledger carries unknown/extra frontmatter field(s) (`Ticket`'s `extra="allow"` captured them into `__pydantic_extra__` instead of hard-failing) -- often a typoed known field, whose value is silently lost to the schema default; see "TICK008 (T-0842)" below |
| TICK009 | tickets | (warn) a planned/in-progress ticket's declared scope is over-broad (`frob.tickets.large_glob_warnings`) -- relocated out of `frob ticket doable`'s own per-invocation output; QUEUED is exempt (T-1645), see "TICK009/TICK010 (T-0714)" below |
| TICK010 | tickets | (warn) a cross-worktree lease file (`.git/frob-leases/*.json`) whose recorded worktree path no longer exists on disk -- names the lease file and the remedy; see "TICK009/TICK010 (T-0714)" below |
| TICK011 | tickets | (warn) a Done report's prose discloses deferred/cut work (a conservative disclosure-phrase scan) with no ticket id resolving nearby and no explicit no-ticket-needed reason -- see "TICK011 (T-1129)" below |
| TICK012 | tickets | (warn, T-2561) an IN_PROGRESS ticket's live cross-worktree lease (`.git/frob-leases/<id>.json`) records a scope path that no longer `scope_matches` its CURRENT declared scope -- the lease was recorded once at start/scope-mutation time and never re-synced when the declared scope narrowed by some other path, so it silently misleads every OTHER `read_all_leases` consumer (a `doable` collision check, an `--add` conflict refusal). Silent for a ticket with no live lease, or any non-in-progress state. Re-record via a scope-mutating `frob ticket scope` call |
| TICK013 | tickets | (error, T-2557) an IN_PROGRESS/PLANNED ticket's declared scope is EMPTY and it has not declared `no_scope_declared` -- the symmetric, strictly more dangerous case TICK009 (over-broad) does not cover, since an undeclared empty scope holds a write lease that tests nothing against it. Silent for a ticket with `no_scope_declared=True` (the T-2394 opt-out for a legitimately scope-free epic/decision-record ticket), any non-empty scope, any QUEUED ticket, or any terminal state; see "TICK013 (T-2557)" below |
| COMPLIANCE005 | compliance | a `docs/design/registry/compliance.yaml` `CMPL_REGISTRY_UNIT_IDS` member carries a `deferred`/undispositioned disposition instead of `handled_by`/`out_of_scope` -- see "COMPLIANCE005 (T-0788)" below |
| FMT001 | fmt | (warn) a diff-touched `frob:` directive comment line exceeds that file's own configured line length -- see "FMT001 (T-0851)" below |
| DEC001 | decisions | a `frob:decision AD-###` edge points at a missing record (opt-in: a `decisions/` dir must exist) |
| DEC002 | decisions | an `accepted` decision record has no `frob:decision` code anchor |
| TEST001 | test | public function/method has no `frob:tests` unit edge |
| TEST002 | test | unit edges for a symbol number fewer than `min_unit_cases` |
| TEST003 | test | interface (package whose public symbols are imported by another package) has fewer than `min_integration` integration edges |
| TEST004 | test | declared system has fewer than its `min_e2e` e2e edges |
| TEST005 | test | measured coverage below threshold (per-symbol branch, per-module line, or per-system line) |
| TEST006 | test | coverage evidence missing, or stale against current file hashes |
| TEST007 | test | a cross-package `frob:uses-contract` dependency has no pairwise integration test covering that boundary (opt-in via `[testing].pair_integration`) |
| TEST011 | test | (warn) coverage.xml predates a tracked source change (`stale_by_mtime`) -- see "TEST011/TEST017 (T-0464/T-1489)" below |
| TEST017 | test | coverage.xml joins far fewer known modules than the snapshot has -- deflation, e.g. dropped subprocess coverage (`module_join_fraction`) -- see "TEST011/TEST017 (T-0464/T-1489)" below |
| TEST019 | test | (warn) one or more symbols look per-symbol deflated (def line hit, every body line 0, corroborated by a `frob:tests` edge) -- possible partial xdist worker-crash merge loss (`suspect_deflated_symbols`) -- see "TEST019 (T-1824/T-1877)" below |
| DOC001 | doclink | a doc file matching `[gates.docs] include` globs (default `docs/**/*.md` -- new files auto-obligated) has no frob:describes anchor, no frob:doc edge into it, and is unreachable via markdown links from the roots (docs/index.md, README.md) |
| DOC002 | docanchor | a `frob:doc <file>#<slug>` edge whose target doesn't resolve: missing `#anchor`, missing file, or `<slug>` matches neither a heading slug (`frob.graph.dsl.slugify`) nor an explicit `<a id="...">` in `<file>` |
| DOC008 | doclink | (T-1231) an obligated doc's own inline markdown link `[text](target#frag)` doesn't resolve: relative `target` isn't a real file, or `#frag` matches neither a heading slug nor an explicit `<a id="...">` in the target |
| DOC009 | docstatus | (T-1232) a `docs/audits/*.md` file has no dated `Status: YYYY-MM-DD` (or `Status: SUPERSEDED (see <path>)`) header in its first 15 lines, or a superseded-by target doesn't resolve |
| DOC010 | docmake | (T-1230) a `` `make <target>` `` prose citation in an obligated doc isn't a real Makefile recipe |
| DOC013 | docseverity | (T-2080, warn) a markdown severity-table row (`` \| \`name\` (CODE, ...) \| ... \| SEVERITY_WORD \| ``) claims a severity word for CODE that contradicts an explicit `frob.toml` `[gates.severity]` override for that code |
| POL* | policy | user-defined rules from `frob.toml` (see below) |
| DUP001/DUP002 | clones | the diff introduces a clone of an existing symbol (opt-in, `[dup].enforce`) |
| DUP003 | clones | (T-0399) `[dup].enforce=true` but frob-core is not installed/built -- clone detection was requested but is unavailable; fails CLOSED (ERROR) instead of silently skipping |
| FUZZ001-003 | fuzz | fuzz obligations under `[fuzz]` (opt-in) |
| PERF001-004 | perf | lexical performance smells (build-a-set-once, etc.) |
| REL001 | release | release-readiness check |
| REL002 | release | (T-1009) `.frob-release.json`'s version disagrees with `pyproject.toml`/`uv.lock` -- always ERROR, never suppressed by land-ownership/`FROB_AGENT`; `frob release sync` is the fix (docs/modules/release.md#rel002-gate-t-1009) |
| SYS001 | sys | a `frob:channel/boundary/secret` directive names a construct id absent from the loaded `.strata` design model (opt-in: a `design/`, or `[strata].design_dir`, directory of `.strata` files must exist); suppressed for the whole run while any design file fails to load (SYS004 reports that instead) |
| SYS002 | sys | a `Boundary` or Secret-clearance `Node` in the design model has no `frob:boundary`/`frob:secret` code binding anywhere |
| SYS003 | sys | (error, T-2407) tier-2 code binding (`frob.strata.bind_code`/`check_import_conformance`) finds an undeclared cross-component import between two design-bound files; started warn-first on landing, promoted to error once T-2380/T-2403/T-2407's calibration burned genuine findings to zero |
| SYS004 | sys | a `.strata` design file failed to parse/elaborate; the message names a stale native build (`make core`) as the likely remedy when one is detected (T-0347, T-0248's `frob.strata.stale_natives`), per the T-0166 incident where a grammar-ahead-of-native mismatch masqueraded as a `.strata` syntax error |
| SELFAUDIT001 | sys | (T-0756, SYS205 leg T-1061, compliance leg T-1314) frob's own self-conformance (SYS100/SYS101/SYS102), resource-contention (SYS2xx), mode-conformance (SYS205), reliability (REL2xx), and compliance (`evaluate_compliance`, WARN-tier) audit surface, folded into the ordinary `frob check` gate pipeline -- see "Self-audit at land (SELFAUDIT001, T-0756)" below |
| SEC001 | secrets | a git-tracked file contains text matching a provider's real-looking credential shape (waivable with reason) |
| SEC002 | secrets | a git-tracked `.env`/`.env.*` file exists (`.env.example`/`.env.sample`/`.env.template` excepted) |
| SEC003 | secrets | a git-tracked file contains a live Stripe secret key (`sk_live_...`) or a private-key PEM header -- unwaivable, see `_UNWAIVABLE_RULES` |
| WAIVE001 | (always on) | a `frob:waive` directive is missing `reason="..."` |
| WAIVE002 | error (T-0753; was warn) | a `frob:waive` targets a rule id that can never be matched -- see "Waive boundary" below |
| WAIVE003 | (always on) | a `frob:waive` on a package-scoped rule (TEST003/TEST004/TEST007) reaches more than one distinct violated package/system id via directory-prefix matching -- see "Waiver over-breadth (T-0470)" below |
| WAIVE004 | warn (T-0753) | a `frob:waive` on a RECOGNIZED rule id matches zero findings this run at its own site -- see "Unnecessary-waiver detection (T-0753)" below |
| WAIVE005 | error (T-0753) | a `frob:waive`'s optional `until="YYYY-MM-DD"` boundary has passed -- see "Waiver expiry (T-0753)" below |
| ARCH001 | arch | `frob.arch`'s complexity-aware long-function check (docs/modules/arch.md) still flags a function after its flat-body filter -- the one `frob.arch` category channeled into a real gate `Violation`, waivable with a reasoned `frob:waive ARCH001 reason="..." [ceiling=N]` (T-0289) |
| ARCH101 | arch (WARN, T-0728) | `frob.arch._srp`'s LCOM4 `low-cohesion-class` category channeled into a real gate `Violation`: a class with at least `LCOM4_MIN_METHODS` (6) methods, at least `LCOM4_MIN_FIELD_USING_METHODS` (4) of which read/write a `self.<field>`, whose field-using methods form 2+ disconnected components in the "shares a field with" graph -- the class is really several unrelated responsibilities sharing one name. Same T-0728 debt-corpus posture as ARCH102/103: WARN, not ERROR, and observed to fire zero times against this repo's own source at calibrated defaults. Waivable with `frob:waive ARCH101 reason="..."`, symref-bound to the class |
| CPPTHROW001 | arch (ERROR, T-1034) | `frob.arch._cpp_mayraise`'s `cpp-noexcept-throws` category (T-0687, docs/modules/arch.md#cpp-may-throw-analysis-t-0687) channeled into a real gate `Violation` -- a C++ `noexcept` function whose computed may-throw set is non-empty with no encompassing `catch (...)`; ships at `Severity.ERROR`, not the `WARN` every other `arch`-family rule here uses, since an escaping exception from `noexcept` is `std::terminate` at runtime, not deferrable debt. Still an ORDINARY waivable rule (`frob:waive CPPTHROW001 reason="..."`), matching every other `arch`-family rule -- ERROR severity is not the same thing as `_UNWAIVABLE_RULES` membership. |
| LARGE001 | arch (ERROR, T-2831; WARN 2026-08 to T-2831) | `frob.arch._check_large_file`'s language-agnostic `large-file` category (any file over `max_file_lines`, `frob.toml`'s `[arch]` table or the calibrated default) channeled into a real gate `Violation` -- previously advisory-only (`frob.arch.analyze_project`'s own text/JSON output), invisible to `frob check`/`frob:waive` entirely. Test files and `fixtures/`-rooted data files stay exempt, same as the underlying advisory check (T-0368/T-0372). Shipped WARN first-turn-on (T-1102) against a 43-file (later re-measured 85-88-file) debt corpus, the same posture ARCH101-103 and EXHAUST001/002 shipped WARN-first for; T-2375 decomposed the corpus into 9 disjoint split/waive children (T-2822..T-2830), and once all 9 reached a terminal state T-2831 re-measured `frob.gates._arch.arch_gate` plus `frob.gates._waive._apply_waivers` against a live `build_graph` snapshot directly (the `frob check --json` summary does not decompose LARGE001 enough to verify this), confirmed zero unwaived findings, and promoted to ERROR. Waivable with a reasoned `frob:waive LARGE001 reason="..."`; a file-level finding has no function/class symbol, so the waiver binds by file/line, not `symref`. `frob arch <single-file>` (single-file mode) reports the identical finding a directory walk containing just that file would (T-1102 also fixed a `frob.arch.analyze_project` bug where single-file mode silently produced zero findings for every category, not just this one). Now ERROR: any newly-created oversized file reds main immediately -- land a `frob:waive LARGE001` in the same change as any file that crosses `max_file_lines`, do not defer it. |
| LEXCHECK001 | lexcheck | (error) a gate rule constructed from raw text (`re.search`/`match`/`fullmatch`/`findall`/`finditer` over source text, or a module-level compiled `_FOO_RE` pattern) with no `symref`/AST binding on its own `Violation` -- T-1662's own directive #4, closing the loop so a NEW lexical decider cannot land silently the way REF001/DEAD001-OPAQUE001/T-2178/T-2201/T-2187/T-2188/T-2243 all did (`frob.gates._lexical_selfcheck`, see [LEXCHECK001](#lexcheck001-t-2344) below) |
| FLAGCOV001 | flag_coverage | (error/unresolved) a CLI flag that parses on a declared `[[docblocks.commands]]` parser tree but never reaches its declared `config=` model (T-2387/T-0749's defect shape); UNRESOLVED (never a silent zero) when no source is declared, or `config=`/`forwarded=` is missing, or a dotted path fails to resolve (`frob.gates._flag_coverage`, see [FLAGCOV001](#flagcov001-t-2397) below) |
| REFSCHEMA001 | refs_schema | (error/unresolved) T-2390 epic child (largest table, 58 leaves): an unknown/misspelled key in a `[[refs.entrypoint]]` entry, undetected by `_load_allowlist`'s own path/reason-only `.get()` reads; UNRESOLVED when no `[refs] entrypoint_schema` is declared or it fails to resolve (`frob.gates._refs_schema`, see [REFSCHEMA001](#refschema001-t-2390-epic-child-t-2428) below) |
| NATIVESCHEMA001 | native_schema | (error/unresolved) T-2390 epic child (T-2429): an unknown/misspelled key in a `[[native]]` entry, undetected by `_parse_native_entry`'s own name/build_cmd/language-only reads; UNRESOLVED when no `[native_schema] known_keys` is declared or it fails to resolve (`frob.gates._native_schema`, see [NATIVESCHEMA001](#nativeschema001-t-2390-epic-child-t-2429) below) |
| PROFILE001 | profile_boundary | (error) `src/frob/**` references `frob.tickets._profile.ProfileName` directly outside `src/frob/tickets/_profile.py`/`src/frob/verify/_backpressure.py` -- the profile-collapse epic's own closing structural gate (T-2362), see [Land profile settings](tickets-verify-sweep.md#land-profile-settings-t-2360) |
| PROFILESCHEMA001 | profile_schema | (error/unresolved) T-2390 epic child (T-2430, smallest table): an unknown/misspelled key in the `[profile]` table, undetected by `effective_profile`/`_override_ratchet_enabled`'s own `.get()`-based reads; UNRESOLVED when no `[profile_schema] known_keys` is declared or it fails to resolve (`frob.gates._profile_schema`, see [PROFILESCHEMA001](#profileschema001-t-2390-epic-child-t-2430) below) |
| TOPSCALARSCHEMA001 | toplevel_scalar_schema | (error/unresolved) T-2390 epic child (T-2431): an unknown/misspelled TOP-LEVEL SCALAR key in frob.toml (min_frob_version, check_base -- no enclosing table at all), undetected by frob.repo_meta/frob.app.check_runner's own single-name `.get()` reads; UNRESOLVED when no `[toplevel_scalar_schema] known_keys` is declared or it fails to resolve (`frob.gates._toplevel_scalar_schema`, see [TOPSCALARSCHEMA001](#topscalarschema001-t-2390-epic-child-t-2431) below) |
| TESTINGSCHEMA001 | testing_schema | (error/unresolved) T-2390 epic child (T-2432): an unknown/misspelled key in the `[testing]` table, silently dropped by `_load_test_config`'s own pre-filter before the existing `TestPolicy` pydantic model is even constructed; UNRESOLVED when no `[testing_schema] known_keys` is declared or it fails to resolve (`frob.gates._testing_schema`, see [TESTINGSCHEMA001](#testingschema001-t-2390-epic-child-t-2432) below) |
| ARCHSCHEMA001 | arch_schema | (error/unresolved) T-2390 epic child (T-2433): an unknown/misspelled key in the `[arch]` table (e.g. "max_fuction_lines"), silently reverting to `load_arch_config`'s own calibrated default with no diagnostic; nested `[arch.layering]` sub-table excluded (a genuinely different, deliberately inert T-0620 schema, not a stray leaf value); UNRESOLVED when no `[arch_schema] known_keys` is declared or it fails to resolve (`frob.gates._arch_schema`, see [ARCHSCHEMA001](#archschema001-t-2390-epic-child-t-2433) below) |
| DOCBLOCKSSCHEMA001 | docblocks_schema | (error/unresolved) T-2390 epic child (T-2434): an unknown/misspelled key in a `[[docblocks.commands]]` entry, undetected by `_console_command_sources`'s own prog/parser/config/forwarded-only `.get()` reads; UNRESOLVED when no `[docblocks_schema] known_keys` is declared or it fails to resolve (`frob.gates._docblocks_schema`, see [DOCBLOCKSSCHEMA001](#docblocksschema001-t-2390-epic-child-t-2434) below) |
| GATESSCHEMA001 | gates_schema | (error) T-2390 epic child (T-2435): TWO shapes -- an unknown key in `[gates.ratchet]` (UNRESOLVED when no `[gates_schema] ratchet_known_keys` is declared or it fails to resolve) PLUS an unregistered rule id as a key in `[gates.severity]` (checked against the live `_KNOWN_GATE_RULES` registry directly, never UNRESOLVED) (`frob.gates._gates_schema`, see [GATESSCHEMA001](#gatesschema001-t-2390-epic-child-t-2435) below) |
| TESTRUNNERSCHEMA001 | test_runner_schema | (error/unresolved) T-2390 epic child (T-2436): an unknown/misspelled key in a `[[test.runner]]` entry, undetected by `_parse_runner_entry`'s own known-key-only reads; UNRESOLVED when no `[test_runner_schema] known_keys` is declared or it fails to resolve (`frob.gates._test_runner_schema`, see [TESTRUNNERSCHEMA001](#testrunnerschema001-t-2390-epic-child-t-2436) below) |
| DUPSCHEMA001 | dup_schema | (error/unresolved) T-2390 epic child (T-2437): an unknown/misspelled key in the `[dup]` table, undetected by `_dup_config`'s own known-key-only reads; UNRESOLVED when no `[dup_schema] known_keys` is declared or it fails to resolve (`frob.gates._dup_graph_schema`, see [DUPSCHEMA001/GRAPHSCHEMA001](#dupschema001graphschema001-t-2390-epic-child-t-2437) below) |
| GRAPHSCHEMA001 | graph_schema | (error/unresolved) T-2390 epic child (T-2437): an unknown/misspelled key in the `[graph]` table, undetected by `frob.excludes`'s own known-key-only reads; UNRESOLVED when no `[graph_schema] known_keys` is declared or it fails to resolve (`frob.gates._dup_graph_schema`, see [DUPSCHEMA001/GRAPHSCHEMA001](#dupschema001graphschema001-t-2390-epic-child-t-2437) below) |
| PII010 | pii_structural | a pydantic/dataclass/TypedDict/attrs field's name or type annotation matches a PII-shaped signature (`FIELD_SIGNATURES`), a TS `interface`/`type`/`class` field, or a Rust `struct` field (T-0352), with no `frob:waive PII010 reason="..."` -- see "PII010/SEC110" below |
| PII011 | pii_structural | a tracked `.py` file's string-literal constant is structurally email-shaped (`_is_email_shaped`, `email.utils.parseaddr`-based) with no `frob:secret-fake` marker or `frob:waive PII011 reason="..."` -- see "PII010/SEC110" below |
| PII012 | pii_structural | a plain identifier or `#`-comment word token resembles a `FIELD_SIGNATURES` keyword (suggestion severity, not deny-by-default) -- see "PII010/SEC110" below |
| SEC110 | pii_structural | an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)` call site, a TS `process.env`/`import.meta.env` access, or a Rust `std::env::var(...)`/`env::var(...)` call (T-0352), with no `frob:waive SEC110 reason="..."` -- see "PII010/SEC110" below |
| OPAQUE001 | opaque | a `docs/design/capability-evasion-taxonomy.md` "runtime-opaque" construct site (`eval`/`exec`, a non-literal `getattr`/`setattr`/`__import__`/`importlib.import_module` name, a non-literal `dlsym` symbol, a non-literal JS/TS dynamic `import()` specifier, a reflection API call, or a `libloading` dynamic symbol lookup) with no `frob:waive OPAQUE001 reason="..."` -- T-0665's fail-closed obligation, WARN-tier at first turn-on (`frob.gates._opaque.opaque_gate`) |
| REF001 | refs | a git-tracked file has zero inbound references (auto-detected or verified `frob:used-by`) from any other tracked file -- see "Anti-orphan file-reference gate" below |
| REF002 | refs | a git-tracked file has exactly one inbound reference (fragile single anchor) -- see "Anti-orphan file-reference gate" below |
| REF003 | refs | a `frob:used-by <consumer>` declaration is dangling: the named consumer is absent from the tracked-file set, or does not itself reference the declaring file back -- see "Anti-orphan file-reference gate" below |
| DOC004 | docblocks | a fenced code block in a tracked `.md` doc references the project's OWN code surface (manifest-derived python/rust/ts namespaces) and either does not resolve (error, "stale") or resolves but carries no nearby `frob:doc`/`frob:describes`/`frob:tests` anchor (warn, "unbound") -- see "Unbound/stale doc code blocks" below |
| DOC005 | docblocks | `README.md`'s command table is out of sync with the live top-level subcommand registry: a real subcommand has no table row (error, "missing"), a table row names a subcommand that no longer exists (error, "stale"), or a "N commands" prose count claim does not equal the live count (error) -- see "DOC005 README command-table drift-lock" below |
| DOC006 | docblocks | (warn, T-0688 new-gate-at-WARN precedent) a doc's PROSE (inline code span or markdown link, not a fenced code block -- DOC004's territory) contains a pointer of a RECOGNIZED, mechanically resolvable shape (file/path, cli invocation, config reference, code symbol, doc-anchor link, `path.py::symbol`/`path.rs::fn`, or a bare identifier within its doc's anchored module scope -- T-1228) <!-- frob:waive DOC006 reason="path.py::symbol/path.rs::fn here are the KIND'S OWN illustrative placeholder shape, not real pointers" --> that does not resolve, or a `frob:tests` directive's target uses pytest's `Class::method` collect-only separator where this graph wants a single `::` then a dotted `Class.method` qualname -- see "DOC006 doc-pointer resolution gate" below |
| DOC012 | docblocks | (error, promoted T-2299; shipped warn at T-0688 new-gate-at-WARN precedent) a real top-level subcommand the live `[[docblocks.commands]]` registry exposes has no dedicated `## `-level (or deeper) doc section anywhere under `docs/commands/` or `docs/modules/` naming it -- a DOC005 command-table row alone does not satisfy this, deliberately: DOC005 asks "is it listed", DOC012 asks "is it actually documented" -- see "DOC012 dedicated command-section drift-lock" below |
| EXCL001 | excludehazard | a `.git/info/exclude` entry shadows a git-tracked file or a directory containing tracked files -- see "EXCL001 (T-0465)" below |
| NARR001 | narrative_blocks | (warn, T-2993/T-2994 doctrine) a `# T-####:` narrative comment block in a tracked `.py`/`.strata` file runs longer than the 12-line threshold -- a candidate for `frob narrative move` to relocate the historical/why prose into the ticket it already names, keeping only the load-bearing part in place -- see `docs/commands/narrative.md#narr001-the-detector` |
| CPLACE001 | comment_placement | (warn, T-2987/T-2994/T-3218) a `frob:waive` directive's reason prose spans more than 2 physical lines -- `frob:ticket`/`frob:tests`/`frob:doc` stay exempt at any length, only `frob:waive` is capped -- see `docs/guides/agent-playbook.md#7b-comment-placement-t-3218` |
| CPLACE002 | comment_placement | (warn, T-2994/T-3022/T-3218) a ticket-id-citing prose paragraph in `docs/modules/**` outside a markdown table row (provenance) runs longer than 15 words -- a bare `(T-1234)` citation or short attribution stays quiet -- see `docs/guides/agent-playbook.md#7b-comment-placement-t-3218` |
| ROOT001 | root_asset_dirs | (warn) a repo-root top-level directory (not `src/`/`tests/`, not on the docs/tickets/design allowlist, not referenced by the Makefile) has zero code references: no `src/frob/**` path token, no `pyproject.toml` mention, and no `frob:external-reader` declaration -- see "ROOT001 (T-1784)" below |
| ENV001 | env_var_docs | (warn) a `FROB_*` string-literal constant assigned under `src/frob/**/*.py` is documented nowhere under `docs/` -- neither its literal env-var string nor its owning Python constant name appears in any tracked `docs/` file, and no file-scoped `frob:waive ENV001` covers it -- see "ENV001 (T-1782)" below |
| PROTO001 | protocol_summary | (warn) a `frob:requires`/`frob:transition`-tagged symbol's `frob.graph.summary.compute_protocol_summaries` result is `poisoned` (an `UNRESOLVED_CALLEE` somewhere in its transitive call closure) -- see "PROTO001 (T-0813)" below |
| PROTO002 | protocol_summary | (error) a `frob:requires` symbol's required state is never established anywhere reachable (or its summary is poisoned), and no language-excuse discharges it -- see "PROTO002/PROTO003 (T-0746)" below |
| PROTO003 | protocol_summary | (error) a `frob:transition` symbol's precondition state is never established anywhere reachable (or its summary is poisoned), and no language-excuse discharges it -- see "PROTO002/PROTO003 (T-0746)" below |
| WIRE001 | wire | (error) a ticket's own diff adds a function/method/class with no non-test caller, a gate `rule="..."` literal absent from `_KNOWN_GATE_RULES`, or a CLI `dest=` absent from `_config_external.py`'s copy lists -- code that landed, passed every gate, and does nothing; see "WIRE001/WIRE002 (T-1428)" below |
| WIRE002 | wire | (error, unwaivable) a `frob:waive WIRE001` present without a `follow_up="T-####"` attribute naming a real, still-open ticket (or, for a private test-tree helper, `permanent="true"`) -- see "WIRE001/WIRE002 (T-1428)" below |
| WIRE003 | wire | (error) a tracked hook (`.claude/hooks/*.py`) or one of the two load-bearing docs (`docs/guides/agent-playbook.md`, `docs/modules/cli.md`) names a `frob` verb, in a matcher pattern or a suggestion string, that does not resolve against the LIVE CLI dispatch table -- repo-wide, not diff-scoped; see "WIRE003 (T-1725)" below |
| CACHE001 | cache | (error) a `@memoize_per_run`-decorated function reads a file (`Path.read_text`/`.read_bytes`/`open()`) or `os.environ`/`os.getenv` whose target expression names none of the function's own parameters -- the read is invisible to `memoize_per_run`'s args-only cache key, the T-1454 incident shape; see "CACHE001 (T-1520)" below |
| ARCH102 | arch | (warn) a module's top-level exports (free functions + classes) number at least the configured minimum AND partition into at least the configured minimum count of disjoint naming/usage clusters (`frob.arch._srp.check_god_module`) -- the module bundles several unrelated concerns under one file instead of one cohesive API |
| ARCH103 | arch | (warn) a function/method mixes all three of an I/O-capability call, a string-formatting call, and enough of its own decision points to count as real compute logic (`frob.arch._srp.check_mixed_concern_function`) -- any one or two of the three alone is ordinary code, only all three together is the "one body, three unrelated concerns" smell |
| COMPLIANCE001 | sys | (error) a regulation id the selected compliance view names has no catalog entry and no explicit out-of-scope entry -- deny-by-default unaddressed regulation (`frob.strata._compliance`) |
| COMPLIANCE002 | sys | (error) a fired regulatory obligation (COPPA/GDPR/HIPAA/...) has no discharging `Claim`/structural mitigation -- see `frob.strata._compliance` for the per-regulation discharge shape (age-gate boundary, revocation edge, retention bound, lawful basis, BAA, minimization) |
| COMPLIANCE003 | sys | (error) a modeled collection flow's `field:<name>` attr names a field the site's declared privacy policy does not list -- the model collects data the published policy does not disclose (`frob.strata._compliance`) |
| DEC000 | decisions | (error) `decisions/` records are unreadable/unloadable at all (parse failure, malformed structure) -- see `frob.gates._decisions_compliance` |
| DOC011 | docanchor | (error, promoted from WARN by T-1542 once the T-1486 first-turn-on debt cleared to zero) a doc's prose mentions a ticket id (`T-####`/`T-draft-<hex>`) that does not resolve to any active or archived ticket -- a typo'd or long-since-renumbered id reads as a real, followable reference but silently resolves to nothing; see "DOC011" below |
| FUZZ002 | fuzz | (error, opt-in via `[fuzz].enforce`) a fuzz-obligated function's signature has a parameter type with no derived/declared/registered `frob.fuzz` arbitrary-value generator |
| FUZZ003 | fuzz | (error, opt-in via `[fuzz].enforce`) a fuzz-obligated function has never been fuzzed (no stamp) or its fuzz stamp is stale against the function's current body digest |
| HOST001 | sys | (error) two distinct `std.host` service-user pairs share a writable filesystem path, a listening port reachable without a declared `Flow` between their nodes, or (T-0272) an OS group -- lateral-movement-impossibility proof over `std.host` manifests (`frob.strata._host_isolation`) |
| HOST002 | sys | (error) a service user owns a setuid path, holds a sudoers grant, runs as root with paths writable by a lower-trust user, or writes a path a higher-trust node also owns -- vertical-movement-impossibility proof over `std.host` manifests (`frob.strata._host_isolation`) |
| KRB001 | sys | (error) a node declares `delegation unconstrained` -- unconstrained Kerberos delegation lets a compromise of that node impersonate any user to any service in the realm (`frob.strata._krb_movement`) |
| KRB002 | sys | (error) a node declares an `spn` (service principal name) -- every declared SPN is presumed roastable (Kerberoasting exposure); `std.krb` has no vocabulary distinguishing a gMSA/machine-account principal from a human-memorable one, so this fires until re-declared or waived with a written attestation (`frob.strata._krb_movement`) |
| KRB003 | sys | (error) a `delegation constrained` node's transitive closure of `target` SPNs (S4U2Proxy chaining) reaches a node whose trust is strictly higher than the delegating node's own -- constrained-delegation blast-radius proof (`frob.strata._krb_movement`) |
| KRB004 | sys | (error) a node in a lower-trust realm reaches a higher-trust node's realm purely via a domain-trust edge -- cross-realm-containment proof over `_krb.py::krb_trust_flows` synthesized flows (`frob.strata._krb_movement`) |
| LANG001 | lang_conformance | a language-conformance finding fired for `std.lang` (see `frob.gates._lang_conformance`) |
| LANG002 | lang_conformance | a language-conformance finding fired for `std.lang` (see `frob.gates._lang_conformance`) |
| LANG003 | lang_conformance | a language-conformance finding fired for `std.lang` (see `frob.gates._lang_conformance`) |
| LINT001 | sys | (error) a flow sourced from a `foreign`-trust node has no declared `rate` -- an external-facing flow accepting external input with no declared throughput bound at all (`frob.strata._lint`) |
| LINT002 | sys | (error) a node with a declared `capacity.service_rate` has non-infra inbound flows whose combined declared rate exceeds that service rate, with no `cache` construct declared over it (no caching relief) (`frob.strata._lint`) |
| LINT003 | sys | (error) a `Scenario` contains a `ScaleRate` rewrite on flow `F` where neither `F`'s endpoints nor `F` itself is the target of a nested `BoundClaim` (RATE/UTILIZATION) inside that same scenario -- a surge scenario with nothing to re-check (`frob.strata._lint`) |
| LINT004 | sys | (error) a node holds a `may` atom whose kind is exec/net (a risky capability) with no declared `flag=<id>` kill-switch attr (`frob.strata._lint`) |
| LINT005 | sys | (error) a node with a declared `capacity` has total inbound flow rate (every flow, no caching exclusion) exceeding `service_rate * replicas_max` -- caching-agnostic overload baseline (`frob.strata._lint`) |
| PERF002 | perf | a `.index(`/`.count(` call (python) or a linear index lookup (typescript `.indexOf`) inside a loop -- build a dict/map from key to index/count once instead (`frob.perf._rules`) |
| PERF005 | perf | recursion with unproven termination -- see `frob.perf._recursion` |
| PERF006 | perf | unbounded tail recursion -- see `frob.perf._recursion` |
| PERF007 | perf | (advisory, `[[perf.heavy]]`-configured) a call target is invoked from 2+ pipeline stages -- cross-stage redundant recomputation, the PERF meta-gap (`frob.perf._redundancy`) |
| PERF010 | perf | `yaml.safe_load`/`yaml.load` called with no C loader, in a hot path -- see `frob.perf._hotpath_smells` |
| PERF013 | perf | more than one `ast.walk(tree)` pass over the same tree in one function -- see `frob.perf._hotpath_smells` |
| PERF014 | perf | a `re.finditer` call nested inside a pattern-list loop at or beyond the configured nested-loop depth threshold -- see `frob.perf._hotpath_smells` |
| PII001 | sys | (error) a `carries` tag's category prefix is not one of the fixed PII category vocabulary -- malformed/unknown PII catalog tag (`frob.strata._pii`) |
| PII002 | sys | (error) a flow touching a PII-carrying node (either end) has no discharging boundary-crossing-protection `Claim` following the required naming convention (`frob.strata._pii`) |
| PII003 | sys | (error) a PII-carrying node has no `retention=` attr declared and no discharging erasure/retention `Claim` -- jurisdiction-agnostic retention/erasure baseline (`frob.strata._pii`) |
| PII004 | sys | (error) a flow whose src node carries PII has no declared handling attr -- undeclared-PII lint (`frob.strata._pii`) |
| PROTO004 | protocol_summary | (error) a call to a `frob:requires`-tagged callee whose precondition is not established anywhere earlier on that same caller's own call sequence (sequence-sensitive ordering violation, not branch-aware) -- see `frob.gates._protocol_summary` |
| REG002 | registry | (error) a registry entry's `handled_by:<rule>` disposition names a rule id absent from the live gate/policy rule registry -- dangling enforcement reference (`frob.gates._registry_exhaustiveness`) |
| REG003 | registry | (error) a registry entry's `deferred:<ticket>` disposition names an unresolvable ticket id, or one that is already DONE/DROPPED -- not a real deferral (`frob.gates._registry_exhaustiveness`) |
| REG004 | registry | (error) a registry entry's `duplicate_of:<target>` disposition names an id absent from the whole registry, or a documented split entry still has empty `cross_refs` -- dangling duplicate/unresolved split (`frob.gates._registry_exhaustiveness`) |
| REG005 | registry | (error) a registry file's declared total count disagrees with its actual entry-list length -- an entry was silently added or dropped without updating the declared denominator (`frob.gates._registry_exhaustiveness`) |
| REG006 | registry | (error) one or more list items under a registry file were not a mapping, or had no string `id` -- these were silently dropped pre-T-0407 instead of raising (`frob.gates._registry_exhaustiveness`) |
| REG007 | registry | (error) the same `id` string is defined by two or more entries anywhere across the loaded registry -- a real id collision, distinct from an intentional `duplicate_of:` cross-reference (`frob.gates._registry_exhaustiveness`) |
| REG009 | registry | (warn, advisory) a `frob:enforces <concept-id>` edge in code names a concept id that does not resolve to any loaded registry entry -- phantom enforcement claim (`frob.gates._registry_exhaustiveness`) |
| REL220 | sys | (error) a flow marked `retry` has no `backoff_jitter` attr declared -- missing backoff/jitter obligation (`frob.strata._retry`) |
| REL221 | sys | (error) a `retry` flow's dst is neither `idempotent` nor covered by a declared idempotency key -- non-idempotent retry with no idempotency key (`frob.strata._retry`) |
| REL222 | sys | (error) a flow declares `backoff_jitter` but has no bound code containing a real backoff-shaped token -- unproven backoff, the T-0331 provability constraint (`frob.strata._retry`) |
| REL230 | sys | (error) a node marked `external` has no `circuit_breaker` attr declared -- missing circuit breaker/bulkhead (`frob.strata._circuit_breaker`) |
| REL231 | sys | (error) a node declares `circuit_breaker` but has no bound code containing a real circuit-breaker/bulkhead-shaped token -- unproven circuit breaker (`frob.strata._circuit_breaker`) |
| REL240 | sys | (error) a node marked `critical` (a critical dependency) has no `fallback` attr declared -- missing fallback/graceful-degradation (`frob.strata._fallback`) |
| REL241 | sys | (error) a node declares `fallback` but has no bound code containing a real fallback-shaped token -- unproven fallback (`frob.strata._fallback`) |
| REL250 | sys | (error) a node is the dst of an inbound flow carrying the `critical` attr, and its own capacity is a structural singleton (`replicas_max == 1`, including undeclared capacity), and it carries no `redundant` exemption -- single point of failure (`frob.strata._spof`) |
| REL260 | sys | (error) a node marked `queue`/`consumer` has no `bounded_intake` attr declared -- missing bounded intake (`frob.strata._backpressure`) |
| REL261 | sys | (error) a node declares `bounded_intake` but has no bound code containing a real bounded-queue/backpressure-shaped token -- unproven bounded intake (`frob.strata._backpressure`) |
| REL270 | sys | (error) a flow attached to a `Boundary` has no `observability` attr declared -- missing metrics/traces/logs instrumentation on a trust/label boundary crossing (`frob.strata._observability`) |
| REL271 | sys | (error) a flow declares `observability` but neither endpoint has bound code containing a real metrics/tracing/logging-shaped token -- unproven observability (`frob.strata._observability`) |
| REL272 | sys | (error) a flow that continues a multi-hop chain (some other flow's dst equals this flow's src) has no `correlation` attr declared -- missing trace-id correlation propagation (`frob.strata._observability`) |
| REL280 | sys | (error) a long-lived service/daemon node has no `slo` attr, no `error_budget` attr, or both missing -- missing golden-signal SLO + error budget (`frob.strata._slo`) |
| REL281 | sys | (error) a node declares both `slo` and `error_budget` but has no bound code containing a real SLO/error-budget-shaped token -- unproven SLO (`frob.strata._slo`) |
| REL290 | sys | (error) a store written by 2+ distinct non-store nodes has no `owner` attr and no `reconciliation` attr declared -- missing single-source-of-truth owner/reconciliation (`frob.strata._ssot`) |
| REL291 | sys | (error) a multi-writer store declares `owner`/`reconciliation` but has no bound code containing a real single-writer/reconciliation-shaped token -- unproven owner (`frob.strata._ssot`) |
| REL300 | sys | (error) an op node writes to 2+ distinct stores (from the caller-supplied store set) with no `transaction` attr and no `saga` attr declared -- missing transactional boundary (`frob.strata._txn`) |
| REL301 | sys | (error) a multi-store-write op declares `transaction`/`saga` but has no bound code containing a real transaction/saga-shaped token -- unproven transactional boundary (`frob.strata._txn`) |
| REL310 | sys | (error) a node marked `interactive` has no `bounded_cost` attr declared -- missing bounded cost on a human-facing CLI/foreground flow (`frob.strata._interactive_cost`) |
| REL311 | sys | (error) a node declares `bounded_cost` but has no bound code containing a real cost-bounding-shaped token (dedup spawn, cache/memo, explicit timeout, stage narrowing) -- unproven bounded cost (`frob.strata._interactive_cost`) |
| REL320 | sys | (error) a node marked `event`/`queue` has no `schema_version` attr declared -- missing message schema version (`frob.strata._message_schema`) |
| REL321 | sys | (error) a node declares `schema_version` but has no bound code containing a real schema-version-shaped token -- unproven schema version (`frob.strata._message_schema`) |
| REL330 | sys | (error) a `queue` node has no `delivery=<value>` attr declared, or one declared whose value is not `exactly_once`/`at_least_once` -- missing/invalid delivery semantics (`frob.strata._delivery_semantics`) |
| REL331 | sys | (error) unproven delivery semantics -- see `frob.strata._delivery_semantics` |
| REL340 | sys | (error) some node is reachable from another only by following the configured max depth or more consecutive synchronous (non-`async`) flow hops, with no `deep_chain_ok` exemption -- sync call-chain depth exceeded (`frob.strata._sync_depth`) |
| REL350 | sys | (error) an op node writes (any outbound flow) to 2+ distinct downstream nodes, with no `saga` attr declared -- missing saga/compensation across service boundaries (`frob.strata._distributed_txn`) |
| REL351 | sys | (error) unproven saga/compensation -- see `frob.strata._distributed_txn` |
| REL360 | sys | (error) a mutable node (dst of at least one Flow) is accessed by Flows connecting it to 2+ distinct other nodes, and the shared node carries no `shared_state_ok` exemption -- shared mutable state across service boundaries (`frob.strata._shared_state`) |
| REL370 | sys | (error) a flow marked `clock_dependent` has no `ordering_strategy` attr declared -- missing clock/ordering strategy (`frob.strata._clock_ordering`) |
| REL371 | sys | (error) a `clock_dependent` flow declares `ordering_strategy` but neither endpoint has bound code containing a real ordering-strategy-shaped token (vector/logical clock, Lamport timestamp, monotonic sequence, happens-before construct) -- unproven ordering strategy (`frob.strata._clock_ordering`) |
| REL372 | sys | (error) unproven or missing clock/ordering obligation beyond REL370/REL371's pair -- see `frob.strata._clock_ordering` |
| REL380 | sys | (error) a serialization-point node's aggregate demand exceeds its one-replica service rate -- serialization-point utilization over threshold (`frob.strata._starvation`) |
| REL381 | sys | (error) a serialization point has no declared capacity to compare demand against -- undeclared demand fails closed (`frob.strata._starvation`) |
| REL382 | sys | (warn, advisory) a resource has 1+ `read` accessor and 1+ write-like accessor but no `alpha` accessor declared -- writer starvation risk (`frob.strata._starvation`) |
| REL383 | sys | (error) a node accesses a contended resource (2+ total accessors) in a write-like/alpha mode with no `timeout` attr declared on the accessing node -- unbounded wait (`frob.strata._starvation`) |
| REL390 | sys | (error) a node marked `kernel_interface` has no `interface_classified` attr declared -- missing kernel-interface classification (`frob.strata._process_bounds`) |
| REL391 | sys | (error) a node declares `interface_classified` but has no bound code containing a real classification-shaped construct (access-mode check, seccomp/capability filter, trust-boundary token) -- unproven interface classification (`frob.strata._process_bounds`) |
| REL392 | sys | (error) a node marked `deployed_process` has no `cgroup_bounds` attr declared -- missing process resource bounds (`frob.strata._process_bounds`) |
| REL393 | sys | (error) a node declares `cgroup_bounds` but has no bound code containing a real cgroup/resource-limit-shaped construct -- unproven process resource bounds (`frob.strata._process_bounds`) |
| REL394 | sys | (error) a node marked `compiled_artifact` has no `abi_compat_window` attr declared -- missing ABI/ISA compat-window declaration (`frob.strata._supply_chain_boot`) |
| REL395 | sys | (error) a node declares `abi_compat_window` but has no bound code containing a real compat-window-shaped construct (version/ABI guard, semver range assertion, symbol-versioning script) -- unproven ABI/ISA compat-window (`frob.strata._supply_chain_boot`) |
| REL396 | sys | (error) a node marked `boot_chain_stage` has no `boot_attested` attr declared -- missing boot-chain attestation (`frob.strata._supply_chain_boot`) |
| REL397 | sys | (error) a node declares `boot_attested` but has no bound code containing a real attestation-shaped construct -- unproven boot-chain attestation (`frob.strata._supply_chain_boot`) |
| RELWAIVE002 | sys | (warn) a `frob:waive`/`waive` clause on one of frob.strata's reliability-family modules (circuit breaker/SLO/SPOF/interactive-cost/fallback/txn/observability/reliability/SSOT/retry/backpressure/...) is stale -- no matching finding fired this run |
| RENDER001 | render_lint | (error) a bare stdout write (`print`, `click.echo`, `sys.stdout.write`) bypasses `frob.render` -- route human-facing output through a `Renderer` instead (INV-RENDER-SOLE-STDOUT, `frob.gates._render_lint`) |
| SEC004 | secrets | (error) a `frob:secret-fake` marker has no `reason="..."` attribute -- mirrors WAIVE001's malformed-directive contract so a fake-marked fixture is auditable (`frob.gates._secrets`) |
| SEC005 | taint | (warn) a repo-state-sourced value (env var, file read, git output) reaches an argv sink with no intervening validator hop or `--` terminator -- command-injection-shaped taint finding (`frob.vet._taint`, `frob.gates._taint_gate`) |
| SYS103 | sys | (error) a `FOREIGN` (unbound) file the binding-aware scanner observes at least one capability effect in -- coverage totality, the root-general form of SYS102 that applies to any audited repo, not just frob's own `src/frob/` tree (`frob.strata._selfconform`) |
| SYS105 | sys | (error) a node's declared `purpose=<profile>` attr's allowed-effect set does not cover an observed effect kind, or the declared profile name is unrecognized -- purpose contract violation (`frob.strata._selfconform`) |
| SYS106 | sys | (error) code laundered into an unbound (FOREIGN) file that is nonetheless reachable via resolved local python imports (transitively) from a bound node's own files -- binding totality / laundering (`frob.strata._selfconform`) |
| SYS107 | sys | (warn by default, ERROR if `[strata] require_may_scope` is set) a node whose `code=` globs bind more than the configured large-node file threshold declares at least one `may` atom with no `via` scoping -- via-less-may-on-a-large-node advisory (`frob.strata._selfconform`) |
| SYS109 | sys | (error) a symbol-form `via "path::qualname"` entry (T-1627) whose named symbol resolves to no declaration in any of the node's own bound files -- stale via symbol: renamed, moved, deleted, or mistyped. Implemented and unit-tested (`frob.strata._effects.check_stale_via_symbols`); folded into SELFAUDIT001 by `_sys_selfaudit._selfaudit_violations` (T-1761), so it runs on every `frob check`/`frob ticket land`, not just the separate `frob sys audit` CLI verb |
| SYS201 | sys | (error) two distinct nodes' `owns` (linux) or `acl` (windows) path atoms overlap by directory-segment prefix -- overlapping path claim, severity raised when either side grants write-capable rights (`frob.strata._contention`) |
| SYS202 | sys | (error) two distinct nodes bind the same `pipe` name -- shared pipe contention (`frob.strata._contention`) |
| SYS203 | sys | (error) two or more distinct non-store nodes have a `Flow` edge landing on the same store node -- shared store write, mode-blind unless the store declares a provably-safe arbiter (`frob.strata._contention`) |
| SYS204 | sys | (error) a resource declared `arbitrated_by`/`lock` still has contending accessors the arbiter does not provably serialize -- see `frob.strata._access`/`frob.strata._contention` |
| SYSWAIVE003 | sys | (warn) a SYS104/SYS105/SYS106 waiver has no `expires:YYYY-MM-DD` marker, or one older than today -- these three families' waivers are mandatorily staleness-dated; the underlying obligation re-fires and this rule names the expired waiver (`frob.strata._selfconform`, T-0671) |
| TEST009 | test | (warn) a `.strata` design file has fewer than the configured `min_design_e2e` `kind="e2e"` `frob:tests` edges -- design constructs are exercised end-to-end via strata's own conformance machinery, not unit/integration tests (`frob.gates.__init__`) |
| TEST010 | test | (error) a `frob:tests` directive's `kind=` attribute is not one of unit/integration/e2e -- `frob.graph.dsl` degrades it to a `MalformedDirective` rather than silently defaulting (`frob.gates.__init__`) |
| TEST013 | test | (warn) a `frob:tests` edge's TEST001-004 credit rests solely on the c/cpp structural fallback (name/path pattern match, no real execution evidence) -- does not withdraw credit, only surfaces the degraded-trust state (`frob.gates.__init__`) |
| TEST014 | test | (warn) two or more different files' public symbols share a leaf name, both relying only on the naming-convention test-inference fallback (no explicit `frob:tests` edge), and are credited by at least one of the same collected test node ids -- ambiguous TEST001 credit (`frob.gates.__init__`) |
| TEST015 | test | (warn) a public symbol clears TEST001 only via test node ids that contain no real assertion evidence -- vacuous credit (`frob.gates.__init__`) |
| THREAT001 | sys | (error) a CWE id the selected baseline view names has no catalog entry and no explicit out-of-scope entry -- catalog completeness (`frob.strata._threat`) |
| THREAT002 | sys | (error) a capability kind a node declares via `may` is not classified (names no sink the catalog recognizes) and no `BenignCapability` entry excuses it -- precondition/capability completeness (`frob.strata._threat`) |
| THREAT003 | sys | (error) a fired weakness obligation has no corresponding `Claim` at or above the catalog's required rung, or the claim is refuted, or (if assumed) has no owner/review date -- discharge completeness (`frob.strata._threat`) |
| THREAT004 | sys | (error) an observed net/fs/exec sink (`frob.strata._effects.extract_effects`) belongs to a node that declares no matching `may` capability -- code-level capability declaration gap, the mirror of THREAT002 (`frob.strata._threat`) |
| THREAT005 | sys | (error) an observed sink's capability kind is not recognized by the catalog and no `BenignCapability` excuses it -- code-level classification completeness, the mirror of THREAT002 (`frob.strata._threat`) |
| TICK003 | tickets | (warn/error by configured threshold) too many closed tickets sit un-archived in `tickets.md` -- run `frob ticket archive` (`frob.gates._tickets_gate`, T-0409) |
| TIERBDEMO001 | -- | deliberately never a real `frob check` rule id -- a synthetic id used only by the Tier-B fix-engine's own end-to-end demo/test fixture (`frob.gates._fix_engine_tier_b`) |
| TODO003 | coverage | (warn) a `frob:todo` edge was deferred under a version that has since shipped at least one release, and the referenced ticket is still open -- stale deferred TODO (`frob.gates._todo_fmt`) |
| VET001 | vet | (error) an enforced `[vet]` config has no `[vet.allow]` entry for an observed dependency -- allow-conformance (`frob.vet._scan_violations`) |
| VET002 | vet | (error) an observed capability is not present in the package's declaration -- capability-declaration mismatch (`frob.vet._scan_violations`) |
| VET003 | vet | (error) a version bump adds a capability versus the stored verdict -- capability escalation on upgrade (`frob.vet._scan_violations`) |
| VET004 | vet | (error) one or more obfuscation/decode-to-exec signals fired against a dependency (`frob.vet._scan_violations`) |
| VET005 | vet | (opt-in, osv-scanner) osv advisories reported against a dependency, or a skipped-note when osv-scanner is disabled/unavailable (`frob.vet._scan`) |
| VET006 | vet | (error) one or more `frob.strata.CVE_FINGERPRINTS` needles matched -- canonical vulnerable-usage class, distinct from VET005's external-scanner signal (`frob.vet._scan_violations`) |
| VET007 | vet | (error) a manifest (pyproject.toml/package.json/Cargo.toml) dependency spec is unpinned/underspecified per the configured supply-chain policy (`frob.vet._supplychain`) |
| VET008 | vet | (error) `setup.py`/`setup.cfg` `data_files` writes to an absolute path or otherwise escapes the package tree (`frob.vet._supplychain`) |
| VET009 | vet | (error) a GitHub Actions `uses: owner/action@ref` pins to a mutable ref (branch/tag) rather than a full commit SHA (`frob.vet._supplychain`) |
| VET010 | vet | (error) a tracked binary blob (.whl/.so/.node/.wasm and similar) is committed to the repo tree (`frob.vet._supplychain`) |
| VET011 | vet | (error/warn by cooldown window) a dependency was newly published within the configured quarantine cooldown window (error) or is otherwise unverified against the NVD feed (warn) -- publish-cooldown quarantine (`frob.vet._scan_violations`, `frob.vet._nvd`) |
| WAIVE006 | (always on) | (error) a `frob:waive`/`waive` site binds to a CLOSED ticket (DONE/DROPPED) -- a waiver justified by a pending ticket must not outlive it; re-justify with a new ticket or fix the underlying issue (`frob.gates._waive_comments`) |
| WAIVE007 | (always on) | (warn) a `frob:waive`/`waive` site's bound ticket ref does not resolve to any ticket (active or archived) -- dangling waiver justification (`frob.gates._waive_comments`) |
| WAIVE009 | (always on) | (error) a `frob:waive` `reason=` promises deferred/future work (a follow-up ticket, "once X clears", "will file", ...) but cites no ticket id that resolves in the queue (active, archived, or `T-draft-*`) -- an unfiled promise hiding behind the very comment that suppresses the finding it defers (`frob.gates._waive.waive009_violations`) |
| WAIVE010 | (always on) | (warn) a `frob:waive` `reason=` reads as deferred/temporary work ("until", "pending", "for now", "temporarily", or a WAIVE009-style promise phrase) rather than a permanent exemption -- `frob:debt`/`until=` are the channels that can actually be tracked/expired/drained; a `frob:waive` records the same fact only as unenforceable prose. Deliberately does NOT key on whether a cited ticket resolves (a resolved-ticket citation is also the normal shape of a legitimate PROVENANCE waiver -- "T-1024: deliberately dead because <reasoning established there>" -- so citation shape alone cannot discriminate; only wording can) (`frob.gates._waive.waive010_violations`) |

**T-0398 (evidence integrity) note on COV003**: COV003 only ever answers
"does this evidence id resolve to a currently-collected test" -- it does
NOT verify the test PASSED, and does NOT verify the evidence binds to the
ticket's own touched/scope symbols (any collected id, however unrelated,
satisfies it). Those two gaps are closed at the `frob.tickets.transition`/
`land` call sites instead, via optional injected parameters
(`add_evidence(..., passed=...)`, `transition(..., covers_scope=...)`,
`land(..., collected=..., passed=..., covers_scope=...)`) rather than a
new COV rule -- `frob.tickets` deliberately has no `frob.testing`/
`frob.graph` dependency (docs/rework.md cycle-avoidance), so it cannot
compute either answer itself; a caller with graph/testing access (today,
directly testable via `frob.gates.evidence_covers_scope`; the `frob
ticket` CLI's own wiring of real values into these parameters is a
disclosed follow-up, not yet done) supplies the answer. See
docs/modules/tickets.md's `add_evidence`/`transition`/`land` entries for
the parameter contracts.

**T-0298 (file-/directory-level COV003 evidence)**: an evidence id with no
`::` at all (a bare path, e.g. `tests/test_vet.py` or `tests/unit/deploy`)
resolves iff at least one collected node id lives under it -- as that exact
file (`<path>::...`) or inside that directory (`<path>/...`). Node-level
resolution (`path::Class::method`) is tried FIRST and stays the preferred,
most precise granularity; the path-level check is a fallback, not a
replacement. It is deliberately non-vacuous: a path with zero matching
collected node ids (nothing landed there, or a typo'd/nonexistent
directory) still fails COV003 -- "this whole file/dir passes" only counts
when something under it actually collected. This exists because a refactor
touching ~20 files naturally produces evidence at file granularity ("this
test file passes"), not one node id per file; forcing node-level-only
evidence for that shape of change is what produced a real 25-error
main-red incident (2026-07-19) when two agents both recorded file-level
ids COV003 could not, at the time, resolve at all.

<!-- frob:invariant INV-013 -->

Severity: `error` (exit 1) or `warn`; per-rule default overridable via the
`[gates.severity]` table in `frob.toml` (`COV001 = "warn"`), applied as a
single post-processing step in `run_gates` -- the legacy-adoption dial. A
rule produced by any of the gates above is waivable at a site via
`frob:waive RULE-ID reason="..."`; waivers are listed in every report, so a
waiver is visible debt, never silence.

### DEBT gate (T-0412)

Implemented in `frob.gates._debt_deprecated` (split out of
`frob.gates.__init__` in T-1115, alongside the DEPRECATED gate below --
re-exported unchanged from `frob.gates` so every external caller and
`frob:doc`/`frob:tests` binding keeps its pre-split symref).

`frob:debt <RULE> reason="..." ticket="T-####" [until="YYYY-MM-DD"|"X.Y.Z"]`
is the TEMPORARY counterpart to `frob:waive`'s PERMANENT exception (full
directive semantics: `docs/guides/extending/comment-dsl-directives.md`'s
"frob:waive vs frob:debt" section). `frob.gates.debt_gate` (rule family
`DEBT`) raises three distinct failure modes, all ERROR severity (a debt is
a structural claim about owed work, not a hygiene nit):

- **DEBT001**: a `frob:debt` missing `reason="..."` and/or `ticket="T-###
  #"` -- surfaced from `frob.graph`'s `MalformedDirective` list, mirroring
  WAIVE001's shape.
- **DEBT002**: `ticket="..."` names a ticket that is missing or not open.
  Same open-ticket check TODO002 applies to `frob:todo`, but at ERROR
  (not WARN) severity: an untracked `frob:todo` is a hygiene gap, a
  mis-tracked `frob:debt` is a lie about what is actually owed.
- **DEBT003**: `until="..."` (a `YYYY-MM-DD` date or an `X.Y.Z` semver,
  judged by `_debt_is_expired` against the run's actual date/version) has
  passed. A debt with no `until` never expires this way on its own --
  release-time blocking (below) still catches it.

`frob.gates.release_gate` (REL001) additionally refuses to bless a release
while ANY `frob:debt` is open at all, expired or not
(`_release_open_debt_violations`) -- this is T-0412's central requirement:
debt is collected and re-raised before shipping, never silently carried
forward as a de facto permanent waiver the way an un-audited
`frob:waive` can be.

`frob.gates.list_debt` (and the `frob debt [--json]` CLI,
`src/frob/app/debt_runner.py`) reports every currently-recorded entry
(rule, site, ticket, until, expired) regardless of whether it is itself
well-formed/open/unexpired -- a listing tool, not a gate; DEBT001-003 are
what actually fail the build.

### DEPRECATED gate (T-0576)

Implemented in `frob.gates._debt_deprecated` (split out of
`frob.gates.__init__` in T-1115, alongside the DEBT gate above).

`frob:deprecated <since> sunset="YYYY-MM-DD" ticket="T-####" [reason="..."]`
generalizes `frob:debt` to the API surface itself: a ticket-bound, dated
exit for a public symbol that is still callable today. Distinct from
`frob:debt` in what it is about -- a debt suppresses a GATE FINDING (the
symptom); a deprecation is about the symbol's continued EXISTENCE.
`frob.gates.deprecated_gate` (rule family `DEPR`) raises four distinct
states:

- **DEPR001**: a `frob:deprecated` missing `sunset="YYYY-MM-DD"` and/or
  `ticket="T-####"`, or with a `sunset=` that is not a `YYYY-MM-DD` date --
  surfaced from `frob.graph`'s `MalformedDirective` list, mirroring
  DEBT001's shape. ERROR.
- **DEPR002**: `ticket="..."` names a ticket that is missing or not open --
  T-0576's "ticket closes without removal" failure mode: once the owning
  ticket closes, the directive (and presumably the symbol it sunsets) must
  be gone. Same open-ticket check DEBT002 applies to `frob:debt`. ERROR.
- **DEPR003**: the bound ticket is open and `sunset` has NOT yet passed --
  the symbol is still inside its warning window. WARN, not ERROR, so a
  live-but-scheduled deprecation stays visible in ordinary `frob check`
  output rather than being silent until the date arrives (`frob:debt` has
  no equivalent "still valid, but visible" signal -- a deprecated PUBLIC
  symbol needs one).
- **DEPR004**: the bound ticket is open and `sunset` HAS passed --
  escalates from DEPR003's warning to a hard ERROR, mirroring DEBT003's
  expiry escalation.

DEPR002 suppresses DEPR003/DEPR004 for the same edge (a mistracked ticket
is the more actionable finding); DEPR003 and DEPR004 are otherwise mutually
exclusive per edge (a given deprecation is either still in its window or
past sunset, never both).

#### DEPR005: new-caller baseline ratchet (T-0639, redesigned T-1052)

T-0576's original body wanted a deprecated symbol GAINING new callers to
fire a finding, but a public symbol's callers are not resolvable by
`frob.graph.callgraph` (private-callee-only by design, T-0639's design
decision -- extending it to public callees is out of scope for this rule
too, T-1052). Rather than extend the callgraph, DEPR005 is a
baseline-ratchet over a MEASURED reference set, the same idiom `PERF009`'s
hot-graph regression ratchet (`frob.perf._ratchet`) applies to a quantile:

- `frob.gates.deprecated_current_references(symbol, root)` -- the current
  `file:line` reference set for a deprecated symbol's bare identifier.
  T-0639's original version unioned `frob.exports.exports_consumers`
  (T-0876, file-level import-statement consumers) with EVERY call-shaped
  `frob.xref.xref` identifier usage in the tree, which bare-name-matched
  any identically-named call anywhere (`subprocess.run(` counted as a
  caller of any `run`-named deprecated symbol -- ~900 junk references per
  symbol in practice). T-1052 adds the missing edge-resolution step: a
  call-shaped usage only counts when its file is ALSO one of
  `exports_consumers`' import-statement hits for that same symbol -- i.e.
  the file actually imports the deprecated name, not merely spells it.
  This is this rule's own resolution over the same "is this really an
  edge to that symbol" question `frob.graph.callgraph.build_call_graph`
  answers for private callees, without extending that module. The
  symbol's own defining file is still excluded (its declaration line and
  any purely internal same-file mention are not a "new caller").
- `frob.gates._deprecated_baseline.file_reference_counts(refs)` -- projects
  a `file:line` reference set down to `{file: count}`, dropping line
  numbers; this is the line-insensitivity boundary (T-1052).
- `frob.gates._deprecated_baseline.DeprecatedBaselineLock` -- the
  committed `frob-deprecated-baseline.lock.json` (repo-root, outside
  `.frob/`'s gitignored reach, same naming convention as
  `frob-ratchet.lock.json`/`frob-coverage.lock.json`, T-0569/T-0545): one
  entry per deprecated symbol, each a frozen set of `"file#count"`-encoded
  per-file reference counts (`DeprecatedBaselineEntry.file_counts`) --
  keyed on `(file, symbol)`, NOT `(file, line)`, so a pure line-shift
  edit inside an already-referencing file never changes the baseline
  (T-1052; the old `file:line` shape churned on every such edit, forcing
  three coordinator re-baselines in one session before T-1052 -- see the
  incident history this rewrite closed out).
- **DEPR005**: a live `frob:deprecated` symbol has a referencing file whose
  CURRENT reference count exceeds what is baselined for that file (a new
  file entirely, or more call sites inside an already-referencing file) --
  a genuinely NEW adopter of a symbol already declared on its way out, or
  growing adoption inside a file that already had some. ERROR. A symbol
  never baselined at all fires nothing (`deprecated_gate` only ever READS
  the committed file; seeding is `tighten_deprecated_baseline`'s job,
  never the gate's).
- `frob.gates._deprecated_baseline.tighten_deprecated_baseline` -- the
  write side, called separately (at land) once a fresh reference-set
  snapshot exists: a symbol never baselined before is seeded whole (its
  first-observed per-file counts are legacy, not flagged); an already-
  baselined symbol's entry SHRINKS, per file, to the MINIMUM of the
  baselined count and the currently-observed count, over files present in
  both (a caller file that disappeared drops out entirely; a file whose
  count fell keeps only the lower count) but never GROWS a file's count
  past what was baselined (a genuinely new reference -- a new file, or
  more references inside an already-baselined file -- stays un-baselined,
  and DEPR005 keeps firing on it, until a human re-baselines
  deliberately); a symbol no longer deprecated drops out of the baseline
  entirely.

DEPR005 is orthogonal to DEPR003/DEPR004 -- a symbol can be both
in-window/past-sunset AND gaining new callers at once; DEPR002 (ticket not
open) still suppresses it, same posture as DEPR003/DEPR004.

`frob.gates.release_gate` (REL001) additionally refuses to bless a release
while ANY `frob:deprecated` is past its sunset (`_release_expired_deprecated_
violations`) -- unlike `frob:debt` (where ANY open debt blocks a release,
expired or not), a deprecation still inside its warning window is fine to
ship; only an unenforced, past-sunset one is a release blocker. This is
T-0576's central requirement: a sunset date with nothing enforcing it is
not actually a sunset.

`frob.gates.list_deprecated` (and the `frob deprecated [--json]` CLI,
`src/frob/app/deprecated_runner.py`, T-0638) reports every currently-
recorded entry (symref, since, sunset, ticket, expired) regardless of
whether it is itself well-formed/open/unexpired -- a listing tool, not a
gate; DEPR001/002/004 are what actually fail the build. The CLI
additionally cross-references `tickets.md`/`tickets-archive.md` to label
each entry's status `in-window`, `past-sunset`, or `orphaned` (ticket
missing or closed) -- a tri-state view `DeprecatedEntry.expired` alone
(in-window vs past-sunset) does not carry, mirroring DEPR002's "ticket
closes without removal" failure mode as a display, not a gate, concern.

### Typestate protocol declarations (T-0744)

`frob:protocol`/`frob:transition`/`frob:requires` (T-0739 umbrella, child 1)
are the comment-DSL declaration surface for typestate protocols --
`frob.graph.dsl` parses them into `EdgeKind.PROTOCOL`/`TRANSITION`/
`REQUIRES` edges; the summary-fixpoint engine and the actual call-graph
verification (state-requirement violations, invalid-transition errors,
cleanup-obligation checks) are later T-0739 children, not built by this
ticket -- this section documents the declaration grammar and its own
parse-time enforcement only.

```
frob:protocol <NAME> states="S1,S2,..." initial="S1" [cleanup="always"|"on-error"|"process-exit-ok"]
frob:transition proto="<NAME>" from="S" to="T"
frob:requires proto="<NAME>" state="S"
```

- `frob:protocol` declares a named state machine at whatever symbol the
  directive binds to (module, class, or function) -- `states=` is a
  comma-separated list of at least one state name, `initial=` must name one
  of those states, and the optional `cleanup=` (default `"on-error"`, the
  later cleanup-obligation gate's policy dial, T-0739 child 4) must be one
  of `always`/`on-error`/`process-exit-ok`. Any of those requirements
  failing is a `MalformedDirective`.
- `frob:transition`/`frob:requires` have no bare target token, unlike every
  other verb in this DSL -- their whole grammar is `key="value"` attrs, and
  the edge's `target` becomes the parsed `proto=` attribute itself
  (`frob.graph.dsl._ATTR_ONLY_VERBS`). `frob:transition` requires `proto=`,
  `from=`, and `to=`; `frob:requires` requires `proto=` and `state=`;
  either missing an attr is a `MalformedDirective` naming which one.
- **Zero-declaration convenience**: a bare `<prefix>_init`/`<prefix>_deinit`
  function pair in the same file (also `<prefix>_open`/`<prefix>_close` and
  `<prefix>_acquire`/`<prefix>_release`, `frob.graph.dsl._INFER_PAIRS`)
  implicitly synthesizes a 3-state `uninitialized -> active -> closed`
  protocol with no `frob:protocol` comment at all -- the same PROTOCOL/
  TRANSITION edges an explicit declaration would produce, each carrying
  `inferred="true"`. Inference is ONLY for these declared name-pair
  patterns, deliberately never a general state-machine inference heuristic
  (T-0744's explicit scope limit) -- an unpaired `*_init` with no matching
  `*_deinit` in the same file infers nothing.
- **Enforceability (user mandate)**: a `frob:protocol` bound by zero
  `frob:transition`/`frob:requires` edges in the same file is itself a
  `MalformedDirective` (`frob.graph.dsl._protocol_coherence`, mirroring
  `frob:debt`/`frob:todo` coherence's `_debt_todo_coherence`) -- the
  catalogued-is-not-enforced doctrine applied to protocols: a declaration
  nothing else in the file binds to is a drift error, never a silent no-op.
  This check is per-file (matching every other DSL-layer coherence pass);
  a protocol declared in one file and bound entirely from another still
  reads as unbound here -- a graph-wide cross-file tally is a later T-0739
  child's job, not this parse-layer pass.

No new gate rule id was added for this surface: every `MalformedDirective`
these checks produce (missing/invalid attrs, an unbound protocol) already
falls through **DSL001**'s existing generic catch-all (any malformed
`frob:` directive not already claimed by a per-flavor rule -- see the
`DEBT001`/`DEPR001` entries above for the established shape this reuses),
so a malformed or unbound protocol declaration fails `frob check` today
with no `frob.gates` change required.

### PROTO001 (T-0813)

`frob.gates._protocol_summary.protocol_summary_gate` is the production
entrypoint the T-0809 reviewer's condition (a) asked for: the first real
repo-scan caller of `frob.graph.callgraph.build_call_graph(...,
mark_unresolved=True)` feeding `frob.graph.summary
.compute_protocol_summaries`, turning the T-0745 `UNRESOLVED_CALLEE`
poisoning channel into a real `frob check` finding instead of a
fixture-only test path.

Scoped narrowly: only a symbol that itself carries a `frob:requires`/
`frob:transition` directive (an explicit T-0744 protocol participant) is
ever reported -- `compute_protocol_summaries` still analyzes every
function transitively reachable from those tagged entrypoints (poisoning
propagates through untagged helpers too, per T-0745's NO-FAIL-SILENT
contract); the scoping only decides which POISONED summaries are worth
surfacing, not what the engine computes. Grouped and cached per package
(same directory, mirroring `DEAD001`'s posture) -- `build_call_graph` and
the package's `frob:` directive parse both run at most once per package
regardless of how many tagged symbols it declares.

**False-positive disposition (dunder/cross-package attribute calls,
T-0813)**: `obj._method(...)` and `super().__init__(...)` both LOOK like
this repo's own private-symbol calling convention (leading underscore)
under `build_call_graph`'s best-effort, name-based resolution, but are
never actually a call to a local helper the graph could ever bind --
`obj`'s real class, or the base class `super()` resolves to, is not
necessarily even in the scanned `paths`. `frob.graph.callgraph
._unresolved_exempt_names` filters these out of `mark_unresolved`'s
poisoning trigger: a call name whose EVERY occurrence in a function body
is an attribute call (`<expr>.name(`) on a receiver other than `self` is
exempt from ever becoming an `UNRESOLVED_CALLEE` edge. `self._foo(...)`
is deliberately NOT exempted -- that receiver token IS the enclosing
class, exactly the intra-package private-helper call this graph exists
to catch. A name that also appears as a bare call or a `self.`-call
elsewhere in the same body is not exempt either (one confident occurrence
keeps it eligible).

Python files ONLY (`.py`): `build_call_graph`'s callee-privacy check
hardcodes Python's leading-underscore `public` convention -- the same
Rust/TypeScript/C soundness gap `DEAD001` already disclosed and scoped
around, not a new gap this gate introduces. WARN-only (advisory-but-
tracked, matching `DEAD001`/REF/PERF/FUZZ's posture), waivable with
`frob:waive PROTO001 reason="..."`.

### PROTO002/PROTO003 (T-0746)

Child 3 of the T-0739 umbrella: the two ERROR-tier verification rules over
the SAME per-package `frob.gates._protocol_summary.protocol_summary_gate`
scan that computes PROTO001 -- one pass, three findings, never three
separate repo walks.

- **PROTO002 (state-requirement violation)**: a `frob:requires proto="P"
  state="S"` symbol whose summary is poisoned (an unresolved callee makes
  it untrustworthy -- ERROR here, stricter than PROTO001's WARN for the
  identical poisoning signal, per the ticket's "unknown/poisoned summaries
  at a checked call site = ERROR" mandate), or whose required state `S` is
  never ESTABLISHED anywhere reachable from the package's tagged
  entrypoints (`S` is neither the protocol's declared `initial=` state nor
  the `to=` state of any reachable `frob:transition`). The `*_init-never-
  called`/`*_deinit-orphaned` cases the ticket names fall out of this
  directly: `frob.graph.dsl`'s T-0744 name-pattern inference (`_init`/
  `_deinit`, `_open`/`_close`, `_acquire`/`_release`) synthesizes a
  requires/transition pair with no `frob:protocol` comment at all, so an
  inferred pair whose init half is unreachable IS exactly "no transition
  into the active state is reachable".
- **PROTO003 (invalid transition)**: a `frob:transition proto="P"
  from="S" to="T"` symbol whose precondition state `S` fails the same
  established-state test PROTO002 uses -- a transition reached in a state
  the protocol can never establish.

**APPROXIMATION, disclosed, not silently papered over**:
`compute_protocol_summaries` (T-0745) has no per-call-site statement
ordering yet -- real path-sensitivity needs an ordered call graph
(deferred, T-0840). PROTO002/PROTO003 therefore ask an EXISTENTIAL
question ("is `S` established by SOME reachable transition anywhere in
the closure") rather than a path-sensitive one ("is `S` established on
EVERY path reaching this exact call site") -- deliberately biased toward
FALSE NEGATIVES (a real ordering bug can be missed if some other path in
the same closure happens to establish the state) rather than false
positives (a state genuinely unreachable by any transition anywhere is
wrong on every path, so that direction is sound). The ticket-named crisp
case -- "reachable without net_init", init never called at all -- is
caught exactly.

**Language-excuse discharge**: before either rule reports an ERROR,
`frob.arch._protocol_excuse`'s per-language predicates get a chance to
discharge it -- a runtime guarantee the T-0744 DSL cannot see but that
provably reestablishes or maintains the missing state:

| Language | Mechanism | Revoked by |
|---|---|---|
| Rust | `impl Drop for T` | `mem::forget(x)`/`ManuallyDrop<T>` observed on `T` |
| C++ | a `~T()` destructor (RAII) | (never modeled as revocable here; T-0809's `escaped`/`acquired` sets are the intended "result actually held" cross-check, left unwired -- no open ticket tracks wiring it, disclosed scope cut rather than active work) |
| Python | a `with` block naming the resource | (lexical; Python's `__exit__` guarantee has no equivalent escape hatch) |
| TypeScript | a `using` declaration or `try`/`finally` naming the resource | (lexical, same as Python) |
| GC-finalized (Java/Kotlin/JS) | **never discharges** -- finalizer run timing is unspecified by every mainstream GC | n/a |

A discharge is recorded as a `Severity.WARN` finding (rule `PROTO002`/
`PROTO003`, never silently dropped -- NO-FAIL-SILENT), naming its
mechanism, so it stays visible and auditable instead of vanishing.
`build_call_graph`'s Python-only scope (the same disclosed limitation
PROTO001 carries) means only `frob.arch._protocol_excuse
.python_with_discharge` is wired into this repo-scan gate today -- the
Rust/C++/TypeScript/GC predicates are doctrine-complete and directly
unit-tested (`TestProtocolLanguageExcuseDischarge` in `tests/test_gates.py`),
but wiring them into a real cross-file scan is blocked on those languages
getting `build_call_graph` support at all (filed as T-0841, mirroring
T-0745's own T-0809 disclosure rather than building a second, unreviewed
call-graph substrate here).

**Severity**: ERROR by default for both rules (T-0746's own "enforceable,
never fail-silent" user mandate) -- this repo's own tracked source carries
zero real (non-fixture, non-test) `frob:protocol` usage today, so
ERROR-by-default measures clean against `main` at landing time. Both are
waivable (`frob:waive PROTO002 reason="..."` / `frob:waive PROTO003
reason="..."`) for a case the engine's existential approximation gets
wrong.

### PROTO005 (T-0747)

Child 4 of the T-0739 umbrella: cleanup obligations -- release-
postdominates-acquisition on all exits (including exceptional ones),
escape transfer, and per-protocol `cleanup=` policy. Shares PROTO001-004's
per-package `frob.gates._protocol_summary.protocol_summary_gate` scan for
package selection only; unlike PROTO001-004 it consumes neither
`build_call_graph` nor `compute_protocol_summaries`' fixpoint (those give
transitive UNION sets with no per-exit ordering, which this check
genuinely needs) -- it is a direct intraprocedural walk over each
acquiring function's own `NormalizedFunction` body plus the T-0809
resource-tracking DSL's own edges
(`docs/modules/graph.md#resource-tracking-dsl-t-0809`).

Two independent sub-checks, both reported as `PROTO005`:

- **Resource-level (intraprocedural postdominance)**: for a symbol
  carrying its own `frob:acquire <resource>` --
  - `frob:escapes <resource>` on the SAME symbol discharges it entirely
    (ESCAPE TRANSFER: the obligation moves to whichever caller receives
    the resource, an accounting that caller's own `frob:acquire`/
    `frob:escapes`/`frob:release` declarations carry, not this one).
  - `frob:release <resource>` on the SAME symbol also discharges it
    entirely -- the DSL attaches `ACQUIRE`/`RELEASE` at FUNCTION
    granularity, not a statement inside it, so a function claiming both
    is trusted whole (there is no finer attachment point to subdivide
    against).
  - Otherwise: every `return` in the function's own body (or, with none,
    one implicit fallthrough exit at the body's last line) must be
    preceded, at an earlier or equal source line, by a call to some
    OTHER same-file function that itself carries `frob:release` for that
    resource -- a `return` reached before any such call is the crisp
    "early-error return skips cleanup" case, reported by its exact line.
    A `cleanup="process-exit-ok"` policy (looked up from whichever
    `frob:protocol` binds to this symbol or its enclosing file, default
    `"on-error"`) additionally discharges silently a `return` preceded by
    a process-terminating call (`exit`/`_exit`/`quit`) -- any other
    policy still requires that exit's own release coverage.
  - EXCEPTIONAL EXIT (Python-only, reusing T-0686's `frob.arch._mayraise
    .compute_may_raise`): existential and false-negative-biased on
    purpose, matching PROTO002/003/004's own disclosed approximation
    posture -- fires only when the function's OWN may-raise set is
    non-empty AND zero release calls appear anywhere in its body at all;
    a genuine path-sensitive "release happens on some paths but not the
    one that actually raises" gap is deferred, not attempted, same
    posture PROTO002/003 already carry toward T-0840.
  - Language-excuse discharge (the same table PROTO002/003 use) is
    checked before either half reports an ERROR.
- **Protocol-level (`*_deinit-never-called`)**: a `frob:protocol
  cleanup="always"` protocol that has been ENTERED somewhere in the
  package's reachable closure (some non-initial state is established) but
  whose terminal state(s) -- any declared state with zero outgoing
  `frob:transition` anywhere in the package -- are never themselves
  established, meaning no reachable transition ever closes it back out.
  `cleanup="on-error"` (the DSL default) and `cleanup="process-exit-ok"`
  protocols are deliberately OUT of this half's scope: the former's
  obligation is conditional on an error path this existential,
  non-path-sensitive established-state view cannot distinguish from a
  clean one, and the latter explicitly waives ever needing a reachable
  close.

**Severity**: ERROR by default (matching PROTO002/003's own "enforceable,
never fail-silent" mandate) -- waivable with `frob:waive PROTO005
reason="..."` for a discharge this check's approximations cannot see (a
release genuinely performed by a different function on the exact path
taken, or a cross-file release the same-file-only bare-name resolution
above cannot follow).

T-0972: `protocol_summary_gate` (the shared PROTO001-005 per-package scan)
picked up a `frob:ticket T-0972` binding for a `sorted(set(symrefs))`
call whose set differs every package iteration -- reasoned
`frob:waive PERF004`, no behavior change.

### Self-audit at land (SELFAUDIT001, T-0756)

Root-cause analysis 2026-07-22 (tickets.md T-0756): frob's own self-
conformance/resource-contention/reliability audit surface
(`frob.strata.check_self_conformance` SYS100-102, `check_resource_
contention` SYS2xx, `check_reliability_timeouts`/`check_reliability_health`
REL2xx) was, until this ticket, reachable ONLY via the separate `frob sys
audit` CLI verb (`frob.app.sys_runner._run_audit`) -- never a `frob check`
gate, never something `frob ticket land`'s own preflight consulted. T-0724
enabled a check whose OWN landing reddened this exact surface undisclosed;
nothing structurally blocked that land, because a reviewer had to remember
to run `frob sys audit` by hand and happened not to.

`frob.gates.sys_gate` (the `sys` tool-stage function `frob check` already
calls unconditionally whenever a `design/`, or `[strata].design_dir`,
directory exists) now also runs `_selfaudit_violations`, folding every
finding from all four families into the ordinary `Violation` pipeline under
one rule id, **SELFAUDIT001** (ERROR, `_KNOWN_GATE_RULES`-registered so
`frob:waive SELFAUDIT001 reason="..."` matches like any other rule). Each
`Violation.message` embeds the ORIGINAL underlying rule id (SYS100/SYS101/
SYS102/SYS200-203/SYS205/REL200/REL201/REL210/REL211) and node so a reader
never has to re-run `frob sys audit` separately to see which family fired.
Suppressed whenever any `.strata` design file failed to load (matches
DOC003/SYS001-004's posture -- a partial model cannot be honestly
self-audited).

T-1061 added the SYS205 (mode-conformance, `frob.strata.
check_mode_conformance`) leg alongside the original four, closing the SAME
"only reachable via a hand-run CLI verb" gap `_access.py`'s own module
docstring disclosed for SYS205 specifically -- `check_mode_conformance`
needs a `Module` argument (the `lock`/`arbitrated_by` arbiter lookup, see
docs/strata/host.md#cli-dispatch--waiver-channel-t-1061 for the
`DesignIds.resources` plumbing this required).

T-1314 added a sixth leg: `frob.strata.evaluate_compliance` (the
`std.compliance` COPPA/GDPR/HIPAA/PRIVACY-NOTICE regulatory-obligation
audit, run once per `DEFAULT_COMPLIANCE_VIEWS` entry against the same
merged model, `out_of_scope=COMPLIANCE_OUT_OF_SCOPE`,
`known_rule_ids=_KNOWN_GATE_RULES`), reviewer-confirmed at the T-1242/
T-1244 close as the SAME "catalogued but check-invisible" gap this whole
section already closed for the other five families -- `evaluate_
compliance` had zero call sites under `src/frob/gates/` until this
ticket, reachable only via `frob sys audit`. `_compliance_selfaudit_
violations` (`frob.gates._sys`) is this leg's own function, mirroring
`_selfaudit_violations`'s suppress-on-design-load-error posture exactly.

**Tier: WARN, not ERROR** (the one leg in this family that is not
ERROR). Every other SELFAUDIT001 sub-family was ERROR from the day it
was folded in, because folding happened alongside the check being built
in the first place -- no repo had ever been able to pass `frob check`
while failing that check. Compliance is different: `evaluate_compliance`
already existed and a `design/` repo could already be failing it
silently (via `frob sys audit`) with a fully green `frob check`. Folding
straight to ERROR would flip every such repo's `frob check` from PASS to
FAIL the moment this ticket lands, with no grace period -- a latent,
previously-advisory gap turning into a hard build break with zero
warning. WARN surfaces the SAME finding in the SAME `frob check` run
(closing the green-check-red-audit divergence class this ticket's own
regression test locks down) without silently blocking a land the moment
it ships; promoting it to ERROR is a deliberate, disclosed follow-up once
a repo's own compliance posture is reviewed, not an accident of this
ticket's landing. This mirrors COMPLIANCE007's own WARN precedent
(`frob.gates._decisions_compliance`) for the identical "real gap
surfaced, not yet a proven code bug for every model" reasoning.

**Why this closes both halves of the ticket's mandate with ZERO new land
wiring**: `frob ticket land`'s existing `check_gates`/`check_gate_findings`
post-merge re-verification (`frob.tickets._land.land`, T-0754/T-0846)
already re-runs `frob check --ticket` against the just-merged tree and
refuses (`LandError.ClaimDivergence`) if the recorded gate-error count no
longer matches. Once SELFAUDIT001 is an ordinary gate `frob check` reports,
that EXISTING machinery automatically covers it -- landing a change that
reddens frob's own self-audit now fails the same way landing a change that
reddens any other ERROR-severity gate already does. No `frob.tickets`/
`frob.app` code needed to change to wire this in; the fix was making the
surface a gate at all.

### SCOPE002 (T-0998)

<!-- frob:describes src/frob/gates/__init__.py::_scope002_violations -->

Moves the AFFECT001/002 idea (docs/modules/graph.md#affects) from
diff-time to scope-DECLARATION-time: SCOPE001 catches a diff that touches
a file outside the active ticket's declared `scope` AFTER the fact;
SCOPE002 catches a scope that is already under-captured BEFORE any file
is touched, by walking the doc-edge and code-edge closure over the
declared scope itself (docs/modules/graph.md#scope-closure-t-0998).

Five directions (a doc pair, a test pair, and the private-helper
leakage), one WARN-severity rule id:

1. **code-missing-doc**: a scoped code symbol's `frob:doc`/`frob:describes`
   target file is not in scope.
2. **doc-missing-code**: a scoped doc anchor's described code file is not
   in scope (the reverse of 1).
3. **code-missing-test**: a scoped code symbol's `frob:tests` target file
   is not in scope -- the same reactive scope-add churn (AFFECT001/COV002
   discovered mid-ticket) this ticket exists to close, for tests instead
   of docs.
4. **test-missing-code**: a scoped test file's covered code file is not
   in scope (the reverse of 3, symmetric with 2).
5. **private-helper leakage**: scoped code calls an underscore-private
   helper defined in a file outside scope -- probable under-capture (the
   caller will likely need to touch that helper too); a helper used ONLY
   by scoped code is the strong "add this file" case, flagged distinctly
   from a helper with other, unscoped callers ("review the dependency").

`frob.gates._scope002_violations` computes all five via
`frob.graph.affects.scope_doc_code_gaps` (1+2),
`frob.graph.affects.scope_test_gaps` (3+4), and
`frob.graph.callgraph.scope_private_helper_gaps` (5) -- reusing the SAME
`frob:doc`/`frob:describes`/`frob:tests` edge reads `affects()` already does and the
SAME `build_call_graph` substrate `frob.dup`/`closure` already use, not a
second traversal engine. Wired into the existing `scope` gate stage
(`scope_gate`), so it runs alongside SCOPE001 for every ticket `frob
check` resolves. `frob ticket new`/`frob ticket scope` also render the
identical gaps as plain warning lines right after scope is
created/changed (`frob.app.ticket_runner._scope_closure_warnings`) --
suggest-or-warn at the CLI, before a `frob check` run is even needed.

**WARN turn-on, per the T-0756 new-gate-rule acceptance policy below**:
SCOPE002 is a nudge, not a hard block -- a ticket legitimately choosing a
narrower scope than its own doc/call graph would suggest must never be
gated shut by it. A future ticket may promote it to ERROR once the
real-repo false-positive rate is measured clean, the same promotion path
PII010/PII012 already took (see "Promotion state" in this file's tickets
history).

### New-gate-rule acceptance policy (T-0756)

The companion structural fix for the SAME root-cause class: several rejected
tickets (T-0630/T-0595/T-0616/T-0710) each shipped a gate/check rule that
was built but never actually reachable from a real invocation --
"invoked-by-nothing". A rule's own unit tests routinely pass in that state
(they call the pure function directly), so T-0755's TEST016 mutation-
evidence obligation cannot catch this class either: TEST016 only asks
whether recorded evidence is adversarial against the diff, never whether
the diff is reachable from production at all.

`frob.tickets._new_gate_rule_acceptance.new_gate_rule_ids` detects, via a
diff-aware scan of `_KNOWN_GATE_RULES`'s frozenset literal (the one
registry every gate rule id must be listed in), any rule id present in the
CURRENT working tree that was not present at `base_ref`'s tip. **T-1155**:
the literal's home file within `src/frob/gates/` is resolved DYNAMICALLY --
every direct `*.py` child of that directory is a candidate, and whichever
one actually carries the literal is used (`_locate_known_rules_in_tree`),
so a future move within the package (as happened once already, T-1139:
`gates/__init__.py` -> `gates/_waive.py`) needs no matching change here. If
the literal cannot be resolved to exactly one candidate in the CURRENT
tree, `new_gate_rule_ids` raises `GateRuleRegistryUnresolvable` rather than
degrading to a silent skip -- the T-1153 incident this closes: the
pre-T-1155 hard-coded single-file path went stale after the T-1139 move and
the preflight warned-and-skipped forever after, a detection check silently
disabling itself. An unresolvable `base_ref` (or an ambiguous match AT that
revision specifically) still degrades to `None`/skip, unchanged -- that
remains a git-side "cannot tell" condition, not a registry-structure
failure. `frob.tickets._evidence._done_transition_guard` runs this check
UNCONDITIONALLY on every `DONE` transition (both direct `frob ticket close`
and `frob ticket land`'s finalize-and-close step, which calls the same
`transition(..., DONE)` internally -- no separate land-time wiring needed,
mirroring `frob.tickets._live_tracker.live_tracker_citations`'s posture):
if any new rule id is found, the ticket must carry at least one BOUND
acceptance criterion (`frob ticket evidence ... --accepts N`) whose text
reads as a before-fails/after-passes fixture proof (contains both a FAIL
and a PASS marker, case-insensitive) -- proving the rule fires through the
PRODUCTION invocation, not merely a pure-function unit test. A ticket
missing this is refused with `TicketError.NewGateRuleUnaccepted` /
`LandError` (via the same `transition` call land's finalize step makes).

`GateRuleRegistryUnresolvable` (frob.tickets._new_gate_rule_acceptance) is
the exception this structural-corruption case raises; it is meant to be
seen -- do not catch and re-degrade it to a skip.

**v1 scope, disclosed**: the detector is scoped to `_KNOWN_GATE_RULES`
specifically (the one registry file every `Violation`-producing gate rule
must be listed in) -- a rule family added some other way is a known
residual gap, not silently assumed covered. This ticket's own SELFAUDIT001
addition folds the previously-uncovered `frob sys audit` SYS1xx/SYS2xx/
REL2xx families INTO `_KNOWN_GATE_RULES` for exactly this reason. v1 also
requires ONE qualifying criterion covering the ticket as a whole (not a
1:1 criterion-per-rule-id mapping) when a diff introduces several rule ids
in one change.

### BUG002 (T-1421): a bug ticket must prove the defect no longer reproduces

`frob.gates._mutation_evidence.bug_repro_violations` (same module as
TEST016 above, not the `test_gate` snapshot pipeline -- same PERF posture:
a real subprocess check, opted into per-caller, never run on every plain
`frob check`). Fires ERROR for `bug`/`security`-kind tickets only.

**The gap it closes, and why TEST016 does not already cover it.** TEST016
proves a ticket's bound evidence is mutation-detectable against its OWN
diff -- adversarial, not confirmatory, for the lines that changed. Five
tickets in one session (T-1384, T-1399, T-1391, T-1239, T-1401) each
passed TEST016, closed honestly, and left the defect they described live
on `main`: in every case the new/changed code WAS mutation-detectable by
its own unit tests, but nothing in production actually CALLED it (an added
guard parameter no caller passed, a computed field nothing wired up). An
absent caller has no mutant to kill or survive, so TEST016 structurally
cannot see this class of gap. BUG002 is complementary, not a TEST016
extension: it re-runs the ticket's own bound evidence against the commit
BEFORE the ticket's changes and requires a genuine failure there -- proof
the SAME test that passes at the fix would have caught the bug before it
was fixed, which is a claim about the evidence's relationship to the
CALLER path, not about the diff's own mutability.

**Mechanism.** `_designated_repro_test` picks the FIRST pytest-node-id-
shaped entry in `ticket.evidence` (deterministic, cheap -- the ticket's
cost budget is ONE test at ONE prior commit, never the bound evidence set
or the suite). `_bug_repro_outcome_at_ref` checks that test out via a
plain `git worktree add --detach <scratch> <base_ref>` (no rebuild -- the
checkout reuses the calling worktree's already-built native extensions and
installed venv; `PYTHONPATH` is pointed at the checkout's own `src/` so
the subprocess imports the PARENT COMMIT's Python source instead of the
current editable install) and runs it there via the current interpreter.
Exit 0 (the test PASSED at the parent) is the BUG002 violation: the
evidence proves nothing about whether the fix mattered. Exit 1 (a genuine
failure) is the expected, permitted case. Any other outcome -- a
collection/import error (the common shape for a parent-commit change that
also touched compiled native code the scratch checkout never rebuilt), a
kill-switch refusal (`FROB_DISABLE_EXEC=1`), or a failed `git worktree
add` -- degrades to NO VERDICT, never a false violation and never a false
pass, mirroring TEST016's own `ExecDisabled` posture one function up in
this same module.

**Cost, measured**: for a small fixture repo and test file, one
`_bug_repro_outcome_at_ref` call (worktree add + one `pytest` invocation +
worktree remove) measured well under a second (`tests/test_gates_
mutation_evidence.py::TestBugRepro`, two real end-to-end fixtures, no
mocking of the outcome). For a real designated test in this repo (an
already-built venv, no native rebuild needed), the added land-time cost is
the single test file's own collection + run time -- one test, not the
touched-file set TEST016 mutates.

**Escape hatch, required and loud (T-1421 acceptance [2]).** `tickets.md`
is excluded from `frob.graph.build_graph`'s doc/source file walk (`frob.
graph._collect_files`'s `is_ledger` exclusion, so a Done report quoting
`frob:waive`/`frob:describes` verbatim does not resurrect a phantom edge)
-- a waiver comment physically placed in `tickets.md` can therefore never
become a real `WAIVE` edge `frob.gates._waive`'s matching spine could find.
BUG002's escape hatch is instead a plain regex scan of the ticket's OWN
BODY TEXT for `frob:waive BUG002 reason="..."` (`_bug002_waiver_reason`) --
the one place a bug ticket's own justification for "this genuinely cannot
be reproduced in a test" naturally already lives (a nondeterministic
crash, an environment the suite cannot create, a ledger/doc correction
filed as `kind=bug`). A bare `frob:waive BUG002` with no parseable
`reason=` is treated as ABSENT -- the check still runs -- never a silent
pass, matching WAIVE001's existing "reason is mandatory" contract for
every other waiver in this repo. Every waive (with or without a reason) is
logged at `WARNING`, same visibility class as `--skip-mutation-evidence`.

**A malformed waiver attempt is reported, never silently dropped
(T-2870).** `_BUG002_WAIVER_RE` is a SECOND, independent directive parser
deliberately outside `frob.graph.dsl` -- `tickets.md` is excluded from
`frob.graph.build_graph`'s file walk (the same `is_ledger` exclusion noted
above), so the general-purpose `parse_directives`/`markdown_anchors`
machinery never sees a ticket body at all. That duplication is
intentional, but it means BUG002's waiver grammar must be kept in sync
with `frob.graph.dsl`'s markdown `frob:waive` grammar BY HAND -- two homes
for one rule, a shape this repo has been bitten by before -- rather than
inheriting a fix automatically. Before T-2870, a `frob:waive BUG002
reason=` shape-match that failed to parse (an unquoted value with no
opening `"` at all, or a `reason="` opened but never closed anywhere in
the rest of the body) fell through `_BUG002_WAIVER_RE`'s `finditer` as a
plain non-match, and `_bug002_waiver_reason` treated that identically to
"no waiver was ever attempted" -- BUG002 ran its normal check with no
indication a waiver had been tried and silently rejected. `_bug002_
malformed_waiver` now scans for the same looser shape with a separate,
deliberately permissive `_BUG002_WAIVER_CANDIDATE_RE` and reports (at
`WARNING`, naming the ticket id and offending text) any candidate whose
start position `_BUG002_WAIVER_RE`'s strict grammar does not also match --
distinguishing "no waiver attempted" from "a waiver was attempted and
rejected" the same way T-2857 did for the markdown-side parser.

**`frob:no-behavior-change reason="..."` INVERTS the obligation, never
skips it (T-1616).** BUG002 is unsatisfiable BY CONSTRUCTION for a pure
refactor or deletion, where the whole point is that behavior did NOT
change -- "the designated test genuinely fails at the parent" proves the
OPPOSITE of that claim. Before T-1616 the only path forward was
reclassifying the ticket's `kind` to `feature` (dodging BUG002 entirely,
invisibly) or `frob:waive BUG002` (skipping the check, no evidence for the
"unchanged" claim either). `_no_behavior_change_reason` scans `ticket.body`
for `frob:no-behavior-change reason="..."` with the same shape/precedent
as the waiver regex just above. When present, `bug_repro_violations`
swaps direction: the designated test must PASS at the parent (proving
nothing changed there either -- `_no_behavior_change_message`'s framing);
a genuine FAILED_AT_PARENT is now the violation, since it falsifies the
ticket's own "nothing behavioral changed" claim. `NO_VERDICT` still
degrades to no violation regardless of direction -- an infra/kill-switch
gap is not evidence against either claim. A bare directive with no
parseable `reason=` is treated as ABSENT, same as the waiver.

**Kind changes after evidence exists are recorded and surfaced, not
silent (T-1616).** `frob ticket kind <id> <kind>` (`set_kind`,
`src/frob/tickets/_setters.py`) appends a `kind_history` entry
(`Ticket.kind_history`, docs/modules/tickets-data-storage.md#data-models) whenever the
new kind differs from the old AND the ticket already carries bound
evidence and/or a substantive Done report -- i.e. a change that could
plausibly be relaxing an already-earned evidence obligation, exactly the
"bug relabeled to feature after the Done report already certified
behavior-preserving work" shape T-1616 diagnosed. A fresh, pre-work
reclassification (no evidence, no Done report yet) is ordinary and does
NOT append. `frob ticket land` (`_warn_kind_history_at_land`,
`src/frob/tickets/_land.py`) logs a loud `WARNING` for every entry a
landing ticket carries, naming the old kind, the new kind, and when it
happened -- so a reviewer sees the reclassification at land time instead
of having to notice it by reading frontmatter.

**Wired (T-1427).** `bug_repro_violations` is registered in
`frob.gates._KNOWN_GATE_RULES` (`src/frob/gates/_waive.py`, its actual
definition site -- `src/frob/gates/__init__.py` only imports/re-exports
it) and called from the same two call sites TEST016's own
`mutation_evidence_violations` uses: `frob.tickets._land.
_check_mutation_evidence` (the `frob ticket land` precheck) and
`frob.app.ticket_runner._close_cmd._close_mutation_evidence_for_ticket`
(the direct `frob ticket close` CLI path, T-0844's precedent). Both call
sites run TEST016 and BUG002 back to back against the SAME `(root,
ticket, base_ref)` triple and merge their violations into one
error/warn accounting and one `--skip-mutation-evidence` escape hatch --
no parallel mechanism. `tests/unit/test_ticket_close_bug002_t1427.py`
proves this end to end through the real `frob ticket close` entry point
(both directions: refused when the designated evidence passes at the
parent commit, permitted when it fails there), mirroring T-1410's own
`TestCloseRefusesT1276ShapeEndToEnd` precedent shape.

**Environment-absence defects: `frob:env-absent`/`frob:env-absent-
unverifiable` (T-3104).** BUG002's repro subprocess inherits the calling
process's environment wholesale (`_spawn_designated_test`'s `env =
dict(os.environ)`), which is exactly right for a code-shaped defect but
structurally wrong for a defect whose trigger is something MISSING from
the environment -- a bare CI runner's absent git identity, an unset
config variable. This repo's own verification sandbox always HAS the
thing whose absence is the defect, so an unmodified repro can never
observe the absent case and reports a spurious `PASSED_AT_PARENT`
(T-3075's own five tests: BUG002 and TEST016 both had to be waived for
exactly this reason). `frob:env-absent VAR1,VAR2,...` in the ticket body
(`_env_absent_vars`) names environment variables to strip from the
parent-commit subprocess before it runs (`_spawn_designated_test`);
`HOME` is special-cased to a freshly created, genuinely empty directory
(with `GIT_CONFIG_NOSYSTEM=1` alongside it) rather than deleted outright,
since deleting `HOME` would break the subprocess's own ability to run,
not just remove the identity it carries. A repro that depends on the
variable being absent now gets a real `FAILED_AT_PARENT` verdict through
the SAME classifier every other repro uses -- no new evidence format, no
new `Ticket` field, mirroring T-3156's `scope_has_python_surface`
precedent (one predicate wired into the existing checkpoint).

For the residual of this class `frob:env-absent` cannot mechanise (a
missing binary on PATH, an unsupported platform primitive -- no
environment-variable strip can simulate either), `frob:env-absent-
unverifiable reason="..."` (`_env_absent_unverifiable_reason`) reports a
distinct, ledger-visible `UNVERIFIABLE-IN-SANDBOX` outcome instead of an
ordinary `frob:waive BUG002`: T-1664's standing doctrine that UNRESOLVED
is never silently counted as either pass or fail, applied to the one
class of bug this repo's own gate is structurally unable to verify at
all. Neither directive is a synonym for `frob:waive BUG002` -- a plain
waiver carries no claim about WHY beyond its own reason text and reads,
in the ledger, exactly like every other waived check; both new
directives keep the check running far enough to distinguish "cannot
verify" from "did not bother to try".

### TEST018 (T-1733): pricing the quiet way to weaken evidence

`frob.tickets._evidence.replace_evidence` (`frob ticket evidence
--replace OLD NEW`) is the only verb that can shrink or weaken what
proves a ticket -- `add_evidence` only appends. Before T-1733 it required
nothing: no reason, no audit trail, no gate. `frob ticket scope`, by
contrast, had required `--reason` since T-0455 and recorded every change
in `ticket.scope_changes`. The asymmetry meant narrowing what a ticket
COVERS was a recorded decision and narrowing what PROVES it was silent
and free -- the tool billed the honest `--skip-mutation-evidence` escape
hatch (T-0755, logged loudly, demands a justification) and comped the
quiet one. Observed live on 2026-08-07: an agent facing ten consecutive
540s `frob ticket close` timeouts (T-1727's own root incident) unbound
its three `TestSpawnWithWatchdog` tests -- the only evidence that
actually exercised the subprocess watchdog the ticket existed to build
-- via `--replace`, and the ledger recorded nothing. It surfaced only
because the agent volunteered it in prose.

**Three parts, mirroring T-0455/T-1422's own shape exactly:**

1. `replace_evidence` now takes a REQUIRED keyword-only `reason: str`
   (`Err(EvidenceReplaceReasonMissing)` when blank) and appends an
   `EvidenceChangeEntry` (`old_node`, `new_node`, `reason`, `actor`,
   `at`) to `ticket.evidence_changes` -- never edited, only appended,
   the same append-only audit discipline `ScopeChangeEntry`/
   `AcceptanceAmendmentEntry` already established. `frob ticket evidence
   --replace OLD NEW (--reason TEXT | --reason-file PATH)` is the CLI
   surface; a pure positional-node-id append or `--evidence-cmd` stays
   completely unaffected -- the point is to price weakening, never to
   tax strengthening.
2. `frob ticket show` surfaces the churn (`_render_evidence_changes`,
   `frob.app.ticket_runner._query`) the same way it already surfaces
   `acceptance_amendments` -- a reviewer sees what was rebound and why,
   not a final evidence list that merely looks fine.
3. **TEST018** (`frob.gates._mutation_evidence.mutation_evidence_
   violations`, registered in `_KNOWN_GATE_RULES`) refuses a close
   OUTRIGHT -- always ERROR severity, regardless of ticket kind, never
   downgraded to WARN the way an ordinary TEST016 finding is for a
   non-bug/security ticket -- when `ticket.evidence_changes` is
   non-empty (evidence was rebound at least once) AND the CURRENT
   evidence set still produces a TEST016 `ConfirmatoryFinding` against
   the ticket's own diff (confirmatory-only, or T-1727's `unmeasured`).
   That combination is the mechanical fingerprint of "the tests that
   proved it were removed so it would close" -- TEST016 already computed
   the confirmatory-only verdict; TEST018 is the consumer that existed
   as a gap. A ticket whose evidence was rebound but whose SURVIVING
   evidence still kills mutants (an honest rename to an equally- or
   more-adversarial test) is unaffected. TEST018 shares TEST016's escape
   hatch: `frob ticket land --skip-mutation-evidence` still works, logged
   and justification-required exactly as before -- this is a warning
   promoted to a refusal, not a new, separate override surface.

**The generalized principle, worth restating because it outlives this
one pair:** EVERY WAY TO MAKE A TICKET EASIER TO CLOSE MUST COST AT
LEAST AS MUCH BOOKKEEPING AS THE HONEST WAY. Wherever a cheap exit is
quieter than the expensive one, the cheap exit is what gets taken, and
the ledger looks clean while the evidence rots. `--skip-mutation-
evidence` vs. silent `--replace` was one instance, not the only
plausible one -- any verb pair where one path is disclosed/costly and a
structurally equivalent path is silent/free is a candidate for the same
fix. None was found elsewhere in this audit at T-1733 land time (`scope`
and `accept --amend/--remove` already both require and record a reason;
`evidence`'s pure-append path has no shrink capability to price); the
principle is recorded here so the NEXT verb that grows a quiet escape
hatch has a named standard to be checked against, not a lesson that has
to be rediscovered from a second incident.

### Waive boundary (T-0101, revised T-0289)

`frob:waive` only ever suppresses entries in a `GateReport`'s `violations`
tuple -- `_apply_waivers` matches a waiver's target against `Violation.rule`
and can never see anything that isn't a `Violation`. `frob check`'s
`frob-arch` tool stage calls `frob.arch.analyze_project` directly and
wraps its `ArchSuggestion`s straight into `Diagnostic`s, bypassing
`frob.gates` entirely -- `god-class`, `high-coupling`, `deep-nesting`,
`abstraction-opportunity`, and `large-file` are still only reachable that
way, so a `frob:waive` naming one of those categories is flagged as
**WAIVE002** (ineffective, ERROR since T-0753 -- was WARN; a waiver that
can never match anything is not a hygiene nit, it silently does nothing
while reading as coverage, the same "looks handled, isn't" failure mode
WAIVE001 already treats as an ERROR for a missing `reason=`).

`long-function` is the ONE exception (T-0289): `frob.gates._arch.arch_gate`
now runs `analyze_project` a second time inside the `archgate` GATE (a
distinct `frob check`/`run_gates` selection name from the `frob-arch` TOOL
stage above -- do not conflate the two) and turns every `long-function`
suggestion into a real `ARCH001` `Violation`, symref-bound to the exact
function. `ARCH001` is in `frob.gates._KNOWN_GATE_RULES`, so
`frob:waive ARCH001 reason="..." [ceiling=N]` is a real, effective,
auditable waiver -- not flagged by WAIVE002 -- while
`frob:waive long-function reason="..."` (the bare category name) still is,
since that string was never a rule id `_apply_waivers` could match.

Any rule id that is simply a typo or a rule that was never registered is
also flagged as WAIVE002 the same way. `frob.gates._KNOWN_GATE_RULES`
(plus the run's loaded `[policy]` rule ids) is the whitelist; anything
outside it is presumed unwaivable. If a future change makes another arch
category waivable, remove it from `_unwaivable_channel_rules`'s returned
set the same way `long-function` was removed, and update this note.

### COV006/COV007 (T-0483)

T-0297 shipped candidate (a) of a three-part COV idea as COV005 (a
directive silently rebound onto a private helper by an extraction).
Candidates (b) and (c) landed here as COV006/COV007:

- **COV006** (warn): a `frob:tests` edge bound to a PRIVATE symbol whose
  named test has no reachability to it in `frob.graph.callgraph`
  (T-0288/T-0290's shared call-graph substrate -- reused as-is, not a
  second traversal implementation). Restricted to PRIVATE targets only:
  `build_call_graph` never records an edge to a PUBLIC callee by
  construction (the mechanism dup/perf rely on to stop expanding at the
  public-API boundary for free), so checking a public target would ALWAYS
  report "unreachable" regardless of whether the test genuinely exercises
  it -- unsound, not merely noisier, which is why COV006 skips it
  entirely rather than caveat it.

  **Known false-positive shape, disclosed rather than tuned away**: a
  test that reaches its bound private helper only INDIRECTLY, via a
  PUBLIC entry point in the same file that itself calls the helper, is
  reported unreachable -- there is no edge for that first hop at all
  (public callees are never edges), so `closure` can never walk through
  it. This is the single most common COV006 finding on this repo's own
  suite today (many `frob:tests <private-helper>` bindings whose test body
  only calls the public gate/wrapper function). It is not a traversal bug;
  `frob.graph.callgraph`'s public-boundary-stop behavior is load-bearing
  for its other two consumers and is used unmodified here. Warn severity
  reflects exactly this: a COV006 finding is a prompt to double check, not
  proof the binding is wrong -- expect a real "adoption cliff" wave of
  these on first landing in any repo with this test-via-public-wrapper
  idiom, same as any other warn-tier gate here.

  **T-0506 update**: the most common shape above is now rescued rather
  than merely disclosed. `_cov006_public_wrapper_reachable` does a
  gate-local, one-hop lookahead: if a PUBLIC symbol in the bound
  target's own file both calls that target directly and is itself
  called, by name, from the test's own body, the binding is accepted
  without ever recording a public-callee edge in the shared `CallGraph`
  (`frob.dup`/arch's public-boundary-stop guarantee stays untouched).
  Reduced this repo's own COV006 count from 98 to 89 on landing; the
  residual is a genuinely reviewable pool, tracked as a follow-up
  burndown ticket rather than the original disclosed "expect noise"
  posture.

- **COV007** (error, promoted from warn by T-2866/T-2873/T-2874 once the
  repo's live findings burned down to zero): a `frob:doc` edge whose src
  symbol is PRIVATE. Doc anchors normally cover the public API surface
  (COV001 only ever asks for one on a PUBLIC symbol), so one on a private
  helper is usually either a directive that rode along onto the wrong
  symbol after an extraction (COV005's failure mode, just discovered post
  hoc instead of diff-scoped) or documentation that belongs on the public
  caller instead. A private helper CAN legitimately warrant its own doc
  anchor (a genuinely complex internal algorithm), and this repo's own
  code has real examples of that (`frob.logging.formatter._FrobFormatter`,
  `frob.gates._pii_structural._FieldSignature`) -- unlike COV006 (whose
  best-effort call-graph makes a permanent warn the only sound posture),
  COV007's judgment call is a human one, so it is now error-tier: keeping
  the private anchor requires an explicit `frob:waive COV007` at the site
  (naming the doc's own individually-named `frob:describes` anchor, or
  the many-symbols-one-section convention this repo already accepted for
  `docs/modules/vet.md`, T-2810), not a warning a reviewer can scroll
  past.

### COV008 (T-2688)

COV003 already refuses a DONE ticket's evidence id that no longer resolves
to a collected test -- but only as a repo-wide, non-diff-scoped sweep, so
the deleting diff itself lands clean and the break is discovered later, by
an unrelated `frob check` run against a completely different ticket
(measured directly: 6 closed tickets' evidence broke silently this way,
one COV003 finding at a time, across a later sweep). COV008 is the
diff-time complement: it cross-references the SAME evidence-resolution
question, but scoped to exactly the files `git diff --name-status -M`
reports the current diff as deleting or renaming away from
(`_diff_deleted_or_renamed_paths`), against every ticket's evidence, open
or done.

This scoping is what keeps COV008 quiet on the two shapes that must never
fire: an UNCITED deletion (the overwhelming majority of ordinary test
cleanup -- no ticket's evidence names the vanished path, so nothing
matches) and a rename whose citation was already rebound via `frob ticket
evidence --replace` (the ticket's evidence now names the NEW path, which
still resolves, so the OLD path's disappearance from `_diff_deleted_or_
renamed_paths` never has anything left to match against it). Only a
still-cited evidence id that both names a path this diff is removing and
no longer resolves against the current collected set fires -- the deleter
sees the refusal in their OWN `frob check`/land, not six tickets down the
line.

### PLACE001 (T-0504)

<!-- frob:describes src/frob/gates/_waive_comments.py::_place001_missed_symbol -->
<!-- frob:describes src/frob/gates/_waive_comments.py::_place001_bindings -->

T-0470 first prototyped a class-directive placement lint as "distance
from the class's own span start" and DELIBERATELY DROPPED it before
landing: that heuristic fires on this repo's own widespread, legitimate
idiom of a per-field `frob:waive`/`frob:ticket` comment documenting one
field deep inside a large pydantic config class (`AppConfig`'s
`frob:waive SCOPE001`, 150+ lines past the class's own `class AppConfig:`
line) -- fields are not `RawSymbol`s, so a directive above one always
falls back to the enclosing class by construction, and doing so far from
the class top is completely intentional there, not mis-scoped.

PLACE001 replaces raw distance with a materially different signal: does
a nearby REAL symbol exist that the directive plausibly should have
bound to via `following` but didn't reach, with nothing but blank
lines/comments/decorators in the gap? `_place001_missed_symbol` answers
this directly -- the per-field idiom always has genuine field-assignment
CODE in that gap (that is what makes it a field, not a stray comment),
so it can never produce a "missed" candidate regardless of how close or
far the class's next real method sits; a directive separated from its
intended `def` by one blank line too many (or an extra decorator, or a
too-long stacked-comment run) always does.

**The subtle trap this check had to avoid**: a `frob:doc`/`frob:ticket`
comment placed directly above `class Foo:` resolves via `following`
straight to `Foo` -- correct and universal across this repo -- even
though `Foo` IS a class. Naively checking "did this resolve to a class
symbol" cannot tell that apart from a directive genuinely stuck at the
class-fallback (sitting somewhere inside the class body with no
reachable `following` target at all). `_place001_bindings` mirrors
`frob.graph.dsl._resolve_block_srcs`'s exact stacked-comment-propagation
algorithm but additionally tags whether each binding was reached via a
`following` match (direct, or propagated backward through an unbroken
comment run, T-0313) versus a genuine `enclosing` fallback -- PLACE001
only ever considers the latter. An earlier draft of this gate skipped
that distinction and fired ~400 findings across this repo, almost all on
the ordinary "directive directly above its class" idiom; with it in
place the finding count on this repo's own tree is zero (the corpus is
clean), proven non-vacuous instead by `TestPlace001Gate`'s constructed
positive case.

WARN severity: best-effort, name/position-based (same tier as COV006) --
a finding is a prompt to double check, not proof the directive is wrong.

### Waiver over-breadth (T-0470)

`_match_waiver`'s directory-prefix fallback (T-0276, see the comment
above `_match_waiver` in `src/frob/gates/__init__.py`) exists because
TEST003/TEST004/TEST007's `Violation.file` is a package or system id
(`crates/foo/src`, `[[system]] my-sys`), never a real leaf file -- no
real source path can ever equal that string, so without the fallback no
placement of a waiver could ever match it. That reach is now gated to an
explicit allowlist, `frob.gates._PACKAGE_SCOPED_RULES = {TEST003, TEST004,
TEST007}` -- it used to run for every symref-less violation regardless of
rule, on the assumption that no other rule's `file` is ever directory-
shaped. Any future rule that reuses a bare directory/virtual id as `file`
must be added to that set deliberately; it no longer inherits unbounded
prefix reach as a side effect of having no symref.

Even correctly gated, the prefix fallback has a real over-breadth shape:
a waiver written in one file reaches every ANCESTOR package prefix of that
file's own path too (a waiver in `src/frob/pkg/sub/deep.py` matches a <!-- frob:waive DOC006 reason="src/frob/pkg/sub/deep.py is a made-up illustrative package path for this WAIVE003 example, not a real file" -->
TEST003 finding against `src/frob/pkg/sub` AND against `src/frob/pkg` <!-- frob:waive DOC006 reason="src/frob/pkg/sub and src/frob/pkg are the same made-up illustrative example, not real directories" -->
simultaneously), which is almost always broader than the author was
reasoning about when they wrote it. **WAIVE003** flags any single waiver
that reaches more than one distinct violated package/system id this way
-- the fix is to split it into one waiver per package, or move each to
that package's own file.

A second prong was investigated for this ticket -- warning when a
class-bound directive of any verb is not near the class's own top,
on the theory that a directive with nothing recognizable following it
(`frob.graph.dsl._enclosing_src`'s fallback to the ENCLOSING symbol) and
sitting far from the class start was probably meant for a nested member.
That heuristic was prototyped and DROPPED before landing: it fires
constantly on this repo's own real, intentional idiom of a per-field
`frob:waive`/`frob:ticket` comment documenting one field deep inside a
large pydantic config class (fields are not `RawSymbol`s, so a directive
above one always falls back to the enclosing class, by design, however
far into the body it sits -- e.g. `src/frob/app/config.py`'s `AppConfig`
carries several such comments 150+ lines past its `class AppConfig:`
line, none of them mis-scoped). A real version of this check needs a
different signal than raw line-distance from the class top; tracked as a
follow-up rather than shipped as a lint proven noisy against the repo's
own pattern.

### Unnecessary-waiver detection (T-0753)

WAIVE002 only catches a waiver whose RULE ID can never match anything at
all. It cannot see the other, more dangerous stale-waiver shape: a waiver
naming a perfectly real, live rule, but whose SITE currently produces zero
findings under that rule -- the underlying issue was already fixed (or
never actually applied there), and the waiver just keeps standing guard
over nothing while silently pre-forgiving the NEXT regression at that site
with no new review ever happening. **WAIVE004** is that detector:
`frob.gates._waive004_violations` re-runs `_match_waiver` for every
recognized-rule `frob:waive` edge against this run's full, pre-waiver
violation set (the same set `_waive003_violations` already consumes) and
fires when nothing matches.

WARN tier, not error: some rules are legitimately context-dependent, so a
zero-match result does not always mean the waiver is stale --

- **`--only`/gate-selection scoping**: `frob check --only gates-fast`
  excludes `dead_symbols` entirely, so every genuinely-needed
  `frob:waive DEAD001 reason="..."` in the tree reports 0 findings under
  `gates-fast` and would falsely WAIVE004 there. This is not a detector bug
  -- it is read against the wrong (partial) violation set. Trust WAIVE004
  findings only from a full, unscoped `frob check` run; treat a scoped
  run's WAIVE004 output as advisory only, never as a signal to remove the
  waiver.
- **Diff/base-scoped rules** (e.g. `SCOPE001`, `POLICY`-family checks bound
  to a diff base) can vary run to run for reasons unrelated to the waiver's
  own site.

**Structurally-unverifiable rules (T-1064).** A third class cannot be fixed
by "run it unscoped" at all: the rule's own gate never lets the finding
reach `all_violations` in the first place, waiver or not, so WAIVE004's
zero-match check is permanently, not just occasionally, wrong for it.
`frob.gates._waive._WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES` names the
confirmed cases and is skipped entirely by `_waive004_violations`
(`_match_waiver`'s own rule-id-exact matching is untouched -- a waiver
still cannot swallow a different rule's finding):

- **`INV006` (DELETED, T-1763)** used to self-suppress: `_inv006_waived`
  checked for a covering `frob:waive INV006` edge INSIDE `_inv006_src_
  violations`, before a `Violation` was ever built, so a genuinely-live
  INV006 waiver's finding never existed for WAIVE004 to see matched or
  not. Confirmed empirically (T-0874/T-1064): deleting one of these
  waivers resurfaced the exact INV006 error it was suppressing; restoring
  it verbatim made the error disappear again, while WAIVE004 reported
  "matches 0" both before and after -- this was ~209 of ~216 WAIVE004
  findings in this repo's own full run before the T-1064 fix, effectively
  every per-file INV006 "first-turn-on pool" waiver (T-0585-style),
  permanently misreported. T-1763 deleted the rule itself (338 waivers,
  zero ever judged worth a bound `frob:invariant` across its whole
  lifetime) rather than continuing to carry this exemption for a
  detector that never earned an actionable finding; the rule id no
  longer appears in `_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES`.
- **`DUP001`/`DUP002`/`AFFECT001`/`AFFECT002`** only ever emit a finding
  for a symbol in the current diff's own touched-ref set (see each gate's
  own "diff-scoped like coverage/fmt" comment in `frob.gates.__init__`).
  A full, unscoped `frob check` run's diff is essentially never the exact
  diff that originally triggered the waived finding, so these read as
  "0 findings" on nearly every run for reasons that have nothing to do
  with the waiver being stale -- the same unreliability class as the
  `SCOPE001`/`COV002`/`TODO001` `SCOPED_RUN_FLAKY_RULE_IDS` set already
  documents, just triggered by diff content rather than `--ticket` base
  drift.
- **`WIRE001`/`SCOPE001`** (T-1577) join the set for the identical
  diff-scoped reason as `DUP001`/`DUP002`/`AFFECT001`/`AFFECT002` above:
  `WIRE001` (`frob.gates._wire`) only ever constructs a finding from a
  diff's own added hunks -- "a newly-added symbol nothing outside its own
  tests can reach" is structurally a diff-relative question, so a full
  unscoped run's diff (whatever this invocation's base/head resolve to)
  is essentially never the exact diff that introduced the waived symbol.
  `SCOPE001` was already documented above (T-0753) as diff-scoped and
  already carries the equivalent exemption for WAIVE004's OWN scoped-run
  flakiness via `SCOPED_RUN_FLAKY_RULE_IDS`; enrolling it here closes the
  matching full-run-side gap. `DEPR005`, `DEAD001`, and `REF002` were
  audited for the same shape (T-1577) and do NOT qualify -- each
  evaluates its full current state every run (a baseline-vs-current
  reference-count compare, a repo-wide call-graph reachability walk, and
  a repo-wide inbound-reference count, respectively), with no diff input
  at all, so a "0 findings" read from any of them on a full run is a
  genuine, trustworthy signal, not diff-scoping noise.

A ratchet-to-error path via the T-0569/T-0594 waivable-warning pool is a
natural follow-up once the known-flaky set above is characterized
empirically across full runs -- not built in this pass; T-0753's mandate
was WARNING tier first.

### Waiver expiry (T-0753)

`frob:waive` gains an optional `until="YYYY-MM-DD"` boundary, parsed by
`frob.graph.dsl` with the exact same date-only grammar `frob:deprecated`'s
`sunset=` already established (T-0576) -- a non-`YYYY-MM-DD` `until=`
value is rejected at parse time as a WAIVE001-shaped `MalformedDirective`,
the same posture `frob:deprecated`'s malformed `sunset=` gets under
DEPR001. Coordinate with T-0671 (strata's bounded waivers): both sides
share this one date convention rather than inventing a second grammar --
strata's `SYSWAIVE002` is the analogous error-tier precedent on that side
(`src/frob/strata/_waive.py`'s `STALE_WAIVER_RULE`).

**WAIVE005** fires when a `frob:waive`'s `until` boundary has passed,
judged against the run's current date -- mirroring DEBT003/DEPR004's plain
expiry escalation (ERROR, not merely a warning: an unenforced expiry date
is not actually an expiry). Unlike `frob:debt`, a `frob:waive` carries no
`ticket=`, so there is no ticket-lifecycle check here (no WAIVE005
counterpart to DEBT002/DEPR002) -- WAIVE005 only makes the boundary itself
loud. An expired waiver still SUPPRESSES its matched violation (the point
is forcing a human re-review, not silently un-waiving something a prior
author deliberately excepted); resolve it by extending `until` with a
written reason, or removing the directive once it's no longer warranted.

### Waiver presets (T-1176)

`frob:waive RULE preset="<name>"` is a second, equivalent way to satisfy
the mandatory reason requirement: instead of `reason="..."`, the site
names a preset, and the reason resolves from the single table below
(`frob.graph._waive_presets.WAIVE_PRESETS`, machine-read -- this table
IS the source of truth, this section is its documented mirror, and
`tests/test_gates.py::TestWaivePresets` drift-locks the two together).
A preset is NOT a blanket waiver: the site still carries an explicit
`frob:waive RULE preset="name"` directive naming the exact rule it
suppresses, at the exact site it suppresses it -- only the REASON PROSE
deduplicates, which the repo's NO DUPLICATION principle applies to
comment prose as much as to code. `preset="unknown-name"` is a malformed
directive (the same WAIVE001-shaped error an inline `reason=`-less
waiver already gets), never a silent no-op; a `preset=` waiver otherwise
matches and reports identically to an equivalent inline `reason=`
waiver (same `_match_waiver`/`_apply_waivers` spine, same `WaiverRef`
shape -- the resolved reason text lands in `attrs["reason"]` at parse
time, so nothing downstream of `frob.graph.dsl` needs to know a preset
was involved at all).

| preset name | reason text |
| --- | --- |
| `split-carried-prose` | INV006 first-turn-on pool (T-0585 lineage): this exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a docstring or comment describing already-implemented internal behavior, verifiable by reading the code it annotates) rather than a separate cross-module contract needing its own tracked invariant; disposed as a calibration batch, not claim-by-claim |
| `split-fragment` | a split submodule of its owning package's own dispatch table, imported only by that package's __init__.py by design -- the same package-split structure every sibling submodule in that package has, so a second consumer would not be genuine |

Both an explicit `reason=` and a `preset=` may appear on the same
directive; the explicit `reason=` wins (a site with something more
specific to say than the preset's generic text is never forced to drop
it). Adding a preset: add it to `WAIVE_PRESETS`, add its row here in
the same change -- the drift-lock test fails otherwise.

### `frob check`'s dup/arch stage summaries are also waiver-aware (T-0375)

The `frob-dup` and `frob-arch` TOOL stages (`frob.check._python._run_dup`/
`_run_arch`, distinct from the `gates` TOOL stage above) never route
through `frob.gates.run_gates`, so they don't get the gates stage's
`N error, M warning, K waived` split for free. T-0375 gave each its own
cross-reference against the obligation graph's WAIVE edges (`_run_dup`:
exact fragment-symref match on DUP001/DUP002; `_run_arch`: reuses
`_apply_waivers` over ARCH001 `Violation`s built from the already-computed
long-function suggestions, `ceiling=` included) so their headlines also
report only unaccounted findings, with waived ones still listed as `note`
diagnostics -- see docs/modules/dup.md#check-stage-summary-is-waiver-aware-t-0375
and docs/modules/arch.md#check-stage-summary-is-waiver-aware-for-arch001-t-0375.
This does not change gate pass/fail behavior anywhere -- it only makes the
advisory count in `frob check`'s printed summary honest.

### TICK006 (T-0726)

<!-- frob:describes src/frob/gates/_tickets_gate.py::_tick006_phantom_filing -->

Two occurrences in one session of a Done report claiming a follow-up was
filed when no ledger block actually exists: T-0707 (an invented
filed-then-absorbed trail) and T-0615 (an invented `T-draft-*` id in
prose, never actually filed) -- both caught only by reviewer diligence,
not by any gate. TICK006 makes this mechanical: it scans every ticket's
Done-report content for an *affirmative filing claim* and ERRORs when the
claimed id resolves to no block, active or archived.

**Where it looks.** Only the substring of a ticket's `body` starting at
its first "Done report" heading (`_tick006_done_report_text`) is scanned
-- any markdown heading whose text contains "done report",
case-insensitive (`## Done report`, `### Done report`, `## Round 1 Done
report`, `## Done report (batch 8)`, ...). A ticket's Description/Plan
routinely narrates OTHER tickets' ids in ordinary prose (`"T-0570 landed
the...")`, and this repo's ledger already carries several `NOTE:
T-XXXX's Done report references this as T-draft-...; the draft did not
survive land..."` disclosures inside Description bodies (the T-0577
draft-loss bug's own paper trail) -- none of that is a filing claim
about the CURRENT ticket's own work, so scanning it would be a
false-positive generator on extremely common, legitimate prose.

**The filing-claim grammar recognized.** Any occurrence of the word
"filed" (case-insensitive, word-boundary) in the Done-report text opens a
claim window extending up to 300 characters forward (long enough to span
a wrapped `Filed: ... (description...)` line/sentence without bleeding
into an unrelated later paragraph). Every ticket-id-shaped token in that
window -- `T-\d{4}` or `T-draft-[0-9a-f]{8}` -- is checked against the
union of ids in the active queue and `tickets-archive.md`. This grammar
covers every real shape observed in this repo's own ledger: `Filed:
T-0104`, `Filed: none` (extracts no id, so never fires), `filed as
**T-0137**`, `filed as a follow-up` (no id, never fires), `Filed
T-draft-4e98abb1 (mints a real T-#### id at land)`, `Filed a new standing
ticket (drafted off-main as T-draft-05d8f716...)`. A literal `T-####`
placeholder (`#` is not `\d`) or `T-draft-XXXXXXXX` template placeholder
(`X` is not `[0-9a-f]`) never match, since neither is a real reference.

**Explicit negations.** A "filed" occurrence preceded, within 40
characters, by a negation word (`not`, `never`, `no`, `n't`) is skipped
entirely -- covers the "not filed", "no ticket filed", "never filed",
"not filed as a new ticket this pass" shapes this repo's ledger already
uses routinely for genuinely-not-filed disclosures.

**A currently-real historical wrinkle.** A `T-draft-<hex>` id that WAS a
real block in the filer's own worktree ledger at write time, but did not
survive `frob ticket land` (the T-0577 draft-loss bug, tracked
separately), resolves to nothing in the ledger a reader has today --
TICK006 fires on it, by design: the rule's contract is "does this id
resolve right now", not "was this claim honest when written". Several
such entries already exist on `main` (pre-dating TICK006). These are
expected to be dispositioned with a `frob:waive TICK006 reason="..."` per
instance naming the T-0577 draft-loss incident, not suppressed
structurally -- see the Done report for this ticket for the specific
instances found and waived at introduction time.

**Where it runs.** TICK006 is one of `tickets_gate`'s checks (alongside
TICK001-TICK005), which runs inside `frob check`'s `tickets` stage --
including `frob ticket close` and `frob ticket land`'s preflight -- so a
phantom filing trail cannot reach `main` undetected going forward. It is
waivable (not in `_UNWAIVABLE_RULES`): unlike TICK001/TICK002, a genuine
draft-loss disclosure is a legitimate, honestly-dispositioned case, not a
silent invariant break.

**T-0929 (perf, no behavior change).** `_tick006_phantom_filing` no
longer loads `tickets-archive.md` itself -- `tickets_gate` now loads it
ONCE and passes the `archived` `Result` down to `_tick001_duplicate_ids`/
`_tick003_stale_archive`/`_tick006_phantom_filing` alike, closing a
same-shape redundant-parse gap the T-0928 check-performance audit found
inside a single gate (docs/audits/check-performance.md row 10). Purely
an internal signature change; TICK006's own detection contract above is
unaffected.

**T-1700 (code-span awareness, sharing DOC011's fix).** T-1542's own
Done report turned main red: it EXPLAINED that two ids
(`` `Filed: T-0104` ``, `` `waive ... ticket "T-9999";" `` ) are
inline-code-span examples DOC011 correctly ignores, and the bare
`\bfiled\b` scan above -- with no code-span awareness at all -- fired
TICK006 on the explanation of the exemption the neighbouring gate
correctly applies. Root cause: TICK006 is a lexical rule (does a
`T-\d{4}`-shaped token follow the word "filed" within a window) with no
notion that a code-spanned "filed" is being MENTIONED, not asserted.

The fix reuses DOC011's own code-span stripping rather than copying it: a
"filed" occurrence whose OWN match position falls inside a fenced or
inline code span (`frob.gates._markdown_scan.strip_code_spans`, extracted
from `_doclink_docanchor.py` into its own module so both rules import ONE
implementation instead of risking a second copy drifting out of sync) is
skipped, the same way an explicit negation is. Deliberately NARROW: only
the "filed" TRIGGER word's own position is checked, not every id in the
window -- an id that is itself backtick-styled while "filed" stays plain
prose (`Filed: ` + `` `T-draft-deadbeef` ``, a real and common Done-report
convention already covered by this repo's own test suite) is still a
genuine, checkable claim and must still fire. Blanking the whole window
instead of just gating on the trigger word's position would have silently
dropped that legitimate case too.

**Considered and declined: a fully semantic filing-claim parser.** T-1700
weighed going further than code-span awareness -- distinguishing "a
filing verb genuinely asserting X was filed" from any other prose shape
near an id -- and declined: the existing "filed" + windowed-id grammar
already IS the cheap, reliable version of that idea (a real filing verb,
a bounded window, an explicit-negation carve-out), and the ONLY gap the
T-1542 incident actually exposed was code-span blindness, now closed.
Any further generalization (e.g. distinguishing "will be filed" from "was
filed", or a claim spanning an intervening unrelated sentence) trades a
concrete, testable fix for guesswork with no incident motivating it yet
-- exactly the shipped-heuristic-that-fails-differently trap this ticket
was asked not to walk into.

### TICK007 (T-0820)

<!-- frob:describes src/frob/gates/_tickets_gate.py::_tick007_undispatched_stale -->

T-0752 built the pure staleness-alarm computation
(`frob.tickets.undispatched_stale`/`dispatch_stale_hours`/
`_dispatch_stale_thresholds`) and wired it into `frob ticket doable`'s
human-facing row rendering (a loud UNDISPATCHED marker) -- but that only
surfaces the alarm to someone who happens to run `doable` and read it.
T-0820 is the `frob check` half of the same signal: `tickets_gate` calls
`undispatched_stale` (imported and reused verbatim, per T-0752's own
Done-report note that the staleness judgment must live in exactly one
place -- this gate does not re-derive it) over the doable set filtered to
non-in-flight (`has_live_lease`) rows, and emits one WARN `Violation` per
alarmed ticket.

**Thresholds.** Same `[tickets]` `frob.toml` table T-0752 defined
(`dispatch_stale_critical_hours`/`dispatch_stale_high_hours`), defaulting
to 4h (CRITICAL) / 24h (HIGH). MEDIUM/LOW never alarm, matching T-0752's
mandate that "a queue always has some" at those priorities.

**Where it runs.** TICK007 is one of `tickets_gate`'s checks (alongside
TICK001-TICK006), which runs inside `frob check`'s `tickets` stage --
including `frob ticket close` and `frob ticket land`'s preflight. It is
waivable (not in `_UNWAIVABLE_RULES`): unlike TICK001/TICK002, a stale
dispatch is a queue-health signal to act on, not a structural invariant
break, so a reasoned `frob:waive TICK007 reason="..."` can disposition a
known, accepted case (e.g. a deliberately deferred CRITICAL awaiting a
blocker that has not been formally recorded yet).

### TICK008 (T-0842)

<!-- frob:describes src/frob/gates/_tickets_gate.py::_tick008_unknown_ledger_fields -->

T-0838 made `Ticket` `extra="allow"` (not `extra="forbid"`) so a ledger
written by a NEWER `frob` binary -- one that has added a field this
binary's `Ticket` does not know about yet -- loads instead of hard-failing
`MalformedFrontmatter`; unknown keys land in `__pydantic_extra__`, are
logged at WARNING (`_warn_unknown_extras`), and round-trip verbatim on the
next dump. That reviewer-caught disclosed cost: a TYPOED known field
(`priorty: low`) is indistinguishable from a genuinely-newer field at load
time -- it silently becomes an extra, the intended value is lost to the
schema default, and the only signal was that same WARNING log line, which
no gate read. TICK008 makes that drift visible mechanically: for every
ticket in the checked ledger with a non-empty `__pydantic_extra__`,
`tickets_gate` emits one WARN `Violation` per unknown field, naming the
ticket id and the field, plus a `difflib.get_close_matches` fuzzy hint
against `Ticket.model_fields` when a likely intended field name exists
(`unknown field 'priorty' -- did you mean 'priority'?`).

**Why WARN, not ERROR.** An initial ERROR pass was the original design
and was REJECTED in adversarial review of T-0842 itself -- worth stating
explicitly so a future "promote to ERROR" attempt re-derives the same
constraint rather than re-discovering it the hard way. `frob ticket
land`'s claim re-verification (`_reverify_done_report_claims_post_merge`)
spawns `frob check --ticket <id>` via `sys.executable` from the ROOT
checkout's venv -- the ROOT binary's OLD `src` tree (the playbook's
"Gate-affecting source only takes effect via `uv run frob`" stale-binary
hazard, one level up: it applies to `frob ticket land`'s own subprocess,
not just to a human running a stale global `frob`). While a schema-
extending ticket is ITSELF being landed, the root binary's `Ticket` model
does not yet know the new field that very ticket is landing -- a
populated new field on that ticket's own block gets captured as
`__pydantic_extra__` by root's stale model. `tickets_gate` correctly does
NOT scope TICK008 to only the active ticket (a stale field anywhere in
the ledger is real drift worth surfacing) -- so an ERROR here fires over
the FULL merged ledger at exactly the moment the schema-owning ticket
lands, `real_errors` diverges from the worktree-captured claim, and land
refuses via `ClaimDivergence`. A `frob:waive TICK008` cannot route around
this either: the same stale root binary evaluating the gate is the one
evaluating the waiver, so the schema gap that causes the false ERROR
equally prevents the waiver from being recognized as covering it. The
original ERROR-severity docstring's claim that "there is no case where
this rule stays red once the schema catches up" is false during exactly
that land window -- "the schema catching up" IS the land event being
refused. WARN avoids this because `frob check`'s pass/fail gating (and
land's real-errors/claim-divergence comparison) keys off ERROR-severity
counts, not warnings -- a WARN still renders as a live, mechanical `frob
check` finding (the actual T-0838 review demand: visibility, not a hard
gate), matching the TICK004/TICK006/TICK007 precedent of leaving a
schema-transition/judgment-window case as WARN rather than ERROR.

**Where it runs.** TICK008 is one of `tickets_gate`'s checks (alongside
TICK001-TICK007), which runs inside `frob check`'s `tickets` stage --
including `frob ticket close` and `frob ticket land`'s preflight. It is
waivable (not in `_UNWAIVABLE_RULES`), matching the TICK004/TICK006/
TICK007 precedent: a genuinely temporary, disclosed exception (e.g. a
worktree deliberately carrying a not-yet-landed schema-extending field
across a short review window) can be dispositioned with a reasoned
`frob:waive TICK008 reason="..."` instead of blocking on it.

### TEST011/TEST017 (T-0464/T-1489)

<!-- frob:describes src/frob/gates/__init__.py::_test011_freshness -->
<!-- frob:describes src/frob/gates/__init__.py::_test017_deflation -->

T-0464 originally folded two independent freshness signals for
`coverage.xml` into one WARN-only rule, TEST011: `stale_by_mtime`
(coverage.xml is older than the newest known source file) and
`module_join_fraction` (coverage.xml's `<class>` entries joined to far
fewer known modules than the snapshot actually has -- the fingerprint of
a run that only measured the main pytest process and never merged
subprocess coverage).

T-1205 acceptance[1]'s second half asked for this to become a genuinely
blocking freshness contract instead of an advisory a reader can ignore
(the exact failure mode of the 2026-07-31 incident: an agent trusted a
23-hour-stale stamp and closed a ticket having fixed 1 of 64 real
findings). T-1489 investigated the rollout risk of simply flipping
TEST011 to ERROR and found the two signals it combines have very
different steady-state behavior:

- `stale_by_mtime` is TRUE for most of any active working tree's life --
  any source edit made after the last `make coverage` run makes
  coverage.xml stale by definition, which is the ordinary, constant state
  of normal dev flow, not a sign anything is wrong. Escalating this to
  ERROR would gate the entire repo on routine editing.
- `module_join_fraction` has no such noise floor -- a healthy `make
  coverage` run joins close to 100% of known modules every single time.
  A fraction below `_TEST011_JOIN_FLOOR` (0.5) is a specific, rare
  corruption signature (T-0464's original incident: subprocess coverage
  silently dropped), not something that fires under ordinary conditions.

T-1489's decision: split the deflation signal out of TEST011 into its own
rule, **TEST017**, and promote only TEST017 to ERROR severity. TEST011
keeps `stale_by_mtime` at WARN, unchanged -- flipping it would trade one
failure mode (a stale finding read as current fact) for a worse one (a
gate that fails on every checkout with an uncommitted edit). TEST017 is
registered in `_UNWAIVABLE`-adjacent form like every other TEST0xx rule
(waivable via `frob:waive TEST017 reason="..."`, same as TEST011) --
promotion to ERROR is a default-severity change, not an unwaivable one.

### TEST019 (T-1824/T-1877): per-symbol deflation, distinct from TEST017's aggregate signal

<!-- frob:describes src/frob/gates/_coverage.py::_suspect_deflated_symbols -->
<!-- frob:describes src/frob/gates/__init__.py::_test019_deflated_symbols -->

TEST017's `module_join_fraction` catches a coverage.xml that dropped MOST
of its data (a whole subprocess never merged), but a single xdist worker
crash can drop just the handful of symbols that worker happened to be the
SOLE source of data for, without moving the repo-wide join fraction enough
for TEST017 to notice at all. T-1824 added `_suspect_deflated_symbols`
(`frob.gates._coverage`) to catch that narrower shape directly: a symbol
whose `def` line shows a coverage hit but every OTHER line in its body
span shows zero hits is exactly what a partial merge loss looks like
per-symbol.

That heuristic is corroborated, not standalone: a symbol only qualifies if
`snapshot.edges` also carries a `frob:tests` edge for it (checked on both
`edge.src`/`edge.target`). An honestly unexercised or genuinely dead code
path is indistinguishable from lost worker data by the per-line shape
alone -- without the corroborating edge raising the expectation that this
symbol SHOULD show real hits, flagging it would be a false positive, and
TEST005/TEST011/TEST017 already gate real work on adjacent signals. A
symbol with fewer than two hit-lines recorded in its span is skipped, not
flagged either way -- same "cannot analyse, so do not claim a verdict"
posture as `_module_join_fraction`'s own sample-size floor.

T-1824's own declared scope (`src/frob/gates/_coverage.py`,
`tests/test_gates.py`) could compute the list but could not reach
`frob.gates.__init__` (where every Violation-emitting gate function lives)
or `frob.gates._waive`'s `_KNOWN_GATE_RULES` registry, so it landed as a
WARNING log line only inside `load_coverage`. T-1877 closes that gap:
`CoverageData.suspect_deflated_symbols` (`frob.gates._models`) now carries
the computed symref tuple out of `load_coverage`, and
`_test019_deflated_symbols` (`frob.gates`) turns a non-empty tuple into a
`TEST019` Violation, folded into `_test005`'s dispatch alongside
TEST008/TEST011/TEST017/TEST012. WARN, not ERROR -- like TEST011's
`stale_by_mtime`, a per-symbol shape match is corroborating evidence for a
possible worker-crash merge loss, not proof; waivable via `frob:waive
TEST019 reason="..."`, same as every other TEST0xx rule.

### Coverage as managed derived state (T-1205/T-1516/T-1517)

<!-- frob:describes src/frob/testing/_coverage_cache.py::fill_from_cache -->
<!-- frob:describes src/frob/testing/_coverage_refresh.py::native_coverage_refresh -->

**T-1676**: `native_coverage_refresh` no longer requires an all-passing
suite to produce an artifact. A non-zero pytest exit keeps the coverage
data, stamps it, and records `degraded` in `.frob/coverage-run.json`;
only a refused spawn (`PytestRefused`) aborts. The suite verdict and the
coverage artifact are independent results. See
[testing.md](testing.md#a-red-suite-does-not-discard-the-run-t-1676) for
the full contract and the two guards that keep a degraded artifact safe
to stamp.

T-1205's own acceptance criteria ask for coverage to stop being a
hand-refreshed artifact TEST005/006/011/017 merely read and complain
about. Two tickets close most of that gap:

- **T-1517** (`src/frob/testing/_coverage_cache.py`): a per-file
  content-hash keyed cache at `.frob/coverage-file-cache.json`, wired
  into `frob.gates._coverage.stamp_coverage`. Before TEST011/TEST017's
  deflation/provenance/canary checks run, `fill_from_cache` backfills
  `CoverageData.module_line` for every file the CURRENT `coverage.xml`
  did not itself measure (a touched-set `--cov-append` run only
  re-executes the touched selection) but whose live content hash still
  matches what was last cached -- so an incremental stamp's join fraction
  reflects every unchanged file's real, previously measured percentage
  instead of reading as deflated just because this run's own
  `coverage.xml` is narrower. `update_file_cache` persists every
  measured file's `(content_hash, line_pct)` after a successful stamp so
  the next run, incremental or full, can backfill from it in turn.
- **T-1516** (`src/frob/testing/_coverage_refresh.py`): a frob-native,
  pure-Python replacement for the COMMON path of `make coverage`/`make
  coverage-fast`'s shell recipe -- `native_coverage_refresh` decides
  cold-start-full vs. touched-set-incremental vs. nothing-to-do (reusing
  T-0484's `python_coverage_targets`), spawns `pytest`/`coverage` via
  `subprocess` directly (no `Makefile`/shell dependency, works
  identically on Linux/macOS/Windows), and always finishes with
  `stamp_coverage`. `frob.testing._coverage_wait.run_coverage_wait`'s
  `command` parameter now defaults to `None`, which routes through
  `native_coverage_refresh` in-process instead of spawning `make
  coverage-fast` -- every existing caller of `run_coverage_wait()` with
  no arguments (e.g. `frob.app.test_runner`) is auto-wired onto the
  native path with no call-site change; an explicit `command=(...)`
  still spawns exactly that command (tests, or a caller that genuinely
  wants the Makefile recipe's own resilience -- see below).

**What T-1516 deliberately does NOT re-derive**: the Makefile recipe's
xdist-crash serial-rerun recovery (`docs/guides/testing.md`,
`tests/unit/test_makefile_coverage.py`'s `TestCombineRecoversDisjointSessions`)
and its configurable rerun-deadline knobs
(`COVERAGE_RERUN_DEADLINE`/`COVERAGE_XDIST_DEADLINE`) are real,
already-hardened resilience against a specific parallel-run flake class;
porting that faithfully to Python is a dedicated follow-up, not folded
into this ticket's diff. `native_coverage_refresh` surfaces a pytest/
coverage subprocess failure as a plain `Err` instead. `make coverage`/
`make coverage-fast` themselves are UNCHANGED and still the right choice
for a run that needs that resilience; they were not rewritten to call
into `native_coverage_refresh` in this same change (T-1205 acceptance[3]'s
"make coverage becomes a thin optional wrapper" is left as residue, not
claimed done here -- see T-1205's own Done report).

T-1205 acceptance[0] and [4]'s "no manual refresh verb, runs
automatically inside a gated command" is intentionally NOT wired into
`frob check` itself: every dispatched worktree agent runs with
`FROB_AGENT=1` set (`docs/guides/agent-playbook.md` section 3b), which
depends on `frob check`/`frob check --ticket` staying bounded under a
foreground timeout -- auto-spawning a coverage refresh (full-suite or
even touched-set) from inside every `frob check` call would reintroduce
exactly the auto-background stall class that section exists to prevent.
`run_coverage_wait`'s own auto-wiring above is the safe form of this: a
caller that explicitly wants to block until fresh (opting into the wait)
gets the native path for free, but a plain `frob check` never
unconditionally triggers a coverage run on a dispatched agent's behalf.

### TICK009/TICK010 (T-0714)

<!-- frob:describes src/frob/gates/_tickets_gate.py::_tick009_scope_breadth_nudges -->
<!-- frob:describes src/frob/gates/_tickets_gate.py::_tick010_stale_lease_report -->

Before T-0714, `frob ticket doable` printed two kinds of diagnostic
directly into the queue listing on EVERY invocation: a `WARNING:` line
per over-broad-scope nudge (`frob.tickets.large_glob_warnings`, one per
matching scope entry across every queued/planned/in-progress ticket) and
implicit stale-lease chatter riding the same output. A session with 65
outstanding over-broad-scope nudges saw all 65 repeated on every single
`doable` call -- a wall of noise on top of the actual queue listing
`doable`'s job is to render cleanly.

TICK009/TICK010 relocate the DETAIL half of that diagnostic into `frob
check`'s `tickets` stage, where it is reported once per check run instead
of once per queue query:

- **TICK009** wraps `frob.tickets.large_glob_warnings` (T-0453, unchanged)
  as one WARN `Violation` per nudge, for every ticket in `IN_PROGRESS`/
  `PLANNED` state -- exactly the same detail `doable` used to print, just
  relocated. T-1645: a `QUEUED` ticket is excluded entirely -- its
  declared scope is a prediction made before anyone has opened the code,
  not a touched set that can honestly be narrowed yet; demanding
  file-level precision at that point either produces a narrow guess the
  implementer scope-adds past anyway (the declaration was noise) or an
  honest broad scope that carries a permanent, un-actionable warning (48
  tickets / ~204 findings on this repo's own ledger before the fix, 40 of
  them filed in one incident-response session where the honest scope
  really was a package glob). `frob ticket start` (`_warn_scope_breadth_
  on_start`) surfaces this exact nudge directly the moment a ticket
  enters `PLANNED` -- more actionable than a warning nobody reads
  per-ticket in a full-repo check.
- **TICK010** scans `.git/frob-leases/*.json` directly (a plain
  `Path.exists()` check against each lease's recorded `worktree` field,
  not the internal TOCTOU-hardened liveness probe
  `frob.tickets._leases._probe_worktree_liveness` uses for its own
  opportunistic-unlink decision) and emits one WARN per lease whose
  worktree is gone, naming the lease file's path and the remedy (delete
  it, or let the next `doable`/`start` call's own opportunistic prune
  handle it).

`frob ticket doable` itself now shows only a single summary line
(`frob.app.ticket_runner._render_scope_breadth_summary`, e.g. "65
scope-breadth nudge(s) outstanding across the queue -- see 'frob check
--only tickets' (TICK009) for detail") when the count is nonzero, and
nothing at all when it is zero -- log-level discipline per the T-0202/
T-0235 precedent this ticket's acceptance criteria named: per-item detail
belongs to a gate's DEBUG/finding-list channel, not doable's stdout.

**Ordering constraint.** `tickets_gate` computes TICK010's report BEFORE
any call that touches `frob.tickets.read_all_leases` (TICK007, via
`doable`/`has_live_lease`) -- that call opportunistically UNLINKS a
lease file the moment it confirms the worktree is gone, so a TICK010 scan
run after it would find the very files it should be reporting already
removed.

**Where they run.** Both are `tickets_gate` checks (`frob check`'s
`tickets` stage), waivable in principle (not in `_UNWAIVABLE_RULES`) -- but
TICK009's own violations are anchored at `tickets.md:0` (they describe a
whole ticket's declared scope, not one source line), so there is no
concrete line to attach an inline `frob:waive TICK009 reason="..."`
comment to in practice -- a TICK010 lease-cleanup finding, by contrast,
still names a real `.git/frob-leases/*.json` path a waiver comment could
target if one were ever added there.

**Acknowledged-broad exemption (WAVE14-B, T-1484).** A
genuinely-broad epic/umbrella ticket (its scope legitimately spans a whole
campaign, not one file list) previously had no honest way to silence
TICK009 -- it re-fired the same nudge on every ledger-wide `frob check`
forever. `frob ticket scope-ack <id> (--reason TEXT | --reason-file PATH)`
sets `Ticket.scope_breadth_ack=True` (with the mandatory justification
recorded in `scope_breadth_ack_reason`), and `_tick009_scope_breadth_nudges`
skips any ticket carrying that flag entirely, independent of `tier`. This
is the same "acknowledge the specific case, with a reason, once" shape
`frob:waive` gives every other gate -- just implemented as a ledger field
instead of a source-line comment, since TICK009's finding has no source
line to anchor to.

### TICK011 (T-1129, active-window-narrowed T-1402)

<!-- frob:describes src/frob/gates/_tickets_gate.py::_tick011_disclosed_cuts_without_ticket -->

Five incidents in one wave (T-1085, T-0321's close, T-1140, T-1150 --
each disclosed deferred/cut work in a Done report's own prose with no
ticket filed for it) made a coordinator hand-screening every Done report
for this shape a standing, non-scaling tax; TICK006 already catches a
phantom FILING claim mechanically, but nothing caught the mirror-image
gap: a report that admits "there's more to do" and simply never files it.

TICK011 scans the SAME Done-report substring TICK006 does
(`_tick006_done_report_text`, everything from the first "Done report"
heading onward -- a ticket's Description/Plan narrating OTHER tickets'
ids is not in scope) for a conservative, deliberately narrow set of
disclosure phrases (`_TICK011_DISCLOSURE_PATTERNS`): "left for/as a
follow-up", "not yet ticketed"/"not ticketed", "deferred to/as/for a
follow-up", bare "residue"/"residual", and a "scope cut"/"cut from/for
this/the pass/scope/ticket" shape. Multi-word phrases on purpose (not a
bare "deferred"/"cut" trigger) -- a WARN-tier first turn-on that drowned
in false positives would train reviewers to ignore it, defeating the
point. Calibrating against this repo's OWN live ledger (T-1129's own
"frob's own ledger findings fixed or dispositioned in the same land"
obligation) found bare "residue"/"residual" is this codebase's own term
of art for "remaining FINDING count" ("7 residual", "WARN residue",
"REG010 residue", "gate:WAIVE residue" -- all real T-1111 Done-report
text), never disclosed leftover scope; `_tick011_preceded_by_technical_
token` excludes exactly that shape (the word immediately before
"residue"/"residual" is a bare number, an ALL-CAPS/rule-id-shaped word,
or contains a `namespace:NAME` colon) rather than a narrower fixed-digit
lookback, which is what actually cleared the false positive found (a
digit-only lookback still fired on "WARN residue"/"gate:WAIVE residue").

A disclosure occurrence is only a finding if NEITHER an explicit
no-ticket-needed reason (`_TICK011_NO_TICKET_NEEDED_RE`: "no ticket
needed", "no follow-up ticket needed", "no-ticket-needed") NOR a
`T-####`/`T-draft-<hex>` id resolving to a real block in `tickets.md` or
`tickets-archive.md` appears within `_TICK011_VICINITY` (300 characters)
of it -- mirroring TICK006's own `_TICK006_CLAIM_WINDOW` precedent for
"same bullet/paragraph, not an unrelated later one". One finding per
ticket (the first uncited occurrence), not one per phrase hit, for the
same noise-conservatism reason the phrase list itself is narrow.

**Where it runs.** TICK011 is one of `tickets_gate`'s checks (`frob
check`'s `tickets` stage), WARN severity, waivable (not in
`_UNWAIVABLE_RULES`) -- a genuine "this really doesn't need its own
ticket" case dispositions with a reasoned `frob:waive TICK011
reason="..."`. First-turn-on measurement against this repo's own live
ledger: 0 findings (the T-1111 false positives above were the only hits
before the technical-token exclusion; the real T-1085/T-0321-class
incidents this rule targets had already been hand-filed by the
coordinator by the time this rule landed).

**Active window (T-1402).** A later, unscoped measurement (2026-08-01)
found 50 unwaived TICK011 findings, every one against a HISTORICAL Done
report -- 14 of them citing tickets below T-0500 -- for scope cuts nobody
can now reconstruct enough context to honestly follow up on. Those 50
could only ever be driven to zero by waiving them en masse, exactly the
dishonest zero this repo's own north star (release drive T-1402: "if
frob passes, the code is good") rejects. TICK011 stays at FULL STRENGTH
-- unchanged from every paragraph above -- for any Done report whose
owning ticket is inside `_TICK011_ACTIVE_WINDOW` (the `_TICK011_
ACTIVE_WINDOW` ids below the ledger's own current highest real `T-####`
id, self-adjusting rather than a fixed historical date/id line); a report
outside that window is skipped by default, not deleted as a capability --
set `FROB_TICK011_INCLUDE_HISTORY` (any non-empty value) to scan the full
ledger anyway for a deliberate history audit. This is a narrowing of
AIM, not of coverage: any report written from now on is always inside
the window the moment it lands.

### TICK013 (T-2557)

Found by walking into the live ledger state, not by reading code: T-2377
sat `state: in-progress` with `scope: []` for roughly an hour, holding a
worktree lease, and not one existing gate fired on it.

Two candidate detectors each miss for a different structural reason.
SCOPE001 (`frob.gates.scope_gate`) is diff-driven -- it iterates the
touched files in a worktree's diff, so a ticket whose worktree is clean
(everything already landed, or work not yet started) never runs that
loop body, and the riskiest ticket state in the ledger reads as clean.
TICK009 already runs the ledger-wide IN_PROGRESS/PLANNED scan this needs
but only ever asks whether a declared scope is too BROAD
(`large_glob_warnings`); the symmetric, strictly more dangerous case -- a
scope that is EMPTY -- was not asked about at all.

TICK013 (`frob.gates._tickets_gate._tick013_empty_scope_without_
declaration`) closes that gap: one ERROR per IN_PROGRESS/PLANNED ticket
whose `scope` is empty and whose `no_scope_declared` field is not set.
ERROR, not WARN, because scope is simultaneously the evidence-coverage
declaration and the write lease (T-2394's own framing) -- an undeclared
empty scope means the ticket can edit anything while the fleet believes
those files are free, and no other check has anything to test against
it.

**What it exempts.** A ticket with `no_scope_declared=True` -- the T-2394
opt-out, set via `frob ticket scope <id> --declare-no-scope --reason
TEXT` and requiring a non-blank `no_scope_declared_reason`
(`set_no_scope_declared`) -- is silent regardless of how empty its scope
is: the declaration IS the disclosure, for a legitimately scope-free
tier=epic rollup or pure decision record. Also silent for any ticket
with a non-empty scope, any QUEUED ticket (mirroring TICK009's own
T-1645 reasoning: a queued ticket's scope is a pre-work prediction, not
yet a live lease, so demanding a declaration that early produces the
same noise TICK009 was narrowed to avoid), and any terminal-state
ticket (done/dropped/failed hold no lease at all). This exemption
deliberately matches `frob.app.ticket_runner._lifecycle._refuse_empty_
scope_on_start`'s own `ticket.scope or ticket.no_scope_declared` check
exactly, so `start`-time refusal and this ledger-scan gate never
disagree about what counts as a legitimate empty scope. `frob ticket
start` already refuses this exact state at write time, which is why the
state looks impossible and was previously unmonitored -- but `frob
ticket scope --remove` can empty a scope AFTER a clean start, and that
is how T-2377 reached it.

### COMPLIANCE005 (T-0788)

<!-- frob:describes src/frob/gates/_decisions_compliance.py::compliance_gate -->

T-0607 built the pure check
(`frob.strata._compliance._check_cmpl_registry_unit_dispositions`, the
`CMPL_REGISTRY_UNIT_IDS` constant, and `check_cmpl_registry`) but did not
wire it into `frob check` -- `_KNOWN_GATE_RULES` and a stage callback both
lived outside T-0607's declared scope, so a `deferred`/undispositioned
regression among the 17 checkable-control compliance-registry units
(`docs/design/registry/compliance.yaml`) would not have failed `frob
check` at all, only a direct call to the strata function. T-0788 is the
`frob check` half: `compliance_gate` loads `compliance.yaml` from
`docs/design/registry` (or a caller-supplied `registry_dir`), calls
`check_cmpl_registry`, and emits one ERROR `Violation` per
`CMPL_REGISTRY_UNIT_IDS` member whose disposition kind is neither
`handled_by` nor `out_of_scope` -- most concretely, a `deferred:<ticket>`
disposition that becomes factually wrong the instant the named ticket
closes (the exact T-0388/T-0607 self-reference incident this rule exists
to refuse a repeat of). T-0833 flipped all 17 `compliance.yaml` entries
under `CMPL_REGISTRY_UNIT_IDS` from `out_of_scope` to
`handled_by:COMPLIANCE005`, matching T-0788's original intent.

**Where it runs.** `compliance_gate` is dispatched as the `compliance`
stage callback (`frob check`'s `gates-fast` stage group). It is silent
(returns no violations) when `registry_dir` has no `compliance.yaml` at
all AND that path was never committed on this branch's history -- a repo
with no compliance registry makes no COMPLIANCE005 claim, matching
`registry_gate`'s own missing-directory posture. It is waivable (not in
`_UNWAIVABLE_RULES`): a reasoned `frob:waive COMPLIANCE005 reason="..."`
can disposition a specific, honest, temporary exception the same way
REG001-004 allow one.

**COMPLIANCE006 (T-0894): adopted-then-deleted registry.** A repo that DID
commit `compliance.yaml` at some point and then lost it -- deleted, by
accident or by a compliance-load-bearing-artifact removal attack --
fires `COMPLIANCE006` instead of silently degrading to the never-adopted
empty-tuple posture above. `path_ever_tracked` (`frob.gates.
_registry_exhaustiveness`, shared with `registry_gate`'s own `REG012` and
`decisions_gate`'s `DEC003` -- see `docs/design/registry/EXHAUSTIVENESS-
GATE.md#reg012-adopted-then-deleted-registry-t-0894`) is the signal: `git
log -1 -- <path>` against `HEAD` tells whether the path was ever committed
regardless of its current working-tree state. `COMPLIANCE006` is in
`_UNWAIVABLE_RULES` -- deleting the registry entirely is a higher-stakes
claim than any individual entry's disposition, unlike COMPLIANCE005 above.

### DERIVED001 (T-0603): derived-state integrity precheck

`frob doctor`'s `verify_derived_state` (T-0570) fingerprints every entry in
`DERIVED_ARTIFACTS` (`.frob/cache.db`, `.frob/dup.db`, `.frob/vet.db`,
`.frob/coverage-stamp`, `.frob/baseline`, `frob-coverage.lock.json`) and
reports each as absent (fine, nothing written yet -- not corruption),
healthy, or present-but-corrupt (fails a format-specific validity check:
SQLite magic header, or `json.loads`). Before T-0603, this diagnosis
existed but nothing in `frob check` ever consulted it -- a truncated
`.frob/cache.db` would silently feed the graph/dup gates wrong data
instead of failing loudly, and `frob doctor` was a diagnosis nobody was
required to run.

`frob.check._derived_state_integrity_result` (`src/frob/check/__init__.py`)
closes that gap: every `run_check`/`run_check_cpp`/`run_check_rust`/
`run_check_ts` entry point calls it once, synchronously, BEFORE
dispatching any concurrent stage. If any derived artifact is
present-but-corrupt, the entire check run short-circuits to a single
`derived-state-integrity` `ToolResult` (diagnostic code `DERIVED001`,
ERROR severity) naming every corrupt artifact and the `rm -f` command to
clear it, pointing at `frob doctor` for the full diagnosis -- no gate ever
sees the corrupt cache. An absent artifact (fresh clone, `frob clean`, a
worktree that has never run `frob check`) is NOT a violation: `run_gates`
and the cache layer already know how to build a missing artifact from
scratch, so only a PRESENT-but-invalid artifact fails closed.

This is deliberately NOT one of `_KNOWN_GATE_RULES` / the `registry_gate`
rule catalog above -- it is a check-orchestration-level precondition (the
same tier as a tool being unavailable), not a `Violation` a `frob:waive`
can target, so it stays unwaivable by construction: a corrupt cache is
never a legitimate, intentional state to accept.

**Why the check runs once, up front, rather than from inside the `gates`
stage itself.** `arch`, `dup`, and `gates` all read or rebuild the same
`.frob/cache.db`/`dup.db` inside `frob check`'s `ThreadPoolExecutor`
batch. Fingerprinting from inside one of those stages while the others
run concurrently races a live writer: a cache mid-rebuild, observed by
another thread, reads as "corrupt" (truncated/incomplete bytes) when it
is merely momentarily in-progress. This was caught for real during T-0603
development by `TestCheckBuildsGraphOnce.test_run_check_calls_build_graph_
exactly_once` turning red once the precheck lived inside `_run_gates`;
moving it to run once, serially, before any stage is dispatched removes
the race entirely and is also strictly cheaper (one fingerprint pass per
`frob check` run instead of one per gate family).

## AFFECT001 AFFECT002 (T-0628)

<!-- frob:describes src/frob/gates/__init__.py::affect_drift_gate -->

T-0325 landed `frob.graph.affects.affects` (docs/modules/graph.md#affects)
-- the warm, test-free query answering "if X's digest changed, exactly
WHICH documentation and WHICH other code must be reviewed/updated" -- but
explicitly cut its enforcement half as future work. `affect_drift_gate`
(gate name `affect_drift`, `gates-fast` stage group) is that enforcement:
for every symbol the working diff touches (`_touched_symrefs`, the same
helper `coverage_gate`/`policy_gate` use), it walks that symbol's
`affects()` closure and fails when

- a dependent doc anchor (`frob:doc`/`frob:describes`) names a file NOT
  also touched anywhere in the same diff (AFFECT001), or
- a dependent symbol (reached via a `uses-contract` chain) lives in a file
  NOT also touched anywhere in the same diff (AFFECT002).

Both are ERROR, unwaivable by default like the rest of the drift family
(waivable via the ordinary `frob:waive AFFECT001/AFFECT002 reason="..."`
channel if a change genuinely does not need its dependent updated). A
symbol whose `affects()` closure is empty (no `uses-contract` dependents,
no doc/test edges at all) is silent -- there is nothing that could have
drifted. A closure `affects()` itself reports `truncated=True` for
(`max_depth`/`max_nodes` cut the walk short) is still checked against
whatever it DID visit: the gate under-reports on a truncated closure
rather than false-positiving on nodes it never saw.

"Touched" is file-granular, not line/hunk-granular -- a dependent doc or
symbol only needs SOME hunk anywhere in its file to clear the gate, not a
hunk overlapping its own span. This mirrors `coverage_gate`'s COV002 scope
grace posture (a file-level touch accounts for its whole contents) rather
than requiring a caller to prove the exact line changed; the query-side
`frob graph affects <ref>` CLI (docs/modules/graph.md#affects) is the tool
for a developer to see precisely what the gate is asking about.

## DOCENUM001 (T-1227)

<a id="docenum001-t-1227"></a>
<!-- frob:describes src/frob/gates/_docenum.py::docenum001_gate -->

`frob:enumerates` (`frob.graph.dsl`, code-side bare-target verb; markdown
side `frob:enumerates <symref> members="..."` inside an HTML comment,
`frob.graph.dsl._ENUMERATES_RE`) binds a doc span to a named collection
literal and makes the doc author's claimed member list EXPLICIT content
rather than free prose. DOCENUM001 (gate name `docenum001`, rides
alongside DOC004/DOC005/DOC006 under the `docblocks` stage group)
AST-diffs that claimed `members="..."` list against the literal's real
members every run -- content-verified, ack-immune: unlike DRIFT001's
digest-based staleness check, a doc's claimed text can be byte-identical
to its last ack and still be wrong if the underlying collection changed
and the ack was never re-run.

Supported shapes: a module- or class-level `dict`/`set`/`tuple`/
`frozenset` literal assignment, a `typing.Literal[...]` annotation, or an
`ErrorSet`/`StrEnum`/`Enum` subclass. An unresolvable shape (e.g. an
argparse `choices=[...]` list, or a computed value) is a disclosed WARN,
never a silent pass.

Every DOCENUM001 finding is `frob:waive DOCENUM001 reason="..."`-able via
the normal source-level waiver path (the markdown anchor's own `origin`
line carries the edge, same as every other doc-facing gate).

**Per-member documentation presence (T-2664, WARN).** The AST-diff above
only verifies that the CLAIMED member LIST matches the code collection's
real members -- it never checked that a correctly-claimed member id has
any actual documentation anywhere in the file. That gap was directly
observed: T-2613 synced this file's own `frob:enumerates members="..."`
list (the rule catalog above) to match `_KNOWN_GATE_RULES` exactly, and
DOCENUM001 read clean throughout even though several of the ids it added
(MILE001, MILE002, WAIVE009 before T-2639) had zero documentation rows --
a bare id in the member list was sufficient to pass. Same failure shape
as a rule declared in `_KNOWN_GATE_RULES` but never wired into
`run_gates`: correct by its own enumeration check while delivering none
of the protection the enumeration exists for.

DOCENUM001 now also checks, per claimed member id, whether it resolves to
a documentation row/section anywhere in the SAME doc file -- either of
this file's own two documentation shapes: a leading table cell
(`| RULEID | ... |`, including combined cells like `DUP001/DUP002`) or a
`#`/`##`/`###` heading naming the id (including combined headings like
`## AFFECT001 AFFECT002 (T-0628)`). A claimed member matching neither
shape fires a **WARN**, not an ERROR: measured at introduction against
this file's own 336-member catalog, 80 pre-existing ids had zero
documentation (a filed backlog ticket tracks clearing it). Landing this check
at ERROR severity would have reddened `frob check` on main the moment it
shipped, for pre-existing gaps unrelated to whoever's diff happened to
touch this file next -- WARN surfaces the gap without blocking. The
existing member-list-mismatch check above is unaffected and remains
ERROR-severity; the two checks are independent and can both fire on the
same edge.

## Ack accountability (T-1317)

<a id="ack-accountability-t-1317"></a>

`frob ack` is the one place the obligation graph accepts a HUMAN
ASSERTION -- "yes, this doc is still accurate against the changed code"
-- in place of a mechanical check: it clears DRIFT001 (the digest-based
staleness comparison, see the gate table above) by recording the CURRENT
digest as the acked one, with nothing that used to distinguish a genuine
re-verification from a rubber stamp. T-1317 closes that gap, following
the same append-only audit-record precedent `frob ticket scope --reason`
(T-0455, `ScopeChangeEntry`), `frob ticket accept --amend/--remove`
(T-1422, `AcceptanceAmendmentEntry`), and `frob ticket evidence
--replace` (T-1733, `EvidenceChangeEntry`) already established: every way
to discharge an obligation cheaply must cost at least as much bookkeeping
as the honest way.

**`--reason` is required.** `frob.graph.lock.acknowledge` takes a
keyword-only, mandatory `reason` parameter; the CLI (`frob ack --reason
TEXT | --reason-file PATH`) refuses with `LockError.AckReasonMissing`
when blank. A reason that is too short or matches a small literal
boilerplate list ("ok", "lgtm", "still accurate", "n/a", ...) is refused
with `LockError.AckReasonBoilerplate` instead -- rubber-stamping is a
gate failure, mirroring WAIVE002's reason discipline, not a formality to
route around with the shortest string that satisfies a non-empty check.

**Every ack records the digest delta it vouches for.** Each `(ref,
facet)` an ack touches appends one `AckAuditEntry` (`frob.graph._models`)
to `frob.lock`'s new `ack_log` -- an append-only list, never edited or
rewritten -- capturing `old_digest` (the value recorded before this call,
or `None` for a genuine first-ever ack of that pair -- never a stand-in
for "the delta could not be computed"; `acknowledge` always has the prior
entries dict in hand before it overwrites anything), `new_digest`,
`reason`, `actor` (best-effort OS login), and `at` (the ack date). This is
what makes an ack auditable evidence rather than an unaccountable
assertion: `frob ack --list` renders the full trail. `--reason-file`'s
verbatim read (the `frob ticket scope --reason-file` precedent, T-0737 --
routes multi-sentence prose around shell command substitution) is shared
via `frob.app.ticket_runner._mutate.read_reason_file_verbatim` rather than
a second capability-declaration site: that module already declares the
`cli` node's `fs.read` capability, so `frob ack`'s `--reason-file` reuses
it instead of `frob.app.ack_runner` declaring its own.

**Ack never clears a content-verified finding.** DOCENUM001 and
NEGEXIST001 AST-diff the doc's claim against the real code every run and
are ack-immune by construction (see "DOCENUM001 (T-1227)" above) -- they
never consult `frob.lock` at all, so no ack, however well-reasoned, can
clear a finding a checker can already prove true or false. `frob ack`'s
authority is scoped to exactly the one claim class that is NOT
mechanically checkable: whether prose that describes behavior still
matches that behavior, which is what DRIFT001's digest comparison stands
in for.

## NEGEXIST001 (T-1229)

<a id="negexist001-gate-t-1229"></a>
<!-- frob:describes src/frob/gates/_negexist.py::negexist001_gate -->

`frob:until T-####` (`frob.graph.dsl`, markdown-side directive inside an
HTML comment: `<!-- frob:until T-#### -->`, `frob.graph.dsl._UNTIL_RE`,
docs/modules/graph.md#comment-dsl) binds a negative-existence prose claim
(the "X is missing today" phrasings `_NEGEXIST_PHRASE_RE` matches: "does
not [yet] exist", "not-yet built/implemented/wired/supported/available/
shipped/landed") to the ticket that will build the missing thing.
`markdown_anchors` also heuristically detects the claim itself
(`frob.graph.dsl._NEGEXIST_PHRASE_RE`) and emits both as edges sharing the
doc's `<doc>#<anchor>` src.

NEGEXIST001 (gate name `negexist001`, rides alongside DOC004/DOC005/
DOC006/DOCENUM001 under the `docblocks` stage group) fires WARN in two
cases: an anchor section carries a negative-existence claim with no
`frob:until` at all (unbound -- nothing will ever catch it once the thing
ships), or its bound ticket(s) are all missing/closed/archived (stale --
the claim should have been revisited when the ticket shipped). A claim
heuristic match is best-effort, matching only a fixed phrase list -- a
false negative here just means an unrelated claim goes unflagged, never a
false failure.

## EXHAUST001 EXHAUST002 (T-0688)

<a id="exhaust001exhaust002-t-0688"></a>
<!-- frob:describes src/frob/gates/_exhaustive_handling.py::exhaustive_handling_gate -->

Child 3 of T-0685's exception may-raise umbrella, over T-0686's
per-function may-raise resolver (`frob.arch._mayraise.compute_may_raise`,
docs/modules/arch.md#may-raise-resolver): `exhaustive_handling_gate` (gate
name `exhaustive_handling`, `gates-native` stage group, `--only
gates-native`) is the fail-closed exhaustiveness half over that resolver's
output, a static-type-checker-for-exceptions check that runs before a
single test does.

A function/method is treated as a declared BOUNDARY only once it has at
least one `except`/`catch` clause of its own (`NormalizedFunction.
catches`) -- a plain function with no attempt at handling is just
propagating, which is normal and not this gate's concern.
`compute_may_raise`'s `FunctionMayRaise.raises` is already the LEAKED
remainder after that function's own catches are subtracted (see that
resolver's own docstring), so any non-empty leaked set on a boundary is,
by construction, an incompletely-handled one:

- **EXHAUST001** (narrowed T-1402) -- `UNKNOWN` is in the leaked set,
  none of the boundary's own catches is broad enough to plausibly
  discharge it (a bare `except:` or `except Exception:`), AND the
  `UNKNOWN` traces to the function's OWN ambiguous bare re-raise (a bare
  `raise` whose nearest preceding catch is itself absent or a bare
  `except:`, mirroring `_mayraise._resolve_direct_raises`'s own-raise
  classification) -- a real, visible-in-source construct, not a
  call-graph resolution limit. A narrow `except ValueError:` never
  discharges it.
- **EXHAUST003** (T-1402) -- the same undischarged `UNKNOWN` leak, but
  traced ONLY to an unresolved callee (this function's own, or one it
  calls transitively) rather than an own ambiguous re-raise: a
  call-graph resolution-coverage gap, not a confirmed unhandled error
  path. Reported as a distinct, quieter signal instead of demanding a
  catch-all -- a 2026-08-01 measurement (T-1402) found 69/69 unwaived
  EXHAUST001 findings in this repo's own source were exactly this shape
  (100% citing "(Unknown)", 0% naming a concrete escaping type), which
  converted a tool resolution limit into developer work and encouraged a
  bare `except Exception:` that would have hidden the real error classes
  this gate exists to surface. Narrow it with a `# frob:callee-raises
  <Type>` declaration on the call, or improve resolution (native
  call-graph/typeshed awareness) -- both make the finding disappear
  honestly, unlike a blanket catch-all.
- **EXHAUST002** -- a named, non-`UNKNOWN` type is in the leaked set with
  no matching `# frob:raises <ExceptionType>` directive (below) declaring
  it as intentional propagation. The violation message names exactly the
  missing type(s). Unaffected by the T-1402 narrowing above -- EXHAUST002
  already only ever fires with a concrete type named.

- **EXHAUST004** (T-2543) -- the same named, non-`UNKNOWN` leak as
  EXHAUST002, but where every type reported exists ONLY because of the
  resolver's SUBSCRIPT rule. A lower-confidence tier, not a different
  question.

**EXHAUST004 -- what it covers, and what separates it from EXHAUST002.**
This is a rule id in the 1.0 gate surface, so its boundary is a contract,
not an implementation detail:

- EXHAUST002 means: this boundary leaks a named type with a CONFIRMED
  source -- an own `raise`, a curated builtin/stdlib raiser, or a
  `frob:callee-raises` declaration. Acting on it is warranted.
- EXHAUST004 means: this boundary leaks a named type whose ONLY source is
  an index expression (`d[k]`, `xs[i]`) the resolver could not
  shape-resolve. `frob.arch._mayraise` has no type information, so it
  cannot tell a mapping index (`KeyError`) from a sequence index
  (`IndexError`), nor a bounds-checked index from an unchecked one. It
  therefore reports the parent it genuinely knows, `LookupError` (T-2543
  A2 -- it previously picked `KeyError` outright, which was wrong in both
  directions: claimed at list-indexing sites and silent about the real
  `IndexError` exposure).

The split is by PROVENANCE, never by type name. `compute_may_raise` runs
a second, identical fixpoint with only the subscript rule suppressed and
reports the difference as `FunctionMayRaise.subscript_derived`, so a type
reachable by BOTH a subscript and some other route keeps its
higher-confidence EXHAUST002 classification. One function can emit both
rules at once -- its confirmed leaks as EXHAUST002 and its subscript-only
leaks as EXHAUST004 -- rather than being demoted wholesale because one of
its types is low-confidence.

This mirrors exactly what T-1402 did when it split EXHAUST003 out of
EXHAUST001 for the unresolved-callee case, and for the same reason: a
resolver coverage limit reported at the same volume and severity as a
confirmed defect converts a tool limitation into developer work, and the
cheapest way to satisfy it is the blanket `except Exception:` this whole
family exists to prevent. Measured on this repo's own source at the time
of the split: EXHAUST002 47 -> 8, with 68 findings carried by EXHAUST004.

NOTE for anyone reading a diff across this change: minting a new rule id
means an existing `frob:waive EXHAUST002` no longer suppresses a finding
that has been re-coded to EXHAUST004. That is visible as previously-
waived findings reappearing under the new id (26 of them here); it does
NOT red the floor, since EXHAUST004 is WARN and an EXHAUST002 waiver does
not become a WAIVE002 error (the id still matches elsewhere). Retargeting
those waiver comments is mechanical follow-up work, the same way T-1402
retargeted its own EXHAUST001 comments to EXHAUST003.

Both rules ship at WARN severity as of this landing (T-0688) -- a first
real run against this repo's own source surfaced 176 pre-existing
findings, the same first-turn-on-debt scale T-0680's REG008-REG011 and
T-0728's ARCH101-103 both disclosed for their own new gates; promoting to
ERROR is deliberately deferred to a follow-up ticket that pays that corpus
down first, not a softened design. Both attach `symref` (the leaking
function's `path::qualname`) so `frob:waive EXHAUST001 reason="..."` /
`frob:waive EXHAUST002 reason="..."` bind precisely to that one function,
the same waiver-precision convention every other symbol-scoped rule uses.

**Declared propagation directive**: `# frob:raises <ExceptionType>`,
placed directly above the function's `def`/decorator block (the same
above-the-def placement every other `frob:` directive in this repo
already uses), marks that the function intentionally lets
`<ExceptionType>` escape uncaught -- an explicit, auditable contract
instead of a silent EXHAUST002 gap. One directive line per declared type;
`_declared_propagations` scans a bounded lookback window directly above
the function's start line (`NormalizedFunction` itself carries no raw
comment text, so this is a raw-source scan, not a model field). A
directive never discharges `UNKNOWN` -- it names a KNOWN type, and
`UNKNOWN` is definitionally not one.

**Naming note (T-0931).** This is the ONLY convention that owns the verb
text `frob:raises`. A different, unrelated same-line call-site directive
(`NormalizedCall.declared_raises`, docs/modules/arch.md#may-raise-resolver)
was originally also named `frob:raises` when T-0689 landed concurrently
with this ticket; T-0931 renamed that call-site form to
`frob:callee-raises` to keep the two unambiguous -- this above-the-def,
function-wide form keeps `frob:raises` unchanged. T-0690's planned
FFI-boundary declarations extend this same above-the-def convention, not
the call-site one.

SCOPE: python-only (same disclosed limit `compute_may_raise` itself
already carries); non-python files, files with no tree-sitter grammar, and
test files (`frob.excludes.is_test_file`) are silently skipped.

### errors-as-values advisory (T-0688)

<a id="errors-as-values-advisory-t-0688"></a>
<!-- frob:describes src/frob/arch/_exceptions.py::check_errors_as_values -->

The sibling, suggestion-severity consumer of the SAME `compute_may_raise`
output (`frob.arch._exceptions.check_errors_as_values`), wiring into
T-0623's fallibility family (docs/modules/arch.md#fallibility-checks): a
PUBLIC function/method (bare name not underscore-prefixed) whose leaked
may-raise set contains a member of the curated recoverable set
(`ValueError`/`KeyError`/`LookupError`/`TypeError`, the same four types
`frob.arch._fallibility._RECOVERABLE_EXCEPTION_TYPES` already curates),
with no same-module caller visibly discharging it (a caller with a
wrapping `except` clause that is a catch-all or names one of the
recoverable types directly -- a disclosed coarse, function-wide,
exact-type-or-catch-all proxy, not a subtype-hierarchy walk), gets an
`ArchSuggestion` (category `errors-as-values-recommended`) recommending a
typani `Result[T, E]` signature instead, with the raising function as the
sketch site. `UNKNOWN` and non-recoverable (programmer-bug-class)
exception types never trigger this advisory -- exceptions remain
sanctioned for those, per T-0623's own house doctrine.

T-0972: the message-formatting `sorted(recoverable)` call inside this
function's per-function loop now carries a reasoned `frob:waive PERF004`
(the set differs every iteration, so there is nothing to hoist) -- no
behavior change.

Like `frob.arch._fallibility.run_fallibility_checks` before it,
`check_errors_as_values` stays on the unwaivable advisory channel every
`ArchCategory` lives on by default (`frob.gates._unwaivable_channel_
rules` picks up the new category automatically) and is not yet dispatched
by `analyze_project`'s live per-file walk -- wiring the whole fallibility
family into that dispatch loop is a distinct, larger-surface follow-up
ticket (T-0616's SRP-family precedent: built and tested first, dispatch
wiring landed later as its own ticket, T-0728), not something this ticket
silently folds in.

## FFI001 FFI002 (T-0690)

<a id="ffi001-ffi002-t-0690"></a>
<!-- frob:describes src/frob/gates/_ffi_boundary.py::ffi_boundary_gate -->

Child 4 of T-0685's exception may-raise umbrella, completing the residual
work `frob:callee-raises` (T-0689/T-0931) and the above-the-def
`frob:raises` directive (EXHAUST001/EXHAUST002 above) left open: neither
of those already-landed conventions cross-checks a pyo3 boundary's
Rust-side observed exception surface against its Python-side declaration,
and neither MANDATES a declaration exist at all on a ctypes/cffi boundary
(they only let one substitute for the may-raise resolver's fail-closed
`Unknown` when present). `ffi_boundary_gate` (gate name `ffi_boundary`,
`gates-native`-style process job, dispatches `frob.arch._ffi`'s two scans,
docs/modules/gates.md#ffi001-ffi002-t-0690) supplies both, per
the parent ticket's three-tier FFI mandate:

- **FFI001** (pyo3 cross-check drift, tier 1 -- our own pyo3 crates,
  `strata-core`/`frob-core`): every `.pyi` stub whose module docstring
  carries a `frob:describes <path>.rs` pragma is paired with that Rust
  source file; `frob.arch._ffi.scan_pyo3_raises` computes each
  `#[pyfunction]`'s OBSERVED raised-type set (explicit `Py<X>Error::
  new_err(...)`/`PyErr::new::<Py<X>Error>(...)` constructions, plus
  `panic!`/`unreachable!`/`todo!`/`unimplemented!`/`.unwrap()`/`.expect(`
  as a `PanicException` sentinel -- pyo3 converts an unhandled Rust panic
  into that raised type at the Python call boundary) and cross-checks it
  against the stub's own above-the-def `# frob:raises <Type>` declarations
  (the SAME directive EXHAUST002 owns, reused here as this boundary's
  declaration surface, not a second grammar). Any observed type absent
  from the declared set is FFI001, naming BOTH sides in the message.
- **FFI002** (mandatory ctypes/cffi declaration, tier 2): ctypes/cffi calls
  have no exception-propagation contract at all (errno/return-code
  convention only; a C++ exception crossing an `extern "C"` boundary is
  `std::terminate`/UB, never a normal Python raise) -- per the mandate, the
  declaration IS the only truth. `frob.arch._ffi.scan_ctypes_boundary_
  calls` finds every call made through a variable bound via
  `ctypes.CDLL`/`ctypes.PyDLL`/`ctypes.WinDLL`/`ctypes.OleDLL`/
  `ctypes.cdll.LoadLibrary` (and the `pydll`/`windll` siblings) and FFI002
  fires on any such call site missing a same-line `# frob:callee-raises`
  comment (T-0689's existing call-site directive) -- a bare `#
  frob:callee-raises` (declaring the empty set) is a valid, honest
  "raises nothing, errno convention" declaration and clears the finding.

Tier 3 (third-party compiled modules: "declaration optional, Unknown
otherwise") is explicitly out of this gate's scope -- `frob.arch.
_mayraise`'s existing fail-closed `UNKNOWN` default for any unresolved
callee already covers it unchanged.

Both rules ship at `Severity.ERROR` directly, not `Severity.WARN` -- a
real run of both scans against this repo's own source at landing time
surfaced exactly one FFI001 finding (`strata_core.worst_age`'s Rust-side
`.expect(...)` on the condensation DAG's zero-indegree SCC lookup, a
genuine if unreachable-in-practice panic site) and zero FFI002 findings
(this repo has no ctypes/cffi usage anywhere); the one FFI001 finding was
fixed at landing by adding `# frob:raises PanicException` to `strata_core.
pyi`'s `worst_age` stub rather than deferred as debt, so there is no
pre-existing corpus an ERROR severity would instantly red the way
EXHAUST001/002's own 176-finding first run did.

SCOPE: FFI001 always cross-checks pyo3 boundaries repo-wide (a boundary
pair is a repo-wide concern, same reasoning EXHAUST001/002 already use for
running against `repo_root` rather than a possibly-scoped `root`); it only
fires for `.pyi` stubs actually carrying the `frob:describes ...rs`
pragma -- a hand-written or third-party `.pyi` with no such pragma is
silently skipped. FFI002 scans every `.py` file under the possibly-scoped
`root`, test files excluded (`frob.excludes.is_test_file`, mirroring
EXHAUST001/002's own carve-out).

## SUPPRESS001 (T-1340)

<a id="suppress001-t-1340"></a>
<!-- frob:describes src/frob/gates/_suppress.py::suppress001_gate -->

Phase 1 of T-1339's suppression-dialect compliance epic: a source line can
carry one checker's suppression comment (mypy's `# type: ignore[code]`)
while a DIFFERENT checker (`ty`) still errors on that exact line, because
`ty` does not honour mypy's suppression dialect at all. The motivating
incident -- two `ty` errors hand-fixed on `main`
(`tests/test_fuzz.py:159`, `tests/test_tickets_collision.py:826`) -- were
not real type defects, only dialect mismatches.

**The goal is portability, not conformance** (T-1339's DESIGN AMENDMENT,
binding): this repo gates on `ty`, but a downstream consumer type-checking
frob's source with `mypy` must not eat spurious errors either, so a
suppressed line should ideally carry every SUPPORTED dialect's
suppression, including one this repo never runs as a gate.
`SuppressionDialect.available` (see `suppression_dialects` below) therefore
means "an oracle exists in THIS process to supply that dialect's real
diagnostics" (a capability limit -- `shutil.which` resolving the tool on
`PATH`), never "is this tool configured for this
project". This supersedes T-1340's own acceptance criterion [2] as
originally written ("a checker that is not configured in this project ..
reports nothing"): the criterion is reworded to "a dialect with no
available oracle produces no findings for that direction".

Detection is EVIDENCE-DRIVEN, never a static mypy-code <-> ty-code mapping
table (both codes are not 1:1 -- `name-defined` vs `unresolved-reference`,
`attr-defined` vs `unresolved-attribute` -- a lossy table was explicitly
rejected by both T-1339 and this ticket). `suppress001_gate` runs whichever
of the `ty`/`mypy` oracles are available against `root`, then for every
diagnostic a `reporting` dialect emits at `file:line`
(`_suppress001_correlate`): if that line already carries a suppression
covering `reporting`'s own rule code (bare, or a matching coded ignore),
nothing fires; otherwise, if the line carries a DIFFERENT dialect's
suppression comment, SUPPRESS001 fires naming both dialects and
`reporting`'s own rule code (the diagnostic itself, never a lookup
table). Each direction (mypy suppressed/ty unsuppressed, and the
symmetric ty suppressed/mypy unsuppressed) falls out of the same loop
with no direction hard-coded.

`mypy` is a DEV DEPENDENCY here, used PURELY as a diagnostic oracle (this
module's own `_mypy_diagnostics` oracle helper) -- `frob check` never gates on
mypy's own exit code or diagnostics, only this gate's correlation of them
against `ty`'s. `--warn-unused-ignores` is deliberately never passed to
the oracle invocation (T-1339's watch item): this gate's evidence-driven
design does not need it, and turning it on would produce unrelated noise
from this repo's 17 pre-existing legacy mypy-only ignores that predate
mypy running here at all. `--check-untyped-defs` IS passed, since mypy
skips type-checking an untyped `def`'s body by default -- without it the
oracle would silently miss most of a typical fixture function.

A line with no suppression comment at all and a genuine unsuppressed
diagnostic from either checker is NOT this gate's concern -- SUPPRESS001
only ever fires on a cross-DIALECT mismatch, never on a bare, honestly
unsuppressed type error (that is `ty`'s own gating job, or a downstream
mypy user's).

Detection only -- `suppress001_gate` itself never edits a source file. The
Tier-A auto-fix that WRITES the paired suppression is
`fix_suppress001_paired_suppression` (T-1341), documented under "`--fix`:
Tier-A deterministic auto-fix handlers (T-1138)" below.

## CACHE001 (T-1520)

<a id="cache001-t-1520"></a>
<!-- frob:describes src/frob/gates/_cache_gate.py::cache_gate -->

The recurring cache-bug class is key incompleteness: a cached computation
reads an input its declared cache key does not cover, so a change to that
input serves a stale result -- the real T-1454 incident (`frob ack`
rewrote `frob.lock`, no tracked source digest changed, a previously cached
DRIFT001 result stayed stale and kept being served). `invariants/
INV-050.md` states the correctness theorem this is one enforcement half
of (`check(S, C) == check(S, empty)` for every persistent cache); CACHE001
is the STATIC half, catching the key-incompleteness shape before a test
run ever has to observe the staleness.

`frob.check._memo.memoize_per_run` is the narrowest, most mechanical case:
its cache key is exactly (and only) the decorated function's own,
`_freeze`d call arguments (T-0423). If the function's BODY reads something
no argument derives from -- a hardcoded path, `os.environ`, a module-level
global -- that read is invisible to the key, and a second call with
identical arguments inside the same `run_memo_scope()` can serve a stale
result even though the thing it silently read changed underneath it.
CACHE001 flags exactly this: an AST scan (same structural-gate precedent
as WALK001/`_pii_structural`, module docstring) over every
`@memoize_per_run`-decorated function, checking that every `Path.
read_text`/`.read_bytes`/`open()` call's target, and every `os.environ`/
`os.getenv` access, names at least one of the function's own parameters
somewhere in its expression tree. A read with no such reference is an
uncovered read: `frob:waive CACHE001 reason="..."` is the escape hatch for
a genuinely immutable-for-the-run's-duration read (dynamic reads the
detector cannot statically rule safe).

**Scope, disclosed rather than silent (T-1520's own acceptance floor):**
this first cut only recognizes the `@memoize_per_run` decorator by bare
name (matching this repo's three real call sites --
`frob.arch.analyze_project`, `frob.dup._legacy.find_duplicates`,
`frob.graph.build_graph` -- all clean, zero CACHE001 findings against the
live tree at introduction), and only a function's OWN body, not callees it
transitively reaches. `frob.lang.parse_file`'s dynamically-wrapped
content-hash-keyed artifact cache is a DIFFERENT, already-correct
cache-key discipline (a real content digest, not `memoize_per_run`'s
args-only key) this detector's decorator-name match structurally cannot
see, by design -- not a gap in the same family. The long tail (every other
persistent-cache-backed computation this repo has -- `.frob/gate-cache.db`,
`.frob/cache.db`'s own writers, `.frob/tickets-archive-cache.json`,
`.frob/pytest-collect.json`, `.frob/hotgraph_sketches.db`,
`.frob/check-budget-timing.json`, `frob-coverage.lock.json` -- see
`invariants/INV-050.md`'s inventory) is tracked as follow-up work, not
silently dropped.

## WIRE001/WIRE002 (T-1428)

<a id="wire001-wire002-t-1428"></a>
<!-- frob:describes src/frob/gates/_wire.py::wire_gate -->

Five real instances in one session landed, passed every gate, closed
honestly, and did nothing: `own_obligations_clean` (T-1384),
`gate_claims_verified` (T-1399), `only_paths` (T-1391), `bug_repro_
violations`/BUG002 (T-1421), and CLI `--amend`/`--remove` silently dropped
by `AppConfig.from_external` (T-1422). Every one was disclosed honestly in
its own Done report, with a follow-up ticket filed. The rule was still
never checkable: a ticket declares a scope, and the new code and its call
site almost always live in DIFFERENT modules, so working strictly inside
scope produces an inert change by default, and unit tests calling the new
code directly pass regardless.

`DEAD001` (above) cannot see this class: it only reasons about PRIVATE
symbols (exempting exactly the shape most of these instances took --
`own_obligations_clean` and `bug_repro_violations` are both public), and
it asks "does ANY private symbol in the whole tree have a caller", not
"did THIS DIFF add something nothing outside its own tests reaches".
WIRE001 asks the diff-scoped question `wire_gate` implements three of the
four case shapes for, deliberately NOT via `build_reference_graph`/
`build_call_graph` (this module's own DEAD001 substrate): both resolve an
edge only when the CALLEE is private (`frob.graph.callgraph._resolve_
edges`'s "never a public symbol" rule) -- exactly backwards here. Instead:

- **A new function/method/class with no non-test caller** (T-1421's
  shape): every symbol whose entire span sits inside this diff's added-
  line hunks is a candidate; a repo-wide, deliberately best-effort TEXT
  scan (`_is_reached_outside_diff_tests`) looks for its short name used
  call-shaped in any non-test file other than its own definition line.
  Biased toward NOT firing on ambiguity (an unrelated same-named function
  elsewhere counts as "reached") -- a false "reached" costs nothing, a
  false "unreached" wrongly blocks a build.
- **A new gate rule id absent from `_KNOWN_GATE_RULES`** (T-1421's BUG002
  shape): a `rule="XYZ001"` literal added by this diff whose id is not in
  `frob.gates._waive._KNOWN_GATE_RULES`.
- **A new CLI flag `dest=` absent from `_config_external.py`'s copy
  lists** (T-1422's shape, called out as the hardest in this ticket's
  brief): the wiring is a quoted string landing inside one of
  `_build_external_config_kwargs`'s field-name tuples, never a call
  token -- structurally invisible to any call-graph approach, general or
  otherwise. Caught by a TARGETED string-membership check over
  `src/frob/app/_config_external.py`'s current text, not by generalizing
  the call-graph machinery to cover it.

**Not implemented**: a new keyword-only parameter no call site passes
(T-1384/T-1399/T-1391's shape) needs a signature-level before/after AST
diff this ticket does not build; disclosed and filed as a follow-up
(see this ticket's Done report for the id).

**Structural limitation, confirmed by measurement (T-2928)**: WIRE001
case 1 only ever evaluates a symbol whose ENTIRE span sits inside THIS
diff's own added-line hunks (`_new_callable_records`) -- it cannot, and
is not meant to, catch a symbol that has been dead since a PRIOR ticket
and is simply being looked at again now (a waiver removed, a comment
touched) without its own defining lines being part of the current diff.
Measured directly on a real controlled deletion: `_parse_bash`/
`_parse_csharp` (T-1604/T-1600, dead ever since, deleted for real by
T-2900/T-2905) never tripped WIRE001 even with their `frob:waive
WIRE001` comments removed, because the diffs that touched them never
touched their own body lines. This is deliberate diff-scoping working
as designed, not a bug -- DEAD001 already owns "does any private symbol
anywhere in the tree have zero callers" (unconditional, WARN); making
WIRE001 also answer that question would duplicate DEAD001 at ERROR
severity, a distinct feature decision, not a fix. Regression fixture:
`tests/test_gates.py::TestWire001DiffScopingMissesPreExistingDeadSymbols`
(a must-stay-quiet case for the exact T-2900/T-2905 shape, paired with a
must-still-fire control proving the SAME dead symbol is caught the
moment it is genuinely introduced by the diff being measured).

**Cross-test-file reachability for a helper DEFINED under `tests/`
(T-1558)**: `_is_reached_outside_diff_tests`'s text scan used to skip
EVERY test path unconditionally, on the theory that a production symbol
with only test callers is still dead in the code that ships. That is
right for production code, but wrong for a helper this diff adds INSIDE
`tests/` -- a shared test-fixture helper (`tests/_cache_transparency.py::
git_init`, called from `tests/test_cache_transparency.py`/
`tests/test_gate_cache.py`) is genuinely wired, just entirely within the
test tree, and skipping every test path made it an unfixable false
positive whose only remedy was a waiver (16 accumulated instances, all
bound to T-1558 as their open "waiver home" ticket before this landed).
For a symbol whose own defining file is under `tests/`, a call from any
OTHER test file now counts as reached; a call from its own defining file
still does not -- same-file-only usage stays genuinely unwired (T-1592's
precedent), and gets a `permanent="true"` waiver (see WIRE002's own
section above), not a gate teach, because there is no other file to teach
the gate to look at.

**The escape hatch is a checkable obligation, not free-text prose**: a
bare `frob:waive WIRE001 reason="..."` would suppress the finding through
the same generic waiver machinery every other gate uses, with no
guarantee anyone ever wires the code later -- exactly the "honest but
unenforceable disclosure" this ticket exists to close. WIRE002 (error,
unwaivable) fires whenever a `frob:waive WIRE001` is missing a
`follow_up="T-####"` attribute, or `follow_up` names a ticket that does not
exist or is already `done`/`dropped`:

```python
# frob:waive WIRE001 reason="public API for downstream consumers, wired \
by the CLI subcommand landing in the same series" follow_up="T-1500"
```

WIRE001 itself stays ERROR-tier but ordinarily waivable (ceiling/package-
prefix matching, same as every other waivable rule) -- WIRE002 is what
makes the waiver's own content matter, so a two-phase landing is an
enforced obligation bound to a real open ticket, not a note nobody has to
act on.

**`permanent="true"` for a test-only helper that is never meant to be
wired (T-1592)**: `follow_up=` asks "who will wire this, and by when" --
the right question for a symbol that is temporarily unwired. It is the
wrong question for a private test-seed helper called only by its own
file's test methods, where having no production caller is the permanent,
intended design. Forcing such a waiver to name a follow-up ticket just
manufactures a placeholder obligation that turns into a fresh WIRE002
orphan the moment that placeholder ticket closes (the live incident:
`tests/unit/test_mutation_sweep_queue.py::_make_ticket` named its own
landed ticket as `follow_up`, and WIRE002 fired again on main the moment
that ticket closed). A `frob:waive WIRE001` may instead declare
`permanent="true"`, satisfying WIRE002 with no `follow_up=` at all,
restricted to a private symbol (leaf name starting with `_`) whose
enclosing file lives under `tests/` -- so production code cannot use this
to dodge real wiring:

```python
# frob:waive WIRE001 reason="a private test-seed helper used only by this \
file's own test methods -- there is no production caller to wire it to \
by design" permanent="true"
def _make_ticket(...):
    ...
```

A `permanent="true"` waiver on a non-test-tree file, or on a public
symbol, does NOT satisfy WIRE002 -- `_wire002_is_permanent_test_helper_
waiver` (`frob.gates._wire`) checks both conditions, and `follow_up=` is
still required otherwise.

**Dynamic-dispatch rescues: an autouse pytest fixture (T-1510) and a
pydantic validator (T-1652/T-2325).** `_new_callable_records`'s text-scan
substrate cannot see a caller that only ever exists inside a FRAMEWORK'S
own dispatch machinery, not a call token in this repo's own source:

- An autouse pytest fixture (`_is_autouse_pytest_fixture`) is injected by
  pytest itself into every in-scope test, never called by name anywhere.
  T-1510 fixed the resulting false positive (5 of this repo's own
  fixtures flagged before the rescue landed).
- A pydantic `@field_validator`/`@model_validator` method
  (`_is_pydantic_validator`) is invoked by pydantic's own decorator-
  registry dispatch at model-construction/field-assignment time, the
  identical dynamic-dispatch shape. T-1652 confirmed 9 of 20 real
  DEAD001 findings were exactly this shape and rescued DEAD001 for it;
  T-2325 closed the matching gap in WIRE001 itself, which had NOT
  rescued this shape even though `frob.gates._waive`'s WAIVE008 (its own
  "is this WIRE001 waiver now permanently dead" liveness check, see
  `_wire001_symbol_now_rescued`) already assumed it was -- a fresh
  pydantic validator false-positived WIRE001 unwaived, and false-
  positived WAIVE008 too if waived anyway, with no clean way to satisfy
  both checks before this fix.

Both predicates live in `frob.gates._dead_symbols` (shared with DEAD001)
and are applied in `_new_callable_records` right alongside each other --
a symbol matching either predicate is excluded from WIRE001's new-symbol
candidate set entirely, same posture as any other symbol the diff never
actually introduced.

## WIRE003 (T-1725)

Hooks and docs reference `frob` verbs BY NAME, as plain strings, with
nothing checking they resolve: `frob-timeout-guard.py`'s own `PATTERN`
(`frob +(ticket +(land|done-report)|check|test)\b`) decides whether a
command needs a large tool timeout, and `frob-suggest.py`'s refusal text
SUGGESTS `uv run frob test`/`frob check`/<!-- frob:waive DOC006 reason="illustrative ellipsis placeholder for any frob ticket subcommand, not a literal invocation" -->`frob ticket ...`/etc. A rename
(the T-1567..T-1571 CLI regrouping this rule exists to unblock) silently
breaks both: the hook keeps running and keeps passing, or keeps blocking
a caller and then telling it to run a command that no longer exists
(the T-1705 failure shape).

`_wire003_stale_verb_references` (`frob.gates._wire`) resolves every
`frob`-verb reference in a tracked hook/doc against the LIVE CLI
dispatch table (`frob.__main__._build_parser`, walked recursively via
`argparse._SubParsersAction.choices` -- never a hand-written list of
verb names, which would be the same defect class as the bug and would
drift the first time someone adds a verb). Two reference SHAPES are
both covered from the same extraction path:

- The regex/matcher form: a `re.compile(...)` call's string-literal
  argument, found via `ast.parse` (so `frob-timeout-guard.py`'s `PATTERN`
  is read even though it is a raw string, never backtick-wrapped).
- The prose form: any backtick-quoted span (`` `frob check` ``) --
  markdown's own "this is code" marker, and the convention every
  suggestion string in this repo's hooks already follows.

Extended-glob alternation (`+()`/`|`) is treated as a token separator,
so `frob +(a|b)` yields BOTH `a` and `b` as independent candidates, each
split into its own fragment before tokenizing -- reading tokens as one
continuous run across an alternation would otherwise misread
`land|totallymadeupverb` as the nonsense chain `land totallymadeupverb`.
At most 2 leading tokens are read per fragment (real `frob` commands
never nest past `<verb> <subverb>`); a 3rd+ token (a ticket id, a flag
value) is an argument, not another verb, and reading it as one would
misread `frob ticket land T-0001` as referencing a nonexistent verb
`T-0001`.

**Scope, deliberately narrower than "every tracked doc" (T-1725's own
"wider scope" ask, measured):** `_WIRE003_SCAN_GLOBS` covers
`.claude/hooks/*.py` and the two docs T-1725 names as load-bearing
(`docs/guides/agent-playbook.md`, `docs/modules/cli.md`) at ERROR
severity. A repo-wide `docs/**/*.md` scan was measured and found too
imprecise to enforce today: this rule's extraction heuristic (a `frob`
word followed by 1-2 tokens inside a backtick span) false-positives
against ordinary doc prose that happens to mention "frob" near
unrelated backtick-quoted vocabulary (ticket priority levels, board
column names, config keys) -- 48 findings across 10 files with backtick-
only scanning, 181 across many more once fenced code blocks (which
routinely contain command OUTPUT -- log lines, JSON -- that reads as
command-shaped to a naive scanner without being one) are also included.
Widening `_WIRE003_SCAN_GLOBS` to the full docs tree is a real follow-up
(a per-token allowlist, or requiring a stricter anchor like `` `uv run
frob ...` ``), not something to force through at ERROR severity before
that precision work lands -- forcing it through today would just
reproduce the 997-waiver anti-pattern this repo has already paid for
once.

`frob:waive WIRE003 reason="..."` is the escape hatch for a genuine
false positive within the enforced scope (prose that happened to land
inside a code span/pattern).

## REFSCHEMA001 (T-2390 epic child, T-2428)

T-2390's own finding: frob validates its CLI-flag input channel to a
real standard (FLAGCOV001) but its config-FILE input channel had no
unknown-key validation anywhere -- a typo'd or stray key in a
`frob.toml` table silently does nothing, forever. This rule is the epic's
first child, applied to the single LARGEST table in this repo's own
`frob.toml` (`[[refs.entrypoint]]`, 58 leaf values across 29 entries)
first, establishing the pattern the epic's other nine children copy.

`frob.gates._refs._load_allowlist` (REF001/002/003's own allowlist
reader) already degrades a MALFORMED entry (missing `path`/`reason`,
wrong type) to a logged warning and a dropped entry. What it does NOT
catch: an entry with an EXTRA or MISSPELLED key alongside otherwise
valid `path`/`reason` values -- `.get("path")`/`.get("reason")` only
ever look at the two names they know, so a third key is never read,
never validated, never reported. `frob.gates._refs_schema.refs_schema_
gate` is that missing check, read from the RAW `[[refs.entrypoint]]`
records (deliberately not `_load_allowlist`'s own filtered output,
which already drops the malformed shape this check needs to still see).

PORTABILITY (T-2384's doctrine): the known-key set is declared via
`[refs] entrypoint_schema = "module:symbol"` (a dotted path to a
`frozenset[str]` or a zero-arg callable returning one), resolved
through the SAME `frob.gates._docblocks_shared.resolve_dotted_symbol`
idiom FLAGCOV001 (T-2397) already established -- this repo's own
declaration points at `frob.gates._refs_schema.REFS_ENTRYPOINT_KNOWN_
KEYS` (`frozenset({"path", "reason"})`), but any project can declare
its own set without touching this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as FLAGCOV001): no `entrypoint_schema`
declared, an unresolvable dotted path, or a resolved value that is
neither a set nor a set-returning callable all report `Severity.
UNRESOLVED` -- never a silently empty (and therefore falsely "clean")
violation list.

## NATIVESCHEMA001 (T-2390 epic child, T-2429)

T-2390's finding applied to `[[native]]` (6 leaf values across 2 entries
in this repo's own frob.toml). `frob.testing._runners._parse_native_
entry` reads exactly `name`/`build_cmd` (required, `entry[...]`) plus
`language` (optional, `.get()` with a default) -- a fourth key (a typo
like "buld_cmd", or a stray field) is never read, never validated, never
reported; the entry parses "successfully" with the typo'd field simply
absent.

PORTABILITY (T-2384's doctrine): the known-key set is declared via
`[native_schema] known_keys = "module:symbol"` (a dotted path to a
`frozenset[str]` or a zero-arg callable returning one), resolved through
the same `resolve_dotted_symbol` idiom REFSCHEMA001/FLAGCOV001 already
established -- this repo's own declaration points at `frob.natives.
_native_schema.NATIVE_KNOWN_KEYS` (`frozenset({"name", "build_cmd",
"language"})`), but any project can declare its own set without touching
this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as REFSCHEMA001/FLAGCOV001): no `known_keys`
declared, an unresolvable dotted path, or a resolved value that is
neither a set nor a set-returning callable all report `Severity.
UNRESOLVED` -- never a silently empty (and therefore falsely "clean")
violation list.

## PROFILESCHEMA001 (T-2390 epic child, T-2430)

T-2390's finding applied to `[profile]` (2 leaf values in this repo's own
frob.toml, the epic's smallest table). `frob.tickets._profile.effective_
profile`/`_override_ratchet_enabled` read exactly `profile` and
`override_ratchet` via `.get(...)` -- a third key (a typo like
"overide_ratchet", or a stray field) is never read, never validated,
never reported; the entry parses "successfully" with the typo'd field
simply absent, silently falling back to defaults.

PORTABILITY (T-2384's doctrine): the known-key set is declared via
`[profile_schema] known_keys = "module:symbol"` (a dotted path to a
`frozenset[str]` or a zero-arg callable returning one), resolved through
the same `resolve_dotted_symbol` idiom every other T-2390 child uses --
this repo's own declaration points at `frob.gates._profile_schema.
PROFILE_KNOWN_KEYS` (`frozenset({"profile", "override_ratchet"})`), but
any project can declare its own set without touching this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as every other T-2390 child): no `known_keys`
declared, an unresolvable dotted path, or a resolved value that is
neither a set nor a set-returning callable all report `Severity.
UNRESOLVED` -- never a silently empty (and therefore falsely "clean")
violation list. A repo with no `[profile]` table at all is not itself an
error -- the table is optional.

## TOPSCALARSCHEMA001 (T-2390 epic child, T-2431)

T-2390's finding applied to frob.toml's two top-level SCALAR keys
(`min_frob_version`, `check_base` -- no enclosing <!-- frob:waive DOC006 reason="[table] here is generic placeholder terminology for 'any TOML table', not a real frob.toml section name" -->`[table]` at all).
Structurally different from every other T-2390 child: there is no table
to iterate and no array-of-records, just a flat set of bare `key = value`
lines at the document root. `frob.repo_meta.declared_min_frob_version`
and `frob.app.check_runner`'s `check_base` default-fill each read exactly
one name via `.get(...)` -- a misspelled top-level key is never read,
never validated, never reported.

PORTABILITY (T-2384's doctrine): the known-key set is declared via a
dedicated `[toplevel_scalar_schema] known_keys = "module:symbol"`
sub-table (kept OUT of the document root itself so the declaration key
can never be mistaken for one of the scalars it describes) -- a dotted
path to a `frozenset[str]` or a zero-arg callable returning one, resolved
through the same `resolve_dotted_symbol` idiom every other T-2390 child
uses -- this repo's own declaration points at `frob.gates.
_toplevel_scalar_schema.TOPLEVEL_SCALAR_KNOWN_KEYS` (`frozenset({"min_
frob_version", "check_base"})`), but any project can declare its own set
without touching this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as every other T-2390 child): no `known_keys`
declared, an unresolvable dotted path, or a resolved value that is
neither a set nor a set-returning callable all report `Severity.
UNRESOLVED` -- never a silently empty (and therefore falsely "clean")
violation list. Table headers themselves (`[arch]`, `[gates]`, etc,
whose parsed value is a `dict`) are excluded from consideration entirely
-- this check only concerns bare scalar keys, never table names.

## TESTINGSCHEMA001 (T-2390 epic child, T-2432)

T-2390's finding applied to `[testing]` (5 leaf values in this repo's
own frob.toml). UNLIKE every other T-2390 child, `[testing]` already has
a real pydantic model (`frob.gates._models.TestPolicy`) -- but `frob.
gates._sys._load_test_config` filters the raw table down to known fields
BEFORE constructing it: `TestPolicy(**{k: v for k, v in testing_tbl.
items() if k in fields})`. That `if k in fields` guard is exactly the
silent-drop this epic exists to close -- an unknown/misspelled key never
reaches `TestPolicy` at all, so `model_config` (even `extra="forbid"`)
never gets a chance to see it, confirming the epic's own finding that a
real pydantic model is not sufficient when the raw-table reader
pre-filters before construction.

PORTABILITY (T-2384's doctrine): rather than hand-listing `TestPolicy`'s
field names a second time, the known-key set is declared via
`[testing_schema] known_keys = "module:symbol"` pointed at `frob.gates.
_testing_schema.testing_known_keys`, a zero-arg callable that reads
`TestPolicy.model_fields` directly -- the model stays the single source
of truth, resolved through the same `resolve_dotted_symbol` idiom every
other T-2390 child uses.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as every other T-2390 child): no `known_keys`
declared, an unresolvable dotted path, or a resolved value that is
neither a set nor a set-returning callable all report `Severity.
UNRESOLVED` -- never a silently empty (and therefore falsely "clean")
violation list. A repo with no `[testing]` table at all is not itself an
error -- the table is optional.

## ARCHSCHEMA001 (T-2390 epic child, T-2433)

T-2390's finding applied to `[arch]` (10 known keys: the 5 T-0373 size
thresholds plus the 5 T-0728 SRP/cohesion knobs -- this repo's own
frob.toml currently sets 5 of the 10). `frob.repo_meta.load_arch_config`
hand-lists its 10 named keys against its own calibrated-defaults dict
and reads each via `arch_cfg.get(key, default)` -- a misspelled key
(e.g. "max_fuction_lines", this epic's own filing-time example) silently
reverts to the built-in default with no diagnostic: the typo'd entry
sits in frob.toml, looking configured, doing nothing.

PORTABILITY (T-2384's doctrine): the known-key set is declared via
`[arch_schema] known_keys = "module:symbol"` pointed at `frob.gates.
_arch_schema.arch_known_keys` (a plain hardcoded literal, deliberately
NOT importing `load_arch_config`'s own default constants -- `frob.
repo_meta` is a different strata component from `frob.gates`, and doing
so would introduce an undeclared cross-component Flow and trip SYS003/
SELFAUDIT001, the same lesson T-2429 already paid for), resolved through
the same `resolve_dotted_symbol` idiom every other T-2390 child uses --
any project can declare its own known-key set for its own [arch]-shaped
table without touching this module.

NESTED SUB-TABLE EXCLUSION: `[arch.layering]` (T-0620's DIP layering
contract, `frob.arch._layering`) is a genuinely different, deliberately
inert, documented sub-table nested one level inside `[arch]` -- a
dict-valued key inside `[arch]` is excluded from this check entirely,
the same way TOPSCALARSCHEMA001 excludes real <!-- frob:waive DOC006 reason="[table] here is generic placeholder terminology for 'any TOML table', not a real frob.toml section name" -->`[table]` headers from its
own scalar-key check.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as every other T-2390 child): no `known_keys`
declared, an unresolvable dotted path, or a resolved value that is
neither a set nor a set-returning callable all report `Severity.
UNRESOLVED` -- never a silently empty (and therefore falsely "clean")
violation list.

## DOCBLOCKSSCHEMA001 (T-2390 epic child, T-2434)

T-2390's finding applied to `[[docblocks.commands]]` (4 leaves in this
repo's own frob.toml currently: `prog`, `parser`, plus T-2397's own
`config`/`forwarded` keys). `frob.gates._docblocks_refs._console_
command_sources` reads exactly those four names via `.get(...)` -- a
fifth key (a typo, or a stray field) is never read, never validated,
never reported.

PORTABILITY (T-2384's doctrine): the known-key set is declared via
`[docblocks_schema] known_keys = "module:symbol"` (a dotted path to a
`frozenset[str]` or a zero-arg callable returning one), resolved through
the same `resolve_dotted_symbol` idiom every other T-2390 child uses --
this repo's own declaration points at `frob.gates._docblocks_schema.
DOCBLOCKS_COMMAND_KNOWN_KEYS` (`frozenset({"prog", "parser", "config",
"forwarded"})`, including T-2397's own `config=`/`forwarded=` keys as
legitimate schema members), but any project can declare its own set
without touching this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as every other T-2390 child): no
`known_keys` declared, an unresolvable dotted path, or a resolved value
that is neither a set nor a set-returning callable all report
`Severity.UNRESOLVED` -- never a silently empty (and therefore falsely
"clean") violation list.

## GATESSCHEMA001 (T-2390 epic child, T-2435)

T-2390's finding applied to the full `[gates]` namespace (19 leaves
total: 18 in `[gates.severity]`, 1 in `[gates.ratchet]` -- there is no
bare `[gates]` table itself in this repo's own frob.toml). TWO
genuinely different validation shapes live under one rule:

- `[gates.ratchet]` (`frob.gates._ratchet`) is an ordinary fixed-key-set
  table, same shape as every other T-2390 child -- its only known key is
  `rules`, declared via `[gates_schema] ratchet_known_keys = "module:
  symbol"` the same way every other child declares its known-key set.
- `[gates.severity]` (`frob.gates._waive._severity_overrides`) is
  structurally different: its KEYS are themselves gate rule ids (e.g.
  `COV001 = "error"`). The existing reader already degrades a malformed
  VALUE gracefully (a non-"warn"/"error" value logs a warning and is
  ignored) -- what it does NOT catch is a malformed KEY: a misspelled
  rule id silently sits in the overrides dict forever, matching against
  nothing. This half validates every KEY against the canonical live
  rule-id registry (`frob.gates._waive._KNOWN_GATE_RULES`) directly --
  same component, imported directly, no cross-component Flow question,
  and no "declared schema" state at all (a frob.toml-configurable
  known-key set for "which rule ids exist" would be circular), so this
  half never reports UNRESOLVED, only findings or a clean pass.

FAIL-LOUDLY (T-2391's doctrine): the `[gates.ratchet]` half reports
`Severity.UNRESOLVED` (never a silently empty, falsely "clean" list) when
no `ratchet_known_keys` is declared or it fails to resolve, same posture
as every other T-2390 child.

## TESTRUNNERSCHEMA001 (T-2390 epic child, T-2436)

T-2390's finding applied to `[[test.runner]]` (16 leaves across 4
entries in this repo's own frob.toml). `frob.testing._runners._parse_
runner_entry` reads `command`/`all_command`/`language` (required) plus
`cwd`/`collector`/`timeout_s` (optional) -- a seventh key (a typo, or a
stray field) is never read, never validated, never reported.

COMPONENT MEMBERSHIP (the T-2429 lesson, re-applied): `frob.testing.
_runners` lives in a different strata component from `frob.gates` -- so,
exactly as with T-2433's `[arch]` child, the known-key set here is a
plain hardcoded literal tuple in `frob.gates._test_runner_schema` rather
than an import of `frob.testing._runners`'s own internals, which would
introduce an undeclared cross-component Flow and trip SYS003/
SELFAUDIT001.

PORTABILITY (T-2384's doctrine): the known-key set is declared via
`[test_runner_schema] known_keys = "module:symbol"`, resolved through
the same `resolve_dotted_symbol` idiom every other T-2390 child uses --
any project can declare its own known-key set for its own
`[[test.runner]]`-shaped table without touching this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as every other T-2390 child): no `known_keys`
declared, an unresolvable dotted path, or a resolved value that is
neither a set nor a set-returning callable all report `Severity.
UNRESOLVED` -- never a silently empty (and therefore falsely "clean")
violation list.

## DUPSCHEMA001/GRAPHSCHEMA001 (T-2390 epic child, T-2437)

T-2390's finding applied to `[dup]` (`frob.gates._dup._dup_config`, 4
known keys: `enforce`, `threshold`, `region_kernel`, `native_rungs`) and
`[graph]` (`frob.excludes`, 1 known key: `exclude`) in ONE child --
unlike this epic's other children, one table each -- because each
currently carries only 1 leaf value in this repo's own frob.toml: two
genuinely disjoint readers, but each too small on its own to justify a
separate ticket. The two schema declarations and their checks stay
clearly separated (`dup_schema_gate`/`graph_schema_gate`, two distinct
rule ids) so a future split-out is mechanical if either table grows.

COMPONENT MEMBERSHIP (the T-2429 lesson, re-applied): `frob.excludes`
lives in a different strata component from `frob.gates`, so `[graph]`'s
known-key set is a plain hardcoded literal here, never an import of
`frob.excludes`'s own internals.

PORTABILITY (T-2384's doctrine): each table's known-key set is declared
via its own dotted path (`[dup_schema] known_keys` / `[graph_schema]
known_keys`), resolved through the same `resolve_dotted_symbol` idiom
every other T-2390 child uses.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED`, same posture as every other T-2390 child): for EACH table
independently, no known_keys declared, an unresolvable dotted path, or a
resolved value that is neither a set nor a set-returning callable
reports `Severity.UNRESOLVED` for that table's half -- never a silently
empty (and therefore falsely "clean") violation list.

## FLAGCOV001 (T-2397)

T-2387's own root cause is this rule's reason for existing:
`find_dropped_cli_flags` (T-2004, `frob.app._config_external`) is a
correct, already-existing detector for "a CLI flag parses but its config-
forwarding layer silently drops it before the model is constructed" --
the exact shape of both T-0749 (`--accepts`) and T-2320's three ruff
flags. It was wired to exactly ONE place, its own unit test
(`tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::
test_current_tree_has_zero_dropped_flags`), which nothing in the
`frob check` gate surface ever ran -- a gate whose only trigger is
"someone happens to run `pytest tests/unit/`" is not a control, it is a
detector nobody is required to consult. This rule is that wiring.

`frob.gates._flag_coverage.flag_coverage_gate` reads every
`[[docblocks.commands]]` entry (the SAME declared table DOC004 already
uses, T-1195) in the project's `frob.toml`. Each entry may now carry two
additional keys beyond DOC004's own `prog`/`parser`:

- `config = "module:Class"` -- the dotted path to the pydantic-shaped
  config model this command tree's CLI flags are meant to reach.
- `forwarded = "module:symbol"` -- the dotted path to either a
  `frozenset[str]` or a zero-argument callable returning one: the actual
  set of `config`'s field names THIS PROJECT'S OWN config-forwarding
  layer copies from a parsed CLI namespace.

Both are required together (declaring `config=` alone is not enough) --
see the "why `forwarded=` is mandatory" note below. For each fully
declared source, the gate resolves `parser`, calls it to build the real
`argparse.ArgumentParser`, resolves `config`, resolves `forwarded`, and
calls `find_dropped_cli_flags(parser, config_cls, forwarded=forwarded)`.
Every returned dest name is an ERROR-severity FLAGCOV001 finding.

PORTABILITY (T-2384's doctrine, applied at design time): this gate holds
no reference to `frob.__main__:_build_parser` or `frob.app.config:
AppConfig` anywhere in its own source -- both are resolved through the
declared `module:symbol` paths, the identical mechanism DOC004 already
uses (`frob.gates._docblocks_shared.resolve_dotted_symbol`, which
`frob.gates._docblocks_refs._load_parser_factory` now delegates to
rather than duplicating). Any project that already declares
`[[docblocks.commands]]` for DOC004 gets FLAGCOV001 for free by adding
`config=`/`forwarded=` to an existing entry -- no new config table.

WHY `forwarded=` IS MANDATORY, NOT OPTIONAL WITH A SENSIBLE DEFAULT.
`find_dropped_cli_flags`'s own `forwarded=None` default resolves to
`frob.app._config_external._all_forwarded_field_names()` -- frob's OWN
hardcoded field-name tuples, computed independently of whichever
`config_cls` was actually passed in. Measured directly while building
this gate: pointed at a synthetic fixture project (its own unrelated
parser/config pair), relying on that ambient default flagged 100% of the
fixture's fields as "dropped" -- every single one, a false positive
across the board, because frob's own tuples know nothing about a foreign
project's fields. Requiring every declaration (including this repo's
own, `forwarded = "frob.app._config_external:_all_forwarded_field_
names"`) to name its forwarding source explicitly closes that gap
before it could bite a second project the way the ungated default would
have.

FAIL-LOUDLY DOCTRINE (T-2391, applied via the mechanism already shipped
ahead of that epic's full type migration): every "could not measure"
state -- no `[[docblocks.commands]]` declared at all, `config=` missing,
`forwarded=` missing, a dotted path that fails to resolve, a parser
factory that raises, a `forwarded=` value that is neither a set nor a
set-returning callable -- reports `Severity.UNRESOLVED` (T-1664, the
same "the check could not determine an answer" signal REF001/REF002
already use), never a silently empty violation list. An empty result
from this gate means exactly one thing: every declared source resolved
and `find_dropped_cli_flags` found nothing -- the only state this rule
treats as a genuine pass.

## LEXCHECK001 (T-2344)

T-1662's standing principle: every check must decide from SEMANTICS --
a resolved symbol, a parsed AST node, a graph edge -- never a lexical/
textual match. T-1663's classification pass (docs/design/gate-semantics-
classification.md) found and fixed every known instance of this drive's
own lexical-decision defects (REF001/T-1665, the DEAD001/OPAQUE001 symref
gap/T-1683, and its addendum's T-2178/T-2201/T-2187/T-2188/T-2243). This
rule is T-1662's own directive #4: the meta-check that stops a NINTH
instance from landing the same way the first eight did, silently.

`frob.gates._lexical_selfcheck.lexical_selfcheck_gate` scans every git-
tracked `.py` file under `frob.gates._detector_scope.DETECTOR_PACKAGE_
ROOTS`'s AST for a FUNCTION that both:

1. Calls `re.search`/`re.match`/`re.fullmatch`/`re.findall`/`re.finditer`
   (directly on the `re` module, or on a module-level compiled pattern
   named by this codebase's own `_FOO_RE`/`_FOO_PATTERN` convention), OR
   a `.find(` call on a non-ElementTree-shaped base -- the unambiguous
   "decide something from a text pattern" signal, AND
2. Constructs at least one `Violation(...)`-shaped call with no
   `symref=` keyword

unless the `(module, function)` pair is in `_lexical_selfcheck.
_ALLOWLIST` with a stated reason. `_ALLOWLIST` mirrors the classification
doc's own "Legitimately lexical (class b)" table (SEC004, INV003/INV004's
whole-doc-file claims, TICK011's disclosure trigger, TODO001's directive-
vs-prose decision, WIRE001 case 2's rule-id-literal scan) -- a NEW entry
needs the same kind of one-line reason those already carry, never a
silent addition.

**SCOPE + TRIGGER widening (T-2466), filed from T-2457's own Done
report.** This gate used to scan `src/frob/gates/**` only and trigger on
`re.*` only. T-2457 -- a `fs.write` capability detector doing `bytes.
find` substring matching, forcing ten false capability declarations into
`design/frob.strata` -- shipped and survived review precisely because of
that double narrowness: the offending code lived in `src/frob/vet/
_capability_core.py` (wrong package, never scanned) and its trigger was
`.find(`, not `re.search` (wrong trigger, would not have fired even if
scanned). This is the [[silent-zero]] shape applied to a META-check: a
"0 findings" result read as "no detector anywhere does lexical matching"
when it actually meant "no detector in `gates/` does lexical matching via
`re.*`". Both axes are now widened:

- **Scope**: `DETECTOR_PACKAGE_ROOTS` (`src/frob/gates/_detector_scope.
  py`) replaces the old `src/frob/gates/` prefix -- `{check/, gates/,
  strata/, vet/}`, MEASURED by which packages construct `Violation(...)`
  objects at all (`arch/` measured zero such calls at T-2466 time and is
  excluded on that basis, not by assumption). This same tuple is meant to
  be PORT001's own widening's (T-2405) import too, rather than a second
  independently-hardcoded scope -- two hardcoded scopes drift apart, and
  that drift is this exact bug again.
- **Trigger**: a non-ElementTree `.find(` call joins the `re.*` trigger
  set -- the literal mechanism T-2457's bug used. `_FIND_TRIGGER_
  EXCLUDED_BASE_SUFFIXES` (`_el`/`_element`) excludes the one measured
  non-string-search `.find(` shape in the widened scope (an `Element.
  find(...)` XPath lookup in `_coverage.py`), the same disclosed,
  measured-not-guessed heuristic posture the `_RE`/`_PATTERN` suffix
  convention already uses for the `re` trigger.

Every run now logs its own scanned scope alongside its count (PORT001's
own T-2388 convention, copied exactly): `lexical_selfcheck_gate: scanned
N tracked file(s) under check/, gates/, strata/, vet/ ONLY (not
repo-wide -- see frob.gates._detector_scope.DETECTOR_PACKAGE_ROOTS), M
violation(s)` -- a count read without that line is a statement about the
scanned subset, never the whole repo.

Known v1 limitation, disclosed rather than silently accepted (same
convention as RENDER001's shadowed-`print` gap): detection is PER-
FUNCTION, so a module that splits the regex/`.find(`-decision and the
Violation construction across two different functions -- OR, as T-2457's
own real pre-fix bug did, across two different MODULES entirely -- is
not caught. T-2466 widened scope and trigger, not detection shape; that
is real, larger future work, not attempted here.

One known, reviewed (c) instance is currently OPEN, not allowlisted:
`_wire.py::_wire001_cli_dest_violations` decides WIRE001 case 3 via a raw
text-membership search over `_config_external.py`, by its own docstring's
admission -- waived in-file (`frob:waive LEXCHECK001 ... follow_up=
"T-2348"`) rather than silently allowlisted, with T-2348 tracking the
real fix (parse `_config_external.py`'s copy-loop tuples for real, or
formally accept the tradeoff as class (b)).

T-2466's own widening surfaced a SECOND, currently open backlog: five
functions in `src/frob/vet/_supplychain.py` (`_pyproject_unpinned_
violations`, `_package_json_unpinned_violations`, `_cargo_toml_unpinned_
violations`, `_python_install_artifact_violations`, `_unpinned_ci_
action_violations`) decide from `re.search`/`re.match` over TOML/JSON/
CI-workflow manifest text and build a symref-less `Violation` each --
real, previously-unscanned findings, not a detector regression. Filed as
its own follow-up (see tickets.md) rather than fixed inline (out of
T-2466's own declared scope) or silently allowlisted; `_lexical_
selfcheck`'s own test suite names this backlog explicitly rather than
masking it behind a loosened assertion.

ERROR severity: a new lexical decider anywhere under `DETECTOR_PACKAGE_
ROOTS` is exactly the failure mode this whole epic exists to prevent
from landing quietly.

## PORT001 (T-2388)

<!-- frob:describes src/frob/gates/_port_selfcheck.py::port_selfcheck_gate -->

`port_selfcheck_gate` (`frob.gates._port_selfcheck`, T-2388, child of
T-2384) flags a gate rule that hardcodes THIS project's own identity
(its package-path prefix, or its own package name used as a bare
path-segment literal) instead of resolving it from the scanned repo's
own `pyproject.toml` `[project].name` -- the same [[catalogued-is-not-
enforced]] failure mode LEXCHECK001 exists for, one layer up: a gate
that silently matches nothing (or the wrong thing) off-repo because it
was built and tested against this repo's own layout only.

Two rule ids, two dispositions, from the same AST scan:

- **PORT001-PATH**: a `"src/<pkg>/"`-shaped string constant passed to
  `.startswith(...)` -- the exact `_env_var_docs.py`/`_root_asset_dirs.
  py` bug shape T-2384 measured. BEHAVIORAL, and the class the WARN ->
  ERROR promotion bar applies to once its own burn-down (T-2389 and
  siblings) reaches zero.
- **PORT001-IDENT**: the bare package-name literal used as a whole
  `/`-delimited path segment inside a `Tuple`/`List`/f-string constant --
  ADVISORY only, permanently excluded from the promotion bar (most real
  hits are maintainer-facing message text naming this repo's own file,
  not path-building logic).

**Scope (T-2405 widening).** PORT001 originally scanned `src/frob/
gates/**` only, by explicit coordinator instruction not to widen inside
T-2388 itself. T-2405 widened it to `frob.gates._detector_scope.
DETECTOR_PACKAGE_ROOTS` (`src/frob/{check,gates,strata,vet}/`) -- the
SAME shared, MEASURED declaration LEXCHECK001 (T-2466) already reuses,
rather than a second, independently-hardcoded scope that would drift
apart from it. `_tracked_gate_files` filters with `is_detector_package_
file` instead of its old `src/frob/gates/`-only prefix; `tracked_python_
files_for_gate`'s existing default pathspec (`git ls-files -- src/frob`)
already covers every `DETECTOR_PACKAGE_ROOTS` prefix, so no new keyword
argument was needed on that shared helper. The widening is a strict
superset of the old scan (`gates/` is itself one of `DETECTOR_PACKAGE_
ROOTS`) and, measured against this repo at T-2405 time, added exactly
one new PORT001-IDENT finding (`src/frob/vet/_capability_scan.py`) and
zero new PORT001-PATH findings -- the promotion bar's own burn-down
target did not grow. `src/frob/repo_meta.py` (a deliberate `project.get(
"name") != "frob"` self-identification check) stays out of scope even
after the widening (`app/` was measured as containing zero gate-shaped
`Violation(` constructors); `gates/_pii_structural/_self_match.py`
(PORT001's own self-exclusion precedent for a PII scanner's identity
list) is allowlisted by exact relpath with a stated reason, same
convention as LEXCHECK001's `_ALLOWLIST`.

Every run logs its own scanned scope alongside its count, unconditionally
(`port_selfcheck_gate: scanned N tracked file(s) under DETECTOR_PACKAGE_
ROOTS (...) ONLY (not repo-wide ...), M violation(s)`) -- a count quoted
without that line is a statement about the scanned subset, never the
whole repo (the same silent-zero-denominator lesson T-2391 exists for).

UNRESOLVED (not a clean pass) if the scanned repo's own `pyproject.toml`
`[project].name` cannot be read -- PORT001 has no denominator to search
source text for in that case, and reports that explicitly rather than an
empty (clean-looking) violation list.

## GATERULE001 (T-2448)

<!-- frob:describes src/frob/gates/_rule_id_scan.py::gate_rule_registry_violations -->
<!-- frob:describes src/frob/gates/_rule_id_scan.py::scan_emitted_rule_ids -->

`find_unregistered_rule_ids` (T-1937, `frob.gates._rule_id_scan`) scans
every `.py` file under `root/src/` for a rule-id-shaped string literal
constructed in code and reports any that are neither in the live
`_KNOWN_GATE_RULES` registry (`frob.gates._waive`) nor in `RETIRED_RULE_
IDS`. Before T-2448 that scanner only ever ran ticket-scoped, at one
ticket's own close/land preflight (`frob.tickets._new_gate_rule_
acceptance.unregistered_rule_ids_in_scope`, T-1956's deliberate
narrowing) -- correct for THAT gate (a pre-existing gap a ticket never
touched must not block an unrelated close), but it left a real blind
spot: a rule id constructed in a branch nobody is currently landing
stayed invisible until someone eventually tried. T-2388's bare `PORT001`
and T-2447's `CLAUDE001` were both found only by manually re-running the
scanner against every live worktree by hand, not by any standing check.

`gate_rule_registry_violations` runs the same scan repo-wide as a
STANDING `frob check` gate, `GATERULE001`, closing that gap: any
unregistered rule id anywhere in the tree is now an ERROR every `frob
check` reports, not only at the moment its own ticket tries to close.

T-2391 fail-loudly: the scan's own coverage assumption is a top-level
`root/src/` layout (T-2384's own disclosed, out-of-scope-to-remove
hardcoding). When `src/` is absent, or the scan itself crashes (an
unreadable file, an encoding error), `GATERULE001` reports
`Severity.UNRESOLVED` naming exactly what could not be scanned, instead
of letting a silent "0 unregistered" read as a false-clean pass.

## Baseline lock producer staleness (T-2999)

`frob.gates._lock_producer` distinguishes a DELIBERATELY frozen committed
baseline lock (`frob-coverage.lock.json`, `frob-ratchet.lock.json`,
`frob-deprecated-baseline.lock.json`) from one whose stamping producer has
quietly ABANDONED it -- two states that raw file age alone cannot tell
apart. `producer_status(root, lock)` measures, against the real git
history, how many commits have touched the lock's own `code_glob` since
its last stamp (`code_commits_since`); at or above
`ABANDONED_CODE_COMMIT_THRESHOLD` with no pin, the verdict is `ABANDONED`.
A lock MAY carry a top-level `{"pin": {"reason": "...", "ticket": "T-####"}}`
object -- a positive declaration that staleness is deliberate, which
always wins over the commit-count signal (`PINNED`).

`all_producer_statuses(root)` runs this for every lock in `KNOWN_LOCKS`
and is what `frob status`'s new "baseline locks" section (see
docs/modules/cli.md#frob-status-t-2911) and `frob check`'s TEST012 gate
both read. TEST012's third finding (`_test012_producer_abandoned`,
`frob.gates.__init__`) escalates an `ABANDONED` coverage-lock producer to
ERROR severity, deliberately separate from its two existing WARN
content-drift checks -- a lock's CONTENT can match a fresh run by
coincidence even while its PRODUCER has stopped running, so this is a
distinct signal, not a severity bump on the same one.

<!-- frob:describes src/frob/gates/_lock_producer.py::ABANDONED_CODE_COMMIT_THRESHOLD -->
<!-- frob:describes src/frob/gates/_lock_producer.py::LockPin -->
<!-- frob:describes src/frob/gates/_lock_producer.py::TrackedLock -->
<!-- frob:describes src/frob/gates/_lock_producer.py::KNOWN_LOCKS -->
<!-- frob:describes src/frob/gates/_lock_producer.py::LockProducerStatus -->
<!-- frob:describes src/frob/gates/_lock_producer.py::producer_status -->
<!-- frob:describes src/frob/gates/_lock_producer.py::all_producer_statuses -->

## Public API

<!-- frob:describes src/frob/gates/_suppress.py::SuppressionDialect -->
<!-- frob:describes src/frob/gates/_suppress.py::suppression_dialects -->
<!-- frob:describes src/frob/gates/_waive.py::SCOPED_RUN_FLAKY_RULE_IDS -->
<!-- frob:describes src/frob/gates/__init__.py::run_gates -->
<!-- frob:describes src/frob/gates/__init__.py::evidence_covers_scope -->
<!-- frob:describes src/frob/gates/__init__.py::drift_gate -->
<!-- frob:describes src/frob/gates/__init__.py::affect_drift_gate -->
<!-- frob:describes src/frob/gates/__init__.py::coverage_gate -->
<!-- frob:describes src/frob/gates/__init__.py::scope_gate -->
<!-- frob:describes src/frob/gates/__init__.py::prework_gate -->
<!-- frob:describes src/frob/gates/_inv.py::invariant_gate -->
<!-- frob:describes src/frob/gates/__init__.py::test_gate -->
<!-- frob:describes src/frob/gates/_coverage.py::stamp_coverage -->
<!-- frob:describes src/frob/gates/_coverage.py::load_coverage -->
<!-- frob:describes src/frob/gates/_coverage.py::exclude_filtered_coverage -->
<!-- frob:describes src/frob/gates/_waive_lease.py::active_ticket -->
<!-- frob:describes src/frob/gates/_prework.py::record_prework -->
<!-- frob:describes src/frob/gates/_prework.py::sweep_ticket -->
<!-- frob:describes src/frob/policy/__init__.py::load_policy -->
<!-- frob:describes src/frob/policy/__init__.py::policy_gate -->
<!-- frob:describes src/frob/gates/invariants.py::load_invariants -->
<!-- frob:describes src/frob/gates/_coverage.py::load_stamp -->
<!-- frob:describes src/frob/gates/_coverage.py::load_lock_audit_log -->
<!-- frob:describes src/frob/gates/_prework.py::load_prework -->
<!-- frob:describes src/frob/gates/__init__.py::scope_digest -->
<!-- frob:describes src/frob/gates/_decisions_compliance.py::decisions_gate -->
<!-- frob:describes src/frob/gates/_dup.py::dup_gate -->
<!-- frob:describes src/frob/gates/__init__.py::release_gate -->
<!-- frob:describes src/frob/gates/_fuzz.py::fuzz_gate -->
<!-- frob:describes src/frob/gates/_doclink_docanchor.py::doclink_gate -->
<!-- frob:describes src/frob/gates/_doclink_docanchor.py::docanchor_gate -->
<!-- frob:describes src/frob/gates/__init__.py::run_gates -->
<!-- frob:describes src/frob/gates/_baseline.py::stamp_baseline -->
<!-- frob:describes src/frob/gates/_baseline.py::load_baseline -->
<!-- frob:describes src/frob/gates/_baseline.py::is_baseline_stale -->
<!-- frob:describes src/frob/gates/_baseline.py::delta_violations -->
<!-- frob:describes src/frob/gates/_baseline.py::violation_fingerprint -->
<!-- frob:describes src/frob/gates/_secrets.py::secrets_gate -->
<!-- frob:describes src/frob/security/_redact.py::_redact -->
<!-- frob:describes src/frob/gates/_secrets.py::fake_marker_staleness_gate -->

`_redact` (never returns the matched token itself, only its
`display_prefix` plus a fixed-length mask) moved from `frob.gates.
_secrets` into `frob.security._redact` (T-1318): `frob.app.telemetry.
redact_command` needed it on every CLI invocation regardless of
subcommand, and importing it through `frob.gates._secrets` pulled in the
whole `frob.gates` package's import graph just to redact one telemetry
string. `frob.gates._secrets` re-exports `_redact` unchanged for its own
`secrets_gate` use, so no gate-side caller needed to change.
<!-- frob:describes src/frob/gates/_pii_structural/__init__.py::pii_structural_gate -->
<!-- frob:describes src/frob/gates/_pii_structural/_signatures.py::_FieldSignature -->
<!-- frob:describes src/frob/gates/_pii_structural/_python_fields.py::_scan_python_fields -->
<!-- frob:describes src/frob/gates/_pii_structural/_env_access.py::_scan_python_env_access -->
<!-- frob:describes src/frob/gates/_waive.py::known_gate_rule_ids -->
<!-- frob:describes src/frob/gates/_gate_cache.py::TrackedSnapshot -->
<!-- frob:describes src/frob/gates/_gate_cache.py::evaluate_cacheable_gate -->
<!-- frob:describes src/frob/gates/_gate_cache.py::invalidate -->

### Per-gate result cache (T-0602)

`run_gates(cfg, use_cache=True)` opts the closed `_CACHEABLE_GATES`
allowlist (`drift`, `test`, `policy`, `parse_failures`, `debt`,
`lang_conformance`, `affect_drift`) into
`frob.gates._gate_cache.evaluate_cacheable_gate`: a gate's prior result is
served from `.frob/gate-cache.db` instead of re-running it, whenever every
file the gate is observed to have read still hashes the same, the tree's
overall tracked-file membership is unchanged, and any non-file scalar
input the gate also depends on is unchanged. Full design, the
membership-guard soundness argument, and the cold-diff oracle property
test live in `frob.gates._gate_cache`'s module docstring and
`docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602`.
`deprecated` is deliberately NOT on this allowlist even though it looks
snapshot-shaped: T-0639 (landed on `main` after T-0602 started) gave it a
`root: Path` argument for DEPR005's baseline-lock/live-reference-set
resolution, filesystem-dependent beyond what `TrackedSnapshot` observes --
excluded per this section's own soundness rule the moment that landed,
rather than cached unsoundly.

**T-1346: `frob check` now actually uses this cache.** `run_gates`'s
`use_cache` parameter existed from T-0602 but no `frob check` call site
ever passed `use_cache=True` -- the whole mechanism sat built and unused
except for `frob.serve._tools.frob_check_delta`. `frob.check._python.
_run_gates` (every `run_check`/`run_check_cpp`/`run_check_rust`/
`run_check_ts` call site funnels through it) now calls `run_gates(cfg,
use_cache=_gate_cache_enabled(no_cache))`, ON by default, so a real
`frob check` invocation with an unchanged file set serves the
`_CACHEABLE_GATES` allowlist from cache instead of recomputing it. Set
`FROB_NO_GATE_CACHE=1` (any non-empty value) to force a full recompute for
one invocation -- a first-class `--no-cache` CLI flag needs
`_cli_parsers/_check.py`/`app/config.py`/`app/check_runner.py`, which sit
outside `src/frob/gates/**`/`src/frob/check/**` and were left as a
follow-up (T-1445, renumbered at land -- see T-1346's Done
report for the real id). Cache HIT/MISS per gate logs at INFO
(`frob.gates._gate_cache`'s own lines), visible under `frob check -v`,
so a suspect cached result is diagnosable without a dedicated flag.

**T-1436: a caller can cap the gate process pool.** `frob.gates.
_run_gates_bounded(cfg, *, max_process_workers=None)` is `run_gates`
with an explicit ceiling on the process-pool width, threaded through to
`_open_process_pool`. Its one real consumer is the serve daemon
(`frob.serve._tools`, `_DAEMON_GATE_MAX_WORKERS = 2` -- see
docs/modules/serve.md#daemon-gate-runs-cap-their-process-pool-t-1436):
a background daemon must not out-compete the foreground work it serves.
`run_gates` itself is now a one-line uncapped wrapper; its public
signature and behavior are unchanged.

**T-0806: `FROB_WORKER_STDOUT_LOG_LEVEL` clamps a process-pool gate
worker's own default-DEBUG logging before it can leak onto stdout.**
`_run_process_gate` (a `ProcessPoolExecutor` entry point, picklable by
`__module__`/`__qualname__`) re-runs each worker's module import chain on
first use -- those fresh imports never see the PARENT process's in-memory
`quiet_stdout_logs`/`stdout_log_level` clamp, since that only mutates the
parent's own handler objects. Left unclamped, a worker's default-DEBUG
per-file parse logging writes straight onto the stdout file descriptor it
inherits from the parent, corrupting a quiet/`--json` `frob check` run's
stdout payload. The pool owner stamps `_WORKER_STDOUT_LOG_LEVEL_ENV`
(`"FROB_WORKER_STDOUT_LOG_LEVEL"`) before pool construction; every spawned
worker reads it back on its own `_init()` re-run and clamps its own
logging to match. Set only by frob itself, never by a user or agent
directly.

**T-1454: side-channel inputs (`frob.lock`, coverage, rules, the ticket
queue, ...) now join the cache key, closing a real stale-DRIFT001 bug.**
`TrackedSnapshot` only observes reads through the `GraphSnapshot` surface
(`.symbols`/`.edges`/`.file_hashes`/`.malformed`/`.parse_failures`) -- it
was blind to a cacheable gate's OTHER positional arguments, e.g.
`drift_gate(snap, st.lock)`'s `st.lock` (the loaded `frob.lock`). A `frob
ack` rewrites `frob.lock` without touching any tracked SOURCE file's
digest, so neither the membership key nor the touched-file key changed --
the cache kept serving the pre-ack DRIFT001 finding indefinitely, workable
around only via `FROB_NO_GATE_CACHE=1` (section 6 of
`docs/guides/agent-playbook.md` still documents that workaround as a
general "cached result looks impossibly stale" escape hatch, useful for
any future gap of this same shape). `frob.gates._gate_cache.
model_side_channel_key(*models)` fingerprints one or more pydantic
`BaseModel` side inputs via `model_dump_json`; every `_CACHEABLE_GATES`
member's `_cacheable_gate_call` branch now folds its OWN side input(s)
into the `extra` tuple it returns (`drift` -> `st.lock`, `test` ->
`st.systems`/`st.coverage`/`st.tests`/`st.test_policy`, `policy` ->
`st.rules`/`st.diff`, `debt` -> `st.queue` alongside the existing
`current_date`/`current_version` scalars, `affect_drift` -> `st.diff`) --
`parse_failures` and `lang_conformance` have no side input beyond (or at
all, for `lang_conformance`) the snapshot and correctly stay keyed on
`()`. A side-channel-only edit now forces a miss exactly like a
tracked-file edit already did; `tests/test_gate_cache.py::
TestRunGatesUseCache.test_ack_invalidates_cached_drift001` is the
regression oracle for the reported DRIFT001-across-ack case specifically.

**What this does NOT yet cover.** `_CACHEABLE_GATES` only spans the
thread-pool gates that read `st.snapshot` alone. The gates measured as the
dominant CPU cost of a full `frob check` -- `sys`, `perf`, `arch`,
`clones`/`dup`, `pii_structural`, `secrets`, `coverage`, `dead_symbols`,
`deprecated`, `opaque` -- all run as `_ProcessJob`s that take `st.root`
directly (an unbounded filesystem walk `TrackedSnapshot` cannot observe),
so none of them are eligible for this cache as designed. Extending
caching to that set is real, separate design work (a root-content-hash or
similar invalidation key, not just a touched-file set) and is the natural
next leverage point, tracked as a follow-up rather than attempted here.

- `exclude_filtered_coverage` -- re-filters a `CoverageData` against
  `[graph] exclude` (T-0997); `stamp_coverage` calls it before writing
  `frob-coverage.lock.json` so the committed lock and the TEST012 gate's
  live comparison agree about what counts as a module (e.g. scaffold
  `.j2` templates), instead of the lock permanently drifting.
- `load_coverage`'s T-1401 unjoined-module enumeration -- whenever
  `module_join_fraction` falls below `_UNJOINED_LOG_THRESHOLD` (0.95),
  the specific known `.py` modules that did NOT join against
  `coverage.xml` (`_unjoined_python_modules`) are enumerated BY NAME in a
  single `load_coverage: ... module_join_fraction=... below ... known .py
  module(s) did not join ...` WARNING log line, not just reported as a
  bare fraction -- a percentage alone tells a reader THAT something is
  missing, not WHICH modules, which let a stale/carried-over lock value
  go unnoticed until directly diffed against the raw xml.
- `stamp_coverage`'s T-1180 deflation floor -- when called with a
  `snapshot`, refuses to write `.frob/coverage-stamp`/`frob-coverage.
  lock.json` at all (`Err(GateError.CoverageDeflated)`) whenever the
  filtered `CoverageData.module_join_fraction` falls below the same 0.5
  floor TEST017 (T-1489; formerly the deflation half of TEST011, see
  "TEST011/TEST017 (T-0464/T-1489)" below) blocks on at check time
  (`_DEFLATION_FLOOR`, `frob.gates._coverage`) -- a stamp-time refusal on
  top of the check-time gate, since a run that silently dropped
  subprocess coverage used to stamp clean and only get flagged after the
  fact.
- `stamp_coverage`'s T-1236 canary-module guard -- `module_join_fraction`
  alone cannot catch every deflation shape: a module that never got
  traced still JOINS against `coverage.xml`, just at 0% line-rate, so the
  aggregate ratio can sit near 1.0 even while a whole class of process
  (subprocess, daemon, CLI-entry) went unmeasured. `_canary_deflation`
  (`frob.gates._coverage`) checks a small named list of modules known to
  be exercised by every healthy full run (`_CANARY_MODULES`, currently
  `src/frob/__main__.py` -- invoked by every system test) and refuses the
  stamp (`Err(GateError.CoverageDeflated)`) if any present canary reads
  exactly 0.0%, independent of what the join fraction reports. Skipped
  when a canary is simply absent from a run's `module_line` (a tiny
  fixture snapshot that never declared it) -- only a present-but-zero
  reading trips it.
- `write_coverage_lock`'s T-1363 downward-ratchet guard -- unless called
  with `allow_decrease=True`, a module already present in the committed
  `frob-coverage.lock.json` can only move up: a drop of more than
  `_LOCK_TOLERANCE` points against the prior committed value is clamped
  back to that prior value rather than written. Fixes a real incident
  (2026-07-31): a failed/partial `make coverage` run rewrote committed
  floors downward (e.g. `src/frob/app/__init__.py` 76.5% -> 16.2%), which
  would have permanently lowered the repo's quality floor through a file
  nobody reviews had it been committed. `stamp_coverage` always calls this
  with the default (`allow_decrease=False`); a deliberate re-baseline
  needs the explicit override, never a bare `make coverage` run.
- `write_coverage_lock`'s T-1401 zero-hit ratchet carve-out -- the T-1363
  clamp above has one unconditional exception: a module whose freshly
  measured value is EXACTLY `0.0` is never clamped back to a stale
  committed value, even with `allow_decrease=False`. A real incident
  (`src/frob/__main__.py`: lock said 81.2%, `coverage.xml` recorded 0 of
  133 lines hit from a clean, crash-free `make coverage` run) showed a
  genuine zero is the most confident, unambiguous signal this module
  produces -- clamping it back up to a stale number is exactly the
  silent-divergence failure mode T-1363 itself exists to prevent, just
  aimed at the opposite case. Non-zero drops still clamp exactly as
  before; only an exact zero is exempt.
- `write_coverage_lock`'s T-1375 durable attribution trail -- a real
  incident found `frob-coverage.lock.json` modified with no matching
  `write_coverage_lock: locked N module(s)` line in either of two
  `make coverage` runs' logs; log output alone is not durable enough to
  attribute a write after the fact (it only survives in whatever
  terminal/session captured it). Every successful `write_coverage_lock`
  call now also appends one JSON line to the per-worktree, gitignored
  `.frob/coverage-lock-audit.log` (`written_at`, `pid`, `source_sha`,
  `module_count`). `load_lock_audit_log(root)` reads that trail back
  (oldest first, `()` if missing/unreadable/malformed); comparing a
  committed lock's `source_sha` against the trail's entries answers
  "was this write attributable to a logged `write_coverage_lock` call in
  THIS worktree's own history" durably, independent of any one session's
  scrollback. A write failure appending to the audit log is logged but
  never fails the lock write itself -- the trail is a diagnostic aid, not
  a hard requirement of stamping.
- `make coverage`'s T-1363 fix -- the `coverage:` recipe now writes the
  combined `coverage xml` to a scratch path (`.frob/coverage.partial.xml`)
  first and only promotes it to the real `coverage.xml` (and only calls
  `frob check --stamp-coverage`, the sole writer of `.frob/coverage-stamp`
  and `frob-coverage.lock.json`) when the pytest run's own exit status was
  0. A nonzero exit (even after the recipe's own crash-recovery reruns)
  leaves the previous `coverage.xml`, `.frob/coverage-stamp`, and
  `frob-coverage.lock.json` completely untouched, printing an explicit
  ERROR line naming the skip instead of silently promoting a failed run's
  data -- the exact defect a real 2026-07-31 incident hit twice in one day
  (a failing suite still overwrote a merely-wrong stamp with a near-empty
  one, driving four cross-agent validation symbols to a uniform, false
  0.0%).
- T-1364 (considered, not built): an explicit `"partial": true` marker on
  `.frob/coverage-stamp`, plus TEST005/TEST006 wording distinguishing
  "stamp missing" from "stamp exists but was computed from a partial
  run", for the case where a partial run's data is judged worth keeping
  over nothing. T-1363 chose "keep nothing" (never promote a failed/
  partial run's data at all) over "keep and mark partial" for its first
  cut, and this is still sufficient: as long as some earlier good stamp
  exists, a failed run leaves it untouched, and TEST006's
  `_test006_missing` already discloses a genuinely-missing stamp as a
  real violation rather than a false clean -- including the bootstrap
  case (no stamp has ever existed and the very first `make coverage` run
  also fails), which already reads as "no data," the acceptance
  criterion T-1363/T-1364 actually cared about. Revisit this decision
  only if a future incident shows losing an entire partial run's signal
  (rather than falling back to the prior good stamp) is itself the worse
  outcome -- e.g. a long stretch where every `make coverage` attempt
  fails and TEST005/006 keep reporting against an increasingly stale
  prior stamp with no partial-data signal ever surfaced. No such
  incident has occurred as of this note.
- T-1265 (CHK-THEME-GITIGNORED-TRUST successor -- a locally-green coverage
  check proved nothing to CI or a reviewer): `.frob/coverage-stamp` and
  `.frob/baseline` are gitignored (`.gitignore:21,:72`) and never restored
  in a fresh `.github/workflows/ci.yml` checkout, so TEST005/006 are
  structurally inert there -- CI has no fresh coverage measurement to
  check them against, and cannot fail a job on a signal it never had.
  This is disclosed, not silently accepted: the self-gate step's own
  `|| echo "::warning::..."` swallow (which used to hide EVERY finding,
  ERROR-tier gate violations included, behind a printed line nobody was
  forced to read) is gone, so a real ERROR-tier finding now fails the
  job outright; and `frob-coverage.lock.json` (T-0545) -- the one
  coverage-derived channel that IS committed and travels with the diff --
  gets its own dedicated CI step that greps the `--json` gate report for
  TEST012 and fails hard on any hit, since TEST012 is WARN-severity by
  design and would not otherwise move the self-gate step's exit code.
  Running a fresh `make coverage` inside CI (so TEST005/006 become live
  there too) was considered and deferred -- it adds real wall-clock and
  flake surface to every PR for a floor the committed lock file already
  covers at the module-aggregate level; revisit if `frob-coverage.
  lock.json` alone proves too coarse in practice.
- `load_stamp` -- the raw `.frob/coverage-stamp` document, or `None` if
  never stamped/unreadable; TEST006 compares it against live file hashes.
- `load_prework` -- the recorded pre-work sweep for a ticket, or `None` if
  `frob ticket start` never ran one; PRE001 compares it to a fresh digest.
- `scope_digest` -- the one canonical sha256 over a scope glob's matched
  file hashes, shared by `frob ticket start` and `prework_gate` so PRE001
  can never see two independently-computed digests drift apart.
- `decisions_gate` -- DEC001/DEC002 over `decisions/` records and their
  code anchors; a no-op when no `decisions/` directory exists.
- `dup_gate` -- DUP001/DUP002: flags a diff that introduces a clone of an
  existing symbol; opt-in via `[dup].enforce` in `frob.toml`. T-0399: if
  `enforce` is true but the `frob-core` native extension is unavailable,
  emits DUP003 (ERROR) instead of silently skipping -- a requested-but-
  unavailable control fails closed, not open. T-0974: also reads
  `[dup].native_rungs` (default false) and threads it into the
  `DupConfig` it builds, independently of `enforce` -- when false, the
  gate's `find_clones` call only runs R1/R2 (cheap, pure-Python); R3/R4/R5
  (native-call-per-symbol, the cost driver a whole-snapshot cold run pays)
  stay off until a repo opts in. See `docs/modules/dup.md`'s
  "[dup].native_rungs" section for the measured cost and
  `frob.dup.DupConfig.native_rungs_enabled`'s docstring for why the class
  default differs from the gate's toml default.
- `release_gate` -- REL001: the public-API change since the last release
  stamp demands a version bump the declared version does not cover.
- `fuzz_gate` -- FUZZ001..003 over the `[fuzz]` policy; opt-in via
  `[fuzz].enforce`, default off.
- `doclink_gate` -- DOC001: a doc file nothing links to (no describes
  anchor, no `frob:doc` edge, unreachable from the doc roots) is an error.
- `sys_gate` -- SYS001/SYS002/SYS003/SYS004 (T-0080): joins `frob:channel`/
  `frob:boundary`/`frob:secret` code directives and tier-2 code binding
  against a `.strata` design model; opt-in via a `design/` (or
  `[strata].design_dir`) directory of `.strata` files existing, same
  posture as `decisions_gate`. See docs/strata/surface.md#directives-t-0080.
- `docanchor_gate` -- DOC002: a `frob:doc` target whose anchor doesn't
  resolve (missing `#anchor`, missing file, or `<slug>` matches neither a
  heading slug nor an explicit `<a id>`) is an error.
- `secrets_gate` -- SEC001/SEC002/SEC003 (T-0157): scans every git-tracked
  file (never untracked/`.env`-skipped -- a tracked `.env` IS the SEC002
  finding) for real-looking provider credentials via a per-provider regex
  table; default-on. `redact` is the one function allowed to turn a matched
  token into printable output (`<provider prefix>... (<N> chars)`, never
  the token itself). A site is exempted by a placeholder shape inside the
  token (`XXXX`/`****` runs, or the words fake/changeme/example/placeholder)
  or by a `frob:secret-fake` marker comment on the same or preceding line
  -- deliberately NOT the pre-existing `frob:secret <construct-id>`
  directive, which already binds code to a strata design's Secret-clearance
  node id; see `frob.gates._secrets`'s module docstring for the full
  reasoning. `SEC003` (live Stripe secret keys, PEM private-key headers) is
  in `_UNWAIVABLE_RULES` alongside `TEST008`; `SEC001`/`SEC002` stay
  waivable with a written reason like every other rule.
- `fake_marker_staleness_gate` -- WAIVE004 (T-0978): zero-findings
  staleness for the `frob:secret-fake reason="..."` marker family, at the
  GATE level rather than the graph-edge level -- `frob:secret-fake` stays
  a reserved, DSL-invisible marker verb (T-0157,
  `frob.graph.dsl._RESERVED_MARKER_VERBS`) that never becomes a real
  `frob:waive` `Edge`, so `frob.gates._waive004_violations`'s graph-edge
  detector cannot see it. This gate re-scans every tracked file's REAL,
  reason-bearing marker sites (excluding prose mentions and a documented
  set of test files that construct marker text as a multi-line Python
  string literal, defeating this check's physical-line site mapping --
  see `_STALENESS_MULTILINE_LITERAL_EXCLUDED_FILES`'s comment) and emits a
  `WAIVE004`-rule `Violation` for any whose site trips zero real SEC00x
  patterns AND does not look email-shaped (`_plausibly_still_needed`, a
  conservative substring stand-in for PII011's real structural check,
  since this marker family is shared between `secrets_gate` and
  `pii_structural_gate`'s PII011). `run_gates` folds its output into the
  same `all_violations` set the graph-edge WAIVE004 pass feeds, so both
  sources present as one `WAIVE004` rule to a caller.
- `run_gates` -- the single entry point: loads all state once, then runs
  the selected gates in parallel and merges/severity-overrides the result.
- `known_gate_rule_ids` -- every rule id a gate can emit (T-0499), the
  live set strata's `caught_by` verification (THREAT006, COMPLIANCE004)
  needs to recognize a rule-id-shaped reference (e.g. `SEC001`) instead of
  treating it as unresolved fail-closed; threaded into
  `evaluate_exhaustiveness`/`evaluate_compliance` from `frob sys audit`'s
  `_evaluate_audit` (`frob.app.sys_runner`).

### Structural PII secrets detection T-0207

`frob.gates._pii_structural` -- `pii_structural_gate` (gate name
`pii_structural`, default-on, WARN severity, dial via `[gates.severity]`).
Extends `frob.strata._pii` (T-0154, declaration/join layer) and
`frob.gates._secrets` (T-0157, tracked-file token scan) with a THIRD,
previously-missing layer: structural observation of actual Python data
structures and env-var access sites, drawn from
`docs/design/secrets-pii-corpus.md`'s field-name/type keyword catalog.

- **PII010**: a pydantic `BaseModel` / `@dataclass` / `TypedDict` /
  `NamedTuple` / attrs class field whose NAME (`_`-tokenized match) or TYPE
  ANNOTATION (`EmailStr`, `SecretStr`) matches an entry in
  `FieldSignature`/`FIELD_SIGNATURES` fires -- deny-by-default, waivable via
  `frob:waive PII010 reason="..."`.
- **SEC110**: an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)`
  call/subscript site fires -- an unmapped secret-source observation,
  waivable via `frob:waive SEC110 reason="..."`.
- **T-0973**: SEC110 was promoted from WARN to ERROR in `[gates.severity]`
  (`frob.toml`) after every one of the 16 unwaived findings named in
  T-0399's gates-quality audit was disposed of -- 13 got a reasoned
  `frob:waive SEC110 reason="..."` (behavior flags, internal reentrancy/
  worker-log markers, cache paths, and test-only synthetic vars, none of
  them a real secret), and 3 more (`src/frob/gates/__init__.py`'s
  `_rel001_bump_suppressed_under_agent` and its worker log-level markers)
  were folded into the same fix once T-0973's scope was extended to that
  file. `tests/test_gates.py::TestSeverityOverrides.
  test_sec110_promoted_to_error_gates_a_real_repo_toml` is the before-
  fails/after-passes fixture proving the promotion actually gates.
- Both rules are file-scoped (same waiver-matching mode as SEC001-003:
  `violation.symref` is `None`, so a waiver anywhere in the file suppresses
  every hit in it).
- Self-match exclusion (T-0201 lesson): `_pii_structural/`'s own module
  paths are hardcoded-excluded from the scan (T-1076 split the module into
  a package -- every sibling file, not just one), so `FIELD_SIGNATURES`'s
  own keyword string literals can never be misread as a scanned field.
- **PII010 also covers DB/DDL schema scanning (T-0348, family 2)**:
  sqlalchemy ORM declarative `name = Column(...)` assignments and alembic-
  style positional `Column("name", ...)` calls (`_scan_orm_columns`), plus
  raw-SQL `CREATE TABLE(...)` column lists embedded in tracked-`.py`
  string literals (`_scan_ddl_strings`) -- both matched against the same
  `FIELD_SIGNATURES` table, no second registry. Schema headers are the
  highest-value PII surface per the umbrella ticket body.
- **PII011 (T-0349, family 4): structural email-shape value detection**:
  every string-literal constant in a tracked `.py` file, checked via
  `email.utils.parseaddr` (an RFC 822 header parser) plus a plain
  character-set validation of the parsed local/domain parts
  (`_is_email_shaped`) -- explicitly NOT a regex, per the ticket body's
  mandate. Escaped by a `frob:secret-fake` comment on the literal's own
  line or the line directly above it, the same T-0157 marker convention
  the secrets scanner uses (a fixture literal discharges both gates with
  one comment).
- **PII012 (T-0350, family 5): keyword-sweep at suggestion severity**:
  every plain identifier (variable/parameter/function name) and every
  `#`-comment word token matching a `FIELD_SIGNATURES` name-kind keyword,
  excluding sites PII010 already reports on. Fires at WARN severity only
  -- "no hard fail on names alone" per the ticket body -- distinct from
  PII010's deny-by-default posture over an actual declared data-structure
  field.
- **std.pii/std.secrets declaration join (T-0351)**: `_load_declared_
  surface` loads every `.strata` design file under the repo's design
  directory (the same loader `sys_gate` already uses, `load_design_ids`),
  tier-2 code-binds each file to its owning `Node` (`bind_code`, also
  reused from `sys_gate`'s SYS003), and joins that node's `carries` PII
  tags (`frob.strata._pii.node_pii_tags`) and `clearance == "Secret"`
  status (the same best-effort std.secrets proxy
  `_design_load.DesignIds.secrets` already documents) into a
  `_DeclaredSurface`. A PII010 finding whose file is already code-bound to
  a node that `carries` the SAME category is discharged outright; a
  SEC110 finding whose file is code-bound to a Secret-clearance node is
  likewise discharged. A repo with no design directory (or no matching
  binding) degrades to the empty surface -- every finding still fires
  exactly as before this ticket, waiver-only. PII011 (bare string-literal
  values have no "owning field" to carry a category against) and PII012
  (already suggestion-severity, not deny-by-default) are NOT joined.
- **Deliberately not built this pass** (see `_pii_structural/__init__.py`'s
  module docstring and this ticket's Done report): non-Python language
  equivalents and non-Python DDL sources (`.sql` migration files). Filed
  as follow-on tickets, not silently dropped.
- **TypeScript/Rust field-shape and env-access equivalents (T-0352)**:
  extends the SAME PII010/SEC110 rule ids (not new rule ids) to the other
  two `frob.lang`-supported grammars, via `frob.lang.raw_tree` (the same
  single tree-sitter grammar-load dispatch `frob.arch`/`frob.dup._legacy`
  already share -- no second parser stood up):
  - PII010 over TS `interface_declaration` bodies, `type_alias_
    declaration`s whose value is an `object_type`, and `class_declaration`
    bodies (`_scan_ts_fields`), and Rust `struct_item` named fields
    (`_scan_rust_fields`) -- reusing `_field_name_hit`/`FIELD_SIGNATURES`
    (name-kind entries) unchanged.
  - SEC110 over TS `process.env.NAME`/`process.env["NAME"]` and
    `import.meta.env.NAME`/`import.meta.env["NAME"]` (`_scan_ts_env_
    access`), and Rust `std::env::var(...)`/`env::var(...)`/`std::env::
    var_os(...)` (`_scan_rust_env_access`) -- reusing `_ENV_VAR_ALLOWLIST`
    unchanged.
  - NO-FAIL-SILENT: a field shape that cannot be statically named -- a TS
    index signature (`[key: string]: T`) or computed property name
    (`[expr]: T`) -- fires PII010 as an "unresolvable field shape" finding
    demanding manual review, rather than being silently skipped. A
    dynamic (non-literal) env-access subscript key (`process.env
    [someDynamicKey]`) likewise still fires SEC110, mirroring
    `_scan_python_env_access`'s existing posture for `os.environ
    [dynamic_key]`.
  - A Rust TUPLE struct (`Point(i32, i32)`) has no source field names at
    all and is out of scope for name-based matching (no name to check
    against `FIELD_SIGNATURES` in the first place -- not a false negative
    on a real PII field, just nothing nameable to test).
  - The T-0351 declared-surface join (`_load_declared_surface`) applies
    identically -- it is keyed on rel_path alone, language-agnostic.
- **Structural PII type-kind for TS/Rust nominal PII-shaped types
  (T-0762)**: T-0352 left TYPE-kind matching (`EmailStr`/`SecretStr`)
  Python-only, an honest gap; T-0762 closes it by extending
  `FIELD_SIGNATURES`'s single-source registry with a `langs` field
  (`_FieldSignature.langs`, default all three languages for NAME-kind
  entries; explicit per-entry scope for TYPE-kind entries, since a type
  name like `SecretStr` or `SecretString` only exists in one language's
  ecosystem):
  - TS: a field typed as a known secret-wrapper type (`Secret`,
    `SecretString`, `SensitiveString`) or a branded/nominal email type
    (`Email`, `EmailAddress`) fires PII010 via `_ts_type_hit`, even when
    the field's own NAME carries no name-kind keyword. A plain
    `string`-typed field does not fire on type alone.
  - Rust: a field typed `secrecy::Secret<...>`/`secrecy::SecretString`
    (the `secrecy` crate's wrapper types named in the ticket body) or a
    conventionally-named `Email` newtype PII wrapper fires PII010 via
    `_rust_type_hit`. A plain `String`-typed field does not fire on type
    alone.
  - Both walk the type-annotation/type subtree for bare type-identifier
    names (`_type_identifier_names`, the TS/Rust analogue of
    `_annotation_names`'s Python AST walk) so a generic-wrapped or
    scoped-path type (`secrecy::SecretString`, `Secret<String>`) still
    surfaces its inner type name -- one shared walker for both grammars,
    funneled through one shared `_type_hit(names, lang)` lookup so the
    `langs` scoping logic lives in exactly one place.
  - Resolving a field/binding TYPE to an imported type's actual
    definition (distinguishing an unrelated same-named local `Email` type
    from a real PII-shaped one, or reading an import alias) is NOT
    attempted -- this is a bare type-identifier NAME match, the same
    posture `_field_type_hit` already has for Python's `EmailStr`/
    `SecretStr`. Full import-resolution-backed type-kind matching is left
    for a follow-on ticket (coordination with T-0717's capability taxonomy
    and the T-0611/T-0612 adapters' type info, per T-0762's ticket body),
    not silently guessed at here.

### Anti-orphan file-reference gate T-0396

`frob.gates._refs` -- `ref_gate` (gate name `refs`, default-on, WARN
severity, dial via `[gates.severity]`). Motivating case: the
`docs/design/registry/*.yaml` manifests were read by ZERO other tracked
files -- a silently dead/unenforced artifact no existing gate reasons
about, because every other gate reasons about SOURCE symbols
(`frob.graph`'s import/DSL edges), never about a bare tracked file's
existence being justified at all. This gate runs over EVERY git-tracked
file, regardless of type (source, docs, config, data, assets).

**Structural limitation, confirmed by measurement (T-2928)**: REF001/
REF002 count inbound references to a whole FILE, never to a symbol
inside it. A file with two or more real, independent consumers clears
REF002's 2+ pass bar even when one particular symbol defined inside
that file has zero callers anywhere -- the dead symbol is invisible to
a check that only ever asks "is this file referenced," never "is this
symbol referenced." Measured directly on a real controlled deletion:
`_parse_bash`/`_parse_csharp` (`src/frob/lang/_walk_bash.py`/
`_walk_csharp.py`, both files with plenty of other real consumers)
never tripped REF001 or REF002, despite being provably dead private
symbols later confirmed and deleted by T-2900/T-2905. This is not a
bug: file-level anti-orphan detection is this gate's entire documented
purpose (see this section's own opening paragraph); symbol-level
dead-code detection is DEAD001's job
(`frob.gates._dead_symbols`, unconditional, WARN not ERROR). Extending
REF001/REF002 to symbol granularity would mean building a second,
ERROR-severity duplicate of DEAD001's own scan -- a distinct feature
decision, not a fix, and out of scope for a bug ticket. Regression
fixture: `tests/unit/gates/test_refs.py::
TestRef002FileGranularityMissesDeadSymbols` (a must-stay-quiet case for
the exact T-2900/T-2905 shape -- a dead symbol inside an otherwise
well-referenced file -- paired with a must-still-fire control proving
REF001 still fires the moment the dead symbol IS effectively the whole
file's content).

Three detection layers, all feeding the same inbound-reference count per
file (T-1665 adds the first):

- **Resolved import** (`.py` targets only): a real AST-resolved import
  edge from `frob.graph.imports.build_import_graph` (T-1985's substrate)
  -- an `import`/`from ... import` statement Python's own grammar-correct
  parser resolves to a tracked file, precise regardless of aliasing,
  multi-name imports, or nesting inside `if`/`try`/`TYPE_CHECKING`
  guards. This REPLACED an older text-regex Python-import parser and,
  more importantly, replaced a bare-EXTENSIONLESS-STEM text-token match
  that used to also count for `.py` targets (a dispatch table's quoted
  module-name string, or an `importlib.import_module(...)` call argument,
  equalling the target's stem) -- that shortcut was false COMFORT, not
  proof: nothing verified the matching string was ever actually
  evaluated to reach that specific file. A `.py` target left at zero
  inbound whose emptiness MIGHT be an artifact of exactly that
  undecidable dynamic shape reports `Severity.UNRESOLVED` (T-1664)
  instead of a flat REF001, via a best-effort substring match against
  the substrate's own disclosed `UnresolvedImport` records (a dynamic
  import/dispatch call, or a relative import walking above the tracked
  root) -- an honest "cannot determine", never a silent pass and never a
  false-certain orphan claim.
- **Auto-scan** (all NON-Python-import reference shapes, every target
  type): file X counts as referenced by file Y when Y's text names X
  (full repo-relative path or bare basename WITH extension) in a real
  reference SYNTACTIC position -- a markdown link (`](path)`), a quoted
  string literal, a backtick-wrapped multi-component path mention
  (contains a `/`), a `frob:doc`/`frob:describes`/`frob:used-by`/
  `frob:tests` directive target, or a non-Python `require`/`include`/
  `use` target. Deliberately NOT a bare substring match over the whole
  text: a README table cell or a ticket-body sentence merely NAMING a
  file (`` `patterns.yaml` ``) is not a reference in any of these shapes,
  and counting it as one silently defeats the gate. This layer is what
  every non-`.py` target (docs, config, data, non-Python source) relies
  on entirely, since the resolved-import substrate above is disclosed
  Python-only.
- **Test-discovery IMPLICIT reference**: a file `frob.excludes.
  is_test_file` recognizes (`tests/**`, `test_*.py`, `*_test.py`, ...)
  is exempt from REF001/REF002 outright -- it is referenced by the test
  RUNNER via filesystem/naming convention, which no textual scan can see.
- **Declared** (`frob:used-by <consumer>`): a file names its own consumer
  explicitly, for references NEITHER layer above can structurally see (a
  path built at runtime from a variable, a glob loaded by a directory
  base). Every declaration is VERIFIED, not trusted: the named consumer
  must be a tracked file AND must itself reach the declaring file (same
  combined resolved-import/auto-scan check, in reverse) -- a declaration
  naming a nonexistent or non-reaching consumer is REF003, not a silent
  pass. This is the anti-lie half: a `frob:used-by` cannot manufacture a
  reference that isn't real.

**Round-2 correction (reviewer-rejected the first landing, T-0396 Done
report):** the first working version's auto-scan produced an 86%
false-positive rate on this repo's own tree (326 of 379 REF001 findings
were detector gaps, not real orphans) -- two systemic causes, both fixed:
(1) a `from X import a, b, c` only captured the module PREFIX, never the
imported names, so any module reached ONLY through a multi-name import
was a permanent false orphan; (2) pytest-discovered test files (52% of
the false findings) are reached by filesystem convention, which no
textual auto-scan can see, and were flagged forever without the implicit
test-discovery exemption above. A post-fix full manual review of every
remaining REF001 finding on this repo found the detector's false-positive
rate at effectively zero (see T-0396's Done report for the finding-by-
finding verification and the exact before/after counts).

Tiers, over the deduped set of inbound-referencing files (auto plus
verified-declared, unioned): **0** -> REF001 (orphan), **1** -> REF002
(single fragile anchor), **2+** -> pass. T-2369: REF001/REF002 are
ERROR-tier (promoted from WARN once the repo-wide burn-down reached zero
findings) -- an unwaived orphan or single-anchor file now fails `frob
check`'s exit code; every REF001/REF002 must be waived-with-reason
(`frob:waive REF001 reason="..."`), given a genuine second
consumer/declaration, or fixed. REF003 (dangling `frob:used-by`) is
unaffected by this promotion and stays advisory-but-tracked, same posture
as PERF/FUZZ.

`[[refs.entrypoint]]` in `frob.toml` exempts genuinely externally-facing
files (README.md, LICENSE, pyproject.toml, the CLI `__main__.py`, ...)
from REF001/REF002 -- each entry is `{ path = "...", reason = "..." }`; a
malformed entry (missing `path`/`reason`) is skipped and logged, never
treated as a blanket mute. T-2369: a `path` value containing `*`/`?`/`[`
is matched as an `fnmatch` glob rather than a literal path (`frob.gates.
_refs._allowlist_covers`) -- added so a structurally-permanent, ever-
growing write-once-artifact class (`changelog.d/*.md`, `tickets/*/
attachments/*`, `tickets/*/evidence/*`) can be covered by one entry
instead of one new literal entry per file forever.

`used-by` is a reserved marker verb in `frob.graph.dsl`
(`_RESERVED_MARKER_VERBS`): recognized and silently skipped by the graph's
generic directive parser (never routed through `EdgeKind`, never an
"unknown verb" `MalformedDirective`) because `_refs.py` owns and verifies
it directly via its own line-oriented scan -- a `frob:used-by` target is a
whole FILE, not a symbol, and every non-source tracked type
(yaml/md/toml/json/...) must be able to carry it too, most of which
`frob.lang` never parses at all.

### DOC004 unbound stale doc code blocks T-0436

`frob.gates._docblocks` -- `doc004_gate` (gate name `docblocks`, default-on,
mixed severity per finding). Motivating case: a fenced code block in a
`.md` doc (a python `from X import Y` example, a rust `use crate::path`
snippet) is the highest-drift-risk prose in a repo -- nothing binds it to
the code it demonstrates, so a rename/removal silently makes the doc lie.
No existing gate catches this: REF001-003 reason about whole-FILE
reachability, never a fenced block's own text; DOC001/DOC002 reason about
doc-to-doc/doc-to-symbol link structure, never code embedded in prose.

Deliberately SIMPLE, CONSERVATIVE, and PROJECT-GENERIC (the REF001
false-positive lesson applies here too: a noisy gate gets blanket-waived):

1. **Namespace derivation (never the directory name, never a hardcoded
   per-tool list)**: python from `pyproject.toml`'s `[project].name` plus
   every top-level package under `src/`; rust from the root `Cargo.toml`'s
   `[package].name` PLUS every `[workspace].members` glob's resolved
   subcrate (each subcrate is its own namespace -- a repo packaged as
   `logandapp_backend` is keyed on that name, never its directory); ts/js
   from `package.json`'s `name` plus `workspaces` members. Computed once
   per gate run.
2. **Extraction**: python `from X import ...`; rust `use X::...;`; ts/js
   `import ... from "X"` / `require("X")`. A token whose root namespace
   segment is not one of the project's own is skipped outright -- external
   libraries, generic shell, pseudo-code never flagged.
3. **Two tiers** for a token that DOES reference the project's own
   surface: **stale** (error) -- the module/crate/symbol does not resolve
   (python: checked against the real `GraphSnapshot` symbols, including a
   deliberately loose re-export check so a package `__init__.py` that only
   imports-and-re-exports a submodule's symbol via `__all__` is not a
   false positive; rust: checked by scanning the resolved crate's tracked
   `.rs` files for a matching `pub` item declaration) -- or **unbound**
   (warn) -- it resolves, but the block carries no `frob:doc`/
   `frob:describes`/`frob:tests` directive within itself or its three
   immediately-preceding doc lines, so future drift on it would go
   undetected. TS/JS is UNBOUND-only by design (no reliable static
   resolver for its export shapes here -- see the module docstring).
   C/C++ (T-0566, `_c_include_violations`) and csharp (T-2906,
   `_csharp_using_violations`) have no manifest namespace to resolve
   against either, so both are UNBOUND-only too, keyed on this repo's own
   tracked files instead of a namespace: a quoted `#include "..."` or a
   `using X.Y;` that plausibly names THIS project's own code (the include
   path exists as a tracked file; the dotted `using` target is a substring
   of a tracked `.cs` file's own dotted path) is checked for a nearby
   binding directive. bash reuses the pre-existing console-command tier
   (`_CONSOLE_LANGS`, point 5 below) for its own fenced blocks -- no
   separate resolver needed.
4. **`frob:waive DOC004 reason="..."` is prominently honored** directly
   out of the block's own nearby text (an HTML comment above the fence, or
   a comment line inside it) -- NOT routed through `frob.graph`'s WAIVE
   edge machinery, because `.md` files never go through
   `frob.graph.dsl.parse_directives` (only the narrower `markdown_anchors`
   describes-only scan), so a waiver written in doc prose has no graph
   edge to bind to. This is the deliberate escape hatch for a genuinely
   external or illustrative block the heuristic cannot confidently
   classify.

5. **Console/bash command-drift checking (T-0443)**: a
   ` ```console ``` `/` ```bash ``` `/` ```sh ``` `/` ```shell ``` ` fenced
   block's lines are scanned for `<prog> <subcommand...>` invocations of a
   CONFIGURED command source -- never a hardcoded, frob-specific
   subcommand list. `frob.toml`'s `[[docblocks.commands]]` array declares
   each source generically:

   ```toml
   [[docblocks.commands]]
   prog = "frob"
   parser = "frob.__main__:_build_parser"
   ```

   `parser` is a `module:callable` dotted path to a zero-argument factory
   returning an `argparse.ArgumentParser`; the gate imports it AT CHECK
   TIME and walks its live `add_subparsers` tree, so the argparse registry
   is the single source of truth -- a subcommand rename/removal there is
   caught automatically, with zero edits to this gate or to `frob.toml`.
   A chain that does not walk the tree is STALE (error); one that does
   resolve is checked for a nearby binding directive same as every other
   tier (UNBOUND, warn). No `[[docblocks.commands]]` entries at all (a
   project that has not opted in) means zero console/bash checking --
   fail-open, matching every other namespace source in this module.

This repo configures itself as its own first instance -- see
`frob.toml`'s `[[docblocks.commands]]` table, pointed at
`frob.__main__:_build_parser`.

**Dogfooding result (T-0436 Done report has the full finding-by-finding
detail)**: run on this repo's own tracked docs, DOC004 found 5 real
blocks -- 2 genuinely stale (`frob.edit._impl`, `frob.app.stub_runner`: <!-- frob:waive DOC006 reason="historical T-0436 dogfooding finding naming modules that were ALREADY removed/never-real at the time; a verbatim record, not a live pointer" -->
illustrative example modules referencing a removed/never-real command
surface) and 1 hypothetical-future worked example
(`export_terraform_sg`), each dispositioned with a reasoned
`frob:waive DOC004 reason="..."`; 1 initial false positive (a package
`__init__.py` re-export, `frob.strata`) was a real detector bug, fixed
before landing (see `_module_reexports`); 1 real UNBOUND advisory
(`docs/modules/logging.md`'s usage example, anchored later in the same
doc's "Public API" section rather than immediately above/inside the
block) was waived with a reason explaining why. Zero blanket waivers --
every waiver names its own specific reason.

### DOC005 README command-table drift-lock T-0435

`frob.gates._docblocks` -- `doc005_gate` (gate name `docblocks`, same as
DOC004, default-on, ERROR severity). Motivating case: `README.md` carries
~0 `frob:describes` anchors, so it is UNANCHORED prose -- DOC001/DOC002
detect drift THROUGH anchors, and DOC004 detects drift in fenced code
blocks, but neither reasons about a markdown TABLE naming commands.
README's command table drifted silently: it was missing 8 of 25 real
subcommands (a third, including whole subsystems added during the
`edit`/`dispatch`/`mission`/`todo` rework) before this ticket, and nothing
ever flagged it.

`doc005_gate` reuses DOC004's console-tier machinery WHOLESALE -- the same
`[[docblocks.commands]]`-configured `argparse.ArgumentParser` factory,
walked into the same live subparser tree (`frob.gates._docblocks.
_console_trees`) -- rather than a second, parallel registry-reading
mechanism. Two checks over `README.md`, both ERROR (concrete, present
drift, not advisory):

1. A markdown table row `| \`<prog> <name>\` | ... |` naming a `<name>`
   that is NOT a real top-level subcommand of the live tree -- STALE, the
   command was renamed/removed and the row never updated.
2. A real top-level subcommand with NO table row anywhere in `README.md`
   -- MISSING, the README silently omits a real command (this repo's
   original T-0435 finding: `clean`/`debt`/`doctor`/`pool`/`registry` had
   no row).
3. A "N commands" (or "N total commands") prose count claim whose `N`
   does not equal the live top-level command count, summed across every
   configured `[[docblocks.commands]]` source -- the "checkable counts"
   half of the ticket's mandate. No such claim in a project's README means
   nothing to check (never a false positive from an absent claim).

No `[[docblocks.commands]]` entries configured, or no `README.md` at the
scanned root, means no checking happens -- fail-open, the same posture as
every other DOC004 namespace source. This repo uses its own already-
configured `[[docblocks.commands]]` entry (`frob.__main__:_build_parser`)
-- adding a new subcommand there and never touching `README.md` now fails
`frob check` immediately; removing a command leaves its stale row failing
until the row is deleted.

4. T-1011: `docs/modules/cli.md`'s GENERATED command-table block (opted in
   via `CLI_COMMAND_TABLE_START`/`CLI_COMMAND_TABLE_END` marker comments,
   see docs/modules/cli.md#generated-command-reference-t-1011) must equal
   what `generate_cli_command_table` produces RIGHT NOW -- a generator-
   freshness check (`_doc005_cli_table_freshness_violations`), distinct
   from checks 1-3 above (which stay a hand-sync MISSING/STALE lock over
   README's own curated, section-grouped table -- regenerating README
   wholesale would destroy that hand-curated grouping, so only cli.md's
   block is fully generated). `frob docs --sync-commands`
   (`sync_cli_command_table`) is the write side: it regenerates ONLY the
   marked block in place, leaving the rest of `docs/modules/cli.md`
   untouched. No marker block present means the doc has not opted in yet
   -- fail-open, nothing to check, same posture as checks 1-3.

### DOC012 dedicated command-section drift-lock T-1783

`frob.gates._docblocks` -- `doc012_gate` (gate name `docblocks`, same as
DOC004/DOC005, default-on, ERROR severity as of T-2299 -- shipped WARN
at first-turn-on per the T-0688 new-gate-at-WARN precedent DOC006 also
used; see the disclosure and promotion paragraphs below). Motivating
case: T-1610's
docs-completeness sweep found `frob coverage` (T-1516/T-1525) had a
README/cli.md command-table row (satisfying DOC005) but no dedicated
section anywhere describing its own flags/behavior -- its content lived
only as a passing aside inside `docs/modules/testing.md`'s section about
a different topic. DOC005 was checked first and correctly found nothing
wrong: it was never designed to ask whether a listed command's own
behavior is documented anywhere, only whether it is LISTED at all. DOC012
closes that gap as its own rule rather than widening DOC005's contract.

Reuses DOC004/DOC005's `_console_command_sources`/`_console_trees`
machinery wholesale -- the same live, `[[docblocks.commands]]`-configured
`argparse.ArgumentParser` walk, not a second registry-reading mechanism.
For every top-level subcommand name that walk exposes, `doc012_gate`
scans every git-tracked `.md` file under `docs/commands/` or
`docs/modules/` for an ATX heading (`#` through `######`) whose text
names it: `_doc012_heading_command` strips a trailing parenthetical
(`(T-1234)`, `(CLI verb, T-1516/T-1525)`) and a leading/trailing
backtick from the heading's first two whitespace-separated tokens, and
the result must equal `(prog, name)` exactly -- `# frob scaffold`, `##
frob coverage (T-1525)`, and `` ## `frob doctor`: ... `` (the trailing
colon-and-more after the second token is ignored, since the regex only
anchors the first two tokens) all resolve; a heading that merely
mentions the command mid-sentence does not. A subcommand with no
resolving heading anywhere is one finding (`_doc012_violation`).

**Disclosed debt at ship time (T-1783's own investigation):** running
`doc012_gate` over this repo at the moment the rule shipped found 24
top-level subcommands with no dedicated section (`ack`, `agent`, `arch`,
`clean`, `debt`, `deprecated`, `design`, `docs`, `dup`, `explore`,
`fleet`, `graph`, `mutate`, `ops`, `perf`, `pool`, `profile`, `quality`,
`registry`, `serve`, `stats`, `test`, `vet`, `worktree`) -- real,
pre-existing gaps, not new drift this ticket introduced. WARN (not
ERROR) at ship time was deliberate per the T-0688 precedent: this was a
genuine backlog to burn down over time, not a signal to force every one
of them into existence inside T-1783's own scope, and not a reason to
red every unrelated land fleet-wide the moment the rule shipped.

**Burn-down and promotion (T-2299):** that disclosed 24-item backlog
existed only as prose in T-1783's archived Done report until T-2299
tracked it as a first-class epic ticket. T-2299 re-measured the backlog
(confirmed still exactly 24, no drift since T-1783), filed two child
tickets grouped by owning doc file so the work could parallelize --
T-2315 (the 10 subcommands whose module already had a dedicated
`docs/modules/*.md` file, just needing a `## frob <name>` heading added
next to the existing prose: `arch`, `clean`, `dup`, `fleet`, `graph`,
`mutate`, `perf`, `serve`, `stats`, `vet`) and T-2316 (the remaining 14
with no dedicated file at all, documented as new `## frob <name>`
sections in `docs/modules/cli.md`: `ack`, `agent`, `debt`, `deprecated`,
`design`, `docs`, `explore`, `ops`, `pool`, `profile`, `quality`,
`registry`, `test`, `worktree`) -- and landed both. With the measured
count at zero, T-2299 promoted `_doc012_violation` from WARN to ERROR: a
newly introduced undocumented subcommand now fails `frob check`
immediately rather than silently re-accumulating the same backlog. See
`tests/test_doc012_promotion.py::TestDoc012PromotedToError` for the
must-fail fixture proving the promotion actually changed severity (filed
in its own file, disjoint from `tests/test_gates.py`'s own
`TestDoc012CommandSectionGate`, because that file carried a live
cross-worktree lease -- T-2314 -- at promotion time; a follow-up
`frob:todo T-2299` in that new file tracks folding it back in and
updating the pre-promotion WARN assertion once the lease clears).

No `[[docblocks.commands]]` entries configured means no checking happens
-- fail-open, the same posture as DOC004/DOC005. T-1682 (filed by T-1610)
is the CONTENT fix for `frob coverage` specifically; this rule is the
MECHANISM, and does not itself write any doc section.

### DOC006 doc-pointer resolution gate T-0437

`frob.gates._docptr` -- `doc006_gate` (gate name `docblocks`, same as
DOC004/DOC005, WARN severity at first-turn-on per the T-0688 new-gate
precedent). Motivating case: a doc's prose routinely "seems to point" at
something -- `frob edit`, `src/frob/gone.py`, `[bogus.section]`, <!-- frob:waive DOC006 reason="deliberately fictional pointer examples this section quotes from _docptr's own module docstring to illustrate the motivating case; never meant to resolve" -->
`docs/missing.md#x` -- and nothing checked whether the pointer was
actually real. Detecting fuzzy "seems to point" intent generically is
unhardenable (high false-positive rate); this gate instead defines a
CLOSED SET of RECOGNIZED, mechanically resolvable pointer shapes and only
fires when a pointer of a known shape targets something that does not
exist. An unrecognized/ambiguous token is never flagged -- that is the
hardening.

Seven recognized pointer kinds (five original, plus two T-1228 additions
below), each detected in an inline code span or markdown link across
every tracked `.md` file's PROSE (fenced code block bodies are DOC004's
own territory and are skipped here, to avoid double-reporting the same
token under two rule ids):

1. **FILE/PATH** -- a repo-relative path (contains `/`, or a well-known
   bare manifest basename: `frob.toml`, `pyproject.toml`, `Cargo.toml`,
   `package.json`) must exist as a git-tracked file.
2. **CLI INVOCATION** -- `` `<prog> <subcommand...>` `` / `` `--flag` ``
   checked against the SAME `[[docblocks.commands]]`-configured live
   argparse registry DOC004/DOC005 already walk -- one live source of
   truth, never a second copy.
3. **CONFIG REFERENCE** -- `` `[section]` ``/`` `[section.key]` `` checked <!-- frob:waive DOC006 reason="[section]/[section.key] here is the KIND'S OWN illustrative placeholder shape, not a real config reference" -->
   against this project's own loaded `frob.toml` structure.
4. **CODE SYMBOL** -- a dotted path (`module.Class.method`) whose root
   namespace is one of this project's own manifest-derived namespaces
   (`frob.gates._docblocks._project_namespaces`), resolved the same way
   DOC004's python tier resolves a `from X import Y`.
5. **DOC-ANCHOR LINK** -- `docs/x.md#anchor`: the file must exist and <!-- frob:waive DOC006 reason="docs/x.md#anchor here is the KIND'S OWN illustrative placeholder shape, not a real doc pointer" -->
   `anchor` must be a real heading/`<a id>` slug in it (the same resolver
   DOC002 uses for `frob:doc` edges).

T-1228 adds two more recognized shapes:

6. **FILE::SYMBOL** -- `` `path.py::qualname` `` / `` `path.rs::name` ``: <!-- frob:waive DOC006 reason="path.py::qualname and path.rs::name here are the KIND'S OWN illustrative placeholder shape, not real pointers" -->
   a doc author naming WHICH file a symbol lives in explicitly (rather
   than its importable dotted module path, kind 4's own territory). The
   FILE half must be a tracked `.py`/`.rs` file (exact spelling or a
   module-relative trailing-component shorthand, same posture as kind
   1's `_is_tracked_path_suffix`); for a `.py` file the (optionally
   dotted, one-level-conservative like kind 4) symbol half must be a real
   top-level name defined there; for a `.rs` file it must be an item
   declaration (`fn`/`struct`/`enum`/`trait`/`mod`/`const`/`static`/
   `type`) somewhere in that one already-named file, `pub` optional --
   round-3 (T-1228, real-corpus false positive): several genuine, real
   functions (`parse_node`, `parse_store`, ...) are TRAIT-IMPL methods,
   which never carry an explicit `pub` of their own even though they are
   real and callable (visibility is inherited from the trait); since the
   FILE is already pinned by the doc's own pointer, matching without
   requiring `pub` is precise here, unlike the crate-wide `use` check
   kind 2 reuses (where requiring `pub` matters to avoid matching an
   unrelated same-named PRIVATE helper elsewhere in the crate).
   Round-3 (T-1228, real-corpus false positive): a shorthand basename
   (`_waive.py`, `_models.py`, no directory) is NOT unique in this repo --
   16 tracked files end in `_models.py` alone -- so a shorthand FILE half
   matching MORE THAN ONE tracked file is treated as unrecognized/
   ambiguous and never flagged, rather than resolving against an
   arbitrary one of the matches (which produced a real false positive:
   `` `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` `` resolved against the
   wrong of two tracked `_waive.py` files).
7. **BARE IDENTIFIER** -- a lone, code-shaped (`snake_case`/
   `CONSTANT_CASE` or multi-hump `CamelCase`) backtick token, resolved
   ONLY when `doc_path` is a genuinely **single-implementation-module**
   doc: exactly ONE distinct python file carries a
   `frob:doc <this-doc>#...` edge into it. A doc with two or more
   distinct anchor files (every reference doc describing a whole module,
   e.g. `docs/modules/gates.md` itself) is describing a SYSTEM, not one
   file, and is out of scope entirely -- round-2 (T-1228, post-close
   reject): the original "at least one anchor" scoping was, on this
   repo's own corpus, effectively no scoping at all (nearly every
   reference doc carries dozens of anchors, one per public symbol it
   documents), producing ~1400 false positives on the real-corpus check
   this ticket should have run before its first close. `docs/strata/**`
   and `design/**` (the strata design language's own spec/system-design
   prose) are excluded outright regardless of anchor count -- their
   vocabulary (`two_phase_commit`, `capability_kind`, `RULE_ID`, ...) is
   DSL terminology the strata grammar defines, not python identifiers,
   even when shaped like one; `tickets.md`/`tickets-archive.md` (ticket-
   ledger prose, which routinely quotes illustrative syntax examples, not
   live pointers) are excluded from this kind and kind 6 alike. Even
   within a qualifying single-anchor doc, a token first checked against
   the WHOLE PROJECT's known symbol names, not just the one anchor file's
   own -- a real cross-file mention (`AuditReport`, discussed in one
   module's doc but defined in another) always resolves.

   Round-3 (T-1228, still real-corpus false positives after round-2's
   narrowing): even inside a genuinely single-anchor, non-spec doc,
   "resolves to NO python symbol anywhere in the project" turned out to
   be a common and entirely legitimate shape for a config/data FIELD name
   (`bin_path`, `service_account`) or third-party/external-system
   vocabulary (`SeDenyInteractiveLogonRight`, `ActiveDirectory`) -- none
   of those are ever going to be top-level python symbols, so their
   absence from the symbol table is not evidence of doc rot the way it is
   for kind 4's dotted symbol. This kind is narrowed to the ONE signal
   that IS unambiguous: a **private-name rename** -- the token doesn't
   resolve as a real (public) name, but a leading-underscore twin
   (`_name`) is a real top-level name in the doc's own anchor file. A
   bare identifier with no matching name at all, public or private, is
   silently skipped -- the same "unrecognized token, never flagged"
   posture this gate's docstring commits to for every other kind.

Both new kinds carry the same **private-name awareness**: when the
identifier does not resolve but a leading-underscore twin (`_name`) is a
real symbol at the same site, the violation message names the private
spelling directly (`did it mean the private ..._name?`) -- the "public
name renamed to private, doc never updated" class the docs-staleness
audit's own bare-identifier sweep found repeatedly (`digest_sig` ->
`_digest_sig`, `host_attrs` -> `_host_attrs`). The dotted CODE SYMBOL kind
(4) carries the same awareness in its own violation message.

The prose token scanner also now resolves **line-wrapped backtick
spans**: commonmark treats a single embedded newline inside an inline
code span as ordinary whitespace, so a span an editor hard-wrapped
mid-token (`` `frob.gates.\n_docptr` `` split across two lines) still
resolves as the same token written on one line. A span containing a
BLANK line (a real paragraph break) is never treated as wrapped -- that
is two unrelated stray backticks, not a genuine wrapped span.

A ninth, source-level check rides alongside the doc-prose scan for the
DRIFT002 dotted-vs-`::` confusion class (T-0940/T-0945): a `frob:tests`
directive's target is itself a recognized, mechanically-checkable shape --
`<file>::<qualname>` with exactly one `::` separating the file from a
DOTTED (`Class.method`) qualname. A target with a SECOND `::` (pytest's
own `Class::method` collect-only separator) is definitively the wrong
shape for a graph-facing `frob:tests` target, flagged here directly
instead of waiting for it to surface later as a generic DRIFT002
dangling-edge failure with a less specific message.

Every finding is `frob:waive DOC006 reason="..."`-able (same nearby-line
convention as DOC004: same line or up to 3 preceding lines), for a
genuinely external/illustrative/future-facing pointer.

**Turn-on disclosure**: shipped at WARN, not ERROR, because this repo's
own tracked docs already carry pre-existing pointer drift the gate newly
detects (see T-0437's Done report for the measured count at turn-on).

### Git-less target contract T-0705

Every gate that scans "every tracked file" (`secrets_gate`, `pii_structural_
gate`, `render_lint_gate`, `walk_lint_gate`, `ref_gate`, DOC004's `src/`/
`*.md` namespace sources) resolves its file list via `git ls-files` under
`root`. When `root` is not a git work tree at all (no `.git`, or `git`
itself missing/unavailable) that subprocess exits 128 -- not a violation,
just an environment with nothing tracked to scan.

The chosen, consistent contract for ALL of these call sites: **degrade
gracefully, never hard-error**. `git ls-files` failing on a git-less
`root` logs at WARNING and the gate returns `()` (no candidates, no
violations) -- the same posture `ref_gate`/DOC004 always had. Before
T-0705, `secrets_gate`/`pii_structural_gate`/`render_lint_gate`/
`walk_lint_gate` logged the identical condition at ERROR, painting their
line red in `frob check`'s raw log stream for a target that was never a
violation. This was an inconsistency between six call sites doing the
exact same "resolve tracked files, degrade on failure" dance, not a
deliberate severity choice -- nothing about a git-less target makes THESE
four gates more alarming than `ref_gate`/DOC004's identical fallback.

This does not weaken what any gate checks in a real git repo: the
`returncode != 0`/`is_err` branch only fires when `git ls-files` itself
fails, which never happens against an actual tracked worktree. A genuinely
untracked/dirty file in a real repo is unaffected -- `git ls-files` still
enumerates every OTHER tracked file normally, and per-file scanning logic
is untouched.

Why not the alternative (git as a hard requirement, erroring loudly with
ONE message before any gate runs)? `frob check <path>` and `frob ticket
new --path <path>` are both documented to accept a bare filesystem path
with no git precondition (`docs/modules/tickets-lifecycle.md#provisional-ids`'s
"ambiguous: no git repo, detached HEAD, git unavailable" ticket-id-minting
fallback is the same call already made for a sibling concern) -- a git-less target is a
supported, if degraded, scan surface, not a usage error. Gates that
inherently need a diff against a base branch (`COV002`/`SCOPE001`/
`TODO001`) are a distinct, ALREADY-deliberate mechanism (T-0550, in
`frob.gates.coverage_gate`/`scope_gate`/`_load_diff`) with its own loud
fail-on-load-failure contract for a different reason (masking a real diff
failure as a silently-clean diff on an actual project); T-0705 does not
touch that mechanism -- see T-0705's Done report for the follow-up ticket
that tracks whether a git-less `root` should also be exempted there.

Regression coverage: `tests/system/test_cli_check.py`'s
`TestGitlessTargetGateSeverity` plants a git-less fixture directory and
asserts each of the four gates' fallback line is WARNING, never ERROR.

### WALK001 unpruned traversal T-0471

`frob.gates._walk_lint` -- `walk_lint_gate` (gate name `walk_lint`,
default-on, WARN severity). Motivating case: T-0453's `_repo_files` did
`root.rglob("*")` -- walking the ENTIRE tree including `.git`, `.venv`,
`__pycache__`, and ~129 stale worktrees under `.claude/worktrees/` --
making `frob ticket doable` take minutes. `frob.excludes` already carried
the shared prune machinery (`_should_prune_dir`/`is_always_pruned_dir`, the
built-in skip set + `frob.toml` globs, established by T-0335 for `os.walk`
sites), but nothing stopped a raw traversal call from bypassing it. This
gate turns that mistake class into a static check: no NEW unpruned
traversal can land silently.

`frob.excludes` grew two shared entry points every walking caller should
route through instead (T-0471): `walk_pruned(root)` (an `os.walk`
generator that prunes `dirnames` in place via `_should_prune_dir` BEFORE
descending) and `iter_files(root, *, suffix=None)` (prefers a `git
ls-files` fast path -- tracked files only, no traversal at all -- when
`root` looks like a git work tree, falling back to `walk_pruned`
otherwise).

Detection is AST-based (Python's `ast` module, matching `_pii_structural`'s
precedent -- a regex/lexical scan both over- and under-fires on multi-line
calls and string mentions that merely name the pattern), scanning every
git-tracked `src/frob/**/*.py` file for:

- `Path.rglob(...)` -- always unbounded recursive regardless of pattern.
- `Path.glob(...)`/`Path.iglob(...)` -- only when the pattern argument
  contains `"**"` (a non-literal/dynamic pattern is treated as
  potentially recursive, deny-by-default).
- `os.walk(...)` -- dotted or bare-imported (`from os import walk`) form.
- `glob.glob(...)`/`glob.iglob(...)` with a `"**"` pattern -- dotted or
  bare-imported form.

Self-excludes `frob/gates/_walk_lint.py` (its own detection logic) and
`frob/excludes.py` (the shared helpers' own implementation, which contains
the one legitimate raw `os.walk` call this whole gate exists to keep
singular). Waivable per-line (`frob:waive WALK001 reason="..."`) for a
genuinely small, bounded-scope walk (e.g. `design_dir.rglob("*.strata")`
over a directory that will never be large enough to matter) -- the message
always names the remedy: route through `frob.excludes.iter_files` /
`frob.excludes.walk_pruned`.

### PLATFORM001 POSIX-only primitive degrades silently (T-2919)

<!-- frob:describes src/frob/gates/_walk_lint.py::_scan_platform_guards -->
<!-- frob:describes src/frob/gates/_walk_lint.py::_scan_import_time_platform_evals -->
<!-- frob:describes src/frob/gates/_walk_lint.py::walk_lint_gate -->

`frob.gates._walk_lint` -- rides alongside WALK001 in the SAME
`walk_lint_gate` function/gate name (default-on, WARN severity), one AST
pass over the same `src/frob/**/*.py` tracked-file set producing both
rule ids' violations, mirroring how NEGEXIST001 rides the "docblocks"
stage rather than getting its own dispatch-table entry.

Motivating case: T-2917/T-2918 measured this repo's CI as ubuntu-latest
only (so no test ever ran on Windows or macOS) AND `frob.app.
ticket_runner._rapid_sweep._baseline_lock` degrading to a logged-but-
silent NO-OP for a process's ENTIRE lifetime whenever `fcntl` was not
importable -- unconditionally true on every Windows process, not merely
under rare lock contention. Both branches type-check; both branches pass
a Linux-only CI; nothing but reading the source (or running on Windows)
would ever surface it. T-2918 fixed that ONE site (a real `msvcrt`-backed
Windows lock, and a loud `BaselineLockUnavailable` refusal when neither
primitive exists); PLATFORM001 generalizes the DETECTION so the next
POSIX/Windows-only primitive added anywhere in `src/frob/**` cannot ship
the identical silent gap.

Detection is AST-based, three steps:

1. **Find platform-optional primitive names.** A `try:` block that binds
   a local name to one of a fixed platform-restricted module list
   (`fcntl`, `termios`, `tty`, `pwd`, `grp`, `resource`, `posix` for
   POSIX; `msvcrt`, `winreg`, `_winapi` for Windows) via either
   `import X [as name]` or `name = importlib.import_module("X")`, whose
   `except ImportError:` handler sets that same name back to `None` --
   the exact idiom this repo's own `fcntl`/`msvcrt` degrade sites use.
   Deliberately excludes third-party optional-dependency names (`z3`,
   `tree_sitter`, ...) that follow the identical shape for an unrelated
   reason (an optional extra, not a platform gap) -- out of this rule's
   population by design, not a missed case.
2. **Find absence guards.** Every `if <name> is None [and <name2> is
   None ...]:` in the module whose tested name(s) came from step 1 --
   handles both a single-primitive guard and T-2918's own "neither
   primitive" compound form.
3. **Classify the guard body.** WARN-AND-CONTINUE (a PLATFORM001 finding)
   if the body logs (any `_log.<level>(...)`-shaped call) and never
   refuses loudly; QUIET if the body contains a `raise` anywhere or a
   top-level `sys.exit(...)`/`os._exit(...)` call (T-2918's own
   `BaselineLockUnavailable` shape).

**T-2934 narrowing (was a v1 disclosed gap):** `_guard_is_loud` now
also treats a `return Ok(...)`/`return Err(...)` (typani's two Result
constructors, bare or dotted) as loud -- a real false positive was
measured on `frob.tickets._land_git_ops.reclaim_orphaned_squash_
residue`'s actual `if _fcntl is None: _log.warning(...); return
Ok(False)`: that function's whole job is deciding whether a mutation is
SAFE, and `Ok(False)` there is a genuine, visible, controlled abort of
the risky operation -- not "proceeded as if the missing primitive did
not matter" the way `_baseline_lock`'s pre-T-2918 bug did. Per this
project's own stated preference ("if any turns out to be a false
positive, say so and narrow the gate rather than waiving it"), the fix
was to the DETECTOR, not a `frob:waive` on the finding. A plain
`return`/bare fallthrough with no `Ok`/`Err` wrapper is still NOT
treated as loud and still fires -- narrowing to accept typed exits does
not weaken the original must-fire shape (re-asserted directly as a
negative control, `test_plain_return_with_no_typed_constructor_still_
fires`).

Fixtures lock all three directions in `tests/test_walk_lint_gate.py::
TestPlatform001` (`test_warn_and_continue_fires` / `test_gate_fires_end_
to_end` for the must-fire shape lifted byte-for-byte from `_baseline_
lock`'s pre-T-2918 form; `test_loud_refusal_is_quiet` / `test_gate_stays_
quiet_on_properly_guarded_module` for its post-fix raise-based shape;
`test_typed_result_refusal_is_quiet` / `test_typed_err_refusal_is_quiet`
for the `_land_git_ops.py`-shaped `Ok`/`Err` false positive this
narrowing fixed) plus a control (`test_no_platform_probe_is_quiet`)
proving an unrelated optional-
dependency probe (`z3`) never anchors this rule at all.

**T-2944: two more shapes.** The above only ever anchored on the `try:
import X / except ImportError: X = None` idiom -- it had zero
visibility into a `sys.platform`-shaped guard or an unguarded import.
Measured directly: `src/frob/process/_reap.py::arm_parent_death_
signal`'s `if sys.platform != "linux": return False` fired PLATFORM001
zero times before this addition, despite being a real silent platform
degrade (its caller happened to log, invisibly to this file-local AST
scan). Two more scans now ride the same `walk_lint_gate` pass:

- **Shape 2 -- silent platform-STRING guard** (`_scan_platform_string_
  guards`): an `if <sys.platform|os.name|platform.system()> (!=|==)
  "<literal>":` guard whose body is a pure no-op degrade
  (`_is_degrade_body` -- a bare `return <falsy>`/`pass`, nothing else)
  and neither logs nor refuses loudly IN ITS OWN BODY. Deliberately
  requires a bare `ast.Compare` test (a `BoolOp` combining it with
  something else, e.g. `reap_orphaned_forkservers`'s own `sys.platform
  == "win32" or not proc.is_dir()`, is real branching logic, not this
  rule's target) and a single-statement body (real cross-platform WORK
  that merely doesn't log/raise, e.g. `_coverage_refresh.py`'s win32
  `taskkill` branch, must stay quiet). Fixtures: `TestPlatform001String
  Guard.test_silent_string_guard_fires` (must-fire, `arm_parent_death_
  signal`'s real shape), `test_logged_string_guard_is_quiet`/
  `test_real_platform_branch_is_quiet`/`test_boolop_guard_is_quiet`
  (must-stay-quiet).
- **Shape 3 -- bare unconditional restricted-module import**
  (`_scan_bare_restricted_imports`): a module-TOP-LEVEL `import X`
  (never nested in a `try:`) naming a `_PLATFORM_RESTRICTED_MODULES`
  module -- the T-2952 regression class (`_new_renumber.py`/
  `_socketd.py`/`_coverage_wait.py`'s pre-fix bare `import fcntl`,
  which crashed the whole module's IMPORT on Windows). Fixtures:
  `TestPlatform001BareImport.test_bare_import_fires` (must-fire) /
  `test_guarded_import_is_quiet` (must-stay-quiet, the standard
  guarded idiom).

Investigated but deliberately NOT given a new shape: `src/frob/tickets/
_leases.py::scan_for_live_worktree_process`'s `/proc`-only degrade
(returns `None`, permissive). Its shape is structurally identical to
two REAL, legitimate, explicitly-documented sites in this same repo
(`reap_orphaned_forkservers`'s "structural no-op, not a degraded scan"
comment; `count_running_checks`'s documented advisory-only contract) --
a blanket AST rule cannot statically tell "backs a safety refusal" from
"advisory/best-effort by design," and attempting one would have
false-positived on legitimate code in this same file. Filed as its own
scoped follow-up rather than guessed at here.

**T-2951: a fourth shape -- import-time evaluation with no guard of any
kind.** All three shapes above look for SOME conditional construct (a
`try`, an `if`) and classify its body. T-2936 fixed a real crash by hand
that had no guard at all to classify: `src/frob/process/_reap.py::
arm_parent_death_signal(sig: int = signal.SIGKILL)` bound a POSIX-only
attribute as a `def`'s DEFAULT ARGUMENT value -- evaluated once, when
the `def` statement itself executes (at module import time), crashing
the import of the whole module before the function's own platform guard
(shape 2, above) ever ran. Neither the original `X is None` scan nor
either T-2944 shape caught this, because there was nothing shaped like a
guard to inspect; the ABSENCE of a guard at `def`-evaluation time WAS
the bug.

`_scan_import_time_platform_evals` closes this: it walks the Module's
own top-level statements plus the body of every `ClassDef` reachable
from there WITHOUT passing through an `if`/`try`/function boundary
(`_unconditional_body_blocks` -- these are exactly the statement lists
guaranteed to execute unconditionally at import time), and for every
`def`'s default argument value, decorator-call keyword argument, or
module/class-level constant assignment found there, flags any
`_restricted_attr_dotted_name` match: an attribute of a whole
`_PLATFORM_RESTRICTED_MODULES` module (`fcntl.flock`, any attribute --
the whole module is platform-restricted), or one of a fixed POSIX-only
`signal.SIG*` name list (`_POSIX_ONLY_SIGNAL_ATTRS`: `SIGKILL`,
`SIGSTOP`, `SIGHUP`, `SIGQUIT`, `SIGUSR1`, `SIGUSR2`, `SIGCHLD`,
`SIGCONT`, `SIGTSTP`, `SIGTTIN`, `SIGTTOU`, `SIGWINCH`, `SIGALRM`,
`SIGVTALRM`, `SIGPROF`, `SIGPIPE` -- unlike `fcntl`/`termios`/etc, the
`signal` module itself imports fine on every platform, so only specific
attributes are restricted).

Two guard shapes stay deliberately quiet, both because Python itself
never evaluates the restricted attribute unconditionally in either
case: an attribute reached only through one arm of an `ast.IfExp`
("ternary") -- `signal.SIGKILL if sys.platform != "win32" else None` --
since Python evaluates only the chosen branch
(`_restricted_attrs_unguarded`'s own guarded-descent tracking); and a
`def`/`Assign` nested inside a real `if`/`try` block at module or class
scope, which `_unconditional_body_blocks` never yields in the first
place (the whole statement's own conditional execution is the guard).
A restricted attribute read only inside a function BODY (never a
default/module/class-level constant) is out of this scan's population
entirely -- that is ordinary lazy evaluation, the shape this rule exists
to distinguish FROM the bug.

Fixtures lock all eight directions in `tests/test_walk_lint_gate.py::
TestPlatform001ImportTimeEval`: `test_default_arg_fires` (T-2936's own
pre-fix shape, byte-for-byte), `test_module_constant_fires`,
`test_class_attribute_fires`, `test_decorator_kwarg_fires` (must-fire,
one per position named in the ticket); `test_guarded_default_arg_is_
quiet` (T-2936's own post-fix `sig: int | None = None` shape),
`test_ternary_guarded_constant_is_quiet` (the `IfExp`-guarded constant),
`test_if_guarded_def_is_quiet` (the whole `def` nested inside a real
`if sys.platform != "win32":` block), `test_body_reference_is_quiet`
(a function-body-only read) -- all four must-stay-quiet twins named in
the ticket. Repo-wide `PLATFORM001` count was 0 both before and after
adding this shape (T-2936's real site was already fixed by hand before
this rule existed to catch it) -- zero new findings to triage.

### EXCL001 (T-0465)

<!-- frob:describes src/frob/gates/_exclude_hazard.py::exclude_hazard_gate -->

`frob.gates._exclude_hazard` -- `exclude_hazard_gate` (gate name
`excludehazard`, default-on, ERROR severity, unwaivable by design -- see
below). Motivating incident: an agent added `src/frob/render/` to
`.git/info/exclude` to hide its own in-progress untracked scratch files.
`.git/info/exclude` is a personal, UNTRACKED gitignore -- but it lives
under `.git/`, which is the COMMON dir shared by every worktree of one
clone (`git rev-parse --git-common-dir`), not a per-worktree path. One
entry there silently changes `git status`/`git add -A` behavior in every
worktree of the clone AND `main` simultaneously. The hazard isn't that
excluding a directory untracks files already committed (it does not) --
it's that a real, git-tracked source directory now has a standing blind
spot: any NEW file added under it later never shows up as untracked,
never gets `git add -A`ed, and silently never gets committed. That is
exactly how the T-0448 foundation went missing.

`exclude_hazard_gate` reads the shared common dir's `info/exclude`
directly (not the repo-relative, possibly-scoped root -- the file is
one, shared, common-dir path regardless of which worktree runs `frob
check`), parses each non-comment, non-negated gitignore-format line into
its directory/file prefix, and flags any prefix that names an exact
git-tracked file or a directory under which `git ls-files` finds at
least one tracked file. An entry matching nothing tracked (`*.pyc`,
`build/`, any genuinely-generated or never-tracked path) is silent --
those are exactly what `.git/info/exclude` is FOR.

Deliberately unwaivable (no `frob:waive EXCL001` escape hatch): the
entry lives in `.git/info/exclude` itself, not in a source file a
`frob:waive` comment could attach to, and the honest fix is always the
same -- remove the entry, or use a genuinely untracked path instead of
hiding work under a real source directory.

```python
# frob/gates/__init__.py
def run_gates(cfg: GateConfig) -> Result[GateReport, GateError]
    # Orchestrates all gates (parallel where independent) over one
    # GraphSnapshot + TicketQueue + diff; single entry for check_runner.

def drift_gate(snapshot: GraphSnapshot, lock: LockFile) -> tuple[Violation, ...]
def coverage_gate(snapshot: GraphSnapshot, queue: TicketQueue,
                  diff: Diff, tests: CollectedTests) -> tuple[Violation, ...]
def scope_gate(diff: Diff, ticket: Ticket, snapshot: GraphSnapshot, *,
               root: Path | None = None,
               queue: TicketQueue | None = None) -> tuple[Violation, ...]
    # SCOPE001. When root/queue are given (run_gates always passes them),
    # a file failing this ticket's own scope is re-checked hunk by hunk via
    # git blame: a hunk is exempt only if every line is already committed
    # (never a dirty/uncommitted line) and every covering commit's subject
    # names another ticket whose own declared scope covers the file (T-0108
    # -- fixes false SCOPE001 on files an earlier ticket already committed
    # on the same branch). Callers omitting root/queue keep the old,
    # unconditional check.
def prework_gate(ticket: Ticket, snapshot: GraphSnapshot,
                 sweep: Option[PreworkSweep] = Nothing()) -> tuple[Violation, ...]
    # PRE001. T-0584: a PARTIAL sweep (gates/_prework.py::sweep_ticket ran
    # out of its bounded budget before finishing every scope pattern) whose
    # digest still matches the ticket's current scope is treated as
    # provisionally clean, not a violation -- otherwise PRE001 would demand
    # completion of the very sweep a slow mount could not finish in one
    # foreground-budget-sized call.
def invariant_gate(invariants: tuple[Invariant, ...], snapshot: GraphSnapshot,
                   tests: CollectedTests) -> tuple[Violation, ...]

def test_gate(snapshot: GraphSnapshot, systems: tuple[SystemSpec, ...],
              coverage: Option[CoverageData], tests: CollectedTests,
              cfg: TestPolicy) -> tuple[Violation, ...]
    # TEST001..TEST006. Interfaces are derived from the snapshot: every
    # package whose public symbols are imported by another package is an
    # interface and owes integration tests. Coverage is consumed as
    # recorded evidence, never produced here.

def stamp_coverage(root: Path) -> Result[Unit, GateError]
    # Called by `make coverage` after pytest-cov: records coverage.xml's
    # sha plus current per-file content hashes into .frob/coverage-stamp.
    # TEST006 compares this stamp against the live snapshot.

def load_coverage(root: Path) -> Result[CoverageData, CoverageError]
    # Parses coverage.xml (branch mode) and maps line hits onto symbol
    # spans from the snapshot -> per-symbol/module percentages.

def active_ticket(root: Path, explicit: str | None) -> Option[str]
    # --ticket flag wins; else branch name matching ^(T-\d{4})- ; else Nothing.
    # Scope/pre-work gates run only when a ticket context exists.

def record_prework(root: Path, ticket_id: str,
                   sweep: PreworkSweep) -> Result[Unit, GateError]
    # `frob ticket start` runs dup+xref over the ticket scope and stores the
    # sweep digest in the ticket body; PRE001 checks its presence.

def sweep_ticket(root: Path, ticket: Ticket,
                 budget_seconds: float | None = DEFAULT_SWEEP_BUDGET_SECONDS
                 ) -> Result[PreworkSweep, GateError]
    # T-0584: bounded and resumable. Times the per-scope-pattern xref loop
    # against `budget_seconds` (None = unbounded, for tests/an explicit full
    # sweep); the dup scan and graph load still run once, unbounded, ahead
    # of it. If the deadline is hit with patterns still remaining, records
    # a `partial=True` sweep with those patterns in `pending_patterns`
    # instead of blocking to completion -- the previous fully-synchronous
    # shape of `frob ticket sweep` (the always-available resweep-after-
    # scope-edit path) could not complete within a slow-mount agent's
    # foreground budget, and PRE001 only ever compared against a fully-
    # completed digest, so the ticket could never get back into a checkable
    # state (the T-0355-item-2 catch-22 this closes). A later call with a
    # matching digest resumes from `pending_patterns` rather than
    # rescanning patterns already swept.

# Diff/working_diff live in frob/gitio.py (the ONE git seam, shared with
# frob.testing -- see docs/modules/testing.md); base default "main", configurable
# [tool.frob] check_base. CollectedTests and its pytest-collection cache
# live in frob.testing and are imported from there.

# frob/policy/__init__.py
def load_policy(root: Path) -> Result[tuple[PolicyRule, ...], PolicyError]
def policy_gate(rules: tuple[PolicyRule, ...], snapshot: GraphSnapshot,
                diff: Diff) -> tuple[Violation, ...]

# frob/gates/invariants.py
def load_invariants(root: Path) -> Result[tuple[Invariant, ...], InvariantError]
```

### ROOT001 (T-1784)

<!-- frob:describes src/frob/gates/_root_asset_dirs.py::root_asset_dir_gate -->

`frob.gates._root_asset_dirs` -- `root_asset_dir_gate` (gate name
`root_asset_dirs`, default-on, WARN severity, waivable). Motivating
incident: the repo-root `agents/`/`skills/` directories were audited
twice with opposite verdicts. The first pass (T-1767) concluded KEEP,
reading the tracked `SKILL.md` files' prose as "empirically confirmed
live-read" because it happened to match this very repo's own
system-prompt role definitions near-verbatim -- a coincidence of
AUTHORSHIP (the harness's real `~/.claude/agents`/`~/.claude/skills`
were almost certainly seeded FROM these files at some point), misread
as proof of a live load path. The second pass (T-1772) corrected it with
a mechanical check: `git grep` across `src/frob/**` for
`agents/`/`skills/` returns nothing, `pyproject.toml` packages `src/`
only, `frob scaffold` does not emit either directory -- nothing in this
repo's own code reads either tree. Deleted. Nothing mechanized that
second, correct verification; this gate is that mechanization.

For every repo-root top-level directory owning at least one git-tracked
file, excluding `src/`/`tests/` (structural), the named allowlist
(`docs/`, `tickets/`, `design/`), and any directory literally referenced
in the repo-root `Makefile`'s text, `root_asset_dir_gate` requires at
least one of:

  (a) this project's own declared source root(s) (`frob.lang.
      declared_source_prefixes`, T-2389 -- `src/frob/**` in this repo,
      resolved rather than hardcoded so an off-repo, differently-named
      `src/<pkg>/**` project is scanned correctly too; `UNRESOLVED`, not
      a silent clean pass, if `pyproject.toml` cannot be read) reference
      the directory's name literally as a `"name/"`-shaped path token
      (scans every tracked file under that prefix, so `frob.scaffold`'s
      own non-Python template/data assets count too, not only `.py`
      sources).
  (b) `pyproject.toml`'s own text references the directory's name.
  (c) a tracked markdown file carries an explicit
      `<!-- frob:external-reader dir="name" reason="..." -->`
      declaration -- a real, checkable claim that some process OUTSIDE
      this repo's own code reads it (the harness-config case), instead
      of an inferred one. This directive is a dedicated regex this gate
      recognizes, not routed through the full `frob.graph.dsl` edge
      machinery -- a repo-root directory audit is rare enough (a few
      times a year, per the T-1611 history above) that a dedicated DSL
      edge kind is not worth the maintenance surface yet.

A directory satisfying none of these is flagged WARN, never auto-deleted
-- the next audit starts from a measured "zero code references" fact
instead of re-deriving it from scratch and risking the same
name-matching mistake T-1767 made.

### ENV001 (T-1782)

<!-- frob:describes src/frob/gates/_env_var_docs.py::env_var_doc_gate -->

`frob.gates._env_var_docs` -- `env_var_doc_gate` (gate name
`env_var_docs`, default-on, WARN severity, waivable). Motivating
incident: T-1610's docs-completeness sweep found
`FROB_WORKER_STDOUT_LOG_LEVEL` (T-0806) undocumented anywhere in `docs/`
for roughly two weeks. `SEC110` already fires on this exact env-var
read, but it asks "is this a secret needing a `std.secrets` registry
mapping" -- a different question than "does this operational env var
have user-facing documentation"; the SEC110 waiver ("worker log-level
marker, not a secret") does not cover the doc-coverage obligation at
all. `COV001`/`COV007` do not apply either: the backing constant is
normally private, and this repo's own COV007 convention is that private
symbols do NOT carry a `frob:doc` anchor by default -- so an
operationally user-facing `FROB_*` env var implemented as a private
constant was structurally invisible to every existing doc-coverage gate.

`env_var_doc_gate` enumerates every string-literal constant ASSIGNMENT
under this project's own declared source root(s) (`frob.lang.
declared_source_prefixes`, T-2389 -- resolved from `pyproject.toml`'s
`[project].name` plus its declared `src`-layout roots, e.g. `src/frob/`
in this repo; `UNRESOLVED`, not a silent clean pass, if `pyproject.toml`
cannot be read) whose value is prefixed with this project's own
uppercased package name plus `_` (e.g. `FROB_` here; derived, not a
hardcoded literal, so a differently-named project off this repo gets its
own correct prefix instead of being silently skipped) and requires each
to either:

  (a) appear literally (the `FROB_...` string) or by its owning Python
      constant name in some tracked file under `docs/` -- the
      "documented by constant name, not literal string" allowance
      T-1610's own audit already established as adequate (the
      `FROB_PARSE_ARTIFACT_CACHE` precedent), or
  (b) carry a `frob:waive ENV001 reason="..."` directive anywhere in the
      same source file -- file-scoped (`_match_waiver`'s ordinary
      symref-less matching mode), not per-constant: a file grouping
      several genuinely internal/test-only/worker-internal `FROB_*`
      constants together can waive them all with one directive.

### NATIVE001 (T-1148)

<!-- frob:describes src/frob/gates/__init__.py::_native_unavailable_report -->
<!-- frob:describes src/frob/strata/_native_staleness.py::unimportable_natives -->
<!-- frob:describes src/frob/strata/_native_staleness.py::native_unavailable_warning -->

2026-07-28 incident: a root `uv sync` reinstalled `frob` without its
compiled native extensions (`strata_core`/`frob_core`). The next `frob
check` produced 43 `DRIFT002` "no candidates" errors, one per
`design/frob.strata` node -- misattributed to design/doc drift, and only
diagnosed via a coordinator's memory of the worktree-natives artifact
(the same class of confusion `docs/guides/agent-playbook.md`'s "worktree
natives artifact" note exists to short-circuit). The actual cause was one
level up: `design/frob.strata` could not even be PARSED because
`strata_core` failed to import, so every symbol/edge that would normally
resolve through it looked dangling instead of "graph unavailable."

`stale_natives` (T-0248) already compares a BUILT native's mtime/content
against its own source tree, but deliberately treats a completely
unbuilt/unimportable native as out of its scope (`_artifact_mtime`
returns `None` for one, the same "nothing to compare against" posture
`missing_natives`, T-0333's TEST-collection-side sibling, already takes)
-- neither one names the "declared but currently unimportable" case with
a single, fail-fast diagnostic before the rest of the gate pipeline runs.

`frob.strata._native_staleness.unimportable_natives` closes that gap:
for every declared `[[native]]`, attempt `importlib.import_module`
directly (not just `find_spec`, since a partially-installed extension can
resolve a spec that still fails at actual import time) and report every
one that fails. `native_unavailable_warning` renders the human message
(native names + `run: uv run frob natives build`).

`run_gates`'s `_native_unavailable_report` (`frob.gates.__init__`) calls
this FIRST, before `_load_inputs` builds the graph/design/ticket state
every other gate depends on: if any declared native is unimportable, it
short-circuits with a `GateReport` containing exactly ONE `NATIVE001`
ERROR violation naming the broken native(s) and the fix command, and
skips every other gate for that run entirely -- the misattributed
cascade (DRIFT002 and anything else that would have looked at a graph
built from a design file that could not even parse) never has a chance
to fire. A healthy checkout (every declared native imports cleanly, or
none are declared at all) is entirely unaffected: `_native_unavailable_
report` returns `None` and `run_gates` proceeds through its normal
pipeline exactly as before this ticket.

### NATIVE001 auto-rebuild (T-1213)

<!-- frob:describes src/frob/gates/__init__.py::NATIVE_AUTOREBUILD_DISABLE_ENV -->

T-1148 above made a broken native fail fast and honestly, but the FIX was
still always manual: a human ran `make core`/`frob natives build` after
reading the NATIVE001 reminder. This is the recurring worktree-natives
false-failure class (`docs/guides/agent-playbook.md`'s "worktree natives
artifact" note) automated away: `_run_gates_bounded` calls
`_maybe_autorebuild_natives(root)` immediately BEFORE
`_native_unavailable_report` runs. Whenever `frob.strata.stale_natives`
(a source-newer-than-artifact native, T-0248) or `unimportable_natives`
(an entirely unbuilt-but-buildable one, T-1148) reports anything, it
attempts `frob.natives._build.build_natives(root)` right there -- T-0732's
shared `CARGO_TARGET_DIR` makes a warm rebuild ~11s, not a multi-minute
cold build -- and logs the attempt and its outcome loudly via
`_log.warning` either way.

This is deliberately fail-closed, never fail-open: a rebuild that could
not run at all (an infra-level `Err`, e.g. the exec kill switch or a
missing toolchain surfacing through `build_natives`'s own documented
`FileNotFoundError` skip) or that ran but left a crate failing
(`CrateBuildResult.ok is False`) simply logs and returns -- the very NEXT
line (`_native_unavailable_report`) still runs its UNCHANGED fail-closed
NATIVE001 check and reports exactly as it did before this ticket. Only a
genuinely SUCCESSFUL rebuild changes the outcome: the next check now sees
a fresh artifact and reports nothing.

Two opt-outs, both read by `_native_autorebuild_disabled`: the
`FROB_NO_NATIVE_AUTOREBUILD` env var (any non-empty value), or a repo's
own `frob.toml` top-level `natives_auto_rebuild = false`. Either skips
straight through to the old reminder-only NATIVE001 behavior -- useful
for a CI runner or sandbox that intentionally wants a stale/missing
native to fail loudly rather than pay a rebuild inline.

### Perf-reach content-staleness signal + land preflight (T-1578)

<!-- frob:describes src/frob/gates/__init__.py::_perf_reach_degraded_marker -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_worktree_natives_verifiably_healthy -->

NATIVE001 (above) only ever detects an UNIMPORTABLE native -- a `frob_
core` that is CONTENT-STALE (source edited, artifact not rebuilt) but
still loads fine is invisible to it, yet `frob.graph.callgraph`'s native
fast path can still be resolving call edges against outdated compiled
logic. This mattered for real: `frob.perf`'s reach-dependent rules
(PERF008/PERF012, `frob.perf._loop_effects`/`_dup_spawn`) walk that same
call graph, and every land's pre-land Tier-A pass runs `fix_
waive004_stale_waiver`'s self-manufactured `run_gates()` inside the
WORKTREE, where a stale `frob_core` is common -- the reach substrate then
silently under-reports PERF008/PERF012 findings to zero, and only
T-1323's mass-invalidation COUNT heuristic (above, in the `--fix` Tier-A
section) saved live waivers from being misread as stale.

**T-1620 widened the structural signal beyond `frob_core`.** The
original T-1578 marker checked ONLY `frob_core` staleness, on the theory
that `perf_gate`'s own natively-independent rules (PERF001-004) "stay
fully trustworthy" regardless. That theory missed that every perf rule's
INPUT -- not just PERF008/012's reach analysis -- passes through `frob.
lang.parse_file`'s tree-sitter grammar, which is `strata_core`, a
DIFFERENT native than the one T-1578 watched. Measured 2026-08-05: a
worktree with a stale `strata_core` read ZERO PERF004 findings
repo-wide while this marker (frob_core-only at the time) reported
healthy, and the resulting land deleted 55 live waivers T-1323's own
mass-invalidation guard should have caught. `_perf_reach_degraded_marker`
now checks `frob.strata.stale_natives` against BOTH declared natives
(`_PERF_REACH_NATIVE_NAMES = {"frob_core", "strata_core"}`) -- either one
stale trips the same `PERF_REACH_DEGRADED_SKIP_MARKER` signal.

**T-1620 also closed a second, independent hole**: T-1323's own
mass-invalidation guard (`_WAIVE004_MASS_INVALIDATION_THRESHOLD = 5`, in
the `--fix` Tier-A section above) is an ABSOLUTE count, structurally
blind to any rule with fewer than 5 live waivers -- a rule with exactly 2
live waivers can never reach 5 candidates no matter how degraded the run
is, so both waivers pass through silently (the 2026-08-05 incident's own
4-waiver DEPR005/DEAD001 residue). `_mass_invalidation_rules` now ALSO
flags the PROPORTIONAL case -- every one of a rule's live waivers
(`frob.gates._waive._waivers_by_rule` over a fresh snapshot,
`_live_waiver_counts`) going stale in the same run -- independent of the
absolute count: 2 of 2 is the same T-1323 incident signature as 40 of 40,
not weaker evidence for having fewer waivers to begin with.

<!-- frob:describes src/frob/gates/_fix_engine_sync.py::_WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT -->

**T-1886 added a minimum-sample-size floor to the PROPORTIONAL check.**
`_mass_invalidation_rules`'s proportional trigger ("every one of this
rule's live waivers went stale together") is a sample-size argument, and
like any sample-size argument it has no discriminating power at N=1: a
rule with exactly one live `frob:waive` directive reads as "100% went
stale" the instant that single waiver is genuinely dead -- indistinguishable
from a degraded run by construction, and not a rare edge case, since a
repo having exactly one live waiver for some rule is an entirely ordinary
state. `_WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT = 2`
(`src/frob/gates/_fix_engine_sync.py`) mirrors the `_DEFLATION_MIN_KNOWN_
MODULES` precedent (`frob.gates._coverage`): below the floor, the
proportional check simply does not fire, and the deletion falls through
to the absolute-threshold check alone (still refusing at >= 5 candidates
for that rule, same as before). At or above the floor the check keeps its
full bite unchanged -- 2-of-2 and up still trip it exactly as before; only
the N=1 case is excluded.

**Read the guards below as deliberate, not incomplete.** Both the
absolute-count guard (`_WAIVE004_MASS_INVALIDATION_THRESHOLD`) and the
proportional guard above are UNCONDITIONAL refusals once tripped -- they
delete nothing for the flagged rule, full stop, even when a human is
confident the waivers really are dead. That is the deliberate post-incident
state, not an oversight to "fix" by adding an escape hatch back in.
`_rule_has_live_finding` was exactly such an escape hatch (T-1579, "a live
finding of the rule elsewhere in the run proves the detector ran"): it
shipped, and during a real land it deleted 55 live waivers, because a
partially-degraded run (stale `strata_core`, every structural health check
reporting clean) still found some instances of a rule lexically while
missing the exact sites the waivers covered. It was reverted (T-1592); see
the T-1323 incident writeup below for the full history, and
`tests/test_gates.py::TestWaive004DegradedRunGuard::
test_mass_invalidation_with_live_finding_elsewhere_still_refuses` locks
against its return. The N=1 floor above does not reopen that hole -- it
only stops the proportional check from firing where it structurally
carries no signal at all; it does not add a way past the check once it
DOES fire. A correct escape needs per-site analysis-coverage proof, not a
same-run elsewhere-finding proxy -- that successor design is T-1904; T-1942
built its first consumer (archgate family only, see the WAIVE004 Tier-A
fix-handler section below for the wiring writeup).

Two-layer fix, matching the two places this gap actually bites:

1. **Structural signal** (`docs/modules/perf.md#perf-reach-native-staleness-signal-t-1578`
   has the full writeup, not yet updated for the T-1620 native-name
   widening above -- see that ticket's filed follow-up): `_perf_reach_
   degraded_marker` (`frob.gates.__init__`) checks `frob.strata.
   stale_natives` for either declared reach-adjacent native, AFTER
   `_maybe_autorebuild_natives` already had its chance to fix it --
   `_build_jobs` appends its `PERF_REACH_DEGRADED_SKIP_MARKER` name to
   `GateStats.skipped` whenever `perf` is a selected gate and this
   fires, so `_fix_engine._degraded_verification_reason`'s existing
   "unexpected skip" branch (T-1323) now also catches this case --
   "zero findings" and "could not analyze" become distinguishable for
   every perf rule, reach-dependent or not.
2. **Land preflight**: `_worktree_natives_verifiably_healthy`
   (`src/frob/app/ticket_runner/_land_cmd.py`) runs the SAME auto-rebuild
   attempt `run_gates` itself would, then checks every declared native
   for staleness/importability directly -- `_tier_a_pre_land_step` calls
   this BEFORE `apply_tier_a_fixes`, and excludes `WAIVE004` from that
   land's Tier-A batch entirely when it says no, at `_log.info` level.
   This produces the IDENTICAL outcome `fix_waive004_stale_waiver`'s own
   guards would have produced anyway (nothing deleted) -- but without
   paying for a full, guaranteed-untrustworthy `run_gates()` pass first,
   and without the scary per-land ERROR log that outcome used to leave
   behind.

## Invariants

<!-- frob:describes src/frob/gates/invariants.py::_Criticality -->
<!-- frob:describes src/frob/gates/invariants.py::Invariant -->
<!-- frob:describes src/frob/gates/invariants.py::InvariantError -->

- `Criticality` -- how severe a broken invariant would be (`high` |
  `medium`); feeds severity weighting in INV001/INV002 reporting.
- `Invariant` -- one tracked invariant: id, statement, criticality, and
  its evidence list, parsed from `invariants/INV-###.md`.
- `InvariantError` -- failure values `load_invariants` can return
  (malformed frontmatter, duplicate id).

"Proving things that matter": an invariant is a tracked statement whose
truth must have standing evidence. Files in `invariants/INV-###.md`:

```markdown
---
id: INV-007
statement: Lock writes are atomic; a crashed frob never truncates frob.lock
criticality: high             # high|medium
evidence:
  - tests/test_lock.py::test_write_atomic_under_kill   # pytest node id
  - POL-no-direct-lock-write                            # or a policy rule id
---
Rationale and threat model prose here.
```

INV001/INV002 close the loop: every invariant is anchored in code
(`frob:invariant INV-007` at the enforcing site) and backed by evidence
that `frob check` verifies still exists (test collected, rule loaded).
Security work becomes monotonic: each audit finding lands as an invariant
plus a policy rule or property test, never a one-off fix.

### INV003 (T-0462)

<!-- frob:describes src/frob/gates/invariants.py::find_exclusivity_claims -->
<!-- frob:describes src/frob/gates/invariants.py::EXCLUSIVITY_CLAIM_PATTERNS -->
<!-- frob:describes src/frob/gates/_inv.py::inv003_gate -->

INV001/INV002 close the loop for invariants that already got written down
in `invariants/INV-###.md`. INV003 catches the earlier failure mode: prose
in `docs/**.md` asserting an exclusivity/normative claim -- "only",
"sole"/"solely", "exclusively", "nothing else", "never...except",
"at most/exactly one" (`find_exclusivity_claims`,
`EXCLUSIVITY_CLAIM_PATTERNS`) -- with nothing tracking whether it still
holds. A doc file making such a claim needs a
`<!-- frob:invariant INV-### -->` marker somewhere in the same file
naming a real, loaded invariant; a marker naming an unknown id does not
count (`inv003_gate`).

INV003 is `Severity.WARN`, not `ERROR` like INV001/INV002: even after
calibration (below) a claim can be genuine design intent rather than an
enforced behavior, so WARN surfaces the signal for human triage rather
than forcing a bind-or-waive on every hit.

**T-0509 calibration.** The original bare-vocabulary scan surfaced ~90
INV003 findings (and ~677 INV004 findings, see below) across `docs/` --
mostly headings, table cells, code samples, and link text carrying the
trigger word with no actual claim attached (a `## Schema` heading, a
`| only |` table cell). Three changes narrow this to a genuinely
reviewable pool without dropping real claims:

- **Noise stripping** (`frob.gates.invariants._strip_markdown_noise`):
  fenced code blocks, inline code spans, markdown link targets, and table
  rows are removed before scanning -- code samples and URLs are not prose
  assertions.
- **Claim-shape requirement** (`_is_claim_shaped`, `_CLAIM_VERB_RE`): a
  trigger word only counts if a claim-verb (`is`/`must`/`supports`/`writes`/
  etc.) appears in the SAME sentence -- a bare heading or dangling noun
  phrase asserts nothing regardless of vocabulary.
- **Directory scoping** (`INV003_SPEC_DIRS = ("docs/modules", "docs/strata")`):
  INV003 only runs over these two spec-normative trees, not all of
  `docs/**.md` -- exclusivity claims worth gating describe enforced
  contracts, which is what those trees are for; a narrative design doc or
  changelog making a passing "only" remark is a different failure mode
  than T-0462 named. INV004 (below) still runs over all of `docs/`.

Markdown-side `frob:waive` support now also exists (`_match_waiver` keys
off graph edges, which doc prose still carries none of -- this is a
separate marker): `<!-- frob:waive INV003 reason="..." -->` anywhere in a
file dispositions that file's INV003 findings, same honesty requirement
as the code-side `frob:waive`'s WAIVE001 (a marker with no `reason=` is
not honored). Applied from `inv003_gate` via
`_file_has_reasoned_doc_waiver` rather than inside `_inv003_doc_violations`
itself -- see that helper's docstring for why (a COV005 false-positive
this repo hit once already, from directive-target reuse across public
and private symbols in the same file).

Net effect measured on this repo after T-0509 (`frob check --only
invariant`): INV003+INV004 combined, 765 -> 604 warnings (INV003 88 ->
31, INV004 677 -> 573). The residual was tracked as a follow-up burndown
ticket rather than hand-closed in one pass; see the INV004 section below
for T-0515's further calibration of that residual.

**T-1649 (PERF011 fix):** `inv003_gate`/`inv004_gate` used to call
`iter_files` once PER `INV003_SPEC_DIRS` entry (2 directories), re-
scanning the whole repo twice for a fixed, small tuple both gates already
hold in full. `_spec_dir_md_files` (`src/frob/gates/_inv.py`) now runs
one `iter_files(root, suffix=".md")` scan and filters its result to paths
under any `INV003_SPEC_DIRS` prefix, shared by both gates -- same
findings, one full-repo scan instead of two.

### INV004 (T-0452, T-0515)

<!-- frob:describes src/frob/gates/invariants.py::find_normative_claims -->
<!-- frob:describes src/frob/gates/invariants.py::NORMATIVE_CLAIM_PATTERNS -->
<!-- frob:describes src/frob/gates/_inv.py::inv004_gate -->

INV003 is a per-CLAIM lint: one specific exclusivity assertion needs one
specific bound invariant. INV004 is the INVERSE, FILE-level signal: a
doc file using ANY normative language at all -- `must`, `must not`,
`never`, `always`, `shall`, `guarantees`, `ensures`, `requires`, plus
INV003's exclusivity vocabulary (`NORMATIVE_CLAIM_PATTERNS`,
`find_normative_claims`) -- but anchoring ZERO `<!-- frob:invariant
INV-### -->` markers anywhere in the FILE (unlike INV003, a marker naming
an unknown id still counts here -- INV004 only asks "is *anything*
tracked here") is flagged as a likely under-specified doc: the "silence"
a per-claim lint can't see, because there is no single explicit claim to
anchor on.

Always `Severity.WARN` -- advisory by design, a suggestion to formalize
rather than a broken obligation; INV004 does not fail `frob check`.

INV004 shares INV003's T-0509 noise-stripping and claim-shape scan
(`find_normative_claims` calls the same `_claim_shaped_sentences`
preprocessing as `find_exclusivity_claims`).

**T-0515 calibration.** After T-0509, INV004 was still section-level
(`_markdown_sections`) and ran over all of `docs/**.md`, and its 573
residual warnings dwarfed INV003's 31 -- mostly many hits per file for a
handful of entirely-unbound docs, not 573 distinct under-specified
regions worth separate triage. Two changes, mirroring INV003's own T-0509
rationale:

- **File granularity, not per-section** (`_inv004_doc_violations`): one
  advisory per file (a doc large enough to need section-level invariant
  tracking should already be split into `invariants/INV-###.md` entries),
  not one per ATX section.
- **Directory scoping** (`INV003_SPEC_DIRS`, shared with INV003): INV004
  now runs only over `docs/modules` and `docs/strata`, not all of
  `docs/**.md` -- a narrative design/audit/guide doc using "must" or
  "always" in passing is a different failure mode than an
  enforced-contract doc with zero bound invariants at all.

A file-scoped markdown `frob:waive` marker
(`<!-- frob:waive INV004 reason="..." -->` anywhere in the file, applied
via `_file_has_reasoned_doc_waiver` from `inv004_gate`, the same helper
INV003 uses) dispositions one under-specified file without a fake bound
invariant.

Net effect measured on this repo (`frob check --only invariant`):
INV003+INV004 combined, 604 -> 63 warnings (INV003 unchanged at 30,
INV004 573 -> 33). The residual 63 spans 33 files under `docs/modules`
and `docs/strata` that assert real behavior with no invariant bound at
all yet; each needs individual triage (bind a real invariant, reword, or
waive with a specific reason) rather than a blanket disposition -- tracked
as a further follow-up ticket rather than hand-closed in this pass.

### INV005 (T-0543)

<!-- frob:describes src/frob/gates/_inv.py::_invariant_evidence_proves_anchor -->
<!-- frob:describes src/frob/gates/_inv.py::_evidence_binds_to_symrefs -->

INV001 only asks whether an invariant's evidence list contains AT LEAST
ONE item that resolves to a collected test node id (or a loaded policy
rule id) -- existence, not proof: `def test_x(): pass`, bound to nothing,
anywhere in the repo, cleared it. INV005 is the same remedy family as
COV006/D-02's `evidence_covers_scope`: when the invariant HAS a
`frob:invariant` anchor, and evidence collected but NONE of it is shown to
actually bind to that anchor (a `frob:tests` edge either direction, or the
evidence test living in the same file as the anchor), INV005 fires.

Deliberately `Severity.WARN`, not a tightened INV001: this repo's own
`invariants/` directory already has evidence entries written before any
edge/same-file binding convention existed (17 invariants at the time this
gate was added), and forcing them all through a binding-proof pass in one
ticket was out of budget -- the same "large, needs its own dedicated
follow-up" shape as the parallel B1 (TEST001 real-coverage) and B2
(DRIFT001 body facet) gates-accounting findings. INV001/INV002 keep their
prior ERROR semantics unchanged; INV005 is the loud-but-non-blocking nudge
toward a real binding for anything NEW.

### INV006 -- DELETED (T-0408 -> T-1763)

INV006 (source-side exclusivity-claim scan, `src`/`strata-core/src`/
`frob-core/src`, the sibling of the INV003/INV004 doc-side scans above)
was DELETED by T-1763. Measured against frob's own corpus at deletion
time: 349 files carrying a `frob:waive INV006 reason="..."` directive,
and ZERO unwaived findings across the rule's entire lifetime (T-0408
onward) -- it never once produced a finding a human judged worth binding
a real `frob:invariant` to.

Root cause: INV006 was a purely LEXICAL scan (the same claim vocabulary
INV003 uses -- "never"/"only"/"always" in a claim-shaped sentence) with
no notion of symbol or cross-module scope, applied unconditionally to
every source file's own docstrings and comments. Ordinary, correct
documentation of a module's OWN internal behavior triggers the identical
vocabulary a genuine undeclared cross-module contract would -- INV006
could not tell the two apart, and 338 of its 349 waivers said so, in
near-identical words, one file at a time. It had already fired on a
`frob:waive` directive's own `reason="..."` prose EXPLAINING a previous
INV006 misfire (T-1640's fix narrowed the scan to exclude directive
attribute text, but did not change the underlying lexical-vs-semantic
defect). `frob:invariant`/INV001/INV002 already bind real invariants to
real evidence; INV006 added hundreds of hand-written waiver
justifications on top of a detector that never earned them.

T-1763 swept all 349 `frob:waive INV006 reason="..."`/`preset="..."`
directives before deleting the gate -- a dead directive naming a deleted
rule reads as a live suppression to the next reader, which is worse than
no directive at all. <!-- frob:waive DOC006 reason="deliberately historical -- this section documents the deletion of INV006 and its helpers, the sentence explicitly says they were removed" -->`frob.gates._inv006_split_assist` (the T-1134
split-carry helper, INV006-only) and its `fix_inv006_carried_waiver`
Tier-A auto-fix handler (`frob.gates._fix_engine`) were deleted along
with it. See `frob.gates._inv`'s own module docstring for the same note
at the code level.

### INV007 and INV008 (T-0757)

INV001-INV006 (above) are all about whether a DECLARED invariant has
evidence, an anchor, or a bound doc claim -- none of them can express a
design invariant of the shape "module X must never import Y" or "this
property must be established by a real test, not an example". Both
shapes existed only as PROSE two known incidents ever caught: T-0611 (a
`TypeScriptAdapter` landed inside the deliberately tree_sitter-free
`src/frob/arch/_normalized.py`, caught by a human reviewer reading the
diff) and T-0682 (`frob.tickets._land_ledger_merge._newer`'s qualified richness
ordering got fixed wrong in the opposite direction from the bug it was
fixing, twice, because the property lived only in a reviewer's head).
T-0757 extends the SAME `frob:invariant` directive with two OPTIONAL
obligation attrs (`frob.graph.dsl`'s `_attrs_verb_error_invariant`) so
both incident classes become static gate findings instead of review
catches -- a bare `frob:invariant INV-###` with neither attr is
unaffected.

**INV007 (import-forbidding).** `frob:invariant INV-### no_import=
"pkg[,pkg2,...]"`, anchored anywhere in a file (or on a symbol inside
it -- INV007's scan is always file-level, so only the enclosing file
matters), declares that file must never import `pkg` or any of `pkg`'s
submodules. `frob.gates._design_invariants.inv007_violations` reads the
file's own RAW import specifiers via `frob.lang.extract_imports` (the
same primitive `frob.arch._smells`/`frob.arch._layering` already use for
project-wide import graphs, T-0625/T-0620) and reports an ERROR the
instant any specifier equals the forbidden module or starts with
`"{forbidden}."` -- a prefix match on `.` boundaries, so a lookalike name
like `tree_sitter_python` does not false-positive against `no_import=
"tree_sitter"`. `src/frob/arch/_normalized.py` carries `frob:invariant
INV-042 no_import="tree_sitter"` as the seeded T-0611 case
(`invariants/INV-042.md`).

**INV008 (establish-property).** `frob:invariant INV-### establishes=
"<property text>"`, anchored on the symbol whose property must hold,
requires a `frob:tests ... kind="property"` edge (T-0757 widens
`frob.graph.dsl._TESTS_KINDS` to include `"property"`, joining `"unit"`/
`"integration"`/`"e2e"`) reaching that same anchor, from either
direction -- mirroring INV005's own either-side `TESTS`-edge walk
(`frob.gates._inv._evidence_binds_to_symrefs`). A bound test declared at any
OTHER kind (or no bound test at all) does not satisfy it: the point is
that the evidence must be declared as exercising the property SPACE (a
comparator's ordering, a round-trip, a monotonicity claim), not one
fixed input. `frob.gates._design_invariants.inv008_violations` reports
an ERROR per unbound `establishes=` anchor. `src/frob/tickets/_land.py`'s
`_newer` carries `frob:invariant INV-043 establishes="..."` as the
seeded T-0682 case (`invariants/INV-043.md`), bound to a Hypothesis
property test (`TestNewerWinnerQualifiedPreferenceProperty`, `tests/
test_ticket_land.py`) proving the qualified richness rule exhaustively
over the small state space `_newer_winner` discriminates on, rather than
the hand-picked field-incident cases `TestSpliceLedgerRicherStatePreference`
already covers.

Both rules ship at `Severity.ERROR` directly, unlike INV003/INV004's
advisory WARN posture (INV006, the third rule in that advisory-WARN
class, was deleted by T-1763): an obligation only exists once someone
EXPLICITLY writes `no_import=`/`establishes=` on a `frob:invariant`
directive (never a bare-vocabulary heuristic scanning every file), so
there is no first-turn-on debt corpus to phase in against -- the first
two anchors this repo carries (INV-042/INV-043) are the two ERROR-clean
seeded cases above.

## Policy rules (`frob.toml`, `[policy]`)

<!-- frob:describes src/frob/policy/_models.py::PolicyKind -->
<!-- frob:describes src/frob/policy/_models.py::PolicyRule -->

- `PolicyKind` -- the three rule kinds `frob.toml`'s `[policy]` table
  supports at alpha: `forbidden-import`, `pattern`, `norm`.
- `PolicyRule` -- one `[[policy.<kind>]]` entry; fields not used by its
  `kind` are left at their default.

```toml
[[policy.forbidden-import]]
id = "POL-no-requests-in-core"
module = "requests"
within = "src/frob/graph/**"
reason = "graph must stay offline-pure"

[[policy.pattern]]
id = "POL-no-subprocess-shell"
language = "python"
query = "(call ...)"          # tree-sitter query, file in policy/queries/
severity = "error"

[[policy.norm]]
id = "POL-max-diff-lines"
max_diff_lines = 400          # per active ticket; restraint merges
```

Three rule kinds at alpha: `forbidden-import`, `pattern` (tree-sitter query
over `frob.lang` trees), and `norm` (diff-shape rules). Taint analysis is
explicitly out of scope for 0.1.0.

## Test obligations (`frob.toml`, `[testing]` and `[[system]]`)

```toml
[testing]
min_unit_cases = 3            # TEST002: unit edges per public symbol
min_integration = 1           # TEST003: integration edges per interface
unit_branch_cov = 90          # TEST005: per-symbol branch coverage floor
module_line_cov = 85          # TEST005: per-module line coverage floor
system_line_cov = 80          # TEST005: per-system line coverage floor

[[system]]
id = "cli-check"              # target of frob:tests <id> kind="e2e"
entrypoint = "frob check"     # documentation; e2e tests drive it via subprocess
min_e2e = 5                   # TEST004
paths = ["src/frob/check/**", "src/frob/gates/**"]   # system_line_cov scope
```

Binding is explicit: a test declares what it tests via `frob:tests`
directives (see docs/modules/graph.md); the gate verifies the declared node ids are
actually collected by pytest, so a deleted test cannot keep satisfying an
obligation. Coverage is recorded evidence: `make coverage` runs pytest-cov
then `stamp_coverage`; `frob check` only reads the stamp and coverage.xml.
A stale or missing stamp is itself a violation (TEST006) -- the gate never
silently passes because tests were not run.

## Delta baseline (agent workflow, T-0095/T-0107)

`frob check` reports every kept violation on every run -- most of them
pre-existing legacy debt (ticketed, not new), not signal for the agent
driving one ticket to green. `stamp_baseline` records the current
violation set's fingerprints (rule + file + message digest, via
`violation_fingerprint`) plus a per-file content hash to `.frob/baseline`.
`delta_violations` filters a later violation set down to fingerprints
absent from that stamp; `is_baseline_stale` detects when any hashed file
has changed since the stamp, the same staleness shape `stamp_coverage`
uses for `.frob/coverage-stamp`.

Wired at the CLI as `frob check --stamp-baseline` (record and exit) and
`frob check --delta` (gates stage reports only new violations; see
docs/commands/check.md). A missing or stale baseline degrades `--delta` to
the full, unfiltered set with a warning -- this is an agent-facing filter
only, opt-in, never a silent narrowing of the human-facing report.

## Ratchet pools (T-0569)

A warn-first detector this repo has turned on more than once (INV 765,
COV ~160, PII 336, DEAD 51 findings at once) needed a hand-managed
calibrate-then-burndown campaign every time: eyeball every finding, waive
the genuine ones, fix or ticket the rest, and hope no NEW finding of the
same shape sneaks in unnoticed among the pile. Ratchet pools (T-0569)
replace that with a self-draining mechanism: freeze the CURRENT findings
of a rule as a tracked baseline, and any finding NOT in that baseline
(i.e. anything new) reports at error severity immediately instead of
quietly joining the warn pile.

`frob.gates._ratchet` (`src/frob/gates/_ratchet.py`) implements the
mechanism as a self-contained, additive module:

- **Storage**: `frob-ratchet.lock.json` at the repo root -- committed to
  git, same "outside `.gitignore`'s reach" posture as
  `frob-coverage.lock.json` (T-0545) -- holds one `RatchetPool` (a
  `rule_id` plus a tuple of `RatchetEntry(key, baselined)`) per rule that
  has ever been snapshotted. `key` is a stable per-finding location
  string (e.g. `path:line`); `baselined` is the date the entry first
  entered the pool.
- **`frob pool snapshot RULE --key KEY [--key KEY ...]`**
  (`snapshot_ratchet`) merges the given keys into `RULE`'s pool: a
  genuinely new key gets stamped with today's date, an already-baselined
  key keeps its ORIGINAL date (re-running snapshot is idempotent, not a
  bulk re-date every time).
- **`frob pool clear RULE --key KEY --reason TEXT`**
  (`clear_ratchet_entry`) is the only way to remove a baselined entry --
  `Err(ClearReasonMissing)` if `--reason` is blank, mirroring the
  `frob:waive` discipline this repo already holds itself to (a suppression
  with no stated reason is a silent discard). This is the TICK004-style
  "eventual disposition" every baselined finding still owes: fix it, then
  clear it, don't leave it frozen forever with no accounting.
- **`resolve_ratchet_severity(rule_id, finding_key, lock)`** is the
  integration point: `"warn"` if `finding_key` is already baselined for
  `rule_id`, `"error"` if it is new. It does not decide WHICH rules are
  ratcheted -- `ratchet_enabled_rules(root)` reads that from `[gates.ratchet]
  rules = [...]` in `frob.toml` (opt-in per rule, empty/absent means no
  rule is ratcheted, matching every other per-section `frob.toml` reader's
  missing-is-default posture, e.g. `load_arch_config`).

**Wired into a live gate (T-0594, DELETED T-1763)**: `INV006`
(`inv006_gate`) used to be the first rule opted into `[gates.ratchet]
rules = ["INV006"]` in this repo's own `frob.toml`. T-1763 deleted the
rule entirely (338 waivers, zero unwaived findings across its whole
lifetime -- see the INV006 section above) -- `[gates.ratchet] rules` is
now empty; no rule is currently ratcheted. The mechanism itself
(`resolve_ratchet_severity`/`ratchet_enabled_rules`/
`frob-ratchet.lock.json`) is unchanged and available for a future rule
to opt into. The storage format, CLI, and severity-resolution
contract are tested against synthetic rule ids in
`tests/test_gates_ratchet.py`/`tests/test_pool_runner.py`; the live-gate
integration itself (opt-in config read, baseline hit stays warn, fresh
finding errors, calibration against this repo's own committed
`frob-ratchet.lock.json`) is tested in `tests/test_gates.py`. Any other
warn-first rule can opt in the same way: add its id to `[gates.ratchet]
rules`, baseline its current findings with `frob pool snapshot`, and call
`resolve_ratchet_severity` at that gate's own severity-decision call
site -- no new mechanism needed.

## `--fix` Tier-A deterministic auto-fix handlers (T-1138)

<!-- frob:describes src/frob/gates/_fix_engine.py::apply_tier_a_fixes -->
<!-- frob:describes src/frob/gates/_fix_engine.py::fix_doc007_dotted_form -->
<!-- frob:describes src/frob/gates/_fix_engine.py::fix_doc002_unique_slug -->
<!-- frob:describes src/frob/gates/_fix_engine.py::fix_tick002_renumber -->
<!-- frob:describes src/frob/gates/_fix_engine_text.py::fix_fmt001_directive_wrap -->
<!-- frob:describes src/frob/gates/_fix_engine_sync.py::fix_reg010_registry_sync -->
<!-- frob:describes src/frob/gates/_fix_engine_sync.py::fix_rel002_release_sync -->
<!-- frob:describes src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver -->
<!-- frob:describes src/frob/gates/_fix_engine_text.py::fix_suppress001_paired_suppression -->
<!-- frob:describes src/frob/gates/_fix_engine.py::TIER_A_HANDLERS -->
<!-- frob:describes src/frob/gates/_fix_engine_sync.py::fix_sys111_capability_ratchet_sync -->
<!-- frob:describes src/frob/gates/_fix_engine_shared.py::FixApplied -->
<!-- frob:describes src/frob/gates/_fix_engine_scope.py::filter_fixes_by_scope_and_lease -->
<!-- frob:describes src/frob/gates/_fix_engine_scope.py::SkippedFix -->

First concrete slice of the T-1137 `--fix` epic ("tiered auto-fix
engine"): `frob.gates._fix_engine` implements exactly the three fix
classes T-1138 scoped in, each a deterministic, semantics-preserving
rewrite with a repeated main-redding incident history behind it (never a
guess, never a waiver insertion):

- **`fix_doc007_dotted_form`**: a `frob:tests` directive whose target
  uses pytest's `Class::method` collect-only separator (DOC007, T-0986)
  where this graph's own convention wants a single `::` then a DOTTED
  `Class.method` qualname -- rewritten in place at its recorded origin
  site. Pure string surgery (`path::Class::method` -> `path::
  Class.method`); a target already in the correct shape is untouched
  (no-op, not an error).
- **`fix_doc002_unique_slug`**: a `frob:doc`/`frob:tests` anchor
  (`<file>#<slug>`) whose slug does not resolve (DOC002) but
  fuzzy-matches (`difflib.get_close_matches`, cutoff 0.6 -- difflib's own
  conventional "plausible typo/rename" threshold) EXACTLY ONE real
  heading/`<a id>` slug in `<file>` is rewritten to that slug. T-1170:
  its lazy call-time slug lookup now imports `_doc_anchor_slugs` from
  `frob.gates._doclink_docanchor` (its new home after the DOC001/DOC002
  gate family split out of `gates/__init__.py`) rather than from the
  parent package directly -- same lazy-import shape, no behavior change.
  Zero or MORE THAN ONE candidate above cutoff is left entirely alone --
  an ambiguous or absent match has no single correct rewrite to make
  automatically, so it stays a normal DOC002 finding (the assisted
  fix-it path, not this ticket's own scope).
- **`fix_tick002_renumber`**: TICK002 (a `T-draft-*` id that survived
  onto the default branch) already prescribes its own remedy in its
  message; this performs exactly that renumber via `frob.tickets.
  _draft_finalize.finalize_draft` (T-1192: moved from `_new_renumber`
  into its own module as LARGE001 residue, same function `frob ticket
  land` calls) for every draft id in the queue while on the default
  branch -- no new renumber logic, just invoking the existing API
  surface. Includes T-1125's prose-reference rewrite automatically,
  since `finalize_draft` -> `renumber_one` already performs it. A no-op
  off the default branch.
- **`fix_tick006_phantom_refile`** (T-1544): TICK006's phantom-citation
  case -- a Done report's "filed" claim whose id resolves to NO ticket
  at all, in either the active ledger or the archive, unlike TICK002's
  survived-draft case above (which has a real ticket to rename FROM).
  Files the real ticket the phantom id was supposed to be, via
  `new_ticket`, with the original claim's own surrounding text quoted
  verbatim in the new ticket's body (the only surviving description of
  the lost work); then rewrites the phantom citation in the CLAIMING
  ticket's own body to the new real id, reusing `_new_renumber.
  _rewrite_body_prose_references` -- the same whole-word prose-citation
  rewrite `renumber_one`/T-1125 already use for a genuine renumber, not
  a second implementation of the same substitution. A no-op whenever
  `new_ticket` itself fails, leaving the phantom citation exactly as
  TICK006 reports it rather than rewriting it to an id that was never
  actually filed.

  **T-2690: three false-positive/blast-radius fixes**, measured against
  a 92% false-positive rate (23/23 triaged auto-filings were bookkeeping
  duplicates of already-completed work):

  1. `ticket_id` (the landing ticket's id, threaded per every other
     handler's own T-1548 convention) now scopes the scan to THAT
     ticket's own Done report alone during a land, never the whole
     active queue -- before this, a land's pre-land Tier-A pass
     re-scanned every ticket mirrored into the worktree's ledger
     (T-2563's fleet-wide mirror) for phantom citations regardless of
     relevance, so a stale citation in an unrelated, already-landed
     ticket B got processed (and could fail noisily) during ticket A's
     land. `ticket_id=None` (bare `frob check --fix`) still scans the
     whole queue, unchanged.
  2. `_resolve_via_git_rename` checks git's own history (`tickets/<id>/`
     is `git mv`-renamed by `frob ticket renumber`'s v2 path) for every
     candidate BEFORE treating it as phantom -- a draft id that was
     genuinely renamed to a real successor is recoverable directly from
     git, the actual "renumber map" this repo has, since a ledger
     snapshot (even the T-2400 merge-target-unioned one) structurally
     cannot contain a rename's source name. This was the dominant
     false-positive shape measured: a draft filed on a PARENT ticket's
     worktree branch, cited from a SIBLING branch that copied the
     citation before the parent's land renumbered it.
  3. `_find_exact_duplicate` (the SAME check `new_ticket`'s own
     `DuplicateTicket` refusal performs, reused rather than
     reimplemented) is checked before every `new_ticket` attempt -- a
     phantom already recovered by an earlier pass (the recovery
     ticket's title is fully deterministic) has its citation rewritten
     to the EXISTING recovery ticket instead of repeating an identical
     failed `new_ticket` call, and leaving an identical unrewritten
     citation, on every subsequent land. This is the "refusing to file
     ... already has this exact title" noise that was once
     misdiagnosed as land lock contention -- unlike contention,
     retrying a duplicate-title refusal never clears it.

  **T-2702: both of T-2690's OWN mechanisms failed in production,
  under real concurrent-land git contention** -- two more recovery
  tickets were auto-filed by lands that PROVABLY contained the T-2690
  fix (T-2699, T-2701). Root cause A: `_resolve_via_git_rename`'s
  underlying git spawn can genuinely fail or time out, and T-2690
  collapsed that failure into the identical `None` a real non-rename
  returns -- unsafe, and it directly contradicted this same module's
  own `MergeTargetKnownIds.measured=False` doctrine everywhere else.
  `_resolve_via_git_rename_measured` now returns `(resolved_id,
  measured)`; an unmeasured lookup refuses to file anything this pass
  rather than treat the failure as confirmation. Root cause B:
  `_find_exact_duplicate` read only the calling land's own (possibly
  stale, pre-cut) worktree ledger -- a byte-identical recovery ticket
  a SIBLING land had already filed on the real merge target seconds
  to minutes earlier was invisible to it. `MergeTargetKnownIds` gains
  a `root` field (the merge target's own checkout path); the
  duplicate check now ALSO reads that root fresh, closing the race.

  **T-3108: a THIRD, independent false-positive source from the same
  92% class** -- T-2400's `merge_target_ids` widened resolution to
  `main`'s own LANDED ledger, but an id minted inside a sibling
  worktree is invisible on `main` until that worktree lands (T-2197);
  a Done report in worktree A citing an id worktree B minted, while B
  is still in flight, read as phantom to every prior view and got
  auto-filed as a duplicate of B's own active, non-terminal work
  (measured: T-3100/T-3103, duplicating T-3107/T-3106 respectively,
  both real and non-terminal at the time). `_sibling_worktree_known_
  ids` enumerates every OTHER live worktree via `git worktree list
  --porcelain` and best-effort reads its own local ticket queue,
  unioned into `known_ids` alongside the archive and merge-target
  views -- a worktree that cannot be read (mid-removal, pruned, gone)
  just contributes nothing, since this is a pure WIDENING source and
  can only ever prevent a false phantom, never manufacture a false
  "known".

T-1261 adds a second batch of four Tier-A handlers, none of which invent
new rewrite logic -- each rule already names its own remedy verbatim in
its finding message, so the handler just calls that existing remedy:

- **`fix_fmt001_directive_wrap`**: an over-long `frob:` directive comment
  line (FMT001) -- calls `frob.gates._fmt_directives.format_paths` in
  write mode over the whole `root` (idempotent by construction, so this
  IS the fix).
- **`fix_reg010_registry_sync`**: a live gate rule id missing its
  `CHK-GATE-<rule>` entry in `docs/design/registry/check-coverage.yaml`
  (REG010) -- calls `frob.registry._staleness.sync_gate_rule_entries`
  directly (the same function `frob registry audit --sync-gate-rules`
  wraps). REG008 (a stale `handled_by:` cross-ref) is a different,
  genuinely Tier-C shape and is NOT handled here.
- **`fix_rel002_release_sync`**: a derived release artifact
  (`pyproject.toml`/`uv.lock`/`CHANGELOG.md`) disagreeing with
  `.frob-release.json`'s authoritative version (REL002) -- calls the
  existing `frob.release` sync functions directly, the same ones `frob
  release sync`'s CLI dispatches to. Never writes `.frob-release.json`
  itself, only the three derived artifacts.
- **`fix_docenum001_enumerates_sync`** (T-1974): a `frob:enumerates` doc
  anchor's claimed `members="..."` list has drifted from the real
  collection literal it targets (DOCENUM001) -- reuses `frob.gates.
  _docenum`'s own AST resolution to recompute the real member set and
  rewrite the doc line's `members=` attribute in place. Covers every
  `frob:enumerates` edge in the graph, not only the gates.md
  rule-catalog anchor that motivated it -- that anchor alone regressed
  the unscoped floor twice in one session (T-1937 -> T-1958, T-1629's
  SYS110) purely because nothing mechanically kept it in sync with
  `_KNOWN_GATE_RULES`, the same shape REG010's own auto-fix already
  closes for check-coverage.yaml.

  T-1924: `fix_reg010_registry_sync` and `fix_rel002_release_sync` used
  to also declare an unused, non-Optional `GraphSnapshot` parameter
  purely for `TIER_A_HANDLERS` dispatch-shape uniformity (immediately
  `del`-ed in the body, never read) -- the same too-strict-for-purpose
  shape T-1911 fixed on `fix_fmt001_directive_wrap`/
  `fix_e501_merge_introduced`. Dropped entirely rather than retyped to
  `GraphSnapshot | None`; `TIER_A_HANDLERS`' lambda wrappers in
  `_fix_engine.py` stop forwarding `snapshot` to these two handlers.
- **`fix_waive004_stale_waiver`**: a `frob:waive` directive matching zero
  findings (WAIVE004) -- ONLY ever trustworthy from a genuine full,
  unscoped run (mirroring `frob.gates._waive`'s own disclaimer), so this
  handler independently re-runs the full gates suite itself
  (`run_gates`) rather than trusting the caller's own scope, and refuses
  to act at all if it is itself invoked with a `gates`/`ticket` scope
  set. Deletes only a bare, single-physical-line waiver comment -- a
  `\`-continued multi-line directive is left alone, since Tier A never
  guesses which physical line to remove.

  **Incident (2026-07-29, T-1323): prove-fresh-or-do-nothing.** A `frob
  ticket land` produced a pre-land wip snapshot commit that captured
  uncommitted worktree state in which every single-line `frob:waive
  PERF00x` comment had been stripped across 50 files, and the land
  commit carried those deletions onto main (gate:PERF regressed from 0
  errors to 42). Root cause: `_absorb_pre_land_fixes`
  (`src/frob/app/ticket_runner/_land_cmd.py`) calls `apply_tier_a_fixes`
  pre-land, and the worktree's native extensions were stale/missing at
  that point -- `fix_waive004_stale_waiver`'s self-manufactured
  `run_gates()` verification silently under-reported (PERF/REF reach
  analysis found nothing), so every live PERF waiver looked
  simultaneously stale and got mass-deleted in one pass. `WAIVE004`
  itself already carried T-1133's "only trust a genuine full,
  unscoped run" disclaimer -- but nothing checked that the run this
  handler manufactured for ITSELF actually was one, only that the
  CALLER hadn't scoped it.

  The fix is two independent guards, applied BEFORE any deletion:
  `_degraded_verification_reason` refuses the ENTIRE batch when the
  self-manufactured `run_gates()` report carries a `NATIVE001` finding
  (the exact stale-natives shape `_native_unavailable_report` already
  detects and short-circuits `run_gates` to report) or an unexpected
  `GateStats.skipped` entry (excluding the routine unscoped-run `scope`/
  `prework` pair every call this handler ever makes produces);
  `_mass_invalidation_rules` independently flags every rule whose
  candidates in a single run meet or exceed
  `_WAIVE004_MASS_INVALIDATION_THRESHOLD` (5) -- the incident's own
  shape, and a signal that needs no separately recorded baseline pool to
  compare against. `_absorb_pre_land_fixes` ran WAIVE004 excluded
  (`exclude=("WAIVE004",)`) as an interim mitigation between the incident
  and this fix landing; it runs unexcluded again now that the handler
  guards itself. `tests/test_gates.py::TestWaive004DegradedRunGuard`
  reproduces the degraded-run and mass-invalidation shapes directly.

  **Attempted refinement (T-1579), reverted (T-1592).** A mass-invalidation
  hit refuses that rule's whole batch, which does mean a rule whose
  waivers become GENUINELY mass-stale (a detector tightened, a mass
  refactor removed the pattern several waivers covered) cannot be cleaned
  by this handler: every run re-flags the same waivers, every run
  refuses. T-1579 tried to escape that by judging each mass-stale rule
  against a live-finding proof -- if the same self-manufactured run also
  contained one REAL (non-`WAIVE004`) finding of that rule elsewhere, the
  detector had demonstrably run and deletion proceeded.

  That proof does not hold. A PARTIALLY degraded run satisfies it: a
  stale-natives worktree still finds some `PERF004` lexically while
  missing every site the waivers actually cover. Measured 2026-08-05
  during a land -- the perf gate reported ZERO `PERF004` findings while
  `_degraded_verification_reason` returned `None`, the escape opened, and
  55 live waivers across `arch`/`strata`/`perf`/`graph`/`vet` were
  deleted: precisely the T-1323 incident this guard exists to prevent.
  `_drop_untrustworthy_mass_stale_candidates` therefore refuses every
  flagged rule unconditionally again, logging each by name.

  Reviving the escape requires a degraded-run signal that fires for a
  silently under-reporting perf/reach substrate -- the zero-findings case
  T-1578 does NOT yet cover. Until then, mass-stale waivers are cleaned
  by hand, deliberately, with a human reading the diff.

  **Third guard, additive only (T-1942): per-site examined-sites, archgate
  family only.** T-1904 (filed when T-1579 was reverted) named the sound
  escape this incident's history actually needs: proof that the specific
  WAIVED SITE, not just the rule somewhere, was re-analyzed this run --
  never a same-run elsewhere-finding proxy like `_rule_has_live_finding`
  again. T-1921 shipped that substrate (`GateStats.examined_sites`, see
  `frob.gates._coverage_sites` in "Data models" below) deliberately
  unwired from any auto-fix/waiver-retirement path, so it would get the
  same scrutiny the original incident should have had before anything
  consumed it. T-1942 is that first consumer: `_waive004_verified_
  candidates` calls `attach_examined_sites` on its self-manufactured
  `run_gates()` report BEFORE deriving WAIVE004 candidates, then
  `_drop_unexamined_archgate_candidates` (`src/frob/gates/
  _fix_engine_sync.py`) drops any remaining candidate whose target rule
  is in the archgate family (`_archgate_rule_ids`, re-derived from
  `frob.gates._arch._ARCH_CATEGORY_TO_RULE` so a new ARCH1xx/CPPTHROW/
  LARGE category is covered automatically) unless `site_examined`
  positively confirms THIS run's archgate pass actually examined the
  candidate's own file.

  This is a third guard STACKED on top of the two above, never a
  replacement for either -- it can only ever REMOVE a candidate a prior
  stage already proposed to retire, never add one back, so the overall
  chain cannot become less conservative than before T-1942, only equal
  or stricter. It also GRANTS NOTHING outside the archgate family:
  `frob.gates._coverage_sites` instruments only `archgate` today (T-1921's
  own scope cut), so the filter is gated on `rule in _archgate_rule_ids()`
  before ever calling `site_examined` -- treating an uninstrumented
  family as "covered" just because the check would trivially report
  False for it would recreate the same blast radius this whole guard
  chain exists to prevent, only inverted. `tests/test_gates.py::
  TestWaive004ExaminedSitesGuard` is the regression lock, in particular
  `test_original_55_waiver_incident_shape_partial_examination_still_
  refuses` -- the T-1579/T-1592 incident's own shape, narrowed from
  "some finding of this rule anywhere" down to "this exact file",
  reproduced and confirmed still refused.

  **Fourth guard, additive only (T-2011): per-site examined-sites, perf
  family.** T-1943 extended `frob.gates._coverage_sites`' substrate from
  archgate-only to four more families (`perf`/`strata`/`graph`/`vet`),
  substrate-only per the same T-1921 posture -- no consumer in that same
  diff. T-2011 investigated each of the four for a sound WAIVE004 consumer,
  reading the actual code path from rule to violation site rather than
  trusting the family name, and only ONE could be wired:

  - **perf: wired.** `_PERF_RULE_IDS` (`src/frob/gates/_fix_engine_sync.py`)
    is PERF001-008 and PERF010-014 -- every one fed from `frob.perf.
    perf_rules(snapshot, parsed)`, where `parsed` is the exact file set
    `perf_gate`'s own candidate/parse pass computes, matching what
    `_perf_examined_sites` independently re-derives. PERF009 is
    deliberately EXCLUDED: `perf_gate` reads it from `.frob/perf/
    ratchet_findings.json`, a precomputed `frob perf collect` artifact
    never derived from this run's own parse pass, so the examined-sites
    substrate says nothing trustworthy about it -- folding it in would
    have been the exact "family name matches, assume covered" mistake
    this investigation was trying to avoid.
    `_drop_unexamined_perf_candidates` mirrors `_drop_unexamined_archgate_
    candidates` exactly (additive-only, grants nothing outside
    `_PERF_RULE_IDS`); `tests/unit/test_waive004_perf_guard.py::
    TestWaive004PerfExaminedSitesGuard` is its regression lock.
  - **strata: left unwired.** `sys_gate` folds SYS001-004 and SELFAUDIT001
    into what this doc calls the "strata" family, but none of their
    `Violation.file` values are `.strata` design-file paths -- SYS001/SYS003
    report the CODE site of a directive/import (`_site_from_edge_origin`/
    `violation.file` from `check_import_conformance`), SYS002 constructs a
    synthetic `design/<kind>/<id>` string, and SELFAUDIT001 always reports
    the whole `design_dir` constant, never an individual file. Only SYS004
    reports a real `.strata` path, and it fires exactly when that file
    FAILED to load -- by construction never a member of `_strata_examined_
    sites`' successfully-parsed set. There is no rule in this family whose
    violation site actually lines up with what the strata reporter tracks.
  - **graph: left unwired.** `frob.graph.build_graph`'s `GraphSnapshot` backs
    dozens of unrelated gate families with heterogeneous violation-site
    semantics (some per-symbol, some per-edge-origin, some synthetic) --
    no single rule family "owns" it the way `arch_gate`/`perf_gate` own
    their rule ids, so there is no sound `_graph_rule_ids` to define.
  - **vet: left unwired.** `_vet_examined_sites`' own docstring names
    OPAQUE001 as this family's consumer, but `opaque_gate` does not call
    `scan_file_capabilities` at all -- it uses `_opaque_indirection_
    findings`, a deliberately DISJOINT scanner (the "runtime-opaque"
    construct universe, `docs/design/capability-evasion-taxonomy.md`'s own
    split from the statically-resolvable universe `scan_file_capabilities`
    walks). `scan_file_capabilities` is actually consumed by `frob.strata.
    _selfconform` (folded into SELFAUDIT001, same `design_dir`-constant
    site problem as strata above) and by `frob.vet`'s dependency-package
    scanners (`_capability_scan.py`'s `_aggregate_capabilities`, which scan
    a THIRD-PARTY package's extracted source tree, not this repo's own
    `root` `_vet_examined_sites` walks) -- neither corresponds to a rule
    whose violation site matches this repo's own tracked-file candidate
    set. This is a real inaccuracy in `_vet_examined_sites`' own docstring,
    left uncorrected here (out of this ticket's declared scope) and filed
    separately.

  Per this repo's standing default-to-conservative posture, an ambiguous
  family stays unwired rather than wired on a guess -- an uninstrumented-
  for-this-guard family behaves exactly as it did before T-2011 (the first
  two guards still apply to it), it is simply not granted this fourth,
  more precise layer.

  A companion guard closes the same incident's OTHER half at the land
  layer itself, independent of which Tier-A handler is at fault: `frob
  ticket land` refuses BEFORE any git mutation (before the wip-commit
  that would otherwise fold a dirty worktree's edits into the merge
  unattributed) when the worktree's uncommitted state deletes a
  `frob:waive` directive whose file is neither in the landing ticket's
  scope nor named in its Done report
  (`frob.tickets._land._check_uncommitted_waive_deletions`,
  `LandError.OutOfScopeWaiveDeletion`) -- see
  docs/modules/tickets-landing.md#frob-ticket-land.

**`fix_suppress001_paired_suppression`** (T-1341, phase 2 of T-1339's
suppression-dialect-portability epic): a SUPPRESS001 finding (`frob.
gates._suppress.suppress001_gate`, phase 1) already names, in its own
message, exactly which reporting checker (`ty`/`mypy`) reports an
unsuppressed rule code on a line that carries a DIFFERENT dialect's
suppression comment -- this handler appends the reporting checker's own
code, in this repo's observed canonical order (confirmed against every
pre-existing dual-dialect line at authoring time: mypy's `# type:
ignore[...]` first, `# noqa: ...` second, `# ty: ignore[...]` last --
`_CANONICAL_DIALECT_ORDER`), never a guessed or cross-dialect-mapped
code. No structured field is added to `Violation` for this -- the
reporting dialect/code is parsed back out of the finding's own message
text (`_parse_suppress001_message`), the same precedent
`_waive004_target_rule` already set for this module.

Order of operations, because it changes the outcome (coordinator
directive, T-1341): `ruff format` is delegated to FIRST, for every file
carrying a violation, before anything is written --
`_run_ruff_format`/`fix_suppress001_paired_suppression`'s own docstring
explains why a hand-rolled signature wrapper is never written here: an
over-long `def`/`class` line is `ruff format`'s own authoritative
territory (verified: it already splits a >88-char signature into
one-parameter-per-line with a trailing comma), and a frob-side wrapper
would both duplicate that logic (this repo's NO DUPLICATION rule) and be
fought by the very next `ruff format` run, which always wins. Only a
violation that SURVIVES formatting (`suppress001_gate` is re-run
afterward, since line numbers may have shifted) gets a suppression
written at all. If the rewritten line is STILL over the configured limit
after the dialect suppression is appended, `# noqa: E501` is added too --
UNLESS ruff's own effective `[tool.ruff.lint.per-file-ignores]`
configuration already silences `E501` at that path
(`_code_ignored_for_path`, matched by glob against the same config
`pyproject.toml` itself declares). This last check is the direct fix for
the incident that motivated this ticket: a repo-wide grep at authoring
time found 2623 hand-written `# noqa: E501` comments, 2493 of them on a
`frob:`-directive comment line, and of the 1566 real E501 violations
under `src/`, 1559 sat on a `tests/**`-adjacent or directive line where
`E501` cannot fire at all under this repo's own per-file-ignores --
writing a suppression there is dead noise, not a fix, so this handler
refuses to write one.

A pre-existing OTHER code already on the same pragma (e.g. `# noqa:
F401`) is MERGED, never clobbered -- `_merged_dialect_codes` unions the
code sets and `_format_dialect_segment` re-renders sorted, comma-joined
(`E501,F401`), and never widens an existing BARE suppression (`#
noqa`/`# type: ignore` with no bracketed code, already covering every
code on that line) to a coded one -- a bare comment is strictly more
permissive already. `_find_comment_start` locates the real trailing
comment by tokenizing the (dedented) line rather than substring-searching
it, so a `#`-shaped sequence living inside a string literal is never
mistaken for a comment boundary; any OTHER trailing prose comment sharing
the line is preserved verbatim (`_strip_known_pragma_comments`) rather
than discarded when the pragma block is rebuilt.

**Precedence with FMT001, explicitly (T-1341):** this handler never
touches a line carrying a `frob:` directive marker anywhere in its
trailing comment, full stop (`_FROB_DIRECTIVE_MARKER_RE`) -- that is
`fix_fmt001_directive_wrap`'s exclusive territory. FMT001's own
`canonicalize_text` already treats an existing trailing `# noqa` suffix
on a directive line as a deliberate T-0985 escape hatch it leaves alone,
so the two handlers could otherwise double-fix or oscillate across
repeated `--fix` runs if SUPPRESS001 ever manufactured a competing noqa
on the same line FMT001 also claims. In practice a SUPPRESS001 target
line (python code with a type-checker suppression comment) and an FMT001
target line (a bare `frob:` directive comment) are never the same
physical line, so this guard is a structural belt-and-suspenders rather
than something expected to fire often --
`tests/test_gates_fix_engine.py::TestSuppress001FMT001Precedence` covers
a synthetic line carrying both shapes at once and asserts the file is
byte-identical after two consecutive `--fix` passes. `TIER_A_HANDLERS`
runs SUPPRESS001 immediately after FMT001 for the same reason, fixed
explicitly rather than left to dict-insertion accident.

Idempotent by construction, not by bookkeeping: once a line carries both
dialects' matching suppression comments, the underlying diagnostic
`suppress001_gate` correlates against is itself silenced for BOTH
checkers (a `# type: ignore[code]  # ty: ignore[code]` pair suppresses
mypy and ty independently), so a second `--fix` pass finds no finding
left on that line at all -- no separate "already fixed" tracking needed.

`apply_tier_a_fixes(root, snapshot, queue)` dispatches through
`TIER_A_HANDLERS`, a `dict[str, Callable]` keyed by rule id (T-1261
promotes the prior positional-call list to this explicit table so a
fixability-registry-field ticket has something real to scan) -- run in
the dict's declared order (DOC007/DOC002/FMT001/
SUPPRESS001/REG010/REL002/DOCENUM001 first, since they are pure
source-text/artifact rewrites with no ledger interaction; TICK002 next,
since it touches the ticket ledger; WAIVE004 last, since it re-invokes
the whole gates suite itself and should see every other handler's
rewrites already applied).
SUPPRESS001 runs immediately after FMT001 specifically (see the
precedence note above). A handler whose own signature differs from the
uniform `(root, snapshot, queue)` call shape (four take `(root,
snapshot)`, one takes `(root, queue)`, `fix_waive004_stale_waiver` takes
extra keyword-only scope params) is adapted at the `TIER_A_HANDLERS` call
site via a thin lambda, never by changing that handler's own signature.
Returns every `FixApplied` (rule, file, line, one-line rewrite summary)
actually made -- the disclosed audit trail every fix must leave,
mirroring T-1137's own "no silent auto-discharge" anti-goal applied to
what WAS auto-fixed rather than only what was left alone.

**Crash-safety and recovery breadcrumb (T-1348).** `_absorb_pre_land_fixes`
calls `apply_tier_a_fixes` BEFORE `frob ticket land`'s own pre-merge
wip-commit (docs/modules/tickets-landing.md#frob-ticket-land) ever runs -- a
process killed anywhere in this window used to leave the tree in a state
that was neither the pre-fix nor the post-fix original (T-1338: a killed
land left `src/frob/gates/_debt_deprecated.py` GARBLED, and the obvious
`git checkout -- <file>` recovery then silently destroyed an unrelated
uncommitted test in a DIFFERENT file). Two independent fixes, both
entirely inside this module:
- Every handler that rewrites a file in place now routes through
  `_write_text` (temp file + `fsync` + `os.replace` in the same
  directory, reusing `frob.tickets._store.atomic_write`'s existing
  T-0456 primitive) instead of a bare `path.write_text(...)` -- a kill at
  any point up to and including immediately before the atomic rename
  leaves the ORIGINAL file's bytes on disk, never a half-written one.
- `apply_tier_a_fixes` writes `.frob/land-autofix-manifest.json`
  (`write_autofix_manifest`) after EVERY handler completes, listing every
  distinct file path rewritten so far in the current run, and clears it
  (`clear_autofix_manifest`) only once the whole pass finishes. A process
  killed partway through the handler loop leaves this manifest naming
  exactly what Tier-A actually touched up to that point, so a recovering
  agent diffs `git status` against it instead of a blanket `git checkout
  --` that cannot tell "Tier-A rewrote this" from "my own uncommitted work
  is in this other file" -- the exact ambiguity T-1338 turned into data
  loss. See docs/modules/tickets-landing.md#frob-ticket-land for how this sits
  relative to `land()`'s own wip-commit step.

**Scope boundary (T-1138, updated T-1261):** this module is the fix
HANDLERS and their callable entry point (`src/frob/gates/**`); the `frob
check --fix` CLI flag itself (argument parsing in
`src/frob/_cli_parsers/_check.py`, orchestration in
`src/frob/app/check_runner.py`) was wired up separately (T-1260) and
calls `apply_tier_a_fixes` directly -- `src/frob/gates/**`/
`src/frob/tickets/**`/`tests/test_gates.py` stay this module's own
scope, the CLI wiring is a sibling ticket's. `tests/test_gates.py::
TestFixEngineTierA`/`TestFixEngineTierABatch2` exercise every handler at
the function level against real `GraphSnapshot`s/`TicketQueue`s,
GIVEN/WHEN/THEN per each ticket's own acceptance criteria.

### `fix_e501_merge_introduced` auto-fix (T-1547)

<!-- frob:describes src/frob/gates/_fix_engine_text.py::fix_e501_merge_introduced -->
<!-- frob:describes src/frob/gates/_fix_engine_text.py::_merge_touched_python_files -->
<!-- frob:describes src/frob/gates/_fix_engine_text.py::_e501_lines_for_file -->

`fix_e501_merge_introduced` (registered in `TIER_A_HANDLERS["E501"]`)
closes the E501 item T-1531's own deferral list named: an over-long line
a land-time MERGE introduces (as opposed to a pre-existing E501 finding
anywhere else in the repo) gets a targeted `ruff format` pass, scoped to
exactly the `.py` files that merge touched -- never a whole-tree `ruff
format` sweep, which would re-litigate every unrelated pre-existing
E501 finding in the repo.

`_merge_touched_python_files` derives the touched set from `HEAD`'s own
two-parent merge diff (`git diff --name-only HEAD^1 HEAD^2`) when `HEAD`
is a real merge commit, or from uncommitted working-tree changes against
`HEAD` (`git diff --name-only HEAD`) for the in-progress-merge shape
`frob ticket land`'s own pre-land Tier-A phase runs in (the worktree has
already `git merge main`d but not yet committed that merge). Distinct
from `fix_fmt001_directive_wrap`, which only ever rewraps `frob:`-
directive comment lines, never ordinary code.

`_e501_lines_for_file` re-verifies E501 is actually gone (a scoped `ruff
check --select E501 --output-format json` before and after the targeted
format pass) before counting a file as fixed -- `ruff format` cannot
always shorten every over-long line (an unbreakable string literal, for
instance), so a file whose E501 lines survive the format pass is left as
an ordinary, still-live E501 finding rather than misreported as fixed.

### `fix_cov002_ticket_directive_insertion` auto-fix (T-1548)

<!-- frob:describes src/frob/gates/_fix_engine_sync.py::fix_cov002_ticket_directive_insertion -->
<!-- frob:describes src/frob/gates/_fix_engine_sync.py::_insert_ticket_directive_above -->

`fix_cov002_ticket_directive_insertion` (registered in
`TIER_A_HANDLERS["COV002"]`) closes a COV002 finding (a changed symbol
with no `frob:ticket` edge to an open ticket and no covering ticket
scope) by inserting `# frob:ticket <landing-id>` (leader resolved per
the TARGET file's own language, see below) directly above the symbol --
but ONLY when the caller supplies a real, currently OPEN `ticket_id`
(the landing ticket, `None` outside a land context: this handler is a
whole no-op then, per Tier-A's own never-guess posture) and the finding
is against `working_diff(root, "main")` -- this land's own diff, the
only diff this handler has any basis to attribute a fix to.

This is the one Tier-A handler in this module whose fix genuinely
depends on WHICH ticket is running the fix pass, which no other handler
here needs -- `TIER_A_HANDLERS`' callable shape and
`apply_tier_a_fixes`'s own signature both grew a `ticket_id: str | None`
parameter for it (T-1548); every other handler ignores the new
argument, unchanged behavior.

**Comment-leader resolution (T-1581).** The insertion helper,
`_insert_ticket_directive_above`, originally hardcoded its own narrow
suffix table (`.py` -> `#`, `.rs` -> `//`, anything else defaulted
silently to `#`). During T-1548's own land that default fired against
`design/frob.strata` (leader `//`), writing a Python-style `#`
directive into it and breaking strata parsing on `main` until it was
hand-repaired. The handler now resolves the leader via
`frob.gates._fmt_directives.marker_for` -- the ONE shared per-suffix
comment-leader table `frob fmt`'s own directive-canonicalization pass
already uses, extended to include `.strata` (`//`) as part of this fix
-- instead of a second, independently-drifting table. A target suffix
`marker_for` does not recognize now REFUSES the insertion outright
(logs a warning, returns a no-op) rather than guessing `#`. Regression
coverage: `tests/test_gates_fix_engine.py::
TestInsertTicketDirectiveAboveCommentLeader` (`.strata` and `.rs`
insert `//`, `.py` inserts `#`, an unrecognized suffix inserts
nothing).

<a id="sys100sys104-strata-declaration-auto-fix-t-1531"></a>
### SYS100 `.strata` declaration auto-widening -- REMOVED (T-2922, supersedes T-1531/T-1545/T-1623/T-1628)

T-1531/T-1545 wired two Tier-A handlers (`fix_sys100_may_via_union`,
`fix_sys100_extended_whole_node_grant`, dispatched together via
`_fix_sys100_both_cases` under the single `TIER_A_HANDLERS["SYS100"]`
key) that, on observing a file or node exercise an undeclared capability,
silently EDITED the node's `may=` declaration to grant it -- widening the
`via` list for the CORE net/fs-write/exec case, or inserting a bare
via-less whole-node grant for the EXTENDED eval/process-control/ffi/...
case. T-1623/T-1628 accepted this as deliberate policy at the time.

**T-2922 (security, critical) deletes both handlers and their
`TIER_A_HANDLERS` entry entirely, on the user's explicit instruction,
because a node's `may=` list exists specifically as a CEILING on what its
code is allowed to do.** An auto-fix that raises the ceiling to match
whatever the code already does turns the declaration into a passive
restatement of behavior rather than a constraint on it -- a ratchet with
no teeth. This is a genuine policy reversal, not a bug fix: T-1623/T-1628
is superseded, not found wrong after the fact.

What is UNCHANGED: SYS100 the DETECTOR
(`frob.strata._selfconform`/`check_self_conformance`, folded into
`sys_gate`'s SELFAUDIT001) still fires, unwaived, on any undeclared
capability use -- detection got strictly LOUDER by this change, since a
finding can no longer be silently resolved by an automatic edit. Dropping
a capability that is declared but never observed (the SHRINKING
direction) remains fully legitimate and untouched -- only auto-WIDENING
is forbidden. A human must now widen a `may=` grant by hand, subject to
ordinary code review, the same as any other declared-surface change.
Proof (must-still-fire / must-not-auto-resolve pair):
`tests/test_gates.py::TestFixEngineTierA::
test_sys100_core_violation_still_fires_and_is_not_auto_resolved` and
`::test_sys100_extended_violation_still_fires_and_is_not_auto_resolved`.

`frob.strata._sync_may` (the writer both deleted handlers called --
`sync_may_report`/`apply_sync_may`/`sync_may_extended_report`/
`apply_sync_may_extended`/`WholeNodeMayGrantDiff`) is left in place for
now, deliberately: it sits inside the concurrent T-2920 shrink-only
ratchet rework's own declared scope (`src/frob/strata/**`), and this
ticket avoids racing that work with an ImportError. It is dead code as
of this change; its removal is a documented follow-up once T-2920's own
use of that file (if any) is confirmed clear.

T-1870 (owner directive: no code path may auto-update declared
public-symbol surface) had already deleted SYS104's own writer/handler
(`fix_sys104_interface_union`, <!-- frob:waive DOC006 reason="deliberately historical -- deleted by T-1870, per an explicit owner directive that no code path may auto-update declared public-symbol surface, as this same sentence explains" -->`frob.strata._sync_interface`) -- `interface=`
was already unsynced by anything, including at land time, before T-2922.
T-2922 extends the same "no code path may silently rewrite a declared
surface to match observed reality" principle from `interface=` to
`may=`.

**SYS112 (T-2503/T-2523): ambient (via-less) grants require a reason.**
A via-less `may "ATOM";` (no `via` trailer) is the AMBIENT form of a
grant: it covers every file in the node's `code` glob, no per-site
enumeration, no via-list churn -- the form T-2503 introduced for
`testsuite`'s `fs.write`/`exec`/`fs.read` (352+190+134 = 676 sites
collapsed to 3 declarations). An ambient grant with no stated
justification is exactly the exemption-that-matches-the-normal-case
failure (T-1967) -- a blanket "this node may do X everywhere" with no
record of WHY. `frob.strata._effects.check_ambient_capability_reasons`
(T-2523, wired into SELFAUDIT001 the same way T-1761/T-1977 wired
SYS109/SYS111) requires a same-line trailing comment on every via-less
`may` line, e.g. `may "exec";  // because: "the suite's purpose is
executing frob under test"`. The reason must state WHY the capability
is expected of every file the node's glob covers, not restate what the
grant does. A via-populated (enumerated) `may ... via [...]` declaration
is NEVER flagged: its explicit site list is already its own
justification. Implemented as a plain text scan of the `.strata` source
(not the parsed `KernelModel`), since the reason has no `MayGrant`-level
field to live in -- the same "read the raw source" posture
`_line_effects` already takes for needle detection.

**`fix_sys111_capability_ratchet_sync` (T-2001)**: the capability-ratchet
lock (`docs/design/registry/capability-via-ratchet.lock.json`, SYS111,
`frob.strata._effects.capability_ratchet_violations`) was built as the
sibling half of the (now-deleted, T-2922) SYS100 auto-widening handlers
above: widening a node's `may ... via [...]` grant in `design/frob.strata`
satisfied SYS100/SYS104 but used to leave the ratchet's committed ceiling
stale, so the breach surfaced on a LATER, unrelated land's SYS111 check
instead of the one that actually caused it -- measured twice in one hour
(T-1977, T-1665) before this handler existed. T-2922: with the SYS100
auto-widener gone, this handler's own growth-attribution ordinarily finds
nothing new to bump; it is NOT deleted, since a human-authored `may=`
widening (still a legitimate, explicit action) can still grow the
via-site count and still needs its ratchet ceiling re-baselined the same
way. The same "one of N parallel bookkeeping obligations self-heals, its
sibling does not" shape `fix_docenum001_enumerates_sync` (T-1974) already
closed for `docs/modules/gates.md`'s rule-catalog anchor.

Registered in `TIER_A_HANDLERS` immediately AFTER `SYS100` (dict order
is call order, `apply_tier_a_fixes`'s own docstring) so its CURRENT-side
count already reflects whatever SYS100 just widened in the same pass.
Never bumps the ceiling unconditionally to whatever is currently
observed -- that would turn the ratchet into a no-op that ratifies any
growth, T-2001's own explicit anti-goal. Instead it measures a BEFORE
snapshot from `design/`'s content at `git show HEAD` (materialized via
`git archive` into a scratch dir, reusing the exact same `load_design_
ids`/`merge_models` loader the live model uses, never a second parsing
implementation over git blob text) and only bumps a `(node, atom)` pair
whose CURRENT count exceeds the committed ceiling AND grew since HEAD --
a pair already in breach at HEAD is a PRE-EXISTING violation, left
untouched (still surfaced by SYS111) rather than silently ratified,
T-2001's own acceptance criterion. Every bump records a `reason` naming
the before/after counts and `"ticket": "T-2001"`, the same accountability
the lock's own module docstring already demands of a human-authored
widening.

Disclosed first-cut gap: a hand-edited via-list widening the agent
already COMMITTED on their own worktree branch before landing is
invisible to this HEAD-relative diff (HEAD already includes it). Both
measured occurrences were caused by SYS100's OWN auto-fix widening an
UNCOMMITTED via-list in the SAME Tier-A pass, which this fully covers; a
committed hand-edit would need a true pre-land-tip base ref threaded
through (the shape `frob.tickets._land.land`'s `sync_gate_rules` callback
already uses) to close completely.

**Remaining SYS100/land-refusal recipes (disclosed deferral, T-1531's own
body names six; two shipped here)**: COV002 changed-symbol-without-edge
auto-insertion, ClaimDivergence done-report re-run, TICK006
phantom-draft-citation refile/renumber, and E501-from-merge targeted
`ruff format` are real, filed as separate follow-up tickets rather than
guessed at inside this ticket's own budget.

### Scope/lease enforcement on Tier-A output (T-2284)

No individual handler above consults the landing ticket's declared scope
or another ticket's live lease -- each one scans its OWN full domain
(the whole repo, or the whole `.strata` design tree) and writes wherever
it finds a fixable finding. During a land this used to be a real defect:
`apply_tier_a_fixes` auto-commits everything it wrote alongside the
landing ticket's own diff, so a handler that touched a file OUTSIDE the
landing ticket's scope either shipped as an undisclosed passenger of the
wrong ticket, or -- since `CrossTicketLeakage`
(`frob.tickets._land._check_cross_ticket_leakage`) does catch it --
refused the whole land and forced a manual revert (T-2274's own land hit
exactly this against `scripts/fleet_status.py`, a file under a live
lease at the time).

`frob.gates._fix_engine_scope.filter_fixes_by_scope_and_lease` closes
this: `apply_tier_a_fixes` calls it once per handler, right after that
handler runs, on its own return value. A fix outside the landing
ticket's scope, or on a file another ticket holds a live lease on
(`frob.tickets._leases.is_effectively_in_progress`), is reverted on disk
(`git checkout --`) and reported as a `SkippedFix` at WARNING -- visible
in `frob ticket land`'s own output, never only a debug log (T-2255's
"a silent skip is worse than a loud one" precedent). **Lease always wins
over scope**: a file under another ticket's live lease is skipped even
when the landing ticket's OWN declared scope also covers it -- two
tickets' scopes can legitimately overlap by declaration (T-2225's own
`src/frob/**` vs. `src/frob/tickets/_land.py` example) without either
being wrong to have written it that way, but a live lease is a real-time
fact that someone is actively editing that file RIGHT NOW; declared
scope is a static intention recorded once, which can be stale or
overbroad. Outside a land (`ticket_id=None`, the bare `frob check --fix`
CLI path) every fix passes through unfiltered -- there is no landing
ticket to scope against, and that command's existing repo-wide behavior
is unchanged.

Only `TIER_A_HANDLERS`/`apply_tier_a_fixes` (this section) goes through
this filter. `frob.gates._fix_engine_tier_b`'s Tier-B engine
(`apply_tier_b_fixes`) is called ONLY from `frob check --fix`
(`frob.app.check_runner`), never from the land path at all -- it cannot
leak an out-of-scope edit into a land's committed changeset the way
Tier-A could, so it does not share this defect and was not touched here.

**Repo-wide handlers.** `REL002`/`fix_rel002_release_sync` genuinely has
no single file to scope-check against -- it resyncs the release manifest
against `pyproject.toml`/`CHANGELOG.md` project-wide by design, and
`pyproject.toml`/`CHANGELOG.md`/`uv.lock` are already land-owned files no
worktree ticket declares in its own scope at all (docs/guides/
agent-playbook.md section 4b). `scope_matches` already carries an
always-in-scope exemption for exactly this shape (`LEDGER_PATH`, the
ticket-ledger analog); REL002's own handler is exempted from this
filter by NAME, not silently -- `_REPO_WIDE_EXEMPT_RULES` in
`_fix_engine_scope.py` names it explicitly, with the same reasoning
recorded at the exemption site, rather than that handler's fix quietly
passing every scope/lease check by never having a scopeable file to
fail one against.

## Unresolved (T-1664)

<!-- frob:describes src/frob/gates/_models.py::Severity -->
<!-- frob:describes src/frob/check/_python.py::_unresolved_count -->
<!-- frob:describes src/frob/check/_python.py::_diag_severity -->

Every serious under-reporting incident this drive found traced to the
same shape: an analysis layer that could not look, reporting that it
found nothing -- indistinguishable from a genuinely clean result. A perf
gate read zero findings with stale natives (the escape hatch that
unlocked deleted 55 live `frob:waive` directives). A mypy oracle sharing
`.mypy_cache` across xdist workers returned zero diagnostics for a file
that had one. A capability scanner's "no capabilities observed" and "I
cannot analyse this language" were the same answer.

`Severity.UNRESOLVED` is the structural fix: a THIRD outcome, not a
severity tier between `warn` and `error`. `ERROR`/`WARN` both mean "the
check ran to completion and this is what it found" (possibly nothing --
an empty violation list is a real, complete answer). `UNRESOLVED` means
"the check could not determine an answer at all" -- an unresolvable call
target, an unparseable file, a missing language adapter, a stale
analysis substrate. A gate emits it only when it KNOWS it cannot
resolve something; it is never a default/fallback for an ordinary empty
result, and converting every hard case into UNRESOLVED would flood a
floor that must stay a trustworthy zero (T-1664's own explicit
guardrail).

Counting and rendering (never silently dropped, never counted as an
error):
- `frob.check._python._unresolved_count` counts UNRESOLVED violations,
  kept as its OWN term everywhere a family/summary line reports
  error/warning/waived counts (`_gates_family_result`, `_gates_summary`)
  -- an UNRESOLVED finding folded into "N warnings" would be
  indistinguishable from a real, completed finding, exactly the failure
  this closes.
- `frob check`'s exit code is gated on `n_err` alone (`_gate_summary_
  result`/`_gates_family_result`) -- UNRESOLVED never fails a run by
  itself, matching WARN's posture; it must stay visible and countable,
  not become a second silent-pass floor-flooding failure mode.
- `_diag_severity` maps an UNRESOLVED `Violation` to a `Diagnostic`
  `info` severity (distinct from `error`/`warning`) when rendered
  through `frob.process.parsers.common.Diagnostic`.

Deliberately NOT built in this pass (disclosed, not silently dropped):
a generic per-gate "declares its optional substrate (natives, a
language adapter, a resolver) and auto-reports UNRESOLVED when absent"
mechanism -- that is a real per-gate wiring effort each family needs
individually, filed as follow-up residue rather than forced into this
change's scope. REF001 (T-1665, docs/modules/gates.md#anti-orphan-file-
reference-gate) is the first concrete consumer.

**T-2891: the coarse pass/FAIL rendering closed a gap this contract left
open.** The twelve `*SCHEMA`/`FLAGCOV` gate families (each resolving an
opt-in `known_keys` declaration out of the target project's own
`frob.toml` via `_docblocks_shared.resolve_dotted_symbol`) correctly
report UNRESOLVED, exactly as designed above, when a target project has
not declared that table -- measured off-repo against a real foreign
project (lograder): 12 gates, each `0 errors, 0 warnings, 1 unresolved,
0 waived`. But `CheckResult.as_text`'s tool-summary row used to key its
icon off `exit_code == 0` alone, so a gate whose ENTIRE result was
UNRESOLVED (not a mix of UNRESOLVED-and-clean, the ordinary case this
contract already covers) rendered identically to a genuine clean pass --
the counting/rendering contract above was upheld at the data level (the
count was always there, correctly named) but not at the coarse icon a
human skims.
`docs/commands/check.md#tool-summary-pass--fail--unres-t-2891` documents
the fix: a third `UNRES` icon for exactly the
all-UNRESOLVED shape. This is a RENDERING-only change -- `exit_code`,
`total_errors`, and every counting rule above are unchanged; UNRESOLVED
still never fails `frob check` by itself, mixed UNRESOLVED-and-real-
finding gates still render their ordinary `pass`/`FAIL` icon.

## Data models

<!-- frob:describes src/frob/gates/_models.py::Severity -->
<!-- frob:describes src/frob/gates/_models.py::WaiverRef -->
<!-- frob:describes src/frob/gates/_models.py::Violation -->
<!-- frob:describes src/frob/gates/_models.py::GateStats -->
<!-- frob:describes src/frob/gates/_models.py::GateReport -->
<!-- frob:describes src/frob/gates/_arch.py::arch_examined_sites -->
<!-- frob:describes src/frob/gates/_coverage_sites.py::attach_examined_sites -->
<!-- frob:describes src/frob/gates/_coverage_sites.py::is_family_instrumented -->
<!-- frob:describes src/frob/gates/_coverage_sites.py::site_examined -->
<!-- frob:describes src/frob/gates/_models.py::GateConfig -->
<!-- frob:describes src/frob/gates/_models.py::PreworkSweep -->
<!-- frob:describes src/frob/gates/_models.py::SystemSpec -->
<!-- frob:describes src/frob/gates/_models.py::TestPolicy -->
<!-- frob:describes src/frob/gates/_models.py::CoverageData -->

- `Severity` -- a violation's exit-code weight: `error` fails
  `frob check`, `warn` and `unresolved` do not. `unresolved` (T-1664,
  see #unresolved-t-1664 below) is a DIFFERENT kind of claim than
  `warn`, not a lower tier of the same claim -- "could not determine an
  answer", never counted as a completed finding.
- `WaiverRef` -- the `frob:waive` edge that suppressed a violation, kept
  on the `Violation` so waivers stay visible debt rather than silence.
- `Violation` -- one gate finding: rule id, severity, site, and a message
  that always embeds its own remedy command.
- `GateStats` -- per-gate counters (violation counts, timing, skipped
  gates) attached to every `GateReport`. T-1921: also carries
  `examined_sites`, the per-site analysis-coverage substrate filed from
  T-1904's investigation of the falsified T-1579 WAIVE004 escape
  (`_rule_has_live_finding`, reverted after deleting 55 live waivers --
  proving only "the rule fired somewhere" is unsound proof that a
  specific waived SITE was re-analyzed). Keyed by gate family name, each
  value is the frozenset of repo-relative paths that family examined
  this run; a family absent from the mapping means "not instrumented",
  never silently "examined and clean". `frob.gates._coverage_sites`
  (`site_examined`/`is_family_instrumented`/`attach_examined_sites`) is
  the sanctioned way to read it -- never inline the dict lookup at a
  call site. `attach_examined_sites` populates it as a post-`run_gates`
  enrichment step; today only the `archgate` family
  (`frob.gates._arch.arch_examined_sites`, backed by `ArchResult.
  files_examined`) reports for real, every other family deliberately
  left uninstrumented (T-1921's own scope cut -- see that module's
  docstring). T-1942 is the first (and, as of this writing, only)
  consumer wiring this substrate into a WAIVE004 auto-fix/waiver-
  retirement path -- `_drop_unexamined_archgate_candidates`, archgate
  family only, additive on top of the two pre-existing WAIVE004 guards,
  never granting anything for an uninstrumented family; see the WAIVE004
  Tier-A fix-handler section above for the full wiring writeup. Any
  OTHER family remains unwired into any waiver-retirement path by this
  substrate; that is still separate, later work per family, precisely so
  each one gets the same scrutiny the original incident should have had.
- `GateReport` -- the merged result of `run_gates`: kept violations,
  waived violations, and stats.
- `GateConfig` -- everything `run_gates` needs to load state and select
  which gates run (root, base ref, ticket, gate subset). **The `drift`
  gate (DRIFT001/DRIFT002) always evaluates regardless of `gates`/`--only`
  narrowing (T-0265)**: `_build_jobs` unconditionally folds a `drift` job
  into the selected set even when a caller's `gates` subset omits it (e.g.
  a ticket-scoped `--only scope` pre-flight check), so a narrowly-scoped
  run can never report clean on a dangling edge (DRIFT002) that a full,
  unscoped `frob check` on the identical tree would catch -- one
  authoritative answer to "does this edge endpoint resolve"
  (`test_gate`'s own docstring: "DRIFT002 already covers TESTS edges"),
  not two evaluation paths that can silently disagree. This costs nothing
  extra: `st.snapshot`/`st.lock` are already unconditionally loaded for
  every gate run before selection is even applied.
- `PreworkSweep` -- a recorded dup+xref sweep over a ticket's scope,
  stamped at `frob ticket start` time; PRE001's evidence. T-0584: also
  carries `partial` (the sweep hit its budget before finishing every scope
  pattern) and `pending_patterns` (the patterns still left to scan) --
  `prework_gate` treats a partial sweep as provisionally clean as long as
  its `digest` still matches, and `sweep_ticket` resumes from
  `pending_patterns` on its next call rather than rescanning from scratch.
- `SystemSpec` -- one `[[system]]` entry: an e2e-tested surface, its
  entrypoint, and its coverage scope for TEST004/TEST005.
- `TestPolicy` -- the `[testing]` table: all test-obligation floors
  (unit case counts, coverage percentages), each overridable.
- `CoverageData` -- parsed `coverage.xml` mapped onto the snapshot:
  per-symbol branch and per-module line percentages.

```python
class Violation(BaseModel):
    rule: str                   # "DRIFT001", "POL-..."
    severity: Severity          # ERROR | WARN
    file: str
    line: int
    message: str                # human sentence incl. the fix command
    waived: WaiverRef | None    # populated when a frob:waive matched

class GateReport(BaseModel):
    violations: tuple[Violation, ...]
    waived: tuple[Violation, ...]
    stats: GateStats            # counts per gate, timing per gate

class GateConfig(BaseModel):
    root: Path
    base: str = "main"
    ticket: str | None = None   # explicit --ticket
    gates: frozenset[str]       # subset selection for frob check --only

class Diff(BaseModel):
    base: str
    hunks: tuple[Hunk, ...]     # file, span, touched symrefs (resolved
                                # against the snapshot by frob.gates)

class PreworkSweep(BaseModel):
    date: date
    dup_findings: int
    xref_hits: tuple[str, ...]
    digest: str                 # over scope file hashes at sweep time
    partial: bool = False       # T-0584: budget exceeded before finishing
    pending_patterns: tuple[str, ...] = ()  # scope patterns left to scan

class Invariant(BaseModel):
    id: str                     # ^INV-\d{3}$
    statement: str
    criticality: Criticality
    evidence: tuple[str, ...]

class CollectedTests(BaseModel):
    node_ids: frozenset[str]    # from pytest --collect-only -q, cached

class SystemSpec(BaseModel):
    id: str
    entrypoint: str
    min_e2e: int
    paths: tuple[str, ...]

class TestPolicy(BaseModel):    # [testing] table, all floors overridable
    min_unit_cases: int = 3
    min_integration: int = 1
    unit_branch_cov: int = 90
    module_line_cov: int = 85
    system_line_cov: int = 80

class CoverageData(BaseModel):
    source_sha: str             # coverage.xml sha recorded by the stamp
    symbol_branch: Mapping[str, float]   # symref -> percent
    module_line: Mapping[str, float]     # package path -> percent
```

## Error types

<!-- frob:describes src/frob/gates/_models.py::GateError -->
<!-- frob:describes src/frob/gates/_models.py::CoverageError -->
<!-- frob:describes src/frob/policy/_models.py::PolicyError -->
<!-- frob:describes src/frob/gates/__init__.py::GateOrderDriftError -->

- `GateError` -- failure values `run_gates` and its loading steps
  (graph build, ticket queue, lock, git diff) can return.
- `CoverageError` -- failure values `load_coverage`/`stamp_coverage` can
  return (missing `coverage.xml`, malformed XML).
- `PolicyError` -- failure values `frob.policy`'s rule loading and
  matching paths can return (malformed rule, non-compiling tree-sitter
  query).
- `GateOrderDriftError` (T-0839) -- raised, not returned as a `Result`:
  `_merge_canonical_order` hits it when the process/thread pool result
  dict names a gate absent from `_CANONICAL_GATE_ORDER`. This is
  unrecoverable wiring drift (a gate registered in `_ALL_GATES`/
  `_build_jobs` but never added to the order tuple) -- exactly the T-0788
  incident, where the "compliance" gate briefly had this gap and its
  findings would have been silently dropped from `frob check` output. A
  module-level `assert set(_CANONICAL_GATE_ORDER) == _ALL_GATES` next to
  the order tuple's definition also catches the same drift at import
  time, before any gate ever runs.

```python
class GateError(ErrorSet):
    GraphUnavailable = "Graph build failed; gates cannot run"
    GitFailed        = "git diff/merge-base failed"
    NoTicketContext  = "Scope gate requested but no active ticket resolved"
    # T-1180: stamp_coverage's hard pre-stamp deflation floor -- see the
    # "Public API" section above.
    CoverageDeflated = "coverage.xml module-join fraction is below the deflation floor"

class PolicyError(ErrorSet):
    MalformedRule = "Policy rule failed schema validation"
    BadQuery      = "tree-sitter query does not compile"

class InvariantError(ErrorSet):
    Malformed   = "Invariant file failed schema validation"
    DuplicateId = "Two invariant files share an id"

class CoverageError(ErrorSet):
    Missing  = "No coverage.xml/stamp found; run make coverage"
    Malformed = "coverage.xml could not be parsed"
```

## frob fmt: directive canonicalization (T-0441)

`frob.gates._fmt_directives` is a canonical-form line-wrap/UN-wrap
normalizer for `frob:` directive comment lines, exposed as `frob fmt
[path] [--check] [--json]`. It exists so a long `frob:waive`/`frob:debt`/
etc. reason never has to fight ruff E501 by hand: canonical form is the
FEWEST physical lines that keep every line within the project's line
length, using T-0286's own trailing-backslash continuation syntax. The
operation is two-directional and idempotent in both directions:

- `fmt(single-line-too-long)` -> minimally wrapped (word-boundary splits,
  each non-final physical line ending in `` \ ``).
- `fmt(wrapped-but-now-fits)` -> joined back to one physical line (the
  reason got shorter, or the limit got raised, or it was split
  unnecessarily to begin with).

T-0972: `canonicalize_text`'s own two-pointer merge scan over lines/runs
picked up a reasoned `frob:waive PERF003` (position-free token detector
false-positive: it is one O(n) pass, not a cross join) -- no behavior
change.
- `fmt(already-canonical)` -> no-op.

T-0984: fixed an off-by-one in `_canonical_lines`' word-boundary cut
search (`rfind(" ", 0, budget + 1)` let a space AT index `budget` itself
match, and keeping that space on the earlier line produced a physical
line one column over `limit`) -- this is the bug T-0972 found wrapping to
89 columns against an 88-char limit and touching ~180 out-of-scope files
on a repo-wide run. Fixed by excluding index `budget` from the search span
(`rfind(" ", 0, budget)`); regression coverage in
`tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984` pins the
at-limit/one-under/one-over boundary plus the specific space-at-budget
shape that triggered the overflow.

Public API (`src/frob/gates/_fmt_directives.py`):

- `marker_for(path) -> str | None` -- the line-comment marker (`#`, `//`)
  for a file's suffix, or `None` for an unsupported language. T-0441 scope
  is `#`/`//` line comments only; a directive written inside a `/* */`
  block comment is left untouched.
- `read_line_length(root) -> int` -- reads `[tool.ruff] line-length` from
  `root/pyproject.toml`, falling back to ruff's own default (88). This is
  Python's OWN width source (see `resolve_line_length` below) -- ruff
  stays the sole owner of Python's limit, unchanged by T-1606.
- `resolve_line_length(path, root) -> int | None` (T-1606) -- the width
  `path`'s OWN formatter would enforce, replacing the pre-T-1606 design
  where every supported language wrapped against ruff's single
  project-wide number. Per language:
  - Python (`.py`/`.pyi`): `read_line_length(root)`, unchanged.
  - Rust (`.rs`): the nearest `rustfmt.toml`/`.rustfmt.toml`'s
    `max_width`, walking upward from `path` to `root` (nearest wins, like
    rustfmt's own resolution in a monorepo); falls back to rustfmt's
    documented default (100) if none is found or the key is absent.
  - TS/JS (`.ts`/`.tsx`/`.js`/`.jsx`/`.mjs`): the nearest prettier config
    (`.prettierrc[.json|.yaml|.yml|.toml]`, or a `package.json`'s
    `prettier` key -- both walked for together, nearest wins) `printWidth`,
    falling back to prettier's documented default (80). A `.prettierrc.js`/
    `.cjs`/`.mjs`/`prettier.config.*` module is deliberately not parsed
    (would mean executing arbitrary JS) and falls back to the default the
    same as having no config at all.
  - C-family (`.c`/`.h`/`.cc`/`.cpp`/`.hpp`/`.hh`): the nearest
    `.clang-format`'s `ColumnLimit`, falling back to clang-format's
    documented default (80).
  - Every other registered suffix (currently only `.strata`, which has no
    formatter of its own): falls back to `read_line_length(root)`, the
    same ruff-derived value it used before T-1606 -- a deliberate,
    documented default rather than an unstated policy call (see the
    function's own T-1606 design-decision comment in
    `src/frob/gates/_fmt_directives.py`).
  - `None` is a first-class return value meaning "this language's
    formatter has no configurable width at all" (gofmt, `zig fmt`,
    `shfmt` are the motivating examples -- none of them are registered
    `_MARKERS` languages yet, so this branch is proven at the
    `canonicalize_text`/`_canonical_lines` level today, not reached
    through `resolve_line_length` itself until such an adapter lands).
    Callers must skip width-wrapping entirely on `None`, never substitute
    a default.
- `canonicalize_text(text, *, path, limit) -> str` -- rewrites every
  `frob:` directive run in `text` to canonical form; non-directive
  comments and all code are untouched byte-for-byte. `limit: int | None`
  (T-1606): `None` means `path`'s language has no width concept -- every
  directive run is folded to one logical line and never wrapped.
  T-0985: a run whose logical text ends in a `# noqa`/`# noqa: CODE`
  pragma is a deliberate escape hatch (content is one unbreakable token,
  e.g. a long dotted pytest node id with no space to wrap at) and is left
  byte-identical rather than force-wrapped -- previously the pragma
  comment was treated as ordinary directive text and force-wrapped
  anyway, defeating its purpose.
- `format_paths(root, *, check_only, limit=None) -> FmtReport` -- walks
  `root` (via `frob.excludes.iter_files`, so the usual excluded/pruned dirs
  are skipped) and canonicalizes every supported file; `check_only=True`
  reports without writing (`frob fmt --check`, CI-friendly, exits 1 if
  anything is non-canonical). T-1606: `limit=None` (the default) resolves
  EACH FILE'S OWN width via `resolve_line_length` -- a single walk over a
  mixed-language tree wraps Rust against rustfmt's config, TS/JS against
  prettier's, C-family against clang-format's, and Python against ruff's,
  all in the same run. Passing an explicit `limit` overrides this
  per-file resolution uniformly for the whole walk (used by tests, and by
  any caller that genuinely wants one number everywhere).

**T-0985: repo-wide recompaction was deliberately deferred, then unblocked
by T-0987.** A large slice of this repo's own `frob:` directive comments
predate T-0441's "fewest physical lines" canonical form (hand-wrapped, or
wrapped by an older/looser tool version) -- a fresh `frob fmt .` still
reports ~260 files as non-canonical purely from this legacy layout, even
after the noqa fix above. Actually performing that one-time repo-wide
recompaction was investigated and found UNSAFE at the time: rewrapping
shifts word-wrap boundaries, and in some files this placed a `frob:`-
shaped prose token (inside a `reason="..."` string, referring to
`frob:describes` by name rather than invoking it) at the start of a
continuation line, which `frob.graph.dsl.parse_directives` misparsed as a
bogus new directive. **T-0987 fixed the underlying DSL bug**: the fold
guard in `frob.graph.dsl.fold_comment_runs` no longer stops a fold merely
because the next physical line's text starts with SOMETHING shaped like
`frob:<token>` -- it now attempts a full structural parse of that line
(`frob.graph.dsl._is_genuine_directive_start`) and only treats it as a
fresh, independent directive if it actually parses as one (a real `Edge`,
or a recognized `_RESERVED_MARKER_VERBS` skip-marker). A shape match that
fails to parse (unknown verb, e.g. `describes`) is folded as continuation
prose instead, regardless of what its first token happens to spell. This
unblocks (but does not itself perform) the deferred repo-wide
recompaction; see T-0987's Done report.

Folding an existing continuation run back into one logical string reuses
`frob.graph.dsl.fold_comment_runs` -- T-0286's own continuation fold,
extended with a physical-line-count 4th tuple element so a caller that
needs to REWRITE physical lines (not just read the folded text, which is
all `frob.graph.dsl.parse_directives` needs) knows exactly which lines a
logical directive's current form spans. `_fold_continuations` is now a
thin wrapper over `fold_comment_runs` that drops the count -- one fold
implementation, not two.

**CRLF preservation (T-0441 review round 1 fix).** `format_paths` reads
and writes through the plain `open()` builtin with `newline=""`
(`pathlib.Path.read_text`/`write_text` only gained a `newline=` parameter
in Python 3.13; this repo targets 3.11) -- this disables Python's
universal-newline translation in BOTH directions. Without it, reading a
CRLF-authored file (any Windows-authored TS/Rust/C/C++ source) silently
translates every `\r\n` to `\n`, and writing back re-translates `\n` to
`os.linesep` (a no-op on Linux) -- so on a Linux worktree, a `frob fmt` run
over a CRLF file flattened EVERY line's terminator to LF, including lines
the formatter never touches, not just the directive it rewrapped.
`canonicalize_text` itself preserves each untouched physical line's own
trailing `\r` verbatim (it only ever splits on `"\n"`, never `"\r\n"`), and
re-attaches a matching `\r` to any freshly generated canonical directive
line based on that RUN's own original convention (not a single
file-global guess). `format_paths`' check-only change-detection
(`rewritten == original`) reads both sides through the same `newline=""`
transform, so it cannot report a false-positive change from a
newline-translation mismatch between the two reads.

**T-0441 known cut, closed by T-0851:** `frob check`'s own remediation-hint
half of this ticket ("directive line over NN cols; run `frob fmt` to
wrap", emitted as a `frob check` finding when a non-canonical directive
line is touched) was NOT implemented in T-0441's pass -- `src/frob/check/`
was outside its declared scope, and wiring a new gate rule into the
existing stage/rule-catalog machinery in `frob.gates.__init__` and the
check orchestrator was a separate unit of work. See "FMT001 (T-0851)"
below for the gate that closes this gap. `frob fmt --check` remains
available standalone (non-zero exit on any non-canonical file) either way.

### FMT001 (T-0851)

`frob.gates.fmt_gate` (gate name `fmt`, default-on, WARN severity,
diff-scoped). The T-0441 follow-up above: fires when a diff-touched
`frob:` directive comment line exceeds that file's OWN configured line
length. T-2761: each touched file resolves its own width via
`frob.gates._fmt_directives.resolve_line_length` (rustfmt.toml's
`max_width`, a prettier config's `printWidth`, `.clang-format`'s
`ColumnLimit`, nearest-config-wins, or `read_line_length`'s ruff-derived
project limit for Python and any other still-ruff-derived suffix) rather
than one project-wide `read_line_length(root)` applied uniformly to every
language -- a file whose own formatter has no configurable width at all
(`resolve_line_length` returns `None`) is never flagged. Reports a
remediation hint naming `frob fmt <path>` as the auto-fix -- the same
self-remedying-message contract as every other gate.

Additive only, by design: FMT001 never suppresses or rewrites the
underlying ruff `E501`/lint finding on the same line -- it only
*annotates* the situation with the one-command fix. A directive line over
the limit still shows up as a normal ruff finding too; FMT001 exists so an
agent chasing the ruff finding also sees the faster remedy instead of
hand-wrapping (fighting T-0286's own continuation syntax by hand) or
truncating the reason.

Detection reuses two pieces of T-0441's own machinery rather than
re-deriving them: `marker_for` (which languages/suffixes are in scope --
`#`/`//` line comments only, same as `frob fmt` itself) and
`frob.graph.dsl.fold_comment_runs` (the same continuation-run folding
`canonicalize_text` folds through, so a run's boundaries are identified
exactly once, in exactly one place). Diff scope comes from the same
`Diff.hunks` machinery TODO001 uses (`_touched_files`/hunk spans) -- only
physical lines the diff's hunks actually cover are checked, never a
pre-existing non-canonical line elsewhere in an untouched part of the
file. Only a folded run whose logical text starts with `frob:` is
checked: an ordinary long comment or a long code line never enters such a
run, so neither is flagged -- matching the gate's own remediation (`frob
fmt` only ever rewrites directive lines, so a finding named FMT001 must
mean a directive line specifically).

## Design decisions

- **Gates are pure functions over loaded state.** Load once (snapshot,
  queue, lock, diff, tests), run gates in parallel. Most gates run on a
  `ThreadPoolExecutor`; the CPU-bound giants (archgate, sys, clones, perf,
  pii_structural, secrets -- docs/audits/perf.md H3) run on a separate
  `ProcessPoolExecutor` instead, so they get real parallelism rather than
  GIL-serializing on the shared thread pool (T-0415). Results from both
  pools are merged back in a fixed gate-name order, so output stays
  byte-identical regardless of which pool finishes a given job first. No
  gate does IO; `run_gates` owns all loading.
- **Ticket context is optional; scope/pre-work gates degrade to skipped,
  not failed**, when no ticket resolves -- humans doing exploratory work on
  main are not fighting the tool. COV002 still catches unticketed diffs at
  check time, so nothing escapes; it just fails later rather than louder.
- **Every violation message embeds its remedy** ("run: frob ack <ref>",
  "run: frob ticket new ..."). Agents act on messages; a message without a
  next command is a dead end.
- **Waivers are per-site, reasoned, and reported.** Global rule disabling
  requires editing `frob.toml` in a reviewed commit.
- **Bare TODO/FIXME comments are violations** (TODO001). The habit the
  system replaces must not survive alongside it.
- **COV002 has a same-diff grace window for a ticket that just closed**
  (T-0214). Without it, closing the covering ticket while its edit is still
  uncommitted is a catch-22: the ticket moves out of `_OPEN_STATES`
  immediately, so every symbol it was covering becomes a hard "changed with
  no open ticket" error before the user has a chance to commit. The
  narrowest honest fix: a `DONE` ticket's `frob:ticket` edge still counts
  if `tickets.md` itself is part of the current diff -- i.e. the close and
  the covered edit are landing together as one change, not two. Once the
  close lands as its own commit and drops out of the diff, the grace window
  closes and a genuinely later, unrelated touch to the same symbol is
  caught exactly as before.
- **The same-diff grace window is mode-aware (T-1582).** The grace
  machinery above was implemented against `tickets.md`'s monofile hunks
  before ledger v2 existed, and stayed v1-only after T-1553 made a fresh
  repo default to v2: `_ledger_states_at_base` read a ticket's pre-diff
  state out of `git show <base>:tickets.md`, a path absent from a v2
  repo's own file layout, and `_ticket_marker_in_diff_hunk` scanned
  `tickets.md` for a `<!-- ticket:<id> -->` marker block that likewise is
  never present there.
  A v2 repo therefore got `{}`/`False` from both, silently denying grace
  on every single ticket-close-in-the-same-diff -- exactly the
  worktree-agent flow the grace exists to permit, false-firing COV002 on
  every new frob repo's very first close. Both helpers now dispatch on
  the ledger's store mode: `_store_mode_at_base(root, base)` (a
  git-object-based historical analog of `frob.tickets._store._store_mode`,
  since the grace needs the mode as it stood BEFORE this diff, which can
  differ from the current mode across a v1 -> v2 migration commit) picks
  `_ledger_states_at_base`'s branch -- v1 keeps the `tickets.md` blob read
  unchanged, v2 lists every `tickets/T-####/ticket.md` blob at `base` via
  `git ls-tree` and reads each one's `state:` field directly out of its
  git object. `_ticket_marker_in_diff_hunk` checks the CURRENT working
  tree's mode instead (`frob.tickets._store._store_mode` directly -- this
  question is "did THIS diff touch this ticket's storage", not a
  historical one): in v2 mode, one ticket owns one whole file, so "the
  ticket's marker is in a touched hunk" collapses to "this ticket's own
  `tickets/<id>/ticket.md` has a hunk in the diff", with no block-span
  scanning needed at all (there is no other ticket's content in the same
  file to accidentally match against, unlike v1's shared monofile).
- **COV005 catches a directive silently rebound to the WRONG symbol, not
  just an unattached one** (T-0297). COV001 only proves a directive resolves
  to SOME symbol; it says nothing about whether that symbol is still the
  one the directive's author meant. Extracting a private helper directly
  above an existing public `def` (a common refactor shape) silently moves
  every trailing `frob:` directive that used to describe the public `def`
  onto the new private helper, because the DSL's `following`/`enclosing`
  binding always attaches to the NEAREST symbol below the comment, not the
  one the author intended -- and every other gate stays green afterward,
  since the directive still resolves. This bit twice in this repo's own
  history (`scan_tree`, `renumber_one`) and was only caught by manual
  review. COV005 is git-diff-aware and scoped to files the current diff
  touches: for each `(kind, target)` pair a directive carries in the
  current tree, it compares against the SAME `(kind, target)` pair's
  binding at `diff.base` (via `git show <base>:<file>`, reparsed) -- if that
  pair bound a PUBLIC symbol at `diff.base` and now binds a PRIVATE one, it
  is a CANDIDATE rebind, flagged as an ERROR only if the new private
  symbol's own span also overlaps one of the diff's hunks in that file --
  i.e. the private symbol carrying the directive is itself part of what
  this diff just changed, the "extracted helper directly above an existing
  def" shape the ticket describes. A `(kind, target)` pair alone is NOT a
  unique directive identity: this repo's own convention reuses one
  `frob:doc <page>#<anchor>` target across every public function a doc
  page covers, so comparing old vs new bindings FILE-WIDE (without the
  hunk-overlap restriction) flagged roughly 50 pre-existing, untouched
  private helpers that merely happen to share an anchor with some
  unrelated public function elsewhere in the same file -- the
  hunk-overlap guard is what keeps COV005 from being a repo-wide,
  diff-oblivious full scan. Files with no
  resolvable blob at `diff.base` (new files) are skipped -- there is no
  "before" to compare a new file's directives against, and COV001 already
  covers a new symbol's own missing-doc obligation. The other two
  candidate detections from the ticket -- (b) `frob:tests` evidence whose
  named test does not actually reach the bound symbol (call-graph
  reachability, ties into T-0288/T-0290's shared substrate) and (c) a
  `frob:doc #public-api` anchor specifically on a private helper -- are
  deliberately out of scope for this pass; each needs its own ticket rather
  than folding into COV005's git-diff comparison.
- **pytest collection is the evidence oracle** for test node ids, cached in
  `.frob/` keyed on test-file hashes; running tests is `make test`'s job,
  existence is the gate's job.
- **Test obligations verify existence, quantity, and measured reach -- not
  quality.** Counts and coverage floors are gameable proxies (assert-free
  tests pass them); the honest quality oracle is mutation testing, which is
  tracked in the ticket ledger (mutation testing shipped as `frob mutate`). A `pattern` policy rule
  banning assert-free test functions ships as a first defense.
- **Interfaces are derived, not declared.** Any package whose public
  symbols another package imports owes integration tests; deriving this
  from the graph means a new boundary cannot be forgotten. Pair-level
  (consumer x provider) strictness is deferred; per-provider at alpha.
- **Coverage thresholds are floors in config, not goals in prose.**
  Raising a floor is a reviewed `frob.toml` commit; lowering one is too,
  and shows up in diff review.

## Root-scanning process-pool gate cache (T-1445)

`docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602`
documents T-0602's `TrackedSnapshot`/`evaluate_cacheable_gate` cache for
the thread-pool `_CACHEABLE_GATES` allowlist -- gates that read only
`GraphSnapshot`-derived state. T-1445 extends the SAME `.frob/gate-cache.db`
storage to `_CACHEABLE_PROCESS_GATES`, the `_ProcessJob` gates (T-0415's
CPU-bound giants) that read `st.root`/`st.repo_root` directly instead:
`perf`, `clones`, `sys`, `secrets`, `taint`, `opaque`, `archgate`,
`exhaustive_handling`, `ffi_boundary`, `pii_structural`, `walk_lint`,
`cve_fingerprint_scan`, `render_lint`, `dead_symbols`, `wire`, `cache`,
`protocol_summary` -- effectively every `_build_process_jobs` entry.

- **Key**: `frob.gates._gate_cache.root_content_key` -- a sha256 over
  `git ls-files -s`'s full output (mode, blob sha, path per tracked file),
  the whole-tree analogue of `_membership_key`'s `GraphSnapshot`-scoped
  membership guard. Any add/remove/edit of any tracked file anywhere
  invalidates every `_CACHEABLE_PROCESS_GATES` entry -- WHOLE-GATE
  granularity, not per-touched-file like T-0602's thread-pool cache (a
  process-pool gate's `_ProcessJob.args` never touches the indexed
  `GraphSnapshot` at all for most members, so there is no cheap way to
  observe a finer-grained read set without splitting each gate's body
  into a per-file callable -- out of this ticket's scope; see the T-1445
  Done report in `tickets-archive.md` for the follow-up ticket tracking
  true per-file decomposition).
- **Storage**: `load_root_gate_cache`/`store_root_gate_cache`
  (`frob.gates._gate_cache`) read/write the SAME `gate_results` table
  T-0602's `evaluate_cacheable_gate` already owns, with
  `membership_key == touched_key == root_content_key(...)` and no
  per-file `touched_files` set (there is none at this granularity).
- **Side inputs**: `clones` (`st.diff`) and `wire` (`st.diff`, `st.queue`)
  are the only two `_CACHEABLE_PROCESS_GATES` members with an argument
  beyond `root`/`repo_root`/`snapshot` -- `frob.gates._process_gate_extra`
  folds them into the same `extra_key` T-1454's `model_side_channel_key`
  already established for the thread-pool side.
- **Dispatch**: `frob.gates._split_process_cache` partitions a run's
  selected `_ProcessJob`s into cache HITS (served without spawning a
  worker process, `_seed_preloaded_process_cache`) and MISSES (submitted
  to the `ProcessPoolExecutor` as before, with the fresh result persisted
  after draining via `_store_pending_process_cache`) -- `run_gates(...,
  use_cache=True)` opts in, same flag T-0602's thread-pool substitution
  already uses; `use_cache=False` (every pre-T-1445 call site) is
  unaffected.
- **`frob check --no-cache`**: a first-class CLI flag (`AppConfig.
  check_no_cache`, threaded through `run_check`/`run_check_cpp`/
  `run_check_rust`/`run_check_ts`) bypassing the WHOLE gate-result cache
  (thread- and process-pool halves alike) for one invocation -- the same
  effect as the pre-existing `FROB_NO_GATE_CACHE=1` env var (T-1346),
  now also reachable without setting an env var.

## Dependencies

- `frob.graph` (snapshot, lock, drift), `frob.tickets` (queue),
  `frob.policy`, `frob.lang` (pattern queries).
- git via subprocess (diff, merge-base, branch name).
- `pydantic`, `typani`.

## Integration points

- `frob.check`: `run_check` gains a gates stage; `frob check --only gates`,
  `--ticket T-0042`, `--base <ref>` flags; exit code folds into the
  existing errors-first report and `frob parse` output format.
- `frob ticket start` calls `record_prework` (dup + xref over scope).
- Pre-commit hook and CI both run `frob check`; agents run it after every
  ticket before writing a done-report.

## Phase 4 implementation notes (deviations from the design above)

The design above is otherwise as-implemented. The following are the
concrete choices made where the design was ambiguous or where a
dependency's real API did not match the sketch:

- **`WAIVE001` is derived from `GraphSnapshot.malformed`, not a separate
  scan.** `frob.graph.dsl.parse_directives` already refuses to turn a
  `frob:waive` directive lacking `reason="..."` into an `Edge` -- it
  becomes a `MalformedDirective` instead. `gates._waive001_violations`
  simply surfaces any malformed directive whose reason text mentions
  `frob:waive`. Every `Edge` with `kind == WAIVE` that reaches a gate is
  therefore guaranteed to already carry a `reason` attr.
- **`prework_gate` takes an extra `sweep: Option[PreworkSweep] = Nothing()`
  argument** beyond the doc's `(ticket, snapshot)` signature. The sweep is
  loaded state (see below) and gates must not do IO, so `run_gates` loads
  it via `gates._prework.load_prework` and passes it in.
- **`invariant_gate` takes an extra `policy_rule_ids: frozenset[str] =
  frozenset()` argument** beyond `(invariants, snapshot, tests)`, so
  INV001 can treat a loaded policy rule id as valid evidence (the doc's
  own example evidence list includes `POL-no-direct-lock-write`); without
  it the pure function would have no way to see policy state.
- **`record_prework` storage**: `frob.tickets` exposes only
  `record_failure` (a fixed "## Failure log" section), not a generic
  body-section appender, and growing `frob.tickets`'s public surface is
  out of scope for this phase. The sweep is instead stored as JSON at
  `.frob/prework/<ticket_id>.json` (`gates/_prework.py`), read back by
  `load_prework`. `PRE001` compares `sweep.digest` against a fresh
  `_scope_digest(ticket, snapshot)` (sha256 over the ticket's scope-glob-
  matched `snapshot.file_hashes` entries).
- **Hunk-to-symref resolution is reimplemented in `gates`**, not imported
  from `frob.testing._select`: `select_tests` does the same span-overlap
  match inline as part of a larger algorithm and never exposes it as a
  standalone function. `gates._touched_symrefs`/`_touched_files` are a
  documented duplicate of that overlap primitive, same posture as the
  extension-table duplicates already accepted across
  `frob.graph`/`frob.testing`/`frob.policy`.
- **TEST003 interface derivation, alpha semantics**: the graph has no
  cross-file import edges (only `frob:` directive edges and doc anchors),
  so real "package A's public symbols imported by package B" derivation
  is not available. Alpha instead treats every `src/<pkg>/<subpkg>`
  directory containing at least one public, non-test symbol as an
  interface owing `min_integration` integration `frob:tests` edges -- the
  simple, honest over-approximation the design's own "Interfaces are
  derived, not declared" note anticipates. Pair-level (consumer x
  provider) strictness is deferred.
- **TEST001/TEST002/TEST005 skip symbols in test files themselves**
  (`frob.excludes.is_test_file`, imported by both `frob.gates` and
  `frob.testing._select`) -- a public `test_*` function does not owe
  itself a unit test.
- **TEST005 system floor** is approximated as the mean of `module_line`
  percentages for files matching any of `[[system]].paths`, since
  `CoverageData` (per the doc's own model) has no separate per-system
  map; `load_coverage` only ever produces `symbol_branch`/`module_line`.
- **`frob.gates` does not re-export `PolicyRule`/`PolicyError`/
  `load_policy`/`policy_gate`.** `frob.policy` imports `Violation`/
  `Severity`/`WaiverRef` from `frob.gates._models`, so a module-level
  `from frob.policy import ...` in `frob.gates.__init__` would form an
  import cycle the first time either package is imported standalone.
  `run_gates` imports `load_policy`/`policy_gate` lazily inside its own
  body instead; callers needing policy types import them from
  `frob.policy` directly.
- **`policy_gate`'s `forbidden-import` and `pattern` rules read file
  content off disk via `Path(snapshot.root)`** plus
  `snapshot.file_hashes` (for glob-matched file listing), since the
  signature `policy_gate(rules, snapshot, diff)` carries no separate
  root parameter; `GraphSnapshot.root` already carries it.
- **`GateError` collapses every loading failure** (`frob.graph`,
  `frob.graph.lock`, `frob.tickets`, `frob.gates.invariants`,
  `frob.policy`) into one of `GraphUnavailable` / `QueueUnavailable` /
  `ConfigMalformed` / `GitFailed` / `WriteFailed`, rather than a full
  `GraphError | LockError | TicketError | InvariantError | PolicyError`
  union, to keep `run_gates`'s `Result[GateReport, GateError]` a single
  small enum callers can match on directly.
- **Severity defaults per rule** are fixed in code (`ERROR` for
  DRIFT/COV002-004/SCOPE001/PRE001/INV001-002/TEST001/TEST004/WAIVE001/
  policy rules with no `severity` override; `WARN` for COV001, TODO001,
  TODO002, TEST002/003/005). Per-rule severity overrides in `frob.toml` were
  scoped out of this phase; `PolicyRule.severity` is the only
  user-configurable severity today (via `[[policy.*]].severity`).

## T-2670 backlog documentation

T-2664 extended DOCENUM001 to verify every member id in this file's own
`frob:enumerates` list resolves to a real row or heading somewhere in the
file; this section closes that backlog by giving each previously-undocumented
id a real row here, written from its actual gate implementation rather than
restating the id. New ids are grouped by source module for review, not
inserted into the main table above, to avoid a large unrelated reflow of
that table in this diff.

| Rule | Gate | Fails when |
|------|------|------------|
| BUDGET001 | budget (WARN, T-1703/T-2235) | `frob check --budget <seconds>` ran out of time and deferred one or more stage groups to a later run (`frob.app._check_chunking._budget_deferred_result`) -- an informational diagnostic, not a real defect, that names the deferred group(s) and whether the resume state was persisted (full run) or must be re-requested via the same `--only <group>` (an `--only`-scoped run never persists shared resume state, T-2250) |
| BUG003 | mutation_evidence (ERROR, T-2193) | a ticket's `frob:must-still-pass NODE-ID` designated control either FAILS when run against the ticket's own fix (a narrowing fix silently disabled the capability the control exercises) or never PASSED at the parent commit either (a misconfigured designation that cannot prove a "was working before" baseline) -- the positive-direction counterpart BUG002/TEST016 have no equivalent for, since both of those only ever prove a negative claim. Opt-in via the directive, not kind-restricted like BUG002 |
| CAP001 | capacity | a `design/` node's projected demand (`frob.strata._capacity`) exceeds its declared `Capacity.service_rate * replicas_max` total throughput -- a node with no declared `Capacity` or an unresolvable `service_rate` unit is skipped, never treated as infinite or zero capacity |
| CHECK001 | check_runner | `detect_project_type` could not map the repo to a known dispatchable language (`frob.app.check_runner._unknown_project_type_result`, T-0546) -- previously silently fell back to the Python toolchain and reported irrelevant ruff/ty noise; now fails loudly with the unrecognized `project_type` named instead |
| CLAUDE001 | check_runner (ERROR, T-1809) | a `.claude/hooks/sync-claude-config.py`-managed file differs from its materialized `~/.claude/` copy, or a managed source file is missing entirely (`frob.app.claude_runner.drift_report`) -- detection only, the fix is `frob claude sync`; opt-in on the managed-config hook existing at all |
| COMPLIANCE004 | compliance (T-0382) | an `OutOfScopeRegulation.caught_by` (`docs/design/registry/compliance.yaml`) cites a control id that does not resolve to any known compliance control -- an out-of-scope disposition claiming coverage from a control that does not exist |
| COMPLIANCE006 | decisions_compliance (ERROR, unwaivable, T-0894) | a `docs/design/registry/compliance.yaml` that was previously committed on this branch's history has since been deleted from the working tree -- an adopted compliance registry cannot silently degrade back to "never adopted"; same "adopted then deleted" family as DEC003/REG012 |
| COMPLIANCE007 | compliance (WARN, T-1244) | a `compliance.yaml` unit's disposition is `handled_by:COMPLIANCE005` where COMPLIANCE005 itself is the disposition doing the checking -- a vacuous self-reference that resolves to nothing. WARN, not ERROR: it surfaces a likely-wrong disposition rather than blocking on it |
| CVEFP001 | cve_fingerprint_scan (deny-by-default, T-1963-family) | a `CveFingerprint` catalog entry's `cwe_id` does not join any real `WeaknessEntry` in the joined `std.cwe` catalog -- an unresolvable CWE citation, refused rather than silently accepted |
| DEAD001 | dead_symbols (WARN) | a private (leading-underscore) function/class/method has zero references anywhere in the graph (excluding dunders and test symbols) -- unreferenced private code, waivable with `frob:waive DEAD001 reason="..."` |
| DEBT001 | debt_deprecated | a `frob:debt` directive is missing its required `reason="..."` and/or `ticket="..."` attribute -- a malformed debt marker |
| DEBT002 | debt_deprecated | a `frob:debt`'s `ticket="..."` names a ticket that is not open (missing or closed) -- debt tracked against work that is not actually tracked |
| DEBT003 | debt_deprecated | a `frob:debt`'s `until="..."` boundary has passed -- debt that was supposed to be resolved by now |
| DEC003 | decisions_compliance (ERROR, unwaivable, T-0894) | a `decisions/` directory that was previously committed on this branch's history has since been deleted from the working tree -- same "adopted then deleted" unwaivable-ERROR shape as COMPLIANCE006/REG012, instead of silently degrading to the never-adopted empty-result posture |
| DEPR001 | debt_deprecated | a `frob:deprecated` directive is missing/has an invalid `sunset="YYYY-MM-DD"` or `ticket="..."` attribute -- mirrors DEBT001's malformed-directive shape for deprecation markers |
| DEPR002 | debt_deprecated | a `frob:deprecated`'s `ticket="..."` names a ticket that is not open -- mirrors DEBT002's shape; suppresses DEPR003/DEPR004 for the same edge, since a mistracked ticket is the more actionable finding |
| DEPR003 | debt_deprecated (WARN, T-0576) | a `frob:deprecated` directive is bound to an open ticket and its `sunset` date has not yet passed -- a visible reminder while still inside the deprecation's warning window; suppressed by DEPR002 (bad ticket) or DEPR004 (already past sunset) |
| DEPR004 | debt_deprecated (ERROR, T-0576) | a `frob:deprecated` directive's `sunset` date has passed -- escalates DEPR003's warning to a hard error, mirroring DEBT003's own expiry escalation; remove the symbol and directive, or extend `sunset` with a written reason |
| DEPR005 | debt_deprecated (ERROR, T-0639) | a `frob:deprecated` symbol's reference set gained a NEW caller in some file since `frob-deprecated-baseline.lock.json` was last recorded -- code is actively adopting a symbol that is already on its way out, distinct from DEPR003/DEPR004's own time-based expiry |
| DEPLOY001 | check_runner (ERROR) | a committed `deploy/{install,status,uninstall}.sh` script does not byte-match a fresh regeneration from the design model -- a hand-edit drifted from the generator; catches THAT it drifted, not why (see DEPLOY002/DEPLOY003 for the structural why) |
| DEPLOY002 | deploy_conform | a committed deploy script performs a system mutation (`useradd`/`mkdir`/`chown`/unit-file write/`rm`/`systemctl`/...) that the design model's `HostManifest` does not declare -- a smuggled extra user, path, or unit; fires even against an otherwise byte-identical regeneration, so a hand-appended rogue mutation cannot bypass DEPLOY001 |
| DEPLOY003 | deploy_conform | a `HostManifest` entry (a declared `owns` path, a declared `runs_as` user) has no corresponding mutation anywhere in the committed deploy scripts -- an incomplete install or incomplete uninstall |
| DOC003 | sys (ERROR) | a `frob:claims <view>` doc marker names either an unknown baseline view, or a view that is not a PROVED exhaustiveness result (zero unresolved gaps) -- an unproved claim of exhaustiveness |
| DOC007 | docptr (ERROR, T-0986) | a `frob:tests` edge's TARGET string uses symref-shaped `path::Symbol` form instead of the required dotted `Class.method` node form -- waivable with `frob:waive DOC007 reason="..."` for a genuinely external/illustrative/future-facing pointer |
| DSL001 | waive | a `frob:` directive comment does not parse as any recognized verb (malformed syntax, unknown verb, or a claimed verb whose required attributes are missing/malformed) and is not already claimed by a more specific rule (WAIVE001-005) -- the generic catch-all for an unrecognized directive |
| E501 | fix_engine_text (Tier-A auto-fix, T-1547) | ruff's line-too-long check fires on a line in a `.py` file touched specifically by the most recent land-time merge (or the in-progress pre-land merge) -- `frob ticket land`'s Tier-A phase runs a targeted `ruff format` over just those merge-touched files and, if the line is still over the limit afterward, adds a `# noqa: E501` (unless `per-file-ignores` already silences E501 at that path); scoped narrowly to merge-introduced lines, not a repo-wide E501 sweep |
| EXHAUST003 | exhaustive_handling (WARN, T-0688/T-1402) | a function's exception handling includes a bare `raise` re-raise whose type this gate's call-graph resolver could not statically identify as escaping through a resolvable callee -- a resolution-COVERAGE gap distinct from EXHAUST001's confirmed ambiguous-reraise finding; narrow with `# frob:callee-raises <Type>` rather than adding a blind catch-all |
| EXHAUST004 | exhaustive_handling (WARN, T-1402/T-2543) | a function guards some exceptions but a type may still escape from a SUBSCRIPT access this gate's resolver could not shape-resolve (cannot tell a mapping `KeyError` from a sequence `IndexError`, nor bounds-checked from unchecked) -- lower-confidence sibling of EXHAUST002's confirmed-leak finding, split by provenance not by type text |
| FUZZ001 | fuzz (ERROR) | a function marked with a fuzz obligation (`FuzzObligation`) has no `frob:tests <symref> kind="fuzz"` edge targeting it -- a declared fuzz requirement with no fuzz test bound |
| HOST-BLAST | strata_audit | a compromised-user scenario's `blast-radius:<user>:<node>` claim is REFUTED -- the modeled compromise reached outside that user's own manifest slice, the exact failure HOST001/HOST002's structural proofs (T-0280) exist to prevent |
| LANG004 | lang_conformance (ERROR, T-2365) | a language adapter's capability registry claims a capability is `IMPLEMENTED` but the behavioral fixture check (`_behavioral_capability_check`, run against a real per-language tmp fixture) fails -- the BEHAVIORAL half of the adapter-capability axis: LANG001 only verifies the registry is internally accounted for, this gate verifies the claim is actually TRUE |
| LEDGERV1001 | tickets_gate | a repo still has legacy ledger content on disk: monofile mode warns while inside its recorded sunset window and errors past it (mirroring the DEPR00x warn-then-error shape); a v2-mode repo with a lingering `tickets.md`/`tickets-archive.md` (an unfinished cutover) errors unconditionally, no sunset grace -- remedy is `frob ticket migrate --to v2` or deleting the stray monofiles |
| PERF001 | perf | `x in <list>` (or non-Python `.includes`/`Vec::contains`) membership test against a list-shaped collection tested repeatedly inside a loop -- build a set/HashSet/Map once outside the loop and test membership against that instead (`frob.perf._rules`) |
| PERF003 | perf | nested loops whose inner loop does an equality comparison against the outer loop's variable -- an O(n*m) linear scan; index the inner collection by the compared key once instead of re-scanning it per outer iteration (`frob.perf._rules`) |
| PERF004 | perf | a `sorted(`/`.sort(` call sits inside a loop body -- the sort re-runs every iteration instead of once; hoist it out of the loop or use a sorted container (`frob.perf._rules`) |
| PERF008 | perf (WARN, T-0775) | a call inside a loop has loop-invariant arguments and transitively reaches an effectful call (I/O, subprocess, etc.) -- the effect re-runs every iteration for no varying input; hoist the call out of the loop, memoize its result, or waive with a reason (`frob.perf._loop_effects`) |
| PERF009 | perf (WARN, T-0712) | a `.frob/perf/ratchet_findings.json` entry recorded by the performance regression ratchet shows a benchmark section regressed beyond its tolerance versus its prior deciles -- named at the findings file itself, since a ratchet finding has no stable source line of its own (`frob.perf._ratchet`) |
| PERF011 | perf (T-1225/T-1647) | a full-repo-scan API call (`xref`/`exports_consumers`/`iter_files`) is invoked from inside a loop over symbols -- the O(n) scan re-runs per iteration instead of once; a call that IS the loop's own single iterable expression is exempted, since that runs once, not per iteration (`frob.perf._hotpath_smells`) |
| PERF012 | perf (WARN, T-1115) | a function has 2+ call sites that each independently reach the same subprocess-spawning (or other identical-effect) call with the same argument shape -- share one result between them instead of paying for it N times, or waive with a reason justifying an independent re-run (`frob.perf._dup_spawn`) |
| PORT001-IDENT | port_selfcheck | a gate rule's source hardcodes this repo's own package name (`"frob"`) as a bare identity-comparison literal (not a path prefix) -- portable only to THIS project; NOT part of PORT001-PATH's WARN-to-ERROR promotion bar, since it changes no gate behavior in a checker-consumer's own repo, only maintainer-facing message text (`frob.gates._port_selfcheck`) |
| PORT001-PATH | port_selfcheck | a gate rule's source hardcodes a `"src/<pkg>/"`-shaped string constant (this repo's own package name as a path prefix) -- a checker that should target ANY consumer's own layout instead targets only this repo's; part of the WARN-to-ERROR promotion bar tracked toward zero (`frob.gates._port_selfcheck`) |
| REG001 | registry | (error) a `docs/design/registry/*.yaml` entry's disposition is missing, `pending`, or an `out_of_scope` disposition with no reason text -- an undispositioned or reason-less registry entry (`frob.gates._registry_exhaustiveness`) |
| REG008 | registry | (error, T-2369) an entry dispositioned `handled_by:<rule>` has no corresponding `frob:enforces` edge in the code graph binding that rule id to real enforcement -- a claimed-but-unwired handler; promoted WARN->ERROR once the corpus's undeclared-enforcement count reached zero (`frob.gates._registry_exhaustiveness`) |
| REG010 | registry | (warn, advisory) a LIVE rule in the known-rules set has no registry entry claiming it at all -- code-side enforcement with no corpus-side accounting, the reverse direction of REG008/REG009's conformance check (`frob.gates._registry_exhaustiveness`) |
| REG011 | registry | (warn, T-0680) an `out_of_scope:<reason>` disposition's reason text does not parse as a substantive, reasoned-none disclosure under the registry's out-of-scope grammar -- a reason string present but not actually saying anything (`frob.gates._registry_exhaustiveness`) |
| REG012 | registry | (error, unwaivable, T-0894) a `docs/design/registry/` directory that was previously committed on this branch's history has since been deleted from the working tree -- same "adopted then deleted" unwaivable-ERROR family as COMPLIANCE006/DEC003 (`frob.gates._registry_exhaustiveness`) |
| REL200 | sys (error) | a flow has no `timeout` attr declared and no exemption (`async` fire-and-forget, or `local` for a non-boundary-crossing flow) -- deny-by-default: every remote/cross-boundary flow must declare a timeout obligation (`frob.strata._reliability`) |
| REL201 | sys (error) | a flow declares `timeout` but neither endpoint has bound code containing a real `timeout=`-shaped token -- an unproven declaration, the T-0331 provability constraint that forbids discharging an obligation by bare declaration alone (`frob.strata._reliability`) |
| REL210 | sys (error) | a long-lived service/daemon node has no `health` attr declared and no exemption -- missing health-check surface, same deny-by-default shape as REL200 (`frob.strata._reliability`) |
| REL211 | sys (error) | a node declares `health` but has no bound code containing a real health-check-shaped token -- unproven health surface, mirroring REL201's provability constraint (`frob.strata._reliability`) |
| SEC-CVE-FINGERPRINT-001 | cve_fingerprint_scan (T-0439) | a git-tracked, first-party source file matches a known vulnerable-usage code fingerprint from the CVE fingerprint catalog (a literal needle string, not merely importing the vulnerable package) -- waivable with a reasoned `frob:waive SEC-CVE-FINGERPRINT-001 reason="..."` if the match is a false positive |
| SYS101 | strata_selfconform | a capability DECLARED in a node's `may` atoms has zero observed sites anywhere in that node's `code=`-bound files -- the reverse direction of THREAT004 (which only catches an OBSERVED effect with no matching `may` declaration); a declared-but-unexercised capability grant (`frob.strata._selfconform`) |
| SYS102 | strata_selfconform | a `src/frob/` top-level directory's `.py` files are ALL bound to `FOREIGN` (or entirely absent from `bind_code`'s partition) -- no node's `code=` glob claims the directory at all, an unmodeled corner of the codebase (`frob.strata._selfconform`) |
| SYS108 | strata_selfconform (ERROR, T-1624) | a node's `interface=` attrs contain the same symbol name more than once -- a duplicated declaration in a language meant to be the single source of truth for declared public surface (`frob.strata._selfconform`) |
| SYS110 | strata_selfconform (ERROR, T-1629) | a node's REAL public surface contains a symbol outside its hand-declared `interface=` intent set -- an accidental surface leak, once the node has opted in by declaring at least one `interface=` attr (a node with zero declared attrs is silently skipped, phased-migration design) (`frob.strata._selfconform`) |
| SYS111 | sys_selfaudit (T-1628/T-1977) | the capability-ratchet check (`capability_ratchet_violations`) finds a node's declared capability grants regressed against their recorded baseline -- wired into `frob sys audit`'s live gate surface after being built-but-uncalled since T-1628 |
| SYS112 | sys_selfaudit (T-2503/T-2523) | an ambient (via-less) `may` grant in `.strata` source has no `// because: "..."` justification comment -- an unscoped whole-node grant with no recorded reason, wired into the live gate surface after being built-but-uncalled since T-2503 |
| SYS200 | strata_contention | two distinct nodes both declare the same `listens` port -- a duplicate-port resource contention finding (`frob.strata._contention`) |
| SYS205 | strata_mode_conformance (T-0700) | a node's own bound code exhibits an effect (e.g. a write-mode `open()` call) its declared `access ... mode MODE` clause forbids -- the code's real behavior does not conform to its declared resource-access mode (`frob.strata._mode_conformance`) |
| SYSWAIVE002 | strata_contention | a `waive "RULE" reason="..."` clause on a node's SYS2xx resource-contention family (SYS200-203) matches zero findings this run -- a stale waiver, mirroring WAIVE004's unnecessary-waiver detection for the `strata` DSL (`frob.strata._contention`) |
| TEST008 | tickets_gate (ERROR) | `coverage.xml` carries real class data but NONE of it joins to a known repo path via any attempted root -- TEST005's coverage floors would silently be measuring nothing; a hardcoded/wrong `--cov=` target must fail loudly, never degrade to a quiet zero |
| TEST012 | tickets_gate (WARN, T-0545) | the committed `frob-coverage.lock.json` is missing, or its claimed per-module line coverage has drifted from this run's `coverage.xml` -- an opt-in-by-adoption mechanism, WARN until the lock is established as standard practice |
| TEST016 | mutation_evidence (T-0755) | a ticket's own bound evidence tests never killed a single mutant of a diff-touched, in-scope file -- confirmatory-only evidence; ERROR for `bug`/`security`-kind tickets, WARN otherwise. `Err(ExecDisabled)` (the mutation-exec kill switch was active) degrades to no violation rather than a false-clean pass |
| THREAT006 | strata_threat (T-0382) | an `OutOfScopeEntry`/`BenignCapability`'s `caught_by` string references a rule id or CWE id that resolves to neither the live gate-rule set nor the cataloged CWE ids -- an unresolved control citation, deny-by-default (an honest `caught_by="none"` disclosure is exempt) |
| TICK001 | tickets_gate (ERROR, T-0162) | a ticket id is present in BOTH the active ledger (`tickets.md`) and the archive (`tickets-archive.md`) -- an id collision across the two stores |
| TICK002 | tickets_gate (ERROR) | a `T-draft-*` provisional id is still present in the ledger while `root` is on the default branch -- a draft id survived onto `main` instead of being renumbered at land |
| TICK004 | tickets_gate (WARN, escalating to ERROR at 2x threshold, T-0411) | a QUEUED/PLANNED ticket has sat past its priority-specific rot-day threshold since `created` -- the queue-health signal that catches "we forgot we have a stack of things"; an already-decomposed epic/story or a `runs_last` ticket gets a distinct, action-specific message instead of the generic "work it" text |
| TICK005 | tickets_gate (ERROR, T-0537) | after a genuine two-parent merge commit, a ticket that was DONE/DROPPED in the merge's first-parent ledger is neither terminal nor archived in the post-merge ledger -- a hand-resolved `tickets.md` merge conflict silently resurrected a closed ticket's stale state |
| TDD001 | tdd_order (ERROR/UNRESOLVED, T-3009) | a `frob:tests` edge's artifact/implementation symbol was introduced (by real ast-symbol-level git history, not a text search) at or before the test that verifies it -- implementation-first or same-commit, neither test-first (T-3004 section 7); reports `Severity.UNRESOLVED`, not a pass, only when ordering is genuinely indeterminate (an unresolvable commit, or diverged histories) |
| VET-JS | vet_scan (ERROR) | a `node_modules` package declares a lifecycle script (`preinstall`/`install`/`postinstall`) not covered by an explicit `[vet.allow]` entry -- install-time code execution outside the reviewed allowlist |
| VET-JS003 | vet_scan (ERROR) | a newly-encountered npm dependency's name is a possible typosquat of a known popular package (Levenshtein-adjacent name match) -- flagged before any capability scan runs |
| VET-JS004 | vet_ecosystem (WARN) | an npm dependency resolves to a non-registry source (git/http/file URL, not `registry.npmjs.org`) -- declarable-only, review the pin |
| VET-PY001 | vet_ecosystem (ERROR) | a Python dependency's `setup.py` declares `cmdclass` -- install-time code execution |
| VET-PY002 | vet_ecosystem (ERROR) | a Python dependency ships one or more `.pth` files -- interpreter-startup code execution |
| VET-PY003 | vet_ecosystem (WARN) | a Python dependency ships `.pkl`/`.pickle` payload files -- serialized-code load is equivalent to eval |
| VET-RS001 | vet_ecosystem (ERROR) | a Rust dependency's `build.rs` exercises real capabilities (file/network/process, via `scan_file_capabilities`) at `cargo build` time |
| VET-RS002 | vet_ecosystem (ERROR) | a Rust dependency's `Cargo.toml` declares `proc-macro = true` -- a proc-macro crate executes inside the compiler itself, requiring an explicit `[vet.allow]` declaration |
| VET-SOURCE-UNAVAILABLE | vet_scan (ERROR, T-0400) | a dependency's source could not be located locally (not installed/cached) so its capability scan never ran -- fail-closed: a dependency that was never read must never look indistinguishable from one that was read and found clean |
| VET-TIMEOUT | vet_scan (WARN, T-0208) | a dependency's per-package scan budget expired before the capability scan completed -- an honest incomplete-verdict outcome, never silently dropped from the report; WARN since a timeout means "not fully checked", not "found bad" |
| WAIVE008 | waive (WARN) | a `frob:waive WIRE001 ...` directive sits on a symbol that is one of WIRE001's own dynamic-dispatch rescue predicates (an autouse pytest fixture or pydantic validator), now unconditionally exempt from WIRE001 regardless of diff -- a permanently dead waiver that WAIVE004's own diff-scoped staleness check cannot see |

## TDD001 (T-3009)

Enforces T-3004 section 7's TDD discipline as a checkable git-history
fact: a `frob:tests` edge's test symbol must be introduced BEFORE the
artifact/implementation symbol it verifies. Generalises BUG002's
single-case precedent (`frob.gates._bug_repro` requires a bug ticket's
designated repro test to fail at the parent commit -- proof it existed
and genuinely failed before the fix) from one designated repro to every
`frob:tests` binding.

WHERE THIS RUNS: pre-land, against a ticket's own worktree branch commit
sequence -- never post-land against `main`. `frob ticket land` squashes a
ticket's commits into one, so on `main` a `frob:tests` pair's two symbols
necessarily share the SAME introducing commit and ordering is
structurally unobservable there; running this check only while the
worktree branch's unsquashed history still exists is the one placement
that can actually see the fact this rule is about.

MECHANISM (`frob.gates._tdd_order`): `resolve_symbol_introduction` finds
a `path::qualname` symref's introducing commit by scanning that file's
own commit history OLDEST-first and `ast.parse`-ing each revision's real
content (`_ast_qualnames`), returning the first revision whose actual
function/class qualname set contains the symbol -- SYMBOL-LEVEL, not a
`git log -S<needle>` pickaxe text search: the standing "checks must
compare symbols, never substrings" directive rules out matching inside a
comment/docstring/string literal that merely mentions the name.
Python-only for now; a symbol this cannot resolve degrades to `None`
(`Severity.UNRESOLVED`) rather than a lexical fallback.

`classify_order` compares two introducing commits by git ANCESTRY (`git
merge-base --is-ancestor`, never committer timestamp, which is trivially
wrong under clock skew or a rebase) and reports one of three outcomes,
never two:

- `TDDOrder.TEST_FIRST` (silent): the test's commit is a STRICT ancestor
  of the artifact's.
- `TDDOrder.IMPLEMENTATION_FIRST` (`Severity.ERROR`, TDD001 fires): the
  artifact's commit is an ancestor of the test's, OR the two commits are
  IDENTICAL. A same-commit pair (this repo's dominant squash-land shape)
  is a DETERMINATE "not test-first" fact, not an unknown -- collapsing it
  into `UNRESOLVED` would make TDD001 structurally unable to ever fire
  against the workflow it exists to police while still reading as a
  passing check, exactly the silent-zero shape T-1664 exists to rule out.
- `TDDOrder.UNRESOLVED` (`Severity.UNRESOLVED`, T-1664's doctrine): either
  commit is genuinely unresolvable, or the two (distinct) commits'
  histories have diverged (neither is an ancestor of the other) --
  ancestry itself cannot order those. Never rendered as a silent pass --
  an honest "cannot tell" beats a comfortable "fine".

`tdd_order_violations(root, edges)` is the whole surface: it filters
`edges` to `EdgeKind.TESTS` (`src`=artifact, `target`=test, the existing
one-level binding T-3004 section 1 identifies as the thing to
generalise) and classifies each pair. It MUST be called pre-land against
a ticket's own worktree branch -- a post-land call against `main` cannot
observe the ordering fact this rule checks. Wiring this into `frob
ticket land`'s pre-land check path (mirroring BUG002's own
`bug_repro_violations` call site in `frob.tickets._land`) is deferred to
a follow-up ticket -- this ticket's scope is the check and its rule, not
the waterfall gate T-3004 section 9 explicitly defers.
