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
tier: epic
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
tier: epic
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

<!-- ticket:T-0380 -->
```yaml
id: T-0380
title: 'vet: extend binding-aware resolution into CVE fingerprint scanning'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0377
- T-0378
- T-0379
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
- docs/modules/vet.md
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: 'playbook mandate: update docs/modules/vet.md in the same change as src/frob/vet/_capability.py''s
    new public-api entries (T-0380 fingerprint binding resolution)'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_vet.py::TestFingerprintBindingResolution::test_python_aliased_pickle_loads_still_matches
- tests/test_vet.py::TestFingerprintBindingResolution::test_python_unaliased_control_still_matches_lexically
- tests/test_vet.py::TestFingerprintBindingResolution::test_typescript_aliased_require_still_matches
- tests/test_vet.py::TestFingerprintBindingResolution::test_typescript_clean_source_does_not_match
- tests/test_vet.py::TestFingerprintBindingResolution::test_rust_aliased_use_still_matches
- tests/test_vet.py::TestFingerprintBindingResolution::test_rust_clean_source_does_not_match
- tests/test_vet.py::TestFingerprintBindingResolution::test_c_aliased_macro_still_matches
- tests/test_vet.py::TestFingerprintBindingResolution::test_c_clean_source_does_not_match
threat: null
component: null
```
_scan_file_fingerprints (CVE matching) is lexical needle-matching for EVERY language including Python -- a renamed import defeats a fingerprint even where capability scanning is binding-aware. Reuse the binding tables built for capability resolution (Python + the new TS/Rust/C-C++ tables) to resolve aliases before fingerprint matching for all languages. Acceptance: an aliased import that would evade a lexical fingerprint match is still caught; adversarial test per language.

## Done report

Extended `_scan_file_fingerprints` (VET006/CVE fingerprint scanning) to
reuse the SAME binding tables capability resolution already built for
python (T-0328), typescript (T-0377), rust (T-0378), and c-cpp (T-0379):
new `_resolved_candidates_for_language` dispatches to whichever
`_python_resolved_candidates`/`_ts_resolved_candidates`/
`_rust_resolved_candidates`/`_c_resolved_candidates` table applies, and
`_binding_fingerprints` mirrors `_python_binding_operations`'s exact
shape against `CVE_FINGERPRINTS` instead of `DANGEROUS_OPERATIONS`.
`_scan_file_fingerprints` now unions the pre-existing lexical result with
`_binding_fingerprints`'s resolver-backed result (deduped by fingerprint
`id`) -- an aliased import that evades the lexical needle scan is still
caught.

Adversarial test per language (acceptance criterion):
- Python: real catalog entry `FP-DESERIALIZE-PICKLE-001` -- `import
  pickle as p; p.loads(...)` (no literal `pickle.loads(` text) still
  matches; unaliased control still matches too.
- TypeScript, Rust, C: no existing `CVE_FINGERPRINTS` entry happens to be
  shaped as a `module.member(`/`Module::method(` dotted call today (the
  real catalog's TS/Rust needles are argument-inclusive or bare-method
  shaped, not aliasable), so these three use a synthetic, test-local
  `CveFingerprint` (via `mock.patch("frob.strata.CVE_FINGERPRINTS", ...)`)
  to prove `_binding_fingerprints`' resolver path itself: TS `const ax =
  require('axios'); ax.get(url)`, Rust `use std::process::Command as C;
  C::new("sh")`, C `#define SYS system; SYS(cmd)` -- none contain the
  literal needle text, all still match through the resolved binding
  table; a clean-source negative accompanies each.

Scope note: `docs/modules/vet.md` was outside T-0380's declared scope
(`src/frob/vet/_capability.py`, `tests/test_vet*.py`); extended via `frob
ticket scope T-0380 --add docs/modules/vet.md` per the playbook's doc-
update mandate, same pattern used for T-1088 earlier in this series.

Changed:
- src/frob/vet/_capability.py::_resolved_candidates_for_language (new)
- src/frob/vet/_capability.py::_binding_fingerprints (new)
- src/frob/vet/_capability.py::_scan_file_fingerprints (unions lexical + binding)
- docs/modules/vet.md (public API section)
- tests/test_vet.py (TestFingerprintBindingResolution, 8 tests)

Evidence: 8 node ids bound via `frob ticket evidence T-0380`. Full
`tests/test_vet.py` (430 tests) passes clean:
`uv run pytest tests/test_vet.py -p no:cacheprovider -q`.

Gates: `uv run frob check --ticket T-0380 --only gates-fast/gates-native`
both clean of NEW errors -- gates-fast shows one pre-existing COV001
finding on `src/frob/gates/_tracked_files.py` (landed by T-1082/its
follow-up repair commit before this ticket started work, confirmed via
`git log -- src/frob/gates/_tracked_files.py`), unrelated to this
ticket's scope.

Filed: none.

### Changed
```
 docs/modules/vet.md         |  11 ++-
 src/frob/vet/_capability.py |  79 ++++++++++++++++++++-
 tests/test_vet.py           | 162 ++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                  |  71 ++++++++++---------
 4 files changed, 289 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestFingerprintBindingResolution::test_python_aliased_pickle_loads_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_python_unaliased_control_still_matches_lexically` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_typescript_aliased_require_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_typescript_clean_source_does_not_match` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_rust_aliased_use_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_rust_clean_source_does_not_match` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_c_aliased_macro_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_c_clean_source_does_not_match` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 7 error(s), 793 warning(s), 426 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:295

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
- T-1072
- T-1076
- T-1074
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
After T-0373 re-thresholds frob-arch large-file to 800 lines / 60 (function), address the residue that still exceeds 800 lines among the 34 large-file advisories: real module splits, or accepted-with-reason for files that don't decompose cleanly. Acceptance: frob check arch large-file advisories at the calibrated threshold reduced to zero unresolved.

## Failure log
- 2026-07-28 attempt 1: 31 in-scope large-file findings after T-0373 calibration (43 total minus 12 strata/vet sibling-owned), up to 12047 lines (gates/__init__.py); large-file is unwaivable per docs/modules/gates.md, real splits needed -- too large for one pass, decomposition tickets filed

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

<!-- ticket:T-0668 -->
```yaml
id: T-0668
title: 'strata: exact interface-conformance check - declared node interface == real
  public code surface'
state: done
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
evidence:
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection
acceptance:
- text: Given a node declaring fewer public symbols than the bound module exports,
    when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- text: Given a node declaring a symbol the bound module does not export, when checked,
    then the obligation fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires
threat: null
component: null
```
A node's declared interface must equal the bound module's real public surface (no under- or over-declaration) -- closes acceptance-criterion (2). Depends on coverage-totality's binding pass existing first (need a bound node before its interface can be checked).

## Done report

Changed:
- src/frob/strata/_selfconform.py::SYS_INTERFACE_CONFORMANCE
- src/frob/strata/_selfconform.py::_interface_conformance_violations
- src/frob/strata/_selfconform.py::_module_public_symbols
- src/frob/strata/_selfconform.py::_module_all_literal
- src/frob/strata/_selfconform.py::_public_names_of_statement
- src/frob/strata/_selfconform.py::_node_real_public_surface
- src/frob/strata/_selfconform.py::_node_attr_values
- src/frob/strata/_selfconform.py::check_self_conformance (wired SYS104 into _collect_sys_violations/_apply_sys_waivers)
- src/frob/strata/__init__.py (re-export SYS_INTERFACE_CONFORMANCE)
- docs/modules/strata.md (SYS104 section)
- tests/unit/strata/test_selfconform.py (TestInterfaceConformance, 5 tests)

SYS104 implements exact interface conformance: a node's declared
`interface=<symbol>` attrs (new opaque `Node.attrs` convention, same
shape as `code=`/`managed`, no `.strata` grammar change) must equal the
real public surface of its `code=`-bound `.py` files (`__all__` if
present, else non-underscore top-level def/class/assignment names).
Fires in both directions: real-but-undeclared, and declared-but-absent.

SCOPE CUT (disclosed): SYS104 only evaluates a node that has already
declared at least one `interface=` attr -- making it mandatory repo-wide
would require adding `interface=` declarations to `design/frob.strata`,
which is outside this ticket's declared scope (`src/frob/strata/**`,
`src/frob/graph/**`, `docs/modules/strata.md`, `tests/unit/strata/**` --
not `design/frob.strata`). This mirrors the T-0667/SYS103 precedent
(`_coverage_totality_scan_prefix`'s own disclosed scope cut). Filed
T-1109 to promote SYS104 to mandatory once `design/frob.strata` can be
edited to carry real `interface=` declarations.

Also landed in this same worktree pass (implementation only lives in
this one file/module, shared by T-0668/T-0669/T-0670): SYS105 (purpose
contract) and SYS106 (binding totality) are ALSO present in this diff
since all three share one `_selfconform.py` module and one
`check_self_conformance` wiring pass -- their own Done reports
(T-0669/T-0670) cite the same file but their OWN new symbols/tests as
Changed, per the series' plan of building all three checks in one pass
before landing each ticket in order. T-0668's evidence below binds only
to the SYS104-specific tests.

Evidence:
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection

Filed: T-1109 (promote SYS104 to mandatory once design/frob.strata is in scope; follow-up to add CHK-GATE-SYS104 registry cross-reference in docs/design/registry/check-coverage.yaml, mirroring SYS103's own deferred registry gap)

Gates: `uv run frob check --ticket T-0668` clean across prework/lint/
static/gates-native/gates-security/test/coverage/doc*/tickets/registry
(measured directly, chunked per playbook section 3b -- 0 errors in every
group; TestRealGateGreen and TestCoverageTotality::
test_repo_unrestricted_scan_is_clean both still pass zero violations
against the real repo).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 1318 warning(s), 429 waived
- error-findings: PRE001@tickets/T-0668

<!-- ticket:T-0669 -->
```yaml
id: T-0669
title: 'strata: PURPOSE contract - node purpose carries an allowed-effect profile
  checked against code'
state: done
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
evidence:
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_outside_profile_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_unrecognized_profile_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_inside_profile_is_silent
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_node_with_no_purpose_attr_is_never_checked
acceptance:
- text: Given a node whose purpose declares a read-only effect profile but whose bound
    code performs a write, when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires
threat: null
component: null
```
Each node's declared purpose must carry an allowed-effect profile (e.g. 'read-only query' cannot emit writes); real observed effects outside that profile fail via _effects.py::check_capability_conformance -- closes acceptance-criterion (3).

## Done report

Changed:
- src/frob/strata/_selfconform.py::SYS_PURPOSE_CONTRACT
- src/frob/strata/_selfconform.py::_purpose_contract_violations
- src/frob/strata/_selfconform.py::_PURPOSE_PROFILES
- src/frob/strata/_selfconform.py::check_self_conformance (wired SYS105 into _collect_sys_violations/_apply_sys_waivers)
- src/frob/strata/__init__.py (re-export SYS_PURPOSE_CONTRACT)
- docs/modules/strata.md (SYS105 section)
- tests/unit/strata/test_selfconform.py (TestPurposeContract, 6 tests including one added this ticket matching the acceptance criterion's exact wording)

Note on landing order: this module (`_selfconform.py`) implements SYS104/
SYS105/SYS106 together (T-0668/T-0669/T-0670 share one file and one
`check_self_conformance` wiring pass, built in one editing pass before
landing each ticket in series order per this wave's dispatch plan). The
SYS105 code itself was committed as part of T-0668's land (both live in
the same file, T-0668 landed first in series order) -- this ticket's own
diff on top of that is the ONE new test
(`test_read_only_purpose_with_write_effect_fires`, matching the
acceptance criterion's literal wording: `purpose=read-only` + an
observed `fs.write` effect) plus this evidence binding and Done report.

SYS105 implements the purpose contract: a node's declared `purpose=`
attr (new opaque `Node.attrs` convention, same shape as `code=`/
`interface=`, no `.strata` grammar change) names a fixed, closed
allowed-effect profile (`_PURPOSE_PROFILES`: `pure`, `read-only`,
`logging`, `network`, `full`); any observed effect outside the declared
profile fires, and an unrecognized profile name is itself a finding
(never silently treated as permissive).

SCOPE CUT (disclosed, same shape as T-0668's): SYS105 only evaluates a
node that has already declared a `purpose=` attr -- mandating every node
declare one requires editing `design/frob.strata`, outside this ticket's
declared scope. Filed as part of T-1109 (same follow-up ticket T-0668
filed, which bundles both SYS104 and SYS105's identical scope-cut
follow-up).

Evidence:
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_outside_profile_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_unrecognized_profile_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_inside_profile_is_silent
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_node_with_no_purpose_attr_is_never_checked

Filed: none new (T-1109, filed by T-0668, already covers this ticket's
scope-cut follow-up)

Gates: `uv run frob check --ticket T-0669` clean across prework/static/
gates-native/gates-security/test/coverage/doc*/tickets (chunked per
playbook 3b; the 2 gate:TICK TICK006 errors seen in the `tickets` group
are pre-existing repo-wide debt (T-1077/T-1084 phantom draft
references), confirmed present identically on a bare unscoped `frob
check --only tickets` against `main` before this ticket's work,
unrelated to this change). `ruff-format` warns on
`src/frob/gates/__init__.py`/`tests/test_app_daemon_proxy.py`
(pre-existing bare-ruff-vs-uv-run-ruff drift, playbook section 12, out
of this ticket's scope, not touched).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_outside_profile_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestPurposeContract::test_unrecognized_profile_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_inside_profile_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestPurposeContract::test_node_with_no_purpose_attr_is_never_checked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 1309 warning(s), 428 waived
- error-findings: INV006@src/frob/gates/_todo_fmt.py, PRE001@tickets/T-0669, TICK006@tickets.md

<!-- ticket:T-0670 -->
```yaml
id: T-0670
title: 'strata: binding-totality + effect-conformance - reject logic laundered into
  an unbound file'
state: done
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
evidence:
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106
acceptance:
- text: Given dangerous logic moved into a helper module not directly bound to any
    node but reachable from a bound node, when checked, then the effect is still attributed
    and conformance-checked, not silently dropped
  evidence:
  - tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
threat: null
component: null
```
Extend SYS100/SYS101/SYS102 so the bound-set is provably total against the capability graph: a module reachable via import/call from a bound node but itself unbound must not silently escape effect-conformance checking -- closes acceptance-criterion (4) 'binding need not be total, so logic can be laundered into an unbound file'.

## Done report

Changed:
- src/frob/strata/_selfconform.py::SYS_BINDING_TOTALITY
- src/frob/strata/_selfconform.py::_binding_totality_violations
- src/frob/strata/_selfconform.py::_reachable_local_files
- src/frob/strata/_selfconform.py::_python_imports_with_lines_module
- src/frob/strata/_selfconform.py::check_self_conformance (wired SYS106 into _collect_sys_violations/_apply_sys_waivers)
- src/frob/strata/__init__.py (re-export SYS_BINDING_TOTALITY)
- docs/modules/strata.md (SYS106 section)
- tests/unit/strata/test_selfconform.py (TestBindingTotality, 3 tests)

Same landing-order note as T-0668/T-0669: this module's SYS106 code was
committed as part of T-0668's land (all three checks share one file,
built together, landed in series order) -- this ticket's own remaining
work is evidence binding + Done report.

SYS106 implements binding totality / anti-laundering: starting from every
bound node's own `.py` files, it follows resolved local python imports
(cycle-safe BFS, `frob.lang.resolve_local_import`) to build the full
reachable-file closure, then fires once per reachable `FOREIGN` file
`scan_file_capabilities` observes a capability in -- "dangerous logic
moved into a helper module not directly bound to any node but reachable
from a bound node" (T-0670's acceptance criterion, verbatim), regardless
of SYS103's own scan-prefix restriction (prefix-independent by
construction, since the reachability edge itself is the join, not a
directory prefix).

Evidence:
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires (the acceptance criterion's own scenario: a bound node imports an unbound helper that performs a network effect)
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106

Filed: none new (this check has no `design/frob.strata` opt-in scope cut
-- unlike SYS104/SYS105, it always runs once any node is bound at all,
so there is no analogous "make it mandatory" follow-up; T-1109 already
covers the CHK-GATE-SYS104/105/106 registry cross-reference for all
three).

Gates: `uv run frob check --ticket T-0670` clean across prework/static/
gates-native/gates-security/test/coverage/tickets (chunked per playbook
3b). `lint` shows 5 pre-existing E501 errors in
`src/frob/vet/_supplychain.py` (outside this ticket's declared scope,
landed by a concurrent wave/ticket, confirmed unrelated to this diff --
not touched). `tickets` group's 2 gate:TICK TICK006 errors are the same
pre-existing T-1077/T-1084 phantom-draft debt noted in T-0669's Done
report, confirmed present on a bare unscoped `frob check --only tickets`
against `main` independent of this work.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 1312 warning(s), 427 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:295, INV006@src/frob/gates/_todo_fmt.py, INV006@src/frob/gates/_waive_comments.py, TICK006@tickets.md

<!-- ticket:T-0671 -->
```yaml
id: T-0671
title: 'strata: bounded/staleness-gated assume+waiver mechanism - un-droppable floor
  view for conformance obligations'
state: done
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
evidence:
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_unexpired_waiver_still_visible_in_floor_view
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_missing_expiry_marker_treated_as_expired
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_parses_embedded_expiry_date
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_no_marker_returns_none
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_malformed_date_returns_none
acceptance:
- text: Given a waiver older than its staleness bound, when checked, then it is treated
    as expired and the underlying obligation re-fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged
- text: Given any active waiver, when frob check runs, then it appears in the floor
    view and cannot be hidden from default output
  evidence:
  - tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_unexpired_waiver_still_visible_in_floor_view
threat: null
component: null
```
Closes acceptance-criterion (5): every conformance escape hatch (interface/purpose/binding waivers) must be bounded (expiry/staleness-gated) and surfaced in an un-droppable floor view so it cannot become a permanent silent exemption. Depends on the three conformance checks existing first since this wraps their waiver channel.

## Done report

Changed:
- src/frob/strata/_waive.py::CONFORMANCE_WAIVER_EXPIRED_RULE
- src/frob/strata/_waive.py::parse_waiver_expiry
- src/frob/strata/_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES (SYS104/SYS105 added)
- src/frob/strata/_selfconform.py::_apply_conformance_waiver_staleness
- src/frob/strata/_selfconform.py::_CONFORMANCE_WAIVER_RULES
- src/frob/strata/_selfconform.py::check_self_conformance (wired the staleness gate in)
- src/frob/strata/__init__.py (re-export CONFORMANCE_WAIVER_EXPIRED_RULE, parse_waiver_expiry)
- docs/modules/strata.md (Bounded escape hatches section)
- tests/unit/strata/test_selfconform.py (TestConformanceWaiverStaleness, 3 tests)
- tests/unit/strata/test_waive.py (TestConformanceWaiverExpiry, 3 tests)

T-0671 closes T-0341's fifth acceptance criterion for the three
conformance checks T-0668/T-0669/T-0670 built (SYS104/SYS105/SYS106):

1. Staleness dating (`expires:YYYY-MM-DD` embedded in the mandatory
   `reason` string -- the `.strata` grammar has no expiry field, and
   adding one is a grammar change outside this ticket's scope;
   `parse_waiver_expiry` is the in-scope substitute, mirroring
   `_split_waiver_rule`'s existing "encode structure into the reason
   string" convention for sub-targets). A conformance waiver with NO
   `expires:` marker, or one whose date has passed, is EXPIRED:
   `_apply_conformance_waiver_staleness` moves its finding back into
   `violations` (re-fires the underlying obligation, acceptance [0])
   and adds a new SYSWAIVE003 finding naming the expired waiver.
2. Floor view (acceptance [1]): `report.waived` already carries every
   currently-active conformance waiver, and `sys_runner.py` already
   prints it unconditionally on every run (confirmed by reading
   `_log_sys_waived_findings`'s call sites -- never behind a flag) --
   this criterion was already structurally satisfied by the existing
   "waived, never silently dropped" mechanism every SYS family uses;
   this ticket adds `test_unexpired_waiver_still_visible_in_floor_view`
   as the first direct regression test proving it for the new
   conformance families specifically.

SYS104/SYS105 also join `MULTI_INSTANCE_WAIVER_FAMILIES` (they can each
fire more than once per node, once per symbol/effect-kind, exactly like
SYS100/SYS101 already do) -- a bare `waive "SYS104"`/`waive "SYS105"` is
now an elaborate-time `MalformedWaiver` error; a waiver must name
`RULE:SUBTARGET` (e.g. `SYS105:net.connect`). SYS106 is deliberately
excluded (fires once per unbound file, like SYS103, not once per node).

Evidence:
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged (acceptance [0])
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_unexpired_waiver_still_visible_in_floor_view (acceptance [1])
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_missing_expiry_marker_treated_as_expired
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_parses_embedded_expiry_date
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_no_marker_returns_none
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_malformed_date_returns_none

Filed: none new.

Gates: `uv run frob check --ticket T-0671` clean across prework/static/
gates-native/gates-security/test/coverage/tickets (chunked per playbook
3b, after merging main mid-ticket to pick up a concurrent wave's
TICK006 phantom-draft fix -- confirmed via `git log -1 main` before and
after). `lint` shows pre-existing ruff-check/format debt in
`src/frob/vet/_supplychain.py`, `src/frob/gates/__init__.py`, `src/frob/
gates/_cve_fingerprint_scan.py`, `src/frob/gates/_waive.py`, `tests/
test_app_daemon_proxy.py`, `tests/test_vet.py` (all outside this
ticket's declared scope, confirmed present on bare `main` root
independent of this work, landed by a concurrent wave). `coverage`
shows one pre-existing COV001 error (`src/frob/gates/_tracked_files.py::
tracked_files`), also confirmed present on bare `main` root, unrelated.

### Changed
```
 tickets.md | 63 +++++++++++++++++++++++++++++++-------------------------------
 1 file changed, 32 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_unexpired_waiver_still_visible_in_floor_view` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_missing_expiry_marker_treated_as_expired` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_parses_embedded_expiry_date` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_no_marker_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_malformed_date_returns_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 8 error(s), 1050 warning(s), 426 waived
- error-findings: AFFECT001@src/frob/strata/_selfconform.py, AFFECT001@src/frob/strata/_waive.py, COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:295

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

<!-- ticket:T-1027 -->
```yaml
id: T-1027
title: sequential-independent-awaits should suggest asyncio.gather (T-0698 disclosed
  cut)
state: done
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
evidence:
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_fires_on_unrelated_calls
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_does_not_fire_when_second_reads_first
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_does_not_fire_on_single_await
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

## Done report

Built the minimal def-use check the ticket asks for:
`frob.arch._async_hazards._check_sequential_independent_awaits`, a fifth
detector in this module, new `ArchCategory` value
`sequential-independent-awaits` (`_models.py`).

Shape: within each own-scope `block` node (a branch already puts its body
in a separate `block`, so branching between awaits correctly takes them
out of the same sequence), scan direct statement children for either a
bare `await CALL(...)` expression statement or `NAME = await CALL(...)`
(a non-identifier assignment target -- tuple/attribute/subscript -- or a
`return`/`yield` of an await is left alone, matching this module's
existing "only what's clearly one shape" precedent). Two awaits are
independent when the earlier one's bound name does not appear as an
identifier anywhere inside the later one's `call` node (callee text AND
every argument -- deliberately broader than "argument" alone, so a bound
value read as a call's receiver, e.g. `a.close()`, still counts as a real
dependency, erring toward the sound side per T-0332's "unsound is worse
than no advisory" framing). A single-pass scan over each block's ordered
await sequence groups them into maximal contiguous runs of mutually
independent awaits; a run of 2+ fires ONE `suggestion`-severity finding
naming every awaited call site and recommending `asyncio.gather`.

Verified against a hand-written litmus before wiring into the test suite:
3 independent sequential awaits fire once (all three callees named); a
second await reading the first's bound name does not fire; a lone await
does not fire (script output confirmed via a scratch run, not just read).

Checked the SELFAUDIT001 dispatch note directly: no new I/O-name
classifier table was added (`_call_identifier_names` walks generic
`identifier` nodes, not a curated subprocess/socket/requests string
table), so no `src/frob/vet/_capability.py::_SELF_PATTERN_SUFFIXES` entry
is needed -- confirmed by running the invariant gate (see below), which
only flagged this module for an unrelated INV006 hit from the new
docstring prose ("arguments-only"), fixed by rewording to drop the
`\bonly\b` match rather than waiving (the INV006 message's own suggested
first option).

Docs: added the category to `docs/modules/arch.md`'s async-event-loop-
hazards section (heading + bullet), matching the existing per-category
format and disclosed model limits.

Gates (manual `--only` loop, `--ticket T-1027`): gates-fast/gates-native/
invariant/prework/coverage/doclink/docanchor/scope all clean after the
INV006 reword + a fresh `frob ticket sweep T-1027` (PRE001 went stale
once the doc/detail wording changed after `ticket start`). `gate:TICK`
shows 2 pre-existing TICK006 phantom-filing warnings (T-1077, T-1084) --
both already present on `main` before this ticket touched anything (T-1084
is my own earlier ticket's Done report citing its pre-renumber draft id,
the same disclosed historical-draft-citation pattern already established
elsewhere in this ledger; T-1077 is unrelated to this ticket's scope).
Neither is fixed here (out of `src/frob/arch/**`/`tests/unit/test_arch.py`/
`docs/modules/arch.md` scope).

Tests: `tests/unit/test_arch.py` full file, 278 collected / all green (no
F/E marks in output; measured via `pytest tests/unit/test_arch.py -q`,
both before wiring in the docs change and again after the final merge).

### Changed
```
 tickets.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_fires_on_unrelated_calls` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_does_not_fire_when_second_reads_first` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_does_not_fire_on_single_await` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 589 warning(s), 425 waived
- error-findings: INV006@src/frob/gates/_todo_fmt.py, TICK006@tickets.md

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

<!-- ticket:T-1031 -->
```yaml
id: T-1031
title: 'frob natives build: estate rollout of the Makefile core one-line shim across
  sibling repos'
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
threat: null
component: null
```
T-0735's user directive named "estate rollout via fleet at close" as part of
the natives-build epic: every sibling repo's Makefile core target should be
converted to the one-line `uv run frob natives build` shim (T-0864's landed
subcommand) via `frob scaffold apply` (T-0865's landed scaffold template +
drift check), removing any lingering per-repo CARGO_TARGET_DIR/maturin-develop
cache logic at the wrong layer (the exact T-0732 drift class this epic exists
to retire).

This repo itself is already compliant (Makefile `core:` is the one-line shim,
verified at T-0735's close: `uv run frob natives build` runs successfully
using the git-common-dir-keyed shared CARGO_TARGET_DIR).

Fleet-level rollout across the other frob-enabled repos is out of THIS repo's
own scope -- draft follow-up for whichever fleet-facing ticket/process
actually walks the sibling-repo list and runs `frob scaffold apply` +
`frob doctor` per repo, plus a short docs note pointing at T-0864/T-0865/
T-0735 as the design precedent for anyone doing that rollout by hand in the
meantime.

<!-- ticket:T-1033 -->
```yaml
id: T-1033
title: 'python graph walker: widen bare type-alias RHS detection beyond Literal[...]
  (Union/Optional/TypeVar)'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/test_lang.py
scope_changes:
- op: add
  glob: tests/test_lang.py
  reason: T-1033 adds/widens tests in tests/test_lang.py::TestParsePython for the
    widened bare-alias RHS shapes
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_lang.py::TestParsePython::test_bare_widened_alias_rhs_extracted_as_type_symbol
- tests/test_lang.py::TestParsePython::test_bare_unrelated_call_still_unindexed
threat: null
component: null
```
T-1028 fixed the python symbol walker (src/frob/lang/_walk_python.py) to index type-alias assignments as SymbolKind.TYPE symbols for three shapes: type X = ... (py>=3.12), X: TypeAlias = ..., and bare X = Literal[...] (this repo's own idiom). The bare-RHS detection deliberately stayed narrow to Literal[...] only -- widening _is_literal_alias_rhs's sibling check to also recognize bare X = Union[...], X = Optional[...], and X = TypeVar(...) assignments (common PEP 613-adjacent alias idioms not covered by an explicit TypeAlias annotation) is a separate, deliberate follow-up, not bundled into T-1028's fix.

## Done report

Widened `frob.lang._walk_python`'s bare module-level type-alias RHS
detection (T-1028's `Literal[...]`-only case) to a curated four-shape
table, matching T-1028's own follow-up note. Renamed
`_is_literal_alias_rhs` -> `_is_bare_alias_rhs` (call site updated in
`_type_alias_symbol`) and split it into two branches:

- subscript RHS (`_BARE_ALIAS_SUBSCRIPT_NAMES = {Literal, Union, Optional}`)
- call RHS (`_BARE_ALIAS_CALL_NAMES = {TypeVar}` -- `TypeVar(...)` is a
  CALL node, not a subscript, so it needed its own branch, not just a
  bigger subscript table)

Both branches share `_bare_alias_head_name`/`_matches_curated_name` for
the "bare or `typing.`-qualified" match rule `_is_type_alias_annotation`
already established for `TypeAlias`, so that rule now lives in exactly
one place instead of being reimplemented per shape.

Verified against a hand-written litmus before wiring into the test suite
(`Union[...]`, `Optional[...]`, `typing.Optional[...]`, `TypeVar(...)` all
recognized as `SymbolKind.TYPE`; an unrelated bare call stays unindexed) --
script output confirmed, not just read.

Newly-surfaced COV001-adjacent debt fixed in the same land (per the
dispatch note): the four new/changed private symbols
(`_BARE_ALIAS_CALL_NAMES`, `_bare_alias_head_name`, `_matches_curated_name`,
`_type_alias_symbol`) needed their own `frob:ticket T-1033` edges since
T-1028 (the prior edge) is already closed -- COV002 (frob:ticket to an
open ticket) caught this; fixed by adding the directive, not by waiving.

Two new DUP001 findings surfaced from the first draft of the test suite
(three near-identical `test_bare_{union,optional,typevar}_..." tests, 95%
similar to each other and to the existing `Literal`/annotated tests) --
fixed by actually removing the duplication (one
`test_bare_widened_alias_rhs_extracted_as_type_symbol` parametrized over
the three RHS shapes), not by waiving; confirmed DUP001 clean afterward.

`tests/test_lang.py` needed a scope-add (SCOPE001) since the widened test
class lives there -- added with a reason.

Gates (manual `--only` loop, `--ticket T-1033`, gates-fast/gates-native/
lint/static all run): 0 new errors. Remaining errors are all pre-existing
and outside `src/frob/lang/**`: `src/frob/gates/_todo_fmt.py` INV006 and
`src/frob/vet/_supplychain.py` ruff E501 (both from other agents' recent
lands, confirmed via `git log -- <path>` before this ticket touched
anything), plus two pre-existing TICK006 phantom-filing entries (T-1077,
T-1084) already present before this ticket started.

Tests: `tests/test_lang.py` full file green (measured, no F/E marks);
individually re-ran the 4 new/changed test-suite entries
(`test_bare_widened_alias_rhs_extracted_as_type_symbol` x3 parametrized
cases plus `test_bare_unrelated_call_still_unindexed`) -- all pass.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestParsePython::test_bare_widened_alias_rhs_extracted_as_type_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestParsePython::test_bare_unrelated_call_still_unindexed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 8 error(s), 632 warning(s), 427 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:295, INV006@src/frob/gates/_todo_fmt.py, INV006@src/frob/gates/_waive_comments.py, TICK006@tickets.md

<!-- ticket:T-1035 -->
```yaml
id: T-1035
title: 'frob-dup: nested-closure fragments cannot be individually waived (symref/binding
  mismatch)'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_legacy.py
- src/frob/dup/_legacy_py.py
- src/frob/graph/dsl.py
- docs/modules/dup.md
threat: null
component: null
```
Found while working T-0862 (tests/**-only frob-dup group triage).

4 of the 154 unaccounted tests/**-only groups measured for T-0862 share a
single root cause that cannot be fixed from tests/** alone: a symref
mismatch between how `frob.dup._legacy` names a NESTED (closure) function
fragment and how `frob.graph.dsl` binds a preceding `frob:waive` comment.

`frob.dup._legacy._enclosing_class_py` (src/frob/dup/_legacy.py via
src/frob/dup/_legacy_py.py:198) walks ALL the way up a function's ancestor
chain looking for the nearest enclosing CLASS, ignoring any enclosing
FUNCTION in between. So a helper closure defined inside a test method
(e.g. `def _run_new():` nested inside
`TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive`)
gets a dup fragment symbol of `TestArchiveRaceWithConcurrentNew._run_new`
-- qualified by the enclosing CLASS only, never the enclosing METHOD.

Meanwhile `frob.graph.dsl`'s directive-to-symbol binding (used to resolve
a `frob:waive DUP001 reason="..."` comment placed directly above a `def`)
only tracks top-level defs and class methods as declared symbols -- it has
no concept of a nested closure as an independently addressable symbol. A
comment placed directly above a nested `def` binds instead to the nearest
OUTER tracked symbol (the enclosing test method), not the nested function.

Net effect: `_dup_group_covering_waivers`'s full-coverage rule
(docs/modules/dup.md#T-0375) requires every fragment's symref -- as
`frob.dup` computes it -- to be covered by a matching `frob:waive` edge --
as `frob.graph.dsl` binds it. For a nested-closure fragment these two
symbol spaces disagree, so no comment placement can ever satisfy coverage
for that fragment. Confirmed by direct probe (calling
`frob.check._python._waive_edges_for_rule` and `frob.dup.find_duplicates`
against this repo): a `frob:waive DUP001` comment placed immediately above
`tests/test_tickets_ledger_concurrency.py`'s nested `_run_new` binds to
`TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive`
(the outer test method), never to
`TestArchiveRaceWithConcurrentNew._run_new` (the fragment `frob.dup`
actually reports) -- so the waiver is silently ineffective no matter where
the comment is placed.

A second, related symptom: two SAME-NAMED nested closures in different
test methods of the same class collapse to the SAME symref (class-only
qualification loses the enclosing-method disambiguation), e.g.
`tests/test_ticket_runner_pytest_env.py`'s two `fake_guarded_subprocess_run`
closures in `TestRunPytestDirectlyStripsLeaseEnv` both report as
`TestRunPytestDirectlyStripsLeaseEnv.fake_guarded_subprocess_run` --
genuinely ambiguous fragment identity, independent of the waiver-binding
gap above.

The 4 residual groups from T-0862 (unfixable from tests/** alone):
- tests/test_tickets_ledger_concurrency.py:98,156 (nested `_run_new`
  in two different test methods of two different classes)
- tests/test_testing.py:1239,2124 (nested `fake_run_argv`)
- tests/test_gitio.py:29 + 8 sibling files, incl.
  tests/test_evidence_integrity.py's nested `git` (the pre-existing
  waiver there already has this exact problem -- it predates T-0862)
- tests/test_ticket_runner_pytest_env.py:40,71 (symref collision, not
  just a binding gap)

Fix direction (not evaluated in depth, needs design):
(a) `frob.dup._legacy`'s Python function-symbol resolution: qualify a
    nested closure's symbol by its full enclosing chain (or at minimum
    the nearest enclosing FUNCTION, not just the nearest enclosing CLASS)
    so two same-named closures in sibling methods no longer collide.
(b) `frob.graph.dsl`'s comment-to-symbol binding: either extend it to
    recognize nested function defs as independently waivable symbols
    (binding a directly-preceding comment to the nested def rather than
    falling through to the outer tracked symbol), or teach
    `_dup_group_covering_waivers` to accept a waiver bound to a fragment's
    nearest OUTER tracked symbol as sufficient coverage for a nested
    fragment (weaker, but matches what a human intuitively expects when
    they place the comment directly above the nested closure).

Scope for whoever picks this up: src/frob/dup/_legacy.py,
src/frob/dup/_legacy_py.py, src/frob/graph/dsl.py, plus
docs/modules/dup.md's T-0375 full-coverage writeup once resolved. The 4
groups above (and the pre-existing evidence_integrity.py waiver, which
should be re-verified once the binding is fixed) are this ticket's
regression fixtures.

<!-- ticket:T-1037 -->
```yaml
id: T-1037
title: 'REG011 quality-bar drift: 798 out_of_scope reasons in weaknesses.yaml fail
  T-0680''s substantive-disclosure check'
state: dropped
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
- src/frob/gates/_registry_exhaustiveness.py
threat: null
component: null
```
Found while closing epic T-0346: `tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations` fails on current main -- `registry_gate` reports 798 REG011 (WARN severity, T-0680: registry-YAML `out_of_scope:<reason>` quality check requiring a substantive reasoned-none disclosure, not a bare excuse) violations against `docs/design/registry/weaknesses.yaml` alone, out of 1157 total registry violations repo-wide.

Root cause: REG011 was added by T-0680, which landed after T-0384's reconciliation test was written and pinned "zero violations" against `weaknesses.yaml`. T-0384 never anticipated this new WARN-level quality bar. `weaknesses.yaml`'s `out_of_scope:` dispositions (presumably many of its CWE `out-of-scope-naming-the-missing-concept` entries, per T-0346's own acceptance criterion [1] wording) apparently do not meet REG011's substantive-reason bar.

This is a real, live gate warning (not an error) affecting a file this session did not touch. Two possible fixes, for the reviewer to choose: (1) improve the ~798 flagged `out_of_scope` reason strings in weaknesses.yaml to satisfy REG011's substantive-disclosure bar (real remediation, likely large), or (2) if the reasons are already substantive and REG011's heuristic is simply too strict for this file's phrasing convention, adjust REG011 or file targeted waivers. Scope: docs/design/registry/weaknesses.yaml, tests/test_registry_reconciliation_weaknesses.py, possibly src/frob/gates/_registry_exhaustiveness.py (REG011 itself) depending on the reviewer's chosen direction.

## Failure log
- 2026-07-28 attempt 1: already fixed by T-1019 before this wave (REG011 0 violations, ticket's own named regression test passes on current main); unrelated pre-existing test_every_deferred_entry_targets_an_open_ticket failure found and filed separately as T-1116

## Drop reason
- 2026-07-28: already fixed by T-1019 before this wave started -- REG011 measures 0 violations repo-wide and the ticket's own named regression test (test_no_weaknesses_violations) passes on current main; unrelated pre-existing failure found while verifying and filed separately as T-1116

<!-- ticket:T-1038 -->
```yaml
id: T-1038
title: promote OPAQUE001 to ERROR-tier once frob's own 93-site first-turn-on set is
  fixed-or-waived
state: queued
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_opaque.py
- src/frob/vet/**
- src/frob/app/config.py
- src/frob/deploy/**
- src/frob/dup/**
- src/frob/fuzz/**
- src/frob/graph/**
- tests/**
threat: null
component: null
```
T-0665 landed OPAQUE001 (frob.gates._opaque.opaque_gate) at WARN-tier
per the T-0688/T-0973 first-turn-on promotion precedent: a first
measurement against frob's own tracked codebase found 93 real sites
after string-literal/comment false-positive filtering (147 before),
concentrated in test fixtures using dynamic getattr/setattr for
monkeypatch-style assertions, plus a handful of production sites
(src/frob/app/config.py, src/frob/deploy/_conform.py,
src/frob/dup/_pipeline.py, src/frob/fuzz/_signatures.py,
src/frob/graph/lock.py, src/frob/vet/_capability.py itself). This is
above the >25-site WARN-first threshold, so promoting straight to
ERROR was not safe to do in the same ticket.

Scope: audit each of the ~93 sites and either (a) rewrite to a static
name where the dynamic lookup was incidental, or (b) add an honest
`frob:waive OPAQUE001 reason="..."` naming why the site is a legitimate
runtime-resolved indirection (most test-fixture sites will fall here --
mock/monkeypatch dynamic attribute access is often intentional test
infrastructure, not an evasion risk). Once the WARN count reaches zero
real (unwaived) findings, promote opaque_gate's Severity from WARN to
ERROR in src/frob/gates/_opaque.py.

<!-- ticket:T-1049 -->
```yaml
id: T-1049
title: 'refactor: decompose oversized _build_jobs gate-job registry (ARCH001)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
evidence:
- tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
threat: null
component: null
```
frob check --ticket T-0602 flags ARCH001 on src/frob/gates/__init__.py::_build_jobs
(201 lines, threshold 60). This is PRE-EXISTING: main already has this function
at 196 lines (verified via git show main:src/frob/gates/__init__.py) -- it is
one large dict-literal gate-job registry (thread_jobs + process_jobs mapping),
not something T-0602 introduced. T-0602 only added ~8 net lines (a `use_cache`
param and one call to a newly extracted `_substitute_cacheable_jobs` helper),
which was enough to lose ARCH001's grandfather exemption for a function this
ticket's diff merely touches rather than substantially grows.

Decompose _build_jobs's thread_jobs/process_jobs dict-literal assembly into
smaller per-concern builder functions (e.g. one for the always-run set, one
for the ticket-scoped set, one for the process-pool set) so the function
itself drops under the ARCH001 threshold. Out of T-0602's scope
(src/frob/gates/**, src/frob/serve/**, tests/test_gate_cache.py,
docs/modules/{serve,gates}.md) -- this refactor would touch the entire
existing gate-job assembly, not the T-0602 feature itself.

## Done report

Decomposed _build_jobs (201 lines, ARCH001 threshold 60) into three
functions: _build_jobs itself now only does selection/force-drift/
cache-substitution/return (~49 lines), and two new extracted builders
carry the actual dict-literal assembly this ticket's plan named:
_build_thread_jobs(st) (the thread-pool half -- drift, coverage,
invariant, test, policy, doclink, docanchor, docblocks, fuzz, release,
decisions, tickets, compliance, debt, deprecated, excludehazard, refs,
parse_failures, registry, lang_conformance, lang_project_conformance,
fmt, affect_drift) and _build_process_jobs(st) (the process-pool half --
perf, clones, sys, secrets, taint, opaque, archgate, exhaustive_handling,
ffi_boundary, pii_structural, walk_lint, cve_fingerprint_scan,
render_lint, dead_symbols, protocol_summary).

Both new functions take the same `st: _GateInputs` this ticket's plan
suggested (one builder per concern -- always-run set / process-pool set
-- rather than three-way, since the thread-pool dict genuinely is one
concern: cheap, I/O-bound gate closures over the same state; the
ticket-scoped set is already its own function, _build_ticket_scoped_jobs,
unaffected by this change).

No public API changed: `_build_jobs`'s signature and return shape are
identical; `_build_thread_jobs`/`_build_process_jobs` are private,
internal-only helpers with no external caller (verified via grep -- only
`_build_jobs` itself calls them).

git diff main --diff-filter=D --stat: empty (no unintended deletions).
Full tests/test_gates.py: 508 passed (FROB_WORKTREE/FROB_AGENT unset per
playbook 5b, same env-leak caveat as T-1077's Done report).
frob check --ticket T-1049 --only arch: 0 errors, ARCH001 no longer
fires on _build_jobs (grep-confirmed absent from output); 18 pre-existing
warnings + 232 suggestions, none new.
frob check --ticket T-1049 --only drift/--only test: 0 errors both runs;
pre-existing DRIFT001/TEST003 waived entries unrelated to this change.

### Changed
```
 src/frob/gates/__init__.py | 76 +++++++++++++++++++++++++++++-----------------
 tickets.md                 | 52 ++++++++++++++++++++++++++++++-
 2 files changed, 99 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1050 -->
```yaml
id: T-1050
title: 'vet/opaque: generalized container-subscript-call detector + rust/cpp/kotlin
  points-to alias tracking (T-1047 residual)'
state: queued
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/gates/_opaque.py
- tests/test_vet.py
threat: null
component: null
```
T-1047 closed 17 of the ~25 taxonomy runtime-opaque gaps T-0666 found (15
new RUNTIME_OPAQUE_CONSTRUCTS needle-based detector entries across
python/typescript/c-cpp/rust/kotlin, plus 2 new rust OPAQUE_SOURCE_INVISIBLE
excuse entries for the extern-FFI-symbol and proc-macro-expansion rows).
The remaining gaps genuinely need MORE than a fixed-substring needle match
-- a generic "container subscript followed by a call" shape
(`handlers[key](x)`, `cp[key](x)`), or a real cast-expression / points-to
analysis (C integer-to-function-pointer cast, C void*-backcast,
C/C++ array-index-into-function-pointer-table with a runtime index) --
which `_opaque_indirection_findings`'s current architecture (a byte-level
needle scan with an optional single-literal-argument check, T-0665) cannot
express without either a full expression grammar or an unacceptable false
positive rate on ordinary bracket/call syntax. Extending that architecture
is real design work, not a registry-entry addition, so it is scoped
separately here rather than forced into T-1047's needle-table shape.

Remaining runtime-opaque taxonomy rows still with NO detector/excuse
(litmus fixtures already lock the current honest non-firing behavior in
tests/test_vet.py::TestOpaqueIndirectionGate, `_not_addressed` suffix):
- python: container-dynamic-key (`handlers[key](x)`)
- typescript: computed-member-non-constant-key (`cp[key](x)`),
  container-dynamic-key (`handlers[key](x)`)
- c: array-nonconstant-index, integer-cast-to-function-pointer,
  void-star-backcast
- cpp: array-runtime-index

Also carried forward from T-0666/T-1047, structural resolver gaps in the
ORDINARY (non-opaque-gate) resolver, `frob.vet._capability.scan_file_
capabilities` and friends -- litmus fixtures already lock these too:
- rust: struct-field points-to (struct-update field rebinding never
  resolves through a later call) --
  `test_struct_update_field_rebind_not_detected`
- rust: `macro_rules!` expansion (no macro-expansion-aware resolution
  exists for rust at all) --
  `test_macro_rules_expansion_emitting_fixed_call_not_detected`
- cpp: pointer-to-member alias tracking (`&Ops::run` / `.*`/`->*`
  dereference has no alias tracking) --
  `test_member_function_pointer_bound_to_named_member_not_detected`
- kotlin: destructuring-declaration alias tracking --
  `test_destructuring_declaration_not_detected`
- kotlin: default-parameter-forwarding alias tracking --
  `test_default_parameter_forwarding_callable_not_detected`
- kotlin: operator `fun invoke` / receiver-instance points-to --
  `test_operator_fun_invoke_making_object_directly_callable_not_detected`

Each needs either: (a) a generalized "subscript-then-call" detector shape
added to `_opaque_indirection_findings` (a new construct kind beyond the
current needle+literal-arg-index model), or (b) real points-to/alias
tracking added to the per-language ordinary resolvers (mirrors C's
existing `_record_c_field_alias` for the rust/cpp/kotlin cases). Until
closed, T-0339's acceptance criterion [1] ("given any RUNTIME-resolved
indirection... FAILS CLOSED") does not fully hold -- these 7 opaque-gate
rows and 6 structural-resolver rows are the reason T-0339 was NOT closed
alongside T-1047.

<!-- ticket:T-1059 -->
```yaml
id: T-1059
title: 'detector: frob ticket start warns when worktree is N+ commits behind main
  tip'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_leases.py
- docs/modules/tickets.md
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: wiring warn_if_worktree_stale needs a test file and doc anchor outside src/frob/tickets/**
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: wiring warn_if_worktree_stale needs a test file and doc anchor outside src/frob/tickets/**
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_warns_when_behind_threshold
- tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_silent_when_within_threshold
- tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_silent_on_non_git_root
- tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_respects_configured_threshold
- tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_returns_default_when_frob_toml_absent
- tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_reads_configured_value
- tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_non_positive_value_falls_back_to_default
- tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_malformed_toml_falls_back_to_default
threat: null
component: null
```
T-1030 investigated why dispatched agent worktrees were repeatedly cut from
a stale base (fa606fe8/b3589c3e). Root cause: the EnterWorktree harness
tool's default worktree.baseRef=fresh branches new worktrees from
origin/<default-branch>, and this clone's origin/main has not been kept in
sync with local main (observed 81 commits behind at investigation time).
This is harness-side behavior, outside frob's codebase, and cannot be
fixed by editing frob source.

Add a frob-side detector: frob ticket start (and/or frob check) warns
loudly when the worktree's merge-base with local main is more than N
commits behind main's current tip, pointing at the playbook's warm-up
section (docs/guides/agent-playbook.md#1-worktree-warm-up). This does not
prevent the stale cut but catches it immediately at the start of a
ticket instead of silently carrying it through a whole session.

## Done report

Added a stale-worktree detector (T-1030's root cause) wired into the existing
`commit_start_transition` call every `frob ticket start` already makes:
`warn_if_worktree_stale(root, ticket_id, main_ref="main")` in
src/frob/tickets/_leases.py measures how many commits `main`'s tip is ahead of
`git merge-base HEAD main` and logs a loud warning (naming the ticket id, the
commit count, and the playbook's warm-up anchor) once that count reaches the
configurable `[tickets] stale_worktree_warn_commits` threshold (frob.toml,
default 20). Best-effort/non-fatal throughout -- any git failure degrades to a
silent no-op, matching this module's other optional-signal helpers.

Extracted a shared `load_positive_int_config(root, key, default)` helper in
_leases.py (DUP001: my new stale-commits reader was 95% similar to the
existing `_load_large_glob_max_files` in tickets/__init__.py) and refactored
both to delegate to it.

Verified via a real multi-commit git-worktree fixture
(tests/test_ticket_leases.py::TestWarnIfWorktreeStale, 4 tests: warns past
threshold, silent within threshold, silent on a non-git root, respects a
configured threshold) plus TestLoadPositiveIntConfig (4 tests) for the shared
reader. docs/modules/tickets.md gained a "Stale-worktree-cut warning (T-1059)"
section.

`frob check --ticket T-1059` is clean except two pre-existing, unrelated
findings verified via `git diff main -- <file>` to be empty (not touched by
this ticket): an INV006 finding in src/frob/gates/_todo_fmt.py, and two
TICK006 phantom-draft findings from T-1077/T-1084's historical Done reports.
Also confirmed one pre-existing ruff-format finding in src/frob/gates/
__init__.py is untouched by this diff.

### Changed
```
 docs/modules/tickets.md      |  36 +++++++++++
 src/frob/tickets/__init__.py |  24 +++-----
 src/frob/tickets/_leases.py  | 113 +++++++++++++++++++++++++++++++++-
 tests/test_ticket_leases.py  | 142 +++++++++++++++++++++++++++++++++++++++++++
 tickets.md                   |  16 ++++-
 5 files changed, 314 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_warns_when_behind_threshold` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_silent_when_within_threshold` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_silent_on_non_git_root` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_respects_configured_threshold` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_returns_default_when_frob_toml_absent` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_reads_configured_value` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_non_positive_value_falls_back_to_default` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_malformed_toml_falls_back_to_default` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 2 error(s), 941 warning(s), 425 waived
- error-findings: INV006@src/frob/gates/_todo_fmt.py, TICK006@tickets.md

<!-- ticket:T-1060 -->
```yaml
id: T-1060
title: 'SYS205 v1: alpha anti-pattern, arbitrated_by code-identity, write path-scoping'
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_mode_conformance.py
- tests/unit/strata/test_mode_conformance.py
threat: null
component: null
```
T-0701's SYS205 mode-conformance check disclosed three v0 cuts (module
docstring, src/frob/strata/_mode_conformance.py):

1. ALPHA's "upgrade-deadlock ANTI-PATTERN" (acquiring a write while
   holding a plain read lock context on the same resource) is not
   detected -- needs per-lock-variable identity across nested `with`
   blocks (which lock guards which resource), the same lock-IDENTITY
   modeling problem `frob.arch._lock_ordering`'s T-0694
   `_collect_module_locks` solves for the cyclic lock-order check.
2. ALPHA/EXCLUSIVE code-checkable arbiter support is `lock`-only --
   an `arbitrated_by NODE` arbiter has no code-level identity resolved
   in this pass (no cross-node call-graph analysis).
3. WRITE mode is unrestricted in v0 -- the mandate's "only on declared
   paths" clause needs path-level identity between a declared resource
   id and a specific file/call site, which this v0 pass does not have
   (same class of cut `_effects.py`'s own capability-conformance join
   already discloses).

Each needs real design work (lock-identity modeling, cross-node call
resolution, or a first-class capability/resource-path grammar) rather
than a quick patch -- filed as its own ticket per T-0701's Done report
rather than approximated unreliably in that pass.

<!-- ticket:T-1061 -->
```yaml
id: T-1061
title: wire SYS205 mode-conformance into CLI dispatch + waiver channel + docs
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/sys_runner.py
- src/frob/gates/**
- docs/strata/host.md
threat: null
component: null
```
T-0701 shipped `check_mode_conformance` (SYS205) as a pure, fully-tested
function in `src/frob/strata/_mode_conformance.py` -- CLI dispatch
(`frob sys audit`, `src/frob/app/sys_runner.py`) and the T-0174
`MULTI_INSTANCE_WAIVER_FAMILIES` waiver channel are both out of T-0701's
declared scope (`src/frob/strata/**`, `src/frob/vet/**`,
`tests/unit/strata/`), same disclosed-cut precedent
`_access.py`'s own SYS204 module docstring already used for T-0700. Also
wire the `docs/strata/host.md#resource-access-modes-t-0700` section (out
of scope for T-0701 too -- docs/strata/** is not in its scope globs) with
a new subsection documenting SYS205's per-mode semantics, the python-only
v0 detection scope, and the `lock`-only arbiter support.

<!-- ticket:T-1062 -->
```yaml
id: T-1062
title: EXHAUST001/002 residual burn-down continuation (post T-1056)
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
Follow-up to T-1056, which closed only the src/frob/gates/__init__.py
slice (16 of 176 sites) of the EXHAUST001/002 turn-on debt burn-down.

Remaining sites (per T-1056's `frob check --only exhaustive_handling
--json` snapshot, minus the closed gates/__init__.py slice and minus the
two sibling-owned trees T-1056 skipped for coordination):

  8 src/frob/gates/_coverage.py
  6 src/frob/dup/_pipeline.py
  6 src/frob/tickets/_leases.py
  5 src/frob/deploy/_conform.py
  5 src/frob/mutate/__init__.py
  5 src/frob/outline/__init__.py
  5 src/frob/strata/_claims.py
  5 src/frob/tickets/__init__.py
  4 src/frob/app/check_runner.py
  4 src/frob/check/_python.py
  4 src/frob/gates/_docptr.py
  4 src/frob/gates/_secrets.py
  4 src/frob/mutate/_journal.py
  4 src/frob/strata/_host_isolation.py
  4 src/frob/strata/_native_staleness.py
  4 src/frob/testing/_collect.py
  3 src/frob/doctor.py
  3 src/frob/gates/_docblocks.py
  3 src/frob/gates/_prework.py
  3 src/frob/stats/_agentic.py
  3 src/frob/xref/__init__.py
  ...remainder spread 1-2 per file across app/gates/check/strata/testing.

Excluded from this list entirely (owned by sibling tickets, do not
recount without checking their status first): src/frob/perf/** (T-1053)
and src/frob/vet/** plus src/frob/gates/_opaque.py (T-1051).

Same disposition rule as T-1056/T-1022: each site gets a truthful
frob:raises/frob:callee-raises annotation (verify against what the
callable can actually raise), a cheap errors-as-values refactor
(tool_crash_result()-style at subprocess/parse boundaries, or a fail-open
try/except matching the function's own documented degrade contract), or a
reasoned frob:waive -- never a blanket suppression. Re-run
`frob check --only exhaustive_handling --json` at the start to get a live
count before starting (T-1056's counts will have drifted).

<!-- ticket:T-1074 -->
```yaml
id: T-1074
title: 'arch: triage 800-2000 line file residue (T-0395 remainder tier 3)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
Filed from T-0395 (failed as too large for one pass). Remaining in-scope
large-file residue under 2000 lines (frob-core/src/lib.rs 2277 --
excluded, native crate, separate toolchain/ownership from the python
gates split above; list the rest as of 2026-07-28):
src/frob/tickets/_models.py (1658), src/frob/arch/_patterns.py (1486),
src/frob/app/check_runner.py (1468), src/frob/gates/_docblocks.py (1460),
src/frob/arch/_python.py (1267), src/frob/testing/_collect.py (1267),
src/frob/gates/_protocol_summary.py (1244), src/frob/tickets/_leases.py
(1191), src/frob/app/config.py (1118), src/frob/gates/_secrets.py (1108),
src/frob/graph/dsl.py (1033), src/frob/gates/_docptr.py (1000),
src/frob/gates/_registry_exhaustiveness.py (993), src/frob/check/__init__.py
(958), src/frob/check/_python.py (936), src/frob/graph/__init__.py (869),
strata-core/src/lib.rs (869, native crate -- confirm with the strata
sibling ticket owner before touching), src/frob/app/sys_runner.py (851),
src/frob/perf/_rules.py (845), src/frob/arch/_rust.py (838),
src/frob/graph/callgraph.py (830), src/frob/perf/_effect_summaries.py
(823), src/frob/gates/_refs.py (818). Triage into real splits vs.
files that genuinely do not decompose cleanly (record the specific
reason per file, per this ticket's acceptance framing) -- do not attempt
all ~20 in one diff; group by subsystem and land incrementally, full
suite verification per group.

<!-- ticket:T-1077 -->
```yaml
id: T-1077
title: 'arch: split remaining gate families out of src/frob/gates/__init__.py (T-0395/T-1072
  remainder)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
evidence:
- tests/test_gates.py::TestCoverageGate::test_todo002_unbound_directive
- tests/test_gates.py::TestCoverageGate::test_todo001_bare_comment_in_touched_file
- tests/test_gates.py::TestCoverageGate::test_todo002_edge_to_closed_ticket
- tests/test_gates.py::TestCoverageGate::test_todo003_fires_after_version_bump_since_deferral_landed
- tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_no_version_bump_since_deferral
- tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_ticket_closes
- tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged
- tests/test_gates.py::TestFmt001Gate::test_ordinary_long_comment_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_long_code_line_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_short_directive_not_flagged
threat: null
component: null
```
Filed from T-1072's partial land: T-1072 extracted only the WAIVE/PLACE001
family (`src/frob/gates/_waive.py`, 1972 lines) out of
`src/frob/gates/__init__.py`, taking it from 12047 to 10159 lines --
still far above the 800-line large-file threshold (docs/modules/gates.md),
still the repo's largest file by a wide margin. This ticket covers the
remaining gate families still resident in `__init__.py`, following the
exact same pattern (private sibling module per cohesive family,
`__init__.py` re-imports and re-exports unchanged, `frob:*` directives
travel with the moved code, DRIFT002/AFFECT001 references in
tests/docs updated to the new module path):

- COV00x (coverage_gate + _cov001.._cov007 helpers) -- large, likely its
  own tier
- TODO00x / FMT00x
- DEBT00x / DEPR00x (deprecated_gate)
- SCOPE00x / PREWORK (prework_gate)
- INV00x (invariant_gate, inv003_gate)
- TEST00x family (test_gate + _test004.._test013 helpers) -- large
- DECISIONS (decisions_gate)
- TICK00x (tickets_gate)
- COMPLIANCE00x (compliance_gate)
- SYS00x / DOC00x (sys_gate, selfaudit)
- DUP00x (dup_gate)
- REL00x (release_gate)
- FUZZ00x (fuzz_gate)
- DOCLINK/DOCANCHOR (doclink_gate, docanchor_gate)
- PERF (perf_gate)
- the `run_gates` orchestration spine (`_GateInputs`, `_build_jobs`,
  `_run_combined_jobs`, etc.) -- likely stays in `__init__.py` as the
  package's true entry point, but should be re-measured once everything
  else has moved out from under it.

Plan carefully before moving code; verify with the full gates test suite
after each chunk; land incrementally, same discipline T-1072 used.

## Done report

Extracted the TODO00x/FMT001 family out of src/frob/gates/__init__.py
into a new src/frob/gates/_todo_fmt.py, following T-1072's WAIVE-family
sibling-module precedent exactly: _todo002_edges, _pyproject_version_at,
_todo003_long_deferred, _todo003_violation_for_edge, _todo001_bare,
_todo001_bare_comment, _todo001, _fmt001_touched_lines, _fmt001_file,
_fmt001_marker_entries, _fmt001_violations_for_runs, fmt_gate, and the
_TODO_RE constant, all moved verbatim with their frob:ticket/frob:tests/
frob:enforces/frob:doc/frob:waive directives intact.

src/frob/gates/__init__.py: 10164 -> ~9802 lines (chunked -- part of the
larger T-1077 remainder, does not by itself clear the large-file
threshold; residue refiled by the coordinator as T-1115 for the rest
after the original draft died at land).
New: src/frob/gates/_todo_fmt.py: 396 lines.

Three call sites (_todo002_edges's _site_from_edge_origin/_OPEN_STATES,
_todo003_long_deferred's _current_version, _todo003_violation_for_edge's
_blame_shas/_UNCOMMITTED_SHA/_site_from_edge_origin, _todo001_bare's
_touched_files, fmt_gate's _touched_files) needed lazy (call-time)
imports back from frob.gates to avoid an init-time circular import,
mirroring T-1072's _design_dir/_site_from_edge_origin lazy-import
pattern exactly -- all of those helpers stay defined in __init__.py
since many other still-resident gate families use them too.

__init__.py re-imports and re-exports only the three names other code
actually calls (_todo001, _todo003_long_deferred, fmt_gate -- verified
via repo-wide grep, no external module imports any of the other moved
private helpers directly), so every existing call site keeps working
unchanged. Dropped now-unused imports from __init__.py's own top-level
list (marker_for, read_line_length, fold_comment_runs -- confirmed via
ruff F401 after the move that nothing else in __init__.py used them).

No frob:tests/frob:doc directive needed a path fixup (DRIFT002/AFFECT001
clean): every TODO/FMT test binding already pointed at a test file path
(tests/test_gates.py::TestCoverageGate.* / TestFmt001Gate.*), not a
src/frob/gates/__init__.py::<symbol> source symref, so the physical
move did not break any existing directive.

git diff main --diff-filter=D --stat: empty (no unintended deletions).
Full tests/test_gates.py: 508 passed (FROB_WORKTREE/FROB_AGENT unset
per playbook 5b -- with them set, 7 unrelated pre-existing tests fail on
worktree-guard/lease env leak into tmp_path repos, a known artifact, not
a regression from this change).
frob check --ticket T-1077 --only drift: gate:DRIFT 0 errors, 0 warnings,
2 waived (both pre-existing T-0453 waivers, unrelated); gate:WAIVE 0
errors, 403 warnings (all WAIVE004 "0 findings in this --only-scoped run"
noise, expected per the gate's own known-flaky note), 0 waived.
frob check --ticket T-1077 --only arch: 0 errors (18 pre-existing
warnings + 232 suggestions, none introduced by this change -- confirmed
none reference src/frob/gates/_todo_fmt.py's own new abstraction shape
beyond the pattern-recommendation noise already present repo-wide).

Filed: T-1115, a coordinator refile after the draft died at land
(remaining gate families: DEBT/DEPR, SCOPE/
PREWORK, INV00x, TEST00x, DECISIONS, TICK00x, COMPLIANCE00x, SYS00x/
DOC00x, DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates
spine, and COV00x which T-1077 also left untouched) -- this ticket's
plan named ~15 families; doing all of them in one pass risked exactly
the kind of high-blast-radius diff T-0395 originally failed on, so this
land does one cohesive family (matching T-1072's own one-family-per-
land discipline) and hands the rest forward explicitly rather than
silently declaring the whole remainder done.

### Changed
```
 src/frob/gates/__init__.py  | 364 +---------------------------------------
 src/frob/gates/_todo_fmt.py | 396 ++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                  |  90 +++++++++-
 3 files changed, 486 insertions(+), 364 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_todo002_unbound_directive` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo001_bare_comment_in_touched_file` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo002_edge_to_closed_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo003_fires_after_version_bump_since_deferral_landed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_no_version_bump_since_deferral` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_ticket_closes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_ordinary_long_comment_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_long_code_line_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_short_directive_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1081 -->
```yaml
id: T-1081
title: 'arch: ARCH102 fires on newly-split src/frob/gates/_waive.py (35 exports, 4
  clusters)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_waive.py
- src/frob/gates/__init__.py
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: cohering _waive.py into smaller sibling modules to clear ARCH102 requires
    updating __init__.py's re-export imports to the new module paths, the same mechanical
    consequence T-1072 hit when it first created _waive.py
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_ticket_attr_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_gates.py::TestActiveTicket::test_explicit_flag_wins
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
```
Post-gates-split (the recent frob.gates.__init__ -> frob.gates._waive extraction), gates-native's archgate stage reports an unwaived ARCH102 on src/frob/gates/_waive.py: 35 top-level exports split across 4 unrelated naming/usage clusters. Out of scope for T-1066/T-1068 (both explicitly excluded from touching src/frob/gates/**); needs either a genuine further split of _waive.py or a reasoned frob:waive ARCH102 the way sibling gates modules already carry (see src/frob/gates/__init__.py's own ARCH102 waiver for the pattern).

## Done report

Split src/frob/gates/_waive.py (2060 lines, unwaived ARCH102 god-module:
35 top-level exports across 4 unrelated naming/usage clusters) into
three cohesive modules, removing the T-1072 transitional ARCH102 waiver
entirely (no waiver anywhere in the module now):

- src/frob/gates/_waive.py (1374 lines): WAIVE001-005/DSL001 directive
  validation, the rule-id registry (_KNOWN_GATE_RULES/known_gate_rule_ids/
  _UNWAIVABLE_RULES), and the shared _match_waiver/_apply_waivers/
  _ceiling_ok/_severity_overrides matching spine every other gate's
  violation list is filtered through -- one cluster: validating and
  applying `frob:waive` directives.
- src/frob/gates/_waive_comments.py (new, 625 lines): WAIVE006/007 (stale/
  dangling waiver ticket refs, both the frob:waive comment channel and the
  .strata waive clause channel) and PLACE001 (misplaced frob: directive) --
  one cluster: is a directive COMMENT sitting somewhere sound.
- src/frob/gates/_waive_lease.py (new, 103 lines): active_ticket/
  ticket_lease_pin -- the --ticket resolution and cross-worktree
  lease-pin helpers that rode along in T-1072's original extraction but
  have nothing to do with waiver matching at all.

Every frob:ticket/frob:tests/frob:enforces/frob:doc directive moved
verbatim with its function. _waive_comments.py imports _waive_edges back
from _waive.py (a real, non-circular dependency -- _waive.py never
imports _waive_comments); _site_from_edge_origin/_design_dir stay
lazily imported from frob.gates at call time inside the moved functions,
same posture T-1072 established.

src/frob/gates/__init__.py's single `from frob.gates._waive import (...)`
block split into three import statements (from _waive, _waive_comments,
_waive_lease respectively) -- every re-exported name unchanged, verified
via `import frob.gates` succeeding and the full gates test suite passing.

DRIFT002 path fixups (4 stale directives found via repo-wide grep,
mechanical module-path-only edits, no semantic change):
tests/test_gates.py::TestActiveTicket.test_explicit_flag_wins
(frob:tests _waive.py -> _waive_lease.py), and 3 docs/modules/gates.md
frob:describes anchors (_place001_missed_symbol, _place001_bindings ->
_waive_comments.py; active_ticket -> _waive_lease.py).

Post-merge follow-on fix (found while merging main forward mid-ticket,
fixed in this land per playbook guidance rather than deferred): main
landed T-0668 (SYS104/105/106, src/frob/strata/_selfconform.py) after
this ticket's own _waive.py split diverged, and _KNOWN_GATE_RULES (which
lives in this ticket's own scope file) was missing all three ids --
TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known failed
post-merge. Added SYS104/105/106 to the literal, same "generated_gate_
rule_ids reports it, paste it in" discipline the literal's own T-0966
comment documents.

git diff main --diff-filter=D --stat: empty (no unintended deletions).
tests/test_gates.py + test_secrets_gate.py + test_waive_gate.py: 559
passed.
frob check --ticket T-1081 --only arch: 0 errors; grep-confirmed
_waive.py no longer appears in ANY god-module finding (ARCH102 cleared);
_waive_comments.py/_waive_lease.py trip no new god-module/large-file
finding of their own. 17 pre-existing warnings + 231 suggestions, none
new to this change (spot-checked: no _waive_comments.py/_waive_lease.py
entries).
frob check --ticket T-1081 --only drift/--only test: 0 errors both runs.

### Changed
```
 docs/modules/gates.md             |   6 +-
 src/frob/gates/__init__.py        |   9 +-
 src/frob/gates/_waive.py          | 726 +-------------------------------------
 src/frob/gates/_waive_comments.py | 627 ++++++++++++++++++++++++++++++++
 src/frob/gates/_waive_lease.py    | 103 ++++++
 tests/test_gates.py               |   2 +-
 tickets.md                        |  17 +-
 7 files changed, 771 insertions(+), 719 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_ticket_attr_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestActiveTicket::test_explicit_flag_wins` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1082 -->
```yaml
id: T-1082
title: 'arch: abstraction-opportunity gates package extraction (T-0393/T-1067 remainder,
  29 findings)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/
evidence:
- tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_spawn_error_yields_no_tracked_files
- tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_nonzero_exit_yields_no_tracked_files
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set
threat: null
component: null
```
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). Of the
84 abstraction-opportunity findings remaining after T-1067 extracted the
gitio/testing._runners `_excerpt` duplicate and the vet package's
`_cache_get`/`_cache_set` TTL-cache duplicate, `src/frob/gates/**` alone
carries 29 (19 in `gates/__init__.py`, 1 each in `_baseline.py`,
`_cve_fingerprint_scan.py`, `_docblocks.py`, `_fmt_directives.py`,
`_gate_cache.py`, `_waive.py`, `invariants.py`, 3 in `_pii_structural.py`).

A cross-cutting genuine duplication spans well beyond this finding count:
at least 9 gates modules (`_cve_fingerprint_scan.py`, `_exclude_hazard.py`,
`_opaque.py`, `_refs.py`, `_secrets.py`, `_docblocks.py`, `_docptr.py`,
`_pii_structural.py`, `_walk_lint.py`) each define their own
`_tracked_files`/`_tracked_all_files`/`_tracked_source_files`/
`_tracked_files_by_pattern` -- a `git ls-files [pattern]` -> root-relative
POSIX path tuple/frozenset helper, near-identical error handling
(warn-and-empty-on-failure), reimplemented per gate instead of shared.
Consolidating into one `frob.gates`-level helper (parametrized by
pathspec, returning both tuple and frozenset call shapes as thin
wrappers) would collapse most of `_docblocks.py`/`_docptr.py`'s
`abstraction-opportunity` finding and a good chunk of the same
"tracked-files helper" duplication pattern likely undercounted by the
detector's per-file grouping (it does not always attribute a cross-file
group to every member file, per T-1067's `gitio.py`/`testing/_runners.py`
finding shape).

`gates/__init__.py` is ALSO the T-0395 large-file-residue candidate
(~15 of its own groups per T-1067's parent ticket T-0393) -- extracting
shared abstractions from it is likely to interact with T-0395's own
split plan; read T-0395 first and coordinate rather than duplicating
file-restructuring work.

Do not attempt all 29 (+ the wider tracked-files consolidation) in one
pass if it does not fit; a coherent partial (e.g. the tracked-files
helper consolidation alone, or just `_baseline.py`'s `_read_toml` x3
duplication) is fine, with the remainder re-filed with exact counts.
Re-measure `uv run frob check --only arch --json`, filter to
abstraction-opportunity + `src/frob/gates/`, before starting -- other
tickets may land in the interim and change the count.

## Done report

Consolidated the "at least 9 gates modules each define their own
_tracked_files-shaped git-ls-files scan" duplication T-1082 specifically
called out: 5 of them (_opaque.py, _exclude_hazard.py, _refs.py,
_secrets.py, _cve_fingerprint_scan.py) had a byte-for-byte identical
`_tracked_files(root) -> tuple[str, ...]` private helper (git ls-files,
root-relative POSIX paths, degrade-to-() on any git failure). Extracted
one shared `frob.gates._tracked_files.tracked_files(root, *, caller)`
(new module) and inlined every one of the 5 call sites directly against
it, deleting all 5 per-file wrapper functions entirely (not left as thin
wrappers -- the arch detector clusters by signature, and a same-named,
same-signature wrapper in each file would still have counted as the
"N functions share this signature" abstraction-opportunity finding even
with identical bodies collapsed to a one-line delegate).

Two of the five (_exclude_hazard.py, _cve_fingerprint_scan.py) logged at
ERROR on a git failure; the shared helper standardizes on WARNING
(matching the majority -- _opaque.py/_refs.py/_secrets.py already used
WARNING) -- a disclosed, minor severity harmonization, not a behavior
change to the scan itself (still degrades to `()`, never raises).
_opaque.py's/_secrets.py's extra "N tracked file(s)" debug log line was
dropped rather than preserved via a wrapper, for the same signature-
collapse reason above -- disclosed, not silently lost (it was DEBUG-tier
and untested).

tests/test_secrets_gate.py::TestTrackedFilesGitFailure's two tests
monkeypatched `frob.gates._secrets.run_argv` directly (the old
module-local seam) -- repointed to `frob.gates._tracked_files.run_argv`
(the new, real seam) since that name-level fixup is a direct, mechanical
consequence of the consolidation itself, not new test-writing.

Did NOT attempt: the other 29 findings T-1082 (and T-1067 before it)
named (19 in gates/__init__.py, 1 each in _baseline.py,
_cve_fingerprint_scan.py's own OTHER cluster, _docblocks.py,
_fmt_directives.py, _gate_cache.py, _waive.py/_waive_lease.py,
invariants.py, 3 in _pii_structural.py), nor the wider
`_tracked_python_files`-shaped duplication (_walk_lint.py,
_pii_structural/_tracked.py, _docblocks.py, _docptr.py) the ticket
flagged as likely undercounted, nor the small new cluster this
consolidation itself surfaced (the new shared `tracked_files` now shares
a `(Path, str) -> tuple[str, ...]` signature with 4 unrelated functions
in src/frob/dup/_pipeline/_callgraph.py -- out of gates/ scope). Filed:
T-1114 (remeasure before starting -- other tickets may have
moved the count).

git diff main --diff-filter=D --stat: empty (no unintended deletions;
the initial run before this ticket's final `git merge main` transiently
showed tests/test_coverage_wait_shared.py as a 231-line deletion --
main had advanced past what this worktree last merged, past T-1095's
landing of that file; a fresh `git merge main` picked it up cleanly and
the deletion-filter check is now empty, confirmed).
tests/test_gates.py + test_secrets_gate.py + test_vet.py: 693 passed.
frob check --ticket T-1082 --only arch: 0 errors; grep-confirmed
"tracked_files" no longer appears in ANY abstraction-opportunity finding
for the 5 consolidated modules. 17 pre-existing warnings + 235
suggestions (one net-new suggestion: the dup/_pipeline/_callgraph.py
cross-package cluster noted above, disclosed, filed as part of the
residue ticket's scope-note rather than fixed out-of-scope here).
frob check --ticket T-1082 --only drift/--only test: 0 errors both runs.

### Changed
```
 src/frob/gates/_cve_fingerprint_scan.py | 21 ++----------------
 src/frob/gates/_exclude_hazard.py       | 19 ++---------------
 src/frob/gates/_opaque.py               | 27 ++---------------------
 src/frob/gates/_refs.py                 | 21 ++----------------
 src/frob/gates/_secrets.py              | 29 +++----------------------
 src/frob/gates/_tracked_files.py        | 38 +++++++++++++++++++++++++++++++++
 tests/test_secrets_gate.py              |  8 +++----
 tickets.md                              |  2 +-
 8 files changed, 54 insertions(+), 111 deletions(-)
```

### Evidence
- `tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_spawn_error_yields_no_tracked_files` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_nonzero_exit_yields_no_tracked_files` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1083 -->
```yaml
id: T-1083
title: 'arch: abstraction-opportunity remaining single-file packages extraction (T-0393/T-1067
  remainder, 23 findings)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/
- src/frob/dup/
- src/frob/lang/
- src/frob/perf/
- src/frob/process/
- src/frob/render/
- src/frob/serve/
- src/frob/strata/
- src/frob/testing/
- src/frob/tickets/
- src/frob/vet/
threat: null
component: null
```
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). The
remainder of the 84 abstraction-opportunity findings not covered by this
pass's sibling per-package tickets (gates/**, arch/**, app/**) is spread
one-or-two-per-file across ~19 small/standalone modules, ~23 findings
total: `check/_native.py` 1, `check/_python.py` 1, `dup/_pipeline.py` 2,
`lang/__init__.py` 1, `lang/_extract.py` 1, `lang/_walk_kotlin.py` 1,
`perf/_loop_effects.py` 1, `process/parsers/cargo.py` 1,
`render/_renderer.py` 1, `serve/_tools.py` 1, `strata/_compliance.py` 1,
`strata/_export.py` 1, `strata/_selfconform.py` 1, `testing/_collect.py` 1,
`tickets/__init__.py` 3, `tickets/_journal.py` 1, `vet/_capability.py` 1,
`vet/_ecosystem.py` 1, `vet/_lockfile.py` 1.

Two of these are almost certainly detector-precision FP classes, not
genuine dup -- triage these FIRST since they may be quick T-1068-style
detector fixes rather than code changes:

- `testing/_collect.py`: `collect_python_tests`/`collect_rust_tests`/
  `collect_ts_tests`/`collect_cpp_tests` sharing `(Path) -> Result[...]`
  is textbook per-language-parity shape, but T-1068's
  `_is_language_parity_family`/`_LANGUAGE_TAGS` only recognizes the
  segments `py`/`rust`/`kt`/`ts`/`cpp` -- `python` never matches `py` as
  a whole underscore-delimited segment, so this family falls through
  uncaught. Likely fix: extend `_LANGUAGE_TAGS` (or add a synonym map --
  `python`->`py`, `typescript`->`ts`, `kotlin`->`kt`, `cplusplus`->`cpp`)
  in `src/frob/arch/_python.py`, in scope src/frob/arch/ not this
  ticket's scope -- file as its own small detector ticket instead of
  fixing it here.
- `render/_renderer.py`: `RenderWriter.heading`/`.subhead`/`.good`/
  `.warn`/`.muted` are each ALREADY documented (existing `frob:invariant`
  comments at each site) as deliberate same-name thin forwarders to the
  identically-named module-level `frob.render._elements`/`_palette`
  function -- a documented, load-bearing naming convention (the vocabulary
  namespace pattern T-0448/T-0460 established), not an accidental
  duplicate. Extracting a shared `_forward(name, fn, text)` wrapper would
  likely make this WORSE (indirection with no real dedup, since each
  forwards to a different target). Recommend accepting this as a new FP
  class and filing a small T-1068-style detector ticket (recognize a
  same-name call-through to an identically-named imported symbol as
  non-actionable) in scope src/frob/arch/, not extracting here.

The rest (`tickets/__init__.py`'s 3 groups, `vet/_capability.py`'s
4-member `walk`/`walk`/`walk`/`walk` group -- likely local nested-closure
tree-walk helpers with different captured free variables per T-1067's
sibling arch-package ticket note, worth the same "read before extracting"
caution -- and the remaining single-group files) are smaller, more
plausible genuine-duplication candidates; read each before deciding.

Re-measure `uv run frob check --only arch --json` (filter to
abstraction-opportunity, excluding gates/**, arch/**, app/**) before
starting; other tickets may land in the interim and change the count.

<!-- ticket:T-1084 -->
```yaml
id: T-1084
title: 'arch: abstraction-opportunity arch package extraction (T-0393/T-1067 remainder,
  27 findings)'
state: dropped
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
```
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). After
T-1067's extraction pass (gitio/testing._runners `_excerpt`, vet package
TTL-cache helper), `src/frob/arch/**` itself carries 27 of the remaining
84 abstraction-opportunity findings: `_async_hazards.py` 3, `_concurrency.py`
1, `_concurrency_model.py` 2, `_cpp.py` 2, `_exceptions.py` 3,
`_fallibility.py` 1, `_kotlin.py` 8, `_ocp.py` 1, `_patterns.py` 3,
`_python.py` 1, `_solid.py` 1, `_typescript.py` 1.

Most of these are NOT the T-1068 language-parity shape (every member
carries a distinct language tag) -- `_is_language_parity_family` already
excludes those. What remains splits into two real classes worth
re-triaging file by file rather than assuming either uniformly:

1. Genuine coincidental-signature collisions across UNRELATED functions
   inside one file (e.g. `_async_hazards.py`'s 32-member `(Node) -> bool`
   group mixes `_is_async_def`, `_kt_has_override_modifier`,
   `_is_trivial_getter`, `_contains_splat`, and 28 others with no shared
   concern) -- these are large groups where at most a handful of members
   are truly duplicate logic; do NOT force a single extraction across an
   entire group just because the detector grouped them by signature.
2. Genuine per-language SHAPE duplication where the language tags are
   NOT all distinct (so T-1068's exclusion correctly does not apply) --
   e.g. `_kotlin.py`'s `_kt_build_class`/`_rust_build_class_shell`/
   `_ts_build_class`/`_ts_build_interface`/`_ts_build_enum` group has two
   `_ts_` members, meaning `_ts_build_class` and `_ts_build_interface`/
   `_ts_build_enum` really are three separate concerns colliding by
   signature only, not one language-parity family, and worth reading
   individually.

Read each group's actual member bodies before deciding extract vs.
accept-as-FP; do not batch-waive (abstraction-opportunity is unwaivable
by design). If a genuine new FP class turns up beyond what T-1068 already
covers (e.g. local nested-closure helpers -- `def walk(node): ...` defined
inside a larger function, recurring by trivial signature across
unrelated tree-walks -- observed in `frob.vet._capability`, may recur
here too), raise it as its own T-0370/T-1068-style detector-precision
ticket rather than hand-waiving it here.

Re-measure `uv run frob check --only arch --json` (filter to
abstraction-opportunity + `src/frob/arch/`) before starting; other
tickets may land in the interim and change the count.

## Done report

Re-measured `frob check --only arch --json` first, filtered to
abstraction-opportunity findings whose reported location is under
`src/frob/arch/`: confirmed 27 groups across 12 files, matching the
ticket body's exact per-file breakdown (_async_hazards.py 3,
_concurrency.py 1, _concurrency_model.py 2, _cpp.py 2, _exceptions.py 3,
_fallibility.py 1, _kotlin.py 8, _ocp.py 1, _patterns.py 3, _python.py 1,
_solid.py 1, _typescript.py 1).

Read every group's actual member bodies (not just the grouped names) per
the ticket's own instruction not to batch-waive. None of the 27 warrant a
manual extraction inside `src/frob/arch/`'s own declared scope. They split
into four recognizable shapes, none of them a genuine missing abstraction:

1. Check-function registry protocol collisions: `_exceptions.py`'s
   27-member `(NormalizedModule) -> list[ArchSuggestion]` group is not a
   coincidence at all -- grep confirms 33 functions across
   `src/frob/arch/*.py` match `^def check_`, and the vast majority share
   this exact bare signature. This is the package's own intentional
   common detector interface, the same shape as T-0360's dispatch-family
   exclusion and T-1068's language-parity exclusion, just not yet
   generalized to a naming-convention-based family.
2. Per-construct mirrored builders that happen to share a return type:
   `_typescript.py`'s `_ts_build_class`/`_ts_build_interface`/
   `_ts_build_enum` (read in full) build three DIFFERENT tree-sitter node
   types (`class_declaration`/`interface_declaration`/`enum_declaration`)
   into `NormalizedClass` -- distinct concerns, not one duplicated
   function. `_kotlin.py`'s 8 groups (its own module docstring explicitly
   documents "mirroring... not reusing" as the deliberate cross-adapter
   design, T-0609/T-0611) are the same shape at the cross-language-file
   level.
3. Deliberately-kept-separate trivial one-liners with reviewed precedent:
   `_bare_callee_name(callee: str) -> str` is defined byte-identically in
   `_mayraise.py`, `_fallibility.py`, and `_exceptions.py`; each docstring
   explicitly cross-references the sibling copy. A prior ticket (T-0686)
   already reviewed this exact tradeoff for the sibling `_qualname`
   duplicate in `_mayraise.py` and chose module independence over sharing
   a one-line private helper across otherwise-unrelated check families
   ("that sibling module is out of this ticket's declared scope; see this
   module's docstring for why duplicating this one small helper... is the
   intended shape here"). Re-deduplicating now would silently reverse
   that reviewed decision without a new instruction to do so -- left
   alone.
4. Large mixed-concern coincidental collisions: `_async_hazards.py`'s
   32-member `(Node) -> bool` group, `_concurrency_model.py`'s 27-member
   `(Node) -> str | None` group, etc. -- read a sample of members in each
   (e.g. `_is_async_def`/`_kt_has_override_modifier`/`_is_trivial_getter`
   share no concern beyond the generic tree-sitter-node-predicate shape).
   This is exactly the class-1 "coincidental collision, do not force
   extraction across an entire group" case the parent ticket's own body
   anticipated.

No code was changed in `src/frob/arch/`; this ticket's actual output is
the triage itself (so the next agent working this package does not
re-derive it) plus one follow-up ticket proposing the actual code fix for
class 1 above (the only class that is a genuine detector-precision gap
rather than already-correct-as-designed): T-1112 (final id after
renumbering at land), adding a `_is_check_registry_family`-style exclusion to
`frob.arch._python._check_abstraction_opportunities` for a same-signature
group where every member's bare name matches `^check_[a-z_]+$`.

Since no source changed, no new test evidence exists to bind; per the
playbook's docs-only-ticket precedent, recording the existing CLI-dispatch
integration test as evidence instead.

Gates: `uv run frob check --ticket T-1084` (gates-fast/gates-native via
the manual --only loop) clean; no new violations introduced (nothing
touched).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 894 warning(s), 426 waived
- error-findings: none (measured, zero errors)

## Failure log
- 2026-07-28 attempt 1: triage of all 27 groups found none safely extractable in src/frob/arch/ scope without reversing prior reviewed design decisions (T-0686) or fragmenting deliberate check-registry/per-language-mirror conventions; filed T-1112 for the one genuine detector-precision gap found

## Drop reason
- 2026-07-28: triage of all 27 groups (read every member body) found none safely extractable in src/frob/arch/ scope without reversing a prior reviewed design decision (T-0686) or fragmenting the deliberate check-registry/per-language-mirror conventions; the one genuine detector-precision gap found is filed separately, not this ticket's own extraction plan (absorbed by T-1112)

<!-- ticket:T-1085 -->
```yaml
id: T-1085
title: 'arch: abstraction-opportunity app package extraction (T-0393/T-1067 remainder,
  5 findings)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/
threat: null
component: null
```
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). Of the
84 remaining abstraction-opportunity findings, `src/frob/app/**` carries 5:
`check_runner.py` 2 groups (`_skip_note_result`/`_missing_tool_result`/
`tool_unavailable_result`/`tool_disabled_result`/`parse_junit_xml` sharing
`(str, str) -> ToolResult`; `_deploy_drift_result`/`_deploy_conformance_result`/
`_derived_state_integrity_result`/`_run_clang_format`/`_run_cargo_fmt_check`/
`_run_cargo_valgrind`/`_run_bind` sharing `(Path) -> ToolResult | None`),
`debt_runner.py` 1 (`_load_snapshot`/`_load_snapshot`/`_snapshot` sharing
`(Path)` -- note the duplicate NAME within the group, worth checking for a
literal same-file duplicate first), `deploy_runner.py` 1
(`_design_dir`/`_design_dir`/`_read_ledger_text_or_empty`/
`_read_archive_text_or_empty` sharing `(Path) -> str` -- again a repeated
name), `perf_runner.py` 1 (`_heat`/`_collect` sharing `(AppConfig) -> None`).

The `check_runner.py` `ToolResult`-builder groups look like the most
promising genuine extraction (several near-identical "build a skip/
unavailable/disabled ToolResult with this message" constructors); the
`debt_runner.py`/`deploy_runner.py` groups with a repeated function name
inside one group are worth checking FIRST for a literal same-file
duplicate (two defs with the same name, one shadowing the other, possibly
dead code) before assuming they're two genuinely distinct functions that
happen to collide.

Re-measure `uv run frob check --only arch --json` (filter to
abstraction-opportunity + `src/frob/app/`) before starting; other tickets
may land in the interim and change the count.

<!-- ticket:T-1088 -->
```yaml
id: T-1088
title: implement 5 statically-detectable-only SC-* supply-chain detectors with no
  enforcing check today
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- docs/design/registry/supply-chain.yaml
- docs/modules/vet.md
- tests/test_vet.py
- src/frob/gates/_waive.py
- docs/design/registry/check-coverage.yaml
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: detectors need docs.modules/vet.md + tests/test_vet.py updates per playbook;
    new VET007-010 rule ids need registering in gates/_waive.py's hand-maintained
    REG002 known-id list and check-coverage.yaml's CHK-GATE-VET0xx entries, same pattern
    T-1101 used for its own new VET ids
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_vet.py
  reason: detectors need docs.modules/vet.md + tests/test_vet.py updates per playbook;
    new VET007-010 rule ids need registering in gates/_waive.py's hand-maintained
    REG002 known-id list and check-coverage.yaml's CHK-GATE-VET0xx entries, same pattern
    T-1101 used for its own new VET ids
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_waive.py
  reason: detectors need docs.modules/vet.md + tests/test_vet.py updates per playbook;
    new VET007-010 rule ids need registering in gates/_waive.py's hand-maintained
    REG002 known-id list and check-coverage.yaml's CHK-GATE-VET0xx entries, same pattern
    T-1101 used for its own new VET ids
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: detectors need docs.modules/vet.md + tests/test_vet.py updates per playbook;
    new VET007-010 rule ids need registering in gates/_waive.py's hand-maintained
    REG002 known-id list and check-coverage.yaml's CHK-GATE-VET0xx entries, same pattern
    T-1101 used for its own new VET ids
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_exact_pin_not_flagged
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_package_json_wildcard_flagged
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_cargo_toml_caret_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_absolute_data_files_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_traversal_data_files_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_package_relative_data_files_not_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_no_setup_py_not_flagged
- tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_branch_ref_flagged
- tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_full_sha_ref_not_flagged
- tests/test_vet.py::TestSupplyChainCiActionPin::test_no_workflows_dir_not_flagged
- tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_tracked_so_without_recipe_flagged
- tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_so_with_nearby_cargo_toml_not_flagged
- tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_no_binary_files_not_flagged
threat: null
component: null
```
Five supply-chain.yaml entries are tagged checkability:['statically-detectable']
ONLY (no requires-external-data, no process-only) but have no enforcing
detector in src/frob/vet/ today -- found while reconciling T-0721's 39
deferred:T-0721 entries:

- SC-ATTACK-UNPINNED-DEPENDENCIES: a lockfile/manifest dependency spec with
  no pin (e.g. a `*`/caret/range spec instead of an exact version) is a
  purely structural property of the manifest text.
- SC-DETECTION-PYTHON-INSTALL-ARTIFACTS: setup.py/setup.cfg/pyproject.toml
  build-backend artifacts a malicious sdist could smuggle (data_files
  writing outside the package, a cmdclass hook already tracked separately
  as install-hook capability, but the broader "installed artifact ends up
  somewhere unexpected" shape is not).
- SC-DETECTION-NPM-NON-REGISTRY-SOURCE: a package.json dependency spec
  pointing at a git/tarball/local-path source instead of a registry
  version range is a structural property of the manifest text.
- SC-DETECTION-UNPINNED-CI-ACTION: a GitHub Actions `uses: owner/action@ref`
  where `ref` is a mutable branch/tag (not a full commit SHA) is a
  structural property of tracked `.github/workflows/*.yaml`.
- SC-DETECTION-OPAQUE-BINARY-ARTIFACT: a tracked binary blob (.whl/.so/
  .node/.wasm and similar) committed directly into source control with no
  accompanying build recipe is a structural property of the tracked file
  tree.

Each needs either a real detector in src/frob/vet/ (then handled_by:<rule>)
or, on closer investigation, a reasoned disposition explaining why it is
NOT actually structurally checkable after all (narrower than it first
looks). Do not leave any of the five at a bare `deferred` pointing back
here without investigating first.

## Done report

Implemented VET007-VET010, four project-tree-wide supply-chain structural
detectors folded into `scan_tree` via `src/frob/vet/_supplychain.py::
supply_chain_tree_violations` (once per scan, not per dependency/lockfile):

- VET007 (SC-ATTACK-UNPINNED-DEPENDENCIES): unpinned pyproject.toml/
  package.json/Cargo.toml dependency specs.
- VET008 (SC-DETECTION-PYTHON-INSTALL-ARTIFACTS): setup.py/setup.cfg
  data_files destinations that are absolute or escape via `../`.
- VET009 (SC-DETECTION-UNPINNED-CI-ACTION): `.github/workflows/*.yaml`
  `uses: owner/action@ref` pinned to a mutable ref, not a full commit SHA.
- VET010 (SC-DETECTION-OPAQUE-BINARY-ARTIFACT): tracked binary blobs with
  no nearby build recipe.

SC-DETECTION-NPM-NON-REGISTRY-SOURCE needed no new detector: investigation
found `_ecosystem.py::_npm_non_registry_rule` (VET-JS004) already covers
it and is already wired into `_scan.py`'s per-dependency path -- it was
just missing its `frob:enforces` edge and its `supply-chain.yaml`
disposition, both added.

All five `supply-chain.yaml` entries re-dispositioned from
`deferred:T-1088` to `handled_by:<rule>`.

Scope note: the ticket's declared scope (`src/frob/vet/**`,
`docs/design/registry/supply-chain.yaml`) did not cover the files this
work structurally needed to touch -- `docs/modules/vet.md` (playbook
mandate), `tests/test_vet.py` (fixtures), `src/frob/gates/_waive.py`
(REG002's hand-maintained known-VET-rule-id list, same file T-1087
originally populated), and `docs/design/registry/check-coverage.yaml`
(CHK-GATE-VET007..010 entries + gate_rule_total bump, same T-1101
precedent). Extended scope via `frob ticket scope T-1088 --add ...`
with a reason, rather than hand-editing outside declared scope or
silently working around SCOPE001.

Changed:
- src/frob/vet/_supplychain.py (new)
- src/frob/vet/_scan.py::scan_tree (wires supply_chain_tree_violations in)
- src/frob/vet/_ecosystem.py::_npm_non_registry_rule (frob:enforces edge)
- src/frob/gates/_waive.py (VET007-010 added to REG002 known-id list)
- docs/design/registry/supply-chain.yaml (5 dispositions re-pointed)
- docs/design/registry/check-coverage.yaml (4 new CHK-GATE entries, total 254)
- docs/modules/vet.md (public API + new Mechanics section)
- tests/test_vet.py (4 new test classes, 14 tests)

Evidence: 14 node ids bound via `frob ticket evidence T-1088` (see
tests/test_vet.py TestSupplyChainUnpinnedDependencies /
TestSupplyChainInstallArtifacts / TestSupplyChainCiActionPin /
TestSupplyChainOpaqueBinaryArtifact) -- all 14 pass:
`uv run pytest tests/test_vet.py -k SupplyChain -p no:cacheprovider -q`
-> 14 passed. Full `tests/test_vet.py` (414 tests) also passes clean
after the merge.

Gates: `uv run frob check --ticket T-1088 --only gates-fast/gates-native/
gates-security` all pass 0 errors (gates-fast has 2 pre-existing TICK006
findings from T-1077/T-1084's merged-in Done reports, unrelated to this
ticket's scope -- confirmed present on plain `main` before this change).

Filed: none -- SC-DETECTION-NPM-NON-REGISTRY-SOURCE resolved via
disposition-only fix (existing detector), no new ticket needed; the two
pre-existing TICK006 phantom-draft findings on main are out of scope for
T-1088 and not filed as a new ticket since they were not discovered by
this ticket's own investigation (playbook doesn't require filing findings
outside the work performed here).

### Changed
```
 docs/design/registry/check-coverage.yaml |  18 +-
 docs/design/registry/supply-chain.yaml   |  10 +-
 docs/modules/vet.md                      |  32 ++++
 src/frob/gates/_waive.py                 |   7 +
 src/frob/vet/_ecosystem.py               |   1 +
 src/frob/vet/_scan.py                    |   6 +
 src/frob/vet/_supplychain.py             | 288 +++++++++++++++++++++++++++++++
 tests/test_vet.py                        | 160 +++++++++++++++++
 tickets.md                               |  39 ++++-
 9 files changed, 554 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_exact_pin_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_package_json_wildcard_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_cargo_toml_caret_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_absolute_data_files_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_traversal_data_files_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_package_relative_data_files_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainInstallArtifacts::test_no_setup_py_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_branch_ref_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_full_sha_ref_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainCiActionPin::test_no_workflows_dir_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_tracked_so_without_recipe_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_so_with_nearby_cargo_toml_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_no_binary_files_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 7 error(s), 635 warning(s), 425 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:295, INV006@src/frob/gates/_todo_fmt.py, TICK006@tickets.md

<!-- ticket:T-1091 -->
```yaml
id: T-1091
title: 'strata: drop SYS103''s _PACKAGE_ROOT restriction now that the self-model covers
  tests/scripts/native trees (T-1079 follow-up)'
state: queued
kind: security
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- tests/unit/strata/test_selfconform.py
threat: null
component: null
```
T-1079 modeled tests/**, scripts/**, frob-core/src/**, strata-core/src/**
in design/frob.strata (testsuite, scripts_ops, strata_core_native,
frob_core_native nodes) so an unrestricted SYS103 scan against the model
now returns zero findings. `_coverage_totality_scan_prefix`
(src/frob/strata/_selfconform.py) itself was out of T-1079's declared
scope and still restricts the LIVE SELFAUDIT001 gate to _PACKAGE_ROOT
("src/frob") on frob's own tree -- now that the model covers the whole
repo with zero findings either way, that restriction can be dropped (or
narrowed to a real, disclosed exception) so the live gate actually
checks what the model now claims to cover, closing the gap for real
rather than just in a test harness.

<!-- ticket:T-1095 -->
```yaml
id: T-1095
title: 'daemon: cross-worktree single-flight coverage/collection keyed by source digest'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
blocked_by:
- T-1092
parent: T-0321
tier: story
sprint: null
scope:
- src/frob/testing/**
- src/frob/serve/**
- docs/modules/testing.md
- docs/modules/serve.md
- tickets.md
- tests/test_coverage_wait_shared.py
- tests/test_app.py
scope_changes:
- op: add
  glob: tests/test_app.py
  reason: run_coverage_wait now also calls git_common_dir (a subprocess spawn) on
    every invocation for the T-1095 shared-state-dir resolution; two pre-existing
    tests here monkeypatch subprocess.run with a strict (cmd,cwd,check) signature
    that only anticipated the coverage command itself, so they now TypeError on the
    new git rev-parse spawn -- widen the fakes to pass through non-matching commands
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_coverage_wait_shared.py::TestTreeDigest::test_identical_hashes_produce_identical_digest
- tests/test_coverage_wait_shared.py::TestTreeDigest::test_differing_hashes_produce_differing_digest
- tests/test_coverage_wait_shared.py::TestSharedStateDir::test_two_worktrees_of_same_clone_share_one_dir
- tests/test_coverage_wait_shared.py::TestSharedStateDir::test_no_git_falls_back_to_worktree_local
- tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_identical_digest_worktrees_share_one_run
- tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_differing_digest_worktrees_each_run_independently
acceptance:
- text: GIVEN two worktrees checked out to commits whose tracked source content hashes
    identically WHEN both concurrently request coverage via run_coverage_wait THEN
    only one real coverage subprocess runs across BOTH worktrees and the second gets
    the shared fresh-or-failed result instead of independently re-running the suite
  evidence:
  - tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_identical_digest_worktrees_share_one_run
- text: GIVEN two worktrees whose source content differs WHEN both request coverage
    concurrently THEN each runs its own independent coverage pass (no cross-contamination
    of results across differing digests)
  evidence:
  - tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_differing_digest_worktrees_each_run_independently
threat: null
component: null
```
Child (b) of T-0321. T-0322 shipped run_coverage_wait with a PER-WORKTREE single-flight lock (.frob/coverage.lock, a path inside that worktree's own .frob/ -- confirmed 2026-07-28 via src/frob/testing/_coverage_wait.py) and a staleness check against that worktree's own coverage stamp. It does not share across worktrees: N agents on N git worktrees of the same commit (the common parallel-dispatch shape, per docs/guides/agent-playbook.md) each still pay their own full coverage run because each has its own .frob/coverage.lock and .frob/ cache. Move the single-flight lock and the content-addressed result cache to a location keyed by TREE DIGEST (source content hash, not worktree path) rather than worktree-local path -- e.g. a shared cache under the daemon's project-root-independent state dir (or the T-1092 daemon arbitrating across worktrees it can see via .claude/worktrees enumeration, matching T-0733's existing lease-enumeration pattern). A worktree with identical source content to one that already has a fresh coverage result gets that result immediately with zero subprocess spawned.

## Done report

Added a cross-worktree single-flight/result-cache layer on top of
T-0322's original per-worktree `run_coverage_wait`, keyed by SOURCE TREE
DIGEST rather than worktree path.

src/frob/testing/_coverage_wait.py:
- `tree_digest(snapshot)`: sha256 hex over the snapshot's tracked
  *.py/*.rs/*.ts/*.tsx file hashes, sorted by path. Two worktrees with
  byte-for-byte identical tracked source produce the identical digest
  regardless of path; any differing file changes it.
- `shared_state_dir(root)`: `<git-common-dir>/frob-coverage-shared/`,
  resolved via the existing `frob.gitio.git_common_dir` primitive -- ONE
  location per clone, shared by every linked worktree, not per worktree.
  Falls back to `<root>/.frob/frob-coverage-shared` outside a git repo.
- `SharedCoverageResult`: the content-addressed cached outcome
  (`ok`/`ran`/`duration_s`/`file_hashes`) one worktree records for a
  digest; `_read_shared_result`/`_write_shared_result` are the cache
  accessors, `_shared_coverage_lock` the per-digest flock serializing
  concurrent worktrees sharing that digest.
- `run_coverage_wait` now checks a digest cache hit before AND after
  acquiring the shared per-digest lock (the second check catches a
  worktree that raced this one and finished while it was blocked),
  adopting a hit via `_adopt_shared_result` (copies the cached
  `file_hashes` into this worktree's OWN local `.frob/coverage-stamp` so
  local staleness checks/gates see it as fresh too) with zero subprocess
  spawned. A miss runs `command` exactly as before
  (`_run_and_settle_shared`, extracted to keep `run_coverage_wait` under
  ARCH001's 60-line threshold) and records the result (success or
  failure -- acceptance [0] promises a shared fresh-OR-FAILED result, not
  success-only) for every other worktree sharing the digest.
- The ORIGINAL per-worktree `.frob/coverage.lock` (`_coverage_lock`,
  `coverage_lock_path`) is unchanged and still wraps the whole call --
  the shared layer composes with it, does not replace it.

Real two-worktree concurrency test (tests/test_coverage_wait_shared.py):
`_two_real_worktrees` creates an actual `git worktree add` pair off one
origin clone. `TestCrossWorktreeSingleFlight.
test_identical_digest_worktrees_share_one_run` runs `run_coverage_wait`
on both worktrees concurrently (two threads, a barrier, a faked but
slow-ish coverage command) and asserts exactly ONE real spawn happened
across both -- acceptance [0]. `test_differing_digest_worktrees_each_
run_independently` mutates one worktree's tracked file first and asserts
BOTH spawn independently -- acceptance [1]. `TestTreeDigest`/
`TestSharedStateDir` cover the two primitives directly.

Extended scope: had to add tests/test_app.py (T-1093/T-0803's own
pre-existing coverage-wait tests) -- run_coverage_wait now also spawns a
`git rev-parse --git-common-dir` subprocess via git_common_dir on every
call, and two of that file's tests monkeypatch subprocess.run with a
strict (cmd, cwd, check) signature that only anticipated the coverage
command itself; widened both fakes to pass unrelated commands through to
the real subprocess.run rather than TypeError-ing on the new spawn.

Pre-existing, unrelated: `frob check` reported two TICK006 phantom-draft
errors (T-1077/T-1084 done reports citing draft ids that died at land)
and INV006 hits on the freshly split gates modules, all predating this
ticket and outside its scope -- repaired inline by the coordinator
(prose repointed at the refiled real ids T-1115/T-1112, split-carried
INV006 waivers added) rather than fixed here. ruff-format also flags
src/frob/gates/__init__.py and tests/test_app_daemon_proxy.py as
needing reformatting; confirmed pre-existing on main (verified against
the root checkout directly), not introduced by this change.

Cut: none against acceptance [0]/[1] -- both are proven by a real
two-worktree test, not a simulated stand-in.

### Changed
```
 docs/modules/testing.md            |  47 +++++-
 src/frob/testing/__init__.py       |   6 +
 src/frob/testing/_coverage_wait.py | 327 ++++++++++++++++++++++++++++++++++---
 tests/test_app.py                  |  22 ++-
 tests/test_coverage_wait_shared.py | 231 ++++++++++++++++++++++++++
 tickets.md                         |   3 +-
 6 files changed, 605 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/test_coverage_wait_shared.py::TestTreeDigest::test_identical_hashes_produce_identical_digest` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestTreeDigest::test_differing_hashes_produce_differing_digest` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestSharedStateDir::test_two_worktrees_of_same_clone_share_one_dir` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestSharedStateDir::test_no_git_falls_back_to_worktree_local` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_identical_digest_worktrees_share_one_run` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_differing_digest_worktrees_each_run_independently` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1097 -->
```yaml
id: T-1097
title: 'daemon: resource leases/semaphores (coverage=1 writer) arbitrated by the socket
  daemon'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
blocked_by:
- T-1092
- T-1095
parent: T-0321
tier: story
sprint: null
scope:
- src/frob/serve/**
- src/frob/testing/**
- docs/modules/serve.md
- docs/modules/testing.md
- tickets.md
- tests/test_serve_leases.py
- tests/test_app_daemon_proxy.py
scope_changes:
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: 'tests/test_serve_leases.py imports _start_daemon from this file (DUP001:
    reuse the existing helper rather than a byte-identical duplicate)'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_serve_leases.py::TestResourceLeaseManager::test_second_acquire_blocks_until_first_releases
- tests/test_serve_leases.py::TestResourceLeaseManager::test_acquire_times_out_if_never_freed
- tests/test_serve_leases.py::TestResourceLeaseManager::test_release_holder_frees_every_resource_that_holder_held
- tests/test_serve_leases.py::TestResourceLeaseManager::test_distinct_resources_do_not_contend
- tests/test_serve_leases.py::TestResourceLeaseManager::test_reentrant_acquire_by_same_holder_does_not_deadlock
- tests/test_serve_leases.py::TestResourceLeaseManager::test_release_of_unheld_resource_is_a_noop
- tests/test_serve_leases.py::TestLeaseRpc::test_explicit_release_frees_the_slot_for_the_next_waiter
- tests/test_serve_leases.py::TestLeaseRpc::test_second_client_blocks_until_first_releases
- tests/test_serve_leases.py::TestConnectionCrashReleasesLease::test_closing_connection_without_explicit_release_frees_the_lease
acceptance:
- text: GIVEN N concurrent clients requesting a coverage run WHEN the daemon arbitrates
    access THEN exactly one holds the coverage writer semaphore at a time and the
    rest block or receive the shared result, with no two coverage subprocesses running
    concurrently against overlapping state
  evidence:
  - tests/test_serve_leases.py::TestLeaseRpc::test_second_client_blocks_until_first_releases
- text: GIVEN a client holding a lease crashes or disconnects WHEN the daemon detects
    the dead connection THEN the lease is released automatically (no permanently stuck
    semaphore requiring a daemon restart)
  evidence:
  - tests/test_serve_leases.py::TestConnectionCrashReleasesLease::test_closing_connection_without_explicit_release_frees_the_lease
threat: null
component: null
```
Child (f) of T-0321. Today T-0322's coverage.lock is a plain per-worktree fcntl.flock with no arbitration beyond OS-level blocking, no visibility into who holds it, and no daemon-mediated release-on-crash semantics. Once T-1095 makes coverage single-flight CROSS-worktree (arbitrated by the T-1092 daemon rather than a per-worktree file lock), formalize it as a general named-resource lease/semaphore primitive the daemon owns (starting with coverage=1 writer, per T-0321's body), so other future contended resources (e.g. a future write-serializing need) can register the same way instead of each inventing its own flock convention. Lease release must be tied to socket connection liveness (a crashed/killed client's lease is freed by the daemon detecting the closed connection), not just an explicit release call, to satisfy T-0321's requirement 3 (killing a client loses nothing, nothing to clean up).

## Done report

Generalized T-0322/T-1095's coverage-only fcntl.flock single-flight into
a named resource lease/semaphore primitive the T-1092 socket daemon
itself owns and arbitrates, with release tied to socket connection
liveness.

src/frob/serve/_leases.py (new): `ResourceLeaseManager` -- a
threading.Condition-guarded dict of named resources, each with a fixed
capacity (default `DEFAULT_LEASE_CAPACITY` = 1, an exclusive writer lock,
matching coverage's own contract), created on first mention.
`acquire(resource, holder_id, capacity=, timeout_s=)` blocks until a slot
frees or the timeout elapses (re-entrant for a holder that already holds
the slot, so a redundant acquire from the same connection can't
self-deadlock); `release` frees one slot; `release_holder` frees every
slot a given holder occupies in one call.

src/frob/serve/_socketd.py: two new JSON-RPC methods special-cased in
`_RequestHandler.handle` alongside subscribe/frob_version/frob_shutdown:
`frob_lease_acquire` (blocks THIS connection's own handler thread --
ThreadingUnixStreamServer gives each connection its own thread, so
blocking here never blocks another connection) and `frob_lease_release`.
Each connection gets a `_lease_holder_id` in `setup()`; `handle`'s
`finally` block now unconditionally calls `lease_manager.release_
holder(self._lease_holder_id)`, same place `subscribe`'s per-connection
unsubscribe already runs -- a crashed or killed client (socket closed
with no explicit frob_lease_release) has every lease it held freed the
moment the daemon notices, no daemon restart required (acceptance [1]).
`_DaemonServer.__init__` now constructs one `ResourceLeaseManager` shared
across every connection thread.

tests/test_serve_leases.py: `TestResourceLeaseManager` covers the pure
manager directly (blocking/release, timeout, multi-resource independence,
re-entrancy, release-of-unheld no-op). `TestLeaseRpc.test_second_client_
blocks_until_first_releases` runs two REAL persistent socket connections
against a real running daemon and proves exactly one holds "coverage" at
a time, the second blocks until the first explicitly releases (acceptance
[0]). `TestConnectionCrashReleasesLease.test_closing_connection_without_
explicit_release_frees_the_lease` acquires the lease on one connection,
closes that socket with NO release sent (a real crash-shaped event), and
proves a second client can then acquire it (acceptance [1]).

Scope note (disclosed, not silently dropped): this ticket ships and
proves the daemon-owned arbitration primitive itself. It does NOT rewire
frob.testing._coverage_wait.run_coverage_wait's actual subprocess flow to
acquire ITS lock through this daemon RPC instead of its existing
per-worktree (T-0322) and shared-per-digest (T-1095) fcntl.flock layers
-- that wiring touches frob.app._daemon_proxy, contended with T-1106's
own src/frob/app/ work this wave and outside this ticket's src/frob/
serve/**, src/frob/testing/** scope. Filed as a follow-on:
T-1118.

Also filed (pre-existing, unrelated, found while re-running gates on
this ticket): T-1119 -- gate:TICK006 phantom-draft-citation
errors from T-1077/T-1084's (and, this session, T-1095's own) Done
reports citing drafts a later tickets.md ledger-restore step wiped
before land; a repeat of the historical T-0707/T-0615 incident class the
playbook's section 10b step 6 warns about, hit again despite following
the recipe (the draft in question was filed BEFORE this session's own
restore step for T-1095, not after -- exactly the ordering mistake
section 10b step 6 calls out). Not fixed inline; same disposition as the
pre-existing T-1077/T-1084 instances.

### Changed
```
 docs/modules/serve.md      |  64 ++++++++++++
 src/frob/serve/_leases.py  | 201 +++++++++++++++++++++++++++++++++++
 src/frob/serve/_socketd.py |  64 ++++++++++++
 tests/test_serve_leases.py | 255 +++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                 |  69 +++++++++++-
 5 files changed, 651 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_second_acquire_blocks_until_first_releases` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_acquire_times_out_if_never_freed` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_release_holder_frees_every_resource_that_holder_held` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_distinct_resources_do_not_contend` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_reentrant_acquire_by_same_holder_does_not_deadlock` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestResourceLeaseManager::test_release_of_unheld_resource_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestLeaseRpc::test_explicit_release_frees_the_slot_for_the_next_waiter` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestLeaseRpc::test_second_client_blocks_until_first_releases` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestConnectionCrashReleasesLease::test_closing_connection_without_explicit_release_frees_the_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1099 -->
```yaml
id: T-1099
title: 'strata-core: split parse.rs (4346 lines) into grammar-family modules'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/
- tests/unit/strata/
acceptance:
- text: given the strata-core crate, when the split lands, then parse.rs holds only
    the parser spine, grammar families live in their own modules, no file exceeds
    2000 lines, and cargo test plus the full strata litmus suite pass unchanged
  evidence: []
threat: null
component: null
```
parse.rs accreted the whole strata grammar across T-0629/T-0700/T-0702 and siblings (4346 lines). Split by grammar family per the T-1072/T-1086 discipline translated to Rust module conventions (mod files, pub(crate) surfaces re-exported from parse.rs or lib.rs so the python bindings and goldens stay byte-identical). Discovered alongside the large-file gate gap (T-1102); the split makes the Rust tree pass the ceiling that gate will enforce.

<!-- ticket:T-1100 -->
```yaml
id: T-1100
title: 'frob ticket flow: created/day vs landed/day vs net + naive burn-down ETA (one
  table, builds on T-0938 velocity mining)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner.py
- tests/test_tickets_velocity.py
- docs/modules/tickets.md
acceptance:
- text: 'given a frob-enabled repo, when frob ticket flow runs, then it prints per-day
    filed/landed/net counts (created: fields + ledger git history via the T-0938 transition
    miner), current open count, the trailing-3-day net rate, and a naive ETA line
    (open / trailing net rate) clearly labeled as extrapolation'
  evidence: []
threat: null
component: null
```
User request 2026-07-28: a simple ticket data-analysis command showing the rate tickets grow vs the rate they complete. Reuse sprint_velocity's git-history transition mining (T-0938) for the landed side and the created: fields for the filed side; plain render-layer table, no new storage. Keep it genuinely simple -- one table plus one ETA line.

<!-- ticket:T-1104 -->
```yaml
id: T-1104
title: 'docs: document T-1102 single-file-mode parity + LARGE001 in docs/modules/arch.md
  (analyze_project anchors)'
state: done
kind: docs
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/arch.md
- src/frob/arch/__init__.py
- tests/unit/test_memo.py
- tests/test_arch_gate.py
scope_changes:
- op: add
  glob: tests/unit/test_memo.py
  reason: 'docs-kind ticket: bind evidence test files in scope before landing (playbook
    recurring-refusal note)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_arch_gate.py
  reason: 'docs-kind ticket: bind evidence test files in scope before landing (playbook
    recurring-refusal note)'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
- tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk
acceptance:
- text: given docs/modules/arch.md, when the section lands, then analyze_project's
    single-file behavior and the LARGE001 channel are documented at the anchors its
    frob:doc directives cite, and the AFFECT001 waiver T-1102 placed at the touched
    symbol is retired
  evidence:
  - tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk
threat: null
component: null
```
Refile of T-1102's dead draft T-1104 (post-close renumber loss). docs/modules/arch.md was outside T-1102's declared scope; this carries the doc debt plus retiring the disclosed AFFECT001 waiver.

## Done report

Documented T-1102's disclosed doc debt at the exact anchors
`analyze_project`'s own `frob:doc` directives cite: added two new
paragraphs to docs/modules/arch.md's `#public-api` section (the
`analyze_project` block) --

1. Single-file-mode parity (T-1102): what changed (`root.is_file()` ->
   resolve to `root.parent` + a one-file candidate list instead of
   `_collect_files`), why the old behavior silently produced zero
   findings for a plain file (`.git`/`os.walk` both no-op on a file), and
   the byte-identical-shape guarantee `_analyze_one_file` gives, citing
   the real proving test.
2. `large-file`/`LARGE001` (T-0368/T-0372 advisory, T-1102 gate wiring):
   the advisory category's own threshold/exemption rule plus the gate-
   side WARN first-turn-on wiring, cross-referencing docs/modules/gates.md's
   existing rule-catalog entry rather than duplicating its turn-on-count
   detail.

Retired the disclosed `frob:waive AFFECT001` directive T-1102 left on
`analyze_project` (citing this ticket's pre-renumber draft id) -- the doc
debt it was waiving is now paid, so the waiver is dead weight, not a live
disclosure; replaced with a plain `frob:ticket T-1104` marker matching
this module's existing per-ticket marker convention. Confirmed no
AFFECT001 refire: `frob check --ticket T-1104 --only affect_drift` is
clean (0 errors).

Verified the anchor exists and resolves: `<a id="public-api"></a>` is
the same anchor `# frob:doc docs/modules/arch.md#public-api` on
`analyze_project` already cited (docanchor/doclink gates both clean, see
below) -- no new anchor was invented, the existing one now carries more
content.

Docs-kind ticket, no code behavior changed -- scope-added the two tests
that actually prove the documented behavior
(`tests/unit/test_memo.py`, `tests/test_arch_gate.py`) before recording
evidence, per the playbook's docs-kind land-refusal note, and bound both
to the ticket's single acceptance criterion (`--accepts 0`).

Gates (manual `--only` loop, `--ticket T-1104`): prework/coverage/
docanchor/doclink/scope/affect_drift/drift all 0 errors (measured after a
fresh `frob ticket sweep T-1104`, since PRE001 went stale after the
mid-ticket `frob ticket scope --add`).

Tests: both cited evidence node ids re-run individually and pass
(`tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit`,
`tests/test_arch_gate.py::TestArchGateLargeFile::
test_single_file_mode_matches_directory_walk` -- 1 passed each, measured).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 752 warning(s), 428 waived
- error-findings: INV006@src/frob/gates/_todo_fmt.py, TICK006@tickets.md

<!-- ticket:T-1105 -->
```yaml
id: T-1105
title: 'daemon: real version-handshake RPC on the socket daemon (replace sidecar meta-file
  skew detection)'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: T-0321
tier: ticket
sprint: null
scope:
- src/frob/serve/_socketd.py
- src/frob/app/_daemon_proxy.py
- tests/test_app_daemon_proxy.py
- docs/modules/serve.md
- tests/test_serve_socket.py
scope_changes:
- op: add
  glob: tests/test_serve_socket.py
  reason: frob_version/frob_shutdown RPC additions to _socketd.py need direct socket-level
    test coverage in this file, not just via the proxy's own test file
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_serve_socket.py::TestDispatchRequest::test_frob_version_reports_daemon_version
- tests/test_serve_socket.py::TestDispatchRequest::test_frob_shutdown_stops_the_server
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_spawns_when_nothing_recorded
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_noop_when_version_matches
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_version_handshake_end_to_end
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew
acceptance:
- text: given a running daemon of a different frob version, when the proxy queries
    it, then skew is detected via a daemon-side version RPC (not the .frob/daemon.meta.json
    sidecar), the stale daemon is replaced, and the query succeeds
  evidence:
  - tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew
threat: null
component: null
```
Refile of T-1093's dead draft T-1105 (lost in the 10b worktree-ledger restore before land). T-1093 shipped sidecar-file skew detection because src/frob/serve/** was a sibling's scope that wave; this moves the version handshake into the daemon protocol proper.

## Done report

Replaced T-1093's client-written `.frob/daemon.meta.json` sidecar-file
version-skew check with a real protocol-level handshake on the socket
daemon itself.

`src/frob/serve/_socketd.py`: added `daemon_version()` (the daemon
process's own installed `frob` version) and two new JSON-RPC methods
special-cased in `_RequestHandler.handle` alongside `subscribe`:
`frob_version` (answers `{"version": ...}`) and `frob_shutdown` (starts a
helper thread that calls `server.shutdown()` and acknowledges
immediately -- calling `shutdown()` inline on the connection thread would
deadlock it against the very `serve_forever()` loop it is stopping).

`src/frob/app/_daemon_proxy.py`: `ensure_daemon` now calls
`_query_daemon_version` (a `send_request(root, "frob_version")`) instead
of reading a sidecar meta file; on a version mismatch it calls
`_shutdown_stale_daemon` (a `frob_shutdown` RPC, waiting on the lock file
to clear) instead of `SIGTERM`-by-recorded-pid. Removed `_meta_path`/
`_read_meta`/`_write_meta`/`_kill_stale_daemon` and the `.frob/
daemon.meta.json` sidecar entirely -- nothing writes it anymore.

Tests: added `TestDispatchRequest.test_frob_version_reports_daemon_version`
and `.test_frob_shutdown_stops_the_server` to tests/test_serve_socket.py
(real running daemon, real socket) -- required extending T-1105's scope
to include this test file (`frob ticket scope T-1105 --add
tests/test_serve_socket.py`), since the new RPC methods live in
_socketd.py and need direct socket-level coverage. Updated
tests/test_app_daemon_proxy.py's TestEnsureDaemon tests to mock the new
_query_daemon_version/_shutdown_stale_daemon seam instead of the removed
meta-file functions, and added a real end-to-end
test_version_handshake_end_to_end against a live daemon.

docs/modules/serve.md: added a new "Version handshake (T-1105)" section
under the socket-daemon docs describing the two new RPC methods, and
rewrote the "Version-skew self-heal" subsection under "CLI daemon proxy
(T-1093)" plus its decision-tree diagram to describe the RPC-based flow
instead of the sidecar file.

Cut: none -- T-1093's disclosed residual (a real version-handshake RPC,
T-draft-8a56400c) is now fully closed by this ticket.

### Changed
```
 docs/modules/serve.md          |  79 +++++++++++++++------
 src/frob/app/_daemon_proxy.py  | 154 +++++++++++++++++++----------------------
 src/frob/serve/_socketd.py     |  55 +++++++++++++++
 tests/test_app_daemon_proxy.py |  49 ++++++++-----
 tests/test_serve_socket.py     |  45 ++++++++++++
 5 files changed, 259 insertions(+), 123 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestDispatchRequest::test_frob_version_reports_daemon_version` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestDispatchRequest::test_frob_shutdown_stops_the_server` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_spawns_when_nothing_recorded` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_noop_when_version_matches` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_version_handshake_end_to_end` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1106 -->
```yaml
id: T-1106
title: 'daemon: wire remaining query-shaped CLI commands through the proxy (T-0321
  integration map)'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: T-0321
tier: ticket
sprint: null
scope:
- src/frob/app/_daemon_proxy.py
- src/frob/app/
- tests/test_app_daemon_proxy.py
- docs/modules/serve.md
acceptance:
- text: given each query-shaped CLI command from T-0321's integration map (outline,
    map, xref, graph, exports, stats, ...), when the daemon runs, then the command
    serves from the daemon with a differential-parity test proving daemon-served output
    identical to in-process
  evidence: []
threat: null
component: null
```
Refile of T-1093's dead draft T-1106 (lost in the 10b restore). T-1093 wired frob perf hot --json only (the one command with a field-identical payload to diff); this extends the proxy across the integration map, each command gaining its own parity test.

<!-- ticket:T-1107 -->
```yaml
id: T-1107
title: 'gates: INV006 exclusivity-claim gap in src/frob/tickets/_new_renumber.py (T-1103
  residue)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- tests/test_gates.py
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: evidence-close needs a regression test proving INV006 finding is gone; test
    file itself lives outside the code scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestInv006Gate::test_new_renumber_file_has_no_unanchored_exclusivity_claim
threat: null
component: null
```
frob check --only invariant fails with 1 error: src/frob/tickets/_new_renumber.py makes an exclusivity/normative claim (\bonly\b, e.g. line 68/140/148/150/152) with no frob:invariant INV-### edge anchored anywhere in the file. Confirmed pre-existing on main (verified via a plain 'uv run frob check --only invariant' against main's own checkout, unrelated to any T-1094/T-1096 change) -- this file was introduced by T-1103's tickets/__init__.py split and never got an invariant binding or waiver. Bind a real invariant covering the claim, waive with a reason, or reword to drop the exclusivity language.

## Done report

Evidence-close only: the INV006 fix (frob:waive at src/frob/tickets/_new_renumber.py:15)
is already on main (c6c2ee55). Verified `frob check --only invariant --ticket T-1107`
passes with 0 errors, 0 warnings against the live file. Added a regression test,
TestInv006Gate.test_new_renumber_file_has_no_unanchored_exclusivity_claim, that copies
the real _new_renumber.py source into an isolated snapshot and asserts inv006_gate
returns zero violations -- proving the finding is gone from the actual file, not just
that a waiver line exists somewhere in it, and locking the regression going forward.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInv006Gate::test_new_renumber_file_has_no_unanchored_exclusivity_claim` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 511 warning(s), 426 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1108 -->
```yaml
id: T-1108
title: 'arch: extract remaining ~8 verb families from tickets/__init__.py (3489) and
  split tickets/_land.py (4762) -- T-1103 residue'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
acceptance:
- text: GIVEN the tickets package WHEN the remaining verb families (doable/leases/scope-breadth,
    scope mutation, field setters/sprint, evidence/transition, done-report/review/drop/attach)
    are extracted into per-family modules THEN tickets/__init__.py drops below 2000
    lines with no public API change and all existing tests pass
  evidence: []
- text: GIVEN tickets/_land.py at 4762 lines WHEN split into cohesive submodules (preflight,
    splice, verify, sweep families) THEN no single tickets/ module exceeds 2500 lines
    and LARGE001 no longer flags _land.py
  evidence: []
threat: null
component: null
```
T-1103 extracted archive + new/renumber families (tickets/__init__.py 4287->3489) and stopped on budget; per its done report the remaining ~8 families are doable/leases/scope-breadth, scope mutation, field setters/sprint, evidence/transition, done-report/review/drop/attach, and _land.py (4762 lines) was not touched. Continue the same extraction pattern: per-family private modules re-exported from __init__, zero behavior change, existing tests as the safety net. Beware the load-time circular import noted in T-1103's report (evidence family).

<!-- ticket:T-1109 -->
```yaml
id: T-1109
title: 'docs: DOC006 doc-pointer round-3 burn-down (~41 residual warnings after T-1015/T-1016)'
state: queued
kind: docs
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
acceptance:
- text: GIVEN a full frob check WHEN the doc gate runs THEN DOC006 reports zero unwaived
    warnings, with every fixed pointer resolving to a real heading slug and no matcher
    loosening
  evidence: []
threat: null
component: null
```
T-1015 (matcher hardening, 771->133) and T-1016 (round 2) left ~41 DOC006 doc-pointer warnings. Round 3: fix or reasoned-waive every residual site. No matcher/threshold loosening; follow T-1015's FP-class analysis before touching the matcher. Narrow scope to the real finding sites at start.

<!-- ticket:T-1110 -->
```yaml
id: T-1110
title: 'warnings: DEAD001/COV/REF edge burn-down (DEAD 32, COV 10, REF 10 unwaived)'
state: queued
kind: bug
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
acceptance:
- text: GIVEN a full frob check WHEN the dead/coverage/refs gates run THEN DEAD001,
    COV00x, and REF00x report zero unwaived warnings, each finding either root-fixed
    (dead code removed, edge bound) or waived with a grounded reason
  evidence: []
threat: null
component: null
```
Post-wave-16 residue: 32 DEAD001 dead-symbol warnings, 10 COV coverage-edge warnings, 10 REF reference warnings (unwaived, per gate summary). T-1024 precedent: DEAD001 13->0 and COV006 3->0 via real removals and edge bindings, not blanket waivers. Callgraph blind spots (cross-package privates, indexed-constant mutation) get confirmed-exercised waivers per the 3d574f3a precedent. Narrow scope to the real finding sites at start.

<!-- ticket:T-1111 -->
```yaml
id: T-1111
title: 'warnings: small-residue sweep to zero (DEPR 4, LANG 3, INV 2, REG 2, WAIVE
  2, WALK 2)'
state: queued
kind: bug
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
- frob.toml
acceptance:
- text: GIVEN a full frob check WHEN all gates run THEN the DEPR, LANG, INV, REG,
    WAIVE, and WALK families each report zero unwaived warnings
  evidence: []
threat: null
component: null
```
Endgame tail: the sub-five-warning families (DEPR003 x4, LANG003 x3, INV003/004 x2, REG009/REG010 x2, WAIVE004 x2, WALK001 x2 per gate summary). Fix or grounded-waive each. REG009/REG010 residue is the CPPTHROW001 check-coverage auto-sync gap noted at T-1042 land -- fold the registry entry fix here. Narrow scope at start.

<!-- ticket:T-1112 -->
```yaml
id: T-1112
title: 'arch: abstraction-opportunity check-registry-protocol detector exclusion'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
threat: null
component: null
```
Filed from T-1084 (triage of the 27 arch-package abstraction-opportunity
findings T-1067 handed off). After reading every one of the 27 groups'
member bodies (not just names), none warrant a manual extraction inside
`src/frob/arch/` -- they split into recognizable, already-reviewed shapes
the detector cannot yet tell apart from a real missing abstraction:

1. The check-function registry protocol itself: `_exceptions.py`'s 27-
   member `(NormalizedModule) -> list[ArchSuggestion]` group is not a
   coincidence -- it is literally every `check_*` detector across the
   whole `frob.arch` package (33 functions match `^def check_` under
   `src/frob/arch/*.py`; ~27 of them share the exact bare signature, the
   handful of others take an extra param). This is the package's own
   intentional common interface (every detector module registers this
   way), not duplicate logic to extract -- the exact same "protocol
   family" shape as T-0360's `_is_dispatch_family`/T-1068's language-tag
   exclusion already carve out for other signature-collision classes,
   just not yet generalized to "every function whose name matches
   `^check_` (or another package-wide naming convention) is exempt from
   this category, regardless of arity."
2. Per-construct mirrored builders: `_typescript.py`'s
   `_ts_build_class`/`_ts_build_interface`/`_ts_build_enum` (and the
   `_kotlin.py`-anchored cross-language equivalents T-1068 already
   partially covers) build genuinely DIFFERENT tree-sitter node types
   (`class_declaration` vs `interface_declaration` vs `enum_declaration`)
   into the same `NormalizedClass` return type -- distinct concerns that
   happen to share a return type, not one duplicated function.
3. Deliberately-kept-separate trivial one-liners: `_mayraise.py`,
   `_fallibility.py`, and `_exceptions.py` each define their own
   byte-identical `_bare_callee_name(callee: str) -> str`, and each
   docstring explicitly cross-references the sibling copy ("same
   convention as `frob.arch._fallibility._bare_callee_name`") -- a prior
   ticket (T-0686) already reviewed this exact tradeoff for the sibling
   `_qualname` duplicate and chose to keep the modules independent rather
   than share a one-line private helper across otherwise-unrelated check
   families. Re-deduplicating now would reverse that reviewed decision
   without a new instruction to do so.
4. Large mixed-concern groups (`_async_hazards.py`'s 32-member
   `(Node) -> bool` group, `_concurrency_model.py`'s 27-member
   `(Node) -> str | None` group, etc.): genuinely unrelated tree-walk
   predicates/extractors that only coincide on a common, very generic
   tree-sitter-node signature shape -- the class-1 "coincidental
   collision" case the parent ticket's own body already anticipated.

Add a `_is_check_registry_family` (or similarly named) exclusion to
`frob.arch._python._check_abstraction_opportunities` alongside
`_is_dispatch_family`/`_is_language_parity_family`: a same-signature group
is exempt when every member's bare name matches the package's own
detector-naming convention (`^check_[a-z_]+$`, mirroring how
`_is_dispatch_family`/`_is_language_parity_family` are both purely
name/structure-based, never raw text proximity). Re-measure
`abstraction-opportunity` count after landing and confirm the drop is
exactly the check-registry groups, mirroring T-1068's own before/after
methodology.

<!-- ticket:T-1113 -->
```yaml
id: T-1113
title: 'strata: promote SYS104/105/106 to mandatory + add CHK-GATE-SYS104/105/106
  registry entries'
state: queued
kind: security
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- docs/design/registry/check-coverage.yaml
- src/frob/strata/_selfconform.py
threat: null
component: null
```
SYS104 (T-0668, src/frob/strata/_selfconform.py) only evaluates a node
that has already declared at least one `interface=` attr -- an opt-in
scope cut, disclosed in T-0668's Done report, because making it
mandatory repo-wide would require adding `interface=` declarations to
`design/frob.strata`, which was outside T-0668's declared scope
(`src/frob/strata/**`, `src/frob/graph/**`, `docs/modules/strata.md`,
`tests/unit/strata/**` -- not `design/frob.strata`).

Two follow-ups bundled here (same shape as SYS103's own T-1079-class
deferred work):
1. Add real `interface=` declarations to `design/frob.strata`'s nodes
   (measured against each node's actual public surface,
   `_module_public_symbols`), then flip SYS104 to fire on ANY node
   whose bound code has a public symbol, not just opt-in nodes.
2. Add `CHK-GATE-SYS104`/`CHK-GATE-SYS105`/`CHK-GATE-SYS106` entries to
   `docs/design/registry/check-coverage.yaml` and the corresponding
   `frob:enforces` directives on `check_self_conformance`, mirroring the
   `CHK-GATE-SYS103` precedent (T-0667's Done report's own deferred
   registry gap, `docs/modules/strata.md#known-gap-registry-cross-
   reference`) -- `docs/design/registry/**` was outside T-0668/T-0669/
   T-0670's declared scope.

<!-- ticket:T-1114 -->
```yaml
id: T-1114
title: 'arch: abstraction-opportunity gates package extraction (T-1082 remainder)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/
threat: null
component: null
```
Filed from T-1082's partial land: T-1082 consolidated the cross-cutting
`_tracked_files`/`git ls-files` duplicate (5 gate modules --
_opaque.py, _exclude_hazard.py, _refs.py, _secrets.py,
_cve_fingerprint_scan.py -- each defining a byte-for-byte identical
private helper) into one shared `frob.gates._tracked_files.tracked_files`
and inlined every call site, clearing that specific abstraction-
opportunity cluster entirely. It did NOT attempt the remaining 29
findings T-1082 was filed to cover (19 in gates/__init__.py, 1 each in
_baseline.py, _cve_fingerprint_scan.py, _docblocks.py,
_fmt_directives.py, _gate_cache.py, _waive.py/_waive_lease.py,
invariants.py, 3 in _pii_structural.py), nor the wider
`_tracked_python_files`-shaped duplication T-1082 named as likely
undercounted (_walk_lint.py, _pii_structural/_tracked.py, _docblocks.py,
_docptr.py all define their own git-ls-files-with-suffix-filter variant),
nor the new small cluster the consolidation itself introduced (the new
`frob.gates._tracked_files.tracked_files` now shares a `(Path, str) ->
tuple[str, ...]` signature with 4 functions in
src/frob/dup/_pipeline/_callgraph.py -- out of gates/ scope entirely).

Re-measure `uv run frob check --only arch --json` scoped to
`src/frob/gates/` before starting; other tickets may have landed in the
interim and changed the count from the 29 this ticket, and its
predecessor T-1082, were filed against.

<!-- ticket:T-1115 -->
```yaml
id: T-1115
title: 'arch: split remaining ~14 gate families out of src/frob/gates/__init__.py
  (~9802 lines) -- T-1077 residue refile'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
acceptance:
- text: GIVEN src/frob/gates/__init__.py WHEN the remaining gate families (DEBT/DEPR,
    SCOPE/PREWORK, INV00x, TEST00x, DECISIONS, TICK00x, COMPLIANCE00x, SYS00x/DOC00x,
    DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates spine, COV00x) are
    extracted one cohesive family per land THEN gates/__init__.py drops below the
    800-line large-file threshold with no public API change and all existing tests
    pass
  evidence: []
threat: null
component: null
```
Refile of T-1077's residue draft, which died at land (TICK006 phantom repaired by the coordinator). T-1077 extracted the TODO00x/FMT001 family (gates/__init__.py 10164 -> ~9802); the remaining families follow T-1072/T-1077's one-family-per-land discipline: verbatim moves with directives intact, lazy call-time imports back to frob.gates where init-time circularity threatens, re-export only externally-called names, split-carried INV006 waivers where prose moves.

<!-- ticket:T-1116 -->
```yaml
id: T-1116
title: 'test: test_every_deferred_entry_targets_an_open_ticket fails, zero deferred
  entries exist in weaknesses.yaml'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
threat: null
component: null
```
Found while working T-1037: tests/test_registry_reconciliation_weaknesses.py
::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_
ticket fails on current main with:

  AssertionError: expected at least one deferred entry to check against

docs/design/registry/weaknesses.yaml currently has ZERO entries whose
disposition.kind is DispositionKind.DEFERRED (confirmed via direct grep
and via _load_weaknesses()/DispositionKind filtering in the test itself).
Either every previously-deferred entry has since been resolved to
checkable/duplicate-of/out-of-scope (in which case the test's own
precondition assertion is now stale and should be relaxed to skip rather
than fail when the deferred set is legitimately empty), or a deferred
entry was dropped/miscategorized somewhere along the way and the test is
correctly catching a real regression -- needs investigation to tell
these apart before deciding the fix.

Out of T-1037's declared scope (that ticket is specifically about REG011
out_of_scope-reason substantive-disclosure, already independently fixed
by T-1019 before this wave started -- confirmed zero REG011 violations
and the ticket's own named regression test passing on current main).

<!-- ticket:T-1117 -->
```yaml
id: T-1117
title: 'test: test_every_deferred_entry_targets_an_open_ticket fails, zero deferred
  entries exist in weaknesses.yaml'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
threat: null
component: null
```
Found while working T-1037: tests/test_registry_reconciliation_weaknesses.py
::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_
ticket fails on current main with:

  AssertionError: expected at least one deferred entry to check against

docs/design/registry/weaknesses.yaml currently has ZERO entries whose
disposition.kind is DispositionKind.DEFERRED (confirmed via direct grep
and via _load_weaknesses()/DispositionKind filtering in the test itself).
Either every previously-deferred entry has since been resolved to
checkable/duplicate-of/out-of-scope (in which case the test's own
precondition assertion is now stale and should be relaxed to skip rather
than fail when the deferred set is legitimately empty), or a deferred
entry was dropped/miscategorized somewhere along the way and the test is
correctly catching a real regression -- needs investigation to tell
these apart before deciding the fix.

Out of T-1037's declared scope (that ticket is specifically about REG011
out_of_scope-reason substantive-disclosure, already independently fixed
by T-1019 before this wave started -- confirmed zero REG011 violations
and the ticket's own named regression test passing on current main).

<!-- ticket:T-1118 -->
```yaml
id: T-1118
title: 'daemon: wire run_coverage_wait through the T-1097 daemon-owned coverage lease'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_wait.py
- src/frob/app/_daemon_proxy.py
threat: null
component: null
```
T-1097 shipped a daemon-owned named resource lease/semaphore primitive
(frob.serve._leases.ResourceLeaseManager, frob_lease_acquire/frob_lease_
release RPC methods) with connection-liveness release, proven against
real socket clients directly.

It did NOT rewire frob.testing._coverage_wait.run_coverage_wait's own
subprocess flow to acquire the coverage lock THROUGH this daemon RPC
instead of its existing file-lock layers (T-0322's per-worktree
fcntl.flock, T-1095's shared per-digest fcntl.flock) -- that wiring
touches frob.app's CLI-proxy layer (_daemon_proxy.query), which was
contended with T-1106's own src/frob/app/ work this wave and out of
T-1097's src/frob/serve/**/src/frob/testing/** scope.

Follow-on: wire run_coverage_wait (or a new coverage-specific daemon
client call) to acquire/release the "coverage" resource lease via the
daemon RPC when a daemon is reachable, falling back to the existing
file-lock layers when it is not -- mirroring frob.app._daemon_proxy.
query's own Ok(daemon)/Err(fallback) shape.

<!-- ticket:T-1119 -->
```yaml
id: T-1119
title: 'gates: TICK006 phantom draft citations from T-1077/T-1084 Done reports'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
threat: null
component: null
```
frob check reports TICK006 phantom-filing-trail errors for T-1077 and
T-1084: both Done reports cite T-draft-a418305e / T-draft-372a1425 as
filed follow-on tickets, but neither draft resolves to a real block in
tickets.md or tickets-archive.md -- the classic T-0707/T-0615 draft-loss
incident class (a worktree's draft ticket getting wiped by the section
10b tickets.md restore recipe before the citing Done report landed).
Found incidentally while landing T-1095 (unrelated ticket); not this
ticket's scope to fix. Resolve by either re-filing the real ticket each
Done report meant to cite and correcting the citation, or adding an
honest frob:waive TICK006 noting the historical draft loss if the
underlying work is otherwise already covered.

<!-- ticket:T-1120 -->
```yaml
id: T-1120
title: 'test: test_every_deferred_entry_targets_an_open_ticket fails, zero deferred
  entries exist in weaknesses.yaml'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
threat: null
component: null
```
Found while working T-1037: tests/test_registry_reconciliation_weaknesses.py
::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_
ticket fails on current main with:

  AssertionError: expected at least one deferred entry to check against

docs/design/registry/weaknesses.yaml currently has ZERO entries whose
disposition.kind is DispositionKind.DEFERRED (confirmed via direct grep
and via _load_weaknesses()/DispositionKind filtering in the test itself).
Either every previously-deferred entry has since been resolved to
checkable/duplicate-of/out-of-scope (in which case the test's own
precondition assertion is now stale and should be relaxed to skip rather
than fail when the deferred set is legitimately empty), or a deferred
entry was dropped/miscategorized somewhere along the way and the test is
correctly catching a real regression -- needs investigation to tell
these apart before deciding the fix.

Out of T-1037's declared scope (that ticket is specifically about REG011
out_of_scope-reason substantive-disclosure, already independently fixed
by T-1019 before this wave started -- confirmed zero REG011 violations
and the ticket's own named regression test passing on current main).

<!-- ticket:T-1121 -->
```yaml
id: T-1121
title: 'test: test_every_deferred_entry_targets_an_open_ticket fails, zero deferred
  entries exist in weaknesses.yaml'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
threat: null
component: null
```
Found while working T-1037: tests/test_registry_reconciliation_weaknesses.py
::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_
ticket fails on current main with:

  AssertionError: expected at least one deferred entry to check against

docs/design/registry/weaknesses.yaml currently has ZERO entries whose
disposition.kind is DispositionKind.DEFERRED (confirmed via direct grep
and via _load_weaknesses()/DispositionKind filtering in the test itself).
Either every previously-deferred entry has since been resolved to
checkable/duplicate-of/out-of-scope (in which case the test's own
precondition assertion is now stale and should be relaxed to skip rather
than fail when the deferred set is legitimately empty), or a deferred
entry was dropped/miscategorized somewhere along the way and the test is
correctly catching a real regression -- needs investigation to tell
these apart before deciding the fix.

Out of T-1037's declared scope (that ticket is specifically about REG011
out_of_scope-reason substantive-disclosure, already independently fixed
by T-1019 before this wave started -- confirmed zero REG011 violations
and the ticket's own named regression test passing on current main).
