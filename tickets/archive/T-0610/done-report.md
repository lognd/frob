## Done report

Added `PythonAdapter` (`frob.arch._python`), a `LanguageAdapter` (T-0609)
implementation that builds a `NormalizedModule` from the existing
tree-sitter parse, reusing this module's own node-level walkers
(`_iter_py_functions`, `_py_max_nesting`, `_py_cyclomatic`, `_py_methods`,
`_annotation_text`) rather than re-deriving grammar knowledge. Extended
`NormalizedFunction` with `max_nesting_depth`/`cyclomatic` fields, computed
by the adapter off the language's own FULL subtree (matching the pre-
migration walk's semantics exactly, including through nested function/class
boundaries) rather than derived from the flattened `branches`/`loops`/
`catches` lists, which deliberately stop at a nested function/class
boundary and would under-count.

Migrated `_check_long_functions`, `_check_god_classes`, and
`_check_deep_nesting` to read `NormalizedModule`/`NormalizedFunction`/
`NormalizedClass` instead of walking `tree` directly -- all three keep
their existing public signature (`tree: object`) since `frob/arch/
__init__.py` (the caller) is outside this ticket's declared scope; each
internally builds the normalized module via `PythonAdapter`/
`_py_build_module` first. Ran the pre-existing 56-test `tests/unit/
test_arch.py` suite unchanged before and after: 56 passed both times,
same suggestions on the same fixtures (long-function/god-class/deep-nesting
categories, messages, symrefs, and metrics are produced identically since
the underlying computations -- `_py_function_line_count`,
`_py_max_nesting`, `_py_cyclomatic`, `_py_methods` -- are unchanged, just
read through the new normalized-model layer). Added 4 new tests
(`TestPythonAdapter`) exercising the adapter directly against real fixture
files (`test_is_a_language_adapter`, `test_adapt_arch_python_fixture_shape`,
`test_adapt_long_func_fixture_structural_events`,
`test_adapt_deep_nest_fixture_nesting_depth`) -- 60/60 pass after.

NOT migrated in this ticket, left on the raw tree-sitter walk unchanged:
`_extract_signatures` (abstraction-opportunity's param/return-type +
body-fingerprint extraction) and `_collect_dispatch_refs`/
`_collect_file_dispatch_refs` (the dispatch-family exclusion corpus).
`NormalizedCall` carries only a callee name + line -- no argument-position/
dict-value/list-element detail `_is_dispatch_family` needs -- and
body-fingerprinting needs the full raw AST for `frob.dup._legacy_py`'s
alpha-renaming, which no `NormalizedFunction` field captures. Migrating
either without a normalized-model schema extension would either lose the
dispatch-family false-suppression protections (T-0360) or the near-
duplicate-body discriminator (T-0370) -- a real regression risk against
the "NO regression" requirement, so I left them on the raw walk and filed
a follow-up ticket (see Filed) to extend the model first.

`_cpp.py` was NOT touched: the ticket's declared `scope` globs
(`src/frob/arch/_python.py`, `src/frob/arch/_normalized.py`,
`tests/unit/test_arch.py`) do not include it, even though the ticket
body's prose asks for a cpp-adapter too -- I followed the scope globs, not
the prose, per the playbook's scope-discipline rule, and note the
discrepancy here rather than silently expanding scope.

Scope was extended twice mid-ticket (`frob ticket scope --add`, both with
reasons recorded in the ticket's audit trail): `uv.lock` (a `git merge main`
mid-ticket, per the playbook's warm-up guidance, brought in main's own
concurrent commits touching it -- final content matches main's tip, the
T-0431 precedent for this exact SCOPE001 shape) and `pyproject.toml`/
`.frob-release.json` (REL001's minor version bump for the new public API:
`PythonAdapter`, `NormalizedFunction.max_nesting_depth`/`cyclomatic`;
bumped 0.81.0 -> 0.82.0 and ran `frob release stamp`).

Filed T-0632 (ex-draft, id lost at land) (mints a real T-#### id at land, off-default-branch
convention) for the normalized-model schema extension `_extract_signatures`/
dispatch detection need before they can migrate too.

Gates: `frob check --ticket T-0610` -- 0 findings mention T-0610 itself.
5 `gate:COV` COV003 errors remain in the full run, all against ticket
T-0577's evidence in `tests/test_ticket_land.py` (stale evidence ids for
tests that no longer exist there) -- unrelated to `frob.arch`/this ticket's
scope; confirmed by diffing my worktree's `tests/test_ticket_land.py`
against current `main`: main advanced past my last `git merge main` and
removed/renamed those tests, so this is drift from main being a moving
target during this session, not a regression I introduced. `ruff check`/
`ruff format` clean under both the PATH `ruff` (0.14.10) and the
project-pinned `uv run ruff` (0.15.16). `ty check src/frob/arch/` clean.
Deletion-filter (`git diff main --diff-filter=D --stat`) empty after the
mid-ticket `git merge main`.

### Changed
```
 .frob-release.json           |   4 +-
 pyproject.toml               |   2 +-
 src/frob/arch/_normalized.py |  15 +-
 src/frob/arch/_python.py     | 475 +++++++++++++++++++++++++++++++++++++++----
 tests/unit/test_arch.py      |  75 +++++++
 tickets.md                   | 172 +++++++++++++++-
 uv.lock                      |   2 +-
 7 files changed, 692 insertions(+), 53 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestPythonAdapter::test_is_a_language_adapter` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPythonAdapter::test_adapt_arch_python_fixture_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPythonAdapter::test_adapt_long_func_fixture_structural_events` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPythonAdapter::test_adapt_deep_nest_fixture_nesting_depth` (pytest node id, verified passing when recorded)
