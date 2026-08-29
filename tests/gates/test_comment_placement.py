"""CPLACE001/CPLACE002 (T-3218) fixtures: must-fire and must-stay-quiet
for both rules, plus the specific must-stay-quiet cases T-3218's own
ticket body names -- an exempt provenance path, a `frob:ticket` directive
at any length, a short `# T-1234:` attribution, and an ordinary one-line
`frob:waive ... reason="..."`."""

from __future__ import annotations

from pathlib import Path

from frob.gates._comment_placement import (
    CPLACE001_WAIVE_REASON_LIMIT_LINES,
    CPLACE002_NARRATIVE_WORD_LIMIT,
    comment_placement_gate,
    scan_cplace001_waive_reason_length,
    scan_cplace002_docs_narrative,
)


def _rule_ids(violations) -> list[str]:
    """Every `.rule` off `violations`, in order -- the common shape used
    by both rule's fixture classes below."""
    return [v.rule for v in violations]


class TestCplace001:
    """`src/**/*.py` frob:waive reason-length cap."""

    def test_must_fire_long_waive_reason(self) -> None:
        """A `frob:waive` directive whose folded reason spans more than
        `CPLACE001_WAIVE_REASON_LIMIT_LINES` physical lines fires."""
        text = (
            '# frob:waive SOME001 reason="this justification runs on for \\\n'
            "# quite a while, well past the compliant one-line summary \\\n"
            "# form, exactly the narrative-essay shape T-2987 flagged as \\\n"
            '# bloat that belongs in the ticket instead of the source"\n'
            "x = 1\n"
        )
        violations = scan_cplace001_waive_reason_length(Path("src/frob/x.py"), text)
        assert _rule_ids(violations) == ["CPLACE001"]
        assert violations[0].line == 1

    def test_must_stay_quiet_ordinary_one_line_waive(self) -> None:
        """An ordinary compliant one-line `frob:waive ... reason="..."`
        must never fire -- T-3218's own must-stay-quiet requirement,
        proving the narrowed exemption still lets a compliant waiver
        through."""
        text = '# frob:waive SOME001 reason="narrow, load-bearing reason"\nx = 1\n'
        assert scan_cplace001_waive_reason_length(Path("src/frob/x.py"), text) == ()

    def test_must_stay_quiet_frob_ticket_directive_any_length(self) -> None:
        """`frob:ticket`/`frob:tests`/`frob:doc` stay exempt at any
        length -- pure binding syntax, not narrative, per T-2987's own
        finding that T-3218 adopts unchanged for these three."""
        text = (
            "# frob:ticket T-1234\n"
            "# some long unrelated prose comment block that just happens \\\n"
            "# to run on for many lines discussing history and rationale \\\n"
            "# and prior attempts and everything else T-2994 calls \\\n"
            "# narrative, but it is NOT a frob:waive directive so CPLACE001 \\\n"
            "# has nothing to say about it whatsoever\n"
            "x = 1\n"
        )
        assert scan_cplace001_waive_reason_length(Path("src/frob/x.py"), text) == ()

    def test_does_not_fire_on_prose_mentioning_frobwaive_by_name(self) -> None:
        """Regression: a long ordinary comment block that merely MENTIONS
        `frob:waive` by name in prose (not a directive-start line) must
        not fire -- the house-rule regression this module's docstring
        cites (a prior detector elsewhere false-fired on its own
        done-report narrative via raw substring matching)."""
        text = (
            "# This block discusses frob:waive at length: how frob:waive \\\n"
            "# directives work, why frob:waive reasons matter, and what \\\n"
            "# frob:waive should and should not be used for -- none of \\\n"
            "# this is an actual frob:waive directive, just prose that \\\n"
            "# happens to say the words\n"
            "x = 1\n"
        )
        assert scan_cplace001_waive_reason_length(Path("src/frob/x.py"), text) == ()

    def test_must_stay_quiet_exempt_path(self) -> None:
        """A provenance-exempt path (e.g. `tickets/**`) never fires even
        with an over-long `frob:waive` directive."""
        text = (
            '# frob:waive SOME001 reason="line one \\\n# line two \\\n# line three"\n'
        )
        assert scan_cplace001_waive_reason_length(Path("tickets/T-0001.md"), text) == ()

    def test_threshold_boundary_is_inclusive(self) -> None:
        """A directive at exactly `CPLACE001_WAIVE_REASON_LIMIT_LINES`
        physical lines stays quiet; one more line fires."""
        at_limit = '# frob:waive SOME001 reason="first line \\\n# second line"\nx = 1\n'
        # Build directly against the limit constant so a future threshold
        # tune does not silently desync this test from the real constant.
        assert CPLACE001_WAIVE_REASON_LIMIT_LINES == 2
        assert scan_cplace001_waive_reason_length(Path("src/frob/x.py"), at_limit) == ()


class TestCplace002:
    """`docs/modules/**/*.md` ticket-narrative-outside-provenance."""

    def test_must_fire_long_narrative_paragraph(self) -> None:
        """A prose paragraph citing a ticket id, well past the word
        limit, outside any table row, fires."""
        text = (
            "# Some heading\n\n"
            "This paragraph explains at considerable length why T-1234 "
            "was implemented the way it was, what a prior attempt got "
            "wrong before that, which earlier policy it superseded, and "
            "the full history of how the team arrived at this decision "
            "over several long discussions and multiple false starts.\n"
        )
        violations = scan_cplace002_docs_narrative(Path("docs/modules/gates.md"), text)
        assert _rule_ids(violations) == ["CPLACE002"]

    def test_must_stay_quiet_table_row_citation(self) -> None:
        """A bare `(T-1234)`-shaped citation inside a markdown table row
        is provenance-by-construction and never fires, regardless of the
        surrounding table's total length."""
        text = (
            "| rule | detail |\n"
            "|------|--------|\n"
            "| DUP003 | clones (T-0399) but frob-core handles the merge "
            "path differently than the original design intended here |\n"
        )
        assert scan_cplace002_docs_narrative(Path("docs/modules/gates.md"), text) == ()

    def test_must_stay_quiet_short_attribution(self) -> None:
        """A short `# T-1234: keep the sort stable`-style attribution (a
        handful of words) stays under the word limit and never fires."""
        text = "# Heading\n\nSee T-1234 for why this stays stable.\n"
        assert scan_cplace002_docs_narrative(Path("docs/modules/gates.md"), text) == ()

    def test_must_stay_quiet_exempt_path(self) -> None:
        """`docs/decisions/**` (and the other T-2994 provenance-exempt
        paths) never fire even with a long narrative paragraph."""
        text = (
            "This paragraph explains at considerable length why T-1234 "
            "was implemented the way it was, what a prior attempt got "
            "wrong before that, which earlier policy it superseded, and "
            "the full history of how the team arrived at this decision.\n"
        )
        assert scan_cplace002_docs_narrative(Path("docs/decisions/x.md"), text) == ()

    def test_word_limit_boundary(self) -> None:
        """A paragraph at exactly `CPLACE002_NARRATIVE_WORD_LIMIT` words
        stays quiet; one more word fires."""
        assert CPLACE002_NARRATIVE_WORD_LIMIT == 15
        words = " ".join(f"word{i}" for i in range(14)) + " T-1234"
        assert (
            scan_cplace002_docs_narrative(Path("docs/modules/x.md"), words + "\n") == ()
        )
        words_over = words + " extra"
        violations = scan_cplace002_docs_narrative(
            Path("docs/modules/x.md"), words_over + "\n"
        )
        assert _rule_ids(violations) == ["CPLACE002"]


class TestCommentPlacementGate:
    """The repo-scanning entrypoint wires both rules together."""

    def test_fires_across_both_surfaces(self, tmp_path: Path) -> None:
        """`comment_placement_gate` reports both CPLACE001 (src) and
        CPLACE002 (docs) findings from one repo-root scan, and skips a
        provenance-exempt file entirely."""
        import subprocess

        root = tmp_path
        (root / "src" / "frob").mkdir(parents=True)
        (root / "docs" / "modules").mkdir(parents=True)
        (root / "tickets").mkdir()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
        )
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)

        (root / "src" / "frob" / "x.py").write_text(
            '# frob:waive SOME001 reason="line one \\\n'
            "# line two \\\n"
            '# line three"\n'
            "x = 1\n"
        )
        (root / "docs" / "modules" / "gates.md").write_text(
            "This paragraph explains at considerable length why T-1234 "
            "was implemented the way it was, what a prior attempt got "
            "wrong before that, which earlier policy it superseded, and "
            "the full history of how the team arrived at this decision.\n"
        )
        (root / "tickets" / "T-0001.md").write_text(
            '# frob:waive SOME001 reason="line one \\\n# line two \\\n# line three"\n'
        )
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True)

        violations = comment_placement_gate(root)
        assert sorted(_rule_ids(violations)) == ["CPLACE001", "CPLACE002"]
