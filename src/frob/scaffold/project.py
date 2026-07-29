from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# comment describing already-implemented internal shell-hook behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"
_DATA_DIR = Path(__file__).parent / "data"
_log = get_logger(__name__)


# frob:doc docs/commands/scaffold.md#public-api
class ScaffoldError(ErrorSet):
    UnknownType = "Requested project type is not registered"
    TemplateNotFound = "Template .j2 file is missing from the data directory"
    OutputExists = (
        "One or more output files already exist (use force=True to overwrite)"
    )
    RenderFailed = "Jinja2 raised an error while rendering a template"
    # T-0431: worktree-lease git hook install failure modes.
    NotAGitRepo = "root is not inside a git work tree"
    HookWriteFailed = "could not write the hook script to the resolved hooks path"


@dataclass(frozen=True)
class _ManifestEntry:
    # Template path inside data/ (relative, may include subdirectories)
    template: str
    # Output path relative to the project root; may contain Jinja2 expressions
    output: str


_MANIFESTS: dict[str, list[_ManifestEntry]] = {
    "python-library": [
        _ManifestEntry("shared/python/README.md.j2", "README.md"),
        _ManifestEntry("shared/python/gitignore.j2", ".gitignore"),
        _ManifestEntry("shared/python/env.example.j2", ".env.example"),
        _ManifestEntry("shared/python/Makefile.j2", "Makefile"),
        _ManifestEntry("shared/python/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry(
            "shared/python/scripts/bump_version.py.j2", "scripts/bump_version.py"
        ),
        _ManifestEntry("shared/python/pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry(
            "types/python-library/__init__.py.j2", "src/{{ project.name }}/__init__.py"
        ),
        _ManifestEntry(
            "shared/python/logging/__init__.py.j2",
            "src/{{ project.name }}/logging/__init__.py",
        ),
        _ManifestEntry(
            "shared/python/logging/config.toml.j2",
            "src/{{ project.name }}/logging/config.toml",
        ),
        _ManifestEntry(
            "shared/python/logging/filter.py.j2",
            "src/{{ project.name }}/logging/filter.py",
        ),
        _ManifestEntry(
            "shared/python/logging/formatter.py.j2",
            "src/{{ project.name }}/logging/formatter.py",
        ),
        _ManifestEntry(
            "shared/python/logging/logger.py.j2",
            "src/{{ project.name }}/logging/logger.py",
        ),
        _ManifestEntry("shared/python/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("shared/python/tests/conftest.py.j2", "tests/conftest.py"),
        _ManifestEntry(
            "shared/python/tests/unit/test_placeholder.py.j2",
            "tests/unit/test_placeholder.py",
        ),
        _ManifestEntry(
            "shared/python/tests/system/test_build.py.j2", "tests/system/test_build.py"
        ),
        _ManifestEntry("shared/python/github/ci.yml.j2", ".github/workflows/ci.yml"),
        _ManifestEntry(
            "shared/python/github/branch-protection.yml.j2",
            ".github/workflows/branch-protection.yml",
        ),
    ],
    "python-tool": [
        _ManifestEntry("shared/python/README.md.j2", "README.md"),
        _ManifestEntry("shared/python/gitignore.j2", ".gitignore"),
        _ManifestEntry("shared/python/env.example.j2", ".env.example"),
        _ManifestEntry("shared/python/Makefile.j2", "Makefile"),
        _ManifestEntry("types/python-tool/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry(
            "shared/python/scripts/bump_version.py.j2", "scripts/bump_version.py"
        ),
        _ManifestEntry("shared/python/pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry(
            "types/python-tool/__init__.py.j2", "src/{{ project.name }}/__init__.py"
        ),
        _ManifestEntry(
            "types/python-tool/__main__.py.j2", "src/{{ project.name }}/__main__.py"
        ),
        _ManifestEntry(
            "types/python-tool/app/__init__.py.j2",
            "src/{{ project.name }}/app/__init__.py",
        ),
        _ManifestEntry(
            "types/python-tool/app/app.py.j2", "src/{{ project.name }}/app/app.py"
        ),
        _ManifestEntry(
            "types/python-tool/app/config.py.j2", "src/{{ project.name }}/app/config.py"
        ),
        _ManifestEntry(
            "shared/python/logging/__init__.py.j2",
            "src/{{ project.name }}/logging/__init__.py",
        ),
        _ManifestEntry(
            "shared/python/logging/config.toml.j2",
            "src/{{ project.name }}/logging/config.toml",
        ),
        _ManifestEntry(
            "shared/python/logging/filter.py.j2",
            "src/{{ project.name }}/logging/filter.py",
        ),
        _ManifestEntry(
            "shared/python/logging/formatter.py.j2",
            "src/{{ project.name }}/logging/formatter.py",
        ),
        _ManifestEntry(
            "shared/python/logging/logger.py.j2",
            "src/{{ project.name }}/logging/logger.py",
        ),
        _ManifestEntry("types/python-tool/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("shared/python/tests/conftest.py.j2", "tests/conftest.py"),
        _ManifestEntry(
            "types/python-tool/tests/unit/test_app.py.j2", "tests/unit/test_app.py"
        ),
        _ManifestEntry(
            "types/python-tool/tests/unit/test_main.py.j2", "tests/unit/test_main.py"
        ),
        _ManifestEntry(
            "types/python-tool/tests/unit/test_logging.py.j2",
            "tests/unit/test_logging.py",
        ),
        _ManifestEntry(
            "types/python-tool/tests/system/test_build.py.j2",
            "tests/system/test_build.py",
        ),
        _ManifestEntry("shared/python/github/ci.yml.j2", ".github/workflows/ci.yml"),
        _ManifestEntry(
            "shared/python/github/branch-protection.yml.j2",
            ".github/workflows/branch-protection.yml",
        ),
        _ManifestEntry(
            "types/python-tool/github/release.yml.j2",
            ".github/workflows/release.yml",
        ),
    ],
    "cpp-library": [
        _ManifestEntry("shared/cpp/README.md.j2", "README.md"),
        _ManifestEntry("shared/cpp/gitignore.j2", ".gitignore"),
        _ManifestEntry("shared/cpp/Makefile.j2", "Makefile"),
        _ManifestEntry("shared/cpp/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("shared/cpp/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/cpp-library/CMakeLists.txt.j2", "CMakeLists.txt"),
        _ManifestEntry(
            "types/cpp-library/cmake/Config.cmake.in.j2",
            "cmake/{{ project.name }}Config.cmake.in",
        ),
        _ManifestEntry("types/cpp-library/src.cpp.j2", "src/{{ project.name }}.cpp"),
        _ManifestEntry(
            "types/cpp-library/include.h.j2", "include/{{ project.name }}.h"
        ),
        _ManifestEntry("shared/cpp/tests/CMakeLists.txt.j2", "tests/CMakeLists.txt"),
        _ManifestEntry(
            "types/cpp-library/tests.cpp.j2", "tests/test_{{ project.name }}.cpp"
        ),
        _ManifestEntry("shared/cpp/github/ci.yml.j2", ".github/workflows/ci.yml"),
        _ManifestEntry(
            "shared/cpp/github/release.yml.j2", ".github/workflows/release.yml"
        ),
        _ManifestEntry(
            "shared/cpp/github/branch-protection.yml.j2",
            ".github/workflows/branch-protection.yml",
        ),
        _ManifestEntry(
            "shared/cpp/cmake/toolchain-linux-arm64.cmake.j2",
            "cmake/toolchain-linux-arm64.cmake",
        ),
    ],
    "cpp-tool": [
        _ManifestEntry("shared/cpp/README.md.j2", "README.md"),
        _ManifestEntry("shared/cpp/gitignore.j2", ".gitignore"),
        _ManifestEntry("shared/cpp/Makefile.j2", "Makefile"),
        _ManifestEntry("shared/cpp/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("shared/cpp/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/cpp-tool/CMakeLists.txt.j2", "CMakeLists.txt"),
        _ManifestEntry("types/cpp-tool/src.cpp.j2", "src/{{ project.name }}.cpp"),
        _ManifestEntry("types/cpp-tool/main.cpp.j2", "src/main.cpp"),
        _ManifestEntry("types/cpp-tool/include.h.j2", "include/{{ project.name }}.h"),
        _ManifestEntry("shared/cpp/tests/CMakeLists.txt.j2", "tests/CMakeLists.txt"),
        _ManifestEntry(
            "types/cpp-tool/tests.cpp.j2", "tests/test_{{ project.name }}.cpp"
        ),
        _ManifestEntry("shared/cpp/github/ci.yml.j2", ".github/workflows/ci.yml"),
        _ManifestEntry(
            "shared/cpp/github/release.yml.j2", ".github/workflows/release.yml"
        ),
        _ManifestEntry(
            "shared/cpp/github/branch-protection.yml.j2",
            ".github/workflows/branch-protection.yml",
        ),
        _ManifestEntry(
            "shared/cpp/cmake/toolchain-linux-arm64.cmake.j2",
            "cmake/toolchain-linux-arm64.cmake",
        ),
    ],
    "pybind11-library": [
        _ManifestEntry("shared/pybind11/gitignore.j2", ".gitignore"),
        _ManifestEntry("types/pybind11-library/pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry("types/pybind11-library/Makefile.j2", "Makefile"),
        _ManifestEntry("types/pybind11-library/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("shared/cpp/README.md.j2", "README.md"),
        _ManifestEntry("shared/cpp/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/pybind11-library/CMakeLists.txt.j2", "CMakeLists.txt"),
        _ManifestEntry(
            "types/pybind11-library/src.cpp.j2", "src/{{ project.name }}.cpp"
        ),
        _ManifestEntry(
            "types/pybind11-library/include.h.j2", "include/{{ project.name }}.h"
        ),
        _ManifestEntry("types/pybind11-library/bindings.cpp.j2", "src/bindings.cpp"),
        _ManifestEntry(
            "types/pybind11-library/python/__init__.py.j2",
            "{{ project.name }}/__init__.py",
        ),
        _ManifestEntry(
            "types/pybind11-library/tests/test_bindings.py.j2", "tests/test_bindings.py"
        ),
        _ManifestEntry(
            "types/pybind11-library/github/ci.yml.j2", ".github/workflows/ci.yml"
        ),
    ],
    "pyo3-library": [
        _ManifestEntry("shared/pyo3/gitignore.j2", ".gitignore"),
        _ManifestEntry("types/pyo3-library/pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry("types/pyo3-library/Cargo.toml.j2", "Cargo.toml"),
        _ManifestEntry(
            "types/pyo3-library/rust-toolchain.toml.j2", "rust-toolchain.toml"
        ),
        _ManifestEntry("types/pyo3-library/Makefile.j2", "Makefile"),
        _ManifestEntry("types/pyo3-library/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("types/pyo3-library/README.md.j2", "README.md"),
        _ManifestEntry("types/pyo3-library/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/pyo3-library/crates/Cargo.toml.j2", "crates/Cargo.toml"),
        _ManifestEntry("types/pyo3-library/crates/lib.rs.j2", "crates/src/lib.rs"),
        _ManifestEntry(
            "types/pyo3-library/python/__init__.py.j2",
            "python/{{ project.name }}/__init__.py",
        ),
        _ManifestEntry(
            "types/pyo3-library/tests/test_bindings.py.j2", "tests/test_bindings.py"
        ),
        _ManifestEntry(
            "types/pyo3-library/github/ci.yml.j2", ".github/workflows/ci.yml"
        ),
        _ManifestEntry(
            "types/pyo3-library/github/release.yml.j2",
            ".github/workflows/release.yml",
        ),
    ],
    "web-app": [
        _ManifestEntry("types/web-app/gitignore.j2", ".gitignore"),
        _ManifestEntry("types/web-app/package.json.j2", "package.json"),
        _ManifestEntry("types/web-app/tsconfig.json.j2", "tsconfig.json"),
        _ManifestEntry("types/web-app/prettierrc.json.j2", ".prettierrc.json"),
        _ManifestEntry("types/web-app/eslint.config.js.j2", "eslint.config.js"),
        _ManifestEntry("types/web-app/vite.config.ts.j2", "vite.config.ts"),
        _ManifestEntry("types/web-app/index.html.j2", "index.html"),
        _ManifestEntry("types/web-app/Makefile.j2", "Makefile"),
        _ManifestEntry("types/web-app/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("types/web-app/README.md.j2", "README.md"),
        _ManifestEntry("types/web-app/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/web-app/src/main.tsx.j2", "src/main.tsx"),
        _ManifestEntry("types/web-app/src/App.tsx.j2", "src/App.tsx"),
        _ManifestEntry("types/web-app/vite-env.d.ts.j2", "src/vite-env.d.ts"),
        _ManifestEntry("types/web-app/tests/setup.ts.j2", "tests/setup.ts"),
        _ManifestEntry(
            "types/web-app/tests/unit/App.test.tsx.j2", "tests/unit/App.test.tsx"
        ),
        _ManifestEntry("types/web-app/github/ci.yml.j2", ".github/workflows/ci.yml"),
    ],
}


# frob:doc docs/commands/scaffold.md#public-api
def list_project_types() -> list[str]:
    return list(_MANIFESTS.keys())


def _resolve_manifest_paths(
    entries: list[_ManifestEntry], env: Environment, ctx: dict, output_dir: Path
) -> Result[list[tuple[_ManifestEntry, Path]], ScaffoldError]:
    """Render each entry's output-path template against `ctx`, joined under
    `output_dir`."""
    resolved: list[tuple[_ManifestEntry, Path]] = []
    for entry in entries:
        try:
            out_rel = env.from_string(entry.output).render(ctx)
        except Exception:
            return Err(ScaffoldError.RenderFailed)
        resolved.append((entry, output_dir / out_rel))
    return Ok(resolved)


def _write_manifest_entries(
    resolved: list[tuple[_ManifestEntry, Path]], env: Environment, ctx: dict
) -> Result[list[Path], ScaffoldError]:
    """Render each entry's template body and write it to its resolved path."""
    written: list[Path] = []
    for entry, out_path in resolved:
        try:
            tmpl = env.get_template(entry.template)
        except TemplateNotFound:
            return Err(ScaffoldError.TemplateNotFound)
        try:
            content = tmpl.render(ctx)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content)
        except Exception:
            return Err(ScaffoldError.RenderFailed)
        written.append(out_path)
    return Ok(written)


# frob:doc docs/commands/scaffold.md#public-api
def render_project(
    project_type: str,
    name: str,
    output_dir: Path,
    *,
    force: bool = False,
) -> Result[list[Path], ScaffoldError]:
    if project_type not in _MANIFESTS:
        return Err(ScaffoldError.UnknownType)

    env = Environment(
        loader=FileSystemLoader(str(_DATA_DIR)),
        keep_trailing_newline=True,
    )
    ctx = {"project": {"name": name, "type": project_type}}

    resolved_result = _resolve_manifest_paths(
        _MANIFESTS[project_type], env, ctx, output_dir
    )
    if resolved_result.is_err:
        return Err(resolved_result.danger_err)
    resolved = resolved_result.danger_ok

    if not force:
        for _, out_path in resolved:
            if out_path.exists():
                return Err(ScaffoldError.OutputExists)

    return _write_manifest_entries(resolved, env, ctx)


# frob:ticket T-0431
_WORKTREE_LEASE_HOOK_SCRIPT = """#!/bin/sh
# Installed by `frob scaffold install-worktree-lease-hook` (T-0431).
#
# Aborts a raw git commit/merge-commit run under an agent-context marker
# (FROB_AGENT set, non-empty) -- the incident this guards against: a
# dispatched worktree agent's shell accidentally ran `git merge main` /
# `git commit` straight against the MAIN checkout instead of its own
# worktree. A coordinator process (FROB_AGENT unset) is never affected.
if [ -n "$FROB_AGENT" ]; then
    echo "frob: refusing commit -- FROB_AGENT=$FROB_AGENT is set in this shell" >&2
    echo "frob: an agent-context shell must not commit directly in $(pwd)" >&2
    echo "frob: unset FROB_AGENT if deliberate, or run from the leased worktree" >&2
    exit 1
fi
"""

_WORKTREE_LEASE_HOOK_TERMINATOR = "exit 0\n"

# frob:ticket T-0577
# Second `pre-merge-commit` guard, appended after the T-0431 body above:
# refuses a REAL (non-squash) merge commit whose incoming side is a
# `worktree-agent-*` ticket branch, from ANY shell -- including a
# coordinator's, which the T-0431 guard above deliberately exempts
# (FROB_AGENT unset). All ~30 landings in one real session were manual
# raw `git merge`s of these branches, each needing the same hand-repeated
# draft-renumber/version-bump/ledger-splice surgery `frob ticket land`
# already automates; this makes bypassing `land` for a ticket branch a
# hard stop instead of a silently-worse manual path. `land`'s OWN internal
# git calls never trip this hook in the first place, by construction: both
# the worktree-into-main merge (`_merge_main_into_worktree`, `--no-commit`
# then a plain later `git commit`) and the squash-apply (`git merge
# --squash`) never let git create the automatic merge commit that
# `pre-merge-commit` fires for -- `--no-commit`/`--squash` both suppress
# it, and the later explicit `git commit` is an ordinary commit invoking
# only `pre-commit`, never `pre-merge-commit`. `FROB_LAND_INTERNAL=1` is
# offered anyway as an explicit, documented manual override for a
# deliberate exceptional raw merge (never set by `land` itself, since it
# never needs it).
_FORBID_RAW_TICKET_MERGE_SCRIPT = """
# T-0577: forbid a raw (non-land) merge of a worktree-agent-* branch.
# `git merge` sets GIT_REFLOG_ACTION to "merge <name-given-on-the-command-
# line>" in the environment every hook it invokes inherits -- read that
# directly rather than `.git/MERGE_HEAD` (observed, empirically, to no
# longer be present by the time `pre-merge-commit` fires on a plain,
# conflict-free merge under this git version/backend, even though older
# documentation describes it as readable here).
if [ -z "$FROB_LAND_INTERNAL" ]; then
    case "$GIT_REFLOG_ACTION" in
        merge\\ *worktree-agent-*)
            echo "frob: refusing raw merge of a ticket branch ($GIT_REFLOG_ACTION)" >&2
            echo "frob: use \\`frob ticket land <id> --worktree <path>\\` instead" >&2
            echo "frob: (set FROB_LAND_INTERNAL=1 to override deliberately)" >&2
            exit 1
            ;;
    esac
fi
"""

# frob:ticket T-0731
# Third guard, appended to `pre-commit` only: refuses a worktree commit
# that touches a land-owned file -- `pyproject.toml`'s version line,
# CHANGELOG.md, or uv.lock. T-0731's mandate: version bump and changelog
# authorship are land-time steps `frob ticket land` computes and writes
# exclusively (`_apply_release_bump_for_land`); an agent worktree hand-
# editing any of these is exactly the source of the merge collisions this
# guard exists to eliminate (every concurrent public-API ticket colliding
# on these three files was the single largest measured coordinator time
# sink). `FROB_LAND_INTERNAL=1` is the same escape hatch the T-0577 guard
# above already established for land's own internal git calls -- land
# itself never needs to set it, since it commits these files as `root`,
# not inside a worktree's `pre-commit` hook path.
#
# `tickets.md` gets a WARNING, not a refusal: detecting "this diff shape
# came from the frob ticket CLI, not a hand-edit" reliably from a shell
# hook is hard (the CLI's own commits have no distinguishing marker in the
# diff itself) -- documented v1 heuristic, per the ticket's own text,
# rather than a false-positive-prone hard refusal.
_FORBID_LAND_OWNED_FILES_SCRIPT = """
# T-0731: land-owned files (version bump, changelog, lockfile) are
# untouchable in a worktree commit; frob ticket land owns them exclusively.
if [ -z "$FROB_LAND_INTERNAL" ]; then
    staged=$(git diff --cached --name-only)
    case "$staged" in
        *CHANGELOG.md*)
            echo "frob: refusing commit -- CHANGELOG.md is land-owned (T-0731)" >&2
            echo "frob: the changelog entry is generated by \\`frob ticket land\\`" >&2
            exit 1
            ;;
    esac
    case "$staged" in
        *uv.lock*)
            echo "frob: refusing commit -- uv.lock is land-owned (T-0731)" >&2
            echo "frob: lockfile updates from a version bump happen at land time" >&2
            exit 1
            ;;
    esac
    if echo "$staged" | grep -qx "pyproject.toml"; then
        version_line='^[+-]version[[:space:]]*='
        if git diff --cached -- pyproject.toml | grep -qE "$version_line"; then
            echo "frob: refusing commit -- pyproject.toml touched (T-0731)" >&2
            echo "frob: version bump is land-owned -- frob ticket land writes it" >&2
            exit 1
        fi
    fi
    case "$staged" in
        *tickets.md*)
            echo "frob: WARNING -- tickets.md changed in this commit (T-0731)" >&2
            echo "frob: the ledger should only be written via the frob ticket CLI" >&2
            echo "frob: (heuristic warning, not a refusal -- v1, see T-0731)" >&2
            ;;
    esac
fi
"""

_WORKTREE_LEASE_HOOK_NAMES = ("pre-commit", "pre-merge-commit")


def _hooks_dir(root: Path) -> Result[Path, ScaffoldError]:
    """The real hooks directory for `root`'s repository (`git rev-parse
    --git-path hooks`, worktree-correct: a linked worktree normally shares
    the common dir's hooks/ unless `core.hooksPath` says otherwise, and
    `--git-path` resolves that for us rather than assuming `.git/hooks`
    literally).

    T-0803: routed through `frob.gitio.run_argv` (gains `guarded_subprocess_
    run`'s `FROB_DISABLE_EXEC` kill switch transitively, T-0778) instead of
    a bare `subprocess.run`."""
    from frob.gitio import run_argv

    spawned = run_argv(
        ["git", "-C", str(root), "rev-parse", "--git-path", "hooks"], timeout_s=10
    )
    if spawned.is_err:
        _log.error("scaffold: git rev-parse --git-path hooks failed")
        return Err(ScaffoldError.NotAGitRepo)
    completed = spawned.danger_ok
    if completed.returncode != 0:
        _log.error(
            "scaffold: %s is not inside a git work tree (git rev-parse --git-path "
            "hooks exited %d)",
            root,
            completed.returncode,
        )
        return Err(ScaffoldError.NotAGitRepo)
    raw = completed.stdout.strip()
    if not raw:
        return Err(ScaffoldError.NotAGitRepo)
    path = Path(raw)
    if not path.is_absolute():
        path = (root / path).resolve()
    return Ok(path)


# frob:doc docs/commands/scaffold.md#public-api
# frob:ticket T-0731
# frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_installs_pre_commit_and_pre_merge_commit  # noqa: E501
# frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_refuses_existing_hook_without_force  # noqa: E501
# frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_commit_refused_changelog  # noqa: E501
# frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_commit_refused_uv_lock  # noqa: E501
# frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_commit_refused_pyproject_version  # noqa: E501
# frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_pyproject_edit_without_version_change_allowed  # noqa: E501
# frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_override_env_var_allows_it  # noqa: E501
# frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_tickets_md_change_warns_but_does_not_refuse  # noqa: E501
def install_worktree_lease_hook(
    root: Path, *, force: bool = False
) -> Result[tuple[Path, ...], ScaffoldError]:
    """Install the T-0431 worktree-lease `pre-commit`/`pre-merge-commit`
    git hooks into `root`'s real hooks directory (`_hooks_dir`): each
    hook aborts loudly if `FROB_AGENT` is set in the environment it runs
    in, catching a stray raw `git commit`/`git merge` from an
    agent-context shell that wandered into the wrong checkout.
    `pre-merge-commit` ALSO carries the T-0577 raw-ticket-branch-merge
    guard (`_FORBID_RAW_TICKET_MERGE_SCRIPT`): it refuses a real merge
    commit whose incoming side is a `worktree-agent-*` branch from ANY
    shell, coordinator included, forcing `frob ticket land` as the only
    path onto main for a ticket branch. `pre-commit` ALSO carries the
    T-0731 land-owned-files guard (`_FORBID_LAND_OWNED_FILES_SCRIPT`): it
    refuses a worktree commit touching `pyproject.toml`'s version line,
    CHANGELOG.md, or uv.lock (all three are `frob ticket land`'s
    exclusively, per T-0731), and warns (does not refuse) on tickets.md.

    `Err(OutputExists)` if either hook file already exists and `force` is
    not set -- never silently overwrites a repo's own custom hook.
    Returns the paths written, executable-bit set (`chmod +x`, POSIX)."""
    hooks_dir_result = _hooks_dir(root)
    if hooks_dir_result.is_err:
        return Err(hooks_dir_result.danger_err)
    hooks_dir = hooks_dir_result.danger_ok

    targets = tuple(hooks_dir / name for name in _WORKTREE_LEASE_HOOK_NAMES)
    if not force:
        existing = [p for p in targets if p.exists()]
        if existing:
            _log.error(
                "scaffold: refusing to overwrite existing hook(s) %s without force",
                existing,
            )
            return Err(ScaffoldError.OutputExists)

    written: list[Path] = []
    try:
        hooks_dir.mkdir(parents=True, exist_ok=True)
        for path in targets:
            # T-0577: `pre-merge-commit` ALSO carries the raw-ticket-branch-
            # merge refusal (`_FORBID_RAW_TICKET_MERGE_SCRIPT`), spliced in
            # BEFORE the shared unconditional `exit 0` terminator -- the
            # T-0431 FROB_AGENT check above runs and exits 1 first when it
            # fires; only when it does NOT fire does control fall through
            # to this guard, which has its own internal `exit 1` (and, if
            # neither guard fires, the shared terminator exits 0).
            body = _WORKTREE_LEASE_HOOK_SCRIPT
            if path.name == "pre-merge-commit":
                body += _FORBID_RAW_TICKET_MERGE_SCRIPT
            if path.name == "pre-commit":
                body += _FORBID_LAND_OWNED_FILES_SCRIPT
            body += _WORKTREE_LEASE_HOOK_TERMINATOR
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            written.append(path)
    except OSError as exc:
        _log.error("scaffold: could not write worktree-lease hook: %s", exc)
        return Err(ScaffoldError.HookWriteFailed)

    _log.info("scaffold: installed worktree-lease hook(s) at %s", written)
    return Ok(tuple(written))
