"""Property tests for `frob:invariant`'s T-0757 `no-import=`/`establishes=`
obligation attrs (docs/modules/gates.md#inv007-inv008-t-0757).

T-0757's own DISCIPLINE note demands Hypothesis-backed proof, over the REAL
parser, that a grammar change does not silently reshape how an EXISTING
directive parses (the T-0987 continuation-discriminator / T-0991
boundary-space lesson this ticket was told to respect): `TestBareInvariant
Unaffected` generates arbitrary `INV-###` ids and confirms a bare
`frob:invariant INV-###` (no obligation attrs -- every invariant anchor
that existed before this ticket) still parses to the exact same
attrs-empty `Edge` shape. `TestNoImportAttr`/`TestEstablishesAttr` cover
the two new attrs' own shape rules with generated inputs, complementing
`tests/unit/graph/test_dsl.py`'s hand-picked cases.
"""

from __future__ import annotations

import string
import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from frob.graph.dsl import parse_directives
from frob.lang import parse_file


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs, and return the path."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _parse_src(src: str):  # noqa: ANN201
    """Parse `src` as a fresh, self-contained temp file's `a.py` -- used by
    every `@given`-driven test here instead of the `tmp_path` fixture,
    since a function-scoped fixture is not reset between Hypothesis-
    generated examples (its own `FailedHealthCheck`); a fresh
    `TemporaryDirectory` per call sidesteps that entirely."""
    with tempfile.TemporaryDirectory() as tmp:
        pf = parse_file(_write(Path(tmp), "a.py", src)).danger_ok
        return parse_directives(pf)


_INV_ID = st.builds(lambda n: f"INV-{n:03d}", st.integers(min_value=0, max_value=999))

#: A single dotted-module-path component: python-identifier-shaped, no
#: leading digit, matching `frob.graph.dsl._IMPORT_MODULE_RE`'s per-segment
#: rule.
_MODULE_SEGMENT = st.text(
    alphabet=string.ascii_lowercase + "_", min_size=1, max_size=12
).filter(lambda s: not s[0].isdigit())
_MODULE_PATH = st.lists(_MODULE_SEGMENT, min_size=1, max_size=4).map(".".join)


class TestBareInvariantUnaffected:
    """A bare `frob:invariant INV-###` (no obligation attrs) parses
    identically before and after T-0757's grammar extension."""

    # frob:tests tests/unit/graph/test_dsl_invariant_property.py::TestBareInvariantUnaffected.test_bare_invariant_parses_with_no_attrs  # noqa: E501
    @given(_INV_ID)
    def test_bare_invariant_parses_with_no_attrs(self, inv_id: str) -> None:
        src = f"def foo() -> None:\n    # frob:invariant {inv_id}\n    pass\n"
        edges, malformed = _parse_src(src)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == inv_id
        assert edges[0].attrs == {}


class TestNoImportAttr:
    """`frob:invariant INV-### no-import="..."` (T-0757, INV007)."""

    # frob:tests tests/unit/graph/test_dsl_invariant_property.py::TestNoImportAttr.test_valid_dotted_path_list_always_parses  # noqa: E501
    @given(_INV_ID, st.lists(_MODULE_PATH, min_size=1, max_size=5))
    def test_valid_dotted_path_list_always_parses(
        self, inv_id: str, modules: list[str]
    ) -> None:
        joined = ",".join(modules)
        src = f'# frob:invariant {inv_id} no_import="{joined}"\ndef foo(): pass\n'
        edges, malformed = _parse_src(src)
        assert not malformed
        assert edges[0].attrs["no_import"] == joined

    # frob:tests tests/unit/graph/test_dsl_invariant_property.py::TestNoImportAttr.test_empty_no_import_is_malformed  # noqa: E501
    def test_empty_no_import_is_malformed(self, tmp_path: Path) -> None:
        src = '# frob:invariant INV-042 no_import=""\ndef foo(): pass\n'
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "no_import" in malformed[0].reason

    # frob:tests tests/unit/graph/test_dsl_invariant_property.py::TestNoImportAttr.test_non_dotted_no_import_is_malformed  # noqa: E501
    def test_non_dotted_no_import_is_malformed(self, tmp_path: Path) -> None:
        src = '# frob:invariant INV-042 no_import="not a module!"\ndef foo(): pass\n'
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1


class TestEstablishesAttr:
    """`frob:invariant INV-### establishes="..."` (T-0757, INV008)."""

    # frob:tests tests/unit/graph/test_dsl_invariant_property.py::TestEstablishesAttr.test_non_empty_text_always_parses  # noqa: E501
    # Printable ASCII, no `"`/`\`/`#` (those interact with the attribute
    # quoting and comment-strip machinery itself, not the establishes=
    # shape rule under test) -- deliberately narrower than a full unicode
    # fuzz, which is `frob.graph.dsl`'s own comment-extraction layer's
    # concern, not this attribute validator's.
    _ESTABLISHES_TEXT = st.text(
        alphabet=st.sampled_from(
            [c for c in string.printable if c not in '"\\#\n\r\t\x0b\x0c']
        ),
        min_size=1,
        max_size=200,
    ).filter(lambda s: s.strip())

    @given(_INV_ID, _ESTABLISHES_TEXT)
    def test_non_empty_text_always_parses(self, inv_id: str, text: str) -> None:
        src = f'# frob:invariant {inv_id} establishes="{text}"\ndef foo(): pass\n'
        edges, malformed = _parse_src(src)
        assert not malformed
        assert edges[0].attrs["establishes"] == text

    # frob:tests tests/unit/graph/test_dsl_invariant_property.py::TestEstablishesAttr.test_blank_establishes_is_malformed  # noqa: E501
    def test_blank_establishes_is_malformed(self, tmp_path: Path) -> None:
        src = '# frob:invariant INV-042 establishes="   "\ndef foo(): pass\n'
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "establishes" in malformed[0].reason
