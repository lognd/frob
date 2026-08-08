# frob.gates -- enforcement gates, policy, and invariants

One sentence: the checks that join the obligation graph, the ticket queue,
docs, and policy rules, and turn every unaccounted-for change -- and every
unaccounted-for *absence* of change -- into a `frob check` failure.

Two enforcement halves (see `docs/rework.md`): the drift half (nothing
declared is silently broken) and the coverage half (nothing new escapes
declaration).

## Rule catalog

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
| COV007 | coverage | (warn) a `frob:doc` edge whose src symbol is PRIVATE -- see "COV006/COV007 (T-0483)" below |
| PLACE001 | coverage | (warn) a `frob:` directive that genuinely class-falls-back (not a directive that correctly resolved via `following` straight to a class it precedes) where a nearby real symbol looks plausibly missed -- see "PLACE001 (T-0504)" below |
| PARSE001 | parse_failures | `frob.lang.parse_file` could not parse/read a tracked source file at all -- its entire symbol/edge set is missing from this build (`GraphSnapshot.parse_failures`, T-0558/T-0561) |
| PARSE002 | parse_failures | `frob.lang.partial_parse_files()` names a file whose tree-sitter parse was SALVAGED around a syntax error (`has_error=True` but usable structure) -- every symbol after the error region is silently missing from this build (T-0905); graph-excluded paths (frob.toml [graph].exclude, e.g. deliberately-broken parser fixtures) are skipped, since they contribute no symbols and in-file waivers cannot bind there (T-0942) |
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
| TICK006 | tickets | a Done report's affirmative "filed" claim (`Filed: T-####`, `filed as T-####`, `Filed T-draft-<hex>`, ...) whose id resolves to no block in `tickets.md` or `tickets-archive.md` -- see "TICK006 (T-0726)" below |
| TICK007 | tickets | (warn) a dispatchable (unblocked, unleased) CRITICAL/HIGH ticket has sat past its `frob.tickets.undispatched_stale` threshold -- see "TICK007 (T-0820)" below |
| TICK008 | tickets | (warn) a ticket in the checked ledger carries unknown/extra frontmatter field(s) (`Ticket`'s `extra="allow"` captured them into `__pydantic_extra__` instead of hard-failing) -- often a typoed known field, whose value is silently lost to the schema default; see "TICK008 (T-0842)" below |
| TICK009 | tickets | (warn) a planned/in-progress ticket's declared scope is over-broad (`frob.tickets.large_glob_warnings`) -- relocated out of `frob ticket doable`'s own per-invocation output; QUEUED is exempt (T-1645), see "TICK009/TICK010 (T-0714)" below |
| TICK010 | tickets | (warn) a cross-worktree lease file (`.git/frob-leases/*.json`) whose recorded worktree path no longer exists on disk -- names the lease file and the remedy; see "TICK009/TICK010 (T-0714)" below |
| TICK011 | tickets | (warn) a Done report's prose discloses deferred/cut work (a conservative disclosure-phrase scan) with no ticket id resolving nearby and no explicit no-ticket-needed reason -- see "TICK011 (T-1129)" below |
| COMPLIANCE005 | compliance | a `docs/design/registry/compliance.yaml` `CMPL_REGISTRY_UNIT_IDS` member carries a `deferred`/undispositioned disposition instead of `handled_by`/`out_of_scope` -- see "COMPLIANCE005 (T-0788)" below |
| FMT001 | fmt | (warn) a diff-touched `frob:` directive comment line exceeds the project's configured line length -- see "FMT001 (T-0851)" below |
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
| DOC001 | doclink | a doc file matching `[gates.docs] include` globs (default `docs/**/*.md` -- new files auto-obligated) has no frob:describes anchor, no frob:doc edge into it, and is unreachable via markdown links from the roots (docs/index.md, README.md) |
| DOC002 | docanchor | a `frob:doc <file>#<slug>` edge whose target doesn't resolve: missing `#anchor`, missing file, or `<slug>` matches neither a heading slug (`frob.graph.dsl.slugify`) nor an explicit `<a id="...">` in `<file>` |
| DOC008 | doclink | (T-1231) an obligated doc's own inline markdown link `[text](target#frag)` doesn't resolve: relative `target` isn't a real file, or `#frag` matches neither a heading slug nor an explicit `<a id="...">` in the target |
| DOC009 | docstatus | (T-1232) a `docs/audits/*.md` file has no dated `Status: YYYY-MM-DD` (or `Status: SUPERSEDED (see <path>)`) header in its first 15 lines, or a superseded-by target doesn't resolve |
| DOC010 | docmake | (T-1230) a `` `make <target>` `` prose citation in an obligated doc isn't a real Makefile recipe |
| POL* | policy | user-defined rules from `frob.toml` (see below) |
| DUP001/DUP002 | clones | the diff introduces a clone of an existing symbol (opt-in, `[dup].enforce`) |
| DUP003 | clones | (T-0399) `[dup].enforce=true` but frob-core is not installed/built -- clone detection was requested but is unavailable; fails CLOSED (ERROR) instead of silently skipping |
| FUZZ001-003 | fuzz | fuzz obligations under `[fuzz]` (opt-in) |
| PERF001-004 | perf | lexical performance smells (build-a-set-once, etc.) |
| REL001 | release | release-readiness check |
| REL002 | release | (T-1009) `.frob-release.json`'s version disagrees with `pyproject.toml`/`uv.lock` -- always ERROR, never suppressed by land-ownership/`FROB_AGENT`; `frob release sync` is the fix (docs/modules/release.md#rel002-gate-t-1009) |
| SYS001 | sys | a `frob:channel/boundary/secret` directive names a construct id absent from the loaded `.strata` design model (opt-in: a `design/`, or `[strata].design_dir`, directory of `.strata` files must exist); suppressed for the whole run while any design file fails to load (SYS004 reports that instead) |
| SYS002 | sys | a `Boundary` or Secret-clearance `Node` in the design model has no `frob:boundary`/`frob:secret` code binding anywhere |
| SYS003 | sys | (warn) tier-2 code binding (`frob.strata.bind_code`/`check_import_conformance`) finds an undeclared cross-component import between two design-bound files; warn-first on landing, intended to flip to error via `[gates.severity]` once proven |
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
| CPPTHROW001 | arch (ERROR, T-1034) | `frob.arch._cpp_mayraise`'s `cpp-noexcept-throws` category (T-0687, docs/modules/arch.md#cpp-may-throw-analysis-t-0687) channeled into a real gate `Violation` -- a C++ `noexcept` function whose computed may-throw set is non-empty with no encompassing `catch (...)`; ships at `Severity.ERROR`, not the `WARN` every other `arch`-family rule here uses, since an escaping exception from `noexcept` is `std::terminate` at runtime, not deferrable debt. Still an ORDINARY waivable rule (`frob:waive CPPTHROW001 reason="..."`), matching every other `arch`-family rule -- ERROR severity is not the same thing as `_UNWAIVABLE_RULES` membership. |
| LARGE001 | arch (WARN, T-1102) | `frob.arch._check_large_file`'s language-agnostic `large-file` category (any file over `max_file_lines`, `frob.toml`'s `[arch]` table or the calibrated default) channeled into a real gate `Violation` -- previously advisory-only (`frob.arch.analyze_project`'s own text/JSON output), invisible to `frob check`/`frob:waive` entirely. Test files and `fixtures/`-rooted data files stay exempt, same as the underlying advisory check (T-0368/T-0372). WARN first-turn-on, not ERROR: this repo's own source tree carried 43 pre-existing over-threshold files at filing time (measured via `frob.gates._arch.arch_gate` itself against `frob.toml`'s `max_file_lines = 800`, `python` + `rust` files -- `analyze_project` called standalone under-counts since it does not walk `frob-core/`'s own crate the same way the gate's repo-root invocation does), the same debt-corpus posture ARCH101-103 and EXHAUST001/002 shipped WARN-first for. Waivable with a reasoned `frob:waive LARGE001 reason="..."`; a file-level finding has no function/class symbol, so the waiver binds by file/line, not `symref`. `frob arch <single-file>` (single-file mode) reports the identical finding a directory walk containing just that file would (T-1102 also fixed a `frob.arch.analyze_project` bug where single-file mode silently produced zero findings for every category, not just this one). |
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
| EXCL001 | excludehazard | a `.git/info/exclude` entry shadows a git-tracked file or a directory containing tracked files -- see "EXCL001 (T-0465)" below |
| PROTO001 | protocol_summary | (warn) a `frob:requires`/`frob:transition`-tagged symbol's `frob.graph.summary.compute_protocol_summaries` result is `poisoned` (an `UNRESOLVED_CALLEE` somewhere in its transitive call closure) -- see "PROTO001 (T-0813)" below |
| PROTO002 | protocol_summary | (error) a `frob:requires` symbol's required state is never established anywhere reachable (or its summary is poisoned), and no language-excuse discharges it -- see "PROTO002/PROTO003 (T-0746)" below |
| PROTO003 | protocol_summary | (error) a `frob:transition` symbol's precondition state is never established anywhere reachable (or its summary is poisoned), and no language-excuse discharges it -- see "PROTO002/PROTO003 (T-0746)" below |
| WIRE001 | wire | (error) a ticket's own diff adds a function/method/class with no non-test caller, a gate `rule="..."` literal absent from `_KNOWN_GATE_RULES`, or a CLI `dest=` absent from `_config_external.py`'s copy lists -- code that landed, passed every gate, and does nothing; see "WIRE001/WIRE002 (T-1428)" below |
| WIRE002 | wire | (error, unwaivable) a `frob:waive WIRE001` present without a `follow_up="T-####"` attribute naming a real, still-open ticket (or, for a private test-tree helper, `permanent="true"`) -- see "WIRE001/WIRE002 (T-1428)" below |
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
| SYS109 | sys | (error) a symbol-form `via "path::qualname"` entry (T-1627) whose named symbol resolves to no declaration in any of the node's own bound files -- stale via symbol: renamed, moved, deleted, or mistyped. Implemented and unit-tested (`frob.strata._effects.check_stale_via_symbols`); NOT YET wired into `frob sys audit`'s CLI/gate surface -- a disclosed gap, tracked as its own follow-up ticket, not silently absent |
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
(`Ticket.kind_history`, docs/modules/tickets.md#data-models) whenever the
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

- **COV007** (warn): a `frob:doc` edge whose src symbol is PRIVATE. Doc
  anchors normally cover the public API surface (COV001 only ever asks
  for one on a PUBLIC symbol), so one on a private helper is usually
  either a directive that rode along onto the wrong symbol after an
  extraction (COV005's failure mode, just discovered post hoc instead of
  diff-scoped) or documentation that belongs on the public caller instead.
  Warn, not error: a private helper can legitimately warrant its own doc
  anchor (a genuinely complex internal algorithm), and this repo's own
  code has real examples of that (`frob.logging.formatter._FrobFormatter`,
  `frob.gates._pii_structural._FieldSignature`) -- COV007 flags the
  pattern for a human decision, it does not forbid it.

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

Two detection layers, both required to feed the same inbound-reference
count per file:

- **Auto-scan**: file X counts as referenced by file Y when Y's text
  names X (full repo-relative path or bare basename) in a real reference
  SYNTACTIC position -- a markdown link (`](path)`), a quoted string
  literal, a `frob:doc`/`frob:describes`/`frob:used-by`/`frob:tests`
  directive target, a `require`/`include`/`use` target, or a Python
  import (`from X import a, b, c` -- single-line, comma-list, OR
  parenthesized/multi-line -- and plain `import a, b.c`, EVERY imported
  name resolved, not just the module prefix). Deliberately NOT a bare
  substring match over the whole text: a README table cell or a
  ticket-body sentence merely NAMING a file (`` `patterns.yaml` ``) is
  not a reference in any of these shapes, and counting it as one
  silently defeats the gate. For `.py` targets only, a bare imported
  name or a dispatch table's quoted bare module-name string (e.g.
  `"ack_runner"` reaching `ack_runner.py`) also resolves via the
  target's extensionless stem -- restricted to `.py` targets because a
  stem match against a non-Python (data/doc) target reintroduces the
  same false-pass failure mode (an unrelated quoted English word
  colliding with a data file's stem).
- **Test-discovery IMPLICIT reference**: a file `frob.excludes.
  is_test_file` recognizes (`tests/**`, `test_*.py`, `*_test.py`, ...)
  is exempt from REF001/REF002 outright -- it is referenced by the test
  RUNNER via filesystem/naming convention, which no textual scan can see.
- **Declared** (`frob:used-by <consumer>`): a file names its own consumer
  explicitly, for references the auto-scan structurally cannot see (a
  path built at runtime, a glob loaded by a directory base). Every
  declaration is VERIFIED, not trusted: the named consumer must be a
  tracked file AND must itself reach the declaring file (same
  syntactic-position check, in reverse) -- a declaration naming a
  nonexistent or non-reaching consumer is REF003, not a silent pass. This
  is the anti-lie half: a `frob:used-by` cannot manufacture a reference
  that isn't real.

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
(single fragile anchor), **2+** -> pass. All three rules are WARN -- this
never fails `frob check`'s exit code, but every REF001/REF002 must
eventually be waived-with-reason (`frob:waive REF001 reason="..."`) or
fixed, same advisory-but-tracked posture as PERF/FUZZ.

`[[refs.entrypoint]]` in `frob.toml` exempts genuinely externally-facing
files (README.md, LICENSE, pyproject.toml, the CLI `__main__.py`, ...)
from REF001/REF002 -- each entry is `{ path = "...", reason = "..." }`; a
malformed entry (missing `path`/`reason`) is skipped and logged, never
treated as a blanket mute.

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
with no git precondition (`docs/modules/tickets.md`'s "ambiguous: no git
repo, detached HEAD, git unavailable" ticket-id-minting fallback is the
same call already made for a sibling concern) -- a git-less target is a
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

A file-scoped markdown `frob:waive` marker (`<!-- frob:waive INV004
reason="..." -->` anywhere in the file, applied via
`_file_has_reasoned_doc_waiver` from `inv004_gate`, the same helper
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
no directive at all. `frob.gates._inv006_split_assist` (the T-1134
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
<!-- frob:describes src/frob/gates/_fix_engine_shared.py::FixApplied -->

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

  A companion guard closes the same incident's OTHER half at the land
  layer itself, independent of which Tier-A handler is at fault: `frob
  ticket land` refuses BEFORE any git mutation (before the wip-commit
  that would otherwise fold a dirty worktree's edits into the merge
  unattributed) when the worktree's uncommitted state deletes a
  `frob:waive` directive whose file is neither in the landing ticket's
  scope nor named in its Done report
  (`frob.tickets._land._check_uncommitted_waive_deletions`,
  `LandError.OutOfScopeWaiveDeletion`) -- see
  docs/modules/tickets.md#frob-ticket-land.

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
SUPPRESS001/REG010/REL002 first, since they are pure source-text/artifact
rewrites with no ledger interaction; TICK002 next, since it touches the
ticket ledger; WAIVE004 last, since it re-invokes the whole gates suite
itself and should see every other handler's rewrites already applied).
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
wip-commit (docs/modules/tickets.md#frob-ticket-land) ever runs -- a
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
  loss. See docs/modules/tickets.md#frob-ticket-land for how this sits
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

### SYS100/SYS104 `.strata` declaration auto-fix (T-1531)

<!-- frob:describes src/frob/gates/_fix_engine_sync.py::fix_sys104_interface_union -->
<!-- frob:describes src/frob/gates/_fix_engine_sync.py::fix_sys100_may_via_union -->
<!-- frob:describes src/frob/strata/_sync_may.py::sync_may_report -->
<!-- frob:describes src/frob/strata/_sync_may.py::apply_sync_may -->

Every real land refusal on 2026-08-04 traced back to one of a small set
of `.strata` declaration classes, each hand-fixed with the same
deterministic recipe repeatedly -- exactly the shape `TIER_A_HANDLERS`
already exists to close mechanically. T-1531 wires the two
highest-frequency classes in:

- **`fix_sys104_interface_union`**: SYS104 (a node's declared
  `interface=[...]` surface drifted from its bound code's real public
  surface) already has a full writer, `frob.strata._sync_interface`
  (T-1150) -- this handler is a thin `TIER_A_HANDLERS["SYS104"]` wrapper
  around `sync_interface_report`/`apply_sync_interface`, the exact
  functions `frob sys sync-interface` itself calls. Before this ticket,
  that writer only ran as its own special-case pre-land step
  (`_land_cmd.py::_sync_interface_pre_land_step`) -- registering it in
  the generic Tier-A table means the POST-land unscoped sweep
  (`docs/modules/tickets.md#post-land-unscoped-error-sweep-t-1456`) can
  now auto-repair a SYS104 drift too, not just a pre-land one.
- **`fix_sys100_may_via_union`**: SYS100's CORE case (net/fs-write/exec,
  `_effects.py::check_capability_conformance`'s per-file `via` join,
  T-1440) had no writer at all -- `frob.strata._sync_may` (this ticket)
  is the new one: for every observed effect with no `may "<kind>" via
  [...]` grant covering its file, it widens the existing `via` list
  (sorted union) or inserts a brand-new via-scoped grant line, mirroring
  `_sync_interface.py`'s own "measure via the real check, edit `.strata`
  text in place, never re-serialize" strategy end to end (same node-
  header/body-span matching, same insert-after-anchor convention for a
  node with no prior declaration).

  **Disclosed scope cut**: SYS100's EXTENDED case
  (eval/process-control/ffi/install-hook/..., `_selfconform.py::
  _extended_kind_violations`) fires per-NODE with no per-file evidence at
  all -- there is no single file this writer could add to a `via` list
  without guessing which of a node's many bound files actually exercises
  the capability, so it is deliberately NOT handled by
  `fix_sys100_may_via_union` (T-1137's own never-guess-at-a-fix posture).
  A follow-up ticket tracks it separately.

Both handlers follow the same `(root: Path, snapshot: GraphSnapshot) ->
list[FixApplied]` shape as every other pure-`.strata`-rewrite handler in
this module (`snapshot` unused -- each reads the design tree itself, same
as `fix_reg010_registry_sync`/`fix_rel002_release_sync`) and are no-ops
(empty list, nothing written) when `root` has no `design/` directory at
all, or when their respective `sync_*_report` call errors (a design file
that fails to parse, an ambiguous code binding) -- logged and skipped,
never raised, matching every other handler's "an auto-fix convenience is
never a hard precondition" posture. Being registered in
`TIER_A_HANDLERS` means both are automatically wired into EVERY existing
Tier-A call site with zero further plumbing -- `_land_cmd.py`'s pre-land
absorption step, its pre-commit unscoped sweep
(`_pre_commit_unscoped_error_sweep`), AND its post-land unscoped sweep
(`_post_land_unscoped_error_sweep`) all call `apply_tier_a_fixes`
already; this ticket needed no changes to `src/frob/app/ticket_runner/
_land_cmd.py` at all.

**Remaining SYS100/SYS104/land-refusal recipes (disclosed deferral,
T-1531's own body names six; two shipped here)**: COV002 changed-symbol-
without-edge auto-insertion, ClaimDivergence done-report re-run,
TICK006 phantom-draft-citation refile/renumber, and E501-from-merge
targeted `ruff format` are real, filed as separate follow-up tickets
rather than guessed at inside this ticket's own budget.

## Data models

<!-- frob:describes src/frob/gates/_models.py::Severity -->
<!-- frob:describes src/frob/gates/_models.py::WaiverRef -->
<!-- frob:describes src/frob/gates/_models.py::Violation -->
<!-- frob:describes src/frob/gates/_models.py::GateStats -->
<!-- frob:describes src/frob/gates/_models.py::GateReport -->
<!-- frob:describes src/frob/gates/_models.py::GateConfig -->
<!-- frob:describes src/frob/gates/_models.py::PreworkSweep -->
<!-- frob:describes src/frob/gates/_models.py::SystemSpec -->
<!-- frob:describes src/frob/gates/_models.py::TestPolicy -->
<!-- frob:describes src/frob/gates/_models.py::CoverageData -->

- `Severity` -- a violation's exit-code weight: `error` fails
  `frob check`, `warn` does not.
- `WaiverRef` -- the `frob:waive` edge that suppressed a violation, kept
  on the `Violation` so waivers stay visible debt rather than silence.
- `Violation` -- one gate finding: rule id, severity, site, and a message
  that always embeds its own remedy command.
- `GateStats` -- per-gate counters (violation counts, timing, skipped
  gates) attached to every `GateReport`.
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
  `root/pyproject.toml`, falling back to ruff's own default (88). Known
  limitation: this is ONE project-wide limit sourced from ruff's config; a
  genuinely per-language limit (`rustfmt.toml`'s `max_width`, a
  `.prettierrc`'s `printWidth`, clang-format's `ColumnLimit`) is not wired
  up -- every supported language wraps against this single limit today.
- `canonicalize_text(text, *, path, limit) -> str` -- rewrites every
  `frob:` directive run in `text` to canonical form; non-directive
  comments and all code are untouched byte-for-byte. T-0985: a run whose
  logical text ends in a `# noqa`/`# noqa: CODE` pragma is a deliberate
  escape hatch (content is one unbreakable token, e.g. a long dotted
  pytest node id with no space to wrap at) and is left byte-identical
  rather than force-wrapped -- previously the pragma comment was treated
  as ordinary directive text and force-wrapped anyway, defeating its
  purpose.
- `format_paths(root, *, check_only, limit=None) -> FmtReport` -- walks
  `root` (via `frob.excludes.iter_files`, so the usual excluded/pruned dirs
  are skipped) and canonicalizes every supported file; `check_only=True`
  reports without writing (`frob fmt --check`, CI-friendly, exits 1 if
  anything is non-canonical).

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
`frob:` directive comment line exceeds the project's configured line
length (`frob.gates._fmt_directives.read_line_length`), with a
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
