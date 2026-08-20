"""Source-to-AST entry point for strata (docs/strata/surface.md#parser).

Calls the Rust lexer/parser (`strata_core.parse_source`), which never
raises and never panics -- every malformed input comes back as `err`
JSON with a line/col/message. This module's only job is turning that JSON
into either a validated `Module` or a logged `StrataError.ParseFailed`.
"""

from __future__ import annotations

import importlib
import json
from types import ModuleType

try:
    strata_core: ModuleType | None = importlib.import_module("strata_core")
except ImportError as _exc:  # pragma: no cover - environment-dependent
    # Guarded the same way as frob.lang._walk_strata (T-0133) and
    # frob.strata._facts (T-0134): a standalone tool install without the
    # native extension degrades every parse to a typed Err instead of
    # crashing at import time. T-2707: the caught exception is captured
    # (single tuple-assignment statement, so ruff's E402 try/except-
    # guarded-import exemption still recognizes this as an import guard)
    # rather than discarded -- a symbol/ABI mismatch or a failing
    # SECONDARY import inside `strata_core` also raises `ImportError`
    # and was previously indistinguishable from a genuinely absent
    # extension.
    strata_core, _import_error = None, f"{type(_exc).__name__}: {_exc}"
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import Module
from ._errors import StrataError

#: T-2707: `_import_error` is only ever bound above, inside the `except`
#: clause -- on a successful import it is never assigned at all, so this
#: default (placed AFTER every import to avoid re-triggering ruff's E402
#: try/except-guarded-import exemption check above) fills it in for the
#: success path only.
if "_import_error" not in globals():
    _import_error: str | None = None

_log = get_logger(__name__)


# frob:doc docs/strata/surface.md#parser
# frob:tests tests/unit/strata/test_parse.py::TestStrataCoreImportError.test_none_when_import_succeeded  # noqa: E501
# frob:tests tests/unit/strata/test_parse.py::TestStrataCoreImportError.test_names_the_real_exception_not_the_generic_guess  # noqa: E501
def strata_core_import_error() -> str | None:
    """The real exception text from this module's guarded `strata_core`
    import, or `None` when the import succeeded. T-2707: callers that
    report `StrataError.NativeExtensionUnavailable` to a human (SYS004's
    message, this module's own log line) use this to name the ACTUAL
    cause instead of only ever guessing "not installed" -- the fixed
    guess previously misdirected a reporter whose `strata_core` was
    installed but failing to import for an unrelated reason."""
    return _import_error


# frob:doc docs/strata/surface.md#parser
def parse_module(text: str) -> Result[Module, StrataError]:
    """Parse strata surface source text into a validated `Module`.

    WHY: the grammar and its error positions live entirely in the Rust
    parser (charter D3, amended); this function only bridges JSON to
    pydantic and turns a parse failure into a logged, typed error rather
    than a bare exception (fallible operation -> Result, per house rules).
    Also degrades to a typed `StrataError.NativeExtensionUnavailable`
    (rather than crashing) when the `strata_core` native extension is not
    installed at all (T-0134). T-2707: the log line now names the real
    caught `ImportError` (`strata_core_import_error()`) alongside the
    typed error, rather than only the fixed not-installed guess.
    """
    if strata_core is None:
        _log.error(
            "parse_module: strata_core native extension unavailable (%s)",
            _import_error or "no import error captured",
        )
        return Err(StrataError.NativeExtensionUnavailable)
    raw = strata_core.parse_source(text)
    payload = json.loads(raw)
    if "err" in payload:
        detail = payload["err"]
        _log.error(
            "strata parse failed at %s:%s: %s",
            detail.get("line"),
            detail.get("col"),
            detail.get("message"),
        )
        return Err(StrataError.ParseFailed)
    _log.debug("strata parse ok: module %r", payload["ok"].get("name"))
    return Ok(Module.model_validate(payload["ok"]))
