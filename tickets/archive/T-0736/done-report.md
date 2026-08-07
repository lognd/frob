## Done report

Implemented managed boilerplate blocks (T-0736), mirroring the deploy
script<->model drift-lock pattern (`frob.deploy._drift`) but for scaffold
boilerplate:

New module `src/frob/scaffold/_managed.py`:
- `ManagedTextBlock`: id + target file + verbatim content. Two instances
  in `MANAGED_TEXT_BLOCKS`: `makefile-core-shim` (T-0732's `core:` target,
  read from this repo's own Makefile as the literal source of truth) and
  `gitignore-standard` (the cross-language `.gitignore` entries this
  project's own global CLAUDE.md mandates). Each is installed inside a
  repo file between `# frob:managed-block BEGIN <id> ... END <id>`
  markers -- present-and-matching is untouched, present-and-different is
  replaced in place (region only), absent is appended.
- `MANAGED_HOOK_NAMES` = the two T-0431/T-0577 worktree-lease guard hooks
  (`pre-commit`, `pre-merge-commit`); `apply_managed_blocks` reuses
  `install_worktree_lease_hook` for these rather than re-deriving hook
  content, so the hook body still has exactly one definition.
- Digest mechanism: sha256 of canonical content, always computed fresh
  from the CURRENT constants (no separate stamp file) -- same
  "regenerate, compare byte-identical" posture DEPLOY001 uses. A present
  block's digest vs the fresh one is the staleness signal.
- `scaffold_conformance_status(root)`: opt-in on `root/frob.toml`
  existing (mirrors DEPLOY001's opt-in-on-`deploy/`-existing posture) --
  a bare directory with no frob adoption reports empty, not "everything
  missing". Reports one `ManagedBlockStatus` per text block and per hook
  (present/stale/digests). A present hook that is NOT recognizably
  frob's own (`_OURS_MARKER` absent) is reported present-not-stale, never
  claimed by `apply`.
- `apply_managed_blocks(root)`: idempotent create/update-in-place/no-op
  per text block, install/refresh both hooks via
  `install_worktree_lease_hook(force=True)` UNLESS any hook slot is
  occupied by a foreign (non-frob) file, in which case it reports that
  and leaves BOTH hooks untouched (all-or-nothing, to avoid partially
  clobbering a repo's own hook setup). Returns one description line per
  block/hook for CLI output and evidence.

CLI: `frob scaffold apply` (new subcommand, `src/frob/__main__.py`,
`src/frob/app/scaffold_runner.py`) -- calls `apply_managed_blocks(Path("."))`
and logs each change line.

Doctor (`src/frob/doctor.py`): `DoctorReport.scaffold_blocks` (T-0736)
folds `scaffold_conformance_status` in the same DERIVED_ARTIFACTS shape
(T-0570 precedent) -- missing/stale blocks in a `frob.toml`-bearing repo
flip `healthy` to False and name `frob scaffold apply` as the remedy in
`remediation`, joined alongside the existing natives/derived-state hints.
A repo with no `frob.toml` (every existing doctor test's bare `tmp_path`)
is unaffected -- confirmed by re-running the full existing
`tests/system/test_cli_doctor.py` suite (all pre-existing tests still
pass, 13/13).

Docs: `docs/commands/scaffold.md#managed-blocks-t-0736` (full block
inventory, hook-refresh/foreign-hook semantics, doctor cross-ref) and
`docs/guides/install.md#scaffold-managed-block-conformance-t-0736`
(doctor-side view, `--json` shape, opt-in rule). Both anchors verified to
resolve (`frob check`'s DOC002 clean).

Bootstrapped THIS repo as the first consumer (`frob scaffold apply`, run
for real, not simulated):
- Appended the `gitignore-standard` managed block to `.gitignore` (new
  entries beyond what was already there: `cmake-build-*/`, `CMakeFiles/`,
  `CMakeCache.txt`, `*.o`, `*.a`, `*.so`, `*.dylib`, `target/`).
- Appended the `makefile-core-shim` managed block to `Makefile`, and
  removed the old hand-written `core:` target it now supersedes (left a
  pointer comment in its old location) -- confirmed `make core` still
  builds both natives cleanly after the edit.
- Installed BOTH `pre-commit` and `pre-merge-commit` hooks. These write
  to the git COMMON dir's hooks/ (`git rev-parse --git-path hooks`
  resolves to `/mnt/c/Users/logan/Projects/Personal/frob/.git/hooks` from
  this worktree -- hooks are shared across all worktrees of a clone by
  git design, this is not worktree-local and is the intended effect:
  every worktree now gets the T-0431/T-0577 guards). Confirmed via `ls`
  before/after that neither hook file existed anywhere prior to this run
  -- T-0574's finding that these were "bootstrapped nowhere" is now
  fixed for this repo. These hook-directory writes are untracked by git
  (outside any worktree's tracked tree) so they do not show up in
  `git status`/the diff for this ticket; noted here since the ticket
  asked for it explicitly.
- `frob doctor` before this bootstrap: `scaffold conformance: 4 block(s),
  4 missing` (native check aside). After: `scaffold conformance: 4
  block(s), 0 missing, 0 stale`, `healthy=True`.

Apply idempotency proof: ran `frob scaffold apply` twice in a row on a
fresh test repo (`tests/system/test_cli_scaffold_apply.py`) -- first run
creates every block/hook, second run reports every text block "already
current" and refreshes the (already-correct) hooks as a no-op content
change. Also covered directly at the unit level
(`tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::
test_idempotent_second_run_is_noop`) and drift-then-repair
(`test_creates_missing_and_updates_stale`: hand-corrupt the installed
`.gitignore` region, confirm `stale=True`, re-apply, confirm `stale=False`).

Foreign-hook safety: `test_refuses_to_clobber_foreign_hook` plants a
non-frob `pre-commit` before calling `apply` and asserts its content is
byte-identical afterward, with a "NOT frob's own" line in the report
instead of a silent overwrite.

README: the existing `frob scaffold` row in the Setup command table
already covers `apply` as a subcommand of `scaffold` (no separate
top-level row needed -- DOC005 only tracks top-level subcommands, and it
was already clean, 0 errors, both before and after this change). No
prose "N commands" count exists in README to bump; noted rather than
invented one that isn't there.

Known limitation / scope cut: T-0735's planned `frob-natives-build`
subcommand does not exist yet (confirmed: no such module/symbol in this
tree), so `makefile-core-shim`'s content is T-0732's `core:` recipe
verbatim rather than a call into that subcommand -- documented inline in
`_managed.py` and in `docs/commands/scaffold.md` as a named follow-up for
T-0735 to update in the ONE place this lives, once it lands.

Scope was extended mid-ticket via `frob ticket scope --add` (CLI-recorded,
`scope_changes` audit trail) to cover `src/frob/app/scaffold_runner.py`,
`src/frob/__main__.py`, the two new test files, `tests/system/
test_cli_doctor.py`, `Makefile`, and `.gitignore` -- the mandate's CLI
subcommand + repo-bootstrap deliverables are undoable without touching
these, and the original scope globs (`src/frob/scaffold/**`,
`src/frob/doctor.py`, `docs/**`) did not cover them.

Per-sibling adoption tickets: explicitly NOT filed from this worktree
(TICK006) -- the coordinator files those at land via the fleet route, per
this ticket's own mandate part (5). Stating plainly: zero tickets filed
by this agent.

Gates: `frob check --ticket T-0736` clean except `gate:REL` (REL001,
public API changed since 0.91.0) -- left unresolved per this repo's
coordinator-landing convention (version bump happens at land against the
merged result, not per-ticket in a worktree; agent-playbook section 2/
CLAUDE.md). No waivers added.

Tests: `uv run pytest tests/unit/test_scaffold_managed.py
tests/system/test_cli_scaffold_apply.py tests/system/test_cli_doctor.py
tests/test_scaffold_worktree_lease_hook.py tests/unit/test_scaffold_project.py
-q -p no:cacheprovider` -> 35 passed (5 new unit + 1 new CLI + 3 new doctor
+ 13 pre-existing doctor + 8 pre-existing hook + 5 pre-existing scaffold-
project). `ruff check`/`ruff format`/`ty check` all clean on every touched
file. `git diff main --diff-filter=D --stat` empty (no unintended
deletions).



Round-2 correction (land-gate catch): the makefile-core-shim managed block initially omitted T-0732 shared-cache mechanism (CARGO_TARGET_DIR variable + env prefix on both maturin lines); fixed in _managed.py commit 074b35e8, re-applied via frob scaffold apply (updated stale block), verified by CARGO_TARGET_DIR appearing in the executed maturin command lines.

### Changed
```
 .gitignore                              |  33 +++
 Makefile                                |  34 ++-
 docs/commands/scaffold.md               |  57 +++++
 docs/guides/install.md                  |  34 +++
 src/frob/__main__.py                    |   8 +-
 src/frob/app/scaffold_runner.py         |  12 +
 src/frob/doctor.py                      |  42 +++-
 src/frob/scaffold/__init__.py           |  13 +-
 src/frob/scaffold/_managed.py           | 427 ++++++++++++++++++++++++++++++++
 tests/system/test_cli_doctor.py         |  50 ++++
 tests/system/test_cli_scaffold_apply.py |  51 ++++
 tests/unit/test_scaffold_managed.py     | 132 ++++++++++
 12 files changed, 873 insertions(+), 20 deletions(-)
```

### Evidence
(no evidence recorded)
