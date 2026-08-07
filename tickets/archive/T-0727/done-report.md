## Done report

PythonAdapter._py_class_fields gated on `c.type == "expression_statement"`
wrapping a class-level annotated assignment, but tree-sitter-python's
grammar yields the `assignment` node directly as a named child of the
class `block` -- no expression_statement wrapper -- so every class-level
field was silently dropped. Verified the real grammar shape directly
(tree-sitter-language-pack parse of `class Foo:\n    x: int = 0\n    y:
str\n` shows `block -> assignment` with no wrapper) before changing the
gate: now the loop accepts the assignment node directly, still
transparently unwrapping an expression_statement if one is ever present
(defensive, matches the doc comment's honesty about the real shape).

T-0615's four-way equivalence meta-test had pinned this bug as a named,
documented waiver test (`test_python_field_detection_is_a_documented_
waiver`, asserting `derived.fields == []` for python). Per T-0727's own
acceptance criterion, that waiver assertion is now folded into
`test_derived_class_has_the_field_and_one_method`, which asserts full
4-way parity (python included) instead of carving python out.

T-0615 is already archived (tickets-archive.md, ticket state done) with
its own Evidence list pointing at the now-removed waiver test node id;
extended T-0727's scope (frob ticket scope --add tickets-archive.md,
reasoned) to update that stale archived evidence line so COV003 stays
clean -- this is a direct, in-scope consequence of T-0727's fix, not
unrelated archive editing.

### Changed
```
 src/frob/arch/_python.py | 13 +++++++++----
 tests/unit/test_arch.py  | 29 ++++++-----------------------
 tickets-archive.md       |  4 +---
 3 files changed, 16 insertions(+), 30 deletions(-)
```
(the done-report tool's own diff detection reported "no changed files
detected" for an uncommitted working tree against main -- the stat above
is `git diff main --stat` run directly and observed, not estimated.)

### Evidence
- `tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_derived_class_has_the_field_and_one_method` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s), plus the full
  `tests/unit/test_arch.py` file: 147 passed, 0 failed, observed via
  `uv run pytest tests/unit/test_arch.py -p no:cacheprovider -n0`)
- gates: `uv run frob check --ticket T-0727 --only <stage>` for each of
  lint/static/gates-fast/gates-native/gates-security (the chunked loop,
  per playbook section 3b) -- 0 errors in every stage-group, all
  warnings pre-existing/waived; a bare `frob check --ticket T-0727`
  refuses under FROB_AGENT (expected, not a failure) which is why the
  CLI's own done-report step reported gates as unmeasured.
