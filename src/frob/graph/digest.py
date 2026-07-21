"""Sha256 digests over `frob.lang` token streams (docs/modules/graph.md, "Digests").

Three independent digests per symbol -- `sig`, `body`, `doc` -- so that a
body-only refactor never invalidates a contract doc, and a signature change
never hides behind an unrelated body edit. Joining is `"\\x00".join` over
the token tuple: tree-sitter leaf tokens never contain NUL, so this is an
unambiguous, deterministic serialization with no escaping needed.
"""

from __future__ import annotations

import hashlib

from frob.graph._models import Digests
from frob.lang import RawSymbol
from frob.logging import get_logger

_log = get_logger(__name__)

_JOIN = "\x00"


def _hash_tokens(tokens: tuple[str, ...]) -> str:
    """Sha256 hex digest of `tokens` joined by NUL (empty tuple hashes fine)."""
    return hashlib.sha256(_JOIN.join(tokens).encode("utf-8")).hexdigest()


# frob:doc docs/modules/graph.md#digests
# frob:waive COV007 reason="docs/modules/graph.md's Digests section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
def _digest_sig(symbol: RawSymbol) -> str:
    """Sha256 hex digest of `symbol.sig_tokens`."""
    return _hash_tokens(symbol.sig_tokens)


# frob:doc docs/modules/graph.md#digests
# frob:waive COV007 reason="docs/modules/graph.md's Digests section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
def _digest_body(symbol: RawSymbol) -> str:
    """Sha256 hex digest of `symbol.body_tokens` (empty for class/const/type)."""
    return _hash_tokens(symbol.body_tokens)


# frob:doc docs/modules/graph.md#digests
# frob:waive COV007 reason="docs/modules/graph.md's Digests section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
def _digest_doc(symbol: RawSymbol) -> str:
    """Sha256 hex digest of `symbol.doc_text` (already whitespace-collapsed)."""
    return hashlib.sha256(symbol.doc_text.encode("utf-8")).hexdigest()


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
