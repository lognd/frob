## Done report

Fixed the hyphen-vs-import-name split across all seven scaffold types.

Root cause: `render_project`'s Jinja ctx carried one `project.name` used
for both the PyPI distribution name AND every Python/C/Rust import
identifier. Added `project.import_name` (name with `-`/`.`/spaces
collapsed to `_`, via `_to_import_name`) alongside `project.dist_name`
(same value as `project.name`, kept hyphenated for PyPI/console-script
use). Threaded `import_name` through every generated reference that
must be a valid identifier or match the real package directory:

- python-library / python-tool: `src/<name>/` package dir, every
  `from <name>...`/`import <name>` in app/logging/tests, pyproject's
  package-data key and script target module path, frob.toml's
  `[[refs.entrypoint]]` path, docs frob:describes/frob:tests paths.
- pybind11-library: the `_<name>` compiled-extension symbol
  (`PYBIND11_MODULE`, CMake target/install dest), the generated
  `from ._<name> import add` and `import <name>` test.
- pyo3-library: maturin's `module-name`, the python re-export's
  `from <name>._core import add`, `import <name>` test, ty/coverage
  paths in the Makefile and CI workflow.
- cpp-library / cpp-tool: the GTest `TEST(<name>Test, ...)` identifier
  (CMake target/project names keep hyphens -- CMake permits them there).
- web-app: verified clean as-is -- npm's package.json name and all
  imports are relative paths, no identifier ever derives from the
  project name.

The critical fix is the generated test source: the original bug's
`from my-test-tool.app import ...` is a SyntaxError, which aborts
pytest COLLECTION for the whole file (not a failing test) -- fixed by
using `import_name` in every generated test import.

VERIFICATION PER TYPE (all seven):
- python-library, python-tool, cpp-library, cpp-tool, pybind11-library,
  pyo3-library, web-app: `render_project(type, "my-test-tool", ...)`
  then `ast.parse()` every generated `.py` file -- 0 SyntaxErrors, all
  seven render (test_hyphenated_name_produces_importable_source_all_types).
- python-library, python-tool, pybind11-library, pyo3-library: asserted
  the import package directory is the underscored form and the
  hyphenated form does not exist
  (test_hyphenated_name_import_paths_are_underscored).
- python-tool (existing real end-to-end DX fixture, extended): scaffold
  a HYPHENATED name, `uv sync`, `uv run pytest --collect-only -q` (must
  succeed -- this is exactly where the original bug aborted), `uv run
  pytest tests/ -q` (must pass), then run the installed hyphenated
  console-script `--help` and assert exit 0
  (test_hyphenated_name_scaffold_installs_and_console_script_runs, ran
  for real: exit 0).
- MUST-STAY-QUIET: rendered every type with a single-word name via both
  the new code and old-main's code and diffed the two output trees --
  zero differences (byte-identical), plus a targeted unit test
  (test_single_word_name_unaffected_by_import_name_split) asserting the
  generated `__main__.py` import line is untouched.
- Pre-existing `tests/system/test_scaffold_dx.py` python-tool DX test
  (renders "demo", runs real ruff/ty/pytest/frob check) still passes
  unchanged -- confirms no regression to the working case.

Considered updating docs/commands/scaffold.md's Jinja-variable table to
document `project.dist_name`/`project.import_name`, then reverted that
edit: touching that doc pulls SCOPE002 closure into unrelated
`_managed.py`/`_core.py` symbols (measured: 13-97 unrelated warnings
depending on how much of the doc's closure is chased). Instead disclosed
per the T-3914/T-4013/T-4019/T-4132 accepted precedent for this exact
file (T-4132 hit the identical SCOPE002 shape on this same project.py
module days ago):

frob:waive SCOPE002 reason="project.py is scaffold's single manifest/
dispatch module -- ScaffoldError/install_worktree_lease_hook/
list_project_types/render_project carry PRE-EXISTING frob:doc edges to
docs/commands/scaffold.md and install_worktree_lease_hook carries a
PRE-EXISTING frob:tests edge to tests/test_scaffold_worktree_lease_hook.py,
none of which T-3930 touches. Widening scope to include
docs/commands/scaffold.md cascades into src/frob/_cli_parsers/_core.py
and src/frob/scaffold/_managed.py (measured: 13 further unrelated
closure warnings); widening to include
tests/test_scaffold_worktree_lease_hook.py and
tests/system/test_scaffold_dx.py's own pre-existing
`src/frob/scaffold`-covering directive similarly explodes. Same
disclosed-breadth class as T-3914/T-4013/T-4019's own accepted SCOPE002
precedent, and the identical shape T-4132 measured and disclosed on
this exact module days ago."

gate:LARGE (src/frob/_cli_parsers/_ticket/_closeout.py, 922 lines) and
gate:REF (.github issue templates, CODE_OF_CONDUCT.md, CONTRIBUTING.md,
SECURITY.md, invariants/INV-022.md, invariants/INV-050.md) failures are
pre-existing and untouched by this diff -- confirmed via
`git diff --stat main` showing zero lines changed in any of them.
ruff-format's 32 "would reformat" files are all pre-existing repo-wide
drift outside this ticket's scope -- none of the touched scaffold/test
files appear in that list (confirmed by name).

Filed: none (no out-of-scope defects found; T-4132's py.typed finding
was pre-existing knowledge, not rediscovered here).

### Changed
```
 .../scaffold/data/shared/python/docs/index.md.j2   |   2 +-
 src/frob/scaffold/data/shared/python/frob.toml.j2  |   2 +-
 .../data/shared/python/logging/__init__.py.j2      |   2 +-
 .../data/shared/python/logging/config.toml.j2      |   6 +-
 .../scaffold/data/shared/python/pyproject.toml.j2  |   4 +-
 .../shared/python/tests/system/test_build.py.j2    |   8 +-
 .../scaffold/data/types/cpp-library/tests.cpp.j2   |   2 +-
 src/frob/scaffold/data/types/cpp-tool/tests.cpp.j2 |   2 +-
 .../data/types/pybind11-library/CMakeLists.txt.j2  |   6 +-
 .../data/types/pybind11-library/bindings.cpp.j2    |   2 +-
 .../types/pybind11-library/python/__init__.py.j2   |   2 +-
 .../pybind11-library/tests/test_bindings.py.j2     |   6 +-
 .../scaffold/data/types/pyo3-library/Makefile.j2   |   4 +-
 .../data/types/pyo3-library/docs/index.md.j2       |   4 +-
 .../data/types/pyo3-library/github/ci.yml.j2       |   4 +-
 .../data/types/pyo3-library/pyproject.toml.j2      |   2 +-
 .../data/types/pyo3-library/python/__init__.py.j2  |   2 +-
 .../types/pyo3-library/tests/test_bindings.py.j2   |   6 +-
 .../scaffold/data/types/python-tool/__main__.py.j2 |   2 +-
 .../data/types/python-tool/app/__init__.py.j2      |   4 +-
 .../scaffold/data/types/python-tool/app/app.py.j2  |   2 +-
 .../data/types/python-tool/docs/index.md.j2        |  18 +-
 .../scaffold/data/types/python-tool/frob.toml.j2   |   2 +-
 .../python-tool/tests/system/test_build.py.j2      |  18 +-
 .../types/python-tool/tests/unit/test_app.py.j2    |   4 +-
 .../python-tool/tests/unit/test_logging.py.j2      |  12 +-
 .../types/python-tool/tests/unit/test_main.py.j2   |   4 +-
 src/frob/scaffold/project.py                       |  71 +++--
 tests/system/test_scaffold_dx.py                   |  74 +++++
 tests/unit/test_scaffold_project.py                |  66 +++++
 tickets/T-3930/ticket.md                           | 312 +++++++++++++++++++++
 31 files changed, 568 insertions(+), 87 deletions(-)
```

### Evidence
- `tests/unit/test_scaffold_project.py::test_hyphenated_name_produces_importable_source_all_types` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_hyphenated_name_import_paths_are_underscored` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_single_word_name_unaffected_by_import_name_split` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_dx.py::test_hyphenated_name_scaffold_installs_and_console_script_runs` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 9 error(s), 4464 warning(s), 935 waived
- error-findings: LARGE001@src/frob/_cli_parsers/_ticket/_closeout.py, REF001@.github/ISSUE_TEMPLATE/config.yml, REF002@.github/ISSUE_TEMPLATE/bug_report.yml, REF002@.github/ISSUE_TEMPLATE/feature_request.yml, REF002@.github/PULL_REQUEST_TEMPLATE.md, REF002@CODE_OF_CONDUCT.md, REF002@CONTRIBUTING.md, REF002@SECURITY.md, SCOPE002@tickets.md
