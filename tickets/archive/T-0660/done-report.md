## Done report

Changed:
src/frob/vet/_capability.py::_resolve_ts_expr
src/frob/vet/_capability.py::_resolve_ts_identifier
src/frob/vet/_capability.py::_resolve_ts_member
src/frob/vet/_capability.py::_ts_attr_rebind_lookup
src/frob/vet/_capability.py::_resolve_ts_subscript
src/frob/vet/_capability.py::_collect_ts_candidates
src/frob/vet/_capability.py::_enclosing_ts_scope
src/frob/vet/_capability.py::_record_ts_default_param_aliases
src/frob/vet/_capability.py::_record_ts_destructure_alias
src/frob/vet/_capability.py::_record_ts_declarator_alias
src/frob/vet/_capability.py::_record_ts_alias
src/frob/vet/_capability.py::_build_ts_alias_table
src/frob/vet/_capability.py::_ts_resolved_candidates
tests/test_vet.py::_ts_find (new, test helper)
tests/test_vet.py::_ts_find_all (new, test helper)
tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution (new, 12 tests)
tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates (new, 8 white-box
  mutation-kill tests, added after land-time TEST016 refusal -- see
  "Mutation evidence" section below)

Scope of the fix (docs/design/capability-evasion-taxonomy.md's TS/JS table,
17 static-resolvable rows): T-0377/T-0432 had already closed
import/require/dynamic-import binding and computed-subscript evasions but
left this module's own documented gap open -- "no scope-local alias
copy-propagation" -- so a local reassignment of an already-resolved import
was simply unresolved past that point. This ticket adds a TS/JS sibling of
the python resolver's T-0337/T-0659 alias table
(`_build_ts_alias_table`/`_record_ts_alias`), closing every remaining
taxonomy static row not already covered by T-0377/T-0432:

- Simple assignment (`const f = require("child_process").exec; f(x)`):
  `_resolve_ts_expr` now resolves a bare `require(...)`/`import(...)` call
  used directly as a member-expression object (not just when assigned to a
  name via the import table), and `_record_ts_declarator_alias` records
  the resulting alias for a plain identifier target.
- Chained assignment (`let a, b; a = b = cp.exec; b(x);`): `_resolve_ts_
  expr` peels through a nested `assignment_expression` RHS; `_record_ts_
  alias` records BOTH the outer and inner assignment_expression node's own
  target when the tree walk visits each in turn.
- Destructuring bind (array) (`const [f] = [cp.exec]; f(x);`): new
  `_record_ts_destructure_alias`, positional correspondence between an
  `array_pattern` target and an `array` literal RHS.
- Default parameter forwarding (`function f(cb = cp.exec) { cb(x); }`):
  new `_record_ts_default_param_aliases`, keyed to the function's own
  scope id (parameters already shadow unconditionally in `_ts_scope_
  bound_names`).
- Member rebinding (`obj.run = cp.exec; obj.run(x);`): new `_ts_attr_
  rebind_lookup` (member-expression resolution fallback) + `_record_ts_
  alias`'s member-target branch -- best-effort, BY-NAME object identity
  only (no real points-to; mirrors the python resolver's `_attr_rebind_
  lookup` tradeoff, disclosed in the docstring).
- Closure capture (`function outer(){ const r = cp.exec; return
  function(){ r(x); }; }`): needed no new mechanism -- the alias table is
  keyed by enclosing scope id and `_shadowing_ts_scope`'s walk climbs past
  a nested closure's own (non-capturing) scope to the enclosing one that
  recorded the alias, same as the python resolver.
- Class field/method holding a bound reference (`class C { run = cp.exec;
  }`): NOT implemented -- disclosed, not silently dropped. Resolving a
  later `new C().run(x)` needs points-to tracking through CONSTRUCTED
  instances, a strictly harder problem than the by-local-name object-
  identity best effort this ticket's member-rebind fix gives ordinary
  object rebinding. Documented in the module's Known-limitations block.
- `export ... from`/`export * from`/`export default` re-export rows: NOT
  implemented -- disclosed. These are CROSS-FILE bindings and this
  resolver (like the whole capability scanner) works one file at a time;
  no multi-module linking is attempted, matching the taxonomy's own
  "needs source-module enumerability" caveat for the `export * from` row.

Honest disclosed cuts (not silently narrowed):
- Member rebinding is by-NAME object identity only, not real points-to
  (two different `obj` locals with the same name in different scopes are
  not distinguished beyond normal scope nesting).
- No cross-file `export`/re-export linking (architectural: single-file
  scanner).
- A class field holding a bound reference is not resolved through a later
  constructed-instance call site.
- Nested array-destructuring patterns are not recursed into; only a
  single flat `array_pattern` level is handled (a narrow, documented
  limitation, same posture as the python resolver's nested-pattern gap).

Evidence: node ids observed collected via `uv run pytest tests/test_vet.py
-k TestCapabilityScanTsTaxonomyClosureResolution --collect-only -q -o
addopts=""` (12/248 collected) and all 12 pass individually and as part of
the full `tests/test_vet.py` suite (280 passed, `uv run pytest
tests/test_vet.py -p no:cacheprovider`). All 12 bound via `frob ticket
evidence T-0660 <node> --accepts 0` (T-0660 has a single acceptance
criterion covering both detection and no-regression cases).

Filed: none -- every construct in this ticket's plan was implementable
in-scope (import/import-as/from-import/star-import/re-export/destructuring
were already covered by T-0377/T-0432; this ticket's own remaining gap was
the alias-copy-propagation layer); the two disclosed cuts above (class
field/cross-file export) are architectural, not fixable within this
ticket's scope without a much larger multi-file-linking mechanism -- noted
here rather than filed as a new ticket since no concrete next step short
of that larger mechanism exists yet.

Gates: `FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob check --ticket
T-0660 --only <stage>` clean for lint/static/gates-native/gates-security.
`gates-fast` shows PRE-EXISTING failures unrelated to this ticket's scope,
introduced by the `git merge main` pulled in mid-ticket (T-0711
DRIFT002/TICK006, unrelated files) -- confirmed via `git diff
<pre-merge-commit>..HEAD --stat -- <that file>` that it was never touched
by this ticket's diff, only pulled in by the main merge. No new violation
this ticket's own diff introduces. `uv run ruff format`/`ruff check --fix`
applied to reach 0 lint errors under both PATH ruff and `uv run ruff`.

## Mutation evidence (land-time TEST016 refusal, round 2)

The initial land attempt was REFUSED by TEST016: the bound
`TestCapabilityScanTsTaxonomyClosureResolution` evidence killed 0/8 mutants
of this ticket's diff-touched lines (`_capability.py:2217`, `2246`, `2292`,
`2472`, `2499`, `2500`). Root cause, confirmed by inspection: `_collect_ts_
candidates`'s file-wide tree walk independently RE-RESOLVES the same bare
member/subscript RHS node every "detected" fixture's alias assignment
necessarily contains (e.g. `const f = ax.get;` flags "net" the instant
`ax.get` exists anywhere in the file, via the SEPARATE direct-member-
expression code path, whether or not the alias-table machinery that copies
it to `f` ever runs at all) -- the full-`scan_file_capabilities` API
structurally cannot observe these particular guard predicates.

Fix: added `TestCapabilityScanTsAliasTablePredicates`, 8 WHITE-BOX tests
that import the private resolver functions directly and construct a
hand-parsed AST (via `frob.lang.raw_tree`) so each guard's outcome is the
thing under test, not incidentally reproduced by the lexical/direct-member
path:

- `test_member_rebind_lookup_used_only_for_identifier_object` --
  `_capability.py:2217` compare-Eq-swap (`obj.type == "identifier"` -> `!=`)
- `test_member_rebind_lookup_skipped_without_alias_table` --
  `_capability.py:2217` boolop-And-swap (`and` -> `or`)
- `test_attr_rebind_lookup_climbs_past_non_matching_scope` --
  `_capability.py:2246` compare-Eq-swap (`cur.type == "program"` -> `!=`)
- `test_resolve_expr_peels_through_chained_assignment` --
  `_capability.py:2292` compare-Eq-swap
  (`node.type == "assignment_expression"` -> `!=`)
- `test_default_param_alias_recorded_for_identifier_pattern` --
  `_capability.py:2472` compare-NotEq-swap
  (`pattern.type != "identifier"` -> `==`)
- `test_default_param_alias_skips_missing_default_value` --
  `_capability.py:2472` boolop-Or-swap (`or` -> `and`)
- `test_destructure_alias_tolerates_length_mismatch` --
  `_capability.py:2499` bool-False-negated (`strict=False` -> `strict=True`)
- `test_destructure_alias_binds_only_identifier_elements` --
  `_capability.py:2500` compare-NotEq-swap
  (`left_el.type != "identifier"` -> `==`)

All 8 mutations HAND-VERIFIED locally (T-0859 recipe: edit the operator in
place with `sed -n`/`sed -i` on the exact line, run only the matching test
node id, confirm FAIL, then revert the exact same `sed` in the opposite
direction, confirm `git diff --stat src/frob/vet/_capability.py` is empty
again before moving to the next line). Every one of the 8 flipped from
PASS (unmutated) to FAIL (mutated) -- transcripts:
`AssertionError: assert None == 'axios.get'` (x4, the three compare-Eq/
NotEq swaps plus one), `AttributeError: 'NoneType' object has no attribute
'get'`/`'type'` (x2, the And-swap and the Or-swap, both trigger a crash on
`None` rather than a wrong value), `ValueError: zip() argument 2 is longer
than argument 1` (the `strict=True` mutant), and `KeyError: 'cb'`/`'f'`
(the two remaining NotEq/Eq swaps). `git diff --stat
src/frob/vet/_capability.py` against the committed state is empty after
all 8 reverts -- confirmed source file unchanged from what was already
committed.

New evidence bound to BOTH T-0660 and T-0661 (the coordinator's refusal
report showed an IDENTICAL survivor list for both tickets, since both
tickets' mutation checks run against the same shared, merged diff of
`src/frob/vet/_capability.py` in this worktree) -- all 8 via `frob ticket
evidence <id> <node> --accepts 0`.

### Changed
```
 src/frob/vet/_capability.py | 788 ++++++++++++++++++++++++++++++++++++++------
 tests/test_vet.py           | 532 ++++++++++++++++++++++++++++++
 tickets.md                  | 361 +++++++++++++++++++-
 3 files changed, 1584 insertions(+), 97 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_simple_assignment_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_chained_assignment_outer_target_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_chained_assignment_inner_target_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_array_destructure_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_default_param_forwarding_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_member_rebind_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_closure_capture_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_reassigned_alias_call_via_chained_target_still_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_default_param_benign_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_member_rebind_benign_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_used_only_for_identifier_object` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_skipped_without_alias_table` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_attr_rebind_lookup_climbs_past_non_matching_scope` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_resolve_expr_peels_through_chained_assignment` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_recorded_for_identifier_pattern` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_skips_missing_default_value` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_tolerates_length_mismatch` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_binds_only_identifier_elements` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
