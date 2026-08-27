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

T-3122: `build_move_ops` relocates a moved symbol's own source TEXT only
-- it never copies forward `SOURCE_MODULE`'s own top-level imports that
text needs to run (a moved class body naming e.g. `StrEnum`/`BaseModel`
as a base class), so a naive split produces a `DEST_MODULE` that PARSES
fine but raises `NameError` at real import time. Each chunk's own plan
now calls `needed_import_ops_for_symbols` (`_scan.py`) once per chunk:
it collects every `Name` referenced anywhere in the chunk's moved
symbols' own subtrees (base classes, decorators, annotations, nested
bodies), matches that against `SOURCE_MODULE`'s top-level import
statements, and prepends one carry-forward append op -- copied verbatim,
not reconstructed -- to `DEST_MODULE` BEFORE the symbols' own body-append
ops in the chunk's op list, so the destination file's needed imports land
above the moved definitions that need them.

## Module-move verb (T-2990)

```
frob refactor move-module SOURCE_MODULE DEST_MODULE [--allow-existing-destination]
```

Moves or renames a whole MODULE (a `.py` FILE), as opposed to `move`/
`rename`'s single-symbol scope. Operands here are bare dotted module
paths (`frob.legacy_io`, no `:`) -- distinct from `move`/`rename`'s
`MODULE:QUALNAME` symbol operands; see "Typed operands" below for why
that distinction is enforced structurally, not just documented.

`move-module` exists because a module rename is NOT the sum of N symbol
moves: `import frob.legacy_io`/`from frob import legacy_io` reference the
MODULE, which no symbol-scoped scan ever sees; a module-private symbol
or `__all__` has no qualname to hang a symbol-move off; and N separate
symbol moves leave an empty husk file that then has to be deleted by
hand, losing git's own rename detection in the process. `move-module`
instead performs a single `git mv` for the file itself (so `git log
--follow`/blame keep working across the rename) plus a repo-wide
reference rewrite pass, still inside the same commit-or-rollback
transaction shape every other verb here uses.

### Typed operands

A symbol reference (`module:qualname`), a module reference (a bare
dotted path), and a file path are three distinct operand KINDS
(`frob.refactor._operands.OperandKind`) -- `classify_operand` parses a
raw CLI string into one of the three by shape alone (a `/` or `\\`
makes it PATH, a `:` makes it SYMBOL, a valid dotted-identifier chain
with neither makes it MODULE) before any verb-specific logic runs.
`move`/`rename` accept SYMBOL only; `move-module` accepts MODULE only;
a mismatch refuses with `OperandError.WrongOperandKind`, tree
untouched, rather than the shared rewrite engine guessing at what a raw
string like an image asset path was supposed to mean (the concrete
example the ticket's own acceptance names: an `attachments` directory
holding `img.jpg`, spelled here without a joining slash so this mention
does not itself look like a file-path pointer to a non-existent tracked
file). The destination
half is validated further (`validate_module_destination`): every
`.`-separated segment must be a real Python identifier, the mapped path
must land inside the repo's declared source root and end in `.py`, and
-- absent `--allow-existing-destination` -- the destination must not
already exist. Every one of these is a pure check with no filesystem
write; a refusal here leaves the tree byte-identical, not rolled back.

### Per-language seam (T-2996 plug-in point)

`frob refactor` today assumes Python throughout -- `move`/`rename`'s
own `--help` says "move/rename a Python symbol", and nothing in this
package branches on language. `move-module` is the first place that
changes: `frob.refactor._module_lang` is the ONE module that decides
"what counts as a reference to this module, and how is it spelled" for
a given language, dispatched by `adapter_for(language)` where
`language` comes from `frob.lang.language_for_extension` (the same
extension table every other `frob.lang` consumer shares -- no second
per-language table here). Only `"python"` is registered
(`_module_scan_python.scan_python_module_references`); a module in any
other language refuses loudly with `RefactorError.UnsupportedLanguage`
at Resolve time (`_module_resolve.resolve_module`) rather than being
silently skipped or partially rewritten. Everything else in the
module-move pipeline -- operand typing, destination validation, `git
mv`, the transaction/rollback shape, and the Verify-phase post-
conditions -- is language-agnostic and imports nothing from
`_module_lang`/`_module_scan_python` by name; adding a language means
registering one new adapter function there, nothing else in this
package changes. T-2996 (not this ticket) owns actually adding more
languages and the cross-module support matrix.

### Python reference-kind inventory

`_module_scan_python.scan_python_module_references` walks every `.py`
file and rewrites, symbolically (AST node comparison, never a text
prefix match -- see "Prefix-collision guard" below):

- `import old.module[ as x]` -- the import statement, plus (unaliased
  only) every `old.module.symbol`-shaped attribute-chain usage
  elsewhere in the file.
- `from old.pkg import old_leaf[ as x]` -- the "from PARENT import
  MODULE" shape; reuses `_scan._rename_usages` (the SAME helper
  `move`/`rename`'s own symbol engine uses for this identical bare-name-
  rebind problem) for any unaliased usage-site rewrite.
- `from old.module import name[, ...]` -- only the module half changes.
- A relative form of either shape above, resolved to an absolute
  dotted path first; re-expressed as relative again when the importing
  file's own package is unchanged relative to the destination, else
  converted to an absolute import (always correct regardless of how
  far the move changes package depth).
- A literal `importlib.import_module("old.module")`/
  `__import__("old.module")` string argument -- rewritten in place. Any
  OTHER argument to either call (computed, an f-string, a variable) is
  out of static-AST scope and is neither guessed at nor silently
  dropped -- it is simply not a shape this scanner can see, matching
  `scan_references`'s own "unresolved, never silently dropped" posture
  for what it cannot mechanically rewrite.

Non-Python surfaces -- `frob.toml` dotted `module`/`module:symbol`
config values, `design/**/*.strata` `code=` bindings, `frob:doc`/
`frob:tests`/`frob:ticket` path citations (both inside `.py` comments
and in `tickets/**/ticket.md`), ticket `scope` globs, and `docs/**/*.md`
prose -- are handled once per module move by
`_module_prose.scan_module_path_citations`, independent of source
language (these are keyed on the module's own PATH, not on any
language-specific import syntax).

### Prefix-collision guard

Every match in `_module_scan_python.py` compares a FULL dotted-name
SEGMENT LIST for exact equality (`_dotted_attribute_chain`/
`_prefix_node`), never a string prefix -- `frob.legacy_io` never matches
`frob.legacy_io_extra` or `frob.legacyiomodel`. `_module_prose.py`'s text
scan enforces the same guarantee via an explicit word-boundary check
(`_token_spans`): the character immediately before and after a literal
match must not be an identifier character (or, for a file-path token,
`/`), so a sibling module's name embedding the old name as a substring
is never touched, and neither is a prose mention that merely contains
the token as part of a longer word.

### Verify: no surviving references

Beyond the three shared Verify-phase post-conditions (import
resolution, `pytest --collect-only`, `frob check --delta` --
`_commit.run_verify_outcomes`, shared with `move`/`rename`), `move-
module` runs one post-condition of its own:
`_module_transaction._verify_no_surviving_references` `git grep -c`s
the whole tracked tree for the OLD dotted module path after the
transaction has applied and committed. Any hit rolls the transaction
back -- a partial rename (something no reference-kind scan above
caught) is exactly the failure mode this verb's whole design exists to
prevent, so it is a hard gate, not a disclosed-only warning.

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
4. **Verify** -- post-conditions, each producing a `VerifyOutcome`. Two
   run UNCONDITIONALLY (never skippable by any `--skip-*` flag);
   `verify_pytest_collect`/`verify_check_delta` are the two optional
   ones:
   - `verify_import_resolution` -- every touched `.py` file still parses
     (non-`.py` touched files, e.g. a `tickets/<id>/ticket.md` evidence
     citation or a `docs/design/registry/*.yaml` cross-ref, are recorded
     in the returned `VerifyOutcome.skipped` and never reach the parse
     loop at all -- T-1885; they were never valid Python and previously
     produced a spurious `SyntaxError`-driven rollback, indistinguishable
     from a genuine failure) AND, for every absolute `from <local module>
     import <name>` it contains, `<name>` actually resolves against
     something that local module currently defines (real, scoped
     import-graph resolution -- see the function's own docstring for the
     exact scope: repo-owned modules under `src/` only, absolute imports
     only; third-party/stdlib and relative imports are outside v1's
     static-AST reach and are never flagged). Pass `repo_root=None` to
     fall back to the syntax-only check (the historical behavior, still
     available for a caller with no enclosing repo); the `detail` string
     always says which mode ran, and mentions the skipped count whenever
     it is nonzero -- a skip is disclosed, never silently folded into
     either a pass or a failure verdict.
   - `verify_module_import` (T-3119, ALWAYS runs) -- a REAL interpreter
     `import <module>` for every touched `.py` file's own dotted module,
     each in its own fresh subprocess with this repo's own `src/` root
     (or repo root, if there is no `src/`) on `PYTHONPATH`. PARSE IS NOT
     IMPORT: `verify_import_resolution` above only proves a file parses
     and that ITS OWN local imports statically resolve against a target
     module's top-level names -- it cannot catch a module that parses
     cleanly but raises at real import time, exactly T-3122's defect (a
     moved class body referencing e.g. `StrEnum` as a base class with
     neither the class's own module nor the destination importing it).
     Scoped to the plan's own `touched_files`, same as
     `verify_import_resolution` -- not a whole-repo sweep, since
     importing an arbitrary file executes its top-level code, which is
     unsafe/slow to do unconditionally outside the files a transaction
     could actually have broken. `run_split`'s own chunk verify
     (`_run_chunk_verify`) delegates to the SAME `_commit.
     run_verify_outcomes` every other verb uses (T-3119: it used to be
     an independent copy of the same three-check sequence, which meant a
     fix landed in `run_verify_outcomes` alone silently never reached
     `run_split` -- proven live by reverting T-3122's fix locally and
     showing the strengthened T-3110 corpus still reported
     `success=True` until this delegation was fixed too).
   - `verify_pytest_collect` -- `pytest --collect-only` succeeds with no
     new collection error. Non-`.py` touched files (e.g. a
     `docs/design/*.md` prose citation) are filtered out before ever
     reaching pytest's own argv and recorded in `VerifyOutcome.skipped`
     -- T-3136; previously any non-Python touched file made pytest
     refuse outright with `rc=4` (USAGE_ERROR), a false refusal
     unrelated to whether any real test collected cleanly, mirroring the
     `.py` filter `verify_import_resolution` already had (T-1885). If
     every touched file is non-Python, this check passes with a note
     (nothing to collect) rather than refusing.
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

T-1483 wired <!-- frob:waive DOC006 reason="frob refactor is real and wired (see the rest of this section) but is special-cased in src/frob/__main__.py::_dispatch BEFORE the normal argparse tree (_build_parser) is built, exactly like frob bind/agent/worktree -- it never becomes a Subcommand enum member or an entry in _SUBCOMMAND_RUNNER_NAMES, so DOC006's CLI-resolution check (which walks the argparse tree) cannot see it" -->`frob refactor` into `frob`'s main dispatch. Because
`run_refactor_command(args: argparse.Namespace) -> int` takes a parsed
`Namespace` and returns a raw exit code directly -- T-1197's own shape,
matching every other `_add_*_parser` builder's signature for a later
single-line wire-in -- rather than the uniform `run(AppConfig)` entry
point every subcommand in `frob.app.app._SUBCOMMAND_RUNNER_NAMES`
shares, <!-- frob:waive DOC006 reason="same special-cased pre-argparse dispatch as the frob refactor waiver above -- real and wired, just invisible to the argparse-tree walk DOC006's CLI resolution performs" -->`frob refactor` is routed the same way `frob bind`/`agent`/
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
<!-- frob:describes src/frob/refactor/_module_transaction.py::run_move_module -->
<!-- frob:describes src/frob/refactor/_module_transaction.py::build_module_plan -->

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
**`VerifyOutcome`**: one Verify-phase post-condition's pass/fail result,
plus `skipped` (T-1885) -- the touched paths this check did not analyse
because they are outside its own domain, disclosed distinctly from a
pass or a failure verdict rather than silently folded into either.

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
`.py` file still parses (non-`.py` touched files are skipped, T-1885),
and (when `repo_root` is given) every absolute local-module import it
contains resolves against what that module currently defines. T-1889:
the per-file parse/skip/syntax-error loop is factored into the private
helper `_parse_touched_python_files` so this function stays under the
long-function architecture threshold; behavior is unchanged.

<a id="verify_module_import"></a>
<!-- frob:describes src/frob/refactor/_verify.py::verify_module_import -->
**`verify_module_import`**: Verify post-condition (T-3119, ALWAYS runs,
never gated by a `--skip-*` flag) -- a REAL interpreter `import
<module>` for every touched `.py` file's own dotted module, each in its
own fresh subprocess; catches the defect class `verify_import_resolution`
structurally cannot (PARSE IS NOT IMPORT). See "Transaction model" above
for the full rationale and the T-3122 defect this closes.

<a id="verify_pytest_collect"></a>
<!-- frob:describes src/frob/refactor/_verify.py::verify_pytest_collect -->
**`verify_pytest_collect`**: Verify post-condition 2 -- `pytest
--collect-only` succeeds with no new collection error. Non-`.py`
touched files are filtered out before reaching pytest's argv (T-3136)
and disclosed via `VerifyOutcome.skipped`.

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
verify-failure rollback). Since T-1854, calls `_route_evidence_rebinds_
through_replace_evidence` on the plan BEFORE `apply_plan` -- see
`scan_evidence_citations`'s own entry above for what that routing does
and why.

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
3 -- a text-level scan for any line citing the moving symbol's old
`path::Class.method` symref or its pytest `path::Class::method` node-id
form, rewritten to the destination's equivalent. Scans BOTH the legacy
`tickets.md`/`tickets-archive.md` monofiles AND, per T-1546, every real
per-ticket `tickets/<id>/ticket.md`/`tickets/archive/<id>/ticket.md`
file this repo's ledger-v2 layout actually uses -- a pre-migration repo
only ever hits the legacy files; this repo, post-migration, hits the
per-ticket ones. `build_plan` folds all three repointer scans into
`reference_ops`/`unresolved` alongside T-1199's directive carrier.

T-1854: every hit still produces a `RewriteOp` here (this scan and its
own dry-run preview are unchanged) -- but for a per-ticket file's
structured-evidence NODE-ID citation specifically, `run_refactor`'s
apply phase (`_route_evidence_rebinds_through_replace_evidence`) routes
the actual write through `frob.tickets.replace_evidence`'s audited,
`--reason`-required path instead of applying this op's raw text
substitution, so the rebind leaves an `EvidenceChangeEntry` trail
exactly like a manual `frob ticket evidence --replace` would. A hit that
`replace_evidence` cannot bind (free prose mentioning the id, not a real
structured evidence entry) falls back to this op's own raw-text apply,
unchanged from before -- never silently dropped either way.
`evidence_citation_targets`/`ticket_id_from_ledger_path` (both public)
are the two small helpers that make this routing possible without
re-deriving the scan.

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

<a id="operandkind"></a>
<!-- frob:describes src/frob/refactor/_operands.py::OperandKind -->
**`OperandKind`**: the three operand shapes a raw CLI argument
classifies into -- SYMBOL, MODULE, PATH -- see "Typed operands" above.

<a id="operanderror"></a>
<!-- frob:describes src/frob/refactor/_operands.py::OperandError -->
**`OperandError`**: operand-shape refusals, distinct from
`RefactorError` (a pipeline-phase failure) -- `WrongOperandKind`,
`InvalidDestination`, `DestinationExists`.

<a id="moduleref"></a>
<!-- frob:describes src/frob/refactor/_operands.py::ModuleRef -->
**`ModuleRef`**: a dotted Python module path operand -- the MODULE
operand kind, distinct from `SymbolRef`.

<a id="classify_operand"></a>
<!-- frob:describes src/frob/refactor/_operands.py::classify_operand -->
**`classify_operand`**: classifies a raw CLI string into an
`OperandKind` by shape alone -- see "Typed operands" above.

<a id="parse_symbol_operand"></a>
<!-- frob:describes src/frob/refactor/_operands.py::parse_symbol_operand -->
**`parse_symbol_operand`**: parses a SYMBOL operand, refusing anything
MODULE- or PATH-shaped -- `move`/`rename`'s own operand gate.

<a id="parse_module_operand"></a>
<!-- frob:describes src/frob/refactor/_operands.py::parse_module_operand -->
**`parse_module_operand`**: parses a MODULE operand, refusing anything
SYMBOL- or PATH-shaped -- `move-module`'s own operand gate.

<a id="validate_module_destination"></a>
<!-- frob:describes src/frob/refactor/_operands.py::validate_module_destination -->
**`validate_module_destination`**: validates a `ModuleRef` as a legal
Python module destination before any write -- see "Typed operands"
above.

<a id="resolvedmodule"></a>
<!-- frob:describes src/frob/refactor/_module_resolve.py::ResolvedModule -->
**`ResolvedModule`**: the module-verb Resolve phase's output -- a
`ModuleRef` pinned to a real file and its `frob.lang` language label.

<a id="resolve_module"></a>
<!-- frob:describes src/frob/refactor/_module_resolve.py::resolve_module -->
**`resolve_module`**: the module-verb Resolve phase entry point --
confirms the file exists and its language has a registered `move-
module` adapter, else `Err(UnsupportedLanguage)`. See "Per-language
seam" above.

<a id="adapter_for"></a>
<!-- frob:describes src/frob/refactor/_module_lang.py::adapter_for -->
**`adapter_for`**: the registered `ModuleReferenceScanner` for a
`frob.lang` language label, or `None` -- see "Per-language seam" above.

<a id="supported_languages"></a>
<!-- frob:describes src/frob/refactor/_module_lang.py::supported_languages -->
**`supported_languages`**: every language with a registered
`move-module` adapter today (`frozenset({"python"})`).

<a id="scan_python_module_references"></a>
<!-- frob:describes src/frob/refactor/_module_scan_python.py::scan_python_module_references -->
**`scan_python_module_references`**: the Python `move-module` adapter's
whole reference-kind inventory -- see "Python reference-kind inventory"
above.

<a id="scan_module_path_citations"></a>
<!-- frob:describes src/frob/refactor/_module_prose.py::scan_module_path_citations -->
**`scan_module_path_citations`**: the shared, language-independent
non-Python-surface scan (`frob.toml`, `.strata`, docs, tickets) -- see
"Python reference-kind inventory" above (non-Python surfaces
paragraph) and "Prefix-collision guard" above.

<a id="moduleplan"></a>
<!-- frob:describes src/frob/refactor/_module_transaction.py::ModulePlan -->
**`ModulePlan`**: the full module-move rewrite plan, the module-verb
mirror of `RefactorPlan` -- no `move_ops` field, since the move itself
is a single `git mv`, not line-span splices.

<a id="modulerefactorreport"></a>
<!-- frob:describes src/frob/refactor/_module_transaction.py::ModuleRefactorReport -->
**`ModuleRefactorReport`**: the disclosed report for a `move-module`
transaction -- the module-verb mirror of `RefactorReport`.

<a id="build_module_plan"></a>
<!-- frob:describes src/frob/refactor/_module_transaction.py::build_module_plan -->
**`build_module_plan`**: the module-verb Plan phase entry point --
resolves the source, validates the destination, and dispatches to the
source language's adapter plus the shared non-Python citation scan.

<a id="run_move_module"></a>
<!-- frob:describes src/frob/refactor/_module_transaction.py::run_move_module -->
**`run_move_module`**: the full `move-module` pipeline in one call --
Resolve+Plan, Apply, `git mv`, commit, Verify (including "no surviving
references"), commit-or-rollback. See "Module-move verb" above.

<a id="commit_wip"></a>
<!-- frob:describes src/frob/refactor/_commit.py::commit_wip -->
**`commit_wip`**: `git add -A` + `git commit` one WIP commit, resetting
hard to a given pre-sha on either step failing -- factored out of
`_transaction.py` (T-2990) so `move-module` shares the exact same
commit-or-reset mechanics as `move`/`rename`/`split`.

<a id="run_verify_outcomes"></a>
<!-- frob:describes src/frob/refactor/_commit.py::run_verify_outcomes -->
**`run_verify_outcomes`**: runs the three shared Verify-phase post-
conditions against a given touched-files set -- factored out of
`_transaction.py` (T-2990) for the same reason as `commit_wip`.

<a id="apply_ops"></a>
<!-- frob:describes src/frob/refactor/_apply.py::apply_ops -->
**`apply_ops`**: the Apply phase's per-file line-span splice mechanics,
operating on a plain list of `RewriteOp`s rather than a `RefactorPlan`
-- factored out of `apply_plan` (T-2990, which is now a thin wrapper
around this) so `move-module` reuses it directly instead of a second
copy; this piece of the engine has nothing symbol-shaped about it.
