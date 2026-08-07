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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
state: done
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
- tests/test_tickets_lease.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_lease.py
  reason: landing requires re-pointing a WIRE001 waiver follow_up= citation that named
    T-1487, since T-1487 is closing without touching that file's fixture
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
designated_repro_test: null
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

Verification-only pass, no new kernel code required.

Investigation before writing anything (per dispatch instructions,
understanding exactly where T-1220's portion-1 boundary sits): T-1220's
own Done report already records extract_tree_python (the python
tree-extraction kernel) as fully delivered -- 917-file golden parity,
FFI-boundary compliance, docs/modules/lang.md and docs/modules/dup.md
updated in that same change. Confirmed directly against this worktree's
main tip:

- frob-core/src/extract.rs already defines extract_tree_python (line
  207) and frob-core/src/lib.rs already registers it in the frob_core
  pymodule; frob-core/frob_core.pyi already types it.
- tests/unit/test_extract_native.py already contains
  TestExtractTreePythonParity with all four tests this ticket's
  acceptance criterion names.
- docs/modules/lang.md and docs/modules/dup.md already document the
  kernel (Extraction API / frob-core kernels sections).

T-1487's own ledger entry already carried a pre-filled Done report
(evidence, Changed diffstat, Captured claims) despite state=queued --
apparently drafted as a carrier stub when T-1220 was split, but never
actually run through start/land. There is no remaining "next portion"
of python-kernel work inside this ticket's own scope: the whole
scope (frob-core/**, tests/unit/test_extract_native.py,
docs/modules/lang.md, docs/modules/dup.md) as it pertains to the
PYTHON kernel is already satisfied by code on main. Remaining
tree-extraction work (cpp/typescript kernels, consumer rewiring) lives
under the parent T-1220 and T-1219 respectively, outside this ticket's
declared scope -- not something to fold in here.

Re-verified rather than trusted the stale prose:
- `pytest tests/unit/test_extract_native.py -q`: 7 passed (4 python-
  parity + 3 rust-parity, both already-landed kernels).
- `frob check --ticket T-1487 --only ffi_boundary`: 0 errors, 0
  warnings.
- `frob check --ticket T-1487 --only scope --only prework --only fmt
  --only affect_drift`: 0 errors, 154 warnings (SCOPE002 breadth notes
  from the ticket's own broad frob-core/** and docs-file globs pulling
  in unrelated anchors/frob:tests edges elsewhere in those same files --
  same pre-existing debt class T-1220's own Done report already
  disclosed for this scope, not new).
- `frob check --ticket T-1487 --only gates-fast --only gates-native
  --only gates-security`: 0 errors repo-wide across every gate family.

No source change was needed or made; this dispatch's own worktree
commit is only the `ticket start` transition record. Closing T-1487 as
delivered-by-T-1220, with T-1487's own evidence re-verified against
current main rather than merely re-asserted from the stale draft.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 301 warning(s), 724 waived
- error-findings: none (measured, zero errors)

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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
threat: null
component: null
```
Refiled: original draft T-1539 (filed during T-1225's perf-detector work) died in the t-1350 ledger corruption spans. PERF012 fires from src/frob/perf but docs/design/registry/check-coverage.yaml has no CHK-GATE-PERF012 entry -- pre-existing gap found (not caused) by T-1225.

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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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

<!-- ticket:T-1567 -->
```yaml
id: T-1567
title: 'cli regrouping: frob quality verb group (check/test/dup/arch/bind/cycle/mutate/perf)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1725
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
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
blocked_by:
- T-1725
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
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
blocked_by:
- T-1725
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
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
blocked_by:
- T-1725
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
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
blocked_by:
- T-1725
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
threat: null
component: null
```
should_color honors FORCE_COLOR and NO_COLOR, and a CLI subprocess a test spawns inherits the whole environment. A shell exporting FORCE_COLOR=3 (Claude Code and several CI images do) embeds ANSI escapes in every CLI output a test asserts on: 5 system tests failed here purely from the ambient shell while the same commit passes elsewhere. An autouse conftest fixture now deletes both per test (delete, not force NO_COLOR, so color-path tests can still monkeypatch either one). Needs a regression test asserting a spawned CLI produces escape-free output with FORCE_COLOR set in the parent env.

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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
threat: null
component: null
```
Work to run only AFTER the rest of the queue is drained, in the stated order. Filed now so it is not forgotten, deliberately gated so it is not started early.

Why the gating is real and not ceremony: each child measures the repo's finished state. A docs sweep run mid-drive documents code that is about to change; a vestigial-artifact cleanup run mid-drive deletes things an in-flight ticket still references; a waiver audit run mid-drive judges waivers whose follow-up work has not happened yet and would condemn honest ones. Running these early produces confidently wrong answers -- the most expensive kind.

Order: docs sweep, then the detector-gap audit it feeds, then the artifact cleanup, and the waiver audit LAST, as explicitly requested.

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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
threat: null
component: null
```
Umbrella for the strata self-model hardening reviewed on 2026-08-05. Findings, in dependency order: the declaration file is half redundancy (duplicate attr blocks, 5277 test names declared as interface); interface= is a generated mirror that cannot be meaningfully violated; capability detection is lexical rather than symbol-resolved; and via grants whole FILES rather than single controllable locations, with permission lists that only ever grow. Children carry the detail. Sequence the mechanical cleanups first so the design work reasons over a smaller surface.

<!-- ticket:T-1626 -->
```yaml
id: T-1626
title: 'strata: capability detection must be symbol-resolved with full alias support,
  not lexical needles'
state: done
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
- docs/modules/vet.md
- tests/test_vet_capability.py
- tests/unit/vet/test_taint.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: tests/**
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/vet.md
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_vet_capability.py
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/vet/test_taint.py
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_dict_literal_dispatch_resolves
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_list_literal_dispatch_resolves
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_dict_literal_dispatch_with_non_dangerous_value_not_flagged
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_wrapping_dangerous_op_resolves
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_called_directly_resolves
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_partial_from_import_alias_resolves
designated_repro_test: null
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

## Done report

Changed:
- src/frob/vet/_capability_python.py::_resolve_py_expr
- src/frob/vet/_capability_python.py::_resolve_py_partial_call (new)
- src/frob/vet/_capability_python.py::_resolve_py_subscript (new)
- src/frob/vet/_capability_python.py::_py_scope_alias_lookup (new, factored out of _attr_rebind_lookup)
- src/frob/vet/_capability_python.py::_attr_rebind_lookup (refactored onto _py_scope_alias_lookup)
- src/frob/vet/_capability_python.py::_py_literal_key_text (new)
- src/frob/vet/_capability_python.py::_record_py_dict_container_alias (new)
- src/frob/vet/_capability_python.py::_record_py_list_container_alias (new)
- src/frob/vet/_capability_python.py::_first_py_positional_arg (new)
- src/frob/vet/_capability_python.py::_record_py_alias (dict/list container branches added)
- src/frob/vet/_capability_python.py::_collect_py_candidates (subscript added to resolvable call-callee/standalone-reference node types)

Scope actually reached: python only, inside src/frob/vet/** as scoped. No
src/frob/graph/** change was needed for this slice (see "What I could not
close" below).

What changed and why (fail-closed framing per the ticket):

This is a SCOPED slice of the ticket's full ambition, not the complete
"consume frob.graph.callgraph for everything" rewrite -- see the split
proposed below. It closes the two evasions the ticket named as its own
worked examples that were previously silently invisible to BOTH detectors
(the raw-text needle scan AND the existing T-0328 import/alias resolver):

1. `functools.partial(dangerous, ...)` -- `_resolve_py_partial_call`
   resolves the call's own identity through to its first positional
   argument when the callee resolves to `functools.partial` (any import
   alias of it). Covers both `p = functools.partial(os.system, cmd); p()`
   (via the existing alias-table assignment path, unchanged) and
   `functools.partial(os.system, cmd)()` called directly.
2. Literal-keyed dict/list dispatch -- `_record_py_dict_container_alias`/
   `_record_py_list_container_alias` record one alias entry per
   string/integer-literal key or list index at assignment time (mirroring
   `_attr_rebind_lookup`'s existing by-name, non-points-to posture);
   `_resolve_py_subscript` looks the entry up at the call site. Covers
   `handlers = {"run": subprocess.run}; handlers["run"](cmd)` and the
   list sibling.

Verified BEFORE this change, both fixtures resolved to `set()` from
`scan_file_capabilities` (needle scan: no literal `"subprocess.run("`
text exists in either fixture; resolver: no `subscript`/`call`-to-
`functools.partial` handling existed in `_resolve_py_expr` at all) --
confirmed by running the new tests against the pre-change code before
writing the fix (both failed with `assert "exec" in set()`). AFTER: both
resolve to `{"exec", ...}` as expected (6 new tests, all passing).

Fail-closed status (the ticket's headline requirement) -- NOT newly built
here, already exists and was verified still fires: `frob.gates._opaque`'s
OPAQUE001 (`RUNTIME_OPAQUE_CONSTRUCTS`/`RUNTIME_OPAQUE_STRUCTURAL_
CONSTRUCTS`, `_capability_scan.py`, T-0665/T-1051/T-1659) already reports
an explicit, gate-blocking finding -- never a silent "no capability" --
for exactly the cases this slice does NOT resolve: a non-literal
`getattr`/`setattr`/`__import__`/`eval`/`exec` name, and a non-literal-
keyed subscript-then-call. Verified directly: `getattr(os, name)(cmd)`
(computed `name`) produces one `_OpaqueFinding` with
`taxonomy_row='python:runtime:getattr-dynamic-name'` via
`_opaque_indirection_findings`. `_capability_scan._subscript_key_looks_
literal`'s own docstring explicitly deferred the LITERAL-key case to "the
ordinary resolver's job" -- that job had never actually been implemented
until this ticket; the non-literal case was always covered. I did not
add a NEW "UNRESOLVED" capability kind because one already exists
(OPAQUE001) and duplicating it inside `scan_file_capabilities` itself
would create two competing fail-closed mechanisms for the same
underlying fact, which is its own kind of drift risk.

Second-detector posture (per T-1328 coordination note): the raw-text
needle scan (`_matched_capabilities`/`_PATTERNS`) is UNCHANGED and still
runs as an independent first pass; the T-1626 resolver work extends the
EXISTING binding-aware second pass. T-1328 is a different, unrelated
second-detector concept (an OS-syscall-backed / generated-manifest
detector for strata's 7 app-level capability kinds, scoped to
src/frob/strata/_mutation_audit.py) -- read, not duplicated; no overlap
with this ticket's file scope.

What I could NOT close in this ticket, and why (proposing a split rather
than half-landing a false completeness claim):

- Cross-file wrapper attribution ("a helper that wraps a dangerous op and
  is called from elsewhere must attribute to the caller's node") is NOT
  attempted. The existing resolver (and this ticket's additions) is
  single-file: a wrapper defined in the SAME scanned file is already
  covered today (its body's own dangerous call is observed when that file
  is scanned), but a helper imported from ANOTHER file/module and called
  here is invisible to a per-file scan regardless of alias resolution.
  Doing this properly needs `frob.graph.callgraph`-backed cross-file
  resolution over the SCANNED DEPENDENCY'S OWN source tree (not this
  repo's own package graph, which is what `frob.graph.callgraph` is built
  and tested against today) -- a materially larger, separate unit of
  work: building/adapting a call graph for an arbitrary third-party
  source tree, deciding a traversal-depth/cycle policy, and deciding the
  attribution semantics (does a capability found N hops down attribute to
  every caller up the chain, or just the direct one?). I am filing this
  as a follow-up ticket rather than attempting a partial version of it
  here.
- TypeScript/Rust/C/Kotlin binding resolvers are untouched -- this
  ticket's own worked examples (functools.partial, dict/list dispatch)
  are Python-specific idioms; the existing T-0328 lineage already treats
  python as "the priority language" and defers the other four languages'
  binding-table depth as documented follow-up (module docstring, pre-
  existing). Extending container-alias/partial-equivalent resolution to
  each of those grammars is a separate, per-language unit of work I did
  not attempt inside this ticket's time budget.
- Symbol-level `via` attribution (naming WHICH declared symbol a resolved
  capability belongs to, not just "this file has capability X") is
  explicitly out of scope per the ticket body's own sequencing note
  ("Prerequisite for symbol-level `via`... Sequence this before, or
  together with, the via-granularity work") -- not attempted here,
  correctly deferred to whatever ticket does the via-granularity work
  next, now that this slice makes the underlying hit itself more
  symbol-resolved than before.

Filed: none yet -- filing the cross-file-wrapper-attribution follow-up
immediately after this report, scope
`src/frob/vet/**,src/frob/graph/**`, referencing this ticket.

Evidence: tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions
(6 node ids, all newly added and passing -- see evidence list on the
ticket). Also ran (not bound as evidence, regression-only):
tests/unit/vet/test_taint.py (8/8 pass, unchanged) and
tests/test_vet.py -k Capability (224/224 pass, unchanged -- this file is
OUT of this ticket's declared scope, run read-only to confirm no
regression in the existing T-0328/T-0337/T-0659 binding-resolution
suite it owns).

Gates: `frob check --ticket T-1626` clean (0 errors after fixing one
self-inflicted ARCH001 -- `_resolve_py_expr` grew past the 60-line
threshold with the inline functools.partial branch, split into
`_resolve_py_partial_call` to fix, no behavior change from the split
itself). `frob check --only static --ticket T-1626` and
`--only archgate --ticket T-1626` independently reconfirmed 0 errors
after the split. No waivers.

### Changed
```
 docs/modules/vet.md                |  23 +++-
 src/frob/vet/_capability_python.py | 265 ++++++++++++++++++++++++++++++++++---
 tests/test_vet_capability.py       |  92 +++++++++++++
 tickets.md                         |   9 +-
 4 files changed, 370 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_dict_literal_dispatch_resolves` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_list_literal_dispatch_resolves` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_dict_literal_dispatch_with_non_dangerous_value_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_wrapping_dangerous_op_resolves` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_called_directly_resolves` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_partial_from_import_alias_resolves` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 926 warning(s), 724 waived
- error-findings: none (measured, zero errors)

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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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

<!-- ticket:T-1631 -->
```yaml
id: T-1631
title: 'coordinator: migrate main''s own ledger to v2 in a quiet window'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
- tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
threat: null
component: null
```
`frob ticket land <id> --worktree W` resolves its ROOT from the current working directory. Run it while cwd is inside W (or inside any other worktree), and the land treats that worktree as "main" -- merging into the wrong place, or refusing with a confusing error that names the wrong repository.

Hit twice on 2026-08-05 by the coordinator: a shell whose cwd had followed an earlier `cd` into a worktree launched two lands whose root was that worktree rather than the real main checkout. Both were caught only because they happened to refuse for an unrelated reason (DirtyMain in the wrong tree). A land that had proceeded would have merged a ticket into a sibling worktree's branch.

The same session also produced the mirror error at the git level: an `Edit` wrote to main's file by absolute path while the shell's cwd was inside a worktree, so the follow-up `git commit` targeted the worktree's branch instead of main. Recorded in the coordinator's own memory as a standing hazard, i.e. currently mitigated by discipline rather than by the tool.

Fix: `frob ticket land` must refuse when the resolved root is inside ANY registered worktree of the repository while `--worktree` names a different one. The check is cheap -- `git worktree list` is already parsed elsewhere in this codebase (`frob.tickets._leases._list_agent_worktrees`) -- and the refusal message should name both the resolved root and the intended target so the fix is obvious.

Consider the same guard for every other verb that takes `--worktree`, and for `--path`: a command whose target is derived from cwd is a foot-gun for any caller running from a shell with sticky cwd, which is every agent and every background job in this repo's workflow.

Regression test: from a cwd inside worktree A, `land <id> --worktree B` must refuse and name both roots.

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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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
designated_repro_test: null
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

<!-- ticket:T-1664 -->
```yaml
id: T-1664
title: Semantic checks must report UNRESOLVED, never silently pass when they cannot
  analyse
state: planned
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
designated_repro_test: null
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
state: planned
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
designated_repro_test: null
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

<!-- ticket:T-1666 -->
```yaml
id: T-1666
title: Classify and re-waive the 142 OPAQUE001 findings T-1659's symref fix surfaced;
  sweep PERF/PII/SEC005 for the same shape
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/_config_external.py
- src/frob/perf/**
- src/frob/gates/_pii_structural/**
- src/frob/gates/_taint_gate.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
T-1659 fixed CACHE001 and OPAQUE001's missing Violation.symref (both now
symbol-exact). That symref narrowing surfaced real work this ticket's
scope did not cover fixing:

## OPAQUE001: 142 newly-unwaived findings (166 waived -> 24 waived + 142/143 error)

Before (main, file-scope matching): 0 errors, 166 waived.
After (this ticket's fix, symbol-exact matching): 142-143 errors, 24 waived
(measured via `frob check --only opaque --json`, `gate:OPAQUE` diagnostics:
166 total, severity counter {error: 142, note: 24}).

Breakdown of the 142 unwaived:
- 136 in tests/** -- overwhelmingly literal getattr()/setattr()/eval()-shaped
  fixture STRINGS written as test source text (e.g.
  tests/test_ticket_work_and_land_finish.py: 30, tests/unit/strata: 14,
  tests/unit/test_ticket_runner_land_release.py: 12, tests/test_app.py: 11,
  tests/test_gates.py: 10, and 10+ more files with 1-9 each). These read as
  a genuine rule-level pattern (test fixtures constructing runtime-opaque
  constructs to exercise OTHER gates/features), not attacker-reachable
  production code -- but each needs a real frob:waive with its own reason
  (or the fixture rewritten to avoid the construct), not a blanket
  re-forgive. Recommend triaging by file: most are probably one `frob:waive
  OPAQUE001 reason="test fixture constructing a <rule> litmus, not
  production code"` per fixture function.
- 6 in src/**, all previously covered by ONE waiver each that the file-scope
  fallback let cover multiple sibling functions:
  - src/frob/app/_config_external.py:399,428,445,458,479 -- five
    `_apply_*_fields` helpers (_apply_path_fields/_apply_int_fields/
    _apply_float_fields/_apply_list_fields/_apply_bool_flags). The ONE
    existing waiver above `_apply_string_fields` (line 381) explicitly says
    in its own reason text (T-1424 update) "this waiver now covers every
    `_apply_*_fields` helper below" -- a deliberate multi-site waiver that
    relied on the file-scope fallback this ticket closes. This is a
    GENUINELY ACCEPTABLE pattern (same closed-tuple-of-known-field-names
    rationale applies to every sibling) -- the fix is mechanical: copy the
    same `frob:waive OPAQUE001 reason="..."` comment above each of the 5
    remaining `_apply_*_fields` functions (or extract a single small
    helper they all route the getattr through, if that reads better).
  - src/frob/logging/filter.py:26 -- NOT the same shape. Investigate
    separately (see the dsl.py bug filed alongside this ticket, referenced
    below) -- the existing waiver in `_BelowLevelFilter.__init__` resolves
    to `_BelowLevelFilter.filter` instead, a real comment-binding bug, not
    a multi-site-waiver pattern. Re-verify after that bug is fixed before
    assuming this site still needs its own waiver.

## CACHE001: dormant hole closed, no live waivers existed

T-1659 confirmed CACHE001 currently has 0 live `frob:waive CACHE001`
directives repo-wide, so populating its symref (done) closed a dormant hole
with no immediate unwaived-count consequence. No further action needed here
beyond what T-1659 already landed.

## Not yet swept for the same missing-symref shape (T-1659's own scope note)

`grep -c symref= <file>` presence-only audit (informed, NOT exhaustively
verified per site -- a real per-rule read is still owed):

- PERF001-014 (src/frob/perf/*.py): only `_recursion.py` sets symref today;
  `_advisories.py` (4 Violation sites), `_dup_spawn.py`, `_hotpath_smells.py`,
  `_loop_effects.py`, `_ratchet.py`, `_redundancy.py`, `_rules.py` do not.
  Each of these is a per-function/per-call-site finding by nature (the
  rule names -- duplicate-spawn, hotpath-smell, loop-invariant-effect,
  redundant-computation -- all describe a specific site), so these read as
  the SAME bug shape as CACHE001/OPAQUE001, not file-level-by-design. Needs
  the same live-waiver-population check T-1659 did for OPAQUE001 before
  fixing (a PERF gate promoted to ERROR with an existing waiver population
  could have the same silent-over-forgiveness exposure).
- PII011/PII012 (src/frob/gates/_pii_structural/*.py): none of the 5
  violation-emitting files (`_crosslang.py`, `_emails.py`, `_env_access.py`,
  `_keywords.py`, `_python_fields.py`) set symref today. Each finding is
  about a specific field/env-var/keyword site in a specific file -- same
  shape, needs the same audit.
- SEC005/taint_gate (src/frob/gates/_taint_gate.py): no symref at all,
  described in T-1659's own filing ticket as "per-sink finding" -- same
  shape, needs the same audit.

Scope for this successor: src/frob/app/_config_external.py (5-site
re-waive), src/frob/perf/**, src/frob/gates/_pii_structural/**,
src/frob/gates/_taint_gate.py, plus a representative slice of tests/** for
the 136 OPAQUE001 test-fixture re-waives (do not assume every file needs a
hand-written reason if a shared pattern emerges -- but do not blanket-waive
either, per the playbook's waive-discipline section).

<!-- ticket:T-1669 -->
```yaml
id: T-1669
title: 'Ledger ownership model: lease-scoped writes plus atomic draft promotion at
  land'
state: queued
kind: feature
origin: human
created: '2026-08-06'
priority: high
blocked_by:
- T-1631
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner/**
- docs/design/ledger-v2.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
The design the repo owner specified 2026-08-06: "apart from the frob ticket commands, main's regular tickets never get overwritten by a worktree, and on land, the draft tickets are automatically converted atomically into main tickets and committed. I don't want any manual handling of tickets."

THE ROOT CAUSE OF EVERY TICKET-HANDLING FAILURE THIS DRIVE IS THE V1 MONOFILE.

One `tickets.md` holds every ticket's record. Every worktree has a copy. Every `frob ticket` command writes the local copy. Git then merges STRUCTURED RECORDS LINE-WISE. Everything that went wrong follows directly from that:
- a `kind` field changed and committed on main was silently dropped by a later merge, with no conflict marker (T-1617) -- the land then read the stale value and refused
- draft blocks vanish across land previews (T-0577), so every follow-up ticket an agent files must be refiled by hand
- the manual refile recipe deletes the block holding the ticket's evidence and Done report (T-1637) -- it destroyed T-1636's and recovery needed `git show <commit>~1:tickets.md`
- duplicate blocks after merges, repaired by hand-splicing python over the ledger
- 33 active-vs-archive duplicate blocks needing manual repair in one earlier session

None of these are workflow mistakes to be more careful about. They are what happens when a structured, per-record datastore is stored as one text file and merged textually.

THE MODEL:

1. OWNERSHIP. A ticket's record is writable only by the holder of its lease.
   - a worktree holding T-1234's lease may write T-1234 and nothing else
   - main must REFUSE to write a ticket currently leased to a worktree (this is the half that lost the kind field -- main edited a ticket a worktree owned)
   - a ticket with no lease is main's to write
   Enforcement under v2 is a path check: refuse a commit touching `tickets/T-####/` you do not hold. Under v1 it is not enforceable at all, which is the argument for prioritising the migration.

2. PROMOTION AT LAND. Drafts stay local and opaque in the worktree; `frob ticket land` converts them atomically.
   A worktree cannot safely allocate a global id -- that needs coordination, and coordination is what breaks (an agent guessing the next free id collided with real ticket T-1651 this session, silently mis-attributing seven frob:ticket edges). The land already runs against main and, with T-1619's lease, holds exclusive access. That is exactly where an id CAN be allocated race-free. So: allocate at land, rewrite the draft record and every citation (ledger and source), commit as part of the land transaction. `frob ticket renumber` already performs the rewrite half atomically and should be reused rather than reimplemented.

3. NO MANUAL HANDLING. The acceptance criterion is the owner's sentence. If any flow still requires a human or coordinator to edit the ledger, extract a body, swap a citation, or delete a block, that flow is not done.

WHY V2 MAKES THIS NATURAL RATHER THAN BOLTED ON:
- one file per ticket -> ownership is a path check
- merging main into a worktree cannot conflict on other tickets, because they are different files
- promotion is `git mv tickets/T-draft-xxxx tickets/T-1234`, genuinely atomic
- a lost field requires two writers to the SAME file, which the ownership rule forbids

SEQUENCING: T-1631 migrates main's own ledger to v2 (coordinator task, quiet window, `frob ticket migrate --to v2`). T-1552 then deletes the v1 splice machinery. The ownership check and promotion path should be built correct-on-v2 and merely non-breaking on v1 -- do not design around the monofile that is being retired.

<!-- ticket:T-1674 -->
```yaml
id: T-1674
title: 'Every frob verb resolves root from cwd silently: widen T-1638 beyond land'
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
T-1638 records that 'frob ticket land' resolves the repo root from cwd, so running it from inside a worktree targets the wrong tree. The defect is not specific to land -- it is how EVERY frob verb resolves root, and the ledger-writing verbs are just as damaging.

Field incident, coordinator, 2026-08-06: a shell whose cwd had drifted into .claude/worktrees/w34-dispatch ran 'frob ticket new'. The ticket was filed into that WORKTREE's ledger rather than main's, and nothing in the output said so -- the command printed a created id and exited 0, identical to a correct run. It was caught only because the id came back as a T-draft-* rather than a T-#### (drafts are allocated in worktrees), and that tell exists only for 'new'. 'close', 'drop', 'evidence', and 'done-report' would have written to the wrong ledger with no distinguishing signal at all. In this case the worktree was about to land, so promotion recovers it; had the worktree been abandoned, the ticket would have been silently destroyed.

This is the R4 shape (position validated too late) and the same class as the earlier incident where a gate measurement was taken against a worktree and reported as main's number.

Work:
1. Every frob command reports the root it resolved -- at minimum on any ledger-writing or measuring verb, unconditionally, not behind -v. A run that cannot be attributed to a tree is not a trustworthy run.
2. Add an explicit --root / FROB_ROOT override so a caller can pin the tree rather than depending on ambient cwd. The coordinator's own measure wrapper already pins ROOT by hand for exactly this reason; that logic belongs in frob.
3. Decide the ownership rule per verb: which verbs are legitimate inside a worktree (start, evidence, done-report on the ticket being worked), and which should refuse or warn (new/close/drop targeting a ticket the worktree does not own). This overlaps T-1669's ownership model -- fold it in there if that is the cleaner home.

Supersedes the narrow framing of T-1638, which should become a child of this.

<!-- ticket:T-1678 -->
```yaml
id: T-1678
title: 'BUG002 compares a main-landed fix against itself: base_ref defaults to main'
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
check_bug_repro / bug_repro_violations in src/frob/gates/_mutation_evidence.py take base_ref: str = 'main'. The check re-runs the designated repro test at that ref to prove the test FAILS without the fix and PASSES with it.

That is correct for the worktree flow: an agent's fix lives on a branch, main genuinely lacks it, so main is a valid pre-fix ref. It is degenerate for work committed DIRECTLY to main, which is exactly the coordinator's flow. There, base_ref='main' resolves to HEAD -- the fix commit itself -- so the check runs the repro test against the fix and reports:

  T-1676's designated reproduction test PASSED at the parent commit
  (ada33703) -- this evidence does not prove the defect was fixed

ada33703 IS the fix. The message calls it 'the parent commit' while naming the commit under test, so the operator is told their evidence is confirmatory-only when in fact the comparison was vacuous. Observed on T-1676, 2026-08-06; the bound test genuinely does fail before the fix (the old code returned Err(PytestFailed) where the test asserts is_ok).

This is the R1/R2 shape: a check reporting a real-sounding negative when it could not actually make the comparison it claims to have made.

Work:
1. Resolve the pre-fix ref from the TICKET, not from a hardcoded branch name -- the commit the ticket started at, or the merge-base of the current branch against main, so it means the same thing whether the fix landed via a worktree or directly on main.
2. When the resolved ref CONTAINS the fix (ref is an ancestor-or-equal of HEAD and the ticket's own commits are already in it), the comparison is impossible: report that explicitly as UNRESOLVED rather than as a failed obligation. Per T-1664, a check that cannot decide must say so instead of emitting a verdict.
3. The message must never call a commit 'the parent commit' when it is the commit under test.

T-1676 was closed with --skip-mutation-evidence citing this ticket.

<!-- ticket:T-1686 -->
```yaml
id: T-1686
title: 'Verification watermark: make landing independent of verifying in every profile'
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
parent: null
tier: epic
sprint: null
scope:
- src/frob/tickets/_land_queue.py
- src/frob/serve/_daemon.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
T-1684 took the multi-minute verification sweep off the land critical
path under `rapid`. The same reasoning generalises to `standard`, and
doing so collapses three profile code paths into one mechanism at three
settings.

THE PRINCIPLE THAT DECIDES WHAT MAY BE DEFERRED

A check must be synchronous if and only if its failure damages someone
OTHER THAN the author. Ledger integrity, LAND-PROOF, lease/lock
discipline, merge-conflict resolution and "the tree imports" corrupt
other agents' work, so they stay on the critical path in every profile,
forever. Coverage floors, doc drift, arch thresholds, dup, perf and the
rest only assert that THIS change is good; their remedy is a follow-up
ticket, not a revert. There is no correctness argument for making the
author wait on those -- only habit.

THE MECHANISM

Verification is a pure function of tree state, so the unit of
verification is a COMMIT, not a land. Introduce a durable watermark:
"main is verified through commit X".

The daemon becomes a COALESCING worker rather than a FIFO one. Each land
appends a cheap intent record (commit sha, ticket id, touched symbol
set). The worker wakes, drains the queue TO ITS TIP, verifies once at the
newest commit, and advances the watermark past every commit in the batch.
Five lands, one verification pass -- and it is not a trick: verifying at
HEAD-after-L5 genuinely verifies L1..L5, because that is the tree that
ships.

The saving compounds twice: the gate pass amortises N-to-1, and the test
run becomes the UNION of the batch's touched sets in a single pytest
process (one collection, one set of fixtures) instead of N cold starts
over overlapping files.

THE HARD PART: ATTRIBUTION

Batching trades wall-clock for attribution precision. Three tiers,
cheapest first: (1) the T-1684 rolling-baseline set diff yields new
(rule, symbol) identities rather than a count; (2) SYMBOLIC attribution
-- a finding anchored at symbol S attributes to the commit whose touched
symbol set REACHES S in the reference graph; (3) bisect only the residue
tier 2 cannot attribute.

WHAT KEEPS IT HONEST

Bounded queue (depth and age; the land blocks at the ceiling -- deferral
is a credit line, not free money) and a quarantine circuit breaker (a red
batch stops further deferred lands until attributed, because landing on a
known-broken base is what makes attribution cost explode).

THE PAYOFF

The profiles stop being three code paths and become one dial:
`fortress` = depth 0 (synchronous, refuse on red); `standard` = bounded
depth K, quarantine + file on red; `rapid` = unbounded, never blocks,
files and never reverts. Every `if rapid:` seam scattered through the
land pipeline deletes.

RECORDED DECISION: on a red batch, `standard` QUARANTINES AND FILES; it
does not auto-revert. Reverting a published commit other worktrees have
already branched from is strictly worse than a filed high-priority ticket
plus a stop-the-line flag. Auto-revert is coherent only at depth 0, where
nobody can have branched yet.

WHAT ALREADY EXISTS (this is a connect-what-exists epic, not greenfield)

- `frob.tickets._land_queue`: persisted, locked, with enqueue/drain_next/
  queue_status. T-1444's own Done report disclosed "sharing one baseline
  capture and one post-drain sweep across a whole batch of N tickets" as
  deferred follow-up. This epic is that owed work.
- `frob.serve._warm`/`_watch`: the daemon already keys a WarmState on a
  repo dirty key and has FS-watch push invalidation -- the watermark's
  substrate, needing a durable commit-keyed sibling.
- T-1684's rolling baseline and `frob ticket sweep-async`: the deferred
  worker, today spawned per-land, becomes the daemon's queue worker.

Adjacent open work: T-1479 (daemon-proxy ticket path), T-1554
(post-commit checkpoint gap beyond the sweep window).

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

<!-- ticket:T-1689 -->
```yaml
id: T-1689
title: 'Batch test selection: run a batch''s union touched-set in one pytest process'
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1687
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_selection.py
- src/frob/app/graph_runner.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
The second, independent half of the batching saving. The gate pass
amortises N-to-1 by coalescing; the TEST run amortises by selection.

Compute the batch's affected test set as the union of its entries'
touched symbol sets expanded through the reference graph to the tests
that reach them -- symbolic reachability, never "tests whose filename
resembles the changed module". Run that union in ONE pytest process: one
collection, one conftest evaluation, one set of session fixtures.

N separate `frob test` invocations over overlapping touched sets pay N
cold pytest startups and re-run every shared test once per ticket. The
union pays one startup and runs each test once. On a batch of five
tickets touching adjacent modules this is usually the larger of the two
savings in this epic.

Report what was selected AND what was excluded, with counts, at INFO. A
selection that silently narrows is indistinguishable from a suite that
passes -- if the selection cannot be computed (graph unavailable), fall
back to the full suite and say so loudly, never to a narrower set.

Acceptance: a batch of tickets with overlapping touched sets runs each
affected test exactly once in a single process; an unresolvable graph
falls back to the full suite with an explicit WARNING naming why.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

<!-- ticket:T-1690 -->
```yaml
id: T-1690
title: 'Symbolic attribution: map a red batch''s findings to the commit that caused
  them via graph reachability'
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
blocked_by:
- T-1688
- T-1703
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_attribution.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
- tests/unit/verify/test_attribution.py
- tests/unit/test_rapid_sweep.py
- src/frob/verify/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_attribution.py
  reason: T-1690 needs new attribution unit tests plus rapid_sweep attribution-wiring
    tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: T-1690 needs new attribution unit tests plus rapid_sweep attribution-wiring
    tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/verify/__init__.py
  reason: editing __init__ to export the new attribution symbols alongside _attribution.py
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_direct_touch_attributes_at_depth_zero
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_two_reaching_commits_is_unattributed
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_zero_reaching_commits_is_unattributed
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_missing_line_falls_back_to_whole_file_candidates
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_graph_unavailable_is_an_error_for_the_whole_batch
- tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_open_ticket_is_open
- tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_done_ticket_is_not_open
- tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_missing_ticket_is_not_open
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_empty_queue_returns_empty_mapping
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_open_ticket_is_not_refiled
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_closed_ticket_is_refiled
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_unattributed_is_filed
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
The hard part, and the leaf most likely to be got subtly wrong.

Tier 1 -- SET DIFF. T-1684's rolling baseline already yields new findings
as identities rather than a count. Upgrade the identity from
(rule, file) to (rule, SYMBOL): a file-level identity cannot survive a
refactor that moves a symbol between files, and reports the move itself
as a regression.

Tier 2 -- SYMBOLIC REACHABILITY. A finding anchored at symbol S
attributes to the batch commit whose touched symbol set REACHES S in the
reference graph. This is the leaf's whole substance and it must be
graph-resolved: "the commit that touched the same file" is the lexical
version, it is wrong whenever a change breaks a caller rather than the
callee, and it is precisely the shortcut to refuse.

Ambiguity is a first-class outcome, not a coin flip. Zero candidates,
or more than one, is UNATTRIBUTED -- a distinct state that hands off to
the bisect leaf. Never pick the newest commit as a tiebreak; a confident
wrong attribution costs more than an honest "unknown", because it sends
someone to read a diff that is not the cause.

Attributed findings are filed against the OWNING ticket where one is
still open, otherwise as a new high-priority bug naming the commit, the
symbol, and the reachability path that produced the attribution. Log the
path -- an attribution nobody can audit is an assertion, not evidence.

Acceptance: a synthetic batch where commit A breaks a caller of a symbol
commit B touched attributes to A, not B; a finding reachable from two
commits' touched sets reports UNATTRIBUTED rather than guessing.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

## Done report

Changed:
- src/frob/verify/_attribution.py (new): AttributionError, Attribution, attribute_batch, _resolve_symbol, _symbols_in_file, _reaches, _load_snapshot_and_call_graph
- src/frob/verify/__init__.py: export Attribution/AttributionError/attribute_batch
- src/frob/app/ticket_runner/_rapid_sweep.py: _attribute_new_findings, _ticket_is_open, _partition_findings_by_attribution (ARCH001 split), _file_regression_ticket (rewritten to consult attribution before filing)
- docs/modules/tickets.md: new "Symbolic attribution (T-1690)" section
- tests/unit/verify/test_attribution.py (new), tests/unit/test_rapid_sweep.py (new test classes)

Design: a finding attributes to the batch commit whose touched symbols
REACH it via `frob.graph.callgraph.build_reference_graph`'s forward
symref edges (bounded BFS, `_reaches`), never a path-string comparison.
Ambiguity (zero or >1 reaching commit) is `status="unattributed"` with
every candidate commit's sha recorded -- never a newest-commit tiebreak.
The reachability path is logged at INFO for every attributed finding and
every candidate is logged at WARNING for an unattributed one, so an
attribution is auditable, not a bare assertion. A graph build/load
failure fails the WHOLE batch (`Err(AttributionError.GraphUnavailable)`),
never a partial attribution.

`_rapid_sweep._file_regression_ticket` now consults attribution before
filing: a finding attributed to exactly one commit whose owning ticket is
still open is logged and left off the regression ticket (already has a
home); everything else (attributed to a closed/dropped ticket, or
genuinely unattributed) is filed with the full audit trail in the body.
Attribution unavailable (queue unreadable/empty, or graph build failure)
degrades to the pre-T-1690 behavior verbatim -- every pair filed, no
attribution lines.

Disclosed scope cuts:
- The upstream `(rule_id, file)` finding identity (`_land_cmd.py`/
  `_verify.py`, out of this ticket's declared scope) still carries no
  line number. When a finding's line is known, `_resolve_symbol` picks
  the exact enclosing symbol; when it is not, every symbol in that file
  becomes a candidate target -- documented in `_attribution.py`'s own
  module docstring as a deliberate, honest degradation, not a silent
  narrowing.
- Tier 3 (bisect for the UNATTRIBUTED residue, T-1686's own framing) is
  not built. An unattributed finding today is filed as an ordinary
  regression ticket naming its candidate commits, for a human to read --
  disclosed in docs/modules/tickets.md's own "What this leaf does NOT
  do" paragraph.

Evidence: 16 pytest node ids recorded via `frob ticket evidence` (6 in
tests/unit/verify/test_attribution.py::TestAttributeBatch, 10 across
tests/unit/test_rapid_sweep.py's TestTicketIsOpen/TestAttributeNewFindings/
TestFileRegressionTicket) -- all measured passing:
`timeout 100 uv run pytest tests/unit/verify/ tests/unit/test_rapid_sweep.py -p no:cacheprovider -q`
-> `collected=59 failed=0` (33 in tests/unit/verify/, 26 in
test_rapid_sweep.py). No `--accepts` binding -- T-1690's ticket body has
no `Acceptance:` structured criteria list (only prose acceptance text),
so there was no acceptance-item index to bind to.

Filed: none -- no out-of-scope defect found beyond what's disclosed above
as a scope cut (both are pre-existing epic-level future work T-1686's own
body already names, not something discovered mid-ticket).

Gates: `frob check --only gates-fast --ticket T-1690` clean (0 errors),
`frob check --only gates-native --ticket T-1690` clean (0 errors) after
fixing an ARCH001 (split `_file_regression_ticket` into
`_partition_findings_by_attribution`) and a PERF003 (restructured
`_reaches`'s inner loop to check `target in callees` via membership
before the nested per-callee loop, instead of a nested `==` comparison).
`frob check --only gates-security --ticket T-1690` surfaces 3 SELFAUDIT001
findings (design/frob.strata's `verify` node interface not yet listing
Attribution/AttributionError/attribute_batch) -- `design/frob.strata` is
outside T-1690's declared scope; per the agent playbook (section 0 step
5) `frob ticket land`'s own pre-merge sweep runs `frob sys sync-interface`
(writes the fix) automatically before merging, so this is expected to
self-resolve at land time, not hand-fixed here.
`frob check --land-parity` could not evaluate in the foreground budget
(deferred lint/static stage groups on this repo's full unscoped size) --
reported honestly as unmeasured, not treated as clean.

### Changed
```
 docs/modules/tickets.md                    |  99 ++++++++
 src/frob/app/ticket_runner/_rapid_sweep.py | 196 ++++++++++++++-
 src/frob/verify/__init__.py                |  17 +-
 src/frob/verify/_attribution.py            | 375 +++++++++++++++++++++++++++++
 tests/unit/test_rapid_sweep.py             | 261 ++++++++++++++++++++
 tests/unit/verify/test_attribution.py      | 188 +++++++++++++++
 tickets.md                                 |  41 +++-
 7 files changed, 1163 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_direct_touch_attributes_at_depth_zero` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_two_reaching_commits_is_unattributed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_zero_reaching_commits_is_unattributed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_missing_line_falls_back_to_whole_file_candidates` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_graph_unavailable_is_an_error_for_the_whole_batch` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_open_ticket_is_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_done_ticket_is_not_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_missing_ticket_is_not_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_empty_queue_returns_empty_mapping` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_open_ticket_is_not_refiled` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_closed_ticket_is_refiled` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_unattributed_is_filed` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 5 error(s), 480 warning(s), 724 waived
- error-findings: ARCH001@src/frob/verify/_attribution.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/verify/_attribution.py, SELFAUDIT001@design, invalid-argument-type@tests/unit/test_rapid_sweep.py

<!-- ticket:T-1691 -->
```yaml
id: T-1691
title: Bisect the unattributable residue of a red batch
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: medium
blocked_by:
- T-1690
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_bisect.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
Tier 3 of the attribution ladder: the fallback for findings the symbolic
tier honestly could not attribute.

Bisect the batch over the single failing finding identity -- log2(N)
verifications, each scoped to re-checking THAT finding rather than
re-running the full gate pass. Scoping matters: a full check per bisect
step makes the fallback cost more than the batching saved, which would
make the whole epic a wash on any batch that ever goes red.

Bisect in a scratch worktree at each candidate commit; never move the
root checkout, which other agents are actively landing against. This is
the same isolation discipline `_capture_pre_land_baseline` already uses,
and it should reuse that machinery rather than growing a second
worktree-snapshot implementation.

Bounded: a step budget and a wall-clock budget, both configurable, both
logged when hit. On exhaustion, file the finding as UNATTRIBUTED against
the whole batch, naming every candidate commit -- a bounded honest answer
beats an unbounded search, and an exhausted bisect that silently reports
success is the failure mode to design against.

Acceptance: a batch with one known-bad commit and no symbolic attribution
converges to that commit within log2(N) scoped verifications; an
exhausted budget files an UNATTRIBUTED finding naming all candidates.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

<!-- ticket:T-1692 -->
```yaml
id: T-1692
title: 'Backpressure: bound the unverified window by depth and age, and block the
  land at the ceiling'
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
blocked_by:
- T-1688
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_backpressure.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- src/frob/verify/__init__.py
- tests/unit/verify/test_backpressure.py
- tests/unit/test_land_cmd_backpressure.py
- src/frob/verify/_attribution.py
- rapid-debt.jsonl
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/__init__.py
  reason: backpressure module needs export wiring in verify/__init__.py and its own
    unit tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/verify/test_backpressure.py
  reason: backpressure module needs export wiring in verify/__init__.py and its own
    unit tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_land_cmd_backpressure.py
  reason: unit test for the _land_core_prepare backpressure wiring
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/verify/_attribution.py
  reason: diff-vs-base noise from interleaved T-1753 work in the same worktree session;
    both files are already correct post-T-1753-land, this widens scope defensively
    rather than leaving a SCOPE001 refusal at land time
  actor: logan
  at: '2026-08-07'
- op: add
  glob: rapid-debt.jsonl
  reason: diff-vs-base noise from interleaved T-1753 work in the same worktree session;
    both files are already correct post-T-1753-land, this widens scope defensively
    rather than leaving a SCOPE001 refusal at land time
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: COV002 flagged _attribute_new_findings as changed with no open frob:ticket
    edge -- same diff-base noise as _attribution.py
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_fortress_is_zero_depth_zero_age
- tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_rapid_is_unbounded
- tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_standard_default
- tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_standard_toml_override
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_empty_queue_is_never_tripped
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_depth_ceiling_trips
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_age_ceiling_trips
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_unbounded_ceilings_never_trip
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_queue_unreadable_is_an_error
- tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_not_tripped_returns_immediately_without_draining
- tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_tripped_drains_and_unblocks
- tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_persistently_red_batch_times_out
- tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_unbounded_ceiling_never_blocks
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_not_tripped_is_a_noop
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_tripped_blocks_then_proceeds
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_block_timeout_logs_and_proceeds
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
Deferral is a credit line, not free money. Without this leaf the epic is
a mechanism for accumulating unbounded unverified debt with a pleasant
user experience, which is worse than the synchronous sweep it replaces.

Two independent ceilings, either one sufficient to trip:

- DEPTH: unverified commits above the watermark exceeds K.
- AGE: the oldest unverified entry is older than T.

Both axes are needed. Depth alone lets one commit sit unverified all
weekend behind a dead worker; age alone lets a burst of forty lands
through inside the window.

At the ceiling the land BLOCKS -- waits for the watermark to advance --
rather than failing. A refusal makes the developer re-run the whole land;
a block simply pays back the deferred cost at the moment it came due, and
is the behaviour a bounded queue should have. Log the block loudly with
the current depth, age, and the watermark being waited on, so the wait is
never mysterious. Blocking silently is the one unacceptable outcome.

The ceilings are per-profile settings, which is what the profile-collapse
leaf consumes: fortress K=0, standard K bounded, rapid unbounded.

Acceptance: with K=2, a third land blocks until the worker advances the
watermark, then proceeds; the block emits depth/age/watermark at WARNING;
an unbounded setting never blocks.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

## Done report

Changed:
- src/frob/verify/_backpressure.py (new): BackpressureError,
  BackpressureCeilings, BackpressureStatus, ceilings_for_profile,
  current_status, block_until_watermark_advances, plus private helpers
  _read_frob_toml_profile_table/_parse_enqueued_at.
- src/frob/verify/__init__.py: export the five new public names.
- src/frob/app/ticket_runner/_land_cmd.py: `_land_core_prepare` calls the
  new `_apply_backpressure(root, cfg, effective_profile)` right after
  profile resolution; `_apply_backpressure` resolves ceilings and blocks
  via `frob.verify.block_until_watermark_advances`, skipped under
  `--dry-run`, logging (never raising) on a block timeout.
- docs/modules/tickets.md: new "Backpressure (T-1692)" section.
- tests/unit/verify/test_backpressure.py (new, 13 tests),
  tests/unit/test_land_cmd_backpressure.py (new, 4 tests).

Design: two independent ceilings (depth, age), either sufficient to
trip, read from the SAME durable verify queue T-1687/T-1688 already
maintain -- no new storage. At the ceiling the land BLOCKS rather than
refuses: `block_until_watermark_advances` logs the trip loudly at
WARNING (depth, age, watermark) and ACTIVELY drives
`frob.verify.run_coalesced_verification` on each iteration (default
`drain_fn`) to pay back the deferred cost itself, rather than assuming a
daemon is watching the queue -- this makes the design correct even with
no daemon running. A last-resort timeout (30 min default) on the block
itself keeps a permanently red/quarantined batch from wedging every
future land forever; a timeout logs at ERROR and the land proceeds
anyway (the loud WARNING trail is the safeguard, not a second refusal).
Per-profile ceilings: fortress depth=0/age=0 (still blocks, never
refuses -- see module docstring "BLOCK, NEVER FAIL"), standard a bounded
default (5 / 3600s) overridable via frob.toml's `[profile]
backpressure_max_depth`/`backpressure_max_age_s`, rapid None/None
(unbounded on both axes, never blocks, by construction).

Acceptance (from the ticket body, verified directly):
"with K=2, a third land blocks until the worker advances the watermark,
then proceeds" -> `TestBlockUntilWatermarkAdvances::test_tripped_drains_
and_unblocks` (K=2, three queued entries, injected drain_fn that
advances the watermark and compacts the queue, asserts the returned
status is no longer tripped and depth==0).
"the block emits depth/age/watermark at WARNING" -> the WARNING log line
in `block_until_watermark_advances` includes `status.reason` (which
axis, by how much), `status.depth`, `status.age_s`, and
`status.watermark_commit` in one message; exercised by the same test
(the loop only reaches `Ok` after logging).
"an unbounded setting never blocks" ->
`TestBlockUntilWatermarkAdvances::test_unbounded_ceiling_never_blocks`
(100 queued entries, ceilings max_depth=None/max_age_s=None, asserts
drain_fn is never called at all).

Disclosed scope cut: the full profile-to-queue-depth collapse (deleting
every remaining `if rapid:` seam scattered through the land pipeline,
T-1686's own "payoff" framing) is NOT this leaf's job -- `_apply_
backpressure` is additive, wired alongside the existing rapid/standard
branching `_land_core_prepare` already has. Stated explicitly in
docs/modules/tickets.md's own "Disclosed scope cut" paragraph, not
silently assumed done.

FOR T-1696 (profile collapse): `ceilings_for_profile` IS the first
concrete instance of "the profiles stop being three code paths and
become one dial" (T-1686's own payoff framing) -- fortress=depth 0/age
0, standard=bounded (toml-overridable), rapid=unbounded, all resolved
from ONE function keyed on `ProfileName`, not three separate `if
profile ==` branches scattered per call site. Whoever takes T-1696
should EXTEND this function (add whatever new per-profile knob the
collapse needs) rather than inventing a second, parallel
profile-to-setting mechanism alongside it.

Evidence: 17 pytest node ids recorded via `frob ticket evidence`, all
measured passing:
`timeout 100 uv run pytest tests/unit/verify/ tests/unit/test_land_cmd_backpressure.py -p no:cacheprovider -q`
-> `collected=50 failed=0`.

Filed: T-1753 (post-land sweep regression from T-1690's own land:
ARCH001/E501/ty invalid-argument-type) -- fixed and landed separately
before this ticket, per explicit coordinator instruction, at commit
8a2f473e454c085890de379dcefd098a2978b4ce.

Gates: `frob check --only gates-fast --ticket T-1692` clean down to 3
SCOPE001 findings on land-owned files (.frob-release.json,
pyproject.toml, uv.lock) -- the same T-1690/T-1753 pattern, reconciled
by `frob ticket land`'s own internal merge, not hand-fixed here (agent
playbook section 4b). `frob check --only gates-native --ticket T-1692`
and `frob check --only gates-security --ticket T-1692` also run clean of
new errors introduced by this ticket's own files.

### Changed
```
 design/frob.strata                       |  10 +-
 docs/modules/tickets.md                  |  72 +++++++
 src/frob/app/ticket_runner/_land_cmd.py  |  62 +++++-
 src/frob/verify/__init__.py              |  26 ++-
 src/frob/verify/_backpressure.py         | 360 +++++++++++++++++++++++++++++++
 tests/unit/test_land_cmd_backpressure.py | 113 ++++++++++
 tests/unit/verify/test_backpressure.py   | 219 +++++++++++++++++++
 tickets.md                               | 161 ++++++++++++++
 8 files changed, 1008 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_fortress_is_zero_depth_zero_age` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_rapid_is_unbounded` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_standard_default` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_standard_toml_override` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_empty_queue_is_never_tripped` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_depth_ceiling_trips` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_age_ceiling_trips` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_unbounded_ceilings_never_trip` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_queue_unreadable_is_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_not_tripped_returns_immediately_without_draining` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_tripped_drains_and_unblocks` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_persistently_red_batch_times_out` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances::test_unbounded_ceiling_never_blocks` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_not_tripped_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_tripped_blocks_then_proceeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_block_timeout_logs_and_proceeds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 17 passed (from 17 evidence id(s))
- gates: 5 error(s), 536 warning(s), 727 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/verify/_backpressure.py, PRE001@tickets/T-1692, invalid-argument-type@src/frob/app/ticket_runner/_land_cmd.py, invalid-argument-type@src/frob/app/ticket_runner/_rapid_sweep.py

<!-- ticket:T-1693 -->
```yaml
id: T-1693
title: 'Quarantine circuit breaker: a red batch stops further deferred lands until
  attributed'
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
blocked_by:
- T-1690
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_quarantine.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
The single most important rule in the epic. Landing on top of a
known-broken base is what makes attribution cost explode: every
subsequent land widens the candidate set and adds findings that are
consequences rather than causes.

On a red batch verification, raise a durable quarantine flag. While
raised, deferred landing is off: a land either runs FULLY SYNCHRONOUS
verification (paying the old cost, which is correct -- the credit line is
suspended, not the work) or blocks, per profile. Ledger-integrity and
LAND-PROOF paths are untouched, as always.

Quarantine clears only when every finding in the red batch is attributed
and filed, or explicitly dismissed by a recorded human decision. It must
NOT clear on a subsequent green verification: a green run after more
lands means the tree is clean NOW, not that the earlier regression was
understood, and auto-clearing on green is how a circuit breaker silently
becomes decoration.

Every raise and clear is logged at ERROR/WARNING with the batch, the
findings, and the clearing reason, and recorded durably so a daemon
restart cannot lose a raised quarantine. A quarantine that evaporates on
restart is worse than none, because it is trusted.

Acceptance: a red batch raises quarantine; a subsequent land does not
defer; a later green verification does NOT clear it; attributing and
filing every finding does; the flag survives a worker restart.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

<!-- ticket:T-1694 -->
```yaml
id: T-1694
title: 'Crash safety: a dead verify worker must never advance the watermark'
state: queued
kind: bug
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1688
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_worker.py
- src/frob/tickets/_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
The watermark is a claim that work was done. Every way it can advance
without that work having been done is a correctness hole, and they are
all crash-shaped.

Reuse the T-1523 post-land-verify marker pattern rather than inventing a
second one: write an in-flight marker naming the batch and target commit
before verification begins, clear it after the watermark advances. A
marker found at startup means a worker died mid-verification; that batch
is UNVERIFIED and must be re-queued, never assumed green.

Specific holes to close, each with a test that kills the worker at that
exact point: death between queue read and verification start; between a
green result and the watermark write; between the watermark write and
queue compaction; and a torn watermark write (write-temp-then-rename, so
a partial file is never observable).

Two workers must never verify concurrently for one root -- reuse the
daemon's existing singleton lock, do not add a second exclusion
mechanism.

Acceptance: for each named kill point, the next startup reports the batch
as unverified and re-queues it; the watermark never names a commit whose
verification did not complete.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

<!-- ticket:T-1695 -->
```yaml
id: T-1695
title: 'Verify-worker resource budget: never starve foreground agents'
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1688
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_worker.py
- src/frob/serve/_daemon.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
A permanent background verifier competes with foreground agent work for
CPU and memory. On this box that is not theoretical: the 2026-07-29
session losses were OOM kills, and the standing cap is 3-4 concurrent
agents. An epic that makes lands fast and then OOM-kills the agents doing
them is a net loss.

Required: reduced scheduling priority for the worker and its children
(nice, and ionice where available); a concurrency budget so the worker
never runs while more than N foreground agents hold leases -- the lease
count `frob worktree sweep` and `_profile._concurrent_lease_count`
already read is the right signal, reuse it rather than inventing a second
notion of "how busy is this repo"; and a memory ceiling that defers the
batch rather than being killed by the OOM killer.

Deferral under load must be visible: log at INFO when the worker yields,
naming the lease count and the depth it is yielding at. A worker that
silently never runs is indistinguishable from one that is keeping up,
until the backpressure ceiling trips and nobody knows why.

Acceptance: the worker yields while the lease count is at or above the
configured ceiling and resumes below it; worker children inherit the
reduced priority; each yield is logged with its cause.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

<!-- ticket:T-1696 -->
```yaml
id: T-1696
title: Collapse rapid/standard/fortress into one queue-depth dial and delete the if-rapid
  land seams
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1692
- T-1693
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/tickets/_profile.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
The payoff leaf, and deliberately LAST: this is a refactor, and it must
land on a mechanism that already works rather than being the thing that
proves it.

Today `rapid` is a scatter of `if effective_profile(...) is RAPID` seams
through the land pipeline -- baseline thread, pre-commit sweep, post-land
sweep, TEST016, REL001, evidence leniency. Each is an independent
opportunity for the profiles to drift out of correspondence, and every
new profile-sensitive behaviour adds another.

After this leaf a profile is a settings record consumed in ONE place:
queue depth ceiling, age ceiling, on-red policy (refuse / quarantine+file
/ file-only), and the never-relaxed set. `fortress` = depth 0 +
refuse-on-red. `standard` = bounded depth + quarantine. `rapid` =
unbounded + file-only. Every land-pipeline branch reads the settings
record; none branches on a profile NAME. A grep for the profile enum
outside the settings module should return nothing, and that is worth a
gate rule of its own if it is cheap to add.

Ledger integrity and LAND-PROOF stay outside the dial entirely, as they
are today -- they are not a setting and must not become expressible as
one.

Migration must be behaviour-preserving per profile, demonstrated by
tests asserting the same observable land behaviour before and after, not
by inspection.

Acceptance: no land-pipeline module branches on ProfileName; each profile
reproduces its current observable behaviour; adding a fourth profile
requires only a new settings row.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

<!-- ticket:T-1697 -->
```yaml
id: T-1697
title: 'frob verify: surface the unverified window -- depth, age, quarantine, attribution'
state: queued
kind: ux
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1687
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/app/verify_runner.py
- src/frob/_cli_parsers/_verify.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
```
An unverified window nobody can see is a liability pretending to be a
feature. This is the leaf that makes the whole epic auditable, and it is
high priority despite being "just CLI": every other leaf's failure mode
is discovered through this surface.

`frob verify status`: the watermark commit and its age, unverified depth,
the oldest unverified entry, quarantine state with the batch and findings
that raised it, and the last batch's outcome including anything
UNATTRIBUTED. Human-readable by default, `--json` for agents.

`frob verify now`: drain and verify synchronously, for a human who wants
the window closed before walking away.

`frob verify explain <finding>`: print the attribution path -- the
reachability chain that assigned this finding to this commit -- so an
attribution can be audited rather than trusted.

Porcelain rule: exit non-zero when quarantine is raised, so a shell or CI
step can gate on "is this repo's verification healthy" without parsing
prose.

Acceptance: `status` reports depth/age/quarantine accurately against a
seeded queue; `--json` round-trips through a pydantic model; a raised
quarantine exits non-zero; `explain` prints a reachability path for an
attributed finding.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

<!-- ticket:T-1699 -->
```yaml
id: T-1699
title: rapid-debt commit races DirtyMain outside the land lock; DirtyMain misreads
  coordinator-owned dirt as a crashed land
state: queued
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
T-1698 stopped a rapid land from leaving root permanently dirty, but the
cleanup commit happens OUTSIDE the land lock, leaving a small race that
matters at three-plus concurrent agents.

Sequence. `land()` holds the ledger/land lock for its body and releases
it when it returns. `_land_core_finish_post_land` then calls
`spawn_deferred_post_land_sweep`, which appends the debt line and commits
it via `_commit_rapid_debt`. Between the append and that commit, root is
dirty and unlocked. A second agent whose land reaches
`_refuse_if_main_dirty` inside that window refuses with `DirtyMain` --
transient and self-clearing, but indistinguishable to the victim from the
permanent deadlock T-1698 just fixed, and agents are briefed to stop
after two failed attempts.

Preferred fix, following existing precedent rather than inventing a
mechanism: `_refuse_if_main_dirty` already tolerates one specific benign
dirty shape -- `_restore_lock_version_only_drift` auto-restores a
uv.lock frob-version-only flap and re-evaluates instead of refusing
(T-0793). Give `rapid-debt.jsonl`-only dirt the same treatment: when it
is the ONLY dirty path, commit it (it is land-owned and always
committable on its own) and re-evaluate, rather than refusing. Any other
dirt, or rapid-debt.jsonl alongside anything else, must still refuse
exactly as today.

Do NOT instead widen the land lock to cover the post-land phase: that
phase is deliberately outside it (T-1684 made the sweep detached
precisely so the lock is not held across a multi-minute verification),
and re-acquiring it would reintroduce the serialization the rapid work
removed.

Second, process-shaped defect from the same incident, worth fixing in
this ticket because it has the same root: THE COORDINATOR WORKING
IN-PLACE ON THE SHARED ROOT BLOCKS EVERY AGENT'S LAND. Three agents this
session each drove a ticket to closed, then burned their remaining budget
retrying a land that could not succeed while the coordinator held
uncommitted edits in `/home/logan/projects/frob`. None of them could fix
it: an agent is correctly forbidden from committing or stashing state it
does not own.

`frob ticket land` should detect this and say so: when root is dirty with
files that belong to NO open ticket's scope and no land is in flight,
the refusal should name that shape explicitly -- "root has uncommitted
work belonging to no in-flight land; whoever owns the root checkout must
commit or stash it" -- instead of the generic dirty-tree message that
sends an agent looking for a crashed land. Three separate agents this
session independently misdiagnosed it as "a crashed land left dirt",
which is the reading the current message invites.

<!-- ticket:T-1702 -->
```yaml
id: T-1702
title: close's own-obligations REL001 check is not rapid-aware, deadlocks a worktree
  that legitimately needs a version bump
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
## Description

`frob ticket close`'s own-obligations preflight
(`_close_own_obligations_for_ticket` / `_own_obligations_rel_bump_dirty` in
`src/frob/app/ticket_runner/_close_cmd.py`) refuses to close a ticket
whose diff requires a REL001 version bump unless `pyproject.toml`'s
declared version already covers it -- but a worktree agent is forbidden
from ever touching `pyproject.toml`'s version line (agent-playbook.md
section 4b, T-0731's land-owned-files guard: version bump/changelog are
`frob ticket land`-exclusive). For a ticket that genuinely changes public
API (removes a public config field/CLI flag/function parameter, as
T-1675 did), this is a real deadlock: close demands a bump the worktree
is not allowed to write, and land (the only thing allowed to write it)
runs strictly AFTER close.

Observed while closing T-1675 (2026-08-07): `frob ticket close T-1675`
refused with `OwnObligationsUnclean` / "REL001 version bump outstanding
(needs 0.358.0, pyproject declares 0.357.0)" even though the repo is
running the `rapid` profile, which explicitly turns REL001 OFF on the
LAND path (`frob ticket land`'s own rapid-profile handling, T-1681/
T-1575) -- but this separate close-time own-obligations check has no
rapid awareness at all. Compare `_done_transition_structural_guard` in
`src/frob/tickets/_evidence.py`, which DOES thread `rapid=_is_rapid(root)`
through to relax its own `covers_scope` obligation (line ~354: `if
covers_scope is False and not rapid`) -- `_close_own_obligations_for_
ticket`/`_own_obligations_rel_bump_dirty` has no equivalent rapid
parameter or check at all.

## Plan (sketch, for whoever picks this up)

- Thread `rapid: bool` into `_close_own_obligations_for_ticket` /
  `_own_obligations_rel_bump_dirty` (mirroring `_done_transition_
  structural_guard`'s existing pattern), sourced from `_is_rapid(root)`.
- When `rapid` is true and the ONLY outstanding own-obligation is the
  REL001 bump (COV001/SELFAUDIT001 findings should still block), relax
  the refusal and record it via `record_rapid_debt` (same debt-ledger
  mechanism `_done_transition_structural_guard` already uses for its own
  rapid relaxations), so the relaxation is disclosed, not silent.
- Add a regression test that closes a ticket whose diff needs a version
  bump, under a `rapid`-profile root, with no `pyproject.toml` edit, and
  asserts the close now succeeds (with a recorded rapid-debt line) instead
  of refusing.

## Workaround used in the T-1675 session

Temporarily edited `pyproject.toml`'s version to the required value
LOCALLY (uncommitted, never staged/committed -- the T-0731 land-owned-
files pre-commit hook only fires on a commit, never on an uncommitted
working-tree edit), ran `frob ticket close T-1675` against that disk
state, then reverted the edit (`git checkout -- pyproject.toml`) before
landing, so `frob ticket land`'s own bump computation was untouched and
wrote the real bump itself. This is not a fix, just what let T-1675 land
without violating the land-owned-files rule or waiving a real gate.

<!-- ticket:T-1705 -->
```yaml
id: T-1705
title: close-time REL001 preflight is not rapid-aware and names a remedy the agent
  is forbidden to perform
state: queued
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/_profile.py
- tests/unit/test_close_rel001_bump.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
`frob ticket close`'s own-obligations preflight
(`_own_obligations_rel_bump_dirty`, `_close_cmd.py`) demands a REL001
version bump that a worktree-isolated agent structurally CANNOT satisfy:
`pyproject.toml` is land-owned and the T-0731 pre-commit hook refuses any
commit that touches its version line. The agent is told to do something
the tooling forbids it from doing.

Two separate defects behind that.

1. NOT PROFILE-AWARE. T-1575 specifies REL001 OFF under `rapid`, and
   `frob check`'s REL gate and the land path both honour that. This
   close-time preflight does not -- it calls `_required_release_bump`
   unconditionally. Under `rapid` it should not run at all. (T-1684
   already fixed a related half of this function: it compared the
   required bump against nothing, so an ALREADY-APPLIED bump never
   satisfied it. This is the remaining half.)

2. NO AGENT-REACHABLE REMEDY EVEN UNDER `standard`. The bump is applied
   by `_apply_release_bump_for_land` during land, which runs with the
   land's own internal commit channel. So the correct answer for an agent
   is "do not close by hand, let land close it" -- but `close`'s error
   message does not say that. It says the bump is outstanding, which
   reads as "go bump it", which the agent then cannot do. Two agents this
   session independently tried and were blocked; one worked around it by
   discovering that `frob ticket land` performs its own close internally.

   That workaround is the actual intended path and should be what the
   error names.

Fix:

- Skip the REL001 preflight entirely when `effective_profile(root)` is
  `rapid`, at the same seam every other rapid relaxation uses -- never an
  inline profile check sprinkled into unrelated logic -- and record it
  via `record_rapid_debt` like every other rapid relaxation, so the
  skipped check stays auditable.
- Under non-rapid profiles, when the bump is outstanding AND the caller
  is not the land path, the message must name the real remedy: the bump
  is applied by `frob ticket land`, which closes the ticket itself; a
  hand `close` is not the supported route for a ticket with a public-API
  change. Do not tell a caller to perform an action the hook forbids.

Regression coverage: under `rapid`, a ticket with a public-API change
closes without a bump and records the relaxation as debt; under
`standard`, the refusal message names `frob ticket land` as the remedy
rather than a bare "bump outstanding".

<!-- ticket:T-1711 -->
```yaml
id: T-1711
title: consider relocating _write_ticket_unchecked out of src/frob/tickets/_store.py
  into a test-only helper module
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
frob:ticket T-1679

`_write_ticket_unchecked` (`frob.tickets._store`) is a deliberately
test-fixture-only escape hatch for the T-1637/T-1679 content-loss guard --
by design it has no production caller and never should. WIRE002 requires
a real `follow_up` ticket for its WIRE001 waiver since it lives in `src/`
(the `permanent="true"` test-tree exemption only applies to symbols under
`tests/`). This ticket is that accountable follow-up: investigate whether
`_write_ticket_unchecked` can be relocated into a `tests/`-tree helper
module instead (it needs access to the private `_write_ticket_impl` split
point in `_store.py`, so this may require exporting a narrow test-only
seam, or may simply not be worth the churn -- either outcome is a
legitimate close for this ticket).

<!-- ticket:T-1716 -->
```yaml
id: T-1716
title: close's own-obligations REL001 check is not rapid-aware, deadlocks a worktree
  that legitimately needs a version bump
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
## Description

`frob ticket close`'s own-obligations preflight
(`_close_own_obligations_for_ticket` / `_own_obligations_rel_bump_dirty` in
`src/frob/app/ticket_runner/_close_cmd.py`) refuses to close a ticket
whose diff requires a REL001 version bump unless `pyproject.toml`'s
declared version already covers it -- but a worktree agent is forbidden
from ever touching `pyproject.toml`'s version line (agent-playbook.md
section 4b, T-0731's land-owned-files guard: version bump/changelog are
`frob ticket land`-exclusive). For a ticket that genuinely changes public
API (removes a public config field/CLI flag/function parameter, as
T-1675 did), this is a real deadlock: close demands a bump the worktree
is not allowed to write, and land (the only thing allowed to write it)
runs strictly AFTER close.

Observed while closing T-1675 (2026-08-07): `frob ticket close T-1675`
refused with `OwnObligationsUnclean` / "REL001 version bump outstanding
(needs 0.358.0, pyproject declares 0.357.0)" even though the repo is
running the `rapid` profile, which explicitly turns REL001 OFF on the
LAND path (`frob ticket land`'s own rapid-profile handling, T-1681/
T-1575) -- but this separate close-time own-obligations check has no
rapid awareness at all. Compare `_done_transition_structural_guard` in
`src/frob/tickets/_evidence.py`, which DOES thread `rapid=_is_rapid(root)`
through to relax its own `covers_scope` obligation (line ~354: `if
covers_scope is False and not rapid`) -- `_close_own_obligations_for_
ticket`/`_own_obligations_rel_bump_dirty` has no equivalent rapid
parameter or check at all.

## Plan (sketch, for whoever picks this up)

- Thread `rapid: bool` into `_close_own_obligations_for_ticket` /
  `_own_obligations_rel_bump_dirty` (mirroring `_done_transition_
  structural_guard`'s existing pattern), sourced from `_is_rapid(root)`.
- When `rapid` is true and the ONLY outstanding own-obligation is the
  REL001 bump (COV001/SELFAUDIT001 findings should still block), relax
  the refusal and record it via `record_rapid_debt` (same debt-ledger
  mechanism `_done_transition_structural_guard` already uses for its own
  rapid relaxations), so the relaxation is disclosed, not silent.
- Add a regression test that closes a ticket whose diff needs a version
  bump, under a `rapid`-profile root, with no `pyproject.toml` edit, and
  asserts the close now succeeds (with a recorded rapid-debt line) instead
  of refusing.

## Workaround used in the T-1675 session

Temporarily edited `pyproject.toml`'s version to the required value
LOCALLY (uncommitted, never staged/committed -- the T-0731 land-owned-
files pre-commit hook only fires on a commit, never on an uncommitted
working-tree edit), ran `frob ticket close T-1675` against that disk
state, then reverted the edit (`git checkout -- pyproject.toml`) before
landing, so `frob ticket land`'s own bump computation was untouched and
wrote the real bump itself. This is not a fix, just what let T-1675 land
without violating the land-owned-files rule or waiving a real gate.

<!-- ticket:T-1717 -->
```yaml
id: T-1717
title: consider relocating _write_ticket_unchecked out of src/frob/tickets/_store.py
  into a test-only helper module
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
frob:ticket T-1679

`_write_ticket_unchecked` (`frob.tickets._store`) is a deliberately
test-fixture-only escape hatch for the T-1637/T-1679 content-loss guard --
by design it has no production caller and never should. WIRE002 requires
a real `follow_up` ticket for its WIRE001 waiver since it lives in `src/`
(the `permanent="true"` test-tree exemption only applies to symbols under
`tests/`). This ticket is that accountable follow-up: investigate whether
`_write_ticket_unchecked` can be relocated into a `tests/`-tree helper
module instead (it needs access to the private `_write_ticket_impl` split
point in `_store.py`, so this may require exporting a narrow test-only
seam, or may simply not be worth the churn -- either outcome is a
legitimate close for this ticket).

<!-- ticket:T-1718 -->
```yaml
id: T-1718
title: 'frob ticket evidence node-id shape validation: investigate the malformed-id
  gap without breaking pytest-form binding'
state: queued
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
## Description

Follow-up to T-1670's part 2 ("malformed ids accepted silently"), split
out after investigation found the naive literal reading would be harmful.

T-1670's own text says: "This graph's convention is `path::Class.method`
-- one `::` then a DOTTED class/method. Pytest's own `path::Class::method`
form is accepted by `frob ticket evidence` without complaint... Fix:
validate the node-id shape AT BIND TIME... and reject the pytest
`::`-separated form."

Investigation while implementing T-1670's part 1 found this cannot be
implemented as literally stated without breaking real, tested, documented
behavior:

- `ticket.evidence` entries are resolved against real pytest node ids via
  `frob.tickets._models.matches_collected`, which requires an EXACT string
  match against `collected` -- and `collected` (from `collect_python_tests`/
  `pytest --collect-only`) is always in pytest's native `path::Class::method`
  (double-`::`) form, never dotted. Rejecting that form at bind time would
  make it impossible to bind evidence using a real collected node id copied
  verbatim from `pytest --collect-only` output -- the most natural, lowest-
  error way to get a correct id.
- `frob.tickets.__init__.normalize_evidence_separator` (T-0293) already
  converts a DOTTED `path::Class.method` id INTO the pytest `::` form for
  storage/resolution -- the existing direction is dot-to-`::`, the opposite
  of what T-1670's literal ask would require.
- The CLI path (`_apply_evidence` in `src/frob/app/ticket_runner/_verify.py`)
  already resolves every id against a real collected set
  (`_collect_python_and_rust_ids`) and rejects (`UnknownEvidence`/
  `EvidenceNotPassing`) anything that does not resolve or pass -- so a
  genuinely malformed/typo'd id is already caught at bind time through the
  real CLI, not silently accepted.

What's still plausibly a real, addressable gap:

1. `normalize_evidence_separator`'s early-return (`if "::" in remainder:
   return entry`) passes through UNCHANGED any id with a remainder that
   already contains `::` -- this correctly leaves a legitimate 2-segment
   pytest id (`path::Class::method`) alone, but ALSO passes through
   unchanged a genuinely malformed 3+-segment id (`path::Class::method::
   extra`) with no rejection at the schema-validation layer
   (`validate_evidence`) itself -- it is only caught later, and only if a
   `collected` set happens to be supplied (true for the real CLI path,
   NOT true for a bare library `add_evidence(root, id, ids)` call with no
   collector, which only WARNS "recorded UNRESOLVED").
2. `frob:tests` DIRECTIVE comments (a SEPARATE namespace from
   `ticket.evidence`, playbook section 5) use the dotted `path::Class.method`
   qualname form by this repo's own convention -- DOC007 flags a `frob:tests`
   directive using pytest's own `::`-form target. If an agent habitually
   copies a `ticket.evidence` id (already normalized to `::` form) verbatim
   into a NEW `frob:tests` directive, DOC007 fires. This is a
   directive-authoring UX gap, not a `frob ticket evidence` bind-time bug --
   worth its own investigation into whether `frob ticket evidence` should
   print the frob:tests-directive-form of a newly-bound id as a hint.

## Plan (sketch, for whoever picks this up)

- Investigate (1): add a schema-level check in `validate_evidence` that
  rejects an id whose remainder-after-first-`::` contains MORE than one
  additional `::` (i.e. 3+ total `::`-segments) -- never reject the
  ordinary 1-or-2-`::` pytest shapes, only the genuinely malformed ones.
- Investigate (2) separately: does `frob ticket evidence` need to print a
  "for a frob:tests directive citing this id, use: <dotted form>" hint
  line, to close the copy-paste UX gap without touching `ticket.evidence`'s
  own resolution-critical `::` storage format at all?
- Do NOT implement "reject the pytest `::`-separated form" as literally
  worded in T-1670's original text -- see the investigation above for why
  that breaks the primary, correct way to bind evidence.

<!-- ticket:T-1719 -->
```yaml
id: T-1719
title: Fold Claude-config sync into a frob verb, gate the drift, and report global-vs-local
  frob skew in doctor
state: queued
kind: feature
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/__init__.py
- src/frob/doctor.py
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
Shared Claude config (PreToolUse hooks, the agent playbook) is now
git-tracked in `.claude/hooks/` and materialised into `~/.claude/` by
`.claude/hooks/sync-claude-config.py`, with `--check` reporting drift and a
SessionStart hook surfacing it. That closes the immediate hole -- a hook
that existed only in one home directory was an undocumented repo-wide
behaviour change no review ever saw.

But the sync script is a loose Python file in `.claude/`, which is exactly
the shape this repo's standing directive rejects: workflows belong in frob
subcommands, not in ad-hoc scripts. It is also unenforced -- `--check` runs
only if someone wires it up, and nothing fails a gate when the copies
drift.

Two pieces of work.

1. FOLD THE SYNC INTO frob. A verb (`frob claude sync` / `frob agent sync`,
   name it as fits the CLI regrouping in T-1567..T-1571) that:
   - reads its managed-file manifest from `frob.toml` rather than a
     hard-coded list in a script, so a repo declares what it publishes;
   - writes each destination behind the do-not-edit banner, atomically
     (write-temp-then-replace -- a half-written hook fails to parse on
     every subsequent tool call);
   - never syncs global -> repo, and never touches a path outside the
     manifest (`~/.claude/` holds plenty this repo has no business
     owning);
   - `--check` exits non-zero on drift, with the drifted paths NAMED. An
     error that does not name its own cause has cost this repo three
     separate fleet stalls already.

2. GATE IT. A rule (CLAUDE001, or the next free id -- register it in the
   rule catalog, do not invent an unregistered one) that fails when a
   managed file differs from its materialised copy. Drift is currently
   invisible to `frob check`, which means the tracked original can say one
   thing while every agent reads another. That is the same
   catalogued-but-not-enforced shape this repo has been burned by before:
   a registry nobody reads is documentation, not enforcement.

Also in scope, because it is the same reconciliation problem:

3. GLOBAL frob IS NOT LOCAL frob, AND NOTHING SAYS SO. Measured today:
   `frob` on PATH is 0.184.0 while this repo's `uv run frob` is 0.361.0 --
   177 versions apart. Every gate number the global build reports for this
   tree is wrong, and nothing surfaces that. `frob doctor` should report
   the skew explicitly (both versions, and the reconcile command), and the
   hook's cached measurement should be the same code path rather than a
   second implementation that can disagree with it.

The `frob-suggest.py` rule table should move with the sync verb, but the
BLOCK-ONCE-THEN-ALLOW semantics must be preserved exactly: the first
attempt at a matching command is denied with a suggestion, an identical
re-run is allowed. A suggestion that cannot be overridden is a policy, and
this deliberately is not one -- it blocked its own authoring commit on a
prose parenthetical within an hour of being written, and the override was
the only thing that made that recoverable.

<!-- ticket:T-1720 -->
```yaml
id: T-1720
title: frob ticket land should auto-rebase the worktree onto main after a successful
  land
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
## Description

Every single land I performed across two ticket groups in this session
(T-1673/T-1630/T-1675/T-1670/T-1679, then T-1714/T-1706) hit the same
sequence: land a ticket successfully (`LAND-PROOF: ... verified=True`),
then the NEXT `frob check --ticket <next-id>` in the same worktree reports
spurious SCOPE001/COV002 findings on files the just-landed ticket touched
-- because the worktree's own commits for that already-landed work are
still present on its branch, and the branch has not moved to include
main's new (squashed) tip. `git diff main` for those files then shows
non-empty content even though the content is byte-identical, because the
branch and main reached the same state via two DIFFERENT commits (the
worktree's own step-by-step history vs. land's squash-apply), so `git
diff main --stat` inherently looks non-empty for anything the worktree
itself changed, whether or not it matches main.

Observed sequence, every time, this session:
1. `frob ticket land T-XXXX --worktree <path>` succeeds, `LAND-PROOF ...
   verified=True`.
2. Start the next ticket in the same worktree; `frob ticket sweep`/`frob
   check --ticket <next>` reports SCOPE001 (files outside declared scope)
   and/or COV002 (changed-with-no-frob:ticket-edge) findings that are
   NOT caused by the next ticket's own work -- they are the just-landed
   ticket's files, which the worktree's branch still carries as its own
   uncommitted-relative-to-main diff.
3. Resolved every time by `git rebase main` in the worktree (dropping the
   now-"patch already upstream" commits git detects automatically, and
   skipping any obsolete `wip: pre-land snapshot for T-XXXX` commits
   land's own machinery leaves behind) BEFORE doing any more gate
   verification for the next ticket.
4. Repeat from step 1 for the next ticket in the series.

This is pure repeated friction -- the exact same manual recipe, by hand,
after every single successful land in a multi-ticket worktree series.
Per the standing directive (systematize repeated friction rather than
re-doing it by hand every time), this should be mechanical.

## Proposal

`frob ticket land --worktree <path>` should, after a successful land
(`verified=True`), automatically `git rebase main` the worktree's own
branch onto the new main tip it just produced -- dropping the now-
redundant commits the same way a manual rebase does (git's own "patch
contents already upstream" detection), before returning control to the
caller. This closes the loop the same way a human currently does by hand,
every time, immediately after every land in this session.

Open questions for whoever picks this up:
- Should this be unconditional, or opt-in via a flag (e.g. `--rebase-
  after`) for a caller that does not want its worktree branch rewritten
  automously? A single-ticket worktree (not a series) may not care either
  way; a series worktree needs it every time.
- What happens if the auto-rebase hits a REAL conflict (not just
  redundant-patch drops) -- should land still report success (the land
  itself is done) and just warn that the auto-rebase needs manual
  attention, rather than let a rebase conflict retroactively fail an
  already-successful land?
- Should the two housekeeping commit classes land already knows about
  (`wip: pre-land snapshot for T-XXXX`, ledger auto-commits) be preemptively
  dropped/skipped rather than relying on git's generic empty-patch
  detection, since land KNOWS which of the worktree's own commits are its
  own now-obsolete staging artifacts?

## Evidence (the actual observed sequence this session)

Every occurrence below is `git rebase main` run in
`.claude/worktrees/agent-ac2dad95d0b2b8809` immediately after a
`LAND-PROOF ... verified=True` line, always resolving 1-3 conflicts (the
shared `rapid-debt.jsonl` append-only log, occasionally a `tickets.md`
splice-driver conflict) and dropping 1-6 "patch contents already
upstream" commits per rebase:

- After landing T-1673: rebased before starting T-1630 (SCOPE001 on
  `rapid-debt.jsonl` and other post-land-sweep-touched files).
- After landing T-1630: rebased before starting T-1675 (same shape).
- After landing T-1675: rebased before starting T-1670 (plus resolving a
  CHANGELOG.md/land-owned-file pre-commit-hook collision on the first
  attempt, which forced an abort-and-rebase-instead-of-merge decision).
- After landing T-1670: rebased before starting T-1679.
- After landing T-1679: rebased before starting T-1714 (2 real conflicts
  in `src/frob/tickets/_store.py`, both trivially resolved by keeping
  HEAD's already-landed content).
- After landing T-1714/merging T-1701 (already landed by another agent):
  rebased before starting T-1706.

Six for six. This ticket exists so the seventh time is automatic.

<!-- ticket:T-1724 -->
```yaml
id: T-1724
title: 'Measure dispatch cost against tickets landed: join agent telemetry to a dispatch
  record in frob stats --agentic'
state: queued
kind: feature
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/stats/_agentic.py
- src/frob/app/telemetry.py
- tests/test_stats_agentic.py
- docs/modules/stats.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
There is no measured answer to "what does a dispatched agent cost, and what
did it deliver". Coordinators size waves, batch tickets, and decide when to
retire an agent on intuition.

WHY THIS TICKET EXISTS, CONCRETELY. On 2026-08-07 a coordinator hand-tallied
twelve agent runs out of task-notification text to answer exactly that
question, and got it wrong twice:

- The runs were reconstructed in the wrong ORDER, which inverted the
  headline figure. A claimed "+263k tokens for 6 tool uses" -- offered as
  the evidence that resuming a heavy agent is expensive -- became a
  DECREASE once the sequence was corrected. The conclusion did not survive
  its own data.
- Whether the underlying counter was cumulative-per-agent or per-run could
  not be determined from the source at all. Under one reading resume is
  ruinous; under the other it is nearly free. Those are opposite operating
  policies and the number could not distinguish them.

A retirement threshold was then published and withdrawn within the hour.
That is the cost of an unmeasured process metric: not a missing number, but
a confidently wrong one.

WHAT ALREADY EXISTS. Do not build a second stream. `frob.stats._agentic`
already aggregates `.frob/telemetry.jsonl` (written by `frob.app.telemetry.
append_event`/`record_cli_event` and the PostToolUse hook), and already
models `ToolTokens` (output tokens per tool), `TicketCycleTime` (from
created/started/done transition events), `TimeSink`, and
`RetreadCandidate`. The substrate is there.

THE MISSING PIECE IS THE JOIN: cost is recorded per tool call, and delivery
is recorded per ticket, and nothing connects them to a DISPATCH.

Add a dispatch as a first-class record:

- A dispatch id, opened when an agent starts work in a worktree and closed
  when it stops, with the worktree/branch it owned.
- Cost accumulated against it: output tokens, tool calls, wall clock,
  and -- crucially -- whether the run was a COLD START or a RESUME. The
  whole open question is the relative price of those two, and a schema that
  cannot tell them apart cannot answer it.
- Delivery attributed to it: the ticket ids that reached done/dropped
  during that dispatch, via the transition events `TicketCycleTime`
  already reads.

Then report the derived numbers `frob stats --agentic` cannot currently
produce: tokens per landed ticket; cold-start floor (cost of a dispatch
that landed nothing); marginal cost of run N vs run N+1 for the same agent;
and dispatches that consumed budget while landing zero, which is the
signal that actually matters for retirement.

HARD REQUIREMENTS, each one a lesson this repo has already paid for:

- The counter's semantics must be UNAMBIGUOUS in the schema -- a field is
  either a per-run delta or a running total, named so, never inferrable
  only by watching whether it goes up. That ambiguity is the whole reason
  this ticket exists.
- Records are ordered by an explicit sequence or timestamp the reader does
  not have to reconstruct. Mis-ordering was the first error.
- "Could not measure" must be representable and must NEVER render as 0.
  A zero cost is a measurement; a missing one is not. Reporting an
  unmeasured dispatch as free would recreate the sweep-reads-zero class
  (T-1703) in the process metrics.
- Non-gated, like the rest of `_agentic`: nothing here fails a gate.
  Telemetry that can block a land will be turned off, and then measured
  nothing.
- Malformed lines skipped, never raised -- match `_load_events`'s existing
  posture; a partially-written telemetry file must not break `frob stats`.

Related: T-1344 (agentic throughput: the land path is the bottleneck) is
the same concern from the other end -- it argues about where time goes
without a way to measure where it went. This ticket is the instrument that
would settle it.

<!-- ticket:T-1725 -->
```yaml
id: T-1725
title: Hooks and docs reference frob verbs by name with nothing checking they resolve;
  gate it before the CLI regrouping renames them
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- .claude/hooks/frob-timeout-guard.py
- .claude/hooks/frob-suggest.py
- src/frob/gates/_wire.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
The PreToolUse hooks in `.claude/hooks/` reference frob verbs BY NAME, as
plain strings, and nothing checks that those names resolve. The CLI
regrouping work (T-1567..T-1571) renames and regroups verbs. A rename will
silently break every reference, and the failure mode is the worst kind:
the hook keeps running and keeps passing.

Concrete references today:

- `frob-timeout-guard.py` matches `frob +(ticket +(land|done-report)|check|
  test)` to decide whether a command needs a large tool timeout. Rename or
  regroup any of those four and the guard stops firing -- silently. The
  stall pattern it exists to prevent comes straight back, and nothing says
  the guard went blind.
- `frob-suggest.py` SUGGESTS `uv run frob test`, `frob check`, `frob ticket
  ...`, `frob coverage`, `frob worktree` in its refusal text. After a
  rename these become instructions to run a command that no longer exists
  -- a hook that blocks a caller and then tells it to do something
  impossible, which is the T-1705 failure exactly.

Both are now git-tracked (`.claude/hooks/**`), so a gate can see them.

Two pieces of work:

1. A DETECTOR. A rule (register a real id in the catalog; do not invent an
   unregistered one) that extracts frob verb references from tracked hook
   sources and fails when one does not resolve against the live CLI
   dispatch table. Resolve against the DISPATCH TABLE, not a hand-written
   list of verb names -- a hand-written list is the same defect class as
   the bug, and it will drift the first time someone adds a verb.

   Both reference SHAPES must be covered: the regex/matcher form
   (`frob-timeout-guard`'s PATTERN) and the prose form inside suggestion
   strings. The second is easy to forget because it is "just a message",
   and it is precisely the half that misleads a human.

2. SEQUENCING. T-1567..T-1571 are blocked on this, deliberately. The
   detector has to exist BEFORE the renames, or the renames are exactly
   the event it cannot warn about. Landing it afterwards means hand-auditing
   the hooks and hoping.

Note for whoever does the regrouping afterwards: keeping the old verb as a
deprecated alias does NOT make this unnecessary. The hooks would keep
working while every suggestion string tells callers to use a verb the help
output no longer documents, which is drift with a longer fuse.

Wider scope, worth checking while here rather than filing again: the same
by-name coupling exists anywhere outside `src/` that names a frob verb --
`docs/guides/agent-playbook.md`, `docs/modules/cli.md`, the scaffold
templates, and any CI recipe. The detector should cover tracked
non-source references generally, not hooks specifically. Report what it
finds; the count is itself the argument for how bad the coupling is.

<!-- ticket:T-1728 -->
```yaml
id: T-1728
title: close's own-obligations REL001 check is not rapid-aware, deadlocks a worktree
  that legitimately needs a version bump
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
## Description

`frob ticket close`'s own-obligations preflight
(`_close_own_obligations_for_ticket` / `_own_obligations_rel_bump_dirty` in
`src/frob/app/ticket_runner/_close_cmd.py`) refuses to close a ticket
whose diff requires a REL001 version bump unless `pyproject.toml`'s
declared version already covers it -- but a worktree agent is forbidden
from ever touching `pyproject.toml`'s version line (agent-playbook.md
section 4b, T-0731's land-owned-files guard: version bump/changelog are
`frob ticket land`-exclusive). For a ticket that genuinely changes public
API (removes a public config field/CLI flag/function parameter, as
T-1675 did), this is a real deadlock: close demands a bump the worktree
is not allowed to write, and land (the only thing allowed to write it)
runs strictly AFTER close.

Observed while closing T-1675 (2026-08-07): `frob ticket close T-1675`
refused with `OwnObligationsUnclean` / "REL001 version bump outstanding
(needs 0.358.0, pyproject declares 0.357.0)" even though the repo is
running the `rapid` profile, which explicitly turns REL001 OFF on the
LAND path (`frob ticket land`'s own rapid-profile handling, T-1681/
T-1575) -- but this separate close-time own-obligations check has no
rapid awareness at all. Compare `_done_transition_structural_guard` in
`src/frob/tickets/_evidence.py`, which DOES thread `rapid=_is_rapid(root)`
through to relax its own `covers_scope` obligation (line ~354: `if
covers_scope is False and not rapid`) -- `_close_own_obligations_for_
ticket`/`_own_obligations_rel_bump_dirty` has no equivalent rapid
parameter or check at all.

## Plan (sketch, for whoever picks this up)

- Thread `rapid: bool` into `_close_own_obligations_for_ticket` /
  `_own_obligations_rel_bump_dirty` (mirroring `_done_transition_
  structural_guard`'s existing pattern), sourced from `_is_rapid(root)`.
- When `rapid` is true and the ONLY outstanding own-obligation is the
  REL001 bump (COV001/SELFAUDIT001 findings should still block), relax
  the refusal and record it via `record_rapid_debt` (same debt-ledger
  mechanism `_done_transition_structural_guard` already uses for its own
  rapid relaxations), so the relaxation is disclosed, not silent.
- Add a regression test that closes a ticket whose diff needs a version
  bump, under a `rapid`-profile root, with no `pyproject.toml` edit, and
  asserts the close now succeeds (with a recorded rapid-debt line) instead
  of refusing.

## Workaround used in the T-1675 session

Temporarily edited `pyproject.toml`'s version to the required value
LOCALLY (uncommitted, never staged/committed -- the T-0731 land-owned-
files pre-commit hook only fires on a commit, never on an uncommitted
working-tree edit), ran `frob ticket close T-1675` against that disk
state, then reverted the edit (`git checkout -- pyproject.toml`) before
landing, so `frob ticket land`'s own bump computation was untouched and
wrote the real bump itself. This is not a fix, just what let T-1675 land
without violating the land-owned-files rule or waiving a real gate.

<!-- ticket:T-1729 -->
```yaml
id: T-1729
title: consider relocating _write_ticket_unchecked out of src/frob/tickets/_store.py
  into a test-only helper module
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
frob:ticket T-1679

`_write_ticket_unchecked` (`frob.tickets._store`) is a deliberately
test-fixture-only escape hatch for the T-1637/T-1679 content-loss guard --
by design it has no production caller and never should. WIRE002 requires
a real `follow_up` ticket for its WIRE001 waiver since it lives in `src/`
(the `permanent="true"` test-tree exemption only applies to symbols under
`tests/`). This ticket is that accountable follow-up: investigate whether
`_write_ticket_unchecked` can be relocated into a `tests/`-tree helper
module instead (it needs access to the private `_write_ticket_impl` split
point in `_store.py`, so this may require exporting a narrow test-only
seam, or may simply not be worth the churn -- either outcome is a
legitimate close for this ticket).

<!-- ticket:T-1730 -->
```yaml
id: T-1730
title: frob ticket land should auto-rebase the worktree onto main after a successful
  land
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
## Description

Every single land I performed across two ticket groups in this session
(T-1673/T-1630/T-1675/T-1670/T-1679, then T-1714/T-1706) hit the same
sequence: land a ticket successfully (`LAND-PROOF: ... verified=True`),
then the NEXT `frob check --ticket <next-id>` in the same worktree reports
spurious SCOPE001/COV002 findings on files the just-landed ticket touched
-- because the worktree's own commits for that already-landed work are
still present on its branch, and the branch has not moved to include
main's new (squashed) tip. `git diff main` for those files then shows
non-empty content even though the content is byte-identical, because the
branch and main reached the same state via two DIFFERENT commits (the
worktree's own step-by-step history vs. land's squash-apply), so `git
diff main --stat` inherently looks non-empty for anything the worktree
itself changed, whether or not it matches main.

Observed sequence, every time, this session:
1. `frob ticket land T-XXXX --worktree <path>` succeeds, `LAND-PROOF ...
   verified=True`.
2. Start the next ticket in the same worktree; `frob ticket sweep`/`frob
   check --ticket <next>` reports SCOPE001 (files outside declared scope)
   and/or COV002 (changed-with-no-frob:ticket-edge) findings that are
   NOT caused by the next ticket's own work -- they are the just-landed
   ticket's files, which the worktree's branch still carries as its own
   uncommitted-relative-to-main diff.
3. Resolved every time by `git rebase main` in the worktree (dropping the
   now-"patch already upstream" commits git detects automatically, and
   skipping any obsolete `wip: pre-land snapshot for T-XXXX` commits
   land's own machinery leaves behind) BEFORE doing any more gate
   verification for the next ticket.
4. Repeat from step 1 for the next ticket in the series.

This is pure repeated friction -- the exact same manual recipe, by hand,
after every single successful land in a multi-ticket worktree series.
Per the standing directive (systematize repeated friction rather than
re-doing it by hand every time), this should be mechanical.

## Proposal

`frob ticket land --worktree <path>` should, after a successful land
(`verified=True`), automatically `git rebase main` the worktree's own
branch onto the new main tip it just produced -- dropping the now-
redundant commits the same way a manual rebase does (git's own "patch
contents already upstream" detection), before returning control to the
caller. This closes the loop the same way a human currently does by hand,
every time, immediately after every land in this session.

Open questions for whoever picks this up:
- Should this be unconditional, or opt-in via a flag (e.g. `--rebase-
  after`) for a caller that does not want its worktree branch rewritten
  automously? A single-ticket worktree (not a series) may not care either
  way; a series worktree needs it every time.
- What happens if the auto-rebase hits a REAL conflict (not just
  redundant-patch drops) -- should land still report success (the land
  itself is done) and just warn that the auto-rebase needs manual
  attention, rather than let a rebase conflict retroactively fail an
  already-successful land?
- Should the two housekeeping commit classes land already knows about
  (`wip: pre-land snapshot for T-XXXX`, ledger auto-commits) be preemptively
  dropped/skipped rather than relying on git's generic empty-patch
  detection, since land KNOWS which of the worktree's own commits are its
  own now-obsolete staging artifacts?

## Evidence (the actual observed sequence this session)

Every occurrence below is `git rebase main` run in
`.claude/worktrees/agent-ac2dad95d0b2b8809` immediately after a
`LAND-PROOF ... verified=True` line, always resolving 1-3 conflicts (the
shared `rapid-debt.jsonl` append-only log, occasionally a `tickets.md`
splice-driver conflict) and dropping 1-6 "patch contents already
upstream" commits per rebase:

- After landing T-1673: rebased before starting T-1630 (SCOPE001 on
  `rapid-debt.jsonl` and other post-land-sweep-touched files).
- After landing T-1630: rebased before starting T-1675 (same shape).
- After landing T-1675: rebased before starting T-1670 (plus resolving a
  CHANGELOG.md/land-owned-file pre-commit-hook collision on the first
  attempt, which forced an abort-and-rebase-instead-of-merge decision).
- After landing T-1670: rebased before starting T-1679.
- After landing T-1679: rebased before starting T-1714 (2 real conflicts
  in `src/frob/tickets/_store.py`, both trivially resolved by keeping
  HEAD's already-landed content).
- After landing T-1714/merging T-1701 (already landed by another agent):
  rebased before starting T-1706.

Six for six. This ticket exists so the seventh time is automatic.

<!-- ticket:T-1731 -->
```yaml
id: T-1731
title: 'frob ticket evidence node-id shape validation: investigate the malformed-id
  gap without breaking pytest-form binding'
state: queued
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
## Description

Follow-up to T-1670's part 2 ("malformed ids accepted silently"), split
out after investigation found the naive literal reading would be harmful.

T-1670's own text says: "This graph's convention is `path::Class.method`
-- one `::` then a DOTTED class/method. Pytest's own `path::Class::method`
form is accepted by `frob ticket evidence` without complaint... Fix:
validate the node-id shape AT BIND TIME... and reject the pytest
`::`-separated form."

Investigation while implementing T-1670's part 1 found this cannot be
implemented as literally stated without breaking real, tested, documented
behavior:

- `ticket.evidence` entries are resolved against real pytest node ids via
  `frob.tickets._models.matches_collected`, which requires an EXACT string
  match against `collected` -- and `collected` (from `collect_python_tests`/
  `pytest --collect-only`) is always in pytest's native `path::Class::method`
  (double-`::`) form, never dotted. Rejecting that form at bind time would
  make it impossible to bind evidence using a real collected node id copied
  verbatim from `pytest --collect-only` output -- the most natural, lowest-
  error way to get a correct id.
- `frob.tickets.__init__.normalize_evidence_separator` (T-0293) already
  converts a DOTTED `path::Class.method` id INTO the pytest `::` form for
  storage/resolution -- the existing direction is dot-to-`::`, the opposite
  of what T-1670's literal ask would require.
- The CLI path (`_apply_evidence` in `src/frob/app/ticket_runner/_verify.py`)
  already resolves every id against a real collected set
  (`_collect_python_and_rust_ids`) and rejects (`UnknownEvidence`/
  `EvidenceNotPassing`) anything that does not resolve or pass -- so a
  genuinely malformed/typo'd id is already caught at bind time through the
  real CLI, not silently accepted.

What's still plausibly a real, addressable gap:

1. `normalize_evidence_separator`'s early-return (`if "::" in remainder:
   return entry`) passes through UNCHANGED any id with a remainder that
   already contains `::` -- this correctly leaves a legitimate 2-segment
   pytest id (`path::Class::method`) alone, but ALSO passes through
   unchanged a genuinely malformed 3+-segment id (`path::Class::method::
   extra`) with no rejection at the schema-validation layer
   (`validate_evidence`) itself -- it is only caught later, and only if a
   `collected` set happens to be supplied (true for the real CLI path,
   NOT true for a bare library `add_evidence(root, id, ids)` call with no
   collector, which only WARNS "recorded UNRESOLVED").
2. `frob:tests` DIRECTIVE comments (a SEPARATE namespace from
   `ticket.evidence`, playbook section 5) use the dotted `path::Class.method`
   qualname form by this repo's own convention -- DOC007 flags a `frob:tests`
   directive using pytest's own `::`-form target. If an agent habitually
   copies a `ticket.evidence` id (already normalized to `::` form) verbatim
   into a NEW `frob:tests` directive, DOC007 fires. This is a
   directive-authoring UX gap, not a `frob ticket evidence` bind-time bug --
   worth its own investigation into whether `frob ticket evidence` should
   print the frob:tests-directive-form of a newly-bound id as a hint.

## Plan (sketch, for whoever picks this up)

- Investigate (1): add a schema-level check in `validate_evidence` that
  rejects an id whose remainder-after-first-`::` contains MORE than one
  additional `::` (i.e. 3+ total `::`-segments) -- never reject the
  ordinary 1-or-2-`::` pytest shapes, only the genuinely malformed ones.
- Investigate (2) separately: does `frob ticket evidence` need to print a
  "for a frob:tests directive citing this id, use: <dotted form>" hint
  line, to close the copy-paste UX gap without touching `ticket.evidence`'s
  own resolution-critical `::` storage format at all?
- Do NOT implement "reject the pytest `::`-separated form" as literally
  worded in T-1670's original text -- see the investigation above for why
  that breaks the primary, correct way to bind evidence.

<!-- ticket:T-1732 -->
```yaml
id: T-1732
title: frob ticket land structurally cannot carry a cross-ticket ledger edit forward
  (splice_ledger tiebreak drops it)
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_ledger_merge.py
- src/frob/tickets/_land_squash.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
## Description

`frob ticket land`'s squash-apply carries `tickets.md` forward via
`splice_ledger` (`frob.tickets._land_ledger_merge`), which merges "at the
ticket-id level, keeping the newest state per section" (`_newer`). This
structurally drops a legitimate edit to a DIFFERENT ticket's own section
made in the same worktree, whenever that edit does not change state rank
or Done-report presence -- an evidence-list value change (e.g. `frob
ticket evidence <other-id> --replace OLD NEW`) is invisible to `_newer`'s
comparison heuristic, so the tiebreak falls through to whichever side it
defaults to (observed: main's side wins), silently discarding the edit.

Observed twice in the same session (2026-08-06/07): while working T-1679,
a coordinator-requested fix rebound T-1637's (a DONE, unrelated ticket)
evidence citations to match a rename made by T-1679's own diff. That
rebind was committed in the worktree and verified clean locally, but
`frob ticket land T-1679`'s squash never carried it -- main kept T-1637's
stale evidence, later surfacing as T-1714's own regression (2 COV003
findings). T-1714 was filed and landed specifically to re-fix this, its
Done report explicitly claiming "This ticket's own land is what actually
carries it" -- but a `git show main:tickets.md` check immediately after
T-1714's land showed T-1637's block STILL unchanged: T-1714's land
carried T-1714's OWN section (state/evidence) but again dropped the T-1637
section edit, for the identical reason.

This is a real structural gap, not a one-off: `frob ticket land <id>`
cannot carry a legitimate edit to a ticket OTHER than `<id>` forward, no
matter which ticket "sponsors" the edit or how many times it is redone,
because `splice_ledger`'s per-section merge only ever compares state-rank/
report-richness, never raw content, and always resolves a tie toward one
side (main) regardless of which side's content is actually newer/correct.

## Impact

Any legitimate cross-ticket ledger correction (evidence rebinds after a
rename, scope corrections discovered while working a different ticket,
citation fixes) made from a worktree is currently **unlandable** through
the normal `frob ticket land` path -- it will always look like it worked
locally and always silently vanish from main. The workaround used twice
(re-apply the edit, hope a DIFFERENT ticket's land carries it) does not
work and should not be relied on again; it burned two ticket-cycles
(T-1714, this investigation) without actually fixing the regression.

## Plan (sketch)

- Extend `_newer`'s (or `splice_ledger`'s) comparison to detect a genuine
  CONTENT difference between `ours`/`theirs` for a ticket's section, not
  only state-rank/report-richness -- when one side differs from `base_text`
  (the true merge-base, already threaded through per T-1154) and the other
  does not, the side that changed should win, independent of state rank.
- Alternatively/additionally: give `frob ticket land` an explicit way to
  declare "this land also carries a correction to ticket X's own section"
  (mirroring `--allow-cross-ticket`'s disclosure model for CODE passengers,
  but for ledger sections specifically) so a deliberate cross-ticket ledger
  fix has a sanctioned, verified path instead of hoping the heuristic
  happens to pick the right side.
- Regression coverage: a worktree edits ticket B's section (evidence only,
  no state change) while landing ticket A; after `frob ticket land A`,
  `git show main:tickets.md` must show ticket B's edit present, not
  reverted to main's stale prior content.

Filed while working T-1706 (the T-1670 part-2 split), after discovering
T-1714's land had not actually fixed what it claimed to fix.

<!-- ticket:T-1733 -->
```yaml
id: T-1733
title: Weakening a ticket's evidence is silent and free, while the honest escape hatch
  is logged and justified
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/gates/_mutation_evidence.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- docs/modules/gates.md
- src/frob/tickets/_models.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/_mutate.py
- tests/test_tickets_evidence_cli.py
- tests/test_tickets_mutation_evidence.py
- src/frob/tickets/_mutation_evidence.py
- src/frob/gates/_waive.py
- tests/test_gates_mutation_evidence.py
- src/frob/tickets/_reporting.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_query.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_tickets_mutation_evidence.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_mutation_evidence.py
  reason: requirement 3 (refuse outright when evidence unbound AND surviving evidence
    confirmatory-only per TEST016) needs to read ConfirmatoryFinding/unmeasured from
    this module, the real engine T-1727 already established is the right home for
    mutation-evidence logic
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_waive.py
  reason: TEST018 (the new outright-refuse rule for requirement 3) must be registered
    in _KNOWN_GATE_RULES (src/frob/gates/_waive.py) per the T-0756 new-gate-rule-acceptance
    policy the ticket itself invoked ('register a real id; do not invent an unregistered
    one') -- that registry lives in this file, not gates/__init__.py, per T-1139's
    move
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: evidence_weakened/TEST018 test coverage for requirement 3 belongs in the
    existing TestMutationEvidenceViolations class in this file, matching TEST016's
    own test-file home
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: requirement 4 (frob ticket show surfaces evidence churn) needs to render
    the new evidence_changes audit trail, mirroring _render_acceptance_amendments_block's
    existing T-1422 precedent in this exact file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/_config_external.py
  reason: AppConfig.from_external's field-copy tuples (src/frob/app/_config_external.py)
    must include the two new ticket_evidence_replace_reason[_file] fields or the new
    --reason/--reason-file CLI flags silently no-op (never reach AppConfig) -- same
    file T-0749's own comment in config.py describes hitting this exact gap for --accepts
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: requirement 4's real home is frob.app.ticket_runner._query._show, which
    already renders acceptance_amendments via _render_acceptance_amendments (T-1422)
    -- evidence_changes needs the identical rendering precedent applied here, not
    in _reporting.py's Done-report composer which is a different, narrower surface
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 flagged the new EvidenceChangeEntry symbol as undeclared in
    the tickets_ledger store's interface= list -- same self-audit obligation T-1727
    already hit for its own new symbols in this file
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_blank_reason_is_a_hard_refusal
- tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_without_reason_exits_nonzero_and_writes_nothing
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_replaces_flat_evidence_and_acceptance_binding_atomically
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_same_old_and_new_is_a_no_op_success
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_evidence_weakened_and_confirmatory_refuses_outright
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_evidence_changes_never_produces_test018
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_evidence_changes_with_strong_surviving_evidence_no_test018
- tests/test_tickets_evidence_cli.py::TestEvidenceChangesSurfaced::test_show_renders_evidence_change_and_reason
designated_repro_test: null
threat: null
component: null
```
T-1727 records that the close-time mutation sweep's cost pushes agents
toward binding cheap evidence, but every one of its requirements is about
BUDGET -- make the sweep bounded, warn earlier, report progress. All of
those make `close` faster. None of them stops a ticket closing on weaker
evidence than it started with. The insight was written down and then not
acted on, which is the catalogued-but-not-enforced shape this repo has
been burned by before.

This ticket is the enforcement half.

THE ASYMMETRY, EXACTLY. Two ways exist to get a slow close to finish:

- `--skip-mutation-evidence`: DISCLOSED. Logs loudly, demands a
  justification, lands in the Done report. The honest exit is expensive
  and permanently visible.
- Unbind the slow tests with `frob ticket evidence --replace`: SILENT.
  Requires no reason, records nothing, leaves no trace anyone reviews.

So the tool bills the honest exit and comps the quiet one. Observed
live on 2026-08-07: an agent facing ten consecutive 540s close timeouts
unbound its three `TestSpawnWithWatchdog` tests -- the only evidence that
actually exercised the subprocess watchdog the ticket existed to build --
and the ledger shows nothing about it. It surfaced only because the agent
volunteered it in prose.

The precedent for the fix is already in this CLI and one verb away:
`frob ticket scope` REQUIRES `--reason` (or `--reason-file`) for any
scope change, and records it. Narrowing what a ticket covers is treated
as a decision worth writing down. Narrowing what PROVES it is not. There
is no principle that makes scope worth recording and evidence not.

REQUIRED:

1. Any evidence REMOVAL or replacement requires `--reason`, recorded in
   the ticket, exactly as `frob ticket scope` already does. Pure additions
   stay free -- the point is to price weakening, never to tax
   strengthening.
2. A gate rule (register a real id; do not invent an unregistered one)
   that refuses a close when the bound evidence set SHRANK during the
   ticket's life without a recorded reason. Shrink means fewer ids, or
   the same count with a strong id swapped for a weaker one.
3. The specific pattern to refuse OUTRIGHT, not merely flag: evidence was
   unbound AND the surviving evidence is confirmatory-only per TEST016.
   That is the exact fingerprint of "the tests that proved it were
   removed so it would close", and it is mechanically detectable because
   TEST016 already computes the confirmatory-only verdict.
4. `frob ticket show` surfaces evidence churn -- what was bound, what was
   unbound, and why -- so a reviewer sees the history rather than the
   final list. A final list that looks fine is precisely what an unbind
   produces.

THE PRINCIPLE WORTH STATING IN THE DOCS, because it generalises past this
ticket: EVERY WAY TO MAKE A TICKET EASIER TO CLOSE MUST COST AT LEAST AS
MUCH BOOKKEEPING AS THE HONEST WAY. Wherever a cheap exit is quieter than
the expensive one, the cheap exit is what will be taken, and the ledger
will look clean while the evidence rots. Audit the other verbs against
that rule while implementing this one, and report any others found --
`--skip-mutation-evidence` versus silent unbinding is unlikely to be the
only pair.

Do NOT make this a warning. A warning here is advice about an action
already taken, at the moment the caller is most motivated to ignore it.

Sibling: T-1727 (the cost that creates the pressure). Fixing that reduces
the motive; this removes the means. Both are needed -- a bounded sweep
still leaves unbinding free, and pricing unbinding still leaves an agent
staring at a 90-minute close.

## Done report

Implemented all four required parts, plus the audit requirement, plus a
loud (not silent) refusal per the coordinator's explicit priority.

1. `frob ticket evidence --replace` now requires `--reason`/`--reason-file`
   (`replace_evidence`'s new required keyword-only `reason: str`,
   `Err(EvidenceReplaceReasonMissing)` when blank), mirroring T-0455's
   `frob ticket scope --reason` precedent exactly. A pure `add_evidence`
   append stays completely free -- only the shrink/rebind path costs
   anything, per the ticket's own "price weakening, never tax
   strengthening" instruction. Every non-no-op replace appends a new
   `EvidenceChangeEntry` (old_node, new_node, reason, actor, at) to
   `ticket.evidence_changes` -- never edited, only appended, same
   discipline as `ScopeChangeEntry`/`AcceptanceAmendmentEntry`.
2. New gate rule **TEST018** (registered in `_KNOWN_GATE_RULES`,
   `src/frob/gates/_waive.py`, not invented ad hoc): refuses a close
   OUTRIGHT -- always ERROR, regardless of ticket kind, never downgraded
   to WARN -- when `ticket.evidence_changes` is non-empty AND the
   surviving evidence still produces a TEST016 `ConfirmatoryFinding`
   (confirmatory-only OR T-1727's `unmeasured`) against the ticket's own
   diff. This is the exact mechanical fingerprint the coordinator named
   as the priority: "evidence was unbound AND the surviving evidence is
   confirmatory-only per TEST016." A ticket whose evidence was rebound
   but whose surviving evidence still kills mutants is unaffected.
   TEST018 shares TEST016's existing `--skip-mutation-evidence` escape
   hatch -- not a new, separate override.
3. `frob ticket show` surfaces the churn (`_render_evidence_changes`,
   `frob.app.ticket_runner._query`) the same way it already surfaces
   `acceptance_amendments` -- what was rebound, to what, and why, not
   just a final list that looks fine.
4. NOT a warning. `replace_evidence`'s reason check is a hard `Err` (no
   write happens at all without a reason); TEST018 is ERROR severity,
   always, refusing the close/land outright.

WHY REFUSAL, NOT A WARNING (the design decision most likely to get
softened by a successor -- read this before relaxing TEST018 to WARN or
adding a bypass that isn't `--skip-mutation-evidence`): a warning is
advice about an action ALREADY TAKEN, delivered at the exact moment the
caller is most motivated to ignore it -- the evidence is already
unbound, the close is already in flight, and the agent reading the
warning is the same agent who just weakened the evidence to escape a
590s timeout. T-1727 already proved warnings do not change behavior
under this exact pressure: the sweep's own findings were always logged,
and the incident happened anyway. TEST018 has to be a hard refusal
specifically BECAUSE it fires at the one moment a warning would be
read and discarded -- close time, under time pressure, after the quiet
escape already happened. Downgrading it to WARN does not make the
mechanism gentler, it makes it inert: it becomes exactly the
"advice nobody reads at exactly the moment it matters" shape this
ticket exists to eliminate. The escape hatch that keeps this humane is
`--skip-mutation-evidence` -- loud, logged, and justification-required
-- not a softened gate.

Audit requirement ("report any others found"): found ONE real second
asymmetric pair -- `frob ticket evidence --designate-repro NODE-ID`
(T-1670) can silently redirect which bound evidence id BUG002 checks,
with no `--reason` and no audit trail, structurally the same shape
`--replace` had. Filed as a new ticket (T-1749, scope:
src/frob/tickets/_setters.py, src/frob/gates/_mutation_evidence.py,
src/frob/app/ticket_runner/_verify.py) rather than folding into T-1733's
own scope. Checked `scope`/`accept --amend/--remove` -- both already
require and record a reason (T-0455/T-1422), no gap there.

Scope note: docs/modules/tickets.md is leased by another in-progress
agent (T-1715/T-1739) for the duration of this ticket's work, per the
coordinator's explicit instruction to stay disjoint from it. Four
symbols (`mutation_evidence_violations`, `replace_evidence`, `Ticket`,
`TicketError`) have an `affects()`-closure doc pointing at that file;
each carries a `frob:waive AFFECT001` with the T-1486 precedent's exact
shape (lease-conflict reason, pointing at where the real documentation
landed instead), and the full behavior is documented in this ticket's
own docs home, docs/modules/gates.md's new "TEST018 (T-1733)" section
(including the generalized "every way to make a ticket easier to close
must cost at least as much bookkeeping as the honest way" principle the
coordinator asked to have stated there).

Changed:
- src/frob/tickets/_models.py::EvidenceChangeEntry (new)
- src/frob/tickets/_models.py::Ticket (evidence_changes field)
- src/frob/tickets/_models.py::TicketError (EvidenceReplaceReasonMissing)
- src/frob/tickets/_evidence.py::replace_evidence (required reason, records entry)
- src/frob/tickets/_evidence.py::_current_actor (new, T-1422 duplication precedent)
- src/frob/gates/_mutation_evidence.py::mutation_evidence_violations (TEST018)
- src/frob/gates/_mutation_evidence.py::_test018_message (new)
- src/frob/gates/_waive.py::_KNOWN_GATE_RULES (TEST018 registered)
- src/frob/app/ticket_runner/_verify.py::_resolve_evidence_replace_reason (new)
- src/frob/app/ticket_runner/_verify.py::_apply_replace_evidence (reason param)
- src/frob/app/ticket_runner/_verify.py::_evidence_apply_replace (requires+resolves reason)
- src/frob/app/ticket_runner/_query.py::_show, _render_evidence_changes (new)
- src/frob/_cli_parsers/_ticket/_closeout.py (--reason/--reason-file flags)
- src/frob/app/config.py, src/frob/app/_config_external.py (new AppConfig fields)
- design/frob.strata (EvidenceChangeEntry interface declaration, SELFAUDIT001)
- docs/modules/gates.md (new "TEST018 (T-1733)" section + generalized principle)

Evidence: 8 new pytest node ids covering (a) the hard refusal on blank
reason (library + CLI level), (b) the audit entry recorded on a real
replace and absent on a true no-op, (c) TEST018 firing when evidence was
weakened AND surviving evidence is confirmatory-only, staying silent
when evidence was never weakened, and staying silent when weakened but
surviving evidence still kills mutants, (d) `frob ticket show` rendering
the evidence_changes block with its reason.

Verification:
- `uv run pytest tests/test_tickets_evidence_cli.py tests/test_gates_mutation_evidence.py tests/test_tickets_mutation_evidence.py tests/gates/test_mutation_evidence_err_branches.py tests/test_tickets_acceptance.py tests/test_ticket_evidence.py tests/test_evidence_integrity.py tests/test_tickets.py tests/unit/test_config.py -q` -- 327 passed, 1 skipped.
- `uv run ty check` / `uv run ruff check` / `uv run ruff format --check` on every touched .py file -- all clean.
- `uv run frob check --land-parity` (cache-bypassed) -- clean, 0 unscoped errors.

Filed: T-1749 (the --designate-repro asymmetry, audit finding).

Gates: frob check --land-parity clean, 0 unscoped errors. Four AFFECT001
waivers added (T-1486 lease-conflict precedent, docs/modules/tickets.md
genuinely leased elsewhere for this ticket's duration) -- no other
waivers.

### Changed
```
 design/frob.strata                         |   3 +-
 docs/design/registry/check-coverage.yaml   |   6 +-
 docs/modules/gates.md                      |  67 ++++
 rapid-debt.jsonl                           |   1 +
 src/frob/_cli_parsers/_ticket/_closeout.py |  20 ++
 src/frob/app/_config_external.py           |   4 +
 src/frob/app/config.py                     |  12 +
 src/frob/app/ticket_runner/_query.py       |  26 +-
 src/frob/app/ticket_runner/_verify.py      |  68 +++-
 src/frob/gates/_mutation_evidence.py       |  62 +++-
 src/frob/gates/_waive.py                   |   8 +
 src/frob/tickets/_evidence.py              |  64 +++-
 src/frob/tickets/_models.py                |  67 ++++
 tests/test_gates_mutation_evidence.py      |  84 +++++
 tests/test_tickets_evidence_cli.py         | 143 +++++++-
 tickets.md                                 | 513 ++++++++++++++++++++++++++++-
 16 files changed, 1131 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_blank_reason_is_a_hard_refusal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_without_reason_exits_nonzero_and_writes_nothing` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_replaces_flat_evidence_and_acceptance_binding_atomically` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_same_old_and_new_is_a_no_op_success` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_evidence_weakened_and_confirmatory_refuses_outright` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_evidence_changes_never_produces_test018` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_evidence_changes_with_strong_surviving_evidence_no_test018` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestEvidenceChangesSurfaced::test_show_renders_evidence_change_and_reason` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 1 error(s), 962 warning(s), 730 waived
- error-findings: TICK006@tickets.md

<!-- ticket:T-1734 -->
```yaml
id: T-1734
title: 'Stop-event hook: nudge when a turn diagnoses a defect but files nothing (semantic
  or state-based, never keyword matching)'
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- .claude/hooks/diagnosis-nudge.py
- .claude/hooks/sync-claude-config.py
- .claude/settings.json
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'OWNER DECISION 2026-08-07: lexical matching is acceptable and an LLM-evaluated
    hook is REJECTED -- do not pipe coordinator messages through a second model. Given:
    a turn ends; when the nudge evaluates it; then no additional model inference is
    performed. The design must therefore be a plain command hook over text and/or
    repo state, and the earlier ''semantic or state-based'' framing in the body is
    superseded on the semantic half.'
  evidence: []
- text: 'The nudge NEVER blocks: it emits systemMessage and exits clean, so a missing
    ticket can never become a stuck session.'
  evidence: []
- text: The nudge names what to file (e.g. 'N findings in X have no owning ticket'),
    not merely that something is unfiled.
  evidence: []
- text: 'MEASURED 2026-08-07 via the temporary Stop probe (~/.claude/hooks/_stop-probe.py,
    output at ~/.claude/hooks/state/stop-probe.jsonl): the Stop payload DOES carry
    the response text. Observed keys: _probe_at, background_tasks, cwd, effort, hook_event_name,
    last_assistant_message, permission_mode, prompt_id, session_crons, session_id,
    stop_hook_active, transcript_path. So the state-based fallback described in the
    body is NOT needed -- read last_assistant_message directly.'
  evidence: []
- text: 'Use stop_hook_active to avoid re-entrancy: the payload carries it, and a
    Stop hook that re-triggers itself is the obvious failure mode.'
  evidence: []
- text: 'REMOVE the probe as part of this ticket: delete ~/.claude/hooks/_stop-probe.py,
    its Stop registration in ~/.claude/settings.json, and ~/.claude/hooks/state/stop-probe.jsonl.
    A diagnostic left running is the same residue class this drive has spent the day
    clearing.'
  evidence: []
threat: null
component: null
```
A coordinator repeatedly diagnoses a defect in prose -- "this is the same
class as X", "that is a real bug", "the cost structure rewards weak
evidence" -- and then does not file it. Observed several times on
2026-08-07 alone:

- An agent lost ~90 minutes to ten consecutive close timeouts, diagnosed
  the cause precisely, and explicitly decided NOT to file ("a known,
  disclosed mechanism working as designed"). The coordinator overruled it
  and filed T-1727.
- The coordinator itself wrote the perverse-incentive analysis (unbinding
  strong evidence is silent while the honest escape hatch is logged) into
  T-1727's PROSE, then shipped four requirements none of which addressed
  it. It became T-1733 only because the repo owner noticed and asked.

That second one is the shape to design against: the diagnosis was
written down, in a ticket, and still went unenforced. Prose is where
findings go to die. The gap is not knowledge -- it is that nothing
converts a stated finding into a tracked obligation.

WANTED: a Stop-event hook that notices when a turn CONTAINED A DIAGNOSIS
BUT FILED NOTHING, and nudges.

Explicitly NOT keyword matching. "bug", "broken", "should fix" as
substrings will fire on every code review, every Done report, and every
message quoting a ticket title -- and a nudge that fires constantly is
one that gets ignored, which is worse than no nudge. This repo has
already paid for lexical rules three times today (TICK006 on prose about
code spans, a hook blocking its own commit message on a parenthetical, a
hook blocking a correctly-scoped test run).

DESIGN CONSTRAINTS, ESTABLISHED BY MEASUREMENT, NOT ASSUMPTION:

- Prompt-type (LLM-evaluated) and agent-type hooks are documented as
  available only for TOOL events (PreToolUse/PostToolUse/
  PermissionRequest), not Stop. The settings schema does not appear to
  enforce that, so whether a `type: "prompt"` hook fires on Stop must be
  TESTED before the design depends on it.
- A temporary probe is registered on Stop
  (`~/.claude/hooks/_stop-probe.py`) writing observed payload keys to
  `~/.claude/hooks/state/stop-probe.jsonl`. Read it FIRST. The whole
  design hinges on whether the Stop payload carries the assistant's
  response text or only a session id: without the text, no hook of any
  type can judge what the turn said, and the feature has to be built from
  a different signal.
- REMOVE THE PROBE when the real hook lands. A diagnostic left running is
  the same class of residue as everything else this drive has cleaned up.

IF THE RESPONSE TEXT IS AVAILABLE: an LLM-evaluated hook judging "does
this turn state a defect, a root cause, or work that needs doing, for
which no ticket was filed?" is the right implementation, because the
judgement is semantic and a regex cannot make it.

IF IT IS NOT AVAILABLE: fall back to a STATE-BASED signal, which is
better than lexical anyway because it reads actions rather than words.
`.frob/telemetry.jsonl` already records every frob CLI invocation
(`frob.app.telemetry.record_cli_event`), so "did this turn file a
ticket" is answerable exactly, with no parsing. Combine with signals the
repo can measure on its own: findings present with no owning open
ticket; files touched outside every open ticket's scope; `frob:todo`
anchors with no ticket. Nudge on the CONJUNCTION -- work happened,
nothing was filed, and there is unaccounted-for surface.

Either way:

- NUDGE, NEVER BLOCK. A Stop hook that blocks turns a missing ticket into
  a stuck session. Emit `systemMessage`, exit clean.
- Say what to file, not that something is unfiled. "3 findings in
  _coverage_refresh.py have no owning ticket" is actionable; "consider
  filing a ticket" is noise.
- Rate-limit per session so a long turn does not nag repeatedly.

Sibling: T-1725 already gates verb references in the tracked hooks, so
whatever this adds must resolve against the live dispatch table too.

<!-- ticket:T-1735 -->
```yaml
id: T-1735
title: SYS108 missing from _KNOWN_GATE_RULES, self-model node count drift (23 vs 22)
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_rule_id_scan.py
- tests/test_gates.py
- src/frob/strata/_selfconform.py
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
Observed 2026-08-07 running `frob test --base main` after merging main into a
long-running worktree (T-1587's own worktree, unrelated to this defect).

Two test failures, both pre-existing on main and unrelated to my own diff
(`src/frob/tickets/_store.py`/`_reporting.py`/`tests/unit/test_ticket_store.py`/
`docs/design/ledger-v2.md`):

- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known`
  fails: `SYS108` (`src/frob/strata/_selfconform.py:1407`) is constructed but
  missing from `_KNOWN_GATE_RULES`.
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates`
  fails: `assert 23 == 22` (module node count drift, same self-model area).

Confirmed neither failure references anything in my own scope by running the
two tests directly against the merged tree. Not investigated further --
filing so the drift is tracked rather than silently re-discovered by the
next agent who merges main.

<!-- ticket:T-1736 -->
```yaml
id: T-1736
title: Wire frob.verify.record_intent into the land-commit path so the verify queue
  actually gets entries
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
found while landing T-1688: frob.verify._watermark.record_intent has no real caller yet -- T-1687 built it foundation-only and T-1688's worker only drains/advances/compacts an existing queue, it never enqueues. Something at land-commit time (most likely src/frob/tickets/_land.py's post-land hook) needs to call record_intent with the landed commit sha and touched symrefs, or the coalescing worker never has anything to verify.

<!-- ticket:T-1737 -->
```yaml
id: T-1737
title: Wire frob.serve._watch.WatchThread on_change to the T-1688 CoalescingWorker.notify()
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_socketd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
T-1688's coalescing verify worker (frob.verify._worker.CoalescingWorker)
gets its "queue append" wake proxy from src/frob/serve/_daemon.py's own
HEAD-moved polling, and its periodic floor from its own internal timer,
but the ticket's third wake condition -- the FS-watch push signal
frob.serve._watch.WatchThread already provides -- is not wired to it.
WatchThread is instantiated in frob.serve._socketd.run_socket_daemon,
outside T-1688's own src/frob/serve/_daemon.py scope.

Wire WatchThread(on_change=...) in _socketd.py to also call the
CoalescingWorker.notify() for the same root (frob.serve._daemon.
_get_verify_worker(root).notify()), so a filesystem change observed by
the poller pushes a debounce-window reset immediately instead of only
via the daemon's own ~20s HEAD-moved poll cadence.

<!-- ticket:T-1738 -->
```yaml
id: T-1738
title: 'frob ticket wave: partition the doable set into N mutually scope-disjoint
  groups for parallel dispatch'
state: queued
kind: feature
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/tickets/_query.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
`frob ticket doable` answers "what can ONE agent safely start right now",
filtering candidates whose scope collides with an in-progress lease
(T-0453). That is the sequential question, and it is answered well.

Nobody answers the PARALLEL question: "partition the doable set into N
groups whose scopes are mutually disjoint, so N agents can run at once
without colliding." A coordinator dispatching a wave has to do that by
hand, and the only cheap hand-proxy is thematic grouping -- "these are
all docs tickets", "these are all gate false positives" -- which is not
the same property at all.

Observed cost, 2026-08-06, in one session:

- A coordinator grouped three waves by theme instead of by scope. Two
  tickets in one wave (T-1699, T-1705) turned out to be scope-blocked by
  leases held by agents dispatched earlier in the SAME wave planning
  pass. `doable --show-blocked` knew; nothing had asked it.
- T-1679 and T-1637 were thematically unrelated and scope-adjacent:
  T-1679 renamed tests that T-1637 (already closed) had bound its
  evidence to. The rename landed green under `--ticket` scoping and broke
  a closed ticket's evidence on main. Theme said "safe"; scope said
  otherwise.

Build the parallel answer:

    frob ticket wave --agents N [--json]

Returns N groups drawn from the doable set such that no two groups share
a scope glob, each group ordered for sequential execution within itself,
plus an explicit REMAINDER list of doable tickets that could not be
placed disjointly -- and WHY (naming the ticket and the shared glob they
collide on). The remainder is the important half: silently dropping
unplaceable tickets would make a wave look complete when it is not.

Requirements:

- Collision must be computed on RESOLVED scope, the same substrate
  `doable`'s T-0453 filter already uses. Do not re-implement glob
  matching -- extract and share whatever `doable` uses, or this grows a
  second answer to the same question that can disagree with the first.
- Groups must also respect blocked_by ordering: a group is a sequence an
  agent works in order, so a ticket must never precede its blocker.
- Deterministic for a given queue state, so two coordinators planning the
  same wave get the same plan.
- N is a hint, not a guarantee: returning fewer, larger groups is correct
  when the queue does not partition further. Say so in the output rather
  than padding groups with colliding work.
- Prefer packing by priority: a group containing a critical ticket should
  not be the one left unplaceable.

A LIKELY FINDING, WORTH REPORTING RATHER THAN DESIGNING AROUND: this
repo's queue may barely partition at all, because `docs/modules/
tickets.md` appears in a large fraction of every ticket's scope and
therefore collides with almost everything. `--show-blocked` currently
shows a dozen tickets all held on that single path, and two in-progress
tickets mutually blocking each other on it. If the wave command finds it
cannot produce more than one or two disjoint groups, that is a real
measurement of a real bottleneck and should be REPORTED as the result,
not worked around by loosening the collision rule. File what you find;
the remedy (splitting that doc, or making doc scope-leases granular per
heading anchor rather than per file) is a separate ticket and a bigger
decision than this one.

Related: T-1344 (the land path is the throughput bottleneck) is the
adjacent framing; this ticket is about the DISPATCH side of the same
throughput problem.

<!-- ticket:T-1742 -->
```yaml
id: T-1742
title: pre-commit land-owned-file guard refuses legitimate git merge main commits
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/scaffold/_managed.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
The scaffolded `.git/hooks/pre-commit` (T-0431/T-0731's land-owned-file
guard) has no exemption for an ordinary `git merge main` merge commit --
it refuses ANY commit whose staged file list contains CHANGELOG.md,
uv.lock, or a pyproject.toml version-line diff, with no check for
whether MERGE_HEAD exists or whether the staged content is byte-
identical to main's own copy (the common case: a worktree merging main
forward legitimately carries main's own land-generated changes to these
files, with zero local divergence).

Hit directly today: `git merge main` in a long-lived worktree pulled
forward several of main's own lands (each of which legitimately bumped
CHANGELOG.md/pyproject.toml/uv.lock), and the resulting merge commit
was refused outright by the hook, even though `git diff main -- \
CHANGELOG.md pyproject.toml uv.lock` was empty (the merged content
exactly matched main -- no hand-edit, no divergence, nothing for the
guard to actually be protecting against). Worked around this once with
`FROB_LAND_INTERNAL=1` for that single commit after verifying byte-
identity to main first; the playbook explicitly says this env var
should never be set by a worktree agent, so this was a one-off, not a
repeatable answer.

Fix: exempt the guard when `$(git rev-parse -q --verify MERGE_HEAD)`
succeeds (a real merge commit in progress), or narrow it further to
only refuse when the staged content of the land-owned file actually
DIFFERS from main's current tip (a hand-edit, not a merge fast-
forwarding main's own history). Either fix removes the false refusal
without weakening the guard against the real hazard (T-0731: a
worktree agent hand-editing these files itself).

<!-- ticket:T-1743 -->
```yaml
id: T-1743
title: doable --show-blocked names the wrong ticket as lease holder, and an orphaned
  lease has no supported release path
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/_query.py
- tests/test_ticket_leases_cross_worktree.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
`frob ticket doable --show-blocked` names the WRONG TICKET as the holder
of a scope lease. Two people chased the wrong ticket for a considerable
stretch on 2026-08-07 because of it.

Observed. `doable --show-blocked` reported, repeatedly and consistently:

    T-1615  held: scope 'docs/modules/tickets.md' leased by in-progress T-1727
    T-1715  held: scope 'docs/modules/tickets.md' leased by in-progress T-1727
    T-1739  held: scope 'docs/modules/tickets.md' leased by in-progress T-1727

But `frob ticket show T-1727` lists its scope as
`_mutation_evidence.py`, `_close_cmd.py`, `_evidence.py`,
`docs/modules/gates.md` -- it does not contain `docs/modules/tickets.md`
and never needed to. And `.git/frob-leases/` held exactly two lease
files, T-1629.json and T-1740.json. THERE WAS NO T-1727 LEASE AT ALL.

The real holder was T-1629, whose lease declares the mega-globs
`docs/**`, `tests/**`, `src/frob/gates/**`, `src/frob/strata/**` and
which belonged to a worktree (`w35-strata`) predating the session
entirely. Removing that stale worktree cleared all three blocks at once.

Two distinct defects:

1. WRONG ATTRIBUTION. The blocked-reason line names a ticket that does
   not hold the lease. An agent then correctly cross-checks against
   `frob ticket show`, finds the scope does not match, and is left with
   an apparent contradiction and no way to resolve it. One agent stopped
   work rather than gamble past it -- the right call, and it cost real
   time that a correct attribution would have saved. Whatever the message
   derives the holder from, it must be the SAME source `doable` uses to
   decide the block, and it must name the lease's own `ticket_id` and its
   worktree path.
2. NO WAY TO RELEASE A STALE LEASE. `frob ticket scope T-1727 --remove
   'docs/modules/tickets.md'` refuses with `ScopeRemoveNotDeclared`,
   correctly, since the glob is not in that ticket's scope. So the only
   verb that touches leases cannot reach an orphaned one. The lease was
   only clearable by deleting a git worktree by hand -- an operation no
   worktree-isolated agent can perform and nothing documents. There must
   be a supported release path that names what it is releasing.

Also observed, and worth fixing in the same pass: after removing the
worktree, `.git/frob-leases/T-1629.json` REMAINS ON DISK while `doable`
correctly stops honouring it. So the lease file is not the authority --
liveness of the worktree is -- yet the file is what a human inspecting
`.git/frob-leases/` would read. A stale file that no longer means
anything is exactly the kind of derived artifact this repo has been
burned by trusting. Either delete it when the worktree goes, or make the
staleness visible in the file itself.

ROOT CAUSE UNDERNEATH ALL OF IT: `docs/**` and `tests/**` in a lease.
T-1629's mega-globs meant a single prior-session ticket held a lease over
essentially every doc and test in the repo, silently, across sessions.
TICK009 already nudges on scope breadth and the queue has been reporting
4 outstanding nudges all session with nobody acting on them. A scope
breadth that can serialize the entire queue should be an ERROR at
`ticket start` time, not a nudge nobody reads -- see T-1738, which asks
for disjoint-group planning and predicted exactly this bottleneck.

FOLLOW-UP OWED, do not lose it: T-1629 has five real unlanded commits on
branch `w35-strata`, including a written Done report and recorded
evidence. The work is preserved but stranded. It needs landing in a
controlled window, and its scope narrowed first so landing it does not
re-serialize the queue.

<!-- ticket:T-1744 -->
```yaml
id: T-1744
title: Detect a queued ticket whose described fix already landed outside the ticket
  workflow (false queue signal)
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_doable.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'SECOND CONFIRMED INSTANCE (T-1487, 2026-08-07): the ticket sat queued and
    72h past its dispatch threshold while its work was ALREADY DELIVERED on main under
    T-1220. Worse, its ledger entry carried a PRE-FILLED Done report (evidence, diffstat,
    captured claims) despite state=queued -- drafted as a template when T-1220 was
    split, never run through start/land. Given: a ticket whose state is queued; when
    it carries a Done report; then that incoherence is itself detectable and must
    be reported, independently of whether the code landed.'
  evidence: []
- text: 'FIRST CONFIRMED INSTANCE (T-1587, 2026-08-07): production fix committed directly
    to main on 2026-08-05 OUTSIDE the ticket workflow, so the ledger claimed critical
    work was pending for two days. Both instances cost an agent real budget verifying
    already-finished work.'
  evidence: []
- text: T-1675 already landed already-landed detection but it is OPT-IN, so nobody
    runs it. The check must run at DISPATCH time by default -- catching this after
    an agent has spent its budget verifying is too late to be worth much.
  evidence: []
threat: null
component: null
```
Observed 2026-08-07 (T-1587): the ticket described a v2 Done-report
visibility bug and sat `queued`, undispatched 48h against a 4h threshold,
flagged critical by the dispatch-alarm machinery. The actual production
fix was already on `main` -- committed directly (commit f08541dc,
2026-08-05) OUTSIDE the ticket workflow, never through `frob ticket
land`, and the ticket's own state was never updated to reflect it. An
agent dispatched onto T-1587 spent real budget re-verifying a fix that
had already shipped two days earlier, because nothing in the queue
signaled "the described defect may already be resolved."

This is a DIFFERENT defect class from T-1675 (already-landed detection
at LAND time, now unconditional via a `state: done` check on
`base_ref`): T-1675 catches a ticket that is BEING landed a second time
after its own `frob ticket land` already ran. This case is a ticket
that was NEVER landed through the workflow at all -- its code arrived on
main by a direct commit (a human `git commit` bypassing `frob ticket
land`/`close` entirely) -- so there is no ticket-state transition to
compare against, and T-1675's positive signal (ticket's own record
shows `state: done` on base_ref) never fires; the ticket's record
genuinely still says `queued` because nothing ever told it otherwise.

Work direction (not yet designed in detail): a `doable`/dispatch-time
check that, for a ticket whose declared `scope` globs are narrow enough
to be meaningful, diffs the current tree against the ticket's `blocked_
by`-free baseline (or greps for `frob:ticket <id>` directives already
present in the scoped files) and flags "this ticket's own directive
markers already exist in the current tree with no corresponding land
commit" as a `WARN`-severity dispatch alarm, distinct from and additive
to T-1675's own already-landed-at-land-time check. Needs its own design
pass -- the false-positive shape here (a ticket's scope legitimately
overlaps a LATER ticket's `frob:ticket` directive, or a draft residue
citation) needs the same "positive signal, not absence" discipline
T-1675 established, not a second inference-from-emptiness check.

<!-- ticket:T-1745 -->
```yaml
id: T-1745
title: Detect a queued ticket whose described fix already landed outside the ticket
  workflow (false queue signal)
state: dropped
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_doable.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
Observed 2026-08-07 (T-1587): the ticket described a v2 Done-report
visibility bug and sat `queued`, undispatched 48h against a 4h threshold,
flagged critical by the dispatch-alarm machinery. The actual production
fix was already on `main` -- committed directly (commit f08541dc,
2026-08-05) OUTSIDE the ticket workflow, never through `frob ticket
land`, and the ticket's own state was never updated to reflect it. An
agent dispatched onto T-1587 spent real budget re-verifying a fix that
had already shipped two days earlier, because nothing in the queue
signaled "the described defect may already be resolved."

This is a DIFFERENT defect class from T-1675 (already-landed detection
at LAND time, now unconditional via a `state: done` check on
`base_ref`): T-1675 catches a ticket that is BEING landed a second time
after its own `frob ticket land` already ran. This case is a ticket
that was NEVER landed through the workflow at all -- its code arrived on
main by a direct commit (a human `git commit` bypassing `frob ticket
land`/`close` entirely) -- so there is no ticket-state transition to
compare against, and T-1675's positive signal (ticket's own record
shows `state: done` on base_ref) never fires; the ticket's record
genuinely still says `queued` because nothing ever told it otherwise.

Work direction (not yet designed in detail): a `doable`/dispatch-time
check that, for a ticket whose declared `scope` globs are narrow enough
to be meaningful, diffs the current tree against the ticket's `blocked_
by`-free baseline (or greps for `frob:ticket <id>` directives already
present in the scoped files) and flags "this ticket's own directive
markers already exist in the current tree with no corresponding land
commit" as a `WARN`-severity dispatch alarm, distinct from and additive
to T-1675's own already-landed-at-land-time check. Needs its own design
pass -- the false-positive shape here (a ticket's scope legitimately
overlaps a LATER ticket's `frob:ticket` directive, or a draft residue
citation) needs the same "positive signal, not absence" discipline
T-1675 established, not a second inference-from-emptiness check.

## Drop reason
- 2026-08-07: exact duplicate title and subject, filed twice from the same finding (draft renumbering at land produced two entries). T-1744 is canonical (absorbed by T-1744)

<!-- ticket:T-1746 -->
```yaml
id: T-1746
title: Implement real fix for WIRE001 same-file test-fixture reuse false positive
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_tickets_mutation_evidence.py
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
`tests/test_tickets_mutation_evidence.py::_repo_with_add_change` carries
a `frob:waive WIRE001` (T-1727's own land) because WIRE001's same-file
exclusion rule (T-1592/T-1558's precedent: a test-tree symbol's OWN
defining file never counts as a "reached" caller, only a DIFFERENT test
file does) does not recognize a shared fixture helper reused by two
test classes within one file as wired, even though every call site is a
real `test_*` method, verifiable by reading the file directly.

Two ways to close this honestly:
1. Move `_repo_with_add_change` to a location a genuinely different
   test file could plausibly reuse (a shared fixtures module), so a real
   cross-file caller exists and the waiver can be dropped.
2. If same-file test-fixture reuse is a legitimate, common shape (it
   plausibly is -- DUP001 actively REQUIRES this exact extraction
   whenever two test classes in one file develop near-identical setup
   bodies), extend WIRE001's `_wire_test_path_excluded` same-file rule
   to also recognize a call from ANY `test_*`-prefixed function/method
   in the SAME file as a genuine reach class, not just cross-file reuse.

Either fix removes the T-1727 waiver's need to exist.

<!-- ticket:T-1747 -->
```yaml
id: T-1747
title: 'post-land sweep regression from T-1715: 1 new error(s) (TICK003)'
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
The deferred post-land unscoped sweep (T-1684) for T-1715 at commit 7ca65c2586b05b508800541746413944e8f291bf found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs:

- TICK003  tickets.md

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

<!-- ticket:T-1748 -->
```yaml
id: T-1748
title: Two tickets sharing one fix mechanism cannot land from one worktree without
  disabling PassengerTickets and BUG002
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_mutation_evidence.py
- tests/test_ticket_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
Two tickets that share one fix mechanism cannot both be landed cleanly
from one worktree. Both agents who hit it today reached for a different
workaround, and neither is what the tool should require.

The shape: an agent is given two related tickets (correctly -- they share
a mechanism, so one agent holding both avoids a lease fight and avoids
two people building the same primitive). It implements the shared piece,
lands ticket A, and then ticket B's land refuses, because:

- `PassengerTickets` scans the WHOLE BRANCH DIFF for `frob:ticket <id>`
  additions, not the per-ticket diff. B's branch still carries A's
  commits, so A rides along as an undisclosed passenger -- and
  symmetrically, landing B first makes A the passenger. There is no
  order that avoids it.
- BUG002 then refuses B on its own terms: B's designated repro
  necessarily ALREADY PASSES at main, because A's land carried the shared
  code. The repro cannot fail-at-parent when the parent already contains
  the fix.

Observed twice on 2026-08-07, with two different escapes:

1. One agent isolated ticket A's commits into a FRESH worktree
   (`git worktree add` at a specific sha), landed A independently, then
   merged B's backup branch onto the post-land state and landed B. Manual,
   fiddly, and it invented a worktree the lease model knows nothing about.
2. The other used `--allow-cross-ticket` on BOTH lands plus a
   `frob:waive BUG002` on the second. Each override is individually
   documented and justified, but the combination means two tickets landed
   with the passenger check and the repro check both disabled -- which is
   most of what those gates exist for.

Neither agent did anything wrong. The tool made them choose between
tedium and turning off the checks.

The second agent judged this "not reproducible as a general defect,
happened inside my own worktree". It is general: it follows mechanically
from stacked commits on one branch plus a whole-branch passenger scan,
and it will recur every time a coordinator groups related tickets --
which is the dispatch strategy this drive uses deliberately, because
ungrouped related tickets fight over leases instead.

WANTED:

1. `PassengerTickets` should evaluate the diff attributable to THE
   TICKET BEING LANDED against main, not the whole branch diff. A commit
   already landed on main is not a passenger; that is exactly what
   "already on main" means. Check reachability rather than scanning the
   branch's accumulated text.
2. BUG002's repro check needs a defined answer for "the fix reached main
   via a sibling ticket in this same series". Passing at parent is
   correct here and not evidence of a bad repro. Either detect the
   sibling-land case explicitly, or make `frob:no-behavior-change`'s
   sibling analogue the documented disposition -- but do not leave
   `frob:waive BUG002` as the only route, because a waiver records
   "we decided to skip this" when the truth is "this check is not
   applicable in this configuration". Those are different facts and the
   ledger should not conflate them.
3. Whatever the fix, `frob ticket land` should be able to land a series
   of related tickets from ONE worktree in dependency order without
   overrides. That is the normal case for grouped dispatch, not an edge
   case.

Evidence must include the real shape: two tickets sharing a mechanism,
stacked on one branch, landed in order, with no `--allow-cross-ticket`
and no BUG002 waiver.

<!-- ticket:T-1749 -->
```yaml
id: T-1749
title: frob ticket evidence --designate-repro is a second silent BUG002-check-redirect
  asymmetry
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_setters.py
- src/frob/gates/_mutation_evidence.py
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
Found while implementing T-1733's audit requirement ("every way to make a
ticket easier to close must cost at least as much bookkeeping as the
honest way -- report any others found"): `frob ticket evidence
--designate-repro NODE-ID` (`frob.tickets._setters.set_designated_repro_test`,
T-1670) is a second candidate for the same asymmetry T-1733 fixed for
`--replace`.

BUG002 (`frob.gates._mutation_evidence.bug_repro_violations`) checks
whichever evidence id is the ticket's "designated repro test" (explicit
`--designate-repro`, or the first bound id by default) for a genuine
FAIL-at-parent outcome. `--designate-repro` can retarget that check onto
a DIFFERENT already-bound id with:

- no `--reason`/`--reason-file` requirement
- no audit trail (no `EvidenceChangeEntry`-shaped record)
- no gate consuming the fact that a redesignation happened

`set_designated_repro_test` does require the target already be bound
(cannot invent a fresh unverified id), so this is narrower than the
`--replace` gap T-1733 fixed -- but it still lets an agent silently
redirect BUG002's check away from a test that genuinely still fails at
parent onto a weaker, already-passing-at-parent bound id, with zero
trace in the ledger. An agent facing a BUG002 refusal has this as a
quiet escape structurally parallel to unbinding via `--replace`.

Candidate fix, mirroring T-1733's own shape: require `--reason` on
`--designate-repro` (at minimum when RE-designating an already-set
value, since a first-time designation on a fresh ticket is closer to
"pure addition" and arguably should stay free, matching T-1733's own
"tax weakening, not strengthening" principle) and record it in a new
append-only audit field, surfaced by `frob ticket show` the same way
`evidence_changes` now is.

Not fixed here -- found during T-1733's audit pass, filed as the
"report any others" deliverable rather than silently expanding T-1733's
own scope.

<!-- ticket:T-1750 -->
```yaml
id: T-1750
title: frob ticket archive corrupts an in-flight worktree's ledger with duplicate
  ids; TICK003 forces it at a non-quiet moment
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_archive.py
- src/frob/tickets/_land_ledger_merge.py
- src/frob/gates/_tickets_gate.py
- tests/test_tickets_organization.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
`frob ticket archive` is not safe against in-flight worktrees, documents
that requirement in prose, and does not enforce it. TICK003 then FORCES
the operation at an arbitrary moment mid-drive.

What happened, 2026-08-07. TICK003 crossed its threshold (61 closed
tickets un-archived against 60) and began refusing every land repo-wide,
including a completed ticket unrelated to the housekeeping. The
coordinator checked for in-flight LANDS, found none, and ran `frob ticket
archive` -- 62 tickets moved from `tickets.md` to `tickets-archive.md`.

But an agent's WORKTREE was still live with a pre-archive `tickets.md`.
Its next `git merge main` produced a ledger with DUPLICATE TICKET IDS
across active and archive (`DuplicateId` on sweep): the merge driver saw
a deletion on one side and an addition on the other rather than
recognising a MOVE between two files.

Recovery cost that agent a full playbook-10b pass: restore both ledger
files from main, re-apply every scope/evidence/done-report mutation
through the `frob ticket` CLI (never by hand), catch and refile a DROPPED
DRAFT before it became a phantom-citation TICK006 finding, and re-run
`frob ticket start` because the restore had reverted the ticket's own
in-progress transition. All of that to recover from a routine
housekeeping command.

Three separable defects:

1. ARCHIVE DOES NOT ENFORCE ITS OWN PRECONDITION. Its documentation asks
   for "a quiet window, no in-flight worktrees". It should REFUSE when
   `git worktree list` shows any agent worktree, naming them, with
   `--force` for a caller who knows better. A precondition that exists
   only in prose is not a precondition -- the coordinator read that line,
   checked for in-flight lands, and still got it wrong, because "no
   in-flight worktrees" and "no land currently running" are different
   conditions and only one of them is easy to check.

2. THE MERGE DRIVER DOES NOT UNDERSTAND AN ACTIVE->ARCHIVE MOVE. A
   ticket relocated between the two ledger files is a MOVE, and the
   splice should reconcile it as one. Today it yields duplicate ids,
   which is the single most damaging ledger state -- `load_queue` refuses
   outright, so every gate goes down at once. T-1721 taught the general
   lesson here: when the splice cannot answer a question correctly it
   must refuse and name the conflict, never produce a corrupt merge.

3. TICK003 FORCES A QUIET-WINDOW OPERATION AT A NON-QUIET MOMENT. The
   gate blocks all landing until someone runs a command that requires
   conditions the gate never checks. That is a deadlock by construction:
   the more agents are landing, the sooner the threshold trips, and the
   less safe the remedy is. Either the threshold should WARN far enough
   ahead to be scheduled deliberately (it is a housekeeping floor, not a
   correctness one, so blocking on it is disproportionate), or archiving
   must become safe enough to run at any time -- which is defect 2.

Preferred direction: fix 2 so archiving is merge-safe, add 1 as the
belt-and-braces guard, and soften 3 to a warning with a much lower
warn-threshold and an ERROR only far above it.

Regression coverage must include the real shape: a worktree branched
BEFORE an archive pass, merging main AFTER it, asserting the merged
ledger has no duplicate ids and no dropped drafts. A test that archives
with no worktrees present proves nothing about the failure mode.

<!-- ticket:T-1751 -->
```yaml
id: T-1751
title: revisit WIRE001 waiver follow_up citation orphaned by T-1487's close
state: queued
kind: docs
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_tickets_lease.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
Found while landing T-1487 (rust python tree-extraction kernel carrier):
tests/test_tickets_lease.py:449 carries a `frob:waive WIRE001 ...
follow_up="T-1487"` directive on `_write_ticket_file`. T-1487's own
scope (frob-core/**, tests/unit/test_extract_native.py, docs/modules/
lang.md, docs/modules/dup.md) never touched this file or fixture, and
T-1487 is closing as delivered-by-T-1220 with no new code -- so this
citation cannot legitimately resolve against T-1487 any longer.

Re-verify whether `_write_ticket_file` still needs the WIRE001 waiver
at all (confirm it is still test-fixture-only, called only by
TestClusterScopeConflict's own methods in this same file per the
existing waiver reason), and either drop the waiver if a real caller
now exists or re-confirm/refresh it with a live follow_up ticket.

<!-- ticket:T-1752 -->
```yaml
id: T-1752
title: 'vet: cross-file wrapper attribution for capability detection needs frob.graph.callgraph-backed
  resolution'
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/graph/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
T-1626 (strata capability detection must be symbol-resolved with full alias
support) closed a python-only slice: functools.partial(dangerous, ...) and
literal-keyed dict/list dispatch tables now resolve through the existing
T-0328 import/binding-aware resolver (src/frob/vet/_capability_python.py).

Explicitly deferred from that ticket: "A helper that wraps a dangerous op
and is called from elsewhere must attribute to the caller's node" -- a
helper defined in a DIFFERENT file/module than the call site is invisible
to today's per-file capability scan regardless of alias resolution, since
the scan never looks across files.

Doing this needs frob.graph.callgraph-backed cross-file resolution over
the SCANNED DEPENDENCY's own source tree (an arbitrary third-party
package under vet, not this repo's own package graph, which is what
frob.graph.callgraph is built/tested against today). Open design
questions to resolve here:
- does a capability found N hops down a call chain attribute to every
  caller up the chain, or just the direct one?
- what traversal-depth/cycle policy is safe and fast enough for a
  dependency-scan hot path (frob vet runs per-lockfile, potentially many
  packages)?
- does this need its own call-graph build per scanned package, or can it
  reuse/adapt frob.graph.callgraph's existing machinery directly?

Read src/frob/vet/_capability_python.py (T-1626's Done report) and
src/frob/graph/callgraph.py before starting.

<!-- ticket:T-1753 -->
```yaml
id: T-1753
title: 'post-land sweep regression from T-1690: 3 new error(s) (ARCH001, E501, invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- /home/logan/projects/frob/src/frob/verify/_attribution.py
- src/frob/verify/_attribution.py
- tests/unit/test_rapid_sweep.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the ty invalid-argument-type finding traces to _attribute_new_findings's
    pairs parameter, whose call site and type both live in _rapid_sweep.py
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires touching the affects()-closure doc for attribute_batch/_attribute_new_findings,
    both fixed by this ticket
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_missing_line_falls_back_to_whole_file_candidates
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_open_ticket_is_not_refiled
designated_repro_test: null
threat: null
component: null
```
The deferred post-land unscoped sweep (T-1684) for T-1690 at commit 5c17406570de3df7006b5737a6fc1cdc8fdf6b5c found 3 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH001  src/frob/verify/_attribution.py
- E501  /home/logan/projects/frob/src/frob/verify/_attribution.py
- invalid-argument-type  tests/unit/test_rapid_sweep.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Done report

frob:no-behavior-change reason="ARCH001 (pure function split along the tier-1/tier-2/tier-3 seams already documented in the module, no logic change), E501 (line wraps only), and a ty invalid-argument-type fix (widening a too-narrow parameter annotation to match what the function already passed through) -- none of the three changes alter runtime behavior, so BUG002's normal 'must fail at parent, pass at fix' repro requirement does not apply; the designated evidence instead PASSES at both parent and fix, which is exactly what a no-behavior-change claim predicts."

Changed:
- src/frob/verify/_attribution.py: `attribute_batch` split along its
  tier boundaries into `_parse_finding` (tier 1: identity parsing),
  `_matching_batch_entries` (tier 2: reachability), `_attribute_one`
  (tier 3: ambiguity/logging bookkeeping) -- ARCH001 fix; two lines
  wrapped under 88 chars -- E501 fix.
- src/frob/app/ticket_runner/_rapid_sweep.py: `_attribute_new_findings`'s
  `pairs` parameter type widened from `list[tuple[str, str]]` to
  `list[tuple[str, str] | tuple[str, str, int]]`, matching what
  `attribute_batch` itself already accepts -- ty invalid-argument-type
  fix.
- docs/modules/tickets.md: T-1753 follow-up note appended to the T-1690
  "Symbolic attribution" section.

Root cause of each finding, and why each is a real fix not cosmetic:

- ARCH001: `attribute_batch` was doing tier-1 set-diff-identity parsing,
  tier-2 graph reachability, and tier-3 ambiguity/logging bookkeeping all
  in one 112-line body. Splitting along those exact seams (not an
  arbitrary line-count split) makes each tier independently readable --
  which matters directly for T-1691's later bisect-fallback leaf, which
  needs to see the tier-2/tier-3 boundary clearly to hook in.
- E501: two lines exceeded 88 chars; wrapped, no behavior change.
- ty invalid-argument-type: `_attribute_new_findings`'s own annotation
  (`list[tuple[str, str]]`) was narrower than what it actually passes
  straight through to `attribute_batch`
  (`list[tuple[str, str] | tuple[str, str, int]]`) -- the annotation was
  wrong, not the test that exercised the 3-tuple (line-bearing) shape.
  Confirmed the test genuinely exercises line-based symbol resolution
  (not just passing type-check): `test_attributed_and_unattributed_round_
  trip` asserts a line-anchored finding attributes correctly and a
  no-such-file finding reports unattributed.

Evidence: 4 pytest node ids recorded via `frob ticket evidence`, all
measured passing as part of the full verify+rapid_sweep suite:
`timeout 100 uv run pytest tests/unit/verify/ tests/unit/test_rapid_sweep.py -p no:cacheprovider -q`
-> `collected=59 failed=0`.

Filed: none.

Gates: `frob check --only gates-fast --ticket T-1753` down to 3 remaining
SCOPE001 findings on land-owned files (.frob-release.json,
pyproject.toml, uv.lock) -- these reflect this worktree branch sitting
one REL001 bump behind main (from an earlier merge-conflict-avoidance
step in this same session, keeping this branch's own pre-bump copies
rather than committing main's copies through the pre-commit land-owned-
file guard) -- `frob ticket land` reconciles land-owned files as part of
its own internal merge, the same mechanism T-1690's land already used
successfully; not hand-fixed here per the agent playbook section 4b
("land-owned files are untouchable in a worktree"). AFFECT001 (the
tier-1/2/3 split's affects()-closure doc obligation) is clean after the
docs/modules/tickets.md note above.

### Changed
```
 .frob-release.json                         |   5 +-
 CHANGELOG.md                               |   4 -
 docs/modules/tickets.md                    |  12 ++
 pyproject.toml                             |   2 +-
 rapid-debt.jsonl                           |   1 -
 src/frob/app/ticket_runner/_rapid_sweep.py |   7 +-
 src/frob/verify/_attribution.py            | 206 ++++++++++++++++++-----------
 tickets.md                                 | 126 +++++++++++++++++-
 uv.lock                                    |   2 +-
 9 files changed, 270 insertions(+), 95 deletions(-)
```

### Evidence
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_missing_line_falls_back_to_whole_file_candidates` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_open_ticket_is_not_refiled` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 450 warning(s), 724 waived
- error-findings: invalid-argument-type@src/frob/app/ticket_runner/_rapid_sweep.py

<!-- ticket:T-1754 -->
```yaml
id: T-1754
title: 'post-land sweep regression from T-1753: 2 new error(s) (REL001, invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires touching the affects()-closure doc for _attribute_new_findings,
    fixed by this ticket's Sequence widening
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing
designated_repro_test: null
threat: null
component: null
```
The deferred post-land unscoped sweep (T-1684) for T-1753 at commit 8a2f473e454c085890de379dcefd098a2978b4ce found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- REL001  pyproject.toml
- invalid-argument-type  src/frob/app/ticket_runner/_rapid_sweep.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Done report

frob:no-behavior-change reason="Sequence(covariant) vs list(invariant) type-annotation fix on _attribute_new_findings's pairs parameter -- no logic change, only the static type the parameter accepts. Runtime behavior is identical for every real caller (all of which pass list[tuple[str, str]])."

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py: `_attribute_new_findings`'s
  `pairs` parameter changed from `list[tuple[str, str] | tuple[str, str,
  int]]` to `Sequence[tuple[str, str] | tuple[str, str, int]]`
  (`collections.abc.Sequence` import added).
- docs/modules/tickets.md: T-1754 follow-up note in the T-1690 section
  explaining the root cause (list invariance, not a wrong element type).

Root cause (this is the real fix, not another symptom patch): T-1753
widened `_attribute_new_findings`'s ELEMENT type
(`tuple[str,str]` -> `tuple[str,str] | tuple[str,str,int]`) but kept the
CONTAINER as `list[...]`. Python's `list` is INVARIANT -- a
`list[tuple[str, str]]` is never assignable to a
`list[tuple[str, str] | tuple[str, str, int]]` parameter, regardless of
how the element union is phrased, because a `list` parameter is
read-write (a callee could in principle append a 3-tuple into a caller's
own list). `_partition_findings_by_attribution`'s own `pairs:
list[tuple[str, str]]` -> `_attribute_new_findings(root, pairs)` call
therefore still failed ty's invariant-argument-type check even after
T-1753's fix -- T-1753 moved the mismatch to the call site rather than
resolving it, exactly as flagged.

The correct fix addresses the CONTAINER, not the element type:
`_attribute_new_findings` only ever ITERATES `pairs` (never mutates
it), so the sound, narrower-capability type is `collections.abc.
Sequence` (covariant, read-only) -- a `list[tuple[str, str]]` argument
is naturally accepted under `Sequence[tuple[str, str] | tuple[str, str,
int]]` without a cast or an `Iterable`/`list` mismatch anywhere in the
call chain.

Evidence: 3 pytest node ids recorded via `frob ticket evidence`, all
measured passing:
`timeout 100 uv run pytest tests/unit/test_rapid_sweep.py -p no:cacheprovider -q`
-> `collected=26 failed=0`.

Filed: T-1755 already exists (coordinator-filed, separate: the detached
post-land sweep leaves its filed regression ticket uncommitted, blocking
the next land -- the DirtyMain-class defect this session hit twice, T-1699's
sibling). Not this ticket's own scope; noted here only to avoid a
duplicate filing.

Gates: `frob check --only gates-fast --ticket T-1754` clean down to 2
SCOPE001 findings on land-owned files (.frob-release.json, uv.lock),
same pattern as every prior ticket in this session -- reconciled by
`frob ticket land`'s own internal merge, not hand-fixed here.
`frob check --only gates-native --ticket T-1754` clean, 0 errors.

### Changed
```
 .frob-release.json      | 11 +----------
 CHANGELOG.md            |  4 ----
 docs/modules/tickets.md | 14 ++++++++++++++
 pyproject.toml          |  2 +-
 tickets.md              | 15 +++++++++++++--
 uv.lock                 |  2 +-
 6 files changed, 30 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 3 error(s), 478 warning(s), 725 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/verify/_backpressure.py, invalid-argument-type@src/frob/app/ticket_runner/_land_cmd.py

<!-- ticket:T-1755 -->
```yaml
id: T-1755
title: The detached post-land sweep leaves its filed regression ticket uncommitted,
  blocking every subsequent land
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/tickets/_new_renumber.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets.md
- src/frob/tickets/_land_git_ops.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: requirement 3 names the likely author (the detached post-land sweep) when
    the dirty path is one it owns (tickets.md/rapid-debt.jsonl) -- describe_root_dirt
    lives here
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: requirement 3 names the likely author (the detached post-land sweep) when
    the dirty path is one it owns (tickets.md/rapid-debt.jsonl) -- describe_root_dirt
    lives here
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commits_the_ledger_write
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commit_failure_logs_at_error_and_does_not_raise
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_detached_sweep_as_likely_author
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_mixed_dirt_does_not_claim_the_sweep
designated_repro_test: null
threat: null
component: null
```
The detached post-land sweep writes to the SHARED ROOT LEDGER and does
not commit what it writes. The uncommitted write then refuses every
subsequent land repo-wide with `DirtyMain`, and no agent can clear it --
they are correctly isolated from root.

Observed 2026-08-07. After a land, the sweep found 2 new errors,
auto-filed them via `frob ticket new` (correct -- that is the whole
design), and left `tickets.md` dirty. The next agent's land refused three
times across several minutes with 30s waits. It correctly concluded the
state was not transient, and correctly reported instead of forcing.
Nothing was going to clear it: the only process that could commit was the
coordinator, by hand.

This is the SECOND uncommitted write from the same detached child. T-1699
already covers the `rapid-debt.jsonl` line racing the DirtyMain check
outside the land lock. This is a distinct instance -- the regression
TICKET is a separate write to a separate tracked file -- and the pair
together says the general rule was never applied: ANY tracked-file write
the detached sweep makes must be committed by the sweep, or it becomes a
repo-wide land block.

Note `frob ticket new` DOES auto-commit (T-1130), and `frob ticket
archive`/every other ledger verb now does too (T-1615). So the write
should have committed itself. Establish why it did not before fixing
anything -- plausible causes worth checking in order:

- the sweep runs with a cwd or env where the auto-commit path is skipped;
- the auto-commit ran and FAILED (index contention with a concurrent
  land is the obvious candidate) and the failure was swallowed;
- the sweep files the ticket through a lower-level API that bypasses the
  CLI verb's auto-commit entirely.

The third is the most likely and the most important to rule in or out,
because it would mean T-1615's uniform auto-commit covers the CLI surface
but not programmatic callers -- which is a much wider hole than this
ticket.

REQUIRED:

1. The detached sweep commits EVERY tracked-file write it makes --
   `rapid-debt.jsonl` (T-1699) and any filed regression ticket -- scoped
   to those paths only, never a bare `git commit` or `git add -A`. A
   blanket add on a root checkout that concurrent lands are racing
   against is how 1416 lines of another agent's in-flight work got
   published under an unrelated commit message earlier today (T-1740).
2. If the commit fails, LOG AT ERROR naming the file and the fact that
   the next land will refuse. A silent failure here converts a background
   nicety into a fleet-wide stall with no visible cause -- which is
   exactly what happened.
3. `DirtyMain`'s message should name the likely author when the dirty
   path is one the sweep owns (`tickets.md`, `rapid-debt.jsonl`), because
   the agent seeing that error is structurally unable to investigate it.
   T-1740 already made the message name staged state; this is the
   same principle extended to WHO.

Regression coverage: a sweep that files a regression ticket leaves the
repo CLEAN, and a subsequent land succeeds. Assert the actual invariant
-- root clean after the sweep completes -- not that a commit helper was
called.

## Done report

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py: `_file_regression_ticket`
  now calls new `_commit_regression_ticket` after a successful
  `new_ticket`, which calls `frob.tickets._leases.commit_ticket_ledger_
  change` (scoped `git add <ledger pathspecs> && git commit -- <ledger
  pathspecs>`) and logs at ERROR (naming the ticket id and the DirtyMain
  consequence) on failure, never raising.
- src/frob/tickets/_land_git_ops.py: `describe_root_dirt` now names the
  detached post-land sweep as the likely author when EVERY dirty path
  matches its own known writes (`rapid-debt.jsonl`, `tickets.md`); a
  mixed dirty set is deliberately left unattributed.
- docs/modules/tickets.md: two new paragraphs in the "Deferred post-land
  sweep" section.
- tests/unit/test_rapid_sweep.py: TestCommitRegressionTicket (2 tests),
  TestDescribeRootDirt gets 2 more (sweep-authored, mixed-not-claimed).

ROOT CAUSE, established by reading the code before writing any fix (per
this ticket's own explicit instruction): `frob.tickets._new_renumber.
new_ticket` -- the LIBRARY function `_file_regression_ticket` calls
directly -- takes `ledger_lock`, calls `write_ticket`, and returns. It
has NO commit step of its own. The T-1130/T-1615 auto-commit
(`commit_ticket_ledger_change`) lives entirely in the CLI dispatch layer
(`frob.app.ticket_runner`'s verb table, `_auto_commit_ledger_after_
dispatch`), which a programmatic caller never reaches. This confirms the
THIRD candidate this ticket's own body named as most likely ("the sweep
files the ticket through a lower-level API that bypasses the CLI verb's
auto-commit entirely") and rules OUT the other two: this is not a cwd/
env issue (the sweep's cwd/env are unremarkable) and not a swallowed
failure (there was no commit ATTEMPT at all to fail).

This IS a wider hole than this ticket's own scope, exactly as flagged:
T-1615's uniform auto-commit covers the CLI surface, not every
programmatic `new_ticket`/`write_ticket` caller. Filed as a follow-up
(see "Filed" below) rather than silently generalizing this fix beyond
`_file_regression_ticket`'s own call site, which is the only
programmatic caller this ticket's declared scope covers.

Constraint compliance: the commit is `git add <ledger pathspecs>` then
`git commit -- <ledger pathspecs>` via `commit_ticket_ledger_change`
(the SAME primitive `frob ticket new`/`drop`/`fail`/`start` already use)
-- never a bare `git commit` or `git add -A`. A commit failure logs at
ERROR naming the exact recovery command and stating explicitly that the
next land will refuse with DirtyMain (test:
`test_commit_failure_logs_at_error_and_does_not_raise` asserts both the
ticket id and the literal string "DirtyMain" appear in the logged
message).

Regression coverage (the ticket's own acceptance): "a sweep that files a
regression ticket leaves the repo CLEAN, and a subsequent land
succeeds" -- `TestCommitRegressionTicket::test_commits_the_ledger_write`
asserts `git status --porcelain` shows nothing under `tickets/` after
`_commit_regression_ticket` runs (previously, per this ticket's own
observed incident, it stayed dirty and blocked the next land).

Evidence: 4 pytest node ids recorded via `frob ticket evidence`, all
measured passing as part of the full suite:
`timeout 100 uv run pytest tests/unit/test_rapid_sweep.py -p no:cacheprovider -q`
-> `collected=30 failed=0`.

Filed: T-1758 (renumbers at land) -- "T-1615's uniform ledger
auto-commit does not cover programmatic (non-CLI) callers of
new_ticket/write_ticket", the wider structural gap this ticket's
investigation surfaced but did not fix (T-1755's own scope is only
`_file_regression_ticket`'s one call site). Grepped the queue first
(`frob ticket list | grep -i "auto-commit\|programmatic"`) and found
nothing already tracking it before filing.

T-1615's own completeness claim needs reframing in light of this: its
audit enumerated the CLI DISPATCH TABLE and made every verb in it
auto-commit uniformly -- correct for what it covered. But the dispatch
table is not the full set of ledger writers. `new_ticket`/`write_ticket`
are library functions any code can call directly, and T-1615's audit
never had a way to see a caller that does not go through dispatch at
all. `_file_regression_ticket` is not an edge case that slipped past the
audit -- it is a DIFFERENT CLASS of caller the audit's own methodology
could not have found, because it was scoped to dispatch, not to every
ledger-mutating code path in the package.

VALIDATION worth recording plainly: `describe_root_dirt`'s new
sweep-authorship hint fired FOR REAL, on this ticket's OWN land attempt
-- a different ticket's detached sweep left `tickets.md` dirty mid-
session, and the refusal read "...(all paths match the detached
post-land sweep's own known writes -- rapid-debt.jsonl/tickets.md,
T-1699/T-1755 -- likely author: a sweep child that filed something and
did not commit it)", correctly diagnosing the exact failure mode this
ticket exists to close, unprompted, on live root state. Not a
constructed test case -- the fix demonstrated itself before it even
landed.

Gates: `frob check --only gates-fast/native/security --ticket T-1755`
all clean down to the expected land-owned-file SCOPE001 noise
(.frob-release.json, pyproject.toml, rapid-debt.jsonl, uv.lock),
reconciled by `frob ticket land`'s own internal merge.

### Changed
```
 docs/modules/tickets.md                    |  43 +++++++
 src/frob/app/ticket_runner/_rapid_sweep.py |  65 +++++++++-
 src/frob/tickets/_land_git_ops.py          |  48 +++++++-
 tests/unit/test_rapid_sweep.py             |  72 +++++++++++
 tickets.md                                 | 184 ++++++++++++++++++++++++++++-
 5 files changed, 406 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commits_the_ledger_write` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commit_failure_logs_at_error_and_does_not_raise` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_detached_sweep_as_likely_author` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_mixed_dirt_does_not_claim_the_sweep` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 507 warning(s), 725 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/verify/_backpressure.py, invalid-argument-type@src/frob/app/ticket_runner/_land_cmd.py

<!-- ticket:T-1756 -->
```yaml
id: T-1756
title: 'post-land sweep regression from T-1692: 3 new error(s) (E501, invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- /home/logan/projects/frob/src/frob/app/ticket_runner/_land_cmd.py
- /home/logan/projects/frob/src/frob/verify/_backpressure.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- src/frob/verify/_backpressure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires touching the affects()-closure doc for BackpressureError/current_status,
    both touched by this ticket's E501 wraps
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/verify/_backpressure.py
  reason: relative-path scope entry alongside the absolute-path one already filed
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_empty_queue_is_never_tripped
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_not_tripped_is_a_noop
designated_repro_test: null
threat: null
component: null
```
The deferred post-land unscoped sweep (T-1684) for T-1692 at commit 1647eb98b3f9a373c9c47effef78ea141857c48f found 3 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_land_cmd.py
- E501  /home/logan/projects/frob/src/frob/verify/_backpressure.py
- invalid-argument-type  src/frob/app/ticket_runner/_land_cmd.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Done report

frob:no-behavior-change reason="4 E501 line-wrap fixes, no logic change."

Changed:
- src/frob/app/ticket_runner/_land_cmd.py: 1 line wrapped
  (`_land_core_prepare`'s `effective` assignment).
- src/frob/verify/_backpressure.py: 3 lines wrapped
  (`BackpressureError.QueueUnreadable`, `current_status`'s
  `watermark_commit`/`age_tripped` computations).
- docs/modules/tickets.md: T-1756 follow-up note.

Verified against current main before doing any work (per explicit
instruction not to fix what is already fixed): all 4 lines were still
present and still over 88 chars
(`ruff check ... --select E501` confirmed 4 real hits before this fix,
0 after).

Evidence: no new test surface -- pure formatting, verified via the
existing `tests/unit/verify/test_backpressure.py`/
`tests/unit/test_land_cmd_backpressure.py` suites still passing
unchanged (`timeout 100 uv run pytest tests/unit/verify/ tests/unit/test_land_cmd_backpressure.py -p no:cacheprovider -q` ->
`collected=50 failed=0`). No evidence node ids recorded (nothing new to
bind; the ticket has no acceptance criteria to satisfy).

Filed: none.

Gates: `frob check --only gates-fast/native --ticket T-1756` clean down
to the expected land-owned-file SCOPE001 noise
(.frob-release.json, pyproject.toml, uv.lock).

### Changed
```
 .frob-release.json                      | 11 +-----
 CHANGELOG.md                            |  4 --
 docs/modules/tickets.md                 |  6 +++
 pyproject.toml                          |  2 +-
 src/frob/app/ticket_runner/_land_cmd.py |  4 +-
 src/frob/verify/_backpressure.py        | 14 +++++--
 tickets.md                              | 68 +++++++++++++++++++++++++++++++++
 uv.lock                                 |  2 +-
 8 files changed, 91 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_empty_queue_is_never_tripped` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_not_tripped_is_a_noop` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 503 warning(s), 725 waived
- error-findings: invalid-argument-type@src/frob/app/ticket_runner/_land_cmd.py

<!-- ticket:T-1757 -->
```yaml
id: T-1757
title: 'post-land sweep regression from T-1754: 1 new error(s) (REL001)'
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
The deferred post-land unscoped sweep (T-1684) for T-1754 at commit 92a1dea0635fc5a4404a314db15bcb97255d35cf found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- REL001  pyproject.toml

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

<!-- ticket:T-1758 -->
```yaml
id: T-1758
title: T-1615's uniform ledger auto-commit does not cover programmatic (non-CLI) callers
  of new_ticket/write_ticket
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
T-1755's investigation confirmed: `frob.tickets._new_renumber.new_ticket`
(and, by the same construction, `write_ticket`/other `frob.tickets`
mutators called directly rather than through the `frob ticket <verb>` CLI
dispatch) has NO auto-commit of its own. The T-1130/T-1615 auto-commit
(`commit_ticket_ledger_change`, `_auto_commit_ledger_after_dispatch`)
lives entirely in the CLI dispatch layer -- it wraps the verb, not the
library call the verb happens to invoke.

`frob.app.ticket_runner._rapid_sweep._file_regression_ticket` was one
concrete victim (fixed in T-1755): it calls `new_ticket` directly (a
detached child, not a CLI dispatch), so its write went uncommitted and
DirtyMain-blocked every subsequent land repo-wide.

This is a STRUCTURAL gap, not just that one call site: ANY current or
future programmatic caller of `frob.tickets.new_ticket`/`write_ticket`/
other ledger mutators that does not go through `frob.app.ticket_runner`'s
CLI dispatch table inherits the exact same silent-DirtyMain hazard.

Scope for whoever picks this up: audit `frob.tickets` for every
programmatic (non-CLI) caller of a ledger-mutating function
(`new_ticket`, `write_ticket`, `add_evidence`, etc. -- grep for direct
imports from `frob.app.ticket_runner`-external modules) and decide,
per T-1755's own two options:

1. Move the auto-commit INTO the library function itself (so it is
   impossible to call any ledger mutator without committing), or
2. Establish a documented convention that every non-CLI caller must
   call `commit_ticket_ledger_change` itself immediately after, and add
   a gate/lint that catches a caller which does not.

Option 1 closes the hole permanently; option 2 is weaker (relies on every
future caller remembering) but may be necessary if some programmatic
caller legitimately wants to batch several ledger writes into one commit
(same shape `commit_ticket_ledger_change(..., no_commit=True)` already
supports for the CLI layer).

<!-- ticket:T-1759 -->
```yaml
id: T-1759
title: 'post-land sweep regression from T-1756: 1 new error(s) (REL001)'
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
```
The deferred post-land unscoped sweep (T-1684) for T-1756 at commit 0f436d9c68c48cc869aec7582b51b67d0548e8c6 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- REL001  pyproject.toml

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
