## Done report

Implemented the help-surface rework (T-1571, acceptance[0] on T-1238):
`frob --help`'s top-level subcommand listing now presents the small set
of intent-named verb groups first (`_VERB_GROUP_NAMES`: explore/quality/
design/ops from T-1238/T-1567/T-1568/T-1569, plus the pre-existing
"already atomic" groups the design doc names alongside them -- ticket/
vet/serve), then every other still-supported flat command under a
separate "also available directly" heading, instead of one intermixed
alphabetical list.

Implementation: `_GroupedHelpFormatter(argparse.HelpFormatter)` overrides
`_format_action` to intercept only the root parser's `_SubParsersAction`
and render its choice pseudo-actions in two labeled sections. Only the
ROOT parser is built with `formatter_class=_GroupedHelpFormatter`
(`_build_parser`) -- `add_parser()`-created nested subparsers do NOT
inherit `formatter_class`, so every subgroup's own `--help` (`frob
quality --help`, etc.) stays the ordinary flat listing, correctly scoped
to just the top-level surface this acceptance criterion is about
(verified directly, test_nested_subparser_help_is_unaffected).

Fixed along the way: a zero-arg `super()` call cannot be used inside a
generator expression (loses the compiler-injected `__class__` cell) --
bound the base class's `_format_action` once instead. Two real gate
findings in my own new code: PERF002 (a test's `.index()` call inside a
loop -- fixed by slicing the help text once and using substring
containment instead of `.index()` per name) and two ty diagnostics (a
private-attribute chain the type checker cannot narrow through
`Optional` -- rewrote to a `next(... isinstance ...)` walk, the same
pattern `_collect_option_strings` already uses elsewhere in this file).

WIRE001 (3 findings): `_GroupedHelpFormatter` and its two methods are
genuinely wired (passed as `formatter_class=`, invoked internally by
argparse's own help machinery) but the best-effort callgraph cannot
trace a class-constructor-kwarg-then-internal-callback chain -- same
class of gap as this repo's cross-package DEAD001 waivers (T-1024
precedent). Waived with follow_up=T-1831, a docs ticket
recording this as a permanent, by-design gap (WIRE002 requires a real
ticket id outside tests/ trees).

Docs: docs/design/cli-regrouping.md's help-surface-rework section
rewritten from "acceptance[0], not yet implemented" to "T-1571,
IMPLEMENTED" with the actual shape built; the frob:doc anchor in
__main__.py updated to match the new heading slug.

Pre-existing, out-of-scope findings disclosed rather than fixed or
silently left unmentioned (same 3 files/4 findings already disclosed and
filed as T-1828 while landing T-1570 earlier in this same series): a
full unscoped `frob check --land-parity` still shows ARCH001 x2, ARCH103,
COV001 in src/frob/app/ticket_runner/_query.py and src/frob/tickets/
_doable.py, confirmed predating this ticket (T-1738's own land,
0b51c6766, a different agent). Neither file is in T-1571's scope or
touched by its diff.

Verification: `uv run frob check --only gates-fast --ticket T-1571` and
`--only gates-native --only gates-security --ticket T-1571` both clean
except the 4 pre-existing T-1738/T-1828 findings named above (0 new
COV002/WIRE001/PERF errors); `pytest tests/unit/test_main_entry.py
tests/integration/test_interfaces.py` 31 passed.

This closes out the T-1567..T-1571 CLI-regrouping series: quality/
design/ops verb groups, the ticket/debt/deprecated naming resolution,
and the help-surface rework are all landed on main.

### Changed
```
 tickets/T-1571/ticket.md           | 32 +++++++++++++++++++++++++++++++-
 tickets/T-1831/ticket.md | 34 ++++++++++++++++++++++++++++++++++
 2 files changed, 65 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_verb_groups_listed_before_also_available_directly_section` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_non_group_verb_listed_after_also_available_directly` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_nested_subparser_help_is_unaffected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 601 warning(s), 740 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/tickets/_doable.py, PRE001@tickets/T-1571
