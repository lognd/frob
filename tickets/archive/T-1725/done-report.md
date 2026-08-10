## Done report

New WIRE003 rule (`frob.gates._wire._wire003_stale_verb_references`)
resolves every `frob` verb reference in a tracked hook/doc against the
LIVE CLI dispatch table -- `frob.__main__._build_parser`, walked
recursively via `argparse._SubParsersAction.choices` -- never a
hand-written list of verb names, per the ticket's own explicit
instruction (a hand-written list is the same defect class as the bug).

Both named reference shapes are covered from one extraction path:
- The regex/matcher form: `.claude/hooks/frob-timeout-guard.py`'s own
  `PATTERN` (a raw string, never backtick-wrapped) is found via
  `ast.parse` locating `re.compile(...)` call arguments.
- The prose form: any backtick-quoted span, matching the convention
  `.claude/hooks/frob-suggest.py`'s own suggestion strings already use
  (`` `uv run frob test` ``, etc.) and markdown's own "this is code"
  marker.

Extended-glob alternation (`+()`/`|`) is split into independent
fragments before tokenizing, so `frob +(a|b)` correctly checks BOTH `a`
and `b`, not just the first branch. At most 2 leading tokens are read
per fragment (real `frob` commands never nest past `<verb> <subverb>`),
which also fixes the "T-0001 read as a fake verb" false positive a
naive unbounded token grab would produce on `frob ticket land T-0001`.

SEQUENCING (item 2, the ticket's own instruction): this lands before
T-1567..T-1571's CLI regrouping, as required -- the detector must exist
before the renames it is meant to catch, or it cannot warn about the
event that motivated it.

WIDER SCOPE (measured, as asked): a repo-wide `docs/**/*.md` scan
(backtick spans only) found 48 candidate references across 10 files;
including fenced code blocks (dropped from the shipped implementation)
raised that to 181 across many more files, dominated by fenced blocks
containing command OUTPUT (log lines, JSON, table rows) that reads as
command-shaped to this heuristic without being one, plus doc prose
using backtick-quoted vocabulary (ticket priority levels, board column
names) that happens to sit near the word "frob". This precision gap is
real and disclosed, not silently dropped: `_WIRE003_SCAN_GLOBS`'s own
docstring in `src/frob/gates/_wire.py` and the new "WIRE003 (T-1725)"
section in `docs/modules/gates.md` both state the measured counts and
name what a follow-up (a per-token allowlist, or a stricter anchor
requirement) would need before widening scope is safe at ERROR
severity -- forcing today's heuristic through repo-wide would reproduce
the 997-waiver anti-pattern this repo has already paid for once.

Registered as WIRE003 in `_KNOWN_GATE_RULES` (`frob.gates._waive`), per
the ticket's instruction to register a real id rather than inventing an
unregistered one.

PII012 note (same class as a recent T-1734 fix): the identifier
`_WIRE003_TOKEN_RE`/`token_match`/`token` triggered PII012's
name-signature sweep (matches the "credentials" category's "token"
keyword) -- added to the SAME `_PII012_REVIEWED_NON_PII` allowlist this
repo already uses for the identical homonym elsewhere (`_TYPE_TOKEN_RE`,
`_leaf_token`, etc. -- "a parsed lexical word," never an auth token),
rather than a second suppression style.

### Changed
```
 docs/modules/gates.md                       |  63 +++++++
 src/frob/gates/_pii_structural/_keywords.py |   6 +
 src/frob/gates/_waive.py                    |   6 +
 src/frob/gates/_wire.py                     | 251 +++++++++++++++++++++++++++-
 tests/test_gates.py                         |  99 +++++++++++
 tickets/T-1725/ticket.md                    |  43 ++++-
 6 files changed, 460 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_wire003_matcher_pattern_stale_verb_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_suggestion_string_stale_verb_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_real_verbs_are_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_dotted_module_path_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 1412 warning(s), 726 waived
- error-findings: none (measured, zero errors)
