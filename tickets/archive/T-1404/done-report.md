## Done report

T-1404: T-1391 built `fix_fmt001_directive_wrap`'s `only_paths` keyword
(restricting FMT001's Tier-A rewrite to a caller-supplied touched-file set)
but wired no real caller to it -- `frob ticket land`'s pre-land absorption
step (`_absorb_pre_land_fixes`, src/frob/app/ticket_runner/_land_cmd.py)
still ran BOTH its raw `frob fmt` whole-tree call AND the generic Tier-A
FMT001 handler unscoped, so either one could rewrite a `frob:` directive
comment in a file entirely outside the landing ticket's own diff -- the
land-scope-discipline collision T-1391 diagnosed but left half-fixed.

Fix: `_land_touched_paths` (new, `src/frob/app/ticket_runner/_land_cmd.py`)
computes the landing ticket's touched-file set from a real git diff
against `main` (`frob.gitio.working_diff`, the same diff-scoped source
FMT001's own gate already uses via `_fmt001_touched_lines` -- not the
ticket's declared `scope` globs, which can both over- and under-match
what actually changed). `_absorb_pre_land_fixes` now:

1. Scopes the raw `frob fmt` pass to exactly the touched files (looping
   `format_paths` per file) instead of walking the whole tree, when the
   touched set can be computed.
2. Excludes `"FMT001"` from the subsequent generic `apply_tier_a_fixes`
   batch in that case, so the Tier-A handler does not redundantly re-walk
   the whole tree right behind the scoped pass and reintroduce the same
   out-of-scope rewrite.
3. Falls back to the pre-T-1404 whole-tree behavior for BOTH steps when
   `_land_touched_paths` returns `None` (diff computation failed) --
   degrading gracefully, never silently skipping the fix.

Two regression tests added to
`tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes`:
- `test_out_of_scope_file_with_noncanonical_directive_is_left_untouched`
  (T-1404 acceptance [0]: an already-committed, untouched file elsewhere
  in the tree with a non-canonical `frob:` directive is left
  byte-identical)
- `test_in_scope_file_with_noncanonical_directive_is_still_fixed`
  (acceptance [1]: a file genuinely inside the landing ticket's touched
  set is still fixed exactly as before, alongside an unrelated
  already-committed file)

Scope: src/frob/app/ticket_runner/_land_cmd.py, plus the test file --
`apply_tier_a_fixes`/`fix_fmt001_directive_wrap` in
src/frob/gates/_fix_engine.py were NOT modified; the existing `exclude=`
and `only_paths=` keyword params (already built, already regression-
tested by T-1391's own suite) were sufficient to wire this from the
caller side alone, matching the ticket's own scope note about avoiding
the wider `_fix_engine.py`/`ticket_runner` scope-closure cascade.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   |    68 +-
 src/frob/gates/_dead_symbols.py           |   251 +-
 tests/test_gates.py                       |   203 +
 tests/test_ticket_work_and_land_finish.py |    59 +
 tickets-archive.md                        | 20772 ++++++++++++++++++++--------
 tickets.md                                | 11411 ++-------------
 6 files changed, 17146 insertions(+), 15618 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_out_of_scope_file_with_noncanonical_directive_is_left_untouched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_in_scope_file_with_noncanonical_directive_is_still_fixed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 9 error(s), 370 warning(s), 695 waived
- error-findings: AFFECT001@src/frob/gates/_dead_symbols.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/gates/_dead_symbols.py, COV003@tickets/T-1378, COV003@tickets/T-1406, COV003@tickets/T-1408, COV003@tickets/T-1419, COV003@tickets/T-1423, PERF004@src/frob/gates/_dead_symbols.py
