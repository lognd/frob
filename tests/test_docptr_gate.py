"""Tests for frob.gates._docptr -- DOC006 doc-pointer resolution gate over a
closed set of recognized, mechanically resolvable pointer shapes
(docs/modules/gates.md#doc006-doc-pointer-resolution-gate, T-0437).

Fixtures mirror tests/test_docblocks_gate.py's synthetic tempfile-backed git
repo + real `GraphSnapshot` posture -- DOC006 reuses `frob.gates._docblocks`'s
namespace/console-registry machinery directly, so it needs the same real
graph and, for the CLI tier, the same `frob.toml [[docblocks.commands]]`
config shape.
"""
# frob:ticket T-0437

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._docptr import doc006_gate
from frob.gates._models import Severity
from frob.graph import build_graph


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _add_all(root: Path) -> None:
    _git(root, "add", "-A")


def _snapshot(root: Path):
    return build_graph(root, root / ".frob" / "cache.db").danger_ok


def _by_rule(violations, file: str | None = None):
    return [
        v for v in violations if v.rule == "DOC006" and (file is None or v.file == file)
    ]


_CLI_CONFIG = (
    '[[docblocks.commands]]\nprog = "frob"\nparser = "frob.__main__:_build_parser"\n'
)


class TestDoc006FilePath:
    """Kind 1: FILE/PATH -- a repo-relative path mentioned in prose must
    exist as a tracked file."""

    def test_missing_path_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "docs/guide.md", "See `src/frob/gone.py` for details.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("gone.py" in v.message for v in found)
        assert all(v.severity == Severity.WARN for v in found)

    def test_real_path_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "src/pkg/real.py", "x = 1\n")
        _write(tmp_path, "docs/guide.md", "See `src/pkg/real.py` for details.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_unrecognized_prose_not_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            "This tool seems to point at `something.fuzzy` in a vague way.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_dot_frob_runtime_path_not_flagged(self, tmp_path: Path) -> None:
        """`.frob/*` is a real, expected-to-exist runtime artifact this
        repo's own `.gitignore` deliberately keeps untracked -- never a
        stale FILE/PATH finding just because it is (correctly) untracked.
        Round-2 fix, dogfooding this gate over frob's own docs/CHANGELOG.md
        found this exact false-positive class."""
        _init_repo(tmp_path)
        _write(tmp_path, "docs/guide.md", "See `.frob/tickets.lock` for it.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006DocAnchor:
    """Kind 5: DOC-ANCHOR LINK -- `docs/x.md#anchor` must resolve both the
    file and a real heading/`<a id>` slug in it."""

    def test_missing_anchor_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "docs/target.md", "# Real Heading\n")
        _write(
            tmp_path, "docs/guide.md", "See [it](docs/target.md#nonexistent-anchor).\n"
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("nonexistent-anchor" in v.message for v in found)

    def test_real_anchor_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "docs/target.md", "# Real Heading\n")
        _write(tmp_path, "docs/guide.md", "See [it](docs/target.md#real-heading).\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006Cli:
    """Kind 2: CLI INVOCATION -- `<prog> <subcommand>` / `--flag` checked
    against the live argparse registry (same [[docblocks.commands]] config
    DOC004's console tier uses)."""

    def test_nonexistent_subcommand_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(tmp_path, "docs/guide.md", "Run `frob nonexistent-subcommand` first.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("nonexistent-subcommand" in v.message for v in found)

    def test_nonexistent_flag_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path, "docs/guide.md", "Run `frob check --nonexistent-flag` first.\n"
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("--nonexistent-flag" in v.message for v in found)

    def test_real_command_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(tmp_path, "docs/guide.md", "Run `frob check --delta` first.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006Config:
    """Kind 3: CONFIG REFERENCE -- `[section]`/`[section.key]` checked
    against this project's own loaded frob.toml."""

    def test_bogus_section_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(tmp_path, "docs/guide.md", "Add `[bogus.section]` to frob.toml.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("bogus.section" in v.message for v in found)

    def test_real_section_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", '[gates.severity]\nDOC001 = "warn"\n')
        _write(tmp_path, "docs/guide.md", "Add `[gates.severity]` to frob.toml.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_all_caps_citation_tag_not_flagged(self, tmp_path: Path) -> None:
        """T-1016: `[IN-REPO]`-shaped tokens are prose citation TAGS, not
        `[section]` TOML pointers -- every real config table this repo's
        own loaders read is lowercase (optionally dotted), so an ALL-CAPS
        bracketed root is structurally never a config reference."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(tmp_path, "docs/guide.md", "Rows already covered are `[IN-REPO]`.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_declared_but_unset_section_not_flagged(self, tmp_path: Path) -> None:
        """T-1016: `[vet.allow]` is a real section `frob.vet._allow` reads
        from `frob.toml` -- but this SYNTHETIC test repo's own `frob.toml`
        never populates it, mirroring the false-positive class the
        curated `_DECLARED_BUT_UNSET_CONFIG_SECTIONS` allowlist exists
        for (this repo's own `frob.toml` has the identical gap)."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(tmp_path, "docs/guide.md", "Configure detectors via `[vet.allow]`.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006Symbol:
    """Kind 4: CODE SYMBOL -- a dotted `module.Class.method`-shaped token
    whose root namespace is this project's own is checked against the real
    graph."""

    def test_nonexistent_symbol_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "pkg"\n')
        _write(tmp_path, "src/pkg/__init__.py", "")
        _write(tmp_path, "src/pkg/mod.py", "def real(): pass\n")
        _write(tmp_path, "docs/guide.md", "See `pkg.mod.nonexistent_symbol` for it.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("nonexistent_symbol" in v.message for v in found)

    def test_real_symbol_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "pkg"\n')
        _write(tmp_path, "src/pkg/__init__.py", "")
        _write(tmp_path, "src/pkg/mod.py", "def real(): pass\n")
        _write(tmp_path, "docs/guide.md", "See `pkg.mod.real` for it.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_module_dunder_init_and_all_pass(self, tmp_path: Path) -> None:
        """`pkg.mod.__init__`/`pkg.mod.__all__` name the module ITSELF (a
        doc's own convention), not a stale top-level symbol -- round-2
        fix, dogfooding this gate over frob's own docs found this exact
        false-positive class."""
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "pkg"\n')
        _write(tmp_path, "src/pkg/__init__.py", "")
        _write(tmp_path, "src/pkg/mod.py", "def real(): pass\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "See `pkg.mod.__init__` and `pkg.mod.__all__` for it.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_class_attribute_chain_not_flagged(self, tmp_path: Path) -> None:
        """`pkg.mod.Real.SOME_ATTR` -- `Real` is a real top-level symbol in
        `pkg.mod`, but a class ATTRIBUTE one level deeper is outside what
        this simple module-map resolver can prove-or-refute; flagging it
        STALE would be exactly the false-positive class the ticket's own
        conservatism directive warns against -- round-2 fix, dogfooding
        this gate over frob's own docs found this exact false-positive
        class (`frob.graph._models.EdgeKind.ENFORCES`)."""
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "pkg"\n')
        _write(tmp_path, "src/pkg/__init__.py", "")
        _write(tmp_path, "src/pkg/mod.py", "class Real:\n    SOME_ATTR = 1\n")
        _write(tmp_path, "docs/guide.md", "See `pkg.mod.Real.SOME_ATTR` for it.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_reexported_class_attribute_chain_not_flagged(self, tmp_path: Path) -> None:
        """T-1016: `pkg.Real.SOME_ATTR` where `Real` is defined in `pkg.mod`
        and RE-EXPORTED (not locally defined) through `pkg/__init__.py`'s
        own `from .mod import Real` line -- the same one-level-deeper
        conservatism as `test_class_attribute_chain_not_flagged`, but
        through a re-export rather than a same-file definition
        (`frob.lang.TreeNode.span` is exactly this shape upstream)."""
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "pkg"\n')
        _write(tmp_path, "src/pkg/mod.py", "class Real:\n    SOME_ATTR = 1\n")
        _write(tmp_path, "src/pkg/__init__.py", "from pkg.mod import Real\n")
        _write(tmp_path, "docs/guide.md", "See `pkg.Real.SOME_ATTR` for it.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_dunder_init_mid_chain_resolves_to_module(self, tmp_path: Path) -> None:
        """T-1016: `pkg.mod.__init__.real` -- a doc author spelling out a
        package's own `__init__.py` explicitly inside a longer chain
        (`frob.gates.__init__.perf_gate` naming a symbol defined directly
        in `frob/gates/__init__.py`) -- `X.__init__` and bare `X` name the
        SAME module, so this resolves exactly as `pkg.mod.real` would."""
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "pkg"\n')
        _write(tmp_path, "src/pkg/__init__.py", "")
        _write(tmp_path, "src/pkg/mod.py", "def real(): pass\n")
        _write(tmp_path, "docs/guide.md", "See `pkg.mod.__init__.real` for it.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006Waive:
    """`frob:waive DOC006 reason="..."` suppresses any of the above tiers,
    same nearby-line convention as DOC004."""

    def test_waive_suppresses(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            '<!-- frob:waive DOC006 reason="illustrative, not real" -->\n'
            "See `src/frob/gone.py` for details.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006TestsTargetShape:
    """The DRIFT002 dotted-vs-:: hardening (T-0986: promoted to its own
    rule, DOC007, at ERROR -- split out of DOC006 so the promotion does
    not also touch DOC006's ~700 unrelated, still-WARN findings): a
    `frob:tests` target with a second `::` (pytest's own `Class::method`
    separator) is a recognized wrong shape, flagged directly regardless of
    doc content."""

    def test_double_separator_target_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:tests tests/test_mod.py::TestX::test_y\ndef real():\n    pass\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = [v for v in violations if v.rule == "DOC007"]
        assert any("TestX::test_y" in v.message for v in found)
        assert all(v.severity == Severity.ERROR for v in found)

    def test_single_separator_target_not_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:tests tests/test_mod.py::TestX.test_y\ndef real():\n    pass\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = [v for v in violations if v.rule == "DOC007"]
        assert not any("tests/test_mod.py::TestX.test_y" in v.message for v in found)
