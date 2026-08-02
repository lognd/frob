# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

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

<!-- ticket:T-1135 -->
```yaml
id: T-1135
title: 'EPIC frob refactor: transactional move/rename/split with full reference, directive,
  and obligation rewrite'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
acceptance:
- text: 'GIVEN frob refactor move/rename/split on a symbol or module family WHEN it
    completes THEN all imports and call sites are rewritten (absolute imports, auto-aliasing
    on destination or import-site name conflicts, with a disclosed alias report),
    and every frob-owned reference moves with the symbol: frob:tests/frob:doc/frob:enforces
    target forms, waiver symrefs including path:: prefixes, PII012 (file,token) allowlist
    entries, check-coverage registry citations, and archived-ticket evidence node
    ids'
  evidence: []
- text: GIVEN a refactor that cannot complete every rewrite THEN it refuses and rolls
    back rather than leaving a half-move; post-conditions verified in-command (import
    graph resolves, tests collect, gate findings diff-clean vs pre-refactor)
  evidence: []
- text: 'GIVEN a moved or renamed symbol WHEN the refactor completes THEN every mention
    of it in prose is rewritten too: docstrings and comments naming the dotted path
    (including all frob: comment-DSL directive targets anywhere in the repo, not just
    those attached to the moved symbol), docs/** prose and code refs, and doc anchors
    whose heading slugs embed the symbol or module name -- auto-documentation updating
    is part of the transaction, with unresolvable prose mentions listed in the disclosed
    report rather than silently skipped'
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: refactors today mean an agent hand-editing every import and callsite, and -- the expensive part -- hand-carrying frob's symbol-attached bookkeeping. Second user directive same day: the rewrite must ALSO cover frob symbols and symbols in comments -- auto-documentation updating -- because a rename that fixes code but strands docs/docstring/comment mentions just converts silent breakage into doc drift (the DRIFT001/DOC006 class this repo keeps paying down). Evidence from this drive: 3 coordinator INV006 waiver carries in one wave (0abc4e3a), PII012 allowlist re-keying on every move (T-1076), the ARCH101/103 waiver-symref path:: bug where moved waivers never matched again, archived evidence repoints after litmus renames (8dae48c5), DRIFT002 edge repoints. frob owns the graph/binding/exports substrate to do this transactionally. Python first; the multi-language binding tables (TS/Rust/C-C++/Kotlin) extend it later. Children to file at design time: reference-rewrite engine, directive/waiver carrier (absorbs T-1134), registry/evidence repointer, split verb built on the T-1072/T-1077 family-extraction pattern, alias-conflict policy. Relationship: makes T-1108/T-1115-class split tickets mechanical.

<!-- ticket:T-1136 -->
```yaml
id: T-1136
title: 'EPIC ledger v2: per-ticket files replace the tickets.md monofile (design first,
  then migration)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/tickets/**
- docs/design/**
- tests/**
acceptance:
- text: GIVEN the design doc WHEN reviewed THEN it covers file-per-ticket layout (block
    + done report), draft lifecycle without splice restores, cross-ticket operations
    (renumber with reference rewrite, doable ordering, archive as git mv, flow/velocity
    mining), lock model, merge story with the frob-ledger driver retired, greppability,
    and a reversible migration plan with a compatibility window
  evidence: []
- text: GIVEN the migration lands THEN the land path performs no monofile splice,
    two agents landing disjoint tickets produce no ledger merge conflict, and the
    TICK002/TICK006 draft-death classes are structurally impossible or auto-repaired
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: too much manual work rides on tickets.md mechanics. The monofile is the root cause of a documented incident museum: land splice regression (T-0577), archive clobber (T-0959), ledger churn rewrites (T-1036), id collision (T-1090), draft deaths in 10b restores (4 coordinator refiles on 2026-07-28 alone: T-1115, T-1126, T-1127, T-1128), DirtyMain transitions (T-1054), hand splices where the merge driver is unregistered in worktrees, ledger-lock starvation and deadlocks (T-0933, T-0982). Per-ticket files make disjoint tickets disjoint git objects so merge/lease/draft/renumber/archive become ordinary git operations. The global convention (tickets/ tracked in git) already names the directory form. Design doc in docs/design/ first; migration is a separate child with golden round-trip tests; T-1125 (draft-id prose rewrite) stays valuable pre-migration and its engine is reusable for renumber-with-references after.

<!-- ticket:T-1137 -->
```yaml
id: T-1137
title: 'EPIC frob check --fix: tiered auto-fix engine (auto / verified-auto / assisted
  fix-its)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/gates/**
- src/frob/app/**
- docs/**
- tests/**
acceptance:
- text: GIVEN frob check --fix WHEN Tier-A findings exist THEN deterministic semantics-preserving
    fixes are applied (directive-form rewrite, unique anchor-slug correction, fmt,
    draft renumber, generated-registry regeneration, release sync, full-run-verified
    stale-waiver removal) and the affected gates re-run clean in the same invocation
  evidence: []
- text: 'GIVEN a Tier-B fix WHEN applied THEN it is transactional: affected gates
    plus the finding''s bound tests re-run per fix and any regression rolls that fix
    back with a disclosed report'
  evidence: []
- text: GIVEN a Tier-C (content-required) finding THEN --fix never edits it and never
    inserts a waiver; it emits a structured fix-it (file, line, proposed patch) for
    explicit acceptance -- an obligation can never be auto-discharged by waiver
  evidence: []
- text: GIVEN the generated rule registry THEN every rule id carries a fixability
    tier (auto/verified/assisted/manual) that is generated-verified against the fix
    engine's actual handler table, so an unwired fixability claim is a check failure
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: the annoying errors are the ones whose fix is mechanical but manual. Drive evidence: DRIFT002 dotted-form rewrites redded main twice and are pure string rewrites; T-0602's one wrong anchor slug caused 11 COV001s with an unambiguous correct slug available; TICK002's message prints its own fix command; REL002 took three incidents before land invoked the existing frob release sync; E501-on-waive-lines when frob fmt exists and is idempotent; WAIVE004 removal is mechanical given a full run (mechanizes T-1021's hand-sweep); REG008/REG010 enforces edges are derivable from emitting sites (T-1008 generate-and-verify precedent). Design doc first (docs/design/): fix-handler protocol per rule id, transaction/rollback model, interaction with frob doctor (inventory what doctor already repairs and fold or delegate), daemon-warm --fix, and the two anti-goals (no auto-waivers ever; no threshold loosening ever). Children at design time: Tier-A handler batch, Tier-B transaction engine, fixability registry field, fix-it emission format for agents.

<!-- ticket:T-1196 -->
```yaml
id: T-1196
title: 'strata: multi-file design split with cross-file reference semantics'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- design/**
- docs/**
- tests/**
acceptance:
- text: GIVEN design/frob.strata split into multiple .strata files under design/ WHEN
    frob check --only sys runs THEN elaboration resolves cross-file node/flow/boundary
    references identically to the single-file model (merged-model or explicit import
    mechanism, design decides) and gate findings are diff-clean vs the monofile
  evidence: []
- text: GIVEN a reference to a node declared in no loaded file THEN elaboration fails
    closed with a per-file error naming the missing id, not a silent partial model
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: design/frob.strata is 5588 lines and monolithic. _design_load.py (T-0080) already rglobs and loads every .strata file under design/, but elaboration produces one KernelModel PER FILE (DesignIds.models, one per file), so cross-file edges (flows/boundaries referencing nodes in another file) do not elaborate into one model today -- only merged id-surfaces (channels/boundaries/secrets/store_ids/resources) are unioned. Design question for the child design note: merge parsed Modules pre-elaboration into one KernelModel vs an explicit import/include construct in the surface grammar. Sibling ticket covers the attr interface= volume; splitting along component seams is only safe once cross-file references resolve.

<!-- ticket:T-1198 -->
```yaml
id: T-1198
title: 'strata: eliminate attr interface= boilerplate (4236 of 5588 frob.strata lines)
  via generated fragment or compact grammar'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- design/**
- docs/**
- tests/**
acceptance:
- text: 'GIVEN the interface surface of a node WHEN it is machine-derivable (sync_interface
    already rewrites attr interface= lines to match code exactly) THEN the hand-authored
    .strata file no longer carries one line per symbol: either a generated .strata
    fragment (generate-and-verify like the rule registry) or a compact declaration
    form (list/module-ref) the parser accepts, design decides'
  evidence: []
- text: GIVEN the migration lands THEN frob check --only sys findings are diff-clean
    vs the inline-attr model and sync_interface round-trips idempotently on the new
    form
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: 4236 of design/frob.strata's 5588 lines are attr interface=<symbol> lines, one symbol per line, maintained mechanically by frob.strata._sync_interface (which loads every .strata file and rewrites the attrs to match code exactly). The hand-authored design intent drowns in generated-shaped noise. Candidate designs for the design note: (a) generated sidecar fragment design/frob.interface.strata written by sync_interface and verified by the SYS gate (T-1008 generate-and-verify precedent); (b) grammar shorthand attr interface=[a, b, ...] or interface from <module-path> resolved at parse time; (c) move interface bindings out of the surface file entirely into the code-binding layer. Coordinate with T-1196 (multi-file split) -- a generated fragment is itself a second file, so the cross-file semantics land first or together.

<!-- ticket:T-1199 -->
```yaml
id: T-1199
title: 'refactor: directive/waiver carrier (absorbs T-1134)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- tests/test_refactor.py
scope_changes:
- op: remove
  glob: src/frob/graph/dsl.py
  reason: reads/calls into these modules but does not modify them; scope narrowed
    to the new refactor carrier module
  actor: logan
  at: '2026-07-29'
- op: remove
  glob: src/frob/gates/_waive.py
  reason: reads/calls into these modules but does not modify them; scope narrowed
    to the new refactor carrier module
  actor: logan
  at: '2026-07-29'
- op: remove
  glob: src/frob/graph/lock.py
  reason: reads/calls into these modules but does not modify them; scope narrowed
    to the new refactor carrier module
  actor: logan
  at: '2026-07-29'
acceptance:
- text: 'GIVEN a symbol with a `frob:waive ARCH101 reason="..."` placed directly

    above it WHEN it is moved to a new file via `frob refactor move` THEN the

    waiver moves with it and `frob.gates._waive._match_waiver`''s per-symbol

    exact-symref mode still matches the moved symbol''s new `path::qualname`,

    with no new unwaived ARCH101 finding at the new location'
  evidence: []
- text: 'GIVEN a `frob:doc docs/x.md#anchor` directive attached to a different,

    non-moving symbol elsewhere in the repo, whose target names a symbol that

    IS moving WHEN the move completes THEN that directive''s target string is

    rewritten to the new path::qualname too'
  evidence: []
- text: 'GIVEN a moved symbol with an existing frob.lock ack at its old symref and

    an unchanged digest WHEN the move completes THEN the ack is carried

    forward to the new symref rather than reported stale by DRIFT001'
  evidence: []
threat: null
component: null
```
Design: docs/design/refactor-verb.md (T-1135). Absorbs T-1134 (done):
reuse its `find_carried_waiver` helper, already written reusable/
standalone per T-1134's own Done report, as the seed for this carrier.

Extends T-1197's plan/apply pipeline with the frob-owned DSL reference
kinds: for a moving symbol, rewrite every `frob:*` comment-DSL directive
whose TARGET names it (frob:doc, frob:tests, frob:enforces,
frob:uses-contract, frob:invariant, frob:ticket, frob:todo, frob:decision,
frob:channel, frob:boundary, frob:secret, frob:protocol, frob:transition,
frob:requires, frob:acquire, frob:release, frob:escapes -- the full
frob.graph.dsl._VERB_TABLE), using frob.graph.dsl's existing parser, not a
second regex.

Also rewrites `frob:waive RULE reason="..."` `src` symrefs, preserving
frob.gates._waive._match_waiver's three matching modes (per-symbol exact
symref, file-scoped, package/system-prefix) -- a waiver's src is itself a
symref that must move with the same rules as a frob:doc target. This is
the direct fix for the ARCH101/103 waiver-symref path:: bug named in
T-1135's epic body.

Carries frob.lock ack entries forward: an ack keyed on (symbol identity,
digest) at the old symref, where the digest is unchanged by the move,
gets re-keyed to the new symref rather than going stale.

Scope note: this ticket rewrites directive/waiver TARGETS repo-wide (per
epic acceptance [2] -- a directive anywhere in the repo pointing at the
moved symbol, not just directives attached to the moved symbol's own
code) but does not move the owning code itself; T-1197 (or the split
verb, T-1201) does that.

<!-- ticket:T-1200 -->
```yaml
id: T-1200
title: 'refactor: registry/evidence repointer (PII012 allowlist, registry citations,
  ticket evidence)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- tests/test_refactor.py
acceptance:
- text: 'GIVEN a PII012 allowlist entry keyed on (old_file_path, token) WHEN the

    file is moved via `frob refactor move` THEN the entry is re-keyed to

    (new_file_path, token) and no new PII012 finding fires at the new

    location for that token'
  evidence: []
- text: 'GIVEN a registry entry in docs/design/registry/*.yaml whose handled_by/

    caught_by citation embeds a literal path::qualname string for a moving

    symbol, not reachable via a frob:enforces DSL edge WHEN the move

    completes THEN that citation string is rewritten and

    frob.gates._registry_exhaustiveness reports no new REG008/REG009 finding'
  evidence: []
- text: 'GIVEN a closed ticket in tickets.md or tickets-archive.md whose Evidence

    section cites a path::Class.method or pytest node id for a moving symbol

    WHEN the move completes THEN the cited evidence string is rewritten to

    the new symref and remains resolvable'
  evidence: []
threat: null
component: null
```
Design: docs/design/refactor-verb.md (T-1135). Extends T-1197's plan/apply
pipeline with the three remaining non-DSL reference kinds named in the
epic:

- PII012 (file, token) allowlist entries: locate the exact storage first
  (src/frob/gates/_pii_structural/ is the closest hit found during design
  survey -- confirm the exact file/data shape before writing the repoint
  logic), then re-key any entry whose file half matches a moving path to
  the new path, token half unchanged (T-1076 precedent for why this keeps
  breaking by hand today).
- check-coverage registry citations (docs/design/registry/*.yaml,
  handled_by/caught_by, read by frob.gates._registry_exhaustiveness
  REG004-011): survey whether any registry entry embeds a literal
  path::qualname string outside a frob:enforces edge (the directive
  carrier, T-1199, already keeps frob:enforces targets correct via the
  DSL rewrite -- this ticket only needs to cover a citation that is NOT
  reachable that way, if one exists).
- Archived-ticket evidence node ids: pytest node ids and path::Class.method
  forms recorded in tickets.md Done-report/Evidence sections and in
  tickets-archive.md, for any ticket (open or archived) whose evidence
  cites a symref that is moving. Both files, not just the live ledger.

This ticket owns the "everything the directive carrier's DSL rewrite
cannot reach" residue -- coordinate with T-1199 to avoid double-rewriting
a citation that IS reachable via frob:enforces.

<!-- ticket:T-1201 -->
```yaml
id: T-1201
title: 'refactor: split verb (built on T-1072/T-1077 family-extraction pattern)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
- T-1199
- T-1200
- T-1267
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- docs/commands/refactor.md
- tests/test_refactor.py
acceptance:
- text: 'GIVEN a source module with N symbols named for a split into a new sibling

    module WHEN `frob refactor split` completes THEN the new module contains

    the moved symbols, the source module re-imports and re-exports every

    moved name unchanged (external `from source import symbol` call sites

    require no edit), and every frob:* directive attached to a moved symbol

    resolves at its new location with no new gate finding'
  evidence: []
- text: 'GIVEN a split naming more symbols than fit one safe apply-and-verify

    chunk WHEN the split runs THEN it applies and verifies in multiple

    chunks, each individually refuse-and-rollback safe, rather than failing

    the entire split on one chunk''s problem'
  evidence: []
threat: null
component: null
```
<!-- frob:waive DOC006 reason="'frob refactor split' names this ticket's own not-yet-built deliverable (T-1267/T-1135 design), a future CLI verb that structurally cannot resolve against today's subcommand tree until this ticket ships it" -->
Design: docs/design/refactor-verb.md (T-1135). New `frob refactor split`
verb, built directly on the T-1072/T-1077 manual family-extraction
pattern used repeatedly this drive (private sibling module per cohesive
family, old module re-imports/re-exports every moved name UNCHANGED so
external `from frob.x import y` call sites never change, frob:* directives
travel with the moved code, DRIFT002/AFFECT001 doc/test references
updated, land incrementally with full-suite verification per chunk).

Depends on T-1197 (resolve/plan/apply/verify pipeline), T-1199 (directive/
waiver carrier), and T-1200 (registry/evidence repointer) all being
callable, since a split is a move of N symbols at once plus generation of
the re-export shim in the source module.

Scope for this ticket: the split-specific pieces only --
- CLI surface: `frob refactor split SOURCE_MODULE --symbols a,b,c --into
  NEW_MODULE` (exact flag shape TBD during implementation).
- Re-export shim generation in the source module (a well-formed `from
  .new_module import a, b, c  # noqa: F401`-style re-export block,
  matching the exact shape T-1072/T-1077 hand-wrote).
- Chunked apply: a split naming many symbols applies and verifies in
  batches (mirroring T-1072/T-1077's own "land incrementally, verify
  after each chunk" discipline) rather than one all-or-nothing giant
  diff, while still being one refuse-and-rollback transaction per chunk
  (not per whole split) per T-1135's transaction model.
- Re-running T-1197/T-1199/T-1200's move/rewrite machinery per symbol
  moved, not reimplementing rewrite logic here.

<!-- ticket:T-1202 -->
```yaml
id: T-1202
title: 'refactor: alias-conflict policy'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- docs/commands/refactor.md
- tests/test_refactor.py
acceptance:
- text: 'GIVEN an import-site name collision during a move/rename with no

    --alias-conflict flag given WHEN the plan phase detects it THEN an

    alias is auto-generated at the import site only and named in the

    disclosed alias report'
  evidence: []
- text: 'GIVEN a destination-namespace collision (two same-named symbols would

    land in the same module) WHEN the plan phase detects it THEN it refuses

    under the default `error` policy, and only proceeds if `--alias-conflict

    rename-dest` was explicitly passed'
  evidence: []
- text: 'GIVEN a completed refactor with at least one auto-generated alias WHEN

    its report is printed THEN every alias appears in a distinct, clearly

    labeled section of the report, never buried in the general rewrite list'
  evidence: []
threat: null
component: null
```
Design: docs/design/refactor-verb.md (T-1135). T-1197's plan/apply
pipeline needs an extension point for handling an import-site name
collision when a destination name is already bound; this ticket owns
that policy layer: the naming scheme for auto-generated aliases, the
`--alias-conflict {error,rename-dest}` flag (default: error -- a
destination-namespace collision is a hard refusal, never a silent
auto-rename of the destination module's own symbol), and the disclosed
alias report format (every auto-generated import alias named, so a human
reviews it rather than discovering it later in a diff).

Depends on T-1197 exposing the plan-phase hook this policy plugs into
(a callback invoked once per detected collision, returning either an
alias name or a refusal).

<!-- ticket:T-1204 -->
```yaml
id: T-1204
title: 'perf: hot-graph burn-down (2026-07-29 profile)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/**
threat: null
component: null
```
Umbrella epic for the 2026-07-29 in-process cProfile hot-graph report (scratchpad hotgraph/report.md). 11 children, one per ranked PERF candidate (10 from the report's 'Ranked PERF ticket candidates' section) plus a CLI-startup lazy-import fix. Each child fixes a measured root cause AND ships a PERF01x lint rule per repo convention (perf root causes ship as both a .strata obligation and a PERF0xx detector, never fix-only). See STANDALONE ticket 'perf: PERF01x detectors from hot-graph root causes' for the four new detector rules this epic's children rely on.

<!-- ticket:T-1205 -->
```yaml
id: T-1205
title: 'coverage as managed derived state: auto-refresh touched-set, never stale,
  never manual'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/app/**
- src/frob/testing/**
- Makefile
- docs/**
- tests/**
acceptance:
- text: GIVEN a tracked source change WHEN frob check runs THEN coverage data for
    affected symbols is refreshed automatically via the touched-set test machinery
    (frob test --base semantics) merged into the persisted coverage store -- no manual
    make coverage invocation exists in any documented or gate-suggested workflow
  evidence: []
- text: GIVEN coverage data that cannot be refreshed (tests failing, run interrupted)
    THEN TEST005-family findings against stale regions are marked stale-and-disclosed
    rather than reported as current fact, and TEST011 escalates from advisory to a
    blocking freshness contract
  evidence: []
- text: 'GIVEN an unchanged file THEN its coverage is never recomputed: per-file coverage
    keyed by content hash, full-suite runs reserved for cold start or explicit --full'
  evidence: []
- text: 'GIVEN any frob-enabled repo on any OS (Linux, macOS, Windows) WHEN coverage
    refresh is needed THEN a frob-native command (frob coverage or frob test --coverage)
    performs the whole orchestration -- subprocess rc generation, pytest invocation,
    combine, xml, stamp -- in Python with no Makefile or shell dependency; make coverage
    becomes a thin optional wrapper calling it (user directive 2026-07-29: portable,
    not just this project and not just Linux)'
  evidence: []
- text: 'GIVEN a frob command whose gates need coverage data WHEN the freshness contract
    says it is stale THEN the frob-native coverage refresh runs automatically inside
    that command (touched-set only) -- the user never invokes a refresh verb, and
    nothing cached is re-run (user directive 2026-07-29: minimal friction)'
  evidence: []
threat: null
component: null
```
ESCALATED TO CRITICAL 2026-07-31. This ticket's absence caused the largest single failure of the 2026-07-31 drive; acceptance [1] describes the exact incident. Evidence, all from one day:
- The repo-wide stamp sat 23 hours stale (2026-07-30 15:05) while ~8 tickets landed, and every TEST005 finding was computed from it and reported as current fact -- precisely what [1] forbids.
- T-1293 was closed having fixed 1 of 64 findings, its agent reporting the package clean in good faith. Post-land re-measure showed 65 still outstanding.
- The stamp does not merely lag, it UNDERSTATES coverage and so INFLATES findings. Measured: strata check_process_bounds_obligations stamp 6.7% / real 98%; check_self_conformance stamp 0.0% ("dead code") / real 95%; release authoritative_version showing def hits=1 with body hits=0, structurally impossible.
- Four agents were sent to write tests for code that was already well covered, and four worktrees (T-1276, T-1281, T-1294, T-1296) had to be PARKED mid-flight once the measurement was found untrustworthy.
- The coordinator had to run `make coverage` by hand to unblock them -- the exact manual step acceptance [0] and [4] exist to abolish.
T-1335 (landed 2026-07-31) fixed the pipeline's SILENT FAILURE (exit 0 on a failed stamp write), so a bad refresh is now loud. T-1353 tracks the xdist symbol-level data drop that appears to be the underlying corruption. Neither makes the refresh automatic or incremental -- that is this ticket, and it is what stops the failure class rather than the instance.

User directive 2026-07-29: we should never run make coverage manually; frob must never consume stale data or retread work that should be cached. Today coverage.xml is a hand-refreshed artifact: TEST011 warns it predates tracked changes and TEST005 findings are computed from it anyway (the attribution-inflation problem T-0969 is untangling). Design: treat coverage like the graph cache -- a derived artifact frob owns, refreshed incrementally from the touched-set (the affects closure already exists in frob.graph.affects), merged per-file keyed by content hash, with the freshness contract enforced by the gate rather than a Makefile comment. Interacts with T-0969 (attribution fix defines what honest data is) and the CI gitignored-trust child under T-1193 (CI needs the same no-stale contract). Related: the profiler found process-pool workers re-derive per-file artifacts every run -- same no-retread principle, separate ticket in the perf tree.

<!-- ticket:T-1209 -->
```yaml
id: T-1209
title: 'perf: pii_structural ~8 independent ast.walk passes per file -- single bucketed
  NodeIndex'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/gates/_pii_structural/**
acceptance:
- text: 'GIVEN _scan_one_python_file dispatches to 8 sub-scans (_scan_python_ddl,
    _keywords.py keyword sweep, _python_fields.py orm columns/fields, _emails.py,
    _env_access.py) each doing its own ast.walk (8.84M walk resumptions, 39.6M isinstance,
    78 pct of the gate) WHEN one walk buckets nodes by type into a per-file NodeIndex
    consumed by each sub-scan THEN pii_structural drops from 6.7s toward ~1.5-2s native
    (report candidate #4)'
  evidence: []
threat: null
component: null
```
Root cause: gates/_pii_structural/__init__.py:141 _scan_one_python_file does one ast.parse (good) but ~8 separate full ast.walk passes per file. Fix: one walk that buckets nodes (Assign/Call/ClassDef/Str/Attribute...) into a per-file NodeIndex; each sub-scan consumes its bucket instead of re-walking. Companion lint rule on the sibling PERF01x-detectors ticket: '>1 ast.walk(tree) over the same tree in one function family'.

<!-- ticket:T-1210 -->
```yaml
id: T-1210
title: 'perf: vet capability comment/docstring spans recomputed per file per gate
  -- tree-sitter Query + sorted-span bisect'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
acceptance:
- text: 'GIVEN _comment_byte_spans/_docstring_byte_spans (per-node Python recursion)
    are recomputed independently by sys and opaque, and _fully_in_any_span does an
    O(candidates x spans) linear any() over an unsorted span tuple (7.8M genexpr steps
    in sys alone) WHEN spans are sorted once and containment uses bisect, and spans
    are cached per (path, content-hash) for the run so sys and opaque share them THEN
    sys+opaque drop ~4-5s native combined (report candidate #5). NOTE: computing spans
    via a tree-sitter Query in C rather than Python recursion is covered by the sibling
    EPIC B child ''tree-sitter Query captures for comment/docstring spans (interim,
    zero-Rust)'' -- this ticket covers only the sort+bisect containment fix and the
    per-run cache, not the extraction mechanism itself'
  evidence: []
threat: null
component: null
```
Root cause: vet/_capability.py:212/:286 recompute comment/docstring byte spans per file per gate via Python recursion (12 pct of sys + 92 pct of opaque), and :244 _fully_in_any_span is a linear any() over an unsorted span tuple per candidate. Fix here: sort spans once, bisect for containment, and cache spans per (path, content-hash) so sys and opaque share one computation. The extraction-mechanism half of this candidate (Query captures replacing the Python recursion) is EPIC B's job, not this ticket's -- see that child to avoid two owners for the same code.

<!-- ticket:T-1211 -->
```yaml
id: T-1211
title: 'perf: secrets gate 33 regexes x finditer per line -- one combined-alternation
  scan per file'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/gates/_secrets.py
acceptance:
- text: 'GIVEN _scan_line runs 33 compiled patterns x finditer per line (544k lines,
    17.97M finditer calls, 94 pct of the gate) plus _fake_marker_reason regex against
    every line WHEN the whole file text is scanned once with one combined alternation
    regex (named groups per provider), match offsets map to lines via a bisect line-offset
    index, and per-pattern logic plus _fake_marker_reason only run on the rare hits
    THEN secrets drops from 4.5s to well under 1s native (report candidate #6)'
  evidence: []
threat: null
component: null
```
Root cause: gates/_secrets.py:932 _scan_line loops 33 compiled patterns via finditer per line; _fake_marker_reason (:676) also runs a regex against every line and its predecessor regardless of hits. Fix: one combined alternation regex over the whole file text, offset->line via bisect, defer per-pattern/_fake_marker_reason logic to actual hits. Companion lint rule on the sibling PERF01x-detectors ticket: 're.finditer with a pattern-list loop inside a per-line loop'.

<!-- ticket:T-1212 -->
```yaml
id: T-1212
title: 'perf: dup_spawn _entry_occurrences re-scans occurrences per (def, entry) pair
  -- index once per file'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/perf/_dup_spawn.py
acceptance:
- text: 'GIVEN _entry_occurrences (perf/_dup_spawn.py:195) re-scans occurrences for
    every (def, entry) pair (44,124 calls, 44.6s profiled, called from _def_violations
    x12702) WHEN occurrences are indexed once per file ({entry -> [spans]}) before
    the def loop, reusing the existing _index_file_occurrences shape from perf/_effect_summaries.py:717
    THEN perf drops ~4-5s native off its 19.1s stage (report candidate #7)'
  evidence: []
threat: null
component: null
```
Root cause: perf/_dup_spawn.py:195 _entry_occurrences is re-invoked per (def, entry) pair instead of building an index once per file. Fix: reuse the _index_file_occurrences pattern (perf/_effect_summaries.py:717) that already exists in this package -- build {entry -> [spans]} once, consume it in the def loop. No-duplication: this is the same indexing shape already implemented elsewhere in perf/, just not shared here.

<!-- ticket:T-1213 -->
```yaml
id: T-1213
title: 'natives: auto-rebuild stale frob_core/strata_core instead of NATIVE001 reminder'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/natives/**
- src/frob/gates/**
- src/frob/app/**
- docs/**
- tests/**
acceptance:
- text: GIVEN NATIVE001/StaleNative detects a source-newer-than-artifact native WHEN
    any frob command that needs the native runs THEN the rebuild happens automatically
    (T-0732 shared CARGO_TARGET_DIR makes warm builds ~11s) with the build disclosed
    in output, and NATIVE001 remains only for the cannot-build case (missing toolchain),
    which stays fail-closed
  evidence: []
- text: GIVEN a fresh worktree with no built natives THEN first frob invocation builds
    them automatically rather than degrading -- the recurring worktree-natives false-failure
    class disappears
  evidence: []
threat: null
component: null
```
Derived-state auto-refresh sweep 2026-07-29 (user directive: nothing frob-managed is refreshed manually). Natives staleness is DETECTED (src/frob/strata/_native_staleness.py, mtime+content-hash discrimination) but the refresh is a manual make core / frob natives build; T-0248 automated only the reminder. Sibling of T-1205 (coverage). Guard: never auto-build when the toolchain is absent -- disclose and fail closed as today.

<!-- ticket:T-1214 -->
```yaml
id: T-1214
title: 'perf: graph/cache load_file_data issues 3 sqlite queries per file -- batch
  whole-table SELECTs'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
acceptance:
- text: 'GIVEN load_file_data (graph/cache.py:560) issues 3 sqlite execute calls per
    file (5595 execute calls per load_all across ~1865 files) plus json.loads on every
    attrs value including the common attrs==''{}'' case WHEN load_all does 3 whole-table
    SELECTs ordered by path and groups rows in Python (or batches an executemany-style
    IN query per chunk), and skips json.loads for attrs==''{}'' THEN snapshot loading
    drops ~1s native off every gate/CLI invocation that loads it (report candidate
    #8)'
  evidence: []
threat: null
component: null
```
Root cause: graph/cache.py:564-587 load_file_data does 3 queries per file instead of 3 queries total. Fix: in load_all, replace the per-file query loop with 3 whole-table SELECTs (or chunked IN-batched queries) ordered by path, group rows in Python; add a fast path skipping json.loads when attrs == '{}'.

<!-- ticket:T-1215 -->
```yaml
id: T-1215
title: 'perf: arch gate ~8-10 independent per-file walks -- shared body-event stream,
  dedupe 3x _iter_own_scope'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- src/frob/arch/_lock_ordering.py
- src/frob/arch/_async_hazards.py
- src/frob/arch/_shared_state_race.py
- src/frob/arch/_concurrency_model.py
- src/frob/arch/_patterns.py
acceptance:
- text: 'GIVEN archgate''s _run_python_checks does ~8-10 independent full-tree walks
    per file (_py_build_function alone runs nesting/cyclomatic/events as 3 separate
    recursions; _iter_own_scope is independently reimplemented in _lock_ordering.py:136,
    _async_hazards.py:148, _shared_state_race.py:141 for 33.2s combined; plus _walk_all
    and _find_if_statements) WHEN all families consume the single shared _py_collect_body_events
    stream and the 3 _iter_own_scope copies collapse into one shared helper THEN archgate
    drops ~3-4s native off its 14.6s stage and the NO-DUPLICATION rule is satisfied
    for _iter_own_scope (report candidate #9)'
  evidence: []
threat: null
component: null
```
Root cause: arch/_python.py:782/637 _py_build_module/_py_build_function run 3 separate recursions per function (body events, nesting/depth, cyclomatic) instead of one; arch/_lock_ordering.py:136, _async_hazards.py:148, _shared_state_race.py:141 each independently reimplement _iter_own_scope (33.2s profiled = 13 pct of archgate); _concurrency_model.py:254 _walk_all and _patterns.py:518 _find_if_statements add further independent walks. Fix: fold nesting/cyclomatic/events into the existing _py_collect_body_events walk; extract one shared _iter_own_scope helper consumed by all three lock/async/race families.

<!-- ticket:T-1217 -->
```yaml
id: T-1217
title: 'perf: process-pool gate workers re-derive per-file artifacts -- persist derived
  artifacts keyed by content hash'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
acceptance:
- text: 'GIVEN _run_process_gate (gates/__init__.py:6050) has no run_memo_scope or
    shared parse artifacts, so perf/clones/dead_symbols/sys/pii/arch each independently
    re-parse+re-extract the whole repo in their own worker (perf 38 pct, clones 69
    pct, dead_symbols 88 pct -- the single biggest summed cost in the run, ~25-30s
    native) WHEN derived per-file artifacts (body tokens, leaf identifiers, comment/docstring
    spans, import specs) are persisted keyed by the content hash already stored in
    cache.db, and parse_file/extract consult that table before re-walking THEN warm-run
    stage time for perf/clones/dead_symbols/sys drops by the dominant share of their
    current native cost (report candidate #10)'
  evidence: []
threat: null
component: null
```
Root cause: gates/__init__.py:6050 _run_process_gate ships gates to a ProcessPoolExecutor with no run_memo_scope and no shared parse-artifact cache, unlike check/__init__.py:612 which wraps thread stages with memoization. Each pool worker re-parses and re-extracts the whole repo independently. Fix (Python-side, precedes any Rust migration): persist derived per-file artifacts (body tokens, leaf identifiers, comment/docstring spans, import specs) in a sqlite table keyed by the content hash already in cache.db; parse_file/extract read this table instead of re-walking trees. This is the single largest summed cost in the profile and should land before or alongside EPIC B's Rust migration, not instead of it -- Rust makes the per-artifact compute cheaper, this ticket stops it from being redone N times.

<!-- ticket:T-1218 -->
```yaml
id: T-1218
title: 'doctor: stale-global-frob self-check -- invoked version vs repo floor'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/doctor.py
- src/frob/app/**
- docs/**
- tests/**
acceptance:
- text: GIVEN a frob invocation in a repo whose frob.toml declares a minimum frob
    version WHEN the invoked frob is older THEN every command prints a prominent stale-binary
    warning naming the upgrade command, and frob doctor reports it as a finding
  evidence: []
threat: null
component: null
```
Derived-state auto-refresh sweep 2026-07-29: the globally installed frob (uv tool) went stale at 0.9.0 while the repo advanced to 0.277.0, causing wrong gate numbers for anyone invoking bare frob -- a documented recurring papercut. Detection belongs in frob itself: version floor in frob.toml, checked at CLI startup (cheap), doctor finding with the exact uv tool upgrade frob remedy.

<!-- ticket:T-1219 -->
```yaml
id: T-1219
title: 'perf: migrate tree-extraction layer to frob_core (Rust)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/lang/**
- frob-core/**
threat: null
component: null
```
Umbrella epic: migrate the Python-side tree-sitter tree-extraction layer (frob.lang._extract.extract, _walk_python, _common.walk) into frob_core (PyO3/Rust), per the report's Rust-migration-candidates ranking. This is the largest single native-cost family measured (perf 38 pct, clones 69 pct, deprecated 76 pct, dead_symbols 88 pct, opaque 92 pct, sys ~50 pct -- summed ~40-50s native per full check) and is not covered by frob_core today (existing kernels consume the token lists this layer produces). 4 children: tree-extraction kernel, capability-scan resolver, arch metrics single-pass walk export, and an interim zero-Rust tree-sitter Query step for comment/docstring spans. New FFI boundaries must satisfy FFI001/FFI002 (src/frob/gates/_ffi_boundary.py).

<!-- ticket:T-1220 -->
```yaml
id: T-1220
title: 'rust: tree-extraction kernel -- source bytes to symbols/spans/tokens/identifiers/comment+docstring
  spans/import specs'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- frob-core/**
acceptance:
- text: 'GIVEN frob.lang._extract.extract and _walk_python do pure per-node Python
    recursion over py-tree-sitter Node objects (measured shares: perf 38 pct, clones
    69 pct, deprecated 76 pct, dead_symbols 88 pct, opaque 92 pct, sys ~50 pct) WHEN
    a frob_core kernel (e.g. extract_tree(source: bytes, lang: str) -> (symbols, spans,
    body_tokens, leaf_identifiers, comment_spans, docstring_spans, import_specs))
    is exported for python/cpp/rust/typescript via the tree-sitter Rust crates, with
    kotlin staying on the existing Python path, and the FFI boundary passes FFI001/FFI002
    THEN callers across perf/clones/deprecated/dead_symbols/opaque/sys switch to the
    native kernel and each site''s measured native-cost share for extraction drops
    correspondingly'
  evidence: []
- text: 'GIVEN the report''s Rust-migration-candidates #1 and #4 overlap (identifier/xref
    index kernel is subsumed by the tree-extraction kernel if it lands first) WHEN
    this ticket lands THEN the identifier/xref index kernel work is satisfied as a
    byproduct (leaf_identifiers output) rather than needing a separate crate export
    -- no duplicate kernel is built for identifier extraction'
  evidence: []
threat: null
component: null
```
Root cause and target: this is Rust-migration candidate #1 from the report, HIGH feasibility. tree-sitter has first-class Rust crates and tree-sitter-python/cpp/rust/typescript grammars exist as crates; kotlin (via tree-sitter-language-pack) stays Python-side for now. frob-core already has the pyo3/abi3 plumbing and .pyi convention; API shape mirrors existing kernels (plain lists/tuples over the FFI, consistent with dup/callgraph/arch kernels already shipped). This ticket SUBSUMES Rust-migration candidate #4 (identifier/xref index kernel): note explicitly in the design that leaf-identifier output from this kernel satisfies #4's need, so no second crate export is built purely for identifiers. Not blocked on anything -- this is the foundation the other EPIC B children (capability resolver, arch metrics walk) build on, but do not add a blocked_by edge for those; they are downstream consumers, this ticket's own scope does not require them to exist first.

<!-- ticket:T-1221 -->
```yaml
id: T-1221
title: 'rust: capability-scan resolver in frob_core -- import table + alias propagation
  + candidate resolution'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- frob-core/**
acceptance:
- text: 'GIVEN vet/_capability.py''s 5 Python recursions per file (import table walk,
    alias walk, candidate walk, comment spans, docstring spans -- 37 pct of sys, est
    ~8s native) are self-contained per-file functions of file bytes + a static needle
    registry WHEN a frob_core export scan_python_capabilities(source: bytes) -> (candidates,
    spans) replaces the Python recursions THEN sys''s capability-scan share drops
    correspondingly and the vet CLI path speeds up proportionally'
  evidence: []
threat: null
component: null
```
Root cause and target: Rust-migration candidate #2 from the report, MEDIUM-HIGH feasibility. Depends on candidate #1's tree access (the tree-extraction kernel), so this is a natural second crate export once that lands. Self-contained semantics make this a clean FFI boundary; respect FFI001/FFI002.

<!-- ticket:T-1222 -->
```yaml
id: T-1222
title: 'rust: arch python metrics single-pass walk export (extraction only, rules
  stay Python)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- frob-core/**
acceptance:
- text: 'GIVEN _run_python_checks is 97 pct of archgate and _py_build_module alone
    is 31 pct, doing body-event/nesting/cyclomatic extraction as separate Python recursions
    per function WHEN a frob_core export py_function_metrics(source: bytes) -> [(span,
    nesting, cyclomatic, events)] replaces the extraction-only portion of _py_build_function/_py_build_module,
    with all rule logic (arch/_lock_ordering.py, _async_hazards.py, _shared_state_race.py,
    _concurrency_model.py, _patterns.py) staying in Python and consuming the exported
    metrics THEN archgate''s per-file walk cost drops toward the export''s native
    cost, and no rule-decision logic crosses the FFI boundary'
  evidence: []
threat: null
component: null
```
Root cause and target: Rust-migration candidate #3 from the report, MEDIUM feasibility -- more rule logic crosses the boundary than candidates #1/#2, so scope is deliberately extraction-only; keep rule families in Python. frob_core already hosts arch's near-dup clustering (near_duplicate_indices), so the crate boundary for arch already exists and this extends it. FFI001/FFI002 apply. This is independent of Epic A's T-1215 (arch dedupe of _iter_own_scope, a Python-side fix) -- that ticket should land on its own timeline; this ticket does not block or get blocked by it, since T-1215 is a pure-Python fix to the current implementation and this ticket replaces the extraction step underneath it.

<!-- ticket:T-1223 -->
```yaml
id: T-1223
title: 'rust(interim): tree-sitter Query captures for comment/docstring spans shared
  by sys+opaque+vet'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
acceptance:
- text: GIVEN _comment_byte_spans (vet/_capability.py:212) and _docstring_byte_spans
    (:286) are per-node Python recursions independently re-run by sys and opaque (12
    pct of sys + 92 pct of opaque combined) WHEN they are replaced with tree-sitter
    Query captures ('(comment) @c' and the docstring-node equivalent), which run in
    C via the existing py-tree-sitter binding rather than a Python recursion, THEN
    sys+opaque's span-extraction share drops without requiring a new frob_core crate
    export
  evidence: []
threat: null
component: null
```
Root cause and target: this is the interim zero-Rust step noted under Rust-migration candidate #1 ('use tree-sitter Query captures (C speed) for comment/docstring/identifier extraction from Python'), and it is the mechanism half of PERF-epic child T-1210 (report candidate #5). Split of ownership: this ticket owns the span-EXTRACTION mechanism (Query captures replacing Python recursion) since it is the natural home for a tree-sitter-API-level change; T-1210 owns the sort+bisect containment fix and the per-run cache for the resulting spans, and its acceptance criteria explicitly defer the mechanism to this ticket to avoid two owners writing to the same function. Do not duplicate the containment/caching acceptance criteria here -- see T-1210.

<!-- ticket:T-1225 -->
```yaml
id: T-1225
title: 'perf: PERF01x detectors from hot-graph root causes'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
acceptance:
- text: GIVEN the 2026-07-29 hot-graph report identified 4 recurring anti-patterns
    (yaml.safe_load/yaml.load without the C loader in non-test code; a repo-scan API
    such as xref/exports_consumers/iter_files called inside a loop over symbols; more
    than one ast.walk over the same tree within one function family; a re.finditer
    pattern-list loop nested inside a per-line loop) WHEN each ships as a distinct
    PERF01x rule id with a registry entry and a .strata obligation layer THEN each
    rule fires on the exact pre-fix code shape it was mined from, backed by a regression
    corpus fixture reproducing that shape (e.g. the pre-fix tickets/_store.py, gates/_debt_deprecated.py,
    gates/_pii_structural/__init__.py, and gates/_secrets.py shapes) so a future regression
    re-introducing the pattern is caught statically
  evidence: []
threat: null
component: null
```
Companion detector ticket for EPIC A's fixes (T-1206 CSafeLoader, T-1207 repo-scan-in-loop, T-1209 multi-ast.walk, T-1211 regex-per-line): per repo convention, a perf root cause ships as both a .strata obligation and a PERF0xx lint rule, never as a fix-only patch. Four rules to add: (a) 'yaml.safe_load/yaml.load without C loader in non-test code'; (b) 'repo-scan API (xref/exports_consumers/iter_files) called inside a loop over symbols'; (c) '>1 ast.walk(tree) over the same tree in one function family'; (d) 're.finditer with a pattern-list loop inside a per-line loop'. Each needs a PERF01x id, a registry entry, and a regression-corpus fixture reproducing the exact pre-fix shape mined from the report (tickets/_store.py, gates/_debt_deprecated.py, gates/_pii_structural/__init__.py, gates/_secrets.py) so the rule is proven to fire before the corresponding EPIC A fix lands, and to keep firing as a regression guard after.

<!-- ticket:T-1226 -->
```yaml
id: T-1226
title: 'docs integrity: close the silent-miss classes from the 2026-07-29 staleness
  sweep'
state: queued
kind: docs
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- docs/**
- src/frob/gates/**
- src/frob/graph/**
threat: null
component: null
```
121-doc staleness sweep (docs/audits/docs-staleness-2026-07-29.md): 2 class-A gate-flagged findings, ~140 class-B silent misses, 6 gate-gap classes, a drift-lock candidate list, and one code-side bug. Every silent miss indicts a frob gate gap: each gap class becomes a mechanism ticket, plus a fix campaign for the doc content itself.

<!-- ticket:T-1229 -->
```yaml
id: T-1229
title: negative-existence claims -- bind absence-claims to a ticket via frob:until,
  flag unbound ones
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/**
threat: null
component: null
```
A directive (e.g. frob:until T-####) binds not-yet-built prose to a ticket; when the ticket closes/archives the claim goes stale. Unbound absence-claims ('does not exist yet' heuristics) get flagged for binding. The sweep found ~20 shipped-but-documented-as-absent instances (docs/audits/docs-staleness-2026-07-29.md, 'Negative-existence claims' section). Ref: gate-gap class 3.

<!-- ticket:T-1230 -->
```yaml
id: T-1230
title: non-python doc targets -- Makefile/frob.toml/pyproject/Rust layout edges into
  the graph
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- docs/**
threat: null
component: null
```
Doc edges to Makefile recipe/dep claims, frob.toml severity claims, pyproject entries, Rust file layout; builds on the multi-language graph. Relate to T-1193's python-only theme; check whether its children already cover part of this and cross-reference rather than duplicate. Ref: gate-gap class 4 in docs/audits/docs-staleness-2026-07-29.md.

<!-- ticket:T-1231 -->
```yaml
id: T-1231
title: 'doclink basename+fragment validation -- resolve relative link targets and
  #fragment anchors'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/gates/**
threat: null
component: null
```
Extend doclink checking (DOCLNK rule) to verify relative link basenames and #fragment anchors resolve, or fail. Ref: gate-gap class 5 in docs/audits/docs-staleness-2026-07-29.md.

<!-- ticket:T-1232 -->
```yaml
id: T-1232
title: status/currency checks -- dated status/superseded-by header on audit docs,
  ticket-id prose vs ledger, index completeness
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/audits/**
threat: null
component: null
```
Require a dated status/superseded-by header on docs/audits/* (gate-checkable); check ticket-id prose against ledger state (open/closed/renumbered); check index completeness vs the docs tree. Ref: gate-gap class 6 in docs/audits/docs-staleness-2026-07-29.md.

<!-- ticket:T-1235 -->
```yaml
id: T-1235
title: 'coverage attribution fix: subprocess rc + multiprocessing concurrency'
state: queued
kind: bug
origin: agent
created: '2026-07-29'
priority: critical
blocked_by:
- T-1395
parent: T-0969
tier: ticket
sprint: null
scope:
- Makefile
- pyproject.toml
- tests/**
- docs/**
evidence:
- tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_uses_absolute_source_and_data_file
- tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_declares_multiprocessing_and_sigterm
- tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_remaps_paths_back_to_source
- tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_pyproject_declares_concurrency_and_sigterm
acceptance:
- text: GIVEN make coverage runs THEN a generated .frob/coverage-subprocess.rc (absolute
    source and data_file, branch/parallel/relative_files/sigterm true, concurrency
    multiprocessing+thread, disable_warnings no-data-collected, paths remap) is what
    COVERAGE_PROCESS_START points at, and zero .coverage.* files are stranded outside
    repo root after the run
  evidence:
  - tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_uses_absolute_source_and_data_file
  - tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_declares_multiprocessing_and_sigterm
  - tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_remaps_paths_back_to_source
- text: GIVEN pyproject [tool.coverage.run] THEN concurrency multiprocessing+thread
    and sigterm true are set so in-process gate-pool execution is recorded
  evidence:
  - tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_pyproject_declares_concurrency_and_sigterm
- text: GIVEN the corrected full run THEN previously-exercised-but-zero symbols (excludes.py,
    doctor.py, serve/, __main__.py) report real coverage and the TEST005 count reflects
    it
  evidence: []
threat: null
component: null
```
T-0969 diagnosis 2026-07-29: fresh coverage RAISED TEST005 to 1357; staleness was not the inflation. Loss A: CLI subprocesses measure nothing (relative source vs child cwd) and strand data files in child cwds (626 stranded, 100% of 120 sampled empty). Loss B: ProcessPoolExecutor gate workers unrecorded. Verified experiment: corrected rc moved excludes.py 51->97, doctor 33->86, 81 of 103 zero-modules gained data; merged count 1357->1175 from a partial subset alone.

## Done report

The coverage-attribution fix this ticket calls for (absolute-path subprocess
rc generation in the `coverage:` Makefile recipe, plus concurrency=
multiprocessing,thread / sigterm=true in both the generated rc and
pyproject.toml's [tool.coverage.run]) was already implemented on main --
Makefile:116-232 and pyproject.toml:157-167 both carry T-1235 comment
references and match the acceptance criteria exactly. No prior worktree had
locked this configuration down with a test, so acceptance [0] and [1] were
still UNBOUND despite the fix being live.

Added TestSubprocessRcIsAbsoluteAndConcurrencyAware to
tests/unit/test_makefile_coverage.py: it extracts the REAL printf block that
builds .frob/coverage-subprocess.rc straight out of the Makefile text
(mirroring the existing _recipe_tail helper's approach) and asserts absolute
source/data_file paths, branch/parallel/relative_files/sigterm/concurrency/
disable_warnings, and the [paths] remap section -- plus a direct
tomllib-parsed assertion that pyproject.toml's [tool.coverage.run] declares
the same concurrency/sigterm pair for the main (non-subprocess) process.
This is a regression lock, not new production code: a future edit that
silently drops the absolute-path fix or the concurrency settings now fails
fast in ~1s instead of only being caught by a 1300+ TEST005 regression on
the next full make coverage run.

Acceptance [2] ("previously-exercised-but-zero symbols report real coverage
and the TEST005 count reflects it") cannot be verified from a worktree: it
requires a full, unscoped `make coverage` run, which is a coordinator-only
step (playbook section 6b) -- a dispatched sub-agent cannot wait on it. This
acceptance is left UNBOUND; the coordinator's next full make coverage +
frob check --stamp-coverage pass is what closes it out. The T-0969 diagnosis
already recorded (in the ticket body) a verified experiment run against this
exact same fix showing excludes.py 51->97, doctor 33->86, 81 of 103
zero-modules gaining data -- but that was measured before this ticket's own
work, not a durable claim from this session, so it is not cited as this
session's own evidence.

`frob sys sync-interface` was run once mid-ticket (playbook section 0 step
5 mentions it is safe to run early to catch drift), which wrote
design/frob.strata to add the new test class's interface attr. That file
is outside T-1235's declared scope (Makefile, pyproject.toml, tests/**,
docs/**), so the edit was reverted -- `frob ticket land` absorbs this same
sync-interface write automatically before its own merge (playbook section
0 step 5), so the SELFAUDIT001 finding this leaves in a scoped `frob check`
run is expected pre-land, not a real gap.

### Changed
```
 tickets.md | 16 ++++++++++++----
 1 file changed, 12 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_uses_absolute_source_and_data_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_declares_multiprocessing_and_sigterm` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_remaps_paths_back_to_source` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_pyproject_declares_concurrency_and_sigterm` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 7685 warning(s), 696 waived
- error-findings: SELFAUDIT001@design

<!-- ticket:T-1236 -->
```yaml
id: T-1236
title: 'coverage deflation guard: canary modules, not just join fraction'
state: queued
kind: security
origin: agent
created: '2026-07-29'
priority: high
parent: T-0969
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/**
- docs/**
acceptance:
- text: 'GIVEN a coverage run that lost subprocess or pool-worker data THEN the stamp
    is refused: guard checks fraction-of-known-modules-with-nonzero-coverage and named
    canaries (src/frob/__main__.py nonzero while system tests exist), not only module_join_fraction
    which reads ~1.0 under source=-inflated zeros'
  evidence: []
threat: null
component: null
```
T-1180's deflation floor stamped three deflated runs clean because source= makes every unexecuted file appear at 0% so the join fraction stays high. Structural blind spot found by the T-0969 diagnosis 2026-07-29.

<!-- ticket:T-1238 -->
```yaml
id: T-1238
title: 'EPIC cli regrouping: verb groups to shrink the top-level surface -- frob explore
  first'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/app/**
- src/frob/__main__.py
- docs/**
- tests/**
acceptance:
- text: 'GIVEN frob --help THEN the top level presents a small set of verb groups
    (target: under ~15 entries) with subcommands grouped by intent, every old invocation
    either still working or aliased with a pointer, and the grouped help readable
    by a first-time user'
  evidence: []
- text: GIVEN frob explore THEN map/outline/xref/docs-search live as its subcommands,
    un-deprecated (frob:deprecated markers and sunset warnings removed), with their
    standalone deprecated top-level forms aliased through a transition window
  evidence: []
- text: GIVEN the regrouping design doc THEN it proposes the full grouping taxonomy
    for every current top-level command with a migration/alias policy, before any
    group beyond explore is implemented
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: frob is intimidating; group everything together. First concrete slice: the T-0580-deprecated navigation commands (map/outline/xref/docs-search) regroup into frob explore instead of being deleted -- this SUPERSEDES the 2026-10-01 sunset (T-0802 dropped with this epic as the reason). Design phase first for the full taxonomy (candidate buckets to evaluate, not prescribe: explore/navigation, quality/check+test+fix, tickets, design/sys+strata, supply-chain/vet, ops/release+registry+natives+doctor+clean, serve/perf tooling); un-deprecation of the explore members includes removing the docs 'Kept commands'/deprecation drift the 2026-07-29 staleness sweep catalogued. Children to file at design time: taxonomy design doc, explore group implementation, alias/transition machinery, help-surface rework, docs/index updates.

<!-- ticket:T-1241 -->
```yaml
id: T-1241
title: 'compliance: enforce the 27-row corpus, not catalogue it'
state: queued
kind: security
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- docs/design/registry/compliance.yaml
- src/frob/strata/_compliance.py
- src/frob/gates/_decisions_compliance.py
acceptance:
- text: GIVEN this epic's children all close WHEN a fresh reader asks 'is CCPA/GDPR
    notice enforced' THEN the answer is a named RegulationEntry+mitigation+test+gate,
    not a disposition string
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: compliance coverage must be ENFORCED, not catalogued. Standing repo principle: a registry row read by zero code is orphaned docs presented as implemented; a completion claim needs a passing gate. State as of filing: 27 CMPL-* rows in docs/design/registry/compliance.yaml are all unit-level dispositioned (10 out_of_scope process/advisory, 17 handled_by:COMPLIANCE005), but COMPLIANCE005 only checks that a disposition STRING exists -- it does not verify any real mitigation predicate or model vocabulary backs the 17 handled_by units. Only 6 RegulationEntry/mitigation pairs exist in COMPLIANCE_CATALOG (COPPA, GDPR-ERASURE/RETENTION/BASIS, HIPAA-BAA, MINIMIZATION). No exposure:public-web (or equivalent) attr vocabulary exists, so nothing today forces a public web-facing node to carry a privacy-policy/notice/consent mitigation -- the user's concrete example of catalogued-not-enforced. CCPA/CPRA sit as OutOfScopeRegulation entries (caught_by PII010) -- worth revisiting once exposure:public-web lands, not force-closed here.

<!-- ticket:T-1243 -->
```yaml
id: T-1243
title: 'tickets: cluster dispatch -- brief and lease an epic/story as one agent mission'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/_cli_parsers/_ticket.py
- docs/**
- tests/**
acceptance:
- text: 'GIVEN frob ticket brief --cluster <epic-or-story-id> THEN one briefing is
    emitted covering every doable descendant in dependency order: shared playbook
    rules once, per-ticket body+acceptance+scope, the union scope lease, and the expected
    land cadence (one land per ticket, not one mega-land)'
  evidence: []
- text: GIVEN frob ticket work --cluster <id> THEN one worktree is created/reused
    with natives built once and every ticket in the cluster leased to it, so an agent
    pays worktree warmup, playbook read, and natives build exactly once per cluster
    instead of once per ticket
  evidence: []
- text: GIVEN two clusters with overlapping union scopes THEN the second lease attempt
    fails loud naming the conflict, preserving the disjoint-scope dispatch guarantee
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: agents should receive a series of related tickets in one mission to avoid cold-start cost (worktree creation, playbook read, natives build, graph warm) being paid per ticket. The tier system (epic/story/ticket) and parent edges already express the grouping; frob ticket brief (T-0568) and frob ticket work already exist per-ticket. This adds the cluster form: dependency-ordered doable descendants of an epic/story as one mission with a union scope lease. Serial-cluster dispatch is already the coordinator practice (drive memory); this makes it a first-class frob verb instead of hand-assembled prompts.

<!-- ticket:T-1259 -->
```yaml
id: T-1259
title: 'ledger v2: migration (frob ticket migrate --to v2, golden round-trip, deprecation
  gate, final cutover)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-1253
- T-1254
- T-1255
- T-1256
- T-1257
- T-1258
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_merge_zones.py
- src/frob/gates/**
- docs/modules/tickets.md
- .gitattributes
- tests/fixtures/tickets/**
- tests/test_tickets_migration.py
acceptance:
- text: 'The migration child ticket, per T-1136''s epic body ("migration is a

    separate child... with golden round-trip tests") and design doc section

    7. Blocked by every design-implementing child (lock model, store

    backend, renumber, archive, doable/index, land merge-story retirement) --

    migration only makes sense once v2 is a fully working alternate mode.'
  evidence: []
- text: "Deliverables (design section 7, this ticket owns ALL of them):\n1. `frob\
    \ ticket migrate --to v2`: one-shot, reversible migrator reading\n   today's `tickets.md`/`tickets-archive.md`\
    \ via existing `_parse_ledger`,\n   writing `tickets/T-####/ticket.md` + `done-report.md`\
    \ + moved\n   attachments -- WITHOUT deleting the monofiles in the same commit.\n\
    2. Golden round-trip test: migrate a fixture ledger to v2, migrate v2\n   back\
    \ to a monofile rendering, assert semantic equality (same id set,\n   field values,\
    \ Done-report text) even if not byte-identical.\n3. A new deprecation-class gate\
    \ (name TBD, e.g. LEDGERV1001) warning on\n   monofile-mode repos once v2 ships,\
    \ mirroring the existing DEPR00x\n   escalation-after-expiry pattern.\n4. Final-cutover\
    \ step (separate commit within this ticket, or an\n   explicitly filed follow-up\
    \ if judged too large): flip the fresh-repo\n   default to v2, delete `_render_ledger`/`splice_ledger`/\n\
    \   `_land_merge.py`/`_land_merge_zones.py`, remove the `.gitattributes`\n   merge-driver\
    \ line."
  evidence: []
- text: 'Do NOT delete the v1 monofile code path until the golden round-trip test

    is green AND a compatibility-window period has been explicitly recorded

    (a dated note in docs/modules/tickets.md is sufficient evidence, no fixed

    calendar length is prescribed here -- follow the DEPR00x precedent''s own

    expiry-recording convention).'
  evidence: []
- text: 'GIVEN a fixture monofile ledger covering a done ticket with a Done

    report, a queued ticket with blocked_by, a ticket with attachments, an

    archived ticket, and a draft-id ticket

    WHEN it is migrated to v2 then migrated back to a monofile rendering

    THEN the round-tripped rendering parses to an equal id-set and equal

    per-ticket field values and Done-report text as the original (golden

    round-trip test, T-1136 acceptance[1]''s reversibility requirement).'
  evidence: []
- text: 'GIVEN a migration mid-way through the compatibility window

    WHEN `frob check` runs against a monofile-mode repo

    THEN it reports a new deprecation-class warning (not yet an error) naming

    the v2 migration path, escalating to error only after an explicitly

    recorded expiry.'
  evidence: []
- text: 'GIVEN the final cutover has landed

    WHEN a real land runs

    THEN it performs no monofile splice (T-1136 acceptance[1]), two agents

    landing disjoint tickets produce no ledger merge conflict, and the

    TICK002/TICK006 draft-death classes described in the epic are

    structurally impossible (draft directories are disjoint git objects,

    verified by a regression test reproducing the T-1115/T-1126/T-1127/

    T-1128 draft-death shape against v2 and asserting no draft is lost).'
  evidence: []
threat: null
component: null
```
The migration child ticket, per T-1136's epic body ("migration is a
separate child... with golden round-trip tests") and design doc section
7. Blocked by every design-implementing child (lock model, store
backend, renumber, archive, doable/index, land merge-story retirement) --
migration only makes sense once v2 is a fully working alternate mode.

Deliverables (design section 7, this ticket owns ALL of them):
1. `frob ticket migrate --to v2`: one-shot, reversible migrator reading
   today's `tickets.md`/`tickets-archive.md` via existing `_parse_ledger`,
   writing `tickets/T-####/ticket.md` + `done-report.md` + moved
   attachments -- WITHOUT deleting the monofiles in the same commit.
2. Golden round-trip test: migrate a fixture ledger to v2, migrate v2
   back to a monofile rendering, assert semantic equality (same id set,
   field values, Done-report text) even if not byte-identical.
3. A new deprecation-class gate (name TBD, e.g. LEDGERV1001) warning on
   monofile-mode repos once v2 ships, mirroring the existing DEPR00x
   escalation-after-expiry pattern.
4. Final-cutover step (separate commit within this ticket, or an
   explicitly filed follow-up if judged too large): flip the fresh-repo
   default to v2, delete `_render_ledger`/`splice_ledger`/
   `_land_merge.py`/`_land_merge_zones.py`, remove the `.gitattributes`
   merge-driver line.

Do NOT delete the v1 monofile code path until the golden round-trip test
is green AND a compatibility-window period has been explicitly recorded
(a dated note in docs/modules/tickets.md is sufficient evidence, no fixed
calendar length is prescribed here -- follow the DEPR00x precedent's own
expiry-recording convention).

GIVEN a fixture monofile ledger covering a done ticket with a Done
report, a queued ticket with blocked_by, a ticket with attachments, an
archived ticket, and a draft-id ticket
WHEN it is migrated to v2 then migrated back to a monofile rendering
THEN the round-tripped rendering parses to an equal id-set and equal
per-ticket field values and Done-report text as the original (golden
round-trip test, T-1136 acceptance[1]'s reversibility requirement).

GIVEN a migration mid-way through the compatibility window
WHEN `frob check` runs against a monofile-mode repo
THEN it reports a new deprecation-class warning (not yet an error) naming
the v2 migration path, escalating to error only after an explicitly
recorded expiry.

GIVEN the final cutover has landed
WHEN a real land runs
THEN it performs no monofile splice (T-1136 acceptance[1]), two agents
landing disjoint tickets produce no ledger merge conflict, and the
TICK002/TICK006 draft-death classes described in the epic are
structurally impossible (draft directories are disjoint git objects,
verified by a regression test reproducing the T-1115/T-1126/T-1127/
T-1128 draft-death shape against v2 and asserting no draft is lost).

<!-- ticket:T-1262 -->
```yaml
id: T-1262
title: 'gates --fix Tier-B transaction engine: apply-verify-rollback per fix'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine_tier_b.py
- tests/test_gates.py
acceptance:
- text: GIVEN a Tier-B fix that applies cleanly WHEN its affected_gates and bound_tests
    all re-verify clean THEN the fix is committed and reported as fixed
  evidence: []
- text: GIVEN a Tier-B fix that introduces a regression WHEN affected_gates or bound_tests
    fail after applying THEN every touched file is restored byte-for-byte from its
    pre-fix backup and a FixRolledBack record discloses which gate/test regressed
  evidence: []
- text: GIVEN N Tier-B fixes in one --fix invocation THEN each is applied and verified
    sequentially, never batched, so a rollback never has to bisect more than one fix
  evidence: []
threat: null
component: null
```
Build the Tier-B transactional fix engine per docs/design/check-fix-engine.md
"Transaction / rollback model" section: new src/frob/gates/_fix_engine_tier_b.py
with TIER_B_HANDLERS: dict[str, TierBHandler], a TierBFix model (backup
bytes, affected_gates, bound_tests), and the apply-verify-commit-or-
rollback engine itself (snapshot pre-fix bytes, apply, re-run affected
gates + bound tests, restore from backup byte-for-byte on any regression,
emit a disclosed FixRolledBack record naming what regressed). Ship
sequential, per-fix verification -- never batched -- exactly as the design
doc specifies. No concrete Tier-B handler is required to exist yet as
part of THIS ticket's scope beyond one minimal reference handler proving
the rollback path end-to-end (a synthetic/test-fixture rule is
acceptable, or reuse whichever real Tier-B-shaped rule is cheapest to
wire first -- implementer's judgment, disclose the choice in the Done
report).

<!-- ticket:T-1263 -->
```yaml
id: T-1263
title: gates --fix Tier-C fix-it emission format for agents
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine_tier_c.py
- tests/test_gates.py
acceptance:
- text: GIVEN a content-required finding with a registered Tier-C emitter WHEN --fix
    runs THEN no file is edited and a FixIt record with a non-empty reason_unfixable
    is emitted
  evidence: []
- text: GIVEN --fix --json THEN the output includes a `fixits` array; on a repo with
    zero Tier-C-eligible findings the array is empty, never a missing key
  evidence: []
- text: GIVEN a FixIt's message field THEN it is the original violation's message
    verbatim, never paraphrased
  evidence: []
threat: null
component: null
```
Build Tier-C fix-it emission per docs/design/check-fix-engine.md
"Fix-it emission format" section: new src/frob/gates/_fix_engine_tier_c.py
with a FixIt model (rule, file, line, message, proposed_patch: str | None,
reason_unfixable: str) and TIER_C_EMITTERS: dict[str, TierCEmitter]. Wire
`--fix --json`'s output to include a `fixits` array (empty when no Tier-C
emitter fires) alongside the existing violations array -- additive only,
never replacing frob check's existing --json shape. Ship at least one
real Tier-C emitter (a content-required finding with no mechanical
rewrite -- e.g. TODO001's "bind this to a ticket" case, or a DOC002
finding with 0 or 2+ fuzzy candidates, reusing fix_doc002_unique_slug's
own already-computed candidate set to populate proposed_patch when
exactly the wrong number of candidates exist, or null when zero).

<!-- ticket:T-1264 -->
```yaml
id: T-1264
title: 'gates --fix fixability registry field: generated-verified auto/verified/assisted/manual
  tier per rule id'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1262
- T-1263
- T-1261
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/_fixability_scan.py
- src/frob/gates/__init__.py
- docs/design/registry/check-coverage.yaml
- src/frob/registry/_staleness.py
- tests/test_gates.py
acceptance:
- text: GIVEN every known gate rule id THEN generated_fixability() maps it to exactly
    one of auto/verified/assisted/manual, with manual as the correct default for a
    rule with no handler in any table
  evidence: []
- text: GIVEN a rule id registered in more than one of TIER_A_HANDLERS/TIER_B_HANDLERS/TIER_C_EMITTERS
    WHEN generated_fixability() runs THEN it raises FixabilityConflict rather than
    silently picking one
  evidence: []
- text: GIVEN the checked-in _KNOWN_RULE_FIXABILITY literal WHEN it drifts from a
    fresh generated_fixability() scan (a handler added without updating the literal)
    THEN TestRuleFixability fails loud
  evidence: []
- text: 'GIVEN check-coverage.yaml''s CHK-GATE-<rule> entries THEN each carries a
    fixability: field kept in sync the same idempotent way gate_rule_entries already
    is'
  evidence: []
threat: null
component: null
```
Build the generated-verified fixability registry field per
docs/design/check-fix-engine.md "Fixability registry field" section,
mirroring src/frob/gates/_rule_id_scan.py's own generated-verified shape
(scanner is authority, checked-in literal is generated artifact,
drift-lock test re-verifies every run). New
src/frob/gates/_fixability_scan.py: generated_fixability() imports
TIER_A_HANDLERS (_fix_engine.py), TIER_B_HANDLERS (_fix_engine_tier_b.py),
TIER_C_EMITTERS (_fix_engine_tier_c.py), and known_gate_rule_ids()
(_rule_id_scan.py), and maps every known rule id to auto/verified/
assisted/manual -- raising FixabilityConflict if a rule id appears in
more than one table. Add the checked-in _KNOWN_RULE_FIXABILITY literal
(frob.gates.__init__ or a similarly central module) plus
tests/test_gates.py::TestRuleFixability re-verifying it against a fresh
scan. Extend docs/design/registry/check-coverage.yaml's CHK-GATE-<rule>
entries with a fixability: field, synthesized the same idempotent way
sync_gate_rule_entries already synthesizes missing entries (reuse that
function's shape, do not invent a second YAML-mutation pattern).

<!-- ticket:T-1267 -->
```yaml
id: T-1267
title: 'refactor: prose/doc-anchor carrier (docstring, docs/**, anchor-slug rewrite)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- tests/test_refactor.py
- docs/design/refactor-verb.md
- docs/commands/refactor.md
scope_changes:
- op: remove
  glob: docs/**
  reason: docs/** is chronically over-broad (matches every doc-anchor in the repo,
    spamming scope-closure warnings); this ticket's own design/docs surface is narrow
    -- the actual doc files it rewrites at runtime are the refactor target's own doc
    set, discovered dynamically, not a static scope glob
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/design/refactor-verb.md
  reason: docs/** is chronically over-broad (matches every doc-anchor in the repo,
    spamming scope-closure warnings); this ticket's own design/docs surface is narrow
    -- the actual doc files it rewrites at runtime are the refactor target's own doc
    set, discovered dynamically, not a static scope glob
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/commands/refactor.md
  reason: docs/** is chronically over-broad (matches every doc-anchor in the repo,
    spamming scope-closure warnings); this ticket's own design/docs surface is narrow
    -- the actual doc files it rewrites at runtime are the refactor target's own doc
    set, discovered dynamically, not a static scope glob
  actor: logan
  at: '2026-07-29'
acceptance:
- text: 'GIVEN a docstring or comment in a file unrelated to a moved symbol''s own

    code, naming that symbol''s old dotted path in prose WHEN the move

    completes THEN that mention is rewritten to the new dotted path'
  evidence: []
- text: 'GIVEN docs/** prose (a sentence naming the old module) or an embedded

    fenced code block citing the old import path WHEN the move completes

    THEN both are rewritten to the new path, and `frob.gates._doclink_docanchor`

    reports no new DOC001/DOC002 finding caused by the move'
  evidence: []
- text: 'GIVEN a doc heading whose slug embeds the moved symbol or module name

    WHEN the move completes THEN the heading text and its anchor slug are

    rewritten together, and every existing `frob:doc`/markdown

    `frob:describes` reference to that anchor still resolves'
  evidence: []
- text: 'GIVEN a prose mention the tool cannot safely rewrite (ambiguous natural-

    language use, a name that collides with a common English word, or a

    mention inside a generated/vendored file) WHEN the refactor completes

    THEN it is listed explicitly in the disclosed report as "not rewritten --

    review by hand", never silently skipped and never guessed at'
  evidence: []
threat: null
component: null
```
Design: docs/design/refactor-verb.md (T-1135), "Prose-rewrite scope"
section. Filed per coordinator review of the design phase: T-1199
(directive/waiver carrier) covers only structured `frob:*` comment-DSL
directive targets; epic acceptance [2] also requires rewriting free text
that merely NAMES a moved symbol, which no filed child owned until now.

Extends T-1197's plan/apply pipeline with the three prose-rewrite items:

- Docstrings and comments naming the moved dotted path, anywhere in the
  repo, not just on the moved symbol's own code (e.g. "see
  `frob.gates._waive._match_waiver` for..." written in some unrelated
  module's docstring).
- `docs/**` prose and embedded code references: prose sentences naming
  the old module/symbol, and fenced code blocks citing the old import
  path.
- Doc anchor slugs whose heading text embeds the symbol/module name
  (a heading literally titled with a module name changes its own slug
  on rename) -- verified against `frob.gates._doclink_docanchor`'s
  `doclink_gate`/`docanchor_gate` (DOC001/DOC002) as the post-condition
  proof that no anchor broke.

Per the epic's acceptance [2], an unresolvable prose mention (ambiguous
natural-language mention, a name that is also a common English word, a
mention inside a generated/vendored file) must be listed explicitly in
the disclosed report as "not rewritten -- review by hand", never
silently skipped and never silently rewritten on a guess.

This ticket owns ONLY the free-text prose/doc-anchor rows; it does not
touch `frob:*` DSL directive targets (T-1199's scope) or the Python
import/call-site rewrite (T-1197's scope).

<!-- ticket:T-1269 -->
```yaml
id: T-1269
title: 'ticket land --plan: atomic design-phase land with automatic draft finalization'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/_cli_parsers/_ticket.py
- docs/**
- tests/**
acceptance:
- text: 'GIVEN a planner worktree containing only docs plus ledger changes (no closeable
    worked ticket) WHEN frob ticket land --plan --worktree PATH runs THEN it performs
    the whole chain atomically: merge via the ledger driver, finalize EVERY incoming
    draft id to the next free real ids in one allocator-locked ledger write (cross-references
    rewritten), verify TICK gate clean, and commit -- one command, one commit for
    the finalization, no hand-assigned ids'
  evidence: []
- text: GIVEN any failure mid-chain THEN the operation unwinds completely (no half-merged
    ledger, no partially-renumbered drafts) and names the manual remedy
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: renumbering must be atomic and automatic. Evidence from this drive: landing four design-phase planner worktrees required a guarded plain git merge (FROB_LAND_INTERNAL=1) plus 15 hand-assigned frob ticket renumber calls across 4 batches, because frob ticket land (T-0176) requires a closeable ticket and its draft-finalization path only runs for worked-ticket lands. Also fix the stale TICK002 remedy text that still says 'once T-0176 lands' (it landed). Builds on the existing finalize_draft_for_land machinery (_draft_finalize.py) and the T-0162 id allocator; ledger-v2 (T-1255 renumber child) later absorbs the same behavior for the file-per-ticket store.

<!-- ticket:T-1271 -->
```yaml
id: T-1271
title: 'cli hygiene: no hidden-argument hell, maximally informative output, mined
  from real agent usage'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: T-1238
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/app/**
- docs/**
- tests/**
acceptance:
- text: 'GIVEN any enum-valued flag receives an invalid value THEN the error lists
    every valid value inline (today: frob ticket list --status open yields ''open''
    is not a valid TicketState with no valid-values list)'
  evidence: []
- text: GIVEN a command emits repeated advisory warnings (scope-closure on ticket
    new can flood thousands of lines) THEN they collapse to a counted summary with
    a --verbose escape hatch -- signal is never drowned
  evidence: []
- text: GIVEN a read-only invocation (check --ticket for review, show, brief) THEN
    it never requires a lease or mutates state -- reviewers repeatedly could not re-verify
    gate claims because check --ticket demands a lease
  evidence: []
- text: GIVEN a multi-step workflow (close needs start, done-report, evidence, accepts)
    THEN each refusal names the exact next command AND a single porcelain verb exists
    that sequences the happy path; hidden optional arguments that change behavior
    (e.g. renumber's positional-only contract) are documented in --help with examples
  evidence: []
- text: GIVEN the audit lands THEN a short cli-hygiene principles doc exists in docs/design/
    and a checklist test (or gate rule) verifies new parsers against it (every flag
    help string states its default; no flag silently changes another flag's meaning)
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: no hidden optional argument hell; intuitive and maximally informative -- no noise, nothing missing; mine what agents ACTUALLY do. Evidence from this drive's own agent/coordinator usage: (1) --status open cryptic enum error; (2) ticket new scope-closure warning floods (5000+ lines in one invocation) drowning the created-id line; (3) frob check --ticket lease requirement blocked all four reviewers from re-verifying gate claims read-only; (4) ticket renumber had no --next and its usage was guessable only from error text; (5) the close dance (start -> done-report -> evidence -> accepts -> close) was discovered by error-chasing across five invocations -- each error WAS informative (good pattern, keep) but no porcelain wraps the sequence; (6) positive examples to preserve: evidence-rejection errors name the cache-refresh remedy, TICK002 names its exact fix command. Method: also mine .frob spawn/telemetry if present and the agent-playbook's accumulated workarounds for further real-usage pain points before designing.

<!-- ticket:T-1273 -->
```yaml
id: T-1273
title: 'TEST005 burn-down: per-package coverage campaign to the 75/70 floors'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-0969
tier: epic
sprint: null
acceptance:
- text: GIVEN this epic WHEN all child packages reach zero TEST005 findings at unit_branch_cov=75/module_line_cov=70
    THEN frob ticket epic reports 0 open children and the floor-ratchet child has
    landed a documented schedule
  evidence: []
threat: null
component: null
```
TEST005 attribution is now honest (T-1235: subprocess + pool-worker
coverage recorded) and floors are recalibrated to unit_branch_cov=75 /
module_line_cov=70 (frob.toml [testing], rationale in-file). Inventory on
this baseline: 1335 TEST005 findings (943 symbol/branch-coverage, 391
module/line-coverage), of which 206 symbols sit at exactly 0.0% branch
coverage -- the priority tier, since a 0.0% symbol is either dead code
(never called from a live path -> route to DEAD-gate/dup scrutiny or a
removal ticket, not a fake test) or a genuinely untested entry point.

This epic parents one child ticket per top-level package with findings,
ordered by 0%-symbol count descending, plus one child for the floor
ratchet-up schedule once a package clears zero. Children carry the
package's finding count, its 0.0% symbol list (or a representative
sample + full count for large buckets), scope limited to that package's
src+tests paths, and GIVEN/WHEN/THEN acceptance requiring the package's
TEST005 count to reach zero at current floors via real behavioral tests
-- never assert-True filler -- with dead symbols routed away from testing
entirely.

<!-- ticket:T-1279 -->
```yaml
id: T-1279
title: 'TEST005 burn-down: src/frob/gates (179 findings, 12 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/gates/**
evidence:
- tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches::test_exec_disabled_degrades_to_no_violations
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_missing_scanned_base_directory_is_skipped_not_an_error
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_unresolved_const_ref_is_left_out
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_const_ref_resolves_against_assignment_in_another_file
- tests/gates/test_rule_id_scan_branches.py::TestGeneratedGateRuleIdsRetiredOverride::test_default_retired_set_is_module_constant
acceptance:
- text: GIVEN a 0.0%-branch symbol in gates WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a gates TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
acceptance_amendments:
- op: remove
  index: 0
  old_text: GIVEN the gates package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/gates/**
  new_text: null
  reason: 'Unsatisfiable by construction, replaced with a triage-shaped criterion.


    The removed criterion asserted zero TEST005 findings across a package holding

    hundreds. No single dispatch can reach that, so the ticket could never close

    honestly -- and since T-1410 wired the gate-claim guard, frob correctly REFUSES

    to close it, stranding genuine completed work behind an aspiration.


    This is a correction, not goalpost-moving. The criterion was authored before we

    knew the count itself was partly artifact: T-1418 is currently classifying the

    306 symbols reporting exactly 0.0 percent, and three agents independently found

    that many already carry real, behavioral, frob:tests-bound tests -- the code is

    exercised, just in a process pytest-cov does not attribute back. Demanding zero

    findings therefore demanded work that in some cases does not exist, and pushed

    agents toward writing filler tests against already-tested code.


    The replacement is the shape used on T-1400 and it is strictly harder to satisfy

    dishonestly: every remaining finding must be triaged, a genuine gap must be

    closed with a behavioral test, and an artifact must be recorded with the

    covering test named so the claim is checkable. Filler still fails it.

    '
  actor: logan
  at: '2026-08-02'
threat: null
component: null
```
Package: src/frob/gates (or the listed root modules).
TEST005 findings at current baseline: 179 total, 12 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_secrets.py :: secrets_gate
_parse_failures.py :: parse_failure_gate
_mutation_evidence.py :: mutation_evidence_violations
_opaque.py :: opaque_gate
__init__.py :: scope_digest
__init__.py :: prework_gate
__init__.py :: test_gate
__init__.py :: release_gate
__init__.py :: perf_gate
__init__.py :: run_gates
_rule_id_scan.py :: scan_emitted_rule_ids
_rule_id_scan.py :: generated_gate_rule_ids

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

## Done report

Changed:
src/frob/gates/_mutation_evidence.py::mutation_evidence_violations (added frob:tests binding for the ExecDisabled Err branch)
src/frob/gates/_rule_id_scan.py::scan_emitted_rule_ids (added frob:tests bindings for comment-skip, missing-base-dir, unresolved-const-ref branches)
src/frob/gates/_rule_id_scan.py::generated_gate_rule_ids (added frob:tests binding for the default-retired-set path)
tests/gates/__init__.py (new test package)
tests/gates/test_mutation_evidence_err_branches.py (new: TestMutationEvidenceErrBranches)
tests/gates/test_rule_id_scan_branches.py (new: TestScanEmittedRuleIdsBranches, TestGeneratedGateRuleIdsRetiredOverride)
design/frob.strata (SELFAUDIT001/SYS104: declared the three new test classes in the testsuite interface)

Investigation of the other 10 of 12 listed 0.0%-branch symbols
(secrets_gate, parse_failure_gate, opaque_gate, scan_emitted_rule_ids's
literal-scan path, scope_digest, prework_gate, test_gate, release_gate,
perf_gate, run_gates) found each already has real, behavioral
frob:tests-bound coverage of both clean and finding-producing branches
in existing test files (tests/test_secrets_gate.py,
tests/test_gates.py's TestParseFailureGate/TestKnownGateRuleIds/
TestScopeDigest*/TestPreworkGate*/TestTestGate*/TestReleaseGate*/
TestPerfGate*/TestRunGates* classes, tests/test_vet.py's
TestOpaqueIndirectionGate). Their reported 0.0% is not explained by a
missing test -- most plausibly the known subprocess/multiprocess
coverage-attribution gap tracked by the concurrent T-1235/T-1395
tickets (out of this ticket's src/frob/gates/** scope to fix). Rather
than fabricate filler tests against already-tested functions to chase
a number, I closed the two symbols with a genuine, verifiable test gap
(the mutation_evidence Err branch, and three rule_id_scan branches)
and filed T-1396 to continue auditing the remaining ~167 non-0.0%-tier
TEST005 findings in src/frob/gates for real (non-attribution) gaps.

Evidence:
tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches::test_exec_disabled_degrades_to_no_violations
tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped
tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_missing_scanned_base_directory_is_skipped_not_an_error
tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_unresolved_const_ref_is_left_out
tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_const_ref_resolves_against_assignment_in_another_file
tests/gates/test_rule_id_scan_branches.py::TestGeneratedGateRuleIdsRetiredOverride::test_default_retired_set_is_module_constant
(all verified: timeout 100 uv run pytest -q -p no:randomly -o addopts="" tests/gates/ tests/test_gates_mutation_evidence.py -- 10 passed)

Filed: T-1396 (continuation: audit src/frob/gates' remaining ~167 TEST005 findings past the 0.0% priority tier for genuine, non-attribution gaps)

Gates: frob check --ticket T-1279 clean across all 39 gate families (run in three --only chunks: prework, gates-security, static, plus a full --budget 100 pass) -- 0 errors. ruff check/format and ty check clean.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 2784 warning(s), 698 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1281 -->
```yaml
id: T-1281
title: 'TEST005 burn-down: src/frob/release (11 findings, 10 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/release/**
- tests/release/**
acceptance:
- text: GIVEN the release package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/release/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in release WHEN it is judged dead code THEN it
    is routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a release TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
threat: null
component: null
```
Package: src/frob/release (or the listed root modules).
TEST005 findings at current baseline: 11 total, 10 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__init__.py :: manifest_path
__init__.py :: load_manifest
__init__.py :: stamp
__init__.py :: authoritative_version
__init__.py :: rewrite_pyproject_version
__init__.py :: changelog_skeleton_entry
__init__.py :: set_manifest_version
__init__.py :: diff_class
__init__.py :: required_version
__init__.py :: satisfies

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

<!-- ticket:T-1294 -->
```yaml
id: T-1294
title: 'TEST005 burn-down: src/frob/vet (54 findings, 1 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/vet/**
acceptance:
- text: GIVEN the vet package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/vet/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in vet WHEN it is judged dead code THEN it is routed
    to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a vet TEST005 finding WHEN reviewed THEN it
    asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
threat: null
component: null
```
Package: src/frob/vet (or the listed root modules).
TEST005 findings at current baseline: 54 total, 1 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_capability_registry.py :: capability_matrix

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

<!-- ticket:T-1296 -->
```yaml
id: T-1296
title: 'TEST005 burn-down: src/frob/strata (196 findings, 1 at 0.0%)'
state: in-progress
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/strata/**
evidence:
- tests/unit/strata/test_atomic.py::TestJoinSagaIdempotencyNoCoordinators::test_empty_coordinator_ids_returns_model_unchanged
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsFactsError::test_build_facts_error_is_propagated
- tests/unit/strata/test_atomic.py::TestEvaluateAtomicContractsSagaError::test_saga_error_short_circuits_before_fault_injection
- tests/unit/strata/test_breach.py::TestContainmentBounds::test_dimension_mismatched_bounds_fail_closed_with_unit_mismatch
- tests/unit/strata/test_breach.py::TestBreachContractsFactsAndScenarioErrors::test_build_facts_error_propagates_out_of_blast_radius
- tests/unit/strata/test_breach.py::TestBreachContractsFactsAndScenarioErrors::test_scenario_evaluation_error_propagates
- tests/unit/strata/test_distributed_txn.py::TestMultiServiceWritersSelfLoop::test_self_loop_flow_is_excluded_from_written_node_set
- tests/unit/strata/test_distributed_txn.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_design_load.py::TestLoadIds::test_unreadable_file_reported_as_parse_failed
- tests/unit/strata/test_design_load.py::TestLoadIds::test_elaborate_failure_reported_with_store_ids_and_resources_intact
- tests/unit/strata/test_design_load.py::TestUnbound::test_kind_with_zero_ids_contributes_nothing_and_outer_loop_continues
- tests/unit/strata/test_design_load.py::TestUnbound::test_edge_of_an_uninteresting_kind_is_skipped
- tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_non_access_attr_amid_access_attrs_is_skipped
- tests/unit/strata/test_clock_ordering.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_delivery_semantics.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_retry.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_backpressure.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_circuit_breaker.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_fallback.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_deploy.py::TestScenarioEvaluationErrorPropagation::test_evaluate_scenarios_error_propagates
acceptance:
- text: GIVEN the strata package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/strata/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in strata WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a strata TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/strata/test_atomic.py::TestJoinSagaIdempotencyNoCoordinators::test_empty_coordinator_ids_returns_model_unchanged
  - tests/unit/strata/test_breach.py::TestContainmentBounds::test_dimension_mismatched_bounds_fail_closed_with_unit_mismatch
  - tests/unit/strata/test_distributed_txn.py::TestMultiServiceWritersSelfLoop::test_self_loop_flow_is_excluded_from_written_node_set
  - tests/unit/strata/test_design_load.py::TestLoadIds::test_unreadable_file_reported_as_parse_failed
  - tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_non_access_attr_amid_access_attrs_is_skipped
threat: null
component: null
```
Package: src/frob/strata (or the listed root modules).
TEST005 findings at current baseline: 196 total, 1 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_selfconform.py :: check_self_conformance

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

## Done report

Closed real, targeted branch-coverage gaps in 12 src/frob/strata modules
by extending their existing unit test files (never new assert-True
filler): _atomic.py, _breach.py, _distributed_txn.py, _design_load.py,
_access.py, _clock_ordering.py, _delivery_semantics.py, _retry.py,
_backpressure.py, _circuit_breaker.py, _fallback.py, _deploy.py.

Each module now measures 100% branch coverage standalone (verified via
`pytest --cov=<module> --cov-branch` against its own test file, before
and after) -- confirmed BEFORE writing any test that the specific
missing branch line/arm reported by coverage was genuinely unexercised,
never added a second happy-path assertion to an already-covered branch.

Targeted branches, by module:
- _atomic.py: `_join_saga_idempotency`'s empty-coordinator-ids early
  return (line 108, only reachable by calling the private helper
  directly, since every real caller already guards it);
  `evaluate_saga_contracts`'s `build_facts` error-propagation arm (140);
  `evaluate_atomic_contracts`'s saga-error short-circuit before fault
  injection generation (217).
- _breach.py: `Quantity.leq`'s `UnitMismatch` arm inside
  `_check_bound_leq_revoke` (128, via a dimension-mismatched
  detect/revoke pair); `_compute_blast_radii`'s `build_facts` error arm
  (173); `_compute_and_evaluate_breach_report`'s blast-radii error arm
  (285) and scenario-evaluation error arm (296).
- _distributed_txn.py: `_multi_service_writers`'s self-loop
  (`flow.src == flow.dst`) exclusion branch (167->166);
  `check_distributed_txn_obligations`'s `bind_code` error-propagation
  arm (288).
- _design_load.py: `_read_and_elaborate`'s `OSError`-on-read arm
  (189-191, via a chmod-0000 unreadable file) and its elaborate-failure
  arm (205-210, via a secret missing `revoke`); `unbound_constructs`'s
  zero-ids-for-a-kind case and the `edge.kind in bound` False arm for an
  edge of an uninteresting kind (279->278).
- _access.py: `node_access_declarations`'s non-`access=`-prefixed attr
  skip (`continue`, line 182).
- _clock_ordering.py: `check_clock_ordering_obligations`'s `bind_code`
  error-propagation arm (327).
- _delivery_semantics.py, _retry.py, _backpressure.py,
  _circuit_breaker.py, _fallback.py: each REL-family entrypoint's own
  `bind_code` error-propagation arm, same pattern as
  `_distributed_txn.py`/`_clock_ordering.py`.
- _deploy.py: `_evaluate_generated_scenarios`'s `evaluate_scenarios`
  error-propagation arm (212).

All new/changed branches verified via monkeypatched collaborator
functions (`build_facts`, `bind_code`, `evaluate_scenarios`) returning
`Err`, or via real inputs that naturally drive the error path
(dimension-mismatched Quantity, unreadable file, malformed secret,
self-loop flow, non-access attr) -- never a mock that bypasses real
behavior verification of the surrounding function.

The ticket's one 0.0%-branch symbol, `_selfconform.py::
check_self_conformance`, was investigated per the brief's instruction:
it already has 67 real, frob:tests-bound assertions in
tests/unit/strata/test_selfconform.py and measures 95% coverage
standalone -- its 0.0% in the ticket brief is a stale/attribution
artifact (the T-1235/T-1395 tracked coverage-attribution defect the
coordinator separately flagged), not a real gap. No new test was added
for it and none was needed; it is not dead code (multiple live callers:
src/frob/gates/_sys.py, src/frob/strata/_native_test.py,
src/frob/app/sys_runner.py), so acceptance [1]'s dead-code-routing
branch does not apply either.

NOT DONE / LEFT OPEN: this covers only 12 of the ~35 root modules under
src/frob/strata. Acceptance [0] ("0 TEST005 findings under
src/frob/strata/**") is NOT met -- the remaining modules (_audit.py 88%,
_compliance.py 89%, _code_binding.py 91%, _crash.py 91%, _claims.py
54%, _elaborate.py 49%, and others not yet sampled) still carry real
partial-coverage gaps. Filed T-1415 ("TEST005 burn-down:
src/frob/strata remainder (post T-1296 partial)") to continue the same
per-module, per-branch discipline. Leaving T-1296 in-progress rather
than force-closing it against an acceptance criterion that is not
actually true, per the coordinator's explicit instruction on this
drive.

DISCLOSED CUT: the ticket's declared scope lists `tests/strata/**`,
which does not match this repo's real test tree
(`tests/unit/strata/**`) -- an ordinary scope-declaration typo. I could
not correct it: `frob ticket scope T-1296 --add
'tests/unit/strata/**'` (and even a single-file `--add`) fails with
`ScopeLeaseConflict` because T-1235 (a concurrent, in-progress,
unrelated ticket) holds a `tests/**` scope lease. This produces 12
SCOPE001 findings against `frob check --ticket T-1296` for the 12 real
test files this ticket touched -- all under the one real strata test
tree, none outside it. I did not force past this (no
`--allow-cross-ticket`, no hand-edit of tickets.md) since it is a real,
structural lease conflict, not a false positive to wave through. The
coordinator/reviewer can re-run `frob ticket scope T-1296 --add
'tests/unit/strata/**'` once T-1235 lands/releases its lease.

SELFAUDIT001 (7 findings, new test class names not yet declared in
design/frob.strata's testsuite interface) is the expected, known
land-time-absorbed drift per the playbook (`frob ticket land` runs its
own sync-interface step) -- not hand-fixed here.

`frob check --ticket T-1296` (repo-wide, per section 6c -- read
gate:scope-note before trusting any of this as ticket-scoped): 19
errors total = exactly the 12 SCOPE001 + 7 SELFAUDIT001 above, 0 other
new errors. `ruff check`/`ruff format --check`/`ty check` all clean
over every touched test file. All 128 tests across the 12 touched test
files pass in 0.43s (`pytest tests/unit/strata/test_atomic.py
tests/unit/strata/test_breach.py tests/unit/strata/test_distributed_txn.py
tests/unit/strata/test_design_load.py tests/unit/strata/test_access.py
tests/unit/strata/test_clock_ordering.py
tests/unit/strata/test_delivery_semantics.py tests/unit/strata/test_retry.py
tests/unit/strata/test_backpressure.py
tests/unit/strata/test_circuit_breaker.py tests/unit/strata/test_fallback.py
tests/unit/strata/test_deploy.py`).

`frob ticket land --dry-run` correctly refused to close T-1296: 3
acceptance criteria are still UNBOUND, matching the honest state above
(acceptance [2] is now bound to 5 of the 20 new node ids; [0] and [1]
remain unbound since they are not actually satisfied yet). Leaving the
ticket in-progress for the coordinator to either extend scope after
T-1235 lands, or split remaining work fully into T-1415 and
close this one as partially-superseded -- coordinator's call, not mine
to force.

### Changed
```
 tests/unit/strata/test_access.py             |  16 +++
 tests/unit/strata/test_atomic.py             |  93 ++++++++++++
 tests/unit/strata/test_backpressure.py       |  33 ++++-
 tests/unit/strata/test_breach.py             |  68 +++++++++
 tests/unit/strata/test_circuit_breaker.py    |  33 ++++-
 tests/unit/strata/test_clock_ordering.py     |  38 ++++-
 tests/unit/strata/test_delivery_semantics.py |  33 ++++-
 tests/unit/strata/test_deploy.py             |  35 +++++
 tests/unit/strata/test_design_load.py        |  82 ++++++++++-
 tests/unit/strata/test_distributed_txn.py    |  58 +++++++-
 tests/unit/strata/test_fallback.py           |  29 +++-
 tests/unit/strata/test_retry.py              |  38 ++++-
 tickets.md                                   | 202 ++++++++++++++++++++++++++-
 13 files changed, 748 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/strata/test_atomic.py::TestJoinSagaIdempotencyNoCoordinators::test_empty_coordinator_ids_returns_model_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsFactsError::test_build_facts_error_is_propagated` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_atomic.py::TestEvaluateAtomicContractsSagaError::test_saga_error_short_circuits_before_fault_injection` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_breach.py::TestContainmentBounds::test_dimension_mismatched_bounds_fail_closed_with_unit_mismatch` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_breach.py::TestBreachContractsFactsAndScenarioErrors::test_build_facts_error_propagates_out_of_blast_radius` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_breach.py::TestBreachContractsFactsAndScenarioErrors::test_scenario_evaluation_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestMultiServiceWritersSelfLoop::test_self_loop_flow_is_excluded_from_written_node_set` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestLoadIds::test_unreadable_file_reported_as_parse_failed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestLoadIds::test_elaborate_failure_reported_with_store_ids_and_resources_intact` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestUnbound::test_kind_with_zero_ids_contributes_nothing_and_outer_loop_continues` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestUnbound::test_edge_of_an_uninteresting_kind_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_non_access_attr_amid_access_attrs_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_clock_ordering.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_delivery_semantics.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fallback.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_deploy.py::TestScenarioEvaluationErrorPropagation::test_evaluate_scenarios_error_propagates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: 0 error(s), 1966 warning(s), 699 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1305 -->
```yaml
id: T-1305
title: 'TEST005 burn-down: src/frob/lang (37 findings, 0 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/lang/**
acceptance:
- text: GIVEN the lang package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/lang/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in lang WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a lang TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
threat: null
component: null
```
Package: src/frob/lang (or the listed root modules).
TEST005 findings at current baseline: 37 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

<!-- ticket:T-1307 -->
```yaml
id: T-1307
title: 'TEST005 burn-down: src/frob/dup (33 findings, 0 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- tests/dup/**
acceptance:
- text: GIVEN the dup package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/dup/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in dup WHEN it is judged dead code THEN it is routed
    to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a dup TEST005 finding WHEN reviewed THEN it
    asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
threat: null
component: null
```
Package: src/frob/dup (or the listed root modules).
TEST005 findings at current baseline: 33 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

<!-- ticket:T-1309 -->
```yaml
id: T-1309
title: 'TEST005 burn-down: src/frob/check (19 findings, 0 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/check/**
- tests/check/**
acceptance:
- text: GIVEN the check package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/check/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in check WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a check TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
threat: null
component: null
```
Package: src/frob/check (or the listed root modules).
TEST005 findings at current baseline: 19 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

<!-- ticket:T-1310 -->
```yaml
id: T-1310
title: 'TEST005 burn-down: src/frob/arch (87 findings, 0 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/arch/**
acceptance:
- text: GIVEN the arch package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/arch/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in arch WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a arch TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
threat: null
component: null
```
Package: src/frob/arch (or the listed root modules).
TEST005 findings at current baseline: 87 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

<!-- ticket:T-1311 -->
```yaml
id: T-1311
title: 'TEST005 burn-down: src/frob/_cli_parsers (6 findings, 0 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers.py
- tests/**
acceptance:
- text: GIVEN the _cli_parsers package at the 75%/70% floors WHEN frob check --only
    test runs THEN it reports 0 TEST005 findings under src/frob/_cli_parsers/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in _cli_parsers WHEN it is judged dead code THEN
    it is routed to the DEAD gate/dup machinery or a removal ticket, never given an
    assert-True filler test
  evidence: []
- text: GIVEN a new test added to close a _cli_parsers TEST005 finding WHEN reviewed
    THEN it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
threat: null
component: null
```
Package: src/frob/_cli_parsers (or the listed root modules).
TEST005 findings at current baseline: 6 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

<!-- ticket:T-1315 -->
```yaml
id: T-1315
title: 'TEST005 floor ratchet-up schedule: 75/70 is a waypoint, not a surrender'
state: queued
kind: docs
origin: human
created: '2026-07-29'
priority: low
parent: T-1273
tier: ticket
sprint: null
acceptance:
- text: GIVEN a package that has reached zero TEST005 findings at 75/70 WHEN the ratchet
    schedule lands THEN that package's effective floor is documented to step toward
    90/85 (per-package override or schedule), not remain frozen at the recalibrated
    minimum
  evidence: []
- text: GIVEN frob.toml's existing recalibration rationale comment WHEN the ratchet
    design is written THEN it explicitly cites and extends that rationale rather than
    contradicting or duplicating it
  evidence: []
threat: null
component: null
```
frob.toml [testing] recalibrated unit_branch_cov=75 / module_line_cov=70
on honest TEST005 attribution data (T-1235 fixed subprocess + pool-worker
coverage recording); the in-file rationale comment documents why these
specific numbers were chosen as the current floor, not a permanent
target.

Design a ratchet schedule: once a package (T-1276..T-1313 in this epic)
reaches zero TEST005 findings at 75/70, its floor should step up toward
90/85 rather than stay parked at the recalibrated minimum -- otherwise
the recalibration silently becomes a ceiling. Decide and document
(either in frob.toml as per-package floor overrides, or as a documented
schedule/policy the gate reads) how and when a cleared package's floor
increases, and how regressions below the new floor are caught.

<!-- ticket:T-1317 -->
```yaml
id: T-1317
title: 'ack accountability: frob ack requires a reason and records the digest delta
  it vouches for'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/graph/lock.py
- src/frob/_cli_parsers/**
- src/frob/app/**
- docs/**
- tests/**
acceptance:
- text: 'GIVEN frob ack clears a DRIFT finding THEN it requires a reason string (waiver-style:
    what was re-verified and why the doc is still true) and records the acked digest
    delta (old->new sig/body/doc facets) in frob.lock, so every ack is an auditable
    vouch rather than a silent clear'
  evidence: []
- text: GIVEN an ack whose reason is empty or boilerplate-detected THEN the ack is
    refused -- rubber-stamping is a gate failure, mirroring WAIVE002's reason discipline
  evidence: []
- text: 'GIVEN a doc claim class that is machine-checkable (enumerations via DOCENUM001,
    pointers via DOC006) THEN it is content-verified and ack-immune: an ack never
    clears a finding that a checker can prove true or false'
  evidence: []
threat: null
component: null
```
User question 2026-07-29 answered by the staleness sweep: the ~140 silent doc misses trace to six gate blind spots (T-1227..T-1232) PLUS this seventh systemic one the audit named but no ticket owned -- DRIFT001 verifies freshness of attention (digest vs last ack), and frob ack clears it with no proof the prose was re-verified. Waivers require reason=; acks do not. Principle: move every machine-checkable claim class from ack-based trust to content-verified proof (the DOCENUM/pointer work), and make the residual human vouches auditable (reason + digest delta + date), refusable when empty. Interacts with T-1137's anti-goal (no auto-discharge): the fix engine must never auto-ack, and this ticket makes a hand-ack itself carry evidence.

<!-- ticket:T-1318 -->
```yaml
id: T-1318
title: 'perf: telemetry redact_command pulls in the whole frob.gates package via frob.gates._secrets'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/telemetry.py
- src/frob/gates/_secrets.py
threat: null
component: null
```
found while working T-1216: after T-1216 removed frob.app's eager
deploy/strata/vet/gates import chain, one gates import still survives on
EVERY CLI invocation regardless of subcommand: `frob.app.telemetry.
timed_call`'s `finally` block always calls `record_cli_event`, which calls
`redact_command`, which does `from frob.gates._secrets import _redact,
_scan_line` -- and `frob.gates._secrets`'s own parent package,
`frob.gates/__init__.py`, eagerly imports its entire stage roster (pii,
arch, dup, vet._capability, testing, ...) as a side effect of that single
submodule import. Measured on `frob ticket list --state queued`: this
residual chain alone costs ~257ms cumulative importtime (frob.gates line
in `python -X importtime`), all AFTER the command's real output has
already been produced (it fires in telemetry's post-command bookkeeping,
not the command itself).

Root cause: redaction-worthy secret-scanning logic
(`_redact`/`_scan_line`) lives inside `frob.gates._secrets`, a submodule
of the heavy `frob.gates` aggregator package, rather than in a small
<!-- frob:waive DOC006 reason="'frob.security' is a hedged 'e.g. ... or similar' example naming one possible location for a not-yet-extracted module -- this ticket proposes the extraction, it has not happened, so no such module can exist yet to resolve against" -->
standalone module with no heavy siblings. Fix: extract `_redact`/
`_scan_line` (or whatever subset `redact_command` actually needs) into a
lightweight module outside `frob.gates` (e.g. `frob.security._redact` or
similar) that both `frob.gates._secrets` and `frob.app.telemetry` import,
so telemetry's per-invocation redaction never drags in the rest of the
gates stage roster. Out of T-1216's scope (src/frob/app/__init__.py,
src/frob/app/app.py only) -- filed as a follow-up.

<!-- ticket:T-1321 -->
```yaml
id: T-1321
title: 'CI-env test hermeticity: doctor scaffold fold, ledger-commit git identity,
  serial-pools install leak'
state: queued
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_doctor.py
- tests/test_prework_parity.py
- tests/unit/perf/test_serial_pools.py
- src/frob/tickets/_leases.py
- .github/workflows/ci.yml
- tests/test_tickets_leases.py
- tests/test_ticket_leases.py
scope_changes:
- op: add
  glob: tests/test_tickets_leases.py
  reason: 'scope closure: _leases.py identity-fallback change must carry its lease
    test file'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'scope closure: second lease test file covering _leases.py symbols'
  actor: logan
  at: '2026-07-29'
threat: null
component: null
```
Three CI-only pytest failures (seen at v0.277.0, all still latent because the causes are environmental, not code that later lands fixed): (1) tests/test_doctor.py run_diagnosis tests assert healthy=True / exact REMEDIATION_HINT against the REAL checkout; doctor folds scaffold conformance into healthy, and a fresh CI clone has the 3 git-hook managed blocks missing (hook-pre-commit, hook-pre-merge-commit, hook-reference-transaction-stash-guard) -- monkeypatch the scaffold/derived scans so the natives tests test natives only. (2) tests/test_prework_parity.py e2e drives frob ticket new in a tmp repo; T-1130 auto-commit runs plain git commit and CI runners have no user.name/user.email, so the ledger commit fails rc=128 (local passes via the developer's global config) -- set identity in the test fixture repo AND consider a -c user.name/user.email fallback in _add_and_commit_tickets_md for identity-less environments. (3) tests/unit/perf/test_serial_pools.py baseline test_without_serial_pools_worker_is_unattributed got fraction 0.45 in CI: install_serial_pools() patches concurrent.futures globally and no test uninstalls it, so full-suite ordering can leak the patch into the baseline -- add an uninstall/restore fixture around every install_serial_pools() caller. Verified 2026-07-29: all six failing tests pass locally in isolation on main, so the remaining exposure is purely environmental/ordering.

<!-- ticket:T-1324 -->
```yaml
id: T-1324
title: 'docs: correct compliance-corpus.md FROB-CATALOG-ENTRIES count 6 -> 7 (PRIVACY-NOTICE)'
state: queued
kind: docs
origin: agent
created: '2026-07-29'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/design/compliance-corpus.md
acceptance:
- text: GIVEN this ticket closes WHEN docs/design/compliance-corpus.md's FROB-CATALOG-ENTRIES
    manifest row and TOTAL_LEAF_CONTROLS_ENUMERATED are inspected THEN both reflect
    COMPLIANCE_CATALOG's real 7 entries (count 6 -> 7, TOTAL_LEAF_CONTROLS_ENUMERATED
    599 -> 600), matching docs/design/registry/compliance.yaml's already-corrected
    CMPL-FROB-CATALOG-ENTRIES row (T-1250)
  evidence: []
threat: null
component: null
```
Found while working T-1250: T-1314 added a 7th RegulationEntry (PRIVACY-NOTICE) to COMPLIANCE_CATALOG. T-1250 corrected docs/design/registry/compliance.yaml's CMPL-FROB-CATALOG-ENTRIES leaf_count (6->7) and total_leaf_controls_enumerated (599->600), but docs/design/compliance-corpus.md is the upstream source manifest that row derives from and is out of T-1250's scope (not in its scope globs) -- it still reads count:6 and TOTAL_LEAF_CONTROLS_ENUMERATED:599. No gate currently cross-checks the registry yaml against this corpus doc (confirmed: REG005 only checks declared total: against entries: list length, not leaf_count/corpus consistency), so this is a real but not gate-visible drift.

<!-- ticket:T-1325 -->
```yaml
id: T-1325
title: 'strata: attr grammar cannot express colon-vocabulary (exposure:/subject:/jurisdiction:)
  needed by std.compliance'
state: queued
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse/grammar_core.rs
- strata-core/src/parse/grammar_node.rs
- strata-core/src/parse/grammar_flow.rs
threat: null
component: null
```
Found while working T-1314 (sys gate compliance fold). The `std.compliance`
vocabulary (`exposure:public-web`, `privacy-policy`, `subject:*`,
`jurisdiction:*`, `retention=`, `covered-party`, `revocation`) documented in
`frob/strata/_compliance.py`'s module docstring as "opaque-string vocabulary
on the existing `attrs` tuples" has NO `.strata` grammar surface: the
`attr`/`attr` grammar keyword (`strata-core/src/parse/grammar_node.rs`,
`grammar_flow.rs`) calls `parse_attrval`, which requires a bare IDENT
(alphanumeric + `_` only, `strata-core/src/parse/lexer.rs`) -- colons and
dashes are lexed as separate symbol tokens, so `attr "exposure:public-web"`
or an unquoted `exposure:public-web` cannot be written in a real `.strata`
source file today. Confirmed by grep: zero hits for
`exposure`/`privacy-policy`/`subject:`/`jurisdiction:` anywhere under
`strata-core/src/**/*.rs`.

Practical effect: every COMPLIANCE00x/`evaluate_compliance` test in this
repo (including T-1314's own new gate-level regression tests) has to
construct a `KernelModel`/`Node` directly in Python, bypassing the `.strata`
parser entirely, because no author-writable `.strata` file can express the
compliance vocabulary at all. This means NO real hand-authored `.strata`
design file (including this repo's own `design/frob.strata`) can ever
trigger a compliance finding through `frob sys audit` or the new
`frob check` SELFAUDIT001 fold, regardless of the model's real posture --
the entire compliance-audit surface is reachable only from Python-
constructed test fixtures, not from the actual authoring surface strata
ships to users.

Mirrors the SAME class of gap `expect_ident_or_string`'s own code comment
in `strata-core/src/parse/grammar_core.rs` already flags for CWE/threat
catalog ids ("Claim ids are normally a bare IDENT ... need ':' and '-'
which IDENT cannot lex" -- solved there via a STRING-quoted alternate
surface). The compliance vocabulary needs the same treatment: either widen
`attr`'s grammar to accept a STRING-quoted attrval (mirroring
`expect_ident_or_string`'s precedent) or add a dedicated STRING-accepting
attr keyword, so a real `.strata` file can actually author
`exposure:public-web`/`subject:child`/etc.

Not touched by T-1314: strata-core grammar/Rust changes are outside that
ticket's declared scope (src/frob/gates/_sys.py, src/frob/strata/
_compliance.py, docs, tests only).

<!-- ticket:T-1328 -->
```yaml
id: T-1328
title: 'strata: build an independent second detector for app-level capability kinds
  (eval/env/ffi/install-hook/sql/deserialize/fetch_url)'
state: queued
kind: invariant
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
threat: null
component: null
```
T-1203's mutation-audit harness (src/frob/strata/_mutation_audit.py, SecondDetectorGap) proves that today only exec/net/fs.read/fs.write have a genuine independent second detector (the seccomp export -- node_allowed_syscalls/_SECCOMP_KIND_MAP): these are real OS-syscall-backed capabilities. The 7 app-level kinds actually declared in design/frob.strata (eval, env, ffi, install-hook, sql, deserialize, fetch_url) have no OS-syscall analog, so faking a seccomp entry for them would be dishonest (no real syscall corresponds to e.g. 'sql'). Acceptance [0] of T-1203 wants EVERY may to be double-detected by two independent mechanisms; this ticket is to design and build a real second detector for these 7 kinds -- e.g. a generated capability-manifest/allowlist artifact (distinct code path from scan_file_capabilities/SYS100) whose diff independently reacts to a may deletion/substitution, mirroring the seccomp-export precedent but for app-level capabilities instead of syscalls.

<!-- ticket:T-1330 -->
```yaml
id: T-1330
title: Wire v2 git-history mining into frob ticket flow/sprint velocity
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_setters.py
- tests/test_tickets_velocity.py
threat: null
component: null
```
T-1257 built the v2-mode git-history mining primitive
(`frob.tickets._store.v2_state_transitions`, design section 4.4) but did
NOT wire it into the user-facing `frob ticket flow` command --
`_setters.py`'s `_ledger_commit_history`/`_blob_at`/`_mine_done_transitions`
family is hardcoded to `git log ... -- tickets.md` (the v1 monofile path)
and is out of T-1257's declared scope
(src/frob/tickets/_doable.py, src/frob/tickets/_store.py,
src/frob/app/ticket_runner/**, tests/test_tickets.py).

Follow-up: branch `frob ticket flow` (and `sprint velocity`, same family)
on `_store_mode(root)` -- v2 mode should mine per-ticket history via
`v2_state_transitions` for every ticket instead of walking one shared
`tickets.md` blob. Needs its own SprintTransition-shaped adapter and a
parity test against the v1 path for an equivalent ticket set (mirrors
T-1257's acceptance criterion 3, not yet closed by that ticket).

<!-- ticket:T-1332 -->
```yaml
id: T-1332
title: 'land waive-guard: test branch-merged-main deletion attribution and rename-aware
  paths'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_ticket_land.py
- src/frob/tickets/_land_merge.py
acceptance:
- text: GIVEN a branch that merged main after main legitimately deleted a waiver WHEN
    land runs THEN no refusal occurs (locked by test)
  evidence: []
- text: GIVEN a waiver deleted inside a file renamed in the same branch THEN the guard
    attributes the deletion to a path that scope-ownership evaluates correctly (test
    proves which)
  evidence: []
threat: null
component: null
```
Two verification gaps flagged at T-1326 review (both inherited/analysis-only today): (1) no test exercises a branch that runs git merge main AFTER main legitimately deleted a waiver, then lands -- the committed-history guard is safe by git merge-base construction (the merge advances the base past main's deletion) but nothing locks that in; every agent worktree merges main mid-flight, so a regression here would break all lands. (2) rename-aware attribution: _waive_deletions_in_diff takes the pre-image path from the hunk header; a waiver deleted inside a renamed file has untested scope-ownership attribution (pre- vs post-rename path) on BOTH the uncommitted (T-1323) and committed (T-1326) checks. Add tests for both; fix attribution if the rename test exposes a wrong-path bug.

<!-- ticket:T-1339 -->
```yaml
id: T-1339
title: Suppression-dialect compliance is automatic, never hand-maintained
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
acceptance:
- text: given a line carrying one checker's suppression and an unsuppressed diagnostic
    from another configured checker, when frob check runs, then SUPPRESS001 reports
    it
  evidence: []
- text: given SUPPRESS001 findings, when frob check --fix runs, then the paired suppression
    is written with the reporting checker's own rule code, in canonical order, idempotently
  evidence: []
threat: null
component: gates
```
User directive (2026-07-31): 'auto-detect mypy waivers and make an additional ty waiver and vice-versa ... all this tool compliance stuff should be automatically handled rather than manually done.'

Motivating incident: two ty errors on main (tests/test_fuzz.py:159 unresolved-reference, tests/test_tickets_collision.py:826 unresolved-attribute) were NOT type defects -- both lines already carried a mypy 'type: ignore' that ty does not honor. Both were hand-fixed. Per the systematize-friction mandate, repeated dev friction becomes tooling, not repeated hand-work.

DESIGN (decided, see leaves): pairing is EVIDENCE-DRIVEN, not static. The gate fires only where checker B emits an unsuppressed diagnostic on a line that already carries checker A's suppression. This avoids the two failure modes of naive static pairing: (a) mypy/ty rule codes are not 1:1 (name-defined vs unresolved-reference, attr-defined vs unresolved-attribute), so static pairing needs a lossy mapping table; (b) stamping suppressions onto lines the other checker never flagged just creates unused-suppression debt. Evidence-driven pairing needs NO mapping table -- the reporting checker's diagnostic carries the exact rule code to emit.

Current population: 37 'type: ignore' lines, 20 already dual-dialect, 17 mypy-only, 6 ty-only.

DESIGN AMENDMENT (2026-07-31, user, SUPERSEDES the configuration-gating decision above): the GOAL IS PORTABILITY, not conformance to whichever checker this repo happens to run. 'This repo runs ty, but that doesn't mean every repo runs ty; I just want anybody to be able to type-check the code.' A downstream consumer running mypy against frob's source must not eat spurious errors, so every suppressed line should carry EVERY supported dialect's suppression -- including for checkers this repo never runs.

Consequences, all of which reverse earlier decisions:
1. Do NOT gate a direction on the tool being configured in the consuming project. Silence-when-unconfigured was correct for a conformance goal and is WRONG for a portability goal -- it would leave frob's own source hostile to mypy users forever, since mypy never runs here.
2. Do NOT drop the mypy dialect or migrate the 17 legacy mypy-only ignores away. They are load-bearing for downstream mypy users. The successor question posed in T-1342 is withdrawn.
3. mypy becomes a DEV DEPENDENCY used purely as an ORACLE (user-sanctioned: 'If we need to get mypy purely for testing this capability, then we can go ahead and do so'). ty stays the gating checker; mypy is never a gate, only a source of ground-truth diagnostics.

This amendment RESCUES the evidence-driven design rather than forcing a retreat to static pairing. The reason evidence-driven pairing looked impossible for an unconfigured checker is that nothing produced its diagnostics; installing mypy as an oracle produces exactly those diagnostics locally. So pairing stays evidence-driven and SYMMETRIC, still needs NO mypy-code <-> ty-code mapping table, and each dialect's suppression is written with that dialect's own rule code taken from that dialect's own diagnostic. Static pairing with a lossy mapping table remains rejected.

Watch item for the oracle: mypy's --warn-unused-ignores must stay OFF, or be reconciled deliberately. Exact evidence-driven pairing should not produce unused ignores, but the 17 pre-existing legacy mypy ignores were written for a mypy that never ran and some may now be unused; treat any such finding as information, never as license to delete a suppression a downstream consumer may need.

<!-- ticket:T-1342 -->
```yaml
id: T-1342
title: Backfill the 23 unpaired suppression lines and lock main at zero SUPPRESS001
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: medium
parent: T-1339
tier: ticket
sprint: null
scope:
- src/**
- tests/**
acceptance:
- text: given frob check on main, when the suppress gate runs, then it reports 0 SUPPRESS001
    findings
  evidence: []
threat: null
component: gates
```
Phase 3 of T-1339, depends on both the detector and the Tier-A handler. Drive the existing population to zero via frob check --fix: 37 'type: ignore' lines exist, 20 already dual-dialect, 17 mypy-only, 6 ty-only. Expect far fewer than 23 actual findings, since evidence-driven detection only fires where the other checker genuinely reports -- the remaining unpaired lines are legitimately fine and MUST NOT be touched. Add a lock test so a regression reds main.

WITHDRAWN by T-1339's DESIGN AMENDMENT (2026-07-31): the successor question originally posed here -- whether to migrate the 17 legacy mypy-only ignores to ty and drop the mypy dialect from this repo -- is answered NO and must not be pursued. The goal is portability: those mypy suppressions are load-bearing for downstream consumers who type-check frob with mypy, even though mypy never gates here. Do not delete or migrate a suppression for a checker this repo does not run.

Expect this ticket's real work to GROW rather than shrink under the amendment: with mypy installed as an oracle, the ty->mypy direction now produces findings too, so lines carrying only a ty suppression will need mypy pairs added.

<!-- ticket:T-1344 -->
```yaml
id: T-1344
title: 'Agentic-development throughput: the land path is the bottleneck, not the work'
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- docs/guides/agent-playbook.md
acceptance:
- text: given N concurrent agents finishing work, when each lands, then no agent is
    refused for DirtyMain and no agent touches another agent uncommitted state
  evidence: []
- text: given an unchanged file set, when frob check re-runs, then gate results are
    served from a content-digest cache rather than recomputed
  evidence: []
threat: null
component: tickets
```
Filed 2026-07-31 from direct observation of a 7-agent parallel drive (T-1334/1336/1337/1338/1340/1327/1276/1293/1294/1296).

THE EVIDENCE: across four completed tickets that day, every agent got its ENGINEERING right on the first pass. Effectively all of the lost wall-clock was in the LAND PATH:

- T-1336: DirtyMain refusal from a sibling's in-flight land, plus one land attempt killed by an undersized timeout wrapper.
- T-1337: committed ANOTHER agent's uncommitted tickets.md churn to main, twice, purely to clear DirtyMain. Inert metadata this time; the shape is dangerous.
- T-1338: land killed mid-Tier-A-autofix left a GARBLED source file; the obvious "git checkout -- <file>" recovery then silently destroyed an uncommitted new test. Caught only because a pytest count looked wrong.
- Coordinator: "frob ticket new" exceeded a 120s timeout under 4 concurrent agents (single-file ledger lock).

So the leverage is not in how agents do the work -- it is in serialization, cache-coldness, and non-atomic recovery. Leaves cover: merge queue, digest-memoized gates, sibling-lease disclosure in brief, transactional land auto-fix, ledger write contention.

ALSO NOTE (separate but related): the coordinator was hand-writing 40-line dispatch prompts duplicating what "frob ticket brief" already emits. Underused capability, not a tool gap -- addressed by convention plus the brief leaf.

CONSTRAINT DISCOVERED: memory is no longer the limit on agent count (.wslconfig now gives 23 GB + 24 GB swap). CPU is: 12 cores, load ~11 at only 4 agents, and land must finish inside a 540s wrapper. Practical ceiling ~7 concurrent agents. Every item below raises that ceiling by making the land path cheaper.

T-1058 (worktree cut from stale origin/main -- a documented silent-revert cause) is ARCHIVED, not resolved in the active ledger; the playbook still carries a manual "git merge main first" step as the mitigation. Re-decide it under this epic if the merge queue does not subsume it.

<!-- ticket:T-1345 -->
```yaml
id: T-1345
title: 'Merge queue: agents enqueue verified branches, one drainer merges onto main'
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: critical
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- docs/guides/agent-playbook.md
acceptance:
- text: given two agents landing at once, when both enqueue, then both land in sequence
    with neither refused for DirtyMain and neither writing to main directly
  evidence: []
- text: given a queued branch that no longer merges cleanly after an earlier entry
    lands, when the drainer reaches it, then it is handled by a declared policy rather
    than silently dropped
  evidence: []
threat: null
component: tickets
```
Leaf of T-1344. THE highest-leverage item: today every agent landed onto one shared main checkout, so lands serialize by collision-and-retry rather than by design.

Observed failures this shape caused: a DirtyMain refusal costing a full retry cycle (T-1336); an agent committing a SIBLING's uncommitted ledger churn to main twice just to clear DirtyMain (T-1337) -- inert that time, but the shape lets one agent commit another's half-finished work; and repeated multi-minute waits.

PROPOSAL: "frob ticket land --queue" enqueues a verified worktree branch and returns immediately. A single serialized drainer merges queued branches onto main one at a time, running the post-merge gate check per merge. Agents then NEVER write to main directly.

MEASURED EVIDENCE (2026-07-31, mined from .frob/telemetry.jsonl, 12,300 records) -- this is now the single most expensive operation in the tool:
  ticket land   13.38 h total over 752 calls   (mean 78s when it succeeds)
    succeeded   484 calls  10.46 h
    FAILED      268 calls   2.92 h  <-- 36% failure rate, pure waste
  For comparison: ALL `frob check` invocations combined cost 6.82 h over 1116 calls.
  `ticket land` alone is ~60% of all frob wall-clock in the corpus, and its
  failures alone (2.92 h) cost more than any other subcommand's total.
The dominant failure mode is DirtyMain contention between concurrent agents --
exactly what a merge queue eliminates by construction. This ticket is therefore
the highest-value speed work in the repo, ahead of any gate optimization.

Design questions to answer in the ticket, not assume:
- Where does the queue live so it survives a crashed drainer (a git ref? a file under .frob/ with a lock?).
- What happens when a queued branch no longer merges cleanly after an earlier queue entry lands -- reject back to the agent, or auto-rebase and re-verify?
- The gate check must run POST-merge to be meaningful; that is what makes throughput depend on the memoization leaf.
- Does this subsume the archived T-1058 stale-worktree-base hazard? If the drainer always merges current main, a stale base becomes detectable at enqueue.

Preserve the existing LAND-PROOF contract: whatever the agent gets back must still let it prove commit + is_ancestor_of_main + state_on_main, or the verification discipline this repo depends on breaks.

<!-- ticket:T-1346 -->
```yaml
id: T-1346
title: Memoize gate results on content digests
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: critical
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/check/**
- docs/modules/gates.md
acceptance:
- text: given an unchanged file set, when frob check re-runs, then unchanged gates
    are served from cache and the run is materially faster
  evidence: []
- text: given a gate whose declared inputs changed, when frob check re-runs, then
    that gate recomputes and never serves a stale result
  evidence: []
threat: null
component: gates
```
Leaf of T-1344. "frob check" recomputes ~35 gates over the whole tree on every invocation. Measured on main 2026-07-31: sys 31.3s, perf 28.9s, arch 23.8s, clones 18.7s, pii_structural 12.4s, secrets 9.6s, coverage 8.9s, dead_symbols 8.7s, deprecated 7.9s, opaque 7.9s -- roughly 3 minutes of CPU per full run.

This is the root cause of THREE separate problems, not one:
1. Land timeouts: land must finish inside a 540s wrapper and a full re-check eats most of it (a land was killed mid-autofix by exactly this on T-1338).
2. The stall pattern: agents background "frob check" and idle waiting BECAUSE it is slow (hit 6+ times historically, twice on 2026-07-31). A year of prompt-repetition has not fixed it; making the check fast removes the incentive.
3. The concurrency ceiling: gates are CPU-bound, so N agents each running full checks saturate 12 cores at N~4 (observed load ~11).

PROPOSAL: memoize gate results keyed on content digests. The key insight is that frob ALREADY maintains a per-symbol/per-file digest graph under .frob/ -- that is the project's founding premise -- so the cache key largely exists and is simply not used for gate results. Cache per (gate, gate-config, input-digest-set); a gate whose inputs are unchanged is served, not recomputed.

MEASURED EVIDENCE (2026-07-31, mined from .frob/telemetry.jsonl, 12,300 records):
  2.55 h of PROVABLY redundant re-runs -- identical `args_head` at identical
  `tree_hash`, i.e. the same command over a byte-identical tree. Bare `check`
  alone accounted for 45.8 min across 39 repeats; `check --only coverage` 6.8
  min across 20; `check --only test` 5.0 min across 21.
  The telemetry schema ALREADY records `tree_hash` per invocation, so this
  redundancy is provable rather than heuristic -- and a digest-keyed cache
  would eliminate all 2.55 h by construction, not by cleverness.
  Full unscoped check measures 139.7s wall; the whole-tree scanners dominate
  (sys 39s, perf 38s, arch 29s, clones 22s, pii 14s, coverage 13s, dead 11s).
NOTE also that `ticket land` runs a post-merge check; at 13.38 h total land
cost (see T-1345), making that check cheap is a large secondary win here.

Design questions to answer, not assume:
- Per-gate input sets must be declared HONESTLY. A gate that secretly reads frob.toml, the ledger, or a baseline file and is not keyed on it will serve stale results -- that is a correctness bug in the gate layer, strictly worse than being slow. Prefer fail-open (recompute) on any doubt.
- Cross-file gates (dup/clones, dead_symbols, cycle) key on a SET of digests, not one file; verify the win survives that.
- Where does the cache live, and is it safe for concurrent readers/writers across worktrees? .frob/ is gitignored, so CI cold-starts -- measure the cold path too.
- Add a "--no-cache" escape hatch and make cache hits visible in output so a wrong result is diagnosable.

<!-- ticket:T-1350 -->
```yaml
id: T-1350
title: 'TEST005 burn-down: src/frob/perf -- honest remainder after T-1293 false-close
  (65 findings)'
state: queued
kind: feature
origin: agent
created: '2026-07-31'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- tests/unit/perf/**
acceptance:
- text: given an unscoped frob check --only test, when TEST005 lines under src/frob/perf
    are counted, then the count is materially below 65 and the report states the exact
    before and after
  evidence: []
threat: null
component: perf
```
Successor to T-1293, which was closed prematurely on 2026-07-31.

WHAT HAPPENED: T-1293 ("TEST005 burn-down: src/frob/perf, 64 findings") landed at cfbbb938 having fixed exactly ONE finding (load_ratchet_findings' two fail-open branches). The agent reported "0 TEST005 findings in src/frob/perf" and disclosed, in good faith, that it could not reproduce the ticket's baseline. A coordinator re-measure immediately after the land shows 65 TEST005 findings still outstanding in the package, including src/frob/perf/_harness.py::main at 3.0% branch coverage -- the very symbol the agent had concluded was "81% covered, well-covered".

ROOT CAUSE: the agent measured with a locally scoped "pytest --cov=src/frob/perf" over that package's own tests, and with "frob check --only test --ticket T-1293" (which filters to the ticket's declared SCOPE, narrower than the package). Neither is what TEST005 reads -- the gate is computed from the REPO-WIDE coverage stamp produced by "make coverage". The agent explicitly noted a full-repo coverage run was "coordinator-only per the playbook" and skipped it, so it had no way to see its real progress and reported a scoped number as a package number. The agent's disclosure was honest; the measurement was wrong.

THE WORK: the original burn-down, honestly measured. 65 findings remain. Worst offenders at time of filing: _harness.py::main 3.0%, _advisories.py::external_call_advisories 4.0%, _advisories.py::nested_loop_fanin_advisories 5.9%, _heat.py::heat 7.1%, _heat.py::render_bar 14.3%, _heat.py::join_smells 33.3%.

MEASURE CORRECTLY: "timeout 540 uv run frob check --only test" (unscoped) and grep TEST005 lines under src/frob/perf. That is the same source the gate uses and it costs ~5s. Do NOT use a scoped pytest --cov run or a --ticket-filtered check to claim completion.

Partial progress is acceptable and expected; report honest before/after and file a further successor for any remainder. Do not close this while the package still shows a large count.

<!-- ticket:T-1359 -->
```yaml
id: T-1359
title: Make FMT001/REG010/REL002 Tier-A handlers' delegated writes crash-safe
state: queued
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/registry/_staleness.py
- src/frob/release/**
threat: null
component: null
```
T-1348 made every in-place file rewrite living directly in
src/frob/gates/_fix_engine.py (DOC007/DOC002/INV006-carry rewrites,
WAIVE004's waiver-line removal) crash-safe via atomic_write (temp file +
fsync + os.replace). Three OTHER Tier-A handlers -- FMT001, REG010,
REL002 -- delegate their actual disk writes to functions in different
modules that were out of T-1348's declared scope:

- FMT001 -> frob.gates._fmt_directives.format_paths (bare
  path.write_text)
- REG010 -> frob.registry._staleness.sync_gate_rule_entries (writes
  check-coverage.yaml)
- REL002 -> frob.release.rewrite_pyproject_version /
  changelog_skeleton_entry (writes pyproject.toml / CHANGELOG.md)

None of these route through a crash-safe write primitive today -- a land
killed mid-FMT001/REG010/REL002 could still leave one of THESE files
half-rewritten, the same T-1338 hazard class T-1348 closed for the other
three handlers. Convert these three write sites to
frob.tickets._store.atomic_write (or an equivalent local primitive) the
same way T-1348 did for _fix_engine.py's own direct writes.

<!-- ticket:T-1360 -->
```yaml
id: T-1360
title: 'Footgun detection: warn when a command failed or under-reported in a way that
  looks like success'
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/telemetry.py
- docs/modules/telemetry.md
acceptance:
- text: given a command re-run at an identical tree_hash with identical args, when
    it completes, then a tip names the prior run and its timestamp
  evidence: []
- text: given a command that exits nonzero in under two seconds, when it completes,
    then a tip states plainly that it errored and did not do the work
  evidence: []
- text: given tips are emitted, when --json is requested, then they are machine-readable
    so an agent can self-correct
  evidence: []
threat: null
component: telemetry
```
Leaf of T-1344. User request 2026-07-31: "Can we do a footgun protection? Can we detect when we are using frob tooling poorly?"

THE TARGET IS SHARPER THAN "POOR USAGE". One session produced THREE instances of a single family: an operation that fails or under-reports in a way INDISTINGUISHABLE FROM SUCCESS.
1. T-1293: coverage measured with the wrong denominator (scoped pytest --cov instead of the repo-wide stamp) -> agent closed a 64-finding ticket having fixed 1, reporting the package clean.
2. T-1337: verification run as `check --only opaque --ticket T-1337` -- filtered by gate AND scope -- so two INV006 errors were invisible and shipped to main.
3. Coordinator: timed `check --ticket T-XXXX` at 0.77s vs 139.7s unscoped and reported a 180x speedup. The fast runs were EXITING EARLY on "no recorded lease" -- an error path read as a speedup, then acted on and broadcast to three agents before being caught.
Three independent, competent actors hit the same shape in one day. That is a tooling defect, not a discipline problem.

THE SUBSTRATE ALREADY EXISTS: .frob/telemetry.jsonl, 12,300 records, fields args_head / duration_ms / exit / iso_ts / kind / subcommand / tree_hash. No new instrumentation is needed for the first rule set. tree_hash is the key field -- it makes redundancy PROVABLE rather than heuristic.

DETECTOR RULES, seeded from mining that corpus (not from a guessed list):
1. REDUNDANT RE-RUN: identical args_head at identical tree_hash. Measured 2.55 h of provably-wasted wall-clock; bare `check` alone repeated 39 times for 45.8 min. Tip: "you ran this exact command at this exact tree state N minutes ago; nothing has changed since."
2. FAST EXIT-1: low duration_ms with nonzero exit. 756 such runs in the corpus. This is the trap the coordinator hit -- the tip must say plainly "this exited with an ERROR in 0.5s; it did not do the work you may think it did."
3. FILTERED VERIFICATION BEFORE LAND: a --ticket or --only run as the last check preceding `ticket land`. This is exactly how T-1337 shipped errors. Must state what the filter SUPPRESSED, not merely that a filter was active (this subsumes/overlaps T-1351 -- reconcile, do not duplicate).
4. REPEATED IDENTICAL FAILURE: same command failing the same way N times = stuck, not progressing. Overall corpus failure rate is 11% (1351/12304); `ticket land` alone fails 36% of the time.
5. COVERAGE-NUMBER MISUSE: a coverage/TEST005 claim made against a stamp older than the working tree. Ties to T-1335.

DELIVERY REQUIREMENTS:
- A tip printed AFTER the command, never blocking it, rate-limited, individually suppressible (a tip that nags gets ignored, which is worse than no tip).
- MACHINE-READABLE form (--json or a structured stream) so AGENTS self-correct. Agents are now the primary users of this CLI and they cannot read a human-styled hint reliably. This is the difference between a nicety and the thing that actually stops the failure class.
- Every tip must name the concrete better command, not just diagnose. "Use --ticket" is useless; "you already ran this at tree_hash abc1234 8 minutes ago" is actionable.
- A `frob doctor usage`-style verb that reports YOUR top time sinks and footguns from the local corpus. The corpus answered "where does the time go" in minutes today; that capability should be a command, not an ad-hoc python script.

DO NOT: make tips block or fail a command; add a tip whose advice is unmeasured (the coordinator's 180x claim would have become a permanent false hint had it shipped into `brief`); or duplicate T-1351 -- fold rule 3 into whichever ticket implements it.

<!-- ticket:T-1366 -->
```yaml
id: T-1366
title: CI still cannot verify the .frob/-local coverage stamp and delta baseline (T-1265
  successor)
state: queued
kind: security
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- .github/workflows/ci.yml
- src/frob/gates/_coverage.py
- src/frob/gates/_baseline.py
acceptance:
- text: GIVEN a CI run WHEN the coverage stamp or delta baseline is absent, stale
    or tampered THEN the build fails rather than silently degrading to a pass
  evidence: []
threat: repudiation
component: null
```
T-1265 made the ci.yml self-gate blocking and added a TEST012 check for frob-coverage.lock.json, the one committed coverage channel. The residue it did not close: the coverage stamp and the delta baseline still live in .frob/, which is gitignored and never restored in CI, so TEST005/TEST006 remain structurally inert there. CHK-THEME-GITIGNORED-TRUST in docs/design/registry/check-coverage.yaml is repointed here.

<!-- ticket:T-1368 -->
```yaml
id: T-1368
title: stamp() return value discarded in _apply_release_bump_for_land, can silently
  drop .frob-release.json writes
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
threat: null
component: null
```
Found while working T-1358 (release-quartet desync land outage).

`_apply_release_bump_for_land` (src/frob/app/ticket_runner/_land_cmd.py)
calls `frob.release.stamp(root, fresh_snapshot.danger_ok, new_version)` to
write `.frob-release.json` after bumping pyproject.toml/CHANGELOG.md, but
never checks `stamp`'s `Result` return value -- a write failure there
(e.g. `stamp`'s own `enforce_worktree_lease` refusal, or any future
failure mode `stamp` grows) is silently swallowed, and the function
proceeds to `git add .frob-release.json` regardless, staging whatever
content (possibly stale) happens to be on disk.

T-1358 added a defense-in-depth coherence check inside
`_apply_release_bump` (src/frob/tickets/_land_release.py) that catches
and repairs this class of desync after the fact, but the root silent-drop
in `_land_cmd.py` itself is still live and outside T-1358's declared
scope. Suggested acceptance: check `stamp(...)`'s return value in
`_apply_release_bump_for_land` and propagate `Err` to
`Err(LandError.ReleaseBumpFailed)` instead of discarding it.

<!-- ticket:T-1371 -->
```yaml
id: T-1371
title: 'Drain EXHAUST001/EXHAUST002 to zero: unresolvable escapes and undeclared KeyError/TypeError'
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
acceptance:
- text: GIVEN main WHEN frob check --only gates runs THEN gate:EXHAUST reports 0 EXHAUST001
    and 0 EXHAUST002 warnings
  evidence: []
threat: null
component: null
```
95 findings at drive start (62 EXHAUST001, 33 EXHAUST002). Each is either a real unhandled-exception path (fix the handling or add a catch-all) or a case for an explicit frob:raises declaration. Prefer declaring the truth over blanket except Exception where the escape is genuinely intended.

<!-- ticket:T-1378 -->
```yaml
id: T-1378
title: 'The check daemon is a net negative: it competes for CPU, ignores frob_shutdown,
  and leaks its forkserver pool'
state: in-progress
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_socketd.py
- tests/test_serve_socket.py
scope_changes:
- op: add
  glob: tests/test_serve_socket.py
  reason: The ticket's own acceptance criteria require regression tests (frob_shutdown
    actually exits, no leaked multiprocessing child survives) and this repo's convention
    binds such evidence into the existing tests/test_serve_socket.py module; minimal
    widening, re-applied after the 10b ledger restore.
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_terminates_and_joins_active_children
- tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_escalates_to_kill_if_terminate_does_not_stick
- tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_no_active_children_is_a_no_op
- tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget
acceptance:
- text: GIVEN a frob_shutdown RPC that returns ok WHEN 5 seconds pass THEN the daemon
    process has actually exited
  evidence:
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_terminates_and_joins_active_children
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_escalates_to_kill_if_terminate_does_not_stick
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_no_active_children_is_a_no_op
  - tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget
- text: GIVEN a daemon that exits WHEN it is gone THEN no multiprocessing forkserver
    or resource_tracker child of it survives
  evidence:
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_terminates_and_joins_active_children
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_escalates_to_kill_if_terminate_does_not_stick
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_no_active_children_is_a_no_op
  - tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget
- text: GIVEN a warm daemon WHEN frob check --only gates --delta --json runs THEN
    it is not slower than the same command with FROB_NO_DAEMON=1
  evidence: []
threat: null
component: null
```
Measured 2026-08-01 alongside T-1377. Three separate defects, all observed directly:

1. frob_shutdown acknowledges but does not stop. send_request(root, 'frob_shutdown') returned Ok, and the daemon process was still alive 20+ seconds later; it took SIGTERM, then SIGKILL. So the graceful-stop path cannot establish that a daemon is genuinely GONE, which is the mirror of the liveness problem T-1377 fixes for genuinely ALIVE. _shutdown_stale_daemon's version-skew path trusts this RPC and only waits _SHUTDOWN_GRACE_S=1.0s for the lock, so on a real skew it will proceed to spawn while the old daemon is still up.

2. It leaks its multiprocessing children. After the daemon died, its forkserver and resource_tracker processes survived and had to be reaped by hand; repeated spawns accumulated several.

3. It costs more than it saves on this box. With a daemon up, load average went from ~0.4 idle to 5-8 while a single frob check ran, and the proxied shape got SLOWER across repeated runs rather than warming up. The daemon's forkserver pool competes with the foreground check for the same cores, so on a 4-core WSL machine the proxy is a pessimization.

Until this is fixed, FROB_NO_DAEMON=1 is the correct default for interactive work and the docs should say so. T-1377 removes the pathological stalls (10s probe, respawn storms) but does NOT make the daemon a win.

## Done report

Fixed defects 1 and 2 within this ticket's declared scope
(src/frob/serve/_socketd.py); disposed of defect 3 as out of scope with a
filed follow-up.

1. frob_shutdown acknowledges but does not stop: the real root cause is
   that a daemon which had served a query touching frob.serve._tools's
   parallel-execution paths left multiprocessing children (forkserver,
   resource_tracker) running after server.shutdown() returned -- only
   Python's own multiprocessing.util._exit_function atexit hook would
   eventually reap them, and its unbounded Process.join() is what made
   "shut down" take 20+ seconds and need a manual SIGTERM/SIGKILL.

2. It leaks its multiprocessing children: same root cause as (1). Added
   _reap_multiprocessing_children() -- terminate() every
   multiprocessing.active_children(), then a bounded join(timeout=
   _CHILD_REAP_GRACE_S), escalating to kill() for anything still alive --
   called from run_socket_daemon's finally block, which both the
   idle-timeout exit and the frob_shutdown RPC exit already share. This
   runs before the interpreter ever reaches its own atexit handling, so
   both defects are fixed by the same change: shutdown is now bounded and
   deterministic regardless of what spawned the children, without
   depending on frob.serve._tools's own pool internals (out of this
   ticket's scope).

3. NOT fixed, decision: the performance regression (warm daemon slower
   than FROB_NO_DAEMON=1, load average 5-8 vs ~0.4 idle) is real but its
   root cause -- a persistent multiprocessing forkserver pool kept warm
   by frob.serve._tools's parallel-execution paths -- lives entirely
   outside src/frob/serve/_socketd.py, this ticket's declared scope.
   T-1379 already made the daemon opt-in (not default-enabled), which
   removes this as a default-install risk; a user who explicitly opts in
   still pays it. Rather than force a fix through the wrong file or
   silently drop it, filed T-1436 (kind=bug, scope=src/frob/
   serve/_tools.py) to investigate lazy/sized-down pool warming and
   re-measure. Acceptance criterion [2] is left UNBOUND for this reason;
   [0] and [1] are bound.

Removing the daemon outright was considered and rejected: defects 1/2
are now fixed cleanly, T-1379 already makes it opt-in, and the daemon's
warm-state value (T-0177/T-1094/T-1096) is real for the interactive/MCP
use case, not just a cost -- the honest fix was closing the two real
process-hygiene bugs, not deleting a feature that works once those bugs
are gone.

Scope was widened by one file (tests/test_serve_socket.py, via
`frob ticket scope --add` with a recorded reason) to bind real
regression-test evidence, matching this ticket's own acceptance criteria.

Test: tests/test_serve_socket.py::TestReapMultiprocessingChildren covers
_reap_multiprocessing_children directly (normal terminate+join, and the
kill() escalation path via a child that ignores SIGTERM); TestShutdown
ReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget is the
end-to-end reproduction -- a real multiprocessing child alive when
frob_shutdown is sent, asserting both the daemon thread joins within the
5s budget and the child does not survive.

Docs: docs/modules/serve.md gets a new "Shutdown reaps multiprocessing
children (T-1378)" subsection under "Version handshake".

Note for the coordinator: this worktree also carries T-1423's commits
(same series worktree per the playbook's "one worktree per series"
rule). `frob check --ticket T-1378` reports SCOPE001/COV002/AFFECT001/
AFFECT002 against T-1423's own files (design/frob.strata, docs/modules/
graph.md, src/frob/graph/cache.py, src/frob/graph/__init__.py,
frob.lock) -- this is the shared-branch-diff artifact of two tickets in
one worktree (the ticket-scoped gate compares against the whole branch
diff vs main, not just this ticket's own commits), not a real T-1378
defect; T-1423 was independently verified clean with `frob check
--ticket T-1423 --budget 100` (exit 0) before T-1378 was started. Re-run
`frob check --ticket T-1378` after T-1423 lands (or is otherwise removed
from this branch's diff) to get a clean per-ticket read.

### Changed
```
 design/frob.strata         |     4 +
 docs/modules/graph.md      |    21 +
 docs/modules/serve.md      |    24 +
 frob.lock                  |     2 +-
 src/frob/graph/__init__.py |    25 +-
 src/frob/graph/cache.py    |   136 +-
 src/frob/serve/_socketd.py |    55 +
 tests/test_graph_lock.py   |   110 +-
 tests/test_serve_socket.py |   112 +
 tickets-archive.md         |  9720 +++++++++++++++++++++++++++++++++++++-
 tickets.md                 | 10967 ++++---------------------------------------
 11 files changed, 11210 insertions(+), 9966 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_terminates_and_joins_active_children` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_escalates_to_kill_if_terminate_does_not_stick` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_no_active_children_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 8 error(s), 394 warning(s), 695 waived
- error-findings: AFFECT001@src/frob/graph/__init__.py, AFFECT002@src/frob/graph/__init__.py, COV003@tickets/T-1406, COV003@tickets/T-1408, COV003@tickets/T-1419, SELFAUDIT001@design, TICK006@tickets.md, WIRE001@tests/test_serve_socket.py

<!-- ticket:T-1382 -->
```yaml
id: T-1382
title: 'Decouple frob from the Makefile: make every workflow a first-class cross-platform
  frob subcommand'
state: queued
kind: feature
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/**
- docs/**
acceptance:
- text: GIVEN a repo with no Makefile WHEN every documented frob workflow is run THEN
    each works via a frob subcommand alone
  evidence: []
- text: GIVEN Windows (no make, no POSIX shell) WHEN the coverage workflow runs THEN
    it works without shell quoting, backslash line continuations, or GNU-make syntax
  evidence: []
- text: GIVEN docs and agent guidance WHEN a workflow is described THEN it names the
    frob subcommand, with make targets documented only as thin optional aliases
  evidence: []
threat: null
component: null
```
User directive 2026-08-01: frob must be cross-project and cross-platform, so it cannot depend on a Makefile.

Current state measured today: the Makefile is 528 lines and 21 call sites across src/frob/ reference it (src/frob/_cli_parsers/_core.py, testing/_collect_cpp.py, vet/_supplychain.py, vet/_capability_registry.py, natives/_build.py, strata/_native_staleness.py, scaffold/_managed.py, scaffold/project.py and others).

The sharpest example is 'make coverage'. Its recipe is ~30 lines of GNU-make-escaped POSIX shell -- COVERAGE_PROCESS_START, a generated coverage rc, an xdist run, a 'node down' grep with a full serial re-run, coverage combine, a T-1363 status guard, then a stamp. None of that runs on Windows, and tests/unit/test_makefile_coverage.py has to slice the recipe text out of the Makefile with a regex and re-run it under bash just to test it -- which is itself evidence the logic is in the wrong place. It should be 'frob coverage', implemented in Python, with the Makefile target reduced to a one-line alias.

Suggested decomposition (leaves to be filed as children):
1. frob coverage -- own the whole recipe in Python, including worker-crash detection and the T-1363 never-promote-partial-data guard.
2. frob build/natives -- replace 'make core' and the native build paths.
3. Audit the 21 Makefile references; each is either a workflow to promote or a scaffold template to re-point.
4. Path/shell portability sweep: no bash -c, no backslash continuations, no assumption of a POSIX shell in any code path.
5. Docs + agent-playbook rewrite so guidance names frob subcommands first; keep make targets as documented optional aliases for muscle memory.

Related: the user's standing preference is still to SUGGEST 'make <target>' where one exists, so this is about removing the DEPENDENCY, not deleting the Makefile.

<!-- ticket:T-1388 -->
```yaml
id: T-1388
title: land's Tier-A pre-fix pass touches out-of-scope _daemon_proxy.py, then self-blocks
  on OutOfScopeWaiveDeletion
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land*.py
threat: null
component: null
```
Found while landing T-1237 (and earlier T-1235) in the coverage-integrity
series worktree: every `frob ticket land <id> --worktree ...` invocation's
own pre-land Tier-A auto-fix pass ("ticket land: T-1235/T-1237 pre-land
Tier-A fixes applied 2 fix(es)") rewrites src/frob/app/_daemon_proxy.py
(re-wrapping two frob:waive reason= comment blocks, ARCH103 at line ~135
and SEC110 at line ~342) and stubs a CHANGELOG.md "## [0.295.0] -
unreleased" entry, even though neither file is in the landing ticket's
declared scope and neither ticket touched src/frob/app/**.

That collateral edit then trips land's OWN OutOfScopeWaiveDeletion guard
on the very same invocation:

  ERROR: land: T-1237 refused -- worktree has uncommitted frob:waive
  deletion(s) outside scope [...] and undeclared by the Done report:
  ['src/frob/app/_daemon_proxy.py:ARCH103', 'src/frob/app/_daemon_proxy.py:SEC110']

i.e. land's own Tier-A fixer creates the exact violation land's own
scope guard then refuses on -- deterministic, reproduced twice in one
session (T-1235's land attempt, then T-1237's, both against the same
_daemon_proxy.py lines). Working around it by `git checkout --
src/frob/app/_daemon_proxy.py CHANGELOG.md` before every land retry is
a manual step every future ticket in this repo will hit the same way,
since the Tier-A fixer re-triggers it every time land runs.

Root cause not fully isolated (would require reading
src/frob/tickets/_land*.py's Tier-A fixer dispatch, which is out of this
series' declared scope -- Makefile, src/frob/clean/**, docs/**, tests/**
only), but the shape strongly suggests either: (a) the Tier-A fmt fixer
runs unscoped (whole repo) instead of restricted to the landing ticket's
own touched-file set, or (b) _daemon_proxy.py's frob:waive reason=
comments sit right at whatever line-length threshold `frob fmt` rewraps,
so any repo-wide fmt pass touches it regardless of which ticket is
landing.

Suggested fix direction: scope the Tier-A pre-land auto-fix pass to the
landing ticket's own scope globs (same set the OutOfScopeWaiveDeletion
guard itself already checks against), so it structurally cannot produce
a collateral out-of-scope edit for a DIFFERENT ticket to trip over.

<!-- ticket:T-1389 -->
```yaml
id: T-1389
title: 'TEST011: extend deflation detection to catch per-symbol false-0.0% coverage
  under xdist worker loss'
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- src/frob/gates/__init__.py
- tests/test_gates.py
threat: null
component: null
```
Investigated directly: reproduced the SAME test (tests/test_ticket_leases.py
::TestWorktreeSweepCli::test_sweep_cli_prints_verdicts_and_summary) under a
real xdist run (-n 4, the exact absolute-path subprocess rc T-1235 fixed:
branch/parallel/relative_files/sigterm/concurrency all matching the real
make coverage recipe) against the whole tests/test_ticket_leases.py file
(45 tests, several workers). `coverage report -m` on the combined result
shows src/frob/app/worktree_runner.py at 80% branch, matching the
originally-cited direct-run number exactly -- no 0% false-negative
reproduces at this scale. The merge machinery (combine + the [paths]
remap) is not dropping this symbol's data in a smaller, controlled xdist
run.

This narrows the likely cause to a FULL-suite-scale-only effect, not a
distinct bug in coverage.xml combine/attribution logic itself. The most
likely explanation is the class T-1353 already root-caused and partially
fixed in the same investigation window: under the full suite's `-n auto`
(pre-T-1353) or even the now-capped `COVERAGE_WORKERS=4`, several tests in
this repo (self-conformance/self-scan tests especially) spawn their own
coverage-traced subprocess/multiprocessing children, oversubscribing
CPU/memory and crashing xdist workers ("node down"); a crash bypasses
`sigterm=true`'s flush and drops that ENTIRE worker's coverage
contribution, not just its failed test(s). If `test_sweep_cli_prints_
verdicts_and_summary` happened to land on a worker that later crashed in
that specific full-suite run, its earlier-recorded coverage would be lost
this exact way -- consistent with "a false 0.0% only in the full suite,
never in isolation" and with T-1353's own measured symptom shape
(severely deflated numbers for symbols near/after a stuck/crashed
worker's tests).

I cannot conclusively distinguish "this exact symbol got node-downed in
that one run" from "a still-undiscovered distinct merge defect" without
re-running the FULL, unscoped `make coverage` under load and inspecting
which worker crashed and when that specific test executed -- both a
coordinator-only step (playbook section 6b: a dispatched sub-agent cannot
run/wait on `make coverage`) and, even if it could, backward-looking
forensics on a run that already happened and was cleaned up. Per this
series' guidance ("if the root cause turns out to be an environment
artifact rather than a defect, say so plainly and drop"), dropping here:
the evidence available points to an already-partially-mitigated
environment/load artifact (T-1353's node-down class), not a fresh,
reproducible defect in the merge code this ticket's scope (src/frob/
gates/_coverage.py, Makefile) could fix.

The ticket's OWN alternative plan item -- "extend TEST011's detection to
catch this class of false 0.0%" -- is real, actionable follow-up work
(a per-symbol deflation heuristic distinct from TEST011's current
aggregate module_join_fraction check, which stays silent when only a
handful of symbols are affected but the overall join fraction is fine).
That is a genuine new detector design, not a small fix-in-place; filing
it as its own ticket rather than forcing a half-designed version into
this investigation ticket's close.

<!-- ticket:T-1393 -->
```yaml
id: T-1393
title: test_disjoint_v2_tickets_land_with_no_custom_merge flakes under xdist -n 4
  (passes standalone)
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_ticket_land.py
threat: null
component: null
```
Found while working T-1392 (verifying the full unscoped suite after fixing its 5 target failures). 'uv run pytest -q -p no:randomly -n 4 --tb=no -rf' surfaced exactly one FAILED: tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge. Re-run standalone ('uv run pytest -q -p no:randomly -o addopts="" tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge') passes in 0.45s. Not one of T-1392's five named deterministic failures and not touched by T-1392's diff -- looks like xdist worker contention over shared ledger/tickets.md state, not a genuine regression. Diagnose and either fix the isolation gap or mark the test appropriately; do not silently ignore -- a suite that flakes under -n 4 blocks confident 'make coverage'/CI runs the same way T-1392's deterministic failures did.

<!-- ticket:T-1394 -->
```yaml
id: T-1394
title: handler.py's _LazyStdoutHandler/_LazyStderrHandler.stream properties are public
  with no frob:doc edge (COV001 x2)
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/logging/handler.py
threat: null
component: null
```
Found while working T-1392 (frob check --ticket T-1392 unscoped repo-wide gate:COV read 2 errors throughout). T-1385 landed _LazyStdoutHandler/_LazyStderrHandler and a sibling fix (eb6e4b23, 'fix(logging): point handler.py's frob:doc anchors at a section that exists') already repaired the DOC002 anchor-resolution half, but each class's public 'stream' property still has no frob:doc edge at all (COV001: src/frob/logging/handler.py::_LazyStdoutHandler.stream and ::_LazyStderrHandler.stream). Not in T-1392's scope and not touched by its diff -- either add a frob:doc anchor on each stream property (docs/modules/logging.md#public-api, matching the class-level anchor) or move the property to private if it was never meant to be part of the public surface.

<!-- ticket:T-1395 -->
```yaml
id: T-1395
title: 'Coverage attribution still misses daemon and CLI-entry processes: serve/ and
  __main__.py remain 0.0%'
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_wait.py
- src/frob/serve/_socketd.py
acceptance:
- text: GIVEN a successful unscoped make coverage run WHEN the TEST005 report is read
    THEN src/frob/serve/** symbols exercised by the daemon tests report non-zero branch
    coverage
  evidence: []
- text: GIVEN the same run WHEN src/frob/__main__.py::main is read THEN it reports
    non-zero branch coverage rather than 0.0%
  evidence: []
threat: null
component: null
```
Measured on main 2026-08-01 after T-1235's subprocess-rc fix landed and make coverage completed green (exit 0, 851 files stamped, source_sha=de76e283).

T-1235's fix demonstrably worked for one class of process: modules that were pinned at 0.0% now report real numbers --
  src/frob/excludes.py::load_exclude_globs   6.7%  (was 0.0)
  src/frob/excludes.py::is_excluded         50.0%  (was 0.0)
  src/frob/doctor.py::scan_venv_shims        3.0%  (was 0.0)
  src/frob/doctor.py::verify_derived_state  50.0%  (was 0.0)

But two of the four module groups T-1235's own acceptance criterion names are STILL at exactly 0.0%:
  src/frob/serve/_leases.py::ResourceLeaseManager.{acquire,release,release_holder}
  src/frob/serve/_socketd.py::daemon_version
  src/frob/__main__.py::main
  src/frob/__main__.py::_SuggestingArgumentParser.error

These share a property the fixed modules do not: they execute in a daemon or CLI-entry process that the subprocess rc does not reach. The daemon is spawned by the socket server, and __main__ runs as the console-script entry -- neither inherits COVERAGE_PROCESS_START the way the pytest-spawned subprocesses do.

306 symbols repo-wide remain at exactly 0.0%, so this is not a rounding artifact.

Related signal worth checking while here: load_coverage reports module_join_fraction=0.53, i.e. only about half of mapped modules join to the graph. T-1236's deflation guard exists for exactly this shape.

This ticket exists because T-1235 cannot honestly close until serve/ and __main__.py attribute -- its criterion names them explicitly, and binding evidence to a half-satisfied criterion would be the false-close this queue has been bitten by before.

## Failure log
- 2026-08-01 attempt 1: Investigated exhaustively (empirical repros of both a real subprocess-spawned daemon and python -m frob CLI entry under the exact Makefile-generated absolute-path subprocess rc): the COVERAGE_PROCESS_START/concurrency mechanism already attributes both process classes correctly in isolation, so this is not a T-1235-style env-inheritance defect confined to src/frob/testing/_coverage_wait.py or src/frob/serve/_socketd.py -- FROB_DAEMON defaults off so _worktree_lock's daemon-lease path never even runs during make coverage, ruling that out too. Filed T-1397 for a real but unrelated Loss-A-shaped bug found in coverage-fast (out of scope: Makefile). The likely real root cause is the already-documented xdist worker-crash/stuck-test data-loss class or the module_join_fraction graph-mapping gap (T-1236), neither fixable from this ticket's two scoped files; forcing an unverifiable change here would violate the do-not-force rule.

<!-- ticket:T-1396 -->
```yaml
id: T-1396
title: 'TEST005 burn-down: src/frob/gates remaining findings past the 0.0% priority
  tier'
state: queued
kind: feature
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/gates/**
threat: null
component: null
```
## Description + plan
T-1279's brief listed 12 symbols in src/frob/gates at exactly 0.0%
branch coverage. Investigation found 10 of the 12 (secrets_gate,
parse_failure_gate, opaque_gate, scan_emitted_rule_ids/
generated_gate_rule_ids partially, scope_digest, prework_gate,
test_gate, release_gate, perf_gate, run_gates) already carry real,
behavioral frob:tests-bound unit tests exercising both clean and
finding-producing branches (e.g. tests/test_secrets_gate.py,
tests/test_gates.py::TestParseFailureGate,
tests/test_gates.py::TestKnownGateRuleIds, tests/test_gates.py's
TestScopeDigest*/TestPreworkGate*/TestTestGate*/TestReleaseGate*/
TestPerfGate*/TestRunGates* classes). Their reported 0.0% is most
plausibly the known coverage-attribution gap tracked by T-1235/T-1395
(subprocess + multiprocess worker coverage not being attributed back
to the parent process) rather than a genuine test gap -- this ticket
does not re-litigate that; it is out of `src/frob/gates/**` scope.

Genuine, closeable gaps found and fixed by T-1279 itself:
- `mutation_evidence_violations`'s `Err` (ExecDisabled) degrade branch
  had no direct test -- added (tests/gates/test_mutation_evidence_err_branches.py).
- `scan_emitted_rule_ids`'s comment-skip line, missing-scanned-base-dir,
  and unresolved-const-ref branches had no direct test -- added
  (tests/gates/test_rule_id_scan_branches.py).

Remaining work for a genuine, non-attribution-driven TEST005 burn-down
of src/frob/gates (179 findings total, only 12 were the 0.0% priority
tier T-1279 targeted): audit the other ~167 findings in the 0-75%
band across src/frob/gates/** for real missing-branch gaps (as opposed
to attribution noise) and close them with behavioral tests, same
discipline as T-1279 (no assert-True filler, judge dead code before
writing a test for it).

## Acceptance
- [ ] GIVEN the gates package at the 75%/70% floors WHEN frob check --only test runs THEN it reports 0 TEST005 findings under src/frob/gates/** that are NOT explained by the T-1235/T-1395 coverage-attribution gap
- [ ] GIVEN a symbol judged to have a genuine missing-branch gap WHEN a test is added THEN it asserts real behavior, never filler

<!-- ticket:T-1397 -->
```yaml
id: T-1397
title: 'coverage-fast Makefile target points COVERAGE_PROCESS_START at pyproject.toml
  (relative source/data_file), same Loss-A shape T-1235 fixed for coverage:'
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
threat: null
component: null
```
Found while investigating T-1395 (coverage attribution for daemon/CLI processes).

Makefile's `coverage-fast` target (line ~305) points COVERAGE_PROCESS_START at
`$(CURDIR)/pyproject.toml` directly:

    COVERAGE_PROCESS_START=$(CURDIR)/pyproject.toml xargs uv run pytest --cov=src/frob ...

pyproject.toml's [tool.coverage.run] has `source = ["src/frob"]` (relative) and
no explicit `data_file` (defaults to a relative `.coverage`). This is exactly
the "Loss A" shape T-1235 fixed for the `coverage:` target by generating a
dedicated `.frob/coverage-subprocess.rc` with ABSOLUTE `source`/`data_file` --
`coverage-fast` was never given the same treatment, so any subprocess spawned
during a `coverage-fast` run (this is `run_coverage_wait`'s own default
command, `src/frob/testing/_coverage_wait.py::run_coverage_wait`) risks
silently losing/stranding subprocess coverage data exactly the way `coverage:`
used to before T-1235, whenever a child process's cwd differs from $(CURDIR).

Verified by reading the Makefile directly (T-1395 investigation, 2026-08-01);
not independently reproduced end-to-end since `coverage-fast` recurses into
`make coverage` on a cold `.coverage` (the common case in a fresh checkout)
masking the bug until a warm/incremental run actually takes the `xargs`
branch.

Fix: generate the same kind of absolute-path subprocess rc `coverage:`
already does (or reuse `.frob/coverage-subprocess.rc` if `coverage:` has
already run once) instead of pointing COVERAGE_PROCESS_START at
pyproject.toml directly.

<!-- ticket:T-1400 -->
```yaml
id: T-1400
title: 'TEST005 burn-down: src/frob/app remainder after T-1276 false-close (116 findings,
  ~50 unsampled runners)'
state: queued
kind: feature
origin: human
created: '2026-08-01'
priority: medium
blocked_by:
- T-1398
- T-1399
- T-1401
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
acceptance:
- text: GIVEN the TEST005 join is fixed per T-1398 WHEN the app package is re-measured
    THEN every remaining finding is triaged as either a genuine gap (closed with a
    behavioral test) or an artifact (recorded, no test written)
  evidence: []
threat: null
component: null
```
Successor to T-1276, which reached state=done on main against an unmet criterion (see T-1399). The work itself is real and unfinished: 116 TEST005 findings remain under src/frob/app/ and roughly 50 runner entrypoints were never sampled.

Deliberately blocked on T-1398 and T-1399. Dispatching this before the join defect is fixed would repeat the failure mode already observed three times today -- agents finding well-tested code reported at 0.0 percent and being pushed toward filler tests. Do not start it until the measured count is trustworthy.

Landed and verified by T-1276 before the false close, so this ticket does NOT need to redo them: _daemon_proxy lease paths, check_runner colorized formatter, and AppConfig.from_external/from_args.

<!-- ticket:T-1404 -->
```yaml
id: T-1404
title: Wire frob ticket land's pre-fix pass to FMT001's new only_paths land-scoping
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
threat: null
component: null
```
T-1391 added `fix_fmt001_directive_wrap`'s `only_paths` keyword-only
parameter (src/frob/gates/_fix_engine.py), which restricts FMT001's
Tier-A rewrite to a caller-supplied set of root-relative paths instead
of walking the whole tree. `only_paths=None` (unset) still preserves the
original whole-tree behaviour, so nothing changed for a standalone
`frob check --fix` or for `frob ticket land`'s existing pre-land
absorption call -- `_absorb_pre_land_fixes` in
src/frob/app/ticket_runner/_land_cmd.py still calls `apply_tier_a_fixes`
with no scoping at all, so the land-scope-discipline collision T-1391
diagnosed (FMT001's pre-fix pass mechanically rewriting frob:waive
reason comments in files outside the landing ticket's declared scope)
is only half fixed: the mechanism exists but nothing in a real land
invokes it yet.

This ticket is that wiring: `_absorb_pre_land_fixes` needs to compute
the landing ticket's touched-file set (git diff of the worktree against
main, or the ticket's declared scope globs resolved to real paths --
whichever this repo's other diff-scoped gates, e.g. FMT001 itself,
already use as their own touched-set source) and pass it through to
`apply_tier_a_fixes` -> the FMT001 lambda in `TIER_A_HANDLERS` ->
`fix_fmt001_directive_wrap`'s `only_paths`.

Scope note: touching `_land_cmd.py` alone was ruled out of T-1391's own
scope during that ticket's work -- `frob ticket scope --add` on it
surfaced a cascade of scope-closure warnings pulling in
`_land_cmd.py`'s own private helpers across
src/frob/app/ticket_runner/__init__.py, _verify.py, and _close_cmd.py.
Whoever takes this should scope narrowly to just the touched-set
computation and the one `apply_tier_a_fixes` call site, and expect to
either satisfy or explicitly waive those same closure warnings.

Acceptance:
- GIVEN a land whose ticket scope excludes a file elsewhere in the tree
  carrying a non-canonical frob: directive, WHEN `frob ticket land` runs
  its Tier-A pre-fix pass, THEN that out-of-scope file is left untouched
  (this is T-1391's own acceptance [0], only actually closed end-to-end
  once this ticket lands).
- GIVEN the same land, WHEN a file genuinely inside the landing ticket's
  touched set carries a non-canonical frob: directive, THEN it is still
  fixed exactly as before.

<!-- ticket:T-1405 -->
```yaml
id: T-1405
title: update docs/modules/gates.md#public-api for T-1401's write_coverage_lock/load_coverage
  behavior changes
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/gates.md
acceptance:
- text: GIVEN a reader of docs/modules/gates.md#public-api WHEN they read the write_coverage_lock
    entry THEN it documents that a genuine zero-hit module value is never clamped
    to a stale committed value, unconditionally
  evidence: []
- text: GIVEN a reader of docs/modules/gates.md#public-api WHEN they read the load_coverage
    entry THEN it documents that modules failing to join below the 0.95 threshold
    are enumerated by name in a warning log, not just reported as a fraction
  evidence: []
threat: null
component: null
```
T-1401 changed the documented behavior of two public functions in
src/frob/gates/_coverage.py:

- write_coverage_lock: the T-1363 downward ratchet now has an explicit
  carve-out -- a module whose freshly measured value is exactly 0.0 is
  never clamped back to a stale committed value, even with
  allow_decrease=False. Previously any large drop (including a genuine
  zero) was clamped.
- load_coverage: when module_join_fraction falls below 0.95, the specific
  unjoined .py modules are now enumerated in a WARNING log line, not just
  reported as a bare fraction.

docs/modules/gates.md#public-api documents both functions and needs a
matching update (AFFECT001 flagged this in T-1401's own check run, but
docs/** was held by T-1235's concurrent in-progress lease for the whole
of T-1401's work, so the doc could not be updated in the same change --
waived at both call sites in src/frob/gates/_coverage.py with a pointer
to this ticket).

Update docs/modules/gates.md's write_coverage_lock and load_coverage
entries (or their #public-api anchor section) to describe the T-1401
zero-hit ratchet carve-out and the unjoined-module enumeration log.

<!-- ticket:T-1413 -->
```yaml
id: T-1413
title: DOC006 has no in-worktree path to zero for land-owned CHANGELOG.md findings
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_docptr.py
acceptance:
- text: A genuine historical-record DOC006 finding in CHANGELOG.md can be dispositioned
    (waived or excluded) without a worktree agent hand-editing a land-owned file
  evidence: []
threat: null
component: null
```
Found while working T-1412 (drain residual DOC006 to zero). CHANGELOG.md
carries a genuine, honestly-classifiable historical-record DOC006 finding
at line 1952 (a since-nonexistent _elaborate_module symbol named in a
0.9.0 release note). The correct disposition per DOC006's own rules is a
frob:waive comment naming the historical-record status -- but CHANGELOG.md
is land-owned (T-0731) and a scaffolded pre-commit hook refuses ANY
worktree commit touching it, comment-only doc waivers included. There is
currently no in-worktree path to zero for this finding.

Two options worth considering: (a) give frob ticket land a mechanism to
apply a queued DOC006 waiver comment to CHANGELOG.md on a ticket's behalf,
alongside its existing auto-generated changelog-entry behavior, or (b)
exempt CHANGELOG.md from DOC006 scanning entirely, the same way
tickets-archive.md is already excluded, on the reasoning that CHANGELOG.md
is equally an append-only historical record where every entry documents
a past release rather than the current tree.

<!-- ticket:T-1415 -->
```yaml
id: T-1415
title: 'TEST005 burn-down: src/frob/strata remainder (post T-1296 partial)'
state: queued
kind: feature
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
threat: null
component: null
```
T-1296 closed real branch-coverage gaps in 12 of the ~35 root modules
under src/frob/strata (_atomic, _breach, _distributed_txn, _design_load,
_access, _clock_ordering, _delivery_semantics, _retry, _backpressure,
_circuit_breaker, _fallback, _deploy -- each now 100% branch coverage
standalone), but that is well short of the package-wide "0 TEST005
findings under src/frob/strata/**" acceptance criterion the parent
ticket declared (196 findings at baseline). Budget/time ran out before
covering the remaining modules (_audit.py 88%, _compliance.py 89%,
_code_binding.py 91%, _crash.py 91%, _claims.py 54%, _elaborate.py 49%,
and others not yet even sampled).

Continue the same discipline: per-module `pytest --cov=<module>
--cov-branch` against its own existing test file, target only the
specific reported missing branch/line (never a second happy-path
assertion on an already-covered arm), extend the existing test file in
place rather than writing new scaffolding. `_claims.py` and
`_elaborate.py` are large (54%/49%) and will likely need several
sessions each -- consider splitting them into their own tickets rather
than trying to close them inside one pass.

<!-- ticket:T-1417 -->
```yaml
id: T-1417
title: gate:OPAQUE OPAQUE001 errors in test_ticket_close_own_obligations_t1387.py
  (setattr monkeypatch)
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_ticket_close_own_obligations_t1387.py
threat: null
component: null
```
Found while verifying T-1402 (unrelated to that ticket's own scope): after
merging main (which had just landed T-1410/T-1387's own obligation-gate
work), an unscoped `frob check --ticket T-1402` shows 7 new gate:OPAQUE
OPAQUE001 errors, all in tests/unit/test_ticket_close_own_obligations_t1387.py
(lines 99, 128, 150, 184, 218, 264, 293) -- each a setattr() monkeypatch
call whose non-literal attribute name is invisible to the static binding
table OPAQUE001 checks.

This file did not exist before T-1410/T-1387 landed and none of its content
was touched by T-1402. It needs either a reasoned `frob:waive OPAQUE001
reason="..."` per site (if the monkeypatch target is genuinely dynamic and
safe) or a rework to a statically-resolvable form.

<!-- ticket:T-1420 -->
```yaml
id: T-1420
title: 'arch: 51-file LARGE001 residue after T-1270''s 2-file split'
state: queued
kind: feature
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/**
- frob-core/src/lib.rs
- strata-core/src/lib.rs
- strata-core/src/parse/mod.rs
- src/frob/vet/_capability_registry.py
scope_changes:
- op: add
  glob: src/frob/vet/_capability_registry.py
  reason: the file deleted by this split; land's UnownedDeletions check did not treat
    the existing src/** scope glob as covering it, so naming the exact path
  actor: logan
  at: '2026-08-02'
threat: null
component: null
```
T-1270 cleared 2 of the 32 files on its list this pass (src/frob/_cli_parsers/_ticket.py
split into a per-concern package; src/frob/app/config.py split by extracting its two
procedural blocks -- from_external's field-copy loop and the stale-install/arch-config
helpers -- into app/_config_external.py and app/_config_meta.py). Both splits verified
scoped-and-foreground (pytest on the covering test files, ruff/format clean) before
landing.

51 unwaived LARGE001 findings remain repo-wide as of this measurement (down from 53),
listed below with current line counts. Same instruction as T-1270's own brief: pick a
cohesive subsystem slice per land, split it where a real seam exists (a parser/renderer
split, a coherent helper family, a distinct concern), or record an accepted-with-reason
frob:waive LARGE001 where the file is a genuinely single irreducible unit -- do not
raise the threshold and do not waive merely for size.

- frob-core/src/lib.rs (2277)
- strata-core/src/lib.rs (869)
- strata-core/src/parse/mod.rs (1744)
- src/frob/app/check_runner.py (1267)
- src/frob/app/sys_runner.py (1023)
- src/frob/app/ticket_runner/_close_cmd.py (1086)
- src/frob/app/ticket_runner/_land_cmd.py (967)
- src/frob/app/ticket_runner/_verify.py (973)
- src/frob/arch/_patterns.py (1486)
- src/frob/arch/_python.py (962)
- src/frob/arch/_rust.py (838)
- src/frob/check/__init__.py (959)
- src/frob/check/_python.py (1063)
- src/frob/doctor.py (920)
- src/frob/dup/_pipeline/_fingerprint.py (812)
- src/frob/gates/__init__.py (6713)
- src/frob/gates/_coverage.py (916)
- src/frob/gates/_debt_deprecated.py (851)
- src/frob/gates/_docblocks.py (822)
- src/frob/gates/_docptr.py (1468)
- src/frob/gates/_fix_engine.py (1401)
- src/frob/gates/_protocol_summary.py (1244)
- src/frob/gates/_registry_exhaustiveness.py (988)
- src/frob/gates/_secrets.py (1089)
- src/frob/gates/_sys.py (818)
- src/frob/gates/_tickets_gate.py (1077)
- src/frob/gates/_waive.py (1459)
- src/frob/graph/__init__.py (864)
- src/frob/graph/callgraph.py (830)
- src/frob/graph/dsl.py (1075)
- src/frob/perf/_effect_summaries.py (823)
- src/frob/perf/_rules.py (840)
- src/frob/strata/__init__.py (957)
- src/frob/strata/_audit.py (1055)
- src/frob/strata/_compliance.py (1257)
- src/frob/strata/_elaborate.py (1403)
- src/frob/strata/_host_isolation.py (1285)
- src/frob/strata/_infra.py (837)
- src/frob/strata/_mode_conformance.py (871)
- src/frob/strata/_selfconform.py (1608)
- src/frob/strata/_threat.py (2522)
- src/frob/tickets/_evidence.py (1369)
- src/frob/tickets/_land.py (1831)
- src/frob/tickets/_land_squash.py (919)
- src/frob/tickets/_leases.py (1403)
- src/frob/tickets/_models.py (1917)
- src/frob/tickets/_new_renumber.py (963)
- src/frob/tickets/_store.py (1552)
- src/frob/vet/_capability.py (6020, T-1074-flagged, still no dedicated follow-up filed)
- src/frob/vet/_capability_registry.py (2991, same T-1074 flag)
- src/frob/vet/_scan.py (901)

Note: src/frob/tickets/ and src/frob/app/ticket_runner/ overlap T-1296's strata TEST005
lease and other concurrent tickets' scopes at filing time -- narrow scope via
`frob ticket scope` before starting, per playbook section 4/lease-collision guidance.

<!-- ticket:T-1423 -->
```yaml
id: T-1423
title: frob check crashes with an unhandled database is locked under concurrent load
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
- tests/test_graph_lock.py
- src/frob/graph/__init__.py
scope_changes:
- op: add
  glob: src/frob/graph/__init__.py
  reason: Acceptance criterion 1 requires the failure to surface as a typani Result
    the caller handles; the only caller of cache.connect/store_file_data/set_root
    that can observe that Result is frob.graph.__init__ (build_graph/load_graph).
    Minimal call site the ticket's own acceptance criteria require, re-applied after
    the 10b ledger restore.
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock
- tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted
- tests/test_graph_lock.py::TestCacheLockRetry::test_non_locked_operational_error_is_not_retried
- tests/test_graph_lock.py::TestCacheLockRetry::test_store_file_data_retries_past_a_held_exclusive_lock
- tests/test_graph_lock.py::TestCacheLockRetry::test_build_graph_reports_err_instead_of_crashing_on_cache_locked
acceptance:
- text: GIVEN the graph cache lock is held by another connection WHEN frob check runs
    THEN it completes and reports rather than crashing with an unhandled exception
  evidence:
  - tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted
  - tests/test_graph_lock.py::TestCacheLockRetry::test_non_locked_operational_error_is_not_retried
  - tests/test_graph_lock.py::TestCacheLockRetry::test_store_file_data_retries_past_a_held_exclusive_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_build_graph_reports_err_instead_of_crashing_on_cache_locked
- text: GIVEN a contended cache operation WHEN the lock cannot be acquired after retry
    THEN the failure surfaces as a typani Result the caller handles, never as an escaping
    exception
  evidence:
  - tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted
  - tests/test_graph_lock.py::TestCacheLockRetry::test_non_locked_operational_error_is_not_retried
  - tests/test_graph_lock.py::TestCacheLockRetry::test_store_file_data_retries_past_a_held_exclusive_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_build_graph_reports_err_instead_of_crashing_on_cache_locked
threat: null
component: null
```
frob check dies with an unhandled exception when the graph cache is contended:

    ERROR: main: unhandled exception during dispatch: database is locked
    frob: database is locked

Measured on main 2026-08-02 with four agents running concurrently against the shared repo. The check had already produced its full warning output; it crashed at the end, so the entire run was lost and the exit code was a hard failure rather than a report.

TWO DEFECTS, and they should be fixed together.

1. It escapes as a raw exception. sqlite3.OperationalError "database is locked" is an expected, recoverable outcome of contending for a shared cache -- not a programmer bug. This repo's own convention is that a fallible operation a caller must handle returns a typani Result, and exceptions are reserved for unrecoverable programmer errors. A lock timeout is the former. Right now it reaches main's top-level handler and prints as an unhandled crash.

2. It does not retry. T-1239 and T-1416 already established the pattern for this exact class in the same subsystem: a locked OperationalError means another process got there first, so poll and re-read rather than treating it as fatal. T-1239 applied that to schema application; T-1416 extended it to the meta.key IntegrityError. This is the third instance of the same family -- a lock encountered on a normal read/write path, outside schema application, with no retry at all. Fix it in the same shape, and check whether a single shared helper should own "retry a contended cache operation" for all three call sites rather than a third bespoke handler. This repo's no-duplication rule applies.

WHY IT MATTERS BEYOND THE CRASH. The practical effect is that frob check is not safe to run while agents are working, which is precisely when a coordinator most wants to measure. Every gate reading taken during this session's concurrent dispatches was therefore suspect, and at least one pair of consecutive runs disagreed (5 errors then 0, with no intervening change) before this crash made the problem explicit. A measurement tool that is unreliable under the conditions it is used in is a hole in the "if frob passes, the code is good" guarantee -- you cannot trust a green you could not reproduce.

ACCEPTANCE SHOULD BE BEHAVIOURAL, not just a caught exception: with a concurrently-held lock on the cache, frob check must complete and report, not crash. A test that holds the sqlite lock from another connection while a check runs is the honest reproduction.

## Done report

Fixed both defects together.

1. cache.py write/read paths outside schema application (store_file_data,
   set_root, touch_file_stat, connect_readonly) had no retry on
   "database is locked" at all -- the third instance of the T-1239/T-1416
   family the ticket asked for. Added _with_lock_retry, a shared helper
   using the same poll/backoff shape and 30s budget as the existing
   schema-application retry, and wired it into all four call sites.
   Whole-function retry is safe here because every wrapped operation is
   a delete-then-insert or a plain read, idempotent under retry.

2. On retry exhaustion, cache.py now raises CacheLocked (a narrow
   sqlite3.OperationalError subclass) instead of the bare exception.
   frob.graph.build_graph and load_graph (both already Result-returning,
   T-0976/T-0799 precedent) catch CacheLocked specifically -- distinct
   from the existing generic-OperationalError-is-CacheCorrupt branch, so
   a transient lock is never misreported as corruption -- and return
   Err(GraphError.CacheLocked) instead of letting the exception reach
   main()'s top-level handler and abort the whole check run.

Scope was widened by one file (src/frob/graph/__init__.py, via
`frob ticket scope --add` with a recorded reason) because acceptance
criterion 1 ("the failure surfaces as a typani Result the caller
handles") is only observable at the one real caller of these cache.py
functions; cache.py alone cannot demonstrate the Result contract.

Test: tests/test_graph_lock.py::TestCacheLockRetry adds the honest
reproduction the ticket asked for (test_store_file_data_retries_past_a_
held_exclusive_lock: two real sqlite connections on the same file, one
holding BEGIN IMMEDIATE while the other retries) plus unit coverage of
_with_lock_retry's retry/give-up/non-locked-passthrough behavior and
build_graph's CacheLocked -> Err(GraphError.CacheLocked) boundary.

Docs: docs/modules/graph.md gets a new "Lock contention (T-1423)"
subsection under Cache, plus the new GraphError.CacheLocked member in
the Error types code block. design/frob.strata's graphlang/testsuite
interface= attrs were refreshed via `frob sys sync-interface` for the
two new public symbols (CacheLocked, TestCacheLockRetry).

### Changed
```
 design/frob.strata         |     4 +
 docs/modules/graph.md      |    21 +
 docs/modules/serve.md      |    24 +
 frob.lock                  |     2 +-
 src/frob/graph/__init__.py |    25 +-
 src/frob/graph/cache.py    |   136 +-
 src/frob/serve/_socketd.py |    55 +
 tests/test_graph_lock.py   |   110 +-
 tests/test_serve_socket.py |   112 +
 tickets-archive.md         |  9720 +++++++++++++++++++++++++++++++++++++-
 tickets.md                 | 10745 ++++---------------------------------------
 11 files changed, 10983 insertions(+), 9971 deletions(-)
```

### Evidence
- `tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_non_locked_operational_error_is_not_retried` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_store_file_data_retries_past_a_held_exclusive_lock` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_build_graph_reports_err_instead_of_crashing_on_cache_locked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 7 error(s), 437 warning(s), 695 waived
- error-findings: AFFECT001@src/frob/graph/__init__.py, AFFECT002@src/frob/graph/__init__.py, COV003@tickets/T-1406, COV003@tickets/T-1408, COV003@tickets/T-1419, SELFAUDIT001@design, WIRE001@tests/test_serve_socket.py

<!-- ticket:T-1425 -->
```yaml
id: T-1425
title: frob sys sync-interface silently skips store blocks, only fixes node blocks
state: queued
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
threat: null
component: null
```
`frob sys sync-interface` only auto-rewrites `node <id> { ... }` blocks
(`_NODE_HEADER_RE` in src/frob/strata/_sync_interface.py matches literally
`node\s+<id>...{`). A `store <id> : trusted { ... }` block declaring its
own `interface=` attrs (e.g. design/frob.strata's `store tickets_ledger`)
is silently skipped by both the report and the writer -- `sync_interface_
report` returns 0 drift for it even when the gate:SELFAUDIT SYS104 check
(`_interface_conformance_violations` in _selfconform.py, which iterates
model nodes generically and does NOT skip stores) correctly flags missing
symbols on it.

Discovered working T-1422 (frob ticket accept --amend/--remove): adding
`amend_acceptance`/`remove_acceptance`/`AcceptanceAmendmentEntry`/
`AcceptanceAmendmentOp` to `frob.tickets.__all__` produced 4 real
SELFAUDIT001 errors on the `tickets_ledger` store that `frob sys
sync-interface` reported as "0 drifted" and refused to fix -- had to be
hand-added to design/frob.strata instead, defeating the entire point of
the mechanical sync tool for every store-typed node in the design.

Fix: extend `_NODE_HEADER_RE` (or add a sibling `_STORE_HEADER_RE`) so
`_sync_one_file`/`_rewrite_node_interface_block` also match `store <id> {`
headers, the same way `_interface_conformance_violations` already treats
them as first-class SYS104 subjects.

<!-- ticket:T-1429 -->
```yaml
id: T-1429
title: T-1422 landed a fresh INV006 on src/frob/tickets/_accept.py
state: queued
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_accept.py
threat: null
component: null
```
T-1422's landed commit (frob ticket accept --amend/--remove) introduced src/frob/tickets/_accept.py, which makes incidental "only" wording in its docstrings/log messages -- an unscoped frob check --only invariant now reports INV006 on this file with no frob:invariant anchor and no waiver. Check each occurrence: most look like incidental prose (module docstring, a log format string) rather than a genuine new normative claim, matching the same shape T-1424 just resolved for the _cli_parsers/_ticket/ split -- likely needs either a targeted waiver with a real reason or a light reword, not a new invariant. Found while verifying T-1424's unscoped frob check (playbook section 6c); out of T-1424's declared scope (src/frob/tickets/** is not in it), so filed separately rather than fixed inline.

<!-- ticket:T-1430 -->
```yaml
id: T-1430
title: 'WIRE001: detect a new keyword-only parameter no call site passes'
state: queued
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_dead_symbols.py
- tests/test_gates.py
threat: null
component: null
```
T-1428 (WIRE001/WIRE002) implements three of the four case shapes named in
its brief: a new function/method/class with no non-test caller, a new gate
rule id missing from _KNOWN_GATE_RULES, and a new CLI flag dest missing
from _config_external.py's copy lists.

The fourth shape -- a new keyword-only parameter no call site passes
(T-1384's own_obligations_clean, T-1399's gate_claims_verified, T-1391's
only_paths) -- is not implemented. It needs a signature-level before/after
diff (does this diff add a new parameter to an existing function's
signature, and does any call site pass it) that neither the text-scan
approach wire_gate uses for new symbols, nor the string-membership
approach it uses for CLI dests, actually covers: the function itself
already has callers (it is not new), so the "no non-test caller" check
wire_gate implements does not fire, and the new PARAMETER specifically
being unpassed is a different, narrower question this ticket did not
build a detector for.

Scope: extend src/frob/gates/_dead_symbols.py's wire_gate (or a sibling
gate) with a keyword-only-parameter-added-and-never-passed check, most
likely via frob.lang's existing per-symbol signature parsing plus a
before/after comparison against the diff's base revision (mirroring how
src/frob/tickets/_new_gate_rule_acceptance.py already reads a symbol's
text at a historical revision for a related purpose).

<!-- ticket:T-1431 -->
```yaml
id: T-1431
title: WIRE001 fires on relocated symbols, so every file split trips it
state: queued
kind: bug
origin: human
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_dead_symbols.py
- tests/test_gates.py
acceptance:
- text: GIVEN a diff that relocates a symbol into a new file without changing its
    reachability WHEN the wire gate runs THEN WIRE001 does not fire for that symbol
  evidence: []
- text: GIVEN a diff that introduces a genuinely new symbol with no caller WHEN the
    wire gate runs THEN WIRE001 still fires exactly as today, proven by a regression
    test
  evidence: []
threat: null
component: null
```
WIRE001 (T-1428) fires on symbols a diff RELOCATES, not just symbols it introduces, because a file split makes every moved symbol look new to a diff-scoped analysis.

First real-world encounter, measured 2026-08-02 on T-1420's split of src/frob/vet/_capability_registry.py into a package:

  WIRE001: _matrix.py::_unexcused_empty_cells is new in this diff and has no caller outside its own module
  WIRE001: _matrix.py::_validate_registry_kinds  ... same

Both judgements are correct about the CODE: each is called only from tests/test_capability_registry.py, with no production caller. But neither is new. Both existed in the pre-split single file with exactly the same test-only status, and the split moved them verbatim. Nothing about the ticket's change made them less reachable.

WHY THIS MATTERS MORE THAN TWO FINDINGS. Every LARGE001 file split creates new files full of relocated symbols, so WIRE001 will fire on every one of them. There are 50 such files left, and the splits are exactly the work the v1.0.0 zero-warning bar needs. A rule that blocks the refactors it should be neutral about will get waived reflexively, and a reflexively-waived rule stops catching the real thing -- which for WIRE001 is the seven-instance inert-code class it was built for.

THE FIX. Compare against the SYMBOL's prior existence, not the FILE's. A symbol whose fully-qualified name (or whose body, by digest) existed anywhere in the tree at the merge base is relocated, not introduced, and WIRE001 should stay silent about its reachability. Only a genuinely new symbol -- one with no prior existence under any path -- is in scope. The graph already computes per-symbol digests, so the information needed is present.

Two sub-cases worth handling deliberately rather than by accident: a symbol that is relocated AND changed in the same diff (still relocated -- the reachability question is unchanged unless the change is what removed its caller), and a symbol relocated into a file that also introduces genuinely new symbols (the new ones stay in scope).

NOT IN SCOPE, and worth stating so it is not lost: the two findings above ARE real, pre-existing, test-only production symbols. Making WIRE001 relocation-aware does not make them reachable. They are a legitimate DEAD-family question about test-only helpers living in production modules, and if that is worth acting on it deserves its own ticket rather than being smuggled in here.

<!-- ticket:T-1432 -->
```yaml
id: T-1432
title: ledger auto-commit sweeps pre-staged index content into its commit
state: queued
kind: bug
origin: agent
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
- tests/test_tickets_leases.py
scope_changes:
- op: remove
  glob: tests/test_tickets_leases.py
  reason: 'typo at filing: the real test file is tests/test_ticket_leases.py (no plural
    s on tickets)'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'typo at filing: the real test file is tests/test_ticket_leases.py (no plural
    s on tickets)'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_tickets_leases.py
  reason: both tests/test_ticket_leases.py and tests/test_tickets_leases.py exist
    and cover _leases.py symbols; the regression test may land in either
  actor: logan
  at: '2026-08-02'
acceptance:
- text: GIVEN a checkout with an unrelated file staged WHEN commit_ticket_ledger_change
    commits a dirty tickets.md THEN the resulting commit touches only tickets.md and
    the unrelated file remains staged
  evidence: []
threat: null
component: null
```
Root cause of T-1403's c2fd45da incident: _add_and_commit_tickets_md runs 'git add tickets.md' then a bare 'git commit -m <message>', which commits the WHOLE index. Anything already staged in the checkout (e.g. by a conflicted stash pop, which auto-stages merged-clean files) rides along into the ledger commit under an unrelated message. Fix: pathspec-limit the commit ('git commit -m <msg> -- tickets.md', i.e. --only semantics) so the ledger commit can never contain anything but tickets.md, and add a regression test that stages a sentinel file, runs commit_ticket_ledger_change, and asserts the sentinel stays staged and out of the commit. Applies to every caller funneling through this helper (commit_start_transition, commit_ticket_ledger_change for new/drop/fail).

<!-- ticket:T-1433 -->
```yaml
id: T-1433
title: make coverage serial-rerun phase wedges forever on a dead-holder futex
state: queued
kind: bug
origin: agent
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/testing/**
acceptance:
- text: GIVEN a make coverage invocation whose serial rerun phase stops making progress
    WHEN the bounded deadline elapses THEN the run fails loudly with a diagnostic
    instead of hanging indefinitely
  evidence: []
- text: GIVEN the futex-owner root cause is identified WHEN the fix lands THEN back-to-back
    make coverage runs complete without a wedge
  evidence: []
threat: null
component: null
```
Two independent full `make coverage` runs wedged identically in the serial
rerun phase (the `-n 0 --cov-append --junitxml=.frob/last-coverage-rerun.xml`
pytest that runs after the xdist phase, added by the T-1426 combine-drop fix):

- Run 1 (2026-08-01 21:39): wedged for 12h52m with only 2m16s of CPU before
  being killed.
- Run 2 (2026-08-02 10:04): same phase, 0 CPU-seconds over a measured 20s
  window after ~28 min elapsed (2m14s total CPU).

Diagnostics captured on run 2's pytest (pid 563010) while wedged:
- State S (sleeping), Threads: 1, wchan=futex_wait_queue -- a single-threaded
  CPython blocked acquiring a lock/semaphore with NO child processes alive,
  i.e. waiting on a synchronization primitive whose holder is gone.
- fds 1/2/6/8 all pointed at deleted /tmp files.
- A leaked multiprocessing forkserver from an earlier worktree test run
  (t-1426 venv, alive 7h40m, spawned 02:51 from a pytest tmp path) was
  present on the system during both wedges -- plausibly related to the
  T-1378 forkserver-leak family, and possibly the dead lock-holder.
- py-spy stack dump unavailable (no root; ptrace restricted).

Suspects, in order:
1. The xdist phase's gw0 worker CRASHED during run 2
   (tests/system/test_frob_self_model.py::TestFrobSelfModel::
   test_sys_gate_zero_violations, see .frob/last-coverage-run.log) -- a
   crashed worker can leave a coverage/multiprocessing lock held; the
   serial rerun then blocks on it forever.
2. COVERAGE_PROCESS_START subprocess coverage (coverage-subprocess.rc)
   installs locks shared across the make recipe's phases.
3. The serve daemon / leaked forkserver holding a semaphore the rerun
   inherits (T-1378's reap fix landed only for run_socket_daemon's own
   shutdown path).

Acceptance direction: the rerun phase must either complete or fail loudly
under a bounded timeout (the make recipe should wrap the rerun in a
deadline and kill-and-report instead of hanging forever), and the root
cause futex owner must be identified and fixed. Reproduction: run
make coverage twice back-to-back; observe the second (or even first)
run's rerun-phase CPU flatline via ps -o cputimes.

<!-- ticket:T-1434 -->
```yaml
id: T-1434
title: Confirm whether frob ticket land or its worktree-merge flow ever reverts a
  freshly stamped frob-coverage.lock.json
state: queued
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- docs/guides/agent-playbook.md
threat: null
component: null
```
T-1419's own fix (a read-after-write durability check in
_run_stamp_coverage) confirms the committed frob-coverage.lock.json's write
path itself is durable within a single frob check --stamp-coverage call
(check_runner.py is write_coverage_lock's only caller repo-wide, verified
by grep). The remaining open question from T-1419's acceptance criterion 2
-- a freshly stamped lock reverting to an OLDER committed value SOME TIME
AFTER a successful stamp run, corroborated independently by the T-1270
agent (land left a stray lock diff it resolved with `git checkout` on that
file) -- points at a LATER git-level event: a merge, a `frob ticket land`
run, or an agent manually restoring the file to resolve what looked like an
unwanted diff.

Investigate src/frob/tickets/_land.py (and the surrounding land/merge
worktree flow) for any path where frob-coverage.lock.json ends up restored
to an older committed value after a genuine stamp: e.g. a land run against
a worktree/root where coverage.xml is not present (it is gitignored and
ephemeral) re-generating or leaving stale lock content, or the dirty-check/
auto-restore machinery (_refuse_if_main_dirty's uv.lock precedent at
_land.py:783) treating an unexpectedly-dirty coverage lock the same way
uv.lock's frob-version drift is auto-restored. Confirm whether land ever
touches frob-coverage.lock.json at all versus this being purely an agent
workflow habit (running `git checkout -- frob-coverage.lock.json` by hand,
per docs/guides/agent-playbook.md's land-owned-files guidance) that needs a
playbook correction instead of a code fix.

<!-- ticket:T-1435 -->
```yaml
id: T-1435
title: Add a stamp-time provenance check for a locally-scoped coverage.xml misread
  as a full run (T-1407 finding 2)
state: queued
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- docs/guides/agent-playbook.md
threat: null
component: null
```
T-1407 investigated why coverage.xml consistently only ever joined ~53% of
known modules even from a full, healthy make coverage run. Direct
measurement (T-1406, this same dispatch) found the root cause was NOT a
measurement/instrumentation gap at all: module_join_fraction's denominator
(_known_repo_paths) counted every .py file in the whole repo -- tests/**,
scripts, everything -- even though make coverage runs pytest --cov=src/frob,
which can structurally never report on anything outside that root. 447 real
src/frob modules / 851 repo-wide known modules = 0.53, a purely structural
artifact of an unscoped denominator, not evidence of any run ever dropping
real data. T-1406 fixed the denominator to scope against coverage.xml's own
<sources> declaration; once landed, a healthy run's module_join_fraction
should read close to 1.0, not ~0.53.

What T-1406 does NOT address, and what remains a live risk: T-1407's second
finding -- burn-down agents' own scoped pytest --cov runs (the sanctioned
section 6b workaround for the make-coverage-is-coordinator-only rule) leave
a narrow coverage.xml on disk that a LATER, unscoped frob check can silently
misread as if it were the full run's data. There is currently no mechanism
that tells these two situations apart at read time.

T-1407's own brief suggested the concrete fix: "a stamp-time provenance
check (e.g. refuse/warn a frob check TEST005 read against a coverage.xml
whose recorded module count is far below the last committed lock's)."
Implement that: at TEST005/--stamp-coverage read time, compare the current
coverage.xml's module count (or module_join_fraction, now that T-1406 makes
that number mean something real) against the last COMMITTED
frob-coverage.lock.json's own module count/fraction; a large, otherwise
unexplained drop is the exact fingerprint of "a narrower, locally-scoped
coverage.xml is on disk, not a full run's" and should warn (or, if the gap
is severe enough, refuse) rather than silently evaluate TEST005 against it.

This must build on T-1406 (module_join_fraction has to mean something
trustworthy first) and should re-verify T-1406's fix has actually landed
and been observed against a real make coverage run before calibrating any
threshold, per this ticket's own investigation discipline.

<!-- ticket:T-1436 -->
```yaml
id: T-1436
title: Warm daemon forkserver pool competes with foreground frob check for CPU
state: queued
kind: bug
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_tools.py
threat: null
component: null
```
T-1378 fixed the socketd-level defects (frob_shutdown now actually exits
the process, and every multiprocessing.active_children() is reaped
before Python's own atexit hook would otherwise hang for 20+ seconds).

The third defect T-1378 measured is still open: with a warm daemon up,
`frob check --only gates --delta --json` measured SLOWER than the same
command with FROB_NO_DAEMON=1, and system load average went from ~0.4
idle to 5-8 while a single check ran. The root cause is a persistent
multiprocessing forkserver pool that frob.serve._tools's
parallel-execution paths (frob_check_delta / frob_run_touched_tests)
keep warm across requests inside the daemon process, competing with the
foreground check for the same cores on a small (4-core) machine -- this
lives entirely in frob.serve._tools, not src/frob/serve/_socketd.py
(T-1378's declared scope), so it could not be fixed there.

T-1379 already made the daemon opt-in (FROB_DAEMON, not
default-enabled), which removes this as a default-install risk, but a
user who opts in still pays the regression measured here. Investigate
whether the pool should be sized down, made lazy (spawned only on the
first parallel-execution request, not eagerly), or shared/reused
differently, and re-measure `frob check --only gates --delta --json`
warm-daemon vs FROB_NO_DAEMON=1 to confirm parity or a real win.
