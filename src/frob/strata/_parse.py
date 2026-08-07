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
except ImportError:  # pragma: no cover - environment-dependent
    # Guarded the same way as frob.lang._walk_strata (T-0133) and
    # frob.strata._facts (T-0134): a standalone tool install without the
    # native extension degrades every parse to a typed Err instead of
    # crashing at import time.
    strata_core = None
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import Module
from ._errors import StrataError

_log = get_logger(__name__)


# frob:doc docs/strata/surface.md#parser
def parse_module(text: str) -> Result[Module, StrataError]:
    """Parse strata surface source text into a validated `Module`.

    WHY: the grammar and its error positions live entirely in the Rust
    parser (charter D3, amended); this function only bridges JSON to
    pydantic and turns a parse failure into a logged, typed error rather
    than a bare exception (fallible operation -> Result, per house rules).
    Also degrades to a typed `StrataError.NativeExtensionUnavailable`
    (rather than crashing) when the `strata_core` native extension is not
    installed at all (T-0134).
    """
    if strata_core is None:
        _log.error("parse_module: strata_core native extension unavailable")
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
