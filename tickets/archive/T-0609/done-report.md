## Done report

EPIC T-0329's ten blocked siblings (T-0610-T-0612, T-0614, T-0616-T-0625)
all need one shared, language-agnostic model of source structure before
any of them can write a single check-once-fires-everywhere rule. This
ticket defines that model (`src/frob/arch/_normalized.py`): pydantic
types for module/class/function/method/param/branch/loop/call/import/
override/field-access/return/raise/catch, plus a `LanguageAdapter`
Protocol each per-grammar walker will implement to produce it. The field
set was derived directly from what the just-landed T-0332 pattern
recommender (`frob.arch._patterns`) already needs to walk (isinstance
chains, state-field chains, telescoping constructors, wrap-delegate,
scattered construction) so the eventual migration (T-0610) has no missing
entity to retrofit. No existing check is migrated or behavior-changed in
this ticket -- `frob.arch._python`/`_cpp` keep parsing tree-sitter
directly, exactly as before; this is model + protocol only, per the
ticket's own acceptance criteria.

### Changed
```
 docs/modules/arch.md         |  48 +++++++
 src/frob/arch/_normalized.py | 274 +++++++++++++++++++++++++++++++++++++
 tests/unit/test_arch.py      | 112 +++++++++++++++
 tickets.md                   | 316 +++++++++++++++++++++++++++++++++++++++++--
 4 files changed, 741 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestNormalizedModel::test_hand_built_python_snippet_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestNormalizedModel::test_language_adapter_is_a_runtime_checkable_protocol` (pytest node id, verified passing when recorded)
