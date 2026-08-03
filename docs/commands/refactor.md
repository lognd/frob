# frob refactor

Transactional Python symbol move/rename: rewrites every import/call site
that references the moved symbol, verifies the result, and rolls back
atomically if it cannot complete. Design: `docs/design/refactor-verb.md`
(T-1135). This page documents the engine T-1197 built; the CLI verb
itself is not yet wired into `frob`'s main dispatch (see "CLI wiring
status" below).
<!-- frob:until T-1483 -->


## Usage (once wired)

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

When the destination name collides with something already bound at a
call site, the default (`--alias-conflict error`, despite the name --
this is the *policy id*, not "refuse") auto-generates an import alias at
that call site only (`<name>_refactored`) and records an `AliasRecord` in
the report. A collision inside the destination module's own namespace
(two symbols landing with the same name in the same module) is always a
hard `DestinationCollision` refusal in v1 -- `--alias-conflict
rename-dest`'s full destination-renaming behavior is the alias-conflict
policy child ticket's own scope, not implemented by this engine.

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
- T-1203 (prose/doc-anchor carrier) -- free-text mentions in
  docstrings/comments/`docs/**`, and doc-anchor heading-slug rewrites.

Each extends `RefactorPlan.reference_ops`/`aliases`/`unresolved` against
the same `build_plan`/`apply_plan`/`run_refactor` pipeline; none
reimplement transaction mechanics.

A `from x.y import z` attribute-style call site written as
`import x.y` + `x.y.z(...)` is detected but listed in
`RefactorPlan.unresolved` rather than rewritten -- v1 only rewrites
`from ... import` bindings mechanically.

## CLI wiring status

`frob.refactor._cli.add_refactor_parser`/`run_refactor_command` are
built and ready (same shape as every other `_add_*_parser` in
`src/frob/_cli_parsers/**`) but T-1197's declared scope
(`src/frob/refactor/**`, this file, `tests/test_refactor.py`) does not
include `src/frob/_cli_parsers/**` or `src/frob/__main__.py`, so the
one-line `_add_refactor_parser(sub)` wiring call is left for a follow-up
ticket rather than done here. Until that lands, exercise the engine via
`frob.refactor.run_refactor` directly (Python) or the standalone
`add_refactor_parser`/`run_refactor_command` functions.

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
**`build_plan`**: Resolve+Plan in one call -- see "Usage" above.

<a id="run_refactor"></a>
<!-- frob:describes src/frob/refactor/_transaction.py::run_refactor -->
**`run_refactor`**: the full pipeline in one call -- see "Transaction
model" above.

<a id="cli"></a>
<!-- frob:describes src/frob/refactor/_cli.py::add_refactor_parser -->
<!-- frob:describes src/frob/refactor/_cli.py::run_refactor_command -->
**`add_refactor_parser`/`run_refactor_command`**: the ready-to-wire CLI
surface -- see "CLI wiring status" above.
