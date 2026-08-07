## Done report

Branch: `worktree-agent-a4bd9dcbe924df101`
HEAD (base, before this ticket's changes): `1911076` (fast-forwarded from `main` at ticket start; `git merge main` was a clean fast-forward with no conflicts).

Changed:
- `src/frob/vet/_capability.py`
  - `_TS_SCOPE_TYPES`, `_TS_NAMED_SCOPE_BOUNDARIES`
  - `_collect_ts_target_names`, `_collect_ts_param_name`
  - `_bind_ts_variable_declarator`, `_scope_bind_ts_step`, `_ts_scope_bound_names`
  - `_shadowing_ts_scope`, `_is_ts_shadowed`
  - `_ts_string_text`, `_ts_require_call_module`
  - `_bind_ts_import_clause`, `_bind_ts_import_statement`
  - `_bind_ts_require_object_pattern`, `_bind_ts_require_declarator`, `_ts_import_table`
  - `_resolve_ts_expr`, `_collect_ts_candidates`, `_ts_resolved_candidates`
  - `_ts_binding_capabilities`, `_ts_binding_operations`, `_extra_ts_binding_operations`
  - `scan_file_capabilities` (new `elif language == "typescript"` branch unioning
    `_ts_binding_capabilities` into the raw-text result)
  - `_scan_file_operations` (new `elif language == "typescript"` branch unioning
    `_extra_ts_binding_operations` into the raw-text result)
- `tests/test_vet.py`
  - new `TestCapabilityScanTsBindingResolution` class, 11 tests

Mechanism (mirrors the T-0328/T-0337 Python resolver's shape, new tree-sitter
node types for the TS/JS grammar):
- `_ts_import_table(program_node)` builds a file-wide local-name ->
  resolved-dotted-target table from every import/require FORM: ES default
  (`import dflt from 'x'`), named with optional alias (`import {run as r}
  from 'x'`), namespace (`import * as cp from 'x'`), TS import-equals-require
  (`import cp = require('x')`), and CommonJS `require()` bound via a plain
  identifier or an `object_pattern` destructure with optional rename
  (`const {get: g} = require('x')`).
- `_resolve_ts_expr` resolves a bare `identifier` or `member_expression`
  chain through that table, recursively for chains (`ax.get` -> resolve `ax`
  -> append `.get`). Any other expression shape (a `call_expression`,
  `new_expression`, ...) is not chased -- this is what makes
  `new Job().get()` structurally unreachable from the import table.
- `_ts_scope_bound_names`/`_shadowing_ts_scope` walk TS/JS scope boundaries
  (`function_declaration`/`function_expression`/`arrow_function`/
  `method_definition`/`class_declaration`/`class_expression`/`program`) and
  bind parameters, `const`/`let`/`var` destructuring targets, and
  `catch`/`for` bindings directly in the enclosing scope -- so a locally
  bound name always wins over an import-table entry of the same name before
  resolution is even attempted. Found and fixed one bug while writing this
  (documented inline at `_bind_ts_variable_declarator`): a `const x =
  require('mod')` declarator is itself an import site AND syntactically an
  ordinary local-variable declarator, so the scope-binder had to be taught
  to skip adding it to the bound-names set, or every `require()` binding
  self-shadowed its own import.
- No T-0337-level alias copy-propagation for TS in this pass (a later local
  reassignment of an already-resolved name is not chased) -- documented as
  an explicit known limitation in the module docstring block, matching this
  module's existing "Honest limits" posture; not required by this ticket's
  acceptance criteria.
- Hooked into both public entry points (`scan_file_capabilities`,
  `_scan_file_operations`) as a `elif language == "typescript"` branch
  parallel to the existing `if language == "python"` branch -- the Python
  path is untouched (confirmed: `TestCapabilityScanBindingResolution` and
  `TestCapabilityScanLocalRebindResolution`, the T-0328/T-0337 python
  suites, still pass unmodified, 16/16).

Adversarial-test results (all in `TestCapabilityScanTsBindingResolution`,
11/11 passing): tests deliberately use the `net`/"axios." needle (dotted,
no bare-module-name needle) for the evasion-CAUGHT cases, not
`exec`/"child_process" -- `exec`'s needle table includes the bare substring
"child_process", which the PRE-EXISTING raw-text lexical scan already
matches on the import line itself regardless of aliasing, so a test built
on it would pass even with the resolver disabled and would not actually
prove the fix. "axios." never appears literally in an aliased/namespaced/
required import's source text (only the quoted module specifier `'axios'`
does), so a positive result can only come from the resolver:
- CAUGHT: `import ax from 'axios'; ax.get(url)` (renamed default import)
- CAUGHT: `const ax = require('axios'); ax.get(url)` (bare require rebind)
- CAUGHT: `const {get: g} = require('axios'); g(url)` (destructure + rename,
  bare call site `g(url)` matches no needle lexically at all)
- CAUGHT: `import * as ax from 'axios'; ax.get(url)` (namespace import)
- CAUGHT: `import ax = require('axios'); ax.get(url)` (TS import-equals-require)
- CAUGHT (operation-name granularity): the renamed-default-import case
  above still reports `_scan_file_operations` entry `library="axios"`,
  `capability_kind="net"` -- not just a bare kind label.
- NOT CAUGHT (correct, no false positive): a parameter literally named
  `get` with no import anywhere in the file
  (`test_param_named_get_not_detected`)
- NOT CAUGHT (correct, no false positive): a parameter named `ax` shadowing
  `import ax from 'axios'` for the duration of that function
  (`test_param_shadowing_import_not_detected`)
- NOT CAUGHT (correct, no false positive): `new Job().get()`, a method on
  an unrelated object -- `new Job()` is a `new_expression`, not a
  resolvable identifier/member chain
  (`test_method_on_unrelated_object_not_detected`)
- NOT CAUGHT (correct, no false positive): a bare `get(url)` call with no
  import anywhere in the file (`test_bare_name_call_with_no_import_not_detected`)
- Regression guard: an ordinary unaliased `import {exec} from
  'child_process'; exec(cmd)` still fires via the pre-existing raw-text
  lexical scan, unaffected by adding the resolver pass
  (`test_direct_unaliased_call_still_detected`)

Evidence: the 11 node ids listed in this ticket's `evidence:` field above,
confirmed via a fresh `pytest --collect-only -q` pass (all 11 collected
under `tests/test_vet.py::TestCapabilityScanTsBindingResolution`) and a
fresh full run: `uv run pytest tests/test_vet.py -p no:cacheprovider -q`
-> 164/164 passed (includes the pre-existing 153 `test_vet.py` tests plus
the 11 new ones; no regressions). `uv run pytest
tests/test_vet.py::TestCapabilityScanTsBindingResolution -p
no:cacheprovider -q` -> 11/11 passed in isolation.

Filed: none -- no out-of-scope work discovered. (T-0378/T-0379/T-0380,
Rust/C-C++/Kotlin binding-aware resolution, are pre-existing sibling
tickets under the same T-0376 parent, not new discoveries from this pass.)

Gates: `uv run ruff check src/frob/vet/_capability.py tests/test_vet.py` and
`uv run ruff format --check` both clean under BOTH the PATH `ruff` and the
project-pinned `uv run ruff` (checked separately, both clean). `uv run frob
check --ticket T-0377` -- diffed the `_capability.py`-scoped violations
before/after this change (via `--json` + grep on `"file":
".../_capability.py"`): two transient `ARCH001` long-function warnings on
`_scope_bind_ts_step` (54 lines) and `_bind_ts_require_declarator` (32
lines) appeared after the initial implementation and were fixed by
extracting `_bind_ts_variable_declarator`/`_bind_ts_require_object_pattern`
-- zero new `_capability.py`/`test_vet.py` violations remain (confirmed by
re-running `--json` and grepping again: only the pre-existing
`large-file`/waived-`ARCH001`-on-`_scan_file_operations`/waived-`PERF004`
entries that predate this ticket remain). No baseline was stamped in this
worktree (`--delta` reports "no baseline found; showing all violations" --
a stamp-baseline run is a coordinator/land-time responsibility per the
agent playbook, section 6b/6). The repo-wide `FAIL ruff-check` (1 error,
`src/frob/testing/_select.py:309` E501) and the repo-wide `FAIL gates`
(pre-existing PII010/SEC110/ARCH001 warnings on other files, all already
carrying `frob:waive` or pre-dating this ticket) are OUT OF SCOPE for
T-0377 -- neither file is touched by this change.

## Round 2 addendum (reviewer REJECTED round 1 -- two live evasion classes)

Reviewer verified against axios/"net" (to isolate the resolver from the
pre-existing lexical layer, per this ticket's own round-1 rationale) and
found TWO ordinary JS/TS idioms the round-1 resolver missed entirely --
both live evasions against any dangerous library whose bare module name is
not already a lexical needle, i.e. every library the resolver exists to
protect:

1. COMPUTED/BRACKET MEMBER ACCESS: `require('axios')['get'](url)` and
   `const ax = require('axios'); ax['get'](url)` -- `_resolve_ts_expr`/
   `_collect_ts_candidates` only ever inspected `identifier`/`member_
   expression` nodes, never `subscript_expression`.
2. DYNAMIC `import()`: `import('axios').then(ax => ax.get(url))` and
   `const ax = await import('axios'); ax.get(url)` -- `_ts_import_table`'s
   walk only ever dispatched on `import_statement`/`variable_declarator`,
   never an `import(...)` CALL expression.

Both FIXED (preferred fix, not a workaround):

- `_resolve_ts_subscript` (new): `subscript_expression` now resolves
  `obj['fn']` the same as `obj.fn` whenever the subscript is a STRING
  LITERAL. `_resolve_ts_expr` also now resolves an inline `require('x')`/
  `import('x')` CALL used directly as the object of a chain (not just when
  bound to a name first), via a new shared `_ts_module_call_target` helper.
  `_collect_ts_candidates` now also treats `subscript_expression` as a
  call-site func / standalone attribute-access site, mirroring the
  existing `member_expression` handling.
- `_ts_dynamic_import_module` (new): recognizes the dynamic `import(...)`
  call form (its `function` field is a bare `import` node, not an
  `identifier`, so it needed its own recognizer, not reuse of
  `_ts_require_call_module`'s identifier check).
- `_unwrap_ts_await`/`_ts_module_call_target` (new): unwraps a leading
  `await` and resolves either a `require()` or dynamic `import()` call to
  its module text -- shared by the declarator binder (`const x = await
  import('mod')` now binds `x -> mod` the same as `const x =
  require('mod')` already did) and by `_resolve_ts_expr`'s inline-call
  case.
- `_bind_ts_dynamic_import_then`/`_ts_dynamic_import_then_module`/
  `_ts_dynamic_import_then_callback`/`_ts_dynamic_import_then_param_name`
  (new): binds a `.then(cb)` callback's first parameter to the imported
  module, handling both the unparenthesized single-arrow-param form (`ax
  => ...`) and the parenthesized/`function` form.
- Found and fixed a SECOND self-shadow bug while extending
  `_bind_ts_variable_declarator`: `const x = await import('mod')` is (like
  `const x = require('mod')` in round 1) simultaneously an import site and
  syntactically an ordinary local-variable declarator -- had to route its
  skip-check through the same `_ts_module_call_target` helper or every
  `await import()` binding would self-shadow its own import, identical to
  the round-1 bug in a second syntactic guise.

CONSERVATIVE LIMITATION, documented and TESTED rather than silently
accepted (reviewer's explicit instruction: "you MUST document it
explicitly... silent gaps... are the exact dishonesty this whole audit
exists to kill"): a FULLY COMPUTED (non-string-literal) subscript --
`ax[dynamicKey](url)` -- resolves to `None`. The actual property name is a
runtime value this static resolver cannot evaluate; closing this
completely needs either a fail-open heuristic (flag whenever the object
resolves to a dangerous import, accepting false positives on legitimate
dynamic dispatch) or light dataflow to resolve simple string-valued local
subscript keys -- a real design decision, not a mechanical extension of
the existing exact-match resolver. Documented in the module's "Known
limitations" block (`src/frob/vet/_capability.py`, T-0377 REVIEWER ROUND 2
section) and locked by `test_computed_subscript_not_detected`. Not Filed as
follow-up ticket T-draft-e7c8b53c (never refiled) (this worktree is off the default
branch, so `frob ticket new` minted a provisional id rather than a
sequential T-#### -- the coordinator/land step will renumber it to a real
id when merged to `main`, per the tool's own off-default-branch
provisional-id behavior).

Adversarial-test results, round 2 (6 new tests in
`TestCapabilityScanTsBindingResolution`, 17/17 total now passing):
- CAUGHT: `require('axios')['get'](url)` (inline require + bracket)
- CAUGHT: `const ax = require('axios'); ax['get'](url)` (aliased + bracket)
- CAUGHT: `import('axios').then(ax => ax.get(url))` (dynamic import .then)
- CAUGHT: `const ax = await import('axios'); ax.get(url)` (await dynamic import)
- CAUGHT (realism confirmation against the actual exec-family library, both
  new forms): `require('child_process')['exec'](cmd)` and
  `import('child_process').then(cp => cp.exec(cmd))` -- note both are ALSO
  caught by the pre-existing lexical layer (bare "child_process" substring
  needle), so this test confirms the full production path end-to-end; the
  4 axios/"net" tests above are what isolate the resolver's own
  contribution.
- NOT CAUGHT (documented conservative limitation, not a bug):
  `ax[dynamicKey](url)` with `ax` a real `require('axios')` binding --
  the OBJECT resolves fine, but the non-literal subscript does not.

Evidence: 6 new node ids appended to this ticket's `evidence:` field
above (17 total), confirmed via `pytest --collect-only -q -o addopts=""`
(all 17 collected under `TestCapabilityScanTsBindingResolution`) and a
fresh full run: `uv run pytest tests/test_vet.py -p no:cacheprovider -q`
-> 190/190 passed (153 pre-existing + 17 TS binding-resolution + 20
T-0328/T-0337 python-resolution tests already counted within that 153; no
regressions anywhere in the file). Two more transient `ARCH001` long-
function warnings appeared during round 2
(`_bind_ts_dynamic_import_then` 32 lines, `_resolve_ts_expr` 35 lines) and
were fixed the same way as round 1's two -- by extracting
`_ts_dynamic_import_then_module`/`_ts_dynamic_import_then_callback`/
`_resolve_ts_member` -- reconfirmed via a fresh `frob check --ticket
T-0377 --json` grep on `_capability.py`: zero new violations remain
(only the same pre-existing `large-file`/waived-`ARCH001`-on-`_scan_file_
operations`/waived-`PERF004` entries).

Worktree hygiene note: `main` advanced during this round (T-0343/T-0418..
T-0426 landed, including a `tickets.md` structural change) while this
round-2 fix was in progress. Per the agent playbook (rule 1b: never `git
stash`; section 9: deletion-filter check), the round-2 changes were
committed first (commit `1f8bb7d`), THEN `git merge main` was run --
producing one real conflict in `tickets.md` (two independently-appended
ticket sections landing in the same place), resolved by keeping BOTH
sides in full (this ticket's new `T-draft-e7c8b53c (never refiled)` ticket ahead of
main's `T-0418`..`T-0426`, per the ledger-splice rule: append-both, never
drop a side). `git diff main --diff-filter=D --stat` is empty after the
merge (no unintended deletions); `make core` was re-run (pyproject.toml/
uv.lock changed in the merge) and the full `test_vet.py` suite (190/190)
was re-verified post-merge.

## Round 3 addendum (reviewer confirmed rounds 1-2 fixed; ONE narrow gap remained)

Reviewer confirmed both original evasions (bracket access, dynamic import,
including nested chaining and the real `child_process`/`exec` forms) are
genuinely fixed, and the false-positive posture is sound. ONE narrow gap
remained: a ZERO-INTERPOLATION TEMPLATE-LITERAL subscript --
`` ax[`get`](url) ``, `` require('cp')[`exec`](cmd) `` -- was silently
dropped. `_resolve_ts_subscript` rejected any `index.type != "string"`,
and a backtick subscript with no `${}` parses to tree-sitter node type
`template_string` (distinct from `string`), so it was rejected even
though `` `get` `` carries IDENTICAL static text to `'get'`. This was ALSO
an honesty gap in the Known-limitations text: it said "a FULLY COMPUTED
(non-literal) subscript resolves to None", but a no-interpolation
template literal is not computed -- the text overclaimed what was
actually covered.

FIXED: `_ts_static_template_text` (new) extracts a `template_string`
node's static text the same way `_ts_string_text` extracts a string
literal's, returning `None` if the node contains any `template_
substitution` child (i.e. has real `${...}` interpolation).
`_ts_static_subscript_text` (new) is `_resolve_ts_subscript`'s single
dispatch point for "is this subscript statically resolvable at all" --
plain string literal OR no-interpolation template literal, `None`
otherwise. An INTERPOLATED template literal (`` ax[`${dynamicKey}`] ``)
correctly stays under the genuinely-computed-subscript exclusion.

Known-limitations text corrected: now reads "a COMPUTED bracket subscript
-- a NON-LITERAL key OR an INTERPOLATED template literal (a static,
no-interpolation template literal DOES resolve) -- never resolves",
replacing the overclaiming "FULLY COMPUTED (non-literal) subscript"
phrasing.

Adversarial-test results, round 3 (2 new tests):
- CAUGHT: `` const ax = require('axios'); ax[`get`](url); `` (static
  template-literal subscript, axios/"net" isolation)
- CAUGHT (real-world repro, reviewer-requested): `` const cp =
  require('child_process'); cp[`exec`](cmd); `` and `` require(
  'child_process')[`exec`](cmd); `` both resolve to `exec` (verified
  directly via `scan_file_capabilities`, not just asserted in a test --
  both printed `frozenset({'exec'})`)
- NOT CAUGHT (documented, correct): `` const ax = require('axios');
  ax[`${dynamicKey}`](url); `` -- interpolated template literal, a
  genuinely computed key, stays under the same accepted false-negative
  gap as `test_computed_subscript_not_detected`
  (`test_interpolated_template_subscript_not_detected`)

Evidence: 2 new node ids appended to this ticket's `evidence:` field above
(19 total), confirmed via `pytest --collect-only -q -o addopts=""` (all
19 collected). Fresh full run: `uv run pytest tests/test_vet.py -p
no:cacheprovider -q` -> 192/192 passed (no regressions). `frob check
--ticket T-0377 --json` grepped on `_capability.py`: zero new violations
(only the same pre-existing `large-file`/waived-`ARCH001`/waived-
`PERF004` entries from every prior round). ruff check/format clean on
both `_capability.py` and `test_vet.py`.

Worktree hygiene note: `main` advanced again during this round
(T-0428 landed). Committed round-3 work first (commit `fc8ea77`, no `git
stash`), then `git merge main` -- this time a CLEAN auto-merge (no
conflict in `tickets.md`); `git diff main --diff-filter=D --stat` empty;
full `test_vet.py` suite (192/192) re-verified post-merge.

Reviewer indicated this should be the last round. Ticket remains
`in-progress`, NOT closed -- reviewer-gated per instructions.
