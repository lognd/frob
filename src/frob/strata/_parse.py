"""Source-to-AST entry point for strata (docs/strata/surface.md#parser).

Calls the Rust lexer/parser (`strata_core.parse_source`), which never
raises and never panics -- every malformed input comes back as `err`
JSON with a line/col/message. This module's only job is turning that JSON
into either a validated `Module` or a logged `StrataError.ParseFailed`.
"""

from __future__ import annotations

import json

import strata_core
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
    """
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
