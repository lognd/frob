# frob scaffold

`frob ops scaffold` (T-1569) also reaches this same code, but `ops` itself
is DEPRECATED (T-4690, sunset 2026-12-01) -- use `frob scaffold` directly.

Scaffold new projects from registered templates. Every type targets
ABSOLUTELY MINIMAL boilerplate: nothing in the rendered template itself
needs hand-fixing to pass its own lint/typecheck/test rules (the web-app
type needs `npm` available; verify by inspection if it isn't).

T-3277: a bare `git init && make check` is NOT the full first-run
sequence, and never has been -- `make check` itself writes
`frob-coverage.lock.json` (via `frob check --stamp-coverage`) and then
immediately re-checks the same tree in one Makefile target, with no
chance to commit in between. `PRE001`/`SCOPE001` correctly flag that as
an uncommitted, unticketed diff (the same discipline this repo holds
itself to) -- so the very first `make check` on a freshly-committed
scaffold always fails on exactly those two rules, by design, not as a
scaffold or gate defect. The real "go green with no manual fixups"
sequence commits the lockfiles `frob check --stamp-coverage` writes
before re-running `frob check`:

<!-- frob:describes src/frob/scaffold/project.py::render_project -->
```bash
frob scaffold new <type> demo && cd demo
git init -q -b main
git add -A && git commit -q -m init

uv sync
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/
uv run ty check src/
uv run pytest tests/ --cov=src --cov-report=xml

frob check --stamp-coverage
git add -A && git commit -q -m "coverage baseline"
frob check
```

Every step here is scripted (no judgment call, no reading an error and
deciding a fix) -- "no manual fixups" means no hand-edits to the
generated template, not zero commands. `tests/system/test_scaffold_dx.py`
is the exact sequence this promise is verified against; if it drifts from
this doc, the doc is wrong, not the test.

## Usage

<!-- frob:describes src/frob/_cli_parsers/_core.py::_add_scaffold_parser -->
```bash
frob scaffold list                  # list available project types
frob scaffold new python-tool demo  # scaffold into ./demo/
frob scaffold new python-tool demo --output /path/to/parent/  # -> /path/to/parent/demo/
frob scaffold new pyo3-library demo --force  # overwrite existing files
```

<!-- frob:describes src/frob/app/scaffold_runner.py::_run_unity_project -->
`frob scaffold unity-project <dir> [--force]` (T-4578): wires T-4503's
`render_unity_project` -- see Project types below for what it writes and
Public API for the underlying function -- as its own CLI leaf rather than
overloading `new`'s type+name+output contract, since `render_unity_project`
takes only a root directory (no separate name):

<!-- frob:waive DOC004 reason="the unity-project subcommand is added by this same land (src/frob/_cli_parsers/_core.py); the pre-land DOC004 sweep resolves console commands against the running parser, not the staged tree" -->
```bash
frob scaffold unity-project /path/to/MyUnityProject          # frob.toml + design/*.strata
frob scaffold unity-project /path/to/MyUnityProject --force  # overwrite existing files
```

<!-- frob:describes src/frob/app/scaffold_runner.py::_run_pool -->
`frob scaffold pool` (T-0877): a warm pool of pre-built worktrees, backed
by `frob.scaffold._pool` (`warm_pool`/`lease_worktree`/`pool_status`, see
`docs/guides/worktree-pool.md` for the full manifest-file API). This is
the same three operations the Makefile's `pool-warm`/`pool-lease`/
`pool-status` inline-python shims used to provide, now wired as real CLI
subcommands:

<!-- frob:describes src/frob/app/scaffold_runner.py::_run_pool -->
```bash
frob scaffold pool warm [N]   # fill the pool to N ready slots (default N=4)
frob scaffold pool lease      # lease one ready slot, print its path, refill in background
frob scaffold pool status     # print the current manifest
```

## Project types

| Type | Stack | Contents |
|------|-------|---------|
| `python-tool` | uv + setuptools | `pyproject.toml` (typani+pydantic, dev group), `src/<name>/` with the App/AppConfig/`__main__` pattern, house logging setup, `frob.toml` (strict gates), `invariants/`, `.env.example`, `Makefile` (bootstrap/build only -- `install/clean/upload`; `frob format`/`frob check`/`frob test`/`frob coverage` are the interface, see T-3400), CI + release workflows |
| `python-library` | uv + setuptools | Same base as `python-tool` minus the CLI entry point/App layer |
| `pyo3-library` | uv + maturin + cargo workspace | `crates/` (Rust, pyo3 extension) + `python/<name>/` layout (lithos-style), `rust-toolchain.toml`, `frob.toml` with both `python` and `rust` test runners, Makefile wiring `cargo fmt`/`clippy` into `check`, CI + release workflows |
| `web-app` | Vite + React + TypeScript + Vitest | `src/`, `tests/unit/`, ESLint 9 flat config, Prettier, `frob.toml` (`typescript` test runner), CI |
| `cpp-library` / `cpp-tool` | CMake + ctest | `src/`, `include/`, `tests/`, `frob.toml` (`cpp` test runner via ctest), CI + release + branch-protection workflows |
| `pybind11-library` | CMake + scikit-build + pytest | `src/`, bindings, `tests/`, `frob.toml` (`python` test runner), CI |

`unity-project` (T-4503) is not in the table above because it does not fit
its shape: every type above scaffolds a FRESH `<output_dir>/<name>/`
tree via `render_project`/`frob scaffold new <type> <name>`, while
`unity-project` scaffolds ONTO an EXISTING Unity project directory (one
that already has `Assets/`/`Packages/`) via its own entry point,
`render_unity_project(root, *, force=False)` -- see Public API below. It
writes a starter `frob.toml` with Unity's `Library/Temp/Logs/obj/*.meta`
excludes pre-populated (T-4515's `UNITY_EXCLUDE_GLOBS`) and a
`dotnet test` `[[test.runner]]` entry, plus one `design/<node_id>.strata`
component-boundary fragment per detected `.asmdef` (T-4512's asmdef
reader, reused unchanged -- one node per asmdef, plus the always-present
default-assembly node covering any `.cs` file no asmdef claims). A
directory with neither `Assets/` nor `Packages/` is refused with
`ScaffoldError.NotAUnityProject`, never a bogus config; a second run
without `force=True` is refused with `OutputExists` before anything is
written.

No type ships a `tickets.md` or `tickets/` seed (T-3272): the scaffold
writes no ledger content at all, so every fresh project starts in ledger
v2 mode (per-ticket files) the moment `frob ticket new` is first run there
-- a repo with no ledger of either shape already defaults to v2
(`frob.tickets._store._store_mode`, T-1553); shipping an empty `tickets.md`
was what pinned new repos to v1 instead. A v1 repo (an existing `tickets.md`
already on disk) is unaffected and keeps working exactly as before; migrate
it with `frob ticket migrate --to v2`.

Run `frob scaffold list` to see the current registry.

## CI/CD design (every type)

`.github/workflows/ci.yml`: push+PR trigger, `concurrency.cancel-in-progress`,
one `check` job per stack running lint -> typecheck -> test(+coverage) ->
`frob check`. The `frob check` step is guarded: it installs frob via
`uv tool install frob`, then only runs it if `frob graph --help` actually
works, emitting a `::notice::` and skipping otherwise. frob is published to
PyPI (0.279.0 as of this writing, installed fleet-wide via `uv tool
install frob`) and the guard now mostly protects against a target repo's
own transient install/network hiccup rather than frob's own availability;
a naive `frob check` step would otherwise red-herring CI with an unrelated
failure in that case.

`python-tool` and `pyo3-library` additionally get <!-- frob:waive DOC006 reason="a scaffold-generated file this command writes into the TARGET repo, not a path in this repo" -->`.github/workflows/release.yml`:
triggered on `v*` tags, builds via `uv build` / `maturin build --release`,
and publishes to PyPI through `pypa/gh-action-pypi-publish` using OIDC
trusted publishing (no stored API token). The workflow's header comment
documents the one-time PyPI "Publishing" trusted-publisher setup.

## Template layout

Templates live under `src/frob/scaffold/data/`:

```
scaffold/data/
  shared/
    python/          -- shared across all Python types (Makefile, gitignore,
                         pyproject.toml, logging/, frob.toml, tests/, github/)
    cpp/             -- shared across all C++ types (Makefile, gitignore,
                         frob.toml, docs/, github/)
    pyo3/            -- gitignore shared by pyo3-library
    pybind11/        -- gitignore shared by pybind11-library
  types/
    python-tool/
      app/, docs/, tests/, github/, frob.toml.j2, ...
    python-library/
      __init__.py.j2
    pyo3-library/
      crates/, python/, tests/, github/, Cargo.toml.j2, frob.toml.j2, ...
    web-app/
      src/, tests/, github/, package.json.j2, ...
    cpp-library/ cpp-tool/ pybind11-library/
      ...
```

Jinja2 variables available in all templates:

| Variable | Value |
|---------|-------|
| `project.name` | Project name as passed on the CLI |
| `project.type` | The scaffold type being rendered (e.g. `"python-tool"`) -- used by `shared/python/pyproject.toml.j2` to gate the CLI entry point to `python-tool` only |

## Public API

<!-- frob:describes src/frob/scaffold/project.py::ScaffoldError -->
<!-- frob:describes src/frob/scaffold/project.py::list_project_types -->
<!-- frob:describes src/frob/scaffold/project.py::render_project -->
<!-- frob:describes src/frob/scaffold/_unity_project.py::render_unity_project -->
<!-- frob:describes src/frob/scaffold/project.py::install_worktree_lease_hook -->

```python
# frob/scaffold/project.py
class ScaffoldError(ErrorSet)
    # Failure values: unknown type, missing template, existing output
    # files without --force, a Jinja2 render error, (T-0431) a hook
    # install failure (not a git repo, or the write itself failed), or
    # (T-4503) a unity-project scaffold run against a non-Unity directory.

def list_project_types() -> list[str]
    # The registered scaffold type names, read directly off _MANIFESTS
    # (unity-project is deliberately not one of these -- see above).

def render_project(project_type, name, output_dir, *, force=False) -> Result[list[Path], ScaffoldError]
    # Render one registered type's templates into output_dir; the single
    # entry point behind `frob scaffold new`.

def render_unity_project(root, *, force=False) -> Result[list[Path], ScaffoldError]
    # T-4503: scaffold the unity-project type onto an EXISTING Unity
    # project directory at root -- frob.toml plus one design/*.strata
    # per detected .asmdef (T-4512's discover_asmdefs/build_component_
    # nodes, reused unchanged). Err(NotAUnityProject) for a directory
    # with neither Assets/ nor Packages/; Err(OutputExists) when
    # frob.toml or any computed design/*.strata path already exists and
    # force is not set, checked before anything is written.

def install_worktree_lease_hook(root, *, force=False) -> Result[tuple[Path, ...], ScaffoldError]
    # T-0431: installs pre-commit + pre-merge-commit git hooks into root's
    # real hooks directory (git rev-parse --git-path hooks) that abort
    # loudly whenever FROB_AGENT is set non-empty -- catches a stray raw
    # `git commit`/`git merge` an agent shell ran directly against the
    # wrong checkout, independent of frob.tickets' own worktree-lease
    # guard (docs/modules/tickets-data-storage.md#worktree-lease-guard-t-0431). Refuses
    # to overwrite an existing hook file without force=True.
    # T-2071: both hooks ALSO carry a second, FACT-based guard that does
    # NOT depend on FROB_AGENT (measured UNSET in every dispatched Agent
    # tool shell, making the guard above inert for its own target
    # population). It refuses a commit made in the PRIMARY checkout while
    # other worktrees exist (a fleet is dispatched) whose staged files
    # are not limited to tickets.md/tickets/** -- almost always a
    # dispatched agent shell that wandered out of its leased worktree --
    # unless FROB_LAND_INTERNAL=1 covers it (frob ticket land's own
    # internal commits).
```

## Managed blocks (T-0736)

Boilerplate that used to get fixed one repo at a time (the Makefile
`core:` shim, standard `.gitignore` entries, the T-0431/T-0577
worktree-lease git hooks) is now defined ONCE, in
`src/frob/scaffold/_managed.py`, and drift-checked/installed everywhere
else -- the same "regenerate fresh, compare byte-identical" posture the
deploy script<->model drift-lock (`docs/strata/host.md#the-deploy-generator`)
already uses, applied to scaffold boilerplate instead of
generated deploy scripts.

<!-- frob:describes src/frob/scaffold/_managed.py::apply_managed_blocks -->
<!-- frob:describes src/frob/scaffold/_managed.py::scaffold_conformance_status -->
```bash
frob scaffold apply   # idempotently install/update every managed block
```

Two kinds of managed block:

- **Text blocks** (`MANAGED_TEXT_BLOCKS`) live inside an existing file
  (`Makefile`, `.gitignore`) between a
  `# frob:managed-block BEGIN <id> ... # frob:managed-block END <id>`
  marker pair. `frob scaffold apply` appends the block if the markers are
  absent, replaces the region in place if present-but-different (drifted
  from the current canonical content), and leaves it alone if already
  current. Content OUTSIDE the markers -- the rest of a repo's own
  Makefile/`.gitignore` -- is never touched.
  - `makefile-core-shim`: T-0732's `core:` target (native-extension
    build), read directly from this repo's own Makefile as the canonical
    definition, not duplicated by hand elsewhere.
  - `gitignore-standard`: the cross-language `.gitignore` entries every
    frob-managed repo should carry (build artifacts, Python caches, frob
    local state, secrets).
  - `makefile-wrapper-targets` / `makebat-wrapper-targets` (T-4760): the
    derived-wrapper targets/branches in `Makefile`/`make.bat`. Content is
    computed fresh each `apply`, not a fixed constant like the two blocks
    above: one `<name>:` target (Makefile) or `if "%1"=="<name>"` branch
    (make.bat) per entry this project's `frob.toml` `[commands]` table
    declares, unioned with the four always-invocable native-default names
    (`test`/`lint`/`format`/`check`, docs/commands/run.md#native-defaults)
    -- each recipe is a single `frob run <name>` call, never an inlined
    sequence. `make.bat` is new (T-4760): no scaffold type shipped a
    Windows wrapper before this; `apply` creates it fresh the first time
    it runs, the same "absent -> append/create" path text blocks already
    take. The core-shim block above is skipped (reported, not applied)
    on a Makefile that defines no `STAMP` variable -- applying it there
    left `core: $(STAMP)` expanding to an unconditional prerequisite
    (measured on a rendered cpp-library: no venv, nothing to gate a
    native build behind).

### The wrapper-drift gate (WRAP001/WRAP002/WRAP003, T-4760)

<!-- frob:describes src/frob/gates/_wrapper_drift.py::wrapper_drift_gate -->
`wrapper_drift_gate` catches a Makefile/make.bat that has drifted from
what `frob scaffold apply` would (re)generate for its `makefile-wrapper-
targets`/`makebat-wrapper-targets` managed blocks:

- **WRAP001**: a wrapper target/branch expands more than one command
  inline (a `&&`/`;`/`&`-joined recipe, or anything that is not a bare
  `frob run <name>` call) -- the sequence has exactly one legitimate
  home, the `[commands]` table itself
  (docs/commands/run.md#relationship-to-derived-wrappers).
- **WRAP002**: a wrapper target/branch names an entry that is neither
  declared in `frob.toml`'s `[commands]` table nor a native default --
  typically an entry `[commands]` used to declare and no longer does.
- **WRAP003**: the Makefile and make.bat managed-block name sets are not
  equal.

The gate is a no-op (returns no violations) on a project that has never
run `frob scaffold apply` at all -- it checks an existing generated
artefact for staleness, it does not require one to exist. Wiring
`wrapper_drift_gate` into the `frob check` `_ALL_GATES` pipeline itself
(`src/frob/gates/__init__.py`) is tracked separately (T-4910): that file
was leased by another in-progress ticket (T-3962) at the time T-4760
landed.
- **Hook blocks** (`MANAGED_HOOK_NAMES`) are the two T-0431/T-0577
  worktree-lease git hooks (`pre-commit`, `pre-merge-commit`) --
  `apply_managed_blocks` reuses `install_worktree_lease_hook` rather than
  re-deriving hook content, so there is still exactly one place the hook
  body is defined. A hook file that already exists and is recognizably
  frob's own (carries its install-comment marker) is refreshed; a hook
  that exists and is NOT frob's own is reported and left completely
  untouched -- `apply` never overwrites a repo's genuine custom hook.
- **The T-0574 stash-guard hook** (`STASH_GUARD_HOOK_NAMES`, currently
  just `reference-transaction`) refuses `git stash` while more than one
  `git worktree list` entry exists for the clone
  (docs/guides/agent-playbook.md#1b-never-git-stash-in-a-worktree-it-is-repo-global-not-worktree-local).
  It exists as its own hook -- not folded into the T-0431 `pre-commit`
  hooks above -- because `git stash` never invokes `pre-commit` (it
  builds its commits via `commit-tree` plumbing) and a repo-local
  `alias.stash` override is silently ignored by git (aliases cannot
  shadow a built-in subcommand name); `reference-transaction` is the one
  native hook that actually fires for a `refs/stash` update and can
  abort it. Same "ours vs foreign" posture as the other hooks: a
  pre-existing `reference-transaction` hook that is not frob's own is
  reported and left untouched. Git older than 2.28 has no
  `reference-transaction` hook at all -- the guard is silently inert
  there (fail-open, not an install error).

`frob doctor` folds the same conformance check into its report
(`docs/guides/install.md#scaffold-managed-block-conformance-t-0736`):
opt-in on `frob.toml` existing (a bare directory with no frob adoption at
all has nothing to be behind on), a `frob.toml`-bearing repo that is
missing or stale on any managed block is reported unhealthy with
`frob scaffold apply` named as the remedy.

`frob natives build` (T-0735) is shipped (`_cli_parsers/_misc.py`) and
`makefile-core-shim`'s content invokes it directly (`uv run frob natives
build`, `src/frob/scaffold/_managed.py::_MAKEFILE_CORE_SHIM`) rather than
inlining the old per-repo cargo recipe. Per-sibling
adoption tickets (rolling `frob scaffold apply` out to the other repos in
the estate) are filed at land time via the fleet route, not from this
ticket's worktree.

## Adding a project type

1. Create `src/frob/scaffold/data/types/<type-name>/` with `.j2` templates.
2. Add a `_MANIFESTS["<type-name>"]` entry in `src/frob/scaffold/project.py`
   (`list_project_types()` reads the registry directly -- no separate list
   to keep in sync).
3. Include the new path glob in `[tool.setuptools.package-data]` in
   `pyproject.toml` if the type introduces a new file extension.
4. Verify the DX bar: render the type into a temp dir, `git init`, and run
   its `make check` (or stack-equivalent) end to end -- see
   `tests/system/test_scaffold_dx.py` for the pattern.
