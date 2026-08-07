## Done report

Landed symbol-form `via` and grammar-enforced `exclusive` exclusivity for
strata's `may` grant, plus a stale-symbol detector, per the ticket's two
stated defects (granularity, cardinality).

Grammar (strata-core/src/parse/grammar_node.rs::Parser.parse_node): a via
entry is unchanged syntax (still a STRING) -- `"path::qualname"` is the
new symbol-form spelling, split at the Python layer, not a new token.
Added an optional `exclusive` trailer after the via list; the parser
itself REFUSES (hard parse error, not a later gate finding) any
`exclusive` that is not paired with exactly one symbol-form via entry --
"exclusive about what?" must have one unambiguous answer at declaration
time. Once that shape is guaranteed, no separate runtime exclusivity
check is needed: a via list narrowed to exactly one symbol already makes
any OTHER site an ordinary SYS100 violation.

Effects join (_effects.py): `_via_glob_and_symbol` splits an entry;
`_via_matches_site` is the shared containment rule (file-form entries
cover every symbol in a matching file -- unchanged migration behavior;
symbol-form entries cover only that symbol or symbols nested inside it).
`check_capability_conformance` now resolves each observed effect's
enclosing symbol (`_enclosing_symbol`, a small local reimplementation of
`frob.lang`'s narrowest-span search -- `src/frob/lang/**` is outside this
ticket's scope, so I did not import the private helper across a package
boundary) and joins via `_declared_kinds_for_effect`, paid for ONLY when
a node actually declares a symbol-form grant (`_node_has_symbol_form_via`)
so a design with no symbol-form via pays no extra parse cost.

"Cannot resolve the named symbol" requirement: `check_stale_via_symbols`
(new, `StaleViaSymbolViolation`, catalogued as SYS109 in
`_selfconform.py`'s module docstring and docs/modules/gates.md) walks
every symbol-form via entry and flags one whose named symbol resolves to
nothing across the node's own bound files -- its own distinct violation
kind, never folded into `CapabilityViolation` and never a silent pass.
Built and independently unit-tested; NOT wired into `frob sys audit`'s
CLI surface, because that wiring needs `src/frob/strata/_audit.py` /
`src/frob/gates/_sys_selfaudit.py` / `src/frob/strata/__init__.py`, all
outside this ticket's declared scope -- filed as its own follow-up
(promoted from draft at land) rather than silently expanding scope.

Migration: `design/frob.strata` was NOT converted -- it still carries 876
file-form via entries (counted directly against the committed file: every
quoted glob inside every `may ... via [...]` clause), matching T-1440's
own precedent of shipping the grammar/join support before the mechanical
per-repo conversion. That count is the argument the doc section
(docs/strata/surface.md#may-scope) makes for doing the conversion
incrementally.

Changed:
- strata-core/src/parse/grammar_node.rs::Parser.parse_node
- src/frob/strata/_ast.py::MayGrantDecl
- src/frob/strata/_models.py::MayGrant
- src/frob/strata/_infra.py::_elaborate_store
- src/frob/strata/_elaborate.py::_elaborate_node
- src/frob/strata/_effects.py::_via_glob_and_symbol (new)
- src/frob/strata/_effects.py::_via_matches (extended)
- src/frob/strata/_effects.py::_via_matches_site (new)
- src/frob/strata/_effects.py::_declared_kinds_for_effect (new)
- src/frob/strata/_effects.py::_node_has_symbol_form_via (new)
- src/frob/strata/_effects.py::_enclosing_symbol (new)
- src/frob/strata/_effects.py::_symbols_for_file (new)
- src/frob/strata/_effects.py::_file_capability_violations (rewritten)
- src/frob/strata/_effects.py::check_capability_conformance (updated join)
- src/frob/strata/_effects.py::StaleViaSymbolViolation (new)
- src/frob/strata/_effects.py::check_stale_via_symbols (new)
- src/frob/strata/_selfconform.py (SYS109 catalog entry, module docstring only)
- design/frob.strata (sync-interface: stratamod interface= list; frob:ticket edge)
- docs/strata/surface.md#may-scope (new subsection)
- docs/modules/gates.md (SYS109 row)

Evidence: 11 pytest node ids (TestSymbolFormViaConformance x3,
TestExclusiveGrammar x4, TestStaleViaSymbol x4), recorded via
`frob ticket evidence`. Also verified end to end interactively: real
`strata_core.parse_source` round trip for `exclusive` acceptance/refusal,
`check_capability_conformance`/`check_stale_via_symbols` against real
files on disk.

Full test files verified green: tests/unit/strata/test_effects.py (33
passed), tests/unit/strata/test_selfconform.py (72 passed, unaffected by
the new symbol-form path since it only activates on symbol-form via).

Gates: `frob check --land-parity` clean (0 unscoped errors) after fixing
the COV002 (frob:ticket edges on every new/changed symbol in _effects.py
and on grammar_node.rs::Parser.parse_node and design/frob.strata),
COV005 (dropped a frob:doc directive that collided with an existing
public-symbol anchor on a private helper), and WIRE001 (check_stale_via_
symbols waived with follow_up citing the wiring draft; the test-file
`_write_module` helper was inlined at each call site instead of waived,
since it was a pure test convenience with no production meaning).
`frob check --only test/archgate/sys --ticket T-1627`: 0 errors on all
three. Rust-side `cargo test` in strata-core could not run in this
worktree (pre-existing pyo3 python-version mismatch in the cargo build
cache, unrelated to this change) -- the grammar change was instead
verified via the actual compiled extension (maturin build through `frob
natives build`) driving real `parse_module`/`elaborate` round trips,
which is the same code path `strata_core.parse_source`'s Python callers
use in production.

Filed: T-1761 (wire SYS109 into frob sys audit -- promoted to a
real id at land).

Not done / disclosed cuts:
- design/frob.strata itself was not converted to symbol-form via (876
  file-form entries remain) -- deliberate, matches T-1440's own
  migration precedent; the count is now documented as the argument for a
  follow-up conversion drive, not done here.
- SYS109 is not yet a live `frob sys audit` finding (see the follow-up
  ticket above) -- the detector function exists and is tested, but
  `frob check --only sys` today runs SYS100-108, not SYS109.
- T-1328 (independent second detector for app-level capability KINDS)
  was reviewed and does not overlap -- it is about kind-level detection
  redundancy (a second scanner proving eval/env/ffi/... independently of
  scan_file_capabilities), orthogonal to this ticket's via-granularity
  and exclusivity work.

### Changed
```
 tickets.md | 407 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 401 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestSymbolFormViaConformance::test_effect_inside_granted_symbol_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestSymbolFormViaConformance::test_effect_outside_granted_symbol_in_same_file_is_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestSymbolFormViaConformance::test_exclusive_grant_still_flags_a_second_site` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestExclusiveGrammar::test_exclusive_with_symbol_form_via_parses` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestExclusiveGrammar::test_exclusive_with_file_form_via_is_a_parse_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestExclusiveGrammar::test_exclusive_with_multiple_via_entries_is_a_parse_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestExclusiveGrammar::test_exclusive_with_bare_via_less_may_is_a_parse_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestStaleViaSymbol::test_resolvable_symbol_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestStaleViaSymbol::test_unresolvable_symbol_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestStaleViaSymbol::test_symbol_matching_a_nested_qualname_resolves` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestStaleViaSymbol::test_file_form_via_entries_are_never_checked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 1 error(s), 851 warning(s), 727 waived
- error-findings: PRE001@tickets/T-1627
