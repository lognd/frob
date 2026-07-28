"""The one place that reads a fail-open, best-effort TOML file.

Extracted T-0861: `frob.gates._docblocks`, `frob.perf._redundancy`, and
`frob.perf._sketch_store` each carried their own copy of the identical
"missing/unreadable/malformed file -> `None`, never a crash" shape (a
missing manifest table just means the feature it configures runs with
defaults or contributes nothing, not a gate failure) -- a near-leaf module
(no frob imports) so any future caller with the same fail-open contract
has one home instead of a fourth copy.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStoreConfig.test_missing_frob_toml_returns_defaults  # noqa: E501
def read_toml_lenient(path: Path, *, log_prefix: str) -> dict | None:
    """Best-effort TOML load: `None` on any missing/unreadable/malformed
    `path`, never a crash -- `log_prefix` names the caller in the WARNING
    line so a malformed-file log entry is still traceable to its gate/
    feature (e.g. `"doc004"`, `"perf007"`, `"sketch store"`)."""
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("%s: %s unreadable: %s", log_prefix, path, exc)
        return None
