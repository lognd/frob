# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
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
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
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
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
- docs/modules/lang.md
- docs/modules/dup.md
- tests/unit/test_extract_native.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/lang.md
  reason: 'portion delivered (T-1220''s coherent first slice): only frob-core/** (new
    Rust extraction kernel) plus the two doc anchors it affects touched this pass;
    src/frob/lang/** consumer rewiring and the cpp/rust/typescript walkers remain
    a later portion of this same ticket, not yet started'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/dup.md
  reason: 'portion delivered (T-1220''s coherent first slice): only frob-core/** (new
    Rust extraction kernel) plus the two doc anchors it affects touched this pass;
    src/frob/lang/** consumer rewiring and the cpp/rust/typescript walkers remain
    a later portion of this same ticket, not yet started'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_extract_native.py
  reason: new pytest golden-parity test file for this portion's extract_tree_python
    kernel
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: merge with main required updating the shared testsuite node capability declarations
    touched by this branch (T-1223 test wiring); consistent with T-1223s own scope
    having included this file
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte
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
  evidence:
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
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

## Done report

Portion delivered (this dispatch, still NOT closing T-1220): the rust
companion kernel to the python slice landed earlier under this same
ticket -- second coherent vertical slice, per the ticket's own scoping
(cpp/typescript kernels and the consumer rewiring remain future work).

1. frob-core/Cargo.toml + Cargo.lock: added `tree-sitter-rust@0.24.2`
   (crates.io; no newer release pins cleanly against this crate's
   `tree-sitter@0.25.0` core at time of writing -- verified the add
   resolves and builds cleanly, `make core` clean).

2. frob-core/src/extract.rs: `extract_tree_rust(source: bytes) ->
   (comment_spans, identifiers, tokens)` -- a 3-tuple, not the python
   kernel's 4-tuple, since rust has no python-style string-literal
   docstring facet; rust's `///`/`/** */` doc comments are
   `line_comment`/`block_comment` leaves already, so they land in
   `comment_spans`. This also extended `frob.lang._extract.
   _IDENTIFIER_TYPES` with a `"rust"` entry (`identifier`,
   `type_identifier`, `field_identifier`) -- rust had NO identifier-walk
   counterpart on the Python side before this portion, so the golden-
   parity target this kernel is tested against is new capability added
   in this same change, not a pre-existing one to mirror.

   One real implementation bug the golden-parity check caught and fixed:
   this grammar generation's `line_comment`/`block_comment` nodes are
   NEVER leaves (each carries its own `//`/`/*` delimiter child) --
   unlike python's `comment` node. A leaf-only walk (the approach the
   python kernel uses) silently found ZERO rust comments. Fixed by adding
   `collect_comment_nodes`, a type-match top-down walk mirroring
   `frob.lang._extract._collect_comment_nodes` exactly, used only for
   `comment_spans`; `identifiers`/`tokens` still share the leaf-only walk
   (verified consistent with `_leaf_tokens`'s own literal exclusion
   check, which also only skips a comment when it is itself a leaf).

3. frob-core/src/lib.rs: wired `extract_tree_rust` into the `frob_core`
   `#[pymodule]`.

4. frob-core/frob_core.pyi: typed stub for the new export (never raises,
   verified by `frob check --only ffi_boundary`: 0 errors/warnings).

5. docs/modules/lang.md (Extraction API) + docs/modules/dup.md (frob-core
   kernels) describe the new kernel, the `_IDENTIFIER_TYPES["rust"]`
   addition, and the leaf-vs-type-match comment-walk finding.

6. tests/unit/test_extract_native.py: added `TestExtractTreeRustParity`
   (3 tests) alongside the existing python parity class -- a synthetic
   fixture (struct/impl/field-access/all three comment styles), the
   never-raises contract, and a byte-for-byte parity check against this
   kernel's own source file (`frob-core/src/extract.rs`).

Golden-test proof (ad hoc script, not committed, same precedent as the
python slice): comment_spans/identifiers/tokens compared against
`frob.lang._extract`'s (newly-extended) rust path across this repo's own
`.rs` corpus (frob-core/**, strata-core/**, tests/fixtures/**/*.rs -- 12
files). Result: 0 mismatches across every collection, both before and
after the `--only ffi_boundary`-passing build.

FFI gate compliance: `frob check --only ffi_boundary` -- 0 errors, 0
warnings (whole-file never-raises convention holds; no `# frob:raises`
needed).

Evidence bound (--accepts 0, same acceptance criterion as the python
slice -- this is additional coverage under the same GIVEN/WHEN/THEN, not
a new criterion):
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte

Also ran (scoped regression, unchanged behavior confirmed):
`pytest tests/test_lang.py tests/unit/test_lang_primitives.py
tests/unit/test_xref.py -q` -- all pass (the `_IDENTIFIER_TYPES["rust"]`
addition is additive, no existing language's dispatch table entry
changed).

Merge note: warming up this worktree for the series required `git merge
main` (~20 commits behind); one real conflict in design/frob.strata's
testsuite `may "exec" via ...` line (unioned per the dispatch's merge
rule, not either-side-wins). The merge also surfaced 44 tickets present
in BOTH tickets.md and tickets-archive.md (this worktree's stale base
predates their archival on main) -- `run_gates` refused to load the
queue (DuplicateId) until the stale active-side copies were removed in a
separate ledger-hygiene commit (tickets-archive.md untouched,
authoritative). design/frob.strata's testsuite node needed a scope add
(the merge's union touched it) -- `frob ticket scope T-1220 --add
'design/frob.strata'`, followed by `frob ticket sweep T-1220` to refresh
the now-stale pre-work sweep.

Filed: none -- no out-of-scope work discovered this pass beyond the
ledger-hygiene fix already disclosed above (in-scope, tickets.md is
always implicitly in scope per the playbook).

Gates: `frob check --ticket T-1220 --only scope --only prework --only
fmt --only affect_drift --only ffi_boundary` clean (0 errors, 321
warnings, 1 waived -- warnings are the SAME pre-existing scope-breadth
debt from the ticket's own broad `src/frob/lang/**` glob the prior
portion already disclosed, now 321 vs the prior 203 solely because this
portion's own new `_IDENTIFIER_TYPES`/kernel additions widened the doc/
test-edge surface under that same broad glob; not new debt introduced by
narrowing scope). No new waivers added.

Status: leaving T-1220 IN-PROGRESS, not closing -- this is a second
portion, not the whole ticket. Remaining under this same ticket id: cpp/
typescript kernels, and the consumer rewiring (perf/clones/deprecated/
dead_symbols/opaque/sys), the latter explicitly T-1219's job per the
original dispatch brief this ticket's own Done report already noted.

### Changed
```
 design/frob.strata                |   4 +-
 docs/modules/dup.md               |   4 ++
 docs/modules/lang.md              |  33 ++++++++++-
 frob-core/Cargo.lock              |  11 ++++
 frob-core/Cargo.toml              |   1 +
 frob-core/frob_core.pyi           |  14 +++++
 frob-core/src/extract.rs          | 122 ++++++++++++++++++++++++++++++++++++++
 frob-core/src/lib.rs              |   3 +-
 src/frob/lang/_extract.py         |   6 ++
 tests/unit/test_extract_native.py |  82 +++++++++++++++++++++++++
 tickets.md                        |  95 +++++++++++++++++++++++++++--
 11 files changed, 365 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 451 warning(s), 769 waived
- error-findings: DUP001@frob-core/src/extract.rs, SELFAUDIT001@design

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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
- src/frob/graph/**
- docs/audits/docs-staleness-2026-07-29.md
- src/frob/gates/_doclink.py
- src/frob/gates/_docanchor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/docs-staleness-2026-07-29.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_doclink.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_docanchor.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
121-doc staleness sweep (docs/audits/docs-staleness-2026-07-29.md): 2 class-A gate-flagged findings, ~140 class-B silent misses, 6 gate-gap classes, a drift-lock candidate list, and one code-side bug. Every silent miss indicts a frob gate gap: each gap class becomes a mechanism ticket, plus a fix campaign for the doc content itself.

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
- design/frob.strata
- src/frob/gates/_inv.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
scope_changes:
- op: add
  glob: design/frob.strata
  reason: widen scope to cover interface= declarations touched to close SYS104 SELFAUDIT001
    findings
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/gates/_inv.py
  reason: widen scope to cover interface= declarations touched to close SYS104 SELFAUDIT001
    findings
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1
acceptance:
- text: 'GIVEN frob --help THEN the top level presents a small set of verb groups
    (target: under ~15 entries) with subcommands grouped by intent, every old invocation
    either still working or aliased with a pointer, and the grouped help readable
    by a first-time user'
  evidence: []
- text: GIVEN frob explore THEN map/outline/xref/docs-search live as its subcommands,
    un-deprecated (frob:deprecated markers and sunset warnings removed), with their
    standalone deprecated top-level forms aliased through a transition window
  evidence:
  - tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
  - tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
  - tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
  - tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
  - tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1
- text: GIVEN the regrouping design doc THEN it proposes the full grouping taxonomy
    for every current top-level command with a migration/alias policy, before any
    group beyond explore is implemented
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: frob is intimidating; group everything together. First concrete slice: the T-0580-deprecated navigation commands (map/outline/xref/docs-search) regroup into frob explore instead of being deleted -- this SUPERSEDES the 2026-10-01 sunset (T-0802 dropped with this epic as the reason). Design phase first for the full taxonomy (candidate buckets to evaluate, not prescribe: explore/navigation, quality/check+test+fix, tickets, design/sys+strata, supply-chain/vet, ops/release+registry+natives+doctor+clean, serve/perf tooling); un-deprecation of the explore members includes removing the docs 'Kept commands'/deprecation drift the 2026-07-29 staleness sweep catalogued. Children to file at design time: taxonomy design doc, explore group implementation, alias/transition machinery, help-surface rework, docs/index updates.

## Done report

EPIC closure decision: T-1238's own scope is the frob explore first-slice
(acceptance[1]) plus the design doc (acceptance[2]). Acceptance[0]
(help-surface rework across every other verb group) is explicitly deferred
per the epic's own directive to design the full taxonomy before
implementing anything beyond explore -- tracked by draft
T-1571 (help-surface rework), filed alongside three further
taxonomy-slice drafts (T-1567 quality group, T-1568
design group, T-1569 ops group) and a naming-decision draft
(T-1570). This closure choice was made by the prior session that
implemented the slice (commit 532799ac) and is being finalized here after
a same-day merge with main (main advanced ~25 lands, including two
unrelated conflicting features -- frob refactor verb group T-1200/T-1201
and ticket migrate --to v2 T-1259 -- both preserved, neither touched by
this ticket's own diff).

Post-merge verification performed fresh in this session:
- git merge main required manual resolution of 4 conflicts in
  src/frob/app/{docs,map,outline,xref}_runner.py -- all four were the same
  shape: this branch's un-deprecation commit vs main's now-superseded
  frob:deprecated/DEPR003-waiver block for the same functions. Resolved by
  keeping this branch's un-deprecated side (the correct outcome per this
  ticket's own acceptance[1], which requires exactly that removal).
- .frob-release.json/CHANGELOG.md/pyproject.toml/uv.lock: no manual
  resolution needed, both sides already matched main verbatim after the
  ticket-merge-driver auto-spliced tickets.md.
- git diff main --diff-filter=D --stat: empty, no unintended deletions
  carried forward.
- Scoped verification run fresh post-merge:
  - pytest tests/unit/test_app_runners.py -k "Explore or Outline or Map or
    Xref or Docs": 18 passed.
  - frob check --only archgate --ticket T-1238: 0 errors.
  - frob check --only test --ticket T-1238: 0 errors (repo-wide TEST family
    warnings only, pre-existing).
  - frob check --only coverage --ticket T-1238: 0 errors.
  - frob check --only sys --ticket T-1238: caught 2 new SELFAUDIT001/SYS104
    findings this merge/rebuild surfaced (_add_explore_parser undeclared on
    the cli node's interface= list, TestExploreRunner undeclared on
    testsuite's) -- fixed by adding both attr interface= lines to
    design/frob.strata in their correct alphabetical position. Re-run: 0
    errors.
- Ticket-state bookkeeping: this worktree's very first `frob ticket start
  T-1238` transition had only ever landed in this branch, so restoring
  tickets.md to main's copy (playbook sec 10b step 1) reverted the ticket to
  queued, per the documented first-ticket edge case -- self-repaired via a
  fresh `frob ticket start T-1238` + `frob ticket sweep T-1238`, then
  evidence re-recorded (idempotent, same 5 node ids, bound to
  acceptance[1]).

No new out-of-scope work found this session beyond the design/frob.strata
interface= fix, which is within this ticket's own (now-widened) scope.

### Changed
```
 README.md                         |   3 +-
 design/frob.strata                |   2 +
 docs/commands/map.md              |   3 +
 docs/commands/outline.md          |   3 +
 docs/commands/xref.md             |   3 +
 docs/design/cli-regrouping.md     | 143 ++++++++++++++++++++++++++++++++++++++
 docs/guides/agentic-workflow.md   |   4 +-
 docs/index.md                     |  15 ++--
 docs/modules/app.md               |   6 ++
 docs/modules/cli.md               |  79 +++++++++++----------
 docs/modules/render.md            |   5 +-
 docs/rework.md                    |   4 +-
 src/frob/__main__.py              |   2 +
 src/frob/_cli_parsers/__init__.py |   2 +
 src/frob/_cli_parsers/_core.py    |  15 ++--
 src/frob/_cli_parsers/_explore.py |  71 +++++++++++++++++++
 src/frob/app/_config_external.py  |   1 +
 src/frob/app/app.py               |   4 ++
 src/frob/app/config.py            |   6 ++
 src/frob/app/docs_runner.py       |  15 ++--
 src/frob/app/explore_runner.py    |  61 ++++++++++++++++
 src/frob/app/map_runner.py        |  16 ++---
 src/frob/app/outline_runner.py    |  16 ++---
 src/frob/app/xref_runner.py       |  22 ++----
 tests/unit/test_app_runners.py    |  48 +++++++++++++
 tickets.md                        |  31 ++++++++-
 26 files changed, 474 insertions(+), 106 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 7598 warning(s), 755 waived
- error-findings: DUP001@src/frob/app/app.py, DUP001@tests/unit/test_app_runners.py

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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
- src/frob/_cli_parsers/_reporting.py
- src/frob/app/ticket_runner/_mutate.py
- docs/modules/gates.md
- tests/test_gates_drift_ack.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/app/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/graph/lock.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates_drift_ack.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
T-1203's mutation-audit harness (src/frob/strata/_mutation_audit.py, SecondDetectorGap) proves that today only exec/net/fs.read/fs.write have a genuine independent second detector (the seccomp export -- node_allowed_syscalls/_SECCOMP_KIND_MAP): these are real OS-syscall-backed capabilities. The 7 app-level kinds actually declared in design/frob.strata (eval, env, ffi, install-hook, sql, deserialize, fetch_url) have no OS-syscall analog, so faking a seccomp entry for them would be dishonest (no real syscall corresponds to e.g. 'sql'). Acceptance [0] of T-1203 wants EVERY may to be double-detected by two independent mechanisms; this ticket is to design and build a real second detector for these 7 kinds -- e.g. a generated capability-manifest/allowlist artifact (distinct code path from scan_file_capabilities/SYS100) whose diff independently reacts to a may deletion/substitution, mirroring the seccomp-export precedent but for app-level capabilities instead of syscalls.

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
- docs/modules/gates.md
- src/frob/gates/_waive.py
- src/frob/gates/_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
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
- src/frob/gates/_waive.py
- tests/test_gates_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
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
- docs/guides/agent-playbook.md
- src/frob/tickets/_land_git_ops.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN a CI run WHEN the coverage stamp or delta baseline is absent, stale
    or tampered THEN the build fails rather than silently degrading to a pass
  evidence: []
threat: repudiation
component: null
```
T-1265 made the ci.yml self-gate blocking and added a TEST012 check for frob-coverage.lock.json, the one committed coverage channel. The residue it did not close: the coverage stamp and the delta baseline still live in .frob/, which is gitignored and never restored in CI, so TEST005/TEST006 remain structurally inert there. CHK-THEME-GITIGNORED-TRUST in docs/design/registry/check-coverage.yaml is repointed here.

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
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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

<!-- ticket:T-1452 -->
```yaml
id: T-1452
title: 'strata: design argument-level may scoping (may KIND of TARGET)'
state: queued
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1440 parent: argument-level `may` scoping follow-up (design sketch item
5, explicitly deferred to documentation-only by T-1440's own acceptance
plan): e.g. `may "env.read" of "FROB_*"` narrowing WHICH env vars, fs
paths, or net hosts a grant covers, not just which FILES (`via`) may
exercise it. Natural follow-up once `via` itself has real migrated usage
(T-1440's sibling migration ticket) to learn argument-scoping shapes
from. Not designed in detail yet -- this ticket is a placeholder for that
design pass, not a ready-to-implement plan.

<!-- ticket:T-1459 -->
```yaml
id: T-1459
title: vet _capability split design
state: queued
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: T-1420
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet.py
- tests/test_vet_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1420 LARGE001 residue: src/frob/vet/_capability.py is 6070 lines (T-1074-
flagged, largest unwaived LARGE001 file repo-wide). This ticket is the
SPLIT DESIGN only -- do not implement blind; a follow-up ticket implements
it once this design is reviewed.

## Seam analysis (measured via `grep -n '^def \|^class ' src/frob/vet/_capability.py`)

The module already reads as a scanner CORE plus a strict per-LANGUAGE
alias/binding-resolution family repeated six times (Python, TypeScript,
Rust, C, Kotlin) plus the tail-end fingerprint/opaque-indirection
aggregation layer. Each per-language family is internally self-contained
(its own scope-binding walk, alias table builder, resolved-candidate
collector, `_<lang>_binding_capabilities`/`_<lang>_binding_operations`
pair) and calls back into the scanner core only through a small, already-
named set of shared helpers (`_needle_hits_outside_comments`,
`_compiled_capability_patterns`, `ByteSpan` family, `_DangerousOperation`).
This is the same shape the registry package split (T-1420, already landed
this ticket's earlier portion: `src/frob/vet/_capability_registry/`) found
in the sibling file -- same treatment applies here.

Proposed module boundaries (verbatim moves, one seam per land, same
discipline as every other T-1420 split):

1. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_core.py` (~180-820, ~640 lines): pattern
   compilation (`_compile_patterns`, `_compiled_capability_patterns`),
   comment/docstring/non-executable byte-span helpers (`_comment_byte_spans`
   through `_non_executable_byte_spans`), the needle-matching primitives
   (`_needle_to_ws_pattern` through `_needle_hits_as_bare_call`), and the
   embedded-code-region family (`_looks_like_embedded_code` through
   `_embedded_operations`). Every per-language module imports from here;
   this module imports from no per-language module -- it is the shared
   floor, so it must land FIRST if this is done incrementally.

2. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_python.py` (~820-1670, ~850 lines): the
   `_py_*`/`_python_*`/`_resolve_py_*`/`_record_py_*`/`_bind_py_*` family
   -- scope binding, alias table construction, resolved-candidate
   collection, `_python_binding_capabilities`/`_python_binding_operations`.

3. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_typescript.py` (~1670-2745, ~1075 lines): the
   `_ts_*`/`_collect_ts_*`/`_resolve_ts_*`/`_record_ts_*`/`_bind_ts_*`
   family, same shape as Python's, plus TS-specific require/dynamic-import
   handling (`_ts_require_call_module`, `_ts_dynamic_import_module`, the
   `_ts_dynamic_import_then_*` chain) that has no Python analog.

4. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_rust.py` (~3282-4043, ~760 lines): the
   `_rust_*` family -- `use`-declaration binding (`_bind_rust_use_as_clause`
   through `_rust_use_table`), scope binding, alias tables,
   `_rust_binding_capabilities`/`_rust_binding_operations`.

5. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_c.py` (~4043-4744, ~700 lines): the `_c_*`
   family -- macro alias table, declaration/scope binding, alias tables
   (including the array/structured-binding/default-param alias variants C
   has that the other languages don't), `_c_binding_capabilities`/
   `_c_binding_operations`/`_extra_c_binding_operations` (note:
   `_c_binding_capabilities`/`_c_binding_operations`/
   `_extra_c_binding_operations` currently sit textually AFTER the Kotlin
   block at ~5208-5274, not adjacent to the rest of the `_c_*` family --
   move them here too, verbatim, to keep the per-language module
   cohesive rather than mirroring the current file's accidental ordering).

6. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_kotlin.py` (~4744-5274, ~530 lines): the
   `_kt_*` family -- import table, callable-reference resolution, alias
   table, `_kt_binding_capabilities`/`_kt_binding_operations`/
   `_extra_kt_binding_operations`.

7. `src/frob/vet/_capability.py` (remaining, ~5274-6070 minus the C tail
   moved to (5), ~700 lines): stays the package's public entry surface --
   `_operation_entry_matches`, `_resolved_candidates_for_language`,
   `_binding_fingerprints`, the CVE-fingerprint scan family
   (`_yaml_load_call_lacks_explicit_loader` through
   `_scan_file_fingerprints`), `_decode_to_exec_signal`/
   `_body_reaches_decode_and_exec`, the directory-level aggregation
   (`_scan_directory_capabilities`/`_aggregate_capabilities`/
   `_scan_directory_fingerprints`/`_aggregate_fingerprints`), self-path
   exclusion (`is_self_pattern_path`/`_is_self_path`/`_is_test_path`), and
   the public `scan_file_capabilities`/`language_for`/
   `non_executable_line_numbers` entry points near the top of this range
   (~2908-3184) -- these dispatch across every per-language module by
   calling `_resolved_candidates_for_language`, so they belong with the
   dispatcher, not with any one language.

   Also stays here: the `_OpaqueFinding` class and the opaque-indirection
   scan family (`_split_top_level_args` through `_needle_construct_findings`
   and beyond, ~5771-6070) -- this is a DIFFERENT concern (structural
   opaqueness of a needle's argument, not capability/operation binding)
   that happens to live in the same file today; worth a SEPARATE follow-up
   ticket to ask whether it should move to its own
   `_capability_opaque.py` rather than folding it into step 7's dispatcher
   module by default -- flagging here rather than deciding unilaterally in
   this design ticket.

## What the registry package split (already landed, T-1420) already absorbed

`_capability_registry.py`'s own LARGE001 split (this ticket's earlier
portion, see Done report) is the PRECEDENT this design follows: verbatim
per-concern module extraction (`_dangerous_ops_python.py`,
`_dangerous_ops_other.py`, `_matrix.py`, `_kinds.py`, `_schemas.py`,
`_opaque.py`) under a package `__init__.py` that re-exports the public
surface unchanged. `_capability.py`'s split should follow the SAME
external-surface-unchanged discipline: `import frob.vet._capability` (or
`from frob.vet._capability import scan_file_capabilities`, etc.) from any
caller outside this module must keep working without a caller-side edit,
whether the final shape is a flat sibling-file split (as sketched above)
or a `_capability/` package mirroring the registry's own package shape --
that packaging decision (flat siblings vs. a package directory) is left
open for whoever implements this, not fixed by this design.

## Why this session did not implement it

Time/effort budget for this T-1420 session was allocated to closing out
the smaller, unambiguous files on the ticket's scope list first (see the
`_new_renumber.py`/`_renumber_v2.py` split landed this session). A ~6000
line, 180-symbol, six-language file is not something to split blind in
the time remaining -- this design ticket exists so the NEXT session (or
this one, if time allows) can implement steps 1-6 as a clean sequence of
one-seam-per-land commits without re-deriving the seam analysis from
scratch.

## Acceptance

- [ ] Design reviewed (seam boundaries above judged unambiguous, or
      revised) before any implementation ticket starts moving code.
- [ ] Implementation, if undertaken, follows the verbatim-relocation +
      frob:waive-carry + same-commit doc/test-edge-repoint discipline
      every other T-1420 split in this ticket's history used.

<!-- ticket:T-1466 -->
```yaml
id: T-1466
title: extend T-1433 SIGUSR1 stack-dump handler beyond pytest-only scope
state: queued
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/conftest.py
- src/frob/testing/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1433's SIGUSR1 stack-dump handler (tests/conftest.py::_install_stackdump_handler/_dump_all_thread_stacks) is currently wired ONLY into the pytest test-session lifecycle (pytest_configure), gated behind FROB_COVERAGE_STACKDUMP. WIRE001 flags both helpers as unreached outside their own tests, since tests/conftest.py itself is a test-path the gate's text scan skips. Follow-up: evaluate whether frob's own daemon/CLI processes (frob serve, frob check's own subprocess pool) would benefit from the same opt-in handler for non-coverage-recipe wedges, or whether the current pytest-only scope is intentionally final (in which case this ticket should close as won't-fix with that recorded).

<!-- ticket:T-1478 -->
```yaml
id: T-1478
title: argument-level may scoping (T-1440 follow-up)
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/surface.md
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
docs/strata/surface.md documents argument-level `may` scoping (e.g.
`may "env.read" of "FROB_*"`, narrowing WHICH env vars/paths/hosts a
grant covers, not just which files) as deliberately deferred by T-1440's
own scope cut, saying "its own follow-up ticket (T-1440's child) rather
than bundled into the grammar/join landing; see tickets.md for its id" --
but no T-1440 child ticket was ever actually filed. File it for real
(this ticket) and build argument-level may scoping. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

<!-- ticket:T-1479 -->
```yaml
id: T-1479
title: wire remaining daemon-proxy subcommands named by T-0321's integration map
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/**
- docs/modules/serve.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
docs/modules/serve.md's daemon-proxy section says T-0321's integration
map names outline/map/xref/parse/graph/exports/bind/docs/stats as
eventual proxy targets alongside check --delta-style reads, and that
these remain a disclosed residual, not yet wired. T-0321 itself is done
(tickets-archive.md); no open follow-up currently tracks wiring the
remaining subcommands through the daemon proxy. Wire the remaining
named subcommands (or a subset chosen by the implementer, disclosed in
the Done report) through frob.serve._tools/query() the same way
T-1128/T-1147 wired frob_graph_query/frob_doable_tickets/
frob_run_touched_tests/frob_check_delta. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

<!-- ticket:T-1480 -->
```yaml
id: T-1480
title: build frob sys check/trace/capacity/threats verbs
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/sys_runner.py
- docs/commands/sys.md
- src/frob/strata/_mutation_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
docs/commands/sys.md documents frob sys as having five verbs today
(plan/doc/export/audit/sync-interface) and names check/trace/capacity/
threats as later phase-5 verbs not yet landed on main. No ticket
currently tracks building these four verbs. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

<!-- ticket:T-1481 -->
```yaml
id: T-1481
title: wire frob check --fix CLI flag to the tiered fix engine
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/app/check_runner.py
- docs/design/check-fix-engine.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
docs/design/check-fix-engine.md's "Status quo" section states
apply_tier_a_fixes has no CLI entry point: src/frob/app/check_runner.py
and src/frob/_cli_parsers/_check.py have no --fix/Fix reference, so
`frob check --fix` does not exist as a runnable command. Wire a --fix
flag through _cli_parsers/_check.py and check_runner.py that invokes
apply_tier_a_fixes (and, once T-1262/T-1263 land, the Tier-B/Tier-C
paths). Found while draining NEGEXIST001 (T-1477): the doc's
absence-claim had no frob:until binding.

<!-- ticket:T-1482 -->
```yaml
id: T-1482
title: build policy refinement-monotonicity diff pass (INV-030)
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/policy.md
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
docs/strata/policy.md documents that policy refinement is DESIGNED to be
monotonic downward (a child may only strengthen an inherited policy,
never weaken it), but compile_policies/_resolve_scope only resolve scope
membership -- there is no refinement-diff pass that compares a child's
policy set against its parent's and flags a weakening. The paragraph
currently states design intent, not an enforced guarantee (also
disclosed via a frob:waive INV003 reason on the same section). Build
the refinement-diff pass. Found while draining NEGEXIST001
(T-1477): the doc's absence-claim had no frob:until binding.

<!-- ticket:T-1483 -->
```yaml
id: T-1483
title: wire frob refactor into main CLI dispatch
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
docs/commands/refactor.md documents frob.refactor._cli.add_refactor_parser
and run_refactor_command as built and ready, but T-1197's declared scope
never included src/frob/_cli_parsers/** or src/frob/__main__.py, so the
one-line _add_refactor_parser(sub) wiring call was never actually made.
Wire frob refactor into the main CLI dispatch. Found while draining
NEGEXIST001 (T-1477): the doc's own "not yet wired" claim had
no frob:until binding.

<!-- ticket:T-1487 -->
```yaml
id: T-1487
title: 'rust: python tree-extraction kernel in frob-core (T-1220 delivered portion
  1)'
state: queued
kind: feature
origin: agent
created: '2026-08-03'
priority: high
parent: T-1220
tier: ticket
sprint: null
scope:
- frob-core/**
- tests/unit/test_extract_native.py
- docs/modules/lang.md
- docs/modules/dup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
acceptance:
- text: GIVEN the delivered kernel WHEN the golden-parity tests run THEN they pass
    and ffi_boundary reads 0 errors
  evidence:
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
threat: null
component: null
```
Leaf carrier for T-1220's first portion: extract_tree_python in frob-core (tree-sitter 0.25 kernel; comment spans, docstring spans, identifiers, token stream behind one non-raising FFI entry), golden-verified byte-for-byte against the Python path across 917 repo files with one documented grammar-generation delta. Consumer rewiring stays T-1219; cpp/rust/ts walkers remain under T-1220.

## Done report

Carrier for T-1220 portion 1; see the parent ticket Done report for
the full delivery narrative (917-file golden parity, FFI compliance,
grammar-generation delta documentation).

### Changed
```
 docs/modules/dup.md               |   7 +
 docs/modules/lang.md              |  23 +++
 frob-core/Cargo.lock              | 196 +++++++++++++++++++++-
 frob-core/Cargo.toml              |   2 +
 frob-core/frob_core.pyi           |  13 ++
 frob-core/src/extract.rs          | 215 ++++++++++++++++++++++++
 frob-core/src/lib.rs              |   6 +
 src/frob/vet/_capability_core.py  | 174 +++++++++++++-------
 tests/test_vet.py                 |  42 +++++
 tests/unit/test_extract_native.py | 123 ++++++++++++++
 tickets.md                        | 336 +++++++++++++++++++++++++++++++++++++-
 11 files changed, 1068 insertions(+), 69 deletions(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 5 error(s), 299 warning(s), 745 waived
- error-findings: DUP001@frob-core/src/extract.rs, F401@/home/logan/projects/frob/.claude/worktrees/w18r-rust/src/frob/vet/_capability_core.py:30, INV006@frob-core/src/extract.rs, SELFAUDIT001@design, WIRE001@tests/unit/test_extract_native.py

<!-- ticket:T-1503 -->
```yaml
id: T-1503
title: WIRE001 on test_extract_native.py's _python_side/_rust_side golden-test helpers
state: queued
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_extract_native.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
WIRE001 flags `_python_side`/`_rust_side` in tests/unit/test_extract_native.py
(T-1220's golden-parity tests for frob_core.extract_tree_python) as unreached
outside their own tests -- they exist solely as per-file test helpers that
assemble the existing Python-side computation vs the native kernel's output
for comparison within TestExtractTreePythonParity's own methods, mirroring
the tests/unit/test_conftest_stackdump.py::_load_conftest precedent (T-1466).
Follow-up: evaluate whether this pair should move to a shared test-support
module (frob.testing or a conftest fixture) if a future native-extraction
golden test wants the same comparison, or whether the current per-file scope
is intentionally final (in which case this ticket should close as won't-fix
with that recorded).

<!-- ticket:T-1505 -->
```yaml
id: T-1505
title: 'vet/resolvers: close remaining 3 structural points-to gaps (rust macro_rules,
  cpp ptr-to-member, kotlin operator-invoke) -- T-1063 residue'
state: queued
kind: bug
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1063's Done report closed 3 of 6 tracked structural points-to gaps and
left 3 genuinely residual (its own body already documents why each is
architecturally deeper than a table addition, quoted from T-1063):

- rust: `macro_rules!` expansion emitting a fixed call. No macro-expansion
  handling exists anywhere in the Rust resolver; closing this means
  expanding a macro body's tokens as if inlined at the invocation site, an
  AST transformation the resolver's plain-walk architecture does not
  support.
- c++: pointer-to-member (`auto p = &Ops::run; (obj.*p)(x);` / `->*`). No
  pointer-to-member alias tracking exists AND the C/C++ candidate
  collector has no handling for a `.*`/`->*` dereference as a call target.
- kotlin: operator-invoke (`class Handler { operator fun invoke(x) = ... };
  val h = Handler(); h(x)`). Needs receiver-INSTANCE points-to -- no
  instance points-to of any kind exists in the kotlin resolver today.

Each row is locked by its own honest non-firing/non-resolving litmus
fixture in tests/test_vet.py (per T-1063's evidence). T-0339 stays open
against these 3 rows until this closes or each gets a reasoned
OPAQUE_SOURCE_INVISIBLE excuse instead.

Filed as the TICK011 remediation for T-1063 (drain-to-zero warning
burn-down, this ticket).

<!-- ticket:T-1506 -->
```yaml
id: T-1506
title: 'docenum: widen _extract_members to resolve argparse choices=[...] lists'
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_docenum.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
frob.gates._docenum's `_extract_members` cannot resolve argparse
`choices=[...]` lists (cycle.md/xref.md --lang, parse.md tool table) --
a `parser.add_argument(..., choices=[...])` call site has no bare
module/class-level assignment target `_find_node_for_qualname` can walk
to at all. Widen `_extract_members` to this shape so doc-enum coverage
extends to CLI choices lists the same way it already covers
Literal/frozenset assignments.

Follow-up filed as the TICK0/TODO002 remediation for the dangling
`frob:todo T-draft-323551f5` directive at
src/frob/gates/_docenum.py::_extract_members (drain-to-zero warning
burn-down, this ticket) -- that draft id was never actually filed as a
real ticket.

<!-- ticket:T-1508 -->
```yaml
id: T-1508
title: z3-solver fails to build in worktrees, blocking dup._pipeline._smt TEST005
  burn-down
state: queued
kind: bug
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_pipeline/_smt.py
- tests/unit/test_dup_smt.py
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
src/frob/dup/_pipeline/_smt.py has TEST005 module-line coverage of 21.0%
(floor: 70%). Its own test file (tests/unit/test_dup_smt.py) correctly
skips when z3-solver is not importable -- but in this worktree,
`uv sync --extra smt` (the "frob[smt]" optional dependency group) fails
outright to build the z3-solver wheel:

  LibError: Unable to build Z3.
  hint: `z3-solver` (v5.0.0.0) was included because `frob[smt]`
  (v0.319.0) depends on `z3-solver`

This blocks raising this module's coverage from any worktree session
until the z3-solver build issue is resolved (likely needs a system
package -- cmake/a C++ toolchain matching what z3-solver's sdist build
expects -- or a prebuilt wheel pin). Filed while working T-1307 (TEST005
burn-down: src/frob/dup); T-1307's own scope was amended to exclude this
finding as environment-blocked rather than force it.

## Failure log
- 2026-08-05 attempt 1: z3-solver has no aarch64 linux wheel compatible with this glibc 2.35 host for any version, and sdist builds fail both directions: 5.0.0.0 needs a GCC with C++20 format header (absent in the system GCC 11.4), while 4.9.1.0 and earlier need CMake below 3.5 support (removed from the installed CMake 3.22); genuinely un-buildable in this worktree, not a pyproject fix

<!-- ticket:T-1521 -->
```yaml
id: T-1521
title: 'strata: decide whether flow src/dst validation belongs inside elaborate()
  itself'
state: queued
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Disclosed cut from T-1196: check_cross_file_references only covers the two
reference shapes elaborate() itself does not already validate at all
(flow src/dst). Whether flow src/dst validation belongs inside elaborate()
itself (so a single-file design also gets it too) is left as a design
question for this follow-up.

<!-- ticket:T-1533 -->
```yaml
id: T-1533
title: CorpusError needs a dedicated write-failure member
state: queued
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/registry/_corpus.py
- src/frob/app/registry_runner.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1359 made src/frob/registry/_staleness.py::sync_gate_rule_entries's
write crash-safe via frob.tickets._store.atomic_write, but on the
(should-never-happen) I/O failure path it has to reuse
CorpusError.FileNotFound as a stand-in -- not semantically accurate --
because CorpusError (src/frob/registry/_corpus.py) has no dedicated
write-failure member, and the two call sites that key a message dict on
CorpusError (frob.app.registry_runner._CORPUS_ERROR_MESSAGES,
frob.app.ticket_runner._land_cmd's synced.danger_err logging) sit
outside T-1359's declared scope (src/frob/gates/_fmt_directives.py,
src/frob/registry/_staleness.py, src/frob/release/**).

Add a CorpusError.WriteFailed member in src/frob/registry/_corpus.py,
have sync_gate_rule_entries return it instead of the FileNotFound
stand-in, and update _CORPUS_ERROR_MESSAGES (src/frob/app/registry_runner.py)
plus any other CorpusError-message dict to cover it so no caller KeyErrors
on the new variant.

<!-- ticket:T-1534 -->
```yaml
id: T-1534
title: WIRE001 false-positives on autouse pytest fixtures (no call-site to find)
state: queued
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
land-repair for t-1321: WIRE001 flags _isolate_from_host_git_config in
tests/test_ticket_land.py (T-1393's autouse pytest fixture that isolates
every fixture repo in this module from the host machine's real git
config) as unreached outside its own tests -- WIRE001's text scan looks
for name(...)-shaped call occurrences, but an autouse=True pytest
fixture is invoked implicitly by pytest's own fixture-injection
machinery, never by a literal name() call anywhere in the file. This is
the same class of detector gap as T-1502/T-1527 (WIRE001's text-scan
missing a real-but-non-call-shaped wiring mechanism), specialized to
autouse fixtures. Teach WIRE001 to recognize @pytest.fixture(autouse=True)
-decorated functions as wired by construction, or otherwise special-case
the shape.

<!-- ticket:T-1538 -->
```yaml
id: T-1538
title: gates.md stale doc anchor for moved redaction engine (frob.security._redact)
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled: original draft T-1538 (filed during T-1318) died in the t-1350 ledger corruption spans. One stale doc anchor in docs/modules/gates.md still points at the pre-move frob.gates._secrets redaction internals; file was leased by T-1205 at the time. Repoint to frob.security._redact's section.

<!-- ticket:T-1539 -->
```yaml
id: T-1539
title: 'PERF012 registry-entry gap: PERF012 detector exists with no CHK-GATE-PERF012
  registry row'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled: original draft T-1539 (filed during T-1225's perf-detector work) died in the t-1350 ledger corruption spans. PERF012 fires from src/frob/perf but docs/design/registry/check-coverage.yaml has no CHK-GATE-PERF012 entry -- pre-existing gap found (not caused) by T-1225.

<!-- ticket:T-1542 -->
```yaml
id: T-1542
title: fix 10 stale ticket-id citations DOC011 found, then promote DOC011 WARN to
  ERROR
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/audits/README.md docs/audits/perf.md docs/modules/dup.md docs/modules/gates.md
  docs/modules/serve.md docs/modules/strata.md docs/modules/tickets.md docs/strata/host.md
  src/frob/gates/_doclink_docanchor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1486 shipped DOC011 (a T-####/T-draft-<hex> mention in doc prose that
does not resolve to any active or archived ticket) as a WARN-severity
gate rather than ERROR, specifically because its first live run against
this repo's own docs tree found 10 genuine pre-existing stale citations,
entirely outside T-1486's own declared scope to fix:

  docs/audits/README.md:31        T-draft-0b60dd31
  docs/audits/perf.md:159         T-draft-bafbce1c
  docs/modules/dup.md:615         T-draft-d6bca168
  docs/modules/gates.md:1175      T-0104
  docs/modules/gates.md:1177      T-draft-4e98abb1
  docs/modules/gates.md:1178      T-draft-05d8f716
  docs/modules/serve.md:726       T-draft-8a56400c
  docs/modules/strata.md:254      T-9999 (may be an intentional example)
  docs/modules/tickets.md:2235    T-draft-2f611252
  docs/strata/host.md:542         T-draft-7b5b5541

Most are T-draft-<hex> ids that finalized to a real T-#### long ago --
fix each by resolving what the draft became (git log/tickets-archive.md
should show the renumber) and updating the citation, or confirm T-9999
is deliberately illustrative and leave it (maybe reword to make that
obvious, e.g. T-####). T-0104 needs its own check: either a genuine typo
for a real id, or a citation that should be dropped.

Once this list is provably empty (re-run `frob check --only docstatus`
unscoped), promote DOC011's severity from WARN to ERROR in
src/frob/gates/_doclink_docanchor.py::_doc011_violation -- this ticket
was only ever meant as a soft landing, not the permanent posture.

<!-- ticket:T-1544 -->
```yaml
id: T-1544
title: 'Tier-A auto-fix: TICK006 phantom draft citation refile+renumber'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1531: when a TICK006 finding names a draft citation absent from both the ledger and archive, refile a real ticket for it and renumber the citation to the new real id. Needs a Tier-A handler that parses the phantom draft id, files a real ticket capturing recoverable context, and rewrites the citation -- T-1125's prose-reference rewrite already handles the case where the draft DOES exist in the ledger.

<!-- ticket:T-1545 -->
```yaml
id: T-1545
title: 'Tier-A auto-fix: SYS100 EXTENDED-kind capability declaration (eval/process-control/ffi/...)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/strata/_sync_may.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1531: SYS100's EXTENDED case (eval/process-control/ffi/install-hook/sql/deserialize/html_render/fetch_url/client_storage, _selfconform.py::_extended_kind_violations) fires per-NODE with no per-file evidence -- there is no single observed file a Tier-A writer could add to a may via list without guessing which of a node's many bound files actually exercises the capability. Needs either a finer per-file extended-kind scan before an auto-fix is even possible, or a deliberately-conservative whole-node (via-less) grant-insertion policy with its own written justification. T-1531's fix_sys100_may_via_union only handles the CORE (net/fs-write/exec, THREAT004-delegated) case.

<!-- ticket:T-1546 -->
```yaml
id: T-1546
title: 'frob refactor rename: detect bound-evidence references and offer --replace
  rebind'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1537 (frob ticket evidence --replace): that ticket shipped the CLI primitive (replace_evidence) but not the detection half its own body named -- frob refactor rename (or an equivalent rename-detection pass) should notice when a renamed/parametrized symbol/test node id is bound as a ticket's evidence and offer (or auto-apply) the matching --replace rebind, closing the loop the T-1520 parametrization incident exposed by hand.

<!-- ticket:T-1549 -->
```yaml
id: T-1549
title: 'Tier-A auto-fix: ClaimDivergence re-run via done-report recap'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1531: a ClaimDivergence land refusal already has a documented manual recipe (re-run the ticket's done-report with its existing why text -- the recap re-measures the claim against current evidence). Wire a Tier-A handler that performs exactly that through the T-1262 verify-or-rollback transaction like every other handler here.

<!-- ticket:T-1551 -->
```yaml
id: T-1551
title: unify duplicated committed-lock-reading test helpers (test_coverage_attribution_lock_t1395.py
  + test_makefile_coverage.py)
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_coverage_attribution_lock_t1395.py
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
tests/unit/test_coverage_attribution_lock_t1395.py::_load_committed_lock
and tests/unit/test_makefile_coverage.py::TestCommittedLockCoverageFloor.
_load_committed_lock (a class method, self-bound) both independently read
module_line out of the repo-root frob-coverage.lock.json for a regression
lock, using near-identical logic. T-1490 evaluated promoting the former
to a shared helper and found this second occurrence, but T-1490's own
scope (tests/unit/test_coverage_attribution_lock_t1395.py only) does not
cover tests/unit/test_makefile_coverage.py, so unifying both into one
shared load_coverage_lock test helper is left as this follow-up rather
than expanded into T-1490 silently.

<!-- ticket:T-1552 -->
```yaml
id: T-1552
title: 'ledger v2: delete v1 splice machinery once main is migrated'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1631
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_ledger_merge.py
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_merge_zones.py
- .gitattributes
- docs/modules/tickets.md
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
## Description

T-1491 (final cutover) deliberately did NOT delete the v1 splice
machinery (`_render_ledger`, `splice_ledger` in
`src/frob/tickets/_land_ledger_merge.py`, `_land_merge.py`,
`_land_merge_zones.py`, the `tickets.md`/`tickets-archive.md`
`.gitattributes` merge-driver lines) because this repo's OWN ledger is
still v1-mode as of T-1491's session -- every ticket mutation across a
multi-agent dispatch still depends on `splice_ledger` via the registered
git merge driver. Deleting the machinery before this repo's own
`tickets.md`/`tickets-archive.md` content is actually migrated to v2
(via `frob ticket migrate` once the v1-to-v2 migrator is CLI-wired --
see T-1492) would break every in-flight worktree's ticket operations
immediately.

## Plan

Blocked on: T-1492 (CLI wiring for `frob ticket migrate --to v2`), the
follow-up default-flip ticket (T-1553, renumbers at land), and
a coordinator-chosen quiet window (per this ticket's own stated
precondition) to actually run the migration against this repo's real
`tickets.md`/`tickets-archive.md`.

1. Coordinator runs `frob ticket migrate --to v2` against this repo in a
   quiet window (zero in-flight worktrees).
2. Observe the LEDGERV1001 deprecation window for the recorded interval.
3. Delete `_render_ledger`, `splice_ledger`, `_land_merge.py`,
   `_land_merge_zones.py`, remove the `.gitattributes` merge-driver
   lines, remove `tickets.md`/`tickets-archive.md` from the repo (or
   archive them as historical artifacts per the coordinator's call).

## Acceptance

- [ ] GIVEN this repo's own ledger has been migrated to v2 in a quiet
      window WHEN this ticket lands THEN `_render_ledger`, `splice_ledger`,
      `_land_merge.py`, `_land_merge_zones.py`, and the `.gitattributes`
      merge-driver lines no longer exist, and `frob check` reports zero
      references to any of them.

<!-- ticket:T-1554 -->
```yaml
id: T-1554
title: 'land: design the remaining post-commit checkpoint gap beyond the sweep window
  (T-1523 follow-up)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1523 closed a narrow slice of this (the post-land unscoped-error sweep's
own killable window, via a durable marker + read-only reconciliation on
the next invocation). Two larger design questions from its body remain
open:

- Option A (full): make EVERY intermediate land state durable/self-
  describing, not just the sweep window, so a kill at ANY instant is
  recoverable, including push and --finish's own worktree-removal step
  (currently believed safe/idempotent per playbook section 0 item 9 and
  T-1175's LAND-PROOF, but never load-bearing-verified against a real
  SIGTERM injection the way T-1523's own test suite does for the sweep).
- Option B: a separately-invocable `frob ticket land --verify-only <sha>`
  resumable CLI step, decoupled from a fresh merge/commit entirely.

Needs its own design doc before implementation, same as T-1523's body
said before it was scoped down.

<!-- ticket:T-1556 -->
```yaml
id: T-1556
title: 'cli hygiene remainder: warning collapse, read-only check --ticket, close porcelain,
  cli-hygiene principles doc (T-1271 split)'
state: queued
kind: ux
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
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
Split from T-1271: its dispatch delivered criterion 0 (enum-valued flag errors list every valid value inline) with bound evidence; these four criteria were not implemented in that worktree and were drafted there as T-1557, which cannot survive a land preview (land-splice draft-loss class). Filed as a real main-side ticket so T-1271 can land its delivered portion with an honest acceptance trail.

<!-- ticket:T-1557 -->
```yaml
id: T-1557
title: 'cli hygiene remainder: warning collapse, read-only check --ticket, close porcelain,
  cli-hygiene doc'
state: queued
kind: ux
origin: human
created: '2026-08-04'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/tickets/**
- src/frob/check/**
- docs/design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1271's own declared scope (src/frob/_cli_parsers/__init__.py, src/frob/
app/config.py, docs/modules/app.md, tests/test_app_config.py) covers only
the AppConfig pydantic layer -- it cannot reach the actual argparse parser
builders (src/frob/_cli_parsers/_ticket/**, _check.py, etc.), the
scope-closure warning emitter, frob check's lease requirement, or ticket
renumber's own --help text, all of which several of T-1271's acceptance
criteria depend on. T-1271 implemented the minimal honest core that DOES
fit its scope (a generic AppConfig field_validator that gives every
ticket-model enum flag -- state/kind/kind_value/tier/tier_value/
priority_level/origin/review_verdict -- an inline valid-values error
message, replacing the bare TicketState(v)-shaped ValueError) and disclosed
the rest here rather than silently widening scope.

Remaining work from T-1271's acceptance criteria, for a properly-scoped
follow-up ticket (or several):

1. (AC0 remainder) Non-ticket-model enum-shaped CLI flags still raise
   whatever their own conversion path raises with no valid-values list --
   e.g. check_type ("python"/"cpp"/"rust"/"typescript", a plain string
   field with no argparse choices=), any argparse choices= flag whose
   error text isn't already argparse's own (which DOES list choices).
   Audit src/frob/_cli_parsers/**/*.py for every type=/dest= flag lacking
   argparse choices= or an AppConfig-level validator and either add
   choices= or a validator per the T-1271 precedent.

2. (AC1) Repeated advisory warnings (scope-closure on `ticket new` observed
   flooding 5000+ lines in one invocation) need to collapse to a counted
   summary with a --verbose escape hatch. Likely lives in
   src/frob/tickets/_scope*.py or wherever scope-closure warnings are
   emitted, plus a new --verbose-style AppConfig field and _cli_parsers
   wiring -- outside T-1271's scope.

3. (AC2) `frob check --ticket` for a read-only invocation (review, show,
   brief) should never require or mutate a lease. Lives in
   src/frob/check/** (lease acquisition) -- outside T-1271's scope.

4. (AC3) A porcelain verb that sequences the ticket close happy path
   (start -> done-report -> evidence -> accepts -> close), plus
   documenting `ticket renumber`'s positional-only contract with --help
   examples. Lives in src/frob/tickets/** and _cli_parsers/_ticket/**  --
   outside T-1271's scope.

5. (AC4) A short cli-hygiene principles doc under docs/design/ (not
   docs/modules/app.md, which is T-1271's only in-scope doc target) plus a
   checklist test/gate rule verifying new parsers against it (every flag's
   help string states its default; no flag silently changes another
   flag's meaning). docs/design/ was not in T-1271's scope globs.

Filed by T-1271's Done report (2026-08-04) per the epic-closure
"minimal honest core, disclose the rest" instruction.

<!-- ticket:T-1558 -->
```yaml
id: T-1558
title: 'WIRE001 module-local test-helper false-positive class: teach the gate or wire
  the helpers (T-1490/T-1488 successor, waiver home)'
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN a module-local pytest helper (fixture factory, git-init scaffold, parametrized-data
    builder) with no direct call-site the callgraph can see THEN WIRE001 either recognizes
    the pytest usage pattern natively or the helper is wired/bound explicitly -- and
    the 16 waivers currently binding here are deleted
  evidence: []
threat: null
component: null
```
Successor to T-1490 and T-1488, which closed while 16 frob:waive WIRE001 directives still named them, orphaning the waivers into WIRE002 errors (2026-08-05 incident). This ticket is the OPEN waiver home those 16 directives rebind to; it stays open until the class is actually resolved. Siblings: T-1503 (extract_native golden helpers), T-1534 (autouse fixtures).

<!-- ticket:T-1567 -->
```yaml
id: T-1567
title: 'cli regrouping: frob quality verb group (check/test/dup/arch/bind/cycle/mutate/perf)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1567 (T-1238 taxonomy slice; the draft died in the land-splice draft-loss class before T-1271's land). Group the quality-facing verbs under one frob quality namespace following the frob explore precedent (T-1271/T-1238, src/frob/_cli_parsers/_explore.py + explore_runner.py).

<!-- ticket:T-1568 -->
```yaml
id: T-1568
title: 'cli regrouping: frob design verb group (sys/registry/docs/graph/exports)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1568 (T-1238 taxonomy slice, draft-loss class). Group design/model verbs under frob design following the frob explore precedent.

<!-- ticket:T-1569 -->
```yaml
id: T-1569
title: 'cli regrouping: frob ops verb group (release/natives/doctor/clean/fleet/deploy/scaffold/gitlog/stats)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1569 (T-1238 taxonomy slice, draft-loss class). Group operational verbs under frob ops following the frob explore precedent.

<!-- ticket:T-1570 -->
```yaml
id: T-1570
title: 'cli regrouping: resolve ticket/debt/deprecated naming (frob tickets vs frob
  ticket)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1570 (T-1238 naming-decision slice, draft-loss class). Decide and implement the singular/plural verb naming for ticket/debt/deprecated surfaces as part of the T-1238 regroup.

<!-- ticket:T-1571 -->
```yaml
id: T-1571
title: 'cli regrouping: help-surface rework -- group verbs in frob --help output'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1571 (T-1238 slice, draft-loss class; also cited by T-1238's Done report). Rework the top-level frob --help output to present the T-1238 verb groups instead of the flat 30+ subcommand list.

<!-- ticket:T-1572 -->
```yaml
id: T-1572
title: 'frob coverage: add --base override, thread through make coverage-fast BASE='
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from worktree draft T-draft-a385ed9f (T-1526 follow-up; drafts cannot be cited by reports that must survive a land preview). make coverage-fast BASE=<ref> was honored by the old shell recipe but frob coverage currently hardcodes the touched-set base; add a --base flag and pass BASE through the Makefile wrapper.

<!-- ticket:T-1579 -->
```yaml
id: T-1579
title: 'WAIVE004 auto-fix: mass-stale states can never self-heal -- add detector-proven
  escape from the count guard'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1620
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- docs/modules/gates.md
- docs/design/check-fix-engine.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_proceeds
threat: null
component: null
```
The T-1323 mass-invalidation guard refuses to delete when >= 5 waivers of one rule go stale in one run. Correct for degraded runs -- but it also means a rule whose waivers become GENUINELY mass-stale (detector tightened, mass refactor) is permanently uncleanable: every run re-flags them, the auto-fix always refuses, warnings never drain. The guard cannot currently tell 'detector died' from 'detector ran and they really are all stale'.

Refinement: when the SAME self-manufactured run produced >= 1 live finding of the target rule elsewhere in the tree, the detector demonstrably ran and can find that rule -- mass-staleness is then trustworthy, and deletion may proceed (still capped per run, still one rule at a time, still logged per waiver). When the rule has ZERO findings anywhere (the degraded signature, exactly what T-1578's structural signal also targets), keep refusing as today. Depends on T-1578 conceptually but is independently implementable; blocked_by is intentionally not set.

## Done report

`_mass_invalidation_rule` (singular, first-match-wins) refused the
ENTIRE WAIVE004 auto-fix batch whenever any one rule's stale-waiver
count in a self-manufactured run met `_WAIVE004_MASS_INVALIDATION_
THRESHOLD` (5) -- correct for a degraded run (the 2026-07-29 incident
this guard was built for), but it also meant a rule whose waivers
become GENUINELY mass-stale (a detector tightened, a mass refactor
removed the pattern several waivers covered) could never be cleaned by
this handler again: every run re-flags the same waivers, every run
refuses, warnings never drain.

Implemented the refinement exactly as scoped: `_mass_invalidation_
rules` (plural) now returns every rule meeting the threshold, and each
is judged independently by the new `_rule_has_live_finding` -- if the
SAME self-manufactured run's `report.violations` also contains at
least one REAL (non-WAIVE004) finding of that rule elsewhere in the
tree, the detector demonstrably ran and can still find it, so
mass-staleness is trustworthy and that rule's candidates proceed to
deletion (still one rule's own candidates at a time, still logged per
waiver, still capped by the same threshold per rule). A mass-stale
rule with ZERO live findings anywhere keeps refusing exactly as
before -- unchanged from the pre-T-1579 behavior for the genuinely
degraded case, and unchanged for every rule that never hits the
mass-invalidation threshold in the first place.

`docs/modules/gates.md`'s WAIVE004 incident writeup gained a
"Refinement (T-1579)" paragraph describing the same self-heal logic.
`docs/design/check-fix-engine.md` was in scope but needed no edit --
its "no threshold loosening" anti-goal section describes a different
mechanism (baseline/ratchet comparison) this change does not touch.

Residual, disclosed rather than forced (same shape as T-1577's Done
report): a `--ticket T-1579`-scoped `frob check` sees SCOPE001/SCOPE002
<!-- frob:waive DOC006 reason="historical Done report: docs/modules/gates_e501_autofix.md was real when this landed; T-1580's own follow-up (also in this ledger) later folded it into gates.md and deleted it" -->
noise against 3 files T-1581 touched in this same worktree
(`docs/modules/gates_e501_autofix.md`, `src/frob/gates/_fmt_
directives.py`, `tests/test_gates_fix_engine.py`) because T-1581's own
code commit (90d65fc2) did not include "T-1581" in its subject line --
T-0108's cross-ticket SCOPE001 exemption keys off a `T-\d{4}` reference
in the attributing commit's subject, and that commit predates this
observation (fixing it now would mean amending an already-referenced,
already-Done-reported commit, which the git safety protocol forbids
without an explicit user request). `_fix_engine.py` itself is exempt
from this since T-1579's own declared scope covers it directly.
`frob check --land-parity` -- the actual land-sweep-equivalent check --
reports CLEAN (0 unscoped errors) against the current combined
worktree tree, confirming this is per-ticket-scoped-check noise from
multi-ticket-worktree sequencing, not a real land blocker.

Separately, while verifying T-1579's own gates, found and fixed one
more instance of the SAME ambiguous-scope-coverage gap T-1577's own
edit to `_waive.py` exposed (`_WAIVE004_STRUCTURALLY_UNVERIFIABLE_
RULES` ambiguously covered by 3 open tickets' scopes at once,
T-1577/T-1342/T-1339) -- resolved with an explicit `frob:ticket T-1577`
directive, committed under T-1577's own scope (`_waive.py` is not in
T-1579's declared scope) as a small follow-up commit
(f90842a5), not folded into this ticket's own changes.

### Changed
```
 docs/modules/gates.md              |  72 ++++++++++----
 docs/modules/gates_e501_autofix.md |  31 ++++--
 src/frob/gates/_fix_engine.py      | 181 +++++++++++++++++++++++----------
 src/frob/gates/_fmt_directives.py  |  10 +-
 src/frob/gates/_waive.py           |  37 ++++++-
 tests/test_gates.py                | 103 +++++++++++++++++++
 tests/test_gates_fix_engine.py     |  78 +++++++++++++++
 tickets.md                         | 198 ++++++++++++++++++++++++++++++++++++-
 8 files changed, 626 insertions(+), 84 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_proceeds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 1135 warning(s), 785 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1583 -->
```yaml
id: T-1583
title: 'write_archive is v1-only: frob ticket archive loses tickets in a v2 repo'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- tests/unit/test_ticket_store.py
- tests/test_gates.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
load_archive is store-mode aware (T-1256: v2 globs tickets/archive/T-####/ticket.md), but write_archive still unconditionally replaces the tickets-archive.md monofile. In a v2 repo the two disagree: archive() writes every archived ticket into a file load_archive will NEVER read, then write_all drops those same tickets from the active store -- the tickets disappear from every read path. Same asymmetry in _new_renumber.py's write_archive call.

Surfaced by tests/test_gates.py::TestTick006PhantomFiling::test_filed_as_real_archived_id_is_silent: write_archive put T-0137 in tickets-archive.md, load_archive globbed the v2 archive tree, found nothing, and TICK006 called a genuinely archived id a phantom.

Fix: give write_archive a v2 branch that writes each ticket through write_archived_ticket (T-1561's per-ticket archive writer) and prunes tickets/archive/T-####/ dirs absent from the map, preserving the wholesale-replace contract the v1 branch has. Every prune logged. Tests: a v2-mode archive round trip (write_archive then load_archive returns the same map) and a prune case.

<!-- ticket:T-1584 -->
```yaml
id: T-1584
title: Wire frob profile CLI (show/downgrade) to frob.tickets._profile
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/app/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Filed while working T-1575: downgrade_profile_ratchet has no CLI caller yet (WIRE001-waived with this follow_up). Add a top-level 'frob profile show' / 'frob profile downgrade --reason ...' subcommand pair. The downgrade path must stay loudly logged and explicit -- the T-1575 ratchet upgrades automatically but never downgrades on its own.

<!-- ticket:T-1585 -->
```yaml
id: T-1585
title: 'rapid profile: evidence/done-report leniency for docs/chore, REL001 off, baseline-thread-free
  land'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Filed while working T-1575: rapid profile's TEST016-skip and pre-commit-sweep-skip seams landed; three remaining rapid semantics from T-1575's body are still open: (1) evidence/done-report requirements light for kind=docs/chore, (2) REL001 off under rapid, (3) no baseline snapshot worktree at all -- today rapid still runs the T-1463 baseline thread because _land_cmd.py's post-land sweep reads the same result. Ledger integrity and LAND-PROOF stay non-negotiable in every profile.

<!-- ticket:T-1586 -->
```yaml
id: T-1586
title: 'test isolation: scrub inherited FORCE_COLOR/NO_COLOR in conftest'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/conftest.py
- docs/modules/logging.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
should_color honors FORCE_COLOR and NO_COLOR, and a CLI subprocess a test spawns inherits the whole environment. A shell exporting FORCE_COLOR=3 (Claude Code and several CI images do) embeds ANSI escapes in every CLI output a test asserts on: 5 system tests failed here purely from the ambient shell while the same commit passes elsewhere. An autouse conftest fixture now deletes both per test (delete, not force NO_COLOR, so color-path tests can still monkeypatch either one). Needs a regression test asserting a spawned CLI produces escape-free output with FORCE_COLOR set in the parent env.

<!-- ticket:T-1587 -->
```yaml
id: T-1587
title: 'ledger v2: Done reports were invisible to every body-reading consumer'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_reporting.py
- tests/unit/test_ticket_store.py
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
v2 stores the Done report in tickets/T-####/done-report.md for lock independence (write_done_report), and set_done_report's v2 branch deliberately leaves ticket.body untouched. But load_all's v2 branch parsed only ticket.md, so Ticket.body never carried the report -- while EVERY consumer reads it from body: close's substantive-report check (_evidence.py), evidence recovery from the report, TICK006 phantom-filing resolution (_tickets_gate.py), the land ledger merge's has_done_report comparisons (_land_ledger_merge.py), and recover_done_report_why.

Effect in any v2 repo: frob ticket close refuses a ticket whose Done report was written seconds earlier ('write a ## Done report heading'), TICK006 goes blind, and the land-side merge cannot tell which side has a report. Observed as MissingEvidence close failures in the suite.

Fixed by making the in-memory Ticket canonical: load_all/load_archive splice done-report.md back into body (_merge_sibling_done_report), write_ticket's v2 branch splits it back out so a load-modify-write round trip never duplicates it into ticket.md, set_done_report returns the merged ticket so its return value matches the next load, and the v2 index cache keys on sibling done-report.md mtimes too (otherwise a report write would not invalidate the cache, since it never touches ticket.md).

Follow-up worth considering: an integration test that runs the full new -> start -> evidence -> done-report -> close cycle against a v2 repo end to end. The unit layer missed this because each half was individually correct.

<!-- ticket:T-1592 -->
```yaml
id: T-1592
title: WIRE001 waivers on permanently-unwired private test helpers should not require
  an open follow_up
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_wire.py
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
A WIRE001 waiver must name an OPEN follow_up ticket (WIRE002 fires when it names a done one). That is right for "this symbol is not wired up YET" -- but wrong for a private test-seed helper used only by its own file's test methods, where having no production caller is the permanent, intended design. Such a waiver has no real follow-up work to point at, so it gets bound to whatever ticket happened to be open at the time and turns into a WIRE002 orphan the moment that ticket closes.

Live instance: tests/unit/test_mutation_sweep_queue.py::_make_ticket named T-1518, which landed, so main now carries a WIRE002 error for a waiver whose own reason states the condition is permanent by design. tests/unit/test_ticket_file_flags.py has the identical _make_ticket precedent.

Fix: let a WIRE001 waiver declare permanence instead of a follow-up -- an explicit permanent=true attribute (or a reason-preset the gate recognizes) that satisfies WIRE002 without naming a ticket, restricted to private symbols under the test tree so production code cannot use it to dodge real wiring. Then sweep the existing test-helper waivers onto it.

Related: T-1559 closed the other half of this class (refusing/auto-migrating orphaned follow_up waivers at close/land time). This is the same problem approached from the other side: some waivers should never have needed a follow-up at all.

<!-- ticket:T-1597 -->
```yaml
id: T-1597
title: 'Language support expansion: C#, Java, CUDA, Zig, Bash and the top 20-50 languages'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: epic
sprint: null
scope:
- src/frob/lang/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Umbrella for expanding frob's language support from its current set to the most widely used languages, and for hardening the cross-language machinery that expansion depends on.

Two goals, and the SECOND is the real one:

1. Coverage: named explicitly by the user -- C#, Java, CUDA, Zig, and Bash/Shell -- plus the rest of the top 20-50 languages, chosen from evidence rather than intuition (see the research child).

2. Stress-testing the machinery. Every language added is an independent probe of whether frob's abstractions are genuinely language-agnostic or quietly Python-shaped. Each new adapter that needs a special case in shared code is a design bug in the shared layer, not a quirk of the language. Expansion is how those get found. Treat a required special case as a finding to ticket, not a detail to absorb.

Sequencing: the research/ranking child and the adapter-contract child come FIRST. Adding languages one at a time against an unspecified contract is how the current per-language drift happened; the contract must be explicit and statically enforced before the batch work starts.

Non-negotiable for every language added: directive parsing (the frob comment DSL) must work in that language's comment syntax, symbol extraction must produce stable node ids, and the language must participate in the obligation graph (doc edges, test edges, waivers) exactly like Python does. A language that can only be parsed but cannot carry obligations is not supported, it is merely tokenized.

<!-- ticket:T-1598 -->
```yaml
id: T-1598
title: 'Language expansion: research and rank the target set, define per-language
  semantics'
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: T-1597
tier: story
sprint: null
scope:
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Produce the evidence base for the expansion, so the language set is defensible rather than a guess.

Deliverables:

1. A ranked target list of 20-50 languages, each row citing its sources. Use several independent rankings and say where they disagree: TIOBE, RedMonk, GitHub Octoverse, Stack Overflow Developer Survey, and IEEE Spectrum are the usual five; weight by what a frob user is plausibly running in a repo that needs obligation tracking, not by raw popularity alone (COBOL and MATLAB rank higher than their relevance here; CUDA and Zig rank lower than theirs).

2. Per language: tree-sitter grammar availability and maturity (this repo already depends on tree-sitter-language-pack -- record which targets it already ships, which need a separate crate, and which have no usable grammar at all, since that last group changes the cost dramatically).

3. Per language: comment syntax for the directive DSL, including the awkward cases -- languages with no line comment, languages where the block comment cannot nest, and languages with significant indentation that constrains where a directive may sit.

4. Per language: what "public symbol" even means. This is where the abstraction will strain. Header/implementation splits in C/C++, Java package-private, Rust pub(crate), Go capitalization, C# internal, and shell functions with no visibility concept at all do not share one definition. The research must state the intended per-language rule BEFORE any adapter is written.

5. A recommended batch order, with the user's five named languages (C#, Java, CUDA, Zig, Bash) first.

Output goes in docs/ as a durable reference, not just a ticket comment -- later batches read it.

<!-- ticket:T-1599 -->
```yaml
id: T-1599
title: 'Language adapter capability matrix: make the cross-language contract statically
  enforced'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1598
parent: T-1597
tier: story
sprint: null
scope:
- src/frob/lang/**
- src/frob/gates/_lang_conformance.py
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Make the language adapter contract explicit and statically enforced before the batch work begins.

Today a language adapter is defined by convention: some implement symbol walking, some implement doc binding, some handle directives fully and some partially, and the gaps are only discovered when a gate misbehaves on a mixed repo. Adding 20-50 languages against that is how drift becomes unmanageable.

Deliverables:

1. A written capability matrix: every capability an adapter may implement (symbol walk, public/private determination, docstring or doc-comment extraction, comment/directive parsing including continuations, call graph edges, import/dependency edges, test discovery), each marked required or optional.

2. A conformance test suite parameterized over EVERY registered adapter, so adding a language automatically inherits the full battery and cannot silently skip a capability. A language declaring a capability it does not actually implement must fail the suite.

3. A gate (or an extension of the existing lang-conformance gate) that fails when a registered adapter declares support it does not have, so the matrix cannot drift from reality.

4. An explicit, documented answer to what happens when an OPTIONAL capability is absent: which gates degrade, which skip, and how a user learns their language will not get a given check. Silent absence is the failure mode to design out -- the same class as this drive's degraded-run and truncated-suite problems, where missing analysis was indistinguishable from clean analysis.

This ticket is the machinery the epic exists to stress-test. It must land before the per-language batches.

<!-- ticket:T-1600 -->
```yaml
id: T-1600
title: 'Language support: C#'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Add C# to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: Roslyn-shaped visibility (public/internal/protected/private), partial classes, properties vs fields, namespaces, and attributes. Nullable reference type annotations must not confuse symbol extraction. XML doc comments (triple-slash) are the doc-comment form.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.

<!-- ticket:T-1601 -->
```yaml
id: T-1601
title: 'Language support: Java'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Add Java to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: Package-private as the default visibility (no keyword) is the trap -- absence of a modifier is meaningful. Inner and anonymous classes, interfaces with default methods, annotations, and Javadoc as the doc-comment form. One public class per file is a convention frob can exploit for node ids.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.

<!-- ticket:T-1602 -->
```yaml
id: T-1602
title: 'Language support: CUDA'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Add CUDA to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: A C++ superset, so the C++ adapter is the starting point, but kernel qualifiers (__global__, __device__, __host__) are the whole point: they are the visibility and execution-surface concepts that matter, and a kernel entry point is the analog of a public symbol. Files are .cu/.cuh. Decide explicitly whether CUDA is a distinct adapter or a C++ dialect flag -- and record why.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.

<!-- ticket:T-1603 -->
```yaml
id: T-1603
title: 'Language support: Zig'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Add Zig to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: pub as the explicit visibility marker, comptime blocks, error unions in signatures, and doc comments (triple-slash) distinct from ordinary comments. Zig has no macro preprocessor, which makes it a cleaner symbol-extraction target than C/C++ -- a good early probe of whether the contract is genuinely language-agnostic.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.

<!-- ticket:T-1604 -->
```yaml
id: T-1604
title: 'Language support: Bash/Shell'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Add Bash/Shell to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: The hardest of the five for the abstraction, and therefore the most valuable probe. There is no visibility concept, functions can be redefined, sourcing is dynamic, and much meaningful code is top-level statements rather than named symbols. Decide and document what a public symbol IS here (exported functions? every function? script entry points?) before implementing. Hash-only line comments, no block comments, so directive continuations matter.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.

<!-- ticket:T-1605 -->
```yaml
id: T-1605
title: 'frob directives: wrap long lines and self-retire the noqa E501 pragma instead
  of honoring it forever'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/gates/_fix_engine.py
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
A frob directive that is too long today gets a trailing "# noqa: E501" and stays on one line forever. There are 3016 such directive lines in src/ and tests/ right now. They should instead be WRAPPED into the canonical backslash-continued form, and the noqa removed.

Current behavior, and why this is not already wired:

- frob fmt / the FMT001 Tier-A handler (fix_fmt001_directive_wrap, T-1261/T-1391) already knows how to canonicalize a frob directive run into wrapped, within-limit form. The wrapping machinery exists and works.
- But T-0985 made a directive run ending in a "# noqa" / "# noqa: CODE" pragma pass through VERBATIM (_NOQA_SUFFIX_RE in src/frob/gates/_fmt_directives.py, the _rebuild-runs half of canonicalize_text). The noqa is treated as a deliberate escape hatch for an unwrappable single token.
- Nothing anywhere strips a noqa. So the pragma is a one-way ratchet: once added, that line is permanently exempt from wrapping, whether or not it was ever genuinely unwrappable.

The T-0985 escape hatch is correct for its real case -- a directive whose logical text is ONE unbreakable token longer than the limit (a very long parametrized test node id with no space to break at) cannot be helped by wrapping, and would otherwise be reformatted pointlessly on every run. The bug is that the hatch is applied by PRESENCE OF THE PRAGMA rather than by actual unwrappability.

Proposed rule, which preserves T-0985's intent while fixing the ratchet:

1. For a frob directive run ending in a noqa pragma, attempt the canonical wrap with the pragma removed.
2. If every resulting physical line fits within the limit, keep that wrap and DROP the noqa -- it was never needed.
3. If any line still exceeds the limit (the genuine single-unbreakable-token case), restore the pragma and pass through verbatim exactly as today.

That makes the pragma self-retiring: it survives only where it is load-bearing, and it can never again be added to a line that wrapping could have fixed.

Deliverables:
- The rule above implemented in _fmt_directives, so both frob fmt and the FMT001 Tier-A handler inherit it.
- A one-time sweep applying it across the repo, expected to remove the large majority of the 3016 pragmas (a rough scan says 3005 have wrappable logical text, though the real number is whatever step 2 actually validates -- measure, do not assume).
- Tests covering all three branches: wrappable-with-noqa loses the noqa; genuinely-unwrappable keeps it byte-identically (extending the existing T-0985 byte-identical tests rather than replacing them); no-noqa behavior unchanged.
- Because the sweep touches thousands of lines across many files, land it as its own commit separate from any behavioral change, so review and bisect stay tractable.

Caution learned this drive: this handler rewrites source files unattended on the land path. FMT001 is already scoped to the touched set at land time (T-1404) precisely because an unscoped rewrite reintroduced out-of-scope edits. Keep that scoping; the one-time repo-wide sweep should be a deliberate, reviewed operation, not something a land quietly performs.

<!-- ticket:T-1606 -->
```yaml
id: T-1606
title: 'Per-language line-length: each formatter owns its own width, not ruff''s'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/lang/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
frob wraps directive comments against ONE project-wide line-length limit, read from [tool.ruff] line-length in pyproject.toml (read_line_length, src/frob/gates/_fmt_directives.py). For Python that is exactly right: ruff owns the limit, ruff is what a "# noqa: E501" silences, and frob correctly steals the value rather than keeping a competing one.

For every other language it is wrong. Each language's own formatter owns its width, and frob currently wraps Rust, C, C++, TypeScript, and everything else against Python's ruff-derived number:

- Rust: rustfmt.toml / .rustfmt.toml -> max_width (default 100)
- TypeScript/JavaScript: .prettierrc (any of its several forms) or a package.json prettier key -> printWidth (default 80)
- C/C++/CUDA/Java/C#/ObjC: .clang-format -> ColumnLimit
- Go: gofmt has no width limit at all -- the correct behavior is "do not wrap on width"
- Zig: zig fmt likewise has no configurable width
- Bash: no standard formatter; shfmt has no width option

Note the last three: "this language has no width limit" is a distinct, legitimate answer, not a missing config to default. Wrapping a directive in a language whose formatter would never complain is pure churn, and worse, it would keep reformatting on every run.

This was disclosed as a known limitation in T-0441's Done report and left as a follow-up. The language expansion epic promotes it from cosmetic to blocking: adding 20-50 languages against a single Python-derived width is exactly the kind of Python-shaped assumption in shared code that the epic exists to surface.

Deliverables:
- Per-language limit resolution: for a given file, find the limit its OWN toolchain would enforce, from that toolchain's own config file, with that tool's documented default as the fallback.
- A first-class "no width limit" answer for languages whose formatters do not have one, and directive wrapping skipped entirely for those files.
- The resolution is a lookup keyed by language, so a new adapter declares its width source once (fits the adapter capability matrix the contract ticket defines -- do it there rather than as a side table).
- Config discovery walks upward from the file, not just the repo root: a monorepo can have a different .prettierrc per package, and the nearest one wins, matching how the real tools resolve.
- Tests per language: config present, config absent (tool default), and no-limit languages.

Do not change the Python path's behavior: ruff stays the owner there, and the existing ruff-derived value must keep coming out unchanged.

<!-- ticket:T-1607 -->
```yaml
id: T-1607
title: 'Language expansion: remaining ranked languages, in research-recommended batches'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: low
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Implement the remaining ranked languages from the research ticket's target list, in the batch order it recommends, after the five named languages have proven the contract.

Split into further child tickets per batch rather than attempting all at once -- this ticket is the placeholder the research output turns into a concrete plan. Each batch must clear the parameterized adapter conformance suite before the next begins.

Expect the cost per language to FALL sharply after the first few if the contract is right, and to stay flat if it is wrong. A flat cost curve is the signal that the contract ticket did not actually succeed and should be revisited before continuing -- report it rather than grinding through.

<!-- ticket:T-1608 -->
```yaml
id: T-1608
title: 'Cross-language inspection stress test: one repo, every supported language,
  one obligation graph'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1607
parent: T-1597
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
The payoff test for the whole epic: a single fixture repository containing every supported language at once, carrying a real obligation graph across language boundaries.

What it must demonstrate:
- Doc edges from a symbol in one language to documentation that also covers symbols in another.
- Test edges from a test written in one language binding a symbol implemented in another (the FFI/binding shape frob users actually have: Python tests over a Rust or C++ core, a TypeScript client over a Java service).
- Waivers, todos, and ticket directives resolving identically regardless of the host language's comment syntax.
- A full frob check over the mixed repo producing correct, non-degraded results -- and, critically, ANNOUNCING any language whose analysis could not run rather than silently reporting zero findings for it.

That last point is this drive's recurring lesson applied to the language layer: a silent under-report is indistinguishable from a clean result, and every incident this session traced back to exactly that. A mixed-language repo multiplies the opportunities for it.

<!-- ticket:T-1609 -->
```yaml
id: T-1609
title: 'Tail-end repo hygiene: docs completeness, detector-gap audit, vestigial cleanup,
  waiver audit'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1597
parent: null
tier: epic
sprint: null
scope:
- docs/**
- src/frob/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Work to run only AFTER the rest of the queue is drained, in the stated order. Filed now so it is not forgotten, deliberately gated so it is not started early.

Why the gating is real and not ceremony: each child measures the repo's finished state. A docs sweep run mid-drive documents code that is about to change; a vestigial-artifact cleanup run mid-drive deletes things an in-flight ticket still references; a waiver audit run mid-drive judges waivers whose follow-up work has not happened yet and would condemn honest ones. Running these early produces confidently wrong answers -- the most expensive kind.

Order: docs sweep, then the detector-gap audit it feeds, then the artifact cleanup, and the waiver audit LAST, as explicitly requested.

<!-- ticket:T-1610 -->
```yaml
id: T-1610
title: 'Docs completeness sweep: enumerate the repo''s real surface and document every
  gap'
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: T-1609
tier: ticket
sprint: null
scope:
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Scan the entire repository for anything true about it that is not documented, and amend the docs to cover it.

Scope is the whole repo, not just docs/: every module, every gate rule, every CLI verb and flag, every config key in frob.toml, every environment variable, every file format frob reads or writes, and every workflow an agent or user is expected to follow.

Method matters more than volume. Enumerate the surface FIRST from the code (the CLI parser tree, the gate rule registry, the config model, the directive DSL grammar), then diff that enumeration against what docs/ actually covers. A prose read-through will miss exactly the things that have been missing all along; a mechanical enumeration will not.

Record every gap found in a durable list -- the audit child consumes it, and it is the input to that audit, not a byproduct. For each gap note what it is, where it should have been documented, and roughly how long it appears to have been missing (git blame on the undocumented symbol).

Do NOT fix detector gaps here. Finding out why frob failed to catch each of these is the next ticket's job, and mixing the two loses the evidence.

<!-- ticket:T-1611 -->
```yaml
id: T-1611
title: Audit why frob missed each doc gap, and ticket every detector gap found
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1610
parent: T-1609
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
For every documentation gap the sweep found, determine why frob did not already catch it, and ticket each detector gap.

This is the important half. A doc gap that frob could have caught and did not is a hole in the enforcement layer, and frob's entire premise is that unaccounted-for work is a build failure. Every gap is therefore a bug report against the gates, not merely an editing task.

For each gap, classify the cause and act accordingly:
- NO RULE EXISTS for this obligation -- file a ticket to add the rule.
- A RULE EXISTS BUT DID NOT FIRE (wrong scope, diff-scoped when it should be full-run, structurally unverifiable, cache serving stale results) -- file a ticket against that rule, and treat it as the same class as this drive's WAIVE004 and degraded-run incidents.
- THE RULE FIRED AND WAS WAIVED -- hand it to the waiver audit child; do not resolve it here.
- THE RULE FIRED AND WAS IGNORED as a warning that never became an error -- file a ticket to decide whether it should be promoted, and say why it was tolerated.

Deliverable: a written classification of every gap plus one filed ticket per distinct detector gap. A gap left unclassified is the outcome to avoid -- it is precisely the silent hole the exercise exists to close.

<!-- ticket:T-1612 -->
```yaml
id: T-1612
title: 'Remove vestigial repo artifacts: FROBLEMS.md, skills/, agents/, keeping only
  frob-central tooling'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1609
tier: ticket
sprint: null
scope:
- FROBLEMS.md
- skills/**
- agents/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Remove repository artifacts that are not central to frob's tooling, so what remains is all load-bearing.

Known candidates, named by the user: FROBLEMS.md and much of skills/ and agents/, which are vestigial. docs/guides/agent-playbook.md is explicitly worth KEEPING (it is the canonical home for process lessons this repo has already paid for once).

Rule to apply: anything not central to frob tooling goes. Anything that IS central stays, however scruffy.

Method, in this order, because deletion is the irreversible part:
1. Enumerate candidates and, for each, find every inbound reference (code, docs, config, CI, scaffolding templates, tests). frob's own refs machinery is the right instrument.
2. For each candidate, state plainly whether it is dead, partially live, or live-but-misplaced. A partially live artifact gets its live part extracted before the rest goes.
3. Delete, with each deletion attributable to this ticket in one commit per coherent group -- not one giant sweep, so any single removal can be reverted independently.
4. Re-run the full gate set afterwards. A deletion that silently reduces coverage or orphans a doc edge is the failure mode; the obligation graph should catch it, and if it does not, that is itself a finding worth a ticket.

Do not delete anything an in-flight ticket references. That is the whole reason this is gated behind the rest of the queue.

<!-- ticket:T-1613 -->
```yaml
id: T-1613
title: 'frob cannot express runs-last: add a marker that stays undoable while any
  other ticket is open'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- src/frob/_cli_parsers/**
- docs/**
- tests/**
- src/frob/tickets/_models.py
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_models.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_store.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
threat: null
component: null
```
frob can express "this ticket is blocked by that ticket" but cannot express "this ticket must be the last thing done in the repository". The distinction matters for audit-shaped work whose correctness depends on everything else being finished.

Concrete case: the waiver cop-out audit. Its blocked_by edges can only name tickets that existed when it was filed. Any ticket filed afterwards must ALSO precede it, but nothing in the graph says so, and nothing stops an agent from popping it early. Today the constraint survives only as prose in the body, which is exactly the kind of tribal knowledge frob exists to replace with enforcement.

Proposed: a runs-last marker (a tier value, a flag, or a blocked_by_all sentinel) that makes such a ticket structurally undoable while ANY other non-terminal ticket exists.

Requirements:
- `frob ticket doable` must never return a runs-last ticket while any other queued/in-progress ticket exists, regardless of filing order.
- `frob ticket start` on one must refuse with a message naming what remains.
- More than one runs-last ticket must be allowed (they order among themselves by ordinary blocked_by edges).
- Filing a NEW ordinary ticket while a runs-last ticket is in-progress should warn loudly: the precondition it started under has been invalidated.

That last requirement is the one that makes this real rather than cosmetic -- the failure mode is not starting the audit too early, it is finishing it and then having new work land that silently invalidates its conclusions.

<!-- ticket:T-1614 -->
```yaml
id: T-1614
title: 'RUNS LAST: audit every frob:waive for cop-outs, after all other work is complete'
state: queued
kind: security
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1612
- T-1611
- T-1613
parent: T-1609
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Audit every frob:waive directive in the repository and confirm each is a genuine, still-necessary exception rather than a cop-out.

THIS TICKET RUNS LAST. Not last among the tickets that existed when it was filed -- last, absolutely. Tickets filed after this one also precede it. The blocked_by edges recorded here cover only what existed at filing time and are therefore a floor, never the whole precondition.

STANDING PRECONDITION, to re-check immediately before starting: every other ticket in the queue is done, dropped, or archived. If `frob ticket list --state queued` or `--state in-progress` returns ANYTHING other than this ticket, it is not yet time -- stop and work that instead. See the runs-last enforcement ticket for making this mechanical rather than a promise.

Why last: a waiver's honesty can only be judged against finished code. Many waivers name a follow_up ticket, and judging them before that work lands would condemn waivers doing exactly what they promised. A waiver audit run early produces confidently wrong answers -- it would delete honest waivers and bless ones whose justification has not yet expired.

For every waiver, decide one of:
- STILL NECESSARY AND HONEST -- the reason describes a real constraint that still holds. Keep. Confirm the reason explains WHY rather than restating the rule.
- OBSOLETE -- the condition passed, the code changed, or the follow-up landed. Remove the waiver and let the gate speak.
- A COP-OUT -- it exists because fixing the finding was inconvenient. Remove it and fix the underlying finding, or, if the fix is genuinely large, replace it with a real ticket and a waiver naming that ticket.
- PERMANENT BY DESIGN -- no follow-up will ever exist (a private test helper with no production caller is the canonical case). These need a way to say so; the permanent-waiver ticket already filed covers that gap.

Specific things this drive learned to look for:
- A reason that merely restates the rule name is not a justification.
- A follow_up pointing at a done ticket is an orphan, not a waiver.
- Waivers added in bulk during a burn-down deserve extra scrutiny: cop-outs cluster there.
- A waiver on a rule that structurally cannot fire (a diff-scoped rule judged on a full run) is noise, not an exception, and belongs in that rule's exemption list instead.

Deliverable: every waiver classified, obsolete and cop-out waivers removed, and a count reported by category. A waiver left unexamined defeats the exercise.

<!-- ticket:T-1615 -->
```yaml
id: T-1615
title: 'frob ticket block leaves the ledger dirty: audit every ledger-writing verb
  for auto-commit parity'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- tests/**
- docs/modules/tickets.md
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
threat: null
component: null
```
frob ticket block writes its edge into the ledger and leaves the file dirty. Every sibling mutation verb auto-commits: start (T-1054), then new/drop/fail (T-1130), then close/evidence/requeue/done-report. block was missed.

Consequence, observed directly on 2026-08-05: two block edges recorded back to back left tickets.md uncommitted on main, and the next `frob ticket land` refused with DirtyMain. The land is right to refuse -- a dirty root is exactly what its precheck exists to catch -- but the dirt was created by frob itself, silently, by a verb the caller had no reason to think left work behind.

This is the same incident class T-1130 names in its own body: "commit before dispatching" was coordinator memory rather than something the tool guaranteed. Any verb that writes the ledger and does not commit it converts a routine command into a trap for whatever runs next.

Fix: route block (and any other ledger-writing verb still missing it -- audit them all rather than fixing only this one) through commit_ticket_ledger_change, with the same --no-commit opt-out the other verbs expose for callers batching several writes.

Audit list to check while here: block, unblock if it exists, scope, accept, evidence --replace, migrate, renumber, archive. For each, state whether it writes the ledger and whether it commits. A table in the Done report is the deliverable, not just the block fix -- the point is that no ledger-writing verb is left in this state.

Test shape: for every ledger-writing verb, assert the working tree is CLEAN after the command (and dirty under --no-commit). A single parameterized test over the verb list makes a future verb that forgets this fail immediately.

<!-- ticket:T-1616 -->
```yaml
id: T-1616
title: BUG002 is unsatisfiable for a pure refactor, and reclassifying kind silently
  dodges it
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/app/ticket_runner/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
BUG002 requires a bug-kind ticket's designated evidence test to FAIL at the parent commit, proving the defect existed and was fixed. That is exactly right for a behavioral defect. It is unsatisfiable by construction for a pure refactor, where the whole obligation is the opposite: prove behavior is UNCHANGED. A refactor's tests pass at the parent because they must.

frob's kinds are feature, bug, security, ux, docs, invariant, incident. None of them means refactor. So a ticket that fixes a structural finding with no behavior change -- an ARCH001 over-length function, a DUP001 duplicate, a LARGE001 file split -- has no honest kind:
- Filed as bug, it is blocked by BUG002 forever and cannot land.
- Filed as feature, it lands, but only because the classification dodged the check.

Observed 2026-08-05: T-1593 (splitting _land_core, _check_mutation_evidence, run_pending_sweep to clear the last 3 ARCH001 errors on main) was filed as bug and refused by BUG002. Its own Done report certifies "pure extraction, same call order, same short-circuit/error semantics, same log lines, no new branches" -- the strongest possible statement that no repro test could fail at the parent. It was relabeled to feature to land.

That relabel is defensible on the merits here, and it is ALSO the finding: if a one-word kind change is all that stands between a bug-kind ticket and skipping its evidence obligation, then BUG002 is advisory for anyone willing to relabel. A gate that can be dodged by reclassification is not enforcing what it claims.

Two things to fix, and the second matters more than the first:

1. Give refactor-shaped work an honest home: either a refactor kind, or an explicit "no behavioral change intended" attribute that BUG002 recognizes and that swaps the obligation rather than removing it. A refactor's evidence obligation should be REAL but DIFFERENT -- prove behavior unchanged (the touched code's existing tests pass at both parent and tip, characterization tests exist for the extracted seams), rather than prove a defect fixed. That keeps the rigor and matches what a refactor can actually demonstrate.

2. Make reclassification visible. Changing kind on a ticket that already has evidence or a Done report should be recorded in the ledger and surfaced at land, so a reviewer sees "this was a bug when the work was done and became a feature before it landed" instead of a silent edit. Kind changes before any work starts are ordinary; kind changes that relax an evidence obligation after the fact are the ones worth showing.

Related: this is the same family as the empty-diff TEST016 refusals seen when a shared series worktree lands its whole branch -- an evidence rule correctly firing on a shape its author did not anticipate. The fix in both cases is to give the unanticipated shape its own honest path, never to weaken the rule.

<!-- ticket:T-1617 -->
```yaml
id: T-1617
title: Ledger merge silently drops a frontmatter field changed on main when a worktree
  edited the same ticket
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- .gitattributes
- tests/**
- docs/design/ledger-v2.md
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_store.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
threat: null
component: null
```
A ticket field changed and committed on main was silently dropped when main was merged into a worktree whose copy of that same ticket block had also changed. No conflict, no warning, no log line -- the field simply kept the worktree's older value, and the next command read the stale one.

Observed 2026-08-05, concretely:
1. On main: `frob ticket kind T-1593 feature`, written to tickets.md and committed.
2. In .claude/worktrees/w26-arch-splits: `git merge main` -- reported success, 79 insertions, no conflicts.
3. In that worktree afterwards: `frob ticket show T-1593 --json` still reported kind=bug.
4. `frob ticket land T-1593` consequently refused with a BUG002 finding naming "(kind=bug)", against a ticket that was feature-kind on main.

The worktree's own T-1593 block had been edited locally (Done report, evidence ids) during the agent's work, so both sides touched the same region of the same block. Git merged the file without complaint and the frontmatter field lost.

NOT root-caused, and the distinction matters -- do not assume:
- git's own line-level auto-resolution may have taken the worktree's hunk, or
- the ledger splice / canonicalization may have rewritten the block from a parsed in-memory ticket, discarding whatever the merge produced.
Determine which BEFORE proposing a fix. A git-level resolution is fixed by a merge driver or .gitattributes; a splice-level overwrite is fixed in frob's own code, and they have nothing in common.

Why this is more than a papercut: a semantic field disappearing with no conflict marker means the ledger can silently disagree with itself across checkouts, and the disagreement surfaces only when some gate happens to read the losing side. state, priority, blocked_by, scope, and parent are all exposed to the same shape -- kind was merely the one caught, and only because a gate refused loudly. A silently lost `state` or `blocked_by` would not announce itself at all.

Deliverables:
- Root cause identified (git resolution vs splice overwrite), stated explicitly.
- Whichever layer is responsible, make a losing field change either impossible or LOUD. A conflict a human resolves is an acceptable outcome; a silent drop is not.
- A regression test reproducing the exact sequence above: edit a field on main, edit the same ticket's body in a worktree, merge, and assert the field change survived.

Note for the fix: ledger v2 (tickets/T-####/ticket.md, one file per ticket) narrows this considerably, since concurrent edits to different tickets stop sharing a file at all -- but it does NOT eliminate it, because this case had both sides editing the SAME ticket. Do not close this on the strength of the v2 migration alone.

<!-- ticket:T-1618 -->
```yaml
id: T-1618
title: A land merges the whole worktree branch, carrying unrelated and even REJECTED
  tickets onto main
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land*.py
- src/frob/app/ticket_runner/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
`frob ticket land <id> --worktree W` merges W's BRANCH, not the commits belonging to <id>. When W holds a series of tickets worked sequentially, the first land carries every sibling's code onto main -- including tickets that were never reviewed, and including tickets that were deliberately REJECTED.

Observed 2026-08-05, the damaging case: worktree w24-waive-family held T-1581, T-1577, T-1579, T-1578, T-1580. T-1579's change (a WAIVE004 self-heal escape) was judged unsafe and reverted IN THE WORKTREE. Landing T-1581 nonetheless put T-1579's code on main, where it proceeded to delete 55 live frob:waive directives across arch/strata/perf/graph/vet on every subsequent land until it was found and reverted on main separately. Reverting the ticket in its own worktree accomplished nothing, because the code had already left by another ticket's door.

The benign-but-confusing case, seen three times the same session: after the first land carries the siblings, those siblings can no longer land. Their fix is already on main, so BUG002 finds the repro test passing at the parent and TEST016 finds an empty diff with no mutants to kill. Both gates are CORRECT; the tickets are simply already done. Resolution each time was to verify the content on main by hand and `frob ticket close` directly, with --skip-mutation-evidence for the empty diff.

Two things to fix:

1. A land must not silently carry unrelated tickets. Either merge only the landing ticket's own commits, or -- if whole-branch merge is deliberate, which is defensible for a series -- REFUSE unless the operator acknowledges the passengers, listing every other ticket whose commits are about to ride along. Silence is the bug: nothing in the output said T-1579 was going to main.

2. Landing a ticket whose content is ALREADY on main should be a recognized, first-class outcome, not a BUG002/TEST016 refusal the operator has to diagnose and route around by hand. Detect "diff is empty because this already landed", verify the content is genuinely present, and offer the close path directly.

Related, and worth deciding here: CrossTicketLeakage already exists as a concept (`--allow-cross-ticket` is its escape hatch). Determine why it did not fire for this case, since a rejected ticket's code reaching main is exactly what that check is named for. If it fires only for uncommitted leakage and not for committed sibling commits, say so and close the gap.

<!-- ticket:T-1619 -->
```yaml
id: T-1619
title: 'Land has no exclusive lease: a concurrent frob ticket new corrupts it mid-staging'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- tests/**
- docs/**
- src/frob/tickets/_land.py
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_land.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
threat: null
component: null
```
A land reads main's working tree at precheck and records main's tip for its unwind path. Any concurrent write to main breaks it, and frob's own commands are the most likely writers:

- Uncommitted edits in main -> the land refuses with DirtyMain, mid-chain.
- A NEW COMMIT on main while the land stages -> tip drift (T-0907), the land refuses to unwind, and it leaves its REL001 version bump STAGED for someone to clean up by hand.

Both happened on 2026-08-05, and the second was caused by `frob ticket new` -- which auto-commits the ledger. So "file a ticket" and "land a ticket" are mutually destructive operations with no interlock between them, and nothing warns you. The operator is expected to just know, which is the same tribal-knowledge failure T-1130 closed for ledger auto-commit.

Fix: a land takes an exclusive repository lease for its duration, and every other ledger-writing verb (new, close, drop, fail, requeue, block, scope, evidence, kind, ...) either refuses with a clear "a land is in progress for T-####, retry after it completes" or waits on it. The lease must be crash-safe -- a killed land cannot leave the repo permanently locked -- which is the same shape as the existing worktree-lease liveness probing (frob.tickets._leases), so reuse that rather than inventing a second mechanism.

Also fix the partial-staging residue: when a land aborts after staging its REL001 bump, it should unstage what it staged, or say exactly what it left behind. Today it prints a refusal and leaves four files staged, and the operator has to work out that `git reset --hard HEAD` is safe only because the land did not complete.

Acceptance: with a land running, `frob ticket new` must not be able to corrupt it -- proven by a test that runs both concurrently.

<!-- ticket:T-1620 -->
```yaml
id: T-1620
title: Degraded-run detection misses zero-findings under-reports and sub-threshold
  mass staleness
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/perf/**
- src/frob/app/ticket_runner/_land_cmd.py
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
This is the blocker that keeps waiver auto-delete disabled on the land path, and the reason T-1579 was reverted.

`_degraded_verification_reason` (src/frob/gates/_fix_engine.py) detects a degraded gates run from two structural signals: stale/missing natives and a skipped gate stage. It does NOT detect the case that actually keeps happening -- a gate that runs to completion and reports ZERO findings for a rule because its analysis substrate is silently under-powered.

Measured 2026-08-05 in a worktree: the perf gate reported zero PERF004 findings repo-wide (main reports many), `_degraded_verification_reason` returned None, and `_worktree_natives_verifiably_healthy` answered "healthy". Everything said the run was fine. Consequences: T-1579's escape opened and deleted 55 live waivers, and separately 4 DEPR005/DEAD001 waivers were deleted because their rules hold fewer than `_WAIVE004_MASS_INVALIDATION_THRESHOLD` (5) waivers each, so the mass-invalidation guard cannot see them at all.

Two distinct holes, both needing closing:

1. ZERO-FINDINGS UNDER-REPORT. A gate that returns zero findings for a rule the repo demonstrably trips elsewhere is suspicious. Give the perf/reach substrate (and any other gate with an optional analysis layer) a way to declare "I ran, but my analysis was degraded", and make `_degraded_verification_reason` consume it. A comparison against a recorded baseline of expected per-rule finding counts is one workable shape: a rule that historically finds N>0 and suddenly finds 0 is a degradation signal, not a clean bill of health.

2. SUB-THRESHOLD MASS STALENESS. The mass-invalidation guard is a COUNT heuristic and is structurally blind to any rule with fewer than 5 waivers. Those waivers are exactly as vulnerable, with no guard at all. Either drop the threshold to something that cannot be dodged by rarity, or make the guard proportional (all waivers of a rule going stale at once is suspicious whether that is 2 of 2 or 40 of 40 -- arguably MORE suspicious at 2 of 2).

Until both are closed, WAIVE004 auto-delete stays excluded from the land path (see the T-1592 comment in src/frob/app/ticket_runner/_land_cmd.py) and T-1579 stays queued. This ticket unblocks both; say so explicitly in its Done report.

Design note learned the hard way: "the detector found something somewhere" is NOT proof the detector worked. A partially degraded run finds some things and misses others, and that is the most dangerous state because it looks healthy from every angle we currently measure.

<!-- ticket:T-1621 -->
```yaml
id: T-1621
title: Every frob log record appears twice in pytest output, making occurrence counts
  unreliable
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/logging/**
- tests/conftest.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Every frob log record appears TWICE in pytest output, in two different formats:

    WARNING: gitio: git rev-parse --abbrev-ref HEAD failed (rc=128): fatal: not a git repository...
    WARNING  frob.gitio:gitio.py:232 gitio: git rev-parse --abbrev-ref HEAD failed (rc=128): fatal: not a git repository...

Cause: frob configures its own root logging via dictConfig with lazy stdout/stderr StreamHandlers (src/frob/logging/handler.py, logger.py). Under pytest, that handler writes into the captured stream AND pytest's own logging-capture plugin reports the same record from the log-capture buffer. Both reach the report.

Why it is worth fixing rather than tolerating: it doubles the volume of every test log, and it makes occurrence COUNTING unreliable -- grepping a log for how many times a condition fired silently returns twice the real number. During this drive, counts pulled from test logs had to be sanity-checked by hand more than once for exactly this reason. A log you cannot count is a log you cannot measure with.

Fix direction: do not install frob's own stream handlers when running under pytest (pytest's capture is already reporting them), or set propagation so exactly one path reports. Whichever is chosen, assert it: a test that emits one record and asserts it appears exactly once in the captured output.

Also verify, and state the answer in the Done report, whether ordinary CLI invocations double as well. A probe during triage did not produce a warning at all, so the CLI case is UNVERIFIED rather than known-clean -- do not assume it is fine because the pytest path explains the observed instances.

<!-- ticket:T-1622 -->
```yaml
id: T-1622
title: Tickets filed from a worktree get draft ids that never survive a land
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- tests/**
- docs/**
- src/frob/tickets/_provisional.py
- src/frob/tickets/_new_renumber.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_provisional.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
threat: null
component: null
```
`frob ticket new` run inside a worktree allocates a T-draft-<hex> id rather than a real T-#### one, because real id allocation needs main's ledger. Those draft ids never survive a land: the ledger splice drops the draft block, and any Done report citing it becomes a phantom citation (TICK006).

Consequence, hit FOUR separate times on 2026-08-05: an agent files legitimate follow-up tickets while working, cites them honestly in its Done report, and the coordinator must then refile each one on main, swap every citation in the worktree ledger, and delete the local draft block by hand before the land will pass. It is pure toil, it is error-prone (a blanket string-swap once renamed the draft's own block instead of removing it), and it happens on nearly every dispatch that discovers follow-up work.

T-1544 already covers the CITATION side (a Tier-A auto-fix that refiles and renumbers phantom draft citations). This ticket is the ALLOCATION side, which is the root: make an id filed from a worktree real from the start.

Options to weigh, and the choice belongs in this ticket:
- Reserve id ranges per worktree, so a worktree can allocate a real id with no coordination.
- Allocate through the existing cross-worktree lease side-channel (frob.tickets._leases already has a shared, peer-writable directory and liveness probing -- the coordination substrate exists).
- Keep draft ids but make the LAND rewrite them to real ids automatically, citations included, so the toil disappears even if the draft mechanism stays.

Whichever is chosen, the acceptance is the same: an agent files a follow-up ticket from a worktree, lands its work, and neither the agent nor the coordinator has to touch the ledger by hand for the citation to be correct on main.

<!-- ticket:T-1623 -->
```yaml
id: T-1623
title: 'strata maturity: make capability enforcement watertight'
state: queued
kind: security
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: epic
sprint: null
scope:
- design/frob.strata
- src/frob/strata/**
- src/frob/vet/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Umbrella for the strata self-model hardening reviewed on 2026-08-05. Findings, in dependency order: the declaration file is half redundancy (duplicate attr blocks, 5277 test names declared as interface); interface= is a generated mirror that cannot be meaningfully violated; capability detection is lexical rather than symbol-resolved; and via grants whole FILES rather than single controllable locations, with permission lists that only ever grow. Children carry the detail. Sequence the mechanical cleanups first so the design work reasons over a smaller surface.

<!-- ticket:T-1624 -->
```yaml
id: T-1624
title: 'strata: sync-interface appends duplicate attr interface blocks instead of
  replacing'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: T-1623
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/strata/_sync_interface.py
- src/frob/strata/_selfconform.py
- tests/unit/strata/test_sync_interface.py
- tests/unit/strata/test_selfconform.py
- src/frob/strata/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: design/frob.strata
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'narrow to files actually touched: sync-interface fix, one-time dedup, new
    lint'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/__init__.py
  reason: SYS_DUPLICATE_INTERFACE constant needs the same public re-export __init__.py
    already does for every other SYS10x rule id
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/strata/**
  reason: narrow to files actually touched; the two broad globs from ticket filing
    are superseded by explicit adds
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: tests/**
  reason: narrow to files actually touched; the two broad globs from ticket filing
    are superseded by explicit adds
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_no_duplicates_silent
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_comment_line_is_not_mistaken_for_a_block
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_grammar_parsed_duplicate_blocks_fire_not_lexical_text
threat: null
component: null
```
Nearly every node in design/frob.strata carries TWO byte-identical `attr interface=[...]` blocks. 45 blocks across ~17 nodes. Measured on node `checker`: block 0 and block 1 both list the same 11 symbols, differing only in a trailing comma.

This predates the 2026-08-05 sync-interface run (verified by inspecting the file at an earlier commit), so it is a long-standing bug, not fresh damage.

Root cause to confirm: `frob sys sync-interface` APPENDS a fresh interface block rather than REPLACING the existing one. The parser evidently tolerates it (last-wins, or first-wins) which is exactly why nobody noticed -- the file stayed semantically correct while doubling in size.

Fix: sync-interface replaces in place. Then a one-time pass removing the duplicate blocks.

Add a lint: more than one `attr interface=` on a single node is an error. A declaration language whose own declarations can silently duplicate cannot be the source of truth for anything -- and this file is supposed to be the source of truth for the whole self-model.

Expected effect: the file loses several hundred lines of pure redundancy, and a whole class of "which block is authoritative?" ambiguity disappears.

## Done report

frob sys sync-interface's span-finder (_find_interface_span, now
_find_interface_spans) used to stop scanning a node's body at the FIRST
attr interface=[...] block it found and return that one span alone.
_rewrite_node_interface_block then only ever replaced that first span --
any SECOND interface block elsewhere in the same node body (this repo's
own design/frob.strata has one right after the header AND another right
before the closing brace, non-contiguous, separated by may/code/clearance
attrs) was silently left in place forever. That produced exactly the
observed damage: 45 byte-identical duplicate blocks across ~17 nodes,
predating any single sync run (confirmed by inspecting an earlier commit).

Fix: _find_interface_spans now scans the WHOLE node body and returns
EVERY span found (compact [...] blocks and legacy one-line-per-symbol
lines, freely mixed). _rewrite_node_interface_block merges every span's
declared names, and rewrites whenever more than one span is found (not
just on a symbol-set mismatch) -- collapsing them into exactly one
compact block at the first span's position, deleting the rest.

Applied the fix to design/frob.strata itself via `frob sys
sync-interface` (no --check): 3191 -> 2363 lines, 34 -> 18 interface
blocks (0 duplicates, one per node with a declared surface). Re-ran
--check immediately after: 0 drift (idempotent). Confirmed the file
still parses via frob.lang.parse_file.

Added SYS108 (_duplicate_interface_violations, src/frob/strata/
_selfconform.py): a node whose interface= attrs (read from the real
ELABORATED grammar model, Node.attrs -- not a text scan) name the same
symbol more than once is now a hard ERROR, always (no advisory tier),
wired into _collect_sys_violations and re-exported from
frob.strata.__init__ alongside every other SYS10x id. Ran `frob check
--only sys --ticket T-1624`: 0 errors -- the repo's own now-deduped
design/frob.strata does not trip its own new lint.

Per a mid-task nudge, added two regression tests proving both the
SYS108 check and the sync-interface span-finder are GRAMMAR-aware, not
merely lexical: a '//' comment line containing literal
"attr interface=[public_fn];" text is provably never counted as a
declaration or a span (this language has no block-comment form, only
'//'-prefixed line comments per strata-core/src/parse/lexer.rs), while
the two REAL (non-commented) duplicate blocks on the same node still
fire exactly once.

`frob check --land-parity` could not complete inside its own 400s
foreground budget under the current session's load (multiple concurrent
agents/lands) -- reported here as an unmeasured result, not a clean
result, per the playbook's own instruction not to claim more than was
observed. Scoped `frob check --only test/sys/scope/prework --ticket
T-1624` all read 0 errors.

### Changed
```
 design/frob.strata                       | 1560 +++++++-----------------------
 src/frob/strata/__init__.py              |    2 +
 src/frob/strata/_selfconform.py          |   60 ++
 src/frob/strata/_sync_interface.py       |  161 +--
 tests/unit/strata/test_selfconform.py    |  112 +++
 tests/unit/strata/test_sync_interface.py |   81 ++
 tickets.md                               |   81 +-
 7 files changed, 790 insertions(+), 1267 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_no_duplicates_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_comment_line_is_not_mistaken_for_a_block` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_grammar_parsed_duplicate_blocks_fire_not_lexical_text` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 258 warning(s), 865 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1625 -->
```yaml
id: T-1625
title: 'strata: testsuite node declares 5277 test names as interface symbols'
state: in-progress
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: T-1623
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/strata/_selfconform.py
- src/frob/strata/_sync_interface.py
- tests/unit/strata/test_selfconform.py
- tests/unit/strata/test_sync_interface.py
- src/frob/strata/_code_binding.py
- src/frob/strata/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/gates/**
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: tests/**
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: design/frob.strata
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_code_binding.py
  reason: new cross-node-reference helper reuses _dotted/_join_dotted/_relative_base_dir
    from _code_binding.py
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/__init__.py
  reason: 'shared worktree: __init__.py''s SYS_DUPLICATE_INTERFACE export was added
    under T-1624, still shows in T-1625''s cumulative branch diff since neither has
    landed yet'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one
threat: null
component: null
```
The `testsuite` node declares 5277 symbols in its `interface=` attr -- more than half of every interface symbol in design/frob.strata (the whole file totals roughly 9000 across all nodes; the next largest node is 919).

Those 5277 entries are test class and test function names. A test exposes nothing to anyone: no other node imports it, no consumer depends on its surface, and renaming one breaks nothing outside its own file. Declaring them as an "interface" is a category error, and it is the single largest source of noise in the self-model.

Cost: it inflates the design file threefold, it makes every sync-interface run rewrite thousands of lines (see the merge-conflict and land-noise incidents this drive), and it buries the ~3700 declarations that DO describe real cross-node surface.

Options, and the ticket should pick one with reasoning:
1. Exempt test-tree nodes from SYS104's declare-every-public-symbol obligation entirely.
2. Keep the obligation but let a node declare `interface=*` (or an explicit `interface_exempt` clearance) meaning "this node exposes no contract; do not enumerate".
3. Narrow SYS104 to symbols actually referenced across node boundaries, which would shrink every node's list, not just testsuite's.

Option 3 is the most principled and the most work; it is also the one that would fix the general problem rather than special-casing tests. Consider it seriously before defaulting to 1.

Whichever is chosen, the acceptance is that the design file describes CONTRACTS, and that a reader can see the real architectural surface without scrolling past five thousand test names.

## Done report

Chose OPTION 3 (narrow SYS104 to symbols actually referenced across node
boundaries), the option the ticket itself flagged as most principled,
over option 1 (exempt test-tree nodes) or option 2 (an interface_exempt
escape hatch). Reasoning: option 1/2 special-case tests specifically and
leave the underlying problem -- "interface=" declaring the WHOLE real
public surface rather than a genuine contract -- untouched for every
other node; option 3 fixes the general problem, and the ticket's own
prediction that it "would shrink every node's list, not just testsuite's"
held (see numbers below).

Implementation: `_cross_node_referenced_symbols` (src/frob/strata/
_selfconform.py) walks every bound .py file's `from <module> import
<name>` statements, resolves `<module>` in-repo, and -- when the target
file is owned by a DIFFERENT node than the importer -- records `<name>`
as required for the target's node. SYS104's required surface becomes
`real_public_surface & cross_node_referenced`, computed once per
check/sync run and threaded through both `_interface_conformance_
violations` (the gate) and `_sync_interface.py`'s writer (so gate and
writer agree on what "required" means -- otherwise every sync run would
immediately re-drift against the gate it's meant to satisfy).

A real infrastructure gap surfaced immediately on the whole-repo pass:
`resolve_local_import`'s python branch resolves a dotted spec by literal
`spec.replace(".", "/")` against `root`, with no src-layout awareness.
A RELATIVE import's dotted prefix is derived from the importing file's
own on-disk position (already carries the `src.` segment via
`_code_binding.py`'s `_dotted`), so it resolves fine -- but an ABSOLUTE
cross-package import (`from frob.excludes import x`, this repo's
dominant CROSS-NODE shape) never resolved against the real repo root,
confirmed directly:
`resolve_local_import("frob.excludes", ..., root=<repo root>)` returns
None even though `src/frob/excludes.py` exists. SYS106's own
`_reachable_local_files` has silently eaten this gap for a while --
invisible there since an unreached file just stays unflagged -- but my
narrowing cannot afford to silently drop nearly every real cross-node
reference. `_resolve_cross_package_import`/`_src_root_prefixes` derive
the missing prefix from the bound file layout itself (no hardcoded
"src") and retry.

Applied via `frob sys sync-interface` (no --check) after the code
change: design/frob.strata 2363 -> 1798 lines. testsuite's own
interface collapsed to `[]` (0 symbols, from 5277) -- confirming nothing
in the repo ever imports a test by name. Total declared interface
symbols across the WHOLE file: ~9000 -> 1457 (smaller than the ticket's
own back-of-envelope ~3700 estimate for "everything except testsuite",
because the general narrowing also trimmed other nodes' previously
over-declared surface, not only testsuite's -- exactly the effect the
ticket predicted and preferred). Re-ran --check immediately after: 0
drift (idempotent). Confirmed the file still parses via
frob.lang.parse_file. `frob check --only sys --ticket T-1625`: 0 errors
-- the full-repo `check_self_conformance` integration test
(TestRealGateGreen.test_repo_design_and_declarations_are_self_conformant)
passes with zero violations against the regenerated file.

Every existing TestInterfaceConformance/TestSyncInterfaceReport unit
test that asserted the OLD "declared == full real surface" semantics
was updated to add an explicit cross-node consumer file/node -- the
new semantics require one before a symbol is expected to be declared
at all; each test's docstring/comment now says why.

### Changed
```
 design/frob.strata                       | 1857 ++++--------------------------
 src/frob/strata/__init__.py              |    2 +
 src/frob/strata/_selfconform.py          |  295 ++++-
 src/frob/strata/_sync_interface.py       |  187 +--
 tests/unit/strata/test_selfconform.py    |  170 ++-
 tests/unit/strata/test_sync_interface.py |  159 ++-
 tickets.md                               |  237 +++-
 7 files changed, 1146 insertions(+), 1761 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 301 warning(s), 870 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1626 -->
```yaml
id: T-1626
title: 'strata: capability detection must be symbol-resolved with full alias support,
  not lexical needles'
state: queued
kind: security
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1663
parent: T-1623
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/graph/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Capability detection is fundamentally LEXICAL: `scan_file_capabilities` matches per-language needle tables against the file's raw bytes, excluding hits inside tree-sitter comment spans. Import/binding-aware passes were bolted on afterwards per language (`_python_binding_capabilities` T-0328, `_ts_binding_capabilities` T-0377, a rust sibling) to recover aliased and from-import evasions the raw-text scan "structurally cannot" catch -- their own words.

That architecture cannot be made watertight by adding more needles. A capability model that decides "does this code eval?" by substring search is guessing, and it fails in both directions:

FALSE NEGATIVES (evasions the current design misses, or catches only by luck):
- indirect binding: `f = subprocess.run` then `f(cmd)` later, or through a dict/list
- attribute chains through a re-export: `from frob import io` then `io.helpers.write(...)`
- wrappers: a local helper that forwards to the dangerous callable, so the call site the scanner sees is innocent
- `functools.partial(os.system, ...)`, decorators, and callables passed as arguments
- `getattr(module, name)(...)` where name is computed
- re-exports through a package `__init__` that rename the symbol

FALSE POSITIVES (already costing real waivers in this repo):
- `_body_reaches_decode_and_exec` carries a waiver explaining that the scanner flags the literal strings "eval"/"exec" in its OWN needle table
- any identifier containing a needle as a substring (`evaluate_cacheable_gate`, `_eval_needle`, `compile_pattern`)

Requirement: capability detection must be a SYMBOL match with full alias resolution, not a text match. Resolve each call site to the symbol it actually reaches -- through import aliases, from-imports with `as`, attribute chains, re-exports, and local rebinding -- and decide the capability from the RESOLVED target. A hit is a resolved reference to a known-dangerous symbol; anything unresolved is reported as unresolved rather than silently passing.

This repo already owns the machinery: frob.graph.callgraph does call-graph resolution, and the lang adapters already produce tree-sitter symbol spans. The capability scanner should consume that resolution rather than maintaining a parallel lexical approximation per language.

Fail-closed requirement: when resolution cannot determine a call's target (genuinely dynamic dispatch, a computed getattr), that must surface as an explicit UNRESOLVED finding demanding a declaration or a waiver -- never as "no capability found". This drive has repeatedly been burned by analysis that reported nothing when it could not look; the capability layer must not repeat it.

Prerequisite for symbol-level `via`: attributing a capability to a specific declared symbol is only meaningful once the hit itself is symbol-resolved. Sequence this before, or together with, the via-granularity work.

<!-- ticket:T-1627 -->
```yaml
id: T-1627
title: 'strata: via must name a SYMBOL and support exactly-one-site exclusivity, not
  whitelist whole files'
state: queued
kind: security
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1626
parent: T-1623
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/strata/**
- src/frob/vet/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
`may "<capability>" via "<file>"` grants the capability to an ENTIRE FILE. The stated intent -- that a dangerous capability happens at exactly one controllable location -- is not what gets enforced.

Concretely today:
- `may "eval" via "src/frob/doctor.py"` permits eval anywhere in a 700+ line module.
- `may "fs.write" via [16 files]` and `may "fs.read" via [12 files]` on node `cli` alone. A sixteen-file permission list is not a chokepoint; it is an inventory.
- `may "exec" via [5 files]`, `may "env" via [6 files]`.

Two separate defects:

1. GRANULARITY. `via` should name a SYMBOL, not a file: `may "eval" via "src/frob/doctor.py::_probe_module"`. A file is an arbitrary container that grows; a function is the actual controllable location. Anything else in that file trips the gate.

2. CARDINALITY. For genuinely dangerous capabilities the correct constraint is not "in this set of places" but "in exactly ONE place". The language has no way to say that. Add it -- an exclusivity marker meaning at most one declared site, so eval, exec, and net get a real chokepoint rather than a list.

Both matter for the same reason: a permission list has no upward pressure. Every new file that writes a file gets appended to the fs.write list, and nothing ever removes one. The declaration ratchets looser as the codebase grows, which is precisely backwards for a security model.

The design pattern this should enable: funnel each capability through a single owner (all fs.write goes through one io module; every other caller calls that), then the via list is 1 and stays 1. That turns each capability into an auditable chokepoint instead of a growing inventory -- and makes the eventual waiver/capability audit tractable.

Sequencing note: symbol-level `via` requires that the capability scanner attribute a hit to an enclosing SYMBOL, not just a file. Check whether the scanner already has that (it builds tree-sitter spans for comment exclusion, so the machinery is likely present) before designing around a file-level constraint.

<!-- ticket:T-1628 -->
```yaml
id: T-1628
title: 'strata: capability via lists only ever grow -- add a one-way ratchet'
state: queued
kind: security
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1627
parent: T-1623
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/strata/**
- src/frob/gates/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Capability `via` lists in design/frob.strata only ever grow. When a new file starts writing to disk, the fix is to append it to the fs.write list, and nothing anywhere pushes back. The self-model therefore documents an ever-loosening posture while looking green the whole time.

Add a ratchet: a via list may SHRINK freely, but growing it requires an explicit, recorded justification -- the same posture the repo already applies to waivers (a reason plus a follow-up), and the same one-way discipline T-1575's profile auto-ratchet uses (tighten automatically, loosen only by deliberate act).

Mechanically: record each capability's declared site count in the baseline the gates already keep; fail when a count increases without an accompanying justification attribute on that declaration; pass silently when it decreases.

This is what converts the capability model from documentation into enforcement. Today a developer who adds an exec call in a new file gets a SYS finding, appends the file, and moves on -- the gate taught them the ritual for widening the boundary rather than making them argue for it.

Report, as part of this ticket, the current per-capability site counts so there is a baseline to ratchet from and a number to drive down later.

<!-- ticket:T-1629 -->
```yaml
id: T-1629
title: 'strata: interface= should declare INTENDED surface, not mirror every public
  symbol'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1625
parent: T-1623
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/strata/**
- src/frob/gates/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
`interface=` is currently a GENERATED MIRROR of each node's entire public surface, maintained by `frob sys sync-interface` and enforced by SYS104 ("public symbol exported by code but not declared in interface=").

A generated mirror cannot be violated in any meaningful sense: when code and declaration disagree, the fix is to regenerate the declaration. So the only thing SYS104 actually catches is "you added a public symbol and did not run sync-interface" -- bookkeeping, not architecture. It can never answer the question an interface declaration exists to answer: is this symbol SUPPOSED to be public?

The valuable form is the inverse. Declare the INTENDED surface by hand -- normally small -- and have the gate fail on anything public beyond it. Then adding a new public symbol is a deliberate act that requires editing the contract, and accidental surface growth (the actual architectural risk) becomes a build failure instead of a regeneration prompt.

That inversion also fixes the size problem from the other end: an intended surface for `core` is a handful of entry points, not 817 symbols.

Design questions the ticket must settle:
- Migration path: today's generated lists are the starting point, but a mechanical copy would enshrine the current sprawl as "intended". Each node's list needs a human pass to distinguish real contract from incidental exposure. That is the actual work, and it should be sequenced per node rather than attempted in one sweep.
- What replaces sync-interface: probably a `--suggest` mode that reports undeclared public symbols for a human to accept or refactor away, rather than silently writing them in.
- Interaction with the SYS104 self-audit family, which currently reads the generated form.

This is the deepest of the strata maturity tickets and should be sequenced after the mechanical ones (duplicate blocks, testsuite noise), since those shrink the surface this has to reason about.

<!-- ticket:T-1630 -->
```yaml
id: T-1630
title: 'renumber(root) has no v2 stale-snapshot guard: wire ledger_digest_map into
  _new_renumber'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_store.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
`renumber(root)` (the plain contiguous-renumber path in
src/frob/tickets/_new_renumber.py, distinct from `renumber_one`) has no
v2-mode dispatch of its own -- it calls `write_all(root, new_map,
expected_digest=digest)` where `digest = ledger_digest(ledger_path(root))`,
a v1 monofile digest. In a v2-mode repo this string is meaningless
(ledger_path(root) does not exist), and T-1588's write_all now correctly
treats a bare str expected_digest in v2 mode as "no check requested"
rather than misapplying it -- but that means renumber(root) in a v2 repo
gets NO stale-snapshot protection at all: a sibling process's write between
this function's load_all and its write_all is silently clobbered by the
wholesale rewrite, same T-0680 shape T-1588 closed for write_all/
write_archive's primitive.

Fix: give renumber(root) a v2-aware digest snapshot, using
frob.tickets._store.ledger_digest_map(root) in place of the v1
ledger_digest(ledger_path(root)) call, mirroring how renumber_one already
dispatches to renumber_one_v2 for its own v2 path. Filed while working
T-1588 (out of scope there -- T-1588 was scoped to src/frob/tickets/
_store.py only).

<!-- ticket:T-1631 -->
```yaml
id: T-1631
title: 'coordinator: migrate main''s own ledger to v2 in a quiet window'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
- tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1552's own precondition (main's ledger migrated to v2) is not yet met:
this repo's tickets.md/tickets-archive.md are still the v1 monofile as of
2026-08-06 (verified directly: tickets.md/tickets-archive.md exist at
repo root, no tickets/T-####/ticket.md directories exist). T-1492 (CLI
wiring for `frob ticket migrate --to v2`) and T-1553 (fresh-repo default
flip) are both done, but nobody has actually RUN the migration against
this repo's own ledger content yet.

This is a coordinator-only action (needs a quiet window with zero
in-flight worktrees, per T-1552's own stated precondition -- a worktree
mid-ticket-mutation during the migration would race the wholesale
rewrite). Filed while working T-1552 so its blocker has a concrete id
instead of a prose-only precondition.

Plan (from T-1552's own Description):
1. Coordinator runs `frob ticket migrate --to v2` against this repo in a
   quiet window (zero in-flight worktrees).
2. Observe the LEDGERV1001 deprecation window for the recorded interval.
3. Once stable, T-1552 unblocks and can delete the v1 splice machinery.

<!-- ticket:T-1633 -->
```yaml
id: T-1633
title: live-tracker scan reads narrative prose as declarations (and its regex lacked
  a left boundary)
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_live_tracker.py
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
`_WAIVER_TICKET_PATTERN` in src/frob/tickets/_live_tracker.py is:

    ticket=\"?{id}\"?\b|ticket\s+\"{id}\"|follow_up=\"?{id}\"?\b

The first and third alternatives have a right-hand word boundary but NO left-hand one, so `ticket=T-12NN` matches as a SUBSTRING of any longer identifier ending in `ticket=`. Real false positives this produces:

- `active_ticket=T-15NN`  -> matches `ticket=T-15NN`
- `landing_ticket=T-12NN`, `parent_ticket=T-12NN`, and anything else of that shape
- the same for `follow_up=` inside a longer attribute name

Observed 2026-08-06: landing T-15NN was refused with LiveTrackerCited, naming tickets.md:7462. The citing text was ordinary NARRATIVE PROSE in T-15NN's own Done report -- a sentence explaining that a scoped run "sets active_ticket=T-15NN". Nothing cited T-15NN as a live tracker; the ticket was simply unlandable until the prose was reworded.

Fix: anchor the left side of each attribute alternative, e.g. `(?<![\w.-])ticket=` and `(?<![\w.-])follow_up=`, so only a genuine standalone attribute matches.

Two further hardening points worth doing in the same pass:

1. The scan greps the LEDGER as well as source. A Done report is narrative, and narrative legitimately quotes commands and attributes -- `--ticket T-12NN`, `follow_up="T-12NN"` shown as an example, a pasted error message. Consider excluding Done-report prose from the waiver-citation grep entirely, or restricting the ledger scan to structured frontmatter. A detector that reads prose as declarations will keep producing this class of refusal no matter how good the regex is. (Precedent in this repo: TICK006 already had to learn that a marker-lookalike inside quoted prose is not a marker, T-1541.)

2. Add the boundary cases to the test suite directly: `active_ticket=T-XXXX` must NOT be a citation, `ticket="T-XXXX"` must be, and the same pair for `follow_up=`.

Note this guard is doing exactly what it should in the general case -- T-1559 added it to stop a closing ticket orphaning waivers that name it, and that is valuable. This is a precision bug in an otherwise correct check, not an argument against the check.

NOTE ON THIS TICKET'S OWN TEXT: the examples above deliberately use non-existent placeholder ids (T-15NN, T-12NN). The first revision of this ticket quoted the real id, and the body itself was then flagged as a live-tracker citation, blocking the very land it describes -- a self-demonstrating instance of the prose-read-as-declaration problem this ticket exists to fix.

<!-- ticket:T-1637 -->
```yaml
id: T-1637
title: Manual draft refile silently discards evidence and Done reports; renumber already
  exists and is undocumented
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner/**
- docs/guides/agent-playbook.md
- docs/modules/tickets.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
`frob ticket renumber <old> <new>` already exists and "rewrites one ticket's id everywhere". It is the correct primitive for turning a worktree draft id into a real one. Nothing documents that, so the recipe actually used -- five times on 2026-08-05/06, by the coordinator -- was a hand-rolled sequence:

1. read the draft's body out of the worktree ledger
2. `frob ticket new` on main with that body, capturing the new real id
3. delete the draft's block from the worktree ledger
4. string-swap every citation of the draft id in the ledger and in source

That recipe is lossy and it lost data. Step 3 deletes the block that holds the ticket's EVIDENCE LIST and its DONE REPORT; step 2 creates a fresh ticket that has neither. The land then refuses with "missing evidence or a Done report", and the only way back is `git show <commit>~1:tickets.md` archaeology to recover 12 evidence ids and a 12KB Done report and re-record them by hand. That happened for T-1636. Earlier repeats of the same recipe were survivable only because those tickets' content had already reached main by other means.

The recipe also has a second failure mode already hit twice: a blanket string-swap of the draft id renames the draft's OWN block instead of removing it, producing a duplicate of the real ticket in the worktree ledger.

Deliverables:

1. A first-class promotion path -- `frob ticket promote <draft-id>` (name negotiable) that allocates the next real id and performs the renumber atomically, carrying frontmatter, evidence, Done report, scope, and every citation across in one operation. This is the missing half of T-1622: that ticket asks worktree ids to be real from the start, this one makes existing drafts recoverable either way.

2. Failing that, document `frob ticket renumber` as THE way to refile a draft, in docs/guides/agent-playbook.md next to the existing draft-loss guidance, so the manual recipe stops being reinvented.

3. Make the lossy step impossible to take by accident: removing or overwriting a ledger block that carries a Done report or a non-empty evidence list should refuse, or at minimum warn loudly naming what is about to be discarded. The ledger already has post-splice integrity checks (`_post_splice_integrity_check`, T-1536) that refuse when an id would be LOST -- this is the same class of protection one level down, for a block's contents rather than its existence.

Point 3 is the one that generalises. The ledger is the system of record for work that has already been done; discarding a Done report should be as hard as discarding a ticket.

<!-- ticket:T-1638 -->
```yaml
id: T-1638
title: 'land resolves root from cwd: running it from inside a worktree targets the
  wrong repository'
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- src/frob/tickets/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
`frob ticket land <id> --worktree W` resolves its ROOT from the current working directory. Run it while cwd is inside W (or inside any other worktree), and the land treats that worktree as "main" -- merging into the wrong place, or refusing with a confusing error that names the wrong repository.

Hit twice on 2026-08-05 by the coordinator: a shell whose cwd had followed an earlier `cd` into a worktree launched two lands whose root was that worktree rather than the real main checkout. Both were caught only because they happened to refuse for an unrelated reason (DirtyMain in the wrong tree). A land that had proceeded would have merged a ticket into a sibling worktree's branch.

The same session also produced the mirror error at the git level: an `Edit` wrote to main's file by absolute path while the shell's cwd was inside a worktree, so the follow-up `git commit` targeted the worktree's branch instead of main. Recorded in the coordinator's own memory as a standing hazard, i.e. currently mitigated by discipline rather than by the tool.

Fix: `frob ticket land` must refuse when the resolved root is inside ANY registered worktree of the repository while `--worktree` names a different one. The check is cheap -- `git worktree list` is already parsed elsewhere in this codebase (`frob.tickets._leases._list_agent_worktrees`) -- and the refusal message should name both the resolved root and the intended target so the fix is obvious.

Consider the same guard for every other verb that takes `--worktree`, and for `--path`: a command whose target is derived from cwd is a foot-gun for any caller running from a shell with sticky cwd, which is every agent and every background job in this repo's workflow.

Regression test: from a cwd inside worktree A, `land <id> --worktree B` must refuse and name both roots.

<!-- ticket:T-1640 -->
```yaml
id: T-1640
title: INV006 fires on waiver-reason prose, penalising precise justifications
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
blocked_by:
- T-1663
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_inv.py
- src/frob/dsl.py
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
INV006 flags a file that "makes an exclusivity/normative claim" -- a bare `only`, `never`, `always` -- with no `frob:invariant INV-###` edge anchored anywhere in it. That is a good rule for a docstring or a design comment stating how the system behaves.

It also fires on WAIVER REASON text. Observed 2026-08-06: a `frob:waive EXHAUST002 reason="..."` justification read "int(str) can only ever raise ValueError, never TypeError", and INV006 turned main red with 1 error until the sentence was reworded.

The question this ticket must settle: should a waiver's reason count as a normative claim?

The case for YES (current behavior): the sentence really does assert an invariant about int()'s behavior, and if that assertion is wrong the waiver is unjustified. Waiver reasons are exactly where unproven claims hide -- which is the whole premise of the waiver audit (T-1614).

The case for NO: a waiver reason is an ARGUMENT about why a finding does not apply, not a specification of system behavior. Demanding an INV-### binding for every explanatory sentence makes reasons worse: the cheapest way to satisfy the gate is to write a vaguer reason, and a vaguer reason is precisely what the waiver audit will later condemn. A rule that penalises precise justification is pointed the wrong way.

My read is NO for waiver reasons specifically, but the decision should be deliberate and documented either way, not left as an accident of which prose the scanner happens to reach.

Note the pattern: this is the third detector this drive found reading PROSE as if it were a declaration (TICK006 on a marker quoted mid-sentence, T-1541; the live-tracker scan on Done-report narrative, T-1633; now INV006 on a waiver reason). Consider whether these want a shared notion of "this span is explanatory text, not a declaration" rather than three independent fixes -- the DSL already knows where directive attributes end and free text begins.

Whatever is decided, add the case to the test suite so the behavior is pinned rather than incidental.

<!-- ticket:T-1643 -->
```yaml
id: T-1643
title: Wire a real Tier-B --fix handler (T-1262 shipped only the synthetic TIERBDEMO001
  reference handler)
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine_tier_b.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1262's own Done report discloses this as a cut, out of its declared scope: fix_tierbdemo001_marker_rewrite is a deliberately synthetic handler (keyed to a placeholder TIERBDEMO001 id that is never a real frob check rule) proving the snapshot-apply-verify-commit-or-rollback transaction path end-to-end. No real, production Tier-B handler (a handler for an actual gate rule id) exists yet. Pick a real candidate rule currently fixed only at Tier A or not auto-fixed at all, and wire it through the Tier-B transaction machinery T-1262 built, following that ticket's own TIER_B_HANDLERS registration precedent.

<!-- ticket:T-1644 -->
```yaml
id: T-1644
title: Bind src/frob/yaml_io.py into the strata self-model and waive INV006 on the
  T-1420 TS split
state: queued
kind: docs
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/vet/_capability_typescript_bindtable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Two mechanical consequences of the wave-8 lands, both caught by the gates on main:

SELFAUDIT001 (SYS102): T-1204 added src/frob/yaml_io.py (the shared fast_yaml_loader factory that stops a fifth re-derivation of loader selection) but no strata node's code= glob covered it, so the file was outside the self-model entirely. Bound to the cli node alongside the other src/frob root-level modules, and frob sys sync-interface then declared fast_yaml_loader in that node's interface=.

INV006: T-1420 split _capability_typescript.py by pipeline phase, and the new _capability_typescript_bindtable.py header carries the module's historical narrative -- 'X only ever inspected identifier/member_expression', past tense, describing a round-1 gap that round 2 closed. The real recursion invariants live on the functions themselves in the sibling module as frob:invariant terminates edges. Waived at file level with that reasoning rather than reworded, because rewording history to dodge a keyword makes the narrative worse without making the code safer. Whether INV006 should read explanatory prose at all is T-1640.

<!-- ticket:T-1648 -->
```yaml
id: T-1648
title: A ticket can close with disclosed unfinished work and no follow-up, silently
  dropping it
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_reporting.py
- src/frob/app/ticket_runner/_close_cmd.py
- tests/**
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Twice in one wave, a ticket closed while its own Done report disclosed substantial unfinished work, and that work became untracked the moment the ticket left the queue:

- T-1420 split 1 file and disclosed 52 more still over the LARGE001 threshold. Closed. The 54 warnings had no owner until T-1646 was filed by hand.
- T-1204 fixed the PERF010 family and disclosed PERF011/014/008/005/013 as not attempted. Closed. 47 warnings, no owner until T-1647.

Both agents behaved WELL: they scoped honestly, did solid work, and disclosed the cut plainly rather than padding a completion claim. The failure is structural. A Done report is free text, so "I did not attempt X" is invisible to the queue, and closing is the act that erases it. The coordinator only caught these by re-reading two long reports and noticing the warning counts had not moved as much as expected.

This is the same family as this drive's other silent-absence incidents (a gate reporting zero because it could not look; a suite truncating without a summary line): the system reports success while the unfinished part is simply not represented anywhere.

Proposed: make a disclosed remainder a first-class, structured thing.
- A ticket may close with a REMAINDER: a short structured field (not prose) naming what was not done.
- Closing with a non-empty remainder REQUIRES a follow-up ticket id, exactly as a WIRE001 waiver requires a follow_up. Frob already knows how to demand "name the ticket that carries this forward" -- reuse that machinery rather than inventing a second one.
- `frob ticket close` refuses if the Done report contains disclosure-shaped language (not attempted, disclosed cut, honest remainder, out of scope for this pass) and no remainder field is set. A heuristic prompt is acceptable here; the goal is to make the author pause, not to parse English perfectly.

The acceptance test is the one that failed here: close a ticket whose report says "52 files remain, not attempted" and have frob demand where those 52 files went.

Note for whoever implements: do NOT make this so heavy that agents stop disclosing. Honest disclosure is the behaviour worth protecting -- the fix should capture it, never punish it. If the choice is between an agent writing "not attempted" freely and an agent hiding a cut to avoid ceremony, the current state is better than a bad fix.

<!-- ticket:T-1649 -->
```yaml
id: T-1649
title: 'PERF remainder: 9 real PERF011 site fixes, PERF014 rule-level audit, 2 out-of-scope
  PERF005 Rust findings'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/_native.py
- src/frob/gates/_inv.py
- src/frob/gates/_inv006_split_assist.py
- src/frob/gates/_lang_conformance.py
- src/frob/vet/_capability_scan.py
- src/frob/gates/_docptr.py
- src/frob/gates/_refs.py
- src/frob/arch/_cpp_mayraise.py
- src/frob/arch/_ffi.py
- src/frob/arch/_protocol_excuse.py
- src/frob/gates/_rule_id_scan.py
- src/frob/perf/_hotpath_smells.py
- frob-core/src/extract.rs
- tests/**
- docs/modules/gates.md
- docs/modules/perf.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 doc-drift edits recording the T-1649 rule-level fixes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/perf.md
  reason: AFFECT001 doc-drift edits recording the T-1649 rule-level fixes
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_does_not_fire_on_whole_text_single_pass
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_hoisted
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
- tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns
- tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_kotlin_file_no_longer_flagged_by_lang002
- tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_aggregates_across_files
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_aggregates_across_files
threat: null
component: null
```
T-1647 fixed the majority of the 47-warning gate:PERF pool (rule-level PERF011 false-positive fix cleared 20 findings on its own; PERF013's genuine duplicate ast.walk got merged; 3 PERF008 findings and 2 residual PERF011 sibling-loop false positives got specific waivers; one PERF005 recursion got its frob:invariant terminates). Unscoped gate:PERF went 47 -> 20 unwaived warnings (99 -> 104 waived).

This ticket is the disclosed remainder T-1647 did not attempt, split by rule:

## PERF011 -- 9 genuine findings (real debt, not rule misfires)

A repo-scan API (iter_files/xref/exports_consumers) called once per outer-loop iteration, genuinely re-walking the same (sub)tree N times where N is a small collection (file extensions, spec dirs) the caller already has in hand. Per this repo's own PERF011 remedy text: hoist and index once per distinct key, don't rescan.

- src/frob/check/_native.py:29 (_collect_sources) -- per-extension rglob via iter_files inside `for ext in exts:`
- src/frob/gates/_inv.py:370 (inv003_gate) -- per spec_dir (2 dirs)
- src/frob/gates/_inv.py:495 (inv004_gate) -- same shape as inv003_gate
- src/frob/gates/_inv.py:661 (inv006_gate) -- nested per src_dir x suffix
- src/frob/gates/_inv006_split_assist.py:89 (find_carried_waiver) -- nested per candidate_dir x candidate_suffix (own docstring notes this runs rarely -- low real-world cost, still worth an honest fix or a reasoned waiver citing that same rarity)
- src/frob/gates/_lang_conformance.py:159 (_lang002_unregistered_files) -- per candidate-language extension
- src/frob/gates/_lang_conformance.py:190 (_lang003_unsound_gaps) -- per supported_extensions() extension, called just to check truthiness (existence) -- cheapest fix of the nine: hoist one `iter_files(repo_root)` call and index by suffix once, or track "extension present" via a single pass
- src/frob/vet/_capability_scan.py:602 (_aggregate_capabilities) -- per _EXT_LANGUAGE extension
- src/frob/vet/_capability_scan.py:663 (_aggregate_fingerprints) -- identical shape, sibling of the above (candidate for a genuinely shared helper -- same walk/exclusion shape already noted in that file's own docstring)

## PERF014 -- 9 findings, rule needs the SAME kind of audit T-1647 gave PERF011 first

_perf014_finditer_in_nested_loop fires on "3+ for/while tokens anywhere earlier in the function", the same flat/no-nesting-info design PERF011 had before T-1647's fix. A spot check of 2 of the 9 live findings found the identical failure class: SEQUENTIAL (sibling), not truly nested, loops earlier in the function inflate the count past the threshold.

- src/frob/gates/_docptr.py:122 (_prose_tokens) -- CONFIRMED false positive: a listcomp's own `for` (building newline_offsets) plus the first (single-loop) finditer call's own `for match in ... finditer(text):` both precede the SECOND, genuinely-2-level-nested finditer call (`for line_no, line in enumerate(...): for match in ..finditer(line):`), pushing the count to 3 and misfiring on a shape the rule's own docstring says must stay silent.
- src/frob/gates/_refs.py:387 (_python_import_targets) -- CONFIRMED false positive: two SEQUENTIAL top-level for-loops (one per import style: `from X import Y` then `import X`), each with its own single level of real nesting; the second loop's count inherits the first loop's tokens, again crossing the >=3 threshold on 2 real levels.

The other 7 (src/frob/arch/_cpp_mayraise.py:238,354; src/frob/arch/_ffi.py:273,366; src/frob/arch/_protocol_excuse.py:91; src/frob/gates/_refs.py:412; src/frob/gates/_rule_id_scan.py:128) were NOT individually re-verified against real code by T-1647 -- do that first, the same way T-1647 audited every live PERF011 finding, before assuming they're all false positives or all real.

A real fix needs the same "is this call inside a loop that is ITSELF nested under an earlier, still-open loop, vs. one that just lexically follows an earlier CLOSED loop" distinction PERF011's T-1647 fix used bracket-depth-plus-first-loop tracking for -- PERF014's threshold-counting design will need a comparable (not necessarily identical) rewrite, since sum-of-preceding-loops can't currently tell "3 truly nested" from "2 nested + 1 sequential sibling" apart. Follow T-1647's own audit-before-fixing method: read the rule, sample every live finding against real code, classify per-site, THEN decide site-fix vs rule-fix vs waive.

## PERF005 -- 2 findings, both out of scope for T-1647 (scope was src/frob/**, tests/**)

- frob-core/src/extract.rs:52 (walk_leaves)
- frob-core/src/extract.rs:254 (collect_comment_nodes)

Both are Rust recursion in the frob-core crate; this repo's `frob:invariant terminates` annotation convention is Python-only as far as T-1647 could tell in-scope -- confirm whether an equivalent Rust-side annotation mechanism exists before fixing/waiving these, or extend scope to frob-core/**.

## Done report

Natives verified healthy before measuring: `make core`/`uv run frob natives
build` (both strata_core and frob_core built cleanly) at the start of this
session, and unscoped `uv run frob check --only perf` read exactly ~20
unwaived warnings (20 -- matches T-1647's disclosed baseline, not 0/near-0),
confirming the analysis layer was live, not silently dead.

PERF014 audit (the ticket's main ask): read `_perf014_finditer_in_nested_loop`
and found the identical flaw T-1647 fixed in PERF011 -- a flat "count every
for/while token anywhere earlier in the function" heuristic that cannot tell
a genuinely nested loop from an earlier, already-closed SIBLING loop.
Rewrote it as a per-file AST pass (`_perf014_ast_violations`, reusing
`frob.lang.raw_tree`, the same substrate `frob.perf._loop_effects` already
uses for PERF008 in this package) computing real ancestor for/while
loop-nesting depth for each `.finditer(...)` call site, via body-only
containment so a loop's own iterable expression never counts as nesting.

Verdict per finding (all 9 sampled against real code):
- src/frob/gates/_docptr.py:122 -- FALSE POSITIVE (confirmed). A listcomp's
  own for-clause plus a first, single-level finditer loop are SEQUENTIAL;
  a genuinely-2-level-nested second finditer call is the only real site.
  Depth-based check: both finditer calls measure depth 0/1, correctly silent.
- src/frob/gates/_refs.py:387 (_python_import_targets) -- FALSE POSITIVE
  (confirmed). Two SEQUENTIAL top-level for-loops, each with one real
  level, never nested in each other. Both finditer calls measure depth 0,
  correctly silent.
- src/frob/gates/_refs.py:412 (_candidate_tokens) -- FALSE POSITIVE. The
  `for pattern in (...): for match in pattern.finditer(text):` shape is
  the FIXED, desired one-loop-per-pattern form (T-1211's own remedy target)
  -- depth 1, correctly silent.
- src/frob/arch/_cpp_mayraise.py:238 (_scan_body_raises) -- FALSE POSITIVE.
  A single compiled pattern's finditer called once per line inside ONE
  loop (`for line in body_lines:`), not a pattern-list-inside-per-line
  shape at all -- depth 1, correctly silent (the rule's own remedy text
  is about pattern-list x per-line; this has no pattern list).
- src/frob/arch/_protocol_excuse.py:91 -- FALSE POSITIVE, same shape as
  _refs.py:412 (single loop-per-pattern, the fixed form). Depth 1, silent.
- src/frob/gates/_rule_id_scan.py:128 -- REAL. `for base in SCANNED_BASES:
  for path in sorted(base_dir.rglob(...)): for lineno, line in enumerate(...):
  for m in _LITERAL_PATTERN.finditer(line):` is 3 real nested levels
  (dir x file x line) around a single-pattern per-line finditer call --
  depth 3, correctly stays live (line shifted to :163 after this diff's
  own unrelated edits elsewhere in the file).
- src/frob/arch/_cpp_mayraise.py:354 (_scan_each_function) -- REAL. Per-
  function x per-line nested loop around `_CALL_RE.finditer(line)` --
  depth 2 (line shifted to :371).
- src/frob/arch/_ffi.py:273,367 -- one FALSE POSITIVE (same single-loop
  shape as _cpp_mayraise.py:238's sibling), one REAL (same per-function x
  per-line shape as _cpp_mayraise.py:354, now at :399).

Net: rewrote the rule (one fix, not nine site edits) rather than hand-
classifying each site with a bespoke waiver. Unscoped gate:PERF PERF014
count: 9 -> 3 unwaived (6 confirmed false positives eliminated; the 3
real, confirmed-nested sites are correctly still live, not silenced).
Filed a successor, T-1660, for those 3 real fixes -- restructuring
each to a whole-text finditer + line-offset recovery (the _docptr.py::
_prose_tokens precedent) is real work outside this ticket's own stated
scope (rule-level audit, not the site fixes).

PERF011: all 9 genuine sites fixed by hoisting the per-extension/per-
directory repo-scan call to ONE `iter_files()` scan, filtered/indexed in
memory against the caller's own already-known small extension/directory
set, instead of one call per extension/directory:
- src/frob/check/_native.py::_collect_sources
- src/frob/gates/_inv.py::inv003_gate/inv004_gate (new `_spec_dir_md_files`
  shared helper) and ::inv006_gate (new `_inv006_src_files` helper)
- src/frob/gates/_inv006_split_assist.py::find_carried_waiver
- src/frob/gates/_lang_conformance.py::_lang002_unregistered_files/
  _lang003_unsound_gaps
- src/frob/vet/_capability_scan.py::_aggregate_capabilities/
  _aggregate_fingerprints (new shared `_files_by_ext` helper, matching
  that file's own docstring note calling these two "candidate for a
  genuinely shared helper")

PERF005 (frob-core/src/extract.rs, Rust): confirmed the `frob:invariant
terminates` comment-DSL convention already applies to Rust (precedent:
frob-core/src/lib.rs:522, strata-core/src/lib.rs:93/167/520) -- not
Python-only as T-1647 left disclosed-uncertain. Added the annotation to
both `walk_leaves` and `collect_comment_nodes`: both recurse strictly into
tree-sitter's own finite parse-tree children, terminating at a leaf (zero
children) or, for `collect_comment_nodes`, also at the first
`RUST_COMMENT_KINDS` match. Rebuilt natives after the Rust edit and
re-verified.

No mass waiving: every disposition above is either a structural rule fix
(PERF014), a real site hoist (PERF011), a real Rust invariant annotation
(PERF005), or an explicit successor ticket for confirmed-real remaining
debt (PERF014 x3) -- zero blanket/reasonless waivers added.

Measured before/after unscoped `uv run frob check --only perf`:
- Before: 0 errors, 20 warnings, 104 waived.
- After: 0 errors, 3 warnings, 105 waived (2 PERF005 fixed via
  annotation not waiver, so waived count only moved by the ledger's own
  bookkeeping, not a new suppression -- see gate:PERF tool output).

Verification: touched-file pytest suites (hotpath_smells, test_gates.py,
test_lang_conformance_gate.py, test_vet.py, test_check.py,
test_app_runners_batch6.py) all green (1285 collected, 0 failed, run in
two passes). `frob check --only gates-fast --ticket T-1649`: 0 errors
(AFFECT001/PRE001/SCOPE001 fixed via doc touches + scope --add + a
sweep re-run). `frob check --land-parity`: clean, 0 unscoped errors.
`git diff main --diff-filter=D --stat`: empty.

### Changed
```
 docs/modules/gates.md                  |  19 ++++
 docs/modules/perf.md                   |   8 ++
 frob-core/src/extract.rs               |  14 +++
 src/frob/check/_native.py              |  21 +++-
 src/frob/gates/_inv.py                 |  78 ++++++++------
 src/frob/gates/_inv006_split_assist.py |  93 +++++++++--------
 src/frob/gates/_lang_conformance.py    |  21 +++-
 src/frob/perf/_hotpath_smells.py       | 180 ++++++++++++++++++++++++++-------
 src/frob/vet/_capability_scan.py       |  28 ++++-
 tickets.md                             |  76 +++++++++++++-
 10 files changed, 415 insertions(+), 123 deletions(-)
```

### Evidence
- `tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_does_not_fire_on_whole_text_single_pass` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_hoisted` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_kotlin_file_no_longer_flagged_by_lang002` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_aggregates_across_files` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_aggregates_across_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 6369 warning(s), 849 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1654 -->
```yaml
id: T-1654
title: Audit remaining real-repo build_graph tests for T-1433/T-1635 xdist self-scan
  contention
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
## Description
T-1635 found and fixed a real cross-process shared-resource contention
class: tests that call `frob.graph.build_graph` directly against this
repo's own real checkout root (`Path(__file__).resolve().parents[1]`,
not an isolated `tmp_path`) contend on `.frob/derived.lock`
(`derived_state_lock`/`derived_state_write_lock`, `src/frob/process/
_lock.py`) -- an unbounded `fcntl.flock` with no internal timeout -- and
also pay full-repo-parse peak-memory cost. Under `pytest-xdist -n auto`,
enough of these landing on different workers at once can queue past the
per-test pytest-timeout budget or trigger an OOM "node down" kill
(T-1433's originally diagnosed shape, tests/conftest.py's
`_SELF_SCAN_HEAVY_NAME_SUBSTRINGS`).

T-1635 extended that existing xdist_group mechanism to the two
`test_registry_exhaustiveness.py` tests it reproduced actually failing
this way. It did NOT audit the other files matching the same
`build_graph(real repo root, ...)` shape found via a grep sweep --
listed here for a future burn-down, each needing the same "does it
actually reproduce under -n auto load" verification before being added
to the group (adding untested names would be superstition, not
evidence):

- tests/test_waive_gate.py
- tests/test_graph.py
- tests/test_dup.py
- tests/test_gates.py
- tests/test_secrets_gate.py
- tests/test_vet.py

## Plan
1. For each file above, identify which test(s) call `build_graph`/
   `find_clones`/similar against the real repo root rather than a
   `tmp_path` fixture.
2. Reproduce contention under `pytest -n auto` load (repeated full-suite
   runs, or a targeted heavy-load repro) before adding any test name to
   `_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` -- do not add speculatively.
3. Consider whether `derived_state_lock` itself should grow a bounded
   wait + clear timeout error (rather than blocking forever) as a
   separate, more general hardening -- out of scope for a test-file-only
   fix, worth its own ticket if picked up.

<!-- ticket:T-1656 -->
```yaml
id: T-1656
title: 'LARGE001 remainder: 48 files after T-1651 (3 waived, seams found for 3, 2
  flagged risky, 43 unexamined)'
state: queued
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- design/frob.strata
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Successor to T-1651. T-1651 waived LARGE001 on 3 files (config.py,
gates/_waive.py, tickets/_models.py -- see its Done report for the
per-file "no honest seam" reasoning) and gate:LARGE moved 53 -> 50
warnings. 48 files remain over the 800-line frob.toml threshold.

Edit-frequency ranking (git log --format=%H --name-only -400, not raw
size -- see T-1651's Done report for the full method and why it
disagrees with a size-only ordering):

Real-seam split candidates identified but NOT attempted (each is its
own multi-session project per T-1646/T-1651 precedent):

1. src/frob/gates/__init__.py -- 79 edits, 7639 lines. Section-divider
   comments already group functions by gate family (DRIFT/AFFECT/COV001
   -COV007/etc). Highest-value target in the whole family.
2. src/frob/tickets/_store.py -- 25 edits, 2230 lines. Docstring names
   two backends ("single" ledger vs legacy "dir"/v2); the v2-specific
   function cluster is a distinct consumer set (legacy-layout repos).
3. src/frob/strata/_selfconform.py -- 23 edits, 1925 lines. Docstring
   documents SYS100-SYS107 as 8 distinct numbered rules, same
   rule-family seam shape as (1).

Flagged high-risk, needs dedicated investigation before deciding
split-vs-waive (already multiply split, orchestrator-shaped -- a rushed
cut risks the exact "arbitrary halves, worse than the warning" outcome
this family's own instructions warn against):

4. src/frob/tickets/_land.py -- 36 edits, 2820 lines. Already split
   3 ways (T-1186, T-1334); its own docstring names 3 retained groups
   (lock/repair-marker machinery, land()/_land_locked orchestrator,
   pre-merge preflight validators) that COULD be a 4th split but risk is
   high given this module's landing-critical role.
5. src/frob/app/ticket_runner/_land_cmd.py -- 35 edits, 2556 lines. Not
   yet examined in detail; do that first.

Everything below rank 5 (43 more files) has not been examined at all --
apply the same per-file judgement T-1651/T-1646 both used: find the real
seam (cohesive responsibility, pipeline phase, distinct consumer set) or
waive with a specific reason naming what was actually checked. A
line-count-only split is strictly worse than the warning; do not force
one to move the number.

Also carries forward one unfixed finding from T-1651 (out of its scope,
noted so it is not lost): src/frob/tickets/_land_merge_zones.py's
"known-gate-rules T-1002" union-zone glob names
src/frob/gates/__init__.py but the actual _KNOWN_GATE_RULES marker pair
lives in src/frob/gates/_waive.py -- the merge-conflict auto-resolver for
that hotspot currently cannot match at all. Worth its own small ticket if
nobody has filed one already.

Side effects every split in this family has produced (per the T-1651/
T-1646 dispatch brief) -- anticipate per split, do not discover at land
time: a new module needs a design/frob.strata code= glob addition plus
`frob sys sync-interface`; prose separated from its frob:invariant anchor
needs the anchor (or its waiver) carried forward explicitly as
carried-forward, not a new claim.

<!-- ticket:T-1657 -->
```yaml
id: T-1657
title: 'TEST005 remainder (~55 findings): successor to T-1655'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestAutofixManifest::test_clear_autofix_manifest_swallows_oserror
- tests/test_gates.py::TestScopePrework::test_record_prework_returns_err_on_oserror
- tests/test_gates.py::TestScopePrework::test_load_prework_returns_none_on_malformed_json
- tests/test_gates.py::TestScopePrework::test_load_prework_returns_none_on_schema_mismatch
- tests/test_gates.py::TestBaselineDelta::test_load_baseline_malformed_json_is_none
- tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths::test_malformed_json_treated_as_empty
- tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths::test_schema_mismatch_treated_as_empty
- tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths::test_malformed_toml_returns_empty
- tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths::test_non_list_rules_shape_returns_empty
- tests/test_decisions.py::test_bad_yaml_frontmatter_is_err
- tests/test_decisions.py::test_frontmatter_not_a_mapping_is_err
- tests/test_decisions.py::test_schema_validation_failure_is_err
threat: null
component: null
```
Successor to T-1655 (itself successor to T-1650/T-1273): T-1655's agent
closed a slice (gitio.py excerpt, doctor.py scan_venv_shims, mutate/_journal.py
record_journal_progress + remove_journal, vet/_capability.py
non_executable_line_numbers, refactor/_gitops.py working_tree_clean +
current_sha -- 8 symbols, 15 new tests, all real Err/edge-path induced
failures bound via frob:tests) and must NOT close T-1655 on partial
progress per its own body's standing instruction -- filing this successor
instead, per that same instruction.

Remaining work, last measured on a fresh non-deflated coverage.xml
(make coverage run completed cleanly, coverage.xml copied from
.frob/coverage.partial.xml, no TEST017 finding): approximately 53-60
TEST005 findings remain (68 measured at T-1655 start, minus the 8 symbols
whose branch/line coverage crossed threshold in this slice -- re-measure
unscoped with `frob check --only test` before burning down further, since
some counts may shift as branch percentages move independently of symbol
count).

Remaining breakdown by package at T-1655 start (re-verify -- gates and
app in particular are large and were NOT touched this round):
gates=14, app=10 (incl. app/ticket_runner), serve=9, arch=8, tickets=5,
scaffold=5, refactor=4 (1 of 5 closed), testing=3, vet=1 (1 of 2 closed),
strata=2, mutate=0 (2 of 2 closed), dup=1 (src/frob/dup/_pipeline/_smt.py
-- involves z3 SMT solver internals, genuinely harder to reach with a
narrow unit test; may need a dedicated investigation rather than a quick
Err-path test), doctor.py=0 (closed), gitio.py=0 (closed).

Method (carried forward, it worked):
- Measure UNSCOPED. A --ticket-scoped zero is not a package zero.
- Verify coverage.xml freshness and non-deflation (TEST017) before
  trusting any count; if TEST017 fires, stop and report rather than
  burning down against fiction. Recover from .frob/coverage.partial.xml
  per playbook 6d if the promote-to-committed step is blocked.
- Write tests that would FAIL if the behaviour broke -- induce the real
  failure (OSError, malformed input, missing git ref) and assert the
  documented Result/contract. A test that only executes lines to move a
  percentage is worse than the missing coverage -- it hides the gap
  permanently.
- Bind each test to the symbol it covers with a frob:tests directive,
  node-level.
- Prioritize `gates` (14) and `app`/`serve` (10/9) next -- they are the
  largest remaining clusters and were not touched this round; `dup`'s
  z3-solver code may warrant a scope note or separate investigation if a
  narrow unit test proves impractical.

Do NOT close this ticket on partial progress. Either drive it to zero or
file a named successor first and say so in the Done report, same as
T-1650/T-1655 before it.

## Done report

Measured UNSCOPED, before/after, on fresh non-deflated coverage.xml (no
TEST017 finding either run):

Before: 62 TEST005 findings (make coverage: 8616 tests, 0 failed; coverage.xml
copied from .frob/coverage.partial.xml per playbook 6d).

After: 55 TEST005 findings (make coverage: 8628 tests, 0 failed after fixing
a design/frob.strata interface-list drift the new tests introduced --
`frob sys sync-interface` added the 5 new top-level test symbols to the
testsuite node's interface= list; without it, 4 self-conformance tests
failed: test_selfconform.py's TestRealGateGreen and TestCoverageTotality,
test_frob_self_model.py's test_sys_gate_zero_violations, and
test_conform_eval_needle.py's test_real_repo_design_selfconform_has_no_eval_gap
-- re-ran all 4 after the fix, all pass).

62 - 55 = 7 findings closed by this round's 12 new tests across 6 symbols:
- src/frob/gates/_fix_engine_shared.py::clear_autofix_manifest (was already
  above threshold pre-round; test added for the untested OSError branch
  anyway since a real failure mode was undertested even if not gate-flagged)
- src/frob/gates/_prework.py::record_prework (OSError write path)
- src/frob/gates/_prework.py::load_prework (malformed JSON + schema
  mismatch)
- src/frob/gates/_ratchet.py::load_ratchet_lock (malformed JSON + schema
  mismatch)
- src/frob/gates/_ratchet.py::ratchet_enabled_rules (malformed TOML +
  non-list rules shape)
- src/frob/gates/decisions.py::load_decisions (bad YAML frontmatter,
  non-mapping frontmatter, schema validation failure)
- src/frob/gates/_baseline.py::load_baseline (malformed JSON; was already
  above threshold pre-round, same rationale as clear_autofix_manifest)

Every new test induces a REAL failure (a directory where a file is
expected -> IsADirectoryError/OSError; literal malformed JSON/TOML/YAML
on disk; a schema-mismatched dict) and asserts the documented
Result[T,E]/None contract -- none merely execute lines to move a
percentage.

Filed successor: T-1661 (renumbers at land), citing the
remaining breakdown: app=10, serve=9, arch=8, tickets=5, scaffold=5,
refactor=3, testing=3, gates=9 (down from 14), strata=2, vet=2, dup=1.
Not closing T-1657 -- 55 findings remain, per its own body's standing
instruction not to close on partial progress.

Untestable this round: none attempted and abandoned; the dup/_smt.py
finding (z3 SMT solver internals) was left alone as noted in the
successor body -- same "may need dedicated investigation" caveat carried
forward from T-1655.

### Changed
```
 design/frob.strata          | 571 +++++++++++++++++++-------------------
 frob-coverage.lock.json     | 167 ++++++-----
 tests/test_decisions.py     |  42 +++
 tests/test_gates.py         |  82 ++++++
 tests/test_gates_ratchet.py |  54 ++++
 tickets.md                  | 659 +++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 1220 insertions(+), 355 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestAutofixManifest::test_clear_autofix_manifest_swallows_oserror` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_record_prework_returns_err_on_oserror` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_load_prework_returns_none_on_malformed_json` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_load_prework_returns_none_on_schema_mismatch` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestBaselineDelta::test_load_baseline_malformed_json_is_none` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths::test_malformed_json_treated_as_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths::test_schema_mismatch_treated_as_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths::test_malformed_toml_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths::test_non_list_rules_shape_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_bad_yaml_frontmatter_is_err` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_frontmatter_not_a_mapping_is_err` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_schema_validation_failure_is_err` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 0 error(s), 2852 warning(s), 849 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1658 -->
```yaml
id: T-1658
title: Audit and clear 19 WAIVE004 stale-waiver warnings post-T-1652 symref fix
state: done
kind: docs
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_core.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/doctor.py
- src/frob/gates/__init__.py
- src/frob/release/__init__.py
- src/frob/serve/_events.py
- strata-core/src/parse/lexer.rs
- tests/system/test_cli_sys_audit.py
- tests/system/test_spawn_budget.py
- tests/test_dup_cross_lang.py
- tests/test_serve_daemon.py
- tests/test_ticket_leases.py
- tests/unit/perf/test_persist_run_cli.py
- tests/unit/perf/test_serial_pools.py
- tests/unit/perf/test_serial_pools_import_failure.py
- tests/unit/test_app_clean_runner_branches_t1400.py
- tests/unit/test_dup_cache.py
- tests/unit/test_land_release_coherence.py
- tests/unit/test_perf_runner_t1400.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
acceptance:
- text: Every WAIVE004 finding classified (a/b/c); obsolete waivers removed; deletions
    declared in the Done report
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
```
T-1652 fixed dead_symbol_gate never setting Violation.symref, which had let
waiver matching silently fall back to file-scope for every DEAD001 waiver
(one waiver anywhere in a file was forgiving every DEAD001 finding in that
file). Fixing it made waiver matching bind exactly, and WAIVE004 (unscoped
count) rose from 10 to 19 as a direct, expected consequence: some fraction
of the 19 are newly-honest reports of waivers that were never really
covering what they claimed, not new debt.

This ticket audits all 19 current WAIVE004 warnings on a full unscoped
`frob check` run, classifies each (obsolete-remove / retarget-remove /
enroll-as-structurally-unverifiable), and removes/retargets waivers whose
underlying finding is confirmed gone.

Scope: only the frob:waive comment lines themselves (deletion), not the
functions/gates they sit beside. No gate logic changes expected -- this is
a hygiene pass over stale waiver directives across the tree.

## Done report

Audited all 19 gate:WAIVE004 findings from a full unscoped `frob check`
(before: 19, after: 0). Every one classified (a) obsolete -- the
underlying finding is confirmed gone on the current tree, not a
scoping/matching artifact -- and removed. No rule was enrolled in
_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES; none of the 19 needed it
(DEAD001/DEPR005/REF002/ARCH*/EXHAUST* all evaluate full current state
per run, matching the T-1577 comment's own prior audit of those three
rule classes).

Per-waiver classification:
- src/frob/_cli_parsers/_core.py:82 DEAD001 (_add_outline_parser): (a)
  the symbol now carries a real frob:tests edge (added by a later
  ticket), so dead_symbol_gate's DECLARED-referenced check exempts it
  outright -- it can never produce a DEAD001 finding again, waiver moot.
- src/frob/app/ticket_runner/_land_cmd.py:1835 ARCH103 (_land): (a) the
  function no longer trips ARCH103 at all (confirmed: 0 ARCH findings for
  this function in a full run) -- refactored/shortened since the waiver
  was written.
- src/frob/doctor.py:324 EXHAUST003 (scan_live_land_processes): (a) no
  EXHAUST003 finding for this function currently; the resolver-visibility
  gap the waiver described is gone.
- src/frob/gates/__init__.py:7067 ARCH001 (_run_combined_jobs): (a) no
  ARCH001 finding for this function currently -- consistent with the
  waiver's own reason text ("executable body is a dozen lines").
- src/frob/release/__init__.py:17 ARCH102 (module-level): (a) the whole
  module carries zero ARCH findings now.
- src/frob/serve/_events.py:154 EXHAUST002 (subscribe_and_wait): (a) the
  waiver's own reason text says the JSONDecodeError case "is now
  explicitly caught inline (T-1062)" -- self-documented as already fixed;
  confirmed only EXHAUST003 (a different, still-waived finding on the
  same function) fires now.
- strata-core/src/parse/lexer.rs:4 REF002 (whole file): (a) lexer.rs now
  has 2 inbound references (parse/mod.rs's `mod` decl plus
  grammar_policy.rs), not the single reference the waiver was written
  against.
- tests/system/test_cli_sys_audit.py:9, tests/test_ticket_leases.py:34,
  tests/unit/test_app_clean_runner_branches_t1400.py:10 -- 3x DEPR005
  (resolver name-collision on run()): (a) verified src/frob/app/
  xref_runner.py::run / outline_runner.py::run / map_runner.py::run no
  longer carry any frob:deprecated directive at all -- they were
  un-deprecated since these waivers were written, so DEPR005 (which only
  evaluates live frob:deprecated edges) can structurally never fire for
  them again.
- 8x DEAD001 on pytest autouse fixtures (tests/system/test_spawn_budget.py:43,
  tests/test_dup_cross_lang.py:75, tests/test_serve_daemon.py:55,
  tests/unit/perf/test_persist_run_cli.py:23,
  tests/unit/perf/test_serial_pools.py:45, tests/unit/test_dup_cache.py:16,
  tests/unit/test_land_release_coherence.py:44,
  tests/unit/test_perf_runner_t1400.py:36): (a) T-1651 (already landed on
  main, see git log) added an `@pytest.fixture(autouse=True)` exemption
  directly into dead_symbol_gate's own DECLARED/REFERENCED check
  (src/frob/gates/_dead_symbols.py's module docstring documents this:
  "_is_autouse_pytest_fixture ... DEAD001 lacked this exemption entirely
  before T-1651 and flagged 5 of this repo's own autouse fixtures as
  dead"). Every autouse fixture in the tree is now exempted at the gate
  level, permanently -- confirmed via a full run's gate:DEAD diagnostics
  (38 findings, zero of them autouse fixtures). These 8 waivers are dead
  weight from before that gate fix landed.
- tests/unit/perf/test_serial_pools_import_failure.py:99 DEAD001 (bare
  `_ = _serial_pools` statement, not a def): (b) this waiver was never
  attached to a real DEAD001-shaped target -- DEAD001 only scans
  function/class/method definitions (private-symbol dead-code), never
  bare module-level import-usage statements, so this waiver's site could
  never produce a matching DEAD001 finding under exact-symref matching
  even in principle. It most likely only ever "worked" pre-T-1652 via the
  file-scope fallback (coincidentally forgiving some other real DEAD001
  finding in this file, if one ever existed) -- confirmed the file
  currently has zero DEAD001 findings of any kind.

No rule needed WAIVE004's structurally-unverifiable-rule escape hatch --
every one of the 19 evaluated real, current, full-run state and read
correctly as "genuinely gone," not "diff-scoped noise."

Symref audit of other gates (requested alongside this ticket): arch_gate
(ARCH001/101-103/CPPTHROW001/LARGE001) and exhaustive_handling_gate
(EXHAUST001-003) both already carry symref correctly -- confirmed by
direct source read, not assumption. Two gates do NOT and structurally
look like the same DEAD001-class shape (a per-symbol finding built from a
resolved function/site name that never gets threaded into
Violation(symref=...)): CACHE001 (src/frob/gates/_cache_gate.py,
site.func_name resolved but unused for symref) and OPAQUE001
(src/frob/gates/_opaque.py, finding resolved per-site but no symref) --
OPAQUE001 is the higher-stakes one, carrying 166 live waived findings
repo-wide right now, all running on file-scope matching unverified. Filed
as T-1659 (out of this ticket's scope: src/frob/gates/_cache_gate.py
and src/frob/gates/_opaque.py are not in this ticket's declared scope).
PERF001-014/PII011-012/SEC005(taint_gate) were spot-checked (symref
present in only a minority of their source files) but not fully audited --
disclosed in T-1659's body as a recommended follow-up sweep,
not silently dropped.

Deletions (DELETION RULE, one per line, file + rule id):
src/frob/_cli_parsers/_core.py DEAD001
src/frob/app/ticket_runner/_land_cmd.py ARCH103
src/frob/doctor.py EXHAUST003
src/frob/gates/__init__.py ARCH001
src/frob/release/__init__.py ARCH102
src/frob/serve/_events.py EXHAUST002
strata-core/src/parse/lexer.rs REF002
tests/system/test_cli_sys_audit.py DEPR005
tests/test_ticket_leases.py DEPR005
tests/unit/test_app_clean_runner_branches_t1400.py DEPR005
tests/system/test_spawn_budget.py DEAD001
tests/test_dup_cross_lang.py DEAD001
tests/test_serve_daemon.py DEAD001
tests/unit/perf/test_persist_run_cli.py DEAD001
tests/unit/perf/test_serial_pools.py DEAD001
tests/unit/test_dup_cache.py DEAD001
tests/unit/test_land_release_coherence.py DEAD001
tests/unit/test_perf_runner_t1400.py DEAD001
tests/unit/perf/test_serial_pools_import_failure.py DEAD001

Verification: full unscoped `frob check` (foreground, timeout-wrapped)
before this change: gate:WAIVE 0 errors, 19 warnings, 0 waived. After:
gate:WAIVE line no longer printed at all (0 errors, 0 warnings, 0
waived) -- confirmed via both the plain-text summary and the --json
diagnostics array (no WAIVE004 entries). Total gate-summary warnings
dropped 128 -> 108 in the same run (the 19 WAIVE004 plus a 1-count
unrelated TICK fluctuation). No other gate family's counts changed except
TICK (15 -> 14, unrelated ledger-state drift, not caused by this change).
ruff-check flagged one incidental import-sort issue this edit's blank-line
removal left in tests/test_ticket_leases.py; fixed with `ruff check --fix`
and re-verified `ruff check .` -> "All checks passed!".

Filed: T-1659 (out-of-scope symref audit finding: CACHE001 and
OPAQUE001 lack Violation.symref, same class of bug as T-1652's DEAD001
fix; OPAQUE001 has 166 live waived findings currently unverified against
exact-symbol matching).

Gates: `frob check --only test --ticket T-1658` clean (0
errors, 9 warnings, 3 waived, all pre-existing/unrelated). Full unscoped
`frob check` clean: 0 errors repo-wide (gate-summary), same as before
this change except gate:WAIVE dropping to 0. Ruff/ty/format all pass.

### Changed
```
 tickets.md | 121 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 121 insertions(+)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 669 warning(s), 848 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1659 -->
```yaml
id: T-1659
title: Audit CACHE001/OPAQUE001 (and PERF/PII/SEC005) for the DEAD001-class missing-symref
  waiver hole
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_cache_gate.py
- src/frob/gates/_opaque.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: CACHE001 and OPAQUE001 Violations carry symref; waiver matching re-verified
    against the new symref for OPAQUE001's existing 166-waiver population
  evidence: []
threat: null
component: null
```
T-1652 fixed dead_symbol_gate never setting Violation.symref, which let
frob:waive DEAD001 fall back to file-scope matching and silently
over-forgive every DEAD001 finding in a waived file (44 of 62 findings
mis-waived by one directive). Auditing sibling gates for the same
"per-symbol finding constructed without symref" shape (requested by the
T-1652 aftermath review, T-1658's dispatch brief) surfaced two
live candidates, both currently ERROR-tier and both carrying real waiver
populations today:

- CACHE001 (src/frob/gates/_cache_gate.py, _cache001_violation): the
  finding is inherently per-@memoize_per_run-function (site.func_name is
  already resolved and used in the message text) but Violation() never
  passes symref=f"{rel_path}::{site.func_name}". No live CACHE001 waiver
  exists yet, so this is a dormant hole, not an active over-forgiveness --
  but the first frob:waive CACHE001 written in a file with more than one
  @memoize_per_run function will silently forgive all of them, the exact
  DEAD001 shape.
- OPAQUE001 (src/frob/gates/_opaque.py, opaque_gate): promoted to ERROR
  (T-1185) and currently carries 166 live waived findings repo-wide --
  the largest waived population of any rule in the tree after this
  ticket's DEAD001 cleanup. finding.construct_name/finding.rationale are
  resolved per-site by frob.vet._capability._opaque_indirection_findings
  but Violation() never sets symref, so every OPAQUE001 waiver in the
  tree is running on file-scope matching right now, unverified. Given the
  size of the waived population this is the single highest-value
  candidate to re-audit once symref is wired, mirroring exactly what
  T-1652's DEAD001 fix uncovered (44/62 mis-waived).

Not investigated in depth (time-boxed out of the audit that filed this
ticket): PERF001-014 (4 of 19 files under src/frob/perf/ set symref
today, rest unchecked), PII011/PII012 (src/frob/gates/_pii_structural/*,
2 of 5 violation-emitting files set symref today), SEC005/taint_gate
(src/frob/gates/_taint_gate.py, no symref at all, per-sink finding).
Recommend a first pass on CACHE001 and OPAQUE001 (highest confidence,
highest stakes given OPAQUE001's waived population), then sweep the rest.

<!-- ticket:T-1660 -->
```yaml
id: T-1660
title: 'PERF014 remainder: 3 confirmed real per-line finditer nesting sites (cpp_mayraise,
  ffi, rule_id_scan)'
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/_cpp_mayraise.py
- src/frob/arch/_ffi.py
- src/frob/gates/_rule_id_scan.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1649's PERF014 rule-level audit (AST-based ancestor-loop-depth rewrite,
replacing the flat token-count heuristic) reclassified all 9 originally-live
PERF014 findings: 6 were confirmed false positives (flat-count conflated
sequential/comprehension loops with real nesting) and 3 are CONFIRMED real,
genuinely-nested per-line finditer sites that the rewrite correctly keeps
flagging:

- src/frob/arch/_cpp_mayraise.py:371 (_scan_each_function) -- calls
  `_CALL_RE.finditer(line)` inside `for idx, name, qualifiers in sig_lines:
  for line in body: ...` -- 2 real nested levels.
- src/frob/arch/_ffi.py:399 -- same per-function x per-line shape.
- src/frob/gates/_rule_id_scan.py:163 (scan_emitted_rule_ids) -- calls
  `_LITERAL_PATTERN.finditer(line)` inside a 3-level nested walk (per
  SCANNED_BASES dir x per file x per line).

T-1649's own scope only covered the rule-level audit/fix, not fixing these
individually-verified real sites. This ticket is that follow-up: for each,
either restructure to call finditer() once over the whole joined text (with
a newline-offset/bisect line-number recovery, the same technique
src/frob/gates/_docptr.py::_prose_tokens already uses for its own
whole-text finditer scan) instead of once per physical line, or add a
specific, reasoned frob:waive PERF014 if the restructure is not worth the
risk for that site (e.g. genuinely bounded/rare, matching the reasoning
_inv006_split_assist.py's own PERF011 fix carried for its "runs rarely"
site).

<!-- ticket:T-1661 -->
```yaml
id: T-1661
title: 'TEST005 remainder (55 findings): successor to T-1657'
state: queued
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Successor to T-1657 (itself successor to T-1655/T-1650/T-1273): T-1657's
agent closed a small slice (gates/_fix_engine_shared.py clear_autofix_manifest,
gates/_prework.py record_prework + load_prework, gates/_ratchet.py
load_ratchet_lock + ratchet_enabled_rules, gates/decisions.py load_decisions
-- 6 symbols, 12 new tests, all real OSError/malformed-JSON/bad-TOML/bad-YAML
induced failures asserting the documented Result/None contract, bound via
frob:tests) and must NOT close T-1657 on partial progress per its own body's
standing instruction -- filing this successor instead, per that same
instruction.

Remaining work, last measured on a fresh non-deflated coverage.xml (make
coverage run completed cleanly with 8628 tests passing, coverage.xml copied
from .frob/coverage.partial.xml, no TEST017 finding): 55 TEST005 findings
remain (62 measured at T-1657 start, minus 7 whose branch/line coverage
crossed threshold from this slice's tests).

Remaining breakdown by package, measured via `frob check --only test`
unscoped on the fresh stamp:
app=10, serve=9, arch=8, tickets=5, scaffold=5, refactor=3, testing=3,
gates=9 (down from 14 -- _baseline/_prework/_ratchet/decisions.py closed
this round; _cache_gate, _coverage(load_lock_audit_log),
_exhaustive_handling, _fix_engine_sync, _fix_engine_tier_c, _gate_cache,
_inv006_split_assist remain), strata=2, vet=2, dup=1.

dup's one remaining finding (src/frob/dup/_pipeline/_smt.py, 21.0% line
coverage) involves z3 SMT solver internals -- genuinely harder to reach
with a narrow unit test; may need a dedicated investigation rather than a
quick Err-path test, same note as prior rounds.

Method (carried forward, it worked -- verified again this round):
- Measure UNSCOPED. A --ticket-scoped zero is not a package zero.
- Verify coverage.xml freshness and non-deflation (TEST017) before
  trusting any count; if TEST017 fires, stop and report rather than
  burning down against fiction. Recover from .frob/coverage.partial.xml
  per playbook 6d if the promote-to-committed step is blocked.
- Write tests that would FAIL if the behaviour broke -- induce the real
  failure (OSError, malformed input, missing git ref) and assert the
  documented Result/contract. A test that only executes lines to move a
  percentage is worse than the missing coverage -- it hides the gap
  permanently.
- Bind each test to the symbol it covers with a frob:tests directive,
  node-level, using the path::Class.method dotted form (not pytest's ::
  form) to satisfy DOC007.
- New top-level Test* classes (or free test functions) added to tests/**
  require `frob sys sync-interface` to be re-run before `make coverage` --
  the testsuite node's design/frob.strata interface list enumerates every
  public test symbol by name, and an undeclared one fails
  tests/unit/strata/test_selfconform.py's SYS104 check AND
  tests/system/test_frob_self_model.py's zero-violations check AND
  tests/unit/strata/test_conform_eval_needle.py's needle-gap check --
  all three failed together in this round until `frob sys sync-interface`
  was run and its rewrite of design/frob.strata committed alongside the
  new tests. Run it as a matter of course whenever a test file gains a
  new top-level class or function, not just when a coverage run
  surprises you with these three failures.
- Prioritize `app`/`serve`/`arch` (10/9/8) next -- they are the largest
  remaining clusters and were not touched this round.

Do NOT close this ticket on partial progress. Either drive it to zero or
file a named successor first and say so in the Done report, same as
T-1650/T-1655/T-1657 before it.

<!-- ticket:T-1662 -->
```yaml
id: T-1662
title: 'EPIC: every check must decide from semantics, never a lexical match'
state: queued
kind: security
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/gates/**
- src/frob/vet/**
- src/frob/strata/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
STANDING PRINCIPLE, set by the repo owner 2026-08-06: every frob and strata check must decide from SEMANTICS -- a resolved symbol, a parsed AST node, a graph edge -- and never from a lexical/textual match. A check that greps is guessing.

This is not a hypothetical concern. Lexical matching has produced a documented incident or false-positive class roughly once per wave in this drive:

- PERF011 counted loop tokens instead of reading nesting structure -- 71% false positives (T-1647), fixed at the rule.
- PERF014 had the identical flaw -- 6 of 9 findings false (T-1649), rewritten as an AST ancestor-depth pass.
- DEAD001 never populated Violation.symref, so waiver matching fell back to FILE SCOPE -- 44 of 62 findings silently mis-waived (T-1652). OPAQUE001 has the same hole with 166 live waived findings (T-1659).
- Four separate detectors read explanatory PROSE as declarations: TICK006 on a marker quoted mid-sentence (T-1541), the live-tracker scan on Done-report narrative (T-1633), INV006 on a waiver reason and again on a module's historical narrative (T-1640).
- The vet capability scanner decides "does this code eval?" by substring search over raw bytes, with per-language binding passes bolted on afterwards to recover aliasing their own comments admit the lexical path "structurally cannot" catch (T-1626).
- An `except json.JSONDecodeError:` clause compared as verbatim TEXT against a bare name never discharged its leak (T-1636).

MEASURED AUDIT of src/frob/gates (60 modules), counting semantic signals (raw_tree/parse_file/GraphSnapshot/callgraph/lang.) against lexical ones (re.search/match/findall/NEEDLE/_PHRASE/startswith/endswith):

Gates with NO semantic signal at all -- pure lexical:
  _refs (22 lexical signals), _tickets_gate (14), _fmt_directives (6),
  _exclude_hazard (5), _secrets (5), _rule_id_scan (4), _render_lint (3),
  _mutation_evidence (2), _ffi_boundary (1), _waive_lease (1), _walk_lint (1)

Gates that are lexical-DOMINANT despite having some semantic access:
  _docptr (7 semantic / 32 lexical), _docblocks_refs (4/23),
  invariants (1/22), _doclink_docanchor (7/14)

Two confirmed concrete cases from that list:
- REF001 (_refs) decides "this file has no inbound references" by looking for its full path or BARE BASENAME mentioned in another file's text. A file reached through a constructed path, a variable, or an import alias is invisible to it; a file merely NAMED in unrelated prose counts as referenced. Both directions are wrong.
- WALK001 (_walk_lint) flags unpruned traversals by matching `os.walk`/`rglob` call TEXT. An aliased or indirectly-bound traversal evades it entirely.

NOT every lexical check is wrong, and this epic must not pretend otherwise. Some are legitimately textual by nature: _fmt_directives is a FORMATTER (it rewrites comment text), _secrets uses entropy/pattern detection which is the industry-standard approach, and a whole-file rule like LARGE001 has no symbol to bind to. The deliverable is a JUDGEMENT per check, not a blanket rewrite.

Children should:
1. Classify every gate rule as (a) genuinely semantic already, (b) lexical but legitimately so -- state why, (c) lexical and WRONG -- raise it to semantics.
2. For each (c), raise it, reusing the substrate that already exists: frob.graph.callgraph for resolution, frob.lang.raw_tree for AST, the snapshot's symbols/edges for the obligation graph. Do NOT build a second parallel analysis layer.
3. Establish the fail-closed rule this drive learned the hard way: when semantic resolution CANNOT determine an answer (genuinely dynamic dispatch, a computed getattr), the check must report UNRESOLVED and demand a declaration -- never silently pass. Every major incident this drive traced to analysis that reported "nothing found" when it could not look.
4. Add a meta-check if feasible: a new gate rule constructed from raw text without a symref or AST node should itself be a finding, so this class cannot silently return.

<!-- ticket:T-1663 -->
```yaml
id: T-1663
title: 'Classify every gate rule: semantic, legitimately lexical, or lexical-and-wrong'
state: queued
kind: docs
origin: human
created: '2026-08-06'
priority: high
parent: T-1662
tier: ticket
sprint: null
scope:
- docs/**
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
The classification pass that must precede any rewrite, so the epic acts on evidence rather than on the signal-count heuristic that produced its shortlist.

For EVERY rule frob emits (the known-rule registry is the authoritative list -- src/frob/gates/_waive.py's _KNOWN_GATE_RULES plus the registry entries), record:
- what the rule actually asserts, in one line
- what it inspects TODAY: raw text, a regex, an AST node, a resolved symbol, a graph edge
- whether its finding carries a `symref` (the DEAD001/OPAQUE001 hole -- a rule without one turns every waiver into a file-wide amnesty)
- classification: (a) semantic already, (b) lexical but legitimately so, (c) lexical and wrong
- for (b), the REASON it is legitimately textual -- a formatter rewriting comment text, an entropy-based secret scan, a genuinely whole-file rule with no symbol to bind
- for (c), what it should read instead, and which existing substrate provides it

The measured starting shortlist (semantic-signal count vs lexical-signal count across src/frob/gates):
- pure lexical: _refs 22, _tickets_gate 14, _fmt_directives 6, _exclude_hazard 5, _secrets 5, _rule_id_scan 4, _render_lint 3, _mutation_evidence 2, _ffi_boundary 1, _waive_lease 1, _walk_lint 1
- lexical-dominant: _docptr 7/32, _docblocks_refs 4/23, invariants 1/22, _doclink_docanchor 7/14

Treat that shortlist as a HINT, not a verdict -- it counts import-site occurrences, so a gate can score low and still be fully semantic, or score high because it formats text for a message. Read each rule.

Deliverable: a table in docs/ (durable, later children read it), plus one filed ticket per (c) rule. Do NOT fix anything in this ticket; misclassifying a legitimately-textual rule as broken would cost more than the bug it chased.

Known (c) candidates already evidenced, include them and verify:
- REF001 -- "no inbound references" decided by full-path or BARE BASENAME text mention. A file reached via a constructed path or import alias is invisible; a file merely named in prose counts as referenced. Wrong in both directions.
- WALK001 -- unpruned traversal detected by matching `os.walk`/`rglob` call text; an aliased or indirectly-bound traversal evades it.
- The four prose-as-declaration detectors (T-1633, T-1640): they need a shared notion of "this span is explanatory text, not a declaration". The DSL already knows where directive attributes end and free text begins -- reuse that rather than three independent fixes.

<!-- ticket:T-1664 -->
```yaml
id: T-1664
title: Semantic checks must report UNRESOLVED, never silently pass when they cannot
  analyse
state: queued
kind: security
origin: human
created: '2026-08-06'
priority: high
blocked_by:
- T-1663
parent: T-1662
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/lang/**
- src/frob/check/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
The rule this drive learned the hard way, made structural.

Every serious incident in this drive traced to the same shape: an analysis layer that could not look, reporting that it found nothing, indistinguishable from a clean result.
- The perf gate reported ZERO PERF004 findings with stale natives while every health check said healthy -- the escape hatch it unlocked deleted 55 live frob:waive directives.
- A mypy oracle sharing .mypy_cache across xdist workers returned zero diagnostics for a file that had one.
- A suite run truncated before its summary line and read as success.
- The capability scanner returns an empty capability set for a language it has no pattern table for -- "no capabilities observed" and "I cannot analyse this language" are currently the same answer.

Requirement: when a semantic check CANNOT resolve, it must say so. An unresolved call target, an unparseable file, a missing language adapter, a stale analysis substrate -- each must produce an explicit UNRESOLVED/DEGRADED finding demanding a declaration or a waiver, never a silent pass.

Concretely:
1. A distinguished outcome in the gate result model separating "checked, found nothing" from "could not check". Today both collapse to an empty violation list.
2. Gates that depend on an optional substrate (natives, a language adapter, a resolver) declare that dependency and report degradation when it is absent -- the structural signal T-1620 asks for, generalised beyond perf.
3. `frob check` surfaces degraded stages in its summary line, so a run that could not analyse half the repo cannot read as a clean run.

This is the single highest-leverage item in the epic. Semantic checks FAIL DIFFERENTLY from lexical ones: a regex always produces an answer, while a resolver can genuinely not know -- so raising checks to semantics without this makes silent under-reporting MORE likely, not less. Sequence it early, ideally alongside the first (c)-class rewrite rather than after several.

<!-- ticket:T-1665 -->
```yaml
id: T-1665
title: 'REF001: decide inbound references from resolved imports and calls, not path/basename
  text mentions'
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
blocked_by:
- T-1663
parent: T-1662
tier: ticket
sprint: null
scope:
- src/frob/gates/_refs.py
- src/frob/graph/**
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
REF001 decides whether a file has any inbound reference by searching other files' TEXT for its full repo-relative path or its BARE BASENAME. Its own module docstring says so: "by file Y if Y names X (full repo-relative path or bare basename) in a ... literal, a backtick-wrapped MULTI-COMPONENT path mention".

That is wrong in both directions:
- FALSE POSITIVE (reports dead when live): a module reached through an import alias, a constructed path (`root / "sub" / name`), a dynamic import, a registry/dispatch table, or a plugin entry point is never NAMED anywhere, so it reads as unreferenced.
- FALSE NEGATIVE (reports live when dead): a file merely mentioned in prose, a changelog entry, or a comment counts as referenced. A genuinely dead module stays hidden as long as some document names it.

Both matter. The false positives generate waivers that then have to be maintained forever (REF002 is at 51 findings largely for this reason), and the false negatives defeat the rule's entire purpose.

Raise it to semantics:
- For code targets, an inbound reference means a resolved IMPORT or a resolved call/attribute reference reaching that module -- frob.graph.callgraph and the snapshot's edges already model this.
- Keep an explicit, NARROW textual channel for the genuinely non-code cases the rule must still cover: a config file named in a template, a data file read by path. Those should be an explicit declared-reference form (`frob:used-by`, which already exists) rather than an accidental substring hit.
- Per T-1664, a target whose reachability cannot be resolved must report UNRESOLVED, not "referenced" and not "dead".

Expect the finding set to CHANGE substantially in both directions, not merely shrink. Report before/after with a classification of everything that appears and disappears -- a file that stops being flagged because it is genuinely imported is a fix; one that starts being flagged because only prose named it is the rule finally working.

While here, check whether the existing REF001 waivers were compensating for the lexical gap. If most of them say some version of "reached dynamically", that is direct evidence for the semantic model and those waivers should be REMOVED, not migrated.
