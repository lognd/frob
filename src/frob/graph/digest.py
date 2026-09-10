"""Sha256 digests over `frob.lang` token streams (docs/modules/graph.md, "Digests").

Three independent digests per symbol -- `sig`, `body`, `doc` -- so that a
body-only refactor never invalidates a contract doc, and a signature change
never hides behind an unrelated body edit. Joining is `"\\x00".join` over
the token tuple: tree-sitter leaf tokens never contain NUL, so this is an
unambiguous, deterministic serialization with no escaping needed.

T-4391: a tree-sitter leaf token spanning a multi-line string/docstring
captures its text verbatim from the source file's bytes, embedded line
endings included. Windows checkouts of this repo see CRLF (`core.
autocrlf`); Linux/macOS see LF. Hashing that raw text unnormalized makes
`sig`/`body`/`doc` digests platform-dependent for any symbol whose token
text crosses a line break -- an acked digest computed on LF then reads as
"moved" (DRIFT001) on a CRLF checkout of the IDENTICAL source, and only
there. `_normalize_newlines` collapses `\r\n`/`\r` to `\n` before hashing
so every digest here is line-ending independent.
"""

from __future__ import annotations

import hashlib

from frob.graph._models import Digests
from frob.lang import RawSymbol
from frob.logging import get_logger

_log = get_logger(__name__)

_JOIN = "\x00"


# frob:ticket T-4391
# frob:tests tests/test_graph.py::TestDigests.test_crlf_checkout_does_not_move_digest
def _normalize_newlines(text: str) -> str:
    """Collapse `\\r\\n` and bare `\\r` to `\\n` so a digest over `text` is
    identical whether the source was checked out with CRLF (Windows) or LF
    (Linux/macOS) line endings (T-4391)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


# frob:ticket T-4391
# frob:tests tests/test_graph.py::TestDigests.test_crlf_checkout_does_not_move_digest
def _hash_tokens(tokens: tuple[str, ...]) -> str:
    """Sha256 hex digest of `tokens` joined by NUL (empty tuple hashes fine),
    each token line-ending-normalized first (T-4391) so a multi-line token's
    embedded `\\r\\n`/`\\r` bytes never make the digest platform-dependent."""
    joined = _JOIN.join(_normalize_newlines(t) for t in tokens)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# frob:doc docs/modules/graph.md#digests
# frob:waive COV007 reason="docs/modules/graph.md's Digests section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _digest_sig(symbol: RawSymbol) -> str:
    """Sha256 hex digest of `symbol.sig_tokens`."""
    return _hash_tokens(symbol.sig_tokens)


# frob:doc docs/modules/graph.md#digests
# frob:waive COV007 reason="docs/modules/graph.md's Digests section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _digest_body(symbol: RawSymbol) -> str:
    """Sha256 hex digest of `symbol.body_tokens` (empty for class/const/type)."""
    return _hash_tokens(symbol.body_tokens)


# frob:doc docs/modules/graph.md#digests
# frob:waive COV007 reason="docs/modules/graph.md's Digests section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:ticket T-4391
# frob:tests tests/test_graph.py::TestDigests.test_crlf_checkout_does_not_move_digest
def _digest_doc(symbol: RawSymbol) -> str:
    """Sha256 hex digest of `symbol.doc_text` (already whitespace-collapsed),
    line-ending-normalized first (T-4391) for the same CRLF/LF independence
    as `_hash_tokens`."""
    return hashlib.sha256(
        _normalize_newlines(symbol.doc_text).encode("utf-8")
    ).hexdigest()


# frob:doc docs/modules/graph.md#digests
def compute_digests(symbol: RawSymbol) -> Digests:
    """All three digests for `symbol` in one `Digests` value."""
    digests = Digests(
        sig=_digest_sig(symbol),
        body=_digest_body(symbol),
        doc=_digest_doc(symbol),
    )
    _log.debug(
        "digested %s: sig=%s body=%s doc=%s",
        symbol.qualname,
        digests.sig[:8],
        digests.body[:8],
        digests.doc[:8],
    )
    return digests


__all__ = ["compute_digests", "_digest_body", "_digest_doc", "_digest_sig"]
