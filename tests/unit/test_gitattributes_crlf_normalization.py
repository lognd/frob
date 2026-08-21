"""T-2611: regression lock for repo-wide CRLF normalization.

`core.autocrlf=true` (a Windows-checkout setting) is present on this
Linux/WSL clone with no repo-wide `.gitattributes` normalization, so git
silently writes CRLF into the working-tree copy of every tracked text
file with no explicit `text`/`eol` attribute of its own -- confirmed on
60 of 60 sampled tracked `src/frob/*.py` files. Any measurement that
reads the working tree byte-for-byte (an `awk`/`wc`/hand-rolled length
or diff check) silently counts the trailing CR as content; this exact
defect turned zero real E501 violations into four apparent ones in one
session (T-2596).

These tests pin the fix at the `.gitattributes` declaration level (via
`git check-attr`, which reads attributes without requiring an actual
fresh checkout) rather than asserting on this worktree's own on-disk
bytes -- a worktree that existed before this ticket landed keeps its
already-checked-out CRLF copies until it is next re-checked-out, so an
on-disk assertion would be a property of THIS worktree's history, not of
the fix. `git check-attr` is what a fresh `git worktree add`/`git clone`
checkout actually consults, so it is the right level to lock.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: representative tracked source paths sampled across the repo -- not
#: exhaustive (T-2611's own audit sampled 60/60 src/frob/*.py files and
#: found CR in all of them), just enough breadth that a narrow/typo'd
#: gitattributes pattern would still be caught.
_SAMPLE_PATHS: tuple[str, ...] = (
    "src/frob/app/ticket_runner/_ledger_mirror.py",
    "src/frob/scaffold/project.py",
    "src/frob/tickets/_reconcile.py",
    "src/frob/__main__.py",
    "tests/unit/test_gitattributes_crlf_normalization.py",
)


def _check_attr(attr: str, path: str) -> str:
    """The value git currently assigns `attr` for `path` per `.gitattributes`
    (reads the working tree's own attribute file, not a checked-out
    smudge result) -- `"unspecified"` if no rule matches."""
    result = subprocess.run(
        ["git", "check-attr", attr, "--", path],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    # format: "<path>: <attr>: <value>"
    return result.stdout.strip().rsplit(":", 1)[-1].strip()


class TestGitattributesEolNormalization:
    """`git check-attr eol` reports `lf` for tracked source, repo-wide."""

    def test_sampled_source_files_are_pinned_to_lf(self) -> None:
        """Every sampled tracked source file resolves `eol=lf` via `.gitattributes`."""
        not_lf = [path for path in _SAMPLE_PATHS if _check_attr("eol", path) != "lf"]
        assert not not_lf, (
            f"these paths do not resolve eol=lf (still exposed to "
            f"core.autocrlf CRLF corruption): {not_lf}"
        )

    def test_attachment_binary_pin_still_holds(self) -> None:
        """T-1433/T-2239's `-text` attachment pin is untouched by the new default."""
        assert _check_attr("text", "tickets/T-0001/attachments/x.md") == "unset"

    def test_rapid_debt_lease_pin_still_holds(self) -> None:
        """T-2586's `rapid-debt.jsonl` pin still resolves `eol=lf`."""
        assert _check_attr("eol", "rapid-debt.jsonl") == "lf"
        assert _check_attr("text", "rapid-debt.jsonl") == "set"
