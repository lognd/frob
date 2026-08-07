## Done report

Added `stale_install_warning(repo_root)` to `src/frob/app/config.py`: reads
`repo_root/pyproject.toml`'s own declared `[project].version` (guarded by
`name == "frob"`), compares it against `importlib.metadata.version("frob")`
(the RUNNING installed distribution), and against `importlib.util.find_spec
("frob").origin` compared to `repo_root/src/frob/__init__.py` -- if the
running package's own file is NOT this checkout's own `src/frob/__init__.py`
(i.e. it's a globally `uv tool install`ed binary, not an editable/`uv run`
install) AND the installed version differs from the checkout's declared
version, returns a loud one-line warning string naming both versions and
telling the user to use `uv run frob` / `make`. Returns `None` (no warning)
for: no pyproject.toml, not this project, an editable/local install, or
matching versions.

Wired into `src/frob/__main__.py`'s `main()`: called right after building
the parser/args and before `AppConfig.from_external`/`App(cfg)()`, printed
to stderr. Since `main()` is the single entry point every subcommand
(`check`, `doctor`, everything) dispatches through, this covers `frob
doctor`/`frob check` per the ticket's acceptance without needing a
per-subcommand copy.

Tests (tests/unit/test_config.py, monkeypatching `importlib.util.find_spec`
and `importlib.metadata.version` so no real installed package location is
needed):
- test_stale_install_warning_flags_version_mismatch: installed 0.9.0 vs
  declared 0.27.0, from an outside package location -> warning naming both.
- test_stale_install_warning_none_for_editable_checkout: running package IS
  the checkout's own src/frob/__init__.py -> None even with differing
  metadata version.
- test_stale_install_warning_none_when_versions_match: outside package
  location but installed version == declared version -> None.

REL001: `stale_install_warning` is a new public symbol; bumped
pyproject.toml 0.53.0 -> 0.54.0 and ran `frob release stamp`.

Scope: added `tests/unit/test_config.py` (new tests), `pyproject.toml` /
`.frob-release.json` / `uv.lock` (REL001 bump+stamp), and
`src/frob/tickets/__init__.py` / `src/frob/tickets/_models.py` /
`tests/test_tickets_scope_mutation.py` -- this last group is NOT new work
for T-0358; it is T-0485's already-landed, already-closed code (commit
35f2678) whose commit SUBJECT line omitted "T-0485" (only the body
mentioned it), so `scope_gate`'s cross-ticket exemption (T-0108,
`_commit_exempts_file`, which matches only the commit `%s` subject) could
not attribute those hunks away from this ticket's diff on the same
worktree branch. Rather than amend a prior commit, declared the overlap
honestly in scope with a reason recording the exact mechanism. Worth a
follow-up systemic note: commit subjects for ticket work in a
multi-ticket-per-worktree session should always carry the ticket id
literally in the subject line, not just the body, or this gate friction
recurs for every subsequent ticket in the same worktree.

### Changed
```
 .frob-release.json                   |  3 +-
 pyproject.toml                       |  2 +-
 src/frob/__main__.py                 |  8 +++-
 src/frob/app/config.py               | 67 +++++++++++++++++++++++++++++++
 src/frob/tickets/__init__.py         | 21 ++++++++--
 src/frob/tickets/_models.py          | 17 ++++++++
 tests/test_tickets_scope_mutation.py | 58 ++++++++++++++++++++++++++-
 tests/unit/test_config.py            | 76 +++++++++++++++++++++++++++++++++++
 tickets.md                           | 78 ++++++++++++++++++++++++++++++++++--
 uv.lock                              |  2 +-
 10 files changed, 321 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_install_warning_none_for_editable_checkout` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_install_warning_none_when_versions_match` (pytest node id, verified passing when recorded)
