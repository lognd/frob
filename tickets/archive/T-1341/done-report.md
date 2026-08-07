## Done report

Added fix_suppress001_paired_suppression, a new Tier-A --fix handler
(src/frob/gates/_fix_engine.py) registered in TIER_A_HANDLERS under
"SUPPRESS001", run immediately after FMT001. For every SUPPRESS001
finding it parses the reporting dialect/code back out of the finding's
own message (_parse_suppress001_message, precedent: _waive004_target_rule),
appends that dialect's own suppression comment in this repo's observed
canonical order (mypy type:ignore, noqa, ty:ignore -- _CANONICAL_DIALECT_ORDER),
merges with any pre-existing OTHER code on the same pragma rather than
clobbering it, and never widens an existing bare suppression to coded.
_find_comment_start locates the real trailing comment via tokenize so a
hash-shaped substring inside a string literal is never mistaken for one.

Coordinator addendum (2) folded in: ruff format is delegated to FIRST for
every violating file (_run_ruff_format), before any suppression is
written, since an over-long def/class line is ruff format's own
authoritative territory, never a hand-rolled wrapper -- only a violation
that SURVIVES formatting gets a suppression. If the suppressed line is
still over the limit afterward, a noqa E501 is appended too, UNLESS
ruff's own per-file-ignores configuration already silences E501 at that
path (_code_ignored_for_path, glob-matched against pyproject.toml) --
this is the direct fix for the ticket's driver incident (2493/2623
hand-written noqa comments, 1559/1566 of them dead noise under tests/**).
Covered by
TestSuppress001NoOpSuppressionRefusal.test_no_op_suppression_never_added_under_tests_glob.

Precedence with FMT001 (coordinator addendum 1) resolved explicitly:
SUPPRESS001's handler never touches a line carrying a frob-directive
marker anywhere in its trailing comment at all (_FROB_DIRECTIVE_MARKER_RE),
deferring wholly to FMT001/a human -- documented in both the handler's
own docstring and docs/modules/gates.md. Covered by
TestSuppress001FMT001Precedence.test_frob_directive_bearing_line_is_left_untouched
(asserts the file is byte-identical after two consecutive fix passes).

Idempotent by construction, not bookkeeping: once both dialects' matching
suppressions are present, the underlying diagnostic suppress001_gate
correlates against is itself silenced for both checkers, so a second
fix pass finds nothing left on that line. Covered by
TestFixSuppress001PairedSuppression.test_idempotent_second_fix_pass_is_a_no_op.

Fallout fix (in scope, tightly coupled): tests/test_gates.py's
TestFixEngineTierABatch2.test_tier_a_handlers_dict_covers_every_batch_rule
hardcodes the exact TIER_A_HANDLERS key set and broke the moment
SUPPRESS001 was registered -- updated the one assertion plus added
frob:ticket T-1341 edges (class + method level) to keep COV002 clean;
extended the ticket's declared scope to include tests/test_gates.py via
the ticket scope command with an explicit reason (see ticket ledger).

Pre-land Tier-A absorption note: `frob ticket land`'s own pre-land
apply_tier_a_fixes pass (unscoped, repo-wide by design, section 0.5 of
the playbook) ran FMT001's directive canonicalizer over the WHOLE tree
and re-wrapped two pre-existing frob:waive directives to a slightly
different (still canonical) backslash-continuation line split -- no
waiver text/reason/rule changed, nothing actually deleted, only
re-flowed. Declaring both explicitly, file and rule together, per
land's own OutOfScopeWaiveDeletion guidance, rather than restoring
(restoring just regenerates the identical FMT001 diff on the next land
attempt, since the file's on-main state is the non-canonical one):
- src/frob/app/_daemon_proxy.py ARCH103 re-wrapped, not deleted.
- src/frob/app/_daemon_proxy.py SEC110 re-wrapped, not deleted.

design/frob.strata interface drift (sys sync-interface) and CHANGELOG.md
are land's own derived-artifact absorption, not authored by this ticket.

Gates: check --ticket T-1341 --only gates-fast: 0 errors (exit 0).
check --ticket T-1341 --only gates-native --only gates-security: 0
errors (exit 0) after removing an ast.literal_eval OPAQUE001 flag
(replaced with plain quote-stripping, since the regex already constrains
the captured group to a quoted run with no embedded quote) and fixing a
tokenize.TokenizeError -> tokenize.TokenError ty error (no such attribute
exists on the tokenize module).

ruff check / ruff format --check / ty check: all clean on every touched
file (src/frob/gates/_fix_engine.py, tests/test_gates_fix_engine.py,
tests/test_gates.py).

pytest: 9/9 new tests in tests/test_gates_fix_engine.py pass; the whole
existing tests/test_gates_suppress.py (15) and the FixEngine/Autofix
subset of tests/test_gates.py (26) pass unchanged.

### Changed
```
 docs/modules/gates.md          | 116 ++++++++++--
 src/frob/gates/_fix_engine.py  | 398 ++++++++++++++++++++++++++++++++++++++++-
 tests/test_gates.py            |   3 +
 tests/test_gates_fix_engine.py | 244 +++++++++++++++++++++++++
 tickets.md                     | 123 ++++++++++++-
 5 files changed, 860 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_idempotent_second_fix_pass_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestSuppress001NoOpSuppressionRefusal::test_no_op_suppression_never_added_under_tests_glob` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestSuppress001FMT001Precedence::test_frob_directive_bearing_line_is_left_untouched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
