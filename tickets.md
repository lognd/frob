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

<!-- ticket:T-1193 -->
```yaml
id: T-1193
title: 'post-audit residual themes: multi-language obligation gates, fail-open residue,
  gitignored-trust CI story (T-0397 successor)'
state: queued
kind: security
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/design/registry/check-coverage.yaml
- docs/**
acceptance:
- text: GIVEN the six audit-concern rows this ticket tracks (python-only COV/DOC/DRIFT
    enforcement, fail-open residue incl second-lockfile and non-UTF-8 docs, gitignored
    .frob/ trust vs CI, DRIFT001 sig-facet body-blindness, non-python frob:tests execution,
    load_graph new-file snapshot completeness) WHEN each is either enforced by a real
    gate or re-dispositioned with evidence THEN the registry rows move from deferred
    to handled_by and this ticket closes
  evidence: []
threat: null
component: null
```
Successor to the T-0397 audit epic for the concern-family rows NOT yet closed by a landed mechanism (each row's residue verified at epic close 2026-07-29): CHK-THEME-PYTHON-ONLY (partial: arch multi-lang and capability tables landed; COV/DOC/DRIFT edges still python-pipeline-only), CHK-THEME-FAIL-OPEN (partial: PARSE001/002, NATIVE001, tool-unavailable ToolResults landed; second-lockfile scan and non-UTF-8 doc handling unverified), CHK-THEME-GITIGNORED-TRUST (open: coverage/stamp/baseline live gitignored, CI cannot verify), CHK-SUBSYS-GATES-ACCOUNTING (partial: collectors exist for rust/ts/cpp; DRIFT001 sig facet still body-blind), CHK-SUBSYS-LANG-CHECK-DOCS (same python-only class), CHK-SUBSYS-GRAPH-EDGES (unverified: load_graph new-file snapshot completeness, non-UTF-8 md crash).

<!-- ticket:T-1194 -->
```yaml
id: T-1194
title: 'arch: split remaining seams of _land_merge.py/_land_finalize.py -- T-1189
  residue'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_finalize.py
threat: null
component: null
```
## Description

T-1189 extracted ONE cohesive family (the union-zone conflict-block
resolution machinery: `_UnionZone`/`_zone_for_path`/`_union_keyed_chunks`/
`_union_append_only`/`_resolve_conflict_blocks`/
`_resolve_union_zone_conflicts`) out of _land_merge.py into a new
src/frob/tickets/_land_merge_zones.py (1722 -> 1506 lines), continuing the
same one-family-per-land discipline T-1186/T-1187/T-1188 established.
Budget did not allow the other seams T-1189's own plan named.
_land_merge.py is still 1506 lines and _land_finalize.py is still 1735
lines, both above the 800-line LARGE001 threshold.

Still remaining, in the same one-family-per-land shape:

- `_land_merge.py`: the ledger-merge/newest-wins family (`splice_ledger`,
  `_merge_ledger_tickets`, `_resolve_divergence`, `_newer`/`_newer_winner`/
  `_richness`, `_union_evidence`/`_union_acceptance`,
  `_drop_resurrected_ids`, `_preserve_sibling_done_reports`,
  `_carry_forward_new_worktree_tickets`, `_overlay_landed_ticket`,
  `_splice_only_ticket`) vs. the git-plumbing/wip-commit family
  (`_merge_main_into_worktree`, `_auto_resolve_out_of_scope_conflicts`,
  `_wip_commit`/`_wip_add_excluding_frob`/`_do_wip_commit`,
  `_splice_and_stage`/`_splice_and_stage_archive`, `_verify_archive_merge`,
  `_rev_parse`/`_true_merge_base`) -- the deletion-authorization pair
  (`_deletion_glob_too_broad`/`_deletion_owned`) can go with whichever side
  ends up using `_unowned_deletions`.
- `_land_finalize.py`: draft-finalization/sibling-renumbering vs.
  squash-apply/close vs. the release-bump/uv.lock/native-rebuild family
  (T-1189's own plan named this split, not yet started).

Re-filed (not re-derived from scratch) rather than letting T-1189 close
with silent residue, per TICK011.

<!-- ticket:T-1195 -->
```yaml
id: T-1195
title: 'arch: 33-file LARGE001 residue after T-1192 split (_new_renumber.py done)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
## Description

T-1192 split ONE file off its 34-file LARGE001 residue list this land
(src/frob/tickets/_new_renumber.py: 847 -> 691 lines, moving
finalize_draft/finalize_draft_for_land into a new
src/frob/tickets/_draft_finalize.py). Budget did not allow the other 33.

Still unowned, current line counts as of T-1192's own filing (re-measure
before starting -- some may have shifted from unrelated work landing in
between):

- src/frob/_cli_parsers/_ticket.py (1102)
- src/frob/app/check_runner.py (1597)
- src/frob/app/config.py (1167)
- src/frob/app/sys_runner.py (1023)
- src/frob/app/ticket_runner/_land_cmd.py (907)
- src/frob/app/ticket_runner/_verify.py (973)
- src/frob/arch/_patterns.py (1486)
- src/frob/arch/_python.py (1635)
- src/frob/check/__init__.py (953)
- src/frob/check/_python.py (977)
- src/frob/doctor.py (918)
- src/frob/gates/_docblocks.py (1465)
- src/frob/gates/_docptr.py (1000)
- src/frob/gates/_protocol_summary.py (1244)
- src/frob/gates/_registry_exhaustiveness.py (988)
- src/frob/gates/_secrets.py (1088)
- src/frob/gates/_tickets_gate.py (953)
- src/frob/gates/_waive.py (1424)
- src/frob/strata/__init__.py (941)
- src/frob/strata/_audit.py (1055)
- src/frob/strata/_compliance.py (1058)
- src/frob/strata/_elaborate.py (1401)
- src/frob/strata/_host_isolation.py (1281)
- src/frob/strata/_infra.py (837)
- src/frob/strata/_mode_conformance.py (867)
- src/frob/strata/_selfconform.py (1621)
- src/frob/strata/_threat.py (2485)
- src/frob/tickets/_evidence.py (1201) -- its prior owner T-1171 is done;
  the exclusion no longer applies.
- src/frob/tickets/_land.py (1178) -- T-1186's own split left this file
  itself still over threshold; not in T-1189's scope (which covers only
  the two NEW files T-1186 produced), so it is unowned residue too.
- src/frob/tickets/_leases.py (1339)
- src/frob/tickets/_models.py (1873)
- src/frob/vet/_capability.py (5944) -- T-1074 explicitly flagged this
  and the next file as needing a dedicated follow-up but did not file
  one ("budget did not allow investigating a safe split boundary for
  either").
- src/frob/vet/_capability_registry.py (2918)
- src/frob/vet/_scan.py (901)

(src/frob/tickets/_new_renumber.py dropped off this list -- T-1192
brought it under the 800-line threshold.)

## Plan

Same discipline as T-1072/T-1074/T-1186/T-1187/T-1188/T-1189/T-1192: pick
a cohesive subsystem slice per land, split it (or record an
accepted-with-reason disposition per T-1074's precedent if no safe seam
exists), full verification per group, re-measure, re-file remaining
residue rather than closing silently. LARGE001 is a warning-tier,
waivable advisory (`frob:waive LARGE001 reason="..."`, file-level since a
file-level finding has no symref) -- not every file on this list needs a
structural split; a disposition is a valid, honest outcome where a real
split boundary would fragment a genuinely cohesive module (T-1074's own
precedent for the 7 files it dispositioned rather than split).

<!-- ticket:T-draft-53d33977 -->
```yaml
id: T-draft-53d33977
title: 'ledger v2: per-ticket lock + allocator lock primitives'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/process/_lock.py
- src/frob/tickets/_store.py
- tests/unit/test_process_lock.py
- tests/test_tickets_ledger_concurrency.py
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 3) needs a per-ticket

    file lock plus a single tiny allocator lock, replacing the one repo-wide

    `ledger_lock` that serializes every ticket-mutating verb today regardless

    of which ticket(s) they touch. Generalizes the T-0933/T-0982 fix (a

    process-registry reentrancy bug caused by one shared contended resource)

    by removing the shared resource for the common case (one verb, one

    ticket).'
  evidence: []
- text: 'Deliverables: a `ticket_lock(root, ticket_id)` context manager (per-ticket

    flock, e.g. `tickets/T-####/.lock` or an flock on `ticket.md` itself) and

    a separate `allocator_lock(root)` guarding only next-id computation. Both

    must compose safely with the existing `ledger_lock` during the

    compatibility window (section 7) -- do not remove `ledger_lock` yet, this

    ticket only ADDS the new primitives alongside it.'
  evidence: []
- text: 'GIVEN two callers each hold `ticket_lock` for different ticket ids

    WHEN both proceed concurrently

    THEN neither blocks the other (verified with a real concurrent-thread

    test, not just code inspection).'
  evidence: []
- text: 'GIVEN two callers both call the id allocator concurrently

    WHEN both request a next id

    THEN they receive distinct ids (interleaving regression test, mirroring

    T-1090''s `test_two_concurrent_finalize_draft_calls_get_distinct_ids`

    shape).'
  evidence: []
- text: 'GIVEN a caller already holds `ticket_lock` for id X in the same thread

    WHEN it acquires `ticket_lock` for X again (reentrant call)

    THEN it does not deadlock (mirrors `derived_state_lock`''s reentrancy

    discipline, T-0933/T-0982 lineage).'
  evidence: []
threat: null
component: null
```
Ledger v2 design (docs/design/ledger-v2.md section 3) needs a per-ticket
file lock plus a single tiny allocator lock, replacing the one repo-wide
`ledger_lock` that serializes every ticket-mutating verb today regardless
of which ticket(s) they touch. Generalizes the T-0933/T-0982 fix (a
process-registry reentrancy bug caused by one shared contended resource)
by removing the shared resource for the common case (one verb, one
ticket).

Deliverables: a `ticket_lock(root, ticket_id)` context manager (per-ticket
flock, e.g. `tickets/T-####/.lock` or an flock on `ticket.md` itself) and
a separate `allocator_lock(root)` guarding only next-id computation. Both
must compose safely with the existing `ledger_lock` during the
compatibility window (section 7) -- do not remove `ledger_lock` yet, this
ticket only ADDS the new primitives alongside it.

GIVEN two callers each hold `ticket_lock` for different ticket ids
WHEN both proceed concurrently
THEN neither blocks the other (verified with a real concurrent-thread
test, not just code inspection).

GIVEN two callers both call the id allocator concurrently
WHEN both request a next id
THEN they receive distinct ids (interleaving regression test, mirroring
T-1090's `test_two_concurrent_finalize_draft_calls_get_distinct_ids`
shape).

GIVEN a caller already holds `ticket_lock` for id X in the same thread
WHEN it acquires `ticket_lock` for X again (reentrant call)
THEN it does not deadlock (mirrors `derived_state_lock`'s reentrancy
discipline, T-0933/T-0982 lineage).

<!-- ticket:T-draft-4ae257ca -->
```yaml
id: T-draft-4ae257ca
title: 'ledger v2: file-per-ticket store backend (ticket.md + done-report.md)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-draft-53d33977
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_models.py
- src/frob/tickets/_reporting.py
- tests/unit/test_ticket_store.py
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 1) needs the actual

    file-per-ticket store backend: `tickets/T-####/ticket.md` (frontmatter +

    body, reusing the existing `_serialize_ticket`/`_parse_ticket_file`

    per-file primitives) plus a NEW `done-report.md` split out of the body,

    plus `_store_mode` gaining a third "v2" detection branch

    (`tickets/*/ticket.md` present). Blocked by the lock-primitive ticket

    since every write here must take the new per-ticket lock, not the

    whole-ledger `ledger_lock`.'
  evidence: []
- text: 'Do NOT touch `tickets.md`/`_render_ledger`/`splice_ledger` in this

    ticket -- v1 stays fully functional and is the default store mode until

    the separate migration ticket flips the default. This ticket only adds

    the v2 backend as an alternate, detectable mode alongside v1.'
  evidence: []
- text: 'GIVEN a repo with `tickets/T-0042/ticket.md` present

    WHEN `_store_mode(root)` is called

    THEN it returns "v2" (new third branch, existing single/dir detection

    unchanged for repos without a v2 tree).'
  evidence: []
- text: 'GIVEN a v2-mode ticket

    WHEN its Done report is written

    THEN it is written to `tickets/T-####/done-report.md`, a file distinct

    from `ticket.md`, and reading it back reproduces the same text

    byte-for-byte.'
  evidence: []
- text: 'GIVEN a v2-mode ticket with attachments

    WHEN an attachment is added

    THEN it is written under `tickets/T-####/attachments/`, resolving the

    open question in design section 8 in favor of the self-contained layout.'
  evidence: []
threat: null
component: null
```
Ledger v2 design (docs/design/ledger-v2.md section 1) needs the actual
file-per-ticket store backend: `tickets/T-####/ticket.md` (frontmatter +
body, reusing the existing `_serialize_ticket`/`_parse_ticket_file`
per-file primitives) plus a NEW `done-report.md` split out of the body,
plus `_store_mode` gaining a third "v2" detection branch
(`tickets/*/ticket.md` present). Blocked by the lock-primitive ticket
since every write here must take the new per-ticket lock, not the
whole-ledger `ledger_lock`.

Do NOT touch `tickets.md`/`_render_ledger`/`splice_ledger` in this
ticket -- v1 stays fully functional and is the default store mode until
the separate migration ticket flips the default. This ticket only adds
the v2 backend as an alternate, detectable mode alongside v1.

GIVEN a repo with `tickets/T-0042/ticket.md` present
WHEN `_store_mode(root)` is called
THEN it returns "v2" (new third branch, existing single/dir detection
unchanged for repos without a v2 tree).

GIVEN a v2-mode ticket
WHEN its Done report is written
THEN it is written to `tickets/T-####/done-report.md`, a file distinct
from `ticket.md`, and reading it back reproduces the same text
byte-for-byte.

GIVEN a v2-mode ticket with attachments
WHEN an attachment is added
THEN it is written under `tickets/T-####/attachments/`, resolving the
open question in design section 8 in favor of the self-contained layout.

<!-- ticket:T-draft-d8653bfe -->
```yaml
id: T-draft-d8653bfe
title: 'ledger v2: renumber via git mv + multi-file reference rewrite'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-draft-4ae257ca
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_draft_finalize.py
- src/frob/tickets/_store.py
- tests/test_tickets_collision.py
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 4.1) needs renumber

    (and finalize-draft) to operate on the v2 tree: `git mv tickets/<old>

    tickets/<new>` plus rewriting the moved ticket''s own `id:` field, plus a

    multi-file reference-rewrite pass reusing T-1125''s

    `_rewrite_body_prose_references` matching core, re-pointed at a glob over

    `tickets/**/*.md` instead of one ledger''s rendered text. Blocked by the

    store-backend ticket (needs v2 file layout to exist first).'
  evidence: []
- text: 'GIVEN a v2-mode draft ticket directory `tickets/T-draft-<hex>/`

    WHEN it is renumbered to a real id

    THEN `git mv` relocates the directory, the frontmatter `id:` field is

    updated, and the operation is a single small commit touching only the

    renamed directory (no other ticket''s file is touched unless it actually

    cited the old id).'
  evidence: []
- text: 'GIVEN another ticket''s body prose cites the draft id being renumbered

    WHEN the renumber runs

    THEN that citation is rewritten to the final id in the same operation

    (reusing the T-1125 rewrite engine), and a post-renumber `frob doctor`

    sweep finds zero dangling references to the old id.'
  evidence: []
- text: 'GIVEN two ticket directories are both being finalized in one land

    WHEN their per-ticket locks are acquired for the git-mv + rewrite

    THEN they are acquired in sorted-by-id order (no lock-ordering deadlock),

    verified by a concurrent regression test mirroring T-1090''s shape.'
  evidence: []
threat: null
component: null
```
Ledger v2 design (docs/design/ledger-v2.md section 4.1) needs renumber
(and finalize-draft) to operate on the v2 tree: `git mv tickets/<old>
tickets/<new>` plus rewriting the moved ticket's own `id:` field, plus a
multi-file reference-rewrite pass reusing T-1125's
`_rewrite_body_prose_references` matching core, re-pointed at a glob over
`tickets/**/*.md` instead of one ledger's rendered text. Blocked by the
store-backend ticket (needs v2 file layout to exist first).

GIVEN a v2-mode draft ticket directory `tickets/T-draft-<hex>/`
WHEN it is renumbered to a real id
THEN `git mv` relocates the directory, the frontmatter `id:` field is
updated, and the operation is a single small commit touching only the
renamed directory (no other ticket's file is touched unless it actually
cited the old id).

GIVEN another ticket's body prose cites the draft id being renumbered
WHEN the renumber runs
THEN that citation is rewritten to the final id in the same operation
(reusing the T-1125 rewrite engine), and a post-renumber `frob doctor`
sweep finds zero dangling references to the old id.

GIVEN two ticket directories are both being finalized in one land
WHEN their per-ticket locks are acquired for the git-mv + rewrite
THEN they are acquired in sorted-by-id order (no lock-ordering deadlock),
verified by a concurrent regression test mirroring T-1090's shape.

<!-- ticket:T-draft-123962ab -->
```yaml
id: T-draft-123962ab
title: 'ledger v2: archive via git mv, no content rewrite'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-draft-4ae257ca
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_archive.py
- src/frob/tickets/_store.py
- tests/test_ticket_land.py
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 4.3) needs archive to

    become a plain `git mv tickets/T-#### tickets/archive/T-####` per ticket,

    with zero content rewrite -- eliminating the T-0959 archive-clobber

    failure mode structurally rather than guarding it. Blocked by the

    store-backend ticket.'
  evidence: []
- text: 'GIVEN a v2-mode ticket reaching state done or dropped

    WHEN `frob ticket archive` runs

    THEN its directory is `git mv`-ed to `tickets/archive/T-####/` with no

    byte of `ticket.md`/`done-report.md` content rewritten (diff shows a pure

    rename, verified via `git diff --stat` showing 0 insertions/deletions for

    the moved files).'
  evidence: []
- text: 'GIVEN a v2-mode repo where one worktree''s archive tree predates another

    branch''s newer archive sweep (the T-0959 shape)

    WHEN both are merged

    THEN there is no clobber possible -- each archived ticket is a disjoint

    git path, so git''s own merge/rename detection handles the union with no

    custom splice code, verified by a regression test reproducing the T-0959

    incident''s two-sided-divergence shape against the v2 archive path and

    asserting no block is lost.'
  evidence: []
- text: 'GIVEN `blocked_by`/`parent` references into an archived v2 ticket from an

    active ticket

    WHEN the referencing ticket is loaded

    THEN the archived ticket still resolves (load path checks both

    `tickets/*/ticket.md` and `tickets/archive/*/ticket.md`, mirroring

    today''s `load_all` reading both tickets.md and tickets-archive.md).'
  evidence: []
threat: null
component: null
```
Ledger v2 design (docs/design/ledger-v2.md section 4.3) needs archive to
become a plain `git mv tickets/T-#### tickets/archive/T-####` per ticket,
with zero content rewrite -- eliminating the T-0959 archive-clobber
failure mode structurally rather than guarding it. Blocked by the
store-backend ticket.

GIVEN a v2-mode ticket reaching state done or dropped
WHEN `frob ticket archive` runs
THEN its directory is `git mv`-ed to `tickets/archive/T-####/` with no
byte of `ticket.md`/`done-report.md` content rewritten (diff shows a pure
rename, verified via `git diff --stat` showing 0 insertions/deletions for
the moved files).

GIVEN a v2-mode repo where one worktree's archive tree predates another
branch's newer archive sweep (the T-0959 shape)
WHEN both are merged
THEN there is no clobber possible -- each archived ticket is a disjoint
git path, so git's own merge/rename detection handles the union with no
custom splice code, verified by a regression test reproducing the T-0959
incident's two-sided-divergence shape against the v2 archive path and
asserting no block is lost.

GIVEN `blocked_by`/`parent` references into an archived v2 ticket from an
active ticket
WHEN the referencing ticket is loaded
THEN the archived ticket still resolves (load path checks both
`tickets/*/ticket.md` and `tickets/archive/*/ticket.md`, mirroring
today's `load_all` reading both tickets.md and tickets-archive.md).

<!-- ticket:T-draft-600ca3b0 -->
```yaml
id: T-draft-600ca3b0
title: 'ledger v2: doable/list/show glob + derived index cache + flow mining'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-draft-4ae257ca
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_doable.py
- src/frob/tickets/_store.py
- src/frob/app/ticket_runner.py
- tests/test_tickets.py
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md sections 4.2, 4.4, 6) needs

    `doable`/`list`/`show` re-pointed at a `tickets/*/ticket.md` glob instead

    of the monofile load, plus a derived (gitignored) `.frob/tickets-

    index.json` cache to keep them fast at scale -- rebuildable any time from

    the files, never authoritative -- plus a `flow`/velocity-mining surface

    that derives cycle-time/throughput from per-ticket `git log --follow`

    history. Blocked by the store-backend ticket.'
  evidence: []
- text: 'GIVEN a v2-mode repo with N ticket directories

    WHEN `frob ticket doable`/`list`/`show` run

    THEN they produce identical results to today''s monofile-backed output for

    an equivalent ticket set (same blocker/lease-scope logic, verified by a

    parametrized test run against both a v1 fixture and its v2-migrated

    equivalent).'
  evidence: []
- text: 'GIVEN `.frob/tickets-index.json` is missing or stale (mtime older than

    some ticket.md''s mtime)

    WHEN a v2-mode command needing the index runs

    THEN it transparently falls back to a full glob+parse (always correct,

    never silently stale) and then rebuilds the cache.'
  evidence: []
- text: 'GIVEN a v2-mode ticket''s git history (queued -> in-progress -> done

    transitions each a distinct commit against its own `ticket.md`)

    WHEN `frob ticket flow`/velocity mining runs (new command, name TBD)

    THEN it reports per-state cycle time and throughput derived purely from

    `git log --follow` diff hunks on the `state:` field, with no separate

    event log required.'
  evidence: []
threat: null
component: null
```
Ledger v2 design (docs/design/ledger-v2.md sections 4.2, 4.4, 6) needs
`doable`/`list`/`show` re-pointed at a `tickets/*/ticket.md` glob instead
of the monofile load, plus a derived (gitignored) `.frob/tickets-
index.json` cache to keep them fast at scale -- rebuildable any time from
the files, never authoritative -- plus a `flow`/velocity-mining surface
that derives cycle-time/throughput from per-ticket `git log --follow`
history. Blocked by the store-backend ticket.

GIVEN a v2-mode repo with N ticket directories
WHEN `frob ticket doable`/`list`/`show` run
THEN they produce identical results to today's monofile-backed output for
an equivalent ticket set (same blocker/lease-scope logic, verified by a
parametrized test run against both a v1 fixture and its v2-migrated
equivalent).

GIVEN `.frob/tickets-index.json` is missing or stale (mtime older than
some ticket.md's mtime)
WHEN a v2-mode command needing the index runs
THEN it transparently falls back to a full glob+parse (always correct,
never silently stale) and then rebuilds the cache.

GIVEN a v2-mode ticket's git history (queued -> in-progress -> done
transitions each a distinct commit against its own `ticket.md`)
WHEN `frob ticket flow`/velocity mining runs (new command, name TBD)
THEN it reports per-state cycle time and throughput derived purely from
`git log --follow` diff hunks on the `state:` field, with no separate
event log required.

<!-- ticket:T-draft-0ce0d873 -->
```yaml
id: T-draft-0ce0d873
title: 'ledger v2: land merge story on native git per-file merge, retire frob-ledger
  driver'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-draft-4ae257ca
- T-draft-d8653bfe
- T-draft-123962ab
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_verify.py
- .gitattributes
- tests/test_ticket_land.py
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 5) needs `frob ticket

    land`''s merge story rebuilt around git''s native per-file 3-way merge:

    disjoint-scope branches touching different `tickets/T-####/` directories

    need no custom resolution at all. Retires the `merge.frob-ledger` git

    merge driver, `splice_ledger`, `_merge_ledger_tickets`, the archive-

    specific splice (T-0959''s fix), and the sibling-Done-report preservation

    heuristic (T-0577 item 2) -- ALL as dead code once every land runs in

    v2-only mode. Blocked by store backend, renumber, and archive tickets

    (land must be able to finalize/renumber/archive in v2 before its old

    monofile-splice logic can be safely removed).'
  evidence: []
- text: 'Do NOT delete `_land_merge.py`/`_land_merge_zones.py` in the same diff

    as adding v2 land support -- land a v2-aware land path FIRST, gated

    alongside v1 support during the compatibility window; deletion of the

    retired monofile-merge code is the migration ticket''s final-cutover step

    (design section 7.4), not this ticket''s.'
  evidence: []
- text: 'GIVEN two branches each editing a DIFFERENT ticket''s `tickets/T-####/`

    directory

    WHEN both land

    THEN git''s own merge produces zero conflicts (no custom driver invoked),

    verified by an end-to-end land test with two disjoint-scope v2 tickets.'
  evidence: []
- text: 'GIVEN two branches BOTH editing the SAME ticket''s `ticket.md`

    WHEN both attempt to land

    THEN the conflict surfaces as an ordinary git conflict on that one file

    (no `splice_ledger`-class resolution needed), verified by a test asserting

    land refuses loudly rather than silently picking a side.'
  evidence: []
- text: 'GIVEN `.gitattributes` currently registers `tickets.md merge=frob-ledger`

    WHEN v2-only mode is reached (post-migration, this ticket''s own scope)

    THEN that line is removed and no replacement driver is registered.'
  evidence: []
threat: null
component: null
```
Ledger v2 design (docs/design/ledger-v2.md section 5) needs `frob ticket
land`'s merge story rebuilt around git's native per-file 3-way merge:
disjoint-scope branches touching different `tickets/T-####/` directories
need no custom resolution at all. Retires the `merge.frob-ledger` git
merge driver, `splice_ledger`, `_merge_ledger_tickets`, the archive-
specific splice (T-0959's fix), and the sibling-Done-report preservation
heuristic (T-0577 item 2) -- ALL as dead code once every land runs in
v2-only mode. Blocked by store backend, renumber, and archive tickets
(land must be able to finalize/renumber/archive in v2 before its old
monofile-splice logic can be safely removed).

Do NOT delete `_land_merge.py`/`_land_merge_zones.py` in the same diff
as adding v2 land support -- land a v2-aware land path FIRST, gated
alongside v1 support during the compatibility window; deletion of the
retired monofile-merge code is the migration ticket's final-cutover step
(design section 7.4), not this ticket's.

GIVEN two branches each editing a DIFFERENT ticket's `tickets/T-####/`
directory
WHEN both land
THEN git's own merge produces zero conflicts (no custom driver invoked),
verified by an end-to-end land test with two disjoint-scope v2 tickets.

GIVEN two branches BOTH editing the SAME ticket's `ticket.md`
WHEN both attempt to land
THEN the conflict surfaces as an ordinary git conflict on that one file
(no `splice_ledger`-class resolution needed), verified by a test asserting
land refuses loudly rather than silently picking a side.

GIVEN `.gitattributes` currently registers `tickets.md merge=frob-ledger`
WHEN v2-only mode is reached (post-migration, this ticket's own scope)
THEN that line is removed and no replacement driver is registered.

<!-- ticket:T-draft-ffbf6ea3 -->
```yaml
id: T-draft-ffbf6ea3
title: 'ledger v2: migration (frob ticket migrate --to v2, golden round-trip, deprecation
  gate, final cutover)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-draft-53d33977
- T-draft-4ae257ca
- T-draft-d8653bfe
- T-draft-123962ab
- T-draft-600ca3b0
- T-draft-0ce0d873
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
