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
blocked_by:
- T-0861
- T-0862
- T-0871
- T-0872
- T-0873
- T-0874
- T-0875
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

## Failure log
- 2026-07-23 attempt 1: Could not reproduce the hunk-splitting regression after three escalating real-diff repro attempts (sequential closes, interleaved scope noise, 40 near-identical tickets); grace window held in every case. See Done report for full detail.

## Done report

Could not reproduce the described COV002 grace-window regression after
three escalating attempts against the REAL diff/gate machinery (not
hand-crafted Hunk objects): (1) three sequential ticket closes in one
branch via the real `write_ticket`/`working_diff`/`_bound_to_open_ticket`
path; (2) the same, plus interleaved scope-change rewrites to a fourth,
unrelated open ticket between each close (simulating "frob ticket
scope/sweep operations on tickets.md in between"); (3) forty tickets with
IDENTICAL title/body/scope boilerplate (maximizing myers-diff ambiguity
against near-duplicate lines), ten of them closed sequentially with
scope-noise on an eleventh interleaved between each close. In all three,
every closed ticket's `_bound_to_open_ticket` check against the real
`working_diff(root, "main")` output returned True -- the grace window held
for every closed ticket in every scenario, including the ones adjacent (by
sorted ticket id, since `_render_ledger` always sorts by id and rewrites
the WHOLE file every `write_ticket` call) to the ticket being repeatedly
rewritten. `git diff <merge-base> --unified=0` (the exact invocation
`working_diff` uses) is a single two-tree diff between the merge-base and
the current working tree, computed once, independent of how many
intermediate commits/rewrites happened in between -- so the "repeated
rewrites split/relocate the hunk" mechanism this ticket's own hypothesis
proposes did not manifest even when I deliberately maximized the
conditions the hypothesis names (adjacent near-duplicate ledger blocks,
many intervening unrelated-ticket rewrites, sorted-by-id reordering
pressure).

I cannot rule out that the real incident needs conditions this reproduction
does not model: the ACTUAL 900+ line tickets.md this repo carries (far
larger and structurally different from a synthetic 12-40 ticket ledger),
a specific `frob ticket sweep`/`scope` CLI sequence rather than direct
`write_ticket` calls (the CLI's sweep touches `dup_findings`/`xref_hits`
fields this repro never populated), an UNCOMMITTED intermediate state
(the real incident narrative mentions "multiple frob ticket scope/sweep
operations ... in between" without saying whether each was its own commit
or accumulated uncommitted), or a specific closed-ticket ORDERING/adjacency
this repro's ten-in-a-row pattern did not hit. Per this ticket's own
plan ("if you cannot reproduce, record that honestly"), I am not shipping
a speculative fix or a message-wording change against an unconfirmed
mechanism -- failing instead of guessing.

Suggested next step for whoever picks this back up: reproduce against a
COPY of this repo's actual tickets.md (or a fixture seeded from it) using
the real `frob ticket sweep`/`scope`/`done-report` CLI commands in the
exact sequence the original incident narrative describes (T-0567, T-0545,
T-0552, T-0547 closes, then T-0556's own start/scope/sweep calls), rather
than a synthetic from-scratch ledger -- the scale and CLI-call shape may
be load-bearing for whatever triggered the original observation.

### Changed
```
 src/frob/tickets/_land.py |  49 +++++++++++-
 tests/test_ticket_land.py |  38 +++++++++-
 tickets.md                | 185 +++++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 265 insertions(+), 7 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 6 error(s), 1209 warning(s), 210 waived

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

<!-- ticket:T-0646 -->
```yaml
id: T-0646
title: 'strata: BACKPRESSURE bounded-intake obligation on queues/consumers'
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
evidence:
- tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_queue_node_without_bounded_intake_fires
- tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_consumer_node_without_bounded_intake_fires
- tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_discharged_and_non_queue_nodes_clean
- tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_waiver_discharges_finding
- tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
acceptance:
- text: Given a queue/consumer node with no bounded-intake policy declared, when checked,
    then the obligation fires
  evidence:
  - tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_queue_node_without_bounded_intake_fires
  - tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_consumer_node_without_bounded_intake_fires
  - tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_discharged_and_non_queue_nodes_clean
  - tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_waiver_discharges_finding
  - tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
threat: null
component: null
```
Every queue/consumer node must declare bounded intake (backpressure policy), extending LINT003 surge / LINT005 capacity.

## Done report

New REL26x BACKPRESSURE-obligation family (`src/frob/strata/_backpressure.py`,
mirroring `_circuit_breaker.py`'s REL23x node-scoped structure): REL260
(missing bounded intake -- a `queue`/`consumer` node with no
`bounded_intake` attr) and REL261 (declared-but-unproven bounded intake,
proof-against-code via `_obligation_proof.py`'s shared owner-index/bound-
code/token-scan plumbing, no re-derivation). Both rules NODE-scoped,
single-instance-per-node (not registered in
`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, same carve-out REL230/REL231
use).

Wired into `src/frob/strata/__init__.py`'s public surface
(`check_backpressure_obligations`, `BackpressureReport`,
`BackpressureViolation`, `REL_MISSING_BOUNDED_INTAKE`,
`REL_UNPROVEN_BOUNDED_INTAKE`, `BACKPRESSURE_RULES`). NOT wired into
`frob.app.sys_runner` -- confirmed by inspection that
`check_retry_obligations`/`check_circuit_breaker_obligations`/
`check_fallback_obligations`/`check_spof` (T-0641/T-0642/T-0643/T-0645,
all already landed) are ALSO only exported from `strata/__init__.py` and
not yet wired into `sys_runner.py` either -- that CLI-wiring step is
evidently a separate follow-up across the whole REL2xx family, not
something this ticket alone left undone, and `src/frob/app/**` is outside
this ticket's declared scope regardless.

Added `docs/strata/reliability.md#rel26x-backpressure-obligation-t-0646`
(surface vocabulary, grammar-data ceiling disclosure, waiver channel),
following the REL22x/REL23x section template exactly.

Tests: `tests/unit/strata/test_backpressure.py`, 7 cases covering REL260
(queue node fires, consumer node fires, discharged/non-population clean,
waiver discharges) and REL261 (unproven fires, proven discharges,
no-bound-code is uncheckable not a violation) -- mirrors
`test_retry.py`'s real-tmp_path bind_code convention.

Measured:
- `uv run pytest tests/unit/strata/test_backpressure.py -p no:cacheprovider -q`
  -> 7 passed.
- `uv run frob check --only lint --ticket T-0646` -> PASS 0 errors 0 warnings.
- `uv run frob check --only static --ticket T-0646` -> PASS 0 errors (204
  warnings, all pre-existing/waived elsewhere in the tree; one frob-dup
  warning on this ticket's own test file, two near-identical Node-literal
  blocks across sibling test cases -- accepted as ordinary test-fixture
  repetition, not extracted).
- `uv run frob check --only gates-fast --ticket T-0646` -> PASS 0 errors
  (after a `frob ticket sweep T-0646` re-run to refresh PRE001 against the
  final file set).
- `uv run frob check --only gates-native --ticket T-0646` -> PASS 0 errors.
- `uv run frob check --only gates-security --ticket T-0646` -> PASS 0
  errors.

Cuts: none against the ticket's stated acceptance criterion (queue/
consumer node with no bounded-intake policy fires). CLI/`sys_runner`
wiring intentionally left out per the scope note above (matches the
existing landed sibling REL2xx families' actual state, not a regression).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_queue_node_without_bounded_intake_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_consumer_node_without_bounded_intake_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_discharged_and_non_queue_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 2300 warning(s), 218 waived
- error-findings: none (measured, zero errors)

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
state: in-progress
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_multi_writer_store_without_owner_fires
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_single_writer_store_clean
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_owner_attr_discharges
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_reconciliation_attr_discharges
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_empty_store_ids_emits_nothing
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_waiver_discharges_finding
- tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
acceptance:
- text: Given a store with >=2 distinct writer nodes and no declared single-owner/reconciliation,
    when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_ssot.py::TestMissingOwner::test_multi_writer_store_without_owner_fires
threat: null
component: null
```
Extends SYS003 hub: a store written by two or more distinct nodes without a declared owner/reconciliation is a hard obligation failure.

## Done report

New REL29x SINGLE-SOURCE-OF-TRUTH-obligation family
(`src/frob/strata/_ssot.py`, mirroring `_circuit_breaker.py`'s REL23x
store-node-scoped structure): REL290 (missing owner/reconciliation -- a
multi-writer store, >=2 distinct non-store nodes with a Flow edge into
it, `_contention.py`'s SYS203 exact mode-blind detection re-derived here
for the full-writer-set shape REL290 needs, with no `owner`/
`reconciliation` attr) and REL291 (declared-but-unproven owner, proof-
against-code via `_obligation_proof.py`'s shared owner-index/bound-code/
token-scan plumbing, no re-derivation). Extends SYS203's DETECTION with
an OBLIGATION (ticket body's "extends SYS003 hub" -- the actual landed
codebase analog is SYS203's shared-store-write rule, `_contention.py`,
not a rule literally named SYS003; documented candidly in the module
docstring).

`store_ids` kept as a caller-supplied parameter, not a `KernelModel`
fact -- the exact same "not reconstructible after elaboration" ceiling
SYS203 already discloses (`_contention.py`'s module docstring), reused
verbatim rather than re-derived.

Both rules NODE-scoped (store), single-instance-per-store (not
registered in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, same carve-out
REL230/REL231/REL280/REL281 use).

Wired into `src/frob/strata/__init__.py`'s public surface
(`check_ssot_obligations`, `SsotReport`, `SsotViolation`,
`REL_MISSING_OWNER`, `REL_UNPROVEN_OWNER`, `SSOT_RULES`). NOT wired into
`frob.app.sys_runner` for the same reason recorded in T-0646/T-0647's
Done reports (every sibling landed REL2xx family is in the identical
state today; `src/frob/app/**` is outside this ticket's scope).

Added `docs/strata/reliability.md#rel29x-single-source-of-truth-obligation-t-0649`
(surface vocabulary, grammar-data ceiling disclosure, waiver channel),
following the REL23x/REL28x section template.

Tests: `tests/unit/strata/test_ssot.py`, 9 cases: REL290 (multi-writer
fires, single-writer clean, owner-attr discharges, reconciliation-attr
discharges, empty store_ids emits nothing, waiver discharges), REL291
(unproven fires, proven discharges, no-bound-code uncheckable).

Measured:
- `uv run pytest tests/unit/strata/test_ssot.py tests/unit/strata/test_slo.py tests/unit/strata/test_observability.py tests/unit/strata/test_backpressure.py -p no:cacheprovider -q`
  -> 31 passed.
- `uv run frob check --only lint --ticket T-0649` -> PASS 0 errors 0
  warnings.
- `uv run frob check --only static --ticket T-0649` -> PASS (frob-exports/
  frob-dup/frob-arch/frob-cycle all pass).
- `uv run frob check --only gates-fast --ticket T-0649` -> PASS 0 errors
  (after `frob ticket sweep T-0649` refreshed PRE001 against the final
  file set).
- `uv run frob check --only gates-native --ticket T-0649` -> PASS 0
  errors (one new unwaived PERF004 warning at `_ssot.py:196`, a small
  per-store `sorted(writer_ids)` call inside the outer store loop --
  same shape as `_contention.py`'s own several pre-existing unwaived
  PERF004 sorted-in-loop warnings; left unwaived to match that
  established repo convention for this exact debt class rather than
  hand-waiving only this file's instance).
- `uv run frob check --only gates-security --ticket T-0649` -> PASS 0
  errors.

Cuts: none against the stated acceptance criterion. CLI/sys_runner
wiring intentionally out of scope (see above). T-0648 (SLO) was written
in the same worktree but is `blocked_by` T-0647 and could not be
`frob ticket start`ed here (`BlockerOpen`) -- its code + tests are
committed and gate-clean, but its own start/evidence/done-report ledger
steps are left for after the coordinator lands T-0647.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_multi_writer_store_without_owner_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_single_writer_store_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_owner_attr_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_reconciliation_attr_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_empty_store_ids_emits_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 2490 warning(s), 219 waived
- error-findings: none (measured, zero errors)

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
blocked_by:
- T-0864
- T-0865
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
blocked_by:
- T-0866
- T-0867
- T-0868
- T-0869
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

<!-- ticket:T-0756 -->
```yaml
id: T-0756
title: self-audit-green-at-land + new-gate-rule end-to-end acceptance policy (kill
  invoked-by-nothing structurally)
state: done
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
- tests/test_tickets_new_gate_rule_acceptance.py
- invariants/INV-041.md
- tests/test_gates.py
- design/frob.strata
scope_changes:
- op: add
  glob: tests/test_tickets_new_gate_rule_acceptance.py
  reason: 'Evidence test files and the invariant spec for this ticket''s own new

    SELFAUDIT001 gate/new-gate-rule-acceptance machinery must live under

    tests/** and invariants/** respectively; declared scope only covered the

    production src/frob/**/gates.md surface.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: invariants/INV-041.md
  reason: 'Evidence test files and the invariant spec for this ticket''s own new

    SELFAUDIT001 gate/new-gate-rule-acceptance machinery must live under

    tests/** and invariants/** respectively; declared scope only covered the

    production src/frob/**/gates.md surface.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates.py
  reason: 'Evidence test files and the invariant spec for this ticket''s own new

    SELFAUDIT001 gate/new-gate-rule-acceptance machinery must live under

    tests/** and invariants/** respectively; declared scope only covered the

    production src/frob/**/gates.md surface.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: design/frob.strata
  reason: 'Wiring SELFAUDIT001 into frob check for the first time surfaced a real,

    previously-undisclosed red frob sys audit (SYS203 on node=serve, missing

    the same waiver its 4 sibling nodes already carry from T-0724) -- landing

    the new blocking gate while knowingly leaving the repo''s own audit red

    would repeat the exact T-0724 incident this ticket exists to close.

    Adding the one missing sibling-pattern waiver line is a precondition for

    SELFAUDIT001 being usable as a land gate at all, not an unrelated design

    change.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_suppressed_on_design_load_error
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_gates_file_at_all_is_empty
- tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_flags_when_no_fixture_criterion_bound
- tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_clear_when_a_bound_fixture_criterion_exists
- tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_unbound_fixture_shaped_criterion_still_flags
- tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_empty_new_rule_ids_is_always_clear
- tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_refused_when_new_rule_has_no_fixture_acceptance
- tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_fixture_acceptance_bound
- tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_no_new_rule_added
acceptance:
- text: GIVEN a change that reddens frob sys audit WHEN land preflight runs THEN land
    errors naming the new self-audit gap; GIVEN a ticket adding a gate rule id with
    no before-fails/after-passes fixture in its evidence THEN close is blocked
  evidence:
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_suppressed_on_design_load_error
  - tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
  - tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
  - tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
  - tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_gates_file_at_all_is_empty
  - tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_flags_when_no_fixture_criterion_bound
  - tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_clear_when_a_bound_fixture_criterion_exists
  - tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_unbound_fixture_shaped_criterion_still_flags
  - tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_empty_new_rule_ids_is_always_clear
  - tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_refused_when_new_rule_has_no_fixture_acceptance
  - tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_fixture_acceptance_bound
  - tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_no_new_rule_added
threat: null
component: null
```
Root-cause analysis 2026-07-22: the invoked-by-nothing pattern caused repeated rejects (T-0724 enabling the check reddened frobs OWN sys audit undisclosed; T-0630/T-0595/T-0616/T-0710 built-but-unwired). Two structural fixes: (1) SELF-AUDIT AT LAND: frob check (and frob ticket land preflight) must run the repos own self-conformance/sys-audit and ERROR if the change reddens it -- T-0724s red audit should have been a land gate, not a reviewer catch. selfconform partly does this; extend to run the full sys audit surface (contention, reliability, all SYS families) as a blocking pre-land step so no landed change leaves frobs own model failing. (2) NEW-GATE-RULE ACCEPTANCE POLICY: a ticket that adds a gate/check rule id (detectable: new entry in _KNOWN_GATE_RULES or a new SYS/REL/etc rule) MUST record, as bound acceptance evidence, a fixture that FAILS frob check before and PASSES after -- proving the rule fires through the production invocation, not just its pure function. A new rule with only unit-level evidence and no end-to-end fixture = a close-blocking finding. This makes the catalogued-is-not-enforced doctrine self-enforcing for every future gate.

## Done report

Changed:
- src/frob/gates/__init__.py::sys_gate (extended: now also runs _selfaudit_violations)
- src/frob/gates/__init__.py::_selfaudit_violation
- src/frob/gates/__init__.py::_selfaudit_violations
- src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added "SELFAUDIT001")
- src/frob/tickets/_new_gate_rule_acceptance.py (new module): new_gate_rule_ids, missing_acceptance_for_new_rules, _extract_known_rules, _read_gates_file_at_revision, _is_fixture_acceptance
- src/frob/tickets/_models.py::TicketError (added NewGateRuleUnaccepted)
- src/frob/tickets/__init__.py::_done_transition_guard (wired the new unconditional check, mirroring live_tracker_citations)
- design/frob.strata (node serve: added the missing SYS203:tickets_ledger waiver its 4 sibling nodes already carried)
- docs/modules/gates.md (SELFAUDIT001 table row + two new sections: "Self-audit at land" and "New-gate-rule acceptance policy")
- invariants/INV-041.md (new invariant spec for the SELFAUDIT001 lossless-fold property)
- tests/test_gates.py::TestSelfAuditGate (3 tests)
- tests/test_tickets_new_gate_rule_acceptance.py (new file, 11 tests)

Mechanism (1) SELF-AUDIT AT LAND: frob.gates.sys_gate (the production
entrypoint `frob check` already calls unconditionally whenever a design
dir exists) now folds frob's own self-conformance (SYS100-102,
frob.strata.check_self_conformance), resource-contention (SYS2xx,
check_resource_contention), and reliability (REL2xx,
check_reliability_timeouts/check_reliability_health) audit surface into
the ordinary gate pipeline under a new rule id, SELFAUDIT001 (ERROR,
registered in _KNOWN_GATE_RULES). This closes the land-preflight half of
the mandate with ZERO app/**-layer changes: frob ticket land's EXISTING
check_gates/check_gate_findings post-merge re-verification
(frob.tickets._land.land, T-0754/T-0846) already refuses a landing whose
gate-error count reddens relative to the recorded claim -- once
SELFAUDIT001 is an ordinary gate frob check reports, that machinery
covers it automatically.

REAL FINDING surfaced by turning this on: wiring SELFAUDIT001 revealed
`frob sys audit` was ALREADY red on main (one unwaived SYS203 finding on
node=serve, missing the same waiver its 4 sibling nodes -- cli/core/
fleet/gates -- already carry from T-0724). This is precisely the
"invoked-by-nothing red audit" root cause the ticket describes. Landing
SELFAUDIT001 while knowingly leaving this red would repeat the incident,
so design/frob.strata's `serve` node was scope-added (--reason-file, see
ticket scope history) and given the identical sibling waiver line.
`frob sys audit .` now exits 0 (verified: WARNING lines only, PROVED
summary for self-conformance/resource-contention/reliability).

Mechanism (2) NEW-GATE-RULE ACCEPTANCE POLICY:
frob.tickets._new_gate_rule_acceptance.new_gate_rule_ids does a
diff-aware text scan (git show base_ref vs current tree, mirroring
_live_tracker's grep-shaped-not-full-parse posture) of
src/frob/gates/__init__.py's _KNOWN_GATE_RULES frozenset literal, and
missing_acceptance_for_new_rules requires at least one BOUND acceptance
criterion whose text contains both a FAIL and a PASS marker
(case-insensitive). Wired UNCONDITIONALLY into
frob.tickets._done_transition_guard (the same DONE-transition guard both
`frob ticket close` and `frob ticket land`'s finalize-and-close step
call internally) -- no separate land-time CLI wiring needed, exactly
mirroring live_tracker_citations's existing posture. New TicketError.
NewGateRuleUnaccepted variant.

DOGFOOD (self-check, per the ticket's own mandate): T-0756's own diff
adds SELFAUDIT001 to _KNOWN_GATE_RULES. Verified directly:
new_gate_rule_ids(root, base_ref="main") == ("SELFAUDIT001",), and
missing_acceptance_for_new_rules(ticket, ("SELFAUDIT001",)) == () once
acceptance criterion [0] (pre-existing ticket text: "...no
before-fails/after-passes fixture...") was bound via
`frob ticket evidence T-0756 <fixture ids> --accepts 0`. Confirmed this
ticket cannot itself close/land without satisfying its own new policy.

Disclosed cuts (v1, documented in docs/modules/gates.md and the module
docstring, not silently dropped):
- new_gate_rule_ids is scoped to _KNOWN_GATE_RULES specifically (the one
  registry every Violation-producing gate rule must be listed in) -- a
  rule family introduced some OTHER way is a known residual gap. This
  ticket's own SELFAUDIT001 folds the previously-uncovered SYS1xx/SYS2xx/
  REL2xx families INTO _KNOWN_GATE_RULES for exactly this reason.
- missing_acceptance_for_new_rules requires ONE qualifying criterion
  covering the ticket as a whole when several rule ids land in one diff,
  not a strict 1:1 criterion-per-rule-id mapping.
- new_gate_rule_ids fails OPEN (returns None, obligation skipped) on any
  git infra failure, a deliberate asymmetry from _live_tracker's
  fail-closed posture -- explained in the function's own docstring:
  this check gates EVERY ticket close in the repo, so a transient git
  hiccup blocking all closes repo-wide is a worse failure mode than
  occasionally missing a genuinely new rule id.
- I did NOT add a fully separate `frob ticket land`-only preflight call
  site for either mechanism; both close the loop through EXISTING
  machinery (check_gates re-verification for (1), _done_transition_guard
  for (2), the latter already reached by land's own finalize-and-close
  step). This was a deliberate minimal-surface-area choice, not an
  oversight -- confirmed by tracing _land_finalize_and_close ->
  _finalize_and_close_ticket -> transition(..., DONE).

Verification (measured, all foreground, chunked --only stages):
- `uv run pytest tests/test_gates.py::TestSelfAuditGate
  tests/test_tickets_new_gate_rule_acceptance.py -q`: 14 passed
- `uv run pytest tests/test_tickets_live_tracker.py
  tests/test_tickets_mutation_evidence.py tests/test_evidence_integrity.py
  tests/test_ticket_land.py tests/test_tickets.py -q`: all passed (no
  regressions in the transition()/land() call sites this change touches)
- `uv run frob check --only lint --ticket T-0756`: PASS 0 errors 0 warnings
- `uv run frob check --only static --ticket T-0756`: 0 errors (frob-exports
  warnings are pre-existing, unrelated to this diff)
- `uv run frob check --only gates-fast --ticket T-0756 --json`: 0 errors
- `uv run frob check --only gates-native --ticket T-0756 --json`: 0 errors
- `uv run frob check --only gates-security --ticket T-0756 --json`: 0 errors
- `uv run frob sys audit .`: exit 0 (was exit 1 before design/frob.strata's
  fix -- the concrete before-fails/after-passes proof for SELFAUDIT001's
  own underlying audit surface)
- `git diff main --diff-filter=D --stat`: empty (verified before this report)

Filed: none (design/frob.strata's serve-node waiver was folded into this
ticket's own scope, not filed separately, since it is a direct
precondition for SELFAUDIT001 being landable at all -- see scope-add
reason recorded in tickets.md's scope history for T-0756).

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_suppressed_on_design_load_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_gates_file_at_all_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_flags_when_no_fixture_criterion_bound` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_clear_when_a_bound_fixture_criterion_exists` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_unbound_fixture_shaped_criterion_still_flags` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_empty_new_rule_ids_is_always_clear` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_refused_when_new_rule_has_no_fixture_acceptance` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_fixture_acceptance_bound` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_no_new_rule_added` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 0 error(s), 2258 warning(s), 219 waived
- error-findings: none (measured, zero errors)

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

<!-- ticket:T-0786 -->
```yaml
id: T-0786
title: 'AUDIT: gate-by-gate vacuous-satisfaction sweep + lang parser trust-boundary
  pass (blindspot audit boundary)'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
scope:
- docs/audits/gates-vacuous.md
- docs/index.md
- tests/integration/test_interfaces.py
scope_changes:
- op: add
  glob: docs/index.md
  reason: 'DOC001 requires docs/audits/gates-vacuous.md be linked from docs/index.md
    (the standard audits-index pattern every other docs/audits/*.md entry follows);
    adding the one-line index entry, not expanding the audit''s own content scope.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: docs-only audit ticket; CLI-dispatch integration test is the bound evidence
    (T-0167 precedent), scope-added for covers_scope (D-02 route 2)
  actor: logan
  at: '2026-07-23'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
acceptance:
- text: GIVEN the audit doc WHEN complete THEN every gate in gates/__init__.py has
    a recorded verdict for empty-diff/empty-scope/cached-stale satisfaction (can it
    go green without doing its work) and the lang/** tree-sitter ingestion of untrusted
    files has a recorded DoS/traversal verdict; every defect found is filed as its
    own ticket
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
```
The 2026-07-23 blindspot audit explicitly skipped: (a) a full vacuous-satisfaction sweep of gates/__init__.py (8568 lines -- can any gate be satisfied by an empty diff, empty scope, or stale cache?), and (b) lang/** parser trust boundary (tree-sitter on untrusted repo files). These are the largest unaudited surfaces. Run per the audit-until-empty discipline (docs/audits/, pessimistic auditor told to find 10+, repeat until 0).

## Done report

FINAL (round 2, after coordinator feedback): completed the full
gate-by-gate catalog. `known_gate_rule_ids()` returns 118 rule ids;
this sweep additionally found 7 real, currently-firing rule ids the
frozenset itself OMITS (PARSE001, TICK005, REG011, PII011, PII012,
SYSWAIVE002, THREAT006 -- itself H3 below), for 125 distinct rule ids
total. Every one of the 125 now carries an explicit verdict in
docs/audits/gates-vacuous.md's "Catalog coverage" table -- swept total
== catalog total, zero unread, per the acceptance criterion's own bar.

Round 1 (18 examined vectors) covered COV/TODO/SCOPE/PRE/TEST/TICK001-002/
COMPLIANCE005/REG001-010/DEC/FUZZ/PARSE-partial/SEC/SEC110/the lang parse
entrypoint/2 strata comment-flagged sites. Round 2 (this pass) closed the
remaining ~60 rule ids/dispatch sites: INV001-006, DEBT001-003,
DEPR001-004, DSL001, WAIVE001-007, REL001, DOC001-005, DUP001-002 (native
path), FUZZ (confirmed), PERF001-007, SYS001-004, TICK003-004/006-008,
FMT001, PII010-012, ARCH001/101-103, REF001-003, REG011, WALK001
(confirmed), EXCL001, SEC-CVE-FINGERPRINT-001, RENDER001, LANG001-003,
DEAD001, PROTO001-003, PARSE001's own dispatch, SYSWAIVE002, THREAT006,
plus the `_KNOWN_GATE_RULES`-completeness cross-check itself.

Findings by severity (final): 3 HIGH, 4 MEDIUM, 3 LOW (disclosed/
already-tracked, no new ticket).

HIGH:
- H1 (round 1): SCOPE001 vacuously passes when `ticket.scope` is empty.
- H2 (round 1): partial (salvaged) tree-sitter parses silently drop
  symbols; `partial_parse_files()` has zero gate consumers.
- H3 (round 2, NEW): `_KNOWN_GATE_RULES` omits 7 real, currently-firing
  rule ids (PARSE001, TICK005, REG011, PII011, PII012, SYSWAIVE002,
  THREAT006) -- the exact DEAD001-class listing-omission T-0753 already
  fixed once, recurred 6+ more times since. Breaks WAIVE002 validity for
  those 7 ids AND strata/registry `caught_by`/`handled_by` resolution
  credit for controls that actually ARE enforced by them.

MEDIUM:
- M1 (round 1): lang/** tree-sitter ingestion has no file-size cap or
  parse timeout -- untrusted-file trust-boundary gap.
- M2 (round 1, broadened round 2): registry/design-dir-backed gates
  (COMPLIANCE005, REG001-011, DEC001-002, and -- newly identified this
  round -- SYS001-004 and DOC001/DOC003) all share the same "missing
  backing dir/file/glob-match == no claim" posture that cannot
  distinguish never-adopted from deleted. SYS*/DOC001/DOC003 instances
  folded into the existing fix ticket's scope rather than re-filed (one
  "adopted-then-vanished" detector should cover all six).
- M3 (round 2, NEW): `dup_gate` silently no-ops (log-only WARNING, no
  Violation) when `frob-core` native is unavailable, even with
  `[dup].enforce=true` -- the exact class T-0552/TEST013 already fixed
  for the coverage gate's own native fallback, never applied to DUP.
- M4 (round 2, NEW): RENDER001, PII010/SEC110 (via `pii_structural_gate`),
  and SEC-CVE-FINGERPRINT-001 each run their own private
  `ast.parse`/file-read outside `frob.lang.parse_file`'s PARSE001-tracked
  pipeline, silently skipping an unparseable/undecodable file with only a
  DEBUG log line -- exactly the class T-0558/PARSE001 was built to make
  loud, recurring in three independent code paths that never route
  through it.

LOW (disclosed/already-tracked, no new ticket): L1 secrets_gate's
line-wrap gap (already fully disclosed in-code, T-0151); L2 DEAD001's
Python-only scope (already disclosed, already has a follow-up ticket
per its own docstring -- T-0422's Done report); L3 ARCH101-103's missing
`frob:enforces CHK-GATE-*` cross-link (already disclosed as a pending
land obligation, same T-0788 precedent).

Draft tickets filed: 7 fix+gate pairs total (14 tickets) -- 4 pairs from
round 1 (H1, H2, M1, M2/COMPLIANCE005), 3 more pairs round 2 (H3, M3, M4).

docs/index.md's audit-index entry updated to reflect the final, complete
sweep (125/125, zero unswept) and the full finding list.

Disclosed cut: none remaining -- round 1's disclosed gap (the other half
of the catalog) is now closed. LANG002's inherent completeness boundary
(cannot flag a wholly unenumerated file extension) and L1-L3 above are
the only residual, explicitly-accepted non-defects.

### Changed
```
 docs/audits/gates-vacuous.md | 429 +++++++++++++++++++++++++++++++++++++++++++
 docs/index.md                |   1 +
 tickets.md                   | 381 +++++++++++++++++++++++++++++++++++++-
 3 files changed, 810 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

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

<!-- ticket:T-0861 -->
```yaml
id: T-0861
title: 'frob-dup: triage src/frob/** extraction-candidate groups (25 groups, split
  from T-0597)'
state: queued
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/**
- tests/**
threat: null
component: null
```
Re-measured 2026-07-23 by T-0597: the frob-dup check stage (frob check --only dup, the legacy find_duplicates scanner T-0597 was scoped against, NOT the newer standalone frob dup CLI's rung pipeline which reports a different, larger count) currently shows 240 total groups, 110 already covered by full-group frob:waive DUP001/DUP002 directives, 130 unaccounted. This ticket carves out the 25 unaccounted groups that touch at least one src/frob/** file -- these need real per-group architectural judgment (genuine extraction vs honest false-pair waiver), unlike the tests/** parallel-scaffolding groups split into a sibling ticket. Full group list (message text from the frob-dup diagnostics, frob check --only dup --json):

1. 30-line: src/frob/gates/_pii_structural.py:492, :829
2. 29-line: src/frob/gates/__init__.py:4192, :4442, :6626
3. 25-line: src/frob/gates/_walk_lint.py:247, src/frob/gates/_render_lint.py:174
4. 23-line: src/frob/deploy/_generate_windows.py:189, :215
5. 22-line: src/frob/app/sys_runner.py:452, :603, :669
6. 21-line: src/frob/deploy/_generate_windows.py:321, :345
7. 20-line: src/frob/process/parsers/common.py:209, :232
8. 19-line: src/frob/tickets/__init__.py:1746, :1773
9. 19-line: src/frob/app/check_runner.py:168, :184
10. 18-line: src/frob/strata/_waive.py:217, src/frob/deploy/_generate.py:300/382/406/571, src/frob/scaffold/_managed.py:140, src/frob/dup/_rules.py:65
11. 17-line: src/frob/gates/_pii_structural.py:777, :1216
12. 17-line: src/frob/deploy/_generate_windows.py:285, :305
13. 16-line: src/frob/gates/_exclude_hazard.py:101, src/frob/gates/_cve_fingerprint_scan.py:96
14. 16-line: src/frob/gates/__init__.py:8500, src/frob/vet/_scan.py:147, :418
15. 15-line: src/frob/gates/_pii_structural.py:1178, src/frob/gates/_walk_lint.py:77, src/frob/gates/_render_lint.py:65
16. 14-line: src/frob/arch/_python.py:285, src/frob/arch/_rust.py:171/181, src/frob/arch/_typescript.py:96
17. 12-line: src/frob/deploy/_generate.py:191, src/frob/deploy/_generate_windows.py:150
18. 12-line: src/frob/app/sys_runner.py:529, :587, :653
19. 11-line: src/frob/gates/_docblocks.py:146, src/frob/perf/_redundancy.py:88
20. 11-line: src/frob/app/sys_runner.py:560, :623, :687
21. 10-line: src/frob/gates/_registry_exhaustiveness.py:169, :207
22. 9-line: src/frob/strata/_host_isolation.py:337, src/frob/strata/_contention.py:156
23. 9-line: src/frob/arch/_rust.py:378, src/frob/arch/_kotlin.py:129
24. 8-line: src/frob/vet/_capability.py:654, :2584
25. 6-line: src/frob/gates/__init__.py:3556, src/frob/perf/_recursion.py:240, src/frob/dup/_pipeline.py:619

Note groups 5/18/20 all sit inside src/frob/app/sys_runner.py's _log_waived_* family and likely share one real extraction opportunity; group 3/15 (_walk_lint.py/_render_lint.py) likewise look related. Re-run frob check --only dup --json at the start of this ticket (do not trust this snapshot -- T-0597's own dispatch drifted 75->240 groups in one day). For each group: genuine extraction (shared logic into one home, update call sites, before/after tests, TEST016 mutant-kill check per the T-0597 dispatch playbook) or an honest full-group frob:waive DUP001/DUP002 reason if it is a false pair. Acceptance: frob check --only dup summary shows these 25 groups' fragments no longer among the unwaived (fixed-or-waived), frob-cycle stays clean, no import cycles introduced.

<!-- ticket:T-0862 -->
```yaml
id: T-0862
title: 'frob-dup: triage tests/**-only near-dup groups (105 groups, split from T-0597)'
state: queued
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
scope:
- tests/**
threat: null
component: null
```
Re-measured 2026-07-23 by T-0597: the frob-dup check stage (frob check --only dup, the legacy find_duplicates scanner T-0597 was scoped against) currently shows 240 total groups, 110 already covered by full-group frob:waive DUP001/DUP002 directives, 130 unaccounted. Of the 130 unaccounted, 105 involve ONLY tests/** files (no src/frob/** member) -- a sibling ticket (see parent T-0597's Done/fail report) carves out the remaining 25 groups that touch src/frob/** for real extraction judgment; this ticket is the tests-only batch, which the T-0597 dispatch playbook expects to be mostly (not necessarily all) legitimate parallel-scaffolding false pairs.

Do NOT hand-copy a stale list: at the start of this ticket, run:

  uv run frob check --only dup --json

and filter diagnostics with severity=="warning" whose message contains no "src/frob" path segment -- that is the authoritative, current group list (it will have drifted again since this filing; T-0597's own dispatch saw the raw dup group count move 75->240 in about one day of concurrent landings). For each group: waive with an honest, specific, full-group frob:waive DUP001 (or DUP002) reason (T-0375's full-coverage rule -- every fragment's symref must be covered, no any-shared-symref shortcuts) if it is a coincidental structural/parallel-test-scaffolding pair, or extract into a shared test helper/fixture (with before/after test runs) if the shared logic is genuinely one thing duplicated, not parallel-but-distinct test intent. Given the volume, batch the work (e.g. by source test file or by group-size band) and commit incrementally per playbook section 12/discipline. Acceptance: frob check --only dup summary shows 0 unaccounted groups whose fragments are entirely under tests/**, no threshold loosened.

<!-- ticket:T-0864 -->
```yaml
id: T-0864
title: 'natives build subcommand: frob-owned maturin develop per [natives] crate with
  git-common-dir shared CARGO_TARGET_DIR'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: high
parent: T-0735
scope:
- src/frob/app/natives_runner.py
- src/frob/natives/**
- src/frob/__main__.py
- Makefile
- docs/modules/cli.md
- tests/unit/test_natives_build.py
acceptance:
- text: GIVEN a frob-enabled repo with [natives] declared WHEN `uv run frob natives
    build` runs THEN each declared native crate compiles via maturin develop into
    the active venv using a git-common-dir-keyed shared CARGO_TARGET_DIR
  evidence: []
- text: GIVEN two worktrees of the same clone WHEN both run `frob natives build` THEN
    they share one cargo target dir and concurrent builds are safe via cargo's own
    locking
  evidence: []
- text: GIVEN this repo WHEN `make core` runs THEN it is a one-line shim delegating
    to `uv run frob natives build` with no cache logic left in the Makefile
  evidence: []
threat: null
component: natives
```
T-0735 child 1 (the subcommand). Implement `frob natives build`: read frob.toml [natives] (load_natives already declares the native crates), run the maturin-develop-per-declared-native sequence that `make core` does today, WITH the shared-cache mechanism built in (git-common-dir keyed CARGO_TARGET_DIR so all worktrees of a clone share one cargo target dir; rely on cargo's own locking for concurrency -- T-0732's verified design). Convert THIS repo's Makefile `core` target to the one-line shim `uv run frob natives build`, removing the cache logic from the Makefile. Doctor integration: the existing native-staleness fingerprint check must point at `frob natives build` as its remedy text.

<!-- ticket:T-0865 -->
```yaml
id: T-0865
title: 'natives build estate conformance: scaffold Makefile shim template + drift
  check for per-repo cache logic'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: high
blocked_by:
- T-0864
parent: T-0735
scope:
- src/frob/scaffold/**
- tests/unit/test_scaffold_natives_shim.py
acceptance:
- text: GIVEN a scaffolded frob-enabled repo WHEN `frob scaffold apply` runs THEN
    the Makefile core target is the one-line `uv run frob natives build` shim
  evidence: []
- text: GIVEN a repo whose Makefile core target contains its own native-build cache
    logic WHEN the conformance check runs THEN it reports the drift naming the shim
    as the remedy
  evidence: []
threat: null
component: natives
```
T-0735 child 2 (estate conformance). Scaffold template: `frob scaffold apply` emits/updates the Makefile `core` target as the one-line `uv run frob natives build` shim in adopter repos. Add a conformance drift check that flags a frob-enabled repo whose Makefile core target carries its own native-build/cache logic instead of the shim (the drift that motivated the parent: per-repo cache hacks at the wrong layer). Estate rollout of the shim across sibling repos happens via fleet at parent close, not in this ticket.

<!-- ticket:T-0866 -->
```yaml
id: T-0866
title: 'typestate declaration surface: module/object protocol declarations + init/deinit
  pair inference'
state: dropped
kind: security
origin: human
created: '2026-07-23'
priority: high
parent: T-0739
scope:
- src/frob/graph/dsl.py
- src/frob/arch/_typestate.py
- docs/design/typestate.md
- tests/unit/test_typestate.py
acceptance:
- text: GIVEN a module declaring an explicit protocol (states, transitions, per-function
    state requirements) WHEN the declaration is parsed THEN the model exposes the
    machine to downstream checks with source locations
  evidence: []
- text: GIVEN a module with foo_init/foo_deinit and no explicit declaration WHEN inference
    runs THEN the init/deinit pair protocol is inferred, and no inference happens
    for any non-pair machine
  evidence: []
threat: null
component: arch
```
T-0739 child 1 (declaration surface). The typestate declaration surface: how a protocol is declared for (a) module/subsystem singleton protocols and (b) declared object protocols. Includes the name-pattern-inferred init/deinit convenience pair (inference ONLY for the common *_init/*_deinit pair, never for general machines) and the explicit declared-state-machine form (states, transitions, functions-valid-in-state). Deliverable: the parsed declaration model + directives/DSL wiring, consumed by the verification child. No enforcement in this ticket.

## Drop reason
- 2026-07-23: duplicate of the pre-existing T-0739 child set (T-0744/T-0745/T-0746/T-0747, mostly done) -- filed 2026-07-23 without checking parent-edge children; typestate declaration surface, summary engine, verification+excuses already delivered in graph/dsl.py, graph/summary.py, gates/_protocol_summary.py

<!-- ticket:T-0867 -->
```yaml
id: T-0867
title: shared per-function summary fixpoint engine over the resolved call graph (protocol/may-raise/capability
  clients)
state: dropped
kind: security
origin: human
created: '2026-07-23'
priority: high
parent: T-0739
scope:
- src/frob/graph/**
- src/frob/arch/_summaries.py
- tests/unit/test_summaries.py
acceptance:
- text: GIVEN a call graph with cycles WHEN the summary fixpoint runs THEN it terminates
    with sound summaries and per-function results are queryable
  evidence: []
- text: GIVEN a call through dynamic dispatch WHEN summaries are computed THEN the
    summary records Unknown fail-closed rather than assuming any resolution
  evidence: []
threat: null
component: graph
```
T-0739 child 2 (the engine). Per-function summary fixpoint engine over the call graph, shared by design with the T-0685/T-0686 may-raise analysis and the capability analysis (one engine, three clients -- no-duplication mandate). Computes per-function summaries (calls-observed, states-required/established/destroyed) to a fixpoint over the resolved call graph; dynamic dispatch is Unknown and fail-closed per T-0339 doctrine. This ticket delivers the engine + the protocol client's summary shape; the verification rules live in child 3.

## Drop reason
- 2026-07-23: duplicate of the pre-existing T-0739 child set (T-0744/T-0745/T-0746/T-0747, mostly done) -- filed 2026-07-23 without checking parent-edge children; typestate declaration surface, summary engine, verification+excuses already delivered in graph/dsl.py, graph/summary.py, gates/_protocol_summary.py

<!-- ticket:T-0868 -->
```yaml
id: T-0868
title: typestate state-requirement verification + recorded language-excuse discharges
state: dropped
kind: security
origin: human
created: '2026-07-23'
priority: high
blocked_by:
- T-0866
- T-0867
parent: T-0739
scope:
- src/frob/arch/_typestate.py
- src/frob/gates/**
- tests/unit/test_typestate.py
acceptance:
- text: GIVEN a fixture calling a state-requiring function with no path establishing
    that state WHEN frob check runs THEN the typestate violation fires naming the
    function, the required state, and the witness path
  evidence: []
- text: GIVEN a fixture whose deinit obligation is discharged by a recorded language
    mechanism (Rust Drop, C++ RAII holder, Python with-block) WHEN frob check runs
    THEN the obligation is discharged with the mechanism named, and a GC-finalizer-only
    fixture is NOT discharged
  evidence: []
threat: null
component: arch
```
T-0739 child 3 (verification + excuses). State-requirement verification: a function valid only in state S must be unreachable on paths where S is not established (init-never-called class; TCP-handshake-style ordering). Language excuses are recorded DISCHARGES naming their mechanism per T-0383 caught_by doctrine: Rust Drop unless mem::forget observed; C++ RAII only when the init result is held by a destructor-bearing object; Python with-blocks count, GC finalizers NEVER count; TS using/try-finally. Declared LIMITS (no aliased per-object heap typestate; concurrency races belong to the T-0693 family) documented, not silently absorbed.

## Drop reason
- 2026-07-23: duplicate of the pre-existing T-0739 child set (T-0744/T-0745/T-0746/T-0747, mostly done) -- filed 2026-07-23 without checking parent-edge children; typestate declaration surface, summary engine, verification+excuses already delivered in graph/dsl.py, graph/summary.py, gates/_protocol_summary.py

<!-- ticket:T-0869 -->
```yaml
id: T-0869
title: typestate cleanup-on-all-paths obligation (deinit-never-called generalized)
state: dropped
kind: security
origin: human
created: '2026-07-23'
priority: high
blocked_by:
- T-0868
parent: T-0739
scope:
- src/frob/arch/_typestate.py
- tests/unit/test_typestate.py
acceptance:
- text: GIVEN a fixture establishing a state then returning early on one branch without
    cleanup WHEN frob check runs THEN the cleanup-on-all-paths violation fires naming
    the leaking path
  evidence: []
- text: GIVEN a fixture releasing on every path or transferring ownership WHEN frob
    check runs THEN no violation fires
  evidence: []
threat: null
component: arch
```
T-0739 child 4 (cleanup-on-all-paths). The *_deinit-never-called class generalized: every path leaving an established state (normal return, early return, raise/throw) must destroy/release it or hand ownership off, with the child-3 excuse discharges applying. Fixture set covers early-return leaks, exception-path leaks, and conditional-establishment joins.

## Drop reason
- 2026-07-23: duplicate of the pre-existing T-0739 child set (T-0744/T-0745/T-0746/T-0747, mostly done) -- filed 2026-07-23 without checking parent-edge children; typestate declaration surface, summary engine, verification+excuses already delivered in graph/dsl.py, graph/summary.py, gates/_protocol_summary.py

<!-- ticket:T-0871 -->
```yaml
id: T-0871
title: 'exports policy residue: drive all frob-exports missing-symbol lines to zero
  (9 packages, 57 symbols)'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
scope:
- src/frob/__init__.py
- src/frob/arch/__init__.py
- src/frob/lang/__init__.py
- src/frob/mutate/__init__.py
- src/frob/perf/__init__.py
- src/frob/scaffold/__init__.py
- src/frob/serve/__init__.py
- src/frob/testing/__init__.py
- src/frob/vet/__init__.py
acceptance:
- text: GIVEN the repo at this ticket's close WHEN frob check runs THEN every frob-exports
    package line reports zero public symbols missing from __init__.py, with each resolution
    being a deliberate export or demotion, not a waiver
  evidence: []
threat: null
component: exports
```
T-0204 child (exports family residue, continuing T-0600/T-0601). frob-exports still reports missing public symbols per package: src/frob 2, src/frob/arch 23, src/frob/lang 2, src/frob/mutate 3, src/frob/perf 5, src/frob/scaffold 1, src/frob/serve 11, src/frob/testing 2, src/frob/vet 8 (57 total at 2026-07-23 baseline; recount at start -- concurrent waves move it). Per-package policy decision as in T-0600/T-0601: export via __init__.py or demote to private (underscore) -- no blanket waiver. Deliverable: every frob-exports tool line reports 0 missing.

<!-- ticket:T-0872 -->
```yaml
id: T-0872
title: 'arch warning burn-down: gate:ARCH to zero unwaived (72 warns baseline) + suggestion
  sweep'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
scope:
- src/frob/**
- tests/**
acceptance:
- text: GIVEN the repo at this ticket's close WHEN frob check runs THEN gate:ARCH
    reports zero unwaived warnings and every remaining waiver carries a current, specific
    reason
  evidence: []
threat: null
component: arch
```
T-0204 child (arch family). gate:ARCH reports 72 warnings (13 waived) + frob-arch 55 warnings/183 suggestions at 2026-07-23 baseline (recount at start). Triage every warning: fix the code (long-function/god-class residue, calibrated-threshold stragglers) or waive with a specific reason per T-0289 doctrine. Suggestions: sweep for real fixes; remainder must be explainable. Deliverable: gate:ARCH 0 unwaived warnings and the summary line honest.

<!-- ticket:T-0873 -->
```yaml
id: T-0873
title: 'perf warning burn-down + waiver re-audit: gate:PERF to zero unwaived (24 warns,
  29 waivers baseline)'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
scope:
- src/frob/**
- tests/**
acceptance:
- text: GIVEN the repo at this ticket's close WHEN frob check runs THEN gate:PERF
    reports zero unwaived warnings and every remaining waiver has been re-verified
    with a current reason
  evidence: []
threat: null
component: perf
```
T-0204 child (perf family). gate:PERF reports 24 warnings + 29 waived at 2026-07-23 baseline (recount at start). Fix the unwaived findings; re-audit every standing waiver still holds after the T-0161-era heuristic fixes (drop stale waivers, re-reason keepers). Deliverable: gate:PERF 0 unwaived warnings, all waivers re-verified with current reasons.

<!-- ticket:T-0874 -->
```yaml
id: T-0874
title: 'stale-waiver purge: delete full-run WAIVE004 zero-match waivers, gate:WAIVE
  to zero (562 baseline)'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
scope:
- src/frob/**
- tests/**
- frob.toml
acceptance:
- text: GIVEN a full frob check after the purge WHEN gate:WAIVE evaluates THEN it
    reports zero warnings, and no previously-masked ERROR was introduced (any resurfaced
    finding is fixed or re-waived with a current reason)
  evidence: []
threat: null
component: gates
```
T-0204 child (waive family). gate:WAIVE reports 562 warnings at 2026-07-23 baseline, dominated by WAIVE004 "waiver matches 0 findings this run" from a FULL check (authoritative, unlike scoped-run WAIVE004 flakes -- see T-0846/T-0850 history). A waiver matching nothing in a full run is stale: the underlying finding was fixed or the rule changed. Sweep: for each WAIVE004 in a full run, delete the waiver; where deletion resurfaces a real finding, that finding is the honest state (fix or re-waive with a current reason). Also triage any WAIVE003-class aging warnings. MUST be run against a full (not scoped) check and re-verified with a second full run after the purge. Deliverable: gate:WAIVE 0 warnings.

<!-- ticket:T-0875 -->
```yaml
id: T-0875
title: 'TEST-family warning burn-down: per-symbol coverage campaign, gate:TEST to
  zero (486 baseline)'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
scope:
- src/frob/**
- tests/**
acceptance:
- text: GIVEN a full frob check at close WHEN gate:TEST evaluates THEN it reports
    zero warnings, with every resolution a real test or a reasoned per-symbol disposition,
    never a blanket waiver
  evidence: []
threat: null
component: testing
```
T-0204 child (test family). gate:TEST reports 486 warnings at 2026-07-23 baseline, dominated by TEST005 per-symbol no-direct-coverage warnings (plus TEST002/TEST014/TEST011/TEST003/TEST012/TEST006 stragglers). Zero-warnings requires per-symbol test coverage or explicit per-symbol disposition. This is a campaign: recount at start, group by package, and split into per-package sub-tickets if any package exceeds a session (this child is the accounting). Interacts with T-0589 (promote TEST005/TEST015 into TEST001 credit) -- coordinate so written tests satisfy the promoted rule, not just silence the warning.

<!-- ticket:T-0876 -->
```yaml
id: T-0876
title: wire frob exports --consumers CLI flag onto exports_consumers
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/app/exports_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- docs/commands/exports.md
threat: null
component: null
```
Follow-on to T-0858's xref-sunset reevaluation. `frob.exports.exports_consumers`
(added by T-0858) answers "who imports this symbol" as a library function, but
there is no CLI entry point yet -- wiring `frob exports --consumers <symbol>`
(or a dedicated verb) requires touching src/frob/app/exports_runner.py,
src/frob/app/config.py, and src/frob/__main__.py's exports parser, none of
which were in T-0858's declared scope. Do this before or around the
2026-10-01 T-0802 sunset so the CLI-level capability is not lost when
`frob xref` porcelain is removed.

<!-- ticket:T-0878 -->
```yaml
id: T-0878
title: 'gate: src/frob/exports/__init__.py missing frob:doc anchors (COV001/DOC, landed
  via T-0601 area merge)'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/exports/__init__.py
- docs/modules/exports.md
threat: null
component: null
```
Pre-existing, unrelated to any arch-cluster ticket: after merging current main into a worktree mid-session (T-0632), a fresh frob check --only gates-fast shows 5 new gate:COV001/gate:DOC errors on src/frob/exports/__init__.py (ConsumerRef, ConsumersResult, ConsumersResult.as_text, ConsumersResult.as_json, exports_consumers all public with no frob:doc edge). This file/these symbols are not part of any ticket in this worktree's scope -- discovered purely as a side effect of picking up main's advancement mid-session. File to track adding the missing frob:doc anchors (and any docs/modules/exports.md content they should point at).

<!-- ticket:T-0879 -->
```yaml
id: T-0879
title: Wire derived_state_lock's EXCLUSIVE side into .frob writers (mutate/doctor/dup/graph)
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/mutate/**
- src/frob/doctor.py
- src/frob/dup/**
- src/frob/graph/**
threat: null
component: null
```
T-0859 shipped `frob.process._lock.derived_state_lock`, a cross-process
shared/exclusive flock over `.frob/derived.lock`, and wired the SHARED
(reader) side into every `frob.check` entry point (`run_check`,
`run_check_cpp`, `run_check_rust`, `run_check_ts`) so a check run holds
it for its entire duration -- precheck through the last stage's read.

That closes the cross-process TOCTOU window between two frob CHECK
processes, but the EXCLUSIVE (writer) side of the contract is not yet
held by any current writer of `.frob`'s derived artifacts: `frob mutate`,
`frob doctor`'s rebuild path, and `frob.dup`/`frob.graph`'s cache
rebuilders can still rewrite `.frob/cache.db`/`dup.db`/`baseline` etc.
while a `frob check` reader holds the shared lock, or while another
writer is also mid-rebuild, with no serialization at all today.

Wire `derived_state_lock(root, exclusive=True)` into each of those
writer call sites (out of T-0859's `src/frob/check/**` +
`src/frob/process/**` scope -- this ticket covers `src/frob/mutate/**`,
`src/frob/doctor.py`, `src/frob/dup/**`, `src/frob/graph/**` as needed)
so the reader/writer contract `derived_state_lock`'s docstring already
describes is actually enforced end to end, not just documented as an
aspiration on the reader side.

See docs/modules/process.md's "Derived-state lock (T-0859)" section and
src/frob/process/_lock.py's module docstring for the primitive and its
contract.

<!-- ticket:T-0880 -->
```yaml
id: T-0880
title: 'system test env leak: FROB_AGENT/FROB_WORKTREE prefix breaks tests/system/**
  subprocess verification'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- tests/system/conftest.py
- docs/guides/agent-playbook.md
threat: null
component: null
```
Setting FROB_AGENT=1/FROB_WORKTREE=<path> in the shell env before running
`frob ticket evidence`/`frob test` (as the agent-playbook and dispatch
prompts instruct for every frob invocation) leaks into any system test's
own `run()` helper (tests/system/conftest.py, `os.environ | env`), which
spawns the real `frob` CLI as a subprocess -- so a system test that calls
`run("check", ...)` unscoped inherits FROB_AGENT and gets the T-0627
bare-check refusal, and a test that runs `frob check`/`stamp-coverage`
against its own `tmp_path` inherits FROB_WORKTREE and trips T-0836's
worktree-lease guard (cwd != leased worktree) -- both spurious, unrelated
to the test's actual correctness. Reproduced directly (T-0750 dispatch):

    FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob ticket evidence \
      T-0750 tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
    -> python verification run FAILED (run_selected: python exit=1)

    # same node id, bare invocation, no env leak:
    uv run frob ticket evidence T-0750 tests/system/test_cli_check.py::...
    -> passes, evidence recorded

This affects every dispatched worktree agent trying to record evidence or
run `frob test` against tests/system/**: the playbook's own mandated
env-var prefix actively breaks verification of the test suite it exists to
protect. Needs either (a) `tests/system/conftest.py`'s `run()` helper to
strip FROB_AGENT/FROB_WORKTREE before merging env (system tests exercise
`frob` as an end user would, never as a dispatched agent), or (b)
explicit playbook guidance that evidence-recording/pytest invocations
must NOT carry the FROB_AGENT/FROB_WORKTREE prefix (only `frob
check`/`frob ticket` gate commands need it). Filed here rather than fixed
silently since tests/system/conftest.py is out of my ticket's own scope
list for this dispatch in one case (T-0742) and touching the playbook
docs is a different kind of change than either of my two tickets.

<!-- ticket:T-0882 -->
```yaml
id: T-0882
title: 'SYS100 capability scanner: eval(/exec( needle substring-matches identifiers
  (self-match false positive)'
state: queued
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/strata/**
- strata-core/**
- design/frob.strata
- tests/unit/strata/test_conform_eval_needle.py
acceptance:
- text: GIVEN a scanned tree containing a function named _mutation_for_eval and no
    real eval/exec calls WHEN the SYS100 scan runs THEN no eval capability finding
    fires
  evidence: []
- text: GIVEN a tree with a genuine bare eval( call WHEN the SYS100 scan runs THEN
    the finding still fires
  evidence: []
- text: GIVEN the fixed scanner WHEN design/frob.strata's SYS100:eval waiver is deleted
    THEN frob sys audit stays green
  evidence: []
threat: null
component: strata
```
Found during T-0860: the strata SYS100 capability scanner's bare `eval(` needle substring-matches identifiers that merely CONTAIN "eval(" -- e.g. src/frob/mutate's `_mutation_for_eval(` function name -- producing a false "deploy uses eval" finding with zero real eval/exec builtin calls in the scanned tree. T-0860 recorded an honest waiver (design/frob.strata:519, waive "SYS100:eval" citing this ticket) rather than a false may-declaration. Fix the scanner: match `eval(`/`exec(` as call sites of the BUILTIN identifier (word-boundary / tokenized match, not raw substring), add a fixture reproducing the _mutation_for_eval self-match, then delete the waiver.

<!-- ticket:T-0884 -->
```yaml
id: T-0884
title: 'ticket evidence: direct-pytest verification leaks caller''s FROB_WORKTREE/FROB_AGENT
  lease env into the spawned test process'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/app/ticket_runner.py
threat: null
component: null
```
Found while working T-0821: `frob ticket evidence`'s direct-pytest
verification fallback (`_run_pytest_directly` in
src/frob/app/ticket_runner.py) spawns `uv run pytest <node_ids> -q -o
addopts=` inheriting the calling shell's full environment. When the
caller is a dispatched worktree agent (FROB_AGENT=1, FROB_WORKTREE=<this
worktree>, both required by every other `frob ticket` invocation per
docs/guides/agent-playbook.md section 1/3), any test that itself performs
real git worktree operations against a throwaway tmp_path fixture repo
(e.g. tests/test_ticket_land.py's `TestLand`/`TestPlannedStateAutoAdvanceOnLand`
classes) gets refused by `frob.tickets._worktree_guard.enforce_worktree_lease`
with `WorktreeLeaseViolation`: the guard sees FROB_WORKTREE pointing at
the AGENT's own worktree and refuses to let the test mutate its own
unrelated tmp_path repo, since that path does not match the leased
worktree.

The same test passes cleanly under `frob check`'s own coverage/test gate
stage (which apparently manages/sanitizes the pytest subprocess
environment differently) and under a plain `uv run pytest <node_id>` with
no FROB_AGENT/FROB_WORKTREE exported -- only `frob ticket evidence`'s
direct-invocation path is affected.

Workaround used in T-0821: unset both vars for just the one `frob ticket
evidence` call. Real fix belongs in `_run_pytest_directly` (and any sibling
runner-based verification path with the same shape) in
src/frob/app/ticket_runner.py -- strip FROB_AGENT/FROB_WORKTREE (and any
other worktree-lease env) from the subprocess environment before spawning
the verification pytest run, so a ticket's own evidence-recording step
never leaks the recorder's own lease into the tests being verified.

<!-- ticket:T-0885 -->
```yaml
id: T-0885
title: 'mutate: leftover mutant journal not auto-restored on next run start (xdist
  worker crash / external SIGTERM, beyond T-0857''s own-crash detection)'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/mutate/**
threat: null
component: null
```
Found while working T-0855: `tests/test_tickets_mutation_evidence.py::
TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings`
is a dogfooding self-check that runs `check_ticket_mutation_evidence`
against THIS repo's own real worktree root (mutating
src/frob/tickets/_mutation_evidence.py and src/frob/tickets/_land.py in
place, journaling originals via `frob.mutate._journal` for a safe revert
per T-0857).

Under heavy concurrent load on the machine (many other agent worktrees
running `frob check`/pytest simultaneously, observed directly via `ps
aux` while working T-0855), this test's pytest-xdist worker was observed
crashing outright ("[gw0] node down: Not properly terminated") while a
mutant was live, and separately, an EXTERNAL SIGTERM (a `timeout N`
wrapper killing the foreground pytest process from outside, not a crash
frob's own harness could detect) also left a mutant applied on disk --
both left `src/frob/tickets/_mutation_evidence.py` corrupted (formatting
collapsed, a boolean literal flipped) in the real worktree tree, with no
automatic recovery on the next run. T-0857 covers the case where
`frob.mutate`'s OWN harness detects its own crash and restores from the
journal; neither an xdist worker crash nor an external process kill goes
through that path, so the journaled backup in `.frob/mutate-backup/`
sits unused and the corrupted file is never auto-restored.

Both incidents were recovered manually here (`git show HEAD:<path>` to
get the clean committed original, since the corruption was on an
uncommitted working-tree file). Suggested fix direction: on `frob check`/
`frob test`/`pytest` startup (or via a dedicated `frob mutate restore`
subcommand run by CI/agent tooling at session start), scan
`.frob/mutate-backup/*.json` for journal entries whose target file's
current on-disk content does NOT match either the journaled original OR
a known-applied-mutant state expected by an in-progress run, and restore
from the journal automatically -- generalizing T-0857's crash-detection
restore to cover ANY leftover journal entry found stale at the start of
a fresh run, regardless of what killed the previous one.

<!-- ticket:T-0886 -->
```yaml
id: T-0886
title: 'gates: real ctest source-accurate collection so the cpp structural fallback
  can retire'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/testing/_collect.py
- src/frob/gates/__init__.py
- tests/test_gates.py
threat: null
component: null
```
T-0730 wires `collect_ts_tests`/`collect_cpp_tests` into `frob.gates._load_tests`
and retires the ts structural fallback (`_NATIVE_TEST_EXTENSIONS`) now that a real
vitest-backed node id can match a TS `frob:tests` directive's `path::name` symref
exactly.

C/C++ could not be retired in the same pass: `collect_cpp_tests`'s own docstring
discloses a KNOWN APPROXIMATION -- a ctest node id anchors to the build directory
(`<build_dir>::<test name>`), not the real source file a `frob:tests` directive
lives above, so a C/C++ directive's `src` (`tests/foo_test.cpp::TestName`) can
essentially never land in `tests.node_ids` even when the test genuinely exists
and ran. Retiring the structural fallback for C/C++ today would silently drop
ALL existing C/C++ TEST001-004 credit in any project using this gate, not
tighten it.

Real fix needs either (a) a ctest source-file mapping (e.g. parsing
`CTestTestfile.cmake` or `--show-only=json-v1`'s richer `properties` for a
`FIXTURES_SETUP`/source hint, if ctest exposes one) or (b) a different collector
for gtest-discovered cases via `--gtest_list_tests` per test binary, which does
carry real per-case names closer to source. Scoped out of T-0730 deliberately,
not silently dropped -- see T-0730's Done report.

<!-- ticket:T-0887 -->
```yaml
id: T-0887
title: done-report --base-ref hangs when the named base ref does not exist in the
  clone
state: queued
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/tickets/**
- tests/test_ticket_runner_done_report.py
acceptance:
- text: GIVEN a clone with no local or remote-tracking main WHEN done-report --base-ref
    main runs THEN it exits nonzero within seconds naming the unresolvable ref
  evidence: []
- text: GIVEN a repo where main exists WHEN done-report --base-ref main runs THEN
    behavior is unchanged
  evidence: []
threat: null
component: tickets
```
Found during T-0590 attempt 2 (see its failure log): `frob ticket done-report <id> --base-ref main` HANGS indefinitely when run in a clone that has no local `main` branch (e.g. a scratch clone created from a worktree branch). Expected: fail fast with a clear error naming the missing ref (or resolve origin/main), never hang. Likely a subprocess waiting on git prompting or an unbounded retry around the base-ref diff. Repro: clone any repo checked out at a non-main branch without fetching main, run done-report --base-ref main.

<!-- ticket:T-0888 -->
```yaml
id: T-0888
title: register REG011 in _KNOWN_GATE_RULES + CHK-GATE-REG011 registry entry (T-0680
  follow-up)
state: dropped
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
- docs/design/registry/check-coverage.yaml
- tests/test_check_coverage_registry.py
acceptance:
- text: GIVEN frob check runs WHEN the registry gate summary renders THEN REG011 appears
    as a known rule and REG010 reports no missing CHK-GATE-REG011 registry entry
  evidence: []
threat: null
component: gates
```
Follow-up to T-0680 (landed 0d7e2f2b): REG011 (out_of_scope caught_by verification, WARN) is implemented in _registry_exhaustiveness.py but not registered in frob.gates.__init__._KNOWN_GATE_RULES nor in docs/design/registry/check-coverage.yaml (CHK-GATE-REG011 entry) -- deferred because another agent held gates/__init__.py during T-0680. Register both (REG010 will demand the yaml row). Refiled from a worktree draft that did not survive T-0680's ledger recovery.

## Drop reason
- 2026-07-23: absorbed by T-0903 (audit finding H3): REG011 is one of 7 missing _KNOWN_GATE_RULES ids being registered together, with T-0901 adding the drift-lock

<!-- ticket:T-0889 -->
```yaml
id: T-0889
title: ticket CLI write-back clobbers externally-replaced ledger with stale in-memory
  snapshot (reverted 3 done tickets)
state: queued
kind: bug
origin: agent
created: '2026-07-23'
priority: high
parent: null
scope:
- src/frob/tickets/**
- tests/test_ticket_store_stale_snapshot.py
acceptance:
- text: GIVEN tickets.md is externally replaced between a CLI process's load and its
    write-back WHEN the write happens THEN no unrelated ticket block regresses (reload-and-merge
    or loud refusal), proven by a regression test
  evidence: []
threat: null
component: tickets
```
Real incident during T-0680 (see its Done report): in a worktree whose tickets.md had just been restored to main's version (section 10b recipe), a sequence of frob ticket start/evidence/sweep/done-report calls SILENTLY REVERTED three unrelated tickets (T-0660/T-0661/T-0719) from done back to queued with evidence and Done reports wiped -- the CLI appears to write back a stale in-memory ticket-queue snapshot loaded before the restore, clobbering the on-disk ledger state. Same corruption family as the land-splice regression (T-0577 lineage) but in the plain CLI write path, not land. Investigate the store's load/write lifecycle for a cached snapshot surviving an external file replacement (mtime/digest check on write-back would fail loudly). Fix = detect ledger-changed-since-load and reload before any write, plus a regression test that replaces tickets.md between load and write.

<!-- ticket:T-0890 -->
```yaml
id: T-0890
title: 'mutate: leftover mutant journal not auto-restored on next run start (xdist
  worker crash / external SIGTERM, beyond T-0857''s own-crash detection)'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/mutate/**
threat: null
component: null
```
Found while working T-0855: `tests/test_tickets_mutation_evidence.py::
TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings`
is a dogfooding self-check that runs `check_ticket_mutation_evidence`
against THIS repo's own real worktree root (mutating
src/frob/tickets/_mutation_evidence.py and src/frob/tickets/_land.py in
place, journaling originals via `frob.mutate._journal` for a safe revert
per T-0857).

Under heavy concurrent load on the machine (many other agent worktrees
running `frob check`/pytest simultaneously, observed directly via `ps
aux` while working T-0855), this test's pytest-xdist worker was observed
crashing outright ("[gw0] node down: Not properly terminated") while a
mutant was live, and separately, an EXTERNAL SIGTERM (a `timeout N`
wrapper killing the foreground pytest process from outside, not a crash
frob's own harness could detect) also left a mutant applied on disk --
both left `src/frob/tickets/_mutation_evidence.py` corrupted (formatting
collapsed, a boolean literal flipped) in the real worktree tree, with no
automatic recovery on the next run. T-0857 covers the case where
`frob.mutate`'s OWN harness detects its own crash and restores from the
journal; neither an xdist worker crash nor an external process kill goes
through that path, so the journaled backup in `.frob/mutate-backup/`
sits unused and the corrupted file is never auto-restored.

Both incidents were recovered manually here (`git show HEAD:<path>` to
get the clean committed original, since the corruption was on an
uncommitted working-tree file). Suggested fix direction: on `frob check`/
`frob test`/`pytest` startup (or via a dedicated `frob mutate restore`
subcommand run by CI/agent tooling at session start), scan
`.frob/mutate-backup/*.json` for journal entries whose target file's
current on-disk content does NOT match either the journaled original OR
a known-applied-mutant state expected by an in-progress run, and restore
from the journal automatically -- generalizing T-0857's crash-detection
restore to cover ANY leftover journal entry found stale at the start of
a fresh run, regardless of what killed the previous one.

<!-- ticket:T-0891 -->
```yaml
id: T-0891
title: 'ticket evidence: direct-pytest verification leaks caller''s FROB_WORKTREE/FROB_AGENT
  lease env into the spawned test process'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/app/ticket_runner.py
threat: null
component: null
```
Found while working T-0821: `frob ticket evidence`'s direct-pytest
verification fallback (`_run_pytest_directly` in
src/frob/app/ticket_runner.py) spawns `uv run pytest <node_ids> -q -o
addopts=` inheriting the calling shell's full environment. When the
caller is a dispatched worktree agent (FROB_AGENT=1, FROB_WORKTREE=<this
worktree>, both required by every other `frob ticket` invocation per
docs/guides/agent-playbook.md section 1/3), any test that itself performs
real git worktree operations against a throwaway tmp_path fixture repo
(e.g. tests/test_ticket_land.py's `TestLand`/`TestPlannedStateAutoAdvanceOnLand`
classes) gets refused by `frob.tickets._worktree_guard.enforce_worktree_lease`
with `WorktreeLeaseViolation`: the guard sees FROB_WORKTREE pointing at
the AGENT's own worktree and refuses to let the test mutate its own
unrelated tmp_path repo, since that path does not match the leased
worktree.

The same test passes cleanly under `frob check`'s own coverage/test gate
stage (which apparently manages/sanitizes the pytest subprocess
environment differently) and under a plain `uv run pytest <node_id>` with
no FROB_AGENT/FROB_WORKTREE exported -- only `frob ticket evidence`'s
direct-invocation path is affected.

Workaround used in T-0821: unset both vars for just the one `frob ticket
evidence` call. Real fix belongs in `_run_pytest_directly` (and any sibling
runner-based verification path with the same shape) in
src/frob/app/ticket_runner.py -- strip FROB_AGENT/FROB_WORKTREE (and any
other worktree-lease env) from the subprocess environment before spawning
the verification pytest run, so a ticket's own evidence-recording step
never leaks the recorder's own lease into the tests being verified.

<!-- ticket:T-0892 -->
```yaml
id: T-0892
title: 'arch: fold TypeDesignCategory into ArchCategory once _models.py lease is free
  (T-0621 follow-up)'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/arch/_typedesign.py
- src/frob/arch/_models.py
- docs/modules/arch.md
- tests/unit/test_arch.py
threat: null
component: null
```
T-0621 (arch: type-driven design checks) implemented its four checks
(illegal-states-representable, primitive-obsession, parse-dont-validate,
boolean-flag-param) against a LOCAL TypeDesignCategory/TypeDesignSuggestion
pair in src/frob/arch/_typedesign.py rather than the shared
frob.arch._models.ArchCategory/ArchSuggestion, because at implementation
time T-0620 (a sibling ticket in the same ARCH1xx cluster) held an active
scope lease on src/frob/arch/_models.py and `frob ticket scope --add`
refused with ScopeLeaseConflict.

Once T-0620 is closed/landed and the lease is free: fold the four
TypeDesignCategory string values into ArchCategory, migrate
TypeDesignSuggestion's four producer functions in _typedesign.py to build
frob.arch._models.ArchSuggestion instead of the local model, and delete
TypeDesignCategory/TypeDesignSuggestion. Purely mechanical -- the four
check functions' logic does not change, only which model they construct.

<!-- ticket:T-0893 -->
```yaml
id: T-0893
title: lang/** tree-sitter parse has no file-size cap or timeout -- untrusted-file
  DoS trust-boundary gap
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/lang/__init__.py
threat: null
component: null
```
Found while working T-0786 (gate-vacuousness sweep).

frob.lang's tree-sitter ingestion (`_parse` in src/frob/lang/__init__.py,
~line 316-370) reads the ENTIRE file into memory (`path.read_bytes()`) and
hands it to tree-sitter's `parser.parse(source)` with no file-size cap and
no parse timeout, for every file frob's graph walk visits -- including
files under an audited/untrusted repo tree (this is a general-purpose
static-analysis tool other people's repos get pointed at, not just this
one's own source). Tree-sitter's incremental-parse error recovery is
generally robust but is not immune to pathological-input classes (deeply
nested brackets/parens driving quadratic-ish recovery, or simply a
multi-GB single file) -- and there is no structural guard here at all, not
even a generous one: no `st_size` check before `read_bytes()`, no
wall-clock budget around `parser.parse()`.

Fix direction: add a configurable max-file-size guard (skip + record a
PARSE001-shaped "too large to parse" finding rather than attempt it) and a
wall-clock timeout around the tree-sitter parse call in `_parse`, so a
single adversarial or merely enormous file cannot hang or exhaust memory
in a `frob check` run over an untrusted tree.

<!-- ticket:T-0894 -->
```yaml
id: T-0894
title: Registry-backed gates (COMPLIANCE005/REG*/DEC*) cannot distinguish never-adopted
  from deleted-registry
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_registry_exhaustiveness.py
threat: null
component: null
```
Found while working T-0786 (gate-vacuousness sweep).

Several registry-backed gates share one "missing backing file/dir means no
claim, not a violation" posture, each independently justified in its own
docstring: `registry_gate` (REG001-011, src/frob/gates/_registry_exhaustiveness.py:812,
"if not base.is_dir(): ..."), `compliance_gate` (COMPLIANCE005,
src/frob/gates/__init__.py:7665, explicitly "matching registry_gate's own
missing-directory posture"), and `decisions_gate`'s DEC001/DEC002 half
(src/frob/gates/__init__.py:7035, "if not decisions_dir(root).exists():
return ()"). Each is individually reasonable ("a repo with no registry
makes no claim") but the aggregate effect is a real vacuousness vector none
of the three docstrings names: these YAML/markdown backing files, once a
repo HAS adopted them, become security/compliance-load-bearing artifacts
(COMPLIANCE005 in particular gates regulatory-control disposition
exhaustiveness) whose accidental or malicious DELETION is structurally
indistinguishable, to every one of these gates, from "this repo never
adopted the registry" -- both silently clear every violation the registry
existing would have produced. Nothing elsewhere in the gate catalog fires
on the deletion itself (no REF/DOC-family check treats
`docs/design/registry/compliance.yaml`'s disappearance as itself a
finding) once a repo has adopted the file.

Fix direction: for a repo that has ever adopted one of these registries
(a simple signal: the file/dir is present in the merge-base commit but
absent in the working tree, or a frob.toml flag marking the registry as
"required once adopted"), treat its disappearance as a loud, ideally
unwaivable violation rather than silently degrading to the "never adopted"
posture. Scope this ticket to at minimum COMPLIANCE005 (the
highest-stakes instance); REG*/DEC* can follow the same pattern once the
mechanism exists.

<!-- ticket:T-0895 -->
```yaml
id: T-0895
title: Add regression test for dup_gate native-unavailable loud-violation behavior
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
threat: null
component: null
```
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2), pairs with the dup_gate native-unavailable fix ticket.

Add a regression test asserting that `dup_gate` with `[dup].enforce=true`
and a mocked/forced `core_available() == False` produces a real Violation
(not just a log line), closing the "opted-in enforcement silently no-ops
when the native toolchain is missing" gap the paired fix ticket addresses.

<!-- ticket:T-0896 -->
```yaml
id: T-0896
title: dup_gate silently no-ops (log-only) when frob-core native is unavailable despite
  [dup].enforce=true
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
threat: null
component: null
```
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2).

`dup_gate` (src/frob/gates/__init__.py:8175, DUP001/DUP002) is opt-in via
`[dup].enforce = true` in frob.toml (disclosed, fine) -- but when enforce
IS on and the `frob-core` native extension is unavailable
(`core_available()` returns False), it degrades to:

    _log.warning("dup_gate: frob-core not installed; DUP rules skipped")
    return ()

a bare log warning, not a `Violation` -- so `frob check`'s exit code and
violation list are UNCHANGED whether DUP001/002 genuinely found nothing or
silently could not run at all. This repo's own playbook
(docs/guides/agent-playbook.md section 1) documents exactly this failure
mode as a REAL, recurring one: "Fresh worktrees do not inherit a sibling
worktree's build -- strata_core/frob_core come up missing" (T-0144) --
meaning a repo that has opted into `[dup].enforce=true` and then runs
`frob check` from a worktree where `make core` has not yet run gets zero
DUP001/002 enforcement, with a green gate-summary line and only a WARNING
in the logs (which the playbook's own section 3 names as something never
piped/read live in a normal `frob check` invocation).

This is the same class T-0552/TEST013 already fixed for the coverage
gate's own native-unavailable structural fallback ("make the structural-
fallback credit ... LOUD instead of silent") -- DUP never got the
equivalent treatment.

Fix direction: when `[dup].enforce=true` and `core_available()` is False,
emit a loud WARN (or ERROR)-tier Violation naming the missing native and
the remediation (`make core`), instead of a log-only degrade -- mirroring
TEST013's shape for the coverage gate.

<!-- ticket:T-0897 -->
```yaml
id: T-0897
title: RENDER001/PII010/SEC-CVE-FINGERPRINT-001 each run a private silent-skip-on-unparseable
  file read outside PARSE001
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/_render_lint.py
- src/frob/gates/_pii_structural.py
- src/frob/gates/_cve_fingerprint_scan.py
threat: null
component: null
```
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2).

At least three gates run their OWN private per-file read+parse, entirely
independent of `frob.lang.parse_file`'s centrally-tracked pipeline (the
one `snapshot.parse_failures`/PARSE001, T-0558, actually covers) -- and
each silently skips a file that fails to read/parse, with only a DEBUG log
line, no Violation of any kind:

- `render_lint_gate` (src/frob/gates/_render_lint.py:220-224):
  `except (OSError, UnicodeDecodeError, SyntaxError): skip` around its own
  `ast.parse(text, filename=rel_path)` call.
- `pii_structural_gate` (src/frob/gates/_pii_structural.py:1861-1865): the
  identical `except (OSError, UnicodeDecodeError, SyntaxError): skip`
  shape around its own `ast.parse` call, for PII010/SEC110.
- `cve_fingerprint_scan_gate` (src/frob/gates/_cve_fingerprint_scan.py:183-187):
  `except (OSError, UnicodeDecodeError): skip` around its plain text read
  (no parse, but the same silent-skip shape) for SEC-CVE-FINGERPRINT-001.

Net effect: a Python file with a syntax error (or bad encoding) is
invisible to RENDER001 (a bare-print-bypassing-Renderer check) and to
PII010/SEC110 (structural PII/secret-shape detection) -- exactly the two
gate families where "this file's content was never actually inspected"
matters most from a security-review standpoint -- with zero surfaced
signal that the skip happened at all, unlike the general PARSE001
mechanism T-0558 built specifically to make this class loud for the
`frob.lang`-routed gates.

Fix direction: route these three gates' file reads through the shared
`frob.lang.parse_file` (or at minimum consult
`frob.lang.partial_parse_files()`/`snapshot.parse_failures`) instead of a
private `ast.parse`/read call with its own silent except, so a single
PARSE001-shaped signal covers every gate that needs a parseable file
rather than each gate independently deciding to stay silent on failure.

<!-- ticket:T-0898 -->
```yaml
id: T-0898
title: Add regression tests for RENDER001/PII010 loud-on-unparseable-file behavior
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/_render_lint.py
- src/frob/gates/_pii_structural.py
- tests/test_gates.py
threat: null
component: null
```
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2), pairs with the private-ast.parse-silent-skip fix ticket.

Add a regression test per affected gate (RENDER001, PII010/SEC110 at
minimum) asserting a syntactically-broken fixture file produces a loud
finding (a PARSE001-shaped violation, or the gate's own equivalent)
instead of a silent zero-violation pass, closing the private-parse-path
silent-skip gap the paired fix ticket addresses.

<!-- ticket:T-0899 -->
```yaml
id: T-0899
title: 'Add regression gate/test: empty-scope ticket must not silently pass SCOPE001'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
threat: null
component: null
```
Found while working T-0786 (gate-vacuousness sweep), pairs with the
SCOPE001 empty-scope fix ticket.

Add a regression gate/lint (or extend SCOPE001 itself) that fires loudly
whenever an in-progress/non-queued ticket carries an empty `scope` tuple --
so the "no declared scope" state cannot silently coexist with an active
ticket ever again, whichever fix direction the paired ticket lands. Bind a
test asserting a ticket with scope=() and a non-empty diff produces a
violation instead of `scope_gate` returning `()`.

<!-- ticket:T-0900 -->
```yaml
id: T-0900
title: Add regression test for COMPLIANCE005 adopted-then-deleted-registry detection
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
threat: null
component: null
```
Found while working T-0786 (gate-vacuousness sweep), pairs with the
registry-deletion detection fix ticket.

Bind a regression test per affected gate (starting with COMPLIANCE005)
asserting that deleting a previously-present registry file between two
`frob check` runs on the same tree produces a loud violation rather than a
silently clean report, closing the "adopted-then-deleted" gap the paired
fix ticket addresses.

<!-- ticket:T-0901 -->
```yaml
id: T-0901
title: 'Add drift-lock test: every emitted rule= literal must be a _KNOWN_GATE_RULES
  member'
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
threat: null
component: null
```
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2), pairs with the _KNOWN_GATE_RULES completeness fix ticket.

Add a regression test that statically enumerates every `rule="..."`
literal passed to a `Violation(...)` constructor call across
`src/frob/gates/**` and `src/frob/strata/**` (an AST/regex scan is fine,
mirroring how `_KNOWN_GATE_RULES` itself is a static frozenset) and
asserts it is a subset of `known_gate_rule_ids()` -- so a new gate/rule
added without a matching `_KNOWN_GATE_RULES` entry fails CI immediately
instead of silently reproducing the PARSE001/TICK005/REG011/PII011/
PII012/SYSWAIVE002/THREAT006 omission class.

<!-- ticket:T-0902 -->
```yaml
id: T-0902
title: Add PARSE002 gate wiring partial_parse_files() into frob check + regression
  test
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/_parse_failures.py
- tests/test_gates.py
threat: null
component: null
```
Found while working T-0786 (gate-vacuousness sweep), pairs with the
PARSE002 (partial-parse) fix ticket.

Bind a regression test asserting `frob.lang.partial_parse_files()` is
actually consumed by `frob check`'s gate dispatch (e.g. a fixture with a
syntax error partway through a file, asserting the missing tail symbol's
COV001 obligation is NOT silently dropped, and that a PARSE002-shaped
violation fires). This closes the "queryable accessor with zero consumers"
class of gap the same way T-0558 closed it for hard parse failures.

<!-- ticket:T-0903 -->
```yaml
id: T-0903
title: _KNOWN_GATE_RULES omits 7 real, currently-firing rule ids (PARSE001/TICK005/REG011/PII011/PII012/SYSWAIVE002/THREAT006)
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
threat: null
component: null
```
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round 2 --
completing the full catalog after the first pass's partial coverage).

`frob.gates.known_gate_rule_ids()` / `_KNOWN_GATE_RULES` (src/frob/gates/__init__.py:904)
is the single frozenset every `frob:waive RULE reason="..."` directive's
validity (WAIVE002: "rule id can never match") is checked against, AND the
set `known_rule_ids` a strata `caught_by`/registry `handled_by` resolution
treats as a recognized, real rule id rather than an unresolved reference
(the function's own docstring: "for strata caught_by resolution to
recognize rule-id-shaped references ... instead of treating them as
unresolved by default").

Verified via direct `known_gate_rule_ids()` call plus a grep for every
`rule="..."` site that actually constructs a `Violation`: at least 7 real,
firing rule ids are MISSING from this frozenset, despite gates.py actively
emitting them today:

- `PARSE001` (src/frob/gates/_parse_failures.py) -- registered as an
  always-run process job in `_ALL_GATES`'s "parse_failures" entry, but
  absent from `_KNOWN_GATE_RULES`.
- `TICK005` (src/frob/gates/__init__.py:7352, `_tick005_merge_state_regression`,
  dispatched from `tickets_gate`).
- `REG011` (src/frob/gates/_registry_exhaustiveness.py:301/317, T-0680's
  out_of_scope-reason check, dispatched from `registry_gate`).
- `PII011`, `PII012` (src/frob/gates/_pii_structural.py:892/957, dispatched
  from `pii_structural_gate`).
- `SYSWAIVE002` (src/frob/strata/_contention.py:437).
- `THREAT006` (src/frob/strata/_threat.py:1477).

This is exactly the DEAD001-class omission T-0753 already fixed once
("This was a listing omission, not evidence DEAD001 was ever renamed or
removed" -- see `_KNOWN_GATE_RULES`'s own DEAD001 comment) -- but the same
listing-omission bug has recurred at least 6 more times since, for rules
added by later tickets that never circled back to add their own entry
here. Concretely: any `frob:waive PARSE001 reason="..."` (or TICK005/
REG011/PII011/PII012/SYSWAIVE002/THREAT006) written anywhere in the tree
today is silently flagged WAIVE002-ineffective ("the rule id can never
match anything") despite targeting a perfectly real, currently-firing
rule -- and a strata `caught_by`/registry `handled_by` claim naming any of
these ids is treated as an UNRESOLVED reference rather than a recognized
enforced control, which can silently understate a threat-model/compliance
disposition's real coverage.

Fix direction: add the 7 missing ids to `_KNOWN_GATE_RULES`. More
durably, per this ticket's own pattern-recognition: add a drift-lock test
(or a small script gate) that diffs `_KNOWN_GATE_RULES` against every
`rule="..."` string literal actually constructed inside `src/frob/gates/**`
and `src/frob/strata/**`'s Violation-building sites, failing loud on any
gap -- so this omission class cannot recur a third time.

<!-- ticket:T-0904 -->
```yaml
id: T-0904
title: Add regression test/lint for lang/** parse size+timeout guard
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/lang/__init__.py
- tests/unit
threat: null
component: null
```
Found while working T-0786 (gate-vacuousness sweep), pairs with the
lang/** file-size/timeout guard fix ticket.

Add a regression test (and, if practical, a static lint) asserting every
`frob.lang` parse entrypoint (`parse_file`/`_parse`/`_parse_strata_file`)
enforces a bounded size/time budget before/around the actual
tree-sitter/strata-core parse call -- so a future refactor cannot silently
drop the guard the paired fix ticket adds.

<!-- ticket:T-0905 -->
```yaml
id: T-0905
title: Partial tree-sitter parse (salvaged, has_error) silently drops symbols -- partial_parse_files()
  has zero gate consumers
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/lang/__init__.py
- src/frob/gates/_parse_failures.py
threat: null
component: null
```
Found while working T-0786 (gate-vacuousness sweep).

frob.lang's tree-sitter ingestion (src/frob/lang/__init__.py's `_parse`/
`_warn_if_partial_tree`, ~line 280-315) already distinguishes a HARD parse
failure (unusable tree: `root_node is None` or `has_error and
child_count == 0`) from a PARTIAL/salvaged parse (`has_error` but the
grammar still produced usable top-level structure). The hard-failure case
is a real, loud gate violation (PARSE001, `frob.gates._parse_failures`,
T-0558/T-0561). The partial case is NOT: `_warn_if_partial_tree` only logs a
WARNING and records the path into the module-level `_partial_parse_files`
set, exposed via the public `partial_parse_files()` accessor -- but nothing
in `frob.gates` (or the `frob check` CLI dispatch) ever calls
`partial_parse_files()`. Verified via repo-wide grep: the only references to
`partial_parse_files`/`_partial_parse_files` are the definition site itself,
its own docstring, and the `__all__` export -- zero gate, zero CLI, zero
test consumes it.

This is the PARSE001 vacuousness bug (T-0404 finding 2, T-0558's own
module docstring) reopened for the partial-tree half: "a syntax error
present, some top-level symbols may be silently dropped from the salvaged
tree" -- exactly the class PARSE001 exists to make loud for a full parse
failure -- but for a partial parse, every downstream gate (COV001, DRIFT,
INV, TEST001-*, ...) sees only the symbols tree-sitter's error-recovery
happened to salvage, with the missing remainder invisible and unflagged.
A source file with a syntax error near its top (a stray unmatched brace, an
unterminated string before the real content) can silently drop obligations
for everything after it, with only a DEBUG/WARNING-level log line as
evidence -- which the T-0558 module docstring itself calls "only visible
above the default log level" and explicitly names as the still-open gap
(finding 1 in that docstring: "no gates stage at all ... to notice a
WARNING here").

Fix direction: add a PARSE002 (or extend PARSE001) ERROR-tier gate over
`frob.lang.partial_parse_files()`, symmetric with PARSE001's hard-failure
handling -- loud by default, waivable with an honest reason for a known
intentionally-malformed fixture.

<!-- ticket:T-0906 -->
```yaml
id: T-0906
title: SCOPE001 vacuously passes when ticket.scope is empty (no non-empty-scope precondition)
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
scope:
- src/frob/gates/__init__.py
- src/frob/tickets/_models.py
threat: null
component: null
```
Found while working T-0786 (gate-vacuousness sweep).

SCOPE001 (frob.gates._models scope_gate, src/frob/gates/__init__.py:5006)
returns () with no enforcement at all whenever `ticket.scope` is empty:

    if not ticket.scope:
        _log.debug(...)
        return ()

`Ticket.scope`/`TicketSpec.scope` both default to `()` (src/frob/tickets/_models.py)
and no validator enforces a non-empty scope at ticket-creation time. A ticket
filed via `frob ticket new` without `--scope` (or one whose scope was cleared
by a bad `frob ticket scope` edit) is therefore NEVER checked by SCOPE001 --
its diff can touch any file in the repo and this gate stays silent. This is a
satisfied-by-absence vacuousness vector: the gate exists specifically to keep
a worked ticket's diff inside its declared scope, but a ticket with no
declared scope silently gets the LEAST enforcement, not the most.

Fix direction: either (a) refuse to start/queue a ticket whose scope is empty
(TicketSpec/Ticket validator, or a `frob ticket start` precondition), or (b)
change scope_gate's empty-scope branch to a loud, unwaivable violation instead
of a silent pass -- symmetric with how COV002/TODO001 treat a failed diff
load (T-0550/T-0719) as a loud violation rather than a silently-cleared
enforcement surface. Prefer (a): an empty scope should never be a valid
ticket state to begin work from.

<!-- ticket:T-0907 -->
```yaml
id: T-0907
title: killed land can reset main to a STALE tip (~60 commits lost off-branch; reflog
  reset moving-to-HEAD)
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: critical
parent: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
acceptance:
- text: GIVEN a land killed by SIGTERM mid-staging WHEN the next frob command runs
    THEN main's tip equals the pre-land tip and the repair path reports what was cleaned
  evidence: []
- text: GIVEN a land whose failure-unwind runs WHEN main's tip differs from the tip
    recorded at this run's start THEN the unwind refuses loudly instead of resetting
  evidence: []
threat: tampering
component: tickets
```
Incident 2026-07-23 (this session): two `frob ticket land T-0765` attempts were killed by an external 580s timeout mid-run (SIGTERM, exit 143). Afterward, MAIN's HEAD had been reset from d67a82d2 back to b3589c3e -- the tip from ~60 commits earlier -- with reflog entry "reset: moving to HEAD" transitioning d67a82d2 -> b3589c3e. A subsequent land attempt then refused with the T-0463 IncompleteLand completeness assertion (staged squash-apply missing 5 files), which is what surfaced the damage. Recovery was `git reset --hard d67a82d2` (all objects intact); no data lost, but only because the coordinator checked the reflog before committing anything new.

Root-cause hypotheses to investigate: land records a pre-land tip (or resolves "HEAD") from stale cached state (.frob cache / an earlier killed run's snapshot) and its failure-unwind resets main to that stale value; or the kill mid-staging left HEAD/index in a state where a later unwind's `git reset` resolved HEAD incorrectly. Fix requirements: (1) land's unwind must reset ONLY to the tip it verified at THIS run's start, stored run-locally (not in shared .frob state); (2) the unwind must refuse (loud error, no reset) if main's current tip no longer equals the recorded pre-land tip; (3) signal-safety: land should trap SIGTERM/SIGINT during staging and complete the unwind coherently or leave an explicit .frob/land-in-progress marker that the next invocation repairs; (4) a regression test that SIGKILLs a land mid-staging and asserts main's tip is unchanged afterward.
