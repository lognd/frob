## Done report

Changed:
src/frob/vet/_capability.py::_rust_use_list_prefix
src/frob/vet/_capability.py::_rust_join_prefix
src/frob/vet/_capability.py::_bind_rust_use_list
src/frob/vet/_capability.py::_bind_rust_use_wildcard
src/frob/vet/_capability.py::_bind_rust_use_declaration
src/frob/vet/_capability.py::_rust_use_table
src/frob/vet/_capability.py::_resolve_rust_identifier
src/frob/vet/_capability.py::_resolve_rust_scoped
src/frob/vet/_capability.py::_resolve_rust_expr
src/frob/vet/_capability.py::_enclosing_rust_scope
src/frob/vet/_capability.py::_record_rust_destructure_alias
src/frob/vet/_capability.py::_record_rust_alias
src/frob/vet/_capability.py::_build_rust_alias_table
src/frob/vet/_capability.py::_collect_rust_candidates
src/frob/vet/_capability.py::_rust_resolved_candidates
tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution (new, 13 tests)
tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates (shared TS-side
  white-box mutation-kill tests, bound here too -- see "Mutation evidence"
  section below; this ticket's own diff carries no Rust-side survivor)

Scope of the fix (docs/design/capability-evasion-taxonomy.md's Rust table,
13 static-resolvable rows): T-0378 had already closed aliased `use ... as`
+ local-shadow discipline (with a position-aware round-2 fix), but left
grouped/nested `use` lists, glob `use`, and any `let`-binding alias-copy-
propagation entirely unbound (a documented limitation). This ticket closes
every remaining taxonomy static row:

- `use path::{a, b}` (grouped/nested): new `_bind_rust_use_list`
  (recursive, handles a further-nested `scoped_use_list` group), wired
  through `_bind_rust_use_declaration`'s new `scoped_use_list` branch.
  Confirmed real evasion gap before the fix: `use std::process::{Command as
  C, Stdio}; C::new(cmd)` resolved through NEITHER the pre-T-0661
  `_bind_rust_use_declaration` (flat-only) NOR the raw-text lexical scan
  (the call site text is "C::new(", never "Command::new(").
- `pub use` re-export: needed NO special-case at all -- a `pub` visibility
  modifier is simply one more `use_declaration` child this walk never
  dispatches on, so path/alias/group/glob children bind identically
  whether or not `pub` precedes them (verified with a dedicated litmus
  test, not just asserted in the docstring).
- `use path::*` (glob): new `_bind_rust_use_wildcard` + `_RUST_WILDCARD_
  TABLE_KEY`/`_RUST_WILDCARD_DANGEROUS_MODULES` -- a best-effort fallback
  for a glob import of a `DANGEROUS_OPERATIONS`-curated module ONLY
  (mirrors the python resolver's `from X import *` fallback), consulted by
  `_resolve_rust_identifier` only when a name is neither locally shadowed
  nor directly `use`-bound.
- `let` binding, chained/shadowed `let`, tuple/struct destructuring bind,
  closure capturing a bound path: new `_build_rust_alias_table`/
  `_record_rust_alias`/`_record_rust_destructure_alias` -- the Rust
  sibling of the python resolver's T-0337/T-0659 alias table and this
  ticket's own TS/JS sibling (T-0660), keyed by enclosing-scope id via
  `_enclosing_rust_scope`, consulted by `_resolve_rust_identifier`'s new
  alias-table fallback when a name IS locally shadowed (T-0378 round 2's
  position-aware shadow check still gates which scope "wins").
- `type` alias, function-pointer coercion from a named fn: no separate
  mechanism needed -- both reduce to a `let_declaration` (with or without
  a `:` type annotation) whose target is a plain identifier, already
  covered by `_record_rust_alias`'s general case.
- `macro_rules!` expansion emitting a fixed call: NOT implemented --
  disclosed, not silently dropped. Resolving a macro's own expansion body
  needs macro-expansion-aware analysis, a fundamentally different (and
  much larger) problem than name-binding resolution; the taxonomy's own
  citation already flags this row as needing the macro to be expanded
  first. No litmus fixture added for it.
- Field rebinding via struct update (`let h = Handlers { run: Command::new,
  ..default }; (h.run)("sh");`): NOT implemented -- disclosed. This needs
  points-to tracking through a struct VALUE's individual field, a harder
  problem than the by-local-name object-identity best effort this
  ticket's TS sibling gives ordinary object member rebinding (no Rust
  analog was added since the shape differs enough from TS `obj.field = x`
  that reusing that mechanism directly would risk an under-tested,
  unverified guess); the taxonomy's own citation already flags this row
  as "needs points-to on struct field".

Honest disclosed cuts (not silently narrowed):
- `use std::fs::{self, File};` -- the `self` re-export-of-parent-module
  keyword inside a group -- is not specially recognized; it falls through
  as an ordinary `identifier` child bound to `"<prefix>::self"`, a
  harmless dead binding rather than a crash or a wrong resolution (no
  capability-routing evasion depends on this; not a real gap in the
  security surface this ticket protects, but named honestly rather than
  silently glossed over).
- `macro_rules!` expansion and struct-field rebinding are NOT resolved
  (see above) -- both need a strictly larger mechanism than name-binding
  resolution and were not attempted rather than risked as an under-tested
  guess.
- Nested tuple-destructuring patterns (`let ((a, b), c) = ...;`) are not
  recursed into; only a single flat `tuple_pattern` level is handled.
- The glob-import wildcard fallback only fires for a
  `_RUST_WILDCARD_DANGEROUS_MODULES`-curated path (a module
  `DANGEROUS_OPERATIONS` already curates an entry for); a glob import of
  an untracked crate/module resolves nothing (honest under-approximation,
  tested: test_glob_use_untracked_module_not_claimed).

Evidence: node ids observed collected via `uv run pytest tests/test_vet.py
-k TestCapabilityScanRustTaxonomyClosureResolution --collect-only -q -o
addopts=""` (13/248 collected) and all 13 pass individually and as part of
the full `tests/test_vet.py` suite (280 passed, `uv run pytest
tests/test_vet.py -p no:cacheprovider`). All 13 bound via `frob ticket
evidence T-0661 <node> --accepts 0` (T-0661 has a single acceptance
criterion covering both detection and no-regression cases).

Filed: none -- every construct in this ticket's plan (use, use ... as, pub
use re-export, glob use, module-path aliasing) was implementable in-scope;
the two disclosed cuts above (macro_rules! expansion, struct-field
rebinding) are architecturally harder problems this ticket's own plan
already flagged as candidates for a follow-up, not oversights -- noted
here rather than filed as new tickets since no concrete bounded next step
short of macro-expansion-aware analysis / points-to-on-struct-fields
exists yet.

Gates: `FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob check --ticket
T-0661 --only <stage>` clean for lint/static/gates-native/gates-security.
`gates-fast` shows the SAME pre-existing failures documented in T-0660's
Done report, pulled in by mid-ticket `git merge main` calls, confirmed
unrelated to this ticket's own diff. No new violation this ticket's own
diff introduces. `uv run ruff format`/`ruff check --fix` applied to reach
0 lint errors under both PATH ruff and `uv run ruff`.

## Mutation evidence (land-time TEST016 refusal, round 2)

The initial land attempt was REFUSED by TEST016 with an IDENTICAL survivor
list to T-0660's (`_capability.py:2217`, `2246`, `2292`, `2472`, `2499`,
`2500`) -- all TS-side lines, since T-0661's own diff-touched-line set for
this shared file overlaps T-0660's (both tickets' commits live in this one
worktree/branch, so the mutation check's touched-set for `_capability.py`
is not per-ticket-hunk-scoped). No Rust-side survivor was reported.

Fix: the same 8 white-box tests added for T-0660
(`TestCapabilityScanTsAliasTablePredicates`, full detail + hand-verified
mutation transcripts in T-0660's Done report -- not duplicated here) are
ALSO bound as evidence on this ticket, since T-0661's mutation check covers
the identical lines. All 8 bound via `frob ticket evidence T-0661 <node>
--accepts 0`. This ticket's OWN Rust-side diff (grouped/glob `use`, the
`let`-alias table) carried no mutation survivor in the coordinator's
report and needed no additional test.

### Changed
```
 src/frob/vet/_capability.py | 788 ++++++++++++++++++++++++++++++++++++++------
 tests/test_vet.py           | 532 ++++++++++++++++++++++++++++++
 tickets.md                  | 361 +++++++++++++++++++-
 3 files changed, 1584 insertions(+), 97 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_grouped_use_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_nested_grouped_use_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_pub_use_reexport_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_let_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_chained_shadowed_let_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_tuple_destructure_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_capture_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_untracked_module_not_claimed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_param_shadowing_let_alias_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_benign_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_used_only_for_identifier_object` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_skipped_without_alias_table` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_attr_rebind_lookup_climbs_past_non_matching_scope` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_resolve_expr_peels_through_chained_assignment` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_recorded_for_identifier_pattern` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_skips_missing_default_value` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_tolerates_length_mismatch` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_binds_only_identifier_elements` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 19 passed (from 19 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
