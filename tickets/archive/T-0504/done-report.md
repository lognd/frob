## Done report

Implemented PLACE001, the class-directive placement lint prong (2)
T-0470 dropped. Detects a nearby real symbol a `frob:` directive
plausibly SHOULD have bound to via `following` but did not reach --
NOT raw line distance from the class start (T-0470's dropped
prototype, proven noisy against this repo's own per-field pydantic
idiom).

Design: `_place001_bindings` mirrors `frob.graph.dsl._resolve_block_srcs`'s
exact stacked-comment-propagation algorithm (order, carry state) but
additionally tags each resolved binding with whether it came via a
`following` match (direct, or propagated backward through an unbroken
comment run per T-0313) versus a genuine `enclosing`/bare-path
fallback. `_place001_missed_symbol` then looks, only for genuine
fallback bindings whose enclosing symbol is a CLASS, for a real symbol
within a wider lookahead window (10 lines) than `_find_following_symbol`'s
window (3), requiring nothing but blank lines/comments/decorators in
the gap between the directive and that candidate.

Non-vacuous, both directions proven by TestPlace001Gate:
- test_missed_following_binding_fires: a directive separated from its
  intended `def` by one blank-line-run too many (4 blank lines vs the
  3-line following window) fires.
- test_per_field_pydantic_idiom_is_silent: T-0470's own counterexample
  shape (a directive above one field, real field-assignment code
  before the next real method) does NOT fire, regardless of distance.
- test_directive_directly_above_def_is_silent /
  test_no_nearby_symbol_at_all_is_silent: the ordinary clean cases stay
  silent.

Development note (disclosed, not hidden): an early draft checked only
"did this directive's resolved binding land on a class symbol",
without the via-following/via-enclosing distinction. That is unsound
by itself -- a `frob:doc`/`frob:ticket` comment placed directly above
`class Foo:` resolves via `following` straight to `Foo` (correct,
universal in this repo) even though `Foo` is a class; checking only
the resolved kind cannot tell that apart from a genuine fallback. That
draft fired ~416 findings on this repo's own tree (`frob check --only
coverage`), essentially all on the "directive directly above its own
class" idiom. Fixed by adding the via_following tag described above;
after the fix this repo's own tree shows ZERO PLACE001 findings (the
corpus is clean, non-vacuous only through the constructed unit tests).

Also caught and fixed en route: the new private helper functions
(_place001_missed_symbol, _place001_bindings, _place001_file, _place001)
were initially given `frob:doc docs/modules/gates.md#public-api`
directives copy-pasted from neighboring code -- that target is reused
by many PUBLIC functions elsewhere in this same file, and editing near
one of those reused-target comments is exactly the COV005
directive-target-reuse false-positive class already documented in
T-0509's Done report. Removed the doc directives from these private
helpers (they don't need one; only public API needs COV001 doc
coverage) rather than working around COV005 a second time.

PLACE001 is WARN severity (best-effort, name/position-based, same tier
as COV006). No public API added (all new symbols are private), so no
REL001 version bump needed.

### Changed
```
 .frob-release.json           |   3 +-
 CHANGELOG.md                 |  18 ++
 docs/modules/gates.md        | 127 ++++++++++--
 pyproject.toml               |   2 +-
 src/frob/gates/__init__.py   | 472 ++++++++++++++++++++++++++++++++++++++-----
 src/frob/gates/invariants.py |  67 +++++-
 tests/test_gates.py          | 235 ++++++++++++++++++++-
 tickets.md                   | 196 +++++++++++++++++-
 uv.lock                      |   2 +-
 9 files changed, 1042 insertions(+), 80 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPlace001Gate::test_per_field_pydantic_idiom_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPlace001Gate::test_directive_directly_above_def_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPlace001Gate::test_no_nearby_symbol_at_all_is_silent` (pytest node id, verified passing when recorded)
