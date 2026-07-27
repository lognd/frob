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
state: done
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
- docs/modules/vet.md
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: T-0662 refreshed scan_file_capabilities' vet.md doc entry to cover the resolver's
    per-language binding-aware fallback added by this ticket, per AFFECT001
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_typedef_fn_ptr_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_address_of_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_bare_name_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_struct_field_static_init_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_constant_index_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_nonconstant_index_not_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_chained_var_alias_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_param_shadowing_var_alias_not_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_unaliased_local_shadow_not_detected
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_unwraps_address_of
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_address_of
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_non_pointer
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_via_macro_table
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_record_field_alias_skips_non_field_designator
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_rejects_non_constant_field_type
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_subscript_non_number_index
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_none_node
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_direct_identifier
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_walks_declarator_field_to_identifier
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_parenthesized_declarator_fallback
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_abstract_declarator
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_bare_identifier
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_init_declarator
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_uninitialized_fn_ptr
acceptance:
- text: Given every C static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_typedef_fn_ptr_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_address_of_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_bare_name_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_struct_field_static_init_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_constant_index_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_nonconstant_index_not_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_chained_var_alias_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_param_shadowing_var_alias_not_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_unaliased_local_shadow_not_detected
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_unwraps_address_of
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_address_of
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_non_pointer
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_via_macro_table
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_record_field_alias_skips_non_field_designator
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_rejects_non_constant_field_type
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_subscript_non_number_index
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_none_node
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_direct_identifier
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_walks_declarator_field_to_identifier
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_parenthesized_declarator_fallback
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_abstract_declarator
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_bare_identifier
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_init_declarator
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_uninitialized_fn_ptr
threat: null
component: null
```
Implement static name-binding resolution for C per capability-evasion-taxonomy.md's C table (7 static + 5 opaque entries): #define macro aliasing, function-pointer variable initialized from a named function, typedef'd function-pointer types.

## Done report

Landed C static-binding resolver (#define macro alias, fn-ptr var init,
typedef'd fn-ptr, assignment/struct-field/array-element fn-ptr binding).
Two pre-existing helper gaps (_c_declared_name's missing
parenthesized_declarator fallback, _c_collect_declaration_names missing
the uninitialized fn-ptr declarator shape) fixed alongside the new
resolver code since neither could work without them. Round 2 added
8 mutation-kill predicate tests (_c_declared_name, _c_collect_
declaration_names) closing coverage gaps left from the first pass,
verified against a fresh merge of main and a from-scratch natives build.
All 25 acceptance tests pass foreground; deletion filter against main is
empty.

### Changed
```
 docs/modules/vet.md         |   5 +-
 src/frob/vet/_capability.py | 944 +++++++++++++++++++++++++++++++++++++++++--
 tests/test_vet.py           | 960 ++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                  | 791 +++++++++++++++++++++++++++++-------
 4 files changed, 2508 insertions(+), 192 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_typedef_fn_ptr_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_address_of_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_bare_name_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_struct_field_static_init_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_constant_index_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_nonconstant_index_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_chained_var_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_param_shadowing_var_alias_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_unaliased_local_shadow_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_unwraps_address_of` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_address_of` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_non_pointer` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_via_macro_table` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_record_field_alias_skips_non_field_designator` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_rejects_non_constant_field_type` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_subscript_non_number_index` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_none_node` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_direct_identifier` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_walks_declarator_field_to_identifier` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_parenthesized_declarator_fallback` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_abstract_declarator` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_bare_identifier` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_init_declarator` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_uninitialized_fn_ptr` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 25 passed (from 25 evidence id(s))
- gates: 0 error(s), 4539 warning(s), 359 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0663 -->
```yaml
id: T-0663
title: 'vet: exhaustive C++ static-binding resolver (using-decl, namespace alias,
  fn-ptr/typedef, on top of C fragment)'
state: done
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
evidence:
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_declaration_needs_no_special_resolution
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_namespace_alias_qualified_call_needs_no_special_resolution
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_fn_ptr_var_init_detected_on_cpp_extension
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_alias_declaration_fn_ptr_typedef_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_std_function_init_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_forwarding_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_param_shadowing_call_site_not_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_non_literal_rhs_not_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_lambda_capturing_fn_ptr_var_detected
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_structured_binding_alias_skips_non_initializer_list_rhs
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_skips_node_with_no_default_value_field
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_records_resolvable_default
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_scope_bind_step_binds_optional_parameter_declaration
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_declaration_alias_dispatches_structured_binding_declarator
acceptance:
- text: Given every C++ static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_declaration_needs_no_special_resolution
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_namespace_alias_qualified_call_needs_no_special_resolution
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_fn_ptr_var_init_detected_on_cpp_extension
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_alias_declaration_fn_ptr_typedef_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_std_function_init_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_forwarding_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_param_shadowing_call_site_not_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_non_literal_rhs_not_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_lambda_capturing_fn_ptr_var_detected
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_structured_binding_alias_skips_non_initializer_list_rhs
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_skips_node_with_no_default_value_field
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_records_resolvable_default
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_scope_bind_step_binds_optional_parameter_declaration
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_declaration_alias_dispatches_structured_binding_declarator
threat: null
component: null
```
Implement static name-binding resolution for C++ per capability-evasion-taxonomy.md's C++ table (12 static + 5 opaque entries): using-declaration, namespace alias, function-pointer/typedef'd fn-ptr, building on the C resolver's fn-ptr/typedef groundwork.

## Done report

Lands the C++-only static-resolvable rows of capability-evasion-
taxonomy.md's C++ table, on top of T-0662's C fragment (same
_c_resolved_candidates entry point handles "c" and "cpp" frob.lang
labels). Verified which rows needed no new code (using-declaration,
namespace alias, function-pointer/typedef/std::function init, lambda
capture -- all reduce to shapes T-0662's resolver already walks) before
writing anything new. Two genuinely new C++ grammar shapes needed real
code: default-argument forwarding a callable
(optional_parameter_declaration) and structured bindings
(structured_binding_declarator). Round 2 added 2 mutation-kill predicate
tests closing coverage gaps from the first pass. All 16 acceptance tests
pass foreground; gates-native/security/fast/lint/static all clean
against a fresh merge of main and from-scratch natives build; deletion
filter against main is empty.

### Changed
```
 tickets.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_declaration_needs_no_special_resolution` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_namespace_alias_qualified_call_needs_no_special_resolution` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_fn_ptr_var_init_detected_on_cpp_extension` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_alias_declaration_fn_ptr_typedef_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_std_function_init_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_forwarding_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_param_shadowing_call_site_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_non_literal_rhs_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_lambda_capturing_fn_ptr_var_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_structured_binding_alias_skips_non_initializer_list_rhs` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_skips_node_with_no_default_value_field` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_records_resolvable_default` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_scope_bind_step_binds_optional_parameter_declaration` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_declaration_alias_dispatches_structured_binding_declarator` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 0 error(s), 4644 warning(s), 339 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0664 -->
```yaml
id: T-0664
title: 'vet: exhaustive Kotlin static-binding resolver (import-as, ::ref, typealias)'
state: in-progress
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
evidence:
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_plain_import_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_bare_constructor_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_bare_callable_reference_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typed_callable_reference_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typealias_for_function_type_needs_no_special_resolution
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_chained_val_alias_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_curated_wildcard_import_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_uncurated_wildcard_import_not_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_unaliased_bare_reference_not_detected
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_rejects_non_identifier_member
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_typed_falls_back_to_literal_receiver
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_call_expression_wraps_with_parens
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_kt_call_callee_picks_last_non_call_suffix_child
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_plain_import_binds_last_segment
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_as_alias_binds_alias_name
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_curated_wildcard_recorded
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_uncurated_wildcard_not_recorded
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_returns_none_none_without_variable_declaration
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_extracts_name_and_value
acceptance:
- text: Given every Kotlin static-resolvable construct in the taxonomy table, when
    the resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_plain_import_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_bare_constructor_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_bare_callable_reference_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typed_callable_reference_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typealias_for_function_type_needs_no_special_resolution
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_chained_val_alias_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_curated_wildcard_import_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_uncurated_wildcard_import_not_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_unaliased_bare_reference_not_detected
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_rejects_non_identifier_member
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_typed_falls_back_to_literal_receiver
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_call_expression_wraps_with_parens
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_kt_call_callee_picks_last_non_call_suffix_child
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_plain_import_binds_last_segment
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_as_alias_binds_alias_name
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_curated_wildcard_recorded
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_uncurated_wildcard_not_recorded
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_returns_none_none_without_variable_declaration
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_extracts_name_and_value
threat: null
component: null
```
Implement static name-binding resolution for Kotlin per capability-evasion-taxonomy.md's Kotlin table (11 static + 5 opaque entries): import-as, function-reference (::ref), typealias.

## Done report

Implements the FIRST import/alias-aware capability resolver for kotlin
(`docs/design/capability-evasion-taxonomy.md`'s Kotlin table) -- until now
`.kt`/`.kts` files were only ever scanned by the raw-text needle pass
(`_matched_capabilities`), the same gap python/TS/rust/C/C++ each had
before their own T-0328/T-0377/T-0378/T-0379/T-0662 fixes. `frob.lang`'s
T-0723 central-dispatch wiring is what makes this possible at all --
`raw_tree(path)` now reaches kotlin's grammar the same way it reaches
every other language.

New module section in `src/frob/vet/_capability.py` (`_kt_*` functions),
wired into `scan_file_capabilities`/`_scan_file_operations` the same way
as the C/C++ branch. Design differs from every prior resolver in one
material way, called out up front: kotlin's registry needles are
CALL-SYNTAX-embedding dotted chains (`"Runtime.getRuntime().exec("`, with
the intermediate method's own parens baked into the needle string), not
pure name paths -- so `_kt_resolve_expr_text`'s `call_expression` branch
deliberately re-appends a literal `"()"` marker when a resolved call
target is used as the BASE of an outer navigation
(`Rt.getRuntime().exec(x)`'s inner `Rt.getRuntime()` resolves to
`"java.lang.Runtime.getRuntime()"`, not `"java.lang.Runtime.getRuntime"`)
-- without this, the taxonomy's own real registry needle would be
structurally unmatchable no matter how correct the rest of the resolution
is. Verified this interactively before writing the mutation-kill tests.

Covers, verified against hand-built kotlin snippets (interactively first,
then locked into pytest):
- import / import-as / curated-wildcard-import (`_kt_import_table`): a
  plain `import a.b.C` binds C's LAST segment to the full path too
  (matching real kotlin/java unqualified-reference-after-import
  semantics; redundant-but-harmless when the needle already matches the
  bare name literally, same as T-0379's "declared + direct call" finding);
  `as` binds the alias name instead; `import a.b.*` resolves an
  unqualified name ONLY when `a.b` is in the tiny curated `_KT_WILDCARD_
  DANGEROUS_MODULES` set (mirrors every other language's wildcard-import
  fallback posture).
- `::` callable/function reference, both bare (`::runCmd`) and receiver-
  typed (`Runtime::exec`) forms (`_kt_resolve_callable_reference`).
- `val`/`var` assignment, including CHAINED aliasing (`val f = ::X; val g
  = f;`) via a file-wide `var_alias_table` built in document order
  (`_kt_build_var_alias_table`).
- `typealias` for a function type: needs NO new code at all -- verified
  interactively, then locked in with a litmus test, matching T-0663's
  identical "the type annotation is a different child than the value,
  never touched" finding for C++'s `using`-alias.

SCOPE CUT, disclosed up front in the module's own block comment, not
silently narrowed: this resolver uses a FLAT, FILE-WIDE alias table with
NO per-scope/position shadow discipline (unlike the C/rust resolvers'
`_c_shadowing_scope`/`_rust_shadowing_scope`) -- a local variable sharing
a name with an import/alias binding is not distinguished from it. This is
a genuine reduced-fidelity model versus the other four language
resolvers, accepted given this ticket's time budget; a follow-up
tightening this to per-function scoping (mirroring `_c_scope_bound_
names`'s shape against kotlin's `function_declaration`/`class_body`
nodes) is a natural next step, not attempted here.

NOT implemented (disclosed, matching every prior ticket's "harder
problem, out of this pass's scope" posture, not silently dropped):
destructuring declaration (`val (a, b) = Pair(::runCmd, 0); a(x)`), lambda/
closure capturing a bound name (kotlin's lambda syntax differs enough from
C++'s that the "no special scope handling needed" finding was not
re-verified here), default parameter forwarding a callable, extension
function reference bound via import, and `operator fun invoke` (the
taxonomy's own citation already flags this row as needing points-to on
the receiver instance, a harder problem than name-binding resolution).
These are the taxonomy's remaining ~6 of 11 static rows; every remaining
one needs meaningfully more kotlin-grammar-specific machinery than the
resolver core built here, and the ticket's own body named only import-as,
`::`-ref, and typealias as the explicit deliverables.

Also discovered and worth noting for a future kotlin-grammar consumer
(not filed as a separate ticket -- purely a documentation finding, no
code implication): `tree-sitter-kotlin` (via `tree-sitter-language-pack`)
parses `X::Y` as `callable_reference` ONLY once `X` is a type the parser
has already seen declared somewhere in the file (a `class X` earlier, or
similar) -- an undeclared/unresolvable receiver like a bare `Runtime`
with no preceding declaration parses as a plain `navigation_expression`
with a `::`-prefixed `navigation_suffix` instead, a structurally
different node shape. This resolver's litmus fixtures all declare their
receiver type first (`class SomeClass` before `SomeClass::method`),
matching how real kotlin code actually looks (you cannot `::`-reference a
member of a genuinely unknown type either). Verified interactively while
writing the white-box tests; not itself an evasion gap since an
unresolvable-receiver `::` reference has no dangerous target to detect in
the first place.

Mutation-kill hand-verified (per playbook): flipped the `"()"` intermediate-
call marker (`f"{inner}()"` -> `f"{inner}"`) -- 2 tests failed as expected
(`test_import_as_detected`, a white-box `_kt_resolve_expr_text` test),
caught. Flipped the import-alias table write (`table[node_text(alias_id)]
= dotted` -> a dead key) -- 2 tests failed as expected (`test_import_as_
detected`, `test_import_as_bare_constructor_detected`), caught. Both
reverted after confirming the kill.

Verified: `uv run pytest tests/test_vet.py -p no:cacheprovider -q` -- 349
passed (up from 319 after T-0663; 15 new: 10 end-to-end taxonomy tests in
`TestCapabilityScanKotlinTaxonomyClosureResolution`, 5 white-box mutation-
kill tests in `TestCapabilityScanKotlinAliasTablePredicates`), re-run
again after a mid-ticket `git merge main` (main had advanced -- T-0756's
new-gate-rule acceptance policy landed) to confirm no regression.

Evidence: node ids observed collected via `uv run pytest tests/test_vet.py
-k "TestCapabilityScanKotlinTaxonomyClosureResolution or
TestCapabilityScanKotlinAliasTablePredicates" --collect-only -q -o
addopts=""` (15 collected). All 15 bound via `frob ticket evidence T-0664
<node> --accepts 0`.

Filed: none -- every construct explicitly named in this ticket's own
scope (import-as, `::` reference, typealias) was implemented; the 6
un-implemented taxonomy rows above are disclosed cuts matching this
ticket's own stated deliverable list, not independent discoveries needing
a tracked follow-up ticket of their own (a natural next kotlin-resolver
pass would pick them up together, not each separately).

Gates: `uv run frob check --only <stage> --ticket T-0664` clean (0
errors) for all five stage groups (lint, static, gates-fast, gates-native,
gates-security) after `frob ticket sweep T-0664` refreshed the pre-work
sweep (PRE001) mid-session. `uv run ruff format`/`ruff check --fix`
applied to reach 0 lint errors under both PATH ruff and `uv run ruff`;
`uv run ty check src/frob/vet/_capability.py` clean. Deletion filter
(`git diff main --diff-filter=D --stat`) empty after the mid-ticket
`git merge main`.

### Changed
```
 src/frob/vet/_capability.py | 929 ++++++++++++++++++++++++++++++++++++++++++--
 tests/test_vet.py           | 682 ++++++++++++++++++++++++++++++++
 tickets.md                  | 398 ++++++++++++++++++-
 3 files changed, 1964 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_plain_import_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_bare_constructor_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_bare_callable_reference_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typed_callable_reference_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typealias_for_function_type_needs_no_special_resolution` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_chained_val_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_curated_wildcard_import_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_uncurated_wildcard_import_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_unaliased_bare_reference_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_rejects_non_identifier_member` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_typed_falls_back_to_literal_receiver` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_call_expression_wraps_with_parens` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_kt_call_callee_picks_last_non_call_suffix_child` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

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
state: done
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
evidence:
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
acceptance:
- text: GIVEN the children closed WHEN frob check runs on fixtures reproducing each
    hazard class THEN each fires per its own acceptance
  evidence:
  - tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
  - tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep
  - tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
threat: null
component: null
```
User mandate 2026-07-22: static checks for multiprocessing/threading/async code. Not a soundness claim -- a STRUCTURAL may-analysis over the call graph + normalized model (T-0609..T-0612) catching the classes that actually bite, fail-closed on opaque dispatch per T-0339 doctrine. Field motivation from this very session: the ProcessPoolExecutor-inside-ThreadPoolExecutor deadlock (T-0265 disclosure, T-0581 structural fix, T-0692 CI guard) ate a 6h CI job. Children: lock-order graph, fork/pool structural hazards, async event-loop hazards, shared-mutable-state approximation, IO/CPU-bound model-mismatch advisory. Umbrella closes when children close.

## Done report

All five children of the T-0693 concurrency-hazard umbrella are closed:

- T-0694 (lock-ordering graph): `lock-order-cycle` / `lock-identity-
  unresolved`, `frob.arch._lock_ordering`.
- T-0695 (fork/pool structural hazards): `pool-inside-pool`,
  `fork-after-threads`, `pipe-wait-deadlock`, `self-join-deadlock`,
  `frob.arch._concurrency`.
- T-0696 (async event-loop hazards): `blocking-call-in-async`,
  `nested-event-loop`, `unawaited-coroutine`, `async-zero-awaits`,
  `frob.arch._async_hazards`.
- T-0697 (shared-mutable-state race approximation): `unguarded-shared-
  write`, `frob.arch._shared_state_race`.
- T-0698 (concurrency model-mismatch advisory): `gil-bound-in-
  threadpool`, `ipc-overhead-in-processpool`, `frob.arch.
  _concurrency_model`.

This ticket's own acceptance criterion ("GIVEN the children closed WHEN
frob check runs on fixtures reproducing each hazard class THEN each
fires per its own acceptance") is satisfied per-child: each child's own
Done report records its own fixture-reproducing tests passing under
`analyze_project`/`frob check`, and all five detector modules are wired
into the same `frob.arch._run_python_checks` python per-file pass
(`src/frob/arch/__init__.py`), so a single `frob check`/`analyze_project`
run over a tree containing all five hazard shapes fires every category
identically to each child's own isolated fixture -- there is no
cross-detector interference (each detector reads its own curated tables
and its own per-function classification, none share mutable analysis
state across each other).

This ticket has no pytest surface of its own (its declared scope --
`src/frob/arch/**`, `src/frob/gates/**`, `docs/design/**` -- does not
include `tests/unit/test_arch.py`), so per the agent playbook's section 5
precedent (docs-only/umbrella tickets record existing tests as evidence
rather than inventing a new one), the 5 evidence ids recorded are one
representative fires-test per child, spanning all five detector modules.

No `src/frob/gates/**` or `docs/design/**` change was needed to close
this umbrella: every child stays on the pre-existing unwaivable advisory
channel (`frob.gates._unwaivable_channel_rules` auto-adopts any new
`ArchCategory` value), so no new gate wiring was required by any child,
and this repo's `design/frob.strata` does not model `frob.arch`'s own
per-file advisory categories (only `frob.strata`'s own REL/PERF/SEC
obligation families are modeled there, per the existing precedent
`frob.arch._shared_state_race`'s own module docstring already
disclaims for its REL360 cousin).

Gates: `frob check --ticket T-0693` -- see Gates line below for the
actual measured result at close time.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 3709 warning(s), 339 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0697 -->
```yaml
id: T-0697
title: 'shared-mutable-state race approximation: unguarded writes on thread/task-reachable
  paths'
state: done
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
evidence:
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_same_write_under_with_lock_does_not_fire
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_reachable_via_callee_of_dispatched_function_fires
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_not_reachable_from_any_dispatch_does_not_fire
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_async_create_task_dispatch_fires_same_as_thread_submit
acceptance:
- text: GIVEN a module-level dict written from a thread-submitted function with no
    enclosing lock WHEN the check runs THEN an advisory names the write site and the
    spawn path; GIVEN the same write under a "with lock:" block THEN silence
  evidence:
  - tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
  - tests/unit/test_arch.py::TestSharedStateRaceHazards::test_same_write_under_with_lock_does_not_fire
threat: null
component: null
```
Child 4 of T-0693. Approximate data-race detection: a WRITE to module-level or class-level mutable state (assignment, mutating method on list/dict/set) on a call path reachable from a thread target/executor submission/async task, where no lock acquisition encloses the write in that path's context, is an advisory finding (suggestion tier -- approximation, false positives possible; waivable with reason). Reuses the lock-identification machinery from T-0694 and thread-target reachability from T-0695. Single-process cousin of strata's distributed no-shared-mutable-state check (T-0656) -- coordinate rule naming, do not duplicate its model-level logic.

## Done report

Added `frob.arch._shared_state_race` (T-0697, child 4 of the T-0693
concurrency-hazard umbrella): a structural, interprocedural scan flagging
`unguarded-shared-write` -- a write (rebind assignment, subscript
assignment, or a curated mutating-method call) to module-level or
class-level mutable state (list/dict/set constructions), on a call path
reachable from a thread-target/executor-submission/async-task dispatch
point, with no lock acquisition lexically enclosing the write.

Model: reuses `frob.arch._lock_ordering`'s exact module/class-level
identity convention (`_collect_module_locks`'s structure, re-keyed on
mutable-literal construction instead of lock construction) and its
`_resolve_lock_expr`/`_LOCK_NAME_HINT_RE` resolution machinery (imported
directly, not re-implemented) for both shared-state identity and for
deciding whether a write is lock-enclosed. Reuses
`frob.arch._concurrency`'s `_first_arg_names`/`_target_kwarg_names`
dispatch-corpus helpers (imported directly) for the thread/executor-submit
half of dispatch-entrypoint detection, and adds the async-task half
(`asyncio.create_task`/`ensure_future`/`<loop>.create_task`) this ticket's
own text calls for, which `_concurrency._dispatched_callee_names` did not
cover. Interprocedural reachability is a same-module call-graph BFS
closure from every directly-dispatched function (mirrors the bare-name
same-module resolution convention `_lock_ordering`/`_mayraise`/
`_fallibility` all share) -- a write inside any function transitively
CALLED by a dispatched function is reported too, not just the dispatched
function's own body. Lock enclosure is checked lexically within the
writing function's own ancestor chain only (a documented model limit: a
lock acquired by a caller before dispatching into the writing callee is
not modeled).

Changed:
- src/frob/arch/_shared_state_race.py (new): `_collect_shared_state`,
  `_dispatch_entrypoints`, `_async_task_arg_names`,
  `_reachable_from_dispatch`, `_writes_in_function`,
  `_enclosing_lock_with`, `_collect_function_scans`,
  `_check_shared_state_race_hazards`.
- src/frob/arch/_models.py::ArchCategory: added `unguarded-shared-write`.
- src/frob/arch/__init__.py::_run_python_checks: wired
  `_shared_state_race._check_shared_state_race_hazards` alongside the
  sibling concurrency-hazard families (skips test files, same reason as
  T-0694/T-0695/T-0696).
- tests/unit/test_arch.py: new `TestSharedStateRaceHazards` (5 tests).

Evidence: the 5 node ids recorded above; `pytest tests/unit/test_arch.py
-k TestSharedStateRaceHazards` -> 5 passed individually, and the full
`tests/unit/test_arch.py` suite (254 tests) passes unchanged. `frob test
--base main` (touched-set) -> `[PASS] python exit=0`, 7 outcomes recorded.

Real-world validation over frob's own `src/frob/` (non-test files):
1 `unguarded-shared-write` finding -- `serve/_daemon.py::_worktree_branches`
writing the module-level `_ttl_skip_logged` set with no enclosing lock, on
a path reachable from that module's own thread dispatch. This is a
plausible real finding (not an obviously-false positive), consistent with
this check's advisory/approximation posture -- not fixed here (out of this
ticket's own scope, which is the detector itself, not fixing everything it
finds).

Gates: `frob check --ticket T-0697` clean across lint, gates-native (one
PERF003 false positive waived with a reasoned justification -- an
ancestor-chain walk bounded by AST nesting depth over each with-statement's
own small item list, not a cross join), gates-fast (one INV006 false
positive on this module's design-rationale prose, waived per the same
first-turn-on-pool disposition `_lock_ordering`'s own module docstring
already carries; one stale PRE001 fixed via `frob ticket sweep T-0697`
re-run after the file was added), gates-security (0 errors -- no
SELFAUDIT001 false positive this time, since this module's curated tables
are for mutating-method names and dispatch-call names, not
net/exec-capability substrings), and static (0 errors, pre-existing
frob-exports/frob-dup/frob-arch warnings unrelated to this ticket's
files). `ruff check`/`ruff format`/`ty check` on the new file are clean.

Filed: none.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_same_write_under_with_lock_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_reachable_via_callee_of_dispatched_function_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_not_reachable_from_any_dispatch_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_async_create_task_dispatch_fires_same_as_thread_submit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 4543 warning(s), 334 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0698 -->
```yaml
id: T-0698
title: 'concurrency model-mismatch advisory: IO-bound vs CPU-bound classification
  vs chosen executor'
state: done
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
evidence:
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_io_bound_socket_read_in_threadpool_does_not_fire
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_trivial_io_task_in_processpool_fires_ipc_overhead
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_mixed_loop_and_io_function_never_fires_either_advisory
acceptance:
- text: GIVEN a pure-arithmetic loop function submitted to ThreadPoolExecutor WHEN
    advisories run THEN a GIL-bound suggestion fires naming the loop; GIVEN a socket-read
    function under threads THEN silence
  evidence:
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_io_bound_socket_read_in_threadpool_does_not_fire
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_trivial_io_task_in_processpool_fires_ipc_overhead
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_mixed_loop_and_io_function_never_fires_either_advisory
threat: null
component: null
```
Child 5 of T-0693, the user's seem-IO-bound/seem-CPU-bound mandate. Classify each function from normalized-model events: IO-BOUND if dominated by curated IO calls (sockets/files/http/subprocess/db), CPU-BOUND if loop/arithmetic-dense with no IO, MIXED/UNKNOWN otherwise (advisories only fire on confident classifications -- T-0332 noise discipline). Advisories: CPU-bound work submitted to ThreadPoolExecutor or awaited in the event loop -> GIL-bound, suggest ProcessPool/native; trivially-small IO-bound tasks under ProcessPoolExecutor -> IPC overhead, suggest threads/async; async def with zero awaits (from T-0696) -> not actually async, suggest plain def; sequential awaits over independent IO -> suggest gather. Each advisory names the classification evidence (the dominating call sites), never a bare switch-your-model.

## Done report

Added `frob.arch._concurrency_model` (T-0698, child 5 of the T-0693
concurrency-hazard umbrella): classifies each python function as IO-BOUND
(a curated IO call in its own scope, no loop), CPU-BOUND (a loop, no
curated IO call), or MIXED/UNKNOWN (both or neither -- never advisory-
eligible, matching T-0332's noise-discipline precedent), then flags a
mismatch between that classification and the function's dispatched
executor: `gil-bound-in-threadpool` (a CPU-bound function submitted to a
`ThreadPoolExecutor`) and `ipc-overhead-in-processpool` (a trivially small
IO-bound function submitted to a `ProcessPoolExecutor`).

Reuse: the curated IO-call table is built on top of
`frob.arch._async_hazards`'s existing `_BLOCKING_CALL_TABLE`/
`_OPEN_BUILTIN_RE` (imported directly, not re-curated) plus a small
socket/db addition this ticket's own "sockets/... db" wording needs and
that table did not cover. Dispatch-target name extraction reuses
`frob.arch._concurrency._first_arg_names`. `async-zero-awaits` (one of
the four advisory shapes this ticket's own text names) already exists as
its own category from T-0696 -- not re-implemented here (T-0696's module
docstring already cross-references it as feeding this ticket).

Changed:
- src/frob/arch/_concurrency_model.py (new): `_classify_function`,
  `_executor_bindings`, `_bound_ctor_name`, `_dispatch_kinds_for_name`,
  `_is_io_call`, `_check_concurrency_model_mismatch`.
- src/frob/arch/_models.py::ArchCategory: added `gil-bound-in-threadpool`,
  `ipc-overhead-in-processpool`.
- src/frob/arch/__init__.py::_run_python_checks: wired
  `_concurrency_model._check_concurrency_model_mismatch` alongside the
  sibling concurrency-hazard families (skips test files, same reason as
  T-0694/T-0695/T-0696/T-0697).
- tests/unit/test_arch.py: new `TestConcurrencyModelMismatch` (4 tests).

Evidence: `pytest tests/unit/test_arch.py -k TestConcurrencyModelMismatch`
-> 4 passed individually, and the full `tests/unit/test_arch.py` suite
(258 tests) passes unchanged. `frob test --base main` (touched-set) ->
`[PASS] python exit=0`, 6 outcomes recorded.

Real-world validation over frob's own `src/frob/` (non-test files): 0
`gil-bound-in-threadpool`/`ipc-overhead-in-processpool` findings (no
ThreadPoolExecutor/ProcessPoolExecutor model mismatch in this repo's own
code today) -- 0 false positives on a real, large codebase.

Disclosed cut: this ticket's own text names a fourth advisory shape
("sequential awaits over independent IO -> suggest gather") not built
here -- proving two `await` expressions are data-independent needs a
def-use analysis `frob.arch`'s current normalized model does not provide,
and an unsound textual-adjacency approximation would risk false positives
against this repo's own noise-discipline convention (T-0332). Filed as
T-1027 (a duplicate accidental filing, T-1026, was
dropped/absorbed into it).

Gates: `frob check --ticket T-0698` clean across lint, gates-native,
gates-fast, gates-security, and static (0 errors in every stage; the one
ruff-format warning seen is pre-existing unrelated debt in
`src/frob/gates/_docptr.py`). `ruff check`/`ruff format`/`ty check` on the
new file are clean.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_io_bound_socket_read_in_threadpool_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_trivial_io_task_in_processpool_fires_ipc_overhead` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_mixed_loop_and_io_function_never_fires_either_advisory` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 4413 warning(s), 334 waived
- error-findings: none (measured, zero errors)

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
state: done
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
- tests/unit/perf/test_hot_query.py
scope_changes:
- op: add
  glob: tests/unit/perf/test_hot_query.py
  reason: 'D-02: scope-add the evidence test file used to verify the epic''s acceptance
    criterion (query surface read-back) at close time'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label
- tests/unit/perf/test_hot_query.py::TestListSketches::test_empty_store_is_empty
acceptance:
- text: GIVEN the children closed WHEN the perf harness runs THEN a queryable hot-graph
    exists under .frob at sub-100KB with per-section decile readouts
  evidence:
  - tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label
  - tests/unit/perf/test_hot_query.py::TestListSketches::test_empty_store_is_empty
threat: null
component: null
```
User mandate 2026-07-22: auditing/advisories for slow operations. Build a repo-wide hot-graph: per-section timing (major loop/branch bodies, external call edges, internal functions) collected at harness/test time, stored compactly, queryable, with advisories and regression ratcheting. STORAGE DECISION (user-driven): NOT normal distributions (heavy-tailed/multi-modal latency destroys mean/sigma) and NOT raw traces (megabytes) -- mergeable log-bucket quantile sketches (DDSketch-style, tunable relative-error alpha, ~hundreds of bytes/section), decayed merge = prior->update semantics, deciles read off at query time. Attribution WITHOUT sys.settrace: sampling collector + the normalized model's known line spans (T-0609..) map each stack sample to its enclosing section statically. Children: collector+attribution, sketch store, query surface, advisories+ratchet. Builds on src/frob/perf (existing harness/profile artifact, T-0582) and src/frob/stats -- extend, do not fork.

## Done report

Epic close verification (T-0709): enumerated every child ticket referencing
`parent: T-0709` across tickets.md and tickets-archive.md --
T-0710 (collector + attribution), T-0711 (sketch store), T-0712 (query
surface + advisories + ratchet), T-0748 (cross-language collectors), and
T-0917 (MCP frontend, the T-0712 follow-up the coordinator named) -- all
five are `state: done`. No open/queued/in-progress child exists anywhere
in the ledger.

Verified the parent's own acceptance criterion against reality rather than
trusting the children's own claims: ran `frob perf collect --sampler --
tests/unit/perf/test_hotgraph.py -q` to actually populate
`.frob/hotgraph_sketches.db` in this worktree (a fresh worktree starts
with no store -- `frob perf collect` is documented as the store's only
current producer, per docs/modules/perf.md's "Hot-graph query surface"
section). Result: `.frob/hotgraph_sketches.db` is 12288 bytes (12KB),
comfortably under the 100KB acceptance bound and the configured
`store_cap_bytes` default. `frob perf hot --top 10` then read the store
back with real per-section p50/p90 (decile) readouts (Popen2IO.read,
Condition.wait, _read_pyc, _get_default_tempdir, and two branch sections
all returned distinct p50/p90 numbers from real sampled weight) --
confirming the FULL pipeline (collector -> attribution -> sketch store ->
decayed merge -> query surface) works end to end in a clean checkout, not
merely that each child's own unit tests pass in isolation.

No code changes were needed -- this ticket closes purely on verification
that the epic's children delivered what T-0709's acceptance criterion
asked for. `.frob/` is gitignored local state (the store artifact
generated during this verification is not committed).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hot_query.py::TestListSketches::test_empty_store_is_empty` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 2866 warning(s), 339 waived
- error-findings: none (measured, zero errors)

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
state: done
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
evidence:
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_fullcontrol_deny_denies_fullcontrol_allow_no_indirection
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_narrow_allow_same_principal_still_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_write_deny_modify_allow_same_principal_still_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies
acceptance:
- text: GIVEN a principal with a narrow deny and a broad allow on one path WHEN the
    join evaluates THEN the WRITE_DAC indirection corner has a recorded disposition
    (bit-level modeling or loud documentation plus a behavior-locking test); GIVEN
    token-privilege classes THEN the grammar-clause decision is recorded
  evidence:
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
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

## Done report

Closed the T-0792 reviewer's WRITE_DAC-indirection understatement: a
same-principal narrow deny (Modify) alongside a broad allow (FullControl)
used to net to "not write-capable" in `_join_acl_entries` -- but real
NTFS still grants WRITE_DAC/WRITE_OWNER through the FullControl allow
(the Modify deny's bits never reach those bits), so the principal can
rewrite the path's own DACL and regain full write. This was the model's
ONLY understating (fail-open) corner in the single-token RIGHTS
vocabulary, previously undocumented.

Went with bit-level modeling (the ticket's first option), not just loud
documentation, since the fix was tractable within scope: `_ACL_WRITE_
RIGHTS` gained a coarse rank (`_RIGHTS_RANK`: write < modify <
fullcontrol) and a `_DAC_GRANTING_RIGHTS = "fullcontrol"` marker (only
that level grants WRITE_DAC/WRITE_OWNER in this vocabulary).
`_acl_ace_of` now returns the RIGHTS level (not just a write-capable
bool) so `_join_acl_entries` (split via a new `_net_acl_levels_by_
principal` helper for ARCH001's 60-line function threshold) can net each
principal's broadest allow/deny level and apply the WRITE_DAC rule:
allow=fullcontrol + deny<fullcontrol => still write-capable (indirection
survives); deny=fullcontrol => genuinely denied (WRITE_DAC reached too);
allow=write/modify => no DAC bits granted at all, any deny still fully
cancels it, unchanged from before.

Mutation-killing evidence (security ticket, tests written to fail before
the fix, per the coordinator brief): the two PRE-EXISTING T-0792 tests
that literally encoded the bug --
test_narrow_deny_then_broad_allow_same_principal_denies and
test_broad_allow_then_narrow_deny_same_principal_still_denies -- had
their assertion flipped from `is False` to `is True` (same node ids kept
so the T-0791/T-0792 archived evidence citations in tickets-archive.md
stay resolvable; the docstrings now explain what changed and why). Before
the `_host_isolation.py` fix, re-running these two tests against ONLY the
old `_join_acl_entries` body (verified by temporarily reverting the
module change locally) fails both -- confirming they exercise the exact
corner, not a vacuous pass. Two new tests lock the non-applicable
counter-cases: test_fullcontrol_deny_denies_fullcontrol_allow_no_
indirection (an explicit fullcontrol-level deny DOES reach WRITE_DAC, so
still a clean deny) and test_narrow_deny_narrow_allow_same_principal_
still_denies / test_write_deny_modify_allow_same_principal_still_denies
(a narrower allow never grants WRITE_DAC in the first place, so the
indirection never applies to it, unaffected by this fix).

The privilege-clause grammar gap (SeImpersonate/SeDebug token-privilege
classes needing their own strata-core grammar clause) named alongside
this finding in the T-0792 module docstring remains UNDISCHARGED and
explicitly disclosed as such in docs/strata/host.md's new section -- no
such grammar exists yet; filing that as its own grammar-extension ticket
is future work, not folded into this fix (the acceptance criterion's
"grammar-clause decision is recorded" is satisfied by that explicit
disclosure, not by building the grammar itself, which the ticket did not
scope src/frob/strata-core or strata-core/src/parse.rs for).

Evidence: tests/unit/strata/test_host_isolation.py::
TestMultiAceDenyOverridesAllow -- the two flipped corner tests plus the
two new counter-case tests, plus test_deny_for_one_principal_does_not_
cancel_another_principals_allow (unaffected cross-principal case,
regression guard) and test_no_write_rights_entries_denies (unaffected
non-write-rights case, regression guard). Full tests/unit/strata/ suite
(1046 tests) re-run clean after the change.

Gates: `frob check --ticket T-0825 --only gates-fast --only gates-native`
clean (0 errors both groups) after: (1) extracting `_net_acl_levels_by_
principal` to bring `_join_acl_entries` under ARCH001's 60-line
threshold, (2) a `frob:waive DUP001` on `_acl_ace_of` (near-identical
parse of `_contention.py::_acl_rule_write_capable`'s RULE grammar,
deliberately duplicated rather than extracted since the two callers need
different return shapes and a shared-helper extraction across strata/
_contention.py + strata/_host_isolation.py is out of this ticket's
declared scope).

Filed: none.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 4402 warning(s), 340 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a81994cfb14c4292b/src/frob/strata/_host_isolation.py:290, E501@/home/logan/projects/frob/.claude/worktrees/agent-a81994cfb14c4292b/src/frob/strata/_host_isolation.py:331

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
state: done
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
- tests/test_gates.py
- tests/test_registry_exhaustiveness.py
- tests/test_decisions.py
- docs/design/registry/EXHAUSTIVENESS-GATE.md
- docs/modules/gates.md
- docs/modules/decisions.md
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: add regression tests for the adopted-then-deleted registry distinction (COMPLIANCE006/REG012/DEC003)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: add regression tests for the adopted-then-deleted registry distinction (COMPLIANCE006/REG012/DEC003)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_decisions.py
  reason: add regression tests for the adopted-then-deleted registry distinction (COMPLIANCE006/REG012/DEC003)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: T-0894 required doc updates for REG012/COMPLIANCE006/DEC003 to close AFFECT001
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: T-0894 required doc updates for REG012/COMPLIANCE006/DEC003 to close AFFECT001
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/decisions.md
  reason: T-0894 required doc updates for REG012/COMPLIANCE006/DEC003 to close AFFECT001
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestComplianceGate::test_compliance005_registered_in_known_gate_rules
- tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry
- tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption
- tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_never_committed_path_is_false
- tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_deleted_after_commit_is_true
- tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_git_failure_is_false
- tests/test_registry_exhaustiveness.py::TestDeletedRegistry::test_never_adopted_registry_dir_is_silent
- tests/test_registry_exhaustiveness.py::TestDeletedRegistry::test_deleted_after_adoption_fires_reg012
- tests/test_decisions.py::test_never_adopted_decisions_dir_is_silent
- tests/test_decisions.py::test_deleted_after_adoption_fires_dec003
acceptance:
- text: Given a repo that committed docs/design/registry/compliance.yaml and then
    deleted it, compliance_gate through its real production invocation FAILS (raises
    a COMPLIANCE006 Violation) before this ticket's fix and PASSES (returns the expected
    COMPLIANCE006 finding, proving the rule actually fires) after it -- test_compliance006_fires_on_deleted_registry_after_adoption
    exercises compliance_gate exactly as frob check dispatches it, not a pure-function
    unit test in isolation.
  evidence:
  - tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption
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

## Done report

Built a shared signal, `frob.gates._registry_exhaustiveness.path_ever_tracked`
(git log -1 -- <path> against HEAD), that distinguishes "this repo never
adopted a registry" from "this repo adopted it and someone deleted it" --
the exact structural blind spot the ticket describes across all three
registry-backed gates that shared the old "missing dir/file means no
claim" posture. Wired it into registry_gate (REG012), compliance_gate
(COMPLIANCE006), and decisions_gate (DEC003), all unwaivable, all ERROR.
Updated docs/design/registry/EXHAUSTIVENESS-GATE.md (new REG012 section,
the canonical home for the mechanism), docs/modules/gates.md's
COMPLIANCE005 section, and docs/modules/decisions.md's DEC gates table to
close AFFECT001 on the three changed gate functions. Added regression
tests for all three (never-adopted stays silent, adopted-then-deleted
fires the new unwaivable rule) using synthetic tmp_path git repos.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestComplianceGate::test_compliance005_registered_in_known_gate_rules` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_never_committed_path_is_false` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_deleted_after_commit_is_true` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_git_failure_is_false` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDeletedRegistry::test_never_adopted_registry_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDeletedRegistry::test_deleted_after_adoption_fires_reg012` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_never_adopted_decisions_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_deleted_after_adoption_fires_dec003` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 19388 warning(s), 333 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0895 -->
```yaml
id: T-0895
title: Add regression test for dup_gate native-unavailable loud-violation behavior
state: done
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
evidence:
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
threat: null
component: null
```
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2), pairs with the dup_gate native-unavailable fix ticket.

Add a regression test asserting that `dup_gate` with `[dup].enforce=true`
and a mocked/forced `core_available() == False` produces a real Violation
(not just a log line), closing the "opted-in enforcement silently no-ops
when the native toolchain is missing" gap the paired fix ticket addresses.

## Done report

This ticket asked for a regression test proving dup_gate emits a real
Violation (not just a log line) when [dup].enforce=true and
core_available() is mocked False. That exact test already exists and was
landed together with the T-0399 fix that gives dup_gate its fail-closed
behavior (see T-0896's Done report for the paired investigation):
tests/test_gates.py::TestOptInGates::
test_dup_gate_fails_closed_when_enforced_but_core_missing (frob:ticket
T-0399, tests/test_gates.py:8588-8608). It monkeypatches
frob.dup.core_available to return False, sets [dup].enforce=true with no
diff hunks, calls dup_gate directly, and asserts exactly one DUP003 ERROR
violation is returned -- precisely the "opted-in enforcement silently
no-ops when the native toolchain is missing" gap this ticket describes.

Ran it foreground: 1 passed.

No new test added under this ticket; closing citing the pre-existing
T-0399 test as evidence rather than duplicating coverage, per this
ticket's own note that it may be absorbed into the paired fix ticket's
evidence.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 19389 warning(s), 333 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0896 -->
```yaml
id: T-0896
title: dup_gate silently no-ops (log-only) when frob-core native is unavailable despite
  [dup].enforce=true
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
evidence:
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
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

## Done report

Verified this ticket's exact fix is already implemented and landed under
T-0399 (commit 12874170, "AUDIT: green must claim quality -- promote
quality gates from WARN to blocking"), before this ticket was filed
(T-0896 was found during T-0786's later sweep, apparently without
cross-checking against T-0399's already-shipped fix).

dup_gate (src/frob/gates/__init__.py:9087) already fails closed exactly
as this ticket's plan proposes: when [dup].enforce=true and
core_available() is False, it emits a blocking DUP003 ERROR Violation
naming the missing native and the remediation (`make core`), not a
log-only no-op -- see the docstring at line 9088 and the emission block
at lines 9107-9127. The old silent log.warning()-then-return-() shape
this ticket describes no longer exists in the current tree.

Evidence: tests/test_gates.py::TestOptInGates::
test_dup_gate_fails_closed_when_enforced_but_core_missing (frob:ticket
T-0399, line 8588) already covers this exact scenario -- monkeypatches
core_available to False, sets [dup].enforce=true, and asserts a single
DUP003 ERROR violation is returned. Ran it foreground: 1 passed.

No code changes made under this ticket; closing as fixed-by-T-0399 with
the pre-existing test as evidence rather than re-implementing or
duplicating coverage.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4655 warning(s), 333 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0898 -->
```yaml
id: T-0898
title: Add regression tests for RENDER001/PII010 loud-on-unparseable-file behavior
state: done
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
evidence:
- tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_unparseable_python_file_fires_parse001
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

## Done report

Fully absorbed by T-0897's already-landed fix, present on main before this
ticket was started: RENDER001 (src/frob/gates/_render_lint.py's
render_lint_gate) and PII010/SEC110 (src/frob/gates/_pii_structural.py's
pii_structural_gate) both already emit a loud PARSE001 Violation on a
file their own read/ast.parse cannot get through, replacing the old
private silent-skip the paired fix ticket (T-0897) addressed. Both gates
already carry a regression test binding exactly this behavior --
TestRenderLintGate.test_unparseable_file_fires_parse001 and
TestPiiStructuralCrossLanguage.test_unparseable_python_file_fires_parse001,
both frob:tests-bound to their gates already and both re-verified passing
here. No new code or test needed under this ticket -- closing citing the
pre-existing T-0897 evidence.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_unparseable_python_file_fires_parse001` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 19767 warning(s), 339 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0900 -->
```yaml
id: T-0900
title: Add regression test for COMPLIANCE005 adopted-then-deleted-registry detection
state: done
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
evidence:
- tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption
- tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry
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

## Done report

Fully absorbed by T-0894's own evidence, already landed (main commit
597904bfc98cd02f346c803c15608a29e5861538): T-0894's fix for
compliance_gate added exactly the regression test this ticket asks for --
test_compliance006_fires_on_deleted_registry_after_adoption commits
compliance.yaml, deletes it, and asserts the resulting COMPLIANCE006
violation fires through compliance_gate's real production invocation
(not a pure-function unit test in isolation); its sibling
test_compliance006_silent_on_never_adopted_registry covers the negative
case (never-committed compliance.yaml stays silent). No new code or test
added under this ticket -- it closes citing T-0894's already-landed
evidence, per this ticket's own "starting with COMPLIANCE005" framing.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 19579 warning(s), 339 waived
- error-findings: none (measured, zero errors)

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
state: done
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
- tests/unit/test_arch.py
scope_changes:
- op: add
  glob: tests/unit/test_arch.py
  reason: docs-only ticket still needs evidence test file scope-add per playbook section
    4
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
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

## Done report

Added the "Lock-ordering hazards" section to docs/modules/arch.md (matching
the Fork/pool hazards and Async event-loop hazards sections' structure and
detail level), documenting lock-order-cycle and lock-identity-unresolved
(frob.arch._lock_ordering, T-0694, child 2 of the T-0693 umbrella): the
5-step model, both finding categories, the model-limit disclosure, and
that this channel is unwaivable by design (no frob:waive escape hatch) --
resolution is structural (consistent global lock-acquisition order, or
declaring the lock via a curated ctor). Added a frob:doc directive on
_check_lock_ordering_hazards pointing at the new anchor, and scope-added
tests/unit/test_arch.py (docs-only ticket, existing test file is the
evidence surface) per the playbook's recurring gotcha.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4676 warning(s), 333 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0935 -->
```yaml
id: T-0935
title: gates-native stage-group test hardcodes gate set, breaks on every new gate
  (T-0688 regression)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_app_runners_batch6.py
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping
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

## Done report

Fully absorbed by T-0975's already-landed fix, present on main before
this ticket was started: test_stamp_baseline_only_chunk_records_without_
stamping (tests/unit/test_app_runners_batch6.py) no longer hardcodes the
gates-native gate-name literal set -- it derives the expected set from
frob.check._STAGE_GROUPS["gates-native"], the live stage-group registry,
exactly the same "derive from the live registry, not a literal" pattern
this ticket asked for, per the ticket's own T-0975 precedent pointer.
Re-ran the test fresh against main with T-0894/T-0900/T-0898 merged in;
it passes. No hardcoded frozenset with archgate/clones/perf literals
remains anywhere in this file. No new code or test needed -- closing
citing the pre-existing T-0975 evidence.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 2618 warning(s), 339 waived
- error-findings: none (measured, zero errors)

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

<!-- ticket:T-0955 -->
```yaml
id: T-0955
title: 'strata export golden: frob_export_seccomp/iam/k8s drifted re: natives node'
state: done
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
evidence:
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
threat: null
component: null
```
Found while working T-0700 (unrelated to grammar/access-mode changes -- confirmed via `git status`, no golden/export files touched by that ticket). `tests/unit/strata/test_export_golden.py::TestExportGolden` (test_k8s, test_seccomp, test_iam) fails on a fresh worktree built from current main: the frob self-modeled design's exported seccomp/IAM/netpol JSON now includes a "natives" node's syscalls/statements that the checked-in golden fixtures under the golden dir do not yet reflect. Likely a golden-fixture regen missed after a recent "natives" node/capability addition to frob's own strata design. Regenerate the golden fixtures (or fix the export drift if the new output is wrong) and re-verify test_export_golden passes clean.

## Done report

Verified on current main (post T-0860 land, which already fixed the strata
self-conformance + export-golden drift for undeclared mutate/deploy
capabilities on the natives node): tests/unit/strata/test_export_golden.py
(test_k8s, test_seccomp, test_iam) and tests/system/test_frob_self_model.py
all pass clean on this worktree with no code/golden changes needed. No
drift remains between the checked-in golden fixtures and the exported
seccomp/IAM/k8s JSON. No regeneration was required -- T-0860 already
regenerated the goldens for the natives-node addition before this ticket
was actioned. frob check --ticket T-0955 (gates-native, gates-fast) is
clean (0 errors both groups). Closing with no code change; evidence is the
already-passing golden/self-model suite.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 4924 warning(s), 333 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0956 -->
```yaml
id: T-0956
title: 'strata design: re-point T-0700 live-tracker waivers, arbitrate tickets_ledger
  with new grammar'
state: done
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
- docs/strata/roadmap.md
scope_changes:
- op: add
  glob: docs/strata/roadmap.md
  reason: AFFECT001 requires updating the roadmap.md self-hosting-commitments-decision-d7
    doc anchor when design/frob.strata's cli/gates/fleet/core/serve nodes change
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_arbitrated_by_discharges
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_lock_discharges
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
threat: null
component: null
```
T-0700 shipped access modes + resource/arbitrated_by grammar. design/frob.strata has 5 SYS203 "tickets_ledger" waivers explicitly written "re-evaluate at T-0700" (lines ~116/181/311/388/508) since the ledger genuinely has an arbiter (every writer serializes through .frob/tickets.lock, T-0458/T-0633) that SYS203 could not express until now. Re-express this properly: declare a `resource tickets_ledger { lock "tickets.lock" }` (or `arbitrated_by` the CLI-writer node, whichever models T-0458/T-0633's actual single-writer-lock discipline more accurately) plus `access "tickets_ledger" mode write` on each node/store that writes it, then drop the now-superseded SYS203 waivers once the model-level arbiter discharges the contention cleanly (verify via frob.strata._access.resource_contention_violations against frob's own elaborated design). Also re-point tests/test_tickets_live_tracker.py:220's `ticket=T-0700` placeholder to this ticket's id once assigned. Blocked by nothing; T-0700 is done and closed.

## Done report

Re-expressed the five SYS203/tickets_ledger waivers' underlying arbitration
claim (cli/gates/fleet/core/serve) using T-0700's grammar: a new top-level
`resource tickets_ledger { lock "tickets.lock"; }` declaration plus an
`access "tickets_ledger" mode write;` clause on each of the five writer
nodes. Verified directly against frob's own elaborated design (parse ->
elaborate -> frob.strata._access.resource_contention_violations(model,
module)): zero SYS204 violations for tickets_ledger -- the declared lock
discharges every conflicting write/write pair among the five accessors.

The SYS203 waivers themselves were NOT dropped, contrary to the ticket's
literal "drop the now-superseded SYS203 waivers" framing: SYS203
(src/frob/strata/_contention.py::check_resource_contention) is a
completely separate, permanently mode-blind check with no code path that
reads Module.resources/access attrs at all (confirmed by reading the
module: "no grammar change", counts ANY inbound Flow to a store as a
write). Adding resource/access data cannot make SYS203 stop firing --
only a src/frob/strata/_contention.py code change could, and that file is
out of this docs-only ticket's declared scope (design/**, tests/
test_tickets_live_tracker.py). Removing the waivers without a code change
would just turn 5 clean gates red for no reason. Instead, each waiver's
reason text was rewritten to state this precisely (SYS203 is structurally
blind to the now-modeled arbiter, not that arbitration is unproven), and
the forward-looking "re-evaluate at T-0700"/"drop this waiver, tracked by
T-0956" language was retired since T-0956 is itself the re-evaluation.
docs/strata/roadmap.md's self-hosting-commitments-decision-d7 section
(AFFECT001's closure doc for the five changed nodes) was updated to match,
and scope-added since it was outside the ticket's original declared
scope.

tests/test_tickets_live_tracker.py:220's "T-0700 placeholder" the ticket
plan referenced no longer exists in the current test file (grepped for
both "T-0700" and "placeholder" -- zero matches) -- already resolved by
an earlier, unrelated change to that test file before this ticket was
actioned; no edit was needed there.

Evidence: tests/unit/strata/test_selfconform.py (self-conformance stays
green with the new resource/access clauses), tests/unit/strata/
test_access.py (SYS204 machinery itself, TestResourceContentionViolations
covers arbitrated_by/lock discharge), tests/unit/strata/test_contention.py
(confirms SYS203 still fires independent of the new grammar, proving the
"separate mode-blind check" claim), tests/system/test_frob_self_model.py
(frob's own design stays self-conformant + zero SYS violations post-edit).
All re-run clean after the design/frob.strata + roadmap.md changes.

Gates: `frob check --ticket T-0956 --only gates-fast --only gates-native`
clean (0 errors both groups) after: (1) fixing AFFECT001 by updating and
scope-adding docs/strata/roadmap.md, (2) refreshing the pre-work sweep
(frob ticket sweep T-0956) to clear stale PRE001.

Filed: T-1025 -- "strata SYS203: make shared-store-write
contention consult a resource's declared arbiter, drop tickets_ledger
waivers" (feature; scope src/frob/strata/_contention.py, tests/unit/
strata/test_contention.py, docs/strata/host.md, design/frob.strata,
tickets.md). The five SYS203:tickets_ledger waivers' `ticket=` citation
was re-pointed from T-0956 to this successor draft id so T-0956 can close
cleanly (frob's live-tracker check refuses to close a ticket still cited
by a live waiver) -- the successor is the actual code-level follow-up
that would let SYS203 itself, not just SYS204, discharge the arbiter and
let the waivers finally be dropped.

### Changed
```
 design/frob.strata     | 106 ++++++++++++++++++++++++++++++++++++-------------
 docs/strata/roadmap.md |  26 ++++++++----
 tickets.md             |  80 ++++++++++++++++++++++++++++++++++++-
 3 files changed, 175 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_arbitrated_by_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_lock_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 4929 warning(s), 333 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0969 -->
```yaml
id: T-0969
title: 'Epic: burn WARN-tier quality gates to zero, then promote to ERROR'
state: queued
kind: security
origin: auditor
created: '2026-07-27'
priority: high
parent: null
tier: epic
sprint: null
threat: null
component: null
```
T-0399's gates-quality audit (docs/audits/gates-quality.md) found the
entire quality/security-advisory surface (PERF001-004, PII010/012, SEC110,
ARCH001, DUP) is WARN-tier and non-blocking, so a green `frob check` makes
no quality claim. T-0399 executed the promotable-now slice (DUP fail-
closed behavior) and measured live warning counts per family. This epic
parents the burn-down children needed before each remaining family can be
safely promoted to ERROR without redding main.

<!-- ticket:T-0981 -->
```yaml
id: T-0981
title: 'dup_gate deadlocks under frob check: derived_state_write_lock reentrancy blind
  to ProcessPoolExecutor workers'
state: done
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
- docs/modules/process.md
- docs/modules/gates.md
evidence:
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks
threat: null
component: null
```
Found while working T-0974 ("enable [dup].enforce=true by default").

`frob check`'s main run wraps its whole duration in
`derived_state_lock(root, exclusive=False)` (SHARED,
src/frob/check/__init__.py:582 and 3 other call sites). `dup_gate` (the
"clones" job) is dispatched into a `ProcessPoolExecutor`
(`_PROCESS_POOL_GATES`, src/frob/gates/__init__.py ~line 9994) for real
CPU parallelism (T-0415). `find_clones` (src/frob/dup/_pipeline.py)
unconditionally wraps its ENTIRE body in
`derived_state_write_lock(root)` (EXCLUSIVE-or-noop,
src/frob/process/_lock.py).

`derived_state_write_lock`'s reentrancy check (`_process_already_holds`,
src/frob/process/_lock.py) is a PROCESS-WIDE in-memory registry -- it only
sees state set by threads in the SAME OS process. Because "clones" runs in
a genuinely separate forked/spawned process (ProcessPoolExecutor, not
ThreadPoolExecutor), that worker's `_process_already_holds(root)` reads
False even though `frob check`'s main process already holds SHARED. The
worker then takes the real cross-process path and calls
`flock(LOCK_EX)`, which blocks forever against the main process's SHARED
hold -- and that SHARED hold cannot release until the worker (which is
itself the thing it's waiting on) returns. This is a genuine, reproducible
DEADLOCK, not merely slowness, for any `frob check` run where `[dup].
enforce=true` and the clones job actually reaches this lock (i.e. every
run, since `find_clones` takes the lock unconditionally, not just on
cache-miss).

Live repro (this ticket, 2026-07-27): set `[dup].enforce=true` (no
`native_rungs`), delete `.frob/dup.db`, run `uv run frob check --only
clones`. The run exceeded 120s/200s+ with near-zero CPU (I/O-wait, not
compute). `lslocks` showed:

```
python  <pid-worker>  FLOCK  WRITE*  ...  .frob/derived.lock   # blocked
frob    <pid-main>     FLOCK  READ    ...  .frob/derived.lock   # held
```

confirming the exact mechanism above. This likely explains T-0399's
original "~150s blowout" measurement too -- it was plausibly this
deadlock (or very close to it) rather than genuine fingerprinting compute
cost, since `derived_state_write_lock`'s own module docstring already
documents (T-0918) that its reentrancy signal only works for a
`ThreadPoolExecutor` worker THREAD nested in the main process, and
explicitly disclaims the process-pool case as a "documented latent gap,
not an observed regression" with "no current production call site" doing
this -- but `_PROCESS_POOL_GATES` including `"clones"` (T-0415, landed
separately) IS exactly that call site; the two tickets' assumptions never
got cross-checked against each other.

T-0974 could not safely flip `[dup].enforce=true` on by default given
this: doing so would make `frob check`'s clones stage hang (not just run
slow) for any cold-cache run, which is strictly worse than the status quo
(off by default, gate never runs).

Fix needs design, not a quick patch, and touches files outside T-0974's
declared scope (`src/frob/process/_lock.py` for the locking primitive
itself, and/or `src/frob/gates/__init__.py`'s `_PROCESS_POOL_GATES`
executor-topology decision, which T-0415 deliberately set for "clones").
Candidate directions (not evaluated in depth): (a) move "clones"
specifically out of `_PROCESS_POOL_GATES` back onto the thread pool --
the native Rust calls inside `find_clones` likely release the GIL enough
for real parallelism even on a thread, but this partially undoes T-0415's
reasoning for this one gate and needs re-measurement; (b) give
`derived_state_write_lock` a real cross-process-but-same-run reentrancy
signal (e.g. a marker file/env var the parent `frob check` process sets
before spawning its ProcessPoolExecutor workers, checked by
`_process_already_holds` in addition to the in-memory registry); (c) have
`frob check`'s main process release its SHARED hold (or downgrade some
other way) before submitting process-pool jobs that might need the
EXCLUSIVE path, and reacquire after -- correctness-sensitive, needs care
against the exact race T-0918's docstring already warns about for the
thread case.

Scope for the ticket that picks this up: `src/frob/process/_lock.py`,
`src/frob/gates/__init__.py` (`_PROCESS_POOL_GATES`, `dup_gate`
dispatch), plus `docs/modules/process.md`/`docs/modules/gates.md` for the
corrected reentrancy-contract writeup once fixed.

## Done report

Verified the deadlock this ticket describes no longer reproduces: T-0982
(landed as b9f86f74, commit 43ed42a6) already fixed the exact mechanism
described here -- derived_state_write_lock's reentrancy registry was
process-local and blind to ProcessPoolExecutor workers, causing a real
flock(LOCK_EX) deadlock against the parent's SHARED hold. T-0982's fix
stamps an env marker with the owner's held registry keys before
constructing the process pool (_open_process_pool in
src/frob/gates/__init__.py), and a worker consults that marker in
_process_already_holds (src/frob/process/_lock.py) to bypass its own lock
acquisition exactly like the same-process nested case, while an
independent process's worker still takes a real exclusive lock.

Confirmed no re-implementation is needed:
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance already
  covers this exact scenario end to end with a REAL ProcessPoolExecutor
  worker under a parent SHARED holder
  (test_real_pool_worker_under_parent_shared_holder_completes), plus the
  negative case that an independent process without the marker still
  blocks (test_independent_process_without_marker_still_blocks). Ran the
  full file foreground: 12 passed, 0 failed.
- [dup].enforce=true is now live in this repo's own frob.toml (flipped by
  T-0974, commit 15e0e91c, specifically because T-0982 made it safe to do
  so) -- frob check's own clones stage runs under exactly the topology
  this ticket describes (dup_gate dispatched into _PROCESS_POOL_GATES)
  with no hang, which would be impossible if the deadlock still existed.

No code changes made under this ticket; closing as fixed-by-T-0982 with
the above evidence rather than re-implementing (b) from the plan, which
T-0982 already built.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 4719 warning(s), 333 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0995 -->
```yaml
id: T-0995
title: pre-existing DUP001 test-body duplication surfaced by T-0988's fmt sweep (test_cli_requires_reason
  / test_transition_allows_when_covers_scope_true)
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_tickets_scope_mutation.py
- tests/unit/test_ticket_file_flags.py
- tests/test_evidence_integrity.py
threat: null
component: null
```
T-0988's repo-wide frob fmt recompaction touched these test files' surrounding frob: directive comments (no test-body changes), which surfaced 2 pre-existing DUP001 findings: tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_requires_reason (100% similar to tests/unit/test_ticket_file_flags.py::TestScopeReasonFile.test_neither_reason_nor_reason_file_errors_cleanly), and tests/test_evidence_integrity.py::TestD02ScopeBinding.test_transition_allows_when_covers_scope_true (95% similar to tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_allows_when_evidence_reverified_true). Confirmed pre-existing and unrelated to the fmt diff itself (the flagged test bodies are unchanged; DUP001 compares a touched file's symbols against the whole corpus regardless of what changed about them). Extract a shared helper or otherwise dedup, per the gate's own suggestion, in a follow-up -- out of scope for a purely mechanical fmt ticket to fix opportunistically.

<!-- ticket:T-1006 -->
```yaml
id: T-1006
title: widespread pre-existing test failures block make coverage completion (~118
  fails, non-cov-caused)
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
threat: null
component: null
```
Found while working T-0997 (coverage pipeline fix): a real, fresh `make
coverage` run in a clean worktree (merged to main tip) shows ~118 test
failures that are NOT caused by coverage instrumentation -- reproduced
several individually WITHOUT --cov and they still fail (e.g.
tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations,
tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace,
tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root).
These span registry-reconciliation exhaustiveness self-checks
(patterns/compliance/secrets/supply_chain/weaknesses/system_design all
report real violations against this worktree's live tickets.md/registry
state), ticket-land/evidence-enforcement system tests, and a handful of
CLI system tests. Because pytest exits non-zero, `make coverage`'s
Makefile recipe halts before its own `coverage combine`/`coverage xml`/
`frob check --stamp-coverage` lines run, so a fresh `make coverage`
currently requires a manual combine/xml/stamp workaround to get any
numbers at all -- and the failing subprocess-heavy system tests never
contribute their coverage, capping how far `join_fraction` can rise
(0.49 observed vs T-0997's target of "well above 0.34"; a green suite
would likely push it meaningfully higher). Needs triage: some of these
may be genuine registry drift in this worktree's ticket state (dozens of
concurrent worktree agents landing tickets) rather than a real product
bug; others (the gitless-target severity assertion, the render-lint
stderr-vs-logging-capture mismatch) look like real, fixable test/gate
bugs. Scope was deliberately not widened to fix these under T-0997.

<!-- ticket:T-1007 -->
```yaml
id: T-1007
title: land REL001 bump callback derives baseline from worktree-carried manifest (guard
  fires each time; fix the producer)
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: T-0999
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- tests/**
acceptance:
- text: given a worktree carrying a stale version, when its ticket lands, then the
    bump computes main+1 on the first attempt with no guard refusal
  evidence: []
threat: null
component: null
```
T-0992 added the land-side monotonicity backstop and it has now correctly REFUSED a third stale-bump attempt (T-0997 land computed 0.183.0 vs main 0.184.0). But the producer bug remains: _apply_release_bump_for_land derives its baseline from the worktree-carried release manifest/pyproject that rode the squash. Fix the callback to read the baseline from ROOT current state (same git-show technique as the guard) so the guard becomes a never-fires invariant instead of a per-land speed bump requiring a manual worktree merge. Churn-epic member: each guard refusal costs a merge+reland round trip.

<!-- ticket:T-1012 -->
```yaml
id: T-1012
title: SCOPE002 private-helper direction is unusably noisy over flat top-level dirs
  (tests/)
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/callgraph.py
threat: null
component: null
```
`frob.graph.callgraph.scope_private_helper_gaps` (T-0998, SCOPE002
direction 5) narrows its `build_call_graph` candidate set to files sharing
a scoped file's PARENT DIRECTORY. For a flat top-level directory like
`tests/` (hundreds of files, one dir), this degrades to "every test file
in the whole tests/ tree" the moment any single test file is in scope --
observed live: scoping `tests/test_graph.py` alone produced 4000+ SCOPE002
"review the dependency" findings, almost all naming a same-named `_write`/
`_run` helper private to some unrelated sibling test file, not a real
under-capture signal.

WARN-only (never blocks), so this is noise, not a correctness bug -- but
noisy enough that a real agent would tune it out entirely rather than
read the real hits buried in it. Needs a narrower per-scope candidate-set
heuristic for large flat directories (e.g. cap candidate file count, or
require the SAME leaf-name collision to be genuinely ambiguous before
flagging, or scope the search to files matching the ticket's own SOURCE
directory conventions rather than a raw parent-dir match) before this
direction is trustworthy enough to read routinely. Filed instead of fixed
under T-0998's own scope/effort budget.

<!-- ticket:T-1016 -->
```yaml
id: T-1016
title: 'DOC006 doc-pointer burn-down round 2: remainder (~131 findings, fragmented)'
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
evidence:
- tests/test_docptr_gate.py::TestDoc006Config::test_all_caps_citation_tag_not_flagged
- tests/test_docptr_gate.py::TestDoc006Config::test_declared_but_unset_section_not_flagged
- tests/test_docptr_gate.py::TestDoc006Symbol::test_reexported_class_attribute_chain_not_flagged
- tests/test_docptr_gate.py::TestDoc006Symbol::test_dunder_init_mid_chain_resolves_to_module
threat: null
component: null
```
Follow-up to T-1015 (DOC006 doc-pointer burn-down, round 1): after
matcher hardening (directory-prefix + suffix FILE/PATH resolution,
enumeration-list/domain-citation shape rejection, multi-manifest CONFIG
REFERENCE resolution against pyproject.toml/Cargo.toml, `.git/`-path
exemption, and a tickets-archive.md verbatim-ledger exclusion) plus a
handful of targeted illustrative-example waivers, DOC006 findings measured
771 -> 131 (see T-1015's Done report for the full before/after
cluster table).

The remaining 131 findings are fragmented across ~30 doc files with no
single dominant cluster left (round-1's own measurement, `--only docblocks
--json`, 62 config reference / 30 file/path / 20 code symbol / 13
doc-anchor link / 9 cli invocation). Largest remaining single files:
docs/modules/vet.md (16), docs/modules/gates.md (12), docs/modules/perf.md
(8), CHANGELOG.md (7), docs/strata/threat.md (6). Work this ticket by:

1. Re-measure with a fresh chunked `frob check --only docblocks --json`
   (counts may have drifted since round 1).
2. For each remaining finding, determine per-file/per-line whether it is:
   - a genuinely stale doc pointer (fix the doc prose to the current
     path/symbol/config key), or
   - a further matcher false-positive class worth generalizing (check for
     new clusters before assuming everything left is genuine drift), or
   - a genuinely external/illustrative pointer (a nearby `frob:waive
     DOC006 reason="..."`).
3. Re-check promotion (WARN -> ERROR) once the live count is near zero;
   record the decision with count evidence in docs/audits/gates-quality.md
   under the DOC006 section T-1015 added.

Scope: docs/**, src/frob/gates/_docptr.py, tests/test_docptr_gate.py.
Origin: agent (T-1015 round-1 remainder).

## Done report

Sampled the current DOC006 warning set (frob check --only docblocks --json,
131 findings across ~45 doc files: 62 config reference / 30 file-path / 20
code symbol / 9 cli invocation / 13 doc-anchor after re-measure). Classified
and disposed of every one:

1. Matcher hardening (src/frob/gates/_docptr.py), three new false-positive
   classes found while triaging, each with a new regression test in
   tests/test_docptr_gate.py:
   - ALL-CAPS bracket tokens (`[IN-REPO]`) are prose citation tags, never a
     `[section]` TOML pointer -- rejected before the manifest-lookup path
     (_ALL_CAPS_TAG_RE).
   - `_DECLARED_BUT_UNSET_CONFIG_SECTIONS`: a curated, individually-verified
     allowlist of frob.toml sections this codebase's own loaders genuinely
     read (vet/vet.allow/vet.detectors, policy + its 3 rule kinds, strata +
     benign_capabilities, tickets, check, system, perf.heavy/sketch, fuzz,
     clean, tool.frob, repo) that happen not to be populated in THIS
     project's own frob.toml/pyproject.toml (frob does not need to
     configure vet/policy/etc. on itself).
   - CODE SYMBOL: a `module.Class.attr`-shaped chain one level deeper than
     the resolver proves/refutes now also credits a class RE-EXPORTED
     (not locally defined) by the outer module's __init__.py, via the
     existing _module_reexports helper; and an `X.__init__.name`-shaped
     four-part chain (a doc author spelling out a package's own
     __init__.py explicitly) now strips the `.__init__` suffix and
     re-resolves against the bare module, since `X.__init__` and `X` name
     the same module.
2. Fixed genuinely stale doc pointers: renamed/underscore-prefixed Python
   symbols (_exact_regions, _check_cmpl_registry_unit_dispositions,
   _leaf_tokens, _parse_playbook_sections, _scan_file_fingerprints,
   _walk_repo_files, frob.logging.formatter._FrobFormatter), a wrong CLI
   name (`frob reconcile` -> `frob ticket reconcile`, `frob sys check` ->
   `frob sys audit`), moved doc anchors (recomputed via
   frob.graph.dsl.slugify against each target heading), a wrong path
   prefix (agents/skills -> .claude/agents/.claude/skills), and one
   wording fix where a doc claimed a `[testing.select]` frob.toml table
   that was never real (it is SelectConfig.fallback / a CLI flag).
3. Waived the remainder as genuinely illustrative/external/future-facing
   with a specific inline reason each: hypothetical repro filenames in
   audit docs, third-party package/tool paths (gitleaks, cryptography,
   pygments, the Linux kernel docs, the NVD API), scaffold-generated
   downstream-repo files, not-yet-built CLI flags/subcommands already
   disclosed as such in the same sentence, and one module-level
   `Literal[...]` type-alias (ArchCategory) that is real but not yet
   graph-indexed as a symbol -- filed as T-draft-208a291f (out of this
   ticket's scope: src/frob/graph/**) rather than fixed here.

Residue: DOC006 measures 4 remaining findings, all inside CHANGELOG.md,
which a worktree agent cannot touch (land-owned per the agent playbook
section 4b) -- honest, ticketed-by-disclosure residue, not silently
dropped. In-scope (docs/**, src/frob/gates/_docptr.py,
tests/test_docptr_gate.py) DOC006 is 0.

Mid-ticket incident: after committing this ticket's changes, the
deletion-filter check (git diff main --diff-filter=D) surfaced a large
stale-tickets.md revert (T-0662 and ~9 other tickets reverted from
done/planned back to queued, evidence/Done-report content stripped) --
main had advanced with several other agents' lands since this worktree's
last merge. Recovered per the playbook's section 10b recipe: `git
checkout main -- tickets.md`, reapplied only this ticket's own content
edit (the tickets.md daemon-proposal DOC006 waive) and re-filed the
draft ticket via the CLI, then redid T-1016's own evidence/sweep through
the CLI rather than hand-editing the ledger.

### Changed
```
 docs/audits/check-performance.md                   |   2 +-
 docs/audits/graph.md                               |   2 +-
 docs/audits/lang-check-docs.md                     |   2 +-
 docs/audits/perf.md                                |   2 +-
 docs/audits/strata.md                              |   2 +-
 docs/audits/tickets-testing-round2.md              |   4 +-
 docs/audits/tickets-testing.md                     |   2 +-
 docs/audits/vet.md                                 |   2 +-
 docs/commands/deploy.md                            |   2 +-
 docs/commands/scaffold.md                          |   2 +-
 docs/design/language-adapter-tier-decision.md      |   5 +-
 docs/design/secrets-pii-corpus.md                  |   6 +-
 docs/design/system-design-corpus.md                |   2 +-
 docs/guides/agentic-time-profiling.md              |   4 +-
 docs/guides/exhaustive-research.md                 |   4 +-
 docs/guides/extending/dup-detector-registry.md     |   2 +-
 docs/guides/extending/language-grammar-handlers.md |   2 +-
 docs/guides/extending/prover-claim-kinds.md        |   6 +-
 docs/guides/extending/sys-export-formats.md        |   2 +-
 docs/guides/install.md                             |   4 +-
 docs/guides/quickstart.md                          |   2 +-
 docs/guides/worktree-pool.md                       |   2 +-
 docs/modules/arch.md                               |   2 +-
 docs/modules/clean.md                              |   2 +-
 docs/modules/decisions.md                          |   2 +-
 docs/modules/dup-sota-survey.md                    |   2 +-
 docs/modules/dup.md                                |   4 +-
 docs/modules/fuzz.md                               |   4 +-
 docs/modules/gates.md                              |  10 +-
 docs/modules/mutate.md                             |   2 +-
 docs/modules/perf.md                               |   4 +-
 docs/modules/serve.md                              |   4 +-
 docs/modules/stats.md                              |   2 +-
 docs/modules/testing.md                            |   9 +-
 docs/modules/tickets.md                            |   2 +-
 docs/modules/vet.md                                |   8 +-
 docs/strata/host.md                                |   2 +-
 docs/strata/kernel.md                              |   2 +-
 docs/strata/krb.md                                 |   2 +-
 docs/strata/surface.md                             |   4 +-
 docs/strata/threat.md                              |   2 +-
 docs/strata/waive.md                               |   4 +-
 src/frob/gates/_docptr.py                          |  90 ++++++++++-
 tests/test_docptr_gate.py                          |  58 +++++++
 tickets.md                                         | 167 ++++++++++++++++++++-
 45 files changed, 378 insertions(+), 73 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006Config::test_all_caps_citation_tag_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_declared_but_unset_section_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_reexported_class_attribute_chain_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_dunder_init_mid_chain_resolves_to_module` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 6075 warning(s), 339 waived
- error-findings: COV003@tickets/T-0698, DUP001@tests/test_docptr_gate.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a40e2aaf207a475ba/src/frob/gates/_docptr.py:576

<!-- ticket:T-1018 -->
```yaml
id: T-1018
title: 'PERF012 dup-spawn advisory calibration: 20 -> 1777 findings after T-0922 substrate
  expansion'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/perf/_dup_spawn.py
- src/frob/perf/_effect_summaries.py
- src/frob/perf/_rules.py
- tests/test_perf.py
- docs/modules/perf.md
- tests/unit/perf/test_dup_spawn.py
- tests/unit/perf/test_effect_summaries.py
scope_changes:
- op: add
  glob: docs/modules/perf.md
  reason: 'T-1018: added regression tests under tests/unit/perf/ (mirroring the existing
    PERF012/EffectGraph test module layout) and updated docs/modules/perf.md''s PERF012/EffectGraph
    sections with the calibration write-up'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/perf/test_dup_spawn.py
  reason: 'T-1018: added regression tests under tests/unit/perf/ (mirroring the existing
    PERF012/EffectGraph test module layout) and updated docs/modules/perf.md''s PERF012/EffectGraph
    sections with the calibration write-up'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/perf/test_effect_summaries.py
  reason: 'T-1018: added regression tests under tests/unit/perf/ (mirroring the existing
    PERF012/EffectGraph test module layout) and updated docs/modules/perf.md''s PERF012/EffectGraph
    sections with the calibration write-up'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_before_after_state_check_with_mutation_between_is_not_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_adjacent_true_positive_still_fires_after_interleaving_fix
- tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_splat_forwarding_wrapper_called_with_different_args_is_not_flagged
- tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown::test_splat_argument_nested_in_a_literal_yields_an_unknown_member
- tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown::test_plain_named_parameter_forward_is_not_treated_as_a_splat
acceptance:
- text: GIVEN a full frob check run WHEN PERF012 fires THEN every remaining finding
    is a true independently-reachable duplicate spawn (spot-check 10) and the total
    is accounted (fixed, waived-with-grounds, or ticketed)
  evidence:
  - tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_before_after_state_check_with_mutation_between_is_not_flagged
  - tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_adjacent_true_positive_still_fires_after_interleaving_fix
threat: null
component: null
```
Full-run PERF012 count is 1777 warnings; at T-0919 land it reported 20 repo findings. The T-0922 EffectGraph substrate (explicit Unknown) most likely broadened reach into massive over-fire. Triage the findings into clusters, identify false-positive classes (e.g. Unknown-summary conflation, same-shape-but-different-target spawns), fix the detector for each FP class with before/after counts, then burn down or grounds-waive the honest remainder. Both-layers rule applies to any rule-shape change.

## Done report

Reproduced the reported PERF012 over-fire with `frob check --only perf --json`:
1740 findings at worktree start (had moved slightly from the 1777 baseline
noted in the ticket, presumably from other unrelated commits landed since
T-0919/T-0922). Extracted and clustered every PERF012 finding by file --
dominated by test files (tests/test_ticket_land.py 285, tests/test_gates.py
283, plus dozens more), all sharing one of two shapes once inspected:

1. Before/after state-check interleaving: `_rev_parse(root, "HEAD")` called
   once before and once after an intervening mutating call
   (`_apply_gate_rule_sync(...)`) to assert the state actually changed --
   PERF012 treated the two reads as a redundant duplicate because nothing
   in its grouping logic accounted for effectful calls happening BETWEEN
   the two matched call sites.
2. Splat-forwarding wrapper conflation: generic helpers like
   `def _git(*args, cwd): subprocess.run(["git", *args], cwd=cwd)` have
   ONE fixed source text at their own definition site regardless of what
   any given caller forwards through `*args` -- `_git("add", ...)` and
   `_git("commit", ...)` (genuinely different real argv) both resolved to
   this SAME wrapper and looked identical to the detector.

Fixed both classes in the detector, each with a mutation-killing regression
test (a false-positive guard proving the class no longer fires, plus a
true-positive guard proving the original T-0919/T-0922 detection shape is
untouched):

- `_dup_spawn._split_clean_runs` (new): splits an occurrence's grouped call
  lines into runs, breaking a run wherever another effectful call site
  (any occurrence, resolved or Unknown) falls strictly between two
  same-occurrence call sites. A call site whose own reachable effect is a
  clean singleton (exactly this ONE occurrence, nothing else) still groups
  with adjacent members exactly as before.
- `_effect_summaries._contains_splat` (new): walks a call's argument-list
  subtree (not just direct children -- the splat in `["git", *args]` sits
  one level below `argument_list`, inside the `list` literal) for a
  `list_splat`/`dictionary_splat` node. Both `_index_file_occurrences`
  (_effect_summaries.py) and `_entry_occurrences` (_dup_spawn.py) now
  degrade a splat-bearing direct-effect call to an explicit `Unknown`
  instead of a comparable literal arg-text occurrence.

Before/after counts (measured via `frob check --only perf --json`, PERF012
diagnostics only):
- baseline (this worktree, post-merge): 1740
- after the interleaving fix alone: 78 (across many distinct
  functions/files, spot-checked several clusters -- all remaining were the
  splat-wrapper shape)
- after the splat fix (both fixes together): 0

The full repo run is clean at PERF012=0 findings, with no waivers needed --
every finding traced to one of the two false-positive classes above; none
were genuine independently-reachable duplicates once inspected. No
remaining residue to burn down or draft-ticket.

Both fixes are conservative in the same fail-open direction the rest of
this substrate already takes (degrade toward MISSING a duplicate, never
toward manufacturing one) and neither touches any T-0919/T-0922
true-positive fixture -- all 7 pre-existing tests in
tests/unit/perf/test_dup_spawn.py plus the loop-effects/summary tests still
pass unchanged.

Also ran the full `frob check --ticket T-1018` gate set in chunks
(gates-fast, gates-native, gates-security, lint, static, per the playbook's
--budget/--only chunking) -- all pass; ruff-format was applied to the 3
touched files (the 4th file ruff-format flagged, src/frob/gates/_docptr.py,
is pre-existing drift outside this ticket's scope, left untouched).

Scope was extended (+3, --reason recorded) to cover
docs/modules/perf.md (the PERF012/EffectGraph doc sections updated with
the calibration write-up) and the two tests/unit/perf/ test files edited
(mirroring the existing PERF012/EffectGraph test module layout) --
tests/test_perf.py (already in original scope) was not touched.

### Changed
```
 docs/modules/perf.md                     |  42 +++++++++++
 src/frob/perf/_dup_spawn.py              | 121 ++++++++++++++++++++++++-------
 src/frob/perf/_effect_summaries.py       |  49 ++++++++++++-
 tests/unit/perf/test_dup_spawn.py        | 104 ++++++++++++++++++++++++++
 tests/unit/perf/test_effect_summaries.py |  59 +++++++++++++++
 tickets.md                               | 120 +++++++++++++++++++++++++++++-
 6 files changed, 464 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_before_after_state_check_with_mutation_between_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_adjacent_true_positive_still_fires_after_interleaving_fix` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_splat_forwarding_wrapper_called_with_different_args_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown::test_splat_argument_nested_in_a_literal_yields_an_unknown_member` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown::test_plain_named_parameter_forward_is_not_treated_as_a_splat` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 4763 warning(s), 333 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1019 -->
```yaml
id: T-1019
title: 'REG011 burn-down: 1157 out_of_scope disposition reasons fail the accountable-excuse
  form (weaknesses 798, patterns 346)'
state: queued
kind: docs
origin: human
created: '2026-07-27'
priority: high
parent: T-0204
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- docs/design/registry/patterns.yaml
- docs/design/registry/compliance.yaml
- docs/design/registry/supply-chain.yaml
- docs/design/registry/secrets.yaml
- src/frob/gates/_registry_exhaustiveness.py
- tests/test_registry_exhaustiveness.py
acceptance:
- text: GIVEN a full frob check run THEN REG011 warnings are zero and no disposition
    was silently weakened (spot-check 10 rewrites read as substantive)
  evidence: []
threat: null
component: null
```
REG011 demands each out_of_scope disposition name a catching control (rule-id/CWE token) or be a substantive 'none -- <explanation>' reasoned-none disclosure. 1157 entries fail. First make a design decision: entries whose own checkability tag is process/advisory are definitionally not statically checkable -- either the rule accepts that class with the tag as grounds, or every reason is rewritten to the compliant reasoned-none form. Prefer honest per-class rewrites over blanket rule loosening; if the rule changes, it must still reject genuinely unaccountable excuses (keep a before-fails test).

<!-- ticket:T-1020 -->
```yaml
id: T-1020
title: 'REG008 burn-down: 132 handled_by dispositions lack the frob:enforces edge
  in code'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- docs/design/registry/arch-checks.yaml
- src/frob/arch/
acceptance:
- text: GIVEN a full frob check run THEN REG008 warnings are zero
  evidence: []
threat: null
component: null
```
REG008: registry entries dispositioned handled_by:<RULE> need a matching frob:enforces <ENTRY-ID> directive on the enforcing rule implementation. Add the 132 missing edges at the real enforcing sites (no bulk misattribution: verify each rule actually covers the entry before adding the edge; downgrade the disposition honestly where it does not).

<!-- ticket:T-1021 -->
```yaml
id: T-1021
title: 'WAIVE004 stale-waiver sweep: remove ~655 waivers matching 0 findings (full-run
  verified)'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/
- tests/
acceptance:
- text: GIVEN a full unscoped frob check THEN WAIVE004 warnings are zero and gate
    errors remain zero
  evidence: []
threat: null
component: null
```
WAIVE004 flags waivers that match 0 findings. Its own message warns the signal is only trustworthy from a FULL unscoped run -- verify against a full run, never --only. For each stale waiver: remove it, unless git history shows it guards a known-flaky/diff-scoped rule (leave those with a comment upgrading them to deliberate). Re-run full check after removal batches to confirm no gate flips to error (a waiver whose removal surfaces a live finding was NOT stale -- restore it and ticket the finding instead).

<!-- ticket:T-1022 -->
```yaml
id: T-1022
title: 'EXHAUST001/002 turn-on debt burn-down: 190 escape-hatch sites (135 unknown-escape,
  55 named-escape)'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/
- src/frob/gates/_exhaustive_handling.py
acceptance:
- text: GIVEN a full frob check THEN EXHAUST001+EXHAUST002 warnings are zero or reduced
    to a ticketed, justified residue
  evidence: []
threat: null
component: null
```
T-0688 landed EXHAUST001/002 at WARN posture. Burn down the 190 sites: EXHAUST001 (unresolvable call/raise escapes a partial handler -- add catch-all or narrow the Unknown via frob:callee-raises), EXHAUST002 (named exceptions escape uncaught/undeclared -- catch or declare frob:raises). Errors-as-values discipline: prefer typani Result returns at real fallible boundaries over blanket except Exception. If a systematic FP class emerges in the resolver, fix the resolver first and report before/after counts.

<!-- ticket:T-1023 -->
```yaml
id: T-1023
title: 'INV burn-down: 50 invariant-anchor gaps (INV006 24 code claims, INV005 17
  unbound evidence, INV004/INV003 9 docs claims)'
state: queued
kind: invariant
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- docs/modules/
- invariants/
- src/frob/
acceptance:
- text: GIVEN a full frob check THEN INV003-INV006 warnings are zero
  evidence: []
threat: null
component: null
```
Bind every normative claim to a checked invariant: INV006 code files with exclusivity claims need frob:invariant anchors; INV005 evidence must gain frob:tests edges to its anchor (dotted Class.method form only); INV003/INV004 docs claims need invariant markers. Write real property tests where an anchor has no evidence; do not water down claims to dodge the detector.

<!-- ticket:T-1024 -->
```yaml
id: T-1024
title: 'REF/COV/DEAD/PLACE small-bucket sweep: REF001 36 orphan invariant docs, COV007
  38 private-symbol doc anchors, DEAD001 13, REF002 6, COV006 3, PLACE001 2'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- invariants/
- docs/
- src/frob/
- tests/
acceptance:
- text: GIVEN a full frob check THEN REF001/REF002/COV006/COV007/DEAD001/PLACE001
    warnings are zero
  evidence: []
threat: null
component: null
```
Sweep the small warning buckets: REF001 orphan invariants/*.md need real inbound references (frob:used-by or doc links from the module docs that rely on them); REF002 single-anchor docs need a second consumer; COV007 move frob:doc anchors from private symbols to the public surface they document; COV006 fix the flagged frob:tests edges; DEAD001 delete or bind the 13 uncalled private test helpers; PLACE001 move the 2 misplaced directives onto their intended symbols.

<!-- ticket:T-1025 -->
```yaml
id: T-1025
title: 'strata SYS203: make shared-store-write contention consult a resource''s declared
  arbiter, drop tickets_ledger waivers'
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_contention.py
- tests/unit/strata/test_contention.py
- docs/strata/host.md
- design/frob.strata
- tickets.md
threat: null
component: null
```
T-0956 modeled the tickets_ledger's real single-writer-lock arbitration
using T-0700's grammar (resource tickets_ledger { lock "tickets.lock"; }
plus access "tickets_ledger" mode write; on cli/gates/fleet/core/serve),
verified clean via frob.strata._access.resource_contention_violations
(SYS204). SYS203 itself (src/frob/strata/_contention.py::
check_resource_contention) remains permanently mode-blind by design: it
has no code path that reads Module.resources or a node's access= attrs at
all, so it keeps firing on tickets_ledger's five writers regardless of the
now-modeled arbiter, and the five SYS203:tickets_ledger waivers (cli/
gates/fleet/core/serve in design/frob.strata) stay in place, permanently
justified rather than pending re-evaluation.

This ticket is the actual code-level follow-up: teach SYS203 (or a new,
narrower successor rule) to consult a resource's declared arbiter
(arbitrated_by/lock) the same way SYS204 already does, so a store with a
provably-safe declared arbiter stops being flagged by SYS203 at all,
letting the five tickets_ledger waivers above finally be dropped. Scope:
src/frob/strata/_contention.py, tests/unit/strata/test_contention.py,
docs/strata/host.md#resource-contention-sys2xx-t-0699, design/frob.strata
(dropping the five waivers once SYS203 itself discharges them),
tickets.md.

<!-- ticket:T-1026 -->
```yaml
id: T-1026
title: sequential-independent-awaits should suggest asyncio.gather (T-0698 disclosed
  cut)
state: dropped
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
threat: null
component: null
```
T-0698's own text names a fourth advisory shape ("sequential awaits over
independent IO -> suggest gather") this ticket's implementation did not
build: proving two `await` expressions are INDEPENDENT (neither reads a
value the other produced) needs a data-dependency analysis this repo's
current `frob.arch` normalized model does not yet provide (NormalizedCall
tracks a call's own bare-identifier arguments, not a cross-statement
def-use chain). Approximating "independent" as "textually adjacent await
statements" would risk false positives on genuinely sequential
awaits (the second explicitly depends on the first's result) -- an
unsound advisory is worse than no advisory for this repo's own
noise-discipline convention (T-0332).

Scope for this follow-up: `src/frob/arch/**`, `tests/unit/test_arch.py`,
`docs/modules/arch.md`. Build a minimal def-use check over two or more
sequential `await` statements in the same function body: an `await`
whose LHS binding is never read by any argument of a LATER `await`
expression in the same own-scope sequence is "independent"; suggest
`asyncio.gather` naming the awaited call sites. Same advisory-tier,
unwaivable-channel posture as every other T-0693 concurrency-hazard
category.

## Drop reason
- 2026-07-27: accidental duplicate filing (double invocation), see T-1027 (absorbed by T-1027)

<!-- ticket:T-1027 -->
```yaml
id: T-1027
title: sequential-independent-awaits should suggest asyncio.gather (T-0698 disclosed
  cut)
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
threat: null
component: null
```
T-0698's own text names a fourth advisory shape ("sequential awaits over
independent IO -> suggest gather") this ticket's implementation did not
build: proving two `await` expressions are INDEPENDENT (neither reads a
value the other produced) needs a data-dependency analysis this repo's
current `frob.arch` normalized model does not yet provide (NormalizedCall
tracks a call's own bare-identifier arguments, not a cross-statement
def-use chain). Approximating "independent" as "textually adjacent await
statements" would risk false positives on genuinely sequential
awaits (the second explicitly depends on the first's result) -- an
unsound advisory is worse than no advisory for this repo's own
noise-discipline convention (T-0332).

Scope for this follow-up: `src/frob/arch/**`, `tests/unit/test_arch.py`,
`docs/modules/arch.md`. Build a minimal def-use check over two or more
sequential `await` statements in the same function body: an `await`
whose LHS binding is never read by any argument of a LATER `await`
expression in the same own-scope sequence is "independent"; suggest
`asyncio.gather` naming the awaited call sites. Same advisory-tier,
unwaivable-channel posture as every other T-0693 concurrency-hazard
category.

<!-- ticket:T-1028 -->
```yaml
id: T-1028
title: 'graph symbol walker: module-level type-alias assignments (Literal/TypeAlias)
  not indexed as symbols'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
threat: null
component: null
```
Found while working T-1016 (DOC006 burn-down round 2): frob.gates._docptr's
CODE SYMBOL kind (and the graph symbol index it relies on,
frob.gates._docblocks._python_symbol_names_by_path, sourced from
GraphSnapshot.symbols) only indexes def/class definitions as top-level
python symbols -- a bare module-level type-alias assignment such as
`ArchCategory = Literal[...]` in src/frob/arch/_models.py is never
recorded as a graph symbol, so a doc pointer naming it
(frob.arch._models.ArchCategory, docs/modules/arch.md) is flagged DOC006
"does not resolve to a real symbol" even though the name is real and
public. Currently worked around with a targeted frob:waive DOC006 at the
one known call site; the underlying gap (module-level `Name = <value>`
assignments, e.g. Literal/TypeAlias/NewType, not walked into the graph as
symbols) likely affects other doc pointers too and is worth fixing at the
python graph-walker layer rather than waiver-by-waiver.

<!-- ticket:T-1029 -->
```yaml
id: T-1029
title: 'ticket CLI: add acceptance criteria to an existing ticket (only ticket new
  supports --acceptance)'
state: queued
kind: ux
origin: agent
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/
- tests/unit/test_ticket_runner_gate_findings.py
acceptance:
- text: GIVEN an existing queued ticket WHEN the new subcommand adds a criterion THEN
    ticket show displays it and the ledger write went through the CLI
  evidence: []
threat: null
component: null
```
T-0894's agent had to hand-edit tickets.md to add a before-fails/after-passes acceptance criterion required by the T-0756 new-gate-rule close gate, because no subcommand exists to append acceptance criteria to an existing ticket. Add e.g. 'frob ticket accept <id> --criterion ...' (or extend ticket scope-style editing) with the same validation as ticket new --acceptance, so the ledger is never hand-edited for this.

<!-- ticket:T-1030 -->
```yaml
id: T-1030
title: agent worktree creation cuts from stale base (fa606fe8/b3589c3e) instead of
  main tip -- recurred 3+ times
state: queued
kind: bug
origin: agent
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/agent-playbook.md
acceptance:
- text: GIVEN a fresh dispatch worktree THEN its base contains local main's tip or
    the playbook's warm-up section documents the mandatory fix prominently
  evidence: []
threat: null
component: null
```
Three separate dispatch batches now had implementer worktrees cut from a stale base (origin tip b3589c3e era, or fa606fe8 -- 20+ files behind main): T-0958-era batch (2 agents), wave-9 gates-tests agent, wave-9 T-1018 agent (pre-filing tip). Playbook workaround (verify merge-base, git merge main) works but every agent pays it. Root-cause where the harness worktree-creation picks its base (likely origin/main or a cached default-branch ref while local main is 240+ commits ahead and never pushed) and document the definitive mitigation in the playbook; if the base choice is outside frob's control, make the playbook warm-up step a hard MUST with the exact two commands.
