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
import sys
from pathlib import Path

import pytest

from frob.findings import Severity
from frob.gates._docptr import _blank_ticket_reason_fields, doc006_gate
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
        assert all(v.severity == Severity.ERROR for v in found)

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


# frob:ticket T-2559
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

    # frob:ticket T-2533
    def test_dispatch_bypassed_worktree_remove_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """T-2533: `_dispatch_worktree` bypasses `_build_parser()` entirely
        for the whole `worktree` verb, and `_build_parser()`'s own
        `--help`-only mirror used to register `sweep` alone -- a doc
        naming the REAL `frob worktree remove` command (confirmed working:
        `frob worktree remove --help` resolves cleanly) must not be
        flagged as pointing at a nonexistent subcommand."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(tmp_path, "docs/guide.md", "Run `frob worktree remove` to clean up.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    # frob:ticket T-2533
    def test_dispatch_bypassed_worktree_release_lease_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """T-2533: same bypass class as `worktree remove`, for
        `worktree release-lease` -- also genuinely real and also missing
        from `_build_parser()`'s incomplete `sweep`-only mirror."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "Run `frob worktree release-lease` to free a stale lease.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    # frob:ticket T-2533
    def test_dispatch_bypassed_release_publish_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """T-2533: `_dispatch_release_publish` bypasses `_build_parser()`
        for the LEAF `release publish` subcommand only -- `release`'s
        other subcommands (`stamp`/`check`/`sync`) genuinely register
        through `_build_parser()`, `publish` never did. A doc naming the
        real `frob release publish` command (confirmed working: `frob
        release publish --help` resolves cleanly) must not be flagged."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(tmp_path, "docs/guide.md", "Run `frob release publish` to ship.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    # frob:ticket T-2533
    def test_worktree_subcommand_still_genuinely_nonexistent_flagged(
        self, tmp_path: Path
    ) -> None:
        """POSITIVE CONTROL (T-2533): the bypass-subtree patch replaces
        `worktree`'s incomplete mirror with its REAL tree -- it must not
        become a rubber stamp that waves through EVERY word under
        `worktree`. A genuinely nonexistent `worktree` subcommand still
        fires, proving the patched tree is still a real, closed set, not
        an accidental always-pass."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "Run `frob worktree nonexistent-subcommand` first.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("nonexistent-subcommand" in v.message for v in found)

    # frob:ticket T-2533
    def test_release_subcommand_still_genuinely_nonexistent_flagged(
        self, tmp_path: Path
    ) -> None:
        """POSITIVE CONTROL (T-2533): same proof as the `worktree` control
        above, for `release`'s leaf-patch path -- adding the `publish`
        leaf must not accidentally widen `release` into accepting
        anything."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            "Run `frob release nonexistent-subcommand` first.\n",
        )
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("nonexistent-subcommand" in v.message for v in found)

    # frob:ticket T-2559
    # frob:waive DUP001 reason="structurally identical to the sibling T-2533 \
    # subcommand-chain positive-fixture tests (same _init_repo/_write/_add_all/ \
    # doc006_gate shape with different literal doc text) -- these are deliberate, \
    # cheap, single-purpose regression fixtures per case, not accidental copy-paste \
    # logic worth extracting into a shared helper that would make each case's own doc \
    # text (the actual thing under test) harder to read at the call site"
    def test_dispatch_bypassed_worktree_sweep_force_flag_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """T-2559: `_build_parser()`'s decorative `--help`-only mirror of
        `worktree sweep` (`frob._cli_parsers._core._add_worktree_parser`)
        never registered `--force`, even though the real dispatch-time
        parser (`frob.app.worktree_runner._build_worktree_parser`, the
        SAME `_BYPASS_SUBTREE_PATCHES` target T-2533 wired for the
        subcommand-chain check) genuinely has it (T-1739). This is the
        FLAG-resolution false positive T-2533 left unfixed -- a doc citing
        the real `frob worktree sweep --force` must not be flagged."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "Run `frob worktree sweep --force` to override the liveness gate.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    # frob:ticket T-2559
    def test_worktree_sweep_nonexistent_flag_still_flagged(
        self, tmp_path: Path
    ) -> None:
        """POSITIVE CONTROL (T-2559): the bypass-parser patch used for
        flag resolution must not become a rubber stamp that waves through
        EVERY flag under `worktree sweep` -- a genuinely nonexistent flag
        on the REAL bypassed parser still fires. Without this control the
        fix above would be indistinguishable from blinding DOC006 for the
        whole `worktree sweep` leaf."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "Run `frob worktree sweep --nonexistent-flag` first.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("--nonexistent-flag" in v.message for v in found)


class TestDoc006Config:
    """Kind 3: CONFIG REFERENCE -- `[section]`/`[section.key]` checked
    against this project's own loaded frob.toml.

    T-2703: candidates now come from the CODE-SPAN-STRIPPED prose (plain
    text, not backtick-wrapped) -- a `[section]`/`[section.key]` shape
    INSIDE a backtick span is deliberately inert (see
    `_CONFIG_REF_PROSE_RE`'s own comment: it collides with unrelated code
    syntax that happens to share the bracket shape, e.g. a C++ lambda
    capture `` `[x]` ``). These fixtures write the pointer as plain prose
    accordingly; a dedicated code-span-inertness test lives just below."""

    def test_bogus_section_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(tmp_path, "docs/guide.md", "Add [bogus.section] to frob.toml.\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("bogus.section" in v.message for v in found)

    def test_real_section_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", '[gates.severity]\nDOC001 = "warn"\n')
        _write(tmp_path, "docs/guide.md", "Add [gates.severity] to frob.toml.\n")
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
        _write(tmp_path, "docs/guide.md", "Rows already covered are [IN-REPO].\n")
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
        _write(tmp_path, "docs/guide.md", "Configure detectors via [vet.allow].\n")
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
            'Set [profile.profile] to "rapid" for a small repo.\n',
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    # frob:ticket T-2703
    def test_bracket_shape_inside_code_span_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """T-2703 control: the reported false positive -- a dotted
        bracket shape that collides with `[section.key]` syntax but is
        actually unrelated code (illustrating attribute-access shorthand),
        written inside a backtick span -- must NOT fire."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "Fancy indexing docs often show (`[arr.dtype]`) as shorthand "
            "for the dtype attribute.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    # frob:ticket T-2703
    def test_bare_bracket_word_without_dot_never_a_candidate(
        self, tmp_path: Path
    ) -> None:
        """T-2703 control: an undotted `[word]` in plain prose (a
        numbered citation, a footnote-style slug) is structurally never a
        `[section.key]` TOML pointer in this repo's real usage -- must
        not fire, backticked or not."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "See finding [silent-zero] in the audit above.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "docs/guide.md")

    # frob:ticket T-2703
    def test_bogus_section_in_fenced_block_is_not_flagged(self, tmp_path: Path) -> None:
        """T-2703 control: a fenced code block showing bracket syntax
        stays inert -- pre-existing behavior, must not regress."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "Example:\n\n```toml\n[bogus.section]\n```\n",
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

    def test_changelog_fragment_dir_is_an_archival_record_not_checked(
        self, tmp_path: Path
    ) -> None:
        """T-3489: `changelog.d/T-####.md` (the T-2445 per-ticket
        changelog fragment `CHANGELOG.md` itself is assembled from) is
        the SAME class as `CHANGELOG.md` one step earlier in the
        pipeline -- written once, at land time, from that land's own
        Done-report prose, never edited again. A broken pointer copied
        verbatim from historical prose (a since-irrelevant line-wrap, or
        a CLI verb the prose explicitly says was NOT added) has the same
        no-honest-fix-but-falsify-history shape `CHANGELOG.md`'s own
        exemption exists for."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write(
            tmp_path,
            "changelog.d/T-0001.md",
            "bump: minor\nT-0001: renamed `src/pkg/mod.py::long_gone_symbol`\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "changelog.d/T-0001.md")

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


def _write_ticket(
    tmp_path: Path, ticket_id: str, state: str, filename: str, body: str
) -> None:
    """Write a minimally-valid `tickets/<ticket_id>/<filename>` ticket
    frontmatter doc with `state` and prose `body` -- shared by
    TestDoc006TicketHistoricalExclusion's terminal/non-terminal cases."""
    frontmatter = (
        "---\n"
        f"id: {ticket_id}\n"
        "title: placeholder\n"
        f"state: {state}\n"
        "kind: bug\n"
        "origin: human\n"
        "created: '2026-08-18'\n"
        "---\n"
    )
    _write(tmp_path, f"tickets/{ticket_id}/{filename}", frontmatter + body)


class TestDoc006TicketHistoricalExclusion:
    """T-2505: `tickets/<id>/ticket.md`/`done-report.md` is a historical
    record ONLY once the ticket is TERMINAL (done/dropped) -- keyed on
    ticket STATE, never on the bare `tickets/` path prefix, so an OPEN
    ticket's body (work still to be done) keeps being checked exactly
    like any other live doc. Positive control both directions."""

    def test_done_ticket_body_not_flagged(self, tmp_path: Path) -> None:
        """A DONE ticket's `ticket.md` is an immutable record of what was
        true when it was written -- a dangling pointer there must NOT
        fire (must-not-fire half of the positive control)."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write_ticket(
            tmp_path,
            "T-9001",
            "done",
            "ticket.md",
            "Removed `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9001/ticket.md")

    def test_dropped_ticket_body_not_flagged(self, tmp_path: Path) -> None:
        """Same exemption for DROPPED -- the other terminal state."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write_ticket(
            tmp_path,
            "T-9002",
            "dropped",
            "ticket.md",
            "Removed `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9002/ticket.md")

    def test_open_ticket_body_still_flagged(self, tmp_path: Path) -> None:
        """An OPEN (queued/in-progress/etc) ticket's body is NOT a
        historical record -- it describes work still to be done, and a
        dangling pointer there is real (must-FIRE half of the positive
        control). This is the exact case a blanket `tickets/` prefix
        exemption would silently stop checking."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write_ticket(
            tmp_path,
            "T-9003",
            "in-progress",
            "ticket.md",
            "Plan: touch `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert _by_rule(violations, "tickets/T-9003/ticket.md")

    def test_done_report_not_flagged_even_if_state_lookup_fails(
        self, tmp_path: Path
    ) -> None:
        """A `done-report.md` is written once, at close, and never edited
        again -- it is exempt outright, without needing a successful
        ticket-state lookup (e.g. even if the sibling `ticket.md` is
        absent/malformed in this fixture)."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write(
            tmp_path,
            "tickets/T-9004/done-report.md",
            "Removed `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9004/done-report.md")

    # frob:ticket T-2534
    def test_done_ticket_evidence_file_not_flagged(self, tmp_path: Path) -> None:
        """T-2534: a DONE ticket's `evidence/*.md` is the SAME historical-
        record class as its `ticket.md` -- written once, describing what
        was true at the time, never edited again, just one directory
        level deeper. Must NOT fire (must-not-fire half of the positive
        control, mirroring test_done_ticket_body_not_flagged above)."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write_ticket(tmp_path, "T-9005", "done", "ticket.md", "placeholder\n")
        _write(
            tmp_path,
            "tickets/T-9005/evidence/fix-measurement.md",
            "Removed `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9005/evidence/fix-measurement.md")

    # frob:ticket T-2534
    def test_done_ticket_attachment_not_flagged(self, tmp_path: Path) -> None:
        """T-2534: same class as the evidence-file case above, for the
        sibling `attachments/` subdirectory (T-2195/T-2328's own shape)."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write_ticket(tmp_path, "T-9006", "dropped", "ticket.md", "placeholder\n")
        _write(
            tmp_path,
            "tickets/T-9006/attachments/01-survey.md",
            "Removed `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9006/attachments/01-survey.md")

    # frob:ticket T-2534
    def test_open_ticket_evidence_file_still_flagged(self, tmp_path: Path) -> None:
        """T-2534: the SAME terminal-state gate applies to evidence/
        attachments as to `ticket.md` itself -- an OPEN ticket's evidence
        file is NOT exempt (must-FIRE half of the positive control,
        mirroring test_open_ticket_body_still_flagged above). This is the
        exact case a blanket subdirectory-prefix exemption (ungated on
        state) would silently stop checking."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        _write_ticket(tmp_path, "T-9007", "in-progress", "ticket.md", "placeholder\n")
        _write(
            tmp_path,
            "tickets/T-9007/evidence/fix-measurement.md",
            "Plan: touch `src/pkg/mod.py::long_gone_symbol`.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert _by_rule(violations, "tickets/T-9007/evidence/fix-measurement.md")


# frob:ticket T-3724
class TestDoc006ReasonFieldExclusion:
    """T-3724: a `frob ticket scope`-written `reason:` frontmatter value is
    free-text accountability prose, never a doc pointer -- a reason
    mentioning a future config key or nonexistent file must not resolve
    as DOC006 pointer syntax. Positive control both directions: the
    frontmatter reason is exempt, the ticket BODY (real prose) still
    fires."""

    def test_scope_change_reason_not_flagged(self, tmp_path: Path) -> None:
        """A dangling-looking backtick span inside `scope_changes[].reason`
        must NOT fire -- it is free text a human/agent wrote to justify a
        scope mutation, not a pointer anyone is expected to keep live."""
        _init_repo(tmp_path)
        frontmatter = (
            "---\n"
            "id: T-9010\n"
            "title: placeholder\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "scope_changes:\n"
            "- op: remove\n"
            "  glob: tests/**\n"
            "  reason: narrow scope, future config key is\n"
            "    `frob.gates._docptr::long_gone_symbol`\n"
            "  actor: logan\n"
            "---\n"
        )
        _write(tmp_path, "tickets/T-9010/ticket.md", frontmatter + "placeholder\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9010/ticket.md")

    def test_open_ticket_body_still_flagged_alongside_reason(
        self, tmp_path: Path
    ) -> None:
        """The reason-field exemption is scoped to the frontmatter block
        only -- a dangling pointer in the ticket BODY of the same open
        ticket must still fire (must-FIRE half of the positive control,
        guards against the fix widening into a whole-file exemption)."""
        _init_repo(tmp_path)
        frontmatter = (
            "---\n"
            "id: T-9011\n"
            "title: placeholder\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "scope_changes:\n"
            "- op: remove\n"
            "  glob: tests/**\n"
            "  reason: mentions `frob.gates._docptr::long_gone_symbol` too\n"
            "  actor: logan\n"
            "---\n"
        )
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "# frob:doc docs/guide.md#anchor\ndef real_thing(): pass\n",
        )
        _write(tmp_path, "docs/guide.md", "# Anchor\n\nSee `real_thing`.\n")
        body = "Plan: touch `src/pkg/mod.py::long_gone_symbol`.\n"
        _write(tmp_path, "tickets/T-9011/ticket.md", frontmatter + body)
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert _by_rule(violations, "tickets/T-9011/ticket.md")


# frob:ticket T-3843
class TestDoc006TitleFieldExclusion:
    """T-3843: a ticket's `title:` frontmatter value is free-text prose
    composed at filing time, in exactly the same sense a `reason:` value
    is (T-3724) -- a feature ticket's title routinely names a config
    section/symbol/path the ticket itself is PROPOSING, which cannot
    resolve without implementing the feature it requests, and which has
    no working waive form at all (DOC006's inline-HTML-comment waive
    cannot be placed inside a YAML scalar). Positive control both
    directions, matching `TestDoc006ReasonFieldExclusion`'s shape: the
    frontmatter title is exempt (must-stay-quiet), the ticket BODY (real
    prose) still fires (must-fire), and plain docs/ prose still fires."""

    def test_single_line_title_not_flagged(self, tmp_path: Path) -> None:
        """A bogus config-section citation sitting entirely on the
        `title:` line itself (no wrap) must not fire."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        frontmatter = (
            "---\n"
            "id: T-9012\n"
            "title: 'proposes a new [check.stack] config section'\n"
            "state: queued\n"
            "kind: feature\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "---\n"
        )
        _write(tmp_path, "tickets/T-9012/ticket.md", frontmatter + "placeholder\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9012/ticket.md")

    def test_wrapped_title_not_flagged(self, tmp_path: Path) -> None:
        """MEASURED CASE (T-3843): the title is long enough that the YAML
        dumper wraps it across a continuation line, and the citation sits
        on that continuation line, not the `title:` line itself -- must
        still not fire."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        frontmatter = (
            "---\n"
            "id: T-9013\n"
            "title: 'F-099: let frob.toml declare a new [check.stack] section for\n"
            "  polyglot monorepos, mirroring [[test.runner]]'\n"
            "state: queued\n"
            "kind: feature\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "---\n"
        )
        _write(tmp_path, "tickets/T-9013/ticket.md", frontmatter + "placeholder\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9013/ticket.md")

    def test_open_ticket_body_still_flagged_alongside_title(
        self, tmp_path: Path
    ) -> None:
        """The title exemption is scoped to the frontmatter block only --
        a dangling pointer in the ticket BODY of the same open ticket must
        still fire (must-FIRE half of the positive control)."""
        _init_repo(tmp_path)
        frontmatter = (
            "---\n"
            "id: T-9014\n"
            "title: 'F-099: proposes a new [check.stack] section, wrapped across\n"
            "  two lines for good measure'\n"
            "state: queued\n"
            "kind: feature\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "---\n"
        )
        body = "Plan: touch `src/pkg/mod.py::long_gone_symbol`.\n"
        _write(tmp_path, "tickets/T-9014/ticket.md", frontmatter + body)
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert _by_rule(violations, "tickets/T-9014/ticket.md")

    def test_body_violation_below_blanked_title_reports_original_line(
        self, tmp_path: Path
    ) -> None:
        """LINE-NUMBER FIXTURE (T-3843): blanking a wrapped title must not
        shift the line number DOC006 reports for a real violation further
        down in the BODY -- line count/indentation are preserved exactly,
        so the body offender's line number is unaffected by how many
        frontmatter lines were blanked above it."""
        _init_repo(tmp_path)
        frontmatter = (
            "---\n"  # line 1
            "id: T-9015\n"  # line 2
            "title: 'F-099: proposes a new [check.stack] section, wrapped across\n"  # line 3
            "  two lines for good measure'\n"  # line 4
            "state: queued\n"  # line 5
            "kind: feature\n"  # line 6
            "origin: human\n"  # line 7
            "created: '2026-09-03'\n"  # line 8
            "---\n"  # line 9
        )
        body = "See `src/pkg/mod.py::long_gone_symbol` for the plan.\n"  # line 10
        _write(tmp_path, "tickets/T-9015/ticket.md", frontmatter + body)
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        offenders = _by_rule(violations, "tickets/T-9015/ticket.md")
        assert offenders
        assert all(v.line == 10 for v in offenders)

    def test_docs_prose_pointer_still_flagged(self, tmp_path: Path) -> None:
        """Sanity control outside the ticket ledger entirely: a
        non-resolving config-section pointer in ordinary `docs/` prose is
        unaffected by this exemption (it never touches non-ticket files)
        and must still fire."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "# Guide\n\nSee the [check.stack] config section.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert _by_rule(violations, "docs/guide.md")


# frob:ticket T-3979
class TestDoc006OldTextNewTextFieldExclusion:
    """T-3979: `acceptance_amendments[].old_text`/`.new_text` (written by
    `frob ticket accept --amend/--remove`) are free-text prose in exactly
    the sense `reason`/`title` are (T-3724/T-3843) -- with the sharper
    no-exit `old_text` adds: `--amend` is the SANCTIONED remedy for a
    DOC006 finding in a criterion's own text, and it is what WRITES the
    superseded (violating) text into `old_text`, so re-amending to clear
    the finding only appends another record carrying the same string.
    Measured on tickets/T-3976/ticket.md (T-3979's own motivating case).
    Positive control both directions, matching `TestDoc006ReasonFieldExclusion`/
    `TestDoc006TitleFieldExclusion`'s shape: the frontmatter `old_text`/
    `new_text` are exempt (must-stay-quiet), the ticket BODY (real prose)
    still fires (must-fire), and the amend-that-fixes-a-violation no-exit
    is made checkable directly."""

    def test_old_text_field_not_flagged(self, tmp_path: Path) -> None:
        """A dead config-section pointer preserved verbatim in `old_text`
        (the historical record of what a criterion used to say) must NOT
        fire -- it is by construction superseded text, never live."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        frontmatter = (
            "---\n"
            "id: T-9016\n"
            "title: placeholder\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "acceptance:\n"
            "- text: given a clean criterion, when it runs, then it passes\n"
            "  evidence: []\n"
            "acceptance_amendments:\n"
            "- op: replace\n"
            "  index: 0\n"
            "  old_text: given [[check.stack]] is implemented, when it runs,\n"
            "    then it passes\n"
            "  new_text: given a clean criterion, when it runs, then it passes\n"
            "  reason: rewritten as prose, matching T-3931/T-3976\n"
            "  actor: logan\n"
            "  at: '2026-09-03'\n"
            "---\n"
        )
        _write(tmp_path, "tickets/T-9016/ticket.md", frontmatter + "placeholder\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9016/ticket.md")

    def test_new_text_field_not_flagged(self, tmp_path: Path) -> None:
        """A PROPOSED config section named in `new_text` -- an amended
        criterion's own current wording, composed at mutation time exactly
        like `title` -- must NOT fire, mirroring T-3843's title precedent."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", "[gates]\nseverity = {}\n")
        frontmatter = (
            "---\n"
            "id: T-9017\n"
            "title: placeholder\n"
            "state: queued\n"
            "kind: feature\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "acceptance:\n"
            "- text: given a clean criterion, when it runs, then it passes\n"
            "  evidence: []\n"
            "acceptance_amendments:\n"
            "- op: replace\n"
            "  index: 0\n"
            "  old_text: stale wording\n"
            "  new_text: given the proposed [[check.stack]] section is implemented,\n"
            "    when it runs, then it passes\n"
            "  reason: reworded to name the proposed section\n"
            "  actor: logan\n"
            "  at: '2026-09-03'\n"
            "---\n"
        )
        _write(tmp_path, "tickets/T-9017/ticket.md", frontmatter + "placeholder\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9017/ticket.md")

    def test_open_ticket_body_still_flagged_alongside_old_text_and_new_text(
        self, tmp_path: Path
    ) -> None:
        """The `old_text`/`new_text` exemption is scoped to the
        frontmatter block only -- a dangling pointer in the ticket BODY of
        the same ticket must still fire (must-FIRE half of the positive
        control)."""
        _init_repo(tmp_path)
        frontmatter = (
            "---\n"
            "id: T-9018\n"
            "title: placeholder\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "acceptance:\n"
            "- text: given a clean criterion, when it runs, then it passes\n"
            "  evidence: []\n"
            "acceptance_amendments:\n"
            "- op: replace\n"
            "  index: 0\n"
            "  old_text: stale wording\n"
            "  new_text: given a clean criterion, when it runs, then it passes\n"
            "  reason: rewritten as prose\n"
            "  actor: logan\n"
            "  at: '2026-09-03'\n"
            "---\n"
        )
        body = "Plan: touch `src/pkg/mod.py::long_gone_symbol`.\n"
        _write(tmp_path, "tickets/T-9018/ticket.md", frontmatter + body)
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert _by_rule(violations, "tickets/T-9018/ticket.md")

    def test_amend_that_removes_a_doc006_violation_leaves_ticket_clean(
        self, tmp_path: Path
    ) -> None:
        """THE NO-EXIT, MADE CHECKABLE (T-3979's own acceptance criterion):
        `frob ticket accept --amend`'s sanctioned remedy for a DOC006
        violation in a criterion's own text is to rewrite it -- which
        writes the OLD, violating wording into `old_text` as an audit
        record. Before this fix that re-created the violation the amend
        was meant to clear; this asserts the amended ticket -- corrected
        `acceptance[0].text`, `new_text` matching it, and `old_text`
        carrying the original violating string verbatim, exactly the
        shape `frob ticket accept --amend` produces -- is DOC006-clean
        end to end, with no exemption of any file/section wider than the
        two prose fields this fix targets."""
        _init_repo(tmp_path)
        clean_text = "given a clean criterion, when it runs, then it passes"
        violating_text = "given [[check.stack]] is implemented, when it runs, then it passes"
        frontmatter = (
            "---\n"
            "id: T-9019\n"
            "title: placeholder\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: human\n"
            "created: '2026-09-03'\n"
            "acceptance:\n"
            f"- text: {clean_text}\n"
            "  evidence: []\n"
            "acceptance_amendments:\n"
            "- op: replace\n"
            "  index: 0\n"
            f"  old_text: {violating_text}\n"
            f"  new_text: {clean_text}\n"
            "  reason: DOC006 fires on the proposed config section written in\n"
            "    literal TOML form; rewritten as prose\n"
            "  actor: logan\n"
            "  at: '2026-09-03'\n"
            "---\n"
        )
        _write(tmp_path, "tickets/T-9019/ticket.md", frontmatter + "placeholder\n")
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-9019/ticket.md")


# frob:ticket T-3724
class TestBlankTicketReasonFields:
    """Direct unit coverage of `_blank_ticket_reason_fields`'s exact line-
    count-preserving, indent-boundary blanking logic (T-3724) -- the
    gate-level tests above prove the end-to-end DOC006 behavior, these
    pin the boundary arithmetic itself (continuation-vs-sibling-key
    indent, blank-line-inside-continuation, non-frontmatter passthrough)
    so a future edit cannot silently shift an off-by-one here."""

    def test_non_frontmatter_text_untouched(self) -> None:
        """No leading `---` line at all -- both `not lines` and `not
        _FRONTMATTER_DELIM_RE.match(...)` must independently short-circuit
        to a no-op (pins the `or`, not just one operand)."""
        text = "plain text\nno frontmatter here\n"
        assert _blank_ticket_reason_fields(text) == text

    def test_empty_text_untouched(self) -> None:
        """`lines` empty -- the other half of the `not lines or ...` guard."""
        assert _blank_ticket_reason_fields("") == ""

    def test_unterminated_frontmatter_untouched(self) -> None:
        """Opening `---` with no closing `---` -- `end` stays `None`, text
        passes through unchanged rather than blanking past EOF."""
        text = "---\nreason: foo\nno closing delimiter\n"
        assert _blank_ticket_reason_fields(text) == text

    def test_reason_value_blanked_key_kept(self) -> None:
        """The inline value after `reason:` is removed but the `key:`
        prefix survives verbatim (pins the exact slice arithmetic, not an
        off-by-one that eats or leaves a stray character)."""
        text = "---\nreason: mentions `pkg.mod::gone` here\n---\nbody\n"
        out = _blank_ticket_reason_fields(text)
        lines = out.splitlines()
        assert lines[1] == "reason:"
        assert len(lines) == len(text.splitlines())

    def test_continuation_indented_more_is_blanked(self) -> None:
        """A wrapped continuation line indented MORE than the `reason:`
        key is blanked -- and a SIBLING key at the SAME indent right after
        it is left completely untouched (pins the strict `>` boundary,
        not `>=`)."""
        text = (
            "---\n"
            "- op: remove\n"
            "  reason: first line\n"
            "    wrapped continuation `pkg.mod::gone`\n"
            "  actor: logan\n"
            "---\n"
        )
        out = _blank_ticket_reason_fields(text)
        lines = out.splitlines()
        assert lines[3] == ""
        assert lines[4] == "  actor: logan"
        assert len(lines) == len(text.splitlines())

    def test_blank_line_inside_continuation_also_blanked(self) -> None:
        """A genuinely blank line inside a wrapped continuation keeps
        being swallowed by the continuation loop (pins the `strip() ==
        ""` disjunct, not just the indent-depth disjunct) -- the sibling
        key that follows is still reached and left alone."""
        text = (
            "---\n"
            "- op: remove\n"
            "  reason: first line\n"
            "\n"
            "    more continuation text\n"
            "  actor: logan\n"
            "---\n"
        )
        out = _blank_ticket_reason_fields(text)
        lines = out.splitlines()
        assert lines[3] == ""
        assert lines[4] == ""
        assert lines[5] == "  actor: logan"

    def test_reason_key_on_last_frontmatter_line_no_overrun(self) -> None:
        """A `reason:` key sitting on the LAST line before the closing
        `---` must not read or blank past `end` (pins the outer `while i
        < end` bound, not an off-by-one that touches the delimiter
        itself)."""
        text = "---\nid: T-1\nreason: trailing value\n---\nbody\n"
        out = _blank_ticket_reason_fields(text)
        lines = out.splitlines()
        assert lines[2] == "reason:"
        assert lines[3] == "---"
        assert len(lines) == len(text.splitlines())

    def test_title_value_blanked_key_kept(self) -> None:
        """T-3843: `title:` is blanked exactly like a `reason:` key --
        same slice arithmetic, same key-kept/value-removed shape."""
        text = "---\ntitle: mentions `pkg.mod::gone` here\n---\nbody\n"
        out = _blank_ticket_reason_fields(text)
        lines = out.splitlines()
        assert lines[1] == "title:"
        assert len(lines) == len(text.splitlines())

    def test_wrapped_title_continuation_blanked_line_count_preserved(
        self,
    ) -> None:
        """T-3843's MEASURED case at the unit level: a `title:` value that
        wraps onto an indented continuation line (the YAML dumper's
        long-scalar wrap) is blanked across both lines, a sibling key
        right after it is left untouched, and total line count is
        unchanged."""
        text = (
            "---\n"
            "id: T-1\n"
            "title: 'F-099: proposes a new [check.stack] section for\n"
            "  polyglot monorepos'\n"
            "state: queued\n"
            "---\n"
        )
        out = _blank_ticket_reason_fields(text)
        lines = out.splitlines()
        assert lines[2] == "title:"
        assert lines[3] == ""
        assert lines[4] == "state: queued"
        assert len(lines) == len(text.splitlines())

    def test_reason_key_blanking_not_regressed_by_title_addition(
        self,
    ) -> None:
        """No-regression fixture: adding `title` to the shared prose-key
        regex must not change `reason:`'s own blanking behavior."""
        text = "---\nreason: mentions `pkg.mod::gone` here\n---\nbody\n"
        out = _blank_ticket_reason_fields(text)
        lines = out.splitlines()
        assert lines[1] == "reason:"
        assert len(lines) == len(text.splitlines())


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


class TestDoc004Doc006ZeroOnFrobsOwnRepo:
    """T-2374's closure-bar evidence: DOC004 and DOC006, run against THIS
    repo's own live tree with its real waivers applied, report zero
    findings -- the epic's (T-0969) acceptance criterion [0]. Mirrors
    `tests/unit/strata/test_sys003_calibration.py::
    TestSys003ZeroOnFrobsOwnRepo`, T-2407's precedent for the same
    burn-to-zero-then-promote shape: filtered to the two rules this
    ticket owns rather than asserting the whole gate output is empty,
    because the surrounding DOC family carries unrelated pre-existing
    DOC001/DOC002/DOC005 findings outside this ticket's scope."""

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="full-repo live-scan (frob self-conformance) is too slow on the "
        "Windows CI runner and timeout-crashes its xdist worker, aborting the "
        "whole suite; platform-independent, covered by the Linux/macOS legs (T-3754)",
    )
    def test_doc004_doc006_zero_against_live_repo(self, tmp_path: Path) -> None:
        from frob.gates import _apply_waivers, doc004_gate
        from frob.gates._docptr import doc006_gate

        repo_root = Path(__file__).resolve().parents[1]
        snapshot = build_graph(repo_root, tmp_path / "cache.db").danger_ok
        raw = tuple(doc004_gate(repo_root, snapshot)) + tuple(
            doc006_gate(repo_root, snapshot)
        )
        kept, _waived = _apply_waivers(raw, snapshot)
        offenders = [v for v in kept if v.rule in ("DOC004", "DOC006")]
        assert offenders == [], f"unexpected DOC004/DOC006 finding(s): {offenders}"

    # frob:ticket T-3485
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="scans changelog.d (900+ files) live; too slow on the Windows CI "
        "runner and timeout-crashes its xdist worker; platform-independent, "
        "covered by the Linux/macOS legs (T-3754)",
    )
    def test_changelog_d_fragment_doc006_zero(self, tmp_path: Path) -> None:
        """T-3485: a targeted pin on changelog.d/T-2691.md's own DOC006
        result, independent of the whole-repo assertion above -- that
        assertion can fail for an UNRELATED reason elsewhere in the tree
        (e.g. a still-open sibling regression on a different file), which
        would make this ticket's own fix un-evidenceable via the repo-
        wide test alone. Filters to this one fragment's findings so this
        test passes exactly when T-3485's own fix (repairing the mid-
        word-wrapped symbol pointer and the intentionally-nonexistent
        `frob ticket land-status` CLI pointer) is in place, regardless of
        any other file's independent state."""
        from frob.gates._docptr import doc006_gate

        repo_root = Path(__file__).resolve().parents[1]
        snapshot = build_graph(repo_root, tmp_path / "cache.db").danger_ok
        violations = doc006_gate(repo_root, snapshot)
        offenders = [v for v in violations if v.file == "changelog.d/T-2691.md"]
        assert offenders == [], f"unexpected DOC006 finding(s): {offenders}"

    def test_doc004_doc006_are_error_severity(self, tmp_path: Path) -> None:
        """The other half of T-2374: a zero that leaves the gate advisory
        lets the debt silently reaccumulate, so the severity freeze is
        asserted here alongside the zero it protects."""
        from frob.gates._docblocks_shared import _doc004_violation
        from frob.gates._docptr import _doc006_violation

        assert (
            _doc004_violation("docs/x.md", 1, tier="unbound", detail="d").severity
            == Severity.ERROR
        )
        assert (
            _doc006_violation("docs/x.md", 1, detail="d", kind="file/path").severity
            == Severity.ERROR
        )
