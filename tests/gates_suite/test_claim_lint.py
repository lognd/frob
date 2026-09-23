"""Tests for `frob.gates._claim_lint` (CLAIM001, T-4116).

F-307 H3-4: a docstring asserting never/always/idempotent-shaped language
with no `frob:invariant` directive bound to that same symbol anywhere in
its own span is an unverified claim. Per the ticket's own Fixture note,
this fires cleanly in frob's own tree, but every assertion here uses a
controlled SYNTHETIC pair (a real must-fire instance in frob's own tree
would be flaky against unrelated future edits) written under a tmp git
repo.
"""

from pathlib import Path

from frob.gates._claim_lint import claim_lint_gate
from tests.conftest import _by_rule, _git_init, _write


# frob:tests src/frob/gates/_claim_lint.py::claim_lint_gate
def test_claim001_fires_on_unbound_never_claim(tmp_path: Path) -> None:
    """Must-fire: a function's docstring says "this never raises" with no
    `frob:invariant` directive anywhere in its span."""
    _write(
        tmp_path,
        "pkg/mod.py",
        (
            "def parse(text):\n"
            '    """Parse text; this never raises."""\n'
            "    return text\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(claim_lint_gate(tmp_path), "CLAIM001")

    assert len(violations) == 1
    assert violations[0].symref == "pkg/mod.py::parse"

# frob:tests src/frob/gates/_claim_lint.py::claim_lint_gate

def test_claim001_quiet_when_invariant_directive_present(tmp_path: Path) -> None:
    """Must-stay-quiet: the SAME docstring text, but WITH a
    `frob:invariant` directive bound to the same symbol."""
    _write(
        tmp_path,
        "pkg/mod.py",
        (
            "# frob:invariant INV-999\n"
            "def parse(text):\n"
            '    """Parse text; this never raises."""\n'
            "    return text\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(claim_lint_gate(tmp_path), "CLAIM001")

    assert violations == []


# frob:tests src/frob/gates/_claim_lint.py::claim_lint_gate
def test_claim001_quiet_on_ordinary_prose_regardless_of_invariant_coverage(
    tmp_path: Path,
) -> None:
    """A function whose docstring uses no never/always/idempotent
    language at all stays quiet regardless of invariant coverage -- this
    lint is claim-triggered, not universal."""
    _write(
        tmp_path,
        "pkg/mod.py",
        ('def parse(text):\n    """Parse text into tokens."""\n    return text\n'),
    )
    _git_init(tmp_path)

    violations = _by_rule(claim_lint_gate(tmp_path), "CLAIM001")

    assert violations == []


# frob:tests src/frob/gates/_claim_lint.py::claim_lint_gate
def test_claim001_honors_frob_waive_escape_hatch(tmp_path: Path) -> None:
    """A `frob:waive CLAIM001 reason="..."` bound to the same symbol
    suppresses the finding -- the standard escape hatch for a claim
    genuinely covered by a differently-shaped test the directive
    convention cannot see."""
    _write(
        tmp_path,
        "pkg/mod.py",
        (
            '# frob:waive CLAIM001 reason="covered by a property test, see tests/test_parse_never_raises.py"\n'  # noqa: E501
            "def parse(text):\n"
            '    """Parse text; this never raises."""\n'
            "    return text\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(claim_lint_gate(tmp_path), "CLAIM001")

    assert violations == []


def test_claim001_fires_once_per_offending_symbol_not_per_word(tmp_path: Path) -> None:
    """A docstring using more than one claim word (never AND always) still
    produces exactly ONE finding for that symbol, not one per word."""
    _write(
        tmp_path,
        "pkg/mod.py",
        (
            "def parse(text):\n"
            '    """This never raises and always returns a string."""\n'
            "    return text\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(claim_lint_gate(tmp_path), "CLAIM001")

    assert len(violations) == 1


def test_claim001_scopes_to_the_exact_symbol_not_the_whole_file(tmp_path: Path) -> None:
    """A `frob:invariant` bound to ONE function does not suppress a claim
    in a DIFFERENT, unbound function in the same file -- directive
    presence is per-symbol, never file-wide."""
    _write(
        tmp_path,
        "pkg/mod.py",
        (
            "# frob:invariant INV-999\n"
            "def bound(text):\n"
            '    """This always succeeds."""\n'
            "    return text\n"
            "\n"
            "\n"
            "def unbound(text):\n"
            '    """This never fails."""\n'
            "    return text\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(claim_lint_gate(tmp_path), "CLAIM001")

    assert len(violations) == 1
    assert violations[0].symref == "pkg/mod.py::unbound"


def test_claim001_fires_on_class_docstring_too(tmp_path: Path) -> None:
    """A CLASS docstring's own never/always/idempotent claim is checked
    the same way a function's is -- this lint is not function-only."""
    _write(
        tmp_path,
        "pkg/mod.py",
        (
            "class Cache:\n"
            '    """This cache is always idempotent under repeated writes."""\n'
            "\n"
            "    def get(self, key):\n"
            "        return None\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(claim_lint_gate(tmp_path), "CLAIM001")

    assert len(violations) == 1
    assert violations[0].symref == "pkg/mod.py::Cache"
