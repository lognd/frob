# frob scaffold

Also available as `frob ops scaffold` (T-1569) -- same flags, same code.

Scaffold new projects from registered templates. Every type targets
ABSOLUTELY MINIMAL boilerplate: `frob scaffold new <type> demo && cd demo
&& git init && make check` should go green immediately, with no manual
fixups, for the Python and Rust types (the web-app type needs `npm`
available; verify by inspection if it isn't).

## Usage

<!-- frob:describes src/frob/_cli_parsers/_core.py::_add_scaffold_parser -->
```bash
frob scaffold list                  # list available project types
frob scaffold new python-tool demo  # scaffold into ./demo/
frob scaffold new python-tool demo --output /path/to/parent/
frob scaffold new pyo3-library demo --force  # overwrite existing files
```

## Project types

| Type | Stack | Contents |
|------|-------|---------|
| `python-tool` | uv + setuptools | `pyproject.toml` (typani+pydantic, dev group), `src/<name>/` with the App/AppConfig/`__main__` pattern, house logging setup, `frob.toml` (strict gates), `tickets/`, `invariants/`, `.env.example`, `Makefile` (`install/format/lint/typecheck/test/coverage/check`), CI + release workflows |
| `python-library` | uv + setuptools | Same base as `python-tool` minus the CLI entry point/App layer |
| `pyo3-library` | uv + maturin + cargo workspace | `crates/` (Rust, pyo3 extension) + `python/<name>/` layout (lithos-style), `rust-toolchain.toml`, `frob.toml` with both `python` and `rust` test runners, Makefile wiring `cargo fmt`/`clippy` into `check`, CI + release workflows |
| `web-app` | Vite + React + TypeScript + Vitest | `src/`, `tests/unit/`, ESLint 9 flat config, Prettier, `frob.toml` (`typescript` test runner), CI |
| `cpp-library` / `cpp-tool` | CMake + ctest | `src/`, `include/`, `tests/`, `frob.toml` (`cpp` test runner via ctest), CI + release + branch-protection workflows |
| `pybind11-library` | CMake + scikit-build + pytest | `src/`, bindings, `tests/`, `frob.toml` (`python` test runner), CI |

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
<!-- frob:describes src/frob/scaffold/project.py::install_worktree_lease_hook -->

```python
# frob/scaffold/project.py
class ScaffoldError(ErrorSet)
    # Failure values: unknown type, missing template, existing output
    # files without --force, a Jinja2 render error, or (T-0431) a hook
    # install failure (not a git repo, or the write itself failed).

def list_project_types() -> list[str]
    # The registered scaffold type names, read directly off _MANIFESTS.

def render_project(project_type, name, output_dir, *, force=False) -> Result[list[Path], ScaffoldError]
    # Render one registered type's templates into output_dir; the single
    # entry point behind `frob scaffold new`.

def install_worktree_lease_hook(root, *, force=False) -> Result[tuple[Path, ...], ScaffoldError]
    # T-0431: installs pre-commit + pre-merge-commit git hooks into root's
    # real hooks directory (git rev-parse --git-path hooks) that abort
    # loudly whenever FROB_AGENT is set non-empty -- catches a stray raw
    # `git commit`/`git merge` an agent shell ran directly against the
    # wrong checkout, independent of frob.tickets' own worktree-lease
    # guard (docs/modules/tickets.md#worktree-lease-guard-t-0431). Refuses
    # to overwrite an existing hook file without force=True.
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
