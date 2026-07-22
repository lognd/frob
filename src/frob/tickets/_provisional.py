"""Provisional (draft) ticket ids -- the T-0162 collision-proofing mechanism
(docs/modules/tickets.md#decision-record-t-0162).

`frob ticket new` off the repo's default branch mints a `T-draft-<hex>` id
instead of the next sequential `T-####`. Final sequential ids are only ever
minted against the default branch's merged view (`finalize_draft` in
`frob.tickets`), so two checkouts filing independently can never converge on
the same final id -- the id space each worktree/branch draws sequential ids
from is disjoint by construction until finalize time, and finalize itself
only ever runs against one ledger view at a time.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/tickets/_provisional.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import secrets
from pathlib import Path

from frob.gitio import current_branch, run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/tickets.md#provisional-ids
DRAFT_PREFIX = "T-draft-"
_DRAFT_HEX_LEN = 8


# frob:doc docs/modules/tickets.md#provisional-ids
def is_draft_id(ticket_id: str) -> bool:
    """Whether `ticket_id` is a provisional draft id, never a final T-####."""
    return ticket_id.startswith(DRAFT_PREFIX)


# frob:doc docs/modules/tickets.md#provisional-ids
def mint_draft_id() -> str:
    """A fresh content-nonce draft id: `T-draft-<8 hex chars>` -- collision
    probability across two independently-filing checkouts is astronomically
    low (1/2^32 per pair), and the ledger's own duplicate-id load check
    (`_load_merged`/`_parse_ledger`) still catches the freak case loudly."""
    return f"{DRAFT_PREFIX}{secrets.token_hex(_DRAFT_HEX_LEN // 2)}"


def _default_branch(root: Path) -> str:
    """Best-effort default branch name: the remote's symbolic HEAD if known,
    else whichever of main/master exists locally, else 'main' -- a repo with
    neither a remote nor a main/master branch has no meaningful "default" to
    protect, so 'main' is a harmless fallback rather than a hard failure."""
    symbolic = run_argv(
        ["git", "-C", str(root), "symbolic-ref", "refs/remotes/origin/HEAD"]
    )
    if symbolic.is_ok and symbolic.danger_ok.returncode == 0:
        ref = symbolic.danger_ok.stdout.strip()
        if ref:
            return ref.rsplit("/", 1)[-1]
    for candidate in ("main", "master"):
        check = run_argv(
            [
                "git",
                "-C",
                str(root),
                "show-ref",
                "--verify",
                "--quiet",
                f"refs/heads/{candidate}",
            ]
        )
        if check.is_ok and check.danger_ok.returncode == 0:
            return candidate
    return "main"


# frob:doc docs/modules/tickets.md#provisional-ids
def on_default_branch(root: Path) -> bool:
    """Whether `root`'s checkout is currently on the repo's default branch.

    Any ambiguity (no git repo, detached HEAD, git unavailable) resolves to
    True -- allocation then falls back to the old sequential behavior
    unchanged, so a non-git or CI-detached checkout never surprises anyone
    with unexpected draft ids. Drafts are minted only when a NON-default
    branch is positively identified.
    """
    branch = current_branch(root)
    if branch.is_err:
        _log.debug(
            "tickets: on_default_branch(%s): no git branch, assuming default", root
        )
        return True
    name = branch.danger_ok
    if not name or name == "HEAD":
        _log.debug(
            "tickets: on_default_branch(%s): detached HEAD, assuming default", root
        )
        return True
    return name == _default_branch(root)
