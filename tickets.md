# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0204 -->
```yaml
id: T-0204
title: 'standing warnings triage: exports (12+ per pkg), dup 64 groups, arch 197 warns,
  perf 174'
state: queued
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
- docs/**
- tickets.md
threat: null
component: null
```
User directive 2026-07-18: the pass-line counters hide real debt -- frob-exports reports 12-253 public symbols missing from __init__.py per package (decide policy: export or demote to private, per package, no blanket waiver), frob-dup 64 duplicate groups (triage: real extraction candidates vs false pairs; feeds T-0187 tree), frob-arch 197 warnings + 123 suggestions (long-function/god-class residue post-calibration -- fix or waive with reasons), perf gate 174 violations (166 waived -- re-audit every waiver still holds after T-0161's heuristic fixes land; the 8 unwaived need real fixes). Deliverable: each family driven to a state where the summary line is HONEST -- zero unwaived findings or a written per-finding reason; no threshold-loosening without a disclosed decision. Split into child tickets per family if any single family exceeds a session of work -- this ticket is the umbrella and the accounting.

<!-- ticket:T-0254 -->
```yaml
id: T-0254
title: 'frob deploy epic: auditable, isolated, provable OS-layer deployment'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
scope:
- src/frob/**
- strata-core/**
- design/**
- docs/**
- tests/**
- Makefile
- tickets.md
threat: null
component: null
```
User mandate 2026-07-19: a frob deploy utility built into strata. The threat model: red teams compromise the one user that owns a service and nothing isolates that user -- lateral and vertical movement must be PROVABLY blocked, not hoped. The deployment sequence (idempotent install, status/health, uninstall with NO artifacts) must be auditable end to end, including an expensive opt-in VM-snapshot audit (VirtualBox) that is NOT part of make check. Scripts must tie into the model so hand edits are DETECTABLE through the strata checker, and the 'weird layer between the OS and the backend' (users, groups, units, ownership, ports) becomes provable architecture. Children: std.host OS-layer modeling -> movement-impossibility proofs + deploy script generation -> script<->model conformance gate -> VM snapshot audit harness -> real-service pilot (malmberg) remediating its awkward setup. Umbrella closes when all children close.

<!-- ticket:T-0260 -->
```yaml
id: T-0260
title: 'deploy pilot: model+generate+audit malmberg''s services, remediate the awkward
  setup'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0257
parent: T-0254
scope:
- docs/**
- tests/**
- tickets.md
threat: null
component: null
```
T-0254 child 6 (proof on reality). Apply the full chain to malmberg (the real server product from pilot P3: server_api/ingest/cloudsync/faces/backup/display + media_store): extend design/malmberg.strata with std.host (dedicated service users per component, units, ownership of media_store paths, ports), prove HOST001/HOST002 movement-impossibility or record honest waivers, generate the deploy scripts, run the conformance gate, and if a VirtualBox environment is available run the full VM snapshot audit and attach the attestation. Remediate the current awkward setup step in malmberg's docs/scripts with the generated sequence. Work happens IN THE MALMBERG REPO per the break-and-report pilot protocol (frob-side gaps come back as tickets, filed serially by the coordinator); this frob-side ticket tracks the campaign and collects the gap list. Success = malmberg installs/uninstalls via generated scripts with a green conformance gate and a documented (or executed) VM audit path.

<!-- ticket:T-0321 -->
```yaml
id: T-0321
title: 'frob daemon epic: warm shared project server (compute-once, serve-many, push-not-poll)'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
scope:
- src/frob/serve/**
- src/frob/**
- tickets.md
- docs/modules/serve.md
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/serve.md
  reason: T-0321 serve work maps to docs/modules/serve.md
  actor: logan
  at: '2026-07-20'
threat: null
component: null
```
Expands T-0177 into a long-lived per-project daemon that holds warm, incrementally-maintained state (obligation graph + per-symbol digests, test collection, coverage, dup analysis, gate results) and serves it to all clients (agents, make, MCP, CI) via single-flight execution + a content-addressed result cache. Root cause it solves (observed live over a long multi-agent session): N parallel agents each redundantly recompute the same expensive state (make core, make coverage ~5min each, frob check 114s stages, ticket sweep dup-scan ~90s) in isolated worktrees with no sharing, and background-then-stall on make coverage. Children: (a) warm graph + FS-watch incremental invalidation by digest; (b) single-flight coverage/collection keyed by source digest, shared across worktrees with identical content; (c) local unix-socket JSON-RPC query protocol; (d) frob CLI auto-proxies to the daemon if running, else in-process (make targets become thin shims); (e) subscribe/push events (coverage-fresh, graph-changed) -- the stall-killer; (f) resource leases/semaphores (coverage=1 writer). MCP becomes one frontend over the same core. See the design discussion 2026-07-19.


## Integration / replacement map (2026-07-19 -- surveyed all subcommands + queue)
The daemon is a warm SUBSTRATE under most read/analysis subcommands, not a new silo.

SUBCOMMANDS -> daemon relationship:
- Warm GRAPH QUERIES (served instantly from the warm graph, zero recompute):
  outline, map, xref, parse, graph, exports, bind, docs, stats -- become thin daemon reads.
- Warm ANALYSIS (incremental, single-flight, cached by digest): dup, arch, perf, vet.
- Warm GATE eval (touched-set, the expensive path): check, sys, test, ticket(sweep/doable/evidence).
- FRONTENDS over one core: `serve` (MCP) becomes ONE frontend; the unix-socket JSON-RPC API is
  another; the `frob` CLI proxies to the daemon if running (make targets stay thin shims).
- One-shot / orthogonal (stay plain CLI; may read from daemon): scaffold, cycle, release, mutate,
  gitlog, ack, deploy.

EXISTING TICKETS the daemon SUBSUMES or de-risks (fold in as children/deps of this epic):
- T-0177 (incremental gate eval over warm graph) -- the SEED; this epic generalizes it. SUPERSEDES.
- T-0245 (stat storms + sqlite contention on /mnt/c, 13-60x tax) -- warm in-memory state + a single
  sqlite owner eliminate the re-stat/contention entirely. SUBSUMED (or its standalone fix becomes the
  daemon's storage layer).
- T-0243 (cache.db not invalidated across frob/parser upgrades) -- daemon owns cache lifecycle
  (digest + tool-version keyed). INTEGRATED.
- T-0279 (frob:tests direction disagrees: fresh dsl parse vs stale graph cache) -- daemon keeps the
  graph always-fresh, so the entire stale-cache class disappears. INTEGRATED.
- T-0180 (vetted-library cache engine) -- daemon holds the vet cache warm. INTEGRATED.
- T-0242 (frob test -> native sys audit on touched .strata) -- daemon touched-set orchestration. CHILD.
- T-0322 (coverage --wait / single-flight) + T-0324 (parametrized evidence) -- steps toward the daemon;
  0322 is the stall-killer extractable first. T-0292/T-0298 (evidence/collection resolution) become
  trivial once collection is warm. RELATED.
- T-0178 (agentic time profiling) -- the daemon is the natural instrumentation point. RELATED.
- T-0325 (doc-drift digest graph) -- the daemon's HEADLINE query (what code/docs must update when X
  changes); only practical warm. CHILD.
- T-0323 (git merge driver for tickets.md) -- INDEPENDENT of the daemon; do first regardless.


## Client-interface design constraints (HARD requirements: no init/deinit, impossible to misuse)
The daemon is a TRANSPARENT ACCELERATOR, never a thing the user/agent manages. Non-negotiable:

1. NO lifecycle commands in the happy path. There is NO `frob daemon start` / `stop` / `init` a
   client must run first. You just run `frob <cmd>` (or `make check`, or an MCP call) and it works.
   (A `frob daemon status`/`stop` MAY exist for debugging, but nothing REQUIRES them.)
2. TRANSPARENT AUTOSTART: the first query that could benefit spawns the daemon if none is running,
   via an atomic single-instance guard (flock/socket-bind on a .frob/ lockfile) so racing clients
   resolve to exactly one daemon -- never an "already running" error, never two daemons.
3. AUTO-SHUTDOWN on idle (N min) and on project-dir removal. No orphaned processes; nothing to clean
   up. Killing the daemon at any moment loses NOTHING (all durable state is content-addressed on disk).
4. CORRECTNESS MUST NOT DEPEND ON THE DAEMON (the #1 safety invariant): a daemon-served result MUST
   equal the in-process result, always -- the daemon only makes it FASTER. Enforce with single-flight
   + digest-keyed cache + FS-watch invalidation, and a property/differential test that daemon-answer
   == cold-answer for every query type. A stale-cache-served-as-fresh is the cardinal failure -- attack
   it in review (races, watch-miss, clock skew) like a security bug.
5. TRANSPARENT FALLBACK: if the daemon is unreachable / crashed / a STALE frob VERSION (post-upgrade)
   / times out, the client SILENTLY falls back to in-process computation (and best-effort restarts a
   fresh daemon). The client NEVER hangs and NEVER surfaces a daemon error for a normal command.
6. SELF-HEALING VERSION SKEW: on a frob/parser upgrade the client detects the running daemon's version
   mismatch and the daemon self-replaces (ties to T-0243/T-0279) -- no manual restart, no stale cache.
7. ZERO required config; opt-OUT only (e.g. FROB_NO_DAEMON=1 forces in-process). Works on a fresh clone
   with no setup step -- this is exactly the 'no awkward setup step' the frob owner wants everywhere.

Acceptance: a fresh clone runs `frob check` with the daemon auto-managed end-to-end, no init/deinit
command ever issued; kill -9 the daemon mid-use -> next command transparently succeeds (respawn or
in-process); daemon-answer == cold-answer differential test green for every served query; FROB_NO_DAEMON=1
fully bypasses it with identical results.

<!-- ticket:T-0329 -->
```yaml
id: T-0329
title: 'EPIC arch multi-language: normalized code model + Rust/TypeScript/Kotlin adapters'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
scope:
- src/frob/arch/**
- src/frob/lang/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0329 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
threat: null
component: null
```
frob arch today has per-language walkers (_python.py, _cpp.py) only. To extend cleanly (not N copies of each check), introduce a NORMALIZED CODE MODEL: a language-agnostic view (module, class, function, method, param, branch, loop, call, import, override, field-access, return, raise/throw, catch) that each language adapter maps its tree-sitter grammar onto. Checks are written ONCE against the model; adapters supply per-grammar node-type maps. Then add adapters for TypeScript, Rust, Kotlin (Kotlin needs tree-sitter-kotlin added to frob.lang; ts/rust/cpp/c already parse via tree-sitter-language-pack). Language-specific checks (Rust must_use/ownership, TS any/strict-null) live in per-language extensions on top of the shared model. Acceptance: an arch check written once fires correctly across python+ts+rust+kotlin on equivalent code; Kotlin grammar wired; the existing python/cpp checks refactored onto the model with no regression. Children: normalized-model, ts-adapter, rust-adapter, kotlin-grammar+adapter.

<!-- ticket:T-0330 -->
```yaml
id: T-0330
title: EPIC arch SOLID + senior-designer checks (static proxies for real design principles)
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
scope:
- src/frob/arch/**
- src/frob/graph/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0330 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
threat: null
component: null
```
Encode what a senior software designer knows (SOLID, ArjanCodes, Logan-Smith type-driven design, logging, fallibility) as STATIC checks over parsed source -- each with a concrete, non-hacky static proxy (subjective principles get objective detectable smells). CATALOG (each becomes a child ticket, ARCH1xx family):
SRP/cohesion: LCOM4 low-cohesion class (methods partition into disjoint field-usage components); god-module (unrelated exports); mixed-concern function (I/O capability + pure compute + formatting in one body).
OCP: type-dispatch smell (N+ isinstance/type==/tag switch on one variable -> polymorphism); non-exhaustive enum match.
LSP (Liskov): override raises NotImplementedError; override signature incompatible (narrower params / different-or-wider return = variance violation); override strengthens a precondition (adds assert/raise base lacks) or weakens a postcondition; override no-ops a value-returning base method.
ISP: fat interface (ABC/Protocol/trait whose implementers stub most methods with raise NotImplementedError/pass); client using only a subset of a wide injected interface.
DIP: LAYERING CONTRACT -- a declared allowed-module-dependency graph (import-linter style), violation = a high layer importing a low/concrete module across the boundary; concrete-collaborator construction inside a method instead of injection (no DI).
Type-driven (Logan Smith): make-illegal-states-unrepresentable (bool flag + validation -> enum/newtype); primitive obsession (many raw str/int params for a domain concept); parse-dont-validate (validates then returns the same unrefined type); boolean/flag parameter (public fn bool param switching behavior -> split).
Logging (CLAUDE.md 'log everything worth logging'): unlogged error path (except/raise/return-Err with no log in it); unlogged boundary (public entry / subprocess / net / fs site with no surrounding log); print()-as-diagnostics.
Fallibility (typani Result / Rust must_use): unhandled Result (Result-returning call as a bare statement, value discarded); swallowed exception (bare except / except Exception: pass); raises a recoverable error where the signature returns T not Result[T,E]; over-broad except; re-raise losing context.
Other smells: mutable default argument; feature envy (method uses another object more than self); data clumps (same 3+ params passed together repeatedly); magic numbers/strings in logic; module dependency CYCLES; dead private code (unreferenced private symbol); deep inheritance (DIT); temporal coupling (_initialized-flag guard).
Every check names its static proxy, severity, and the ARCHxxx id; each is waivable via the ARCH001-style reasoned override (T-0289). MUST coincide with strata (see the systems epic): logging-IN-CODE is arch; observability-OF-FLOW is strata -- no overlap.

ADVERSARIAL HARDENING (2026-07-20, see docs/design/structural-linter-adversarial-hardening.md): each ARCH1xx check must ground on the RESOLVED graph not a surface/syntactic proxy (measure the LOGICAL unit -- inline single-caller private helpers via the T-0288 call graph before complexity; a helper module called only by one class IS that class); resolve re-exports transitively and FAIL CLOSED on dynamic/reflective indirection; the generated marker (T-0234) must not exempt arch. Escape hatches are BOUNDED: waiver budget/density + reason-quality + staleness meta-gate, and global threshold loosening is an AUDITED config event, never silent (per-function reasoned override only, T-0289). Coincident with the conformance-totality epic T-0341.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: architecture-check-catalog.md (tier-1 statically-checkable entries) + design-pattern-traps-corpus.md (trap hallmarks). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0331 -->
```yaml
id: T-0331
title: 'EPIC strata senior-systems checks: reliability/observability/consistency/distributed
  (complete, not hacky)'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
scope:
- src/frob/strata/**
- strata-core/**
- docs/strata/**
- tickets.md
- tests/unit/strata/
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0331 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
threat: null
component: null
```
Complete the system-design linter with what a senior systems/reliability engineer checks -- over the .strata MODEL (nodes/flows/boundaries/stores), each a real static obligation, SYS2xx/REL2xx family. CATALOG:
Reliability: TIMEOUT on every remote/cross-boundary flow (unbounded hang otherwise); RETRY must declare exponential backoff+jitter, and no retry on a non-idempotent op; IDEMPOTENCY key required on a mutating op reachable by a retryable flow (duplicate effects); CIRCUIT BREAKER / bulkhead per external dependency (extends LINT004 kill-switch); FALLBACK / graceful degradation declared for a CRITICAL dependency; HEALTH liveness+readiness on every service node; SPOF -- a node with inbound critical flows and replicas_max=1/no redundancy; BACKPRESSURE bounded intake on queues/consumers (extends LINT003 surge / LINT005 capacity).
Observability: every boundary flow emits metrics+traces+logs; CORRELATION/trace-id propagated across a flow chain (distributed tracing); golden-signal SLOs (latency/traffic/errors/saturation) + error budget declared per service.
Data/consistency: SINGLE SOURCE OF TRUTH (two nodes writing one store = hazard; extends SYS003 hub); transactional boundary on multi-write ops; MESSAGE SCHEMA VERSION on events/queues (backward-compat); exactly-once vs at-least-once declared on queues; retention/TTL on PII stores (ties T-0207).
Distributed: SYNC CALL-CHAIN DEPTH bound (cascading latency/failure; uses reachability incl. non-transitive T-0282); distributed txn across services requires saga/compensation; no shared mutable state across service boundaries; clock/ordering assumptions (T-0282).
Each is a strata surface addition (new node/flow attrs) + a checker + litmus + docs, deny-by-default with a reasoned waive channel (T-0174). COINCIDENCE with arch: strata reasons over the MODEL (flows/nodes); arch reasons over CODE (functions). Where they touch (observability, error handling), the code check BACKS the system claim via the capability/binding graph -- one obligation, checked at the right level, never duplicated.

## PROVABILITY CONSTRAINT (user, 2026-07-19 -- non-negotiable)
strata's job is NOT model-only lint. Its purpose is to PROVE the actual CODE conforms to
the .strata system design, the way a type-checker proves code matches its types. The
existing bridge is capability self-conformance (SYS100 undeclared-capability-in-code,
SYS101 declared-but-never-observed, SYS102 unmodeled-code). EVERY new systems obligation
here MUST preserve this: an obligation is satisfied ONLY by one of --
  (a) PROOF AGAINST CODE: the code is analyzed and shown to match the declared property
      (e.g. a flow declaring timeout=T must have an actual timeout arg at the real call
      site; a node declaring a fallback must have the fallback path in code; a declared
      retry-backoff must match the code's retry loop; declared observability must have the
      instrumentation). This reuses arch's code analysis + the capability/binding graph.
  (b) PROOF AGAINST MODEL: the kernel model-checks it structurally (reach/noflow/isolation).
  (c) EXPLICIT REASONED DISCHARGE: an assume/waive (T-0174) with a written reason + ticket,
      when the code cannot be statically shown -- NEVER a silent pass.
NO obligation may be satisfied by bare declaration in the .strata file alone. FOUNDATIONAL
DEPENDENCY: proof-against-code is only sound if the code analysis is sound -- an evadable
scanner (grep) makes SYS100 unsound (exec via an alias slips the proof). So T-0328
(import/binding-aware resolution) underpins this whole epic; the code<->model proof is only
as trustworthy as the resolver. This is the arch<->strata coincidence in full: arch analyzes
code STRUCTURE; strata PROVES code CONFORMS to the declared system model, USING arch's
analysis + the capability graph as the evidence.

ADVERSARIAL HARDENING (2026-07-20, see docs/design/structural-linter-adversarial-hardening.md): the anti-evasion structure is CONFORMANCE TOTALITY (epic T-0341): coverage totality (every capable module binds to a node), EXACT interface conformance (declared interface == real public surface), a PURPOSE contract (purpose carries an allowed-effect profile), binding totality (no laundering logic into an unbound file), effect conformance with opaque effects FAILING CLOSED (T-0339), and bounded/staleness-gated assumes+waivers with an un-droppable floor view. 'No obligation by bare declaration' is made TOTAL: the model cannot be dangerous-and-silent.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: system-design-corpus.md (the entries tagged strata-checkable). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0339 -->
```yaml
id: T-0339
title: 'EPIC: sound capability may-analysis -- exhaustive over static name-binding
  per language spec, fail-closed on runtime dispatch'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: null
scope:
- src/frob/vet/**
- src/frob/lang/**
- src/frob/strata/**
- tickets.md
- docs/modules/vet.md
- tests/test_vet.py
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/vet.md
  reason: T-0339 vet work maps to docs/modules/vet.md
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_vet.py
  reason: T-0339 vet work maps to tests/test_vet.py
  actor: logan
  at: '2026-07-20'
acceptance:
- text: given a per-language-spec denominator of every name-binding/aliasing/re-export
    construct that can route a call to a dangerous target (Python, TypeScript/JS,
    Rust, C, C++, Kotlin), when the capability resolver runs, then EVERY such STATIC
    construct resolves the call to its dangerous target -- verified by one litmus
    per construct, with a coverage table proving the denominator is fully covered
  evidence: []
- text: given any RUNTIME-resolved indirection the spec defines as opaque to static
    analysis (reflection, eval/exec, dynamic import, computed member access with non-constant
    key, callable retrieved from a container, function pointer from a non-constant
    expression), when it could reach a call position, then the analyzer FAILS CLOSED
    -- emits an 'opaque capability indirection' obligation that must be discharged
    by a reasoned waiver, never a silent pass
  evidence: []
- text: 'given the two guarantees above, evasion is impossible-in-the-silent-sense:
    a reviewer can point to the per-spec denominator table (static fragment complete)
    and the fail-closed obligation (dynamic fragment gated), so no code path routes
    a dangerous call to an unaccounted sink without either resolving to it or tripping
    the opaque-indirection finding'
  evidence: []
threat: elevation-of-privilege
component: null
```
User mandate (2026-07-20): 'ensure that you stop ALL methods EXHAUSTIVELY across ALL LANGUAGES of evading detection. ENSURE THAT IT IS 100% EXHAUSTIVE via LANGUAGE SPEC.' HONEST ARCHITECTURE (recorded so no one later mistakes the goal for the impossible one): a sound STATIC analyzer cannot resolve runtime dispatch (getattr/eval/reflection/dynamic-require/fn-ptr-from-data) -- Rice's theorem. So 'exhaustive' means: (1) EXHAUSTIVE-RESOLVE the DECIDABLE fragment -- enumerate FROM EACH LANGUAGE SPEC every static name-binding/aliasing/re-export/copy construct (imports, import-as, from-import[-as], star-import, local + chained + attribute rebinding, destructuring, tuple/list unpack, Rust use/use-as/pub use, C/C++ #define + using-decl + function-pointer init from a named fn + typedef'd fn-ptr, Kotlin import-as + ::ref + typealias) and resolve calls through all of them, transitively, per-scope, cycle-guarded, WITHOUT regressing shadowing soundness (a benign/param binding must stay silent); (2) FAIL CLOSED on the UNDECIDABLE fragment -- every spec-defined runtime-resolved indirection becomes an 'opaque capability indirection' obligation (fires, requires a reasoned waiver), consistent with strata's prove-or-reject philosophy (T-0290 recursion, arch-override). DELIVERY: (a) dispatch exhaustive-research to produce the per-language evasion denominator from the actual specs (the coverage denominator for acceptance 1) + the opaque-construct list (acceptance 2); (b) child tickets per language implementing the static resolver to its denominator + litmus; (c) one child for the fail-closed opaque-indirection obligation in the scanner/strata may-analysis; (d) a cross-language exhaustiveness meta-test binding each denominator entry to its litmus (fails if a construct has no fixture, like the CVE catalog drift-lock). T-0337 (Python local rebind) and T-0328 (Python import resolution) are the first two leaves. This is the 'you cannot get around it' guarantee the whole tool exists for.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: capability-evasion-taxonomy.md (every static-resolvable construct -> a resolver litmus; every runtime-opaque construct -> a fail-closed obligation). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0341 -->
```yaml
id: T-0341
title: 'EPIC: strata conformance totality -- every module binds to a node, declares
  its exact interface + purpose, effects proven against code'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: null
scope:
- src/frob/strata/**
- src/frob/vet/**
- src/frob/graph/**
- tickets.md
- docs/modules/strata.md
- tests/unit/strata/
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/strata.md
  reason: T-0341 strata work maps to docs/modules/strata.md
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0341 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
acceptance:
- text: 'COVERAGE TOTALITY (SYS-COV): every deployable/public module -- and every
    module the binding-aware scanner finds ANY capability in -- must bind to exactly
    one strata node; unbound-but-capable code is a hard failure (the model cannot
    omit dangerous code)'
  evidence: []
- text: 'INTERFACE CONFORMANCE (exact): a node''s declared interface must EQUAL the
    code''s actual public surface -- an undeclared public export fails, and a declared-but-absent
    symbol fails; every module is forced to declare its interface and keep it in lockstep
    with the code'
  evidence: []
- text: 'PURPOSE CONTRACT: every node declares a PURPOSE carrying an allowed-effect
    profile; an effect outside the purpose''s profile (e.g. a network effect in a
    declared logging/pure purpose) fires and needs a reasoned discharge -- purpose
    is a typed constraint, not a comment'
  evidence: []
- text: 'BINDING TOTALITY + EFFECT CONFORMANCE: code<->node binding is a TOTAL function
    over capable code (no laundering logic into an unbound file); the exhaustive binding-aware
    scanner''s extracted effect set must be a subset of what the node declares, declared
    >= actual, with opaque/unresolvable effects failing closed (T-0339)'
  evidence: []
- text: 'BOUNDED ESCAPE HATCHES + GATED CONFIG: waivers/assumes are counted, reason-required,
    staleness-dated, and budget-limited (waive-everything is itself a smell); baseline-view
    and threshold loosening is an audited event, never silent'
  evidence: []
threat: elevation-of-privilege
component: null
```
The user asked (2026-07-20): 'what mechanisms enforce conformance to the .strata file? Do we force every module to declare its purpose and interface?' -- and to harden it adversarially. Design north-star: docs/design/structural-linter-adversarial-hardening.md. Today _code_binding.py (bind_code/ConformanceReport/check_import_conformance) and _effects.py::check_capability_conformance exist, and T-0331 already mandates 'NO obligation satisfied by bare declaration' -- but conformance is NOT TOTAL, which is the evasion surface: (1) un-modeled modules escape all obligations; (2) a node can declare a partial interface while the code exports more; (3) nothing binds a module's PURPOSE to an allowed-effect profile; (4) binding need not be total, so logic can be laundered into an unbound file. This epic closes those into the five acceptance criteria above (SYS-COV coverage totality, exact interface conformance, purpose contract, binding totality + effect conformance, bounded escape hatches + gated config), each a child ticket. Soundness rests entirely on the exhaustive binding-aware scanner (T-0328/T-0337/T-0339) -- this epic is the conformance layer ON TOP of that foundation. Coincident with the arch epic (T-0330) and strata-systems epic (T-0331); this is the 'the model cannot lie about the code' guarantee made total.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: the conformance mechanisms in structural-linter-adversarial-hardening.md (coverage/interface/purpose/binding/effect totality). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0346 -->
```yaml
id: T-0346
title: 'EPIC: unified design-knowledge registry -- single source of truth, per-entry
  disposition, no prose-only or split-across-files misses'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
scope:
- docs/design/**
- src/frob/strata/**
- src/frob/arch/**
- tickets.md
- tests/unit/strata/
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0346 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
acceptance:
- text: every item across ALL corpora (design patterns, arch checks, traps, system-design,
    capability-evasion, security/CWE, compliance, secrets, PII, supply-chain) has
    a stable canonical id in ONE machine-readable registry (docs/design/registry/*.yaml
    or equivalent); the prose corpus docs become human elaboration that REFERENCES
    registry ids, never the sole home of an entry -- a reconciliation test fails if
    any prose entry (a table row / named item in a corpus doc) has no registry id
    (a prose-only miss) or if two docs describe the same item under different unlinked
    ids (a split-across-files miss)
  evidence: []
- text: 'TRUE exhaustiveness: enumerations that were bulk-skipped or census-only get
    COMPLETED to per-entry granularity with an individual disposition each -- CWE-1000
    full (~900+, each: has-design-precondition->checkable / no-kernel-concept->out-of-scope-naming-the-missing-concept
    / duplicate-of-cataloged-id), AWS pattern catalog, the detector rule sets counted
    only as census (gitleaks/trufflehog/GitHub-partner-patterns). ''seems like spam/redundant''
    is NOT a valid skip; redundant-with-X is a disposition (duplicate-of X), not an
    omission'
  evidence: []
- text: 'every registry entry carries a DISPOSITION: addressed-by-check(s) <ids> |
    reasoned-deferral(advisory/not-checkable, reason) | duplicate-of <id> | out-of-scope(named-missing-concept).
    T-0343''s exhaustiveness drift-lock binds to this registry and fails if ANY entry
    lacks a disposition or an addressed entry''s check vanishes -- so an implementing
    ticket provably addresses EVERYTHING'
  evidence: []
threat: null
component: null
```
User critique (2026-07-20): the corpora hedged where the mandate is to EXHAUST -- e.g. security-corpus skipped CWE-1000 as 'repo spam' when the intent is to enumerate ALL ~900, categorize each, and reason mitigation per entry; and information split across 10 docs/design/*.md files means an item can exist in one file's prose but be absent from the enforceable denominator ('miss split across two files'). This epic makes the corpus a REGISTRY, not a reading list: (1) a single canonical machine-readable registry aggregating every corpus manifest with stable ids + cross-refs (pattern<->trap<->evasion<->mitigation linked by id); (2) a reconciliation/consolidation pass that de-dups cross-file and flags any prose-only entry; (3) completion of the bulk-skipped enumerations to per-entry disposition; (4) T-0343 (exhaustiveness drift-lock) bound to the registry with a mandatory per-entry disposition. Governs T-0330/331/332/339/341/343 and all the corpus docs. The corpora already emit '## DENOMINATOR MANIFEST' sections (per-doc TOTAL); this epic unifies them into one registry and closes the 'seems like spam so I skipped it' and 'split across two files' gaps permanently.

<!-- ticket:T-0380 -->
```yaml
id: T-0380
title: 'vet: extend binding-aware resolution into CVE fingerprint scanning'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- ''
- T-0377
- T-0378
- T-0379
parent: T-0376
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
threat: null
component: null
```
_scan_file_fingerprints (CVE matching) is lexical needle-matching for EVERY language including Python -- a renamed import defeats a fingerprint even where capability scanning is binding-aware. Reuse the binding tables built for capability resolution (Python + the new TS/Rust/C-C++ tables) to resolve aliases before fingerprint matching for all languages. Acceptance: an aliased import that would evade a lexical fingerprint match is still caught; adversarial test per language.

<!-- ticket:T-0391 -->
```yaml
id: T-0391
title: 'registry reconciliation: arch-checks (311 entries)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/gates/
- docs/design/registry/arch-checks.yaml
threat: null
component: null
```
Reconcile docs/design/registry/arch-checks.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0393 -->
```yaml
id: T-0393
title: 'advisories: triage abstraction-opportunity near-dup families'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
scope:
- src/frob/
threat: null
component: null
```
Triage the 37 frob-arch abstraction-opportunity advisories: for each genuine near-duplicate or specific-signature family, either extract the real shared code into one home, or add an explicit reason-note accepting the duplication. Acceptance: frob check arch advisories for abstraction-opportunity reduced to zero unresolved (each is either fixed or reason-noted).

<!-- ticket:T-0394 -->
```yaml
id: T-0394
title: 'advisories: deep-nesting refactor (2 findings)'
state: queued
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
scope:
- src/frob/
threat: null
component: null
```
Address the 2 frob-arch deep-nesting advisories: refactor to reduce nesting depth, or add an explicit reason-note if the nesting is justified. Acceptance: both findings resolved (fixed or reason-noted).

<!-- ticket:T-0395 -->
```yaml
id: T-0395
title: 'advisories: large-file residue after calibrated thresholds (T-0373)'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0373
parent: T-0376
scope:
- src/frob/
threat: null
component: null
```
After T-0373 re-thresholds frob-arch large-file to 800 lines / 60 (function), address the residue that still exceeds 800 lines among the 34 large-file advisories: real module splits, or accepted-with-reason for files that don't decompose cleanly. Acceptance: frob check arch large-file advisories at the calibrated threshold reduced to zero unresolved.

<!-- ticket:T-0397 -->
```yaml
id: T-0397
title: 'AUDIT REMEDIATION EPIC: North-Star integrity -- every green must be earned'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
scope:
- src/frob/
threat: null
component: null
```
Full-repo pessimistic capability audit (2026-07-20, 7 read-only auditors). North-Star: if frob check / a ticket-close / a strata proof passes, the thing it claims must ACTUALLY hold. The audit found the North-Star is violated in concrete ways across subsystems. Each subsystem audit gets an umbrella child holding its full findings table; each HIGH finding gets an actionable child. Findings files live in the audit run; this epic is the durable tracked home so the audit itself does not become an orphaned document (the exact failure mode that motivated it). Consolidation in progress as the 7 auditors land: tickets/testing (evidence integrity), strata (vacuous proofs), graph/edges, gates-accounting, gates-quality/security, vet (lexical resolution), lang/check/docs.

<!-- ticket:T-0399 -->
```yaml
id: T-0399
title: 'AUDIT: green must claim quality -- promote quality gates from WARN to blocking
  (docs/audits/gates-quality.md)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
scope:
- src/frob/gates/
- src/frob/app/config.py
- frob.toml
threat: null
component: null
```
See docs/audits/gates-quality.md. HIGH: entire quality surface is non-blocking (PERF/PII010/SEC110/ARCH001/DUP/lower-secrets are WARN, frob check exits 0 on them) -- green makes NO quality claim; DUP fails open (default-off AND no-op without natives); frob:secret-fake suppresses real secrets with no accountability/reason/ledger. RIGHT-WAY fix: decide per rule which are error-tier (and default DUP on / fail-closed when natives missing); give secret suppression the same reasoned-waiver accountability as frob:waive. Expect the build to red -- that red is honest. Then re-audit until empty. MED/LOW in the doc.

<!-- ticket:T-0417 -->
```yaml
id: T-0417
title: 'Evidence integrity round 2: close still not converged -- empty-scope bypass,
  no re-verify-at-close, vacuous-test passes (docs/audits/tickets-testing-round2.md)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0398
scope:
- src/frob/tickets/
- src/frob/gates/
- src/frob/app/ticket_runner.py
- src/frob/testing/
threat: null
component: null
```
Convergence re-audit of the tickets/testing subsystem AFTER T-0398 landed (docs/audits/tickets-testing-round2.md): D-01..D-12 genuinely fixed EXCEPT the subsystem is NOT converged -- 3 new HIGH CLI-reachable bypasses (no --force needed): N-01 omitting --scope skips the D-02 covers_scope binding entirely (a code ticket with no scope closes on any passing evidence); N-02 frob ticket close does NOT re-run the evidence tests -- it trusts the pass status recorded at evidence-record time, so a test recorded green then later broken still closes (TOCTOU); N-03/N-04 pass == pytest exit 0, so a VACUOUS test (asserts nothing) or a self-scoped no-op test satisfies the gate -- the exact vacuous-test class the review loop keeps catching. Plus D-03 is only a 3-char floor (weak done-report substance) and D-10/D-12 unchanged. FIX the RIGHT way: (N-01) fail-CLOSED on empty scope for CODE-kind tickets (a code ticket MUST declare scope + have covering evidence); (N-02) RE-VERIFY evidence at close the way land already does (re-run the evidence tests at close, not just trust record-time status); (N-03/04) detect vacuous/no-assertion evidence tests (a test that passes but asserts nothing / never exercises the scope symbol should not count -- reuse the covers_scope graph binding to require the evidence actually reaches a touched symbol, and consider an assertion-presence check); strengthen D-03 beyond a char floor (require the real sections). Re-audit again after -- converged only when a pessimistic pass finds nothing. Full findings + repros: docs/audits/tickets-testing-round2.md. QUEUED behind T-0343/T-0415 (gates/app overlap) to avoid merge conflict.

<!-- ticket:T-0437 -->
```yaml
id: T-0437
title: 'Doc-pointer resolution gate: every doc reference of a RECOGNIZED resolvable
  shape must resolve (hardened closed-set, not fuzzy ''seems to point'')'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0435
scope:
- src/frob/gates/
- src/frob/graph/
- docs/
- frob.toml
threat: null
component: null
```
User (2026-07-20): account for anything that looks like a tool usage/guide, and any documentation that SEEMS to point to something -- and HARDEN the wishy-washy part. THE HARDENING: do not try to detect fuzzy "seems to point to X" intent (unhardenable, high FP). Instead define a CLOSED SET of RECOGNIZED, RESOLVABLE POINTER SHAPES and only fire when a pointer of a known shape targets something that does NOT exist. This converts "seems to point" into a mechanical, resolvable check with a naturally-low FP rate (an unrecognized shape is simply not checked). POINTER KINDS (each detectable + resolvable against the real project): (1) FILE/PATH -- a repo-relative path (src/frob/foo.py, docs/bar.md, frob.toml) mentioned in a code span/block/link must EXIST; (2) CLI INVOCATION / TOOL-GUIDE -- `<project-cli> <subcommand>` and `--flag`/`-x` options against the projects real argparse/command source (frob is one instance; per-project via a configurable command source) -- a nonexistent subcommand or flag is stale; (3) CONFIG REFERENCE -- a `[section]` or `[section].key` or a frob.toml/pyproject/Cargo key referenced must be a REAL config key of that manifest/schema; (4) CODE SYMBOL -- a dotted path / import / use (module.Class.method, from X import Y, use crate::x) resolves in the graph against the projects manifest-derived namespaces (see T-0436: Rust workspace subcrates, pyproject/package.json package names != dir names; external namespaces skipped); (5) DOC-ANCHOR LINK -- a docs/x.md#anchor (or a frob:doc/frob:describes anchor target) must exist. SCOPE: inline code spans AND fenced code blocks AND markdown links AND tool-guide prose ("run `X`", "add `[section]` to frob.toml", "the `--foo` flag", "see `docs/bar.md`"). CONSERVATISM: only a pointer matching a recognized shape whose target is DEFINITIVELY resolvable-or-refutable is checked; an unrecognized/ambiguous token is NOT flagged (the hardening). PROMINENTLY WAIVABLE (frob:waive) for intentional external/illustrative/future-facing pointers. Ships per-project (T-0406), all languages. T-0436 (unbound/stale CODE BLOCKS) is ONE INSTANCE of this; this ticket is the general doc-pointer-resolution gate (the north-star doc-drift check, cf T-0325). Acceptance: a doc mentioning `src/frob/gone.py` (nonexistent) flagged; `frob edit`/`--nonexistent-flag` flagged; a `[bogus.section]` frob.toml reference flagged; a `docs/missing.md#x` link flagged; a real path/command/flag/symbol/anchor passes; an unrecognized prose token NOT flagged; external pointers waivable. Run on frobs own docs, report FP rate, disposition honestly.

<!-- ticket:T-0440 -->
```yaml
id: T-0440
title: 'strata model debt: deploy/serve/mutate swept into coarse utility-hub node,
  not modeled as distinct capabilities with own effects/threat surface'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: null
scope:
- design/frob.strata
- docs/strata/
- tests/system/test_frob_self_model.py
- tests/unit/strata/test_effects.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'T-0440 tests/** is chronically over-broad per doable''s flag. Narrowing
    to

    the specific strata self-model + capability-conformance test files this

    node-split ticket actually touches: tests/system/test_frob_self_model.py

    (node/flow/claim counts + frob:tests directives for new flows) and

    tests/unit/strata/test_effects.py (capability-conformance coverage for

    the new deploy/serve/mutate nodes), rather than holding a lease across

    the entire tests/ tree.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: 'T-0440 tests/** is chronically over-broad per doable''s flag. Narrowing
    to

    the specific strata self-model + capability-conformance test files this

    node-split ticket actually touches: tests/system/test_frob_self_model.py

    (node/flow/claim counts + frob:tests directives for new flows) and

    tests/unit/strata/test_effects.py (capability-conformance coverage for

    the new deploy/serve/mutate nodes), rather than holding a lease across

    the entire tests/ tree.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: 'T-0440 tests/** is chronically over-broad per doable''s flag. Narrowing
    to

    the specific strata self-model + capability-conformance test files this

    node-split ticket actually touches: tests/system/test_frob_self_model.py

    (node/flow/claim counts + frob:tests directives for new flows) and

    tests/unit/strata/test_effects.py (capability-conformance coverage for

    the new deploy/serve/mutate nodes), rather than holding a lease across

    the entire tests/ tree.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_deploy_declares_every_real_effect_it_exercises
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_mutate_declares_every_real_effect_it_exercises
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
threat: null
component: null
```
## Done report

T-0440: deploy/serve/mutate split off core's former utility-hub node into
three standalone strata nodes with their own real, measured effects/kill
switches/edges, closing the modeling-debt this ticket described.

Measurement method (mirrors the file's own established discipline):
frob.strata._effects._line_effects (the same net/fs/exec scanner
check_capability_conformance itself uses) and
frob.vet._capability._scan_directory_capabilities run directly against
src/frob/deploy/**, src/frob/serve/**, src/frob/mutate/** to get ground
truth before writing any `may` declaration.

Findings:
- mutate: real fs (write_text)/fs-read (read_text)/exec
  (guarded_subprocess_run) -- all three genuine, all already routed
  through the real FROB_DISABLE_EXEC kill switch (T-0803's
  ExecDisabled-abort behavior, not a mis-scored "killed" mutant).
  Declared `may "exec"`/`"fs"`/`"fs-read"` + `attr
  flag=frob_check_exec_kill_switch`.
- deploy: real fs (open("rb") in _drift.py, per the registry_model/fleet
  precedent that maps to bare "fs" not "fs-write")/fs-read
  (read_text)/exec (_vm_runner.py's guarded_subprocess_run, real kill
  switch). The scanner ALSO flagged "eval" here -- verified by hand as a
  T-0151-class false positive: the needle `eval(` matches
  `_conform.py::_mutation_for_eval`'s own Python FUNCTION NAME, not a
  call to eval()/exec(); direct grep of src/frob/deploy/** confirms zero
  real eval/exec-builtin calls. NOT declared (an unfalsifiable claim
  SYS101 exists to catch), matching gates' own precedent for the
  analogous compile()-vs-re.compile() false positive.
- serve: measured ZERO net/fs/exec/eval effects of its own by BOTH
  scanners. Every effect a `frob serve` request performs (cache reads,
  git subprocess calls, gate/graph/ticket reads) is delegated to
  core/gates/graphlang/tickets_ledger code, modeled as flow edges, not
  serve's own capability. Declared as a genuinely zero-`may` node (same
  shape as the `registry` boundary node, minus foreign clearance) -- the
  MCP stdio transport boundary itself (an external agent process talking
  to this component directly) is the real, previously-undeclared surface
  this split makes visible, documented in prose since the grammar has no
  first-class "external client" marker beyond node/flow/boundary.

Added 10 flow edges (cli -> deploy/mutate/serve inbound;
deploy -> stratamod/core, mutate -> core, serve ->
core/gates/graphlang/tickets_ledger outbound) and 2 THREAT003 `assume`
discharge claims (weakness:CWE-78:deploy, weakness:CWE-78:mutate --
mutate declares no `may "eval"` so no CWE-94; deploy same). serve drags
in zero obligations (no `may` atoms).

DISCLOSED PRE-EXISTING DEBT (found while re-measuring, not introduced by
this ticket): tests/system/test_frob_self_model.py's node/flow/claim
counts (10/27/23) were ALREADY stale against the pre-T-0440 tree
(measured directly: 12/32/24) before this ticket touched them --
specifically, T-0707's `fleet` node has declared `may "exec"` (dragging a
weakness:CWE-78:fleet discharge claim) since before this ticket, and that
claim was never folded into this docstring's running tally. Both tests
in that file were RED on main prior to this ticket (verified by
temporarily swapping in the original design/frob.strata against the
original test file and running pytest: test_parses_and_elaborates and
test_every_claim_proves both failed). This ticket's edits fix both the
pre-existing fleet gap and the new T-0440 counts together in one
re-measurement pass (10/27/23 -> 15/42/26), since both live in the same
test file already in scope. No new ticket filed for this -- it is
disclosed here rather than fixed silently, and the fix is a strict
re-measurement (both counts only ever moved toward the real, currently
elaborated model, never fudged to make an assertion pass).

Docs: docs/strata/roadmap.md's D7 component-count paragraph updated
(8 -> 13 components, noting T-0707's registry_model/fleet and this
ticket's deploy/serve/mutate split, and the narrower dup+frob-core
package list).

No new ticket filed for the T-0151-class eval-needle-vs-function-name
scanner false positive on _conform.py -- the original T-0150 Done report
already filed the general scanner-precision ticket this specific
instance falls under; disposed here the same way gates' own
`compile(`-vs-`re.compile(` precedent was disposed (documented,
not-declared, not re-filed).

Gates: chunked `frob check --only <stage>` run for every stage group
(lint, static, gates-fast, gates-native, gates-security), each 0 errors
attributable to this ticket. `frob ticket sweep T-0440` re-run twice
mid-session to keep PRE001 (pre-work-sweep staleness) fresh against
edits; not a content finding. `git diff main --diff-filter=D --stat` is
empty (no out-of-scope deletions).

Scope narrowed at the start per dispatch instructions: tests/** ->
tests/system/test_frob_self_model.py + tests/unit/strata/test_effects.py
(frob ticket scope --reason-file, recorded in the ticket's scope_changes
audit trail).

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_deploy_declares_every_real_effect_it_exercises` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_mutate_declares_every_real_effect_it_exercises` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 1204 warning(s), 210 waived

<!-- ticket:T-0441 -->
```yaml
id: T-0441
title: 'frob fmt: auto-wrap over-length frob: directive comment lines via T-0286 continuation
  so ruff E501 never fires on waive reasons'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/
- src/frob/app/
- docs/
threat: null
component: null
```
Friction hit by hand 2026-07-20: a `frob:waive` reason long enough to be
useful overflows ruff's E501, so `frob check` (ruff) and the waive author
fight -- you truncate the reason (losing the explanation) or hand-wrap it
with the T-0286 trailing-backslash continuation. frob owns the continuation
syntax, so frob should own the wrapping.

Design:
- `frob fmt` (or `frob check --fix-directives`) detects any `frob:<verb>`
  directive comment line exceeding the project's configured line length
  (read the real limit from ruff/pyproject, per-language for TS/Rust/C++
  too, not a hardcoded 88) and rewrites it into a T-0286 continuation run:
  break at a word boundary before the limit, end each physical line with
  ` \`, keep every physical line under the limit, and preserve the exact
  logical directive text (round-trip: fold(wrap(x)) == x).
- Idempotent: re-running on already-wrapped directives is a no-op.
- When run inside `frob check` without the fix flag, emit a remediation
  hint on the offending line: "directive line over NN cols; run `frob fmt`
  to wrap" -- same self-remedying-message contract as every other gate.
- Cover comment prefixes for all supported languages (`#`, `//`), and the
  continuation-line prefix each language needs so the fold still parses.
- Tests: property test that wrap then fold is identity on arbitrary
  directive text; fixtures per language; an idempotency test.

REFINEMENT (user): frob fmt must be a CANONICAL-FORM NORMALIZER, not a
one-way wrapper -- it needs DEDENTING / UN-WRAPPING capability too. If a
directive was previously split across continuation lines (trailing `\`) but
now fits within the configured limit on a single line -- because the reason
text was shortened, the limit was raised, or it was split unnecessarily in
the first place -- frob fmt must JOIN it back into one physical line (strip
the `\` continuations and the continuation-line comment prefixes, fold the
text, re-emit as a single line) rather than leaving a needlessly-split
directive. Canonical form = the FEWEST physical lines that keep every line
under the limit: one line when it fits, wrapped only as far as necessary.
So the operation is idempotent in BOTH directions: fmt(wrapped-but-fits) ->
single line; fmt(single-line-too-long) -> minimally wrapped; fmt(already-
canonical) -> no-op. Add tests for the un-wrap direction: a 3-line
continuation whose joined form fits collapses to 1 line; a 2-line split
where only the first line was over-long re-wraps to the minimal split;
round-trip join(split(x)) == canonical(x). This shares the fold logic with
T-0286's `_fold_continuations` (reuse, do not duplicate) -- fmt's job is to
choose the canonical physical-line layout, folding to normalize then
re-splitting only where a physical line would exceed the limit.

<!-- ticket:T-0525 -->
```yaml
id: T-0525
title: COV006 waiver granularity is file-scoped, not symbol-scoped -- can silently
  over-waive
state: queued
kind: bug
origin: agent
created: '2026-07-21'
priority: low
parent: null
scope:
- src/frob/gates/__init__.py
threat: null
component: null
```
Discovered while working T-0516: COV006 Violation objects carry no symref (file=test_file, line=0), so _match_waiver falls back to file-level matching for a frob:waive COV006 comment anywhere in that file -- ANY single COV006 waiver in a test file silently suppresses EVERY COV006 finding in that file, not just the one it was written next to. Verified directly: adding one waiver comment near one test in tests/test_gates.py suppressed all 7 COV006 findings then present in that file, including unrelated ones that were NOT sound (an import-alias false-positive that needed a real fix, not a waiver). Consider giving COV006 violations a symref (the test's own qualname) so _match_waiver can do symbol-exact matching the way most other rules do, instead of falling back to file-scope for a rule that very plausibly has multiple independent findings per file.

<!-- ticket:T-0542 -->
```yaml
id: T-0542
title: 'gates: COV002 satisfied by ANY open ticket whose scope glob covers the file
  (B10)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0403
scope:
- src/frob/gates/
threat: null
component: null
```
docs/audits/gates-accounting.md B10. _cov002 uses _open_scopes = every open ticket's scope glob, matched via _scope_covers against ANY of them. One broad-scope open ticket (e.g. src/frob/**) makes every changed symbol under it accounted for regardless of relation to that ticket. Fix direction: prefer the ACTIVE ticket's own scope first, and require a narrower/more-specific glob match (or an explicit frob:ticket edge) when multiple open tickets' scopes could cover the same file, rather than accepting the first match found.

<!-- ticket:T-0584 -->
```yaml
id: T-0584
title: 'PRE001 catch-22 on slow mounts: sweep needs a timeout/partial-state or async
  design (T-0355 item 2)'
state: queued
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
threat: null
component: null
```
found while working T-0355 (deliberately split out, item 2 of that ticket's original 3-item report): editing a ticket's scope after start demands a re-sweep before PRE001 is satisfiable, and frob ticket sweep's dup+xref pass is a synchronous full-scope scan -- on a slow mount (WSL /mnt/c, network share) that scan itself can be slow enough that the ticket can never get back into a checkable state within a reasonable session. T-0474 already backgrounds the sweep at frob ticket start time, but frob ticket sweep (the always-available resweep path used after a scope edit) is still fully synchronous by design (see its docstring: 'the always-available, always-synchronous way to record it'), and PRE001 itself only ever compares against a fully-completed digest -- there is no partial-sweep-ok state. This needs an actual design decision before implementation (a timeout + partial-sweep-ok ticket state that prework_gate treats as provisionally clean, vs. making frob ticket sweep itself background-and-poll like start), not a mechanical port of an existing fix, so it was NOT implemented as part of T-0355 (items 1 and 3 of that ticket were: clean SIGINT message in __main__.py, and confirming scope_digest is already content-only/checkout-portable).

<!-- ticket:T-0588 -->
```yaml
id: T-0588
title: 'Resolve TEST014 name-collision cases: disambiguate or tighten TEST001 credit'
state: queued
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
threat: null
component: null
```
T-0547 added TEST014 (WARN) to surface every case where _inferred_unit_cases's naming-convention fallback ambiguously credits two DIFFERENT files' same-leaf-name public symbols off the same collected test id(s) (docs/audits/gates-accounting.md B6). It deliberately does NOT withdraw TEST001 credit: a compat survey against this repo (T-0547's Done report) found a blanket path/module-correlation requirement breaks ~100% of convention-fallback matches here (96/81 depending on heuristic), since tests/ does not mirror src/frob/<pkg>/ layout. But the survey ALSO found 5 real leaf-name collision groups in this repo TODAY sharing convention-matched tests (main, format, as_text, as_json, run) -- TEST014 will fire WARN for each until resolved. This ticket is to actually resolve those 5 (add explicit frob:tests edges to disambiguate, or accept the WARN permanently via frob:waive with a reason), and to decide/design a general per-symbol tightening path now that real examples exist to test any proposed rule against (e.g. requiring the matched test's own module path to appear as a substring of the target's qualname, or promoting TEST014 to ERROR once explicit edges are added to eliminate ambiguity repo-wide).

TEST-pool triage (T-draft-edbf1e26, 2026-07-22) re-measured `frob check --only test` against current main+T-0583: 244 TEST014 warnings remain, all pairwise fan-out from only 4 (not 5 -- `main` no longer collides) distinct leaf-name groups: `run` (171 pairs, 20 app/*_runner.py `run(cfg)` entrypoints all convention-matched by the same frob-core test), `as_json`/`as_text` (36 pairs each), `format` (1 pair). None resolved this pass -- disambiguating 20 runner modules' TEST001 credit is exactly this ticket's own scope and outsized for a triage pass; left queued with this refreshed count so the next attempt does not need to re-derive it.

<!-- ticket:T-0589 -->
```yaml
id: T-0589
title: Tie TEST001 credit to real per-symbol coverage (promote TEST005/TEST015, cross-cutting)
state: queued
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
threat: null
component: null
```
T-0548 added TEST015 (WARN) reusing T-0549's existing _has_assertion_evidence heuristic to surface a public symbol whose ONLY TEST001 credit comes from a test with no assertion-shaped construct at all (docs/audits/gates-accounting.md B1's def-myfunc-pass repro). It deliberately does NOT change what TEST001 itself blocks on. This ticket is the actual cross-cutting fix the audit asked for: tie TEST001 credit to nonzero per-symbol branch coverage (frob.gates._coverage.CoverageData.symbol_branch, already computed for TEST005) or promote TEST005 to ERROR -- either requires touching TEST002/003/004/005/009's severities and interactions together, plus reconciling with the legacy-adoption WARN campaign frob.toml already documents (see its own comments), which is why it was split out rather than attempted inside T-0548. Concretely: decide whether TEST001 should require symbol_branch[record.symref] > 0 in addition to a name/edge match (requires wiring CoverageData into _test001_002, which today only sees tests: CollectedTests, not coverage), survey how many currently-green symbols would flip red (mirroring T-0547/T-0556's compat-survey precedent in this same audit pass), and land the sound subset.

TEST-pool triage (T-draft-edbf1e26, 2026-07-22): re-measured `frob check --only test` -- TEST005 and TEST015 both currently report 0 findings against this tree (fixture-pinned to `main`+T-0583, no coverage stamp present so a stale/absent stamp masking a real regression cannot be ruled out; re-verify once T-0586's committed-lock wiring lands). No genuine findings to disposition in this pass for either bucket.

<!-- ticket:T-0590 -->
```yaml
id: T-0590
title: 'COV002 grace-window regression: closed-ticket edges lose coverage across sequential
  same-worktree ticket closes'
state: queued
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
threat: null
component: null
```
Discovered incidentally while closing T-0556 (unrelated ticket) in a worktree that had already closed T-0567/T-0545/T-0552/T-0547 earlier in the same branch: symbols touched by T-0545/T-0552 (e.g. src/frob/gates/_coverage.py::stamp_coverage, src/frob/gates/__init__.py::_test005/test_gate/_edge_has_execution_evidence/_KNOWN_GATE_RULES/_COVERAGE_LOCK_REL) started failing COV002 again -- 'changed with no frob:ticket edge to an open ticket' -- even though each carries a valid frob:ticket T-0545/T-0552 directive and both tickets' closures are still part of the same uncommitted diff against main (git diff main --stat still shows all the intervening commits). This reproduces with a bare frob check (no --ticket override), so it is not scoped to T-0556's own diff content -- it appeared sometime between T-0552's own clean check (frob check --ticket T-0552 showed 0 COV errors right after closing it) and starting T-0556's ticket workflow (multiple frob ticket scope/sweep operations on tickets.md in between). Hypothesis: _bound_to_open_ticket's grace-window hunk-matching (docs/audits or __init__.py:1917 _bound_to_open_ticket docstring, T-0214/T-0320) depends on a ticket's DONE-transition marker line falling within a single git diff hunk against main; repeated tickets.md rewrites by later ticket operations (scope changes, sweeps, done-report writes for OTHER tickets) can split/relocate that hunk so an EARLIER ticket's own close marker no longer registers as 'in this diff's tickets.md hunk' even though the closure commit is still, in aggregate, part of the diff vs main. Needs investigation: reproduce minimally (two sequential ticket closes in one branch, then a third ticket's ledger operations), confirm the hunk-boundary hypothesis, and either make the grace window robust to intervening unrelated tickets.md hunks or make COV002's message clearer that this is a hunk-shape artifact, not a real missing edge. Related: docs/guides/agent-playbook.md section 10b's existing multi-ticket-worktree warnings (about ledger finalization) -- this is a parallel failure mode in the SAME class of hazard, but for COV002 rather than the Done-report/close ledger writes.

<!-- ticket:T-0596 -->
```yaml
id: T-0596
title: 'gate:PERF: resolve 11 unwaived findings (9x PERF004 sort-in-loop, 2x PERF005
  unprovable recursion)'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_coverage.py
- src/frob/gates/_registry_exhaustiveness.py
- src/frob/strata/_cve_fingerprint.py
- src/frob/tickets/_brief.py
- src/frob/__main__.py
- src/frob/gates/_docblocks.py
threat: null
component: null
```
gate:PERF currently reports 0 errors, 11 warnings, 39 waived (measured 2026-07-22). The 11 unwaived are: 9x PERF004 sorted()/.sort() in a loop (src/frob/gates/__init__.py:1183,2914,4279,4610,4695; src/frob/gates/_coverage.py:545; src/frob/gates/_registry_exhaustiveness.py:405; src/frob/strata/_cve_fingerprint.py:518; src/frob/tickets/_brief.py:118) and 2x PERF005 no-provable-termination recursion (src/frob/__main__.py:92 _collect_option_strings; src/frob/gates/_docblocks.py:386 _subparser_tree). For each PERF004: hoist the sort out of the loop, switch to a sorted container, or waive with a genuine per-site reason (the existing 39 waived findings on this same gate show the expected reason shape -- 'runs once after the loop', 'own iterable not repeated', etc; do not copy a reason that does not actually hold for the new site). For each PERF005: add a frob:invariant terminates reason=... measure=... annotation with a real termination measure, or restructure. Acceptance: gate:PERF summary line reports 0 unwaived findings (fixed or waived-with-reason), no threshold loosened without a disclosed decision.

<!-- ticket:T-0597 -->
```yaml
id: T-0597
title: 'frob-dup: triage duplicate-block report (75 groups, 112 waived) into extraction
  vs accepted-false-pair'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
scope:
- src/frob/**
- tests/**
threat: null
component: null
```
frob-dup currently reports 75 duplicate groups (112 waived), measured 2026-07-22 (was 64 groups at T-0204 filing, has grown). This is distinct from the frob-arch abstraction-opportunity advisories already covered by T-0393 -- frob-dup is the raw clone-detector report over both src/frob/** and tests/**, not the arch gate's near-dup-family suggestions. For each of the 75 groups: if it is a genuine extraction candidate (shared logic that should live in one home), extract it; if it is a false pair (coincidental structural similarity, e.g. parallel test scaffolding), waive it with an honest per-group reason. Acceptance: frob-dup summary line reports 0 unwaived groups (fixed or waived-with-reason), no threshold loosened without a disclosed decision.

<!-- ticket:T-0600 -->
```yaml
id: T-0600
title: 'frob-exports triage: src/frob/gates, src/frob/graph, src/frob/process/parsers,
  src/frob/registry (14 symbols across 4 packages)'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
scope:
- src/frob/gates/**
- src/frob/graph/**
- src/frob/process/parsers/**
- src/frob/registry/**
threat: null
component: null
```
frob-exports currently reports (measured 2026-07-22): src/frob/gates 9 public symbols missing from __init__.py, src/frob/graph 2, src/frob/process/parsers 1, src/frob/registry 2 (14 total). For each symbol, decide per-symbol: export it from the package's __init__.py, or demote it to private (leading underscore) if it should not be public API. No blanket waiver -- each symbol gets an explicit decision. Acceptance: frob-exports(src/frob/gates), frob-exports(src/frob/graph), frob-exports(src/frob/process/parsers), frob-exports(src/frob/registry) summary lines report 0 unresolved findings (exported, demoted, or waived-with-reason), no threshold loosened without a disclosed decision.

<!-- ticket:T-0601 -->
```yaml
id: T-0601
title: 'frob-exports triage: src/frob/strata, src/frob/tickets (22 symbols across
  2 packages)'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
scope:
- src/frob/strata/**
- src/frob/tickets/**
threat: null
component: null
```
frob-exports currently reports (measured 2026-07-22): src/frob/strata 5 public symbols missing from __init__.py, src/frob/tickets 17 (22 total, tickets is the largest single-package residue in this family). For each symbol, decide per-symbol: export it from the package's __init__.py, or demote it to private (leading underscore) if it should not be public API. No blanket waiver -- each symbol gets an explicit decision. Acceptance: frob-exports(src/frob/strata), frob-exports(src/frob/tickets) summary lines report 0 unresolved findings (exported, demoted, or waived-with-reason), no threshold loosened without a disclosed decision.

<!-- ticket:T-0602 -->
```yaml
id: T-0602
title: 'serve: per-obligation dependency-tracked partial re-evaluation inside gate
  dispatch'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0177
scope:
- src/frob/gates/**
- src/frob/serve/**
acceptance:
- text: GIVEN a warm daemon and a one-file edit WHEN frob_check_delta runs THEN only
    obligations whose inputs include that file are re-evaluated AND verify mode shows
    zero fingerprint mismatch vs a cold run
  evidence: []
threat: null
component: null
```
Deferred remainder of T-0177 deliverable 2. The warm daemon caches graph snapshot, baseline, and collected test ids, and frob_check_delta filters full-run results against the stamped baseline -- but run_gates itself still evaluates EVERY gate in full on each call. Build per-obligation input tracking inside gate dispatch so a delta call evaluates only obligations whose inputs changed, with the verify=True cold-diff mode as the correctness oracle (incremental results must provably match a cold frob check). NOTE: T-0177's Done report references this as T-0602 (ex-draft, id lost at land); the draft block did not survive  (same draft-loss failure as T-0401's draft -- T-0577 tracks the land-time fix), so this ticket is its real replacement.

<!-- ticket:T-0603 -->
```yaml
id: T-0603
title: wire derived-state integrity manifest into frob check/gates as a hard block
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0570
scope:
- src/frob/check/**
- src/frob/gates/**
acceptance:
- text: GIVEN a truncated .frob/cache.db WHEN frob check runs THEN the run fails closed
    naming the corrupt artifact before any gate consumes it
  evidence: []
threat: null
component: null
```
T-0570 landed the doctor-first fingerprint/format check (verify_derived_state in src/frob/doctor.py) but frob check/gates still consume derived state (.frob caches, coverage stamp, baseline) without consulting it -- corrupt state is reported by doctor, not blocked at the gate boundary. Wire verify_derived_state in so a corrupt derived artifact fails closed before any gate trusts it. NOTE: T-0570's Done report references this as T-draft-1327a057 (and mislabels it as T-0571); the draft did not survive land (T-0577 tracks the draft-loss bug), so this ticket is its real replacement.

<!-- ticket:T-0604 -->
```yaml
id: T-0604
title: 'derived-state manifest: persist fingerprints and detect drift across runs'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0570
scope:
- src/frob/doctor.py
- tests/system/test_cli_doctor.py
acceptance:
- text: GIVEN a derived artifact rewritten out-of-band between two doctor runs WHEN
    run_diagnosis executes THEN the drift is reported naming the artifact and both
    fingerprints
  evidence: []
threat: null
component: null
```
T-0570 computes sha256 fingerprints per run and validates format (SQLite magic, JSON parse) but never persists them -- so content DRIFT between runs (an artifact silently rewritten by a stale tool or a foreign process) is undetectable; only malformed bytes are caught. Store the fingerprints in a manifest file and compare on the next doctor run, reporting any artifact whose hash changed without a corresponding legitimate producer run. Flagged by T-0570's reviewer as the gap between the ticket title's 'manifest' promise and the delivered check-on-read.

<!-- ticket:T-0605 -->
```yaml
id: T-0605
title: 'design-pattern recommender phase 2: Adapter, Flyweight/pool, Observer, anemic-domain-model,
  poltergeist/lava-flow, sequential-coupling detectors'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0332
scope:
- src/frob/arch/**
- docs/modules/arch.md
- tests/unit/test_arch.py
- docs/design/registry/patterns.yaml
acceptance:
- text: GIVEN each of the 6 rows WHEN this ticket closes THEN the row is either detected
    by a tested high-precision detector or carries a reasoned not-checkable/out-of-scope
    disposition AND the patterns reconciliation pin test passes
  evidence: []
threat: null
component: null
```
The 6 registry rows T-0332 deferred for precision reasons: each needs a fuzzier structural signal than the >=3-occurrence floors phase 1 shipped, and shipping them imprecise would train users to ignore the advisory channel (the ticket's own noise mandate). Design a high-precision signal per row or record a reasoned not-checkable disposition. Any patterns.yaml entries re-deferred at T-0332 close point HERE -- keep the reconciliation pin test (tests/test_registry_reconciliation_patterns.py) green when this ticket changes dispositions. NOTE: T-0332's Done report references this as T-draft-4fb8deee; drafts do not survive land (T-0577), so this is the real ticket.

<!-- ticket:T-0608 -->
```yaml
id: T-0608
title: 'check CLI: thread --ticket/--base/--delta/--skip-gates through non-Python
  pipeline dispatchers'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0554
scope:
- src/frob/app/check_runner.py
- tests/unit/test_check.py
acceptance:
- text: GIVEN a TS-only repo WHEN frob check --ticket T-X runs THEN _run_gates receives
    ticket=T-X (asserted via test) and same for --base/--delta/--skip-gates across
    cpp/rust/ts dispatchers
  evidence: []
threat: null
component: null
```
T-0554 wired _run_gates into run_check_cpp/rust/ts with skip_gates/ticket/base/delta kwargs, but src/frob/app/check_runner.py's _dispatch_check_cpp/_dispatch_check_rust/_dispatch_check_ts do not pass cfg.check_skip_gates/check_ticket/check_base/check_delta down -- only _dispatch_check_python does. Gates run unconditionally for non-Python repos (correct default), but CLI-level --ticket/--base/--delta scoping is silently ignored there. Thread the four kwargs through and test each dispatcher. Found by T-0554's reviewer.

<!-- ticket:T-0618 -->
```yaml
id: T-0618
title: 'arch: LSP checks (ARCH1xx) -- override contract violations'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
scope:
- src/frob/arch/_solid.py
- src/frob/arch/_models.py
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
Override checks against a base/interface method: (1) raises NotImplementedError in a supposedly-concrete override; (2) incompatible signature (narrower accepted params, or wider/different return than base -- variance violation); (3) strengthened precondition (override adds an assert/raise the base lacks on the same param); (4) weakened postcondition; (5) no-op override of a value-returning base method (bare pass/return None where base returns a value). Needs override-resolution over the normalized model (base<->override linkage). Acceptance: one fixture per sub-check; docs updated.

<!-- ticket:T-0619 -->
```yaml
id: T-0619
title: 'arch: ISP checks (ARCH1xx) -- fat interface, narrow-client usage'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
scope:
- src/frob/arch/_solid.py
- src/frob/arch/_models.py
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
fat interface: ABC/Protocol/trait whose implementers stub most methods with raise NotImplementedError/pass (measured over resolved implementers, not per-class). narrow-client usage: a function/class injected with a wide interface but only calling a small subset of its methods -- flag as an ISP split candidate. Acceptance: positive+negative fixtures; docs updated.

<!-- ticket:T-0620 -->
```yaml
id: T-0620
title: 'arch: DIP layering contract (declared allowed-module-dependency graph) + no-DI
  construction smell'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
scope:
- src/frob/arch/_layering.py
- frob.toml
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
Layering contract: a frob.toml-declared allowed-module-dependency graph (import-linter style: layers + allowed edges); a violation is a high layer importing a low/concrete module across the declared boundary -- new ARCHxxx id, resolved against actual (not surface) imports per the adversarial-hardening note (transitive re-export resolution, fail-closed on dynamic import). concrete-collaborator construction smell: a method body directly constructs a concrete dependency instead of receiving it via constructor/param injection. Acceptance: a sample frob.toml layering config + fixture violating it fails; a compliant fixture passes; docs updated with the config schema.

<!-- ticket:T-0621 -->
```yaml
id: T-0621
title: 'arch: type-driven design checks (ARCH1xx) -- illegal states, primitive obsession,
  parse-dont-validate, boolean flag param'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
scope:
- src/frob/arch/_typedesign.py
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
make-illegal-states-unrepresentable: a bool flag field/param whose valid combinations are validated at runtime rather than modeled as an enum/newtype (heuristic: bool field + a validator/assert referencing it + another field it constrains). primitive-obsession: 3+ raw str/int params on one function representing what looks like one domain concept (repeated co-occurrence across call sites). parse-dont-validate: a function that validates its input (raise/assert on shape) then returns the SAME unrefined input type instead of a refined one. boolean/flag parameter: public function with a bool param that switches behavior (branches internally on it) -- split-function candidate. Acceptance: fixture per sub-check; docs updated.

<!-- ticket:T-0622 -->
```yaml
id: T-0622
title: 'arch: logging discipline checks (ARCH1xx) -- unlogged error path, unlogged
  boundary, print-as-diagnostic'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
scope:
- src/frob/arch/_logging_checks.py
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
unlogged error path: except/raise/return-Err block with no log call inside it. unlogged boundary: public entry point / subprocess call / network call / filesystem call site with no log statement in its immediate scope. print-as-diagnostic: print() call used where a module logger call is expected (not a CLI-output module). Must coincide with strata's observability-of-flow split per CLAUDE.md note -- these checks are logging-IN-CODE only, no runtime/flow correlation. Acceptance: fixture per sub-check; docs updated including the strata/arch boundary note.

<!-- ticket:T-0623 -->
```yaml
id: T-0623
title: 'arch: fallibility checks (ARCH1xx) -- unhandled Result, swallowed exception,
  wrong-signature raise, over-broad except'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
scope:
- src/frob/arch/_fallibility.py
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
unhandled Result: a call known to return typani Result[T,E] (or Rust #[must_use]) used as a bare statement, discarding the value. swallowed exception: bare except: or except Exception: pass with no re-raise/log/return-Err. recoverable-error-wrong-signature: a function raises a clearly-recoverable error (e.g. ValueError on bad user input) but its signature returns T, not Result[T,E]. over-broad except / re-raise-losing-context: except Exception (or bare except) catching more than the call site can name, or a re-raise that drops the original exception/traceback. Acceptance: fixture per sub-check; docs updated.

<!-- ticket:T-0624 -->
```yaml
id: T-0624
title: 'arch: misc design smells (ARCH1xx) -- mutable default arg, feature envy, data
  clumps, magic literals, dead private code, deep inheritance, temporal coupling'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
scope:
- src/frob/arch/_smells.py
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
mutable default argument (list/dict/set literal as a default param value). feature envy (method's body references another object's attrs/methods more than self's). data clumps (same 3+-param group passed together across 3+ call sites). magic numbers/strings in logic (bare literal in a comparison/branch outside a named constant). dead private code (unreferenced private symbol, using the T-0288 call graph so helper-splices don't false-positive). deep inheritance (DIT beyond a configurable threshold). temporal coupling (an _initialized-style flag guarding call order instead of the type system). Acceptance: fixture per sub-check; docs updated.

<!-- ticket:T-0625 -->
```yaml
id: T-0625
title: 'arch: module dependency cycle detection (ARCH1xx)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0620
parent: T-0330
scope:
- src/frob/arch/_smells.py
- src/frob/graph/**
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
Detect import cycles across modules using the existing module-dependency graph (shared with T-0620's layering contract, do not fork a second graph builder). Report the cycle path. Acceptance: a fixture pair of modules importing each other fails; docs updated; explicitly reuses T-0620's graph builder (no duplicate import-resolution code).

<!-- ticket:T-0626 -->
```yaml
id: T-0626
title: 'arch: register all ARCH1xx checks in the T-0343 unified registry, close the
  DENOMINATOR MANIFEST gap for T-0330'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0616
- T-0617
- T-0618
- T-0619
- T-0620
- T-0621
- T-0622
- T-0623
- T-0624
- T-0625
parent: T-0330
scope:
- docs/design/registry/**
- docs/design/architecture-check-catalog.md
- docs/design/design-pattern-traps-corpus.md
threat: null
component: null
```
Per T-0330's EXHAUSTIVENESS DRIFT-LOCK paragraph: every tier-1 statically-checkable entry in architecture-check-catalog.md and every trap hallmark in design-pattern-traps-corpus.md that this epic's ARCH1xx family (T-0616..T-0625) was meant to cover must get a disposition in docs/design/registry/ (addressed-by-check <ARCHxxx id> | reasoned-deferral | duplicate-of | out-of-scope), per the T-0343 REG001 gate contract. Acceptance: frob check's registry gate (REG001-family) shows zero unaccounted entries whose owning corpus row maps to T-0330's scope; any entry NOT built in T-0616..T-0625 gets an explicit reasoned-deferral or out-of-scope disposition, never silently dropped. This ticket is the epic's actual close condition -- T-0330 cannot close until this is green.

<!-- ticket:T-0628 -->
```yaml
id: T-0628
title: frob graph affects CLI subcommand + digest-drift gate (T-0325 follow-on)
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0325
scope:
- src/frob/app/graph_runner.py
- src/frob/gates/**
- docs/modules/graph.md
acceptance:
- text: GIVEN a symbol with dependents WHEN frob graph affects SYMREF runs THEN the
    affected code/docs/tests print with truncation flagged; GIVEN a diff changing
    a symbol whose affects-closure docs were untouched WHEN the drift gate runs THEN
    it reports the stale dependents
  evidence: []
threat: null
component: null
```
T-0325 landed the warm affects() library query and frob_affects MCP tool but cut two surfaces as out of scope, noting them only in docs/modules/graph.md prose: (a) a frob graph affects REF CLI subcommand in src/frob/app/graph_runner.py so the north-star query is usable outside MCP; (b) a digest-drift gate that consumes the affects closure to FAIL when a changed symbol's dependent docs/code were not updated in the same change -- the enforcement half of the north-star (CLAUDE.md: 'a graph of WHAT DOCUMENTATION and WHAT OTHER CODE needs to be updated whenever something is touched'). Cut work must live in tickets, not prose -- this is that ticket.

<!-- ticket:T-0629 -->
```yaml
id: T-0629
title: 'std.host windows: binPath/ImagePath vocabulary so install.ps1 can create the
  SCM service, not just harden it'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0261
parent: T-0254
scope:
- strata-core/src/parse.rs
- src/frob/strata/_host.py
- src/frob/deploy/_generate_windows.py
- tests/unit/strata/
- tests/unit/deploy/
acceptance:
- text: GIVEN a windows node declaring service with a binPath WHEN install.ps1 is
    generated THEN it idempotently creates the SCM service with that image path before
    hardening AND uninstall.ps1 deletes it
  evidence: []
threat: null
component: null
```
T-0264's windows generator hardens an existing SCM service (SID type, privileges via sc.exe config) but cannot CREATE one -- std.host has no binPath/ImagePath (executable path + arguments) vocabulary, so sc.exe create is impossible from the model. T-0254's epic text says the install sequence registers the Windows Service; full-install-from-zero needs the vocabulary. Add the grammar clause (parse.rs node/store symmetry per T-0261 precedent), HostManifest read-back, and wire generate_windows_install_script to sc.exe create idempotently when binPath is declared. Flagged by T-0264's reviewer so the epic's full-install intent is not silently lost.

<!-- ticket:T-0631 -->
```yaml
id: T-0631
title: 'frob ticket land: TICK005-backed regression sweep + --push option'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0577
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
acceptance:
- text: GIVEN a land with --push WHEN the land completes THEN the push happens only
    after every land verification passed; GIVEN the TICK005 rule defined WHEN land
    runs THEN the regression sweep executes and blocks on failure
  evidence: []
threat: null
component: null
```
The two T-0577 dispatch items that had no existing design to build against, deferred honestly rather than half-built: (1) a TICK005-backed regression sweep at land time (define the TICK005 rule first, then have land run it); (2) a --push option for frob ticket land so the coordinator can land+push in one verified step. NOTE: T-0577's Done report references this as T-draft-f6f10c67; that draft was filed pre-fix and will not survive T-0577's own land, so this is the real ticket.

<!-- ticket:T-0632 -->
```yaml
id: T-0632
title: 'arch: extend NormalizedCall with arg-position detail and migrate _extract_signatures/_collect_dispatch_refs
  onto the model'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0610
parent: T-0329
scope:
- src/frob/arch/_normalized.py
- src/frob/arch/_python.py
- tests/unit/test_arch.py
acceptance:
- text: GIVEN the existing T-0360/T-0370 regression tests unmodified WHEN both check
    families run through the normalized model THEN all pass and no raw-tree walk remains
    in _collect_dispatch_refs (or a reasoned decision records what stays raw and why)
  evidence: []
threat: null
component: null
```
T-0610 migrated long-function/god-class/deep-nesting onto NormalizedModule but left two check families on the raw tree-sitter walk, with concrete schema gaps documented: _extract_signatures' body-fingerprint needs full raw AST for alpha-renaming, and _collect_dispatch_refs needs argument-position/dict-value detail NormalizedCall does not carry. Extend the model (arg positions on NormalizedCall; a fingerprint-friendly body projection or a documented decision to keep fingerprints raw-AST-based), then migrate both WITHOUT regressing the T-0360 dispatch-family suppression or T-0370 near-dup discriminator protections (their tests must pass unmodified). NOTE: T-0610's Done report references this as T-0632 (ex-draft, id lost at land) (prose only); this is the real ticket.

<!-- ticket:T-0634 -->
```yaml
id: T-0634
title: 'fix circular import: frob.testing standalone import fails through frob.gates'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/testing/**
- src/frob/gates/**
acceptance:
- text: GIVEN a fresh python process WHEN import frob.testing runs as the first frob
    import THEN it succeeds and the test-file workaround import is removed
  evidence: []
threat: null
component: null
```
import frob.testing as the first frob-touching import raises ImportError (cannot import name CollectedTests) through the frob.gates cycle; masked in the full suite by import order, breaks standalone runs. tests/unit/testing/test_stability.py carries a documented workaround (import frob.gates first). Was T-draft-3d5f6965 in T-0575's worktree; the draft was dropped at land (see the auto-finalize field-failure ticket).

<!-- ticket:T-0635 -->
```yaml
id: T-0635
title: wire flake-quarantine stability tracking into frob test CLI run path
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0575
scope:
- src/frob/app/test_runner.py
- src/frob/testing/**
acceptance:
- text: GIVEN a flaky test with an open quarantine ticket WHEN frob test runs via
    the CLI THEN the run records history, the quarantined failure does not fail the
    build, and alarms surface for closed-ticket quarantines
  evidence: []
threat: null
component: null
```
T-0575 landed frob.testing._stability (record_outcomes, evaluate_gate, quarantine, alarms) but nothing in the frob test CLI path calls it -- tracking only happens if invoked programmatically. Wire capture/track + evaluate_gate + alarm surfacing into src/frob/app/test_runner.py so every frob test run updates history and applies quarantine semantics automatically. Disclosed cut in T-0575's Done report.

<!-- ticket:T-0638 -->
```yaml
id: T-0638
title: 'frob deprecated CLI subcommand: list deprecations with sunset/ticket status'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0576
scope:
- src/frob/app/**
- src/frob/__main__.py
- README.md
- docs/modules/gates.md
acceptance:
- text: GIVEN a repo with frob:deprecated directives WHEN frob deprecated runs THEN
    each deprecation prints with its DEPR status and the README command table includes
    the new command
  evidence: []
threat: null
component: null
```
T-0576 landed the frob:deprecated directive and DEPR001-004 gates plus the list_deprecated API, but no CLI surface. Add a frob deprecated subcommand (App/AppConfig runner pattern) listing every deprecation with since/sunset/ticket/status (in-window vs past-sunset vs orphaned), plus the README command-table row and count bump so DOC005 stays green. Was T-0638 (ex-draft, id lost at land) in T-0576's worktree; drafts still do not survive land (T-0637).

<!-- ticket:T-0639 -->
```yaml
id: T-0639
title: 'design: detect a deprecated symbol gaining NEW callers (public-symbol caller
  graph)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0576
scope:
- src/frob/graph/**
- src/frob/gates/**
acceptance:
- text: GIVEN a design decision recorded WHEN implemented THEN a change adding a call
    to a deprecated public symbol produces a DEPR finding naming the new call site
  evidence: []
threat: null
component: null
```
T-0576's ticket body wanted a deprecated symbol gaining new callers to fire a finding, but frob.graph.callgraph's caller/reference resolution only covers PRIVATE callees by design -- a PUBLIC deprecated symbol's callers are not resolvable today. Design work: either extend the callgraph to public-symbol references (cost/precision tradeoff) or diff-based detection (a new call site referencing the symbol in a change since the directive appeared). Was T-0639 (ex-draft, id lost at land) in T-0576's worktree; drafts still do not survive land (T-0637).

<!-- ticket:T-0640 -->
```yaml
id: T-0640
title: 'strata: TIMEOUT obligation on every remote/cross-boundary flow (REL2xx)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
- design/frob.strata
- src/frob/app/sys_runner.py
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'Salvage of T-0640 (docs/guides/agent-playbook.md): the REL2xx TIMEOUT

    obligation implementation is already fully landed on main (commits

    cdbd4337, 05264346, b13d2c66, plus T-0644/T-0758 follow-ups) but the

    ticket ledger record itself was never updated past queued/in-progress.

    No new code is being written in this pass, only the ticket record is

    being reconciled against what already exists on disk. The already-landed

    footprint touches design/frob.strata (per-flow attr timeout/local

    disposition + two disclosed REL200 waivers) and src/frob/app/sys_runner.py

    (CLI wiring of check_reliability_timeouts into `frob sys audit`), both

    outside the ticket''s originally declared strata-only scope -- widening

    scope here documents that footprint accurately rather than leaving scope

    narrower than the work it is being credited for.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'Salvage of T-0640 (docs/guides/agent-playbook.md): the REL2xx TIMEOUT

    obligation implementation is already fully landed on main (commits

    cdbd4337, 05264346, b13d2c66, plus T-0644/T-0758 follow-ups) but the

    ticket ledger record itself was never updated past queued/in-progress.

    No new code is being written in this pass, only the ticket record is

    being reconciled against what already exists on disk. The already-landed

    footprint touches design/frob.strata (per-flow attr timeout/local

    disposition + two disclosed REL200 waivers) and src/frob/app/sys_runner.py

    (CLI wiring of check_reliability_timeouts into `frob sys audit`), both

    outside the ticket''s originally declared strata-only scope -- widening

    scope here documents that footprint accurately rather than leaving scope

    narrower than the work it is being credited for.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_discharged_and_exempt_flows_clean
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_waiver_on_one_flow_keeps_sibling_flow_finding
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_real_code_evidence_discharges
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_proves_against_dst
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_lacking_evidence_fires_against_dst
- tests/unit/strata/test_reliability.py::TestCrossFamilyWaiverScoping::test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
acceptance:
- text: Given a .strata flow crossing a service/process boundary with no timeout attr,
    when frob check runs, then REL2xx fires unless waived with a reason
  evidence:
  - tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires
  - tests/unit/strata/test_reliability.py::TestMissingTimeout::test_waiver_on_one_flow_keeps_sibling_flow_finding
- text: Given a declared timeout, when the bound code path lacks a matching real timeout
    arg, then the check fails (proof-against-code), not merely passes on declaration
  evidence:
  - tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires
  - tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_real_code_evidence_discharges
threat: null
component: null
```
Add a flow-level TIMEOUT attribute + REL2xx checker + litmus + docs: every remote/cross-boundary flow must declare a bounded timeout (unbounded hang otherwise). Deny-by-default with reasoned-waive channel (T-0174). Discharge must be proof-against-code (real timeout arg at the call site) per T-0331's PROVABILITY CONSTRAINT, not bare declaration.

## Done report

Salvage/reconciliation pass (docs/guides/agent-playbook.md): the REL2xx
TIMEOUT obligation this ticket asked for is already fully implemented and
landed on main -- cdbd4337 (REL2xx TIMEOUT-obligation reliability family,
REL200 missing-timeout + REL201 unproven-timeout with proof-against-code
discharge per T-0331's provability constraint), 05264346 (REL2xx waiver
in_scope per rule-family), b13d2c66 (wired into `frob sys audit` via
`check_reliability_timeouts` in src/frob/app/sys_runner.py + cross-family
stale-waiver false-positive fix), hardened further by the T-0644 (REL21x
HEALTH) and T-0758 (REL201 dst-endpoint proof anchoring) follow-ups. The
ticket ledger record was simply never updated past queued: no state
transition, no evidence, no acceptance binding. This pass writes no new
feature code; it reconciles the record against what exists.

Verification, not assertion: all 10 recorded evidence tests (the full
tests/unit/strata/test_reliability.py REL2xx suite + the system-level
self-model parse/elaborate test) run green on current main, and both
acceptance criteria are bound to the specific tests that prove them
(missing-timeout fires + waiver stays flow-scoped; declared-but-unproven
timeout fails against code).

Scope was widened (reasons recorded per-glob) to design/frob.strata and
src/frob/app/sys_runner.py because the already-landed footprint touches
both -- leaving them out would credit this ticket for less than the work
being reconciled.

Deferred remainder made honest: the two REL200 waivers on
design/frob.strata's elaborator-synthesized in-process cache flows
(graph_cache__fill, graph_cache__inval_f_parse) previously cited T-0640
itself as their follow-up. Closing this ticket would have left them bound
to a done ticket (exactly what WAIVE006 exists to catch), so the
attr-forwarding surface they wait on is now filed as T-0845 and both
waivers' ticket refs re-pointed there in this pass.

### Changed
```
 design/frob.strata |   4 +-
 tickets.md         | 140 +++++++++++++++++++++++++++++++++++++++++++++++++++--
 2 files changed, 139 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestMissingTimeout::test_discharged_and_exempt_flows_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestMissingTimeout::test_waiver_on_one_flow_keeps_sibling_flow_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_proves_against_dst` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_lacking_evidence_fires_against_dst` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestCrossFamilyWaiverScoping::test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 1209 warning(s), 210 waived

<!-- ticket:T-0641 -->
```yaml
id: T-0641
title: 'strata: RETRY backoff+jitter + non-idempotent-op guard + IDEMPOTENCY key obligation'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a flow with retry=true and no backoff/jitter declared, when checked,
    then it fails
  evidence: []
- text: Given a retryable flow targeting a non-idempotent mutating op with no idempotency
    key, when checked, then it fails
  evidence: []
threat: null
component: null
```
RETRY flow attr must declare exponential backoff+jitter; a retry on a non-idempotent op is a hard obligation failure unless the target op declares an idempotency key. Proof-against-code: retry loop and backoff params must match declared values; bare declaration insufficient (T-0331 PROVABILITY CONSTRAINT).

<!-- ticket:T-0642 -->
```yaml
id: T-0642
title: 'strata: CIRCUIT BREAKER / bulkhead obligation per external dependency'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given an external-dependency node with no circuit-breaker/bulkhead declared,
    when checked, then the obligation fires
  evidence: []
threat: null
component: null
```
Every external dependency node must declare a circuit-breaker/bulkhead policy, extending LINT004 kill-switch. Proof-against-code required per epic PROVABILITY CONSTRAINT.

<!-- ticket:T-0643 -->
```yaml
id: T-0643
title: 'strata: FALLBACK/graceful-degradation obligation for CRITICAL dependencies'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0640
- T-0642
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a CRITICAL dependency with no fallback declared, when checked, then
    the obligation fires
  evidence: []
threat: null
component: null
```
A dependency marked CRITICAL must declare a fallback/graceful-degradation path, and the fallback code path must be shown present (proof-against-code) or explicitly waived. Reuses the circuit-breaker ticket's dependency-criticality classification, hence blocked on that groundwork existing.

<!-- ticket:T-0645 -->
```yaml
id: T-0645
title: 'strata: SPOF detection - inbound-critical-flow node with replicas_max=1/no
  redundancy'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a node with inbound critical flows and replicas_max=1, when checked,
    then SPOF obligation fires unless waived
  evidence: []
threat: null
component: null
```
A node receiving critical inbound flows with replicas_max=1 or no declared redundancy is a single point of failure; flag as a hard obligation, deny-by-default with reasoned waive (T-0174).

<!-- ticket:T-0646 -->
```yaml
id: T-0646
title: 'strata: BACKPRESSURE bounded-intake obligation on queues/consumers'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a queue/consumer node with no bounded-intake policy declared, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
```
Every queue/consumer node must declare bounded intake (backpressure policy), extending LINT003 surge / LINT005 capacity.

<!-- ticket:T-0647 -->
```yaml
id: T-0647
title: 'strata: boundary-flow metrics+traces+logs obligation + trace-id CORRELATION
  propagation'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a boundary flow with no metrics/traces/logs declared, when checked,
    then the obligation fires
  evidence: []
- text: Given a multi-hop flow chain with no trace-id propagation declared, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
```
Every boundary flow must declare metrics+traces+logs instrumentation; a flow chain must propagate a correlation/trace-id across hops (distributed tracing). Proof-against-code required.

<!-- ticket:T-0648 -->
```yaml
id: T-0648
title: 'strata: golden-signal SLO + error-budget obligation per service'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0647
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a service node with no golden-signal SLOs + error budget declared, when
    checked, then the obligation fires
  evidence: []
threat: null
component: null
```
Every service node must declare golden-signal SLOs (latency/traffic/errors/saturation) and an error budget. Depends on the metrics-instrumentation obligation existing first, since an SLO without the underlying signal is unverifiable.

<!-- ticket:T-0649 -->
```yaml
id: T-0649
title: 'strata: SINGLE SOURCE OF TRUTH obligation - two nodes writing one store is
  a hazard'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a store with >=2 distinct writer nodes and no declared single-owner/reconciliation,
    when checked, then the obligation fires
  evidence: []
threat: null
component: null
```
Extends SYS003 hub: a store written by two or more distinct nodes without a declared owner/reconciliation is a hard obligation failure.

<!-- ticket:T-0650 -->
```yaml
id: T-0650
title: 'strata: transactional-boundary obligation on multi-write ops'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0649
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a multi-write op with no transactional-boundary declared, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
```
Any op writing to >1 store must declare a transactional boundary (or saga, see distributed-txn ticket). Reuses the store-writer graph built for the single-source-of-truth obligation.

<!-- ticket:T-0651 -->
```yaml
id: T-0651
title: 'strata: MESSAGE SCHEMA VERSION obligation on events/queues'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given an event/queue node with no schema version declared, when checked, then
    the obligation fires
  evidence: []
threat: null
component: null
```
Every event/queue node must declare a message schema version for backward-compat tracking.

<!-- ticket:T-0652 -->
```yaml
id: T-0652
title: 'strata: exactly-once vs at-least-once delivery-semantics declaration on queues'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0651
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a queue node with no delivery-semantics declared, when checked, then
    the obligation fires
  evidence: []
threat: null
component: null
```
Every queue node must declare its delivery semantics (exactly-once/at-least-once). Shares the queue-node surface work with the message-schema-version obligation.

<!-- ticket:T-0653 -->
```yaml
id: T-0653
title: 'strata: retention/TTL obligation on PII stores'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a PII-tagged store with no retention/TTL declared, when checked, then
    the obligation fires
  evidence: []
threat: null
component: null
```
Every store holding PII must declare a retention/TTL policy (ties T-0207).

<!-- ticket:T-0654 -->
```yaml
id: T-0654
title: 'strata: SYNC CALL-CHAIN DEPTH bound obligation'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a sync call chain exceeding the declared/default depth bound, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
```
Bound the depth of synchronous call chains (cascading latency/failure risk), using reachability including non-transitive edges (T-0282).

<!-- ticket:T-0655 -->
```yaml
id: T-0655
title: 'strata: distributed-transaction-across-services requires saga/compensation'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0650
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a cross-service transaction with no saga/compensation declared, when
    checked, then the obligation fires
  evidence: []
threat: null
component: null
```
A transaction spanning multiple services must declare a saga/compensation strategy; builds on the transactional-boundary obligation's multi-write detection extended across service boundaries.

<!-- ticket:T-0656 -->
```yaml
id: T-0656
title: 'strata: no-shared-mutable-state-across-service-boundaries obligation'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given two services sharing a mutable store/memory region across their boundary
    with no declared exception, when checked, then the obligation fires
  evidence: []
threat: null
component: null
```
Detect and flag shared mutable state reachable across a declared service boundary.

<!-- ticket:T-0657 -->
```yaml
id: T-0657
title: 'strata: clock/ordering-assumptions obligation across distributed flows'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
acceptance:
- text: Given a cross-node flow with an implicit clock/ordering assumption and no
    declared strategy, when checked, then the obligation fires
  evidence: []
threat: null
component: null
```
Flag flows relying on wall-clock ordering/synchronization assumptions across distributed nodes without a declared clock/ordering strategy (T-0282 reachability).

<!-- ticket:T-0658 -->
```yaml
id: T-0658
title: 'strata systems-checks: N:M coverage meta-test vs system-design-corpus.md denominator
  (epic T-0331 close condition)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0640
- T-0641
- T-0642
- T-0643
- T-0644
- T-0645
- T-0646
- T-0647
- T-0648
- T-0649
- T-0650
- T-0651
- T-0652
- T-0653
- T-0654
- T-0655
- T-0656
- T-0392
parent: T-0331
scope:
- src/frob/strata/**
- docs/design/registry/system-design.yaml
- tests/unit/strata/**
acceptance:
- text: Given the full system-design-corpus.md denominator, when the meta-test runs,
    then every entry has a disposition (addressed-by-check | reasoned-deferral) and
    the coverage total matches TOTAL
  evidence: []
- text: Given a future new system-design-corpus.md entry with no disposition, when
    the meta-test runs, then it fails the build
  evidence: []
threat: null
component: null
```
Epic close condition. Bind every genuine system-design-corpus.md manifest entry (105 genuine, per RECONCILIATION.md finding (d), plus 14 manifest-extraction artifacts explicitly excluded) to >=1 registered SYS2xx/REL2xx check or a reasoned deferral, following the T-0343 drift-lock framework. (addressed union deferred) == TOTAL. Cannot close while any relevant entry is unaddressed and un-deferred. Depends on all 16 obligation children plus T-0392 (system-design registry-domain reconciliation) landing so 'registered check' is a real, checkable claim.

<!-- ticket:T-0659 -->
```yaml
id: T-0659
title: 'vet: exhaustive Python static-binding resolver closure vs capability-evasion-taxonomy.md
  denominator'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
acceptance:
- text: Given every Python static-resolvable construct in the taxonomy's Python table,
    when the resolver runs on a litmus fixture for that construct, then the aliased
    dangerous call is detected
  evidence: []
- text: Given a benign parameter/local binding shadowing a dangerous name, when the
    resolver runs, then it stays silent (no regression)
  evidence: []
threat: null
component: null
```
T-0328 (import/binding-aware resolution) and T-0337 (local rebinding) are done, but not yet checked against the full capability-evasion-taxonomy.md Python denominator (13 static + 9 opaque entries). Enumerate every remaining Python static construct (chained attribute rebinding, destructuring/unpack aliasing, star-import re-export chains, conditional/try-except import fallback aliasing) and close any gap with a resolver fix + litmus fixture, without regressing shadowing soundness (a benign/param binding must stay silent).

<!-- ticket:T-0660 -->
```yaml
id: T-0660
title: 'vet: exhaustive TypeScript/JS static-binding resolver (import/import-as/from-import/star-import/re-export/destructuring)'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
acceptance:
- text: Given every TS/JS static-resolvable construct in the taxonomy table, when
    the resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
```
Implement per-scope, transitive, cycle-guarded static name-binding resolution for TS/JS per capability-evasion-taxonomy.md's TS/JS table (17 static + 9 opaque entries): import/import-as, named/default/namespace import, re-export (export ... from), destructuring assignment, CommonJS require aliasing where statically resolvable.

<!-- ticket:T-0661 -->
```yaml
id: T-0661
title: 'vet: exhaustive Rust static-binding resolver (use/use-as/pub use/glob use)'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
acceptance:
- text: Given every Rust static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
```
Implement per-scope, transitive, cycle-guarded static name-binding resolution for Rust per capability-evasion-taxonomy.md's Rust table (13 static + 6 opaque entries): use, use ... as, pub use re-export, glob use, module-path aliasing.

<!-- ticket:T-0662 -->
```yaml
id: T-0662
title: 'vet: exhaustive C static-binding resolver (#define, fn-ptr init from named
  fn, typedef''d fn-ptr)'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
acceptance:
- text: Given every C static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
```
Implement static name-binding resolution for C per capability-evasion-taxonomy.md's C table (7 static + 5 opaque entries): #define macro aliasing, function-pointer variable initialized from a named function, typedef'd function-pointer types.

<!-- ticket:T-0663 -->
```yaml
id: T-0663
title: 'vet: exhaustive C++ static-binding resolver (using-decl, namespace alias,
  fn-ptr/typedef, on top of C fragment)'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0662
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
acceptance:
- text: Given every C++ static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
```
Implement static name-binding resolution for C++ per capability-evasion-taxonomy.md's C++ table (12 static + 5 opaque entries): using-declaration, namespace alias, function-pointer/typedef'd fn-ptr, building on the C resolver's fn-ptr/typedef groundwork.

<!-- ticket:T-0664 -->
```yaml
id: T-0664
title: 'vet: exhaustive Kotlin static-binding resolver (import-as, ::ref, typealias)'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
acceptance:
- text: Given every Kotlin static-resolvable construct in the taxonomy table, when
    the resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
```
Implement static name-binding resolution for Kotlin per capability-evasion-taxonomy.md's Kotlin table (11 static + 5 opaque entries): import-as, function-reference (::ref), typealias.

<!-- ticket:T-0665 -->
```yaml
id: T-0665
title: 'vet/strata: fail-closed opaque-capability-indirection obligation for runtime-resolved
  dispatch'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/strata/**
- tests/test_vet.py
acceptance:
- text: Given code containing a spec-defined runtime-resolved indirection construct
    with no waiver, when checked, then the obligation fires
  evidence: []
- text: Given the same construct with a reasoned waiver, when checked, then it passes
    and the waiver reason is recorded
  evidence: []
threat: null
component: null
```
Per-language, every spec-defined runtime-resolved indirection construct (Python getattr/eval/importlib; TS dynamic import()/eval; Rust reflection-via-trait-object-from-data; C/C++ dlopen/dlsym/fn-ptr-from-data; Kotlin reflection API) becomes an 'opaque capability indirection' obligation: fires by default, requires a reasoned waiver (T-0174), never a silent pass. Consistent with strata's prove-or-reject philosophy (T-0290).

<!-- ticket:T-0666 -->
```yaml
id: T-0666
title: 'vet: cross-language exhaustiveness meta-test binding capability-evasion-taxonomy.md
  denominator (112 entries) to per-construct litmus fixtures (T-0339 close condition)'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0659
- T-0660
- T-0661
- T-0662
- T-0663
- T-0664
- T-0665
- T-0390
parent: T-0339
scope:
- src/frob/vet/**
- docs/design/registry/evasion.yaml
- tests/test_vet.py
acceptance:
- text: Given the full evasion taxonomy denominator, when the meta-test runs, then
    every entry maps to >=1 registered litmus fixture
  evidence: []
- text: Given a new taxonomy entry added with no fixture, when the meta-test runs,
    then it fails the build
  evidence: []
threat: null
component: null
```
Epic close condition. Binds every capability-evasion-taxonomy.md entry (112: 13+9 Python, 17+9 TS/JS, 13+6 Rust, 7+5 C, 12+5 C++, 11+5 Kotlin) to >=1 litmus fixture that exercises it, mirroring the CVE-fingerprint catalog drift-lock. Fails the build if any construct has no fixture. Depends on all per-language resolver tickets and the opaque-indirection obligation landing, plus T-0390 (evasion registry-domain reconciliation) for disposition accuracy.

<!-- ticket:T-0667 -->
```yaml
id: T-0667
title: 'strata: SYS-COV coverage-totality check - every capable module binds to a
  modeled node'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0630
parent: T-0341
scope:
- src/frob/strata/**
- src/frob/vet/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
acceptance:
- text: Given a module with an observed capability effect and no strata node binding,
    when checked, then SYS-COV fires
  evidence: []
- text: Given every module bound to a node, when checked, then SYS-COV is silent
  evidence: []
threat: null
component: null
```
Extend the capability graph (T-0328-resolved) to enumerate every module with an observed capability effect, then cross-check against strata node bindings. A capable-but-unbound module is a hard obligation failure -- this closes acceptance-criterion (1) 'un-modeled modules escape all obligations'. Depends on T-0630 wiring real code binding into production entrypoints so the check has real data to run against, not just unit-test fixtures.

<!-- ticket:T-0668 -->
```yaml
id: T-0668
title: 'strata: exact interface-conformance check - declared node interface == real
  public code surface'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0667
parent: T-0341
scope:
- src/frob/strata/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
acceptance:
- text: Given a node declaring fewer public symbols than the bound module exports,
    when checked, then the obligation fires
  evidence: []
- text: Given a node declaring a symbol the bound module does not export, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
```
A node's declared interface must equal the bound module's real public surface (no under- or over-declaration) -- closes acceptance-criterion (2). Depends on coverage-totality's binding pass existing first (need a bound node before its interface can be checked).

<!-- ticket:T-0669 -->
```yaml
id: T-0669
title: 'strata: PURPOSE contract - node purpose carries an allowed-effect profile
  checked against code'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0667
parent: T-0341
scope:
- src/frob/strata/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
acceptance:
- text: Given a node whose purpose declares a read-only effect profile but whose bound
    code performs a write, when checked, then the obligation fires
  evidence: []
threat: null
component: null
```
Each node's declared purpose must carry an allowed-effect profile (e.g. 'read-only query' cannot emit writes); real observed effects outside that profile fail via _effects.py::check_capability_conformance -- closes acceptance-criterion (3).

<!-- ticket:T-0670 -->
```yaml
id: T-0670
title: 'strata: binding-totality + effect-conformance - reject logic laundered into
  an unbound file'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0667
parent: T-0341
scope:
- src/frob/strata/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
acceptance:
- text: Given dangerous logic moved into a helper module not directly bound to any
    node but reachable from a bound node, when checked, then the effect is still attributed
    and conformance-checked, not silently dropped
  evidence: []
threat: null
component: null
```
Extend SYS100/SYS101/SYS102 so the bound-set is provably total against the capability graph: a module reachable via import/call from a bound node but itself unbound must not silently escape effect-conformance checking -- closes acceptance-criterion (4) 'binding need not be total, so logic can be laundered into an unbound file'.

<!-- ticket:T-0671 -->
```yaml
id: T-0671
title: 'strata: bounded/staleness-gated assume+waiver mechanism - un-droppable floor
  view for conformance obligations'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0668
- T-0669
- T-0670
parent: T-0341
scope:
- src/frob/strata/**
- docs/modules/strata.md
- tests/unit/strata/**
acceptance:
- text: Given a waiver older than its staleness bound, when checked, then it is treated
    as expired and the underlying obligation re-fires
  evidence: []
- text: Given any active waiver, when frob check runs, then it appears in the floor
    view and cannot be hidden from default output
  evidence: []
threat: null
component: null
```
Closes acceptance-criterion (5): every conformance escape hatch (interface/purpose/binding waivers) must be bounded (expiry/staleness-gated) and surfaced in an un-droppable floor view so it cannot become a permanent silent exemption. Depends on the three conformance checks existing first since this wraps their waiver channel.

<!-- ticket:T-0672 -->
```yaml
id: T-0672
title: 'strata conformance totality: N:M meta-test binding structural-linter-adversarial-hardening.md
  denominator to the five conformance checks (T-0341 close condition)'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0667
- T-0668
- T-0669
- T-0670
- T-0671
- T-0391
parent: T-0341
scope:
- src/frob/strata/**
- docs/design/registry/arch-checks.yaml
- tests/unit/strata/**
acceptance:
- text: Given the structural-linter-adversarial-hardening.md denominator, when the
    meta-test runs, then every SLH-* entry has a disposition (addressed-by-check |
    reasoned-deferral)
  evidence: []
- text: Given a new hardening-doc entry with no disposition, when the meta-test runs,
    then it fails the build
  evidence: []
threat: null
component: null
```
Epic close condition. Binds the structural-linter-adversarial-hardening.md denominator (5 named principles + 9 arch-evasion + 9 strata-evasion rows, registry ids SLH-RULE-*/SLH-ARCH-EVA-*/SLH-SYS-EVA-*, per RECONCILIATION.md finding (a)) to the five conformance checks built above, following the T-0343 drift-lock framework. Depends on all five checks plus T-0391 (arch-checks registry-domain reconciliation, which owns the SLH-* disposition slice).

<!-- ticket:T-0673 -->
```yaml
id: T-0673
title: 'registry: cross-file concept dedup - link cross_refs for the 10+ known-duplicate
  concepts, extend to a full pairwise scan'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0346
scope:
- docs/design/registry/**
- tests/unit/strata/**
acceptance:
- text: Given the 10 named concepts, when the registry is queried, then each has a
    reviewed cross_refs linkage (either merged to one canonical id or explicitly justified
    as distinct)
  evidence: []
- text: Given a full pairwise scan over all 1950 entries, when it completes, then
    any newly found split is either linked or recorded as a residual finding, not
    silently dropped
  evidence: []
threat: null
component: null
```
RECONCILIATION.md finding (b): Circuit Breaker, Bulkhead, Idempotent Receiver, Anti-Corruption Layer, Value Object, Repository, Timeout, Singleton, Anemic Domain Model, Saga each currently exist as 2-4 unlinked file-local ids (cross_refs: []) across arch-checks.yaml/patterns.yaml/system-design.yaml/supply-chain.yaml. Make a reviewer judgment call per concept (one canonical id with facets, vs genuinely distinct checkable claims that share a name) and wire cross_refs accordingly. Then extend the spot-check to a full pairwise name-similarity scan over all 1950 entries (the prior pass explicitly did not do this) to surface additional splits beyond the 10 named.

<!-- ticket:T-0675 -->
```yaml
id: T-0675
title: 'registry: resolve compliance/secrets/pii leaf-granularity gap (599+56+44 leaf
  items)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0388
- T-0386
- T-0387
parent: T-0346
scope:
- docs/design/compliance-corpus.md
- docs/design/secrets-pii-corpus.md
- docs/design/registry/**
acceptance:
- text: Given the decision made, when RECONCILIATION.md is reread, then finding (f)
    is marked resolved with either the leaf-level registry built or a written granularity-freeze
    rationale
  evidence: []
threat: null
component: null
```
RECONCILIATION.md finding (f): compliance-corpus.md/secrets-pii-corpus.md are unit-granular (27+3+7 = 37 entries) but their own TOTAL_LEAF_CONTROLS_ENUMERATED fields imply 599+56+44 = 699 individually addressable leaf items that were never actually enumerated row-by-row in the source docs. Make an explicit decision: either (a) expand the source docs to real leaf-level enumeration with stable ids and rebuild the registry at that granularity, or (b) formally freeze at unit granularity with a written rationale recorded in registry/README.md and RECONCILIATION.md, closing the gap as a documented decision rather than an open question. Depends on the three unit-granularity reconciliation tickets having landed.

<!-- ticket:T-0678 -->
```yaml
id: T-0678
title: 'registry: cross-corpus totality meta-test - zero unlinked duplicate concepts,
  zero prose-only entries (T-0346 close condition)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0673
- T-0384
- T-0389
- T-0390
- T-0391
- T-0392
parent: T-0346
scope:
- docs/design/registry/**
- src/frob/strata/**
- tests/unit/strata/**
acceptance:
- text: Given the full registry, when the meta-test runs, then every cross_refs-eligible
    concept has exactly one canonical id or a recorded justification for staying split
  evidence: []
- text: Given a future corpus doc edit that adds a table row with no matching registry
    id, when the meta-test runs, then it fails the build
  evidence: []
threat: null
component: null
```
Epic close condition. Extends T-0343's per-domain drift-lock with a cross-corpus check over all 11 source docs / 1950+ registry entries: (1) no named concept may exist under >=2 unlinked file-local ids (uses cross_refs, closes finding (b) permanently going forward); (2) no corpus table row may exist with no registry id (closes finding (a) permanently -- the 3 prose-only docs already retrofitted must never regress). Depends on the dedup pass and all five domain-reconciliation tickets (weaknesses/supply-chain/evasion/arch-checks/system-design) landing so the meta-test has a fully-dispositioned base to run against.

<!-- ticket:T-0679 -->
```yaml
id: T-0679
title: 'flake quarantine: recent-tail-window variant of is_hard_regression'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0636
parent: T-0575
scope:
- src/frob/testing/_stability.py
- tests/unit/testing/test_stability.py
- docs/modules/testing.md
acceptance:
- text: GIVEN history [P] followed by K consecutive fails under live quarantine WHEN
    evaluate_gate and hard_regression_alarms run THEN the gate stays red and the alarm
    fires
  evidence: []
threat: null
component: null
```
T-0636's is_hard_regression checks all-fail over the ENTIRE bounded 20-run window, so a single stale pass anywhere in the window defeats detection for up to 19 subsequent all-fail runs -- a real hard regression stays promoted and un-alarmed that whole time. Add a recent-tail rule (last K runs all-fail, K configurable, default ~5) alongside or replacing the whole-window rule, with tests covering the one-old-pass-then-long-fail-tail case T-0636's reviewer identified. Update docs/modules/testing.md semantics. NOTE: the hard-regression CLI/alarm wiring is T-0635's scope; T-0636's a lost draft (its scope is covered by T-0635) duplicated it and needs no refile.

<!-- ticket:T-0680 -->
```yaml
id: T-0680
title: 'registry: route out_of_scope disposition reason through T-0382 caught_by verification'
state: queued
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0383
scope:
- src/frob/gates/_registry_exhaustiveness.py
- docs/design/registry/**
- tests/test_registry_exhaustiveness.py
acceptance:
- text: GIVEN a registry entry with out_of_scope disposition whose reason names no
    catching control and is not a substantive reasoned-none WHEN the registry gate
    runs THEN a finding fires naming the entry
  evidence: []
threat: null
component: null
```
The one remaining caught_by gap after T-0382/T-0383: registry-YAML out_of_scope:<reason> disposition strings are a separate surface from the strata model objects and never pass through T-0382's caught_by verification -- a registry entry can be excused with a reason that names no catching control and nothing checks it. Route those disposition reasons through the same verification (or an equivalent registry-side rule) so an out_of_scope registry entry either names a real catching control or carries a substantive reasoned-none, mechanically checked. Was T-0680 (ex-draft, id lost at land) in T-0383's worktree; drafts do not survive land (T-0637).

<!-- ticket:T-0681 -->
```yaml
id: T-0681
title: 'arch TS adapter phase 2: interface/type-alias/enum declarations + TSX'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0611
parent: T-0329
scope:
- src/frob/arch/_normalized.py
- src/frob/arch/_typescript.py
- tests/unit/test_arch.py
acceptance:
- text: GIVEN TS fixtures with interface, type alias, enum, and a TSX component WHEN
    TypeScriptAdapter.adapt runs THEN each is represented in the NormalizedModule
    and asserted by a test
  evidence: []
threat: null
component: null
```
T-0611's TypeScriptAdapter cannot map interface_declaration, type_alias_declaration, enum_declaration, or TSX/JSX -- no NormalizedModule entity exists for them yet. Extend the model (likely a NormalizedTypeDecl entity or fields on NormalizedClass) keeping _normalized.py tree_sitter-free, then map the four constructs in _typescript.py with fires/near-miss tests. Was T-0681 (ex-draft, id lost at land) in T-0611's worktree; drafts do not survive land until T-0637's fix lands.

<!-- ticket:T-0683 -->
```yaml
id: T-0683
title: 'docs: state that the drift gate always evaluates regardless of --only/narrowed
  gate selection (T-0265 semantics)'
state: queued
kind: docs
origin: agent
created: '2026-07-22'
priority: low
parent: T-0265
scope:
- docs/modules/gates.md
acceptance:
- text: GIVEN docs/modules/gates.md WHEN a reader checks --only semantics THEN the
    always-evaluated drift behavior is documented with the T-0265 rationale
  evidence: []
threat: null
component: null
```
T-0265 made _build_jobs fold drift into every run_gates call so narrowed selections agree with full runs (DRIFT002 is authoritative for edge-endpoint resolution). docs/modules/gates.md does not yet say drift always evaluates under --only; T-0265's reviewer flagged the doc gap. One short note under the --only description. Also note here for the record: the _run_combined_jobs ProcessPoolExecutor-inside-ThreadPoolExecutor fork hazard disclosed in T-0265's Done report is T-0581's territory (its redesign should eliminate it).

<!-- ticket:T-0684 -->
```yaml
id: T-0684
title: implement checkable-control enforcement for CWE weakness registry Top-25-class
  units
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/vet/
- src/frob/strata/
- docs/design/registry/weaknesses.yaml
threat: null
component: null
```
Standing home for 27 weaknesses.yaml CWE entries (CWE-20,22,77,78,79,89,94,119,125,190,269,276,287,306,352,362,416,434,476,502,639,787,798,862,863,918,922 -- overlapping the CWE Top-25/OWASP classic set, relevant to T-0674's Top-25 tension follow-up) whose controls are machine-checkable but not yet enforced by any gate/check. They previously carried deferred:T-0384 (the reconciliation ticket itself) -- a self-reference that would orphan them the moment T-0384 closed; T-0384's pass re-pointed them here. Each entry needs either a real enforcing check (then flip to handled_by:<rule-id>) or a reasoned out_of_scope/not-checkable disposition.

<!-- ticket:T-0685 -->
```yaml
id: T-0685
title: 'exception may-raise analysis: per-function may-raise sets with fail-closed
  unknowns (parent)'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- docs/design/**
acceptance:
- text: GIVEN the children closed WHEN frob check runs on a fixture with a known exception
    surface THEN the may-raise sets are queryable and every child gate/advisory fires
    per its own acceptance
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22: complement the errors-as-values preference with an EXHAUSTIVE static exception story. Compute a per-function may-raise set: explicit raise sites + resolved callees' sets propagated over the call graph + curated builtin-raiser table (dict[k]->KeyError, int()->ValueError, attr->AttributeError, ...). Unresolvable calls (dynamic dispatch, getattr, plugins) contribute an Unknown marker FAIL-CLOSED, per the T-0339 doctrine -- reuse its per-language resolvers (T-0659..T-0664), do not build a second binding analysis. Ubiquitous asynchronous exceptions (MemoryError, KeyboardInterrupt, SystemExit) live in a separate always-possible tier that exhaustiveness never demands enumerated (only a boundary catch-all may discharge). The normalized model's NormalizedRaise/NormalizedCatch events (T-0609..T-0612) are the substrate. Children: Python may-raise resolver, C++ may-throw + noexcept obligation, exhaustive-handling gate + errors-as-values advisory. Umbrella closes when children close.

<!-- ticket:T-0686 -->
```yaml
id: T-0686
title: 'python may-raise resolver: raise sites + callee propagation + builtin-raiser
  table, Unknown fail-closed'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0659
parent: T-0685
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
acceptance:
- text: GIVEN a fixture chain f->g->h where h raises ValueError and g catches it and
    f calls dict subscript WHEN the resolver runs THEN f's may-raise is exactly {KeyError}
    plus the ubiquitous tier and a fixture with an unresolvable call yields Unknown
  evidence: []
threat: null
component: null
```
Child 1 of T-0685. Over the normalized model (NormalizedRaise/NormalizedCall) plus T-0659's sound Python name-binding: per-function may-raise = own raises (resolve the raised type where statically evident; bare raise re-raises the active set) + union of resolved callees' sets (fixpoint over the call graph, cycles converge) + builtin-raiser table for subscript/attribute/arithmetic/casts/io. Unresolved callee -> Unknown, fail-closed. except clauses SUBTRACT what they catch (mind exception hierarchies: except Exception catches ValueError). Async-ubiquitous tier (MemoryError/KeyboardInterrupt/SystemExit) tracked separately. Deliverable is the queryable analysis + tests on hand-built fixtures with known surfaces; gates/advisories are T-0688's job.

<!-- ticket:T-0687 -->
```yaml
id: T-0687
title: 'c++ may-throw analysis: throw sites + callee propagation + noexcept hard-boundary
  obligation'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0662
parent: T-0685
scope:
- src/frob/arch/**
- src/frob/lang/**
- tests/unit/test_arch.py
acceptance:
- text: GIVEN a noexcept function calling a may-throw callee WHEN the analysis runs
    THEN an error finding names the call site AND a try/catch(...) boundary discharges
    Unknown
  evidence: []
threat: null
component: null
```
Child 2 of T-0685. Same may-set shape over the C++ tree-sitter parse: explicit throw + resolved-callee propagation + std-library thrower table (vector::at, new, stoi, ...). Virtual/indirect/function-pointer calls -> Unknown fail-closed (T-0665's obligation pattern). noexcept functions are HARD boundaries: a may-throw (or Unknown) call inside noexcept is an ERROR finding (std::terminate at runtime), not advisory. Document that full soundness needs libclang eventually; the tree-sitter approximation with fail-closed unknowns is the deliverable.

<!-- ticket:T-0688 -->
```yaml
id: T-0688
title: exhaustive-exception gate + errors-as-values advisory over may-raise sets
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0686
parent: T-0685
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/arch/**
scope_changes:
- op: add
  glob: src/frob/arch/**
  reason: the advisory half lives beside the T-0332 recommender in arch
  actor: logan
  at: '2026-07-22'
acceptance:
- text: GIVEN a boundary catching a strict subset of its guarded may-raise set WHEN
    the gate runs THEN the missing exception types are named; GIVEN a public raiser
    with unhandling callers WHEN arch advisories run THEN a Result recommendation
    fires with the raise sites
  evidence: []
threat: null
component: null
```
Child 3 of T-0685 (blocked by the python resolver landing; extend to C++ when its child lands). Two consumers of the may-raise sets: (1) EXHAUSTIVE-HANDLING gate: a try block or declared boundary function is exhaustive iff every member of the guarded may-raise set is caught, explicitly declared-propagated (a frob: directive), or waived with reason; Unknown in the set forces a catch-all or fixing the unresolvable call -- silent non-exhaustiveness impossible. (2) ERRORS-AS-VALUES advisory (suggestion severity, T-0332 noise discipline): a public function with non-empty recoverable may-raise whose callers do not handle it recommends typani Result[T,E], with the raise-site list as the sketch; exceptions remain sanctioned for programmer bugs (assert/invariant class exempt). Wire into T-0623's fallibility family; register rule ids in _KNOWN_GATE_RULES; docs in the same change.

<!-- ticket:T-0689 -->
```yaml
id: T-0689
title: 'python may-raise: ctypes/cffi/C-extension call boundaries are opaque -- Unknown
  fail-closed unless declared'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0686
parent: T-0685
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
acceptance:
- text: GIVEN a call into an undeclared ctypes function WHEN the resolver runs THEN
    Unknown appears in the caller's may-raise set; GIVEN the same call with a frob:raises
    declaration THEN the declared set substitutes
  evidence: []
threat: null
component: null
```
User mandate: account for the builtins AND the ctypes-ish surface we know. Calls crossing into ctypes, cffi, or compiled C-extension modules (module has no Python source in the graph, or known binary-ext loader) contribute Unknown to the caller's may-raise set fail-closed. EXCEPTION: a boundary covered by a frob:raises declaration (sibling ticket) substitutes its declared set. Curate the stdlib C-extension raiser table for modules we know (json.loads -> JSONDecodeError, sqlite3 -> sqlite3.Error family, struct -> struct.error, ...) so common cases resolve precisely instead of Unknown.

<!-- ticket:T-0690 -->
```yaml
id: T-0690
title: 'frob:raises directive: declared exception surfaces at FFI boundaries, cross-checked
  where statically visible'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0686
parent: T-0685
scope:
- src/frob/graph/dsl.py
- src/frob/gates/**
- src/frob/arch/**
- strata-core/**
- docs/modules/gates.md
acceptance:
- text: GIVEN a pyo3 function whose Rust side constructs PyValueError but whose frob:raises
    omits it WHEN the gate runs THEN a drift error names both sides; GIVEN a ctypes
    boundary with no frob:raises THEN a finding demands the declaration
  evidence: []
threat: null
component: null
```
User mandate: propagate exception info across the FFI boundary and enforce declaration wherever possible. Three tiers by static visibility: (1) OUR pyo3 crates (strata_core/frob_core): the Rust side IS visible -- PyResult error constructions, explicit PyErr types, panic! -> pyo3 PanicException; parse the Rust side (Rust adapter already parses these crates) and CROSS-CHECK the Python-side frob:raises declaration against the observed Rust-side set; drift = gate error. (2) ctypes/extern-C: no exception propagation exists (errno/return codes; a C++ exception crossing extern C is terminate/UB -- flag that pattern in our C++ as an ERROR); declaration is the only truth -- enforce every ctypes boundary in our repos carries frob:raises (declaring the empty set + errno convention is valid). (3) third-party compiled modules: declaration optional; Unknown otherwise. Grammar mirrors frob:deprecated (T-0576 precedent); register rule ids; docs same change.

<!-- ticket:T-0691 -->
```yaml
id: T-0691
title: 'decision: next language-adapter tier (Go, Java, C#) -- demand-driven per estate
  + TIOBE/Innovation Graph'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: low
parent: T-0329
scope:
- docs/design/**
acceptance:
- text: GIVEN the estate language survey WHEN this ticket closes THEN docs/design
    records the chosen next adapter tier with rationale and per-language tickets exist
    for chosen languages only
  evidence: []
threat: null
component: null
```
User question 2026-07-22: should we expand supported languages per github.com Innovation Graph global metrics and the TIOBE index? Current coverage: Python, TypeScript/JS, Rust, C, C++ (+ Kotlin grammar wired, adapter pending T-0614). By both indexes the largest uncovered languages are Java, Go, C#, then PHP/Ruby/Swift. RECOMMENDATION recorded here: expand DEMAND-DRIVEN, not index-driven -- the adapter protocol (T-0609) makes each language a bounded ~1-session ticket, so speculative adapters are cheap to add when a real repo in the estate (or a user project) needs one, and unexercised adapters are exactly the catalogued-but-unenforced dead weight this repo's doctrine forbids. This DECISION ticket closes by recording the chosen next tier (or explicitly none-for-now) in docs/design/ after checking the 9-repo estate's actual language mix; implementation tickets get filed per language only when chosen.

<!-- ticket:T-0693 -->
```yaml
id: T-0693
title: 'concurrency hazard analysis: structural deadlock/race/event-loop checks +
  model-mismatch advisory (parent)'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- docs/design/**
acceptance:
- text: GIVEN the children closed WHEN frob check runs on fixtures reproducing each
    hazard class THEN each fires per its own acceptance
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22: static checks for multiprocessing/threading/async code. Not a soundness claim -- a STRUCTURAL may-analysis over the call graph + normalized model (T-0609..T-0612) catching the classes that actually bite, fail-closed on opaque dispatch per T-0339 doctrine. Field motivation from this very session: the ProcessPoolExecutor-inside-ThreadPoolExecutor deadlock (T-0265 disclosure, T-0581 structural fix, T-0692 CI guard) ate a 6h CI job. Children: lock-order graph, fork/pool structural hazards, async event-loop hazards, shared-mutable-state approximation, IO/CPU-bound model-mismatch advisory. Umbrella closes when children close.

<!-- ticket:T-0694 -->
```yaml
id: T-0694
title: 'lock-ordering graph: cyclic acquisition order across call paths = potential-deadlock
  finding'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: medium
parent: T-0693
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
acceptance:
- text: GIVEN two functions acquiring locks A-then-B and B-then-A WHEN the check runs
    THEN a finding names both call paths; GIVEN consistent global ordering THEN silence
  evidence: []
threat: null
component: null
```
Child 1 of T-0693. Track with-statement (and explicit acquire/release) nesting of statically-identifiable lock objects (module/class-level threading.Lock/RLock/Semaphore, multiprocessing locks, anyio/asyncio locks); build the acquisition-order graph across call paths via the call graph; a cycle = potential deadlock naming both paths and both locks. Unresolvable lock identity -> advisory-tier note, fail-closed philosophy without drowning signal. Fixtures: the classic AB/BA two-lock deadlock fires; single global lock ordering does not.

<!-- ticket:T-0696 -->
```yaml
id: T-0696
title: 'async event-loop hazards: blocking calls in async def, nested run_until_complete,
  un-awaited coroutines'
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: T-0693
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
acceptance:
- text: GIVEN time.sleep inside async def WHEN the check runs THEN a finding suggests
    asyncio.sleep/to_thread; GIVEN an un-awaited coroutine call THEN a finding names
    the site
  evidence: []
threat: null
component: null
```
Child 3 of T-0693. Curated blocking-call table (time.sleep, requests.*, urllib, sync open/read on large paths, subprocess.run, .result() on futures) flagged when reachable inside async def without run_in_executor/to_thread dispatch; run_until_complete/asyncio.run reachable inside a running-loop context; coroutine-constructing call whose result is neither awaited nor gathered nor stored (un-awaited coroutine); async def containing zero awaits (feeds the model-mismatch advisory too). Table extensible via frob.toml like other curated tables.

<!-- ticket:T-0697 -->
```yaml
id: T-0697
title: 'shared-mutable-state race approximation: unguarded writes on thread/task-reachable
  paths'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: medium
parent: T-0693
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
acceptance:
- text: GIVEN a module-level dict written from a thread-submitted function with no
    enclosing lock WHEN the check runs THEN an advisory names the write site and the
    spawn path; GIVEN the same write under a "with lock:" block THEN silence
  evidence: []
threat: null
component: null
```
Child 4 of T-0693. Approximate data-race detection: a WRITE to module-level or class-level mutable state (assignment, mutating method on list/dict/set) on a call path reachable from a thread target/executor submission/async task, where no lock acquisition encloses the write in that path's context, is an advisory finding (suggestion tier -- approximation, false positives possible; waivable with reason). Reuses the lock-identification machinery from T-0694 and thread-target reachability from T-0695. Single-process cousin of strata's distributed no-shared-mutable-state check (T-0656) -- coordinate rule naming, do not duplicate its model-level logic.

<!-- ticket:T-0698 -->
```yaml
id: T-0698
title: 'concurrency model-mismatch advisory: IO-bound vs CPU-bound classification
  vs chosen executor'
state: queued
kind: ux
origin: human
created: '2026-07-22'
priority: medium
parent: T-0693
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
acceptance:
- text: GIVEN a pure-arithmetic loop function submitted to ThreadPoolExecutor WHEN
    advisories run THEN a GIL-bound suggestion fires naming the loop; GIVEN a socket-read
    function under threads THEN silence
  evidence: []
threat: null
component: null
```
Child 5 of T-0693, the user's seem-IO-bound/seem-CPU-bound mandate. Classify each function from normalized-model events: IO-BOUND if dominated by curated IO calls (sockets/files/http/subprocess/db), CPU-BOUND if loop/arithmetic-dense with no IO, MIXED/UNKNOWN otherwise (advisories only fire on confident classifications -- T-0332 noise discipline). Advisories: CPU-bound work submitted to ThreadPoolExecutor or awaited in the event loop -> GIL-bound, suggest ProcessPool/native; trivially-small IO-bound tasks under ProcessPoolExecutor -> IPC overhead, suggest threads/async; async def with zero awaits (from T-0696) -> not actually async, suggest plain def; sequential awaits over independent IO -> suggest gather. Each advisory names the classification evidence (the dominating call sites), never a bare switch-your-model.

<!-- ticket:T-0700 -->
```yaml
id: T-0700
title: 'strata grammar: access modes + shared-resource/lease declarations for contention
  proofs'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- editors/**
- docs/strata/**
- tests/unit/strata/
acceptance:
- text: GIVEN two nodes with write-mode access to one resource and no arbiter WHEN
    sys checks run THEN a fail-closed error; GIVEN the same with a declared arbiter
    or read-only modes THEN the obligation discharges
  evidence: []
threat: null
component: null
```
Second half of the resource-contention mandate -- the grammar extension. Add: (1) access MODE on resource edges (owns/acl/stores gain mode=read|append|alpha|write|exclusive, default write for backward compat with current semantics -- decide and document). ALPHA SEMANTICS (user-specified 2026-07-22, the update/upgradeable-lock pattern): alpha declares INTEREST in a future writer lock; many writes need a read just before, so alpha sits between read and write. Compatibility matrix to encode and check: read+read OK; read+alpha OK (alpha never conflicts with readers); alpha+alpha CONFLICT (exactly one writer-intender per resource -- this is what prevents the two-readers-both-upgrading deadlock); alpha+write and write+anything CONFLICT; an alpha holder upgrades to write only once readers drain. (2) a shared-resource declaration with an ARBITER (resource NAME mode... arbitrated_by NODE|lock NAME) so two writers are provable-safe only through a declared arbiter/lease; (3) contention proof obligation: for every resource whose declared accessor modes violate the compatibility matrix (>1 writer-mode with no arbiter, OR >1 alpha declarant) a SYS error (fail-closed). parse.rs node/store symmetry per T-0261 precedent, tmLanguage update, docs/strata section, litmus fixtures. Field motivation: frob's own ledger-lock/refs-stash/info-exclude incidents -- repo-global resources with multiple writers and only convention as the arbiter. The mode-blind rules ship first in the sibling ticket; this upgrades them to mode-aware without renaming.

<!-- ticket:T-0701 -->
```yaml
id: T-0701
title: 'strata mode-conformance enforcement: prove each node''s code OBEYS its declared
  access mode (read/append/write/exclusive)'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0700
- T-0717
parent: T-0331
scope:
- src/frob/strata/**
- src/frob/vet/**
- tests/unit/strata/
acceptance:
- text: GIVEN a node declaring mode=read whose bound code opens the resource for writing
    WHEN sys checks run THEN a fail-closed error names the write site; GIVEN mode=exclusive
    with an access outside the arbiter context THEN an error names the unguarded path;
    GIVEN conforming code per mode THEN each discharges
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22: contention semantics are worthless unless ENFORCED -- a declared mode nothing verifies is the catalogued-is-not-enforced trap (T-0343 doctrine). For every node with code= bindings and a declared resource mode (T-0700 grammar), join the declaration against the code's OBSERVED effects (the T-0595 code-binding pattern, wired to production per T-0630; effect classification from the vet/T-0339 capability resolvers): READ = zero write-capable operations against the resource (write-mode opens, os.remove/rename, SQL DML, sends on the port) -- fail-closed on opaque access to the resource; APPEND = writes only via append-mode opens, no truncate/rewrite; ALPHA (update/upgradeable-lock intent, user-specified) = reads freely, but every observed WRITE against the resource must be provably preceded on the same path by an upgrade acquisition (alpha->write transition through the declared arbiter) -- a write reachable while still in alpha-only context fails closed; additionally the model-level alpha+alpha exclusion (at most one alpha declarant per resource) is checked at elaboration, and the code-level analysis flags the upgrade-deadlock ANTI-PATTERN (acquiring write while holding plain read on the same resource, the case alpha exists to prevent -- recommend alpha in the finding); WRITE = read+write allowed but only on declared paths (undeclared sibling access = finding); EXCLUSIVE = write conformance PLUS every observed access provably inside the declared arbiter/lease context (join T-0694's code-level lock identification with the model-level arbiter declaration; an access path outside the arbiter fails closed). Violations are SYS errors naming the node, the declared mode, and the offending observed operation. Litmus fixtures per mode, firing and clean.

<!-- ticket:T-0702 -->
```yaml
id: T-0702
title: 'strata grammar: demand declarations (users/rate) with flow propagation and
  fan-in summation'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- editors/**
- docs/strata/**
- tests/unit/strata/
acceptance:
- text: GIVEN two entry nodes declaring users 300k and 200k both flowing into one
    db resource WHEN elaboration runs THEN the db's aggregate demand is 500k and queryable;
    GIVEN no demand declared THEN the resource reports demand-undeclared, not zero
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22 (starvation semantics prerequisite): the model has no notion of LOAD, so an exclusive lock and an exclusive lock behind 500k users look identical. Add: (1) demand declarations on entry nodes -- users N (steady population) and/or rate N per_s (arrival rate), parse.rs node/store symmetry per T-0261; (2) propagation: demand flows along existing Flow edges, SUMMING at fan-in, so any node/resource can be asked 'what aggregate demand reaches you' (elaboration-time computation, queryable like effects); (3) optional capacity/holding-time hints on resources and arbiters (capacity N, holds MS) with documented defaults; (4) tmLanguage + docs/strata section + litmus fixtures (propagation sums correctly across fan-in/fan-out, missing demand is distinguishable from zero demand). Consumers (utilization/starvation obligations) are the sibling ticket.

<!-- ticket:T-0703 -->
```yaml
id: T-0703
title: 'strata starvation/throughput obligations: serialization-point utilization,
  writer starvation, unbounded waits'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0700
- T-0702
parent: T-0331
scope:
- src/frob/strata/**
- tests/unit/strata/
acceptance:
- text: GIVEN 500k declared users flowing to a db with mode=exclusive and default
    holding time WHEN sys checks run THEN a utilization error fires showing the arithmetic;
    GIVEN the same db with demand undeclared THEN a fail-closed demand-undeclared
    finding; GIVEN a read-preferring lock with no alpha/fairness on a read-heavy resource
    THEN a writer-starvation advisory
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22: the 500k-users-vs-exclusive-write-lock case. Three obligation families over the T-0700 modes + demand grammar: (1) SERIALIZATION-POINT UTILIZATION: every effective-concurrency-1 point (exclusive mode, single arbiter, alpha-gated writer path) compares aggregate inbound demand x holding-time hint against capacity; over threshold = SYS error SHOWING THE ARITHMETIC in the finding (demand, holding time, resulting utilization/wait), not a vibe; an exclusive/arbitered resource with UNDECLARED upstream demand fails closed with demand-undeclared (the check cannot be silently skipped). Coordinate with T-0645 (SPOF -- a saturated single arbiter is quantitative SPOF) and T-0646 (backpressure -- what bounds the queue at the serialization point). (2) WRITER STARVATION policy: read-heavy resource whose declared lock discipline lets readers perpetually preempt the writer (plain RW preference, no alpha or fair-queuing declaration) = advisory recommending alpha (T-0700) or fair queuing, even at low utilization. (3) UNBOUNDED WAIT: lock/arbiter acquisition on a contended resource with no declared timeout joins the T-0640 timeout obligation family. Litmus fixtures per family, firing and clean.

<!-- ticket:T-0708 -->
```yaml
id: T-0708
title: 'native-missing fail-loud tests broken: SYS004 behavior drifted'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/strata/**
- tests/system/test_cli_native_missing.py
acceptance:
- text: GIVEN a repo with .strata files and no built native WHEN frob check runs THEN
    SYS004 fails loud AND both tests pass
  evidence: []
threat: null
component: null
```
CI triage 2026-07-22: tests/system/test_cli_native_missing.py x2 fail on current main (test_check_fails_loud_with_sys004_when_strata_present, test_check_unaffected_when_no_strata_files). Investigate whether the native-staleness/fingerprint work (T-0570 doctor, _native_staleness) changed the SYS004 fail-loud contract or the tests' fixtures rotted; fix whichever is wrong -- the contract (a missing native with strata files present must fail LOUD, not silently skip) must hold.

<!-- ticket:T-0709 -->
```yaml
id: T-0709
title: 'runtime hot-graph: section-level timing sketches across the repo (parent)'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/perf/**
- src/frob/stats/**
- docs/design/**
acceptance:
- text: GIVEN the children closed WHEN the perf harness runs THEN a queryable hot-graph
    exists under .frob at sub-100KB with per-section decile readouts
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22: auditing/advisories for slow operations. Build a repo-wide hot-graph: per-section timing (major loop/branch bodies, external call edges, internal functions) collected at harness/test time, stored compactly, queryable, with advisories and regression ratcheting. STORAGE DECISION (user-driven): NOT normal distributions (heavy-tailed/multi-modal latency destroys mean/sigma) and NOT raw traces (megabytes) -- mergeable log-bucket quantile sketches (DDSketch-style, tunable relative-error alpha, ~hundreds of bytes/section), decayed merge = prior->update semantics, deciles read off at query time. Attribution WITHOUT sys.settrace: sampling collector + the normalized model's known line spans (T-0609..) map each stack sample to its enclosing section statically. Children: collector+attribution, sketch store, query surface, advisories+ratchet. Builds on src/frob/perf (existing harness/profile artifact, T-0582) and src/frob/stats -- extend, do not fork.

<!-- ticket:T-0711 -->
```yaml
id: T-0711
title: 'hot-graph sketch store: log-bucket quantile sketches with decayed merge in
  .frob sqlite'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0709
scope:
- src/frob/stats/**
- src/frob/perf/**
- tests/unit/perf/
acceptance:
- text: GIVEN bimodal latencies (1ms and 100ms modes) WHEN sketched at alpha=2 percent
    THEN p10/p50/p90 read back within relative error and the serialized sketch is
    <1KB; GIVEN repeated runs THEN decayed merge converges and the store stays under
    its cap
  evidence: []
threat: null
component: null
```
Child 2: the user-specified compact encoding. DDSketch-style log-scale bucket sketch per section/edge: tunable relative-error alpha (frob.toml, default ~2 percent), mergeable, serialized to .frob sqlite keyed by stable section id (symbol digest + section kind + span -- survives line drift via the existing symbol digest machinery). prior->update = merge(current_run_sketch, decay(stored_prior, half_life_runs)); deciles/any-quantile computed at read time, never stored. Size budget enforced: a repo-wide store cap (~100KB default) with eviction of coldest sections, so it structurally cannot grow to megabytes. Property tests: merge associativity, quantile relative-error bound holds under adversarial bimodal inputs (the anti-normal-distribution case).

<!-- ticket:T-0712 -->
```yaml
id: T-0712
title: hot-graph query surface + slow-operation advisories + perf regression ratchet
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0710
- T-0711
parent: T-0709
scope:
- src/frob/perf/**
- src/frob/app/**
- src/frob/gates/**
- docs/modules/perf.md
acceptance:
- text: GIVEN a section whose p90 regresses beyond tolerance vs the stored prior WHEN
    frob check runs with the ratchet enabled THEN a PERF finding names the section
    and both decile sets; GIVEN a loop dominated by an external call THEN an advisory
    fires with the edge's deciles
  evidence: []
threat: null
component: null
```
Child 3: consumers. (1) QUERY: frob perf hot [--top N --by p90|p50xcount] renders the hot-graph (section, callee edge, decile readout, sample count) from the sketch store; MCP tool mirror for agents. (2) ADVISORIES (suggestion tier, T-0332 noise discipline): external call edge dominating a loop body's time -> batch/cache/move-out-of-loop suggestion naming the edge and its deciles; nested-loop section hot AND upstream of a fan-in -> complexity suspect; section p90 >> p50 (heavy tail) -> variance advisory naming likely modes. (3) REGRESSION RATCHET: current run sketch vs stored prior -- quantile shift beyond alpha + configured tolerance = PERF finding naming the section and both deciles (ratchet-pool style per T-0569/T-0594 precedent, baseline-old error-new).

<!-- ticket:T-0713 -->
```yaml
id: T-0713
title: Audit COV007 dedup passes (T-0524) for over-pruned extending-guide anchors
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/**
threat: null
component: null
```
found while working T-0706: 2642c5f3 (T-0524) removed the docs/guides/extending/capability-registry.md#capability-registry frob:doc anchor above DANGEROUS_OPERATIONS in src/frob/vet/_capability_registry.py as a supposed COV007 duplicate, but no other anchor in the file carried the extending-guide fragment -- broke tests/unit/test_extending_guides_complete.py silently until T-0706 caught and restored it (waived SCOPE001 there). Audit other T-0524 COV007 dedup commits for the same over-pruning pattern against docs/guides/extending/registry_of_registries.json rows.

<!-- ticket:T-0714 -->
```yaml
id: T-0714
title: 'ticket doable: relocate stale-lease/scope diagnostics to frob check (doable
  output stays clean)'
state: queued
kind: ux
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/app/**
- docs/modules/tickets.md
acceptance:
- text: GIVEN 5 stale lease files WHEN frob ticket doable runs THEN the queue prints
    with at most one summary line about leases AND frob check (or doctor) reports
    each stale lease once with its path and remedy
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22: frob ticket doable currently emits a wall of per-invocation diagnostics (stale-lease warnings -- 'T-XXXX lease references a worktree that no longer exists, treating as stale, skipped' -- repeated for every stale lease on EVERY queue query; observed 5 leases x repeated blocks flooding the session-start listing) plus scope/lease conflict notes. Doable's job is a clean ordered queue listing. Move the diagnostics: (1) doable emits the list only (a single summary line like 'N stale leases skipped, see frob check' is acceptable); (2) a check gate (LEASE001-style, warning tier) or the doctor reports stale leases, lease-worktree mismatches, and scope-conflict details ONCE with remediation (the lease file paths to clean); (3) log-level discipline per T-0202/T-0235 precedent -- the per-lease detail goes to DEBUG, not stdout.

<!-- ticket:T-0715 -->
```yaml
id: T-0715
title: 'ticket organization model: epic -> story -> ticket tiers, sprint grouping,
  and team views'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
acceptance:
- text: GIVEN an epic with two stories each with open leaf tickets WHEN frob ticket
    doable runs THEN only leaves surface and closing the epic is refused while descendants
    are open; GIVEN tickets assigned to sprint-1 WHEN frob ticket sprint show sprint-1
    runs THEN the commitment lists with state rollup and closed-count velocity
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22 (first filing -- nothing like this existed in the ledger): formalize dev-team organization on top of the existing parent/blocked_by graph. (1) TIERS: an explicit tier field (epic|story|ticket, default ticket) with structural rules -- epics parent stories, stories parent tickets, doable only ever surfaces leaf tickets, an epic/story cannot close while an open descendant exists (today's convention, enforced); migration: existing EPIC-titled tickets get tier epic mechanically. (2) SPRINTS: a sprint field (free-form label like 2026-W30 or sprint-14) settable at new/via frob ticket sprint assign; frob ticket sprint show SPRINT lists committed tickets with state rollup; frob ticket doable --sprint SPRINT restricts the queue to the commitment; velocity/burndown derived from ledger state-transition history (closed-per-sprint counts), no new storage. (3) TEAM VIEWS: doable already orders by priority/age -- add --by-parent grouping so a story's remaining leaves display together (the user's pop-the-whole-stack-not-just-the-top concern). Keep the ledger format backward compatible (absent fields default); single-writer CLI discipline throughout. Coordinate with T-0571 (review records) and T-0573 (fleet routing) -- sprint labels should be routable cross-repo via fleet in a follow-up, note it, do not build it here.

<!-- ticket:T-0718 -->
```yaml
id: T-0718
title: 'check: project-type detection reports ''unknown'' when a fixture has no pyproject.toml,
  unrelated to git'
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/app/**
- tests/system/test_cli_check.py
- tests/system/test_cli_perf.py
threat: null
component: null
```
Found while working T-0705. tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output, tests/system/test_cli_check.py::TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested, and tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero all fail with CHECK001 'unknown project type: 'unknown' (no dispatchable language stage)' even though each fixture DOES git init + commit (so this is not the T-0705 git-ls-files mechanism at all). Each of these fixtures writes a bare .py file with no pyproject.toml. Project-type detection (src/frob/app/**, exact site not yet located) appears to require pyproject.toml presence rather than falling back to extension-based detection when only .py files are tracked. Investigate src/frob/app/config.py's project-type resolution and either fix the fixtures (add a pyproject.toml) or fix the detector, whichever is the real contract.

<!-- ticket:T-0719 -->
```yaml
id: T-0719
title: 'check: COV002/SCOPE001/TODO001 hard-error on a genuinely git-less root, not
  just a real repo''s bad diff'
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/gitio.py
- src/frob/gates/__init__.py
threat: null
component: null
```
Found while working T-0705. `_load_diff`'s diff_load_failed classification (T-0550) does not distinguish 'root is not a git repository at all' (GitError.NotARepo-shaped, e.g. a one-off frob check <path> on a plain filesystem directory) from 'a real git repo's working_diff genuinely failed' (bad --base, detached HEAD). Both currently hard-error COV002/SCOPE001/TODO001 identically. This dominates ~9 of T-0705's originally-reported ~12 system-test failures in tests/system/test_cli_check.py (test_clean_code_exits_zero, test_skip_ruff, test_skip_exports, test_check_skip_from_frob_toml, test_scoped_docanchor_matches_unscoped, test_only_gates_reports_violation_with_remedy, test_clean_ts_passes_tsc) -- these fixtures never call git init, so working_diff fails not because a real diff is broken but because there is no repo at all. T-0705's scope (the 4 named git-ls-files gates) was fixed and does not touch this gitio.py/T-0550 mechanism; this ticket tracks whether a genuinely-no-repo root should be treated as an empty/clean diff (skip diff-gates) rather than the loud diff_load_failed violation, without weakening the T-0550 protection against a REAL git failure inside an actual repo.

<!-- ticket:T-0720 -->
```yaml
id: T-0720
title: Add pytest.mark.timeout overrides to slow system tests
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- tests/system/**
threat: null
component: null
```
T-0692 added a global 120s/thread pytest-timeout default (pyproject.toml addopts). tests/system/test_scaffold_dx.py (pytest.mark.slow, spawns uv sync + a real venv + full lint/typecheck/test/frob-check pipeline) legitimately runs well over 120s and needs an explicit @pytest.mark.timeout(N) override (and an audit of any other tests/system/** file that might exceed 120s) so it does not start failing under the new default. Out of T-0692's docs/guides+config-only scope; filed per that ticket's Done report.

<!-- ticket:T-0721 -->
```yaml
id: T-0721
title: implement checkable-control enforcement for SC-* supply-chain registry entries
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/vet/**
- docs/design/registry/supply-chain.yaml
threat: null
component: null
```
Standing home for the 39 supply-chain.yaml entries whose controls previously carried deferred:T-0389 (the reconciliation ticket itself) -- a self-reference that would orphan them the moment T-0389 closed; T-0389's pass re-pointed them here. Each entry needs either a real enforcing check in src/frob/vet/ (then flip to handled_by) or a reasoned out_of_scope disposition (many require external network/registry data -- checkability tag requires-external-data -- and are legitimate deferrals to future external-data-fetching work, not silent drops).

<!-- ticket:T-0722 -->
```yaml
id: T-0722
title: implement SYS/REL checkable-control enforcement for the 49 unresolved system-design
  registry entries
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/strata/**
- docs/design/registry/system-design.yaml
threat: null
component: null
```
Standing home for the 49 system-design.yaml entries whose controls previously carried deferred:T-0392 (the reconciliation ticket itself) -- a self-reference that would orphan them the moment T-0392 closed; T-0392's pass re-pointed them here. Each entry needs either a real enforcing SYS2xx/REL2xx check in src/frob/strata/ (then flip to handled_by) or a reasoned out_of_scope/duplicate_of disposition. Related to the T-0331 systems-checks epic and its T-0658 N:M coverage close condition (which is itself blocked by T-0392) -- once this ticket's entries get real checks, T-0658's coverage math should account for them the same way it accounts for the T-0331-deferred 56.

<!-- ticket:T-0723 -->
```yaml
id: T-0723
title: 'lang: wire kotlin into central dispatch (_EXTENSION_TABLE + RawSymbol walker
  + COMMENT_TYPES)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0614
parent: T-0329
scope:
- src/frob/lang/**
- tests/unit/test_lang_kotlin.py
acceptance:
- text: GIVEN a repo with a .kt file WHEN frob check runs THEN the file parses into
    the symbol graph (no KeyError) and its symbols appear in frob map output
  evidence: []
threat: null
component: null
```
T-0614's KotlinAdapter works standalone but .kt/.kts files are invisible to parse_file/frob check: _EXTENSION_TABLE lacks the extensions and _extract.py's _WALKERS dict-subscript (line ~91, no fallback) would KeyError if the table alone were wired. Deliver the RawSymbol walker for kotlin (mirroring the TS/Rust walkers in _extract.py), COMMENT_TYPES entry, and the extension-table wiring together, with tests proving a real .kt file flows through parse_file into the graph. Was T-0723 (ex-draft, id lost at land) (prose-only) in T-0614's Done report.

<!-- ticket:T-0725 -->
```yaml
id: T-0725
title: 'strata: export golden fixtures (k8s/seccomp/iam) drifted from design/frob.strata
  after fleet flows landed'
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- tests/unit/strata/test_export_golden.py
- tests/unit/strata/golden/**
threat: null
component: null
```
found while working T-0699: tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s/test_seccomp/test_iam fail on a clean worktree at main tip (e2f38a51, no T-0699 changes involved) -- design/frob.strata gained fleet node/flows (T-0614 era merge) but the committed golden JSON fixtures were not regenerated to match. Pre-existing, unrelated to T-0699's SYS2xx resource-contention work; regenerate the golden fixtures or fix whatever drifted.

<!-- ticket:T-0727 -->
```yaml
id: T-0727
title: 'arch: PythonAdapter never detects class-level annotated fields (_py_class_fields
  gates on a nonexistent expression_statement wrapper)'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0329
scope:
- src/frob/arch/_python.py
- tests/unit/test_arch.py
acceptance:
- text: GIVEN class Foo with an annotated field WHEN PythonAdapter.adapt runs THEN
    the field appears in NormalizedClass.fields AND the T-0615 waiver test is updated
    to assert parity
  evidence: []
threat: null
component: null
```
Found while working T-0615 (four-way equivalence meta-test). PythonAdapter._py_class_fields (src/frob/arch/_python.py) gates on 'if c.type != "expression_statement": continue' over a class body's named_children, expecting a class-level annotated assignment to be wrapped in an expression_statement node. In practice tree-sitter-python's grammar yields the assignment node directly as a named child of the class block, with NO expression_statement wrapper. Concrete repro: PythonAdapter().adapt(...) on 'class Foo:\n    x: int = 0\n' returns classes[0].fields == [] every time -- confirmed directly against the adapter, not just inferred. No existing test caught this because TestPythonAdapter's real-fixture tests never assert on .fields via the adapter itself (only a hand-built NormalizedField construction test exists, bypassing the adapter). T-0615's tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_python_field_detection_is_a_documented_waiver currently PINS this broken behavior as a documented waiver (asserting derived.fields == []) -- fixing this ticket must also update/remove that waiver test to assert real parity with TS/rust/kotlin (which all capture this shape via their own adapters).

<!-- ticket:T-0730 -->
```yaml
id: T-0730
title: 'gates: consume vitest/ctest collector node ids in _load_tests/_valid_edges,
  retire the ts/c/cpp structural fallback'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0587
scope:
- src/frob/gates/**
- tests/test_gates.py
acceptance:
- text: GIVEN a vitest project with a frob:tests directive naming a real vitest test
    WHEN gates run THEN the edge resolves against the collected id and the structural
    fallback no longer credits unverified ts edges
  evidence: []
threat: null
component: null
```
T-0587 built real vitest/ctest collectors (collect_ts_tests, collect_cpp_tests in src/frob/testing/_collect.py, exported from frob.testing) but left frob.gates untouched (out of T-0587's declared scope, src/frob/testing/ only). This ticket wires collect_ts_tests/collect_cpp_tests into frob.gates test-evidence loading (_load_tests, alongside collect_python_tests/collect_rust_tests) so frob:tests directives on TS/C/C++ resolve against REAL collected node ids, and retires _edge_is_native_unverified's structural name/path fallback for those languages once real collection exists (per T-0552's original plan).

<!-- ticket:T-0735 -->
```yaml
id: T-0735
title: 'frob natives build: frob-owned native compilation with shared cache -- Makefiles
  become one-line shims (parent)'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: high
parent: null
scope:
- src/frob/**
- docs/**
acceptance:
- text: GIVEN any frob-enabled repo with [natives] WHEN uv run frob natives build
    runs THEN natives compile with the shared per-clone cache and the repo Makefile
    contains no cache logic
  evidence: []
threat: null
component: null
```
User directive 2026-07-22: T-0732's shared CARGO_TARGET_DIR fix lives in THIS repo's Makefile -- wrong layer; fix ALL repos structurally. frob.toml [natives] already declares the native crates (load_natives); the build logic belongs in frob: a "frob natives build" subcommand that does what make core does (maturin develop per declared native) WITH the shared-cache mechanism (git-common-dir keyed CARGO_TARGET_DIR, cargo's own locking -- T-0732's verified design) built in. Every repo's Makefile core target becomes "uv run frob natives build" -- one line, zero per-repo cache logic, upgraded by upgrading frob. Doctor integration: the existing native-staleness fingerprint check points at the new command as remedy. Children: (1) the subcommand + this repo's Makefile shim conversion; (2) scaffold template + conformance drift check; estate rollout via fleet at close.

<!-- ticket:T-0738 -->
```yaml
id: T-0738
title: 'worktree warm pool: frob scaffold pool N pre-warmed worktrees with background
  refresh'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0732
scope:
- src/frob/scaffold/**
- Makefile
- docs/guides/**
acceptance:
- text: GIVEN a warm pool of N WHEN an agent leases a worktree THEN it starts with
    natives built and main current, and the pool refills in the background
  evidence: []
threat: null
component: null
```
Part 2 of T-0732 (part 1, the shared cargo cache, landed 30.4s->11.4s): pre-create N worktrees with natives built + main merged; agents lease from the pool; a background refresh re-warms after lands. Closes the residual per-worktree crate recompile cost (cargo keys by absolute path) by amortizing it ahead of dispatch. Coordinate with T-0736's scaffold-managed blocks and T-0735's frob natives build.

<!-- ticket:T-0739 -->
```yaml
id: T-0739
title: 'typestate protocol enforcement: init/deinit, declared state machines, cleanup-on-all-paths
  (parent)'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: null
scope:
- src/frob/arch/**
- src/frob/graph/**
- docs/design/**
acceptance:
- text: GIVEN the children closed WHEN frob check runs on fixtures for each fragment
    THEN each child gate/advisory fires per its own acceptance
  evidence: []
threat: null
component: null
```
User mandate 2026-07-22: statically enforce system state protocols -- the *_init-never-called / *_deinit-never-called class, and generally functions valid only in particular states (TCP-handshake-style machines), plus cleanup-on-all-paths. Frame: TYPESTATE over the call graph, restricted to two decidable fragments: (a) module/subsystem protocols (the object is a singleton subsystem -- reachability + summaries suffice, no alias analysis); (b) declared object protocols checked at summary granularity. DELIBERATE DECISIONS: declared protocols with name-pattern-inferred init/deinit convenience (inference ONLY for the common pair, never for general machines); per-function summary fixpoint engine shared with the T-0686 may-raise engine (one engine, three clients: exceptions, capabilities, protocols -- no-duplication); language excuses are recorded DISCHARGES naming their mechanism (Rust Drop unless mem::forget observed; C++ RAII only when init result held by destructor-bearing object; Python with-blocks, GC finalizers NEVER count; TS using/try-finally), per T-0383 caught_by doctrine. LIMITS declared: no aliased per-object heap typestate (Rust owns that); concurrent establishment races belong to T-0693 family; dynamic dispatch = Unknown fail-closed (T-0339). Children: declaration surface, summary engine, state-requirement verification + excuses, cleanup obligations. Umbrella closes when children close.

<!-- ticket:T-0740 -->
```yaml
id: T-0740
title: 'tickets: investigate missing-marker ledger corruption class (T-0367 found
  absorbed into T-0363''s body)'
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/tickets/**
threat: null
component: null
```
found while working T-0726 (TICK006 phantom-filing gate): T-0367 existed in tickets-archive.md as a fully-formed yaml frontmatter block + body (title/state/scope/created all present) but with NO <!-- ticket:T-0367 --> marker line before it, so _parse_ledger's marker-based chunking silently absorbed its entire block as prose inside the PRECEDING ticket's (T-0363) body instead of parsing it as its own ticket -- load_archive/load_all never saw T-0367 at all (frob ticket show T-0367 would have 404'd). Fixed the one instance directly in tickets-archive.md (added the missing marker, restoring T-0367 as its own resolvable block) since it directly corrupted TICK006's phantom-filing measurement, but did not audit the rest of the ~500-ticket ledger for the same missing-marker shape, nor find the write path that produced it (a hand-edit? a merge-splice bug? frob ticket new failing mid-write?). Investigate: (1) whether any other ledger block is missing its marker the same way (a scripted marker-vs-yaml-id cross-check over both ledger files), (2) the root cause / write path that can produce a markerless block, (3) whether frob.tickets._store or the land/splice path needs a structural guard against ever writing yaml frontmatter without its marker.

<!-- ticket:T-0742 -->
```yaml
id: T-0742
title: 'test_scaffold_dx: explicit pytest timeout override with measured headroom'
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: low
parent: T-0692
scope:
- tests/system/test_scaffold_dx.py
acceptance:
- text: GIVEN the slow scaffold test WHEN the suite runs under the global 120s ceiling
    THEN the test carries its own measured override and passes cold-cache
  evidence: []
threat: null
component: null
```
Lost draft from T-0692 (pytest-timeout guard): tests/system/test_scaffold_dx.py spawns a real uv sync + venv + full pipeline; measured 4.52s locally (25x margin under the 120s ceiling) but cold-cache CI could erode it. Add an explicit pytest.mark.timeout override with a measured-based value and a comment. T-0692 reviewer judged deferral safe-to-land; this is the standing home.

<!-- ticket:T-0743 -->
```yaml
id: T-0743
title: 'arch model: NormalizedVariant for enum associated-data shape (Rust/Kotlin
  payloads)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0612
parent: T-0329
scope:
- src/frob/arch/_normalized.py
- src/frob/arch/_rust.py
- tests/unit/test_arch.py
acceptance:
- text: GIVEN a Rust enum with tuple and struct variants WHEN RustAdapter.adapt runs
    THEN variant payload shapes are represented and asserted by a test
  evidence: []
threat: null
component: null
```
Lost draft from T-0612 (Rust adapter): enum variants with associated data currently flatten to NormalizedField, losing the payload shape. Extend the model (NormalizedVariant or fields on NormalizedClass) keeping _normalized.py tree_sitter-free, map Rust enum payloads and coordinate with T-0681 (TS phase 2, same model-extension class).

<!-- ticket:T-0747 -->
```yaml
id: T-0747
title: 'cleanup obligations: release-postdominates-acquisition on all exits incl.
  exceptional, escape transfer, per-protocol policy'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0745
- T-0686
parent: T-0739
scope:
- src/frob/arch/**
- src/frob/gates/**
- tests/test_gates.py
acceptance:
- text: GIVEN a C fixture acquiring a resource with an early-error return skipping
    cleanup WHEN the gate runs THEN an ERROR names the leaking path; GIVEN the Python
    equivalent inside a with-block THEN a recorded context-manager discharge; GIVEN
    cleanup=process-exit-ok THEN termination paths discharge silently by declared
    policy only
  evidence: []
threat: null
component: null
```
Child 4 of T-0739. Cleanup obligations: (a) intraprocedural -- every acquisition (transition into a resource-held state) must be postdominated by its release on ALL exits, using T-0686 may-raise sets for the exceptional edges (blocked_by T-0686), UNLESS the resource escapes (returned/stored) -- escape transfers the obligation to the receiver via the summary (T-0745); (b) per-protocol cleanup policy: cleanup = always | on-error | process-exit-ok, declared in the protocol (T-0744), default on-error; the *_deinit-never-called case = a protocol with cleanup=always whose deinit is unreachable from entrypoint terminating paths = ERROR. NO-FAIL-SILENT: a path the analysis cannot classify (poisoned/Unknown) is an ERROR at the acquisition site; escapes into containers/globals the summary cannot track are reported as obligation-escaped-untracked findings (waivable), never dropped.

<!-- ticket:T-0750 -->
```yaml
id: T-0750
title: 'system tests: gitless tmp_path fixture trips COV002/SCOPE001/TODO001 across
  test_cli_check.py'
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- tests/system/test_cli_check.py
- tests/system/conftest.py
threat: null
component: null
```
found while working T-0627: a wide swath of tests/system/test_cli_check.py (TestCheckCleanProject, TestCheckSkipFlags, TestCheckGatesStage, TestCheckDocAnchorScopedVsUnscoped, TestFrobTomlCheckDefaults, TestCheckTypescript, TestCheckStampBaselineAndDelta, TestCheckTicketScopedAlwaysReportsOnFailure) fail on this worktree's post-merge main: _make_project's tmp_path fixture never git-inits, and newly-merged gates (COV002, SCOPE001, TODO001) now error loudly on a missing git repo instead of the older gates that degraded quietly -- 'working diff against base=main failed to load ... this is a load failure, not a clean/empty diff, so it is not silently passing'. Pre-existing as of the T-0627 warm-up merge, not caused by T-0627's changes (verified: T-0627's own new tests pass; this same failure set reproduces independent of T-0627's diff). Fix is either: git-init tmp_path in the shared fixture, or add gate exemptions those specific tests already relied on for the older gate set.

<!-- ticket:T-0751 -->
```yaml
id: T-0751
title: 'frob check --stamp-baseline: chunk or make incremental so it stays under agent
  foreground caps'
state: queued
kind: ux
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
- docs/guides/agent-playbook.md
threat: null
component: null
```
follow-up from T-0627: --stamp-baseline runs the full undelta'd gates pass (same ~110s+ wall time as a bare frob check) and is deliberately NOT refused under FROB_AGENT since it is a legitimate one-shot warm-up step, not a repeatable verification loop -- so it can still stall a dispatched sub-agent the same way T-0627 fixed for plain frob check. T-0627's ticket body named this as option (c) (make --stamp-baseline itself incremental) and left it unbuilt. Needs either: stamp per stage-group chunk and merge, or a documented coordinator-only path (stamp-baseline runs from the coordinator's shell before dispatch, never from an agent's).

<!-- ticket:T-0755 -->
```yaml
id: T-0755
title: 'adversarial evidence obligation: ticket tests must fail on a diff-scoped mutant
  (confirmatory-only tests flagged)'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: T-0417
scope:
- src/frob/mutate/**
- src/frob/tickets/**
- src/frob/gates/**
- docs/modules/tickets.md
- tests/test_mutate.py
- tests/test_tickets_mutation_evidence.py
- tests/test_gates_mutation_evidence.py
- tests/test_ticket_land.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner.py
- docs/modules/mutate.md
scope_changes:
- op: add
  glob: tests/test_mutate.py
  reason: 'Test files for the T-0755 mutation-evidence obligation (new tests/test_tickets_mutation_evidence.py,
    tests/test_gates_mutation_evidence.py; edits to tests/test_mutate.py for the new
    max_mutants cap and tests/test_ticket_land.py for the land precheck) live under
    tests/, outside the src/**-only scope declared at filing time.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_mutation_evidence.py
  reason: 'Test files for the T-0755 mutation-evidence obligation (new tests/test_tickets_mutation_evidence.py,
    tests/test_gates_mutation_evidence.py; edits to tests/test_mutate.py for the new
    max_mutants cap and tests/test_ticket_land.py for the land precheck) live under
    tests/, outside the src/**-only scope declared at filing time.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: 'Test files for the T-0755 mutation-evidence obligation (new tests/test_tickets_mutation_evidence.py,
    tests/test_gates_mutation_evidence.py; edits to tests/test_mutate.py for the new
    max_mutants cap and tests/test_ticket_land.py for the land precheck) live under
    tests/, outside the src/**-only scope declared at filing time.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Test files for the T-0755 mutation-evidence obligation (new tests/test_tickets_mutation_evidence.py,
    tests/test_gates_mutation_evidence.py; edits to tests/test_mutate.py for the new
    max_mutants cap and tests/test_ticket_land.py for the land precheck) live under
    tests/, outside the src/**-only scope declared at filing time.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/__main__.py
  reason: 'Reviewer round-2 finding 4 requires a documented --skip-mutation-evidence
    escape hatch on `frob ticket land`. Wiring a new CLI flag structurally touches
    the three CLI-wiring files (dispatch table, AppConfig flag plumbing, runner),
    matching the existing CLI_WIRING_FILES precedent for feature-shaped work even
    though this ticket is kind=security.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/config.py
  reason: 'Reviewer round-2 finding 4 requires a documented --skip-mutation-evidence
    escape hatch on `frob ticket land`. Wiring a new CLI flag structurally touches
    the three CLI-wiring files (dispatch table, AppConfig flag plumbing, runner),
    matching the existing CLI_WIRING_FILES precedent for feature-shaped work even
    though this ticket is kind=security.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/ticket_runner.py
  reason: 'Reviewer round-2 finding 4 requires a documented --skip-mutation-evidence
    escape hatch on `frob ticket land`. Wiring a new CLI flag structurally touches
    the three CLI-wiring files (dispatch table, AppConfig flag plumbing, runner),
    matching the existing CLI_WIRING_FILES precedent for feature-shaped work even
    though this ticket is kind=security.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/mutate.md
  reason: Round-2 changes altered run_mutations' public signature (max_mutants, line_ranges)
    and added the MUTATION_RUN_ENV recursion-guard sentinel; docs/modules/mutate.md
    is that surface's doc home and updating it in the same change is the repo's document-as-you-go
    rule, same precedent as docs/modules/tickets.md already being in scope for the
    TEST016 section.
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_mutate.py::test_run_mutations_max_mutants_caps_points_explored
- tests/test_tickets_mutation_evidence.py::TestEvidenceTestIds::test_filters_non_node_id_entries
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_filters_to_scope_and_python
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_empty_when_nothing_touched
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_no_test_evidence_is_ok_empty
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_exec_disabled_is_err
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_security_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_bug_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_findings_no_violations
- tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_security_kind_error_finding_blocks
- tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_feature_kind_warn_finding_does_not_block
- tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_no_findings_is_ok
- tests/test_mutate.py::test_generate_mutants_line_ranges_filters_to_changed_lines
- tests/test_mutate.py::test_generate_mutants_line_ranges_no_match_is_empty
- tests/test_mutate.py::test_run_mutations_line_ranges_scopes_to_changed_lines
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_large_file_unmutable_changed_lines_is_skipped_not_flagged
- tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_skip_flag_bypasses_error_finding_but_still_logs
- tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_parses_to_true
- tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_omitted_defaults_false
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings
- tests/test_mutate.py::test_run_mutations_sets_mutation_run_sentinel_in_child_env
acceptance:
- text: GIVEN a ticket whose recorded evidence tests all pass against a mutant of
    the changed logic WHEN close/land verifies THEN a confirmatory-only-test finding
    fires naming the tests; GIVEN at least one evidence test fails on the mutant THEN
    it passes
  evidence:
  - tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
  - tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged
  - tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_security_kind_error_finding_blocks
threat: null
component: null
```
Root-cause analysis 2026-07-22: several rejects were correctness bugs whose own tests PASSED because they were confirmatory, not adversarial -- written to pass for the reason the implementer built the thing (T-0611, T-0571, T-0682, T-0574, T-0710). A confirmatory test that would pass on BOTH the pre-change and post-change code proves nothing. frob already has `frob mutate`. Add a diff-scoped obligation: for a ticket touching code with new/changed tests, run those tests against the PRE-change version of the changed symbols (or a targeted mutant of the new logic) and require at least ONE recorded evidence test to FAIL on the mutant -- proving the test actually distinguishes the change. A test that passes on the mutant is a confirmatory-only test = a TEST-family warning (ratchet to error via T-0569 pool for security/bug-kind tickets). This is mutation testing scoped to the ticket diff, wired into close/land as evidence-quality verification, reusing frob.mutate.

## Done report

Implements the T-0755 diff-scoped adversarial evidence obligation as
TEST016: a bounded mutation pass over a ticket's own diff-touched,
in-scope Python files, using the ticket's own bound pytest evidence ids
as the kill oracle. Reuses `frob.mutate` exclusively (no parallel
mutation engine) -- `run_mutations` gained an optional `max_mutants` cap
(first N mutation points in source order, deterministic) so the check
stays bounded.

New module `frob.tickets._mutation_evidence` (`evidence_test_ids`,
`touched_python_files`, `check_ticket_mutation_evidence`) does the
selection + orchestration: `.py` files under the ticket's scope that
`frob.gitio.working_diff` shows changed against `base_ref`, excluding
test files themselves (mutating a test and re-running the SAME test as
oracle is a self-referential no-op), capped at 3 files x 8 mutants x 90s
timeout each. A file where every mutant survives becomes a
`ConfirmatoryFinding`.

New module `frob.gates._mutation_evidence` (`mutation_evidence_violations`)
turns findings into `TEST016` `Violation`s: WARN by default, ERROR for
security/bug-kind tickets (T-0569 kind-based ratchet the ticket text
calls for) -- NOT the `frob.gates._ratchet` baseline-pool mechanism,
since no retroactive concern applies: the check only ever runs at a
ticket's own close/land time, never re-scanning an already-closed
ticket's evidence, so this cannot turn a past close red on landing.

Wired into `frob ticket land` (`_land.py::_check_mutation_evidence`,
called from `_land_precheck` right after resolving main's branch name,
before any git mutation): a security/bug-kind ticket with an
ERROR-severity finding refuses the land (new `LandError.
EvidenceConfirmatoryOnly`); every other kind's WARN finding is logged,
non-blocking.

Deviations / disclosed choices:

- `frob.check`'s own gate pipeline (`_ALL_GATES`/`_STAGE_GROUPS`,
  `src/frob/check/**`) is NOT wired to run TEST016 -- `frob.check` was
  outside this ticket's declared scope, and every other TEST rule is a
  pure function of the graph snapshot cheap enough for every `frob
  check`; this rule spawns real bounded subprocesses per ticket, which
  would violate the ticket's own PERF guard if it ran unconditionally
  there. `mutation_evidence_violations` has exactly one caller today:
  `frob.tickets._land`.
- `frob ticket close` (the direct, non-land close path through
  `frob.app.ticket_runner`, also out of scope) is NOT wired -- filed as
  a follow-up ticket (draft id T-0844, finalizes at land) so a
  security/bug ticket closed without landing is not silently exempt
  forever.
- Landing-safety: satisfied structurally, not via the ratchet-pool
  mechanism the ticket text mentions as one option -- the check only
  ever evaluates the CURRENT ticket at its own close/land time, so an
  already-closed ticket's evidence is never re-scanned and this rule
  cannot retroactively redden a past close.
- v1 is Python-only, matching `frob.mutate`'s own existing v1 scope.

Gate state: `frob check --ticket T-0755` chunked (lint/static/gates-fast/
gates-native/gates-security) all PASS, 0 errors, 0 waivers added beyond
one `frob:waive INV006` on `gates/_mutation_evidence.py`'s module
docstring (design-rationale prose hit, T-0585 calibration precedent).
`git diff main --diff-filter=D --stat` is empty.


Reviewer round 2 (4 findings, all addressed):

1. CRITICAL, changed-lines scoping: file-wide mutation-point selection
   let an unrelated pre-existing line supply every mutant for a tiny
   diff. `generate_mutants`/`run_mutations` gained `line_ranges`;
   `check_ticket_mutation_evidence` now derives per-file changed-line
   spans from the diff and mutates ONLY those spans. A file whose
   changed lines admit zero mutable points is skipped, never flagged.
2. Real-repo self-test: `test_self_check_t0755_own_diff_zero_error_
   findings` runs the actual obligation against this worktree's own
   T-0755 diff (base_ref=main) and asserts zero ERROR findings.
3. Large-file skip honesty: an unmutable changed region in a large file
   is a skip, not a finding (test added).
4. Documented escape hatch: `frob ticket land --skip-mutation-evidence`
   (AppConfig `ticket_skip_mutation_evidence`, default False) logs the
   TEST016 finding at WARNING but does not refuse the land; for genuine
   false positives only.

Incident found and fixed while landing round 2: the round-2 self-check
test (finding 2) made the evidence suite self-referential -- the check
re-runs the ticket's evidence per mutant, and that evidence now
contained the self-check itself, so each mutant run re-entered the
harness and the suite became a self-sustaining fork bomb (observed
2026-07-23: orphaned full-suite pytest processes respawning after their
drivers died; killed by hand). Fix: `_run_mutants` now stamps
`MUTATION_RUN_ENV` (`FROB_MUTATION_RUN=1`) into every spawned test
process's environment, and the self-check skips under that sentinel.
Guarding inside `check_ticket_mutation_evidence` instead was rejected:
a vacuous early-return under the sentinel would make the tmp-fixture
unit tests fail-on-env rather than fail-on-behavior, fabricating kill
scores -- the same refusal-is-not-a-verdict posture as T-0803. The
sentinel is itself adversarially evidenced
(`test_run_mutations_sets_mutation_run_sentinel_in_child_env`: the kill
oracle exits 0 iff the sentinel is present, so a harness that stopped
stamping it kills the probe mutant and the test fails).

### Changed
```
 docs/modules/mutate.md                  |  17 +-
 docs/modules/tickets.md                 |  81 +++++++++
 src/frob/__main__.py                    |  12 ++
 src/frob/app/config.py                  |   6 +
 src/frob/app/ticket_runner.py           |  10 ++
 src/frob/gates/__init__.py              |   5 +
 src/frob/gates/_mutation_evidence.py    | 110 ++++++++++++
 src/frob/mutate/__init__.py             | 148 +++++++++++++---
 src/frob/tickets/_land.py               | 112 +++++++++++-
 src/frob/tickets/_models.py             |   5 +
 src/frob/tickets/_mutation_evidence.py  | 294 ++++++++++++++++++++++++++++++
 tests/test_gates_mutation_evidence.py   |  88 +++++++++
 tests/test_mutate.py                    | 112 ++++++++++++
 tests/test_ticket_land.py               | 170 ++++++++++++++++++
 tests/test_tickets_mutation_evidence.py | 253 ++++++++++++++++++++++++++
 tickets.md                              | 305 +++++++++++++++++++++++++++++++-
 16 files changed, 1700 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/test_mutate.py::test_run_mutations_max_mutants_caps_points_explored` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestEvidenceTestIds::test_filters_non_node_id_entries` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_filters_to_scope_and_python` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_empty_when_nothing_touched` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_no_test_evidence_is_ok_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_exec_disabled_is_err` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_security_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_bug_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_findings_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_security_kind_error_finding_blocks` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_feature_kind_warn_finding_does_not_block` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_no_findings_is_ok` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_generate_mutants_line_ranges_filters_to_changed_lines` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_generate_mutants_line_ranges_no_match_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_line_ranges_scopes_to_changed_lines` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_large_file_unmutable_changed_lines_is_skipped_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_skip_flag_bypasses_error_finding_but_still_logs` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_parses_to_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_omitted_defaults_false` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_sets_mutation_run_sentinel_in_child_env` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 24 passed (from 24 evidence id(s))
- gates: 6 error(s), 1211 warning(s), 210 waived

<!-- ticket:T-0756 -->
```yaml
id: T-0756
title: self-audit-green-at-land + new-gate-rule end-to-end acceptance policy (kill
  invoked-by-nothing structurally)
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: T-0397
scope:
- src/frob/check/**
- src/frob/gates/**
- src/frob/tickets/**
- docs/modules/gates.md
acceptance:
- text: GIVEN a change that reddens frob sys audit WHEN land preflight runs THEN land
    errors naming the new self-audit gap; GIVEN a ticket adding a gate rule id with
    no before-fails/after-passes fixture in its evidence THEN close is blocked
  evidence: []
threat: null
component: null
```
Root-cause analysis 2026-07-22: the invoked-by-nothing pattern caused repeated rejects (T-0724 enabling the check reddened frobs OWN sys audit undisclosed; T-0630/T-0595/T-0616/T-0710 built-but-unwired). Two structural fixes: (1) SELF-AUDIT AT LAND: frob check (and frob ticket land preflight) must run the repos own self-conformance/sys-audit and ERROR if the change reddens it -- T-0724s red audit should have been a land gate, not a reviewer catch. selfconform partly does this; extend to run the full sys audit surface (contention, reliability, all SYS families) as a blocking pre-land step so no landed change leaves frobs own model failing. (2) NEW-GATE-RULE ACCEPTANCE POLICY: a ticket that adds a gate/check rule id (detectable: new entry in _KNOWN_GATE_RULES or a new SYS/REL/etc rule) MUST record, as bound acceptance evidence, a fixture that FAILS frob check before and PASSES after -- proving the rule fires through the production invocation, not just its pure function. A new rule with only unit-level evidence and no end-to-end fixture = a close-blocking finding. This makes the catalogued-is-not-enforced doctrine self-enforcing for every future gate.

<!-- ticket:T-0757 -->
```yaml
id: T-0757
title: 'design-invariant encoding: import-forbidding frob:invariant + establish-property
  obligation (T-0611/T-0682 class as gates)'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0330
scope:
- src/frob/graph/dsl.py
- src/frob/gates/**
- src/frob/arch/_normalized.py
- src/frob/tickets/_land.py
- docs/modules/gates.md
acceptance:
- text: GIVEN _normalized.py gains a tree_sitter import WHEN the INV gate runs THEN
    an error fires; GIVEN a comparator invariant declared with a property test THEN
    a violating change fails it; both known cases seeded
  evidence: []
threat: null
component: null
```
Root-cause analysis 2026-07-22: two rejects (T-0611 tree_sitter imported into the deliberately-pure _normalized.py; T-0682 the newer state must win the splice) were violations of a DESIGN INVARIANT that existed only in the implementers/reviewers head, not as a checkable property. frob already has frob:invariant anchors + INV gates. The thread: module-level design properties (this module must not import X; this comparator must be monotonic in Y; this data model must round-trip) are not being written as invariants at the point they are established, so their violation needs a human skeptic to reconstruct. Deliver: (1) a frob:invariant flavor for IMPORT/DEPENDENCY properties (module M must never import package P) checkable statically -- T-0611s exact case becomes an INV gate error, not a review catch; (2) guidance + lint (docs + a check) that a ticket ESTABLISHING a design property (a new pure module, a new ordering/comparator, a new serialization round-trip) record it as a frob:invariant in the same change; (3) seed the two known ones now: _normalized.py-no-tree_sitter and splice_ledger-newer-wins.

<!-- ticket:T-0759 -->
```yaml
id: T-0759
title: harden T-0710 overhead test against xdist wall-clock fragility
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- tests/unit/perf/test_hotgraph.py
threat: null
component: null
```
T-0710's TestStackSampler.test_overhead_under_five_percent measures wall-clock elapsed time (unsampled vs sampled, best-of-3) to assert sampler overhead stays under 5 percent. Under pytest-xdist parallel workers (this repo's default -n auto), concurrent worker contention can inflate wall-clock noise beyond what best-of-3 suppresses, risking flakiness in CI even though the sampler itself is not slow. Fix: mark the test to run serially (a 'serial'/xdist_group marker forcing it off the parallel grid) or relax/parameterize the tolerance for CI, whichever this repo's existing flaky-timing precedent (frob.toml/pytest.ini markers) prefers. Found during T-0710 review round 2.

<!-- ticket:T-0760 -->
```yaml
id: T-0760
title: harden T-0710 hot-graph overhead test against xdist wall-clock fragility
state: queued
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0710
scope:
- tests/unit/perf/
- src/frob/perf/**
acceptance:
- text: GIVEN the overhead test WHEN the full suite runs under -n auto THEN it passes
    reliably (serial marker, CPU-time measure, or documented-tolerance margin), not
    only under -n0
  evidence: []
threat: null
component: null
```
From T-0710: the hot-graph overhead test (attribution sampler <5% overhead) asserts a hard <5% on a ~0.11s workload = ~5.5ms margin, best-of-3 min-vs-min. Under pytest-xdist (-n auto, the default) the baseline and sampled loops compete with 11 concurrent workers for cores -- reproduced live: the test FAILS under -n auto, passes -n0. Harden it: either mark it serial (a no-xdist / serial marker so it runs alone), or relax the CI margin with a documented tolerance, or switch to a CPU-time (not wall-clock) measure immune to core contention. Pick the robust option and document why.

<!-- ticket:T-0762 -->
```yaml
id: T-0762
title: 'structural PII type-kind: TS/Rust nominal PII-shaped types (branded email,
  secrecy::Secret/SecretString wrappers)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0352
scope:
- src/frob/gates/_pii_structural.py
- tests/test_gates.py
- docs/modules/gates.md
acceptance:
- text: GIVEN a TS field typed as a known secret-wrapper or a Rust field typed secrecy::SecretString
    WHEN pii_structural runs THEN a type-kind PII finding fires; a plain String field
    does not
  evidence: []
threat: null
component: null
```
From T-0352 (TS/Rust structural PII, landed): the NAME-kind field detection is cross-language, but TYPE-kind PII signals (Python EmailStr/SecretStr) stay Python-only. Extend to nominal PII-shaped TYPES in TS/Rust: TS branded/nominal email types and known secret-wrapper types; Rust secret-wrapper crate types (secrecy::Secret, SecretString) and newtype PII wrappers. Requires resolving a field/binding TYPE to a known-PII-type registry per language -- coordinate with T-0717 capability taxonomy and the T-0611/T-0612 adapters type info. Disclosed in T-0352 module docstring, not silently dropped.

<!-- ticket:T-0765 -->
```yaml
id: T-0765
title: 'frob perf CLI: live collector wiring (perf/V8/JFR + python sampler) end-to-end
  subcommand'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/app/**
- src/frob/perf/**
- docs/modules/perf.md
acceptance:
- text: GIVEN a repo and a recorded profile artifact (perf script output, .cpuprofile,
    or JFR print output) WHEN the user runs the frob perf collect subcommand THEN
    the hit stream is resolved through resolve_stream and per-language deciles are
    readable from the CLI output
  evidence: []
threat: null
component: null
```
T-0748 delivered the collector parser adapters (parse_perf_script, parse_v8_cpuprofile, parse_jfr_print + build_class_to_file) proven through resolve_stream/HitStream, but no frob perf CLI entrypoint exists for any collector including the T-0710 python sampler. Wire a subcommand that accepts a profile artifact path (or invokes the sampler), runs the matching collector, and renders the resolved hot-graph deciles. Filed per T-0748 reviewer recommendation (disclosed deviation, real unscoped work).

<!-- ticket:T-0771 -->
```yaml
id: T-0771
title: 'capability taxonomy: wire net/env/proc/ffi mode split + sibling-repo migration
  (T-0717 follow-up)'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- docs/design/registry/**
- docs/strata/**
threat: null
component: null
```
T-0717 shipped the shared mode-qualified capability vocabulary
(frob.vet._capability_modes: FAMILY_MODES, CAPABILITY_MODE_KINDS,
LEGACY_CAPABILITY_ALIASES, resolve_capability_kind/expand_declared_kind/
canonical_declared_kind/normalize_observed_kind) and wired it live for the
fs family only (fs.read/fs.write, WIRED_MODE_FAMILIES={"fs"}) -- the one
family the acceptance tests exercised. net.connect/net.listen,
env.read/env.write, proc.spawn, and ffi.call are DEFINED in FAMILY_MODES
but deliberately NOT exploded by expand_declared_kind/normalize_observed_
kind yet (a bare may "net" stays exactly {"net"}), because the vet
scanner has no connect/listen (or env-read/write, proc, ffi-call)
distinction to normalize observations against -- exploding the
declaration side without a matching observation side would make every
existing bare "net"/"env"/etc. declaration spuriously SYS101-stale.

Follow-up work, explicitly not done in T-0717:
1. Extend frob.vet._capability's per-language needle tables with a real
   connect-vs-listen split for net (e.g. socket.connect vs socket.bind+
   listen; net.connect vs net.listen in TS/Rust equivalents), and an
   env read-vs-write split, before adding those families to
   WIRED_MODE_FAMILIES.
2. Mechanical sweep of this repo's own design/frob.strata declarations
   and DEFAULT_BENIGN_CAPABILITIES (src/frob/strata/_threat.py) once a
   family is wired, mirroring what T-0717 did for fs (BenignCapability
   entries + CAPABILITY_KINDS registration would be needed for fs.read/
   fs.write too if any node ever declares them precisely -- currently
   design/frob.strata only uses the still-legal coarse "fs"/"fs-read"
   spellings, so this was deferred).
3. ESTATE migration (mandate point 3): once net/env/proc/ffi are wired,
   file per-repo tickets (T-0573 fleet routing) for the 8 sibling repos'
   own capability declarations to adopt the precise family.mode spellings
   ahead of the T-0717 alias sunset (fs-write/fs-read, 2026-10-20).

<!-- ticket:T-0775 -->
```yaml
id: T-0775
title: 'perf: loop-invariant effectful call detector (spawn/fs-walk callee in a loop
  with loop-invariant args)'
state: queued
kind: feature
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0632
parent: null
scope:
- src/frob/perf/**
- src/frob/arch/**
- tests/unit/perf/
acceptance:
- text: GIVEN a fixture where a loop body calls a function that transitively spawns
    a process with arguments invariant across iterations WHEN frob check runs THEN
    a prove-or-justify finding fires naming the call site, the effectful callee, and
    the invariant args; GIVEN the same call with a loop-varying argument THEN no finding;
    GIVEN the pre-T-0773 read_all_leases-per-ticket-row shape THEN the finding fires
    on the real repo history fixture
  evidence: []
threat: null
component: null
```
Motivated by the 2026-07-22 rev-parse incident (T-0773): frob ticket list spawned git rev-parse --git-common-dir dozens of times because the loop (ticket rows) and the effect (subprocess spawn 3 calls deep) live in different modules -- no per-function syntactic PERF heuristic can see it. The ingredients already exist: vet capability observation knows which functions transitively proc.spawn/fs-walk; the obligation graph has the call graph; T-0632 adds per-argument call detail needed for the loop-invariance test. Detector: for each loop (incl. comprehensions and per-item pipeline stages), for each reachable effectful callee whose observed effect is spawn/fs-walk, if every argument at the call site is loop-invariant, fire a prove-or-justify finding (hoist, memoize, or frob:waive with a freshness justification -- re-reading mutable state can be deliberate under concurrency, so this is warn-tier with an unwaivable-style justification requirement, not a silent error). Keep recall honest: undecidable invariance leans toward firing per the repo philosophy.

<!-- ticket:T-0777 -->
```yaml
id: T-0777
title: wire resolve_lease pinning into frob check's --ticket resolution entry point
state: queued
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
threat: null
component: null
```
T-0766 added `frob.tickets._leases.resolve_lease(root, ticket_id,
invoking_worktree)`: a pinned, per-ticket lease resolution primitive that
reads exactly one ticket's own lease file (never scans/iterates across all
recorded leases) and fails loudly (`NoLeaseForTicket` /
`LeaseWorktreeMismatch`) instead of ever borrowing a sibling ticket's lease.

Investigation while working T-0766 found that `frob check --ticket T-XXXX`
(src/frob/app/check_runner.py, src/frob/gates/__init__.py's `active_ticket`/
`_resolve_ticket`) currently performs NO cross-worktree lease consultation
at all -- `active_ticket` resolves the ticket id purely from `--ticket` or
the branch name, and `_worktree_guard.enforce_worktree_lease` (the
FROB_WORKTREE env-var check) is wired into `ack_runner.py`, `gates/
_coverage.py`, and `gates/_baseline.py`, but NOT into `check_runner.py` at
all. Neither path currently calls `resolve_lease`.

This ticket did not reproduce the exact T-0695 incident mechanism inside
this codebase's current `check` code path in the time available -- it is
possible the incident predates a since-landed fix, or the actual cross-talk
happened one level up (dispatcher/coordinator tooling outside this repo).
Regardless, `resolve_lease` is a real, useful hardening primitive now
available and should be wired in as defense in depth:

- Call `resolve_lease(root, ticket.id, root)` from `_resolve_ticket`
  (gates/__init__.py) or `check_runner.py` when `--ticket` is explicit,
  and surface a loud, actionable failure (naming `frob ticket start`) if
  it errs, rather than silently proceeding with whatever the local ledger
  says.
- Consider also wiring `enforce_worktree_lease` into `check_runner.py`
  for symmetry with `ack_runner.py`/`gates/_coverage.py`/`gates/
  _baseline.py`, since it is currently the one mutating/gating entry point
  missing it.

Scope: src/frob/app/check_runner.py, src/frob/gates/__init__.py (the
`active_ticket`/`_resolve_ticket` region only).

<!-- ticket:T-0781 -->
```yaml
id: T-0781
title: 'vet/gates: taint rule -- repo-writable state (.git/.frob JSON or text) reaching
  subprocess argv requires validation or ''--'''
state: queued
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/vet/**
- src/frob/gates/**
acceptance:
- text: GIVEN a fixture where a value parsed from a file under .git/ or .frob/ flows
    into a subprocess argv position without passing a registered validator or a preceding
    -- literal WHEN the check runs THEN a finding fires naming source and sink; GIVEN
    the same flow through a validator THEN no finding
  evidence: []
threat: null
component: null
```
Audit M1 gate-direction: SEC gates catch shell=True and f-string-into-argv but not the trust-boundary shape (peer-writable state file -> argv). Model the source set (read_text/json.loads on .git//.frob paths) and the sink (subprocess/run_argv argv positions); require a validator hop or -- terminator. Same rule covers worktree paths reaching Path.exists/display. This is a dataflow rule -- scope it honestly as intra-module flow first, interprocedural later.

<!-- ticket:T-0783 -->
```yaml
id: T-0783
title: 'gates: long-deferred-obligation rule -- shipped deferral comment citing a
  still-open ticket past a release boundary'
state: queued
kind: feature
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/**
acceptance:
- text: GIVEN a shipped comment deferring work to ticket T-X (that ticket's job shape
    or frob:todo) WHEN T-X remains open across a REL001 version bump since the comment
    landed THEN a warning fires naming the deferral site and age; GIVEN the ticket
    closes THEN the finding clears
  evidence: []
threat: null
component: null
```
Audit M2 gate-direction: deferred cleanup silently became permanent (T-0476 open since the lease layer shipped). Detect deferral comments bound to open tickets that have crossed release boundaries so deferrals get re-litigated instead of fossilizing.

<!-- ticket:T-0786 -->
```yaml
id: T-0786
title: 'AUDIT: gate-by-gate vacuous-satisfaction sweep + lang parser trust-boundary
  pass (blindspot audit boundary)'
state: queued
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
scope:
- docs/audits/gates-vacuous.md
acceptance:
- text: GIVEN the audit doc WHEN complete THEN every gate in gates/__init__.py has
    a recorded verdict for empty-diff/empty-scope/cached-stale satisfaction (can it
    go green without doing its work) and the lang/** tree-sitter ingestion of untrusted
    files has a recorded DoS/traversal verdict; every defect found is filed as its
    own ticket
  evidence: []
threat: null
component: null
```
The 2026-07-23 blindspot audit explicitly skipped: (a) a full vacuous-satisfaction sweep of gates/__init__.py (8568 lines -- can any gate be satisfied by an empty diff, empty scope, or stale cache?), and (b) lang/** parser trust boundary (tree-sitter on untrusted repo files). These are the largest unaudited surfaces. Run per the audit-until-empty discipline (docs/audits/, pessimistic auditor told to find 10+, repeat until 0).

<!-- ticket:T-0789 -->
```yaml
id: T-0789
title: uv.lock auto-resyncs frob version on every uv run in a worktree, causing spurious
  SCOPE001 unless manually reverted
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- pyproject.toml
- uv.lock
- Makefile
threat: null
component: null
```
Observed while working T-0704 (worktree agent-ad82d24588b5083b6, 2026-07-22/23). This worktree's checked-in uv.lock records frob's own package version as 0.97.0 while pyproject.toml's version line is already 0.98.0 (a pre-existing mismatch present at the worktree's own base commit, not introduced by any ticket worked in this session). Because uv.lock is not scope-locked against auto-sync, EVERY `uv run ...` invocation (including read-only ones like `frob ticket show` or `frob check`) silently rewrites uv.lock's frob version line to match pyproject.toml, leaving a working-tree modification an agent must notice and `git checkout HEAD -- uv.lock` away before every commit/check -- and if missed, SCOPE001 fires (uv.lock outside the ticket's declared scope) on every subsequent `frob check` even though no agent hand-edited the file. Section 4b of docs/guides/agent-playbook.md already forbids agents from touching uv.lock by hand, but does not cover this auto-touch-by-tooling case. Fix: either (a) make `uv run`'s auto-sync a no-op when only the local version-line mismatch is the cause (uv config: --frozen or --no-sync for frob's own CLI invocations, or a repo-level uv setting), or (b) have the section-4b agent-file-blacklist pre-commit hook silently discard/reset a version-line-only uv.lock diff caused by this sync rather than warning/blocking, or (c) reconcile pyproject.toml/uv.lock at land time so fresh worktrees never start with the mismatch. Any one of the three removes the recurring "revert uv.lock before committing" step every worktree agent currently has to remember.

<!-- ticket:T-0800 -->
```yaml
id: T-0800
title: 'dup: normalize combined-vs-split early-return conditionals before similarity
  compare'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/dup/**
- frob-core/src/**
threat: null
component: null
```
Found while working T-0785 (dup: normalize error-channel before similarity
compare). The ticket's motivating case -- frob.tickets._leases.git_common_dir
(Result[Path, LeaseError]) vs frob.gates._exclude_hazard._git_common_dir
(Path | None) -- differs along TWO independent axes, not one:

1. Error-channel shape (Err(...)/Ok(...) vs None/bare value) -- T-0785
   normalizes this axis. Fixed.
2. Combined-vs-split early-return conditional: git_common_dir merges both
   failure checks into one `if spawned.is_err or spawned.danger_ok
   .returncode != 0:` (both branches map to the SAME Err(LeaseError
   .GitCommonDirUnavailable)), while _git_common_dir keeps them as two
   separate `if`s because each logs a DIFFERENT debug message. This axis
   is NOT normalized by T-0785.

With only axis 1 normalized, the real current pair's R4 near-miss floor
similarity measures 0.444 (frob.dup._pipeline._R4_SIMILARITY_FLOOR =
0.6) -- it does not register as a duplicate group today. A fixture with
axis 2 also aligned (both sides using the same combined-if structure)
reaches 0.799 and registers cleanly (rung r4).

Scope sketch: a control-flow-level token normalization (or a real
AST-level desugar, similar in spirit to R3's elif-desugar in
frob_core::r3_canonicalize) that recognizes "N early-return branches each
guarding a distinct condition, all exiting with an error-channel exit"
as equivalent to "one early-return branch guarding the disjunction of
those conditions" when the exit shapes are otherwise interchangeable.
Needs real AST structure (branch condition/body pairs), not a flat
token-stream heuristic like T-0785's error-channel marker -- likely a
frob_core kernel addition (parallel to r3_canonicalize's elif desugar)
rather than a pure-Python _pipeline.py transform.

<!-- ticket:T-0801 -->
```yaml
id: T-0801
title: 'dup: control-flow-shape normalization axis (combined-vs-split if) so the real
  git_common_dir pair registers'
state: queued
kind: feature
origin: agent
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/dup/_pipeline.py
- tests/test_dup.py
acceptance:
- text: GIVEN the real _leases.py::git_common_dir and _exclude_hazard.py::_git_common_dir
    pair WHEN the dup scan runs with both error-channel and control-flow normalization
    THEN they register as a duplicate group (similarity above the 0.6 floor, was 0.444
    with error-channel alone); repo-wide group delta stays bounded and each new pair
    is examined
  evidence: []
threat: null
component: null
```
Promotion of T-0785's worktree draft 2e4385db (worktree removed at land before renumbering). T-0785 landed the error-channel axis; the motivating real pair still differs on a combined-vs-split if structural axis and measures 0.444 (<0.6). Normalize simple guard-shape variants so semantically-one functions pair. Prereq for T-0784's seam unification to be regression-locked by DUP.

<!-- ticket:T-0802 -->
```yaml
id: T-0802
title: 'execute the 2026-10-01 navigation-command sunset: remove map/outline/xref/docs-search
  per T-0580 deprecation'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: low
parent: null
scope:
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/docs_runner.py
- src/frob/__main__.py
- docs/modules/cli.md
acceptance:
- text: GIVEN the sunset date 2026-10-01 has passed WHEN this ticket is worked THEN
    the four deprecated navigation commands and their parsers, tests, and doc/test/export
    obligations are removed (or the sunset is explicitly re-adjudicated with the user),
    and no frob:deprecated directive for them remains
  evidence: []
threat: null
component: null
```
Sunset-execution ticket for the user's 2026-07-23 deprecation decision (T-0580, done). Stays OPEN until the sunset so the four frob:deprecated directives have a live ticket binding (DEPR002 requires ticket= to reference an open ticket -- T-0797 registration surfaced that the directives bound to the closed T-0580). Do not work before the sunset date.

<!-- ticket:T-0821 -->
```yaml
id: T-0821
title: 'land: close path refuses planned-state tickets with full evidence (recurring
  InvalidTransition; auto-advance or preflight-name the state gap)'
state: queued
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
acceptance:
- text: GIVEN a worktree ticket in planned state with evidence bound and a Done report
    WHEN land runs THEN it either advances planned->in-progress->done transparently
    during finalize or the PRE-MERGE preflight refuses naming the state and the frob
    ticket start remedy -- never a post-merge InvalidTransition; a regression test
    covers the planned-state land
  evidence: []
threat: null
component: null
```
Hit 3x this drive (T-0799, T-0752 post-10b-restore, T-0815): implementers leave tickets planned (never ran start, or a ledger restore reverted the state), evidence+report are complete, land merges+finalizes then dies InvalidTransition at close, forcing the coordinator start-then-retry recipe. Either fold the start transition into finalize when preconditions are met, or extend the T-0763 preflight to check state transitions pre-merge.

<!-- ticket:T-0823 -->
```yaml
id: T-0823
title: 'lang: LANG003 known-gap ticket refs unresolvable in adopter repos (escalates
  to ERROR outside frob itself)'
state: queued
kind: bug
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/lang/_support.py
- src/frob/gates/**
- tests/test_lang_conformance_gate.py
acceptance:
- text: GIVEN an adopter repo whose queue carries no frob-internal ticket ids WHEN
    LANG003 evaluates a known-gap facet THEN it does not hard-error on the unresolvable
    frob-internal reference (per the chosen design), with a fixture test proving the
    adopter shape
  evidence: []
threat: null
component: null
```
Disclosed by T-0818's investigation (2026-07-23): LANG003's KNOWN_GAP facet
verification requires the CHECKED repo's own ticket queue to carry the
ticket id named in frob's internal _arch_status gap table (e.g. T-0329
for typescript arch). For frob itself that id resolves; for any DOWNSTREAM
adopter repo (the 8-repo rollout) the id is meaningless -- their queues
will never mirror frob-internal ids, so every known-gap facet escalates
to ERROR on adopter repos. Adjudicate the design: (a) known-gap ids
verify against frob's own shipped registry, not the checked repo's queue;
(b) gap references become adopter-neutral (URL/registry key); or (c)
document that adopters must waive. Pick one, implement, and add an
adopter-shaped fixture test (repo with no frob-internal ids).

<!-- ticket:T-0825 -->
```yaml
id: T-0825
title: 'strata host: same-principal narrow-deny/broad-allow WRITE_DAC indirection
  understates; privilege-clause grammar gap'
state: queued
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/strata/_host_isolation.py
- docs/strata/host.md
- tests/unit/strata/test_host_isolation.py
acceptance:
- text: GIVEN a principal with a narrow deny and a broad allow on one path WHEN the
    join evaluates THEN the WRITE_DAC indirection corner has a recorded disposition
    (bit-level modeling or loud documentation plus a behavior-locking test); GIVEN
    token-privilege classes THEN the grammar-clause decision is recorded
  evidence: []
threat: elevation-of-privilege
component: null
```
T-0792 reviewer finding: with per-principal netting, a same-principal
narrow deny (Modify) plus broad allow (FullControl) nets to
not-write-capable in the model, but real NTFS still grants
WRITE_DAC/WRITE_OWNER through the FullControl allow (the denied Modify
bits do not cover them), so the principal can rewrite the DACL and regain
write -- the model's ONLY understating (fail-open) corner, currently
undocumented. Inexpressible in the single-token RIGHTS vocabulary. Pair
with the disclosed privilege-clause gap (SeImpersonate/SeDebug classes
need a strata-core grammar clause, per the T-0792 module docstring).
Either extend the RIGHTS model to bit-level semantics for the deny join,
or document the corner loudly in the module + host.md and add a fixture
test locking the current (understating) behavior so any future change is
deliberate.

<!-- ticket:T-0826 -->
```yaml
id: T-0826
title: 'tickets CLI: done-report --why-file duplicates the ''## Done report'' heading
  (recurring cosmetic ledger noise)'
state: queued
kind: ux
origin: agent
created: '2026-07-23'
priority: low
parent: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/**
acceptance:
- text: GIVEN a why-file that already begins with a Done report heading WHEN frob
    ticket done-report renders it THEN exactly one heading appears in the ledger block;
    existing double-heading blocks are tolerated by parsers
  evidence: []
threat: null
component: null
```
Recurred 5+ times this drive (reviewers keep flagging it cosmetically): done-report prepends its own heading on top of one already present in --why-file content. Deduplicate at render time.

<!-- ticket:T-0837 -->
```yaml
id: T-0837
title: 'docs: port the frob review channel section for T-0571, repoint its frob:doc
  anchors'
state: queued
kind: docs
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- docs/modules/tickets.md
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner.py
threat: null
component: null
```
T-0571's salvage port (frob review: structured adversarial review channel
as first-class evidence) landed without its docs section --
docs/modules/tickets.md was outside the port's six-file scope, so the
donor's #structured-review-channel-t-0571 section was never ported and
two frob:doc anchors were repointed at #public-api as a disclosed
workaround. Write the section (CLI usage: frob ticket review with
--verdict/--reviewer/--findings-file/--commit, close --strict,
require_review_for_close frob.toml key, ReviewEntry evidence shape) and
repoint the two anchors in src/frob/tickets/__init__.py /
src/frob/app/ticket_runner.py back at the new section.

<!-- ticket:T-0840 -->
```yaml
id: T-0840
title: path-sensitive per-call-site state verification (ordered call graph)
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/graph/**
- src/frob/gates/_protocol_summary.py
threat: null
component: null
```
T-0746 disclosure: PROTO002/PROTO003 (frob.gates._protocol_summary) ask
an EXISTENTIAL question over compute_protocol_summaries' unordered,
per-function transitive requires/transitions sets ("is state S
established by SOME reachable transition anywhere in the tagged
package closure") rather than a path-sensitive one ("is S established
on EVERY path reaching this exact call site"), because the T-0745
engine has no per-call-site statement ordering yet. This is
false-negative-biased (a real ordering violation can be missed if some
other path in the same closure happens to establish the state) -- the
ticket-named crisp case (a state never established by ANY transition
anywhere) is still caught soundly. Building real path-sensitivity needs
an ordered call graph (each function's calls recorded in statement
order, not just as an unordered edge set) plus a per-call-site
dataflow pass over compute_protocol_summaries' SCC-ordered worklist.
Scope: src/frob/graph/**, src/frob/gates/_protocol_summary.py.

<!-- ticket:T-0841 -->
```yaml
id: T-0841
title: wire Rust/C++/TypeScript language-excuse discharge into a real call-graph scan
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: low
parent: null
scope:
- src/frob/gates/_protocol_summary.py
- src/frob/graph/callgraph.py
threat: null
component: null
```
T-0746 disclosure: frob.arch._protocol_excuse's per-language discharge
predicates (rust_drop_discharge, cpp_raii_discharge,
typescript_using_discharge, gc_finalizer_discharge) are built and
directly unit-tested, but only python_with_discharge is wired into the
real repo-scan protocol_summary_gate today -- because
frob.graph.callgraph.build_call_graph is Python-only (the same
disclosed limitation PROTO001 already carries, and DEAD001 before it).
Wiring Rust/C++/TypeScript discharge into a real cross-file scan needs
those languages to get build_call_graph support first (or an
equivalent per-language call-graph substrate); this is deliberately
NOT built here to avoid a second, unreviewed call-graph implementation
per language, mirroring T-0745's own T-0809 disclosure pattern.
Scope: src/frob/gates/_protocol_summary.py, src/frob/graph/callgraph.py.

<!-- ticket:T-0843 -->
```yaml
id: T-0843
title: 'ticket archive: refusal hint says force=True not the CLI flag; T-0753 guard
  over-broad for in-progress-only leases'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
- tests/test_ticket_runner_archive_force.py
threat: null
component: null
```
`frob ticket archive` refusal message says "pass force=True to override"
-- that is the internal python kwarg, not the CLI surface. The CLI flag
is --force (verify; if absent, add it mirroring other force flags).
Remedy hints must be copy-pastable commands (the repo's own violation-
message convention). Also consider: when the only live leases belong to
tickets whose blocks archive would NOT touch (in-progress tickets are
never archived), the refusal is over-broad -- evaluate narrowing the
T-0753 guard to refuse only when a live-leased ticket's OWN block would
be moved/rewritten, so a red TICK003 can be cleared without waiting for
unrelated in-flight work.

<!-- ticket:T-0844 -->
```yaml
id: T-0844
title: wire TEST016 mutation-evidence obligation into frob ticket close (not just
  land)
state: queued
kind: security
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
threat: null
component: null
```
T-0755 wired the diff-scoped adversarial evidence obligation (TEST016,
frob.gates.mutation_evidence_violations) into `frob ticket land`
(frob.tickets._land._check_mutation_evidence), because frob.tickets/**
and frob.gates/** were in scope but frob.app/** was not.

`frob ticket close` (the direct, non-land close path) goes through
frob.app.ticket_runner and frob.tickets.transition, and does NOT run the
mutation-evidence check today -- a security/bug-kind ticket closed
directly (never landed) can still close on confirmatory-only evidence.

Plan: inject mutation_evidence_violations (or an equivalent
Callable[[Ticket], tuple[Violation, ...]]) into the close-path CLI
runner, mirroring the covers_scope/reviewed injection pattern
transition()/_done_transition_guard() already use, and block DONE on an
ERROR-severity finding the same way land does.

<!-- ticket:T-0845 -->
```yaml
id: T-0845
title: 'strata: attr-forwarding surface for elaborator-synthesized in-process cache
  flows (REL200 waiver burn-down)'
state: queued
kind: feature
origin: agent
created: '2026-07-23'
priority: medium
parent: T-0640
scope:
- src/frob/strata/**
- design/frob.strata
- tests/unit/strata/**
threat: null
component: null
```
The two REL200 waivers on design/frob.strata's graph_cache__fill and graph_cache__inval_f_parse flows exist because elaborator-synthesized in-process cache flows have no attr-forwarding surface: there is no way to declare (or discharge) a timeout/local disposition on a flow the elaborator invents. Add that surface (per-flow attr forwarding from the synthesizing rule, or an explicit local disposition for in-process in-memory flows), then burn down both waivers. Deferred from T-0640 at its salvage-close; the waivers' ticket refs point here.
