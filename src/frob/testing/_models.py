"""Data shapes for touched-set test selection and execution
(docs/modules/testing.md)."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict


# frob:doc docs/modules/testing.md#data-models
# frob:doc docs/guides/extending/test-runner-entries.md#test-runner-entries
class RunnerSpec(BaseModel):
    """One `[[test.runner]]` entry: how to invoke a language's test runner.
    `collector` (T-0748) names the `frob.perf._collectors` adapter this
    runner's invocation should be profiled through -- `"perf"`, `"v8"`,
    `"jfr"`, or `""` (the default) for no hot-graph collection at all;
    empty is always valid since collection is opt-in per runner."""

    model_config = ConfigDict(frozen=True)

    language: str
    command: tuple[str, ...]
    all_command: tuple[str, ...]
    cwd: str = "."
    timeout_s: float = 900.0
    collector: str = ""


# frob:doc docs/modules/testing.md#data-models
class NativeSpec(BaseModel):
    """One `[[native]]` entry: a compiled extension module the test suite
    `importorskip`-gates on, and how to build it. Declaring it lets
    collection fingerprint the module's build state (so a rebuild
    invalidates the cache) and lets a missing-native gate name the real
    remedy instead of a stale collection (T-0333)."""

    model_config = ConfigDict(frozen=True)

    # python import name (e.g. "strata_core"), NOT a file path -- resolution
    # is via importlib.util.find_spec so it works identically whether the
    # artifact was produced by maturin/pyo3 (rust) or setuptools/pybind11/
    # scikit-build (c/c++): the fingerprint hashes the compiled OUTPUT.
    name: str
    build_cmd: str
    language: str = ""


# frob:doc docs/modules/testing.md#data-models
class SelectConfig(BaseModel):
    """Selection knobs: the unbound-file fallback mode."""

    model_config = ConfigDict(frozen=True)

    fallback: str = "package"


# frob:doc docs/modules/testing.md#data-models
class SelectionReport(BaseModel):
    """The pure result of `select_tests`: what was touched and what runs."""

    model_config = ConfigDict(frozen=True)

    touched: tuple[str, ...]
    selected: Mapping[str, tuple[str, ...]]
    ripple: tuple[str, ...]
    unbound: tuple[str, ...]
    fallback: str


# frob:doc docs/modules/testing.md#data-models
class RunnerOutcome(BaseModel):
    """One runner's completed invocation: argv, exit code, bounded output."""

    model_config = ConfigDict(frozen=True)

    language: str
    argv: tuple[str, ...]
    exit_code: int
    duration_s: float
    stdout_tail: str
    stderr_tail: str


# frob:doc docs/modules/testing.md#data-models
class TestRunReport(BaseModel):
    """Every runner outcome for one `run_selected` call, plus the selection it ran."""

    __test__: bool = False

    model_config = ConfigDict(frozen=True)

    selection: SelectionReport
    outcomes: tuple[RunnerOutcome, ...]
    ok: bool


# frob:doc docs/modules/testing.md#data-models
class CollectedTests(BaseModel):
    """The set of pytest node ids collected by `collect_python_tests`, plus
    any declared native extensions that are NOT currently built (T-0333):
    an unbuilt native `importorskip`-skips its tests, so they never enter
    `node_ids` -- `missing_natives` lets COV003 name the real remedy (build
    the extension) instead of blaming the evidence id."""

    model_config = ConfigDict(frozen=True)

    node_ids: frozenset[str]
    missing_natives: tuple[NativeSpec, ...] = ()


__all__ = [
    "CollectedTests",
    "NativeSpec",
    "RunnerOutcome",
    "RunnerSpec",
    "SelectConfig",
    "SelectionReport",
    "TestRunReport",
]
