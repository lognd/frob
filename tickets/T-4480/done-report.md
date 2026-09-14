## Done report

CI run 34817719845 failed once T-4475/T-4477 landed: FMT001
(src/frob/gates/_todo_fmt.py) is a raw len(line) <= limit check with no
noqa awareness at all, so it flagged the canonicalizer's own deliberate,
ruff-E501-clean, noqa-suffixed over-limit line as a NEW finding on the
very output frob fmt had just produced -- the gap flagged during T-4477.

Fix:
- src/frob/gates/_fmt_directives.py: publish NOQA_SUFFIX_RE as a public
  alias of the existing _NOQA_SUFFIX_RE (same regex object, not a copy).
- src/frob/gates/_todo_fmt.py: _fmt001_violations_for_runs imports and
  checks NOQA_SUFFIX_RE.search(raw_line) before flagging an over-limit
  line -- a noqa-suffixed line is compliant.
- tests/gates_suite/test_fix_engine.py: the fixed test's invariant is
  now "every physical line either fits the limit or ends with the noqa
  marker", plus a real `ruff check --select E501` subprocess (skipif
  ruff missing) is clean on the rewrite, and FMT001's own _fmt001_file
  re-verifies clean on its own output -- gate and test now agree on the
  canonical form. --check-repro confirms this is a genuine repro (FAILED
  at parent, not TEST_ABSENT) -- no BUG002 waiver needed.

Gate cleanup found along the way (all within touched/widened scope):
- COV001: added the pre-existing FMT001/directive-canonicalization
  frob:doc anchor to the new public NOQA_SUFFIX_RE.
- LEXCHECK001: allowlisted _fmt001_violations_for_runs in
  _lexical_selfcheck.py (a raw text/regex decision over an already-
  resolved comment line, same class as this file's existing TODO001
  entry for _todo001_bare_comment) -- widened scope to include this
  file for the one allowlist tuple.
- AFFECT001: the new public NOQA_SUFFIX_RE needed its own doc-anchor
  file touched in the same diff -- added a Public API entry to
  docs/modules/gates.md's existing T-0441 section -- widened scope to
  include this doc file.
- TODO001: touching src/frob/gates/_lexical_selfcheck.py at all made
  its OWN pre-existing TODO001-allowlist comment (which literally reads
  "...bare TODO/FIXME marker...") trip the gate it describes -- TODO001
  scans the whole diff-touched FILE, not just touched lines, so this
  was unavoidable once that file needed any edit. Lowercased to
  "todo/fixme", matching the established convention
  _todo001_bare_comment's own docstring already uses for the identical
  self-reference.

Pre-applied the fixed formatter (`python -m frob format --directives`)
to every touched file with frob: directive comments; verified a no-op
against the root checkout's own (main) binary and a real
`ruff check --select E501` clean on all of them.

frob check --ticket T-4480 (via uv run frob, from the worktree): down
to the same 2 pre-existing/unrelated baseline errors as every prior
ticket in this chain (doctor.py DRIFT001, macos-portability.md REF002).

### Changed
```
 docs/modules/gates.md                | 12 ++++++
 src/frob/gates/_fmt_directives.py    | 13 +++++++
 src/frob/gates/_lexical_selfcheck.py | 10 ++++-
 src/frob/gates/_todo_fmt.py          | 51 ++++++++++++++++----------
 tests/gates_suite/test_fix_engine.py | 71 ++++++++++++++++++++++++++++++------
 tickets/T-4480/ticket.md             | 19 ++++++++++
 6 files changed, 144 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4984 warning(s), 970 waived
- error-findings: DRIFT001@src/frob/doctor.py, REF002@docs/design/macos-portability.md
