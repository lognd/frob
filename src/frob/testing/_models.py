"""Data shapes for touched-set test selection and execution
(docs/modules/testing.md)."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict


# frob:doc docs/modules/testing.md#data-models
class RunnerSpec(BaseModel):
    """One `[[test.runner]]` entry: how to invoke a language's test runner."""

    model_config = ConfigDict(frozen=True)

    language: str
    command: tuple[str, ...]
    all_command: tuple[str, ...]
    cwd: str = "."
    timeout_s: float = 900.0


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
    """The set of pytest node ids collected by `collect_python_tests`."""

    model_config = ConfigDict(frozen=True)

    node_ids: frozenset[str]


__all__ = [
    "CollectedTests",
    "RunnerOutcome",
    "RunnerSpec",
    "SelectConfig",
    "SelectionReport",
    "TestRunReport",
]
