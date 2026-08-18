"""T-2299: DOC012 promoted WARN -> ERROR now that its disclosed T-1783
backlog (24 subcommands) measures zero (children T-2315/T-2316 burned it
down). This file is deliberately separate from tests/test_gates.py's own
TestDoc012CommandSectionGate -- that file carried a LIVE cross-worktree
lease (T-2314) at the time this promotion landed, so the must-fail
fixture proving the new severity lives here instead, disjoint from that
lease. Reuses the same synthetic two-command fixture parser
(`tests.test_gates:_doc012_fake_parser_factory`) and fake-config shape
`TestDoc012CommandSectionGate` already established, so both files check
the identical mechanism without duplicating the fixture factory itself.

Follow-up filed and parented to T-2299 (see tickets/ for the current id
-- filed as a draft that renumbers at land, so not hardcoded here): fold
this file's must-fail fixture back into
tests/test_gates.py::TestDoc012CommandSectionGate once T-2314 releases
its tests/test_gates.py lease, and update that class's own
test_undocumented_subcommand_fails assertion (currently asserts
Severity.WARN, now stale) to Severity.ERROR in the same pass.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates import Severity
from frob.gates._docblocks import doc012_gate

_DOC012_PROMOTION_FAKE_CONFIG = (
    '[[docblocks.commands]]\nprog = "acme"\n'
    'parser = "tests.test_gates:_doc012_fake_parser_factory"\n'
)


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs -- local copy of
    tests/test_gates.py's own `_write` helper, kept small enough that
    duplicating it here (rather than importing across a leased file) is
    cheaper than the cross-file coupling would be."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _git_init(root: Path) -> None:
    """Minimal git init for a DOC012 gate fixture tree -- local copy of
    tests/test_gates.py's own `_git_init` helper, same reasoning as
    `_write` above."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)


class TestDoc012PromotedToError:
    """T-2299: the must-fail fixture proving DOC012's severity is
    actually ERROR now, not just documented as promoted -- an
    undocumented subcommand must fail `frob check`, not merely warn."""

    def test_undocumented_subcommand_is_now_error(self, tmp_path: Path) -> None:
        """A real gap (T-2299): before promotion this same fixture only
        ever produced a WARN finding (see the sibling, pre-promotion
        assertion this test intentionally diverges from) -- prove the
        promotion actually changed severity, not just prose."""
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", _DOC012_PROMOTION_FAKE_CONFIG)
        _write(tmp_path, "docs/commands/widget.md", "# acme widget\n\nDoes widget things.\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        violations = doc012_gate(tmp_path)

        gadget = [v for v in violations if v.rule == "DOC012" and "gadget" in v.message]
        assert gadget, "expected a DOC012 finding naming the undocumented `gadget` subcommand"
        assert gadget[0].severity == Severity.ERROR

    def test_documented_subcommand_still_passes(self, tmp_path: Path) -> None:
        """The promotion changes severity only -- a properly documented
        subcommand still reports zero DOC012 findings, same as before."""
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", _DOC012_PROMOTION_FAKE_CONFIG)
        _write(tmp_path, "docs/commands/widget.md", "# acme widget\n\nDoes widget things.\n")
        _write(
            tmp_path,
            "docs/modules/gadget.md",
            "## `acme gadget` (CLI verb, T-9999)\n\nDoes gadget things.\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        violations = doc012_gate(tmp_path)

        assert [v for v in violations if v.rule == "DOC012"] == []
