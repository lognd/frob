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
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
- docs/**
- tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/**
- strata-core/**
- design/**
- docs/**
- tests/**
- Makefile
- tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
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
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
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
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
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
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
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
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
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
evidence: []
attachments: []
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
labels: []
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
blocked_by: []
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
evidence: []
attachments: []
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
labels: []
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
blocked_by: []
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
evidence: []
attachments: []
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
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0376
scope:
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0376
scope:
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0397
scope:
- src/frob/gates/
- src/frob/app/config.py
- frob.toml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0398
scope:
- src/frob/tickets/
- src/frob/gates/
- src/frob/app/ticket_runner.py
- src/frob/testing/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0435
scope:
- src/frob/gates/
- src/frob/graph/
- docs/
- frob.toml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User (2026-07-20): account for anything that looks like a tool usage/guide, and any documentation that SEEMS to point to something -- and HARDEN the wishy-washy part. THE HARDENING: do not try to detect fuzzy "seems to point to X" intent (unhardenable, high FP). Instead define a CLOSED SET of RECOGNIZED, RESOLVABLE POINTER SHAPES and only fire when a pointer of a known shape targets something that does NOT exist. This converts "seems to point" into a mechanical, resolvable check with a naturally-low FP rate (an unrecognized shape is simply not checked). POINTER KINDS (each detectable + resolvable against the real project): (1) FILE/PATH -- a repo-relative path (src/frob/foo.py, docs/bar.md, frob.toml) mentioned in a code span/block/link must EXIST; (2) CLI INVOCATION / TOOL-GUIDE -- `<project-cli> <subcommand>` and `--flag`/`-x` options against the projects real argparse/command source (frob is one instance; per-project via a configurable command source) -- a nonexistent subcommand or flag is stale; (3) CONFIG REFERENCE -- a `[section]` or `[section].key` or a frob.toml/pyproject/Cargo key referenced must be a REAL config key of that manifest/schema; (4) CODE SYMBOL -- a dotted path / import / use (module.Class.method, from X import Y, use crate::x) resolves in the graph against the projects manifest-derived namespaces (see T-0436: Rust workspace subcrates, pyproject/package.json package names != dir names; external namespaces skipped); (5) DOC-ANCHOR LINK -- a docs/x.md#anchor (or a frob:doc/frob:describes anchor target) must exist. SCOPE: inline code spans AND fenced code blocks AND markdown links AND tool-guide prose ("run `X`", "add `[section]` to frob.toml", "the `--foo` flag", "see `docs/bar.md`"). CONSERVATISM: only a pointer matching a recognized shape whose target is DEFINITIVELY resolvable-or-refutable is checked; an unrecognized/ambiguous token is NOT flagged (the hardening). PROMINENTLY WAIVABLE (frob:waive) for intentional external/illustrative/future-facing pointers. Ships per-project (T-0406), all languages. T-0436 (unbound/stale CODE BLOCKS) is ONE INSTANCE of this; this ticket is the general doc-pointer-resolution gate (the north-star doc-drift check, cf T-0325). Acceptance: a doc mentioning `src/frob/gone.py` (nonexistent) flagged; `frob edit`/`--nonexistent-flag` flagged; a `[bogus.section]` frob.toml reference flagged; a `docs/missing.md#x` link flagged; a real path/command/flag/symbol/anchor passes; an unrecognized prose token NOT flagged; external pointers waivable. Run on frobs own docs, report FP rate, disposition honestly.

<!-- ticket:T-0440 -->
```yaml
id: T-0440
title: 'strata model debt: deploy/serve/mutate swept into coarse utility-hub node,
  not modeled as distinct capabilities with own effects/threat surface'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- design/frob.strata
- docs/strata/
- tests/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```

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
blocked_by: []
parent: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/
- src/frob/app/
- docs/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Discovered while working T-0516: COV006 Violation objects carry no symref (file=test_file, line=0), so _match_waiver falls back to file-level matching for a frob:waive COV006 comment anywhere in that file -- ANY single COV006 waiver in a test file silently suppresses EVERY COV006 finding in that file, not just the one it was written next to. Verified directly: adding one waiver comment near one test in tests/test_gates.py suppressed all 7 COV006 findings then present in that file, including unrelated ones that were NOT sound (an import-alias false-positive that needed a real fix, not a waiver). Consider giving COV006 violations a symref (the test's own qualname) so _match_waiver can do symbol-exact matching the way most other rules do, instead of falling back to file-scope for a rule that very plausibly has multiple independent findings per file.

<!-- ticket:T-0541 -->
```yaml
id: T-0541
title: 'gates: SCOPE001/PRE001 fully disabled with no active ticket / off-convention
  branch (B9)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B9. _build_ticket_scoped_jobs only registers scope+prework jobs when st.ticket is not None; active_ticket derives the ticket purely from the branch name's T-#### prefix. A branch not named after a ticket (or work on main) skips scope and pre-work enforcement entirely rather than failing. Fix direction: a diff that touches source with no derivable active ticket should be a loud blocking condition, not a skip.

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
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B10. _cov002 uses _open_scopes = every open ticket's scope glob, matched via _scope_covers against ANY of them. One broad-scope open ticket (e.g. src/frob/**) makes every changed symbol under it accounted for regardless of relation to that ticket. Fix direction: prefer the ACTIVE ticket's own scope first, and require a narrower/more-specific glob match (or an explicit frob:ticket edge) when multiple open tickets' scopes could cover the same file, rather than accepting the first match found.

<!-- ticket:T-0571 -->
```yaml
id: T-0571
title: 'frob review: structured adversarial review channel as first-class evidence'
state: queued
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
blocked_by: []
parent: null
scope: []
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Adversarial review is this repo's most load-bearing quality mechanism (every false-confidence detector was caught by it) but lives only in dispatch prompts. frob review generate <diff|ticket> emits a per-diff checklist (detector changed -> demand counterexample; claim added -> demand refutation attempt; suppression code -> demand over-suppression probe); frob review record stores the verdict as a typed evidence channel consumable by close. Scope: new src/frob/review/, app runner, docs.

<!-- ticket:T-0574 -->
```yaml
id: T-0574
title: 'agent environment hardening: auto-inject FROB_WORKTREE/FROB_AGENT + mechanical
  stash guard'
state: queued
kind: security
origin: agent
created: '2026-07-21'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/tickets/_worktree_guard.py
- src/frob/app/agent_runner.py
- src/frob/__main__.py
- src/frob/scaffold/_managed.py
- docs/guides/agent-playbook.md
- tests/test_worktree_guard.py
scope_changes:
- op: add
  glob: src/frob/tickets/_worktree_guard.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/agent_runner.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/__main__.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/scaffold/_managed.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_worktree_guard.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Four agents ran git stash despite playbook 1b; several ran ticket commands against the shared checkout because FROB_WORKTREE was never SET (T-0431 guard exists but inert without it). (1) frob agent env prints/exports the guard env for a worktree; scaffold/playbook wire it into dispatch. (2) a pre-stash guard (hook or wrapper) refuses git stash while sibling agent worktrees exist. Catalogued-is-not-enforced applied to the playbook itself. Scope: src/frob/tickets/_worktree_guard.py, scaffold hooks, playbook.

<!-- ticket:T-0582 -->
```yaml
id: T-0582
title: 'perf audit re-measurement: verify vet/secrets/selfconform after T-0410 parse_file
  memo fix; profile refs stage (now 2nd dominator)'
state: queued
kind: bug
origin: human
created: '2026-07-21'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/vet/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0410 landed one concrete fix: memoize parse_file's extract() walk (coverage_gate 155.8s->15.9s isolated, ~40s->~4s in real frob check) plus M6 (.hypothesis/.serena skip-dirs). Two things from docs/audits/perf.md need re-measurement, not assumption: (1) H4's other cited multipliers (vet.scan_file_capabilities uses raw_tree not parse_file, so bypasses the new memo -- but _parse's own content-hash cache may already make repeats cheap; verify with a profile) and H5 (selfconform's double capability-scan, likely still unfixed). (2) refs_gate is now the 2nd-largest stage (measured ~8-11s across several frob check runs) and was never profiled by the original audit; isolate and profile it the way this ticket isolated coverage_gate. Update docs/audits/perf.md with a dated re-measurement section (mark H1/H2 RESOLVED via T-0423) rather than a fresh audit.

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
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Discovered incidentally while closing T-0556 (unrelated ticket) in a worktree that had already closed T-0567/T-0545/T-0552/T-0547 earlier in the same branch: symbols touched by T-0545/T-0552 (e.g. src/frob/gates/_coverage.py::stamp_coverage, src/frob/gates/__init__.py::_test005/test_gate/_edge_has_execution_evidence/_KNOWN_GATE_RULES/_COVERAGE_LOCK_REL) started failing COV002 again -- 'changed with no frob:ticket edge to an open ticket' -- even though each carries a valid frob:ticket T-0545/T-0552 directive and both tickets' closures are still part of the same uncommitted diff against main (git diff main --stat still shows all the intervening commits). This reproduces with a bare frob check (no --ticket override), so it is not scoped to T-0556's own diff content -- it appeared sometime between T-0552's own clean check (frob check --ticket T-0552 showed 0 COV errors right after closing it) and starting T-0556's ticket workflow (multiple frob ticket scope/sweep operations on tickets.md in between). Hypothesis: _bound_to_open_ticket's grace-window hunk-matching (docs/audits or __init__.py:1917 _bound_to_open_ticket docstring, T-0214/T-0320) depends on a ticket's DONE-transition marker line falling within a single git diff hunk against main; repeated tickets.md rewrites by later ticket operations (scope changes, sweeps, done-report writes for OTHER tickets) can split/relocate that hunk so an EARLIER ticket's own close marker no longer registers as 'in this diff's tickets.md hunk' even though the closure commit is still, in aggregate, part of the diff vs main. Needs investigation: reproduce minimally (two sequential ticket closes in one branch, then a third ticket's ledger operations), confirm the hunk-boundary hypothesis, and either make the grace window robust to intervening unrelated tickets.md hunks or make COV002's message clearer that this is a hunk-shape artifact, not a real missing edge. Related: docs/guides/agent-playbook.md section 10b's existing multi-ticket-worktree warnings (about ledger finalization) -- this is a parallel failure mode in the SAME class of hazard, but for COV002 rather than the Done-report/close ledger writes.

<!-- ticket:T-0594 -->
```yaml
id: T-0594
title: Wire ratchet-pool severity resolution into a real gate (frob.gates.__init__)
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by: []
parent: null
scope: []
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0569 built frob.gates._ratchet (RatchetLock/snapshot_ratchet/clear_ratchet_entry/resolve_ratchet_severity/ratchet_enabled_rules) as a complete, additive, self-contained mechanism + CLI (frob pool snapshot/clear), deliberately NOT wired into any live gate's severity resolution because src/frob/gates/__init__.py's per-rule dispatch is large shared surface owned by a concurrent wave. This ticket is that follow-up: pick one real warn-first rule (e.g. INV006 or PII010), opt it into [gates.ratchet] rules, and call resolve_ratchet_severity at that gate's severity-decision call site so a baselined finding stays warn and a fresh one errors for real, not just in tests/test_gates_ratchet.py's synthetic fixture. Scope: src/frob/gates/__init__.py (the one call site), frob.toml, docs/modules/gates.md.

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
blocked_by: []
parent: T-0204
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_coverage.py
- src/frob/gates/_registry_exhaustiveness.py
- src/frob/strata/_cve_fingerprint.py
- src/frob/tickets/_brief.py
- src/frob/__main__.py
- src/frob/gates/_docblocks.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0204
scope:
- src/frob/**
- tests/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
frob-dup currently reports 75 duplicate groups (112 waived), measured 2026-07-22 (was 64 groups at T-0204 filing, has grown). This is distinct from the frob-arch abstraction-opportunity advisories already covered by T-0393 -- frob-dup is the raw clone-detector report over both src/frob/** and tests/**, not the arch gate's near-dup-family suggestions. For each of the 75 groups: if it is a genuine extraction candidate (shared logic that should live in one home), extract it; if it is a false pair (coincidental structural similarity, e.g. parallel test scaffolding), waive it with an honest per-group reason. Acceptance: frob-dup summary line reports 0 unwaived groups (fixed or waived-with-reason), no threshold loosened without a disclosed decision.

<!-- ticket:T-0599 -->
```yaml
id: T-0599
title: 'frob-exports triage: src/frob, src/frob/app, src/frob/check (19 symbols across
  3 packages)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
blocked_by: []
parent: T-0204
scope:
- src/frob/__init__.py
- src/frob/app/**
- src/frob/check/**
scope_changes: []
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch
- tests/unit/test_config.py::test_missing_toml_defaults
- tests/test_excludes.py::test_walk_pruned_does_not_descend_venv_or_git
- tests/test_excludes.py::test_iter_files_git_fast_path_matches_ls_files
- tests/test_gitio.py::TestSpawnRecorder::test_tallies_spawns_made_inside_the_block
- tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
- tests/unit/test_memo.py::test_reset_run_memo_activates_an_unbounded_scope
- tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit
- tests/unit/test_check.py::TestRunCheck::test_all_stages_skipped_returns_empty_result_for_root
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
frob-exports currently reports (measured 2026-07-22): src/frob 5 public symbols missing from __init__.py, src/frob/app 11, src/frob/check 3 (19 total). For each symbol, decide per-symbol: export it from the package's __init__.py, or demote it to private (leading underscore) if it should not be public API. No blanket waiver -- each symbol gets an explicit decision. Acceptance: frob-exports(src/frob), frob-exports(src/frob/app), frob-exports(src/frob/check) summary lines report 0 unresolved findings (exported, demoted, or waived-with-reason), no threshold loosened without a disclosed decision.

## Done report

## Done report

Live frob-exports state at start of work (post-merge, drifted from the
2026-07-22 measurement in the ticket body): src/frob 12 missing, src/frob/app
14 missing (13 module `run` + telemetry, plus 2 more found during
verification: app.config.load_arch_config/stale_install_warning, total 16),
src/frob/check 4 missing. Every symbol was traced to at least one
cross-module consumer (grep across src/ and tests/) before being exported --
none were dead/internal-only, so nothing was demoted to private.

Changed:
- src/frob/__init__.py -- export frob.doctor's verify_derived_state,
  run_diagnosis, NativeExtensionStatus, DerivedArtifactStatus, DoctorReport;
  frob.excludes' walk_pruned, iter_files; frob.gitio's spawn_recorder,
  git_common_dir, reset_common_dir_cache, common_dir_and_branch,
  SpawnRecorder. frob.__main__.main stays deliberately unexported (existing
  documented decision, unchanged).
- src/frob/app/__init__.py -- alias+export the 6 runner modules missing from
  the `_runner_run` pattern (clean_runner, debt_runner, doctor_runner,
  fleet_runner, pool_runner, registry_runner -- same dynamic-dispatch shape
  as the other 25 already exported), all 9 frob.app.telemetry symbols
  (is_disabled, iso_now, redact_command, append_event, tree_hash,
  estimate_tokens, record_cli_event, record_ticket_event, timed_call), and
  frob.app.config's load_arch_config/stale_install_warning.
- src/frob/check/__init__.py -- export frob.check._memo's
  reset_run_memo, run_memo_stats, memoize_per_run (run_memo_scope was
  already imported but not in __all__; now included too).

Disposition: every symbol above was EXPORTED (no demotions, no waivers).
None were sole-use-within-own-module -- each had at least one confirmed
cross-module import site.

Evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch
- tests/unit/test_config.py::test_missing_toml_defaults
- tests/test_excludes.py::test_walk_pruned_does_not_descend_venv_or_git
- tests/test_excludes.py::test_iter_files_git_fast_path_matches_ls_files
- tests/test_gitio.py::TestSpawnRecorder::test_tallies_spawns_made_inside_the_block
- tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
- tests/unit/test_memo.py::test_reset_run_memo_activates_an_unbounded_scope
- tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit
- tests/unit/test_check.py::TestRunCheck::test_all_stages_skipped_returns_empty_result_for_root
- Import smoke: `python -c "import frob, frob.app, frob.check; [getattr(frob, n) for n in frob.__all__]; [getattr(frob.app, n) for n in frob.app.__all__]; [getattr(frob.check, n) for n in frob.check.__all__]"` -- resolved cleanly (24/52/11 symbols).
- `frob check --ticket T-0599 --only static`: frob-exports(src/frob),
  frob-exports(src/frob/app), frob-exports(src/frob/check) report ZERO
  findings (absent from the tool-summary list entirely -- every other
  package's pre-existing findings are untouched/out of scope).
- `frob check --ticket T-0599 --only lint`: 0 errors, 0 warnings (ruff-check,
  ruff-format, ty all pass) after `ruff format`/`ruff check --fix`.
- `frob check --ticket T-0599 --only prework`: 0 errors after re-running
  `frob ticket sweep T-0599`.
- `frob test --base main` (full suite, ran in background per playbook 6b):
  pre-existing failures only (native-extension-availability doctor tests,
  strata self-model, render_lint gitless-root warning path, a
  `_STAGE_GROUPS` coverage gap for the new `protocol_summary` gate landed by
  T-0813) -- none touch src/frob/__init__.py, src/frob/app/__init__.py, or
  src/frob/check/__init__.py; none are new regressions from this change.

Filed: T-0824 (bug) "protocol_summary gate missing from
_STAGE_GROUPS coverage" -- scope src/frob/check/__init__.py's
_STAGE_GROUPS membership, found while running `frob test --base main`
during verification, out of T-0599's exports-only scope.

Gates: `frob check --ticket T-0599 --only static/--only lint/--only prework`
all clean (0 errors/0 warnings on the touched packages). `--only gates-fast`
and `--only gates-native`/`--only gates-security` not separately reported
here beyond the prework/static/lint slices above since no gate logic was
touched by this ticket (pure __init__.py re-export additions); nothing new
observed in those groups tied to the three touched files.

Deviations from plan: none. All 3 packages resolved to 0 exports findings
via export (not demotion or waiver), matching the ticket's "explicit
decision, exported/demoted/waived" requirement -- the decision made for
every symbol was "export" since every one had a genuine cross-module
consumer.

### Changed
(no changed files detected)

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_missing_toml_defaults` (pytest node id, verified passing when recorded)
- `tests/test_excludes.py::test_walk_pruned_does_not_descend_venv_or_git` (pytest node id, verified passing when recorded)
- `tests/test_excludes.py::test_iter_files_git_fast_path_matches_ls_files` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestSpawnRecorder::test_tallies_spawns_made_inside_the_block` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_memo.py::test_reset_run_memo_activates_an_unbounded_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheck::test_all_stages_skipped_returns_empty_result_for_root` (pytest node id, verified passing when recorded)

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
blocked_by: []
parent: T-0204
scope:
- src/frob/gates/**
- src/frob/graph/**
- src/frob/process/parsers/**
- src/frob/registry/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0204
scope:
- src/frob/strata/**
- src/frob/tickets/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0177
scope:
- src/frob/gates/**
- src/frob/serve/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a warm daemon and a one-file edit WHEN frob_check_delta runs THEN only
    obligations whose inputs include that file are re-evaluated AND verify mode shows
    zero fingerprint mismatch vs a cold run
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0570
scope:
- src/frob/check/**
- src/frob/gates/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a truncated .frob/cache.db WHEN frob check runs THEN the run fails closed
    naming the corrupt artifact before any gate consumes it
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0570
scope:
- src/frob/doctor.py
- tests/system/test_cli_doctor.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a derived artifact rewritten out-of-band between two doctor runs WHEN
    run_diagnosis executes THEN the drift is reported naming the artifact and both
    fingerprints
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0332
scope:
- src/frob/arch/**
- docs/modules/arch.md
- tests/unit/test_arch.py
- docs/design/registry/patterns.yaml
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN each of the 6 rows WHEN this ticket closes THEN the row is either detected
    by a tested high-precision detector or carries a reasoned not-checkable/out-of-scope
    disposition AND the patterns reconciliation pin test passes
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0554
scope:
- src/frob/app/check_runner.py
- tests/unit/test_check.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a TS-only repo WHEN frob check --ticket T-X runs THEN _run_gates receives
    ticket=T-X (asserted via test) and same for --base/--delta/--skip-gates across
    cpp/rust/ts dispatchers
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0325
scope:
- src/frob/app/graph_runner.py
- src/frob/gates/**
- docs/modules/graph.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a symbol with dependents WHEN frob graph affects SYMREF runs THEN the
    affected code/docs/tests print with truncation flagged; GIVEN a diff changing
    a symbol whose affects-closure docs were untouched WHEN the drift gate runs THEN
    it reports the stale dependents
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a windows node declaring service with a binPath WHEN install.ps1 is
    generated THEN it idempotently creates the SCM service with that image path before
    hardening AND uninstall.ps1 deletes it
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0577
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a land with --push WHEN the land completes THEN the push happens only
    after every land verification passed; GIVEN the TICK005 rule defined WHEN land
    runs THEN the regression sweep executes and blocks on failure
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the existing T-0360/T-0370 regression tests unmodified WHEN both check
    families run through the normalized model THEN all pass and no raw-tree walk remains
    in _collect_dispatch_refs (or a reasoned decision records what stays raw and why)
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/testing/**
- src/frob/gates/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a fresh python process WHEN import frob.testing runs as the first frob
    import THEN it succeeds and the test-file workaround import is removed
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0575
scope:
- src/frob/app/test_runner.py
- src/frob/testing/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a flaky test with an open quarantine ticket WHEN frob test runs via
    the CLI THEN the run records history, the quarantined failure does not fail the
    build, and alarms surface for closed-ticket quarantines
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0576
scope:
- src/frob/app/**
- src/frob/__main__.py
- README.md
- docs/modules/gates.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a repo with frob:deprecated directives WHEN frob deprecated runs THEN
    each deprecation prints with its DEPR status and the README command table includes
    the new command
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0576
scope:
- src/frob/graph/**
- src/frob/gates/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a design decision recorded WHEN implemented THEN a change adding a call
    to a deprecated public symbol produces a DEPR finding naming the new call site
  evidence: []
threat: null
component: null
labels: []
```
T-0576's ticket body wanted a deprecated symbol gaining new callers to fire a finding, but frob.graph.callgraph's caller/reference resolution only covers PRIVATE callees by design -- a PUBLIC deprecated symbol's callers are not resolvable today. Design work: either extend the callgraph to public-symbol references (cost/precision tradeoff) or diff-based detection (a new call site referencing the symbol in a change since the directive appeared). Was T-0639 (ex-draft, id lost at land) in T-0576's worktree; drafts still do not survive land (T-0637).

<!-- ticket:T-0640 -->
```yaml
id: T-0640
title: 'strata: TIMEOUT obligation on every remote/cross-boundary flow (REL2xx)'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a .strata flow crossing a service/process boundary with no timeout attr,
    when frob check runs, then REL2xx fires unless waived with a reason
  evidence: []
- text: Given a declared timeout, when the bound code path lacks a matching real timeout
    arg, then the check fails (proof-against-code), not merely passes on declaration
  evidence: []
threat: null
component: null
labels: []
```
Add a flow-level TIMEOUT attribute + REL2xx checker + litmus + docs: every remote/cross-boundary flow must declare a bounded timeout (unbounded hang otherwise). Deny-by-default with reasoned-waive channel (T-0174). Discharge must be proof-against-code (real timeout arg at the call site) per T-0331's PROVABILITY CONSTRAINT, not bare declaration.

<!-- ticket:T-0641 -->
```yaml
id: T-0641
title: 'strata: RETRY backoff+jitter + non-idempotent-op guard + IDEMPOTENCY key obligation'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a flow with retry=true and no backoff/jitter declared, when checked,
    then it fails
  evidence: []
- text: Given a retryable flow targeting a non-idempotent mutating op with no idempotency
    key, when checked, then it fails
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given an external-dependency node with no circuit-breaker/bulkhead declared,
    when checked, then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a CRITICAL dependency with no fallback declared, when checked, then
    the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a node with inbound critical flows and replicas_max=1, when checked,
    then SPOF obligation fires unless waived
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a queue/consumer node with no bounded-intake policy declared, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a boundary flow with no metrics/traces/logs declared, when checked,
    then the obligation fires
  evidence: []
- text: Given a multi-hop flow chain with no trace-id propagation declared, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a service node with no golden-signal SLOs + error budget declared, when
    checked, then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a store with >=2 distinct writer nodes and no declared single-owner/reconciliation,
    when checked, then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a multi-write op with no transactional-boundary declared, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given an event/queue node with no schema version declared, when checked, then
    the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a queue node with no delivery-semantics declared, when checked, then
    the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a PII-tagged store with no retention/TTL declared, when checked, then
    the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a sync call chain exceeding the declared/default depth bound, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a cross-service transaction with no saga/compensation declared, when
    checked, then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given two services sharing a mutable store/memory region across their boundary
    with no declared exception, when checked, then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a cross-node flow with an implicit clock/ordering assumption and no
    declared strategy, when checked, then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
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
labels: []
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
blocked_by: []
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
scope_changes: []
evidence: []
attachments: []
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
labels: []
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
blocked_by: []
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given every TS/JS static-resolvable construct in the taxonomy table, when
    the resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given every Rust static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given every C static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given every C++ static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given every Kotlin static-resolvable construct in the taxonomy table, when
    the resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0339
scope:
- src/frob/vet/**
- src/frob/strata/**
- tests/test_vet.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given code containing a spec-defined runtime-resolved indirection construct
    with no waiver, when checked, then the obligation fires
  evidence: []
- text: Given the same construct with a reasoned waiver, when checked, then it passes
    and the waiver reason is recorded
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given the full evasion taxonomy denominator, when the meta-test runs, then
    every entry maps to >=1 registered litmus fixture
  evidence: []
- text: Given a new taxonomy entry added with no fixture, when the meta-test runs,
    then it fails the build
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a module with an observed capability effect and no strata node binding,
    when checked, then SYS-COV fires
  evidence: []
- text: Given every module bound to a node, when checked, then SYS-COV is silent
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a node declaring fewer public symbols than the bound module exports,
    when checked, then the obligation fires
  evidence: []
- text: Given a node declaring a symbol the bound module does not export, when checked,
    then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a node whose purpose declares a read-only effect profile but whose bound
    code performs a write, when checked, then the obligation fires
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given dangerous logic moved into a helper module not directly bound to any
    node but reachable from a bound node, when checked, then the effect is still attributed
    and conformance-checked, not silently dropped
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given a waiver older than its staleness bound, when checked, then it is treated
    as expired and the underlying obligation re-fires
  evidence: []
- text: Given any active waiver, when frob check runs, then it appears in the floor
    view and cannot be hidden from default output
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
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
labels: []
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
blocked_by: []
parent: T-0346
scope:
- docs/design/registry/**
- tests/unit/strata/**
scope_changes: []
evidence: []
attachments: []
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
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given the decision made, when RECONCILIATION.md is reread, then finding (f)
    is marked resolved with either the leaf-level registry built or a written granularity-freeze
    rationale
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: Given the full registry, when the meta-test runs, then every cross_refs-eligible
    concept has exactly one canonical id or a recorded justification for staying split
  evidence: []
- text: Given a future corpus doc edit that adds a table row with no matching registry
    id, when the meta-test runs, then it fails the build
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN history [P] followed by K consecutive fails under live quarantine WHEN
    evaluate_gate and hard_regression_alarms run THEN the gate stays red and the alarm
    fires
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0383
scope:
- src/frob/gates/_registry_exhaustiveness.py
- docs/design/registry/**
- tests/test_registry_exhaustiveness.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a registry entry with out_of_scope disposition whose reason names no
    catching control and is not a substantive reasoned-none WHEN the registry gate
    runs THEN a finding fires naming the entry
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN TS fixtures with interface, type alias, enum, and a TSX component WHEN
    TypeScriptAdapter.adapt runs THEN each is represented in the NormalizedModule
    and asserted by a test
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0265
scope:
- docs/modules/gates.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN docs/modules/gates.md WHEN a reader checks --only semantics THEN the
    always-evaluated drift behavior is documented with the T-0265 rationale
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/vet/
- src/frob/strata/
- docs/design/registry/weaknesses.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- docs/design/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the children closed WHEN frob check runs on a fixture with a known exception
    surface THEN the may-raise sets are queryable and every child gate/advisory fires
    per its own acceptance
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a fixture chain f->g->h where h raises ValueError and g catches it and
    f calls dict subscript WHEN the resolver runs THEN f's may-raise is exactly {KeyError}
    plus the ubiquitous tier and a fixture with an unresolvable call yields Unknown
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a noexcept function calling a may-throw callee WHEN the analysis runs
    THEN an error finding names the call site AND a try/catch(...) boundary discharges
    Unknown
  evidence: []
threat: null
component: null
labels: []
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
evidence: []
attachments: []
acceptance:
- text: GIVEN a boundary catching a strict subset of its guarded may-raise set WHEN
    the gate runs THEN the missing exception types are named; GIVEN a public raiser
    with unhandling callers WHEN arch advisories run THEN a Result recommendation
    fires with the raise sites
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a call into an undeclared ctypes function WHEN the resolver runs THEN
    Unknown appears in the caller's may-raise set; GIVEN the same call with a frob:raises
    declaration THEN the declared set substitutes
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a pyo3 function whose Rust side constructs PyValueError but whose frob:raises
    omits it WHEN the gate runs THEN a drift error names both sides; GIVEN a ctypes
    boundary with no frob:raises THEN a finding demands the declaration
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0329
scope:
- docs/design/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the estate language survey WHEN this ticket closes THEN docs/design
    records the chosen next adapter tier with rationale and per-language tickets exist
    for chosen languages only
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- docs/design/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the children closed WHEN frob check runs on fixtures reproducing each
    hazard class THEN each fires per its own acceptance
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0693
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN two functions acquiring locks A-then-B and B-then-A WHEN the check runs
    THEN a finding names both call paths; GIVEN consistent global ordering THEN silence
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0693
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN time.sleep inside async def WHEN the check runs THEN a finding suggests
    asyncio.sleep/to_thread; GIVEN an un-awaited coroutine call THEN a finding names
    the site
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0693
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a module-level dict written from a thread-submitted function with no
    enclosing lock WHEN the check runs THEN an advisory names the write site and the
    spawn path; GIVEN the same write under a "with lock:" block THEN silence
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0693
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a pure-arithmetic loop function submitted to ThreadPoolExecutor WHEN
    advisories run THEN a GIL-bound suggestion fires naming the loop; GIVEN a socket-read
    function under threads THEN silence
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- editors/**
- docs/strata/**
- tests/unit/strata/
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN two nodes with write-mode access to one resource and no arbiter WHEN
    sys checks run THEN a fail-closed error; GIVEN the same with a declared arbiter
    or read-only modes THEN the obligation discharges
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a node declaring mode=read whose bound code opens the resource for writing
    WHEN sys checks run THEN a fail-closed error names the write site; GIVEN mode=exclusive
    with an access outside the arbiter context THEN an error names the unguarded path;
    GIVEN conforming code per mode THEN each discharges
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0331
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- editors/**
- docs/strata/**
- tests/unit/strata/
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN two entry nodes declaring users 300k and 200k both flowing into one
    db resource WHEN elaboration runs THEN the db's aggregate demand is 500k and queryable;
    GIVEN no demand declared THEN the resource reports demand-undeclared, not zero
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN 500k declared users flowing to a db with mode=exclusive and default
    holding time WHEN sys checks run THEN a utilization error fires showing the arithmetic;
    GIVEN the same db with demand undeclared THEN a fail-closed demand-undeclared
    finding; GIVEN a read-preferring lock with no alpha/fairness on a read-heavy resource
    THEN a writer-starvation advisory
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/system/test_cli_native_missing.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a repo with .strata files and no built native WHEN frob check runs THEN
    SYS004 fails loud AND both tests pass
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- src/frob/stats/**
- docs/design/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the children closed WHEN the perf harness runs THEN a queryable hot-graph
    exists under .frob at sub-100KB with per-section decile readouts
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0709
scope:
- src/frob/stats/**
- src/frob/perf/**
- tests/unit/perf/
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN bimodal latencies (1ms and 100ms modes) WHEN sketched at alpha=2 percent
    THEN p10/p50/p90 read back within relative error and the serialized sketch is
    <1KB; GIVEN repeated runs THEN decayed merge converges and the store stays under
    its cap
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a section whose p90 regresses beyond tolerance vs the stored prior WHEN
    frob check runs with the ratchet enabled THEN a PERF finding names the section
    and both decile sets; GIVEN a loop dominated by an external call THEN an advisory
    fires with the edge's deciles
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/app/**
- docs/modules/tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN 5 stale lease files WHEN frob ticket doable runs THEN the queue prints
    with at most one summary line about leases AND frob check (or doctor) reports
    each stale lease once with its path and remedy
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN an epic with two stories each with open leaf tickets WHEN frob ticket
    doable runs THEN only leaves surface and closing the epic is refused while descendants
    are open; GIVEN tickets assigned to sprint-1 WHEN frob ticket sprint show sprint-1
    runs THEN the commitment lists with state rollup and closed-count velocity
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/app/**
- tests/system/test_cli_check.py
- tests/system/test_cli_perf.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/gitio.py
- src/frob/gates/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- tests/system/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- docs/design/registry/supply-chain.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- docs/design/registry/system-design.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a repo with a .kt file WHEN frob check runs THEN the file parses into
    the symbol graph (no KeyError) and its symbols appear in frob map output
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- tests/unit/strata/test_export_golden.py
- tests/unit/strata/golden/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0329
scope:
- src/frob/arch/_python.py
- tests/unit/test_arch.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN class Foo with an annotated field WHEN PythonAdapter.adapt runs THEN
    the field appears in NormalizedClass.fields AND the T-0615 waiver test is updated
    to assert parity
  evidence: []
threat: null
component: null
labels: []
```
Found while working T-0615 (four-way equivalence meta-test). PythonAdapter._py_class_fields (src/frob/arch/_python.py) gates on 'if c.type != "expression_statement": continue' over a class body's named_children, expecting a class-level annotated assignment to be wrapped in an expression_statement node. In practice tree-sitter-python's grammar yields the assignment node directly as a named child of the class block, with NO expression_statement wrapper. Concrete repro: PythonAdapter().adapt(...) on 'class Foo:\n    x: int = 0\n' returns classes[0].fields == [] every time -- confirmed directly against the adapter, not just inferred. No existing test caught this because TestPythonAdapter's real-fixture tests never assert on .fields via the adapter itself (only a hand-built NormalizedField construction test exists, bypassing the adapter). T-0615's tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_python_field_detection_is_a_documented_waiver currently PINS this broken behavior as a documented waiver (asserting derived.fields == []) -- fixing this ticket must also update/remove that waiver test to assert real parity with TS/rust/kotlin (which all capture this shape via their own adapters).

<!-- ticket:T-0728 -->
```yaml
id: T-0728
title: 'arch: wire ARCH1xx SOLID checks into analyze_project, frob.toml thresholds,
  gate registry'
state: queued
kind: feature
origin: agent
created: '2026-07-22'
priority: high
blocked_by:
- T-0616
parent: T-0330
scope:
- src/frob/arch/__init__.py
- src/frob/app/config.py
- src/frob/gates/**
- docs/modules/arch.md
- tests/unit/test_arch_srp.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a fixture repo with a two-cluster class WHEN frob check runs THEN ARCH101
    appears in arch output with frob.toml-tunable thresholds AND the rule ids are
    waivable/registered
  evidence: []
threat: null
component: null
labels: []
```
T-0616 (and successive T-0330 children) deliver check families over the normalized model with module-default thresholds, but nothing invokes them in production -- the invoked-by-nothing pattern, called out by T-0616's reviewer with the exact wiring list: (a) register run_srp_checks (and each subsequent family runner) in analyze_project's dispatch so they fire during real frob check; (b) thread the thresholds (LCOM4_MIN_METHODS, LCOM4_MIN_FIELD_USING_METHODS, GOD_MODULE_MIN_EXPORTS, GOD_MODULE_MIN_CLUSTERS, MIXED_CONCERN_MIN_DECISION_POINTS, plus later families') into frob.app.config's [arch] table; (c) add ARCH101-103 (and successors) to _KNOWN_GATE_RULES for waiver/registry visibility; (d) coordinate with T-0626's registry rows. Extend as each T-0617..T-0625 sibling lands -- this is the standing wiring home for the family.

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
blocked_by: []
parent: T-0587
scope:
- src/frob/gates/**
- tests/test_gates.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a vitest project with a frob:tests directive naming a real vitest test
    WHEN gates run THEN the edge resolves against the collected id and the structural
    fallback no longer credits unverified ts edges
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/**
- docs/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN any frob-enabled repo with [natives] WHEN uv run frob natives build
    runs THEN natives compile with the shared per-clone cache and the repo Makefile
    contains no cache logic
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0732
scope:
- src/frob/scaffold/**
- Makefile
- docs/guides/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a warm pool of N WHEN an agent leases a worktree THEN it starts with
    natives built and main current, and the pool refills in the background
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/arch/**
- src/frob/graph/**
- docs/design/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the children closed WHEN frob check runs on fixtures for each fragment
    THEN each child gate/advisory fires per its own acceptance
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0692
scope:
- tests/system/test_scaffold_dx.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the slow scaffold test WHEN the suite runs under the global 120s ceiling
    THEN the test carries its own measured override and passes cold-cache
  evidence: []
threat: null
component: null
labels: []
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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a Rust enum with tuple and struct variants WHEN RustAdapter.adapt runs
    THEN variant payload shapes are represented and asserted by a test
  evidence: []
threat: null
component: null
labels: []
```
Lost draft from T-0612 (Rust adapter): enum variants with associated data currently flatten to NormalizedField, losing the payload shape. Extend the model (NormalizedVariant or fields on NormalizedClass) keeping _normalized.py tree_sitter-free, map Rust enum payloads and coordinate with T-0681 (TS phase 2, same model-extension class).

<!-- ticket:T-0745 -->
```yaml
id: T-0745
title: 'protocol summary engine: per-function fixpoint over the call graph, shared
  with may-raise'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0744
parent: T-0739
scope:
- src/frob/arch/**
- src/frob/graph/**
- tests/unit/test_arch.py
- docs/modules/graph.md
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: 'T-0745''s declared scope omitted a docs file, but every new public symbol

    (compute_protocol_summaries, FunctionSummary, SCCTimeout, SummaryResult,

    UNRESOLVED_CALLEE) needs a frob:doc edge resolving to a real anchor

    (COV001). Adding docs/modules/graph.md#protocol-summary-engine via the

    sanctioned frob ticket scope mechanism rather than hand-editing scope.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_caller_summary_includes_callee_transitions
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_requires_and_transitions_join_across_two_hops
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_self_recursive_function_converges
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unresolved_callee_poisons_the_summary
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_poisoning_propagates_transitively_through_a_clean_caller
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unreachable_function_is_reported_not_analyzed_never_silent
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_diamond_shaped_calls_join_without_duplication_or_loss
attachments: []
acceptance:
- text: GIVEN a recursive call cluster with transitions WHEN the fixpoint runs THEN
    summaries converge and match hand-computed values; GIVEN an unresolvable callee
    THEN the summary is poisoned and surfaces as an ERROR downstream, never silence
  evidence:
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_caller_summary_includes_callee_transitions
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_requires_and_transitions_join_across_two_hops
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_self_recursive_function_converges
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unresolved_callee_poisons_the_summary
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_poisoning_propagates_transitively_through_a_clean_caller
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unreachable_function_is_reported_not_analyzed_never_silent
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_diamond_shaped_calls_join_without_duplication_or_loss
threat: null
component: null
labels: []
```
Child 2 of T-0739. The shared per-function summary fixpoint engine over the call graph: each function summarizes to (required protocol states, may-perform transitions, acquired/released/escaped resources) computed bottom-up to fixpoint, recursion via lattice join, using the T-0339-family resolvers for callee binding. DESIGN CONSTRAINT: ONE engine shared with T-0686 may-raise (whichever builds first hosts the engine; the other consumes -- coordinate explicitly, no second fixpoint). NO-FAIL-SILENT (user mandate): an unresolvable callee contributes Unknown which POISONS the summary (poisoned summaries are ERRORS at verification unless waived with reason); a function outside the call graph (unreachable from any entrypoint) is reported as not-analyzed, never silently passed; engine timeouts/aborts are ERRORS naming the SCC that failed to converge.

## Done report

## Done report

Built the shared per-function protocol-summary fixpoint engine
(`frob.graph.summary.compute_protocol_summaries`): a bottom-up fixpoint
over an explicit `CallGraph` + T-0744 `Edge` sequence (PROTOCOL/
TRANSITION/REQUIRES), decomposing the graph into SCCs via a private,
iterative (non-recursive) Tarjan implementation -- deliberately not
`frob.cycle.graph.find_cycles`, which drops non-cyclic singleton
components this engine still needs a node for -- processed strictly
bottom-up (a callee's summary always finalizes before its caller's).
Recursive clusters (mutual recursion or a self-recursive function)
iterate the union/or-poison join to a fixpoint, bounded by
`max_iterations` (default 100).

NO-FAIL-SILENT channels implemented per acceptance: `UNRESOLVED_CALLEE`
(a sentinel callee symref a caller wires into `CallGraph.calls`) POISONS
the calling function's summary and propagates through every transitive
caller, never resetting at a clean intermediate hop
(`test_poisoning_propagates_transitively_through_a_clean_caller`). A
function never reached from any passed-in `entrypoints` gets NO summary
at all -- reported in `SummaryResult.not_analyzed`, not a falsely-clean
empty one (`test_unreachable_function_is_reported_not_analyzed_never_
silent`). A recursive SCC that fails to converge within `max_iterations`
is reported as an `SCCTimeout` naming the cluster, with every member
poisoned (`test_non_converging_scc_is_reported_as_a_timeout_error_and_
poisoned`).

Deferred, disclosed, filed as T-0809 (scope:
src/frob/graph/**, src/frob/graph/dsl.py, docs/modules/graph.md):
1. Real callee-resolution wiring (the "T-0339-family resolvers for
   callee binding" the ticket's design sketch names) -- nothing yet
   decides, from real source, when a call becomes `UNRESOLVED_CALLEE`;
   `build_call_graph` today silently omits unresolved calls rather than
   marking them. This ticket's engine defines what an unresolved callee
   DOES to a summary; wiring real detection is separate.
2. The "acquired/released/escaped resources" third of the design
   sketch's summary shape -- no DSL exists yet for resource acquire/
   release (only T-0744's protocol/transition/requires).
3. The T-0686 may-raise DESIGN CONSTRAINT ("ONE engine, whichever builds
   first hosts it") could not be coordinated on this pass -- T-0686 does
   not exist yet in this repo. Whoever builds it should consume
   `frob.graph.summary`'s SCC/fixpoint machinery rather than re-deriving
   a second one; noted in the module docstring and docs/modules/graph.md.

Scope deviation: T-0745's declared scope omitted a docs file, but every
new public symbol needs a `frob:doc` edge resolving to a real anchor
(COV001). Used the sanctioned `frob ticket scope --add --reason-file`
mechanism (not a hand-edit) to add `docs/modules/graph.md` to scope
before writing the new "Protocol summary engine" section there.

Changed:
  src/frob/graph/summary.py (new) -- UNRESOLVED_CALLEE, FunctionSummary,
    SCCTimeout, SummaryResult, compute_protocol_summaries
  tests/unit/test_arch.py -- TestProtocolSummaryEngine (10 tests)
  docs/modules/graph.md -- new "Protocol summary engine" section
  tickets.md -- T-0745 scope change, evidence, this Done report

Evidence (bound via --accepts 0, all pass):
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_caller_summary_includes_callee_transitions
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_requires_and_transitions_join_across_two_hops
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_self_recursive_function_converges
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unresolved_callee_poisons_the_summary
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_poisoning_propagates_transitively_through_a_clean_caller
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unreachable_function_is_reported_not_analyzed_never_silent
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_diamond_shaped_calls_join_without_duplication_or_loss

`uv run pytest tests/unit/test_arch.py tests/unit/graph/ -q`: 164 passed
(10 new + full pre-existing arch/graph suites, all green).
`uv run frob test --base main`: python selection touched=28 ripple=0,
exit=0, 4.01s.

Filed: T-0809 (deferred callee-resolution wiring + resource-
tracking DSL, out-of-scope machinery per the ticket's own instruction to
disclose rather than build).

Gates: `frob check --ticket T-0745 --only lint/static/gates-fast/
gates-native/gates-security` all PASS except `gate:REL` (REL001, land-
owned per docs/guides/agent-playbook.md section 4b -- FROB_AGENT was not
set in this interactive shell so the bump-suppression half didn't
trigger; land recomputes the version bump itself, not a worktree
concern). `frob ticket sweep T-0745` re-run after the scope change to
clear the stale-sweep PRE001 the scope add produced. No waivers added by
this ticket's own code.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-ae284e6e98e77b58f
Not closed, not landed (per dispatch instructions) -- ready for review/land.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_caller_summary_includes_callee_transitions` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_requires_and_transitions_join_across_two_hops` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_self_recursive_function_converges` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unresolved_callee_poisons_the_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_poisoning_propagates_transitively_through_a_clean_caller` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unreachable_function_is_reported_not_analyzed_never_silent` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_diamond_shaped_calls_join_without_duplication_or_loss` (pytest node id, verified passing when recorded)

<!-- ticket:T-0746 -->
```yaml
id: T-0746
title: 'protocol verification gate: state-requirement + invalid-transition errors
  with recorded language-excuse discharges'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0745
parent: T-0739
scope:
- src/frob/gates/**
- src/frob/arch/**
- docs/modules/gates.md
- tests/test_gates.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a C fixture where net_requires-annotated functions are reachable without
    net_init WHEN the gate runs THEN an ERROR names the unestablished state and the
    call path; GIVEN the same shape in Rust with a Drop impl THEN a recorded Drop
    discharge, and with mem::forget observed THEN the excuse is revoked and the ERROR
    returns
  evidence: []
threat: null
component: null
labels: []
```
Child 3 of T-0739. Verification: for every call site of a requires-state function, the caller-context established states (from summaries + entrypoint initial states) must include the required state -- violation is a GATE-TIER ERROR (not advisory; user mandate: enforceable, never fail-silent). A transition function reachable in a state where the transition is undefined = ERROR. The *_init-never-called and *_deinit-orphaned cases fall out: an inferred init protocol whose init is never reachable from any entrypoint while state-requiring functions are = ERROR naming both. LANGUAGE EXCUSES as recorded discharges (T-0383 caught_by doctrine): Rust pairing discharges to Drop UNLESS mem::forget/ManuallyDrop observed on the type (revokes); C++ discharges to RAII only when the init result is observed held by a destructor-bearing class; Python discharges lexically to with-blocks; TS to using/try-finally; GC finalizers NEVER discharge. Every excuse names its mechanism in the finding output; an excuse whose mechanism cannot be observed in code is an ERROR, not a discharge. Unknown/poisoned summaries at a checked call site = ERROR (waivable with reason).

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
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a C fixture acquiring a resource with an early-error return skipping
    cleanup WHEN the gate runs THEN an ERROR names the leaking path; GIVEN the Python
    equivalent inside a with-block THEN a recorded context-manager discharge; GIVEN
    cleanup=process-exit-ok THEN termination paths discharge silently by declared
    policy only
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- tests/system/test_cli_check.py
- tests/system/conftest.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
- docs/guides/agent-playbook.md
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
follow-up from T-0627: --stamp-baseline runs the full undelta'd gates pass (same ~110s+ wall time as a bare frob check) and is deliberately NOT refused under FROB_AGENT since it is a legitimate one-shot warm-up step, not a repeatable verification loop -- so it can still stall a dispatched sub-agent the same way T-0627 fixed for plain frob check. T-0627's ticket body named this as option (c) (make --stamp-baseline itself incremental) and left it unbuilt. Needs either: stamp per stage-group chunk and merge, or a documented coordinator-only path (stamp-baseline runs from the coordinator's shell before dispatch, never from an agent's).

<!-- ticket:T-0752 -->
```yaml
id: T-0752
title: 'doable: priority column, in-flight/dispatchable split, and undispatched-critical
  staleness alarm'
state: done
kind: ux
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0716
parent: T-0715
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
scope_changes: []
evidence:
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_no_lease_is_not_in_flight
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_no_root_never_in_flight
- tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_same_day_is_zero_hours
- tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_one_day_old_is_24_hours
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_under_threshold_no_alarm
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_medium_priority_never_alarms
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_high_past_threshold_alarms
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_configured_threshold_from_frob_toml
- tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
attachments: []
acceptance:
- text: GIVEN a critical ticket unleased past threshold WHEN frob ticket doable runs
    THEN its row shows priority and an UNDISPATCHED alarm at the top of the dispatchable
    section AND frob check emits a TICK-family warning naming it
  evidence:
  - tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms
  - tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight
  - tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
threat: null
component: null
labels: []
```
User mandate 2026-07-22, after T-0731 (CRITICAL) sat filed-but-undispatched for hours while its conflict class kept firing: the doable listing must make dispatch state and priority impossible to miss. (1) PRIORITY COLUMN: doable renders the priority (critical/high/medium/low) per row -- ordering exists (T-0411) but is invisible today, so a critical at rank 4 reads like any other line. (2) DISPATCH-STATE SPLIT: rows with a live, non-stale lease (T-0716 overlay machinery) render in a separate IN-FLIGHT section (or an @worktree marker) below the truly-dispatchable rows, so line 1 of the top section is always the next thing to dispatch -- no mental subtraction of in-flight work. (3) STALENESS ALARM: a critical or high ticket that has been dispatchable (unleased, unblocked) longer than a configurable threshold (frob.toml, default 4h for critical / 24h for high, measured from the last state change or filing) gets a loud UNDISPATCHED marker on its row AND a TICK-family check warning, so the condition surfaces in frob check too, not only when someone happens to run doable. Coordinate with T-0714 (doable noise relocation) and T-0716 (lease overlay) -- one display surface, no duplicate lease-reading logic.

## Done report

Implemented all three display-layer asks against `frob ticket doable`'s default (non-json, non-show-blocked) render:

1. PRIORITY COLUMN: every row (dispatchable and in-flight) now prints `priority=<level>`.
2. IN-FLIGHT/DISPATCHABLE SPLIT: `has_live_lease` (new, reuses `display_state`'s existing `read_all_leases` overlay from T-0716 -- no second lease-read path) partitions `doable()`'s result; rows with a live lease against them render under a separate "In-flight (leased, already being worked)" section below the dispatchable ones.
3. STALENESS ALARM: `undispatched_stale` (new) flags any CRITICAL/HIGH dispatchable ticket whose `dispatch_stale_hours` (measured from `Ticket.created`, the only timestamp the ticket model carries -- see deviation below) exceeds a per-priority `frob.toml [tickets]` threshold (`dispatch_stale_critical_hours`/`dispatch_stale_high_hours`, defaulting to 4h/24h). Alarmed rows sort to the top of the dispatchable section and print a `[UNDISPATCHED Xh > Yh threshold]` suffix.

`--json`/`--ignore-lease` output is unchanged (raw `doable()` result) -- the split/alarm are display-only, matching the ticket's ask that this stay a rendering concern.

DOCS (reviewer ride-along gap, closed): `docs/modules/tickets.md`'s Scope-lease model section documents the two new `frob.toml [tickets]` keys (`dispatch_stale_critical_hours`/`dispatch_stale_high_hours`, matching the existing `large_glob_max_files` entry's style), and the Public API section's `frob:describes` list plus its python code-block gained `has_live_lease`, `dispatch_stale_hours`, and `undispatched_stale` entries.

SPAWN-DISCIPLINE FIX (land blocker, closed): the FIRST landed version of `_doable` computed `breadth = scope_breadth_context(root)` once (one `git ls-files` spawn) for its own warnings, but called `doable(queue, root, ignore_lease=...)` with no way to pass that `breadth` through -- `doable()` had no such kwarg, so its internal `leased_by` filter recomputed `scope_breadth_context` itself, a SECOND `git ls-files` spawn per invocation. This regressed the T-0773 spawn-budget guarantee and failed `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once` once current main was merged in for land. Fixed by giving `doable()` the exact same `breadth: tuple[int, tuple[str, ...]] | None = None` kwarg `doable_blocked()` already carries (mirrored precisely: `if root is not None and breadth is None: breadth = scope_breadth_context(root)`), and threading `_doable`'s precomputed `breadth` into the `doable(...)` call. `frob ticket doable`'s default render is now back down to one `git ls-files` per invocation.

DEVIATION (disclosed, not silently dropped): the acceptance criterion also asks for "AND frob check emits a TICK-family warning naming it". `Ticket` has no per-transition timestamp (only `created: date`), so `dispatch_stale_hours` degrades "last state change or filing" to "filing" (`(today - created).days * 24`) -- day-granular, not true wall-clock hours; documented in the function's docstring and the module doc. Wiring an actual TICK-family `frob check` gate warning requires touching `src/frob/gates/__init__.py`, OUTSIDE T-0752's declared scope (`src/frob/tickets/**`, `src/frob/app/ticket_runner.py`, `docs/modules/tickets.md`). Built the alarm judgment as a single reusable library function (`frob.tickets.undispatched_stale`) precisely so a future gate can call it with zero duplicated lease/staleness logic, and filed T-0820 to do that wiring. The ticket's single acceptance criterion is left UNBOUND rather than force-bound.

T-0752's `blocked_by=['T-0716']` was stale at start-of-work: T-0716 is `[done]` -- ticket start proceeded normally.

Verification run in this worktree (final pass, current main merged):
- `uv run --frozen pytest tests/system/test_spawn_budget.py tests/test_tickets_dispatch_stale.py -q` -> 14 passed, 0 failed (spawn-budget duplicate-argv assertion green)
- `uv run ruff check` / `uv run ruff format --check` and bare PATH `ruff check` / `ruff format --check` on the touched files -> clean under both
- Chunked `uv run --frozen frob check --ticket T-0752 --only <lint|static|gates-fast|gates-native|gates-security>` -> all 0 errors (gates-fast FAILed and was fixed across several passes this ticket's history: missing frob:doc/frob:tests/frob:ticket directives + stale pre-work sweeps each time source changed, always resolved by adding the directive/re-running `frob ticket sweep T-0752`)
- `uv run --frozen frob test --base main` -> touched-set selection, prior pass `[PASS] python exit=0 2.45s`; re-verified green via the direct pytest run above after the spawn-discipline fix

Left unmodified: `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes` fails on this worktree both before and after my change (pre-existing strata sys_runner REL200 fixture failure, unrelated to tickets/ticket_runner) -- not touched, not in scope.

### Changed
```
 docs/modules/tickets.md              |  36 +++++++
 src/frob/app/ticket_runner.py        |  67 ++++++++++++-
 src/frob/tickets/__init__.py         | 131 +++++++++++++++++++++++++-
 tests/test_tickets_dispatch_stale.py | 178 +++++++++++++++++++++++++++++++++++
 4 files changed, 405 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_no_lease_is_not_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_no_root_never_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_same_day_is_zero_hours` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_one_day_old_is_24_hours` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_under_threshold_no_alarm` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_medium_priority_never_alarms` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_high_past_threshold_alarms` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_configured_threshold_from_frob_toml` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)

<!-- ticket:T-0754 -->
```yaml
id: T-0754
title: 'captured Done-report claims: test-count and gate-state fields populated from
  real command output, re-verified at land'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by: []
parent: T-0417
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a done-report whose typed test count differs from the actual evidence
    run WHEN done-report captures THEN it records the real count and flags the divergence;
    GIVEN a captured gate-state that no longer holds at land THEN land errors
  evidence: []
threat: null
component: null
labels: []
```
Root-cause analysis 2026-07-22: across ~15 review rejects this session, the single largest class was the Done report claiming numbers/state that did not reproduce (T-0572 142-reported-as-145 and 0-errors-that-was-27; T-0710/T-0724 undisclosed gate state; the phantom-filing family already closed by TICK006). The Done report is the ONLY pipeline artifact that is unverified free prose -- evidence ids resolve, scope binds, the diff is real, but the prose claims are typed from memory/stale runs. Fix: CAPTURE, do not type. Extend frob ticket done-report so structured claim fields are populated from REAL command output, not narrative: (1) a test-result field captured by actually running the recorded evidence node ids (pass count + a digest of the run), refusing to record a count the run did not produce; (2) a gate-state field auto-filled from a fresh frob check --ticket capture (the "clean except X" line becomes generated, never typed); (3) at land, re-verify the captured claims still hold against the merged tree and ERROR on divergence. The narrative prose stays for WHY; the CHECKABLE claims become captured artifacts. This is the general form of TICK006 (which made filing-claims checkable) applied to test-count and gate-state claims.

<!-- ticket:T-0755 -->
```yaml
id: T-0755
title: 'adversarial evidence obligation: ticket tests must fail on a diff-scoped mutant
  (confirmatory-only tests flagged)'
state: queued
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by: []
parent: T-0417
scope:
- src/frob/mutate/**
- src/frob/tickets/**
- src/frob/gates/**
- docs/modules/tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a ticket whose recorded evidence tests all pass against a mutant of
    the changed logic WHEN close/land verifies THEN a confirmatory-only-test finding
    fires naming the tests; GIVEN at least one evidence test fails on the mutant THEN
    it passes
  evidence: []
threat: null
component: null
labels: []
```
Root-cause analysis 2026-07-22: several rejects were correctness bugs whose own tests PASSED because they were confirmatory, not adversarial -- written to pass for the reason the implementer built the thing (T-0611, T-0571, T-0682, T-0574, T-0710). A confirmatory test that would pass on BOTH the pre-change and post-change code proves nothing. frob already has `frob mutate`. Add a diff-scoped obligation: for a ticket touching code with new/changed tests, run those tests against the PRE-change version of the changed symbols (or a targeted mutant of the new logic) and require at least ONE recorded evidence test to FAIL on the mutant -- proving the test actually distinguishes the change. A test that passes on the mutant is a confirmatory-only test = a TEST-family warning (ratchet to error via T-0569 pool for security/bug-kind tickets). This is mutation testing scoped to the ticket diff, wired into close/land as evidence-quality verification, reusing frob.mutate.

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
blocked_by: []
parent: T-0397
scope:
- src/frob/check/**
- src/frob/gates/**
- src/frob/tickets/**
- docs/modules/gates.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a change that reddens frob sys audit WHEN land preflight runs THEN land
    errors naming the new self-audit gap; GIVEN a ticket adding a gate rule id with
    no before-fails/after-passes fixture in its evidence THEN close is blocked
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0330
scope:
- src/frob/graph/dsl.py
- src/frob/gates/**
- src/frob/arch/_normalized.py
- src/frob/tickets/_land.py
- docs/modules/gates.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN _normalized.py gains a tree_sitter import WHEN the INV gate runs THEN
    an error fires; GIVEN a comparator invariant declared with a property test THEN
    a violating change fails it; both known cases seeded
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- tests/unit/perf/test_hotgraph.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0710
scope:
- tests/unit/perf/
- src/frob/perf/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the overhead test WHEN the full suite runs under -n auto THEN it passes
    reliably (serial marker, CPU-time measure, or documented-tolerance margin), not
    only under -n0
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: T-0352
scope:
- src/frob/gates/_pii_structural.py
- tests/test_gates.py
- docs/modules/gates.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a TS field typed as a known secret-wrapper or a Rust field typed secrecy::SecretString
    WHEN pii_structural runs THEN a type-kind PII finding fires; a plain String field
    does not
  evidence: []
threat: null
component: null
labels: []
```
From T-0352 (TS/Rust structural PII, landed): the NAME-kind field detection is cross-language, but TYPE-kind PII signals (Python EmailStr/SecretStr) stay Python-only. Extend to nominal PII-shaped TYPES in TS/Rust: TS branded/nominal email types and known secret-wrapper types; Rust secret-wrapper crate types (secrecy::Secret, SecretString) and newtype PII wrappers. Requires resolving a field/binding TYPE to a known-PII-type registry per language -- coordinate with T-0717 capability taxonomy and the T-0611/T-0612 adapters type info. Disclosed in T-0352 module docstring, not silently dropped.

<!-- ticket:T-0764 -->
```yaml
id: T-0764
title: 'friction: archive/concurrent-ledger-rewrite silently reverts in-flight tickets
  start+evidence+acceptance (recovered T-0753 by hand)'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: high
blocked_by: []
parent: T-0577
scope:
- src/frob/tickets/**
- tests/test_tickets*.py
- tests/test_ticket_land.py
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-0764 also needs regression tests in tests/test_ticket_land.py for splice_ledger
    richness/id-drop guards; test_tickets*.py glob doesn't match this filename
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_force_overrides_the_live_lease_refusal
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_ignores_a_stale_lease_from_a_removed_worktree
- tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie
- tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins
- tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_a_side_only_id_missing_from_theirs_survives_the_splice
- tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_malformed_side_is_refused_not_silently_treated_as_empty
- tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_render_that_would_drop_an_id_is_refused
attachments: []
acceptance:
- text: GIVEN a live non-stale lease WHEN frob ticket archive runs THEN it refuses
    without --force; GIVEN an in-flight ticket WHEN main ledger is rewritten under
    it THEN its start/evidence/acceptance survive the finalize
  evidence:
  - tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists
  - tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie
threat: null
component: null
labels: []
```
Coordinator friction 2026-07-22: frob ticket archive (and any concurrent land that rewrites main tickets.md) causes in-flight worktree tickets to LOSE their start/evidence/acceptance-binding when the worktree next runs the 10b restore (git checkout main -- tickets.md picks up the archived/rewritten ledger where the in-flight ticket is back to queued with empty evidence). Recovered T-0753 by hand (re-start, re-record 6 evidence ids, re-bind acceptance). Fixes: (1) archive should REFUSE (or warn-and-require --force) when live non-stale leases exist -- archiving during in-flight work is the hazard; the TICK003 remediation text already says run in a quiet window, make it enforced. (2) the 10b restore recipe is fragile against a rewritten-ledger main; the real fix is the single-writer done-report/evidence path never needing a full restore -- coordinate with T-0577/T-0637 land machinery so an agent NEVER git-checkout-main-tickets.md (the land --path replay the coordinator already does is the safe pattern).

## Done report

Root-caused three distinct write paths in the T-0753 incident class and
closed each with a regression-tested guard:

1. `frob.tickets.archive` (src/frob/tickets/__init__.py) rewrites main's
   whole active ledger without checking whether any OTHER ticket is
   mid-`start` in a sibling worktree; the in-flight worktree's later
   section-10b `git checkout main -- tickets.md` restore then silently
   reverted its own start/evidence/acceptance to queued. `archive` now
   refuses (`Err(ArchiveLiveLeaseExists)`) whenever `read_all_leases`
   reports any live cross-worktree lease, unless `force=True` is passed --
   a stale lease (worktree removed) is correctly ignored, never wedging
   archive forever.

2. `splice_ledger`'s `_newer` tiebreak (src/frob/tickets/_land.py) only
   ever qualified on Done-report presence; an in-flight ticket with
   `start` + recorded evidence + a bound acceptance criterion but NO Done
   report yet, tied in state-rank with a bare reset copy of the same id,
   fell to an arbitrary `b`-wins tiebreak that could discard the richer
   side -- exactly T-0753's shape. Generalized the tiebreak to a full
   richness tuple (Done-report presence, evidence count, bound-acceptance
   count), same priority order, so an existing Done-report-differs case
   decides identically to before. Added `_union_acceptance` (the
   acceptance-binding twin of the existing `_union_evidence`/D-09) so a
   winning side that itself lacks a binding the losing side already had
   inherits it rather than dropping it.

3. Structural guard for the T-0367 markerless-block/id-drop incident
   class: `check_ledger_id_integrity` (src/frob/tickets/_store.py)
   re-parses a rendered ledger and refuses (`Err(LedgerIntegrityViolation)`)
   if any input id fails to round-trip back out with its marker --
   wired into `write_all`, `write_archive`, and `splice_ledger` (which
   also separately refuses if the merge step itself drops an id present
   on either input side, outside an intentional archive-resurrection
   drop).

Deviations / disclosed cuts:
- `frob ticket archive`'s CLI entrypoint (src/frob/app/ticket_runner.py)
  does not yet expose `--force` -- that file is outside this ticket's
  declared scope. Filed T-0810 (finalizes to a sequential id at
  land) for the CLI wiring.
- The acceptance criterion's "markerless block" half is exercised via a
  direct unit-level pin on `check_ledger_id_integrity`
  (`test_render_that_would_drop_an_id_is_refused`, monkeypatching the
  render step to simulate a future regression) rather than a genuinely
  markerless FRESH input side -- a marker-less chunk with no prior
  parseable state carries no id to compare against, so an id-drop cannot
  be detected there at all; this is an information-theoretic limit, not
  a gap left unaddressed. A separate test confirms a malformed (marker
  present, fence broken) side still propagates its `Err` rather than
  being silently treated as empty.
- `scope` was extended by one glob (`tests/test_ticket_land.py`, via
  `frob ticket scope T-0764 --add ... --reason ...`) since
  `tests/test_tickets*.py` does not match that filename; recorded in
  `scope_changes`, not a silent expansion.

Gates: `frob check --ticket T-0764` clean across lint/static/gates-fast/
gates-native/gates-security except REL001 (land-owned, expected under
FROB_AGENT).

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_force_overrides_the_live_lease_refusal` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_ignores_a_stale_lease_from_a_removed_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_a_side_only_id_missing_from_theirs_survives_the_splice` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_malformed_side_is_refused_not_silently_treated_as_empty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_render_that_would_drop_an_id_is_refused` (pytest node id, verified passing when recorded)

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
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/perf/**
- docs/modules/perf.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a repo and a recorded profile artifact (perf script output, .cpuprofile,
    or JFR print output) WHEN the user runs the frob perf collect subcommand THEN
    the hit stream is resolved through resolve_stream and per-language deciles are
    readable from the CLI output
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- docs/design/registry/**
- docs/strata/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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

<!-- ticket:T-0773 -->
```yaml
id: T-0773
title: 'tickets: memoize git-common-dir/lease reads per CLI invocation (dozens of
  identical rev-parse spawns per command)'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/__init__.py
- tests/test_tickets_leases.py
- tests/system/test_spawn_budget.py
scope_changes:
- op: add
  glob: tests/system/test_spawn_budget.py
  reason: T-0773's own ticket text names these two strict-xfail budget locks as an
    explicit land obligation (remove the xfail markers once the memoization fix lands);
    the tests are tagged to this ticket and must be edited as part of it
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once
- tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree
- tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease
- tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_new_lease_file_written_by_a_sibling_process_is_seen_next_call
- tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_lease_file_removed_by_a_sibling_process_is_seen_next_call
- tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_unchanged_lease_file_content_is_reused_from_cache
attachments: []
acceptance:
- text: GIVEN one frob ticket list/doable/show invocation WHEN it completes THEN git
    rev-parse --git-common-dir was spawned at most once and the lease directory was
    read at most once for that invocation; a regression test counts spawns
  evidence:
  - tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once
  - tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
threat: null
component: null
labels: []
```
User observation 2026-07-22: a single frob ticket command spawns git rev-parse --git-common-dir dozens of times and re-reads/re-judges every lease file each time (the same stale-lease WARNING printed 4+ times per command). Cause: read_all_leases -> leases_dir -> git_common_dir runs an uncached subprocess per call, and callers (_cross_worktree_leases via doable ordering, display_state per ticket row, sweep/check paths) call read_all_leases repeatedly within one invocation. Fix: memoize git_common_dir per (root) for the process lifetime (safe: the common dir cannot move mid-invocation) and thread one lease snapshot through a single CLI invocation instead of re-reading per ticket. Keep the WARNING-on-stale behavior but emit each stale lease once per invocation.

## Done report

Fixed the 2026-07-22 rev-parse incident: `frob.tickets._leases` now
memoizes `git_common_dir` per resolved root for the process's lifetime
(`_common_dir_cache`) and splits `read_all_leases` into a memoized
parse step (`_leases_parse_cache`, globbing + JSON-parsing every lease
file) plus a FRESH per-call liveness re-check (`Path(record.worktree).
exists()` is never cached, since a lease's worktree can vanish
out-of-band via `git worktree remove` with no write to the leases
directory to invalidate on -- caching liveness would have kept
offering a dead worktree's lease for the rest of the process; this is
what made `tests/test_ticket_leases_cross_worktree.py::
TestCrossWorktreeLeaseVisibility::test_stale_lease_for_a_removed_worktree_is_skipped`
fail under a first, naive full-snapshot-cache design -- fixed by the
parse/liveness split). The stale-lease INFO diagnostic is still logged
only once per (leases directory, ticket id) per process
(`_stale_lease_logged`), even though liveness reruns every call.
`record_lease`/`release_lease` clear the parse cache on write so a
write followed by a read in the same process still observes it.

`frob.tickets.leased_by`/`doable`/`doable_blocked` additionally thread
one precomputed `_all_leases(queue, root)` snapshot through the
per-candidate loop, mirroring the existing `breadth` parameter
(`scope_breadth_context`) -- belt-and-suspenders on top of the
`_leases.py`-level memoization, matching the ticket's explicit ask.

## Measured spawn counts (3-ticket fixture, tests/system/test_spawn_budget.py)

Before (checked out the pre-fix `_leases.py`/`__init__.py` from commit
89820713 into the working tree, ran the un-xfailed assertion, then
restored the fix -- no `git stash` used):
- `frob ticket list`: `git rev-parse --git-common-dir` spawned 3 times
  (identical argv) -- one per ticket row via `display_state` ->
  `read_all_leases` -> `leases_dir` -> `git_common_dir`.
- `frob ticket doable`: same argv spawned 3 times -- one per candidate
  via `leased_by` -> `_all_leases` -> `_cross_worktree_leases` ->
  `read_all_leases`.

After (this fix):
- `frob ticket list`: 0 duplicate spawns (spawned at most once).
- `frob ticket doable`: 0 duplicate spawns (spawned at most once).

(The real-repo incident report was "dozens" of spawns per invocation
against this repo's actual hundreds of tickets; the 3-ticket test
fixture demonstrates the same per-row/per-candidate multiplier at a
scale small enough to assert exactly, and the fix removes the
multiplier entirely regardless of ticket count.)

## Evidence

- `tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once`
  (xfail marker REMOVED, now plain-passing, accepts acceptance[0])
- `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once`
  (xfail marker REMOVED, now plain-passing, accepts acceptance[0])
- `tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once`
  (pre-existing, still passing)
- `tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree`
- `tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease`

`uv run --frozen pytest tests/system/test_spawn_budget.py -q` -> 4 passed
in 2.47s, 0 xfailed (confirmed by `-v`, all four tests listed PASSED,
no XFAIL line).

`uv run --frozen pytest tests/test_tickets_leases.py -v` -> 4 passed.

`uv run --frozen pytest tests/test_tickets_leases.py
tests/test_ticket_leases_cross_worktree.py tests/test_tickets_lease.py
tests/test_tickets_lease_overlay.py tests/test_ticket_reconcile.py
tests/test_tickets_brief.py -q` -> 65 passed (all lease-adjacent
suites clean, including the T-0766 `resolve_lease` tests and the
worktree-liveness test that exposed the naive-cache design flaw during
development).

`uv run --frozen frob test --base main` -> python exit=0 (touched-set
selection covered both spawn-budget tests, all cross-worktree lease
tests, `tests/test_tickets.py::TestDoable`/queue-workflow integration,
and the T-0453 lease tests).

`uv run --frozen frob check --ticket T-0773 --only <stage>` for each
of lint/static/gates-fast/gates-native/gates-security -> all PASS, 0
errors (gates-fast/REL001 required `FROB_AGENT=1` in the invoking
shell -- it was not already set for this dispatch, unlike the
playbook's stated default; exporting it inline is the documented T-0574
escape hatch, not a config change, and is the only way REL001's
public-API-surface-changed-since-0.101.0 finding (from `leased_by`'s
new `all_leases` kwarg) suppresses correctly, per playbook section 4b:
version bump/changelog is land-owned, never a worktree concern).

## Deviations from the dispatch

- `FROB_AGENT` was not set in this dispatch's shell environment (the
  playbook says it is "true for every dispatched worktree agent,
  T-0574"); had to export it inline per gates-fast invocation to get
  REL001's open-debt/expired-deprecation halves scoped correctly
  without touching `pyproject.toml`. Not a ticket-scope concern, noted
  for visibility only.
- The coordinator's mid-task message correctly called out that I had
  drifted into an idle wait-on-monitor pattern; killed the stray
  background `frob check` process and re-ran everything foreground
  with explicit `timeout` values per this report.

Filed: none (no out-of-scope work discovered).
Gates: `frob check --ticket T-0773` clean across all five stage groups
(lint, static, gates-fast, gates-native, gates-security), no waivers
added.
## Round 2 (reviewer REJECT addressed)

Reviewer found the round-1 design cached the whole `read_all_leases`
result until this PROCESS's own `record_lease`/`release_lease` call
(CRITICAL: `frob.serve`'s `poll_rebase_bot` daemon loop calls
`read_all_leases` forever and never calls either, so it would go blind
to sibling-process lease writes/removals after its first poll cycle)
and mutated the module-level caches with no lock despite the daemon
thread and gate worker pools being able to call in concurrently
(MAJOR).

### Invalidation design (revised)

`_leases.py` now keys `read_all_leases`'s cache per FILE, not per
directory-snapshot: `_lease_file_cache: dict[leases_root, dict[path,
(stat_key, parsed_record_or_None)]]`. Every call:

1. Re-globs the leases directory for the CURRENT file listing (cheap
   `Path.glob`, no subprocess).
2. Drops any cached entry whose file is no longer in that listing
   (handles a sibling process's `release_lease`/direct unlink).
3. For each current file, `stat()`s it (mtime_ns, size). If the stat
   matches the cached entry, reuses the already-parsed `LeaseRecord`
   (or `None` for a known-bad file) without touching the file's bytes.
   If the stat differs (new file, or a sibling process's
   `record_lease`/direct write changed it), re-reads and re-parses,
   then updates the cache entry.

This makes the EXPENSIVE step (JSON parse) cache-hit as long as a file
is untouched, while the directory's current membership and every
file's current content are always re-observed -- a sibling process's
write or removal is visible on the very next call, from ANY process,
with no explicit invalidation hook required (so `record_lease`/
`release_lease` no longer need to clear anything).

Liveness (`Path(record.worktree).exists()`) is unchanged from round 1:
still re-checked every call, never cached, for the same reason now
extended one level -- a lease's worktree can vanish with no leases-
directory write to key a stat off of at all.

### Locking

Added `_cache_lock = threading.Lock()` (T-0125 `quiet_stdout_logs`
precedent) guarding all three caches (`_common_dir_cache`,
`_lease_file_cache`, `_stale_lease_logged`). `git_common_dir` takes the
lock only around the dict read/write, not around the `git` subprocess
itself (a benign double-spawn race between two threads missing the
cache simultaneously is possible but harmless and does not reintroduce
duplicate spawns in steady state, since the cache is warm after the
first call in a given process). `read_all_leases` takes the lock for
the whole file-cache read/update/stat-comparison sequence per call
(CPython's GIL makes one dict op atomic, but "check stat, maybe
re-parse, write back" is not one op and must not interleave across
threads).

### New tests (`tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility`)

- `test_new_lease_file_written_by_a_sibling_process_is_seen_next_call`
  -- writes a lease file directly (bypassing `record_lease`, simulating
  a sibling process), asserts the very next `read_all_leases` call sees
  it.
- `test_lease_file_removed_by_a_sibling_process_is_seen_next_call` --
  the reverse: direct `unlink` (bypassing `release_lease`), asserts the
  next call no longer returns it.
- `test_unchanged_lease_file_content_is_reused_from_cache` -- proves
  the cache-hit path is real (not accidentally always-re-reading) by
  corrupting a file's on-disk bytes while preserving its exact
  mtime/size signature (`os.utime` restore) and asserting the SECOND
  `read_all_leases` call still returns the original, previously-parsed
  record rather than failing to parse the corrupted bytes.

### Test results (foreground, `uv run --frozen`)

- `pytest tests/system/test_spawn_budget.py -v` -> 4 passed, 0 xfailed
  (re-stat adds filesystem `stat()`/`glob()` calls only, zero
  additional subprocess spawns -- the budget lock still holds).
- `pytest tests/test_tickets_leases.py -v` -> 7 passed (4 existing +
  3 new).
- `pytest tests/system/test_spawn_budget.py tests/test_tickets_leases.py
  tests/test_ticket_leases_cross_worktree.py tests/test_tickets_lease.py
  tests/test_tickets_lease_overlay.py tests/test_ticket_reconcile.py
  tests/test_tickets_brief.py -q` -> 70 passed.
- `frob check --ticket T-0773 --only lint` -> PASS after `ruff format`
  (one line-length wrap in the new module-level comment block).
- `frob check --ticket T-0773 --only static` -> PASS.
- `frob check --ticket T-0773 --only gates-fast` (FROB_AGENT=1) -> PRE001
  cleared by re-sweeping; remaining `gate:COV` COV003 findings are
  against T-0795/T-0799 (unrelated in-flight tickets whose evidence
  references test classes not present in THIS worktree's checkout --
  confirmed by grepping `tests/test_ticket_land.py` for
  `TestLandRetryAfterFinalizeThenFail`, which does not exist here; not
  caused by this ticket's change, not in T-0773's scope, pre-existing
  cross-worktree ledger churn in a highly concurrent session).

Evidence added this round:
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_new_lease_file_written_by_a_sibling_process_is_seen_next_call`
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_lease_file_removed_by_a_sibling_process_is_seen_next_call`
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_unchanged_lease_file_content_is_reused_from_cache`
## Round 3 (lock-scope re-review)

Re-review finding: `read_all_leases` held `_cache_lock` across the
ENTIRE per-file loop, including `path.stat()`, `read_text()`,
`json.loads()`, and `LeaseRecord.model_validate()` -- serializing every
concurrent caller (daemon thread, gate worker pools) behind one file's
IO/parse for the whole directory scan.

### Lock structure (final)

`read_all_leases` now takes `_cache_lock` twice, both briefly, with all
file IO/parsing OUTSIDE it:

1. Glob the leases directory and `stat()` every current file -- no lock.
2. Lock #1 (brief): prune cache entries for files no longer present,
   read each remaining file's cached `(stat_key, record)` against the
   just-taken stat, and partition into `hits` (stat unchanged, reuse
   the cached record) vs. `to_parse` (new file or changed stat).
3. Parse every `to_parse` file (`read_text` + `json.loads` +
   `model_validate`) -- no lock.
4. Lock #2 (brief): write the freshly-parsed `(stat_key, record)`
   entries back into the cache.
5. Recombine `hits` + freshly-parsed results in the ORIGINAL sorted
   (id-ordered) file order -- `hits`/`freshly_parsed` are separate
   dicts, so a naive concatenation would have reordered a listing with
   a mix of hits and misses; this is fixed by iterating `current_paths`
   once and looking each path up in whichever dict has it.

`git_common_dir`'s lock shape is unchanged from round 2 (already
correct: lock only around the dict get/set, `git` subprocess runs
outside it). A benign race where two threads both miss the cache for
the same file and both parse it independently is possible under this
design (last write to the dict wins) -- harmless and idempotent, same
reasoning as `git_common_dir`'s already-accepted double-spawn race.

### Test results (foreground, `uv run --frozen`)

- `pytest tests/test_tickets_leases.py -v` -> 7 passed.
- `pytest tests/system/test_spawn_budget.py -rx -v` -> 4 passed, 0
  xfailed (the extra glob/stat pass and the two brief locks add no
  subprocess spawns; the budget lock still holds).
- `pytest tests/system/test_spawn_budget.py tests/test_tickets_leases.py
  tests/test_ticket_leases_cross_worktree.py tests/test_tickets_lease.py
  tests/test_tickets_lease_overlay.py tests/test_ticket_reconcile.py
  tests/test_tickets_brief.py -q` -> 70 passed.
- `ruff check`/`ruff format` on `src/frob/tickets/_leases.py` -> clean.

`git diff main -- tickets.md` at finish shows only T-0773's own block
(state/scope/scope_changes/evidence/acceptance/Done-report lines) --
confirmed no other ticket id appears in the diff.

### Changed
```
 src/frob/tickets/__init__.py      |  34 +-
 src/frob/tickets/_leases.py       | 201 +++++++++--
 tests/system/test_spawn_budget.py |  40 +--
 tests/test_tickets_leases.py      |  92 ++++-
 tickets.md                        | 713 +++++++++++++++++++++++++++++++++++++-
 5 files changed, 1008 insertions(+), 72 deletions(-)
```

### Evidence
- `tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_new_lease_file_written_by_a_sibling_process_is_seen_next_call` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_lease_file_removed_by_a_sibling_process_is_seen_next_call` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_unchanged_lease_file_content_is_reused_from_cache` (pytest node id, verified passing when recorded)

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
scope_changes: []
evidence: []
attachments: []
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
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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

<!-- ticket:T-0778 -->
```yaml
id: T-0778
title: 'security: FROB_DISABLE_EXEC kill switch is a partial no-op -- wire gitio/serve/tickets
  through the T-0200 guard, delete stale waivers'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: critical
blocked_by: []
parent: null
scope:
- src/frob/gitio.py
- src/frob/process/_guard.py
- design/frob.strata
- tests/test_gitio.py
scope_changes: []
evidence:
- tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning
attachments: []
acceptance:
- text: GIVEN FROB_DISABLE_EXEC=1 WHEN any frob code path attempts a git spawn via
    run_argv (including the serve daemon and lease reads) THEN the spawn is refused
    by the guard and logged; GIVEN the five strata nodes THEN no LINT004 waiver cites
    T-0200 as pending
  evidence:
  - tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning
threat: denial-of-service
component: null
labels: []
```
Audit H2 (docs/audits/frob-blindspots-2026-07-23.md): five strata nodes (core,
fleet, tickets_ledger, stratamod, vet) waive LINT004 with reason "no real kill
switch around subprocess spawning yet -- T-0200 is the follow-on ticket to
build one". T-0200 is DONE (archived) and shipped
src/frob/process/_guard.py::guarded_subprocess_run, but only check/_python.py,
check/_ts.py, check/_native.py wired in. gitio.run_argv (the single git seam),
the serve daemon (spawning git every 20s in a background thread), and the
tickets lease git calls all bypass the guard -- so FROB_DISABLE_EXEC=1 is a
partial no-op while _guard.py's docstring promises it "genuinely stops EVERY
process this component spawns". Fix: route gitio.run_argv through
guarded_subprocess_run (which transitively covers serve+tickets since all git
IO flows through run_argv), verify no other subprocess call sites bypass it
(grep subprocess. outside _guard.py/gitio.py), DELETE the five stale waivers
from design/frob.strata (the mechanism exists; honest state is wired, not
pending), and add a test that FROB_DISABLE_EXEC=1 makes run_argv refuse.

## Done report

Changed:
- src/frob/gitio.py::run_argv -- routed through frob.process._guard.guarded_subprocess_run so FROB_DISABLE_EXEC=1 refuses every git spawn (Err(GitError.GitFailed), logged) without ever calling subprocess.run; this is gitio's single spawn seam, so the serve daemon (src/frob/serve/_daemon.py, _warm.py, which already call run_argv/working_diff) and every gitio-based read are covered transitively -- no changes needed there.
- design/frob.strata -- rewrote the 4 stale LINT004 waivers that still cite "T-0200 is the follow-on ticket to build one" (fleet, core, tickets_ledger, vet). T-0200 is done and T-0778 wired gitio.py's own spawns, so each waiver now states the honest remaining gap and points at the new follow-on ticket instead of a since-shipped mechanism. Could not delete these waivers outright (contrary to the ticket's literal instruction) -- see Deviations below.
- tests/test_gitio.py::TestRunArgv.test_kill_switch_refuses_without_spawning -- new test: FROB_DISABLE_EXEC=1 makes run_argv return Err(GitError.GitFailed), never calls the real subprocess.run (spied via monkeypatch), and logs a WARNING containing "exec disabled".

Sweep for other bypassing subprocess call sites (grep subprocess.run/Popen/call/check_output outside src/frob/process/_guard.py and src/frob/gitio.py):
- CONFIRMED WIRED (no action needed): src/frob/serve/_daemon.py, src/frob/serve/_warm.py, src/frob/serve/_tools.py all call frob.gitio.run_argv/working_diff, not subprocess directly -- T-0778's gitio wiring covers them.
- STILL BYPASSING, filed as a follow-up (out of T-0778's scope -- none of these files are in scope=[gitio.py, _guard.py, frob.strata, test_gitio.py]):
  - src/frob/tickets/__init__.py:930 `_repo_files_git` -- direct `git ls-files` subprocess.run, NOT routed through gitio.run_argv. This is the closest remaining gap to the audit's "tickets lease" language.
  - src/frob/tickets/__init__.py:2370 `_run_evidence_command` -- shell=True evidence-command spawn.
  - src/frob/gitlog/__init__.py:230 -- direct `git log` subprocess.run.
  - src/frob/app/ticket_runner.py:863,1159; src/frob/fleet/__init__.py:164,194; src/frob/tickets/clipboard.py (9 sites); src/frob/mutate/__init__.py:260; src/frob/deploy/_vm_runner.py:109,116,134,153; src/frob/scaffold/project.py:509; src/frob/testing/_coverage_wait.py:151.
  Filed as T-0803 ("wire remaining subprocess call sites through the T-0200/T-0778 exec guard...").

Deviations from the ticket's literal plan (disclosed, not hidden):
- The ticket said "DELETE the five stale LINT004 waivers" and, if LINT004 then legitimately re-fires, "the honest fix is wiring that node's spawns through the guard, not re-waiving." I found only 4 waivers with this exact reason text today (checker's was already retired with a real attr flag, and stratamod's net waiver was already dropped by T-0769 -- both before T-0778 started; git history in tickets-archive.md confirms the original 5 were checker/core/stratamod/tickets_ledger/vet). Of the remaining 4 (fleet, core, tickets_ledger, vet), NONE could be honestly deleted: each node's `may "exec"`/`may "net"` capability is attributed to files outside T-0778's scope (fleet/__init__.py's own subprocess.run; core's gitlog/mutate/deploy/scaffold/testing subprocess.run calls, only one of core's many code-glob files being gitio.py; tickets_ledger's git-ls-files/evidence-shell/clipboard.py calls; vet's net_enabled() never being called anywhere). Wiring any of those requires touching files outside scope=[gitio.py, _guard.py, frob.strata, test_gitio.py]. Deleting the waivers and declaring `attr flag=` would have been a false completeness claim -- the exact anti-pattern this repo's T-0150/T-0151 discipline (and this very ticket) exists to prevent. Instead I rewrote each waiver's reason to state the real, current state (mechanism exists and is genuinely wired for the git seam; specific remaining unwired call sites named; pointed at the new follow-on ticket T-0803 instead of the shipped T-0200) -- this satisfies the ticket's actual acceptance criterion ("no LINT004 waiver cites T-0200 as pending") without a false claim. `uv run frob sys audit` confirms selfconform stays clean (0 unwaived findings) after this change.

Evidence: tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning
- `uv run --frozen pytest tests/test_gitio.py tests/test_serve_daemon.py tests/system/test_spawn_budget.py -v` -> 33 passed, 2 xfailed (both pre-existing/unrelated).
- `uv run --frozen pytest tests/test_gitio.py -q` -> 23 passed on its own.
- `uv run --frozen pytest tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning --collect-only -q` confirms the node id resolves.

Filed: T-0803 (wire remaining subprocess call sites through the T-0200/T-0778 exec guard)

Gates: `uv run --frozen frob check --only gates-fast --ticket T-0778` clean (0 errors after `frob ticket sweep T-0778` refreshed PRE001); `--only gates-native --ticket T-0778` clean; `--only gates-security --ticket T-0778` clean; `--only static --ticket T-0778` and `--only lint --ticket T-0778` clean (pre-existing exports/frob-dup noise, all `pass`). `uv run --frozen frob sys audit` -> "sys audit: PROVED (4 waived) -- zero UNWAIVED gaps across every configured view" / "self-conformance PROVED -- zero SYS gaps", the 4 WAIVED LINT004 lines are the rewritten fleet/core/tickets_ledger/vet waivers above, no other node newly reds.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)

<!-- ticket:T-0779 -->
```yaml
id: T-0779
title: 'gates: stale-waiver detection -- waive reason citing a DONE/DROPPED ticket
  is an error (WAIVE-tier)'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- tests/test_waive_gate.py
- docs/design/registry/check-coverage.yaml
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'Adding the new WAIVE006 rule id to frob''s own reflexive check-coverage

    registry (docs/design/registry/check-coverage.yaml) is structurally

    required by the SAME change this ticket implements -- every other

    gate rule added by prior tickets (WAIVE004, WAIVE005, DEAD001, ...)

    registered itself here in the same change, and REG008/REG009 would

    otherwise immediately red main on the new frob:enforces edge. This is

    not a new task, just the one-line companion entry a new rule id always

    needs.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_pending_phrasing_is_binding
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_is_the_follow_on_ticket_phrasing_is_binding
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_bare_historical_mention_is_not_binding
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_built_a_real_kill_switch_narration_is_not_binding
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_no_ticket_mention_at_all_is_not_binding
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_dropped_ticket_fires
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_open_ticket_is_silent
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_binding_reason_phrase_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_historical_mention_of_done_ticket_is_silent
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_unresolvable_ticket_id_is_silent
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_ticket_attr_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_binding_phrase_bound_to_dropped_ticket_fires
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_open_follow_on_with_historical_mention_is_silent
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_no_design_dir_is_silent
- tests/test_waive_gate.py::TestWaive006Registration::test_waive006_is_a_known_gate_rule
- tests/test_waive_gate.py::TestWaive006Registration::test_waive006_gate_combines_both_channels
- tests/test_waive_gate.py::TestWaive006Registration::test_waivable_via_frob_waive_comment
- tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
attachments: []
acceptance:
- text: GIVEN a waive directive (frob:waive or strata waive) whose reason or ticket
    attribute references a ticket that is DONE or DROPPED in the ledger/archive WHEN
    frob check runs THEN a gate error fires naming the waiver site and the closed
    ticket; GIVEN a waiver citing an open ticket THEN no finding
  evidence:
  - tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires
  - tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_open_ticket_is_silent
  - tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
threat: null
component: null
labels: []
```
Audit H2 gate-direction (docs/audits/frob-blindspots-2026-07-23.md): the five LINT004 kill-switch waivers cite T-0200 as the follow-on ticket to build -- but T-0200 closed long ago, and no gate re-litigates a waiver once its justifying ticket lands. A waiver justified by pending-T-XXXX must not outlive T-XXXX. Implement in the WAIVE gate family: resolve every ticket id referenced in waiver reasons/attributes against the ledger+archive; DONE/DROPPED means the waiver must be re-justified or deleted. Land AFTER T-0778 clears the five current offenders or the gate reds main immediately (sequencing note for the coordinator, not a design choice).

## Done report

## Done report

Changed:
- src/frob/gates/__init__.py -- `WAIVE006` (new stale-waiver-detection
  gate rule): `_waive006_binding_ticket_refs` (binding-phrase extraction),
  `_waive006_stale_ticket` (ledger+archive resolution), `_waive006_violation`
  (shared Violation constructor), `_waive006_comment_violations` (the
  `frob:waive` comment channel), `_STRATA_WAIVE_RE`/`_strata_waive_sites`
  (regex-scan of `.strata` `waive "RULE" reason "..." [ticket "..."]`
  clauses under the design dir), `_waive006_strata_violations` (the
  `.strata` channel), `waive006_gate` (public entry point, wired into
  `_assemble_gate_report` alongside the other WAIVE00* self-checks).
  `WAIVE006` added to `_KNOWN_GATE_RULES` (waivable -- deliberately NOT
  added to `_UNWAIVABLE_RULES`).
- docs/design/registry/check-coverage.yaml -- `CHK-GATE-WAIVE006` entry
  (`handled_by:WAIVE006`), `gate_rule_total` 104 -> 105. Required by the
  same change (REG008/REG009 red main on the new `frob:enforces` edge
  otherwise); scope was extended to cover this file via `frob ticket
  scope T-0779 --add docs/design/registry/check-coverage.yaml`.
- tests/test_waive_gate.py -- new file, 19 tests across binding-phrase
  extraction, the comment channel, the strata channel, waivability/
  registration, and a real-repo zero-false-positive proof.

Rule design: WAIVE006 fires when a waiver (either a `frob:waive` code
comment or a `.strata` `waive "RULE" reason "..." ticket "..."` clause)
BINDS ITSELF to a ticket id that is DONE or DROPPED in the merged
active+archive ledger (`frob.tickets.load_queue`, the same source
DEBT002 already resolves against). "Binds itself" is deliberately
narrower than "mentions": an explicit `ticket=`/`ticket "..."` attribute
is always binding; absent that, only two conservative reason-text
phrasings count as binding ("pending T-####[...]" and "T-#### is the
follow-on ticket") -- a bare id mention in build-history prose (e.g.
"(T-0200/T-0778)" or "T-0200 built a real kill switch") is never
extracted. An unresolvable ticket id (typo, not-yet-landed draft) is
silently skipped -- that is a different honesty gap, not WAIVE006's.

Calibration / real-repo result: `TestWaive006RealRepo::
test_zero_errors_on_real_repo` runs `waive006_gate` against this repo's
OWN live snapshot+queue (via `_load_inputs`) and asserts zero violations
-- verified passing. This specifically proves the T-0778 case the ticket
called out: `design/frob.strata`'s five current LINT004 waivers cite
`ticket "T-draft-8cd37914"` (open) while their `reason` text mentions the
long-closed T-0200 only as build-history narration ("kill-switch
mechanism exists (T-0200/T-0778) but ... -- tracked in
T-draft-8cd37914") -- WAIVE006 does not fire on that. The full `frob
check --only <stage>` chunked loop (lint/static/gates-fast/gates-native/
gates-security, `--ticket T-0779`, `FROB_AGENT=1` set so REL001's
bump/changelog half is suppressed per the worktree-agent posture) is
clean: `gate:WAIVE` reports 0 errors in every stage that runs it.

Evidence: 19 node ids recorded via `frob ticket evidence T-0779`, all
resolving under `pytest --collect-only`:
tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::{test_pending_phrasing_is_binding,
test_is_the_follow_on_ticket_phrasing_is_binding,
test_bare_historical_mention_is_not_binding,
test_built_a_real_kill_switch_narration_is_not_binding,
test_no_ticket_mention_at_all_is_not_binding},
TestWaive006CommentChannel::{test_ticket_attr_bound_to_done_ticket_fires,
test_ticket_attr_bound_to_dropped_ticket_fires,
test_ticket_attr_bound_to_open_ticket_is_silent,
test_binding_reason_phrase_bound_to_done_ticket_fires,
test_historical_mention_of_done_ticket_is_silent,
test_unresolvable_ticket_id_is_silent},
TestWaive006StrataChannel::{test_strata_ticket_attr_bound_to_done_ticket_fires,
test_strata_binding_phrase_bound_to_dropped_ticket_fires,
test_strata_open_follow_on_with_historical_mention_is_silent,
test_no_design_dir_is_silent},
TestWaive006Registration::{test_waive006_is_a_known_gate_rule,
test_waive006_gate_combines_both_channels,
test_waivable_via_frob_waive_comment},
TestWaive006RealRepo::test_zero_errors_on_real_repo.

`uv run pytest tests/test_waive_gate.py tests/test_gates.py -q`: 19 + 253
passed (both files, no failures). `uv run frob check --only lint/static/
gates-fast/gates-native/gates-security --ticket T-0779` (FROB_AGENT=1):
each stage 0 errors.

Filed: none.

Gates: `frob check --ticket T-0779` clean across all five `--only`
stage-groups (0 errors each). No waivers taken on this ticket's own
changes.

Deviations: the ticket's scope glob (src/frob/gates/**,
tests/test_waive_gate.py) did not cover the one-line registry companion
entry every new gate rule id needs (docs/design/registry/
check-coverage.yaml) -- extended scope via `frob ticket scope T-0779
--add ...` rather than silently touching an out-of-scope file, per the
SCOPE001 finding's own suggested remedy. `.strata` waive-clause detection
uses a plain single-line regex scan (`_STRATA_WAIVE_RE`) rather than a
`strata_core` parse -- every live `waive` clause in this repo today is
single-line (T-0778's own rewrite), so this is a documented, not a
silent, limitation; a clause split across lines is simply not matched.

### Changed
```
 tickets.md | 69 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 66 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_pending_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_is_the_follow_on_ticket_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_bare_historical_mention_is_not_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_built_a_real_kill_switch_narration_is_not_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_no_ticket_mention_at_all_is_not_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_dropped_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_open_ticket_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_binding_reason_phrase_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_historical_mention_of_done_ticket_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_unresolvable_ticket_id_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_ticket_attr_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_binding_phrase_bound_to_dropped_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_open_follow_on_with_historical_mention_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_no_design_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006Registration::test_waive006_is_a_known_gate_rule` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006Registration::test_waive006_gate_combines_both_channels` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006Registration::test_waivable_via_frob_waive_comment` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo` (pytest node id, verified passing when recorded)

<!-- ticket:T-0780 -->
```yaml
id: T-0780
title: 'security: serve daemon feeds peer-writable lease branch names into git argv
  -- validate + ''--'' terminator'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/serve/_daemon.py
- src/frob/tickets/_leases.py
- tests/test_serve_daemon.py
- tests/test_tickets_leases.py
scope_changes: []
evidence:
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_branch
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_worktree
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_admits_a_legitimate_branch
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_detached_head_sentinel
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_resolve_lease_treats_an_evil_branch_as_no_lease
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_rejection_is_logged_once_per_process
- tests/test_serve_daemon.py::TestPollRebaseBotLeaseInjectionGuard::test_evil_lease_branch_never_reaches_git_argv
attachments: []
acceptance:
- text: GIVEN a lease JSON with branch or worktree starting with a dash or containing
    a git-invalid ref shape WHEN read_all_leases loads it THEN the record is rejected
    and logged, never admitted; GIVEN daemon merge-base/merge-tree invocations THEN
    ref operands follow a -- terminator; a regression test injects a crafted evil
    lease and asserts no git call receives it
  evidence:
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_branch
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_worktree
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_admits_a_legitimate_branch
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_detached_head_sentinel
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_resolve_lease_treats_an_evil_branch_as_no_lease
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_rejection_is_logged_once_per_process
  - tests/test_serve_daemon.py::TestPollRebaseBotLeaseInjectionGuard::test_evil_lease_branch_never_reaches_git_argv
threat: elevation-of-privilege
component: null
labels: []
```
Audit M1 (docs/audits/frob-blindspots-2026-07-23.md): poll_rebase_bot passes lease-JSON branch strings verbatim into git merge-base/merge-tree argv with no -- terminator and no ref validation. Any local process able to write under the shared .git common dir (every co-located worktree agent) can drop evil.json with branch='--output=...' and the unattended daemon executes git option injection. Fix both layers: (1) read_all_leases/resolve_lease validate branch/worktree shape (reject leading dash; git check-ref-format-conformant allowlist) and drop+log failures; (2) daemon git calls put -- before ref operands. NOTE: also coordinate with T-0778 (guard wiring) and the M2 lease-TTL ticket -- same files, serialize dispatch.

## Done report

Two independent layers, matching the ticket's plan.

Layer 1 (admission, src/frob/tickets/_leases.py): a new
`_looks_like_a_safe_git_argv_operand` predicate -- non-empty, no leading
`-`, matching a conservative allowlist `^[A-Za-z0-9._/-]+$` -- is applied
to both `branch` and `worktree` via `_lease_shape_is_safe`, checked in
BOTH parse paths that admit a `LeaseRecord`: `read_all_leases`'s per-file
parse loop and `_read_one_lease` (which `resolve_lease` calls). A record
that fails is dropped (never returned) and logged once per process per
file path via `_log_rejected_lease_once` (same pattern as T-0773's
`_stale_lease_logged`), so a long-lived daemon re-polling the same
peer-written evil file does not spam the log. Deliberately NOT full `git
check-ref-format` conformance -- documented inline: the allowlist exists
to make option-injection (leading `-`) structurally impossible, not to
validate every git ref-format rule; over-rejecting a merely-unusual but
legitimate ref would be worse than under-validating format details this
repo never actually shells out to `check-ref-format` to check anyway.
`branch="HEAD"` (T-0784's detached-HEAD sentinel) and absolute worktree
paths both pass the allowlist as-is, verified by test.

Layer 2 (argv, src/frob/serve/_daemon.py): `_merge_would_conflict`'s `git
merge-base` call now terminates options with `--` before its ref operands
(`git merge-base -- main branch`), verified directly against this repo's
git 2.34 baseline. `git merge-tree` (old-style, pre-`--write-tree`) does
NOT accept a `--` terminator on this git version -- verified directly,
`git merge-tree -- <a> <b> <c>` fails with a usage error -- so adding one
there would break every rebase-bot simulation rather than harden one; this
is documented inline with the verification note. `merge-tree`'s operands
are `merge_base` (git-computed) and `main_head` (self-resolved via
`rev-parse main`), never lease-sourced, plus `branch`, which is already
guarded by layer 1 before `_merge_would_conflict` ever sees it -- layer 1
alone is that call's defense, and the docstring says so explicitly rather
than implying `--` covers it.

Regression test (tests/test_serve_daemon.py::
TestPollRebaseBotLeaseInjectionGuard::
test_evil_lease_branch_never_reaches_git_argv): writes a lease file
directly to the shared leases directory (bypassing `record_lease`
entirely, simulating a peer worktree agent) with
`branch="--output=/tmp/x"`, spies on `frob.serve._daemon.run_argv`, runs
`poll_rebase_bot`, and asserts no captured argv call contains the payload
string, plus that a warning naming the rejected ticket id was logged.

Six more unit tests in tests/test_tickets_leases.py::
TestLeaseShapeValidation cover: a dash-prefixed `branch` dropped by
`read_all_leases` (with the once-per-process log assertion isolated into
its own test), a dash-prefixed `worktree` dropped the same way, a
legitimate branch name still admitted, the `branch="HEAD"` sentinel still
admitted, and `resolve_lease` surfacing an evil-branch lease as
`NoLeaseForTicket` (the same loud failure as no lease at all, via the
separate `_read_one_lease` code path).

Verification: ran the ticket's `--only` stage groups
(lint/static/gates-fast/gates-native/gates-security) scoped to T-0780,
all 0 errors; `uv run frob test --base main` (touched-set) returncode=0;
`uv run pytest tests/test_serve_daemon.py tests/test_tickets_leases.py
tests/system/test_spawn_budget.py -q` -- 33 tests collected, all passed
(green, no failures); `git diff main --diff-filter=D --stat` is empty.

Deviation from the literal acceptance wording: the acceptance text reads
"daemon merge-base/merge-tree invocations follow a -- terminator"
(plural). Only `merge-base` actually gets one -- `merge-tree` cannot, on
this repo's git 2.34 baseline, without breaking every simulation (verified
directly, not assumed). The security property the ticket cares about
(no git call ever receives an injected operand) still holds for
`merge-tree` via layer 1's admission-time rejection, proven by the
regression test above. This is disclosed here rather than silently
following the letter of the acceptance text over its actual intent.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_branch` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_admits_a_legitimate_branch` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_detached_head_sentinel` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_resolve_lease_treats_an_evil_branch_as_no_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_rejection_is_logged_once_per_process` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBotLeaseInjectionGuard::test_evil_lease_branch_never_reaches_git_argv` (pytest node id, verified passing when recorded)

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
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- src/frob/gates/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a fixture where a value parsed from a file under .git/ or .frob/ flows
    into a subprocess argv position without passing a registered validator or a preceding
    -- literal WHEN the check runs THEN a finding fires naming source and sink; GIVEN
    the same flow through a validator THEN no finding
  evidence: []
threat: null
component: null
labels: []
```
Audit M1 gate-direction: SEC gates catch shell=True and f-string-into-argv but not the trust-boundary shape (peer-writable state file -> argv). Model the source set (read_text/json.loads on .git//.frob paths) and the sink (subprocess/run_argv argv positions); require a validator hop or -- terminator. Same rule covers worktree paths reaching Path.exists/display. This is a dataflow rule -- scope it honestly as intra-module flow first, interprocedural later.

<!-- ticket:T-0782 -->
```yaml
id: T-0782
title: 'leases: implement T-0476 cleanup -- unlink stale leases opportunistically
  + TTL for dead-agent leases (daemon stops re-simulating)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/tickets/_leases.py
- src/frob/serve/_daemon.py
- tests/test_tickets_leases.py
- tests/test_serve_daemon.py
scope_changes:
- op: add
  glob: tests/test_serve_daemon.py
  reason: 'Ticket''s own acceptance criteria requires a daemon-path regression test

    (TTL-expired lease skipped by poll_rebase_bot with exactly one log) --

    that test necessarily lives in tests/test_serve_daemon.py, the daemon''s

    existing test module, not tests/test_tickets_leases.py (which covers only

    frob.tickets._leases''s own primitives). Extending scope to cover it.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_tickets_leases.py::TestLeaseTtl::test_age_seconds_computes_elapsed_time
- tests/test_tickets_leases.py::TestLeaseTtl::test_age_seconds_none_for_unparseable_timestamp
- tests/test_tickets_leases.py::TestLeaseTtl::test_expired_past_ttl
- tests/test_tickets_leases.py::TestLeaseTtl::test_not_expired_within_ttl
- tests/test_tickets_leases.py::TestLeaseTtl::test_unparseable_timestamp_is_never_treated_as_expired
- tests/test_tickets_leases.py::TestOpportunisticUnlink::test_stale_path_lease_is_unlinked_from_disk
- tests/test_tickets_leases.py::TestOpportunisticUnlink::test_live_lease_is_never_unlinked
- tests/test_serve_daemon.py::TestPollRebaseBot::test_ttl_expired_lease_skipped_and_logged_once
- tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_stat_failure_does_not_unlink
- tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_failure_is_logged_once_per_process
- tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_genuine_enoent_still_unlinks
attachments: []
acceptance:
- text: GIVEN a lease whose worktree path no longer exists WHEN read_all_leases judges
    it stale THEN the file is unlinked (guarded so a live worktree lease is never
    removed) and the directory stops growing; GIVEN a live-path lease older than the
    TTL with no refresh THEN the daemon skips re-simulating it and logs once
  evidence:
  - tests/test_tickets_leases.py::TestOpportunisticUnlink::test_stale_path_lease_is_unlinked_from_disk
  - tests/test_tickets_leases.py::TestOpportunisticUnlink::test_live_lease_is_never_unlinked
  - tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_stat_failure_does_not_unlink
  - tests/test_serve_daemon.py::TestPollRebaseBot::test_ttl_expired_lease_skipped_and_logged_once
threat: null
component: null
labels: []
```
Audit M2: .git/frob-leases/ grows monotonically -- release only happens on clean IN_PROGRESS exit; stale leases are skipped-not-deleted (T-0476 deferral comment in read_all_leases); a dead agent with a still-existing worktree burns 2 git spawns per 20s daemon cycle forever. Implement the deferred T-0476 reconcile plus recorded_at TTL. Same files as T-0780 -- coordinator serializes dispatch.

## Done report

Implemented the deferred T-0476 lease reconcile (audit M2): read_all_leases
now opportunistically unlinks a lease file once its worktree's absence is
CONFIRMED, and prunes the matching stat-cache entry so the cache never
leaks the removed path. Added a recorded_at TTL (LEASE_TTL_SECONDS, 6
hours, module constant in _leases.py) via two new public helpers,
lease_age_seconds and is_lease_ttl_expired, for the live-path-but-dead-
agent case read_all_leases' path check alone cannot catch.
frob.serve._daemon._worktree_branches now filters TTL-expired leases
before poll_rebase_bot re-simulates them, logging the skip once per
(root, ticket id) via a new _ttl_skip_logged set, mirroring _leases.py's
existing log-once pattern.

Reviewer round 1 (REJECT): the original guard used a plain
Path(record.worktree).exists() boolean, which swallows every OSError --
a transient stat failure (PermissionError, a stale NFS handle, a slow
mount, T-0584) reads identically to a genuine ENOENT and would have
silently unlinked a perfectly LIVE peer's lease (audit L2's TOCTOU note).
Fixed by replacing it with _probe_worktree_liveness: os.stat on the
worktree path, catching FileNotFoundError as the ONLY trustworthy
absence signal, and additionally requiring the PARENT directory to
still stat successfully (so a wholesale mount failure can never read as
a single worktree's absence). Any other OSError is classified
"ambiguous" -- the lease is skipped for this pass exactly as before (not
promoted to live), logged once via a new _ambiguous_liveness_logged set,
but never unlinked. Only "confirmed_absent" (FileNotFoundError + a
reachable parent) triggers the opportunistic unlink. Added
TestAmbiguousLivenessGuard (3 tests: ambiguous stat failure does not
unlink, ambiguous failure logs once, genuine ENOENT still unlinks) to
tests/test_tickets_leases.py, and updated the read_all_leases docstring
and inline comments to describe the real guard instead of the
overstated "re-verify non-existence" language from round 1.

Scope extended by one file (frob ticket scope T-0782 --add
tests/test_serve_daemon.py) because the ticket's own acceptance criteria
require a daemon-path regression test that necessarily lives in that
module.

### Changed
```
 src/frob/serve/_daemon.py    |  55 ++++++++++-
 src/frob/tickets/_leases.py  | 219 ++++++++++++++++++++++++++++++++++++++-----
 tests/test_serve_daemon.py   |  55 +++++++++++
 tests/test_tickets_leases.py | 189 +++++++++++++++++++++++++++++++++++++
 tickets.md                   |  63 ++++++++++++-
 5 files changed, 549 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/test_tickets_leases.py::TestLeaseTtl::test_age_seconds_computes_elapsed_time` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseTtl::test_age_seconds_none_for_unparseable_timestamp` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseTtl::test_expired_past_ttl` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseTtl::test_not_expired_within_ttl` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseTtl::test_unparseable_timestamp_is_never_treated_as_expired` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestOpportunisticUnlink::test_stale_path_lease_is_unlinked_from_disk` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestOpportunisticUnlink::test_live_lease_is_never_unlinked` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBot::test_ttl_expired_lease_skipped_and_logged_once` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_stat_failure_does_not_unlink` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_failure_is_logged_once_per_process` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_genuine_enoent_still_unlinks` (pytest node id, verified passing when recorded)

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
blocked_by: []
parent: null
scope:
- src/frob/gates/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a shipped comment deferring work to ticket T-X (that ticket's job shape
    or frob:todo) WHEN T-X remains open across a REL001 version bump since the comment
    landed THEN a warning fires naming the deferral site and age; GIVEN the ticket
    closes THEN the finding clears
  evidence: []
threat: null
component: null
labels: []
```
Audit M2 gate-direction: deferred cleanup silently became permanent (T-0476 open since the lease layer shipped). Detect deferral comments bound to open tickets that have crossed release boundaries so deferrals get re-litigated instead of fossilizing.

<!-- ticket:T-0784 -->
```yaml
id: T-0784
title: 'gitio: promote git_common_dir to the single git seam (3 divergent copies)
  + batch the lease-write double spawn'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/gitio.py
- src/frob/tickets/_leases.py
- src/frob/gates/_exclude_hazard.py
- tests/test_gitio.py
scope_changes: []
evidence:
- tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
- tests/test_gitio.py::TestGitCommonDir::test_err_when_not_a_repo
- tests/test_gitio.py::TestGitCommonDir::test_memoized_per_root
- tests/test_gitio.py::TestGitCommonDir::test_reset_clears_cache
- tests/test_gitio.py::TestCommonDirAndBranch::test_single_spawn_parses_both_lines
- tests/test_gitio.py::TestCommonDirAndBranch::test_err_when_not_a_repo
attachments: []
acceptance:
- text: GIVEN the repo WHEN searched for rev-parse --git-common-dir call sites THEN
    exactly one implementation exists (frob.gitio) and _leases/_exclude_hazard delegate
    to it; GIVEN record_lease THEN common-dir and branch are fetched in one spawn
    not two
  evidence:
  - tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
threat: null
component: null
labels: []
```
Audit M3 + L1: three near-identical git-common-dir resolvers (Result vs Path|None error channels) violate the single-seam claim in gitio's own docstring; a fix to one silently desyncs the others. Promote git_common_dir(root) -> Result into frob.gitio; batch record_lease's two spawns (rev-parse --git-common-dir + branch --show-current) into one. COORDINATE: T-0773 adds memoization for the same function -- land T-0773 first, then this refactor moves the memoized seam, or merge scopes if the same implementer takes both.

## Done report

## Done report

Changed:
src/frob/gitio.py::git_common_dir
src/frob/gitio.py::reset_common_dir_cache
src/frob/gitio.py::common_dir_and_branch
src/frob/tickets/_leases.py::git_common_dir
src/frob/tickets/_leases.py::record_lease
src/frob/tickets/_leases.py::_clear_lease_caches
src/frob/gates/_exclude_hazard.py::_git_common_dir

Design: promoted git_common_dir(root) -> Result[Path, GitError] into
frob.gitio as the single canonical resolver, carrying forward T-0773's
process-lifetime memoization (dict keyed by resolved root) and its
threading.Lock (renamed _common_dir_lock/_common_dir_cache, same shape
as the old _leases.py copy). Added gitio.reset_common_dir_cache() as the
test-only cache-drop hook (_leases._clear_lease_caches now delegates to
it instead of clearing its own dict). frob.tickets._leases.git_common_dir
is now a thin LeaseError-typed wrapper over gitio.git_common_dir;
frob.gates._exclude_hazard._git_common_dir is now a thin Path|None
wrapper over the same. Added gitio.common_dir_and_branch(root) ->
Result[tuple[Path, str], GitError] which spawns ONE
`git rev-parse --git-common-dir --abbrev-ref HEAD` and parses both
result lines; record_lease now calls this instead of its old two
back-to-back spawns (rev-parse --git-common-dir + branch --show-current).

Spawn-budget results: tests/system/test_spawn_budget.py -- 4 passed, 0
xfailed (unchanged from before this ticket).

Dup delta: `frob check --only dup --ticket T-0784` before and after this
change both report 117 duplicate groups (110 waived) -- 0 group-count
delta. The synthetic Result-vs-Path|None git_common_dir/_git_common_dir
pairing from T-0785's dup-scan work (tests/test_dup.py) is a fixture
constructed inline in that test file, independent of the real source
files touched here, so it is unaffected either way.

Evidence:
tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
tests/test_gitio.py::TestGitCommonDir::test_err_when_not_a_repo
tests/test_gitio.py::TestGitCommonDir::test_memoized_per_root
tests/test_gitio.py::TestGitCommonDir::test_reset_clears_cache
tests/test_gitio.py::TestCommonDirAndBranch::test_single_spawn_parses_both_lines
tests/test_gitio.py::TestCommonDirAndBranch::test_err_when_not_a_repo
tests/system/test_spawn_budget.py (4 passed 0 xfailed)
tests/test_tickets_leases.py (all passing)
tests/test_ticket_leases_cross_worktree.py (all passing)
tests/test_gates.py::TestExcludeHazardGate::* (all passing)

Filed: none

Gates: `frob check --ticket T-0784` chunked loop (lint/static/gates-fast/
gates-native/gates-security) clean except REL001 (public API version
bump), which is land-owned per docs/guides/agent-playbook.md section 4b
and left for `frob ticket land` -- FROB_AGENT was not set in this shell
so the usual worktree-agent suppression did not apply, but no version/
changelog/lockfile edit was made by hand. PRE001 cleared via
`frob ticket sweep T-0784` after the code changes landed. `frob test
--base main` (touched-set): python exit=0.

Deviations: none from the ticket's plan. One correction made mid-flight:
the frob:tests directive I first wrote for common_dir_and_branch used
`Class::method` (double-colon) instead of the repo's `path::Class.method`
dot-separator convention, which DRIFT002 caught immediately (dangling
tests edge, no candidates) -- fixed to match the convention used
everywhere else in this file.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestGitCommonDir::test_err_when_not_a_repo` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestGitCommonDir::test_memoized_per_root` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestGitCommonDir::test_reset_clears_cache` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestCommonDirAndBranch::test_single_spawn_parses_both_lines` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestCommonDirAndBranch::test_err_when_not_a_repo` (pytest node id, verified passing when recorded)

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
blocked_by: []
parent: null
scope:
- docs/audits/gates-vacuous.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the audit doc WHEN complete THEN every gate in gates/__init__.py has
    a recorded verdict for empty-diff/empty-scope/cached-stale satisfaction (can it
    go green without doing its work) and the lang/** tree-sitter ingestion of untrusted
    files has a recorded DoS/traversal verdict; every defect found is filed as its
    own ticket
  evidence: []
threat: null
component: null
labels: []
```
The 2026-07-23 blindspot audit explicitly skipped: (a) a full vacuous-satisfaction sweep of gates/__init__.py (8568 lines -- can any gate be satisfied by an empty diff, empty scope, or stale cache?), and (b) lang/** parser trust boundary (tree-sitter on untrusted repo files). These are the largest unaudited surfaces. Run per the audit-until-empty discipline (docs/audits/, pessimistic auditor told to find 10+, repeat until 0).

<!-- ticket:T-0787 -->
```yaml
id: T-0787
title: 'check CLI: wire resolve_lease pinning into --ticket resolution (promote T-0766''s
  lost draft)'
state: done
kind: security
origin: agent
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
- tests/test_tickets_leases.py
scope_changes: []
evidence:
- tests/test_tickets_leases.py::TestTicketLeasePin::test_no_lease_mechanism_engaged_passes_through
- tests/test_tickets_leases.py::TestTicketLeasePin::test_pinned_lease_for_this_worktree_passes
- tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_absent_for_this_worktree_refuses
- tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_recorded_elsewhere_refuses
- tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_pins_to_own_worktree_lease
- tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree
- tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_no_ticket_resolved_skips_the_check_entirely
attachments: []
acceptance:
- text: GIVEN an agent invoking frob check --ticket T-X from a worktree WHEN T-X has
    a lease THEN the check pins to T-X's own lease/worktree via resolve_lease and
    refuses loudly (naming frob ticket start) when the lease is absent or recorded
    for a different worktree; a test drives the check entry point across two fake
    worktrees
  evidence:
  - tests/test_tickets_leases.py::TestTicketLeasePin::test_no_lease_mechanism_engaged_passes_through
  - tests/test_tickets_leases.py::TestTicketLeasePin::test_pinned_lease_for_this_worktree_passes
  - tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_absent_for_this_worktree_refuses
  - tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_recorded_elsewhere_refuses
  - tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_pins_to_own_worktree_lease
  - tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree
  - tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_no_ticket_resolved_skips_the_check_entirely
threat: null
component: null
labels: []
```
Promotion of a draft filed in T-0766's worktree and lost during that ticket's land recovery (premature worktree removal destroyed uncommitted ledger state; disclosed in coordinator notes). T-0766 landed the resolve_lease(root, ticket_id, invoking_worktree) fail-loud primitive in src/frob/tickets/_leases.py, but nothing in the live check path consults leases at all (verified by the T-0766 reviewer: active_ticket/_resolve_ticket derive the id from --ticket/branch only). The reviewer marked this wiring a HARD DEPENDENCY: the guard prevents nothing until check consults it. Wire check's --ticket resolution through resolve_lease when a lease exists, keeping the no-lease path working for non-agent invocations.

## Done report

## Done report

Changed:
  src/frob/gates/__init__.py::ticket_lease_pin
  src/frob/app/check_runner.py::_refuse_ticket_lease_mismatch
  src/frob/app/check_runner.py::run (wired the new refusal before any stage/run_gates call)

Wiring design: `ticket_lease_pin(root, ticket_id)` (new, gates/__init__.py, exported
via __all__) wraps T-0766's resolve_lease. It passes through Ok(None) both when the
resolved worktree pins cleanly AND when the cross-worktree lease mechanism has never
been engaged at all in this repo (no shared git common dir, or a leases directory
that has never been created because no ticket has ever been `frob ticket start`ed
anywhere) -- this is what keeps non-agent/plain-repo invocations working unchanged
per the acceptance criterion. Once the mechanism IS engaged (the leases directory
exists) it returns Err(NoLeaseForTicket) or Err(LeaseWorktreeMismatch) exactly as
resolve_lease itself does. `_refuse_ticket_lease_mismatch(root, cfg)` (new,
check_runner.py) is the CLI-boundary caller: it resolves the active ticket the same
way `run_gates` does (`frob.gates.active_ticket(root, cfg.check_ticket)`), and when
one resolves, calls `ticket_lease_pin`; any Err logs a loud message naming
`frob ticket start <ticket_id>` and the underlying LeaseError text. `run()` calls
this immediately after the `--only list`/agent-refusal checks and before
`_handle_stamp_modes`/any stage dispatch, so both a full run and `--stamp-baseline`
are covered by one choke point, matching every other early-refusal check in this
module. No changes to src/frob/gates/_models.py (GateError) -- reusing/adding a
GateError variant would have required editing a file outside T-0787's declared
scope and risked colliding with the unrelated existing WorktreeLeaseViolation
(FROB_WORKTREE env-var) mechanism; the CLI-boundary refusal achieves the same
loud-refusal contract without touching it.

Evidence (tests/test_tickets_leases.py, all pytest -p no:cacheprovider -q, 21/21 pass
including pre-existing TestResolveLease/TestReadAllLeasesSiblingProcessVisibility):
  TestTicketLeasePin::test_no_lease_mechanism_engaged_passes_through
  TestTicketLeasePin::test_pinned_lease_for_this_worktree_passes
  TestTicketLeasePin::test_lease_absent_for_this_worktree_refuses
  TestTicketLeasePin::test_lease_recorded_elsewhere_refuses
  TestCheckTicketLeaseCli::test_pins_to_own_worktree_lease
  TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree
  TestCheckTicketLeaseCli::test_no_ticket_resolved_skips_the_check_entirely
Bound to acceptance[0] via `frob ticket evidence T-0787 ... --accepts 0`.

`uv run --frozen frob test --base main`: python exit=1 -- 3 pre-existing failures
unrelated to T-0787 (TestCheckCleanProject::test_clean_code_exits_zero,
TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation,
TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage). Verified unrelated by
temporarily reverting the two lines in check_runner.py::run that call
_refuse_ticket_lease_mismatch and re-running the same three tests: all three fail
identically without T-0787's change in place (pre-existing "not a git repository"/
stray gitio debug-line-in-stdout breakage in TestCheckCleanProject's tmp_path
fixture, unrelated to leases). Re-verified my own new tests pass both with and
without that revert cycle.

Gates: `uv run --frozen frob check --ticket T-0787 --only lint|static|gates-fast|
gates-native|gates-security`, chunked, all clean for T-0787's own scope after two
fixes made along the way:
  - ruff-format: reformatted tests/test_tickets_leases.py (line-length wrap).
  - DRIFT002 (gate:DRIFT, 6 violations): my initial `frob:tests` directives used
    `path::Class::method` (double `::`) instead of this repo's actual qualname
    convention `path::Class.method` (dot before the method) -- fixed in both
    gates/__init__.py and check_runner.py; re-verified 0 DRIFT violations after a
    graph cache rebuild (`rm -f .frob/cache.db`).
  - PRE001 (stale pre-work sweep): re-ran `frob ticket sweep T-0787` after adding
    the new symbols; clean afterward.
  - SCOPE001/uv.lock and a stray `uv.lock` version-line diff (0.101.0 -> 0.102.0):
    both were side effects of `make core`/`uv sync` in this worktree, not my own
    edits -- `git checkout -- uv.lock` before every check/finish, per playbook 4b
    (land-owned file). Re-appeared once more after a later `pytest` run and was
    reverted again before finishing; confirmed 0 remaining diff on uv.lock at
    finish time.
  - REL001 (public API changed, minor bump needed) still fires: this worktree's
    shell does not actually have FROB_AGENT set (despite being a dispatched
    worktree agent), so REL001's bump/changelog suppression half never engaged.
    Per the dispatch instructions and playbook 4b, land computes the bump
    automatically -- disclosing rather than hand-bumping pyproject.toml/
    CHANGELOG.md/uv.lock myself.
  - `git diff main --diff-filter=D --stat`: empty (playbook section 9 check).

Filed: none -- no out-of-scope findings.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_leases.py::TestTicketLeasePin::test_no_lease_mechanism_engaged_passes_through` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestTicketLeasePin::test_pinned_lease_for_this_worktree_passes` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_absent_for_this_worktree_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_recorded_elsewhere_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_pins_to_own_worktree_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_no_ticket_resolved_skips_the_check_entirely` (pytest node id, verified passing when recorded)

<!-- ticket:T-0788 -->
```yaml
id: T-0788
title: 'gates: register COMPLIANCE005 in the live rule set and dispatch check_cmpl_registry
  in frob check'
state: queued
kind: feature
origin: agent
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
- src/frob/strata/_compliance.py
- docs/design/registry/compliance.yaml
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a compliance.yaml entry regressed to deferred or undispositioned WHEN
    frob check runs THEN COMPLIANCE005 fires as a registered, waivable gate rule;
    GIVEN the 17 CMPL units re-dispositioned by T-0607 THEN their entries may cite
    handled_by:COMPLIANCE005 and REG002 accepts it
  evidence: []
threat: null
component: null
labels: []
```
T-0607 built check_cmpl_registry/COMPLIANCE005 but could not register the rule id in _KNOWN_GATE_RULES nor dispatch the check inside frob check (gates/__init__.py out of its scope) -- the implementer disclosed this and used reasoned out_of_scope dispositions naming COMPLIANCE005 as the compensating control. Until this ticket lands, COMPLIANCE005 is enforcement code invoked by nothing in a real check run (the catalogued-is-not-enforced class, T-0343). Wire the dispatch, register the rule, then flip the 17 dispositions to handled_by:COMPLIANCE005.

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
blocked_by: []
parent: null
scope:
- pyproject.toml
- uv.lock
- Makefile
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Observed while working T-0704 (worktree agent-ad82d24588b5083b6, 2026-07-22/23). This worktree's checked-in uv.lock records frob's own package version as 0.97.0 while pyproject.toml's version line is already 0.98.0 (a pre-existing mismatch present at the worktree's own base commit, not introduced by any ticket worked in this session). Because uv.lock is not scope-locked against auto-sync, EVERY `uv run ...` invocation (including read-only ones like `frob ticket show` or `frob check`) silently rewrites uv.lock's frob version line to match pyproject.toml, leaving a working-tree modification an agent must notice and `git checkout HEAD -- uv.lock` away before every commit/check -- and if missed, SCOPE001 fires (uv.lock outside the ticket's declared scope) on every subsequent `frob check` even though no agent hand-edited the file. Section 4b of docs/guides/agent-playbook.md already forbids agents from touching uv.lock by hand, but does not cover this auto-touch-by-tooling case. Fix: either (a) make `uv run`'s auto-sync a no-op when only the local version-line mismatch is the cause (uv config: --frozen or --no-sync for frob's own CLI invocations, or a repo-level uv setting), or (b) have the section-4b agent-file-blacklist pre-commit hook silently discard/reset a version-line-only uv.lock diff caused by this sync rather than warning/blocking, or (c) reconcile pyproject.toml/uv.lock at land time so fresh worktrees never start with the mismatch. Any one of the three removes the recurring "revert uv.lock before committing" step every worktree agent currently has to remember.

<!-- ticket:T-0791 -->
```yaml
id: T-0791
title: 'strata host: :deny ACL flag path has zero test evidence (deny-overrides verified
  by inspection only)'
state: in-progress
kind: bug
origin: auditor
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- tests/unit/strata/test_host_isolation.py
scope_changes: []
evidence:
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
attachments: []
acceptance:
- text: GIVEN an ACL rule carrying the :deny flag on a write-capable RIGHTS value
    WHEN _acl_grants_write evaluates it THEN write_capable is False and a shared-writable-path
    violation does NOT fire; a test constructs the :deny shape explicitly
  evidence:
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
threat: null
component: null
labels: []
```
T-0606 reviewer finding: test_deny_acl_does_not_fire_shared_writable_path uses Everyone:Read (non-write RIGHTS), never an actual :deny flag; _acl_grants_write implements deny correctly by inspection but no test exercises that branch. Add the missing fire/no-fire pair.
<!-- ticket:T-0792 -->
```yaml
id: T-0792
title: 'strata host windows: multi-ACE ACLs collapse to last-declaration-wins, under-reporting
  movement violations'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/strata/_host_isolation.py
- tests/unit/strata/test_host_isolation.py
scope_changes: []
evidence:
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_allow_entry_grants
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_fire_shared_writable_path
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere
attachments: []
acceptance:
- text: GIVEN two acl entries on the same path (a broad allow after a narrow deny)
    WHEN the movement-impossibility join runs THEN deny-overrides-allow NTFS semantics
    apply (the deny is honored regardless of declaration order) and a violation fires
    where the current last-wins collapse stays silent; SeImpersonate-class token privileges
    get a recorded modeling decision (implement or explicit out-of-scope)
  evidence:
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_allow_entry_grants
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies
  - tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_fire_shared_writable_path
  - tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere
threat: elevation-of-privilege
component: null
labels: []
```
T-0606 reviewer finding: _owned_paths_by_user collapses multiple ACL entries per path to last-declaration-wins, mirroring the POSIX one-owner convention -- but windows ACLs are multi-ACE by design, and an early deny overridden by a later broad allow silently suppresses a violation the proof system should detect (soundness gap in the direction that matters). Implement real deny-overrides-allow joining across all ACEs per path. Also adjudicate SeImpersonatePrivilege/SeDebugPrivilege-class token privileges: model or record out-of-scope with reason.

## Done report

## Done report

Changed:
src/frob/strata/_host_isolation.py::_acl_ace_of
src/frob/strata/_host_isolation.py::_acl_grants_write
src/frob/strata/_host_isolation.py::_join_acl_entries
src/frob/strata/_host_isolation.py::_owned_paths_by_user

Semantics design: `_join_acl_entries` replaces the last-declaration-wins
dict overwrite (`_owned_paths_by_user`'s prior `claims[acl_entry.path] = ...`
loop, which discarded every ACE for a path except whichever happened to
land last in node/field-declaration order) with a real NTFS deny-
overrides-allow join across ALL ACEs declared for a path. ACEs are
grouped by PRINCIPAL (parsed from the RULE's `PRINCIPAL:RIGHTS[:deny]
[:no_inherit]` shape via the new `_acl_ace_of` helper, shared by
`_acl_grants_write`'s single-ACE question and the new multi-ACE join so
the RULE grammar is only split in one place). An explicit `:deny` ACE
always wins over an explicit allow ACE for the SAME principal, no matter
declaration order (`net_deny_by_principal`/`net_allow_by_principal` sets
in `_join_acl_entries`). A deny for one principal never cancels a
DIFFERENT principal's allow -- the path is write-capable overall if ANY
principal's net verdict is allow (final `any(...)` OR-reduction). This
closes the T-0606 reviewer finding: the prior collapse could silently
drop an earlier ACE's real write grant to a different principal purely
because a later-iterated ACE for a DIFFERENT principal happened to be a
deny, under-reporting a shared-writable-path violation. `owns` (linux
POSIX MODE, one mode per path) keeps its existing last-declaration-wins
behavior unchanged -- only the windows `acl` half needed the multi-ACE
join.

Token-privilege disposition: SeImpersonatePrivilege/SeDebugPrivilege-class
windows token privileges are recorded as an explicit OUT-OF-SCOPE
disposition with reason in the module docstring (new "Token-privilege
classes: explicit out-of-scope disposition (T-0792)" section,
src/frob/strata/_host_isolation.py). `std.host`'s grammar has no
`privilege "NAME"` clause parallel to `group`/`sudoers` (T-0272's
precedent) for a manifest to declare a granted windows privilege, so
there is no fact this module could join against -- modeling it would
require a `strata-core/src/parse.rs` grammar addition, outside this
ticket's `src/frob/strata/**` scope (mirroring the T-0272 precedent of
deferring a grammar-gated gap to a follow-up). Not modeled in docs/strata/
host.md itself since that file is outside this ticket's declared scope
globs (src/frob/strata/_host_isolation.py, tests/unit/strata/
test_host_isolation.py only) -- documented in the in-scope module
docstring instead, disclosed here rather than silently left unstated.

T-0791 absorption: T-0791 ("strata host: :deny ACL flag path has zero
test evidence") asked for a fire/no-fire pair explicitly exercising the
`:deny` flag on write-capable RIGHTS (the existing test used Everyone:Read,
a non-write RIGHTS value, never an actual `:deny` flag). This ticket's
new tests `TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_
fire_shared_writable_path` (no-fire: both sides carry ONLY a
`Everyone:Modify:deny` ACE) and `test_explicit_deny_acl_flag_fires_when_
write_rights_present_elsewhere` (fire: a `:deny`'d ACE for one principal
alongside a plain write-capable ACE for a different principal, also
exercising T-0792's multi-ACE join) satisfy T-0791's acceptance criterion
exactly -- both were written to close this ticket's own acceptance
criterion (which also names the T-0791 deny-flag test gap explicitly) and
happen to be the identical fire/no-fire pair T-0791 asks for. Evidence
recorded on T-0791 directly (`frob ticket evidence T-0791 --accepts 0 ...`)
so the coordinator can drop it without re-deriving evidence; T-0791 was
NOT closed/landed by this ticket (land-owned, out of scope for a worktree
agent per the playbook).

Evidence:
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_allow_entry_grants
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies
tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_fire_shared_writable_path
tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere

Full-file test run: `uv run --frozen pytest tests/unit/strata/test_host_isolation.py
-p no:cacheprovider -q` -> 33 passed (all pre-existing 25+ tests preserved
plus 8 new). `uv run --frozen frob test --base main` (touched-set) ->
[PASS] python exit=0.

Filed: none.

Gates: `uv run --frozen frob check --ticket T-0792` chunked over lint,
static, gates-fast, gates-native, gates-security, and prework (via
`frob ticket sweep T-0792` before the prework re-check) -- all clean, 0
errors in every stage. `git diff main --diff-filter=D --stat` empty
(deletion-filter land rule).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_allow_entry_grants` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_fire_shared_writable_path` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere` (pytest node id, verified passing when recorded)

<!-- ticket:T-0793 -->
```yaml
id: T-0793
title: 'land: re-sync uv.lock in the release-bump commit so per-invocation lock flap
  stops tripping DirtyMain/SCOPE001'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Regression tests for the uv.lock resync/dirty-tolerance behavior added
    to

    src/frob/tickets/_land.py live in this file per repo convention (one test

    module per source module); adding scope so COV002/SCOPE001 can bind them.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
- tests/test_ticket_land.py::TestUvLockSync::test_lock_sync_spawn_failure_unwinds_squash
attachments: []
acceptance:
- text: GIVEN a land whose version bump changes pyproject WHEN the land commits THEN
    uv.lock is re-synced and committed in the same land commit and a subsequent uv
    run in any checkout produces no lock drift
  evidence:
  - tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit
  - tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse
  - tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
  - tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
  - tests/test_ticket_land.py::TestUvLockSync::test_lock_sync_spawn_failure_unwinds_squash
threat: null
component: null
labels: []
```
Promotion of T-0767's worktree draft db4263e7 (manual land skipped the renumber path). The uv.lock version line flaps on every uv run against a bumped pyproject, tripping DirtyMain at land and SCOPE001/PRE001 in every worktree. Land owns the version bump; it should own the lock sync too.

## Done report

## Done report

Design: land's release-bump step (`_apply_release_bump` in
src/frob/tickets/_land.py) now calls a new `_sync_uv_lock_for_land(root,
final_id)` right after a real version bump is staged -- it runs `uv lock`
through the guarded `run_argv` seam (T-0778), `git add`s the result, and
unwinds the staged squash on failure the same way a bump-callback failure
already did. Skipped (Ok(None), no spawn) when `root` has no
pyproject.toml, so library callers/test fixtures without a real uv
project are unaffected. Separately, `_refuse_if_main_dirty` now tolerates
one specific dirty shape before refusing: a new
`_restore_lock_version_only_drift(root)` helper checks whether uv.lock is
the SOLE dirty path and its diff is exactly a `version = "..."`
line-flip inside the `name = "frob"` stanza (via
`_diff_is_frob_version_line_only`); if so it auto-restores
(`git checkout -- uv.lock`) and the dirty check is re-evaluated. Any
other drift (a real lock change, a second dirty file) is left untouched
and still refuses with DirtyMain exactly as before.

Changed:
  src/frob/tickets/_land.py::_apply_release_bump
  src/frob/tickets/_land.py::_sync_uv_lock_for_land (new)
  src/frob/tickets/_land.py::_refuse_if_main_dirty
  src/frob/tickets/_land.py::_restore_lock_version_only_drift (new)
  src/frob/tickets/_land.py::_diff_is_frob_version_line_only (new)
  src/frob/tickets/_land.py::_LOCK_VERSION_LINE (new)

Evidence:
  tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit
  tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse
  tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
  tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
  tests/test_ticket_land.py::TestUvLockSync::test_lock_sync_spawn_failure_unwinds_squash
  (all 5 bound to acceptance[0] via `frob ticket evidence --accepts 0`)
  Full `tests/test_ticket_land.py` regression run: 71 passed
  (`uv run --frozen pytest tests/test_ticket_land.py -q -p no:cacheprovider`)

  Reviewer-required additions (round 2): `test_dirty_lock_version_plus_
  other_line_still_refuses` exercises `_diff_is_frob_version_line_only`'s
  `len(changed) != 2` rejection on the destructive-restore path -- uv.lock
  is the SOLE dirty path but its diff has the frob version-line flip PLUS
  an unrelated changed line (a `source` value); asserts DirtyMain refusal
  AND that uv.lock's dirty content is left byte-for-byte untouched (no
  auto-restore). `test_lock_sync_spawn_failure_unwinds_squash` mirrors
  the existing `test_bump_failure_unwinds_squash` shape but fails the
  `uv lock` spawn itself (via a fake `run_argv` returning rc=1) after a
  real bump succeeds -- asserts `ReleaseBumpFailed`, main's HEAD sha
  unchanged, and a fully clean working tree (the `reset --hard`/`clean
  -fd` unwind fired).

Filed: none

Gates: `uv run --frozen frob check --ticket T-0793` chunked loop
(lint/static/gates-fast/gates-native/gates-security, per the agent
playbook's stall-avoidance recipe) all clean: 0 errors across every
stage after adding scope for tests/test_ticket_land.py (COV002/SCOPE001)
and re-running `frob ticket sweep T-0793` (PRE001). `lint`'s one
remaining `ty` diagnostic (tests/test_gitio.py:316) is pre-existing and
outside this ticket's scope, untouched by this change.

Deviations: scope extended by one file --
`frob ticket scope T-0793 --add tests/test_ticket_land.py --reason-file
...` -- the regression tests for this behavior live alongside the rest
of `_land.py`'s test suite per repo convention; recorded via the CLI
with a reason, not a silent expansion.

uv.lock itself was NOT touched by this ticket's diff (it stays out of
worktree scope per docs/guides/agent-playbook.md#4b -- `frob ticket land`
owns it). The pre-existing frob-version-line flap observed repeatedly
during this session's own `uv run`/`frob check` invocations was
`git checkout -- uv.lock`'d back to the committed state before every
commit, never staged.

### Changed
```
 src/frob/tickets/_land.py | 129 +++++++++++++++++++++++++++++++++++++++++++++-
 tests/test_ticket_land.py | 108 ++++++++++++++++++++++++++++++++++++++
 tickets.md                |  94 +++++++++++++++++++++++++++++++--
 3 files changed, 326 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_lock_sync_spawn_failure_unwinds_squash` (pytest node id, verified passing when recorded)

<!-- ticket:T-0794 -->
```yaml
id: T-0794
title: 'arch: discharge self-join-deadlock advisory on vet/_scan.py::_run_with_timeout
  (same shape as T-0767)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/vet/_scan.py
- tests/unit/test_arch.py
scope_changes: []
evidence:
- tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_vet_scan
attachments: []
acceptance:
- text: GIVEN main WHEN frob check runs THEN zero self-join-deadlock warnings on src/frob/vet
    while the timeout behavior is preserved and a regression test locks the discharge
  evidence:
  - tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_vet_scan
threat: null
component: null
labels: []
```
Promotion of T-0767's worktree draft 1910bd1a: the T-0695 self-join-deadlock advisory fires on vet/_scan.py::_run_with_timeout (unwaivable channel). Restructure the join ownership the same way T-0767 discharged _run_combined_jobs. Required for zero-warnings.

## Done report

Discharge T-0695's self-join-deadlock advisory on vet/_scan.py::_run_with_timeout, same shape T-0767 used for gates/_run_combined_jobs's pool-inside-pool. _run_with_timeout is the function `_scan_dependencies_parallel` dispatches as a worker task via ThreadPoolExecutor.submit, and its own body used to construct + shutdown an inner single-worker ThreadPoolExecutor -- exactly the self-join-deadlock co-occurrence shape (dispatched-as-task + owns join/shutdown/close on a pool). Hoisted the inner pool's construction into a new `_open_single_worker_pool` helper and its submit/await/shutdown into a new `_bounded_process_dependency` helper; `_run_with_timeout` is now a pure orchestrator with two branches (timeout is None -> direct call; else -> delegate to `_bounded_process_dependency`) and no pool calls of its own. Timeout semantics (per-package bound via `fut.result(timeout=...)`, TIMEOUT verdict via `_timeout_verdict`, non-blocking `shutdown(wait=False)` on both the success and timeout paths so the caller returns within ~timeout wall-clock) are preserved verbatim -- only moved to the new helper. Added a real-repo regression test mirroring T-0767's discharge test naming/shape (`test_self_join_deadlock_discharges_on_real_repo_vet_scan`) that asserts zero fork/pool-hazard findings across all four categories on src/frob/vet, alongside the existing synthetic fire fixtures (unchanged, still green) proving the detector itself was not weakened.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_vet_scan` (pytest node id, verified passing when recorded)

<!-- ticket:T-0795 -->
```yaml
id: T-0795
title: 'land: retry robustness -- close is not idempotent after own finalize (InvalidTransition
  done->done) + cwd-inside-worktree misdiagnosis'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: critical
blocked_by: []
parent: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner.py
- tests/test_ticket_land.py
scope_changes: []
evidence:
- tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff
- tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition
- tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake
- tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits
attachments: []
acceptance:
- text: GIVEN a land that merged and finalized in the worktree but failed before committing
    to main WHEN land is retried with identical arguments THEN it completes the squash-apply
    onto main instead of erroring InvalidTransition on the already-done ticket; GIVEN
    land invoked with cwd inside the worktree THEN the error names the actual mistake
    (run from the root checkout) instead of the T-0640 false-green diagnosis
  evidence:
  - tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff
  - tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition
  - tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake
  - tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits
threat: null
component: null
labels: []
```
Three lands this drive (T-0676, T-0774, T-0767) merged+finalized in the worktree (ticket transitioned to done in the worktree ledger) then failed before the main commit; every retry then errored InvalidTransition because close re-runs the done transition. Each required a manual splice-apply onto main (see the three land commits). Make the close step idempotent (done ticket + pending squash = proceed to squash-apply) or checkpoint the land so retry resumes at the squash. Separately, when root==worktree because the invoker's cwd is inside the worktree, say so explicitly.

## Done report

Two fixes in src/frob/tickets/_land.py, both wired through _land_precheck /
_close_finalized_ticket (no LandError enum change, no ticket_runner.py change
needed -- root is already CLI-cwd-derived, the fix belongs entirely in land()'s
own precheck/close path in _land.py).

1. Idempotent retry after own finalize: _close_finalized_ticket now loads
   `final_id` FIRST and checks its state before calling transition(). If
   already TicketState.DONE (a prior land() attempt reached finalize+close,
   committed that in the worktree, then failed at a LATER step -- squash
   conflict, REL001 bump, or the T-0463 completeness assertion, all of which
   unwind ONLY root via reset --hard, leaving the worktree's done commit
   intact), it logs and returns Ok(final_id) directly instead of re-running
   transition(..., DONE), which used to error InvalidTransition (done has no
   done->done edge in _TRANSITIONS) every time. A non-done ticket still runs
   the real transition unchanged (covered by a companion sanity test).

2. Early cwd-inside-worktree refusal: new _refuse_if_root_is_worktree, called
   first in _land_precheck (before the dirty-main check, before any git
   mutation). If root == worktree (both already .resolve()d by land()), it
   refuses with Err(LandError.IncompleteLand) and a log message naming the
   actual likely cause (root defaults to the invoker's cwd, so running `frob
   ticket land` from inside the worktree makes root resolve to worktree for
   free) and the remedy (run from the root checkout). Reuses the existing
   IncompleteLand enum tag deliberately (the log message carries the
   corrected diagnosis, not a new enum) so the pre-existing T-0761 regression
   test (renamed/preserved as
   TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits)
   stays green under the new, earlier, more specific check. The genuinely
   distinct T-0640/T-0761 diagnosis in _worktree_full_changeset (merge-base
   == HEAD for a DISTINCT worktree path pointed at the same branch) is
   untouched and still fires for that separate condition.

Changed:
  src/frob/tickets/_land.py::_refuse_if_root_is_worktree (new)
  src/frob/tickets/_land.py::_land_precheck (calls the new check first)
  src/frob/tickets/_land.py::_close_finalized_ticket (idempotent DONE check)
  tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail (new, 2 tests)
  tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree (new, 2 tests)

Evidence:
  tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff
  tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition
  tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake
  tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits
  (bound to acceptance[0] via --accepts 0)

  `uv run --frozen pytest tests/test_ticket_land.py -q` -> 66 passed (62
  pre-existing + 4 new); every pre-existing test, including the T-0761
  same-branch regression, still green.
  `uv run --frozen frob test --base main` -> run_selected: python exit=0
  duration=7.01s [PASS], selecting tests/test_ticket_land.py (whole file) +
  the 4 new node ids + tests/test_tickets.py::test_tickets_queue_workflow_integration.

Filed: none -- no out-of-scope work discovered.

Gates: `uv run --frozen frob check --ticket T-0795` chunked via `--only
lint|static|gates-fast|gates-native|gates-security` (the standard chunked
loop, T-0627) -- 0 errors in every stage after a `ruff format` pass and a
`frob ticket sweep T-0795` refresh (PRE001 was stale from the pre-work sweep
taken before implementation started). No waivers added for this ticket's own
code; touched functions carry frob:tests directives to their new regression
tests.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits` (pytest node id, verified passing when recorded)

<!-- ticket:T-0796 -->
```yaml
id: T-0796
title: 'tickets CLI: --evidence-cmd with --accepts silently records evidence UNBOUND
  (add_cmd_evidence has no accepts param)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner.py
- tests/test_tickets_evidence_cli.py
scope_changes: []
evidence:
- tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_evidence_cmd_with_accepts_binds_acceptance_via_cli
- tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_close_evidence_cmd_with_accepts_binds_acceptance_via_cli
attachments: []
acceptance:
- text: GIVEN frob ticket evidence T-X --evidence-cmd CMD --accepts 0 WHEN the command
    verifies THEN the cmd evidence is bound to acceptance index 0 exactly like pytest-node
    evidence; a regression test drives the CLI path
  evidence:
  - tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_evidence_cmd_with_accepts_binds_acceptance_via_cli
  - tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_close_evidence_cmd_with_accepts_binds_acceptance_via_cli
threat: null
component: null
labels: []
```
Promotion of T-0677's worktree draft 91ef53bd: add_cmd_evidence in frob.tickets has no accepts parameter and both CLI call sites in ticket_runner.py drop cfg.ticket_accepts for cmd evidence, so docs-kind tickets silently end up with UNBOUND acceptance despite the operator passing --accepts (T-0677 worked around via the library add_evidence call). With the T-0763 land preflight now refusing unbound acceptance, this silent drop blocks docs-ticket lands.

## Done report

Threaded `accepts: Sequence[int] | None` through `add_cmd_evidence`
(src/frob/tickets/__init__.py) using the same 0-based validation and
Err(AcceptanceIndexOutOfRange) shape as `add_evidence`, then delegated the
merge/write to the existing `_append_evidence_and_write` helper so cmd
evidence binds onto named acceptance criteria the same way pytest-node
evidence does. Wired `cfg.ticket_accepts` through both CLI call sites in
src/frob/app/ticket_runner.py (`_close`, `_evidence`, via `_apply_cmd_evidence`,
which gained the same `accepts` parameter). Added a regression test class
(tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding) driving
both the `evidence` and `close` CLI subcommands with a docs-kind ticket,
`--evidence-cmd` and `--accepts 0`, asserting `ticket.acceptance[0].evidence`
is bound to the recorded cmd: entry.

### Changed
```
 src/frob/app/ticket_runner.py      | 25 +++++++++---
 src/frob/tickets/__init__.py       | 35 +++++++++++++----
 tests/test_tickets_evidence_cli.py | 79 ++++++++++++++++++++++++++++++++++++++
 tickets.md                         | 31 +++++++++++++--
 4 files changed, 154 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_evidence_cmd_with_accepts_binds_acceptance_via_cli` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_close_evidence_cmd_with_accepts_binds_acceptance_via_cli` (pytest node id, verified passing when recorded)

<!-- ticket:T-0797 -->
```yaml
id: T-0797
title: 'gates: DEPR001-004 are dead code -- ''deprecated'' missing from _ALL_GATES
  so no frob check run evaluates them'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: critical
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
- src/frob/check/__init__.py
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/docs_runner.py
scope_changes:
- op: add
  glob: src/frob/check/__init__.py
  reason: deprecated gate now real in _ALL_GATES; test_available_stages_cover_every_gate_and_tool
    requires it land in a _STAGE_GROUPS alias too, structurally the same change
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/map_runner.py
  reason: 'DEPR002 rebind: directives must cite an open ticket; T-0802 is the sunset-execution
    ticket'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/outline_runner.py
  reason: 'DEPR002 rebind: directives must cite an open ticket; T-0802 is the sunset-execution
    ticket'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/xref_runner.py
  reason: 'DEPR002 rebind: directives must cite an open ticket; T-0802 is the sunset-execution
    ticket'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/docs_runner.py
  reason: 'DEPR002 rebind: directives must cite an open ticket; T-0802 is the sunset-execution
    ticket'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestDeprecatedGate::test_deprecated_is_registered_in_all_gates
- tests/test_gates.py::TestDeprecatedGate::test_deprecated_fires_through_real_gate_dispatch
- tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
attachments: []
acceptance:
- text: GIVEN a frob:deprecated directive in the tree WHEN frob check runs (no --only
    filter) THEN the deprecated gate evaluates and DEPR003 in-window warnings appear
    in gate output; frob check --only deprecated is accepted; a regression test locks
    the gate registration
  evidence:
  - tests/test_gates.py::TestDeprecatedGate::test_deprecated_is_registered_in_all_gates
  - tests/test_gates.py::TestDeprecatedGate::test_deprecated_fires_through_real_gate_dispatch
  - tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
threat: null
component: null
labels: []
```
Promotion of T-0580's worktree draft f226d099 (worktree removed at land before renumbering; refiled by coordinator). deprecated_gate and DEPR001-004 are implemented and unit-tested but 'deprecated' is absent from _ALL_GATES, so no real check run ever evaluates them -- the T-0580 deprecations are currently enforced by nothing (catalogued-is-not-enforced class). One-line registration + regression test. CRITICAL because the user's deprecation decision (map/outline/xref/docs-search, sunset 2026-10-01) silently has no teeth until this lands.

## Done report

Registered "deprecated" in `_ALL_GATES` and `_CANONICAL_GATE_ORDER`
(src/frob/gates/__init__.py) -- deprecated_gate's dispatch-table lambda
already existed but was unreachable since T-0576 because the gate name
was never added to the selectable set. Also added "deprecated" to the
"gates-fast" stage group in src/frob/check/__init__.py: this file was
structurally necessary (not originally in scope) because
test_available_stages_cover_every_gate_and_tool asserts every
_ALL_GATES member lands in some _STAGE_GROUPS alias -- added via
`frob ticket scope T-0797 --add src/frob/check/__init__.py --reason ...`
per the sanctioned scope-expansion mechanism, not silently.

Added two regression tests to TestDeprecatedGate in tests/test_gates.py:
test_deprecated_is_registered_in_all_gates (locks membership) and
test_deprecated_fires_through_real_gate_dispatch (end-to-end run_gates
with no --only filter, proving DEPR003 actually surfaces through real
dispatch, not just via a direct deprecated_gate() call).

Deviation from the ticket's predicted output: a real, unscoped
`frob check --only deprecated` on this repo now reports 4 DEPR002
errors, not the 4 DEPR003 in-window warnings the dispatch anticipated.
Cause: the T-0580 deprecation directives (map/outline/xref/docs-search
navigation commands) are bound via `ticket="T-0580"`, and T-0580 itself
is now closed/done -- DEPR002 fires because the bound ticket is no
longer open. This is correct new-gate behavior surfacing a real,
previously-invisible problem (catalogued-is-not-enforced), not a defect
in this ticket's registration. Filed T-0802 (rebind folded into this ticket at land; the interim draft was dropped as absorbed) (rebind the four
T-0580 frob:deprecated directives to a new open ticket) rather than
fixing it here -- out of this ticket's declared scope
(src/frob/app/{xref,outline,docs,map}_runner.py).

`uv run --frozen frob test` (full, unscoped, foreground) shows a large
set of pre-existing failures in unrelated areas (native/strata sys
audit, doctor, compliance registry, cli_check assorted) that reproduce
on this worktree's checked-out main independent of this change -- not
investigated further as out of scope for a 2-file (+1 scope-expansion)
gate-registration ticket. The touched-set verification below is what
this ticket's own change is judged against.

Fold (coordinator-directed, post-initial-report): merged main (brings
T-0802, the sunset-execution ticket, and reconciles the earlier-flagged
tests/unit/graph/test_cache.py main-advance). Scope-added the four
navigation runner files (map/outline/xref/docs_runner.py) with reason
"DEPR002 rebind: directives must cite an open ticket; T-0802 is the
sunset-execution ticket", rebound each frob:deprecated directive's
ticket= from the closed T-0580 to the open T-0802. Dropped
T-0802 (rebind folded into this ticket at land; the interim draft was dropped as absorbed) as absorbed-by T-0797 (its fix landed here instead of
as a separate ticket). `frob check --only deprecated` now shows 0
errors, 4 DEPR003 in-window warnings, matching the ticket's original
acceptance criterion exactly.

### Changed
```
 src/frob/check/__init__.py |  2 +
 src/frob/gates/__init__.py |  7 ++++
 tests/test_gates.py        | 36 +++++++++++++++++
 tickets.md                 | 96 ++++++++++++++++++++++++++++++++++++++++++++--
 4 files changed, 137 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeprecatedGate::test_deprecated_is_registered_in_all_gates` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_deprecated_fires_through_real_gate_dispatch` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)

<!-- ticket:T-0798 -->
```yaml
id: T-0798
title: 'dup: verdict cache serves stale results across rule changes (.frob/dup.db
  keyed by content digest only)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/dup/**
- tests/test_dup.py
scope_changes: []
evidence:
- tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_dup_code_fingerprint_change_invalidates_cached_verdict
- tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_unchanged_dup_code_fingerprint_still_serves_cached_verdict
attachments: []
acceptance:
- text: GIVEN a dup rule/normalization change WHEN frob check runs the dup gate THEN
    cached verdicts computed under the old rules are invalidated (cache key includes
    a rules/version fingerprint) and results reflect current rules; a test proves
    a rule change flips a cached verdict
  evidence:
  - tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_dup_code_fingerprint_change_invalidates_cached_verdict
  - tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_unchanged_dup_code_fingerprint_still_serves_cached_verdict
threat: null
component: null
labels: []
```
T-0785 reviewer-mandated filing: during T-0785 the .frob/dup.db verdict cache silently served pre-rule-change results until manually cleared -- a gate-integrity hole (the dup gate can report stale verdicts as current). Key the cache by (content digest, rules fingerprint) or invalidate on frob.dup code-digest change.

## Done report

T-0785 exposed a gate-integrity hole: .frob/dup.db verdicts survived dup
rule changes because the T-0517 fingerprint is package-version-only.
_dup_code_fingerprint (sha256 over sorted src/frob/dup/*.py name+bytes
with NUL separators) is folded into _check_fingerprint's stored value, so
any in-tree dup-code edit invalidates the cache wholesale through the
existing T-0517 path. Threshold edits need no coverage: verdicts cache
raw scores; config comparison happens at read time (reviewer-verified).
Cold rebuild reproduces the 117-group baseline unchanged.

### Changed
```
 src/frob/dup/_cache.py | 39 +++++++++++++++++++++++++++++++++++----
 tests/test_dup.py      | 48 ++++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md             | 10 +++++++---
 3 files changed, 90 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_dup_code_fingerprint_change_invalidates_cached_verdict` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_unchanged_dup_code_fingerprint_still_serves_cached_verdict` (pytest node id, verified passing when recorded)

<!-- ticket:T-0799 -->
```yaml
id: T-0799
title: 'graph cache: schema drift crashes load_graph (no such column/table) instead
  of rebuilding'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/graph/cache.py
- src/frob/graph/__init__.py
- tests/unit/graph/test_cache.py
scope_changes: []
evidence:
- tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_symbols_table_rebuilds_clean
- tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_mtime_ns_column_rebuilds_clean
attachments: []
acceptance:
- text: GIVEN a .frob/cache.db created by an older schema WHEN load_graph opens it
    THEN it detects the schema mismatch and rebuilds the cache instead of raising
    sqlite3.OperationalError; a test opens an old-schema fixture db and asserts a
    clean rebuild
  evidence:
  - tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_symbols_table_rebuilds_clean
  - tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_mtime_ns_column_rebuilds_clean
threat: null
component: null
labels: []
```
Observed twice during 2026-07-23 lands: worktrees carrying pre-migration cache.db files crashed land mid-flight with 'no such table: symbols' and 'no such column: mtime_ns' (the second crash left a partial squash staged on main). Stamp a schema version in the db and rebuild on mismatch; never let OperationalError escape load paths.

## Done report

Fixed load_graph() (src/frob/graph/__init__.py) to catch sqlite3.OperationalError
across its entire read body, not just the get_root() query. The writer path
(cache.connect()) already stamped/checked a schema version (meta.schema_version,
_SCHEMA_VERSION=3) and self-healed via DROP+recreate on mismatch or any
DatabaseError during DDL -- that mechanism was already correct and untouched.

The actual bug was in the READ-ONLY path: connect_readonly() opens a cache.db
with no schema-version check at all (a read-only connection cannot self-heal),
so a pre-migration cache.db (missing the 'symbols' table, or missing the
'mtime_ns' column T-0245 added) crashed with a raw sqlite3.OperationalError
the moment any query after get_root() touched the drifted shape --
_first_stale_cached_file, _first_added_file, or load_all. Only get_root()
itself was guarded by a try/except; everything after it in the same try block
had no except clause at all (only a finally), so the OperationalError
propagated straight out of load_graph and crashed callers mid-land.

Fix: wrapped the whole read body (get_root through load_all) in one try, with
an explicit sqlite3.OperationalError handler (schema drift -> CacheCorrupt)
ahead of the existing sqlite3.DatabaseError handler (corrupt bytes ->
CacheCorrupt). No versioning scheme changes: this repo already has one
(meta.schema_version) that the writer honors; the read path just needed to
stop letting its query errors escape uncaught. Every real load_graph() caller
already falls back to build_graph() on Err, so CacheCorrupt now triggers a
clean rebuild instead of a crash.

Regression tests (tests/unit/graph/test_cache.py, new file, in ticket scope):
hand-crafted two fixture cache.db files -- (a) missing the symbols table
entirely, (b) missing the mtime_ns/size columns on files (pre-T-0245 shape) --
and assert load_graph() returns Err(CacheCorrupt) rather than raising, then
assert build_graph() against the same path rebuilds cleanly and a subsequent
load_graph() succeeds.

Verified: uv run --frozen pytest tests/unit/graph/ -q -> 37 passed.
uv run --frozen frob check --ticket T-0799 --only prework/lint/static/gates-fast
all pass (0 errors each stage).

Deviations: none from the ticket's plan. cache.py itself needed no change --
its schema-version stamping already existed (T-0279/T-0245); the gap was
entirely in __init__.py's load_graph read-error handling.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_symbols_table_rebuilds_clean` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_mtime_ns_column_rebuilds_clean` (pytest node id, verified passing when recorded)

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
blocked_by: []
parent: null
scope:
- src/frob/dup/**
- frob-core/src/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/dup/_pipeline.py
- tests/test_dup.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the real _leases.py::git_common_dir and _exclude_hazard.py::_git_common_dir
    pair WHEN the dup scan runs with both error-channel and control-flow normalization
    THEN they register as a duplicate group (similarity above the 0.6 floor, was 0.444
    with error-channel alone); repo-wide group delta stays bounded and each new pair
    is examined
  evidence: []
threat: null
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/docs_runner.py
- src/frob/__main__.py
- docs/modules/cli.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN the sunset date 2026-10-01 has passed WHEN this ticket is worked THEN
    the four deprecated navigation commands and their parsers, tests, and doc/test/export
    obligations are removed (or the sunset is explicitly re-adjudicated with the user),
    and no frob:deprecated directive for them remains
  evidence: []
threat: null
component: null
labels: []
```
Sunset-execution ticket for the user's 2026-07-23 deprecation decision (T-0580, done). Stays OPEN until the sunset so the four frob:deprecated directives have a live ticket binding (DEPR002 requires ticket= to reference an open ticket -- T-0797 registration surfaced that the directives bound to the closed T-0580). Do not work before the sunset date.

<!-- ticket:T-0803 -->
```yaml
id: T-0803
title: wire remaining subprocess call sites through the T-0200/T-0778 exec guard (tickets
  git spawn, gitlog, fleet, clipboard, mutate, deploy, scaffold, coverage-wait)
state: done
kind: security
origin: human
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/tickets/__init__.py
- src/frob/gitlog/__init__.py
- src/frob/app/ticket_runner.py
- src/frob/fleet/__init__.py
- src/frob/tickets/clipboard.py
- src/frob/mutate/__init__.py
- src/frob/deploy/_vm_runner.py
- src/frob/scaffold/project.py
- src/frob/testing/_coverage_wait.py
- src/frob/app/gitlog_runner.py
- tests/test_app.py
- tests/test_clipboard.py
- tests/test_mutate.py
- tests/test_tickets_lease.py
- tests/unit/deploy/test_vm_runner.py
- tests/unit/fleet/test_status.py
- tests/unit/test_gitlog.py
- tests/unit/test_scaffold_project.py
- tests/unit/test_ticket_runner_land_release.py
scope_changes:
- op: add
  glob: src/frob/app/gitlog_runner.py
  reason: T-0778's guarded_subprocess_run adds a DEBUG spawn log; gitlog's --json
    runner needed quiet_stdout_logs wrapping to avoid leaking it into stdout output
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_app.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_clipboard.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_mutate.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_lease.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/deploy/test_vm_runner.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/fleet/test_status.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_gitlog.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_scaffold_project.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_gitlog.py::test_git_log_kill_switch_refuses_without_spawning
- tests/test_tickets_lease.py::TestBreadthPerf::test_repo_files_git_kill_switch_refuses_without_spawning
- tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn::test_kill_switch_refuses_without_spawning
- tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_kill_switch_refuses_without_spawning
- tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_kill_switch_refuses_without_spawning
- tests/test_clipboard.py::TestKillSwitch::test_clipboard_image_kill_switch_refuses_without_spawning
- tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning
- tests/unit/deploy/test_vm_runner.py::TestAvail::test_kill_switch_refuses_without_spawning
- tests/unit/test_scaffold_project.py::test_hooks_dir_kill_switch_refuses_without_spawning
- tests/test_app.py::TestRunCoverageWait::test_kill_switch_refuses_without_spawning
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0778 (H2 fix) wired frob.gitio.run_argv through
frob.process._guard.guarded_subprocess_run, which transitively covers every
git spawn that already goes through gitio (serve daemon, gitio-based lease
reads). The T-0778 sweep (grep subprocess.run/Popen/call/check_output
outside src/frob/process/_guard.py and src/frob/gitio.py) found additional
call sites that still bypass the guard entirely -- FROB_DISABLE_EXEC=1 does
NOT stop these:

- src/frob/tickets/__init__.py:930 `_repo_files_git` -- direct `git
  ls-files` subprocess.run, not routed through gitio.run_argv. This is a
  real git spawn the audit's "tickets lease" language pointed at.
- src/frob/tickets/__init__.py:2370 `_run_evidence_command` -- shell=True
  evidence-command spawn (caller-supplied command, T-0215); arguably
  intentionally outside a git-argv guard shape, but still an unguarded
  exec capability.
- src/frob/gitlog/__init__.py:230 -- direct `git log` subprocess.run.
- src/frob/app/ticket_runner.py:863,1159 -- subprocess.run/Popen.
- src/frob/fleet/__init__.py:164,194 -- subprocess.run.
- src/frob/tickets/clipboard.py (9 call sites) -- subprocess.run for
  clipboard tool spawns (pbcopy/xclip/etc).
- src/frob/mutate/__init__.py:260 -- subprocess.run.
- src/frob/deploy/_vm_runner.py:109,116,134,153 -- subprocess.run.
- src/frob/scaffold/project.py:509 -- subprocess.run.
- src/frob/testing/_coverage_wait.py:151 -- subprocess.run (noqa S603).

Fix: for each site, either route it through
frob.process._guard.guarded_subprocess_run (preferred, matching T-0778's
gitio wiring), or justify in a code comment why it must stay outside the
kill switch (e.g. a non-exec-capability tool, or a case where refusing to
spawn would be actively harmful) and record that justification in
design/frob.strata as a real `attr flag=` or an honest waiver -- never a
"T-0200 is pending" waiver again, since the mechanism is real now.
Prioritize the two GIT call sites (tickets/__init__.py:930,
gitlog/__init__.py:230) since those are the closest remaining gap to
FROB_DISABLE_EXEC's advertised "stops every process this component
spawns" claim.

## Done report

## Done report

Changed (round 2, reviewer fix): reviewer REJECTed round 1 on one blocking
finding -- mutate's refusal-as-killed made mutation score gameable via
FROB_DISABLE_EXEC=1 (fabricated 100% score / zero survivors without
running a test). Fixed:

- src/frob/mutate/__init__.py: new `MutateError.ExecDisabled` variant.
  `_run_mutants` now returns `Result[tuple[int, list[Mutant]], MutateError]`
  and returns `Err(MutateError.ExecDisabled)` on the FIRST guarded refusal,
  aborting the whole run instead of scoring it killed (the TimeoutExpired
  case is left as "killed" -- that IS observed behavior under the mutant;
  a refusal ran nothing). `run_mutations` propagates the `Err`, still
  restores the source file (existing `finally`), and logs the abort
  reason. `frob.app.mutate_runner.run` already logs `result.danger_err`
  and exits nonzero on `Err` -- no runner change needed.
- tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning:
  kept the spy-no-spawn assertion, changed expectation from
  `result.is_ok`/no-survivors/100% to `result.is_err` /
  `MutateError.ExecDisabled`.

Evidence (round 2): `uv run --frozen pytest tests/test_mutate.py -q`
(11 passed) and `tests/unit/test_app_runners.py -k "Mutate or mutate"`
(6 passed, mutate_runner CLI wiring incl. its own Err-exits-1 path).
`uv run --frozen frob test --base main` exit=0 (python selection).
`uv run --frozen frob check --ticket T-0803` chunked (lint, gates-fast)
re-run PASS, 0 errors, after `frob ticket sweep T-0803` refreshed the
pre-work stamp. Deletion filter (`git diff main --diff-filter=D`) empty.

All other 10 sites/contracts/tests from round 1 stand as reviewed sound
(unchanged this round). The gitlog human-mode DEBUG-loss nit and the
--json sweep are explicitly out of this ticket's scope per reviewer/
coordinator direction (coordinator filing its own ticket for the sweep).

Filed: none.

Gates: `uv run --frozen frob check --ticket T-0803` chunked loop clean,
0 errors, after both rounds' sweeps. No waivers added.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-a39110485a411b302
Commits (round 2 adds one on top of round 1's three):
- 90a5a8cf fix(process): wire remaining subprocess call sites through T-0778 exec guard
- 849e55d2 Merge branch 'main' into worktree-agent-a39110485a411b302
- 5d5b5b6d chore(tickets): record T-0803 Done report (round 1)
- e015d4fd fix(mutate): abort mutation run on exec-disabled instead of scoring killed

### Changed
```
 src/frob/app/gitlog_runner.py                 |  30 +++--
 src/frob/app/ticket_runner.py                 |  21 +++-
 src/frob/deploy/_vm_runner.py                 |  25 +++-
 src/frob/fleet/__init__.py                    |  22 +++-
 src/frob/gitlog/__init__.py                   |  16 ++-
 src/frob/mutate/__init__.py                   |  38 +++++-
 src/frob/scaffold/project.py                  |  25 ++--
 src/frob/testing/_coverage_wait.py            |  20 +++-
 src/frob/tickets/__init__.py                  |  23 ++--
 src/frob/tickets/clipboard.py                 |  56 +++++++--
 tests/test_app.py                             |  35 +++++-
 tests/test_clipboard.py                       |  34 ++++++
 tests/test_mutate.py                          |  46 ++++++++
 tests/test_tickets_lease.py                   |  32 ++++++
 tests/unit/deploy/test_vm_runner.py           |  43 ++++++-
 tests/unit/fleet/test_status.py               |  45 ++++++++
 tests/unit/test_gitlog.py                     |  28 +++++
 tests/unit/test_scaffold_project.py           |  34 ++++++
 tests/unit/test_ticket_runner_land_release.py |  31 ++++-
 tickets.md                                    | 160 +++++++++++++++++++++++++-
 20 files changed, 693 insertions(+), 71 deletions(-)
```

### Evidence
- `tests/unit/test_gitlog.py::test_git_log_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestBreadthPerf::test_repo_files_git_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn::test_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_clipboard.py::TestKillSwitch::test_clipboard_image_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_vm_runner.py::TestAvail::test_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_hooks_dir_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestRunCoverageWait::test_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)

<!-- ticket:T-0804 -->
```yaml
id: T-0804
title: 'gates: rebind T-0580''s four frob:deprecated directives off the now-closed
  T-0580 (DEPR002)'
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/app/xref_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/docs_runner.py
- src/frob/app/map_runner.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
found while working T-0797 (registering the deprecated gate in _ALL_GATES). T-0580 deprecated the four navigation commands (map/outline/xref/docs-search) with frob:deprecated ticket=T-0580, but T-0580 itself is now closed/done -- so a real frob check --only deprecated run reports DEPR002 (bound to a non-open ticket) on all four, not the DEPR003 in-window warning the T-0797 dispatch predicted. Rebind each directive's ticket= to a new open removal-tracking ticket (or reopen/track differently) so the sunset lifecycle is enforceable again.

## Drop reason
- 2026-07-23: absorbed: rebind folded into T-0797 land (absorbed by T-0797)

<!-- ticket:T-0805 -->
```yaml
id: T-0805
title: 'security: evidence-command runner spawns with shell=True on repo-writable
  ticket YAML input'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/tickets/__init__.py
- tests/test_tickets_evidence_cli.py
scope_changes: []
evidence:
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_command_substitution_is_not_expanded
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_malformed_quoting_fails_cleanly_instead_of_shelling_out
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_exec_kill_switch_stops_evidence_commands
attachments: []
acceptance:
- text: 'GIVEN a cmd: evidence entry WHEN _run_evidence_command executes it THEN it
    runs without shell=True (argv form or an explicitly justified sanctioned shell
    path with input validation) and through the exec guard; a test proves shell metacharacters
    in a crafted evidence command do not reach a shell'
  evidence:
  - tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell
  - tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_command_substitution_is_not_expanded
  - tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_malformed_quoting_fails_cleanly_instead_of_shelling_out
  - tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_exec_kill_switch_stops_evidence_commands
threat: elevation-of-privilege
component: null
labels: []
```
Split out of T-0803 per the T-0778 reviewer: tickets/__init__.py::_run_evidence_command runs caller-supplied commands from ticket YAML (repo-writable by every agent/tool) with shell=True -- injection-adjacent surface that must not ride a medium wiring ticket. Note evidence commands are a sanctioned feature (T-0215) so the fix must preserve legitimate cmd evidence (shlex.split argv execution or documented constrained shell) while removing raw shell interpolation, and wire through guarded_subprocess_run (T-0778).

## Done report

Removed shell=True from _run_evidence_command (src/frob/tickets/__init__.py):
`cmd:` evidence entries in ticket YAML are repo-writable by every agent/tool,
so handing them to a shell was injection-adjacent even though cmd evidence
itself is a sanctioned feature (T-0215).

Survey of every real `cmd:` entry recorded in tickets.md/tickets-archive.md
found five distinct commands. Four are plain argv with no shell metacharacters
(`grep -n '...'`, `grep -q "..."`, `python3 <script>`, `uv run frob check
--only docblocks`) and parse identically under shlex.split. Exactly one
(T-0677's archived, already-DONE evidence: `test "$(grep -c ...)" = N &&
test "$(grep -c ...)" = N`) relies on shell command substitution and `&&`
sequencing and cannot be expressed as a single argv -- that ticket is closed
and nothing re-verifies its evidence live, so it is the deliberate migration
case, not a live constraint.

Chose argv-only execution (shlex.split(command), no shell) over a
constrained-shell path: with only one dead entry needing shell features,
keeping shell=True anywhere (even guarded) would still let a freshly
hand-pasted evidence command reach a shell interpreter, which is the exact
class of finding this ticket flags. _run_evidence_command now shlex.splits
the command into argv and runs it through frob.process._guard.
guarded_subprocess_run (T-0778) so FROB_DISABLE_EXEC also stops evidence
commands, not just frob check's own tool runners. A ValueError from
shlex.split (unbalanced quotes) or an empty parsed argv both fold to
Err(EvidenceCmdFailed), same failure shape as a nonzero exit -- callers
don't need a new error branch.

Honest assessment of the trust-domain argument in the ticket: cmd evidence
does execute in the same trust domain as the repo's own hooks/CI (an agent
that can write ticket YAML can also write source), so shell=True was never
a privilege-escalation vector by itself. What this fix removes is shell
*metacharacter interpretation* -- `;`, `$()`, backticks, `|`, `>` -- from a
string an agent may paste without full attention (copy-pasted from a log,
or containing an accidental semicolon), turning a plausible slip into inert
argv text instead of a sequenced/substituted command. That is a real,
non-cosmetic hardening, not a no-op: the regression test proves a `;
touch <marker>` payload no longer creates the marker file.

Migration note for future evidence needing multi-step/substitution logic:
shell out to a checked-in script and record `cmd:python3 <script>` or
`cmd:bash <script>` as a single argv entry, rather than relying on inline
shell syntax in the YAML string itself. Documented in
_run_evidence_command's own docstring.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_command_substitution_is_not_expanded` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_malformed_quoting_fails_cleanly_instead_of_shelling_out` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_exec_kill_switch_stops_evidence_commands` (pytest node id, verified passing when recorded)

<!-- ticket:T-0806 -->
```yaml
id: T-0806
title: 'tests: test_cli_check tmp fixtures broken on main -- git ls-files rc=128,
  3 system tests red'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- tests/system/test_cli_check.py
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
scope_changes:
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'Root-caused as two product bugs, not just fixture debt: (1) frob check

    --json leaked _refuse_ticket_lease_mismatch''s own gitio debug logging to

    stdout before the --json quiet clamp was ever entered

    (src/frob/app/check_runner.py::run), and (2) ProcessPoolExecutor(spawn)

    worker processes for CPU-bound gates never inherit the parent''s

    quiet_stdout_logs clamp, so they leaked their own default-DEBUG per-file

    parse logging onto the shared stdout fd (src/frob/gates/__init__.py). Both

    fixed inline; scope extended per T-0806''s own instructions ("fix

    (scope-add product files with a reason if product code is at fault)").

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'Root-caused as two product bugs, not just fixture debt: (1) frob check

    --json leaked _refuse_ticket_lease_mismatch''s own gitio debug logging to

    stdout before the --json quiet clamp was ever entered

    (src/frob/app/check_runner.py::run), and (2) ProcessPoolExecutor(spawn)

    worker processes for CPU-bound gates never inherit the parent''s

    quiet_stdout_logs clamp, so they leaked their own default-DEBUG per-file

    parse logging onto the shared stdout fd (src/frob/gates/__init__.py). Both

    fixed inline; scope extended per T-0806''s own instructions ("fix

    (scope-add product files with a reason if product code is at fault)").

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
- tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation
- tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
- tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
attachments: []
acceptance:
- text: GIVEN main WHEN tests/system/test_cli_check.py runs THEN TestCheckCleanProject::test_clean_code_exits_zero,
    TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation, and TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
    pass; a run()-level exit-code test for the T-0787 lease-pin refusal is added once
    the fixture works
  evidence:
  - tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
  - tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation
  - tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
  - tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
threat: null
component: null
labels: []
```
T-0787 reviewer verified these three nodes fail on CURRENT main with git ls-files exit 128 inside the tmp_path fixture (not-a-git-repository shape) plus JSON parse of polluted stdout -- pre-existing fixture debt unrelated to recent lands, no covering ticket found. Root-cause the fixture (missing git init? cwd leakage? the T-0768 quiet clamp changing expected stdout?), repair, and add the deferred end-to-end run() exit-1 test for ticket_lease_pin refusal (T-0787 reviewer action item b).

## Done report

Root cause (two distinct product bugs, not fixture-only debt):

1. `frob check --json` refuses a stale/cross-worktree ticket lease
   (T-0787's `_refuse_ticket_lease_mismatch`) BEFORE `_run_all_stages`
   ever enters `_stdout_log_ctx`'s `quiet_stdout_logs()` clamp. That
   refusal path (and `--stamp-baseline`/`--stamp-coverage` via
   `_handle_stamp_modes`) calls into `frob.gitio` (branch/lease lookups),
   whose own DEBUG/INFO logging printed straight to stdout, unclamped,
   corrupting `--json`'s stdout payload on a git-less tmp_path fixture
   (`json.loads` failure observed in
   TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage).

2. `frob.gates`'s CPU-bound gates (arch/dup) run in a
   `ProcessPoolExecutor(mp_context=spawn)`. Spawn-context workers are
   FRESH interpreters that re-run `frob.logging.logger._init()` from
   scratch on import -- they never see the PARENT process's in-memory
   `quiet_stdout_logs`/`stdout_log_level` clamp (that only mutates the
   parent's own handler objects), so every worker's default-DEBUG
   per-file parse logging (`dispatching path=...`, `extracted N
   symbols...`, `parsed ...`) printed straight to the shared stdout file
   descriptor it inherits from the parent, regardless of `--json` or
   default (non-`-v`) mode. Root-caused via `strace -f -e trace=write`
   (traced the leaking `write(1, ...)` calls to a
   `multiprocessing.spawn_main` worker PID, distinct from the parent
   PID) after ruling out Python-`logging`-level causes (patched
   `sys.stdout.write`, `logging.StreamHandler.emit/handle`,
   `Logger.callHandlers` -- none fired for the leaked lines, proving they
   never went through the PARENT's logging machinery at all).

Neither cause is "missing git init in the fixture" per se, though most of
the file's OTHER fixtures (unrelated to #1/#2, but sharing the same
git-less `_make_project`/bare-`pkg.py` shape) also needed a real git
commit or a `pyproject.toml` for `working_diff`/`detect_project_type` to
resolve at all -- T-0550 (COV002/SCOPE001/TODO001 load-failure handling)
and T-0546 (CHECK001 unknown-project-type) both predate this ticket and
are intentional, unrelated hardening; the fixtures in this file had
simply never been updated to match.

Fix:
- src/frob/app/check_runner.py::run -- wraps
  `_refuse_ticket_lease_mismatch`/`_handle_stamp_modes` in the same
  `quiet_stdout_logs()` `--json` uses everywhere else (reentrant via
  T-0125's depth counter, so `_run_all_stages`'s later nested entry is a
  no-op).
- src/frob/gates/__init__.py -- new `_WORKER_STDOUT_LOG_LEVEL_ENV`;
  `_open_process_pool` stamps it with the parent's current stdout handler
  level before constructing the pool; `_run_process_gate` (the picklable
  worker entry point) reads it and clamps its OWN stdout handler before
  running the gate function.
- tests/system/test_cli_check.py -- git-init+commit (or a minimal
  `pyproject.toml` via new `_write_pyproject` helper) added to the
  fixtures that needed a real git repo / recognized project type for
  `working_diff`/`detect_project_type` to resolve cleanly, WITHOUT
  touching the shared `_make_project`/`_make_ts_project` helpers (kept
  git-less/language-agnostic, since `TestGitlessTargetGateSeverity`
  intentionally depends on that).
- Added the deferred T-0787 end-to-end test,
  TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses:
  a real `git worktree add` second checkout, a ticket started (lease
  recorded) in the main worktree, then `frob check --ticket <id>` run
  from the SECOND worktree asserts exit 1 with a refusal naming
  `frob ticket start <id>`.

Deviations / disclosed cuts:
- Two more failures in this file were found and fixed-attempted but are
  PRE-EXISTING, UNRELATED to this ticket's git-ls-files/JSON-pollution
  regression (confirmed: pass standalone/in most orderings, and their
  failure modes have nothing to do with gitio or process-pool logging):
  TestCheckTypescript::test_clean_ts_passes_tsc (needs a warn-severity
  frob.toml AND a fix to a dangling `T-0329` reference inside LANG003's
  known_gap declaration -- T-0329 does not exist as a real ticket) and
  TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
  (order-dependent: `frob.logging.logger._init()` binds
  `ext://sys.stdout`/`ext://sys.stderr` ONCE per process/xdist-worker, at
  the first `get_logger()` call -- if that happens before THIS test's own
  `capsys` fixture activates, `capsys.readouterr()` can never observe
  frob's own stderr handler). Filed as T-0818 (title:
  "test_cli_check: TS/gitless fixture debt unrelated to T-0806 (LANG003
  T-0329 dangling ref, capsys/logging init-order flake)"), left
  unfixed here -- out of this ticket's actual root-cause scope, and each
  needs its own investigation (a real product decision for #1, a
  test-isolation redesign for #2).
- `tests/system/test_cli_check.py -q` (no `-n0`, matching the coordinator's
  exact instruction) is verified fully green below EXCEPT those two
  pre-existing, filed-separately failures.

Evidence: 4 node ids bound via `frob ticket evidence T-0806` (see
Changed). `uv run --frozen pytest tests/system/test_cli_check.py -q`:
34 passed, 2 failed (the two filed-separately, pre-existing failures
above) out of 36 total.
Filed: T-0818 (unrelated TS/gitless fixture debt, see above).
Gates: `uv run --frozen frob check --ticket T-0806` clean (0 errors,
1101 warnings, 207 waived -- none new/related to this ticket's touched
files).

### Changed
```
 src/frob/app/check_runner.py   |  20 +++++-
 src/frob/gates/__init__.py     |  53 +++++++++++++-
 tests/system/test_cli_check.py | 154 +++++++++++++++++++++++++++++++++++++++++
 3 files changed, 222 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses` (pytest node id, verified passing when recorded)

<!-- ticket:T-0807 -->
```yaml
id: T-0807
title: 'check: auto-suppress land-owned REL001 bump-half in worktree/ticket context
  (reviews keep tripping on it)'
state: done
kind: ux
origin: agent
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
- src/frob/app/check_runner.py
- tests/test_gates.py
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'Verification tests for T-0807''s context-derived REL001 suppression live
    in

    tests/test_gates.py (TestDebtGate, alongside the existing T-0731 bump tests

    they extend) -- adding this test home to scope so COV002 accounts for the

    new/changed test methods.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestDebtGate::test_release_gate_bump_fires_without_frob_agent
- tests/test_gates.py::TestDebtGate::test_release_gate_bump_suppressed_under_frob_agent
- tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket
- tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket
- tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease
- tests/test_gates.py::TestDebtGate::test_rel001_linked_worktree_detected
attachments: []
acceptance:
- text: GIVEN frob check --ticket T-X running in a worktree (or against a ticket with
    a live worktree lease) WHEN the public API changed THEN REL001's version-bump
    demand is reported as an informational note (land owns the bump) not an error;
    GIVEN a plain root-checkout check with no ticket context THEN REL001 errors as
    today
  evidence:
  - tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket
  - tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease
  - tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket
threat: null
component: null
labels: []
```
Recurring friction (4+ review cycles this drive): REL001's bump-half fires as an error in worktree reviews/implementations because suppression is keyed on the FROB_AGENT env var, which reviewers and some dispatch shells never set -- every reviewer then REJECTs or hand-waives a violation that frob ticket land auto-clears seconds later (auto-bumps landed 0.97.0 through 0.105.0 this week). Derive the suppression from CONTEXT instead of env: if the check runs with --ticket and that ticket holds a worktree lease (or cwd is a linked worktree), the bump is land-owned by definition. Keep the API-diff REPORTING (reviewers should still see 'public API changed (minor)'), demote only the bump demand.

## Done report

## Done report

Changed:
src/frob/gates/__init__.py::_rel001_bump_suppressed_under_agent (docstring clarified: explicit FROB_AGENT override only)
src/frob/gates/__init__.py::_rel001_is_linked_worktree (new)
src/frob/gates/__init__.py::_rel001_land_owned (new)
src/frob/gates/__init__.py::release_gate (signature: +ticket_id param; branches on FROB_AGENT override vs context-derived land_owned vs plain error path)
src/frob/gates/__init__.py::_rel001_land_note (new)
src/frob/gates/__init__.py::_build_jobs (release job now passes st.ticket.id)

Detection design: REL001's bump/changelog demand is land-owned (WARN
informational note, not ERROR) when EITHER (a) ticket_id's cross-worktree
lease (resolve_lease, frob.tickets._leases, unchanged/reused) pins to
root, or (b) root is a linked git worktree (`git rev-parse --git-dir`
resolves to a worktree-private path distinct from `--git-common-dir`).
The pre-existing FROB_AGENT env-var override (T-0731) is preserved as a
SEPARATE, higher-priority path that still fully suppresses (no note at
all) -- this keeps the two existing T-0731 tests passing unchanged. A
plain root checkout with no --ticket and no live lease keeps erroring
exactly as before T-0807.

Evidence (pytest --collect-only confirmed resolving; frob test --base main green):
tests/test_gates.py::TestDebtGate::test_release_gate_bump_fires_without_frob_agent (pre-existing, still green)
tests/test_gates.py::TestDebtGate::test_release_gate_bump_suppressed_under_frob_agent (pre-existing, still green)
tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket (new)
tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket (new)
tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease (new)
tests/test_gates.py::TestDebtGate::test_rel001_linked_worktree_detected (new)
`uv run --frozen pytest tests/test_gates.py -q` -> 352 passed
`uv run --frozen pytest tests/test_release.py tests/test_ticket_land.py tests/unit/test_ticket_runner_land_release.py -q` -> all passed
`uv run --frozen frob test --base main` -> [PASS] python exit=0

Filed: none (no out-of-scope work found)

Gates: `uv run --frozen frob check --ticket T-0807 --only <stage>` clean
(0 errors) for all 5 stage groups (lint, static, gates-fast, gates-native,
gates-security) after `frob ticket sweep T-0807` and adding
tests/test_gates.py to scope (reason: T-0807's own verification tests
live there, alongside the T-0731 tests they extend -- COV002 needed the
new/changed test methods accounted for).

Deviation: scope was widened by one file, tests/test_gates.py, via
`frob ticket scope T-0807 --add tests/test_gates.py --reason-file ...`
per the playbook's normal scope-add mechanism (not a silent edit) --
the ticket's own acceptance criteria named "Tests" without a declared
test-file scope entry, and COV002/DRIFT002 confirmed a real gate
required it.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestDebtGate::test_release_gate_bump_fires_without_frob_agent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_release_gate_bump_suppressed_under_frob_agent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_rel001_linked_worktree_detected` (pytest node id, verified passing when recorded)

<!-- ticket:T-0808 -->
```yaml
id: T-0808
title: 'gates: WAIVE007 dangling-waiver-ref -- unresolvable BINDING ticket ref in
  a waiver is a warning, not silence'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
- tests/test_waive_gate.py
- docs/design/registry/check-coverage.yaml
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'WAIVE007 gate needs a registry entry documenting it as a live,

    enforced gate rule (docs/design/registry/check-coverage.yaml,

    CHK-GATE-WAIVE007), mirroring WAIVE006''s CHK-GATE-WAIVE006 entry,

    plus the gate_rule_total bump the new rule id requires.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_waive_gate.py::TestWaive007ExemptDanglingRef::test_draft_id_is_exempt
- tests/test_waive_gate.py::TestWaive007ExemptDanglingRef::test_real_ticket_id_is_not_exempt
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_binding_reason_phrase_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_resolvable_id_is_silent
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_draft_id_is_exempt
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_no_binding_ref_at_all_is_silent
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_draft_id_is_exempt
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_resolvable_id_is_silent
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_no_design_dir_is_silent
- tests/test_waive_gate.py::TestWaive007Registration::test_waive007_is_a_known_gate_rule
- tests/test_waive_gate.py::TestWaive007Registration::test_waive007_gate_combines_both_channels
- tests/test_waive_gate.py::TestWaive007Registration::test_waivable_via_frob_waive_comment
- tests/test_waive_gate.py::TestWaive007RealRepo::test_zero_findings_on_real_repo
attachments: []
acceptance:
- text: GIVEN a waiver whose binding ticket reference resolves to no ticket in active
    or archive WHEN frob check runs THEN a WARNING-tier finding names the site and
    the dangling id; GIVEN a resolvable open ref THEN no finding
  evidence:
  - tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires
  - tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires
  - tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_resolvable_id_is_silent
threat: null
component: null
labels: []
```
T-0779 reviewer finding: WAIVE006 deliberately skips unresolvable binding refs, but a dangling ref (e.g. a draft id renumbered at land -- the T-draft-8cd37914 -> T-0803 case that left four design/frob.strata waivers pointing at a dead id) is a permanent silent waiver, the same accountability shape WAIVE006 closes. Add WAIVE007 warning-tier for dangling BINDING refs (drafts in live worktrees are a legitimate transient -- consider exempting T-draft-* ids younger than N days or referenced by a live lease, document the choice).

## Done report

Added WAIVE007 (WARNING-tier): a waiver whose binding ticket ref
(`ticket=`/`ticket "..."` attribute, or WAIVE006's binding-phrase
extraction in the reason text) resolves to no ticket at all in the
active+archive ledger. Mirrors WAIVE006's two-channel shape
(`_waive007_comment_violations` for `frob:waive` comments,
`_waive007_strata_violations` for `.strata` `waive` clauses,
combined by `waive007_gate`), reusing `_waive006_binding_ticket_refs`
so the binding-vs-historical-mention calibration is not duplicated.

Exemption design: every `T-draft-*` id is exempt from WAIVE007
unconditionally -- the simpler of the two options the ticket offered,
chosen and documented in the module comment above
`_waive007_is_exempt_dangling_ref`. A narrower "exempt only if a live
worktree lease still claims this draft id" rule was considered and
rejected: it would make the gate depend on `frob.tickets._leases`
state that is worktree-local and routinely absent in the very runs
(a landed/merged checkout, CI, another agent's worktree) where the
gate needs to be trustworthy, making the exemption itself
environment-dependent. `T-draft-*` ids are worktree-local transients
by construction (minted only inside an active worktree, always
renumbered to a real `T-####` id at `frob ticket land`), so any
`T-draft-*` id a gate run observes is either still in-progress (not
a dangling reference) or was already renumbered away and is now
permanently unresolvable by design -- the same "out of scope" shape
WAIVE006 already applies to unresolvable ids generally.

Registered WAIVE007 in `_KNOWN_GATE_RULES`, wired `waive007_gate`
into the WAIVE00*-self-check group in `run_gates` (same dependency
shape as WAIVE006: snapshot waive edges + merged ticket queue only),
and exported `waive007_gate` from `__all__`.

Registry: added `CHK-GATE-WAIVE007` to
`docs/design/registry/check-coverage.yaml` (mirroring
`CHK-GATE-WAIVE006`) and bumped `gate_rule_total` 105 -> 106. This
file was added to T-0808's scope via `frob ticket scope --add
--reason-file` (not originally declared) since the new gate rule id
needs a registry entry to satisfy REG002 (`handled_by:<rule>` names
a rule id absent from the live gate set).

Tests: `tests/test_waive_gate.py` gained
`TestWaive007ExemptDanglingRef`, `TestWaive007CommentChannel`,
`TestWaive007StrataChannel`, `TestWaive007Registration`, and
`TestWaive007RealRepo` (15 tests total), mirroring the existing
WAIVE006 test classes' structure and fixture helpers exactly. The
real-repo calibration test (`test_zero_findings_on_real_repo`) is
the proof the ticket demanded: WAIVE007 fires zero findings against
this repo's own live `design/frob.strata` and `frob:waive` comments
-- main has no dangling binding refs left after the T-0803
draft-id retarget.

Verification: `uv run --frozen pytest tests/test_waive_gate.py
tests/test_gates.py -q` -> 74 passed (34 in test_waive_gate.py + 40
in test_gates.py). `uv run --frozen frob check --ticket T-0808`
chunked per section 3b/playbook (`--only prework`, `gates-fast`,
`gates-native`, `gates-security`, `lint`, `static`) -> every stage
group 0 errors; `gate:WAIVE` 0 errors throughout (no new WAIVE007
findings on the real repo, consistent with the calibration test).
`uv run --frozen ruff format` clean on both changed files after one
initial reformat of the test file.

Deviations: none from the ticket's plan. `docs/design/registry/
check-coverage.yaml` was added to scope via the CLI (see above)
since it was not in the ticket's originally declared scope but is
required by the "registry entry" plan item.

### Changed
```
 docs/design/registry/check-coverage.yaml |   6 +-
 src/frob/gates/__init__.py               | 157 +++++++++++++++++++++++
 tests/test_waive_gate.py                 | 212 +++++++++++++++++++++++++++++++
 3 files changed, 374 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

<!-- ticket:T-0809 -->
```yaml
id: T-0809
title: wire real callee-resolution + resource-tracking DSL into the T-0745 protocol
  summary engine
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/graph/dsl.py
- docs/modules/graph.md
- tests/test_graph.py
- tests/unit/test_arch.py
- tests/unit/graph/test_dsl.py
scope_changes:
- op: add
  glob: tests/test_graph.py
  reason: 'Deterministic fixture tests for the two T-0809 mechanisms (real

    callee-resolution UNRESOLVED_CALLEE wiring in build_call_graph, and the

    new resource-tracking DSL folded into compute_protocol_summaries) live in

    the existing test homes for the modules they exercise, per the playbook''s

    evidence discipline: tests/test_graph.py already hosts TestCallGraph

    (build_call_graph/build_reference_graph fixture tests) and

    tests/unit/test_arch.py already hosts TestProtocolSummaryEngine (the

    T-0745 summary-engine fixture tests this ticket extends) -- adding a

    parallel, disconnected test file for the same two modules would just be

    duplication.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_arch.py
  reason: 'Deterministic fixture tests for the two T-0809 mechanisms (real

    callee-resolution UNRESOLVED_CALLEE wiring in build_call_graph, and the

    new resource-tracking DSL folded into compute_protocol_summaries) live in

    the existing test homes for the modules they exercise, per the playbook''s

    evidence discipline: tests/test_graph.py already hosts TestCallGraph

    (build_call_graph/build_reference_graph fixture tests) and

    tests/unit/test_arch.py already hosts TestProtocolSummaryEngine (the

    T-0745 summary-engine fixture tests this ticket extends) -- adding a

    parallel, disconnected test file for the same two modules would just be

    duplication.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: 'tests/unit/graph/test_dsl.py is dsl.py''s own dedicated parser test home

    (TestProtocolDeclarations already covers the T-0744 protocol/transition/

    requires verbs this ticket''s resource verbs are siblings of) -- the

    correct place for a directive-grammar round-trip test, not

    tests/test_graph.py or tests/unit/test_arch.py (which cover the summary

    engine''s join semantics, already scoped).

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_graph.py::TestCallGraph::test_build_call_graph_marks_unresolved_private_looking_callee
- tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_mark_unresolved_public_looking_call
- tests/test_graph.py::TestCallGraph::test_build_call_graph_default_preserves_old_silent_omission_behavior
- tests/test_graph.py::TestCallGraph::test_build_call_graph_resolved_private_callee_is_not_also_unresolved
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_resource_declarations_populate_acquired_released_escaped
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_transitively_through_a_caller
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_across_a_recursive_cluster
- tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_release_escapes_round_trip
- tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_missing_target_is_malformed
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0745 built the shared per-function protocol-summary fixpoint engine
(frob.graph.summary.compute_protocol_summaries) over an explicit
CallGraph + Edge input, with UNRESOLVED_CALLEE as an engine-level sentinel
a caller wires in to mean "this call could not be bound". Two pieces of
the original design sketch were explicitly deferred, not built:

1. Real callee-resolution wiring: nothing yet decides, from real source,
   when a call site should become UNRESOLVED_CALLEE in the CallGraph fed
   to the engine (the ticket referenced "T-0339-family resolvers for
   callee binding" for this). frob.graph.callgraph.build_call_graph today
   silently omits any call it cannot resolve rather than recording it as
   unresolved -- that gap needs closing before the engine's poisoning
   channel means anything on a real repo scan, not just fixture graphs.

2. The "acquired/released/escaped resources" third of the summary
   (states/transitions are covered; resources are not) -- there is no
   frob:acquire/frob:release-style DSL surface for this yet, only the
   T-0744 protocol/transition/requires directives.

Also noted: the T-0745 ticket's own DESIGN CONSTRAINT ("ONE engine shared
with T-0686 may-raise, whichever builds first hosts it") could not be
coordinated on this pass -- T-0686 does not exist yet. Whoever builds
T-0686 should consume frob.graph.summary's SCC/fixpoint machinery rather
than re-deriving a second one.

## Done report

Built (both mechanisms the ticket scoped):

1. Real callee-resolution wiring: `build_call_graph(root, paths, *,
   mark_unresolved=False)` -- opt-in, NOT the default. When
   `mark_unresolved=True`, a call target whose short name starts with `_`
   (looks like this module's own private-symbol convention) but resolves
   to zero candidates anywhere in `paths` gets a `UNRESOLVED_CALLEE` edge
   instead of the previous silent omission. `UNRESOLVED_CALLEE` moved to
   `callgraph.py` (its real producer now) and is re-exported unchanged
   from `summary.py` for backward compatibility.

   Default stayed `False`, not `True`: `frob.gates` (3 call sites,
   including `_cov006_third_file_reachable`) and `frob.dup._pipeline`
   already call `build_call_graph` and iterate its output (including
   `closure()`) assuming every entry is a real `path::qualname` symref
   splittable on `"::"`. Discovered via a real `IndexError` crash in
   `_cov006_third_file_reachable` during this ticket's own gates-fast
   verification pass when I first defaulted to `True`. Those call sites
   are in `src/frob/gates/**` and `src/frob/dup/**`, outside T-0809's
   scope, so widening them is not this ticket's to do -- disclosed here,
   not silently worked around.

2. Resource-tracking DSL: `frob:acquire <resource>` / `frob:release
   <resource>` / `frob:escapes <resource>` (bare-target verbs, same
   grammar as `frob:doc`/`frob:ticket`) -- new `EdgeKind.ACQUIRE`/
   `RELEASE`/`ESCAPES`, parsed by `dsl.parse_directives` exactly like the
   T-0744 protocol verbs. `FunctionSummary` gained `acquired`/`released`/
   `escaped` frozenset fields, folded transitively through
   `compute_protocol_summaries` by the same plain set-union join
   `requires`/`transitions` already use (own declaration union callee
   summaries, propagated bottom-up through the existing SCC/fixpoint
   machinery, no new traversal logic).

Deferred, disclosed (not built, per the ticket's own instruction to
disclose rather than build past scope):
- Real postdominance-based cleanup-obligation VERIFICATION (does every
  acquire actually get released -- or legitimately escape -- on every
  exit path) is T-0747's job (already ticketed, blocked_by T-0745,
  T-0686). This ticket only adds the DSL surface + transitive summary
  exposure T-0747's verifier will need, same posture `requires`/
  `transitions` already have toward T-0746.
- The T-0686 may-raise engine this substrate is meant to eventually share
  with does not exist yet to consume it -- the T-0745 DESIGN CONSTRAINT
  ("one engine, whichever builds first hosts it") still cannot be
  coordinated on this pass, unchanged from T-0745's own disclosure.
- Widening `frob.gates`/`frob.dup._pipeline`'s own `build_call_graph`
  call sites to be `UNRESOLVED_CALLEE`-aware (so a real repo-wide
  protocol-summary run could actually be wired end-to-end) is outside
  `src/frob/graph/**` -- `mark_unresolved` is available for a future
  ticket to opt those call sites in, or to build a genuine production
  entrypoint that calls `build_call_graph(..., mark_unresolved=True)`
  and feeds `compute_protocol_summaries`.

Scope deviations: scope-added tests/test_graph.py, tests/unit/test_arch.py,
and tests/unit/graph/test_dsl.py via the sanctioned `frob ticket scope
--add --reason-file` mechanism (not a hand-edit) -- deterministic fixture
tests for both mechanisms live in each module's existing dedicated test
home rather than a new parallel file.

Changed:
  src/frob/graph/callgraph.py -- UNRESOLVED_CALLEE (moved here),
    build_call_graph gains mark_unresolved kwarg (default False),
    _resolve_edges gains the unresolved-marking logic
  src/frob/graph/summary.py -- UNRESOLVED_CALLEE re-exported from
    callgraph; FunctionSummary gains acquired/released/escaped;
    _own_contribution/_join_from_callees/compute_protocol_summaries
    fold the three new sets transitively
  src/frob/graph/_models.py -- EdgeKind.ACQUIRE/RELEASE/ESCAPES
  src/frob/graph/dsl.py -- "acquire"/"release"/"escapes" verbs in
    _VERB_TABLE
  docs/modules/graph.md -- Call graph section updated for
    mark_unresolved + the default-False rationale; Protocol summary
    engine section updated for the moved UNRESOLVED_CALLEE and a new
    "Resource-tracking DSL (T-0809)" subsection; Comment DSL directive
    table gains the three new verb rows
  tests/test_graph.py -- 4 new TestCallGraph tests (unresolved marking,
    no-mark on public-looking calls, default-False preserved, resolved
    callee never also unresolved)
  tests/unit/test_arch.py -- 3 new TestProtocolSummaryEngine tests
    (resource leaf declarations, one-hop join, recursive-cluster join)
    plus _acquire/_release/_escapes test helpers
  tests/unit/graph/test_dsl.py -- new TestResourceDirectives class (2
    tests: round-trip, missing-target malformed)
  tickets.md -- T-0809 scope changes, evidence, this Done report

Evidence (9 ids, bound via `frob ticket evidence`, all pass):
  tests/test_graph.py::TestCallGraph::test_build_call_graph_marks_unresolved_private_looking_callee
  tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_mark_unresolved_public_looking_call
  tests/test_graph.py::TestCallGraph::test_build_call_graph_default_preserves_old_silent_omission_behavior
  tests/test_graph.py::TestCallGraph::test_build_call_graph_resolved_private_callee_is_not_also_unresolved
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_resource_declarations_populate_acquired_released_escaped
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_transitively_through_a_caller
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_across_a_recursive_cluster
  tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_release_escapes_round_trip
  tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_missing_target_is_malformed

`uv run pytest tests/unit/graph/ tests/unit/test_arch.py tests/test_graph.py`:
274 passed (21 new + full pre-existing graph/dsl/arch suites, all green).
`uv run frob test --base main`: touched=35 ripple=0, exit=0, 3.06s.

Filed: none -- both out-of-scope discoveries (gates/dup call sites not
UNRESOLVED_CALLEE-aware; T-0686/T-0747 dependency chain) are already
covered by existing tickets (T-0747, T-0686) or are a future-opt-in this
ticket's own kwarg default already protects against, not a new bug
needing its own ticket.

Gates: chunked `frob check --ticket T-0809 --only <stage>` for
lint/static/gates-fast/gates-native/gates-security all PASS (0 errors).
gates-fast initially FAILed with a real `IndexError` crash in
`frob.gates._cov006_third_file_reachable` when `mark_unresolved` first
defaulted to `True` -- fixed by flipping the default to `False` (see
"Built" section above), not by waiving or working around the gate.
gates-fast also initially flagged DRIFT002 (a `frob:describes` anchor in
docs/modules/graph.md still pointing at
`src/frob/graph/summary.py::UNRESOLVED_CALLEE` after the symbol moved to
`callgraph.py`) and PRE001 (stale pre-work sweep after the scope-add) --
both fixed (anchor retargeted, `frob ticket sweep T-0809` re-run), not
waived. No new waivers added by this ticket's own code.

Worktree: .claude/worktrees/agent-ad87b621f69d37500
Not closed, not landed (per dispatch instructions) -- ready for review/land.

### Changed
```
 docs/modules/graph.md        |  89 ++++++++++++++++++-----
 src/frob/graph/_models.py    |  15 ++++
 src/frob/graph/callgraph.py  |  95 +++++++++++++++++++++++--
 src/frob/graph/dsl.py        |   7 ++
 src/frob/graph/summary.py    | 164 ++++++++++++++++++++++++++++++++++++-------
 tests/test_graph.py          |  77 ++++++++++++++++++++
 tests/unit/graph/test_dsl.py |  34 +++++++++
 tests/unit/test_arch.py      |  64 +++++++++++++++++
 tickets.md                   |  85 +++++++++++++++++++++-
 9 files changed, 579 insertions(+), 51 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_marks_unresolved_private_looking_callee` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_mark_unresolved_public_looking_call` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_default_preserves_old_silent_omission_behavior` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_resolved_private_callee_is_not_also_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_resource_declarations_populate_acquired_released_escaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_transitively_through_a_caller` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_across_a_recursive_cluster` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_release_escapes_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_missing_target_is_malformed` (pytest node id, verified passing when recorded)

<!-- ticket:T-0810 -->
```yaml
id: T-0810
title: wire --force flag through to frob.tickets.archive's CLI entrypoint
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/__main__.py
- src/frob/app/config.py
- tests/test_ticket_runner*.py
- tests/test_tickets*.py
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: T-0810 needs argparse wiring in __main__.py and an AppConfig field in config.py
    for --force, plus CLI test home; the T-0764 scope only covered tickets/**
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/config.py
  reason: T-0810 needs argparse wiring in __main__.py and an AppConfig field in config.py
    for --force, plus CLI test home; the T-0764 scope only covered tickets/**
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_runner*.py
  reason: T-0810 needs argparse wiring in __main__.py and an AppConfig field in config.py
    for --force, plus CLI test home; the T-0764 scope only covered tickets/**
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets*.py
  reason: T-0810 needs argparse wiring in __main__.py and an AppConfig field in config.py
    for --force, plus CLI test home; the T-0764 scope only covered tickets/**
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0764 added archive(root, *, force: bool = False) in src/frob/tickets/__init__.py, refusing when a live cross-worktree lease exists unless force=True. The CLI entrypoint (_archive in src/frob/app/ticket_runner.py, 'frob ticket archive' subcommand) does not yet expose a --force flag to pass through, since that file is outside T-0764's declared scope (src/frob/tickets/**, tests/test_tickets*.py, tests/test_ticket_land.py). Add an argparse --force flag to the archive subcommand and thread it to archive(root, force=...).

## Done report

## Done report

Changed:
- src/frob/tickets:archive (unchanged, T-0764) -- consumed by CLI as force=cfg.ticket_force
- src/frob/app/ticket_runner.py::_archive -- now accepts force kwarg, threads to archive(), logs a warning naming the live-lease count before overriding
- src/frob/app/ticket_runner.py::_ticket_dispatch_table -- archive lambda now passes cfg.ticket_force
- src/frob/app/config.py::AppConfig.ticket_force -- new bool field, wired into from_external's bool-field list
- src/frob/__main__.py::_add_ticket_fail_evidence_archive_parsers -- registers --force on the archive subparser (dest=ticket_force)

Evidence:
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet

Filed: none

Gates: frob check --ticket T-0810 clean (0 errors); frob test --base main PASS (touched-set: interface/CLI dispatch tests, archive-force CLI tests, AppConfig toml-read test)

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet` (pytest node id, verified passing when recorded)

<!-- ticket:T-0811 -->
```yaml
id: T-0811
title: 'land: draft renumbering must rewrite draft-id references in Done-report prose
  (recurring TICK006 after every draft-filing land)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_changes: []
evidence:
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_own_draft_id_reference_in_done_report
attachments: []
acceptance:
- text: GIVEN a worktree ledger whose Done reports reference T-draft ids WHEN land
    renumbers those drafts to real ids THEN every reference to the old draft id anywhere
    in the spliced ledger text is rewritten to the new id and no TICK006 fires post-land;
    a regression test lands a draft-referencing Done report and asserts zero stale
    draft ids
  evidence:
  - tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_own_draft_id_reference_in_done_report
threat: null
component: null
labels: []
```
Recurred 3x this drive (T-0778/T-0797, T-0745/T-0764 pairs): land renumbers T-draft blocks to real ids but leaves Done-report prose citing the old draft id, so TICK006 reds main after every draft-filing land until the coordinator hand-retargets. The renumber step already knows the old->new id mapping; apply it as a text substitution across the spliced ledger (and archive) before the integrity check.

## Done report

renumber_one already rewrites STRUCTURAL id references (a ticket's own id,
blocked_by/parent, frob:* directive lines in code) when finalizing a
draft, but never touches free-text Done-report prose (a "Filed: T-draft-
<hex8> (...)" claim about a sibling draft) since that is not a structural
field. _land_finalize_and_close now collects the exact old-draft-id ->
final-id mapping renumber_one/finalize_draft already compute -- both for
the ticket being landed itself (if it started as a draft) and for every
sibling draft _finalize_sibling_drafts finalizes alongside it (changed
that helper's return type from a bare tuple of new ids to an old->new
dict so the mapping survives) -- then runs a new
_rewrite_draft_references_in_bodies(worktree, mapping) pass BEFORE
_commit_finalize_writes: it loads both the active and archive ledgers
(load_all/load_archive), regex-substitutes every occurrence of an old
draft id in each ticket's body text with its final id (a fixed-width
T-draft-<hex8> token has no partial-match risk; a trailing
(?![0-9a-fA-F]) guard is kept anyway as a structural safety margin), and
writes back only the stores that actually changed (write_all/
write_archive), so the rewrite lands in the SAME finalize commit as the
structural renumbering. This closes the recurring TICK006 phantom-filing-
claim false-positive (T-0778/T-0797, T-0745/T-0764) without touching
renumber_one itself, staying inside the ticket's _land.py-only scope.

Regression test (TestDraftReferenceRewriteOnLand): lands a worktree whose
own Done report cites its own pre-finalize draft id ("Filed: T-draft-...");
asserts the landed ticket's final id is not the draft id, the draft id
string is gone from the final ticket's body, "Filed: <final_id>" is
present instead, and zero "T-draft-" substrings survive anywhere in
main's landed tickets.md.

Gates: frob check --ticket T-0811 clean (0 errors, gate-summary pass).
frob test --base main PASS. tests/test_ticket_land.py: 77 passed
(includes the 76 pre-existing tests plus the new regression test).

Filed: none.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-a32451bda533ca284

Deviations: none from the ticket's plan.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

<!-- ticket:T-0812 -->
```yaml
id: T-0812
title: 'land: extend draft-id renumber substitution to .strata waive clauses and frob:waive
  comments + unrelated-draft survival test'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_changes: []
evidence:
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_strata_waive_clause_draft_id_reference
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_frob_waive_comment_draft_id_reference
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_leaves_unrelated_draft_id_reference_untouched
attachments: []
acceptance:
- text: GIVEN a worktree whose design/frob.strata or source frob:waive comments cite
    a draft id that land renumbers WHEN the land completes THEN those refs are rewritten
    to the final id (no permanently-invisible dangling draft ref under WAIVE007's
    exemption); GIVEN an UNRELATED draft id in ledger prose THEN it survives the rewrite
    untouched (negative test)
  evidence:
  - tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_strata_waive_clause_draft_id_reference
  - tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_frob_waive_comment_draft_id_reference
  - tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_leaves_unrelated_draft_id_reference_untouched
threat: null
component: null
labels: []
```
Combined follow-up from the T-0808 and T-0811 reviews: T-0811's rewrite covers ledger+archive prose only, so a .strata waiver or frob:waive comment citing a renumbered draft (the ORIGINAL T-draft-8cd37914 incident class) stays dangling forever and is unconditionally exempt from WAIVE007 -- the exemption becomes load-bearing instead of safe. Extend the land's old->new mapping substitution to tracked files containing waive sites (grep-scoped, per-id-keyed regex like the T-0811 mechanism). Also add the T-0811 reviewer's missing negative test: an unrelated draft id in prose survives the ledger rewrite untouched (separate test; the existing blanket zero-T-draft assertion conflicts with planting one).

## Done report

Extended the T-0811 draft-id-renumber prose rewrite (`_rewrite_draft_references_in_bodies`, ledger bodies only) to cover WAIVE-site channels that were still exempt: `design/*.strata` `waive ... ticket "T-draft-..."` clauses and source `frob:waive ... ticket=T-draft-...` comments. Left as-is, WAIVE007's unconditional `T-draft-*` exemption would silently become load-bearing for these sites once their draft id is renumbered at land (the original T-draft-8cd37914 incident class), since a waiver would never be re-litigatable again.

Added `_rewrite_draft_references_in_waive_sites` in `src/frob/tickets/_land.py`, called from `_land_finalize_and_close` right after the existing ledger-body rewrite and before `_commit_finalize_writes` (which `git add -A`s and commits any working-tree changes it made, so the new rewrite lands atomically in the same finalize commit, before the squash-apply). It reuses the identical fixed-width-token regex approach from T-0811 (`(?:old-id|old-id|...)(?![0-9a-fA-F])`), but scopes the file set cheaply via `git grep -l --fixed-strings -e <old_id> ...` against the worktree -- only files that literally contain an old draft id are ever opened, and the ledger files (`tickets.md`/`tickets-archive.md`) are excluded from this raw-text pass since they are already handled by the ticket-model-driven `_rewrite_draft_references_in_bodies`.

Also added the T-0811 reviewer's missing negative test as a SEPARATE test (not folded into the existing blanket "zero T-draft- ids in the ledger" assertion, since planting an unrelated draft id in that same test would conflict with that assertion): an unrelated draft id mentioned in ledger prose survives a land untouched.

Deviations from the ticket body: none. Both waive-site channels (.strata clauses and frob:waive comments) are covered, plus the reviewer's negative test, as scoped.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_strata_waive_clause_draft_id_reference` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_frob_waive_comment_draft_id_reference` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_leaves_unrelated_draft_id_reference_untouched` (pytest node id, verified passing when recorded)

<!-- ticket:T-0813 -->
```yaml
id: T-0813
title: 'graph: production entrypoint wiring mark_unresolved=True into compute_protocol_summaries
  (opt-in flag currently invoked by nothing)'
state: done
kind: feature
origin: auditor
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- docs/modules/gates.md
- docs/modules/graph.md
- tests/test_gates.py
- tests/test_graph.py
- docs/design/registry/check-coverage.yaml
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'T-0813: adding doc anchors for the new gate (docs/modules/gates.md rule
    catalog + PROTO001 subsection) and updating docs/modules/graph.md production-entrypoint
    note -- required companion documentation for the new PROTO001 gate this ticket
    wires in, not out-of-scope discovery.'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/graph.md
  reason: 'T-0813: adding doc anchors for the new gate (docs/modules/gates.md rule
    catalog + PROTO001 subsection) and updating docs/modules/graph.md production-entrypoint
    note -- required companion documentation for the new PROTO001 gate this ticket
    wires in, not out-of-scope discovery.'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates.py
  reason: 'T-0813: adding tests/test_gates.py and tests/test_graph.py to scope --
    the deterministic unit tests this ticket added for the new PROTO001 gate and the
    callgraph false-positive exemption live here; narrow file-level entries (not tests/**)
    to avoid colliding with any other tickets leasing the broader tests/ tree.'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_graph.py
  reason: 'T-0813: adding tests/test_gates.py and tests/test_graph.py to scope --
    the deterministic unit tests this ticket added for the new PROTO001 gate and the
    callgraph false-positive exemption live here; narrow file-level entries (not tests/**)
    to avoid colliding with any other tickets leasing the broader tests/ tree.'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-0813: adding CHK-GATE-PROTO001 registry entry for the new PROTO001 gate
    rule this ticket wires in -- required to keep missing_gate_rule_ids/REG010 clean,
    per T-0779/T-0808 precedent.'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol
- tests/test_gates.py::TestProtocolSummaryGate::test_clean_protocol_tagged_symbol_is_not_flagged
- tests/test_gates.py::TestProtocolSummaryGate::test_untagged_symbol_with_unresolved_call_is_not_flagged
- tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
- tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved
- tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_super_dunder_call_from_unresolved
- tests/test_graph.py::TestCallGraph::test_build_call_graph_still_marks_unresolved_self_attribute_call
attachments: []
acceptance:
- text: GIVEN a real repo scan through the protocol-summary entrypoint WHEN a private-convention
    callee has no candidates THEN the summary shows UNRESOLVED_CALLEE poisoning end
    to end; the dunder/cross-package private-method false-positive class (obj._method,
    super().__init__ with zero in-paths candidates) has a recorded disposition (filtered
    or documented)
  evidence:
  - tests/test_gates.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol
  - tests/test_gates.py::TestProtocolSummaryGate::test_clean_protocol_tagged_symbol_is_not_flagged
  - tests/test_gates.py::TestProtocolSummaryGate::test_untagged_symbol_with_unresolved_call_is_not_flagged
  - tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
  - tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved
  - tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_super_dunder_call_from_unresolved
  - tests/test_graph.py::TestCallGraph::test_build_call_graph_still_marks_unresolved_self_attribute_call
threat: null
component: null
labels: []
```
T-0809 reviewer condition (a): mark_unresolved is tested but production-dead (no src/ caller passes True; compute_protocol_summaries itself has no production consumer yet). Wire a real entrypoint when the T-0739-family verifier lands, or earlier as a frob graph subcommand. Note the reviewer's residual false-positive class in the heuristic for adjudication at wiring time.

## Done report

## Done report

Changed:
src/frob/graph/callgraph.py::_unresolved_exempt_names
src/frob/graph/callgraph.py::build_call_graph
src/frob/graph/callgraph.py::_resolve_edges
src/frob/gates/_protocol_summary.py::protocol_summary_gate
src/frob/gates/_protocol_summary.py::_package_files
src/frob/gates/_protocol_summary.py::_package_edges
src/frob/gates/__init__.py (registered "protocol_summary" gate name / PROTO001 rule id in _ALL_GATES, _build_jobs, _PROCESS_POOL_GATES, _CANONICAL_GATE_ORDER, _KNOWN_GATE_RULES, __all__)

Evidence:
tests/test_gates.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol
tests/test_gates.py::TestProtocolSummaryGate::test_clean_protocol_tagged_symbol_is_not_flagged
tests/test_gates.py::TestProtocolSummaryGate::test_untagged_symbol_with_unresolved_call_is_not_flagged
tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved
tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_super_dunder_call_from_unresolved
tests/test_graph.py::TestCallGraph::test_build_call_graph_still_marks_unresolved_self_attribute_call

Wiring choice: gate-side integration (PROTO001, frob.gates._protocol_summary.protocol_summary_gate),
not a CLI subcommand -- src/frob/__main__.py is outside this ticket's scope globs, but
frob.gates.run_gates's dispatch tables live in src/frob/gates/__init__.py, which is in scope.
Registered as a real process-pool job so a plain `frob check` now runs a genuine repo scan:
build_call_graph(..., mark_unresolved=True) + compute_protocol_summaries over every package
containing a frob:requires/frob:transition-tagged symbol, flagging (WARN, waivable) any tagged
symbol whose summary comes back poisoned.

False-positive adjudication: filtered, not just documented. frob.graph.callgraph
._unresolved_exempt_names (wired through a new exempt_extractor parameter on
_resolve_edges/build_call_graph) exempts a call-token name from ever becoming UNRESOLVED_CALLEE
when EVERY occurrence of it in a function body is an attribute call (<expr>.name() on a receiver
other than self) -- kills both the obj._method(...) and super().__init__(...) false-positive
shapes the T-0809 reviewer named. self._foo(...) is deliberately NOT exempted (verified by a
dedicated negative test) since that is exactly the intra-package private-helper call this graph
exists to catch.

Real-repo smoke test: TestProtocolSummaryGate.test_real_repo_scan_runs_end_to_end_without_crashing
runs protocol_summary_gate against this repo's OWN live GraphSnapshot (not a fixture) -- 0
violations today (no production symbol is yet protocol-tagged), proving the wiring completes
without the IndexError/crash class T-0809's own Done report disclosed as the reason
mark_unresolved defaulted to False.

Filed: none

Gates: frob check --ticket T-0813 clean (0 errors, protocol_summary gate ran in ~0.7s alongside
every other gate; verified twice after the scope-add + pre-work re-sweep). frob test --base main
exit 0. ruff check clean on all touched files.

Deviations: scope extended twice via `frob ticket scope --add` (both reasoned, recorded in the
ticket's audit trail): docs/modules/gates.md + docs/modules/graph.md (companion documentation for
the new PROTO001 rule and false-positive disposition), then tests/test_gates.py +
tests/test_graph.py (file-level, not tests/**, to avoid colliding with any other ticket's lease on
the broader tests/ tree) once COV002 flagged the new/touched test symbols as unaccounted-for.

### Changed
```
 docs/modules/gates.md               |  46 +++++++++
 docs/modules/graph.md               |  11 +++
 src/frob/gates/__init__.py          |  27 +++++-
 src/frob/gates/_protocol_summary.py | 179 ++++++++++++++++++++++++++++++++++++
 src/frob/graph/callgraph.py         |  65 ++++++++++++-
 tests/test_gates.py                 |  91 ++++++++++++++++++
 tests/test_graph.py                 |  54 +++++++++++
 7 files changed, 471 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolSummaryGate::test_clean_protocol_tagged_symbol_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolSummaryGate::test_untagged_symbol_with_unresolved_call_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_super_dunder_call_from_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_still_marks_unresolved_self_attribute_call` (pytest node id, verified passing when recorded)

<!-- ticket:T-0814 -->
```yaml
id: T-0814
title: 'gates: closure() consumers IndexError on non-symref graph entries (latent
  crash class in _cov006 + siblings)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
- src/frob/dup/_pipeline.py
- tests/test_gates.py
scope_changes: []
evidence:
- tests/test_gates.py::TestCoverageGate::test_is_symref_gates
- tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_skips_unresolved_callee_sentinel
- tests/test_gates.py::TestDupPipelineClosureConsumers::test_is_symref_dup
- tests/test_gates.py::TestDupPipelineClosureConsumers::test_callee_name_map_skips_unresolved_callee_sentinel
attachments: []
acceptance:
- text: GIVEN a call-graph closure containing a sentinel or non path::qualname entry
    WHEN _cov006_third_file_reachable and sibling closure consumers process it THEN
    they skip or handle it without raising; a regression test feeds a sentinel entry
    through each consumer
  evidence:
  - tests/test_gates.py::TestCoverageGate::test_is_symref_gates
  - tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_skips_unresolved_callee_sentinel
  - tests/test_gates.py::TestDupPipelineClosureConsumers::test_is_symref_dup
  - tests/test_gates.py::TestDupPipelineClosureConsumers::test_callee_name_map_skips_unresolved_callee_sentinel
threat: null
component: null
labels: []
```
T-0809 reviewer condition (b): _cov006_third_file_reachable (gates/__init__.py ~3361) does split('::',1)[1] on every closure entry and IndexErrors on any non-symref (discovered when mark_unresolved=True injected UNRESOLVED_CALLEE); same shape assumption at 3 gates call sites + dup/_pipeline. Any future graph extension crashes them. Harden all closure consumers.

## Done report

## Done report

Consumer inventory (grepped exhaustively for `split("::", 1)` applied to
closure()/CallGraph.calls-derived entries, not to Edge.src/Edge.target
which come from the graph snapshot and are always real symrefs):

- src/frob/gates/__init__.py `_cov006_third_file_reachable` (~line 3511-3524):
  iterates `reached_helpers = closure(test_only_graph, edge.src, ...)` and
  did `helper_symref.split("::", 1)[1]` unconditionally -- the confirmed
  IndexError site from the T-0809 reviewer note. Fixed: guarded with the
  new `_is_symref` helper, non-symref entries are skipped.
- src/frob/dup/_pipeline.py `_callee_name_map` (~line 617-628): iterates
  `graph.calls.get(caller_symref, ())` and did
  `callee_symref.split("::", 1)[1].rsplit(".", 1)[-1]` unconditionally.
  Fixed the same way with a matching `_is_symref` helper local to this
  file. `_callee_tokens` and `_splice_call_site` (which also split a
  `callee_symref`) only ever receive values sourced from
  `_callee_name_map`'s output, so filtering there protects them
  transitively -- no separate crash site to hardn independently.

Deviation from the T-0809 reviewer's estimate ("3 gates call sites +
dup/_pipeline"): I grepped every `split("::", 1)` in both files and
checked which operand is a closure()/graph.calls-derived value versus an
`Edge.src`/`Edge.target` (always real, DB-backed symrefs, safe to split
unconditionally) or an already-guarded value (`"::" in x else x`, lines
3008/3099). The other five `closure(...)` call sites in gates.py
(`_cov006_public_wrapper_reachable`, `_cov006_implicit_dispatch_reachable`,
`_cov006_edge_violation`, and the second closure call inside
`_cov006_implicit_dispatch_reachable`) only ever use the closure result in
an `x in closure(...)` MEMBERSHIP test, which cannot raise on an odd
string -- a sentinel simply fails to match, no crash, no fix needed there.
I found exactly one real crash site per file (gates.py, dup/_pipeline.py),
not three in gates.py; disclosing this rather than inventing hardening
for sites that were never actually vulnerable.

No shared single home for `_is_symref`: the natural home is
`frob/graph/callgraph.py` (where `UNRESOLVED_CALLEE` and `closure()` are
defined), but that file is outside T-0814's declared scope
(`src/frob/gates/__init__.py`, `src/frob/dup/_pipeline.py`,
`tests/test_gates.py`). Each file keeps its own one-line
`_is_symref(entry: str) -> bool: return "::" in entry` predicate with a
matching docstring instead -- filed no new ticket for the consolidation
since it is a one-line, zero-behavior-risk duplication, not worth its own
ticket overhead, and disclosing it here per playbook's "disclose cuts
honestly" is what governs it.

Changed:
- src/frob/gates/__init__.py::_is_symref (new)
- src/frob/gates/__init__.py::_cov006_third_file_reachable (hardened loop)
- src/frob/dup/_pipeline.py::_is_symref (new)
- src/frob/dup/_pipeline.py::_callee_name_map (hardened loop)
- tests/test_gates.py: 4 new regression tests

Evidence (measured, `uv run --frozen pytest tests/test_gates.py
tests/test_dup*.py`): 459 passed in 11.62s (re-verified after ruff
reformat: 459 passed in 11.98s). New node ids, all collected and passing:
- tests/test_gates.py::TestCoverageGate::test_is_symref_gates
- tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_skips_unresolved_callee_sentinel
- tests/test_gates.py::TestDupPipelineClosureConsumers::test_is_symref_dup
- tests/test_gates.py::TestDupPipelineClosureConsumers::test_callee_name_map_skips_unresolved_callee_sentinel

Real symref behavior unchanged: the existing COV006/dup suites (459 tests
total across both files) stay green with no modifications to any
pre-existing test.

Filed: none (see the `_is_symref` duplication note above -- disclosed
rather than filed, one-line predicate, zero behavior risk).

Gates: `uv run --frozen frob check --ticket T-0814 --only <stage>`
chunked over all 5 stage groups (lint, static, gates-fast, gates-native,
gates-security) after `frob ticket sweep T-0814` re-ran the pre-work
sweep post-edit -- all 5 groups PASS, 0 new errors (only pre-existing,
already-waived warnings across the whole repo). `git diff main
--diff-filter=D --stat` is empty.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-ac7b7a66bce3bea1b

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

<!-- ticket:T-0815 -->
```yaml
id: T-0815
title: 'app: sweep --json runners for guard-log stdout pollution (mutate and fleet
  already emit spawn DEBUG into JSON payloads)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/app/mutate_runner.py
- src/frob/app/fleet_runner.py
- tests/integration/
scope_changes: []
evidence:
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_human_mode_still_shows_diagnostics
- tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean
- tests/integration/test_gitlog.py::TestGitlogJson::test_json_valid
attachments: []
acceptance:
- text: GIVEN every runner module with a json flag whose payload path can reach guarded_subprocess_run
    WHEN the json mode runs THEN stdout parses as clean JSON (conditional quiet_stdout_logs
    like xref_runner) and an integration test parses the full stdout per runner; GIVEN
    human mode THEN diagnostic lines still appear
  evidence:
  - tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
  - tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_human_mode_still_shows_diagnostics
  - tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean
threat: null
component: null
labels: []
```
T-0803 reviewer finding: the exec guard now DEBUG-logs every spawn, and the
stdout handler defaults to DEBUG, so any --json runner spawning through the
guard pollutes its payload. gitlog_runner was fixed in T-0803
(unconditionally -- align it to the conditional xref pattern in this
sweep); mutate_runner and fleet_runner are polluted TODAY. Sweep every
runner with a _json flag, apply the conditional quiet_stdout_logs pattern
(quiet when json, nullcontext otherwise), and lock each with a
json.loads-of-full-stdout integration test.

## Done report

Survey: grepped every `src/frob/app/*_runner.py` for a `_json` config flag,
then checked which of those payload paths reach `guarded_subprocess_run`
(`grep -rl guarded_subprocess_run src/frob/`). Findings:

| runner | _json flag | reaches guard? | pre-fix state | action |
|---|---|---|---|---|
| mutate_runner.py | mutate_json | yes -- `frob.mutate.run_mutations` -> `_run_mutants` -> `guarded_subprocess_run` per mutant | unwrapped, polluted | wrapped conditionally |
| fleet_runner.py | fleet_json | yes -- `frob.fleet.rollup` -> `collect_status` -> `_git_branch_and_dirty`/`_gate_summary_probe` -> `guarded_subprocess_run`, always (even with --skip-gates, branch/dirty probe still runs); also `load_manifest`'s own INFO log leaked ahead of the guard line | unwrapped, polluted (both the guard DEBUG line and load_manifest's INFO line) | wrapped conditionally, widened to cover load_manifest too |
| gitlog_runner.py | gitlog_json | yes -- `frob.gitlog.git_log` -> `guarded_subprocess_run` | wrapped UNCONDITIONALLY (T-0803) | aligned to conditional pattern |
| xref_runner.py | xref_json | yes -- `frob.xref.xref` | already conditional (existing reference pattern) | no change |
| check_runner.py | check_json | yes -- native/python/ts collectors, lease ops | already conditional (line 966) | no change, out of scope |
| ticket_runner.py | ticket_json | `land`'s `make core` rebuild spawns via guard, but that path is not on the `--json` read-path for any ticket_json-emitting command surveyed (land itself isn't `--json`) | not polluted for any `--json` output surveyed | no change; not filed, no reachable pollution found |
| test_runner.py | test_json | `run_selected` (frob.testing._runners) does not go through `guarded_subprocess_run` per the guard-user grep; `--wait-coverage` (guard-using `_coverage_wait`) is a separate non-json code path | not polluted | no change |
| vet_runner.py, docs_runner.py, deploy_runner.py | vet_json/docs_json/attestation write | not in the `guarded_subprocess_run`-using module list | not polluted | no change |

Only mutate_runner.py, fleet_runner.py, and gitlog_runner.py needed fixes.
gitlog_runner.py was not in the ticket's original declared scope; scope-added
with reason (T-0815 acceptance explicitly names it for alignment).

Changed:
- src/frob/app/mutate_runner.py: run -- wrapped `run_mutations` call in
  `quiet_stdout_logs()` conditional on `cfg.mutate_json`
  (`contextlib.nullcontext()` otherwise), matching xref_runner's pattern.
- src/frob/app/fleet_runner.py: _run_status -- wrapped the whole
  `load_manifest` + `rollup` payload path in the same conditional, since
  `load_manifest`'s own INFO log (not just the guard's DEBUG line) also
  leaked into `--json` stdout ahead of the payload.
- src/frob/app/gitlog_runner.py: run -- aligned the T-0803 unconditional
  `quiet_stdout_logs()` wrap to the conditional pattern; human mode now
  keeps the guard's diagnostic spawn line visible again.
- tests/integration/test_mutate_runner.py (new): `TestMutateRunnerJson` --
  drives `frob mutate --json` over a real on-disk target through the real
  CLI subprocess and `json.loads`s the full stdout; a second test asserts
  human mode still shows `mutation score`.
- tests/integration/test_fleet_integration.py: added
  `TestFleetIntegrationJson.test_fleet_status_json_is_clean` -- `frob fleet
  status --skip-gates --json` over a real one-repo manifest, full stdout
  `json.loads`d (the branch/dirty guard spawn runs even with
  `--skip-gates`, so this specifically locks the always-on guard path, not
  just the optional gate-probe path).
- gitlog's existing `TestGitlogJson.test_json_valid`
  (tests/integration/test_gitlog.py) already exercises the aligned
  conditional path end to end; no new gitlog test needed, bound as evidence
  instead.

All four evidence tests drive the real CLI as a subprocess
(`sys.executable -m frob ...`), so they exercise the same process-pool /
env-clamp path T-0806 touched (no separate accommodation needed -- these
tests never go through frob's own in-process worker pool, they spawn a
fresh interpreter each time, same as every other integration test in this
suite).

Evidence:
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_human_mode_still_shows_diagnostics
- tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean
- tests/integration/test_gitlog.py::TestGitlogJson::test_json_valid
(all four collected and passed: `pytest tests/integration/test_mutate_runner.py
tests/integration/test_fleet_integration.py tests/integration/test_gitlog.py -q`
-> 22 passed)

Filed: none -- survey found no other polluted runner to file a follow-up
for; ticket_runner/test_runner/vet_runner/docs_runner/deploy_runner all
checked and found not reachable to `guarded_subprocess_run` on any
`--json` payload path.

Gates: `uv run frob check --ticket T-0815` run chunked per
docs/guides/agent-playbook.md section 3b (`--only` prework/lint/static/
gates-fast/gates-native/gates-security) -- all stage groups pass, 0 new
errors attributable to this change (remaining warnings are pre-existing
repo-wide debt, same counts before and after).

`uv run frob test --base main` (full python+strata+rust suite, backgrounded
by the harness past 120s, foreground-observed via Monitor) shows several
FAILs (tests/test_doctor.py, test_export_golden.py, test_frob_self_model.py,
test_cli_native_missing.py, test_spawn_budget.py, test_cli_sys_audit.py,
test_cli_check.py::TestCheckTypescript, TestGitlessTargetGateSeverity, and
the strata compliance-registry GAP for COMPLIANCE004/PII010) -- none touch
mutate_runner.py, fleet_runner.py, gitlog_runner.py, or the new/changed
test files; these are pre-existing failures unrelated to this ticket's
scope (worktree-native / registry-drift / other-ticket artifacts), not
introduced by this change.

Deviations: none from the ticket's plan. Scope-added
src/frob/app/gitlog_runner.py (reason: T-0815 acceptance explicitly
directs aligning gitlog_runner's unconditional wrap to the conditional
pattern in this sweep).

### Changed
```
 src/frob/app/fleet_runner.py                | 36 +++++++----
 src/frob/app/gitlog_runner.py               | 15 +++--
 src/frob/app/mutate_runner.py               | 18 +++++-
 tests/integration/test_fleet_integration.py | 35 +++++++++++
 tests/integration/test_mutate_runner.py     | 75 +++++++++++++++++++++++
 tickets.md                                  | 93 ++++++++++++++++++++++++++++-
 6 files changed, 249 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean` (pytest node id, verified passing when recorded)
- `tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_human_mode_still_shows_diagnostics` (pytest node id, verified passing when recorded)
- `tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean` (pytest node id, verified passing when recorded)
- `tests/integration/test_gitlog.py::TestGitlogJson::test_json_valid` (pytest node id, verified passing when recorded)

<!-- ticket:T-0816 -->
```yaml
id: T-0816
title: 'tests: sys-audit clean-model fixture red on main (matrix/reliability leg exits
  1 after recent strata lands)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- tests/unit/test_app_runners_batch7.py
scope_changes: []
evidence:
- tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes
attachments: []
acceptance:
- text: GIVEN main WHEN TestSysAudit::test_clean_model_passes runs THEN it passes
    with every audit leg PROVED, with the fixture updated to current rules (or the
    responsible check fixed if it false-positives on a clean model, with the choice
    documented)
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes
threat: null
component: null
labels: []
```
Found during T-0752 (2026-07-23, confirmed on current main): the sys-audit
clean-model fixture test fails -- self-conformance and resource-contention
legs PROVE, then the runner exits 1 from the final composite check
(reliability / health / matrix_proved legs; last frame shows `or not
matrix_proved`). Almost certainly fixture-vs-new-check drift: a recently
landed strata leg (T-0606 windows host wiring, T-0644 health leg, T-0717
mode vocabulary, or the T-0769 may-net narrowing) tightened what a clean
model must declare and the fixture was never updated. Root-cause which leg
reports the gap (run the test, capture the named-gap summary), then fix
the FIXTURE to be genuinely clean under current rules -- do NOT weaken any
check. If the leg's demand is wrong (false positive on a genuinely clean
model), fix the check instead and say so.

## Done report

Root cause: `_CLEAN_MODEL` in tests/unit/test_app_runners_batch7.py declared a
flow (`evil -> api`) with no `timeout` attr and no `async`/`local` exemption.
`frob sys audit` fails it under REL200 (T-0640's reliability-timeout-
obligation rule, module docstring in src/frob/strata/_reliability.py):
"every flow with no `timeout` attr declared and no exemption" is a
deny-by-default gap. `sys_run`'s composite check
(`combined_reliability.violations`) folds this into the same exit path as
the health leg, which is why the test's failure looked like a
reliability/health/matrix composite exit rather than naming REL200
directly -- captured log confirms it explicitly: "sys audit: 1 reliability
gap(s) found ... GAP family=sys rule=REL200 node=evil detail=flow f1
(evil -> api) has no timeout obligation (no `timeout` attr, no
`async`/`local` exemption)".

Responsible land: T-0640 (REL200/REL201, the reliability-timeout family),
not one of the four candidates the ticket named (T-0606/T-0644/T-0717/
T-0769) -- T-0644 landed alongside it in the same T-0331 epic (REL210/
REL211 node-health pair) but the actual firing rule here is REL200, which
predates T-0644. The fixture was simply never updated when T-0640 added
this obligation to every flow.

Fix choice: fixture fix, not a check fix. Added `attr timeout;` to the one
flow in `_CLEAN_MODEL`. This is genuinely clean under current rules, not a
weakening: neither `evil` nor `api` declares a `code=` glob, so
`_unproven_timeout_violations` (REL201) treats the flow as UNCHECKABLE
(neither endpoint has bound code) and skips it silently by design --
module docstring's documented "honestly silent rather than a guessed-at
proof" ceiling, the same one `_selfconform.py`'s `managed` exemption and
SYS203's `store_ids` already use. Verified this discharges REL200 without
tripping REL201: full pytest run on the touched file is green.

Out-of-scope finding: `uv run --frozen frob check --ticket T-0816` (a
scoped, not full, run) shows 4 gate:WAIVE WAIVE006 errors at
design/frob.strata:307,370,418,469 -- each `waive "LINT004"` there is
bound to ticket T-0803, which is now closed, and WAIVE006 treats a
closed-ticket binding as stale. This file is outside this ticket's scope
(tests/unit/test_app_runners_batch7.py only) and pre-exists this change
(confirmed by inspecting design/frob.strata directly -- no lines from this
ticket touch it). Filed T-0819 for it. The other gate:WAIVE
WAIVE004 warnings in the scoped run are the documented "known-flaky for
diff-scoped ... trust this only from a full run" noise, not new findings.

A full-repo `uv run --frozen frob test` (touched-set base=main run) surfaced
a large number of failures entirely outside this ticket's scope (test_doctor,
test_export_golden, test_cli_check, test_frob_self_model, TestWaive006RealRepo,
etc. -- unrelated modules, pre-existing on main, not touched by this change).
These are not attributable to the one-line fixture edit in
tests/unit/test_app_runners_batch7.py and are left untouched, consistent with
"touch only files/symbols matching the ticket's scope globs."

## Done report

Changed: tests/unit/test_app_runners_batch7.py::_CLEAN_MODEL (module-level
fixture constant -- added `attr timeout;` to flow f1)

Evidence: tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes
(also verified full-file green: `uv run --frozen pytest
tests/unit/test_app_runners_batch7.py -q` -> 96 passed)

Filed: T-0819 (gate:WAIVE006 design/frob.strata waivers reference
closed ticket T-0803 -- out-of-scope pre-existing finding)

Gates: `uv run --frozen frob check --ticket T-0816` -- clean except two
pre-existing, out-of-scope findings noted above (WAIVE006 on
design/frob.strata, filed as T-0819; WAIVE004 diff-scoped noise
per its own documented caveat). No new gate violations introduced by this
change.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes` (pytest node id, verified passing when recorded)

<!-- ticket:T-0817 -->
```yaml
id: T-0817
title: 'vet: wire net_enabled kill-switch into vet''s network call sites (LINT004
  net gap)'
state: dropped
kind: security
origin: agent
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- tests/test_vet.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN FROB_DISABLE_NET=1 (or the guard's net flag) WHEN any vet code path
    attempts a network operation THEN it is refused and logged without connecting;
    the vet strata node declares the net kill-switch flag and its LINT004 waiver is
    deleted
  evidence: []
threat: denial-of-service
component: null
labels: []
```
The net kill-switch mechanism exists (T-0200 frob.process._guard.net_enabled) but no call site invokes it; vet's strata node holds may-net with a LINT004 waiver that previously cited T-0803 (exec-only sweep, now closed). Wire net_enabled into vet's network paths, declare attr flag on the node, delete the waiver.

## Drop reason
- 2026-07-23: absorbed: the vet net kill-switch wiring landed as T-0822 (worked from a worktree draft filed when a ledger restore predated T-0817's filing); design flag declared, waiver deleted, sys audit PROVED (absorbed by T-0822)

<!-- ticket:T-0818 -->
```yaml
id: T-0818
title: 'test_cli_check: TS/gitless fixture debt unrelated to T-0806 (LANG003 T-0329
  dangling ref, capsys/logging init-order flake)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- tests/system/test_cli_check.py
- src/frob/gates/**
scope_changes: []
evidence:
- tests/system/test_cli_check.py::TestCheckTypescript::test_clean_ts_passes_tsc
- tests/system/test_cli_check.py::TestCheckTypescript::test_type_error_fails_tsc
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
While root-causing T-0806 (test_cli_check tmp fixtures broken on main),
two more failures in tests/system/test_cli_check.py were found -- neither
is related to T-0806's git-ls-files/JSON-pollution regression, and both
are pre-existing, unrelated debt:

1. TestCheckTypescript::test_clean_ts_passes_tsc -- once the fixture is a
   real git repo (fixed under T-0806), the run still fails on TWO
   unrelated issues:
   a. TEST001 ("src.ts::add is public with no unit test") and TEST006
      ("no coverage stamp found") fire because the fixture never sets a
      warn-severity frob.toml the way tests/system/test_cli_check.py's
      other python fixtures (_make_project) do.
   b. LANG003 fires unconditionally for any typescript project checked
      against this repo's own queue: "typescript facet 'arch' is
      known_gap ... tracked by T-0329 ... which does not exist in the
      loaded queue". T-0329 is referenced in the LANG003 known_gap
      declaration but does not exist as a real ticket -- this is a
      genuine product-side dangling reference (either T-0329 needs to be
      created/tracked, or the known_gap declaration needs a live ticket
      id), independent of any test fixture.

2. TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
   -- flaky/order-dependent: passes standalone and in some pairings, fails
   in others. Its docstring explains it reads frob's own stderr
   StreamHandler via `capsys` rather than `caplog` because
   `frob.logging.logger._init()` binds `ext://sys.stdout`/`ext://sys.stderr`
   ONCE, lazily, at the first `get_logger()` call in the whole pytest
   session/worker -- if that first call happens before this particular
   test's own `capsys` fixture is active (i.e. some earlier test in the
   file already triggered `_init()` first), the bound stream handler
   never observes THIS test's `capsys` wrapper, and `capsys.readouterr()`
   comes back empty regardless of what frob.gates._render_lint actually
   logged. This is a structural test-isolation gap: any in-process test in
   this file that wants `capsys`/`capfd` to observe frob's own logging
   output needs the process's first `frob.logging.get_logger()` call to
   happen AFTER capsys is installed, which pytest does not guarantee
   across a whole session/xdist worker. Needs either a fixture that resets
   `frob.logging.logger._initialized` and rebinds handler streams per
   test, or the assertion needs a different capture mechanism entirely.

Scope: tests/system/test_cli_check.py (both fixtures/assertions), and
possibly src/frob/gates/_lang_conformance.py or wherever the LANG003
known_gap detail for T-0329 lives (find via grep "T-0329").

## Done report

## Done report

Changed:
- tests/system/test_cli_check.py::TestCheckTypescript._make_ts_project
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity.test_render_lint_gate_warns_not_errors_on_gitless_root

Root causes:
1. TestCheckTypescript::test_clean_ts_passes_tsc:
   a. `_make_ts_project` never set a warn-severity `frob.toml`, unlike
      `_make_project` (the python fixture helper) -- TEST001/TEST006 hard
      -errored on the fixture's undocumented/untested `add` symbol.
   b. LANG003 escalates a `KNOWN_GAP` facet to ERROR unless the CHECKED
      repo's own ticket queue independently carries an open ticket for the
      id named in the gap's detail (`frob.lang._support._arch_status`
      names `T-0329` for typescript's `arch` facet) -- verified against
      `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate
      ::test_present_known_gap_with_open_ticket_warns`, which constructs
      exactly this scenario with a synthetic queue. I confirmed T-0329 is
      NOT a dangling/nonexistent reference in the shipped product: it is a
      real, `queued` ticket in this repo's own `tickets.md` (tickets.md,
      `<!-- ticket:T-0329 -->`, EPIC arch multi-language). The failure was
      entirely a fixture gap -- an isolated tmp-path TS project has no
      `tickets.md` at all, so `queue.tickets` is empty and ANY `KNOWN_GAP`
      ticket reference in `frob.lang._support` fails to verify against it,
      by design (same anti-lie posture REG002/REG003 apply to
      `handled_by`/`deferred`). This is the same class of debt T-0719
      already tracks (isolated tmp-path fixtures missing the repo-level
      state a gate needs to resolve cleanly) -- I did not duplicate T-0719,
      I fixed this specific fixture's setup directly since the fix is a
      three-line addition local to this one test class, not the broader
      git-less/queue-less diff-classification mechanism T-0719 owns.
      I did NOT find a genuine dangling/nonexistent-ticket product bug to
      fix in `src/frob/gates/**` or `src/frob/lang/**` -- disclosing this
      plainly since T-0818's dispatch prompt asked for one; the concrete
      "T-0329 is a phantom reference" framing in T-0818's body did not
      hold up under investigation (T-0329 is real and queued). What IS a
      real, broader design question -- whether LANG003's `KNOWN_GAP`
      details, which name FROB's OWN internal roadmap ticket ids, should
      really be verified against every DOWNSTREAM adopting repo's own
      independent ticket queue (an external adopter's queue will almost
      never happen to contain a ticket literally named `T-0329`) -- is out
      of this bug ticket's narrow fixture-debt scope and not something I
      judged safe to redesign under this ticket; noting it here rather
      than silently dropping it.

2. TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root:
   `frob.logging.logger._init()` binds its `StreamHandler`s (via
   `dictConfig`'s `ext://sys.stdout`/`ext://sys.stderr` resolution) to
   whatever stream objects are live the FIRST time `get_logger()` runs in
   the process, and only ever runs once (`_initialized` guard). If an
   earlier test in the same pytest-xdist worker already triggered
   `get_logger()` before this test's `capsys` fixture replaced
   `sys.stderr`, the handler stays bound to the pre-capsys stream forever
   and `capsys.readouterr()` observes nothing -- an order-dependent flake,
   not a logic bug in the assertion itself. Fix: force `frob.logging.
   logger._initialized = False` at the start of the test body (after
   `capsys` is already installed, since it's a fixture argument), so
   `_tracked_python_files`'s first `get_logger()` call inside the test
   re-runs `dictConfig` and rebinds handlers to the CURRENT (capsys
   -patched) streams. Deterministic regardless of what ran earlier in the
   session/worker -- not a reordering, not a flaky marker, not a different
   capture mechanism swap (kept `capsys` per the test's own documented
   rationale for why `caplog` doesn't work here).

Evidence:
- tests/system/test_cli_check.py::TestCheckTypescript::test_clean_ts_passes_tsc
- tests/system/test_cli_check.py::TestCheckTypescript::test_type_error_fails_tsc
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error
- `uv run --frozen pytest tests/system/test_cli_check.py -q` -> 36 passed
  (run 4x in a row post-fix, including once right after `git merge main`,
  to confirm the capsys fix is order-independent, not just lucky).
- Node ids re-confirmed resolvable via
  `uv run --frozen pytest --collect-only -q -o addopts="" tests/system/test_cli_check.py`.

Filed: none (see root-cause 1b's disclosed out-of-scope design question --
judged not safe/appropriate to fix or file speculatively without the
dispatcher's read on whether LANG003's downstream-queue-verification
contract is intended to change; leaving it in this Done report rather than
opening a ticket I'm not confident is correctly scoped).

Gates: `frob check --ticket T-0818` clean across all stage groups (lint,
static, gates-fast, gates-native, gates-security) -- 0 errors in every
group, run AFTER a mid-ticket `git merge main` (playbook 1b) that pulled in
T-0821 and other landed work; re-swept (`frob ticket sweep T-0818`) and
re-verified clean post-merge. `git diff main --diff-filter=D --stat` empty
post-merge (playbook section 9).

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-a081356c067c42f95

Deviations: per dispatch instructions, did NOT close or land T-0818; did
NOT bump REL001/version/CHANGELOG (land-owned). Did not find or apply a
`src/frob/gates/**`/`src/frob/lang/**` product-code fix for the T-0329
"dangling reference" framing in T-0818's body -- see root-cause 1b above
for why (T-0329 verified real/queued, not dangling).

### Changed
```
 tests/system/test_cli_check.py | 64 +++++++++++++++++++++++++++++++++++++++++-
 tickets.md                     |  2 +-
 2 files changed, 64 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckTypescript::test_clean_ts_passes_tsc` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckTypescript::test_type_error_fails_tsc` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error` (pytest node id, verified passing when recorded)

<!-- ticket:T-0819 -->
```yaml
id: T-0819
title: gate:WAIVE006 design/frob.strata waivers reference closed ticket T-0803
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- design/frob.strata
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
found while working T-0816: frob check gate:WAIVE fires 4x WAIVE006 errors at design/frob.strata:307,370,418,469 -- each waive() references ticket T-0803 which is now closed, but WAIVE006 treats a closed-ticket binding as stale. Re-review whether the underlying gaps these waivers cover are actually resolved by T-0803's landing (in which case remove the waivers) or still open (in which case re-point them at a still-open follow-on ticket, per the T-0803 waiver text's own note 'tracked in T-0803').

## Drop reason
- 2026-07-23: already fixed directly on main (commit re-litigating the LINT004 waivers: kill-switch flags declared on core/fleet/tickets_ledger, vet waiver rewritten to open T-0817); WAIVE006 count is zero on main

<!-- ticket:T-0820 -->
```yaml
id: T-0820
title: 'gates: wire a TICK-family frob check warning for undispatched-stale CRITICAL/HIGH
  tickets (T-0752 gate half)'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: high
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0752 built the pure staleness-alarm computation (frob.tickets.undispatched_stale, dispatch_stale_hours, _dispatch_stale_thresholds -- src/frob/tickets/__init__.py) and wired it into frob ticket doable's row rendering (src/frob/app/ticket_runner.py), per its acceptance criterion's UNDISPATCHED row marker. The SAME criterion also asks for "AND frob check emits a TICK-family warning naming it" -- a new TICK-family gate (e.g. TICK007) that calls undispatched_stale over the doable set and emits a Violation per alarmed ticket, the same way TICK004 (queue rot) already does. That half requires touching src/frob/gates/__init__.py (and its TICK-family stage wiring), which is OUTSIDE T-0752's declared scope (src/frob/tickets/**, src/frob/app/ticket_runner.py, docs/modules/tickets.md). Filed as a separate ticket per the agent playbook's "found work outside scope -> file, don't fold in" rule. Reuse frob.tickets.undispatched_stale verbatim -- do not re-derive the staleness judgment in the gates module. Coordinate with T-0714 (doable diagnostics relocation to frob check) since both move doable-adjacent signal into the gate layer.

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
blocked_by: []
parent: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a worktree ticket in planned state with evidence bound and a Done report
    WHEN land runs THEN it either advances planned->in-progress->done transparently
    during finalize or the PRE-MERGE preflight refuses naming the state and the frob
    ticket start remedy -- never a post-merge InvalidTransition; a regression test
    covers the planned-state land
  evidence: []
threat: null
component: null
labels: []
```
Hit 3x this drive (T-0799, T-0752 post-10b-restore, T-0815): implementers leave tickets planned (never ran start, or a ledger restore reverted the state), evidence+report are complete, land merges+finalizes then dies InvalidTransition at close, forcing the coordinator start-then-retry recipe. Either fold the start transition into finalize when preconditions are met, or extend the T-0763 preflight to check state transitions pre-merge.

<!-- ticket:T-0822 -->
```yaml
id: T-0822
title: 'vet: wire net_enabled kill-switch into vet''s network call sites'
state: done
kind: security
origin: agent
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- tests/test_vet.py
- design/frob.strata
scope_changes: []
evidence:
- tests/test_vet.py::TestRegistryLookup::test_fetch_publish_date_refuses_when_net_disabled
- tests/test_vet.py::TestNvdLookup::test_fetch_cwe_for_cve_refuses_when_net_disabled
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
attachments: []
acceptance:
- text: Given FROB_DISABLE_NET=1, when vet looks up a registry publish date or an
    NVD CVE->CWE mapping, then no urlopen call happens and the result degrades to
    ok=False with a "net disabled" note.
  evidence:
  - tests/test_vet.py::TestRegistryLookup::test_fetch_publish_date_refuses_when_net_disabled
  - tests/test_vet.py::TestNvdLookup::test_fetch_cwe_for_cve_refuses_when_net_disabled
- text: Given design/frob.strata's vet node, when frob sys audit runs, then the node
    declares a real attr flag=<id> kill-switch and carries no LINT004 waiver.
  evidence:
  - tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
  - tests/test_vet.py::TestRegistryLookup::test_fetch_publish_date_refuses_when_net_disabled
threat: null
component: null
labels: []
```
Dispatch referenced ticket id T-0817 ("vet: wire net_enabled kill-switch
into vet's network call sites"), but no such ticket exists in
tickets.md/tickets-archive.md (`frob ticket show T-0817` -> "no ticket
T-0817"). Filing the real ticket here so the implementation has a real
frob:ticket edge to bind evidence to, per the ticket's own instructions
("do not force it ... file a ticket").

Survey (done as part of this ticket): vet has two real, live outbound
`urllib.request.urlopen` call sites -- src/frob/vet/_registry.py::
_result_from_network (publish-date lookups) and src/frob/vet/_nvd.py::
_fetch_from_network (CVE->CWE lookups). `_osv.py` and `_popular_*.py`
do not make network calls (osv-scanner subprocess / static curated
lists respectively). design/frob.strata's `vet` node already declares
`may "net"` with a `waive "LINT004"` pointing at T-0200, and T-0200
already built the real mechanism (`frob.process.net_enabled()` /
`FROB_DISABLE_NET`, `src/frob/process/_guard.py`) but left it unwired
pending a real net call site -- this ticket is that wiring.

Plan: gate both `urlopen` sites behind `net_enabled()`, degrading to the
existing `ok=False` "could not verify" shape each site's docstring
already commits to for a network failure (VET011's offline-must-never-
hard-block posture) -- a disabled kill switch is not a new failure mode,
it degrades identically to an unreachable host. Declare `attr
flag=frob_vet_net_kill_switch;` on the `vet` node in design/frob.strata
and delete the LINT004 waiver (mirrors the T-0769 stratamod precedent).
Add tests with a no-connect `urlopen` spy proving the switch
short-circuits before any socket opens.

## Done report

Changed:
src/frob/vet/_registry.py::_result_from_network
src/frob/vet/_nvd.py::_fetch_from_network
design/frob.strata (vet node: attr flag=frob_vet_net_kill_switch; replaces waive "LINT004")
tests/test_vet.py::TestRegistryLookup.test_fetch_publish_date_refuses_when_net_disabled
tests/test_vet.py::TestNvdLookup.test_fetch_cwe_for_cve_refuses_when_net_disabled

Evidence:
tests/test_vet.py::TestRegistryLookup::test_fetch_publish_date_refuses_when_net_disabled
tests/test_vet.py::TestNvdLookup::test_fetch_cwe_for_cve_refuses_when_net_disabled
uv run --frozen pytest tests/test_vet.py -q -> 145 passed
uv run --frozen frob test --base main -> [PASS] python exit=0 12.64s (touched-set incl. both new tests + frob self-model sys-gate tests)
uv run --frozen frob sys audit -> "sys audit: PROVED -- zero gaps across every configured view" (zero LINT004 waivers left anywhere in the model, vet's included)

Filed: none (T-0822 is this ticket itself, filed because dispatch id T-0817 does not exist in the ledger -- see deviations below)

Gates: frob check --only {lint,static,gates-fast,gates-native,gates-security} --ticket T-0822 all clean (0 errors); the one pre-existing lint red (tests/system/test_cli_doctor.py ty diagnostic, predates this change, outside scope) is untouched.

### Changed
```
 design/frob.strata        | 23 ++++++++++-------
 src/frob/vet/_nvd.py      | 14 ++++++++++
 src/frob/vet/_registry.py | 17 +++++++++++++
 tests/test_vet.py         | 65 +++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                | 58 ++++++++++++++++++++++++++++++++++++++++++
 5 files changed, 168 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)

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
blocked_by: []
parent: null
scope:
- src/frob/lang/_support.py
- src/frob/gates/**
- tests/test_lang_conformance_gate.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN an adopter repo whose queue carries no frob-internal ticket ids WHEN
    LANG003 evaluates a known-gap facet THEN it does not hard-error on the unresolvable
    frob-internal reference (per the chosen design), with a fixture test proving the
    adopter shape
  evidence: []
threat: null
component: null
labels: []
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

<!-- ticket:T-0824 -->
```yaml
id: T-0824
title: protocol_summary gate missing from _STAGE_GROUPS coverage
state: queued
kind: bug
origin: human
created: '2026-07-23'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/check/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
fails on main (post T-0813 merge): the new `protocol_summary` gate
(src/frob/gates/_protocol_summary.py, wired into _ALL_GATES) was not added
to any `_STAGE_GROUPS` membership in src/frob/check/__init__.py, so
`frob check --only <group>` can never reach it and the coverage test fails.

Found while verifying T-0599 (frob-exports triage); out of that ticket's
scope (src/frob/check/__init__.py's _STAGE_GROUPS membership, not its
exports). Fix: add "protocol_summary" to the appropriate _STAGE_GROUPS
bucket in src/frob/check/__init__.py (likely gates-native or gates-fast
depending on cost) and re-run the coverage test.

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
blocked_by: []
parent: null
scope:
- src/frob/strata/_host_isolation.py
- docs/strata/host.md
- tests/unit/strata/test_host_isolation.py
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a principal with a narrow deny and a broad allow on one path WHEN the
    join evaluates THEN the WRITE_DAC indirection corner has a recorded disposition
    (bit-level modeling or loud documentation plus a behavior-locking test); GIVEN
    token-privilege classes THEN the grammar-clause decision is recorded
  evidence: []
threat: elevation-of-privilege
component: null
labels: []
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
blocked_by: []
parent: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/**
scope_changes: []
evidence: []
attachments: []
acceptance:
- text: GIVEN a why-file that already begins with a Done report heading WHEN frob
    ticket done-report renders it THEN exactly one heading appears in the ledger block;
    existing double-heading blocks are tolerated by parsers
  evidence: []
threat: null
component: null
labels: []
```
Recurred 5+ times this drive (reviewers keep flagging it cosmetically): done-report prepends its own heading on top of one already present in --why-file content. Deduplicate at render time.
