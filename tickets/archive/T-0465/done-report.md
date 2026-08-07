## Done report

New EXCL001 gate rule (ERROR severity, unwaivable -- joins
_UNWAIVABLE_RULES alongside TEST008/SEC003/TICK001/TICK002): flags a
`.git/info/exclude` entry that shadows git-tracked source. New module
`src/frob/gates/_exclude_hazard.py` (`exclude_hazard_gate`): resolves
the shared common dir (`git rev-parse --git-common-dir`, since
`.git/info/exclude` is shared across every worktree of a clone, not
per-worktree), parses each non-comment, non-negated gitignore-format
line into its directory/file prefix, and flags any prefix that names an
exact tracked file or a directory under which `git ls-files` finds at
least one tracked file. An entry matching nothing tracked (build
artifacts, caches, genuinely never-tracked paths) is silent -- that is
exactly what the file is meant for.

Deliberately unwaivable: the violation's "file" is `.git/info/exclude`
itself, not a source file a `frob:waive` comment could attach to, and
the remedy is always the same (remove the entry, or use a genuinely
untracked path).

Wired into the `frob check` invariant/gate pipeline as a new default-on
stage "excludehazard" (repo_root-scoped, same reason secrets/refs are --
the hazard is repo-wide by construction, not scoped-root). Added
"excludehazard" to both `_ALL_GATES` and `_CANONICAL_GATE_ORDER` (a
dedicated test, TestGateOrderSetEquality, catches drift between the
two -- caught this the first time I forgot the second list).

Added docs/modules/gates.md's rule-catalog row plus an "EXCL001
(T-0465)" narrative section (placed next to WALK001, same hazard-guard
family), and a new hard rule in docs/guides/agent-playbook.md (section
1c, "NEVER edit .git/info/exclude") describing the same T-0448 incident
this ticket names, mirroring section 1b's git-stash hazard writeup and
pointing back at EXCL001 as the static check.

Confirmed non-vacuous by hand: a synthetic repo with `.git/info/exclude`
containing `src/pkg/` (a directory with a tracked file under it) fires
exactly one EXCL001; the same repo with `*.pyc`/`build/` (nothing
tracked matches) is silent. Both directions covered by
TestExcludeHazardGate in tests/test_gates.py.

REL001: new public API (frob.gates.exclude_hazard_gate) bumped
pyproject.toml 0.45.0 -> 0.46.0, CHANGELOG.md entry added, uv lock
refreshed, `frob release stamp` run. Scope extended (frob ticket scope
--add) to cover docs/modules/gates.md (not covered by the original
docs/guides/agent-playbook.md-only scope) plus
pyproject.toml/CHANGELOG.md/uv.lock/.frob-release.json.

Confirmed via `uv run frob check`: 0 new errors (1 pre-existing
unrelated error, docs/commands/sys.md DOC003, present before this
ticket started and outside its scope). ruff check/format and ty clean
under both `uv run` and bare PATH `ruff`/`ruff format --check`.
tests/test_gates.py full suite passes.

Ledger note: a `frob ticket evidence` write mid-session hit a race with
main advancing far ahead of this worktree's stale code tree (many
sibling tickets landed since this worktree's last merge at 5f2d29d);
the rewrite briefly diverged tickets.md by hundreds of lines against
main. Restored by hand: checked out main's current tickets.md verbatim
and spliced only T-0335/T-0452/T-0462/T-0465's own blocks back in from
this worktree's copy (a python marker-based splice, not a manual
line-edit), confirmed via `git diff main -- tickets.md` showing zero
ticket-marker adds/removes and only these four tickets' content
changed. A full `frob check` now also surfaces COV003 findings for
OTHER, unrelated tickets (T-0338, T-0357, T-0409, T-0421, ...) whose
evidence names tests that only exist in main's current code tree, not
this worktree's -- pre-existing drift from main having moved past this
worktree's code since the session's original 5f2d29d merge, not
something introduced by this ticket's changes; `--ticket T-0465`
confirms zero errors attributable to T-0465/T-0462/T-0452/T-0335
specifically.

### Changed
```
 .frob-release.json           |   8 +-
 CHANGELOG.md                 |  32 ++++++
 docs/modules/gates.md        |  51 ++++++++++
 pyproject.toml               |   2 +-
 src/frob/gates/__init__.py   | 184 +++++++++++++++++++++++++++++++++-
 src/frob/gates/invariants.py |  80 ++++++++++++++-
 tests/test_gates.py          | 103 +++++++++++++++++++
 tickets.md                   | 229 +++++++++++++++++++++++++++++++++++++++++--
 uv.lock                      |   2 +-
 9 files changed, 677 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestExcludeHazardGate::test_entry_shadowing_tracked_dir_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExcludeHazardGate::test_entry_matching_no_tracked_path_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExcludeHazardGate::test_comment_and_negated_lines_are_ignored` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExcludeHazardGate::test_exact_tracked_file_entry_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExcludeHazardGate::test_empty_exclude_file_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExcludeHazardGate::test_non_git_root_is_silent` (pytest node id, verified passing when recorded)
