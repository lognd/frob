# strata -- frob v1 inventory (for the Rust v2 redesign)

Source of truth: <frob-v1>/ (read-only). All figures below were measured
or quoted from the v1 tree on 2026-10-01. ASCII only. Ticket ids (T-nnnn) are v1 history.

## 0. Coverage statement (read this first)

Universe enumerated up front (Phase 0), then drained. Denominator and depth:

| Node group | Count | Depth reached |
|---|---|---|
| docs/strata/*.md | 17 files, 8738 lines | charter, surface (all headings, key sections in full), kernel, graph, vmodel, entity_architecture, evidence, policy, selfconform, waive, roadmap, threat (all sections) read in full or near-full; boundary read to the grammar/elaboration section; host, krb, reliability, dataset-construct, provenance-trust-identity read by heading + surface vocabulary + rule definitions, NOT line by line (reliability is 1780 lines of 16 near-identical families) |
| src/frob/strata/*.py | 89 modules, 39136 lines | every module docstring read; ~12 modules read in depth (_code_binding, _effects head+index, _selfconform_ids, _waive via doc, _design_load, _plan, _export, _shrink, _mutation_audit, _threat_models, _cve_fingerprint, _obligation_proof); the other ~75 known by docstring + doc only |
| strata-core/ (Rust) | 10117 lines, 14 src files | Cargo.toml, lib.rs function index, keyword inventory of every grammar_*.rs, docs for graph/vmodel; parse/mod.rs (2421 lines) not read beyond tests index |
| design/frob.strata | 2940 lines (835 non-comment) | structure, counts, store/resource/cache/boundary/assert/assume blocks, header comments |
| design/litmus/ | 9 .strata + fixtures | payments, sys_liveness read; others by header + roadmap description |
| src/frob/registry/ + docs/design/registry/ | 3 py modules, 10 yaml + 3 md | all three md read; yaml heads + schema; py docstrings |
| docs/design/*corpus*.md etc. | 9 corpus docs + cwe-1000-registry + design-pattern-catalog (7667+ lines) | headers, method notes, DENOMINATOR MANIFEST format; row content NOT read |
| docs/guides/extending/*.md (10) | 917 lines | all read |
| invariants/ | 52 INV files | all statements read |
| editors/ | vscode-strata (tmLanguage), jetbrains README | existence + drift-lock test description only |
| consumer repos | 10 repos with design/*.strata | construct counts measured by grep, not read |

Pending: 0 nodes. Blocked: 0 nodes. Honest caveat: depth is uneven as shown; claims about
unread rows (corpus content, reliability family internals, host/krb algorithms) rest on the
docs' own summaries. Where I extrapolate, the text says "assessment".

## 1. What strata is, in one page

strata = a deny-by-default system-design DSL ("design/**/*.strata", CLI namespace `frob sys`)
whose claims are about flows between nodes. Pipeline: parse (Rust, strata-core) -> pydantic AST
-> elaborate (vocabularies desugar to kernel facts) -> fact base (Datalog-ish closure + interval
arithmetic) -> claims/scenarios -> verdicts -> SYS/THREAT/etc gate violations. Tier 2 joins the
model against real code (file globs, imports, effect needles, directives). Tier 3 = evidence.

Six laws (charter): (1) one kernel, many vocabularies; (2) deny by default at every layer;
(3) three-way closure: every claim PROVED / EVIDENCED / ASSUMED (assume = named, owned,
expiring; overdue = REFUTED since T-4675); (4) counterexamples always, quantifiers recorded;
(5) two-way binding (design constrains code, code attests design); (6) model is load-bearing
(exporters to k8s netpol / seccomp / IAM).

Three collapses: age (cache TTL = credential lifetime = replica lag = assumption expiry = one
bound `age(x) <= t`); endorsement (validation / review / attestation = one boundary form);
scenario (zone failure = load surge = compromise = rewrite model + recheck claims).

Scale: 39k lines Python + 10k Rust + 8.7k lines docs; 52 invariants; 667 gate rules repo-wide.

## 2. The .strata surface grammar

File shapes: a ROOT file (`module NAME`) or a FRAGMENT (`part of NAME`, only `extend node`
statements, T-2502). Comments `//`. Strings are `"..."` with no escapes. No security defaults:
omitted security-relevant facts are errors. Units are types (`5 req/s`, `250 ms`, `4 KiB`,
`15 %/month`). Lexer keeps IDENT = [A-Za-z_][A-Za-z0-9_]*; anything with `. / * :` must be a
STRING (design choice T-0132: reuse Str token rather than add token classes per vocabulary).

### 2.1 Top-level statements (dispatched in grammar_policy.rs::parse_program)

| Keyword | Meaning | Example |
|---|---|---|
| module | names the file's module (one per root file) | `module frob` |
| part of | marks a fragment file; mutually exclusive with module | `part of frob` |
| extend node | fragment-only: widen an existing root node's `may ... via` list | `extend node testsuite { may "exec" via "tests/x.py"; }` |
| import / export | module-system grammar, PARSE-ONLY (T-5125): `import a.b as c;` `export { node X; channel Y; label Z; }` | `import base.labels as lb;` |
| layer N | module hierarchy rank (lower = higher); parse-only | `layer 0;` |
| node | place holding state/computation: trust level + body | `node cli : trusted { ... }` |
| store | node with durability props (engine, rpo, append_only, immutable...) | `store tickets_ledger : trusted { engine git_tracked; append_only; }` |
| cache X of Y | derived view: ttl/staleness, invalidate_on flow, hit ratio | `cache graph_cache of graphlang { ttl 1 s; invalidate_on f_parse; }` |
| queue | delivery at_least_once/at_most_once + ordering | `queue webhookq : trusted { delivery at_least_once; }` |
| cdn / balancer | infra nodes; `tls_terminates_at_provider`, `sticky`, `provider` | `cdn edge : trusted { tls_terminates_at_provider; }` |
| flow | directed movement src->dst: label, rate, age, size, fanout, growth, transport, attrs, condition | `flow f_parse : cli -> graphlang { label Internal; attr local; }` |
| boundary | the only legal label/trust change: endorse/declassify on one flow, with predicate, optional six-phase block | `boundary b endorse f_x : foreign -> trusted when "checksum_verified"` |
| operation | frame-conditioned writes + atomicity | `operation Transfer on Db { modifies { Bal } on Ok; modifies {} on Err; atomic via tx }` |
| secret | credential as cache-of-authority: issued_by, audience, lifetime, revoke | `secret k { issued_by vault; lifetime 24 h; revoke 5 min; }` |
| resource | shared resource arbitration: `arbitrated_by NODE` or `lock "NAME"` | `resource tickets_ledger { lock "tickets.lock"; }` |
| policy | L4 syntactic rule over a scope (see 2.4) | `policy NoDyn on trust >= trusted { forbid call eval, exec; enables extraction_soundness }` |
| scenario | counterfactual rewrite + nested claims | `scenario z { remove replica; assert bound age refund <= 60 s }` |
| assert / assume | claim: must prove / owned expiring TCB entry | `assume "weakness:CWE-78:vet" noflow registry -> vet owner logan review "2026-10-15"` |
| refine X into {...} | decompose an `abstract` node; one `binds X = inner` | `refine gw into { node a : trusted; flow ...; binds gw = a }` |
| entity | behaviour half: free-text `obligation`s + `may` ceiling (no implementation) | `entity storage { may "net.out:s3"; obligation "persist before ack"; }` |
| architecture A of E | implementation half: `binds MODULE` | `architecture fast of storage { binds storage_fast; }` |
| configuration | selects architecture per entity | `configuration c { entity storage; architecture fast; }` |
| vmodel_node | V-model spec-graph node (artifact/test/decision) | `vmodel_node req_1 kind "artifact" level "requirements" code_ref "docs/x.md:REQ1";` |
| vmodel_edge | V-model edge (satisfies/verifies/refines/allocates/decides/supersedes/blocked_by) | `vmodel_edge kind "satisfies" src d1 dst req_1;` |

### 2.2 node / store body clauses (grammar_node.rs, grammar_infra.rs)

| Clause | Meaning | Example |
|---|---|---|
| clearance LABEL | max data label allowed to rest here (default Secret) | `clearance Pii;` |
| code STRING+ | tier-2 binding: glob list (at least one) | `code "src/frob/app/**" "src/frob/__main__.py";` |
| may STRING [via S,S..] [of S,..] [exclusive] | capability atom, optionally scoped per file/symbol (`via "path::qualname"`) and per argument (`of "FROB_*"`); `exclusive` only with one symbol-form via | `may "net.connect" via "src/x/client.py::Client.send";` |
| carries STRING+ | PII tags `<category>.<field>` -> `pii=` attrs | `carries "identifier.email";` |
| managed | external pure-config infra; exempt from tier-2 conformance | `managed;` |
| abstract | placeholder awaiting `refine` (unrefined frontier = plan frontier) | `node gw : trusted abstract;` |
| attr KEY[=VAL] / attr KEY=[a,b,c] | opaque attr; bracket list is parse-time sugar for N attrs (`interface=[...]`) | `attr flag=kill_switch_id;` |
| capacity Q replicas A..B | service rate and replica range | `capacity 100 req/s replicas 1..3;` |
| skew zipf N | hot-key skew for utilisation | `skew zipf 1.5;` |
| errors_total / panics_contained_by X | err-handling claims (std.err) | `panics_contained_by supervisor;` |
| observe { log CLASS,..; to NODE } | observability target (synthesises a `X__obs` flow) | `observe { log error; to audit }` |
| on deploy { canary{..}; endorsed_by ..; rollback within Q } | deploy contract | `on deploy { rollback within 5 min; }` |
| waive "RULE[:SUB]" reason "..." [ticket "..."] | in-design waiver for an audit finding; reason mandatory in grammar | `waive "SYS100:exec" reason "x" ticket "T-1";` |
| users N, rate Q (+growth) | demand declarations feeding aggregate_demand/capacity | `users 500000;` |
| access "RES" mode MODE | shared-resource access (read/append/alpha/write/exclusive) | `access "ledger_db" mode write;` |
| runs_as / unit / owns / listens / group / sudoers / pipe / acl / platform / service / gmsa / bin_path | std.host OS-layer facts (Linux + Windows variants) | `runs_as "api-svc"; owns "/etc/api" "0644"; listens 8080;` |
| realm / kdc / spn / delegation / trusts | std.krb Kerberos facts | `delegation constrained target "HTTP/b@R";` |
| residence ID | host/zone/region atom for scenario rewrites | `residence eu1;` |

Marker attrs consumed by REL families are bare idents inside node/flow bodies (`timeout`,
`async`, `local`, `health`, `retry`, `backoff_jitter`, `idempotency_key`, `external`, `critical`,
`circuit_breaker`, `fallback`, `bounded_intake`, `observability`, `correlation`, `slo`,
`error_budget`, `owner`, `reconciliation`, `transaction`, `saga`, `interactive`, `bounded_cost`,
`event`, `schema_version`, `deep_chain_ok`, `shared_state_ok`, `clock_dependent`,
`ordering_strategy`, `kernel_interface`, `interface_classified`, `deployed_process`,
`cgroup_bounds`, `compiled_artifact`, `abi_compat_window`, `boot_chain_stage`, `boot_attested`,
`purpose=PROFILE`, `retention=Nd`, `derived_from:TAG=HELPER`, `trust_identity:TAG`,
`parent_store=NODE`, `append_only`). These are string attrs, not grammar -- the "grammar-data
ceiling" the reliability docs apologise for repeatedly (e.g. `timeout` is presence-only: no
magnitude can round-trip through `attr KEY=IDENT`).

### 2.3 flow / boundary / claim sub-grammar

| Construct | Clauses |
|---|---|
| flow | label, rate Q, age Q, size Q, fanout N, growth N %, transport ATOM.., attr .., utility (non-transitive hub edge), authenticates_via tgt/st (krb), `on Ok/Err` and `in PHASE` conditions |
| boundary | `endorse FLOW : from -> to when "pred"` / `declassify`; optional phase block: admit{rate_limit,max_size} parse{time,frame{}} judge{} effect{frame{..}} record{audit to X} refuse{respond X; frame{..}} |
| claim_body | `noflow A -> B` ; `reach A -> B` ; `bound METRIC TARGET <= QUANTITY` with METRIC in age/rate/latency/size/utilization. Claim id may be a STRING (e.g. `"weakness:CWE-78:vet"`). `independent(p,n)` and `readers(x)==S` exist in the kernel but have NO surface grammar (auto-generated only, e.g. by secret elaboration and breach scenarios) |
| claim trailer | `require proof >= L1..L5`; assume needs `owner IDENT review "YYYY-MM-DD"` |
| scenario rewrite | `remove NODE` ; `scale FLOW by N` ; `trust NODE := LEVEL` (kernel also has AddFlow) |

### 2.4 policy forms (grammar_policy.rs) -- the five universal L4 forms

| Form | Syntax | Meaning |
|---|---|---|
| Prohibition | `forbid call a, b` / `forbid import x` | no occurrence in scope |
| Confinement | `confine use X to PATH` | occurrences only inside home |
| Obligation-at-site | `at call F require arg A` | every F call carries A |
| Chokepoint | `mediate cap via FILE::Sym require proof >= L3` | all uses mediated by one proved function |
| Structural | `every public function in C returns Result` | property over graph symbols |
Scope: `on component X` | `on trust >= L` | `on label >= L`; metadata `enables ATOM`, `rationale`.
Packs: std.policy.analyzable (mandatory for any trusted node; auto-injected with a WARNING),
errors-total, observe, crypto, pii. Only Tier-1 (compile + weakening diff, INV051) is
implemented; Tier-2 per-language tree-sitter execution of policy rules is NOT implemented
(roadmap says phase 4; policy.md "What does not compile yet").

### 2.5 Keyword census and the editor drift-lock

Distinct keyword strings matched via at_keyword/expect_keyword, by grammar file: node 61,
infra 58, flow 35, policy 28, core 10, vmodel 7, module 1; 149 distinct across the crate. A kernel survey (scratchpad/STRATA-KEYWORDS.md, quoted
in kernel.md) counted 139 surface keywords, ~79 of which do not desugar into the six
primitives (see 3.1). Keyword list is hand-duplicated in
editors/vscode-strata/syntaxes/strata.tmLanguage.json; tests/unit/test_strata_tmlanguage.py is
the ONLY bidirectional drift-lock; no gate parses .strata keywords. Add-a-keyword recipe is 5
manual steps (parser, tmLanguage, `make core`, rust test + fixture, surface.md). JetBrains
has a README only (no grammar).

### 2.6 Elaboration desugars (what the surface really is)

Most constructs elaborate to node/flow ATTR STRINGS, not kernel fields: `code=<glob>`,
`pii=<tag>`, `skew=`, `fanout=`, `growth=`, `rpo=`, `managed`, `access=RES:MODE`, `flag=ID`,
`panics=ID`, `interface=SYM`, plus `Node.may` / `Node.may_grants` as real fields. The elaborator
(_elaborate.py 1508 lines + _infra.py 818) is the real "vocabulary" machinery; user-defined
vocabularies were explicitly deferred. Multi-file load (T-1196): parse all files, merge the
parsed Modules (order-independent concatenation), resolve fragments, then elaborate ONCE.
Refinement v0: target validity, no new external surface, no trust laundering are checked;
budget distribution (faithfulness check 3) is deferred.

## 3. The kernel

### 3.1 Primitives and the eight recorded extensions

| Primitive | Fields (v1 pydantic, _models.py, all frozen) |
|---|---|
| Node | id, trust, clearance (default Secret), may (atoms), may_grants (atom+via+of+exclusive), attrs (opaque strings), capacity (service rate, replicas), users, rate (+growth), residence, crash/breach/deploy contracts |
| Flow | id, src, dst, label (default Public), rate, age, size, transport atoms, attrs, condition (on Ok/Err/phase), timeout |
| Boundary | id, flow_id, direction (endorse/declassify), from_level, to_level, predicate (opaque string), obligations |
| Bound | metric in {age, rate, latency, size, utilization} + target + limit Quantity |
| Claim | body (NoFlow, Reach, BoundClaim, Independent, SetEquality) + rung + assumed{owner, review} |
| Scenario | rewrites (RemoveNode, ScaleRate, SetTrust, AddFlow) + nested claims |
KernelModel = nodes, flows, boundaries, claims, scenarios, trust lattice, label lattice.
Lattices: TRUST foreign < authenticated < trusted; LABELS Public < Internal < Pii < Secret;
both user-extensible; never merged. StrataError is one closed error enum (about 19 variants by grep).

Kernel extensions (kernel.md "beyond the six primitives"): 8 domains do NOT lower to the six
primitives and are evaluated by bespoke Python: (1) code binding, (2) capability via-lists,
(3) waivers, (4) entity/architecture (SYS300-303 at parse/load), (5) vmodel graph (VMOD gate),
(6) policy (AST rules, no Datalog), (7) host/ACL (HOST gates), (8) Kerberos graph. The "one
kernel" law 1 is therefore aspirational: roughly 79 of 139 surface keywords bypass the prover.

### 3.2 What strata-core (Rust) actually computes

PyO3 functions in lib.rs (1449 lines, 7 #[pyfunction]s including parse_source):

| Function | Computes |
|---|---|
| reachable(edges, src, ...) | deterministic BFS closure over lexicographically sorted out-edges; per-edge barrier flag (boundary = endorsement stops taint unless through_barriers); per-edge `transitive` flag (T-0282): non-transitive edge is a terminal hop (used for krb non-transitive trusts and `utility` flows); returns witness paths |
| worst_age(edges, target) | longest-path staleness; SCC condensation (Tarjan) + longest-path DP on the DAG; a positive-weight cycle that can reach target returns +inf with the cycle as witness (INV-028); requires non-negative weights (Python fails closed with NegativeQuantity) |
| demand(rates, node) | plain declared inbound-rate sum (legacy; superseded) |
| propagated_demand(edges, target) | fanout-weighted demand SUMmed over converging paths (age is max, demand is sum); rate-fed cycle -> +inf with witness |
| vmodel_check(nodes, edges) | builds a typed Graph against v_model_schema(); returns (construction_errors, [(rule, node_id)]) for the 4 closure rules |
| milestone_closure_check(nodes, edges, known_gaps) | rule 3 variant: untested artifact is exempt iff named in known_gaps |
| parse_source(text) | full parser -> JSON AST string (Python deserialises into pydantic) |
Runs deep recursion on a big-stack thread (run_on_big_stack). No pure-Python fallback
(charter D3). Historical bug kept as permanent regression: memoised-DFS worst_age undercounted
(3.0 vs correct 4.0) because cached values were context-dependent.

"Staleness" in the kernel is exactly worst_age; "demand" is propagated_demand; "closure" is
reachable. Everything else (claim evaluation, capacity/skew/zipf/growth arithmetic, scenarios,
lints) is Python on top. Python-side capacity: utilisation = demand / (service_rate *
replicas_max); skew zipf alpha -> hottest-shard share; growth compounding -> months to
saturation vs a 24-month deny-by-default horizon (`frob sys capacity --at DATE`).

### 3.3 Claim decision procedures

| Form | Procedure | Refutation witness |
|---|---|---|
| noflow A->B | reachable closure; boundary flows stop taint (endorse) | node path |
| reach A->B | same closure with through_barriers=True | none (missing) |
| bound age | worst_age over flow ages; cache ttl, cdn staleness, store rpo, credential lifetime all collapse to flow `age` | longest path / cycle |
| bound rate/utilisation | propagated_demand vs capacity, skew, growth | hottest node + number |
| bound latency/size | path sum / max | path |
| independent(p,n) | recovery path shares no node with the compromised node's reach set | shared node |
| readers(x)==S | exact-set closure equality (secrets) | extra/missing reader |
Verdicts PROVED/EVIDENCED/ASSUMED/REFUTED each with a Quantifier (forall/exists). `enables`
cascade: waiving a policy that declares `enables extraction_soundness` downgrades every PROVED
noflow/reach/independent/readers verdict to ASSUMED (bound claims exempt). Reports order
REFUTED, ASSUMED, EVIDENCED, PROVED; an Assumption ledger section lists all assumes.
Fact-base diagnostics (non-fatal): at-least-once into a non-idempotent consumer; payload label
above destination clearance; sticky-balancer contradiction; mutable data behind `staleness
unlimited`.

### 3.4 Evidence model (evidence.md)

Ladder (every claim declares or inherits a minimum rung; weaker evidence => gate failure unless
an assume): L5 by-construction (kernel proof / type embedding), L4 universal policy (syntactic
forall over a semantic scope), L3 leaf proof (SMT/verifier on a small mediator), L2 property
test / generated fault injection (forall over enumerated Err variants), L1 example test
(exists, tripwire only). The semantic-to-syntactic reduction: chokepoint policy form turns an
undecidable forall into confinement (L4) + a proved mediator (L3/L5). Tool attestations
(ty exhaustiveness, tsc no-floating-promises, rustc must_use) are digest-stamped evidence.
Implementation status: rungs exist as Rung enum and THREAT003 compares claim rung to catalog
rung (INV-029); L2 fault-injection test GENERATION (T-0075) and L3 SMT were never built; z3 is
mentioned as a fallback only.

### 3.5 Boundary, operations, crash (boundary.md)

Six-phase boundary contract: admit (size/rate/authn before parse), parse (pure, total, linear;
frame must be empty), judge (the endorse/declassify itself), effect (first phase with a frame),
record (audit emit), refuse (failure frame = audit-append only). Frames are the kernel's only
conditional-flow extension: `modifies X on Ok / modifies {} on Err`; atomicity discharge ladder:
stage-then-commit, immutable swap, tx chokepoint, WAL; cross-store atomic needs saga +
compensate. `on crash { restart within t; ... }` desugars to a crash scenario; INV-027 no-hang
check: every synchronous flow into a crashable node declares a timeout >= restart+retry bound.
v0 compiles only structural diagnostics (phase uniqueness, empty parse frame, panics-supervisor
exists, observe targets exist); fault-injection generation never landed.

### 3.6 Entity / architecture / configuration (entity_architecture.md, T-3006)

VHDL-inspired split: `entity` = obligations + `may` ceiling (no build); `architecture A of E {
binds MODULE; }` = one realisation (today's whole node/flow surface); `configuration` selects
which architecture satisfies which entity. SYS300 (entity unresolved, cross-file at load time),
SYS301 (binds != own module), SYS302 (architecture's union of node `may` grants must be subset
of entity ceiling -- the shrink-only ratchet at a new layer; no code ever widens the ceiling),
SYS303 (configuration pairing mismatch). Obligations are free text with NO verifier edge
(deferred); no existing .strata file declares an entity (self-model deliberately not migrated);
only a test fixture pair (tests/unit/strata/entity_arch/) exercises it. Milestone-scoped partial
closure (MSCLOSE001) was built on top as the incremental-release mechanism.

### 3.7 The V-model spec graph (vmodel.md, graph.md)

Generic typed-graph kernel strata-core::graph (model.rs 751, query.rs 349): GraphSchema declares
node kinds, levels, edge kinds with allowed src/dst kinds and a LevelRelation (Any/Same/
Paired(map)); required attrs per kind; Graph::add_node/add_edge refuse malformed input at
CONSTRUCTION (UnknownNodeKind, DuplicateNodeId, UnknownLevel, UnknownEdgeKind, DanglingEndpoint,
WrongEndpointKind, LevelConstraintViolation, MissingNodeAttr, MissingEdgeAttr). Queries:
forward_closure/backward_closure with KindFilter, reachable, find_cycle (witness path).
V-model instance (vmodel/mod.rs 441, closure.rs 900): node kinds artifact (needs `code_ref`
path[:symbol]), test (needs `runnable` path::Class.method), decision; 10 levels paired
requirements<->customer-test, requirement-specification<->customer-test-plan,
system-specification<->system-integration-test-plan, system-design<->subsystem-integration-
test-plan, component-design<->component-unit-test; edge kinds satisfies, verifies (test ->
artifact, level-paired, enforced at construction), refines, allocates, decides, supersedes
(needs `reason`), blocked_by. Five structural closure rules: orphan_requirement (backward
closure must REACH innermost level), unjustified_design (forward closure must reach
requirements), untested_artifact (>=1 incoming verifies), orphan_test (>=1 outgoing verifies),
trace_cycle. Sixth, opt-in: milestone closure with declared known_gaps.
Gates: VMOD001 (WARN, opt-in on design dir having vmodel_node), MSCLOSE001 (WARN). Hard design
principle: "structural closure, never quality judgement". Deferred by owner: waterfall gate
(block implementation on spec closure) and migrating the ticket ledger onto this graph.

### 3.8 Host, Kerberos, and other std vocabularies (read by heading + rules)

| Vocabulary | What it models | Rules (inputs) |
|---|---|---|
| std.host | runs_as, unit, owns PATH MODE, listens PORT, group, sudoers; Windows variant (acl, gmsa, service, bin_path, platform). Elaborates to attrs + a platform-tagged HostManifest | HOST001 lateral movement per service-user pair (shared writable path / port / group), HOST002 vertical (setuid, sudoers, root unit writable path), multi-ACE deny-overrides join (WRITE_DAC corner) |
| deploy generator | HostManifest -> systemd unit / useradd script (frob deploy generate) | DEPLOY001 committed-script byte drift, DEPLOY002/003 conformance (not read in depth) |
| std.krb | realm, kdc, spn, delegation none/constrained/rbcd/unconstrained, trusts (direction, transitive), flow authenticates_via tgt/st; synthesises a Flow so the same closure answers cross-realm reach | KRB001 unconstrained delegation, KRB002 kerberoasting per SPN, KRB003 constrained-delegation blast radius, KRB004 cross-realm containment |
| resources (SYS2xx) | access "RES" mode, resource{lock|arbitrated_by} | SYS200 dup port, SYS201 overlapping path claim, SYS202 shared pipe, SYS203 shared store write (mode-blind), SYS204 mode-aware unarbitrated conflict, SYS205 code mode conformance |
| std.secrets | credential = cache of authority; auto-emits issue/revoke/read flow triad + readers() SetEquality claim + age bound | fail-closed MissingRevocation |
| std.deploy | canary schedule, endorsement chain, rollback latency | evaluate_deploy_contracts |
| std.dataset (T-3964) | no keyword: a node with `attr parent_store=X` is a fine-grained dataset; `append_only` | structural gate (not read) |
| provenance / trust-as-identity (T-3961) | `derived_from:TAG=HELPER`, `trust_identity:TAG` attrs | PII005, SYS116, SYS117 |
All of these are bespoke Python joins over attr strings. None lowers into the prover except
krb's synthesised flow. Assessment: host/krb/deploy were driven by a deploy epic (T-0254) and
a fleet-hardening motive, none appear in any consumer repo (see 10.2).

Reliability families REL2xx-REL39y: one template (marker attr + bound-code token proof + waive + stale-waiver); see 5.4.

## 4. BINDING: how a .strata construct binds to code today, where it is weak, and a v2 proposal

### 4.1 Every binding mechanism in v1 (exhaustive list)

| # | Mechanism | Model side | Code side | Resolution / granularity | Consumer |
|---|---|---|---|---|---|
| B1 | `code "glob"` on node/store | list of fnmatch globs stored as `code=<glob>` attrs | none (pure model-side) | per FILE, Python bind_code walks `*.py`; `_capability_binding` re-binds other scannable languages with the same globs; first partition: exactly one owner else AmbiguousCodeBinding, none => FOREIGN | SYS003, SYS100-103, SYS106, SYS107, SYS113, REL*, THREAT004 |
| B2 | `may "atom" [via ..] [of ..]` | capability atom + optional per-file / per-symbol / per-argument scope | none | kind = atom prefix up to first `.` or `:`; join is per file (T-1440) or per observation SITE when any symbol-form via exists (T-1627); `of` matches the first quoted string literal on the line | SYS100, SYS101, SYS105, SYS107, SYS109, SYS111, SYS112 |
| B3 | `frob:channel FLOW`, `frob:boundary BOUNDARY`, `frob:secret NODE` comment directives | design id must exist (merged across all files) | comment above/in the symbol; becomes an EdgeKind CHANNEL/BOUNDARY/SECRET edge in the frob graph from the enclosing SYMBOL to the design id | symbol-granular on the code side; id-granular on the model side | SYS001 (dangling -> error), SYS002 (boundary or Secret-clearance node with no directive -> warn), `frob sys plan` "unbound" frontier |
| B4 | frob:doc / frob:ticket / frob:waive / frob:todo comments placed above a `node`/`store`/`flow` in the .strata file | .strata is the 6th frob.lang grammar; `_walk_strata` turns each top-level construct into a RawSymbol (node/store/queue/cache/cdn/balancer/resource/module -> CLASS, boundary/flow -> FUNCTION, assert/assume -> CONST, refine/policy -> TYPE, operation/scenario -> METHOD) so ordinary frob graph directives attach to design constructs | the directive is in the .strata comment | construct-granular, span found by a regex line scan paired with the parser's declared-id list (walk fails closed if the regex cannot locate a declared id) | DOC/TICKET/WAIVE gates, doc-drift acks (design/frob.strata carries 188 frob:doc, 90 frob:ticket, 16 frob:waive comments) |
| B5 | `attr interface=[Sym,...]` | hand-declared intended public surface | none | symbol NAME list (Python public surface); opt-in per node | SYS108 (duplicate), SYS110 (real public symbol not declared -> ERROR; 14 nodes exempt via hard-coded SYS110_UNAUDITED_NODES) |
| B6 | flows as import permission | directed `flow A -> B` | Python `import`/`from` statements parsed with stdlib `ast`, resolved to repo files by frob.lang.resolve_local_import | per IMPORT line; direction exact (A->B does not permit B->A); FOREIGN-> bound imports and non-Python imports unchecked | SYS003 (ERROR since T-2407 after calibration 4834 -> 133 -> 0) |
| B7 | marker attrs + bound-code token scan | `attr timeout;` etc on flow/node | regex over every file the node's code= binds (`\btimeout\s*=`) | per node (all bound files pooled) | REL201/211/221.../397 |
| B8 | `refine`/`abstract` | decomposition tree | code binding legal only on leaves (documented; enforcement = abstract node has no `code`, plan frontier) | n/a | `frob sys plan` |
| B9 | vmodel_node `code_ref "path[:symbol]"`, `runnable "path::Class.method"` | spec artifact -> doc or code reference; test -> runnable id | none enforced at the graph layer (strings) | symbol-form string, NOT resolved by strata-core | VMOD001 checks presence of the attr only; resolution is a frob concern |
| B10 | `[graph].exclude` in frob.toml | shared exclusion globs | n/a | file | bind_code, capability scan, SYS101 fully-excluded-node skip (INV-026) |
| B11 | Unity .asmdef (T-4512) | generated root module `design/unity-assemblies.strata`: one node per asmdef, `code=<asmdef dir>/**`, edges from references, plus synthetic unity_default_assembly | none | assembly directory | demonstrates the first non-Python "binding generator" |
| B12 | `frob sys init` bootstrap | derives one node per package dir + flow per observed import direction; never writes may | n/a | directory | one-time skeleton |

How effects are OBSERVED (the join behind B2): frob.vet._capability registry = 167 hand-written
`_op(language, library, function_or_pattern, capability_kind, cwe_links, rationale,
safer_alternative, severity, needles)` rows across python/typescript/rust/c-cpp/kotlin/bash/
csharp/java/cuda; scanner is line-level SUBSTRING needle matching with recall-over-precision
philosophy, a binding/import-aware resolver added later (T-0328) for aliasing, and
`non_executable_line_numbers` to skip docstrings/comments. Kinds: net.connect, net.listen,
fs.read, fs.write, exec, env.read, env.write (the 7 in `_KIND_MAP`, i.e. THREAT004-joinable)
plus eval, env, ffi, install-hook, sql, deserialize, html_render, fetch_url, client_storage
(the "extended" kinds). Observation site = (file, line, kind, extracted-first-string-argument);
enclosing symbol resolved by frob.lang.parse_file only when a symbol-form via exists.

### 4.2 Where binding is weak (measured)

1. GLOB (FILE) GRANULARITY IS THE UNIT. A node owns whole files. A file with two
   responsibilities cannot be split; the only symbol-level escape is the `via "path::qualname"`
   clause on `may`, and design/frob.strata (the one big adopter) still carries 641 file-form
   via entries and a documented 876-entry hand-migration backlog (T-1627 migration note).
2. GLOB SEMANTICS ARE fnmatch, NOT PATH GLOBS. `fnmatch.fnmatch` lets `*` cross `/`; `**` has no
   special meaning; ambiguity between two nodes is a hard error, so adding a new directory
   requires editing 1-2 nodes by hand (every new test file appended a glob to the testsuite
   node's via lists, producing >13KB single lines; fragments T-2502 were added purely to avoid
   merge conflicts on that line).
3. PYTHON-FIRST. Import conformance (SYS003, flows-as-imports) is Python-only (`ast`);
   C/C++ #include resolution exists in frob.lang but is not wired; TS/Rust/others get only the
   capability needle scan, never import-flow checking. FOREIGN->bound imports are unchecked.
4. SUBSTRING EFFECT DETECTION. Needles match text, not resolved calls. Consequences measured
   in docs: self-matching (a docstring spelling a needle fired SYS100 on its own module;
   pattern-catalog files need `is_self_pattern_path` exclusion), `compile(` matched as eval,
   `of` argument scoping is "first quoted string on the same line", aliasing handled only
   best-effort. SYS101 "stale" on a grant with partial via staleness is left unfixed because
   re-deriving per-via joins would duplicate logic.
5. SYMBOL IDENTITY IS A STRING. `via "src/x.py::Class.method"` and `interface=Name` are
   name lookups: rename = SYS109/SYS110 noise, no similarity/rename detection, no signature
   or body digest, nothing detects a symbol silently changing behaviour while keeping its name.
6. ONE DIRECTION OF DRIFT. SYS100 (observed not declared) and SYS101 (declared not observed)
   are both per capability KIND; there is no declared-vs-observed check for what a symbol
   RECEIVES/RETURNS or which flows it implements. Directives (frob:channel/boundary/secret)
   are the only symbol->flow edge, and they are almost unused: 3 directive comments exist in
   all of src/frob (2x frob:channel f_cli_tickets, 1x frob:boundary b_vet_endorse); 188
   frob:doc comments live in the .strata file instead.
7. MODEL SIDE HAS NO INVERSE INDEX. A flow is not bound to a producer symbol and a consumer
   symbol; REL201/etc pool all node files; SYS114 greps a regex for a config-bound host in
   the whole outbound file.
8. CROSS-LANGUAGE IS NOT MODELLED. No construct says "this Rust fn is called by that
   Python wrapper" or "this HTTP route handler in TS implements flow f". FFI is a capability
   kind only; the Unity asmdef generator is the lone cross-language-ish exception.
9. Design-file symbol spans are regex-located (parser returns none).
10. Bookkeeping risk: the self-model `interface=` lists (1567 declared names across 22
    blocks, hand-maintained after the generator was deleted by owner directive) and the 641 via
    entries are exactly the "declaration that duplicates observable fact" shape the v1 team
    itself called bookkeeping (T-2920, entity_architecture.md "SYS100-112's bookkeeping shape").

### 4.3 Proposal: symbol-level, cross-language binding for v2 (inside a PM tool)

Goal: the .strata-equivalent model names architecture; every model element resolves to
concrete SYMBOLS in any supported language; drift in either direction is a first-class,
ticketable finding. Principle (keep from v1): model side holds intent and ceilings, code side
holds attestations; neither side is ever auto-regenerated to match the other (shrink-only
ratchet; owner directive T-1870/T-2920).

A. Identity layer (shared, the one new primitive).
   - SymbolId = (language, repo-relative path, qualname, kind) plus a content fingerprint
     triple: sig_hash (normalised signature), body_hash (normalised AST, comments stripped),
     and a stable `anchor` (optional explicit `frob:id X` comment) that survives renames.
   - Produced by ONE tree-sitter-backed extractor per language implementing a small trait
     (symbols(), imports(), calls(), effect_sites()); every rule consumes the resulting
     per-repo SymbolGraph, never raw text. v1's frob.lang already has this; v2 makes it the
     only substrate (no regex rescans).

B. Model side declares (all in the design file):
   - `owns`: node -> selectors, `SELECTOR := lang? path-glob [ "::" qualname-glob ] [ kind ]`.
     Real path globs (gitignore semantics, `**` crossing dirs, `*` not), qualname globs
     (`Client.*`), kind filter (fn/class/const/type/module). Resolution = most specific
     selector wins (symbol > file > dir); equal specificity on one symbol is an error;
     unclaimed symbols are FOREIGN (deny by default). Files are only a default expansion:
     a file glob owns all symbols in the file unless a more specific selector claims some.
   - `grants`: node -> capability atoms with explicit SCOPE: `may net.connect:host.example
     at Client.send` (symbol selector) and `of` argument constraints resolved from the call
     AST, not "first string on the line". Ceiling semantics unchanged (declared >= observed).
   - `flow` gains `via`: producer selector and consumer selector (the symbols that send and
     receive) plus an optional `contract` selector naming the shared schema/type/IDL symbol
     (protobuf, OpenAPI path, TS interface, Rust struct). A cross-language flow is simply a
     flow whose producer and consumer selectors resolve in different languages; the contract
     symbol is the join key and is fingerprinted.
   - `surface`: node -> intended public symbols (replaces `interface=[...]` lists with
     selectors such as `pub fn *` or explicit ids) with subset semantics (SYS110 semantics:
     real public surface must be a subset of declared intent). Never generated.
   - `requires_tests`/`verified_by`: node or obligation -> runnable selector (path::qualname).

C. Code side declares (sparse, optional, always checked against the model):
   - `frob:anchor ID` on a symbol for rename-stable identity.
   - `frob:node NODE` override (explicit one-symbol assignment; model must still allow it, so
     this is an attestation not an escape hatch -- mismatch = finding).
   - `frob:channel FLOW [role=producer|consumer]`, `frob:boundary B`, `frob:secret N`
     (keep v1 verbs, add role). Required by rule where the model marks a flow/boundary as
     `attested` (not blanket SYS002 for all boundaries).
   - `frob:effect ATOM because "reason"` for ambient effects that cannot be inferred
     (replaces the `// because:` text convention of SYS112 with a code-side attestation).

D. Drift detection (all computed from SymbolGraph + design, run at check time and on land):
   | Drift | Detection |
   |---|---|
   | model selector resolves to zero symbols | UNRESOLVED (v1 SYS113/SYS109, but for any selector) |
   | symbol claimed twice | AMBIGUOUS |
   | symbol unclaimed but has effects or public visibility | UNMODELED (v1 SYS102/103/106 unified) |
   | observed effect not covered by grant at that symbol | EXCEEDS_CEILING (SYS100) |
   | grant never observed at its scope | STALE_GRANT, shrink-only auto-fix allowed (SYS101 + `frob sys shrink`) |
   | resolved import/call edge between owners with no flow in that direction | UNDECLARED_FLOW (SYS003, now for every language via the import/call resolver) |
   | flow declared, no producer symbol or no consumer symbol | UNIMPLEMENTED_FLOW |
   | symbol fingerprint changed since the model/binding was last acknowledged | CHANGED (acks like `frob ack`: body_hash change on a bound symbol requires re-ack or ticket) |
   | symbol vanished but a similar fingerprint appears elsewhere | RENAMED (suggest selector/anchor edit, never auto-edit) |
   | contract symbol fingerprint differs between producer and consumer revisions | CONTRACT_SKEW |
   | public symbol outside `surface` | UNDECLARED_SURFACE (SYS110) |
   Fingerprints and acknowledgements live in a tracked lock file keyed by SymbolId (the same
   shape as v1's capability-via-ratchet.lock.json: growth requires a human-written reason).

E. Cross-language mechanics.
   - One import/call resolver per language returns edges between SymbolIds; flows are checked
     against edges between OWNERS, so no per-language special case exists in the rule.
   - FFI/IPC/HTTP edges are NOT inferred from text: they are declared flows with contract
     selectors; the check is "producer exists, consumer exists, contract fingerprint matches
     on both sides". A missing resolver for a language downgrades its files to
     "binding-only, no edge checking" and says so in the report (v1 hid this).
   - Effect detection moves from substring needles to typed call-site patterns (tree-sitter
     queries + resolved callee qualname) held in a data registry like v1's DANGEROUS_OPERATIONS
     (keep its row schema: language, library, pattern, capability_kind, cwe_links, rationale,
     safer_alternative, severity), with the "empty cell must be excused" matrix check.

F. Cost control. Fingerprints and edges are cached by file content hash (v1 INV-050 style
   `check(S, C) == check(S, empty)`); rules take a read-only SymbolGraph snapshot; native Rust
   makes whole-repo resolution cheap enough to run on every check.

## 5. Every strata rule and exactly what inputs it needs (for macro generation)

Input legend: M = elaborated KernelModel (nodes/flows/boundaries/claims/scenarios);
P = parsed pre-elaboration Module data that does NOT survive into KernelModel (stores, resources,
policies, may_grants, entities); B = code binding (file -> owner, CodeBinding.owner);
S = source text of bound files (scan); I = resolved local import graph; Sy = frob.lang symbols
of a file; G = frob graph directive edges (channel/boundary/secret/doc/...); C = in-code catalog
data; Cfg = frob.toml ([graph].exclude, [strata], benign capabilities); Y = registry YAML;
T = ticket ledger state; Git = git history/HEAD; Txt = raw .strata text (comments etc.).
Waive key: S = RULE:SUBTARGET required (multi-instance); B = bare rule; - = not waivable.
Severity noted where documented; everything flows through `frob check --only sys` via
SELFAUDIT001 (sys_gate folds frob sys audit families into ordinary Violations, T-0756).

### 5.1 Binding / self-conformance (SYS0xx, SYS1xx, SYS3xx, SYS9xx)

| Id | Fires when | Inputs | Sev | Waive |
|---|---|---|---|---|
| SYS001 | frob:channel/boundary/secret names an id absent from merged design ids (suppressed if any file failed to load) | G + merged design ids | ERROR | frob:waive |
| SYS002 | boundary or Secret-clearance node has no directive anywhere | M + G | WARN | frob:waive |
| SYS003 | resolved import from owner A's file to owner B's file with no flow A->B | M + B + I (python ast) | ERROR | frob:waive |
| SYS004 | a .strata file fails to parse/elaborate | design dir + native parser | ERROR | frob:waive |
| SYS100 | observed capability kind at a site not covered by node `may` (file/site/argument scoped) | M(may_grants) + B + S (+Sy if symbol via) | ERROR | S (kind) |
| SYS101 | declared `may` atom (per via grant) never observed in bound files; skipped for nodes whose whole code set is excluded | M + B + S + Cfg(exclude) | ERROR | S (kind) |
| SYS102 | src/frob top-level dir (or loose file) all FOREIGN | B + fs (hard-coded src/frob root) | ERROR | B |
| SYS103 | FOREIGN file with any observed capability, any repo root | B(all langs) + S | ERROR | B |
| SYS105 | node `purpose=PROFILE` bounds allowed effect kinds (pure/read-only/logging/network/full); unknown profile is a finding | M(attrs) + B + S | opt-in | S |
| SYS106 | FOREIGN file reachable by imports from a bound file and capable | B + I closure + S | ERROR | B |
| SYS107 | via-less `may` on a node binding > 20 files (per atom); exec/eval/install-hook/ffi always ERROR | M + B + Cfg[strata].require_may_scope | WARN/ERROR | S |
| SYS108 | duplicate `interface=` symbol on a node | M(attrs) | ERROR | S |
| SYS109 | symbol-form via names a symbol that resolves in zero bound files | M + B + Sy | ERROR | S |
| SYS110 | real public symbol not in a node's declared `interface=` (opt-in per node; 14 exempt nodes hard-coded) | M(attrs) + B + Sy | ERROR | S |
| SYS111 | via-list grew past ceiling in capability-via-ratchet.lock.json without a written reason; also testsuite glob growth finding | M + Y(lock json) + Git(HEAD .strata text) | ERROR | lock reason |
| SYS112 | via-less (ambient) `may` lacks a same-line `// because: "..."` | Txt (raw .strata) | ERROR | - |
| SYS113 | `code` glob set or glob-form via matches zero real files | M + B + fs | ERROR | B |
| SYS114 | outbound flow to a foreign node whose granting file has no config-field-bound host constraint (regex) | M + B + S | deny-by-default | S (flow id) |
| SYS115 | outbound-to-foreign flow lacks `rate` while a sibling declares one | M | lint | S (flow id) |
| SYS116 | node carries `identifier.*` PII with no `derived_from:TAG=HELPER` | M(attrs) | gate | - |
| SYS117 | `trust_identity:TAG` attr without matching `carries` | M(attrs) | gate | - |
| SYS119 | >=2 assumes identical after substituting node id (token-level parse comparison) | M(claims) per source file | WARN | - |
| SYS120 | one review date shared by assumes across > 2 modules (module = file stem today) | M(claims) + file provenance | WARN | - |
| SYS300 | architecture names an entity declared nowhere (same-file at parse, cross-file at load) | parse + design-load pass | ERROR | - |
| SYS301 | architecture `binds` a module other than own file's | parse | ERROR | - |
| SYS302 | union of bound module's node `may` grants exceeds entity `may` ceiling | P(entities) + M | ERROR | - |
| SYS303 | configuration pairs an entity/architecture that do not match | parse | ERROR | - |
| SYS900 | explicit worktree/branch sys audit could not resolve (UNRESOLVED severity) | Git + sys_gate | UNRESOLVED | - |
| SYSWAIVE002/003 | in-design waiver matched nothing (stale) / waiver hygiene | M(waivers) + all findings | ERROR | - |
| RELWAIVE002 | same stale-waiver finding for REL families | M + REL findings | ERROR | - |
| SELFAUDIT001 | wrapper: any sub-family above surfaced as one gate violation | all | - | - |
| DOC003 | prose claim marker `frob:claims VIEW` in docs not backed by a PROVED exhaustiveness result | docs markers + M | ERROR | - |
| INV051 | child policy weakens an inherited confine_use/at_call_require_arg/mediate | P(policies) + M (compile_policies) | ERROR | - |

### 5.2 Threat / compliance / privacy / lint / supply-chain

| Id | Fires when | Inputs | Waive |
|---|---|---|---|
| THREAT001 | baseline-view CWE has no WeaknessEntry or OutOfScopeEntry (INV-035) | C(catalogs, VIEWS) + Cfg(selected views) | - (view-scoped) |
| THREAT002 | `may` capability kind classified by no catalog and no BenignCapability | M + C(ALL_CATALOG, benign) + Cfg(repo benign) | S (kind) |
| THREAT003 | fired obligation (node has capability_kind of an entry) lacks a discharging claim at >= catalog rung that PROVES as a chokepoint (managed nodes exempt from boundary-kind proof) | M + claims + C | S (CWE) |
| THREAT004 | observed net/fs/exec effect with no matching `may` | M + B + S | -- |
| THREAT005 | observed kind unrecognised and unexcused | B + S + C | -- |
| THREAT006 | OutOfScope/Benign `caught_by` names unresolved rule/CWE | C + live rule-id set | - |
| COMPLIANCE001 | regulation id in a baseline view has no RegulationEntry/OutOfScope | C + Cfg | - |
| COMPLIANCE002 | fired regulation duty (COPPA, GDPR erasure/retention/lawful basis, HIPAA BAA, minimisation, PRIVACY-NOTICE) undischarged | M(attrs subject:/jurisdiction:/basis:/retention=/privacy-policy) | B |
| COMPLIANCE003 | collection flow `field:NAME` not listed in the declared privacy policy | M(attrs) | B |
| COMPLIANCE004 | regulation out-of-scope `caught_by` unresolved | C | - |
| COMPLIANCE005/006/007 | compliance.yaml unit dispositions missing / file deleted-after-adoption / vacuous self-referential handled_by (WARN) | Y + Git | - |
| PII001 | `carries` tag category not in 7 categories (identifier, contact, financial, health, biometric, behavioral, credentials) | M(attrs pii=) | B |
| PII002 | flow touching a PII node crosses a different TRUST level without `assume "pii:PROTECTION:<flow>"` | M | B |
| PII003 | PII node has neither `retention=` nor a revocation-edge flow | M | B |
| PII004 | flow from a PII node labelled below Pii | M | B |
| PII005 | two different derived_from helpers for one tag | M(attrs) | - |
| PII010-013 | structural (non-strata) PII-in-code detectors: PII-shaped field names/types in py/ts/rust structs; email-shaped literals; land-parity; no_pii | S (tree-sitter fields) | frob:waive |
| LINT001 | flow from foreign node has no `rate` | M | B |
| LINT002 | node capacity exceeded by non-infra inbound rate, no cache over it | M(capacity, rate, caches via P) | B |
| LINT003 | scenario with ScaleRate nests no bound claim on scaled flow/endpoint | M(scenarios) | B |
| LINT004 | `may` of kind exec/net with no `attr flag=ID` kill switch | M | B |
| LINT005 | total inbound rate exceeds service_rate * replicas_max | M | B |
| CVEFP001 | CveFingerprint.cwe_id unresolved in CWE+TOP25+QUALITY union | C | - |
| VET006 | dependency source matches a fingerprint needle | S of deps | vet allowlist |
| HOST001/002 | lateral / vertical movement between service users | M(host attrs -> HostManifest) | S |
| KRB001-004 | unconstrained delegation / kerberoast per SPN / constrained blast radius / cross-realm containment | M(krb attrs + synthesised flows) | S (per spn/node) |
| DEPLOY001-003 | generated deploy script drift / conformance | HostManifest + deploy/ dir bytes | - |
| SEC001-005, SEC110 | secrets/tokens in tracked files (not strata) | S | frob:waive / frob:secret-fake reason= |

### 5.3 Contention, claims, V-model, registry, invariants

| Id | Fires when | Inputs | Sev |
|---|---|---|---|
| SYS200 | two nodes `listens` same port | M(attrs) | ERROR |
| SYS201 | two nodes' `owns`/`acl` paths overlap by directory prefix (write_capable flag) | M(attrs) | ERROR |
| SYS202 | two nodes bind same `pipe` | M(attrs) | ERROR |
| SYS203 | >= 2 nodes have a Flow into the same store (mode-blind); discharged by resource arbiter | M + P(stores, resources) | ERROR |
| SYS204 | two accessors of one resource in conflicting modes with no `lock`/`arbitrated_by` | M(attrs access=) + P(resources) | ERROR |
| SYS205 | code observed in a mode its node did not declare for the resource | M + B + S | per site |
| claims | REFUTED noflow/reach/bound/independent/readers; overdue assume => REFUTED | M + FactBase + today | gate |
| VMOD001 | orphan_requirement / unjustified_design / untested_artifact / orphan_test / trace_cycle / construction error | vmodel_node/edge from all files (strata-core) | WARN |
| MSCLOSE001 | untested artifact not named in MILESTONE_GAP_REGISTRY[milestone] | vmodel + Python registry + frob.toml default_milestone | WARN |
| REG001 | registry entry undispositioned / bare `addressed` / empty out_of_scope reason | Y | ERROR |
| REG002 | `handled_by:RULE` names a non-live rule | Y + live gate rule ids | ERROR |
| REG003 | `deferred:T-id` ticket missing/closed | Y + T | ERROR |
| REG004 | `duplicate_of` dangling; documented split lacks cross_refs | Y | ERROR |
| REG005 | declared `total:` != actual count | Y | ERROR |
| REG006/007 | non-mapping/idless list item; duplicate id across files | Y | ERROR |
| REG008/009 | `frob:enforces` code edge vs `handled_by` cross-check (derived coverage), WARN | Y + G(enforces edges) | WARN |
| REG010 | live gate rule has no CHK-GATE-<rule> row in check-coverage.yaml (auto-fixed on land) | Y + live rule ids | WARN |
| REG011 | out_of_scope reason names no resolvable control and is not a substantive "none -- why" | Y + C | WARN |
| REG012 | registry dir adopted (git history) then deleted; unwaivable | Git + fs | ERROR |
| INV001/2/5 | invariant has no standing evidence / no `frob:invariant` code anchor / evidence never shown | invariants/*.md + G(invariant edges) + test collection | ERROR |
| INV003/4 | doc normative claims lack invariant binding | docs text + invariants | ERROR |

### 5.4 Reliability families (all: M(flows/attrs) + B + S regex; waive S; stale-waiver RELWAIVE002)

| Ids | Obligation | Declaration (marker) | Proof-against-code token (rule 2) |
|---|---|---|---|
| REL200/201 | timeout on every flow | flow `timeout` / `async` / `local` | caller's bound code has `timeout=` |
| REL210/211 | health surface on long-lived `unit` | node `health` | bound code health token |
| REL220/221/222 | retry backoff+jitter; idempotent target; retry code proof | flow `retry`+`backoff_jitter`, node `idempotency_key` | retry token |
| REL230/231 | circuit breaker on `external`+`critical` | node `circuit_breaker` | token |
| REL240/241 | fallback on critical dependency | node `fallback` | token |
| REL250 | SPOF: critical inbound path into node with replicas_max=1 | flow `critical`, capacity | model only |
| REL260/261 | backpressure on queue/consumer | node `bounded_intake` | token |
| REL270/271/272 | observability on boundary flow; correlation on chained hop | flow `observability`/`correlation` | token |
| REL280/281 | golden-signal SLO + error budget on services | node `slo`, `error_budget` | token |
| REL290/291 | single source of truth for a store | node `owner`/`reconciliation` (+P store ids) | token |
| REL300/301/303 | transaction or saga boundary; inbound-rate on write flow from untrusted source (REL303) | node `transaction`/`saga`; flow `rate` | token |
| REL310/311 | interactive cost bound | node `interactive`+`bounded_cost` | token |
| REL320/321 | message schema version on events/queues | node `event`/`queue`+`schema_version` | token |
| REL330/331 | delivery semantics declared | `attr delivery=...` | token |
| REL340 | sync call-chain depth over limit | M flows, `deep_chain_ok` | model only |
| REL350/351 | distributed txn across services needs saga | node `saga` | token |
| REL360 | shared mutable state across service boundaries | `shared_state_ok` | model only |
| REL370/371/372 | clock/ordering assumptions | flow `clock_dependent`+`ordering_strategy` | token |
| REL380-383 | starvation/throughput at every contended resource | node `users`, `access`, `capacity`, resources | model arithmetic |
| REL390-393 | kernel-interface classified; process cgroup bounds | node markers | token |
| REL394-397 | ABI/ISA compat window; boot attestation | node markers | token |
Total REL ids: about 55. Common weakness: marker presence + a lexical token anywhere in the
node's bound files; the REL docs admit it proves neither magnitude nor same-call-site.

### 5.5 What a v2 rule macro must capture (derived from the tables)

Per rule: id; family; one-line statement; severity default + promotion ladder (all new rules
shipped WARN then ratcheted); INPUT SET drawn from {Model, Parsed-only data, SymbolGraph owners,
Source/AST facts, ImportEdges, Directive edges, Catalog, Config, Registry, Tickets, Git, RawText};
unit of finding (node | flow | file | symbol | whole-view); waiver key shape (bare | RULE:SUB with
sub-target extractor); `fires_when` predicate; `discharge` options (claim / marker / waiver /
excuse entry); catalog join (if any) and its drift-lock; positive-control fixture AND
negative-control fixture (v1 doctrine: "a clean verdict with no must-fire case proves nothing",
tests/gates_suite/test_sys_rule_liveness.py sweeps rule-id -> fixture); registry row
(CHK-GATE-<id>, auto-synced); doc anchor; telemetry liveness (SF-01 measured 79 SYS rule ids
with zero real fires). v1 hand-wrote ~100 such modules; the shared shapes are: (1) per-node
per-attribute presence check, (2) per-flow presence check, (3) presence + bound-code token proof,
(4) pairwise conflict over a keyed attr, (5) catalog completeness join, (6) catalog-entry fire +
discharge-claim check, (7) closure/arithmetic claim, (8) stale-waiver. Shapes 1-4 and 8 are
macro-generable from a ~10 line declaration; 5-7 need catalog + claim plumbing.

## 6. The registries: threat, compliance, capability, CVE, PII, benign excuses

### 6.1 Row shapes and sizes

| Registry | Location | Row shape | Size |
|---|---|---|---|
| CWE catalog (security) | strata/_threat_catalog_cwe.py (+_threat_models.py) | WeaknessEntry{id "CWE-79", title, cite url, family="security", capability_kind (a `may` atom kind or None), mitigation (boundary predicate name), rung L1-L5} | 14 WeaknessEntry constructors in the file (CWE_CATALOG + CWE_TOP_25_CATALOG tables) + 16 OutOfScopeEntry{id, reason, caught_by} (cwe-top-25 2025 pin) |
| Quality catalog | _threat_catalog_quality.py | same WeaknessEntry with family="quality": CWE-639, REL-001, PERF-002, CWE-295, CWE-916, CWE-1321, CWE-1333, CWE-601, CWE-1336, PERF-COMPRESS-001, PERF-BATCH-001, PERF-OPTIMISTIC-001, SEC-CORS-001, SEC-ROUTE-AUTHZ-001 | 9 weakness + 5 out-of-scope rows (counted by constructor) |
| Views | VIEWS (owasp-top-10 ...), CWE_TOP_25_VIEWS, QUALITY_VIEWS, REGULATION_VIEWS, CVE_FINGERPRINT_VIEWS | dict view -> id set; baseline the exhaustiveness proof is measured against; `cwe-top-25` deliberately NOT in the default view set, disclosed via AuditReport.narrower_than_baseline | 4 tables |
| Benign capabilities | _threat_catalog_benign.py; repo extension `[[strata.benign_capabilities]]` in frob.toml | BenignCapability{kind, reason (min_length 1), caught_by, family "security"|"quality" (mandatory + load-verified for repo entries)} | 17 built-in |
| Compliance catalog | _compliance.py | RegulationEntry{id, title, cite, attrs (jurisdiction=, subject=)}; OutOfScopeRegulation | 7 entries (COPPA, GDPR erasure, retention, lawful-basis, HIPAA BAA, minimisation, PRIVACY-NOTICE) + 1 out-of-scope (CCPA right-to-delete) |
| PII categories | _pii.py PII_CATEGORIES | flat set of 7 category strings; tag = `<category>.<field>` | 7 |
| CVE fingerprints | _cve_fingerprint.py | CveFingerprint{id "FP-EXEC-SHELL-001", title, cve (>=1 REAL id), cwe_id (joins catalog union), language, needles (>=1), remediation} | 18 entries |
| Capability registry | vet/_capability_registry/ (_kinds, _schemas, _matrix, _dangerous_ops_*) | _DangerousOperation{language, library, function_or_pattern, capability_kind, cwe_links, rationale, safer_alternative, severity, needles}; _MatrixExcuse{capability_kind, language, reason}; NO_CAPABILITY_MODULES | 167 `_op` rows over 9 languages |

### 6.2 The "benign capability excuse" model

THREAT002 asks: is every `may` capability kind CLASSIFIED? A kind is classified iff some
catalog family has an entry with that capability_kind (taxonomy-wide union ALL_CATALOG, T-0171)
OR a BenignCapability excuses it. An excuse is a statement "no sink in THIS family's taxonomy
targets this kind" -- e.g. `ffi` has no CWE sink entry; `fs.read`, `net.connect`, `net.listen`
have none on their own. Rules that make it more than a silencer: reason is mandatory
(Field(min_length=1) / MalformedBenignConfig); `family` is mandatory for repo-declared excuses
and the loader REJECTS an excuse for a kind already classified in the family it names (blocks
masking a known sink); `caught_by` must resolve to a live rule id/CWE or be a substantive
"none -- why" (THREAT006/COMPLIANCE004/REG011 share one helper). The excuse lives in frob.toml
rather than the .strata file because it is whole-repo vocabulary bridging, not a claim about one
node (design decision in threat.md, T-0017). Code-level mirrors THREAT004/005 apply the same
taxonomy to OBSERVED effects.

### 6.3 Obligation machinery (threat.md "core reframe")

A CWE is a CONDITIONAL OBLIGATION predicated on a capability being present. Declaring
`may "sql"` auto-instantiates CWE-89 (+ quality CWE-639); `html_render` -> CWE-79/116;
`exec` -> CWE-78/94 (one shared join; kernel cannot tell OS-command from code-eval);
`deserialize` -> 502; `fetch_url` -> 918; `client_storage` -> 922/312. Discharge = a claim named
`weakness:<cwe>:<node>` (STRING claim id, T-0138) that is a NoFlow claim PROVED as a genuine
mitigation chokepoint at >= the entry's rung, or an ASSUME (owner + expiry). Library mode
(T-0223): `assert "weakness:CWE-78:runner" noflow foreign -> runner` is vacuously PROVED when the
model has no foreign node, and automatically REFUTES the moment one with an unendorsed path is
added. Exhaustiveness = conjunction of THREAT001 (catalog completeness vs a cited baseline
view), THREAT002 (capability classification), THREAT003 (discharge completeness), reported as a
per-family matrix by `frob sys doc` and checked by `frob sys audit`. Honest limit stated in the
docs: exhaustive RELATIVE to the cited baseline only; four catalog ids (CWE-22, 352, 798, 611)
have capability_kind=None and can NEVER fire under THREAT003 (litmus "unfired" fixtures prove
the negative); 16 of the 2025 Top-25 are OutOfScope for missing kernel vocabulary (memory
safety, authn/authz routes, upload, resource exhaustion).

### 6.4 LINT / PII / COMPLIANCE / SEC families -- what they are really checking

- LINT001-005: operational design lints over declared rates/capacity/caches/scenarios/risky
  capabilities. Pure model joins; no code. LINT004 (kill switch) is waived on 4 frob nodes with
  ticket T-0200 because no real kill switch exists -- the waiver goes stale if the finding stops.
- PII001-005: `carries` tag hygiene, boundary-crossing protection, retention, undeclared-PII
  flow labels, provenance contradiction. frob's own self-model asserts zero PII by test.
- PII010-013 and SEC001-005/110 are NOT strata: they are structural scanners (field-name
  signatures, email-shaped literals, token regexes) that happen to share the registry/REG
  discipline.
- COMPLIANCE: catalog + bespoke `_check_<regulation>` functions (NOT data-driven: adding a
  RegulationEntry gives no discharge check). Privacy-policy-as-claims (reverse audit) is a
  design idea whose enforcing machinery (COMPLIANCE003 + DOC003) exists but whose surface
  grammar cannot author `subject:child` flow attrs, so the COPPA litmus is a Python fixture.
- CVE: two distinct things. (1) dependency-version join through `frob vet` (osv-scanner, 14-day
  cooldown, shared CWE id); (2) CVE fingerprints = code-level needles for canonical vulnerable
  usage (TLS verify=False, shell=True, pickle.loads, XXE, ...), joined by CVEFP001 and surfaced
  as VET006 in dependency scans, deliberately curated not exhaustive (JNDI/Log4Shell omitted,
  CWE-916 pending a catalog row).

## 7. The prover: claim kinds, scenario kinds, invariants

### 7.1 Claim kinds (ClaimBody union in _models.py; dispatch in _claims.py::evaluate_claims)

NoFlow, Reach, BoundClaim(Metric), Independent, SetEquality. One entry point, one ClaimResult
per claim in declaration order (a report can never silently drop a claim), fails closed on a
malformed model. Surface-authorable: noflow, reach, bound. Auto-generated only: independent
(breach recovery paths), readers()==S (secret audience). Evaluation reuses FactBase queries
(reachable/worst_age/propagated_demand); guides forbid ad hoc traversal in _claims.py.

### 7.2 Scenario kinds (_scenarios.py, 536 lines; _breach.py, _crash.py, _atomic.py)

Rewrites applied to a COPY of the frozen KernelModel then evaluate_claims re-run:
RemoveNode (cascades: deletes touching flows and their boundaries, logged INFO per deletion),
ScaleRate (UnratedFlow error if the flow has no declared rate), SetTrust (level must exist),
AddFlow. Higher-level sugar: breach scenarios (blast radius = reachability under a trust
downgrade + independent() recovery-path claim), crash contracts (`on crash` -> auto scenario +
no-hang INV-027), deploy contracts. LINT003 forces any ScaleRate scenario to nest a bound claim.

### 7.3 How invariants/INV-*.md connect to frob:invariant and tests

invariants/INV-NNN.md = YAML frontmatter {id, statement (one falsifiable sentence),
criticality, evidence: [pytest node ids]} + prose + `frob:used-by <file>` footer. Code or doc
places `frob:invariant INV-NNN` (comment directive -> EdgeKind.INVARIANT edge from the symbol).
Gates: INV001 invariant has no evidence resolving to a collected test; INV002 no code anchor;
INV005 evidence collects but is never shown to run; INV003/004 doc-side normative claims
("must never", "always") need a binding or a documented waiver (this is why the strata docs
carry long `frob:waive INV003/INV004` reasons); INV006 (source-side lexical claim scan) was
DELETED (T-1763): 338 waivers, zero unwaived findings -- a purely lexical rule cannot tell a
real cross-module contract from descriptive prose. 52 invariants exist; ~20 are strata:
INV-026 (SYS101 fully-excluded skip), 027 (no-hang), 028 (worst_age inf on cycle), 029 (rung
floor), 030 (trust-scoped policy auto-covers), 031 (one-way trust default), 033 (HOST from real
manifest), 034 (unique ids), 035 (THREAT001), 036 (waiver exact triple), 041 (sys_gate never
reports clean while sub-audits fail), 047 (REL200), 048 (SYS103 totality), 050 (cache
transparency), 051 (policy refinement monotonic). Mechanism assessment: it works, is cheap, and
is the one binding in the system that is symbol-level AND bidirectional (symbol <-> invariant
<-> test id); it is plain frob, not strata.

Waivers: exact (node id, rule, sub-target) triple (INV-036); reason mandatory in grammar and blank-checked; 25 multi-instance families require RULE:SUB; stale waiver fails; WAIVED always printed with reason; frob:waive comments are the code-side twin.

Extension guides (docs/guides/extending): data registries = append a row; logic registries (compliance discharge, LINT, claim kinds, scenario rewrites) = new code; no gate checks claim-variant dispatch coverage or LINT aggregation.

Editors: vscode tmLanguage hand-synced (one pytest drift-lock), jetbrains README only, no LSP.

## 8. Registry drift-lock (`frob registry`, REG rules, docs/design/registry/*.yaml)

Purpose: every enumerable universe frob researched (CWE-1000 view, design patterns, compliance
units, system-design checks, evasion constructs, ...) gets canonical ids and an honest
disposition, enforced by a gate, so "we surveyed it" cannot silently diverge from "we enforce
it". Built by T-0343/T-0407/T-0424/T-0428/T-0560.

| File | Entries | Source corpus |
|---|---|---|
| weaknesses.yaml | 984 (944 CWE-1000 + 40 other) | cwe-1000-registry.md (MITRE v4.20), security-corpus.md |
| patterns.yaml | 346 | design-pattern-catalog.md (325), design-pattern-traps-corpus.md (21) |
| arch-checks.yaml | 311 | architecture-check-catalog.md (288), structural-linter-adversarial-hardening.md (23 SLH rows) |
| system-design.yaml | 119 (14 are extraction artifacts) | system-design-corpus.md |
| evasion.yaml | 112 | capability-evasion-taxonomy.md |
| compliance.yaml | 27 units (599 leaf controls deliberately NOT id'd: borrowed denominators) | compliance-corpus.md |
| secrets.yaml / pii.yaml | 3 / 7 sections | secrets-pii-corpus.md |
| supply-chain.yaml | 41 (doc's own total says 39) | supply-chain-corpus.md |
| check-coverage.yaml | gate_rule_total 667 CHK-GATE-<rule> rows + concern_family_entries | live rule registry + docs/audits |
| capability-via-ratchet.lock.json | 395 lines | SYS111 ceiling |
Grand total 1950 corpus-derived entries (README) plus the 667-row reflexive file.

Entry: `{id, name, source_doc, source_ref|parents|framework|leaf_count, checkability
(tier1-static|tier2-advisory|tier3-not-checkable|provable|advisory..., NOT normalised across
files), disposition, cross_refs[], fixability?}`. Disposition grammar (frob.registry._models,
parse_disposition): `handled_by:<rule-id>` (must be live; REG002), `deferred:<ticket>` (must
be open; REG003), `duplicate_of:<id>` (REG004), `out_of_scope:<reason>` (reason must name a live
control or be "none -- <explanation>"; REG001/REG011), anything else = REG001. DERIVED model
(T-0428): handled_by is cross-checked against code-declared `frob:enforces <concept-id>` edges
(REG008/009) instead of trusted. Mechanics: `frob registry audit` prints per-file accounting
(handled/deferred/duplicate/out_of_scope/unaccounted/malformed vs total); `--sync-gate-rules`
appends missing CHK-GATE rows crash-safely (atomic_write) and `frob ticket land` runs it
automatically when _KNOWN_GATE_RULES changed; `frob registry add` (_corpus.py append_entry)
is the emit path an exhaustive-research pass uses to write straight into the registry.

Assessment of the drift-lock: the mechanism is sound (denominator + disposition + live
cross-check). The content is mostly "out_of_scope:none -- <long boilerplate>": patterns.yaml
GoF rows are ALL advisory out-of-scope; weaknesses.yaml's 944 CWEs are overwhelmingly
out-of-scope/duplicate; compliance rows self-reference COMPLIANCE005 (vacuous, flagged by
COMPLIANCE007). The registry proves enumeration discipline, not enforcement breadth.

## 9. Corpora, litmus fixtures, editor grammar

### 9.1 Corpora (docs/design/, ~7.7k lines) -- what they were for

Exhaustive-research outputs (frontier method: enumerate categories with denominators first,
then source each row with a primary citation) feeding (a) the T-0331 "senior-systems checks"
epic and the REL2xx families (system-design-corpus: STRATA-CHECKABILITY tag provable/advisory/
not-checkable per row), (b) the strata threat catalogs (security-corpus: design-level-provable /
needle-detectable / advisory / not-checkable), (c) frob perf rules (coding-performance-corpus:
STATIC/PROFILE/ADVISORY, maps PERF001-008; system-performance-corpus: methodology depth layer),
(d) supply-chain/vet design, (e) compliance and secrets/PII scoping, (f) cwe-1000-registry.md
(944 ids with per-id disposition checkable/duplicate-of/out-of-scope) and
design-pattern-catalog.md (325 patterns). Each ends in a `## DENOMINATOR MANIFEST` of
machine-readable rows that the registry consolidation (RECONCILIATION.md: 7 hard findings,
156 prose-only rows given minted ids) and the REG gate bind to. Only system-design and
security corpora materially shaped shipped strata rules; the rest are reference reading.

### 9.2 Litmus models (design/litmus/, golden-tested)

payments.strata + payments_hardened.strata (Stripe-shaped: unendorsed foreign response,
at-least-once webhook vs idempotency, stale replica refund = double-refund class, breach +
recovery independence); tube.strata (cold-cache stampede, `staleness unlimited` only on an
immutable blob, CDN TLS termination as declassification, 300s > 60s age refute); chirp.strata
(fanout 5 + zipf 1.5 hot shard: 89.8% vs mean-based 37.5%, growth 10% saturates in 2 months);
audit_vuln/audit_hardened (CWE-89 + CWE-639 twin); deploy_secret.strata (std.secrets +
std.deploy); forbid_rules.strata (+ fixtures/forbid_rules/{clean,violation}.py -- policy
forbid with real code); sys_liveness.strata (SYS204 planted violation, liveness sweep). The
design-D4 doctrine: litmus models are the language's compiler test suite; every language
change must keep them expressible and firing; every catalog entry needs a fixture pair
(vuln fires undischarged / hardened discharges) -- test_litmus_cwe.py parametrises over the
catalog so a new entry with no fixture fails. v2 should keep the pair-fixture doctrine.

## 10. Honest assessment

### 10.1 What is actually used (measured)

| Evidence | Finding |
|---|---|
| Self-model design/frob.strata | 24 nodes, 1 store, 1 cache, 1 resource, 1 boundary, 3 asserts, 37 weakness assumes (all one template), ~118 flow lines (almost all `label Internal; attr local;` import-direction flows), 113 `may` grants, 641 via entries, 1567 hand-declared interface= names. Constructs used: node/store/flow/may/code/waive/assume + one each of boundary/cache/resource/assert-bound/reach. Never used in the self-model: policy, scenario, refine, queue, cdn, balancer, secret, operation, entity/architecture/configuration, vmodel, host, krb, carries, deploy. |
| 10 consumer repos with design/*.strata | all use node + flow + code + may + assert/assume + waive (typani 21 nodes/50 flows; logand.app-v2 adds secret x7, carries x6, resource x3, 30 waives, 27 assumes). Only logand.app-v2 (492 vmodel nodes, 728 edges: 241 artifacts, 251 tests, 262 verifies, 466 satisfies) and kicad-libsync (36/36) use the V-model. No consumer uses policy, scenario, refine, entity, host, krb, deploy. |
| Directive binding (frob:channel/boundary/secret) | 3 uses in all of src/frob |
| Capability conformance (SYS100/101/103) | the heavily-used core: it is what keeps the design files honest and what consumers adopted |
| Import-flow conformance (SYS003) | used, ERROR-severity, Python-only |
| THREAT003 weakness assumes | 37 identical boilerplate assumes in the self-model: the obligation machinery fires and gets rubber-stamped, which SYS119 now flags (D-M8) |
| Reliability REL families (~55 ids) | SF-01 measured 79 SYS rule ids with zero real fires; REL rules are deny-by-default over every flow, so adoption needs marker attrs nobody writes; none visible in consumer designs |
| Registry/REG drift-lock | active, ERROR severity, high bookkeeping cost (667 rule rows auto-synced) |
| vmodel / entity | vmodel is real and growing; entity/architecture/configuration has zero adopters |

### 10.2 Speculative or over-built (v1 strata)

1. Host/Kerberos/deploy generator (3.8) and DEPLOY/HOST/KRB rules: a fleet-hardening epic with
   no consumer; unrelated to "design + code binding in a PM tool".
2. Six-phase boundary grammar, `operation`/atomic/saga fault-injection, crash/breach
   contracts, std.secrets/std.deploy contracts: parsed and structurally checked, never
   consumed by a real design; fault-injection generation and L2/L3 rungs never built.
3. Policy Tier-2 (AST rule execution) never built; only compile + weakening diff.
4. Compliance regulatory matrix, privacy-policy-as-claims, CVE fingerprints: elaborate, thin
   data (7 regs, 18 fingerprints), no consumers, COMPLIANCE005 vacuous.
5. 1950-row corpus registry: valuable as research, low enforcement leverage.
6. The "one kernel, six primitives" claim: 79 of 139 keywords bypass the prover; the kernel is
   really {closure, longest-path age, summed demand, V-model graph closure}, each ~100-900
   lines of Rust. Everything else is attr-string joins in Python.
7. REL families: one template copy-pasted 16 times with admitted grammar-data ceiling.
8. Hand-maintained duplicates: tmLanguage keywords, `interface=` lists, via entry lists,
   check-coverage rows; v1 repeatedly built writers then deleted them by owner directive
   (T-1870), leaving humans to maintain bookkeeping.
9. Tool-specific coupling: self-model hard-codes src/frob (SYS102, _PACKAGE_ROOT), Python-only
   import checking, `make core` rebuild trap, hard-coded 14-node SYS110 exemption set.

### 10.3 What genuinely works and should carry into v2

KEEP (core of "system design + symbolic code binding in a PM tool"):
- Deny-by-default model: node (trust, clearance) / flow (label, rate, age) / boundary
  (endorse/declassify) / claims noflow, reach, bound. Closure + SCC longest-path + summed
  demand are small, proven (incl. the regression in 3.2), and port directly to Rust.
- Three-way verdicts with quantifiers and counterexample witnesses; assume = owned, expiring,
  overdue => failing; auto-generated assumes for honest-unprovables.
- Capability ceilings with shrink-only automation: `may` + scope (via/of), SYS100 (exceeds),
  SYS101 (stale, auto-shrink only), SYS111 high-water ratchet lock with human-written reasons,
  SYS113 zero-match, SYS109 unresolved selector. The "never auto-widen" owner directive is the
  most hard-won design lesson.
- Reflexion-model import-flow conformance (SYS003) -- extend to all languages (section 4.3).
- Waivers with exact (node, rule, sub-target) triples, mandatory reason, stale-waiver failure,
  WAIVED always printed (INV-036).
- V-model spec graph as a generic typed graph kernel with construction-time refusals, paired
  levels, five structural closure rules, milestone known_gaps. It is the piece that maps
  directly onto a PM tool (requirement -> design -> test -> runnable) and has real adopters.
- Invariant triple (INV md + frob:invariant anchor + test id) with INV001/002/005 gates.
- Entity/architecture/configuration as the intent-vs-implementation split IF paired with a
  verifier edge (obligation -> test/claim); v1 left obligations as unverified prose.
- Registry drift-lock grammar (handled_by live / deferred open ticket / duplicate_of /
  out_of_scope with caught_by) and the DENOMINATOR MANIFEST + enumerate-before-explore
  doctrine; pair-fixture (vuln fires / hardened discharges) litmus doctrine; positive control
  for every rule; ship-WARN-then-ratchet.
- Data-registry shape for dangerous operations (language, library, pattern, capability_kind,
  cwe_links, rationale, safer_alternative, severity) with the empty-cell-must-be-excused matrix.
- Obligation/discharge model for threats (conditional obligation on a capability, discharged
  by a chokepoint claim at a rung) -- but keep catalogs as data in a registry file, not Python.

CUT or DEFER (do not rebuild first): host/krb/deploy generator; six-phase boundary +
operation/saga/crash/breach until a consumer exists; policy Tier-2; compliance matrix and
privacy-policy claims; REL template families (replace by one data-driven "marker + evidence"
rule shape from 5.5); regex span location for design symbols (emit spans from the Rust
parser); hand-kept tmLanguage (generate from the grammar's keyword table); auto-injected
analyzable pack; the 37-assume boilerplate (module-specific assumes only, SYS119 semantics);
`interface=` lists (replace by `surface` selectors, 4.3B); fnmatch globs (real path globs).

DESIGN CHANGES v1 learned too late:
1. One substrate: a per-language SymbolGraph (symbols, imports, calls, effect sites, spans)
   that every rule reads; no line-level substring needles, no regex rescans, no per-rule
   walks (v1 repeatedly cut walks to one: T-1449).
2. Grammar-data ceiling: make `attr` values typed (numbers with units, idents, strings) from
   day one so markers like timeout can carry magnitude; do not encode semantics as magic attr
   strings (`code=`, `pii=`, `access=`) -- give them real fields.
3. Parser returns spans for every construct (v1 had none).
4. Rule declaration as data (section 5.5) so id registration, docs, waiver validation,
   registry rows, and fixtures cannot drift (v1 needed GATERULE001, REG010, a liveness sweep,
   WIRE001 to patch this).
5. Opt-in per node for strictness (SYS110, SYS105 pattern) with a measured migration set, not
   a hard-coded exemption list.
6. Treat the design file as multi-file from the start (v1 bolted on fragments after one line
   reached 13KB) and key everything by stable ids, not file position.
7. Name the one thing strata is: a typed spec/architecture graph (nodes, flows, claims,
   V-model) plus a code-binding layer. Everything else (threat catalogs, reliability, host)
   should be optional rule packs loaded as data, never part of the core grammar.

## 11. Phase-2 verdict

Denominator enumerated in section 0; all enumerated groups were touched, none blocked, none
left pending. Coverage is NOT uniform: unread-in-depth items are listed in section 0 (reliability
family bodies, host/krb algorithms, corpus rows, ~75 Python module bodies, strata-core
parse/mod.rs). If v2 needs exact behaviour for any of those, open the named file; the doc
anchors in each row of section 5 point at the owning module. The binding section (4) and rule
inputs (5) were checked against code for B1-B3, B5-B7, the SYS ids, and measured counts, and
against docs for the rest.
