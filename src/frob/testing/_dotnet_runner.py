"""dotnet test evidence channel (T-4508): invokes `dotnet test --filter
FullyQualifiedName=...` for a selected set of csharp node ids and parses
its VSTest TRX output into a per-node pass/fail map.

Split out of `_runners.py` (T-4508 follow-up: `_runners.py` crossed
LARGE001's 800-line threshold once this channel was added) rather than
folded into `run_selected`'s generic `[[test.runner]]` path, for the same
reason `_unity_batchmode.py` stands apart: this reports a per-test
breakdown from ONE batched invocation, not one aggregate exit code per
run. `_csharp_fqn`/`_strip_xml_ns` are shared with `_unity_batchmode.py`
(both TRX and Unity's NUnit3 XML need the same node-id-to-dotted-FQN
transform and the same namespace-stripping helper), so they live here as
this module's own public surface and `_unity_batchmode` imports them
rather than each keeping its own copy (T-4508's no-duplication rule).
"""

from __future__ import annotations

import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.gitio import excerpt, run_argv
from frob.logging import get_logger
from frob.testing._runners import TestingError

_log = get_logger(__name__)

# dotnet's own outcome vocabulary for a `UnitTestResult/@outcome` attribute
# that counts as a real pass; every other value (Failed, NotExecuted,
# Inconclusive, ...) is not-passing (T-4508).
# frob:ticket T-4508
_DOTNET_PASSED_OUTCOMES = frozenset({"Passed"})

# frob:ticket T-4508
_DOTNET_RUN_TIMEOUT_S = 900.0


# frob:doc docs/modules/testing.md#public-api
# frob:ticket T-4508
def _csharp_fqn(node_id: str) -> str:
    """The `<path>::<Namespace.Class>::<Method>` node id
    (`frob.testing._collect_csharp`'s NODE ID SHAPE) as .NET's dotted
    `Namespace.Class.Method` fully-qualified test name -- the identifier
    both `dotnet test --filter FullyQualifiedName=...` and Unity Test
    Framework's `-testFilter` key a test by, never frob's own
    `::`-delimited node id. Returns `node_id` unchanged if it does not
    have the expected two-`::`-separator shape (defensive: a caller
    handing this a non-csharp id gets an inert passthrough, not a raise)."""
    _, sep, rest = node_id.partition("::")
    if not sep:
        return node_id
    class_part, sep2, method = rest.partition("::")
    if not sep2:
        return rest
    return f"{class_part}.{method}"


# frob:ticket T-4508
def _dotnet_filter_expr(items: tuple[str, ...]) -> str:
    """A `dotnet test --filter` boolean-OR expression selecting every
    `_csharp_fqn` derived from `items` (dotnet's `--filter` grammar ORs
    `FullyQualifiedName=...` clauses with `|`; a single item needs no
    `|` and this still produces a valid one-clause expression)."""
    return "|".join(f"FullyQualifiedName={_csharp_fqn(item)}" for item in items)


# frob:ticket T-4508
def _strip_xml_ns(tag: str) -> str:
    """An XML element tag with any `{namespace}` prefix removed -- TRX's
    root xmlns wraps every tag, so a plain tag-name comparison against
    `"UnitTest"`/`"TestMethod"`/`"UnitTestResult"` would otherwise never
    match."""
    return tag.rsplit("}", 1)[-1]


# frob:ticket T-4508
def _parse_trx(text: str) -> Result[dict[str, str], TestingError]:
    """Parse one VSTest TRX results file (`dotnet test --logger trx`'s
    native output format) into `{dotted_fqn: outcome}` (outcome is TRX's
    own vocabulary, e.g. `"Passed"`/`"Failed"`/`"NotExecuted"`) --
    `Err(DotnetResultsUnreadable)` on malformed XML, never a silently
    empty map. TRX links a `<UnitTestResult testId=.../>` to its
    `<UnitTest id=...><TestMethod className=... name=.../></UnitTest>`
    definition by `id`/`testId`; `className` carries a trailing
    `, AssemblyName` qualifier this strips before joining with `name`."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        _log.error("run_dotnet_tests: malformed TRX output: %s", exc)
        return Err(TestingError.DotnetResultsUnreadable)

    definitions: dict[str, str] = {}
    for el in root.iter():
        if _strip_xml_ns(el.tag) != "UnitTest":
            continue
        test_id = el.get("id")
        method_el = next(
            (c for c in el.iter() if _strip_xml_ns(c.tag) == "TestMethod"), None
        )
        if test_id is None or method_el is None:
            continue
        class_name = (method_el.get("className") or "").split(",", 1)[0]
        name = method_el.get("name") or ""
        definitions[test_id] = f"{class_name}.{name}"

    outcomes: dict[str, str] = {}
    for el in root.iter():
        if _strip_xml_ns(el.tag) != "UnitTestResult":
            continue
        test_id = el.get("testId") or ""
        fqn = definitions.get(test_id)
        if fqn is None:
            continue
        outcomes[fqn] = el.get("outcome") or ""
    return Ok(outcomes)


# frob:ticket T-4508
def _dotnet_trx_path(root: Path) -> Path:
    """A fresh, not-yet-existing path for `dotnet test --logger trx` to
    write its results to -- under `root/.frob` when that directory
    already exists (kept off the tracked tree, matching every other
    `.frob/`-scoped scratch file this package writes), a plain system
    temp file otherwise. The file itself is created empty by `mkstemp`
    then immediately unlinked: `dotnet test` refuses to write a TRX file
    that already exists, so this only reserves a unique name."""
    frob_dir = root / ".frob"
    fd, raw_path = tempfile.mkstemp(
        prefix="dotnet-",
        suffix=".trx",
        dir=str(frob_dir) if frob_dir.is_dir() else None,
    )
    os.close(fd)
    path = Path(raw_path)
    path.unlink(missing_ok=True)
    return path


def _run_dotnet_test_process(
    argv: list[str], root: Path, timeout_s: float
) -> Result[str, TestingError]:
    """Spawn `dotnet test` and return its TRX file's text -- `Err(
    SpawnFailed)` on a spawn/timeout failure, `Err(DotnetRunFailed)` when
    the process exits with no TRX file at all (an editor-crash-shaped
    failure with nothing to attribute a result to). Split out of
    `run_dotnet_tests` (T-4508 follow-up) so that function stays under
    ARCH001's line threshold; the caller still owns TRX parsing and
    per-id result mapping."""
    trx_path = _dotnet_trx_path(root)
    full_argv = [*argv, "--logger", f"trx;LogFileName={trx_path}"]
    spawned = run_argv(full_argv, cwd=root, timeout_s=timeout_s)
    if spawned.is_err:
        _log.error("run_dotnet_tests: dotnet test failed to spawn or timed out")
        return Err(TestingError.SpawnFailed)
    result = spawned.danger_ok
    if not trx_path.exists():
        _log.error(
            "run_dotnet_tests: dotnet test exited %d with no TRX file at "
            "%s -- treating as a run failure, not a silent empty pass "
            "(stderr: %s)",
            result.returncode,
            trx_path,
            excerpt(result.stderr),
        )
        return Err(TestingError.DotnetRunFailed)
    try:
        return Ok(trx_path.read_text(encoding="utf-8"))
    finally:
        trx_path.unlink(missing_ok=True)


# frob:doc docs/modules/testing.md#public-api
# frob:ticket T-4508
# frob:waive WIRE001 reason="the direct evidence-channel entry point this ticket adds; \
# routing frob's ticket-runner CLI to call it for csharp node ids is T-4516's own \
# scope (blocked_by T-4518's project-model detection), not this ticket's" \
# follow_up="T-4516"
def run_dotnet_tests(
    items: tuple[str, ...],
    root: Path,
    *,
    project: str = ".",
    timeout_s: float = _DOTNET_RUN_TIMEOUT_S,
) -> Result[dict[str, bool], TestingError]:
    """Run `items` (csharp `<path>::<Namespace.Class>::<Method>` node ids,
    T-4517's collection shape) through ONE batched `dotnet test --filter
    FullyQualifiedName=...` invocation, parsing its TRX output into a
    per-node `{node_id: passed}` map -- the direct evidence channel
    T-4508 asks for, distinct from `run_selected`'s generic per-language
    `[[test.runner]]` path (which only reports one aggregate exit code
    per invocation, not a per-test breakdown).

    `Err(SpawnFailed)` on a spawn/timeout failure (dotnet not on PATH,
    the process wedged); `Err(DotnetRunFailed)` when the process exits
    with no TRX file at all (an editor-crash-shaped failure: the run
    never produced results to attribute anything to); `Err(
    DotnetResultsUnreadable)` on malformed TRX XML OR when a requested
    id has no corresponding result in it (a filter that matched nothing,
    or a test dotnet silently dropped) -- every one of these is a hard
    `Err`, never a map missing that id, so a caller can never mistake
    "we could not tell" for "it passed" (mirrors the Unity batchmode
    parser's own "never a silent empty-results false pass" rule)."""
    if not items:
        return Ok({})
    argv = ["dotnet", "test", project, "--filter", _dotnet_filter_expr(items)]
    spawned_text = _run_dotnet_test_process(argv, root, timeout_s)
    if spawned_text.is_err:
        return Err(spawned_text.danger_err)

    parsed = _parse_trx(spawned_text.danger_ok)
    if parsed.is_err:
        return Err(parsed.danger_err)
    outcomes = parsed.danger_ok

    results: dict[str, bool] = {}
    for item in items:
        fqn = _csharp_fqn(item)
        outcome = outcomes.get(fqn)
        if outcome is None:
            _log.error(
                "run_dotnet_tests: %s (fqn=%s) has no TRX result -- refusing "
                "to report a silent pass for an unmeasured id",
                item,
                fqn,
            )
            return Err(TestingError.DotnetResultsUnreadable)
        results[item] = outcome in _DOTNET_PASSED_OUTCOMES
    _log.info(
        "run_dotnet_tests: %d/%d item(s) passed", sum(results.values()), len(results)
    )
    return Ok(results)


__all__ = [
    "run_dotnet_tests",
]
