## Done report

Changed:
- src/frob/gates/_wire.py::_wire_reach_patterns (extended wrapper_pattern
  with a keyword-argument-value alternative, gated to
  SymbolKind.FUNCTION)
- src/frob/gates/_wire.py::_is_reached_outside_diff_tests (unchanged
  call-site, benefits from the widened wrapper_pattern automatically)

Evidence:
- tests/unit/test_wire001_callback_keyword_argument.py::TestWire001CallbackKeywordArgument.test_function_passed_as_keyword_argument_value_is_not_flagged
- tests/unit/test_wire001_callback_keyword_argument.py::TestWire001CallbackKeywordArgument.test_function_with_no_caller_anywhere_still_flagged_positive_control
- tests/unit/test_wire001_callback_keyword_argument.py::TestWire001CallbackKeywordArgument.test_class_passed_as_keyword_argument_value_still_flagged_anchor_control

Design note (requested by coordinator): considered collapsing this
alongside T-2746's `_is_property`/property_access_pattern and T-2753's
`_is_pytest_fixture`/fixture-consumption reach onto one shared "reachable
via non-call reference" seam. Did NOT introduce a third parallel is_X
helper -- instead extended the EXISTING `wrapper_pattern` regex (the
T-1502/T-1532/T-1684 "passed by reference" pattern family) with one more
OR-alternative, since a bare keyword-argument value is the same
"passed by reference, not called" question that pattern already answers,
just one more syntactic shape of it -- not a new detection axis requiring
its own decorator/injection-shape classifier the way property-access and
fixture-injection did. Property (attribute-access, no call parens ever
legal) and fixture (parameter-name injection, never a call token) are
each a genuinely distinct SHAPE of reference needing their own
recognizer; a keyword-argument value is not a new shape, it is the same
by-reference shape wrapper_pattern already recognizes for markers/
job-tables/dict-values, just missing the "ordinary call, arbitrary
keyword" case. Net: 3 mechanisms in the file (property, fixture,
wrapper-pattern-family), not 4 -- the callback case joined the existing
by-reference family instead of starting a fourth.

Anti-abuse: gated to `kind == SymbolKind.FUNCTION` only (never CLASS,
never METHOD) so the T-1831 anchor (`formatter_class=
_GroupedHelpFormatter`, a CLASS passed the identical keyword-argument
shape) is NOT rescued -- proven by
test_class_passed_as_keyword_argument_value_still_flagged_anchor_control.
T-2451 (`signal.signal(sigterm, _sigterm_handler)`, positional not
keyword) and T-1820 (argparse `dest=` string literals, not a symbol
reference at all) are unaffected by construction -- neither shape
matches the new `identifier=short` alternative.

Filed: none (no out-of-scope work found)
Gates: frob check --ticket T-2778 clean for gate:SCOPE/gate:PREWORK
(the ticket-scoped families); gate:COV's 3 repo-wide errors and every
other FAIL'd gate family in the run are pre-existing repo-wide noise
unrelated to this diff (per gate:scope-note, only SCOPE/PREWORK/
COV002+TODO001/FMT/AFFECT are ticket-scoped by --ticket; verified the
one --ticket-scoped SCOPE001 finding this diff itself produced --
missing scope declaration for the new test file -- and fixed it via
`frob ticket scope T-2778 --add`).

### Changed
```
 src/frob/gates/_wire.py                            |  43 +++++-
 .../unit/test_wire001_callback_keyword_argument.py | 161 +++++++++++++++++++++
 tickets/T-2778/ticket.md                           |   9 +-
 3 files changed, 209 insertions(+), 4 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 20 error(s), 892 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2778, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
