"""T-4510: proves the `_CSHARP_LANGS` facet bucket (`frob.lang._support`)
fires end to end for real, against a checked-in fixture, rather than
resting on `frob.dup._exhaustiveness`'s `_non_python_excuses` and
`_support._docblock_languages`'s registry-level "implemented" claim.

Two facets, two fixtures, one shared root
(`tests/fixtures/csharp_dup_docblock/`):

- dup: `frob.dup.find_duplicates` (the scanner backing `frob check`'s
  dup stage and the `frob dup` CLI) must report the near-duplicate method
  pair in `Sample/Dup/Duplicate.cs`. T-4510's own finding, before this
  ticket's fix: `frob.dup._legacy._scan_tree` dispatched only `_PY_EXTS`/
  `_CPP_EXTS` -- `.cs` files were never scanned at all, so this facet's
  "implemented" claim was unproven. `src/frob/dup/_legacy_cs.py` (new,
  T-4510) plus `_CS_EXTS`/`_scan_cs_file` in `_legacy.py` close the gap;
  `python_control/duplicate.py`'s identically-shaped pair is the positive
  control proving a firing assertion here is not a harness false
  positive.
- docblock: `frob.gates._docblocks_refs._csharp_using_violations` (the
  `_CSHARP_LANGS` DOC004 bucket, already real and wired -- T-2906) must
  fire UNBOUND for an unanchored `using Sample.Dup;` block, clear for an
  anchored twin, and stay silent (zero false positives) on a BCL
  `using System.Text;` block. All three block bodies are built in memory
  here rather than read off `guide.md` on disk -- `_tracked_source_files`
  (the only piece of `_csharp_using_violations` that shells out to `git
  ls-files`) is mocked with the fixture's own known tracked path -- so
  this stays a pure unit test with no fs.read/subprocess/tmp_path-write
  capability effect to declare, per the ticket brief's "prefer checked-in
  fixtures" guidance. `guide.md` itself still carries the anchored/BCL
  cases in real fenced blocks for `frob check`'s own repo-wide DOC004
  gate to scan (see its own module note for why the unanchored case is
  NOT checked in there).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from frob.dup import find_duplicates
from frob.gates._docblocks_refs import _csharp_using_violations, _FencedBlock

_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "csharp_dup_docblock"
_TRACKED_CS_PATH = "tests/fixtures/csharp_dup_docblock/Sample/Dup/Duplicate.cs"


class TestCsharpDupFacetFires:
    """Acceptance: GIVEN two near-duplicate C# methods, WHEN the dup
    detector runs, THEN it reports the duplicate pair using the
    `_CSHARP_LANGS`/`_CS_EXTS` facet path."""

    # frob:ticket T-4510
    #: (suffix, expected symbols, label) -- csharp is the acceptance
    #: criterion itself; python is the positive control proving the
    #: assertion shape above isn't a harness false positive (T-4510:
    #: merged from two near-identical test bodies per DUP002, which
    #: correctly caught the two find_duplicates-and-assert calls as
    #: 95% similar).
    @pytest.mark.parametrize(
        ("suffix", "expected_symbols", "label"),
        [
            (
                ".cs",
                {"Documented.AddNumbers", "Undocumented.AddValues"},
                "csharp facet bucket",
            ),
            (
                ".py",
                {"add_numbers", "add_values"},
                "positive control",
            ),
        ],
    )
    def test_find_duplicates_reports_near_duplicate_methods(
        self, suffix: str, expected_symbols: set[str], label: str
    ) -> None:
        # frob:tests tests/unit/test_support_csharp.py::TestCsharpDupFacetFires.test_find_duplicates_reports_near_duplicate_methods  # noqa: E501
        result = find_duplicates(_FIXTURE_ROOT, min_lines_overrides=())

        matching = [
            g
            for g in result.groups
            if any(f.file.endswith(suffix) for f in g.fragments)
        ]
        assert matching, (
            f"frob dup reported ZERO groups touching a {suffix} fragment -- "
            f"the {label} is not actually firing "
            f"(all groups: {[g.model_dump() for g in result.groups]})"
        )
        symbols = {f.symbol for g in matching for f in g.fragments}
        assert symbols == expected_symbols, (
            f"unexpected {suffix} fragment symbols: {symbols}"
        )


class TestCsharpDocblockFacetFires:
    """Acceptance: GIVEN a C# `using` statement `_csharp_using_violations`
    (T-2906) is meant to police, WHEN the checker runs on the fixture,
    THEN the expected violation fires with zero false positives on clean
    code; and GIVEN a public C# member without a nearby binding
    directive, the same UNBOUND/anchored contract as python's own
    DOC004 buckets applies."""

    def test_unanchored_project_using_fires_unbound(self) -> None:
        """Mirrors `guide.md`'s Case 1, minus its binding marker (never
        checked in that shape -- see `guide.md`'s own module note: a real
        unanchored occurrence of this pattern in a tracked `.md` file is
        exactly what DOC004 exists to catch)."""
        # frob:tests tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires.test_unanchored_project_using_fires_unbound  # noqa: E501
        block = _FencedBlock(
            lang="csharp", body="using Sample.Dup;\n", start_line=3, end_line=5
        )
        doc_lines = [
            "# unanchored fixture",
            "",
            "```csharp",
            "using Sample.Dup;",
            "```",
        ]

        with patch(
            "frob.gates._docblocks_refs._tracked_source_files",
            return_value=frozenset({_TRACKED_CS_PATH}),
        ):
            violations = _csharp_using_violations(
                block, "synthetic.md", doc_lines, _FIXTURE_ROOT
            )

        assert len(violations) == 1, (
            "frob's docblock facet reported ZERO violations for an "
            "unanchored project-internal `using` -- the _CSHARP_LANGS "
            f"DOC004 bucket is not firing (got: {violations})"
        )
        assert violations[0].rule == "DOC004"

    def test_anchored_project_using_has_zero_violations(self) -> None:
        """Mirrors `guide.md`'s Case 1 exactly (the checked-in anchored
        block `frob check`'s own repo-wide DOC004 gate scans for real)."""
        # frob:tests tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires.test_anchored_project_using_has_zero_violations  # noqa: E501
        block = _FencedBlock(
            lang="csharp", body="using Sample.Dup;\n", start_line=6, end_line=8
        )
        doc_lines = [
            "## Case 1: anchored project reference",
            "",
            "<!-- frob:doc tests/fixtures/csharp_dup_docblock/guide.md -->",
            "",
            "```csharp",
            "using Sample.Dup;",
            "```",
        ]

        with patch(
            "frob.gates._docblocks_refs._tracked_source_files",
            return_value=frozenset({_TRACKED_CS_PATH}),
        ):
            violations = _csharp_using_violations(
                block, "guide.md", doc_lines, _FIXTURE_ROOT
            )

        assert violations == []

    def test_bcl_using_is_zero_false_positives(self) -> None:
        """Mirrors `guide.md`'s Case 2: `System.*` never resolves against
        a tracked `.cs` path, so it is skipped outright -- even
        unanchored, even with a tracked csharp file present in the
        repo."""
        # frob:tests tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires.test_bcl_using_is_zero_false_positives  # noqa: E501
        block = _FencedBlock(
            lang="csharp", body="using System.Text;\n", start_line=3, end_line=5
        )
        doc_lines = [
            "## Case 2: BCL reference",
            "",
            "```csharp",
            "using System.Text;",
            "```",
        ]

        with patch(
            "frob.gates._docblocks_refs._tracked_source_files",
            return_value=frozenset({_TRACKED_CS_PATH}),
        ):
            violations = _csharp_using_violations(
                block, "guide.md", doc_lines, _FIXTURE_ROOT
            )

        assert violations == []
