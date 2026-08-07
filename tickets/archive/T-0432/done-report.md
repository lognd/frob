## Done report

Implemented option (b) from the ticket's own candidate list: a light,
conservative dataflow pass that resolves a computed bracket subscript
when the key is a local name bound to exactly ONE string literal (or
no-interpolation template literal) anywhere in the file --
`const key = 'exec'; ax[key](url)` and `` ax[`${key}`](url) `` (single
substitution, no other content) now resolve the same as `ax['exec'](url)`.

Design decision recorded in the module docstring: candidate (a) (fail-open
-- flag ANY bracket access on an object resolved to a known-dangerous
import regardless of subscript shape) was considered and REJECTED -- the
false-positive cost against ordinary dynamic-dispatch idioms (lookup
tables, plugin registries) was judged too high without a concrete finding
to weigh it against. Candidate (b) is a genuine, non-evadable-by-trivial-
indirection closure for the one shape that matters (a single, unambiguous
local constant) while staying honest about what remains unresolved.

Made genuinely resistant to trivial indirection, not just the one-hop
case: `_ts_local_string_bindings` tracks BOTH `variable_declarator`s and
plain `assignment_expression` reassignments to the same name, and marks a
name permanently ambiguous (excluded from the table) the instant it sees
a second, DIFFERENT literal value OR any non-literal value anywhere in
the file -- it never guesses which binding is "live" at the subscript
site. This closes the naive "just check the last assignment" hole a
careless implementation would have left (a `let key = 'get'; key =
'post';` reassignment case is exercised by
`test_reassigned_const_string_subscript_not_detected`).

Honest negative tests recording what stays out of scope (not attempted,
would need real reaching-definitions dataflow or a precision-cost
decision this ticket explicitly declines to make):
- a name bound to a non-literal value (function-call result, string
  concatenation, another variable) anywhere in the file
  (`test_non_literal_bound_subscript_not_detected`)
- a name reassigned to two different literal values, including via plain
  `=` reassignment, not just a second declarator
  (`test_reassigned_const_string_subscript_not_detected`)
- a template literal with more than one substitution or any surrounding
  literal text (`test_multi_substitution_template_subscript_not_detected`)
- a truly runtime-computed key with no literal binding anywhere
  (`test_computed_subscript_not_detected`,
  `test_interpolated_template_subscript_not_detected` -- pre-existing
  tests, updated comments to clarify they now specifically cover the
  UNBOUND case)

### Changed
```
 docs/modules/vet.md                  |  17 ++-
 src/frob/vet/_capability.py          |  43 +++++-
 src/frob/vet/_capability_registry.py |  76 ++++++++++-
 src/frob/vet/_lockfile.py            |  35 +++--
 src/frob/vet/_obfuscation.py         |  22 +++-
 src/frob/vet/_scan.py                | 112 ++++++++++++----
 tests/test_vet.py                    | 249 +++++++++++++++++++++++++++++++++++
 tickets.md                           | 130 +++++++++++++++++-
 8 files changed, 637 insertions(+), 47 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_local_const_string_subscript_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_local_const_template_substitution_subscript_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_reassigned_const_string_subscript_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_non_literal_bound_subscript_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_multi_substitution_template_subscript_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_computed_subscript_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_interpolated_template_subscript_not_detected` (pytest node id, verified passing when recorded)
