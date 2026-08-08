# frob refactor

Transactional Python symbol move/rename: rewrites every import/call site
that references the moved symbol, verifies the result, and rolls back
atomically if it cannot complete. Design: `docs/design/refactor-verb.md`
(T-1135). This page documents the engine T-1197 built; T-1483 wired the
CLI verb into `frob`'s main dispatch (see "CLI wiring status" below).


## Usage

```
frob refactor move SOURCE_MODULE:QUALNAME DEST_MODULE:QUALNAME [--alias-conflict {error,rename-dest}]
frob refactor rename SOURCE_MODULE:QUALNAME DEST_MODULE:QUALNAME [--alias-conflict {error,rename-dest}]
```

`move` relocates a symbol to a different module; `rename` changes its
name (optionally within the same module). Both go through the identical
resolve/plan/apply/verify pipeline -- a rename is just a move whose
destination module happens to equal the source module.

`--full-repo-collect` runs the Verify phase's `pytest --collect-only`
over the whole repository instead of just the files this transaction
touched (see "Open design question" below). `--skip-check-delta` skips
the `frob check --delta` post-condition for fast local iteration.

## Split verb (T-1201)

```
frob refactor split SOURCE_MODULE --symbols a,b,c --into DEST_MODULE [--alias-conflict {error,rename-dest}] [--chunk-size N]
```

Moves every named symbol out of `SOURCE_MODULE` into a new sibling
module `DEST_MODULE`, built directly on the T-1072/T-1077 manual
family-extraction pattern used repeatedly across this drive: the source
module keeps a re-export shim (`from DEST_MODULE import (a, b, c, ...)
# noqa: F401`) so any external `from SOURCE_MODULE import symbol` call
site this engine's own scan does not reach still resolves; every
repo-local call site `scan_references` DOES reach is rewritten in place,
same as a single `move` would.

`--symbols` names go in one `chunk-size`-sized group (default 5) at a
time; each group is its own apply-verify-rollback transaction (`git`
commit or `git reset --hard`), reusing `build_plan`/`apply_plan` per
symbol in the group (so every T-1199/T-1200/T-1267 carrier already wired
into `build_plan` applies to a split exactly as it does to a single
move) plus one combined re-export-shim op. A chunk's own transaction
failing stops the whole split from attempting any LATER chunk, but never
touches an EARLIER chunk's own already-committed symbols -- each chunk
stands on its own, per the design's "individually refuse-and-rollback
safe" requirement. Two symbols moved out of the same source module in
the same chunk each independently plan a full rewrite of the shared
`from source import a, b` statement; `_dedupe_equivalent_import_ops`
recognizes the two rewrites as equivalent (same resulting name set, just
possibly reordered) and collapses them to one op rather than tripping
`apply_plan`'s overlapping-rewrite refusal.

## Transaction model

1. **Resolve** -- `frob.refactor.resolve_symbol` parses the source
   module via `ast` and confirms the target names exactly one top-level
   or one-level-nested (`Class.method`) symbol. Refuses with no writes if
   the target does not resolve.
2. **Plan** -- `frob.refactor.build_plan` computes the full rewrite plan
   before any file write: the move itself (delete from the old file,
   append to the new one) plus every `from module import name` /
   call-site rewrite found by `frob.refactor.scan_references`, repo-wide.
   Refuses with no writes on a destination-name collision.
3. **Apply** -- `frob.refactor.apply_plan` splices every planned
   `RewriteOp` into its file, preserving formatting outside each touched
   span, then commits the result as one WIP commit in the caller's own
   worktree. Refuses with `Err(OverlappingRewrites)`, before a single
   byte is written, if two or more planned ops targeting the same file
   have overlapping or duplicate line ranges -- each op is computed
   against the ORIGINAL source, so applying both would let the
   later-applied op silently clobber the earlier one's rewrite with no
   warning; the transaction refuses instead of risking that. `scan_references`
   (Plan phase) applies the same discipline one level earlier: a
   semicolon-joined statement sharing a physical line with an import
   it would otherwise mechanically rewrite is reported via `unresolved`
   instead of rewritten, since a whole-line-span replacement there would
   silently delete the sibling statement.
4. **Verify** -- three post-conditions, each producing a `VerifyOutcome`:
   - `verify_import_resolution` -- every touched file still parses AND,
     for every absolute `from <local module> import <name>` it contains,
     `<name>` actually resolves against something that local module
     currently defines (real, scoped import-graph resolution -- see the
     function's own docstring for the exact scope: repo-owned modules
     under `src/` only, absolute imports only; third-party/stdlib and
     relative imports are outside v1's static-AST reach and are never
     flagged). Pass `repo_root=None` to fall back to the syntax-only
     check (the historical behavior, still available for a caller with
     no enclosing repo); the `detail` string always says which mode ran.
   - `verify_pytest_collect` -- `pytest --collect-only` succeeds with no
     new collection error.
   - `verify_check_delta` -- `frob check --delta` is diff-clean against
     the pre-refactor baseline. Invoked as `sys.executable -m frob`, not
     a bare `frob` on PATH, so it stays version-consistent with whatever
     interpreter is running this code (`docs/guides/agent-playbook.md`
     sec 2 -- a bare `frob` can resolve to a stale global install).
5. **Commit or rollback** -- any failing post-condition rolls the whole
   transaction back via `git reset --hard` to the pre-transaction sha
   (never `git stash`, per `docs/guides/agent-playbook.md` sec 1b).
   Success or failure, the same `RefactorReport` shape is returned:
   the plan, every verify outcome, every auto-generated import alias, and
   every unresolvable reference (never silently dropped).

## Alias-conflict policy

Two distinct collision kinds, two distinct handlers (T-1202):

- **Import-site name collision**: the destination name collides with
  something already bound at a call site. The default (`--alias-conflict
  error`, despite the name -- this is the *policy id*, not "refuse")
  auto-generates an import alias at that call site only
  (`<name>_refactored`) and records an `AliasRecord` in the report --
  `frob.refactor._scan.scan_references`'s own job, unaffected by which
  `--alias-conflict` value is passed.
- **Destination-namespace collision**: two symbols would land with the
  same name in the same destination module. Under the default `error`
  policy this is always a hard `DestinationCollision` refusal, before any
  file is written. Passing `--alias-conflict rename-dest` instead renames
  the EXISTING colliding symbol out of the way
  (`frob.refactor._alias_policy.resolve_rename_dest_collision`): an
  in-place identifier substitution on its own def/class line plus every
  call site `scan_references` finds for it (reusing the move engine's own
  reference-rewrite pass, not a second implementation), so the incoming
  move lands under the name it asked for. Every such rename is recorded
  as its own `AliasRecord`, appearing in the disclosed report's alias
  section alongside any import-site alias -- never buried in the general
  rewrite list.

## Scope: Python import/call sites only

This engine (T-1197) rewrites Python `from module import name` /
call-site references only. It is the shared substrate three sibling
tickets extend with their own reference kinds, per
`docs/design/refactor-verb.md`'s reference-kind inventory:

- T-1199 (directive/waiver carrier) -- every `frob:*` comment-DSL
  target and `frob:waive` symref.
- T-1200 (registry/evidence repointer) -- PII012 allowlist keys,
  `docs/design/registry/*.yaml` citations, ticket-ledger evidence node
  ids.
- T-1267 (prose/doc-anchor carrier) -- free-text mentions in
  docstrings/comments/`docs/**`, and doc-anchor heading-slug rewrites.

Each extends `RefactorPlan.reference_ops`/`aliases`/`unresolved` against
the same `build_plan`/`apply_plan`/`run_refactor` pipeline; none
reimplement transaction mechanics.

A `from x.y import z` attribute-style call site written as
`import x.y` + `x.y.z(...)` is detected but listed in
`RefactorPlan.unresolved` rather than rewritten -- v1 only rewrites
`from ... import` bindings mechanically.

## CLI wiring status

T-1483 wired `frob refactor` into `frob`'s main dispatch. Because
`run_refactor_command(args: argparse.Namespace) -> int` takes a parsed
`Namespace` and returns a raw exit code directly -- T-1197's own shape,
matching every other `_add_*_parser` builder's signature for a later
single-line wire-in -- rather than the uniform `run(AppConfig)` entry
point every subcommand in `frob.app.app._SUBCOMMAND_RUNNER_NAMES`
shares, `frob refactor` is routed the same way `frob bind`/`agent`/
`worktree` already are: `src/frob/__main__.py::_dispatch` recognizes
`argv[0] == "refactor"` and dispatches directly, before the main
`argparse` parser tree (`_build_parser`) is even built -- it never
becomes a `Subcommand` enum member or an entry in
`_SUBCOMMAND_RUNNER_NAMES`.

`run_refactor_command`'s human-facing report lines route through a
`frob.render.Renderer` (T-1336), matching the sole-stdout convention every
other `*_cli.py`/runner module in this repo uses (INV-RENDER-SOLE-STDOUT)
-- the refusal path still writes to stderr via a plain `print(...,
file=sys.stderr)`, which is outside the Renderer's stdout-only remit.

## Error handling

`resolve_symbol`/`build_plan`/`run_refactor` all return
`Result[T, RefactorError]`:

- `RefactorError.DirtyWorkingTree` -- the caller's tree has uncommitted
  changes; the transaction refuses to start.
- `RefactorError.TargetNotFound` -- the source `MODULE:QUALNAME` does not
  resolve to exactly one symbol.
- `RefactorError.DestinationCollision` -- the destination module already
  defines a symbol with the destination name.
- `RefactorError.ApplyFailed` -- the Apply phase could not complete every
  planned rewrite; the (as-yet-uncommitted) working tree is restored.
- `RefactorError.GitError` -- a git operation the transaction depends on
  failed.

Once a transaction has actually committed its WIP snapshot, a Verify
failure is reported as `Ok(RefactorReport(success=False, rolled_back=True,
...))`, not `Err` -- the disclosed report is the point, not an exception.

## Public API

<!-- frob:describes src/frob/refactor/_transaction.py::run_refactor -->
<!-- frob:describes src/frob/refactor/_transaction.py::build_plan -->
<!-- frob:describes src/frob/refactor/_resolve.py::resolve_symbol -->
<!-- frob:describes src/frob/refactor/_scan.py::scan_references -->
<!-- frob:describes src/frob/refactor/_apply.py::apply_plan -->

```python
# frob/refactor/_transaction.py
def run_refactor(
    repo_root: Path,
    kind: RefactorKind,
    source: SymbolRef,
    destination: SymbolRef,
    alias_conflict: str = "error",
    run_pytest_collect: bool = True,
    run_check_delta: bool = True,
    pytest_scope_touched_only: bool = True,
) -> Result[RefactorReport, RefactorError]

def build_plan(
    repo_root: Path,
    kind: RefactorKind,
    source: SymbolRef,
    destination: SymbolRef,
    alias_conflict: str = "error",
) -> Result[RefactorPlan, RefactorError]
```

## Public API reference

<a id="refactor-error"></a>
<!-- frob:describes src/frob/refactor/_models.py::RefactorError -->
**`RefactorError`**: the failure `ErrorSet` every fallible pipeline call
returns -- see "Error handling" above.

<a id="refactor-kind"></a>
<!-- frob:describes src/frob/refactor/_models.py::RefactorKind -->
**`RefactorKind`**: `MOVE`/`RENAME`, the two v1 verbs -- see
"Transaction model" above.

<a id="symbolref"></a>
<!-- frob:describes src/frob/refactor/_models.py::SymbolRef -->
**`SymbolRef`**: a `module`+`qualname` pair identifying a Python symbol,
used for both the source and destination of a move/rename.

<a id="resolvedsymbol"></a>
<!-- frob:describes src/frob/refactor/_models.py::ResolvedSymbol -->
**`ResolvedSymbol`**: the Resolve phase's output -- a `SymbolRef` pinned
to a real file and exact source span.

<a id="rewriteop"></a>
<!-- frob:describes src/frob/refactor/_models.py::RewriteOp -->
**`RewriteOp`**: one exact text-span substitution the Apply phase
performs verbatim.

<a id="aliasrecord"></a>
<!-- frob:describes src/frob/refactor/_models.py::AliasRecord -->
**`AliasRecord`**: one auto-generated import alias, named in the
disclosed report -- see "Alias-conflict policy" above.

<a id="refactorplan"></a>
<!-- frob:describes src/frob/refactor/_models.py::RefactorPlan -->
**`RefactorPlan`**: the full rewrite plan computed once by the Plan
phase -- move ops, reference ops, aliases, and unresolved mentions.

<a id="verifyoutcome"></a>
<!-- frob:describes src/frob/refactor/_models.py::VerifyOutcome -->
**`VerifyOutcome`**: one Verify-phase post-condition's pass/fail result.

<a id="refactorreport"></a>
<!-- frob:describes src/frob/refactor/_models.py::RefactorReport -->
**`RefactorReport`**: the disclosed report a transaction returns either
way -- the plan, every verify outcome, and whether it committed or
rolled back.

<a id="module_to_path"></a>
<!-- frob:describes src/frob/refactor/_resolve.py::module_to_path -->
**`module_to_path`**: the single place a dotted module path becomes a
`src/**.py` filesystem path.

<a id="resolve_symbol"></a>
<!-- frob:describes src/frob/refactor/_resolve.py::resolve_symbol -->
**`resolve_symbol`**: the Resolve phase entry point -- see "Transaction
model" above, step 1.

<a id="find_python_files"></a>
<!-- frob:describes src/frob/refactor/_scan.py::find_python_files -->
**`find_python_files`**: every `.py` file under a repo root, skipping
VCS/build/venv directories.

<a id="scan_references"></a>
<!-- frob:describes src/frob/refactor/_scan.py::scan_references -->
**`scan_references`**: the Plan phase's Python import/call-site reference
scan -- see "Scope: Python import/call sites only" above.

<a id="build_move_ops"></a>
<!-- frob:describes src/frob/refactor/_apply.py::build_move_ops -->
**`build_move_ops`**: computes the two `RewriteOp`s that relocate a
symbol's own source span.

<a id="apply_plan"></a>
<!-- frob:describes src/frob/refactor/_apply.py::apply_plan -->
**`apply_plan`**: the Apply phase -- splices every planned `RewriteOp`
into its target file; refuses with `Err(OverlappingRewrites)` before any
write if two ops targeting the same file overlap.

<a id="verify_import_resolution"></a>
<!-- frob:describes src/frob/refactor/_verify.py::verify_import_resolution -->
**`verify_import_resolution`**: Verify post-condition 1 -- every touched
file still parses, and (when `repo_root` is given) every absolute
local-module import it contains resolves against what that module
currently defines.

<a id="verify_pytest_collect"></a>
<!-- frob:describes src/frob/refactor/_verify.py::verify_pytest_collect -->
**`verify_pytest_collect`**: Verify post-condition 2 -- `pytest
--collect-only` succeeds with no new collection error.

<a id="verify_check_delta"></a>
<!-- frob:describes src/frob/refactor/_verify.py::verify_check_delta -->
**`verify_check_delta`**: Verify post-condition 3 -- `frob check --delta`
is diff-clean.

<a id="build_plan"></a>
<!-- frob:describes src/frob/refactor/_transaction.py::build_plan -->
**`build_plan`**: Resolve+Plan in one call -- see "Usage" above. Since
T-1199, also extends the move span for any attached directive/waiver
comment block and folds `scan_directive_carriers`' repo-wide directive
rewrites into `reference_ops`/`unresolved`. Since T-1200, also folds
`scan_pii_allowlist_carrier`/`scan_registry_citations`/
`scan_evidence_citations`'s own ops/unresolved in the same way.

<a id="run_refactor"></a>
<!-- frob:describes src/frob/refactor/_transaction.py::run_refactor -->
**`run_refactor`**: the full pipeline in one call -- see "Transaction
model" above. Since T-1199, also calls `carry_lock_acks` after a
successful Apply, before the WIP commit, so a carried `frob.lock` ack
lands in the same commit (and reverts together with everything else on a
verify-failure rollback).

<a id="cli"></a>
<!-- frob:describes src/frob/refactor/_cli.py::add_refactor_parser -->
<!-- frob:describes src/frob/refactor/_cli.py::run_refactor_command -->
**`add_refactor_parser`/`run_refactor_command`**: the ready-to-wire CLI
surface -- see "CLI wiring status" above.

<a id="extend_span_for_attached_directives"></a>
<!-- frob:describes src/frob/refactor/_directives.py::extend_span_for_attached_directives -->
**`extend_span_for_attached_directives`**: T-1199's directive/waiver
carrier, part 1 -- extends a move's span so a `frob:*` comment block
attached directly above the symbol's own definition line moves WITH it,
since `ast`'s own `lineno`/`end_lineno` never includes leading comments.

<a id="scan_directive_carriers"></a>
<!-- frob:describes src/frob/refactor/_directives.py::scan_directive_carriers -->
**`scan_directive_carriers`**: T-1199's directive/waiver carrier, part 2
-- a repo-wide scan (reusing `frob.graph.dsl.parse_directives`) for every
`frob:*` directive elsewhere in the repo whose `target`/`src` names the
moving symbol's old symref; rewrites it to the new one.

<a id="carry_lock_acks"></a>
<!-- frob:describes src/frob/refactor/_directives.py::carry_lock_acks -->
**`carry_lock_acks`**: T-1199's directive/waiver carrier, part 3 -- a
post-apply step that re-keys any `frob.lock` ack entry from the moving
symbol's old symref to its new one, so an unchanged digest is never
reported stale by DRIFT001 just because the symbol moved.

<a id="scan_pii_allowlist_carrier"></a>
<!-- frob:describes src/frob/refactor/_repointer.py::scan_pii_allowlist_carrier -->
**`scan_pii_allowlist_carrier`**: T-1200's registry/evidence repointer,
part 1 -- re-keys any `_PII012_REVIEWED_NON_PII`
(`src/frob/gates/_pii_structural/_keywords.py`) entry whose `(file,
identifier-text)` matches the moving symbol's old file and own leaf name,
to `(new file, identifier-text)`; the identifier half never changes.

<a id="scan_registry_citations"></a>
<!-- frob:describes src/frob/refactor/_repointer.py::scan_registry_citations -->
**`scan_registry_citations`**: T-1200's registry/evidence repointer, part
2 -- a text-level scan of `docs/design/registry/*.yaml` for any line
citing the moving symbol's old `path::qualname` symref (a `cross_refs`
entry is the observed shape), rewritten to the destination's equivalent.

<a id="scan_evidence_citations"></a>
<!-- frob:describes src/frob/refactor/_repointer.py::scan_evidence_citations -->
**`scan_evidence_citations`**: T-1200's registry/evidence repointer, part
3 -- a text-level scan of `tickets.md` and `tickets-archive.md` for any
line citing the moving symbol's old `path::Class.method` symref or its
pytest `path::Class::method` node-id form, rewritten to the destination's
equivalent. `build_plan` folds all three repointer scans into
`reference_ops`/`unresolved` alongside T-1199's directive carrier.

<a id="scan_python_prose_mentions"></a>
<!-- frob:describes src/frob/refactor/_prose.py::scan_python_prose_mentions -->
**`scan_python_prose_mentions`**: T-1267's prose/doc-anchor carrier, part
1 -- a repo-wide scan of every docstring/comment (excluding the moving
symbol's own file and any `frob:*` directive line, both owned
elsewhere) naming the symbol's old dotted path or `path::qualname`
symref in prose, word-boundary matched and rewritten to the
destination's equivalent.

<a id="scan_docs_prose_mentions"></a>
<!-- frob:describes src/frob/refactor/_prose.py::scan_docs_prose_mentions -->
**`scan_docs_prose_mentions`**: T-1267's prose/doc-anchor carrier, part
2 -- every `docs/**` line (a prose sentence or a fenced-code-block import
line) naming the moving symbol's old dotted path, word-boundary matched
and rewritten to the destination's equivalent.

<a id="scan_doc_anchor_carriers"></a>
<!-- frob:describes src/frob/refactor/_prose.py::scan_doc_anchor_carriers -->
**`scan_doc_anchor_carriers`**: T-1267's prose/doc-anchor carrier, part 3
-- a `docs/**` heading whose text embeds the moving symbol's old leaf
name gets its text and its `frob.graph.dsl.slugify` anchor slug rewritten
together, then every existing `frob:doc`/markdown reference to the old
anchor is repointed to the new one so no doc edge silently breaks. A
prose mention this pass judges unsafe to rewrite (an ambiguous match, an
unreadable file) is disclosed in `unresolved` as "review by hand",
never silently skipped. `build_plan` folds all three prose/anchor scans
into `reference_ops`/`unresolved` alongside T-1199's directive carrier
and T-1200's repointer.

<a id="resolve_rename_dest_collision"></a>
<!-- frob:describes src/frob/refactor/_alias_policy.py::resolve_rename_dest_collision -->
**`resolve_rename_dest_collision`**: T-1202's alias-conflict policy --
see "Alias-conflict policy" above. Renames the existing symbol occupying
a destination-namespace collision out of the way and rewrites its own
call sites, returning the rename op, caller ops, and the `AliasRecord`
`build_plan` folds in when `--alias-conflict rename-dest` is passed.

<a id="git"></a>
<!-- frob:describes src/frob/refactor/_gitops.py::git -->
**`git`**: one `git` invocation inside a repo root, routed through the
package's shared exec kill-switch -- the primitive every transaction
(single move/rename or a split chunk) commits and rolls back through.

<a id="working_tree_clean"></a>
<!-- frob:describes src/frob/refactor/_gitops.py::working_tree_clean -->
**`working_tree_clean`**: `True` iff `git status --porcelain` is empty --
the precondition every transaction checks before it starts writing.

<a id="current_sha"></a>
<!-- frob:describes src/frob/refactor/_gitops.py::current_sha -->
**`current_sha`**: the `HEAD` sha a transaction rolls back to on
failure.

<a id="chunk_symbols"></a>
<!-- frob:describes src/frob/refactor/_split.py::chunk_symbols -->
**`chunk_symbols`**: T-1201's split verb -- splits a symbol-name list
into ordered groups of at most `chunk_size`, preserving input order.

<a id="build_reexport_shim_op"></a>
<!-- frob:describes src/frob/refactor/_split.py::build_reexport_shim_op -->
**`build_reexport_shim_op`**: T-1201's split verb -- builds the source
module's own `from DEST_MODULE import (...)  # noqa: F401` re-export
append op, matching the T-1072/T-1077 family-extraction precedent's own
shape.

<a id="chunkreport"></a>
<!-- frob:describes src/frob/refactor/_split.py::ChunkReport -->
**`ChunkReport`**: one chunk's outcome -- the symbols it attempted,
whether its own transaction committed or rolled back, and every verify
outcome; `RefactorReport`'s shape at chunk granularity.

<a id="splitreport"></a>
<!-- frob:describes src/frob/refactor/_split.py::SplitReport -->
<!-- frob:describes src/frob/refactor/_split.py::SplitReport.success -->
<!-- frob:describes src/frob/refactor/_split.py::SplitReport.moved_symbols -->
**`SplitReport`**: the whole split's disclosed report -- one
`ChunkReport` per chunk attempted, in order; `.success` is true only
when every chunk committed; `.moved_symbols` is every symbol name whose
own chunk actually committed, in order.

<a id="run_split"></a>
<!-- frob:describes src/frob/refactor/_split.py::run_split -->
**`run_split`**: T-1201's split verb entry point -- see "Split verb"
above. Chunks `symbols`, then plans/applies/verifies/commits-or-rolls-
back each chunk in order as its own transaction, stopping the moment one
chunk fails.
