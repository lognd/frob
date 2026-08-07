## Done report

EPIC T-0330's "Logan Smith" type-driven-design slice of the ARCH1xx
catalog. Adds a new module `src/frob/arch/_typedesign.py` with four
checks, all written once against the T-0609 normalized model, same
convention as `_solid.py`/`_layering.py`:

- `check_illegal_states_representable`: a class's `bool`-typed field
  runtime-guarded (a branch mentioning both the bool field's name AND
  another field's name, immediately followed by a raise -- reusing the
  same line-adjacency guard-clause proxy LSP's strengthened-precondition
  check uses) inside some method's own body.
- `check_primitive_obsession`: a function/method signature with 3+ raw
  `str`/`int`/`float`-typed params (a same-file, single-signature proxy;
  disclosed simplification of the ticket's fuller "repeated co-occurrence
  across call sites" framing, which would need a project-wide scan).
- `check_parse_dont_validate`: a function/method with exactly one param,
  guarded by a branch+raise on that param, whose declared return type is
  IDENTICAL to the param's own declared type -- validates then hands back
  the same unrefined type instead of a refined one.
- `check_boolean_flag_param`: a PUBLIC function/method with a bool param
  its own body branches on internally -- a split-function candidate.

SCOPE-LEASE BLOCKER (disclosed, worked around, not routed around):
T-0621's declared scope does NOT include `src/frob/arch/_models.py`, and
at implementation time T-0620 (a sibling in the same ARCH1xx cluster)
still held an active scope lease on that file (left `in-progress` per
this dispatch's own "do not close or land" instruction). `frob ticket
scope T-0621 --add src/frob/arch/_models.py` was attempted first and
refused with `ScopeLeaseConflict: requested --add glob overlaps a path
leased by another in-progress ticket`. Rather than stall this entire
ticket on another ticket's land timing, the four checks build a LOCAL
`TypeDesignCategory`/`TypeDesignSuggestion` pair (`_typedesign.py`'s own
scope) that mirrors `frob.arch._models.ArchCategory`/`ArchSuggestion`'s
shape field-for-field instead of extending the shared `Literal`. Filed
T-0892 ("arch: fold TypeDesignCategory into ArchCategory once
_models.py lease is free") as the tracked, purely-mechanical follow-up --
the four check functions' logic will not change, only which model they
construct.

`analyze_project` dispatch wiring, a real ARCH1xx gate, and
`frob.arch.__init__` re-export are all out of this ticket's scope,
matching every sibling ticket's own disclosed gate-wiring cut.

### Changed
```
docs/modules/arch.md          | type-driven-design section + 4 top-table rows
src/frob/arch/_typedesign.py  | new file, ~375 lines
tests/unit/test_arch.py       | 9 new tests across 5 new test classes
```

### Evidence
Collected via `pytest tests/unit/test_arch.py -p no:cacheprovider -q`
(113 passed, full file) and `--collect-only` (all 9 node ids below
resolved):
- tests/unit/test_arch.py::TestIllegalStatesRepresentable::test_bool_field_cross_field_guard_flagged
- tests/unit/test_arch.py::TestIllegalStatesRepresentable::test_bool_field_alone_not_flagged
- tests/unit/test_arch.py::TestPrimitiveObsession::test_three_plus_raw_params_flagged
- tests/unit/test_arch.py::TestPrimitiveObsession::test_two_raw_params_not_flagged
- tests/unit/test_arch.py::TestParseDontValidate::test_validates_then_returns_same_type_flagged
- tests/unit/test_arch.py::TestParseDontValidate::test_validates_then_returns_refined_type_not_flagged
- tests/unit/test_arch.py::TestBooleanFlagParam::test_public_function_branching_on_bool_param_flagged
- tests/unit/test_arch.py::TestBooleanFlagParam::test_private_function_not_flagged
- tests/unit/test_arch.py::TestRunTypeDesignChecks::test_combines_all_four_checks

`frob check --only <lint|static|gates-fast|gates-native|gates-security>
--ticket T-0621` (chunked loop), measured after a `git merge main`.

### Filed
T-0892 -- "arch: fold TypeDesignCategory into ArchCategory once
_models.py lease is free (T-0621 follow-up)", `feature` kind, scope
`src/frob/arch/_typedesign.py,src/frob/arch/_models.py,docs/modules/
arch.md,tests/unit/test_arch.py`.

### Gates
`frob check --only <lint|static|gates-fast|gates-native|gates-security>
--ticket T-0621`: lint/static/gates-native/gates-security all 0 errors.
gates-fast has exactly one remaining error, `TICK003` (68 closed tickets
un-archived, threshold 60) -- the same pre-existing repo-wide housekeeping
debt already disclosed in T-0620's Done report, not caused by or scoped
to this ticket. An `INV006` (exclusivity-claim vocabulary) finding fired
on the new module's docstring; disposed with a targeted `frob:waive
INV006` following the exact `frob.arch._solid`/`_protocol_excuse`
precedent already established in this cluster.

### Changed
```
 docs/modules/arch.md         | 253 ++++++++++++++
 frob.toml                    |  24 ++
 src/frob/arch/_layering.py   | 380 +++++++++++++++++++++
 src/frob/arch/_models.py     |  18 +
 src/frob/arch/_solid.py      | 278 +++++++++++++++-
 src/frob/arch/_typedesign.py | 376 +++++++++++++++++++++
 tests/unit/test_arch.py      | 770 +++++++++++++++++++++++++++++++++++++++++++
 tickets.md                   | 289 +++++++++++++++-
 8 files changed, 2381 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestIllegalStatesRepresentable::test_bool_field_cross_field_guard_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestIllegalStatesRepresentable::test_bool_field_alone_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPrimitiveObsession::test_three_plus_raw_params_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPrimitiveObsession::test_two_raw_params_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestParseDontValidate::test_validates_then_returns_same_type_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestParseDontValidate::test_validates_then_returns_refined_type_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestBooleanFlagParam::test_public_function_branching_on_bool_param_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestBooleanFlagParam::test_private_function_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRunTypeDesignChecks::test_combines_all_four_checks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
