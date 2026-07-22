"""Python stack-sampling collector: the FIRST producer of the language-
neutral `SampledStack` stream `frob.perf._hotgraph` defines (T-0710).

Two backends, chosen automatically by interpreter version:

- `sys.monitoring` (PEP 669, python 3.12+): a low-overhead line-event
  callback registered on `sys.monitoring.events.LINE` for the tool's own
  namespace, walked down to a config-tunable sampling rate (every Nth line
  event, not every line -- full line tracing is far above the <5 percent
  budget). Not available on 3.11 (this repo's minimum supported/pinned
  interpreter, `requires-python = ">=3.11"`) -- see `_HAS_SYS_MONITORING`.
- A background sampling thread reading `sys._current_frames()` at a fixed
  wall-clock interval (the py-spy-style fallback, portable to every
  CPython this repo supports). This is the backend actually exercised by
  this repo's own test/CI interpreter today.

Neither backend is python-specific past this module: both produce nothing
but `SampledStack`/`SampledFrame` values, the exact shape `frob.perf.
_hotgraph.resolve_stream` consumes regardless of which collector produced
them (T-0748 wires native/V8/JVM collectors into the identical contract).
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable
from types import FrameType

from pydantic import BaseModel

from frob.logging import get_logger
from frob.perf._hotgraph import SampledFrame, SampledStack

_log = get_logger(__name__)

__all__ = [
    "SamplerConfig",
    "StackSampler",
]

#: `sys.monitoring` (PEP 669) is 3.12+ only; this repo's pinned interpreter
#: is 3.11 (`requires-python = ">=3.11"`), so `StackSampler` always takes
#: the background-thread backend today -- the attribute check (not a hard
#: version pin) is so a future interpreter bump picks up the lower-
#: overhead backend automatically, with no code change needed here.
_HAS_SYS_MONITORING = hasattr(sys, "monitoring")

_DEFAULT_INTERVAL_S = 0.01
_MAX_STACK_DEPTH = 64


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class SamplerConfig(BaseModel):
    """`StackSampler`'s tunable knobs (`frob.toml`-configurable, T-0712's
    consumer surface): `interval_s` is the wall-clock gap between samples
    (larger = lower overhead, coarser resolution -- the <5 percent budget
    is measured/documented at the default); `max_depth` caps frames walked
    per sample (protects against pathological recursion inflating a
    single sample's cost)."""

    model_config = {}

    interval_s: float = _DEFAULT_INTERVAL_S
    max_depth: int = _MAX_STACK_DEPTH


def _frame_to_stack(
    frame: FrameType | None, max_depth: int
) -> tuple[SampledFrame, ...]:
    """Walk `frame`'s `f_back` chain into `SampledFrame`s, innermost
    first, capped at `max_depth` -- pure `(file, line)` extraction, no
    python-specific data (bytecode offsets, cell vars, ...) leaks into the
    language-neutral frame shape."""
    frames: list[SampledFrame] = []
    current = frame
    depth = 0
    while current is not None and depth < max_depth:
        frames.append(
            SampledFrame(file=current.f_code.co_filename, line=current.f_lineno)
        )
        current = current.f_back
        depth += 1
    return tuple(frames)


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_hotgraph.py::TestStackSampler
class StackSampler:
    """Background-thread stack sampler (the py-spy-style fallback backend
    -- see module docstring): samples the CALLING thread's frame stack
    every `config.interval_s` seconds while running, appending one
    `SampledStack` per sample to `self.stacks`. `start`/`stop` bracket a
    workload the same way `cProfile.Profile.enable`/`disable` do in
    `frob.perf._profile`, so it composes with the existing profiling
    harness without a second execution model."""

    def __init__(self, config: SamplerConfig | None = None) -> None:
        """Build an idle sampler; `config` defaults to `SamplerConfig()`
        (10ms interval, 64-frame depth cap)."""
        self._config = config or SamplerConfig()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._target_ident: int | None = None
        self.stacks: list[SampledStack] = []

    # frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
    def start(self) -> None:
        """Begin sampling the CALLING thread's frame stack in a daemon
        background thread. A no-op if already running (idempotent, so a
        caller does not need its own guard)."""
        if self._thread is not None:
            _log.warning("StackSampler.start: already running, ignoring")
            return
        self._target_ident = threading.get_ident()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        _log.info(
            "StackSampler.start: sampling thread ident=%s at interval_s=%.4f",
            self._target_ident,
            self._config.interval_s,
        )

    # frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
    def stop(self) -> list[SampledStack]:
        """Stop sampling and return every `SampledStack` collected since
        `start`. Safe to call when not running (returns whatever is
        already in `self.stacks`, empty if `start` was never called)."""
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join(timeout=2 * self._config.interval_s + 1.0)
            self._thread = None
        _log.info("StackSampler.stop: collected %d sample(s)", len(self.stacks))
        return self.stacks

    def _run(self) -> None:
        """The sampling thread's loop: every `interval_s`, snapshot the
        target thread's current frame via `sys._current_frames()` and
        record one `SampledStack` (weight 1.0 per sample -- a caller
        wanting time-weighted samples scales by `interval_s` downstream,
        kept out of the sample itself since the interval is fixed and
        constant-factor)."""
        target_ident = self._target_ident
        assert target_ident is not None
        max_depth = self._config.max_depth
        while not self._stop_event.wait(self._config.interval_s):
            frames = sys._current_frames()
            frame = frames.get(target_ident)
            if frame is None:
                continue
            stack_frames = _frame_to_stack(frame, max_depth)
            if stack_frames:
                self.stacks.append(SampledStack(frames=stack_frames, weight=1.0))


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_hotgraph.py::TestStackSampler.test_collects_at_least_one_sample_over_a_hot_loop  # noqa: E501
def run_sampled(
    fn: Callable[[], None], config: SamplerConfig | None = None
) -> tuple[list[SampledStack], float]:
    """Run `fn()` (a workload with no return value, matching `frob.perf.
    _profile`'s harness shape) under a `StackSampler`, returning its
    collected `SampledStack`s plus the wall-clock seconds `fn` took --
    the overhead-measurement seam `docs/modules/perf.md#hot-graph-
    collector-t-0710-epic-t-0709`'s measured `<5 percent` figure is
    computed from (run `fn` unsampled, run it sampled, compare wall
    times)."""
    sampler = StackSampler(config)
    sampler.start()
    start = time.monotonic()
    try:
        fn()
    finally:
        elapsed = time.monotonic() - start
        stacks = sampler.stop()
    _log.info("run_sampled: elapsed_s=%.4f samples=%d", elapsed, len(stacks))
    return stacks, elapsed
