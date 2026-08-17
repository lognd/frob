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

    # frob:ticket T-1641
    def test_profile_section_not_flagged(self, tmp_path: Path) -> None:
        """T-draft-8c110736: `[profile]`/`[profile.profile]` (`frob.tickets._profile`,
        T-1575) is a real section that codebase reads but that this
        SYNTHETIC test repo's own `frob.toml` never populates -- same
        `_DECLARED_BUT_UNSET_CONFIG_SECTIONS` false-positive class as
        `[vet.allow]` above, added when this repo's own `docs/modules/
        tickets.md` was caught by the gap."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(
            tmp_path,
            "docs/guide.md",
            'Set `[profile] profile = "rapid"` for a small repo.\n',
        )
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


class TestDoc006FileSymbol:
    """Kind 6 (T-1228): `` `path.py::qualname` `` / `` `path.rs::name` ``
    -- a doc author naming WHICH file a symbol lives in explicitly,
    distinct from the dotted importable-module-path kind 4 already
    covers."""

    def test_py_missing_symbol_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "src/pkg/mod.py", "def real(): pass\n")
        _write(tmp_path, "docs/guide.md", "See `src/pkg/mod.py::nonexistent` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("nonexistent" in v.message for v in found)

    def test_py_real_symbol_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "src/pkg/mod.py", "def real(): pass\n")
        _write(tmp_path, "docs/guide.md", "See `src/pkg/mod.py::real` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_py_private_twin_noted_in_message(self, tmp_path: Path) -> None:
        """The renamed-to-private awareness case: `digest_sig` was renamed
        `_digest_sig` and the doc was never updated -- the violation
        message should point at the real, private name."""
        _init_repo(tmp_path)
        _write(tmp_path, "src/pkg/mod.py", "def _digest_sig(): pass\n")
        _write(tmp_path, "docs/guide.md", "See `src/pkg/mod.py::digest_sig` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("_digest_sig" in v.message for v in found)

    def test_rust_missing_fn_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "crate/src/lib.rs", "pub fn real() {}\n")
        _write(tmp_path, "docs/guide.md", "See `crate/src/lib.rs::nonexistent` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("nonexistent" in v.message for v in found)

    def test_rust_real_fn_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "crate/src/lib.rs", "pub fn real_fn() {}\n")
        _write(tmp_path, "docs/guide.md", "See `crate/src/lib.rs::real_fn` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_rust_non_pub_trait_impl_fn_passes(self, tmp_path: Path) -> None:
        """T-1228 round-3: a real, currently-defined rust function that is
        a TRAIT-IMPL method never carries its own explicit `pub` keyword
        (visibility is inherited from the trait) -- real-corpus
        verification found several genuine functions (`parse_node`,
        `parse_store`, ...) flagged stale this way. Kind 6 is scoped to
        one already-named file, so matching without `pub` is precise here,
        unlike the crate-wide `use` check kind 2 reuses."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "crate/src/lib.rs",
            "impl Visitor for Walker {\n    fn parse_node(&mut self) {}\n}\n",
        )
        _write(tmp_path, "docs/guide.md", "See `crate/src/lib.rs::parse_node` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_missing_file_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "docs/guide.md", "See `src/pkg/gone.py::real` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("gone.py" in v.message for v in found)

    def test_ambiguous_basename_shorthand_not_flagged(self, tmp_path: Path) -> None:
        """T-1228 round-3: a shorthand basename (`_mod.py`, no directory)
        that matches TWO different tracked files cannot be resolved OR
        refuted without guessing -- real-corpus verification found this
        picked an arbitrary wrong match (`_waive.py::
        MULTI_INSTANCE_WAIVER_FAMILIES` resolved against the wrong of two
        tracked `_waive.py` files, flagging a real symbol as stale)."""
        _init_repo(tmp_path)
        _write(tmp_path, "src/pkg_a/_mod.py", "def only_in_a(): pass\n")
        _write(tmp_path, "src/pkg_b/_mod.py", "def only_in_b(): pass\n")
        _write(tmp_path, "docs/guide.md", "See `_mod.py::only_in_b` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006BareIdentifier:
    """Kind 7 (T-1228): a bare, code-shaped backtick identifier resolved
    within the doc's OWN anchored module scope (a `frob:doc <this doc>#...`
    edge somewhere in the tree) -- never fires on an unanchored doc."""

    def _anchored_repo(self, tmp_path: Path, module_body: str, doc_body: str) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            f"# frob:doc docs/guide.md#anchor\n{module_body}",
        )
        _write(tmp_path, "docs/guide.md", f"# Anchor\n\n{doc_body}")
        _add_all(tmp_path)

    def test_unanchored_doc_not_checked(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "src/pkg/mod.py", "def real_thing(): pass\n")
        _write(tmp_path, "docs/guide.md", "See `nonexistent_thing` here.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_anchored_unresolved_without_twin_not_flagged(self, tmp_path: Path) -> None:
        """T-1228 round-3: a code-shaped bare identifier that resolves to
        NEITHER a public NOR a private name is silently skipped -- real-
        corpus verification found this generic "doesn't exist" signal was
        unhardenable (data/config field names and third-party vocabulary
        are code-shaped and never top-level python symbols). Only the
        private-name-rename signal (see `test_anchored_private_twin_noted`
        below) is unambiguous enough to flag."""
        self._anchored_repo(
            tmp_path,
            "def real_thing(): pass\n",
            "See `nonexistent_thing` here.\n",
        )
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_anchored_real_name_passes(self, tmp_path: Path) -> None:
        self._anchored_repo(
            tmp_path,
            "def real_thing(): pass\n",
            "See `real_thing` here.\n",
        )
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_anchored_private_twin_noted(self, tmp_path: Path) -> None:
        self._anchored_repo(
            tmp_path,
            "def _digest_sig(): pass\n",
            "See `digest_sig` here.\n",
        )
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("_digest_sig" in v.message for v in found)

    def test_plain_prose_word_not_flagged(self, tmp_path: Path) -> None:
        """Even inside an anchored doc, a plain English backtick word
        (no underscore, no multi-hump CamelCase) is not code-shaped and is
        never checked -- the shape filter, not the anchor, is what keeps
        this kind closed-set."""
        self._anchored_repo(
            tmp_path,
            "def real_thing(): pass\n",
            "See `result` here.\n",
        )
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006WrappedSpan:
    """Line-wrapped backtick spans (T-1228): commonmark treats a single
    embedded newline inside an inline code span as ordinary whitespace, so
    a span an editor hard-wrapped mid-token still resolves as the SAME
    token written on one line."""

    def test_wrapped_backtick_span_resolves(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "src/pkg/mod.py", "def real(): pass\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "See `src/pkg/mod.py::\nreal` for it.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006BareIdentifierNarrowing:
    """T-1228 round-2 (post-close reject over ~1400 real-corpus false
    positives): kind 7 is narrowed to genuinely single-implementation-
    module docs, excludes spec-prose (`docs/strata/**`, `design/**`) and
    ledger files outright, and resolves against the WHOLE project's
    symbol table, not just the one anchor file."""

    def test_multi_anchor_doc_not_checked(self, tmp_path: Path) -> None:
        """A doc describing TWO modules (two distinct frob:doc anchor
        files) is a reference/system doc, not a single-module doc -- kind
        7 is out of scope for it entirely, even for an unresolved,
        code-shaped bare identifier."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod_a.py",
            "# frob:doc docs/guide.md#anchor\ndef real_a(): pass\n",
        )
        _write(
            tmp_path,
            "src/pkg/mod_b.py",
            "# frob:doc docs/guide.md#anchor\ndef real_b(): pass\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "# Anchor\n\nSee `nonexistent_thing` here.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_spec_prose_doc_excluded(self, tmp_path: Path) -> None:
        """A `docs/strata/**` page is spec/design-language prose -- its
        vocabulary is DSL terminology, not python identifiers, even when
        singly anchored and code-shaped."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/strata/spec.md#anchor\ndef real_thing(): pass\n",
        )
        _write(
            tmp_path,
            "docs/strata/spec.md",
            "# Anchor\n\nSee `two_phase_commit` here.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/strata/spec.md")

    def test_changelog_is_an_archival_record_not_checked(self, tmp_path: Path) -> None:
        """T-1412: `CHANGELOG.md` is append-only and land-owned -- `frob
        ticket land` writes each entry describing the tree as it was THEN,
        and T-0731's pre-commit guard refuses a hand-edit outright. A
        DOC006 there therefore has no honest path to zero: the only fix
        would be falsifying an immutable record. Same class, and same
        rationale, as `tickets-archive.md`."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write(
            tmp_path,
            "CHANGELOG.md",
            "# Changelog\n\n- renamed `src/pkg/mod.py::long_gone_symbol`\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "CHANGELOG.md")

    def test_sharded_archive_dir_is_an_archival_record_not_checked(
        self, tmp_path: Path
    ) -> None:
        """T-2131: `tickets/archive/<id>/*.md` (the v2 sharded-per-ticket
        migration's own archive shard) is the SAME class as `tickets-
        archive.md`/`CHANGELOG.md` above -- `frob ticket archive` moves a
        closed/dropped ticket's `done-report.md` here verbatim, forever.
        Its command citations are correct-at-close-time history, not a
        doc that is wrong right now."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write(
            tmp_path,
            "tickets/archive/T-0001/done-report.md",
            "Removed `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/archive/T-0001/done-report.md")

    def test_live_ticket_dir_still_flagged(self, tmp_path: Path) -> None:
        """The archive-directory exclusion above narrows to `tickets/
        archive/**` specifically -- a still-open ticket's own `tickets/
        T-<id>/ticket.md` (not yet archived) must still be checked exactly
        as any other live doc, per the standing rule against blanket-
        excluding all of `tickets/**`."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write(
            tmp_path,
            "tickets/T-0002/ticket.md",
            "Removed `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert _by_rule(violations, "tickets/T-0002/ticket.md")

    def test_live_doc_still_flagged_after_changelog_exclusion(
        self, tmp_path: Path
    ) -> None:
        """The exclusion above narrows AIM, never capability: a stale
        pointer in a LIVE doc -- one anybody can still edit honestly --
        must still be caught exactly as before."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "# Anchor\n\nSee `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert _by_rule(violations, "docs/guide.md")

    def test_cross_file_real_symbol_passes(self, tmp_path: Path) -> None:
        """A single-anchor doc mentioning a symbol defined in ANOTHER file
        (not its own anchor file) is a real cross-file reference, not
        stale drift -- resolved against the whole project's symbol table."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "src/pkg/other.py", "class AuditReport:\n    pass\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "# Anchor\n\nSee `AuditReport` here.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    def test_absent_everywhere_without_twin_not_flagged(self, tmp_path: Path) -> None:
        """T-1228 round-3: a single-anchor, non-spec doc's code-shaped bare
        identifier that resolves NOWHERE in the project (not the anchor
        file, not any other file, and no private twin either) is NOT
        flagged -- real-corpus verification found "resolves nowhere" alone
        is not a resolvable-or-refutable signal for this shape (config
        field names, third-party vocabulary, ...)."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "src/pkg/other.py", "def unrelated(): pass\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "# Anchor\n\nSee `totally_nonexistent_thing` here.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")


class TestDoc006LedgerExclusion:
    """T-1228 round-2: ticket-ledger prose (`tickets.md`/`tickets-archive.
    md`) routinely quotes illustrative syntax examples that are never live
    pointers -- excluded from BOTH new T-1228 kinds (kind 6 FILE::SYMBOL,
    kind 7 BARE IDENTIFIER)."""

    def test_ledger_file_symbol_placeholder_not_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "tickets.md",
            "Use the `path.py::qualname` shape for a file::symbol pointer.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets.md")

    def test_ledger_bare_identifier_placeholder_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """Even a shape that WOULD be flagged (private-name-rename) in an
        ordinary single-anchor doc is skipped in a ledger file -- the
        ledger exclusion is checked before the private-twin resolution."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc tickets.md#anchor\ndef _digest_sig(): pass\n",
        )
        _write(
            tmp_path,
            "tickets.md",
            "# Anchor\n\nSee `digest_sig` here.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets.md")
