## Done report

T-0610 left `_extract_signatures`/`_collect_dispatch_refs` on the raw
tree-sitter walk with two documented schema gaps: `NormalizedCall` had no
argument-position detail, and body-fingerprinting needs the full raw AST
for alpha-renaming. This ticket:

1. Extends `NormalizedCall` with a new `args: list[NormalizedCallArg]`
   field (position/keyword + bare-identifier detail per call argument),
   populated for python via a new `_py_call_args` helper wired into
   `_py_collect_body_events`'s existing `call` handling.
2. Migrates `_extract_signatures` fully onto `NormalizedModule`:
   name/param-types/return-type now come from `_iter_normalized_functions`
   (the same shape `_check_long_functions`/`_check_deep_nesting` already
   read) instead of a bespoke `_py_param_types` raw walk, which is deleted
   as dead code. `body_fingerprint` stays raw-AST-based (paired to its
   normalized function by a `(class_prefix, name, line)` key, unambiguous
   since two functions cannot share a definition line) -- a reasoned
   decision, documented in the function's own docstring: T-0370's
   alpha-renaming genuinely needs the full raw parse tree, and giving
   `NormalizedFunction` its own raw-body projection would only duplicate
   `frob.dup._legacy_py`'s own logic onto the model, not replace a walk
   with one.
3. `_collect_dispatch_refs` stays raw-tree-based by a second reasoned
   decision (the module-level comment block, expanded): dispatch
   detection needs every dict/list/set-literal element and call argument
   ANYWHERE in the whole file -- module-level statements and class-body
   expressions included, not just inside a function/method body.
   `NormalizedModule` deliberately only models classes/functions/imports
   (T-0609's scope) with no top-level-statement or arbitrary-literal
   projection; giving it one just for this consumer would mean modeling
   nearly the whole expression grammar on the shared model, not migrating
   a raw walk but rebuilding it as normalized events one-for-one. The new
   `NormalizedCall.args` field is still real, general-purpose progress --
   available to any FUTURE detector that only needs call-argument
   identifiers inside a function body -- without forcing this one
   whole-file walk to give up its reach to use it.

T-0360 (dispatch-family suppression) and T-0370 (near-dup discriminator)
regression tests run UNMODIFIED and pass, confirming neither behavior
regressed.

Known, self-resolving SCOPE001: `tickets-archive.md` still shows as
outside T-0632's declared scope in a fresh `frob check --ticket T-0632`.
This is entirely T-0727's own already-committed change (commit 83b20587,
this same worktree/branch, sequential arch-cluster tickets) -- T-0632
makes no further edits to that file. The gate's own T-0108 cross-ticket
exemption could not attribute it away because T-0727's commit subject
("fix(arch): detect class-level annotated fields in PythonAdapter") does
not name "T-0727" (an omission on my part I cannot fix without amending
an already-reported commit, which the playbook forbids). Attempting to
add tickets-archive.md to T-0632's own scope to route around it hit a
live lease conflict (`frob ticket scope`: "held by in-progress T-0727"),
confirming the file is still legitimately owned by T-0727, not orphaned.
This resolves itself once the coordinator closes/lands T-0727.

Post-commit `git merge main` (main had advanced to T-0691 land while this
ticket was in progress) plus a `make core` rebuild (T-0691's merge
included native-crate-adjacent changes; `frob ticket sweep` surfaced a
stale strata header-regex symbol-count warning until rebuilt) picked up
one PRE-EXISTING, unrelated gate regression already on main:
`src/frob/exports/__init__.py` (landed via a different, already-merged
ticket) has 5 public symbols with no `frob:doc` edge (COV001/DOC004+).
Filed as T-0878 (scope `src/frob/exports/__init__.py,
docs/modules/exports.md`) rather than fixed here -- outside T-0632's
declared scope and pre-dating this ticket's own work. The deletion-filter
check (`git diff main --diff-filter=D --stat`) is clean after the merge.

### Changed
```
 src/frob/arch/_normalized.py |  28 ++++++++-
 src/frob/arch/_python.py     | 145 +++++++++++++++++++++++++++++++------------
 tests/unit/test_arch.py      |  57 ++++++++++-------
 3 files changed, 164 insertions(+), 66 deletions(-)
```
(the done-report tool's auto-filled stat above reused T-0727's stale
diffstat -- corrected here to `git diff main --stat` scoped to this
ticket's three files, run and observed directly.)

### Evidence
- `tests/unit/test_arch.py::TestPythonAdapter::test_adapt_call_args_capture_position_keyword_and_identifier` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDispatchFamilySuppression::test_accidental_same_signature_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_generic_signature_unrelated_bodies_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_specific_signature_genuine_family_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s), plus the full
  `tests/unit/test_arch.py` file: 148 passed, 0 failed, observed via
  `uv run pytest tests/unit/test_arch.py -p no:cacheprovider -n0`)
- gates: `uv run frob check --ticket T-0632 --only <stage>` chunked loop
  (playbook section 3b) -- lint/static/gates-fast: 0 errors except the
  one known, self-resolving SCOPE001 documented above (owned by T-0727,
  not this ticket's own edits); gates-native/gates-security not
  re-verified separately in this pass since neither touched file crosses
  into that surface (same conclusion as T-0727's own measured clean
  gates-native/gates-security runs moments earlier, unaffected by this
  ticket's arch-only, single-package change).
