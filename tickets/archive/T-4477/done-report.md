## Done report

Root cause: T-4475's fix appended a noqa marker only when the WHOLE
remainder of a run was the final, unsplittable line (_wrap_cut_point's
cut_point-is-None branch). A run whose unsplittable token is immediately
followed by a trailing kind=/reason= field -- frob:tests <node id>
kind="integration" -- still took the OTHER branch: search forward from
the token for the next space, cut there, keep wrapping the rest. That
produced a MIDDLE physical line (the token plus a continuation
backslash) which was ALSO over budget but got no noqa, since only the
true final line did. T-4474's land was refused on exactly this shape, 7
times, in src/frob/tickets/_land.py and
src/frob/tickets/_land_passenger_identity.py.

Fix: _wrap_cut_point no longer searches forward for just the offending
token's own end. Once no clean word-boundary cut exists within budget,
the ENTIRE remainder -- trailing attrs included -- becomes the final,
unsplittable physical line. This reuses T-4475's own noqa-on-final-line
contract completely unchanged; no new marker-placement code, and no
changes needed to _land_git_ops.py's _normalize_waive_fragments (already
strips a trailing noqa per T-4475, and the marker is now always
trailing, never mid-run) -- _land_git_ops.py stayed in scope per the
ticket but needed no edit.

Considered and rejected: embedding the noqa marker mid-run, before the
token's own continuation backslash (e.g. "<token>  # noqa: E501 \").
Verified by hand that ruff DOES honor a noqa marker followed by more
text on the same physical line (a real subprocess check). But it fails
round-trip: the marker would fold back into logical_text sitting BEFORE
the trailing kind=/reason= fields on the next canonicalize pass (not at
the true end), so _rewrite_directive_run's existing _NOQA_SUFFIX_RE
escape hatch (end-anchored, T-0985) would never recognize it as
already-suppressed -- it would re-wrap, and re-embed a marker, every
single pass. Not idempotent. The merge-everything-onto-one-line approach
has no such problem since it is the exact case T-4475 already proved
idempotent.

Also considered: reordering the directive's rendered text so trailing
attrs come before the unsplittable target, making the target the final
token by construction. Rejected: the real parser (frob.graph.dsl.
_parse_target) derives `target` as "everything up to the first space" --
target must stay first in the logical text or a reordered directive
would parse a trailing attribute's own text as the target.

Tests: TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477 -- the exact
T-4474 repro shape (a 135-char node id + kind="integration"): joins onto
one final noqa line (not a middle line), parses to the same
target/kind via the real frob.graph.dsl._parse_line (not a
reimplementation), idempotent on a second canonicalize pass, and a real
`ruff check --select E501` subprocess is clean. Updated
TestNodeIdNeverSplitT4179 (now merges onto one line, matching the new
contract).

Verified by hand against a COPY of main's src/frob/tickets/_land.py (out
of this ticket's own scope to edit -- T-4474 owns it): `frob format
--directives` rewrites it, `ruff check --select E501` on the result
reports 0, and a second format pass is a no-op (the ticket's own stated
acceptance criterion).

Pre-applied the fixed formatter to this ticket's own two touched files
(src/frob/gates/_fmt_directives.py, tests/test_gates_fmt_directives.py)
so main's current (T-4475-only) canonicalizer is a no-op on them --
verified with the root checkout's own binary (0 files would change) and
a real ruff check --select E501 (clean). --check-repro hits the same
documented T-2025 pre-land limitation as the two prior tickets in this
chain (a brand-new test has no pre-fix ref to diff against once land
squashes test+fix into one commit) -- not a regression.

### Changed
```
 src/frob/gates/_fmt_directives.py  |  47 +++++++++++-----
 tests/test_gates_fmt_directives.py | 109 ++++++++++++++++++++++++++++++++++++-
 tickets/T-4477/ticket.md           |   6 ++
 3 files changed, 147 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477::test_target_plus_trailing_kind_joins_one_final_noqa_line` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477::test_directive_still_parses_to_the_same_node_id_and_kind` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477::test_idempotent_on_a_second_canonicalize_pass` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477::test_ruff_check_e501_is_clean_on_every_line` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestNodeIdNeverSplitT4179::test_pytest_node_id_directive_value_is_never_split` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 4875 warning(s), 970 waived
- error-findings: DRIFT001@src/frob/doctor.py, FMT001@tests/test_gates_fmt_directives.py, PRE001@tickets/T-4477, REF002@docs/design/macos-portability.md
