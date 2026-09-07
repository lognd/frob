"""ONE mechanism for spawning a TARGET PROJECT's own toolchain (T-3887/
T-4125): every call site that used to hardcode a bare tool name (`["ty",
...]`, `["ruff", ...]`) or a hand-rolled `["uv", "run", "ruff", ...]`
routes through `project_tool_argv`/`resolve_project_tool` instead, so the
binary that actually runs is always the one `uv run --project <root>`
resolves inside THAT project's own environment -- never whatever a bare
name happens to resolve to on PATH.

WHY THIS EXISTS (T-4125): a bare `["ty", "check", ...]` in `_land_cmd.py`
resolved via PATH to a globally installed `ty` (0.0.58) while this
project's own venv pinned `ty` 0.0.46 -- so a land refused a ticket on
findings from a checker version the project does not use and does not
pin. A consumer hit the identical defect in the OPPOSITE direction (their
venv's `ty` was NEWER than PATH's), which is why this module never
assumes which side is "right" by version comparison: it simply never
lets a bare name resolve at all. `uv run --project <root> <tool> ...`
resolves `<tool>` from the project's own lockfile/venv regardless of what
PATH holds, exactly the pattern this repo's own `pyfmt_runner.py`
already used correctly at two of its four `ruff` call sites (T-4125's
population measurement) -- this module makes that the ONLY spelling
rather than one of two.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run

if TYPE_CHECKING:
    pass

_log = get_logger(__name__)


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_project_tool.py::TestResolveProjectTool.test_which_spawn_failure_is_err  # noqa: E501
class ProjectToolError(ErrorSet):
    """Recoverable failures resolving or identifying a project-scoped
    toolchain binary through `uv run --project`: `uv` itself is not on
    PATH (`UvUnavailable`), or the resolve/version probe spawn failed or
    timed out (`ResolveFailed`)."""

    UvUnavailable = "uv is not on PATH -- cannot resolve any project tool"
    ResolveFailed = "spawning the project-scoped tool resolution probe failed"


def _project_tool_argv(root: Path, tool: str, *args: str) -> list[str]:
    """Shared argv builder behind both `project_tool_argv` and
    `project_import_argv` (T-4171): `uv run --no-sync --project <root>
    <tool> <*args>`. Both spawn kinds resolve `tool` from `root`'s own
    lockfile/venv rather than the spawning process's PATH, and both
    must never create or mutate that environment as a side effect --
    `--no-sync` is load-bearing for each, not just the run-only kind
    (T-4163's dirty-tree bug can happen to an importing spawn exactly
    the same way). What differs between the two public wrappers is
    never this argv shape, only how a caller must react when the
    environment `--no-sync` refuses to populate turns out not to have
    what's needed -- see each wrapper's own docstring."""
    return ["uv", "run", "--no-sync", "--project", str(root), tool, *args]


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_project_tool.py::TestProjectToolArgv.test_shape
def project_tool_argv(root: Path, tool: str, *args: str) -> list[str]:
    """The RUN-ONLY spawn kind (T-4171): invoking `tool` (e.g. `"ty"`,
    `"ruff"`, `"pytest"`) purely as a tool BINARY inside the project
    rooted at `root`'s OWN environment -- the caller never imports
    anything from `root`'s own source tree, it only runs an external
    checker/formatter against it and reads that process's stdout/exit
    code. `uv run` resolves `tool` from that project's lockfile/venv
    regardless of what a bare name would resolve to on PATH -- the fix
    for T-4125's population of bare-name call sites and the one shape
    T-3887's BARETOOL001 gate (`frob.gates._bare_toolchain`) now
    enforces everywhere a project toolchain is spawned. Every caller
    should pass this list straight to `guarded_subprocess_run`/
    `subprocess.run`, never construct its own `["uv", "run", ...]` or
    bare-name argv by hand -- one mechanism, not a second correct
    spelling living next to the wrong one (T-4125's own
    `pyfmt_runner.py` finding: both spellings existed four lines apart).

    T-4163: `--no-sync` is load-bearing, not an optimization -- plain
    `uv run --project <root>` lazily locks/syncs that project's OWN
    environment on first use, writing an untracked `uv.lock` (and
    creating `.venv/`) INSIDE the target project's working tree as a
    side effect of a read-only lint/typecheck spawn. When `frob check`
    is the caller diffing that same tree a few gates later, its own
    tool invocation manufactures the dirty file PRE001/SCOPE001 then
    refuse on -- a check that never touched the target's source still
    exits nonzero over a file `frob` itself just wrote. `--no-sync` runs
    `tool` against whatever environment already exists without
    resolving/writing a lockfile or venv; a project that genuinely needs
    a fresh sync should run `uv sync` itself as an explicit step, not
    have it triggered as a hidden side effect of `frob check`. Every
    call site behind this wrapper is a run-only spawn -- if a future
    caller needs to IMPORT `root`'s own modules, it must use
    `project_import_argv` instead, never this one (T-4171: the two
    kinds have opposite failure postures once the environment is
    absent)."""
    return _project_tool_argv(root, tool, *args)


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_check.py::TestProjectImportArgv.test_shape kind="unit"
# frob:tests \
# tests/unit/test_check.py::TestProjectImportArgv.test_same_shape_as_run_only kind="unit"  # noqa: E501
# frob:tests \
# tests/unit/test_check.py::TestProjectToolSpawnNonMutation.test_import_spawn_does_not_mutate_an_already_present_env kind="unit"  # noqa: E501
def project_import_argv(root: Path, tool: str, *args: str) -> list[str]:
    """The IMPORTING spawn kind (T-4171): a `tool` invocation (in
    practice always `"python"`, running a short script argv) whose
    WHOLE POINT is to import code that lives inside the project rooted
    at `root` -- `frob.gates._flag_coverage`'s resolver script is the
    one caller today, importing a consumer's own parser-factory/config
    module so a dependency-version mismatch with frob's own interpreter
    can never break the import (T-4147).

    Argv shape is IDENTICAL to `project_tool_argv` -- still `--no-sync`,
    still never creates or mutates `root`'s environment -- because
    T-4163's dirty-tree bug applies here too: an importing gate that
    silently synced `root` on a cold environment would write the exact
    untracked lockfile/venv a later gate then refuses `root`'s tree on,
    the same failure mode T-4163 fixed for the run-only kind. The
    difference this wrapper exists to name is what a caller MUST do
    when the import then fails because no environment was present to
    import from: report the check as UNRESOLVED/UNMEASURED, never as a
    clean pass and never by falling back to syncing one into existence.
    A project whose dependencies genuinely need to be present for this
    gate to measure anything must be synced by an explicit `uv sync`
    step (the operator's or CI's, not this gate's) BEFORE `frob check`
    runs -- exactly the T-4163 doctrine, extended to the importing case
    instead of carved out as an exception to it."""
    return _project_tool_argv(root, tool, *args)


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_project_tool.py::TestToolIdentity.test_describe
class ToolIdentity:
    """The RESOLVED identity of a project-scoped tool spawn: the
    absolute binary path `uv run` actually launched, and the tool's own
    `--version` output. Carried by `resolve_project_tool`'s `Ok` so a
    caller (in particular the land's type-check refusal message, T-4125)
    can name exactly which binary produced a finding -- the diagnostic
    gap T-4125's original report identified: a refusal naming only a
    count, reproducible in no tree or checker version the operator could
    inspect."""

    __slots__ = ("path", "version")

    def __init__(self, path: str, version: str) -> None:
        """Store the resolved absolute `path` and the tool's raw
        `version` string (its own `--version` stdout, trimmed)."""
        self.path = path
        self.version = version

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """`ToolIdentity(path=..., version=...)`, for logs/assertions."""
        return f"ToolIdentity(path={self.path!r}, version={self.version!r})"

    # frob:doc docs/modules/process.md#public-api
    # frob:tests tests/unit/test_project_tool.py::TestToolIdentity.test_describe
    def describe(self) -> str:
        """One-line `<path> (<version>)` rendering for embedding in a
        gate refusal or diagnostic message."""
        return f"{self.path} ({self.version})"


#: T-4125: `uv run --project <root> python -c ...` resolves `tool`'s
#: absolute path from INSIDE the project's own environment (`shutil.
#: which` run by that environment's own `python`, not frob's) -- the
#: only way to name the resolved binary path without assuming which of
#: several possible resolution orders `uv run` itself used internally.
_WHICH_PROBE = (
    "import shutil, sys; p = shutil.which(sys.argv[1]); print(p or '', end='')"
)


# frob:doc docs/modules/process.md#public-api
# frob:ticket T-4125
# frob:tests tests/unit/test_project_tool.py::TestResolveProjectTool.test_ok_resolves_path_and_version  # noqa: E501
def resolve_project_tool(
    root: Path, tool: str, timeout_s: float = 30.0
) -> Result[ToolIdentity, ProjectToolError]:
    """Resolve `tool`'s absolute path AND `--version` string, both from
    INSIDE the project rooted at `root`'s own `uv`-managed environment --
    never frob's own interpreter's view of PATH. Two short spawns
    (`uv run --project <root> python -c '<which-probe>' <tool>`, then
    `project_tool_argv(root, tool, "--version")`); either spawn failing
    to run at all (missing `uv`, a timeout, exec disabled) is
    `Err(ProjectToolError.ResolveFailed)` -- a caller that only needs a
    best-effort diagnostic string should treat `Err` as "identity
    unknown", never crash. `tool --version` exiting nonzero still
    yields `Ok`: some tools (rare) print version info to stderr with a
    nonzero exit, and refusing to NAME the tool because the version
    probe itself was imperfect would defeat this function's whole
    purpose (T-4125: the refusal message must name the tool regardless)."""
    which_result = guarded_subprocess_run(
        project_tool_argv(root, "python", "-c", _WHICH_PROBE, tool),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if which_result.is_err:
        _log.warning(
            "resolve_project_tool: could not resolve %r's path in %s: %s",
            tool,
            root,
            which_result.danger_err,
        )
        return Err(ProjectToolError.ResolveFailed)
    path = which_result.danger_ok.stdout.strip() or f"<unresolved:{tool}>"

    version_result = guarded_subprocess_run(
        project_tool_argv(root, tool, "--version"),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if version_result.is_err:
        _log.warning(
            "resolve_project_tool: could not run %r --version in %s: %s",
            tool,
            root,
            version_result.danger_err,
        )
        return Err(ProjectToolError.ResolveFailed)
    proc = version_result.danger_ok
    version = (proc.stdout + proc.stderr).strip() or f"<exit {proc.returncode}>"
    return Ok(ToolIdentity(path=path, version=version))


__all__ = [
    "ProjectToolError",
    "ToolIdentity",
    "project_import_argv",
    "project_tool_argv",
    "resolve_project_tool",
]
