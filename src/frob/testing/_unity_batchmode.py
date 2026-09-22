"""Unity batchmode test-results evidence channel (T-4508, story T-4516,
epic T-4513): resolves the Unity Editor binary to invoke (T-4501's
already-shipped doctor lookup, plus a `[tool.frob] unity_editor` pyproject
override), runs it in `-batchmode -runTests` against a selected set of
`<path>::<Namespace.Class>::<Method>` node ids (T-4517's csharp
collection shape -- Unity Test Framework `[Test]`/`[UnityTest]` methods
share that same shape), and parses the resulting NUnit3 XML report into a
per-node pass/fail map.

Kept as its own module, not folded into `_runners.py`, because Unity
batchmode is not a `[[test.runner]]`-declarable command the way `dotnet
test`/`cargo test`/`pytest` are (T-0128's per-runner-per-cwd model): a
Unity Editor process launch is minutes, not seconds, per invocation, so
this channel always runs the WHOLE selected set in one editor launch and
attributes every result from ONE parsed report -- there is no
bisection-friendly "run just this one test" fallback the way
`run_selected`'s generic per-id retry path assumes for cheap runners.
See `docs/guides/unity.md` for the exact CLI this module documents and
drives.
"""

from __future__ import annotations

import os
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.gitio import excerpt, run_argv
from frob.logging import get_logger
from frob.testing._dotnet_runner import _csharp_fqn, _strip_xml_ns

_log = get_logger(__name__)

_DEFAULT_TIMEOUT_S = 1800.0

# NUnit3's own outcome vocabulary (`<test-case result="...">`) that counts
# as a real pass; every other value (Failed, Skipped, Inconclusive, ...)
# is not-passing (mirrors `_runners.py`'s `_DOTNET_PASSED_OUTCOMES`).
_UNITY_PASSED_RESULTS = frozenset({"Passed"})


# frob:doc docs/guides/unity.md#unity-batchmode-evidence-channel
class UnityBatchmodeError(ErrorSet):
    """Failure values `run_unity_batchmode`/`parse_unity_batchmode_xml`
    can return (T-4508)."""

    __test__: bool = False

    EditorNotFound = (
        "No Unity Editor binary resolved (UNITY_PATH/UNITY_EDITOR, "
        "[tool.frob] unity_editor, Unity Hub, or PATH)"
    )
    SpawnFailed = "The Unity Editor process could not be started or timed out"
    RunFailed = (
        "Unity exited with no results file -- an editor crash or license "
        "failure, not a genuine test failure"
    )
    ResultsUnreadable = (
        "The batchmode results file was malformed, or a requested node id "
        "had no matching test-case -- never a silent empty pass"
    )


# frob:ticket T-4508
def _pyproject_unity_editor(root: Path) -> str | None:
    """The `[tool.frob] unity_editor` key from `root/pyproject.toml`, an
    explicit path override checked before any auto-detection -- `None`
    when the file/table/key is absent or unparsable (never raises; a
    malformed pyproject degrades to "no override", the same posture
    `_runners.py`'s `load_runners` takes for a malformed `frob.toml`)."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        with pyproject.open("rb") as f:
            doc = tomllib.load(f)
    except (OSError, ValueError) as exc:
        _log.error("unity_batchmode: could not parse %s: %s", pyproject, exc)
        return None
    value = doc.get("tool", {}).get("frob", {}).get("unity_editor")
    return str(value) if value else None


# frob:doc docs/guides/unity.md#unity-batchmode-evidence-channel
# frob:ticket T-4508
def resolve_unity_editor(root: Path) -> str | None:
    """The Unity Editor binary path to invoke for batchmode runs, in
    precedence order: `[tool.frob] unity_editor` in `root/pyproject.toml`
    (an explicit, repo-pinned override), then `UNITY_PATH`/`UNITY_EDITOR`/
    Unity Hub/PATH via `frob.doctor._locate_unity_editor` (T-4501 --
    reused rather than re-implemented, per this ticket's own instruction).
    `None` when nothing resolves. Imported lazily: `frob.doctor` is a
    large, broadly-importing module this narrow evidence channel should
    not force onto every `frob.testing` import."""
    explicit = _pyproject_unity_editor(root)
    if explicit:
        _log.info(
            "unity_batchmode: editor resolved via pyproject override: %s", explicit
        )
        return explicit
    from frob.doctor import _locate_unity_editor

    status = _locate_unity_editor()
    if status.present and status.path:
        return status.path
    _log.error("unity_batchmode: no Unity editor resolved (env/pyproject/Hub/PATH)")
    return None


# frob:doc docs/guides/unity.md#unity-batchmode-evidence-channel
# frob:ticket T-4508
def parse_unity_batchmode_xml(text: str) -> Result[dict[str, str], UnityBatchmodeError]:
    """Parse one Unity Test Framework batchmode NUnit3 results file
    (`Unity -batchmode -runTests -testResults <path>`'s own output
    format) into `{dotted_fqn: result}` (`result` is NUnit3's own
    vocabulary: `"Passed"`/`"Failed"`/`"Skipped"`/`"Inconclusive"`).
    NUnit3 nests `<test-case fullname="Namespace.Class.Method" .../>`
    leaves arbitrarily deep inside `<test-suite>` wrappers -- this walks
    every descendant rather than assuming a fixed depth. `Err(
    ResultsUnreadable)` on malformed XML, never a silently empty map."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        _log.error("unity_batchmode: malformed results XML: %s", exc)
        return Err(UnityBatchmodeError.ResultsUnreadable)
    outcomes: dict[str, str] = {}
    for el in root.iter():
        if _strip_xml_ns(el.tag) != "test-case":
            continue
        fullname = el.get("fullname")
        if not fullname:
            continue
        outcomes[fullname] = el.get("result") or ""
    return Ok(outcomes)


def _unity_results_path(root: Path) -> Path:
    """A fresh, not-yet-existing path for `-testResults` to write to --
    same reservation shape as `_runners.py`'s `_dotnet_trx_path` (create
    via `mkstemp` then unlink, so the name is unique but the Editor -- not
    us -- creates the real file)."""
    frob_dir = root / ".frob"
    fd, raw_path = tempfile.mkstemp(
        prefix="unity-results-",
        suffix=".xml",
        dir=str(frob_dir) if frob_dir.is_dir() else None,
    )
    os.close(fd)
    path = Path(raw_path)
    path.unlink(missing_ok=True)
    return path


def _unity_batchmode_argv(
    editor: str, project_path: Path, results_path: Path, items: tuple[str, ...]
) -> list[str]:
    """The `Unity -batchmode -runTests ...` argv for one invocation;
    `-testFilter` (a comma-separated dotted-FQN allowlist Unity Test
    Framework understands) is added only when `items` names specific
    tests -- an empty `items` runs the project's whole suite, matching
    `run_selected`'s own `ALL_SENTINEL`-absent-means-everything
    convention."""
    argv = [
        editor,
        "-batchmode",
        "-runTests",
        "-projectPath",
        str(project_path),
        "-testResults",
        str(results_path),
        "-quit",
    ]
    if items:
        fqns = ",".join(_csharp_fqn(item) for item in items)
        argv.extend(["-testFilter", fqns])
    return argv


# frob:ticket T-4508
def _run_unity_batchmode_process(
    editor: str,
    project_path: Path,
    results_path: Path,
    items: tuple[str, ...],
    root: Path,
    timeout_s: float,
) -> Result[str, UnityBatchmodeError]:
    """Spawn the Unity batchmode process and return its results file's
    text -- `Err(SpawnFailed)` on a spawn/timeout failure, `Err(
    RunFailed)` when the process exits with no results file at all (an
    editor crash or license failure, not a genuine test failure). Split
    out of `run_unity_batchmode` (T-4508 follow-up) so that function
    stays under ARCH001's line threshold; the caller still owns XML
    parsing and per-id result mapping."""
    argv = _unity_batchmode_argv(editor, project_path, results_path, items)
    spawned = run_argv(argv, cwd=root, timeout_s=timeout_s)
    if spawned.is_err:
        _log.error("run_unity_batchmode: Unity failed to spawn or timed out")
        return Err(UnityBatchmodeError.SpawnFailed)
    result = spawned.danger_ok
    if not results_path.exists():
        _log.error(
            "run_unity_batchmode: Unity exited %d with no results file at "
            "%s -- editor crash or license failure, not a genuine test "
            "failure (stderr: %s)",
            result.returncode,
            results_path,
            excerpt(result.stderr),
        )
        return Err(UnityBatchmodeError.RunFailed)
    try:
        return Ok(results_path.read_text(encoding="utf-8"))
    finally:
        results_path.unlink(missing_ok=True)


# frob:doc docs/guides/unity.md#unity-batchmode-evidence-channel
# frob:ticket T-4508
# frob:waive WIRE001 reason="the direct evidence-channel entry point this ticket adds; \
# routing frob's ticket-runner CLI to call it for Unity node ids is T-4516's own scope \
# (blocked_by T-4518's project-model detection), not this ticket's" follow_up="T-4516"
def run_unity_batchmode(
    items: tuple[str, ...],
    root: Path,
    *,
    project_path: Path | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> Result[dict[str, bool], UnityBatchmodeError]:
    """Run `items` (`[Test]`/`[UnityTest]` node ids, T-4517's csharp
    collection shape) through ONE `Unity -batchmode -runTests` invocation
    and parse its NUnit3 results into a per-node `{node_id: passed}` map.

    `Err(EditorNotFound)` when `resolve_unity_editor` finds nothing to
    run. `Err(SpawnFailed)` on a spawn/timeout failure. `Err(RunFailed)`
    when the process exits with NO results file at all -- this is this
    ticket's third acceptance criterion: an editor crash or Unity license
    failure must surface as a distinct, clearly-labeled error, never read
    as "zero tests ran, zero tests failed" (a silent empty-results false
    pass). `Err(ResultsUnreadable)` on malformed XML, or when a requested
    id has no matching `test-case` in the parsed report (the run
    completed but never actually exercised that test) -- also never a
    silent pass."""
    editor = resolve_unity_editor(root)
    if editor is None:
        return Err(UnityBatchmodeError.EditorNotFound)
    results_path = _unity_results_path(root)
    spawned_text = _run_unity_batchmode_process(
        editor, project_path or root, results_path, items, root, timeout_s
    )
    if spawned_text.is_err:
        return Err(spawned_text.danger_err)

    parsed = parse_unity_batchmode_xml(spawned_text.danger_ok)
    if parsed.is_err:
        return Err(parsed.danger_err)
    outcomes = parsed.danger_ok

    wanted = items or tuple(outcomes)
    results: dict[str, bool] = {}
    for item in wanted:
        fqn = _csharp_fqn(item)
        outcome = outcomes.get(fqn)
        if outcome is None:
            _log.error(
                "run_unity_batchmode: %s (fqn=%s) has no test-case in the "
                "results -- refusing to report a silent pass for an "
                "unmeasured id",
                item,
                fqn,
            )
            return Err(UnityBatchmodeError.ResultsUnreadable)
        results[item] = outcome in _UNITY_PASSED_RESULTS
    _log.info(
        "run_unity_batchmode: %d/%d item(s) passed", sum(results.values()), len(results)
    )
    return Ok(results)


__all__ = [
    "UnityBatchmodeError",
    "parse_unity_batchmode_xml",
    "resolve_unity_editor",
    "run_unity_batchmode",
]
