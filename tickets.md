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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
threat: null
component: null
```
_scan_file_fingerprints (CVE matching) is lexical needle-matching for EVERY language including Python -- a renamed import defeats a fingerprint even where capability scanning is binding-aware. Reuse the binding tables built for capability resolution (Python + the new TS/Rust/C-C++ tables) to resolve aliases before fingerprint matching for all languages. Acceptance: an aliased import that would evade a lexical fingerprint match is still caught; adversarial test per language.

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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/app/config.py
- frob.toml
threat: null
component: null
```
See docs/audits/gates-quality.md. HIGH: entire quality surface is non-blocking (PERF/PII010/SEC110/ARCH001/DUP/lower-secrets are WARN, frob check exits 0 on them) -- green makes NO quality claim; DUP fails open (default-off AND no-op without natives); frob:secret-fake suppresses real secrets with no accountability/reason/ledger. RIGHT-WAY fix: decide per rule which are error-tier (and default DUP on / fail-closed when natives missing); give secret suppression the same reasoned-waiver accountability as frob:waive. Expect the build to red -- that red is honest. Then re-audit until empty. MED/LOW in the doc.

<!-- ticket:T-0584 -->
```yaml
id: T-0584
title: 'PRE001 catch-22 on slow mounts: sweep needs a timeout/partial-state or async
  design (T-0355 item 2)'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- docs/modules/gates.md
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'gate:AFFECT/COV forced a doc update in docs/modules/gates.md for the PreworkSweep/sweep_ticket/prework_gate
    changes this ticket makes; widening scope to include the doc file the code''s
    own frob:doc anchor already points at.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestScopePrework::test_pre001_passes_with_partial_sweep_matching_digest
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_partial_on_budget_exceeded
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_resumes_pending_patterns
- tests/test_gates.py::TestScopePrework::test_prework_sweep_default_partial_is_false_and_treated_as_final
threat: null
component: null
```
found while working T-0355 (deliberately split out, item 2 of that ticket's original 3-item report): editing a ticket's scope after start demands a re-sweep before PRE001 is satisfiable, and frob ticket sweep's dup+xref pass is a synchronous full-scope scan -- on a slow mount (WSL /mnt/c, network share) that scan itself can be slow enough that the ticket can never get back into a checkable state within a reasonable session. T-0474 already backgrounds the sweep at frob ticket start time, but frob ticket sweep (the always-available resweep path used after a scope edit) is still fully synchronous by design (see its docstring: 'the always-available, always-synchronous way to record it'), and PRE001 itself only ever compares against a fully-completed digest -- there is no partial-sweep-ok state. This needs an actual design decision before implementation (a timeout + partial-sweep-ok ticket state that prework_gate treats as provisionally clean, vs. making frob ticket sweep itself background-and-poll like start), not a mechanical port of an existing fix, so it was NOT implemented as part of T-0355 (items 1 and 3 of that ticket were: clean SIGINT message in __main__.py, and confirming scope_digest is already content-only/checkout-portable).

## Done report

Chose the "timeout + partial-sweep-ok ticket state that prework_gate treats
as provisionally clean" option from the ticket's two sketched designs,
rather than making `frob ticket sweep` background-and-poll like `start`.
Reason: the sweep-and-poll approach only relocates the wait -- an agent who
edits scope then needs PRE001 clean before closing still has to poll for
completion, and the CLI dispatch wiring that would background `sweep`
(app/ticket_runner.py) is out of this ticket's declared scope
(src/frob/gates/**, src/frob/tickets/**) anyway. Bounding sweep_ticket
itself with a wall-clock budget and persisting resumable partial state is
fully implementable inside gates/_prework.py and gates/__init__.py: every
existing call site (start's foreground/background paths, the `sweep`
command, land's refresh) gets the fix automatically via the changed
default, no CLI wiring needed, and it directly answers the ticket's stated
failure mode (a full dup+xref scan exceeding the ~90s per-stage foreground
budget on a slow mount).

Design: `PreworkSweep` gained `partial: bool` and `pending_patterns: tuple`.
`sweep_ticket` now takes `budget_seconds` (default 60s, None = unbounded).
The dup scan + graph load still run once, unbounded (they are not
per-pattern and dup's own bounding is a separate concern); the
per-scope-pattern xref loop checks a wall-clock deadline before each
pattern and, on exceeding it, records a partial sweep with the remaining
patterns as `pending_patterns` instead of blocking to completion. A
subsequent `sweep_ticket` call whose current scope digest still matches a
recorded partial sweep resumes from `pending_patterns` rather than
rescanning already-swept patterns. `prework_gate` (PRE001) treats a partial
sweep whose digest matches the ticket's current scope as provisionally
clean (not a violation) -- the catch-22 this closes is specifically that
PRE001 used to demand a fully-completed digest with no partial-ok state,
so a sweep that could never finish in one foreground-budget-sized call
could never satisfy the gate either.

Cut/left as-is: no expiry/staleness cap on how long a ticket can stay
"partial but provisionally clean" -- the ticket's own two sketched options
did not require one, and each `frob ticket sweep` call makes forward
progress (shrinks pending_patterns) rather than looping forever, so an
explicit cap was left out rather than guessed at. If observed to matter in
practice, that is a follow-up, not folded in here.

docs/modules/gates.md needed updating (AFFECT001/COV001 fired on the
changed prework_gate/PreworkSweep/sweep_ticket/DEFAULT_SWEEP_BUDGET_SECONDS
symbols) -- widened the ticket's scope to include that one doc file via
`frob ticket scope T-0584 --add docs/modules/gates.md` rather than silently
touching an out-of-scope file.

Follow-up (post-close, coordinator-flagged TEST016): `frob test`'s mutation
sweep found one surviving mutant at src/frob/gates/_models.py:180 --
negating `PreworkSweep.partial`'s `False` default to `True`. No existing
test constructed a `PreworkSweep` WITHOUT `partial=` and asserted the
default's observable behavior, so the mutant survived. Added
`TestScopePrework::test_prework_sweep_default_partial_is_false_and_treated_as_final`:
constructs a `PreworkSweep` with no `partial=` kwarg and asserts (a)
`.partial is False` and `.pending_patterns == ()` directly, (b) a
record/load round-trip preserves `partial is False`, and (c) `prework_gate`
accepts it with zero violations (the "treated as a complete sweep" half of
the ask). Hand-verified the kill: flipped the default to `True` in
src/frob/gates/_models.py, re-ran the new test alone -- it failed
(`assert sweep.partial is False` no longer holds) -- then reverted; `git
diff main -- src/frob/gates/_models.py` shows only the original T-0584
diff, confirming a byte-identical revert.

### Changed
```
 docs/modules/gates.md      | 36 +++++++++++++++++--
 src/frob/gates/__init__.py | 17 +++++++++
 src/frob/gates/_models.py  | 17 ++++++++-
 src/frob/gates/_prework.py | 86 ++++++++++++++++++++++++++++++++++++++++++----
 tests/test_gates.py        | 72 ++++++++++++++++++++++++++++++++++++++
 tickets.md                 | 84 +++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 302 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestScopePrework::test_pre001_passes_with_partial_sweep_matching_digest` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_partial_on_budget_exceeded` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_resumes_pending_patterns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_prework_sweep_default_partial_is_false_and_treated_as_final` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- docs/design/registry/supply-chain.yaml
threat: null
component: null
```
Standing home for the 39 supply-chain.yaml entries whose controls previously carried deferred:T-0389 (the reconciliation ticket itself) -- a self-reference that would orphan them the moment T-0389 closed; T-0389's pass re-pointed them here. Each entry needs either a real enforcing check in src/frob/vet/ (then flip to handled_by) or a reasoned out_of_scope disposition (many require external network/registry data -- checkability tag requires-external-data -- and are legitimate deferrals to future external-data-fetching work, not silent drops).

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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
scope:
- tests/**
threat: null
component: null
```
Re-measured 2026-07-23 by T-0597: the frob-dup check stage (frob check --only dup, the legacy find_duplicates scanner T-0597 was scoped against) currently shows 240 total groups, 110 already covered by full-group frob:waive DUP001/DUP002 directives, 130 unaccounted. Of the 130 unaccounted, 105 involve ONLY tests/** files (no src/frob/** member) -- a sibling ticket (see parent T-0597's Done/fail report) carves out the remaining 25 groups that touch src/frob/** for real extraction judgment; this ticket is the tests-only batch, which the T-0597 dispatch playbook expects to be mostly (not necessarily all) legitimate parallel-scaffolding false pairs.

Do NOT hand-copy a stale list: at the start of this ticket, run:

  uv run frob check --only dup --json

and filter diagnostics with severity=="warning" whose message contains no "src/frob" path segment -- that is the authoritative, current group list (it will have drifted again since this filing; T-0597's own dispatch saw the raw dup group count move 75->240 in about one day of concurrent landings). For each group: waive with an honest, specific, full-group frob:waive DUP001 (or DUP002) reason (T-0375's full-coverage rule -- every fragment's symref must be covered, no any-shared-symref shortcuts) if it is a coincidental structural/parallel-test-scaffolding pair, or extract into a shared test helper/fixture (with before/after test runs) if the shared logic is genuinely one thing duplicated, not parallel-but-distinct test intent. Given the volume, batch the work (e.g. by source test file or by group-size band) and commit incrementally per playbook section 12/discipline. Acceptance: frob check --only dup summary shows 0 unaccounted groups whose fragments are entirely under tests/**, no threshold loosened.

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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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
tier: ticket
sprint: null
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

<!-- ticket:T-0925 -->
```yaml
id: T-0925
title: 'docs: add lock-ordering hazards section to docs/modules/arch.md'
state: queued
kind: docs
origin: human
created: '2026-07-26'
priority: medium
parent: T-0694
tier: ticket
sprint: null
scope:
- docs/modules/arch.md
- src/frob/arch/_lock_ordering.py
threat: null
component: null
```
docs/modules/arch.md needs a "Lock-ordering hazards" section documenting
`lock-order-cycle`/`lock-identity-unresolved` (frob.arch._lock_ordering,
T-0694, child 2 of the T-0693 concurrency-hazard umbrella), matching the
existing "Fork/pool hazards" (T-0695) and "Async event-loop hazards"
(T-0696) sections' structure/detail level. T-0694's own scope
(src/frob/arch/**, tests/unit/test_arch.py) does not include docs/, so no
frob:doc anchor was added on the check function in that ticket -- add the
section and the frob:doc directive together here.

<!-- ticket:T-0935 -->
```yaml
id: T-0935
title: gates-native stage-group test hardcodes gate set, breaks on every new gate
  (T-0688 regression)
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_app_runners_batch6.py
threat: null
component: null
```
Found while working T-0715 (unrelated to its scope, filed instead of
fixed): `tests/unit/test_app_runners_batch6.py::TestCheckRunner::
test_stamp_baseline_only_chunk_records_without_stamping` hard-codes the
expected `--only gates-native` gate-name set as
`frozenset({"archgate", "clones", "perf"})`. T-0688 (landed on main,
`feat: exhaustive-exception gate + errors-as-values advisory`) added a
new `exhaustive_handling` gate into that same stage group without
updating this test's expected set, so it now fails on `main` itself
(confirmed via `git show main:tests/unit/test_app_runners_batch6.py`
before touching anything) -- not something my worktree's merge
introduced.

Acceptance: GIVEN `main` as it stands WHEN
`test_stamp_baseline_only_chunk_records_without_stamping` runs THEN it
passes, either by widening the expected set to include
`exhaustive_handling` or by asserting membership/count instead of an
exact literal set (so the next gate added to `gates-native` doesn't
require a matching test edit every time).

<!-- ticket:T-0936 -->
```yaml
id: T-0936
title: migrate existing EPIC-titled tickets to tier=epic
state: queued
kind: docs
origin: human
created: '2026-07-26'
priority: medium
parent: T-0715
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
threat: null
component: null
```
T-0715's user mandate asked for existing EPIC-titled tickets to get
`tier: epic` mechanically as part of the migration to the new
`TicketTier` field (landed by T-0715 itself). This ticket is the actual
one-time backfill: scan `tickets.md`/`tickets-archive.md` for tickets
whose title matches the repo's existing "EPIC" naming convention (case-
insensitively prefixed, e.g. titles starting "EPIC:" or "EPIC "), set
their `tier` field to `epic` via the normal `frob ticket` write path (not
a hand-edit), and record the count changed in the Done report. Also worth
deciding here (not decided by T-0715): whether direct children of an
epic-titled ticket should default to `tier: story` at the same time, or
whether that requires a human judgment call per ticket.

Acceptance: GIVEN the ledger as it stood at T-0715 land WHEN this
migration runs THEN every ticket whose title matched the EPIC convention
carries `tier: epic` afterward, and no other ticket's tier changed.

<!-- ticket:T-0938 -->
```yaml
id: T-0938
title: sprint velocity/burndown derived from ledger state-transition history
state: queued
kind: feature
origin: human
created: '2026-07-26'
priority: medium
blocked_by:
- T-0715
parent: T-0715
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
threat: null
component: null
```
T-0715's user mandate also asked for velocity/burndown derived from
ledger state-transition history (closed-per-sprint counts), explicitly
"no new storage" -- i.e. it must be computed from the same
`frob:tests`/Done-report/state history already in the ledger and git log,
not a new tracked field. This is a real design + implementation gap on
its own: today's `Ticket`/ledger model does not retain a transition-
history log at all (only the CURRENT `state`), so "closed-per-sprint"
needs either (a) mining git log diffs of `tickets.md` for `state: done`
transitions per commit, correlated with each ticket's `sprint` field
(landed by T-0715), or (b) a lightweight append-only transition-log this
ticket would introduce (weighed against the "no new storage" mandate).
Depends on T-0715 (the `sprint` field) being in place first.

Acceptance: GIVEN a sprint with N tickets closed across several commits
WHEN `frob ticket sprint show <label>` (built by the CLI-surface child
ticket) is asked for velocity THEN it reports a closed-count derived
from history, not a hand-maintained counter, and the number matches a
manual `git log` tally of `state: done` transitions for that sprint's
tickets.

<!-- ticket:T-0939 -->
```yaml
id: T-0939
title: 'check --only scope hangs: derived.lock self-deadlock (same pid holds READ+WRITE*
  simultaneously)'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/process/_lock.py
- src/frob/gates/__init__.py
threat: null
component: null
```
Observed while verifying T-0718: `uv run frob check --ticket <id> --only scope` hung
indefinitely (multiple repeat attempts, 300s+ each, across varying system load from
load-average 17 down to under 1) in worktree
/home/logan/projects/frob/.claude/worktrees/agent-a71338f817a4d2945. `lslocks` showed the
SAME pid holding both a READ and a WRITE* (pending/blocked) flock on the same
.frob/derived.lock file at the same time:

  frob  <pid>  FLOCK  WRITE*  .../a71338f817a4d2945/.frob/derived.lock
  frob  <pid>  FLOCK  READ    .../a71338f817a4d2945/.frob/derived.lock

This looks like the process opened a second fd on derived.lock and requested LOCK_EX
while its first fd still held LOCK_SH -- flock(2) locks are associated with the open
file description, not the process, so two different fds in the same process can
deadlock each other exactly like two different processes would. src/frob/process/_lock.py
already has same-process reentrancy tracking (_process_held_counts, see its module
docstring re: avoiding exactly this self-deadlock) -- the --only scope code path
apparently reaches a second derived_state_lock acquisition that bypasses/misses that
tracking. Reproduced 3x in a row with fresh invocations (fresh pids each time, same
symptom). Worked around verification by calling frob.gates.scope_matches directly in
Python instead of through the CLI gate pipeline.

Investigate src/frob/process/_lock.py's derived_state_lock and whatever in the "scope"
check-stage wiring (src/frob/gates/__init__.py around scope_gate/PRE001 prework-sweep
loading, or app/check_runner.py's --only dispatch) acquires it twice without releasing
the first handle.

<!-- ticket:T-0944 -->
```yaml
id: T-0944
title: 'frob check self-deadlocks: derived.lock opened twice, READ+pending WRITE same
  pid'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/process/_lock.py
- src/frob/check/__init__.py
threat: null
component: null
```
## Description

Every `frob check --ticket T-XXXX --only <anything>` invocation in this
worktree (agent-a5842ed351bbd927e) hangs indefinitely instead of
completing. Confirmed via `/proc/<pid>/fd` and `/proc/locks`, not a slow
computation under contention:

- The `frob check` process opens `.frob/derived.lock` TWICE, holding two
  separate file descriptors (fd 3 and fd 4) to the same inode.
- `/proc/locks` shows the SAME pid holding a `READ` (shared) `FLOCK` on
  one fd and a pending `WRITE` (exclusive) `FLOCK` request on the other:
  ```
  31: FLOCK  ADVISORY  READ 1008549 08:30:1142126 0 EOF
  31: -> FLOCK  ADVISORY  WRITE 1008549 08:30:1142126 0 EOF
  ```
- `flock(2)` has no cross-fd reentrancy/upgrade semantics within one
  process -- a second, independent open+`LOCK_EX` request against a file
  the same process already holds `LOCK_SH` on (via a different fd) blocks
  forever, since the shared lock is never released before the exclusive
  request is made.
- `src/frob/process/_lock.py`'s own module docstring already flags this
  exact hazard class ("an `always os.open + flock` implementation would
  self-deadlock the moment a [...] `ThreadPoolExecutor` gate workers)
  holding it concurrently") and tracks `_process_held_counts` to guard
  against same-process reentrancy -- but that tracking evidently does not
  cover whatever two call sites raced here (one held via
  `derived_state_lock(..., exclusive=False)`, another requesting
  `derived_state_write_lock`/`exclusive=True` before the first is
  released).
- Reproduced twice, with two different `--only` gate selections
  (`scope`, then `prework`) against the same worktree -- not specific to
  one gate's code path, so likely in shared `check` runner
  setup/teardown around `_lock.py`, not gate-specific logic.

## Plan (for whoever picks this up)

1. Reproduce under `py-spy dump` or a debug build to get both call
   stacks holding fd3 (shared) and fd4 (pending exclusive) at the moment
   of hang.
2. Audit `frob.process._lock`'s `_process_held_counts`/reentrancy guard
   for the gap that let a second `os.open` + `flock` happen before the
   first shared lock in the SAME process was released or upgraded
   in-place (upgrade-in-place on the same fd via `LOCK_EX` again is safe
   and non-blocking against oneself; opening a NEW fd and locking THAT is
   not).
3. Fix by (a) tracking open fds per-process so a nested acquire reuses
   the existing fd/lock rather than opening a new one, or (b) removing
   whatever code path re-derives `root` and re-opens the lock file
   instead of reusing an already-lock-held context manager.

Filed while working T-0931 (comment-DSL `frob:raises` reconciliation);
that ticket needed `frob check` to record evidence/close and this bug
blocks it entirely in that worktree. Not fixed there -- `src/frob/
process/_lock.py` is outside T-0931's declared scope
(`src/frob/arch/**`, `src/frob/gates/**`, plus the doc/test files
scope-added for the rename itself).

<!-- ticket:T-0955 -->
```yaml
id: T-0955
title: 'strata export golden: frob_export_seccomp/iam/k8s drifted re: natives node'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/test_export_golden.py
- docs/strata/**
- tests/system/test_frob_self_model.py
scope_changes:
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: 'same root cause: frob''s own strata design gained a node (natives) node/flow/claim
    count that this drift-lock test''s hardcoded assertions (and the export goldens)
    were never updated for'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: already added
  actor: logan
  at: '2026-07-27'
threat: null
component: null
```
Found while working T-0700 (unrelated to grammar/access-mode changes -- confirmed via `git status`, no golden/export files touched by that ticket). `tests/unit/strata/test_export_golden.py::TestExportGolden` (test_k8s, test_seccomp, test_iam) fails on a fresh worktree built from current main: the frob self-modeled design's exported seccomp/IAM/netpol JSON now includes a "natives" node's syscalls/statements that the checked-in golden fixtures under the golden dir do not yet reflect. Likely a golden-fixture regen missed after a recent "natives" node/capability addition to frob's own strata design. Regenerate the golden fixtures (or fix the export drift if the new output is wrong) and re-verify test_export_golden passes clean.

<!-- ticket:T-0956 -->
```yaml
id: T-0956
title: 'strata design: re-point T-0700 live-tracker waivers, arbitrate tickets_ledger
  with new grammar'
state: queued
kind: docs
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/**
- tests/test_tickets_live_tracker.py
threat: null
component: null
```
T-0700 shipped access modes + resource/arbitrated_by grammar. design/frob.strata has 5 SYS203 "tickets_ledger" waivers explicitly written "re-evaluate at T-0700" (lines ~116/181/311/388/508) since the ledger genuinely has an arbiter (every writer serializes through .frob/tickets.lock, T-0458/T-0633) that SYS203 could not express until now. Re-express this properly: declare a `resource tickets_ledger { lock "tickets.lock" }` (or `arbitrated_by` the CLI-writer node, whichever models T-0458/T-0633's actual single-writer-lock discipline more accurately) plus `access "tickets_ledger" mode write` on each node/store that writes it, then drop the now-superseded SYS203 waivers once the model-level arbiter discharges the contention cleanly (verify via frob.strata._access.resource_contention_violations against frob's own elaborated design). Also re-point tests/test_tickets_live_tracker.py:220's `ticket=T-0700` placeholder to this ticket's id once assigned. Blocked by nothing; T-0700 is done and closed.

<!-- ticket:T-0958 -->
```yaml
id: T-0958
title: reconcile the 56 deferred:T-0331 system-design entries against the landed REL26x-REL38x
  obligation families
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/system-design.yaml
- tests/test_registry_reconciliation_system_design.py
- src/frob/gates/__init__.py
- src/frob/strata/_distributed_txn.py
- src/frob/strata/_delivery_semantics.py
- src/frob/strata/_retry.py
- src/frob/strata/_reliability.py
- src/frob/strata/_backpressure.py
- src/frob/strata/_observability.py
- src/frob/strata/_slo.py
- src/frob/strata/_clock_ordering.py
- src/frob/strata/_message_schema.py
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_distributed_txn.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_delivery_semantics.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_retry.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_reliability.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_backpressure.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_observability.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_slo.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_clock_ordering.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_message_schema.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
- tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
acceptance:
- text: given the 56 rows, when the registry gate runs, then zero rows cite T-0331
    and every disposition resolves (REG002/REG008/REG011 clean)
  evidence:
  - tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119
  - tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted
  - tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
  - tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
  - tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
- text: T-0756 new-gate-rule fixture proof -- before this change, TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
    FAILed (REG002 dangling handled_by:REL200/REL220/REL221/REL260/REL270/REL272/REL280/REL320/REL330/REL350/REL370,
    none of those ids were in gates/__init__.py's _KNOWN_GATE_RULES yet); after adding
    them alongside the matching handled_by dispositions and frob:enforces edges, the
    same production `registry_gate` invocation PASSes with zero violations
  evidence:
  - tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
threat: null
component: null
```
Successor to epic T-0331 (closing). The epic landed thirteen obligation families (REL26x backpressure through REL38x starvation, plus SYS204 contention). The 56 registry entries that deferred to the epic must now be re-dispositioned individually: handled_by:<rule> where a landed family genuinely covers the concept (with the frob:enforces edge REG008 wants), deferred to a real follow-up ticket for concepts still unbuilt, or reasoned out_of_scope per the T-0722/T-0912 precedents. Catalogued-is-not-enforced applies: no handled_by without a live registered rule.

## Done report

Changed:
docs/design/registry/system-design.yaml (56 rows re-dispositioned; header note updated)
src/frob/strata/_distributed_txn.py::check_distributed_txn_obligations (frob:enforces SDC-4-DISTRIBUTED-TRANSACTIONS, SDC-4-OUTBOX-SAGA-PATTERNS)
src/frob/strata/_delivery_semantics.py::check_delivery_semantics_obligations (frob:enforces SDC-4-EXACTLY-ONCE-PROCESSING, SDC-5-IDEMPOTENT-RECEIVER, SDC-8-AT-MOST-ONCE, SDC-8-AT-LEAST-ONCE, SDC-8-IDEMPOTENT-CONSUMERS)
src/frob/strata/_retry.py::check_retry_obligations (frob:enforces SDC-4-IDEMPOTENCY, SDC-5-RETRY-BACKOFF-JITTER)
src/frob/strata/_reliability.py::check_reliability_timeouts (frob:enforces SDC-5-TIMEOUT)
src/frob/strata/_backpressure.py::check_backpressure_obligations (frob:enforces SDC-5-LOAD-SHEDDING)
src/frob/strata/_observability.py::check_observability_obligations (frob:enforces SDC-6-USE-METHOD-UTILIZATION-SATURATION-ERRORS, SDC-7-THREE-PILLARS-METRICS-LOGS-TRACES, SDC-7-DISTRIBUTED-TRACING-DAPPER)
src/frob/strata/_slo.py::check_slo_obligations (frob:enforces SDC-7-SLO-BASED-ALERTING)
src/frob/strata/_clock_ordering.py::check_clock_ordering_obligations (frob:enforces SDC-8-ORDERING-GUARANTEES)
src/frob/strata/_message_schema.py::check_message_schema_obligations (frob:enforces SDC-13-EVERY-SERVICE-TO-SERVICE-API-DECLARES-AN-EXPLICIT-SCHEMA-CONTRACT-WITH-A-VERSIONING)
src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added REL200/220/221/260/270/272/280/320/330/350/370, the exact ids this ticket's handled_by dispositions cite -- REG002 needs them in known_rules to resolve)

Disposition counts (56 rows, all previously deferred:T-0958):
  handled_by: 17 (REL200 x1, REL220 x1, REL221 x1, REL260 x1, REL270 x2, REL272 x1, REL280 x1, REL320 x1, REL330 x5, REL350 x2)
  deferred: 4 (to 2 new child tickets, 2 rows each -- see Filed)
  out_of_scope: 35 (7 network-fallacy descriptive concepts, 10 named consensus/replication algorithms frob does not implement, 6 replication/sharding architecture patterns, 2 db-transaction/CDC descriptive concepts, 1 meta-concept, 1 tail-latency descriptive phenomenon, 1 named-practice/person citation, 1 log-abstraction descriptive concept, 6 deployment/ops methodology patterns)

Enforces edges added: 17 `frob:enforces <SDC-id>` directives across the 9 strata modules listed above (one per handled_by row), each paired with the disposition's target rule.

Filed:
T-0962 -- static checks: ABI/ISA compat-window stability + boot-chain signed/measured attestation obligations (feature; 2 sec-13 rows deferred here)
T-0960 -- static checks: kernel/userspace-interface classification + per-process cgroup resource-bound declaration obligations (feature; 2 sec-13 rows deferred here)
T-0961 -- gates/__init__.py _KNOWN_GATE_RULES missing the bulk of the REL26x-REL38x + SYS204 obligation-family rule ids (bug; the broader listing-omission this ticket only partially closed, scoped to just the 11 ids it needed)

Evidence:
tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119 -- pass
tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted -- pass
tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket -- pass
tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket -- pass
tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations -- pass
Also observed passing (not separately bound as evidence): full tests/test_registry_reconciliation_system_design.py (8/8), tests/test_registry_exhaustiveness.py (33/33), tests/unit/strata/test_{retry,reliability,backpressure,observability,slo,clock_ordering,message_schema,distributed_txn,delivery_semantics}.py (all pass), tests/test_gates.py -k KnownGateRuleIds (pass).

Gates: `frob check --ticket T-0958` chunked (prework, scope, coverage, doclink, docanchor, registry) all pass 0 errors after re-running `frob ticket sweep T-0958` post scope-add. `frob check --ticket T-0958 --only registry` shows 0 violations of any severity attributed to docs/design/registry/system-design.yaml (REG002/REG008/REG011 clean).

### Changed
(no changed files detected)

### Evidence
- `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 4971 warning(s), 220 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0959 -->
```yaml
id: T-0959
title: land clobbers tickets-archive.md with the worktree's stale copy (62 archived
  blocks wiped by T-0703's land)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
evidence:
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
acceptance:
- text: given a worktree whose tickets-archive.md predates an archive sweep on main,
    when its ticket lands, then every block in main's pre-land archive survives in
    the post-land archive
  evidence:
  - tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
threat: null
component: null
```
T-0703's land (a9486381) replaced main's tickets-archive.md wholesale with the worktree's pre-archive-sweep copy, deleting the 62 blocks a TICK003 sweep had archived -- every Done report citing them then fired TICK006 phantom-filing (19 errors), plus COV003 regressions. Recovery was git checkout of the pre-land archive (2ab3c386, verified strict superset). Root cause to find: the land path stages tickets-archive.md from the worktree without the merge/splice discipline tickets.md gets; T-0740's _check_ledger_id_integrity guards _splice_only_ticket for tickets.md but the archive file appears to ride along unguarded (T-0703's worktree archive was stale because the sweep happened on main after the worktree's warmup merge). Fix: land must treat tickets-archive.md like tickets.md -- merge/splice not overwrite -- plus an id-integrity assertion that no archived id present on main's archive disappears in the staged result. Regression test: worktree with stale archive + main with newer archived blocks -> land must preserve main's blocks.

## Done report

Root cause confirmed: `tickets-archive.md` had no per-id splice discipline
at all in `frob ticket land` -- unlike `tickets.md` (`_splice_and_stage`,
T-0740's `_check_ledger_id_integrity` backstop), the archive file rode
along on whatever git's raw merge/checkout produced at both land merge
points (`_merge_main_into_worktree`'s conflict auto-resolve, and
`_squash_and_splice_ledger`'s final squash-apply onto root). A reproducible
regression case shows the real loss shape: when the worktree ALSO
independently archives its own ticket (a genuine two-sided divergence on
tickets-archive.md, not a one-sided fast-forward git resolves for free),
the pre-fix code silently drops that side's addition entirely -- confirmed
by running the new regression test against the pre-fix `_land.py` (fails)
and post-fix `_land.py` (passes).

Fix: added `_splice_and_stage_archive` (mirrors `_splice_and_stage`'s
tickets.md discipline) -- parses both sides as ledgers, unions by id
keeping newest (`_merge_ledger_tickets`/`_newer`), then refuses loudly
(`Err(GitFailed)`) if any id present in the AUTHORITATIVE side (root/main's
current archive at that call site) would vanish from the merged result --
the T-0959 id-integrity assertion extending T-0740's
`_check_ledger_id_integrity` pattern to this file. Wired into both land
merge points: `_merge_main_into_worktree` (worktree gets main's archive
splice) and `_squash_and_splice_ledger` (root gets the final archive
splice, using root's freshest tip captured right before the squash as
authoritative). `tickets-archive.md` also added to the out-of-scope-
conflict exclusion set in `_auto_resolve_out_of_scope_conflicts`
(previously only `tickets.md` was excluded from raw `git checkout`
auto-resolution).

Changed:
- src/frob/tickets/_land.py
  - `_read_archive_text_or_empty` (new)
  - `_splice_and_stage_archive` (new)
  - `_merge_main_into_worktree` (now also splices tickets-archive.md)
  - `_squash_and_splice_ledger` (now also splices tickets-archive.md)
  - `_auto_resolve_out_of_scope_conflicts` (excludes tickets-archive.md too)
  - docstring fixes on `_check_only_tickets_conflicted`/
    `_check_squash_conflicted` (mention tickets-archive.md)
- tests/test_ticket_land.py
  - `TestArchiveSpliceDiscipline` (new): two unit tests on
    `_splice_and_stage_archive` directly (union-by-id merge, id-integrity
    refusal) plus one end-to-end `land()` regression test reproducing the
    T-0703 incident shape (worktree with a stale archive + main with newer
    archived blocks, PLUS the worktree independently archiving its own
    sibling ticket -- the two-sided-divergence shape that actually fails
    pre-fix) -> land preserves both sides' archived blocks.

Evidence (collected via `pytest --collect-only`, 3/3 resolve):
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
  (acceptance criterion 0 bound to this evidence id)

`uv run pytest tests/test_ticket_land.py -q -p no:cacheprovider -k TestArchiveSpliceDiscipline`
-> 3 passed. Manually confirmed the end-to-end test fails against the
pre-fix `_land.py` (git-diff-and-revert-only-that-file, no test changes)
and passes against the post-fix file.

`uv run pytest tests/test_ticket_land.py -q -p no:cacheprovider` (full
module, minus 6 pre-existing-on-main env-artifact failures unrelated to
this change -- confirmed independently failing against unmodified
`_land.py` too: TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace,
TestMergeConflictOutsideLedger::test_real_conflict_outside_tickets_md_aborts,
TestGitSubprocessFailures::test_unowned_deletions_diff_failure_after_merge,
TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
(all four: stray `.frob/derived.lock` untracked file trips a "leaves no
trace" assertion), and
TestClaimDivergencePostMerge::test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds,
TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds
(both: `uv run pytest --collect-only` subprocess spawned inside a fixture
worktree fails to collect in this sandboxed environment)) -> all remaining
tests pass.

`uv run ruff check src/frob/tickets/_land.py tests/test_ticket_land.py`
and the PATH `ruff check` (same two files) -> both clean.

Filed: none (no out-of-scope work found).

Gates: not run repo-wide (chunked `frob check` not needed for this
scoped, test-verified fix); scoped test suite and ruff both clean as
above. `frob ticket close` will re-verify evidence/Done-report from
scratch.

<!-- ticket:T-0960 -->
```yaml
id: T-0960
title: 'static checks: kernel/userspace-interface classification + per-process cgroup
  resource-bound declaration obligations'
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_process_bounds.py
- docs/strata/reliability.md
threat: null
component: null
```
Filed while reconciling T-0958's system-design.yaml deferred rows. SDC-13-EVERY-KERNEL-USERSPACE-INTERFACE-SYSCALL-PROCFS-SYSFS-ENTRY-IOCTL-IS-CLASSIFIED-INT and SDC-13-EVERY-DEPLOYED-PROCESS-DECLARES-ITS-RESOURCE-BOUNDS-CGROUP-LIMITS-CPU-MEMORY-IO-AND name two genuinely checkable, currently-unbuilt obligations: (1) every kernel/userspace interface (syscall, procfs/sysfs entry, ioctl) a node touches being classified (trusted/untrusted, read/write, etc.) into the same kind of deny-by-default declared-attr obligation REL2xx/REL3xx already use, and (2) every deployed process node declaring its resource bounds (cgroup cpu/memory/io limits) -- structurally the same "declared bound + provability" shape _backpressure.py's REL260/261 and _interactive_cost.py's REL310/311 already establish for other resource dimensions, just not yet built for process-level cgroup bounds or kernel-interface classification. No landed REL/SYS family covers either concept today. Scope: a new strata rule module (e.g. src/frob/strata/_process_bounds.py) plus docs/strata/reliability.md plus the corresponding registry re-disposition once built.

<!-- ticket:T-0961 -->
```yaml
id: T-0961
title: gates/__init__.py _KNOWN_GATE_RULES missing the bulk of the REL26x-REL38x +
  SYS204 obligation-family rule ids
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
threat: null
component: null
```
Filed while working T-0958 (system-design.yaml reconciliation). T-0958 added exactly the 11 REL2xx/REL3xx rule ids it needed for its own handled_by dispositions (REL200/220/221/260/270/272/280/320/330/350/370) to gates/__init__.py's _KNOWN_GATE_RULES frozenset, but the REL26x-REL38x epic (T-0331's landed obligation families) shipped roughly two dozen more rule ids that were never added there either -- the same listing-omission class T-0903/T-0923/T-0924 already fixed for other batches. Known gap at filing time (non-exhaustive): REL201, REL210, REL211, REL222, REL230, REL231, REL261, REL271, REL281, REL290, REL291, REL300, REL301, REL310, REL311, REL321, REL331, REL340, REL351, REL360, REL371, REL372, REL380, REL381, REL382, REL383, and SYS204. Fix: audit every REL_MISSING_*/REL_UNPROVEN_*-shaped constant across src/frob/strata/*.py plus SYS204 (frob.strata._contention) against _KNOWN_GATE_RULES and add every one actually missing, mirroring T-0903/T-0923/T-0924's own precedent comments.

<!-- ticket:T-0962 -->
```yaml
id: T-0962
title: 'static checks: ABI/ISA compat-window stability + boot-chain signed/measured
  attestation obligations'
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_supply_chain_boot.py
- docs/strata/reliability.md
threat: null
component: null
```
Filed while reconciling T-0958's system-design.yaml deferred rows. SDC-13-A-DECLARED-ABI-ISA-TARGET-IS-STABLE-ACROSS-A-COMPATIBILITY-WINDOW-A-COMPILED-ARTIFA and SDC-13-EVERY-BOOT-CHAIN-STAGE-IS-SIGNED-SECURE-BOOT-OR-MEASURED-INTO-AN-ATTESTABLE-LOG-MEA name two genuinely checkable, currently-unbuilt supply-chain/OS obligations: (1) a declared ABI/ISA compatibility-window claim on a compiled artifact that a static check could verify stays honored across the window, and (2) each boot-chain stage being signed (secure boot) or measured into an attestable log, again a presence/provenance claim a static grammar attr + proof check could enforce, mirroring the REL2xx/REL3xx PROVABILITY CONSTRAINT pattern (_obligation_proof.py::node_has_bound_code) already established for other obligation families. No landed REL/SYS family covers either concept today. Scope: a new strata rule module (e.g. src/frob/strata/_supply_chain_boot.py) plus docs/strata/reliability.md (or a new supply-chain doc section) plus the corresponding registry re-disposition once built.
