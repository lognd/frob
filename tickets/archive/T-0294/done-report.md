## Done report

Changed:
- src/frob/graph/dsl.py::_RESERVED_MARKER_VERBS (new constant)
- src/frob/graph/dsl.py::_parse_line
- src/frob/graph/dsl.py::parse_directives
- tests/system/test_cli_check.py (kind="system" -> kind="e2e")
- tests/unit/strata/test_selfconform.py (2x kind="drift" -> kind="unit"; also
  retargeted the second directive's symbol, see below)
- src/frob/app/perf_runner.py (trailing prose moved off the frob:ticket line)
- src/frob/fuzz/_arbitrary.py (trailing prose moved off the frob:todo line;
  T-0002 rebind, see below)
- src/frob/fuzz/_run.py (trailing prose moved off the frob:todo line; T-0002
  rebind, see below)
- tests/test_dup_rungs.py (3x trailing prose moved off frob:ticket lines)
- tests/test_gates.py (trailing prose moved off frob:ticket line; also fixed
  a stray colon on `T-0148:` that was folding into the target)
- tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs (new test class, 2 tests)

Class 1 (frob:secret-fake): added `_RESERVED_MARKER_VERBS` (owner-commented,
pointing at `_secrets.py::_FAKE_MARKER`) and taught `_parse_line`/
`parse_directives` to return/skip `None` for a reserved verb -- no edge, no
`MalformedDirective`. Audited the codebase for other intentional literal
`frob:` markers (grepped for "literal substring"/"unregistered marker"/
"graph-invisible" across src/); `frob:secret-fake` is the only one, so the
reserved set has exactly one member for now.

Class 2 (invalid kind): `tests/system/test_cli_check.py:237` `kind="system"`
-> `kind="e2e"` (CLI system test). `tests/unit/strata/test_selfconform.py:434`
`kind="drift"` -> `kind="unit"` (drift-lock conformance test, target already
resolved). `tests/unit/strata/test_selfconform.py:465` `kind="drift"` ->
`kind="unit"`, AND retargeted the directive from
`_selfconform.py::_EXTENDED_KINDS` to
`_selfconform.py::_observed_extended_kinds_by_node` -- `_EXTENDED_KINDS` is a
module-level constant, which `frob.lang`'s Python extractor does not surface
as a resolvable symbol (verified via `parse_file(...).symbols` returning no
match), so once the directive stopped being globally malformed it produced a
NEW DRIFT002 ("no longer resolves") against a target that in fact never
resolved. `_observed_extended_kinds_by_node` is the function that consumes
`_EXTENDED_KINDS` and is what the test's docstring actually exercises.

Class 3 (trailing prose): all 7 directives fixed by moving the explanatory
prose to the following plain-comment line(s), leaving the directive line as
bare `frob:<verb> <target> [attrs]` -- the simplest sound fix named in the
ticket, no parser change needed since T-0286 already landed
backslash-continuation (which this class deliberately does not use, since
the prose isn't a continuation of the target/attrs). Verified each directive
still binds to its intended ticket/todo target after the edit (spot-checked
via `frob check` graph-build: all 7 sites produce a valid edge, zero of
their prior "bad attribute syntax" warnings remain).

Reserved-marker constant: `_RESERVED_MARKER_VERBS` in
src/frob/graph/dsl.py, `frozenset({"secret-fake"})`, with a docstring-comment
pointing at `_secrets.py::_FAKE_MARKER` as the owner.

Side effect filed as a new ticket, not fixed in scope here: fixing Class 3's
prose for `fuzz/_run.py:30` and `fuzz/_arbitrary.py:41` turned their
`frob:todo T-0002` directives from malformed (invisible to TODO001) into
valid edges -- and T-0002 is `dropped`, so TODO001 correctly started firing
("not bound to an open ticket"). Filed T-draft-9b07cab7 (never refiled) ("Rebind frob.fuzz
deferred-work TODOs off dropped T-0002") and rebound both directives to it
(off-default-branch worktree mints provisional ids; this id will resolve to
a real T-#### once landed against main) rather than silently reopening
T-0002's scope inside this DSL-parser ticket.

Evidence (node-level, recorded via `frob ticket evidence T-0294`):
- tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs::test_secret_fake_is_silently_skipped
- tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs::test_unreserved_unknown_verb_still_reports_malformed
- tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
- tests/test_dup_rungs.py::TestR6Probing::test_fires_on_equivalent_functions_with_renamed_multi_arg_params
- tests/test_gates.py::TestCoverageLoad::test_parses_line_to_symbol_span

Not Filed: T-draft-9b07cab7 (never refiled) (frob.fuzz TODO rebind, see above; will mint a real
T-#### id once this worktree lands against main).

Gates: after `make coverage` re-stamp, `uv run frob check` reports 0
malformed-directive warnings (grep for "malformed directive:" against full
output: 0 hits, was 13 before this change) and `gates` tool summary is
"0 errors, 3 warnings, 205 waived" -- the 3 remaining warnings are
pre-existing TEST005 branch-coverage warnings on files this ticket does not
touch (`_selfconform.py::check_self_conformance`,
`_host_isolation.py::evaluate_host_isolation_waived`,
`_land.py::splice_ledger`), confirmed present on a clean `git stash` of main
tip 4302bb5 before this change. `ty` reports the same 2 pre-existing
diagnostics in `src/frob/vet/_allow.py:72-73` both before and after this
change (confirmed via `git stash`/`git stash pop` A-B comparison) -- out of
this ticket's declared scope, not touched. `ruff check` and
`ruff format --check` both clean over `src/` and `tests/`.
`uv run frob check --only coverage`: TODO001 clear (0), COV001 not present
in output.

`git diff main --diff-filter=D --stat` is empty (deletion-filter clean).

Reviewer re-check finding (post-approval, fixed in same worktree): the
`frob:tests` directive on `TestExtendedKindsDriftLock::
test_extended_kinds_is_disjoint_from_kind_map` had been retargeted from the
unresolvable module constant `_EXTENDED_KINDS` to
`_selfconform.py::_observed_extended_kinds_by_node` to satisfy DRIFT002, but
the bound test never called that function -- a hollow binding satisfying
the gate mechanically without exercising the symbol. Fix path taken:
PREFERRED option -- strengthened the test suite so the binding is honest.
Added a sibling test,
`test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds`, that
writes a real `eval(x)` needle to a tmp file, builds a `CodeBinding` over
it, calls `_observed_extended_kinds_by_node` directly, and asserts its
output is both non-empty and a subset of `_EXTENDED_KINDS` disjoint from
`_KIND_MAP` -- i.e. it exercises the exact `& _EXTENDED_KINDS` intersection
behavior the drift-lock constants describe. `_observed_extended_kinds_by_node`
computes "every node id -> the union of `_EXTENDED_KINDS` capabilities
`scan_file_capabilities` observes across that node's `code=`-bound files",
so it is the actual consumer of the disjointness invariant, not an
unrelated symbol -- no extractor ticket needed. Re-verified: `uv run pytest
tests/unit/strata/test_selfconform.py -q` all pass (26 tests, was 25);
`uv run frob check --only coverage` reports DRIFT002 and COV001 absent from
output (0 hits); full `uv run frob check` still reports 0 malformed-
directive warnings and "0 errors, 4 warnings, 205 waived" (the 4 warnings
are the same pre-existing waived-adjacent PERF/arch items, no new ones);
`ty` still reports the same 2 pre-existing `src/frob/vet/_allow.py:72-73`
diagnostics, confirmed unrelated to this file; `ruff check` and `ruff
format --check` clean. Not closing -- left for re-review per dispatch.
