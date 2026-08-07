## Done report

Implemented type-generalizing anti-unification: `frob.dup._template`
classifies a hole as a TYPE hole when its bound node's immediate parent
is a real type-annotation wrapper node (`_TYPE_WRAPPER_LABELS`: python's
`type` node -- `def f(a: int)` parses `int` as `type -> identifier` --
and typescript's `type_annotation`) in EVERY group member. A hole that
is type-shaped in some members but a plain value in others is left as an
ordinary value hole -- the ticket's explicit "consistency guard" (never
emit a bogus generic when the sides do not agree).

Two type holes whose per-member bound-text sequence agrees exactly
(e.g. a parameter annotation and the return annotation it matches, both
diverging int/str identically across members) are unified into ONE
shared type variable rather than getting independent names -- verified
directly: `def f(x: int) -> int` vs `def f(x: str) -> str` produces
`type_params == ("T0",)` and a skeleton `def f(x: T0) -> T0:`, not two
separate placeholders.

Model additions (both additive, non-breaking): `CloneBinding.type_var:
str | None = None` and `CloneTemplate.type_params: tuple[str, ...] = ()`.
A classified hole renders as its type-variable name directly in
`skeleton_text` (previously always `$hole_N`); `suggested_signature`
gains a `TN = TypeVar("TN")` preamble per distinct type parameter, and
its extracted-parameter list synthesizes only from the REMAINING value
holes (a type hole is not a call-site argument).

This is pure Python postprocessing over the existing `anti_unify` kernel
output and `frob.lang`'s already-populated node arrays -- no `frob-core`
(Rust) change was needed; the classification only needed parent-label
lookups the Python side already has via the `(labels, parents)` arrays
`_template.py` was already building.

Cross-language honesty (per the ticket's own text): rust/c/cpp place a
type node as a direct, unwrapped sibling distinguished only by
tree-sitter FIELD NAME, which `frob.lang.TreeNode` does not carry today
(label + children + span only) -- extending it is a `frob.lang` change,
out of this ticket's declared scope. Not Filed T-draft-f67069a7 (never refiled) for that
follow-up rather than silently leaving it undocumented; a rust/c/cpp
type-position hole still behaves as an ordinary value hole today (no
regression, just not yet classified).

Updated docs/modules/dup.md with a new "Type-hole classification
(T-0287)" subsection under "Reverse-templating report", cross-linked via
`frob:describes src/frob/dup/_template.py::_classify_type_vars`.

Ran the full targeted dup suite (tests/test_dup*.py,
tests/unit/test_dup*.py) plus ruff/ty/gates scoped to this ticket -- all
clean except one pre-existing REG003 error inherited from main
(docs/design/registry/pii.yaml referencing a since-closed ticket,
introduced by another concurrently-landed ticket, entirely unrelated to
frob.dup and outside this ticket's declared scope).

### Changed
```
 .frob-release.json              |   4 +-
 docs/modules/dup.md             |  39 +++++++
 src/frob/dup/_exhaustiveness.py |  78 ++++++++------
 src/frob/dup/_models.py         |  42 ++++++--
 src/frob/dup/_pipeline.py       |  64 ++++++------
 src/frob/dup/_template.py       | 139 +++++++++++++++++++++++--
 tests/test_dup.py               |  62 ++++++++---
 tests/unit/test_dup.py          |  40 +++++++
 tests/unit/test_dup_template.py |  87 ++++++++++++++++
 tickets.md                      | 225 ++++++++++++++++++++++++++++++++++++++--
 10 files changed, 681 insertions(+), 99 deletions(-)
```

### Evidence
- `tests/unit/test_dup_template.py::TestTypeHoleClassification::test_matching_type_annotations_propose_one_shared_type_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestTypeHoleClassification::test_value_divergence_alongside_type_divergence_stays_separate` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestTypeHoleClassification::test_type_position_in_one_member_only_stays_a_value_hole` (pytest node id, verified passing when recorded)
