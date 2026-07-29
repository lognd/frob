"""Tests for frob.gates._docblocks -- DOC004 unbound/stale fenced-code-block
doc-drift heuristic (docs/modules/gates.md#doc004-unbound-stale-doc-code-blocks,
T-0436).

Fixtures are synthetic tempfile-backed git repos with a real graph built via
`frob.graph.build_graph`, same posture as `tests/test_fuzz.py`'s snapshot
fixtures -- DOC004 needs a real `GraphSnapshot` to resolve python symbols
against, unlike `ref_gate` (root-only).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._docblocks import doc004_gate, doc005_gate
from frob.gates._models import Severity
from frob.graph import build_graph


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
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


def _snapshot(root: Path):
    return build_graph(root, root / ".frob" / "cache.db").danger_ok


def _rule_ids(violations, file: str) -> list[str]:
    return [v.rule for v in violations if v.file == file]


class TestPythonNamespace:
    """Python: pyproject.toml [project.name] derives the namespace; a
    `from <ns> import <missing>` is flagged stale, a resolving one passes."""

    def test_python_import_of_nonexistent_symbol_is_stale(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "pyproject.toml",
            '[project]\nname = "widget"\n',
        )
        _write(
            tmp_path,
            "src/widget/__init__.py",
            "",
        )
        _write(
            tmp_path,
            "src/widget/core.py",
            "def real_func() -> None:\n    pass\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "```python\nfrom widget.core import real_func, fake_func\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        rules = _rule_ids(violations, "docs/guide.md")
        assert "DOC004" in rules
        stale = [v for v in violations if v.severity == Severity.ERROR]
        assert any("fake_func" in v.message for v in stale)
        assert not any("real_func" in v.message for v in stale)

    def test_anchored_block_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "widget"\n')
        _write(tmp_path, "src/widget/__init__.py", "")
        _write(
            tmp_path,
            "src/widget/core.py",
            "def real_func() -> None:\n    pass\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "<!-- frob:describes src/widget/core.py::real_func -->\n\n"
            "```python\nfrom widget.core import real_func\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []

    def test_unanchored_but_valid_import_warns_unbound(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "widget"\n')
        _write(tmp_path, "src/widget/__init__.py", "")
        _write(
            tmp_path,
            "src/widget/core.py",
            "def real_func() -> None:\n    pass\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "```python\nfrom widget.core import real_func\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        matches = [v for v in violations if v.file == "docs/guide.md"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARN
        assert matches[0].rule == "DOC004"

    def test_waive_doc004_suppresses(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "widget"\n')
        _write(tmp_path, "src/widget/__init__.py", "")
        _write(
            tmp_path,
            "docs/guide.md",
            '<!-- frob:waive DOC004 reason="intentional illustrative example" -->\n\n'
            "```python\nfrom widget import totally_fake_symbol\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []

    def test_generic_external_shell_block_not_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "widget"\n')
        _write(tmp_path, "src/widget/__init__.py", "")
        _write(
            tmp_path,
            "docs/guide.md",
            "```console\ngit status\nls -la\n```\n\n"
            "```python\nimport numpy as np\nnp.array([1, 2, 3])\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []

    def test_package_name_differs_from_directory_name(self, tmp_path: Path) -> None:
        """pyproject.toml's [project].name (not the checkout dir name) is
        the namespace root -- T-0436 refinement 3's `logand.app` example,
        mirrored here as a package literally named unlike its repo dir."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "pyproject.toml",
            '[project]\nname = "acme-widgets"\n',
        )
        _write(tmp_path, "src/acme_widgets/__init__.py", "")
        _write(
            tmp_path,
            "docs/guide.md",
            "```python\nfrom acme_widgets import nonexistent_thing\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        stale = [v for v in violations if v.severity == Severity.ERROR]
        assert any("nonexistent_thing" in v.message for v in stale)


class TestRustNamespace:
    """Rust: [workspace].members subcrates are each their own namespace; a
    `use <subcrate>::missing` is stale, `use <external-crate>::x` is skipped."""

    def _write_workspace(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "Cargo.toml",
            '[workspace]\nmembers = ["crates/core"]\n',
        )
        _write(
            tmp_path,
            "crates/core/Cargo.toml",
            '[package]\nname = "acme-core"\nversion = "0.1.0"\n',
        )
        _write(
            tmp_path,
            "crates/core/src/lib.rs",
            "pub fn real_thing() -> i32 { 42 }\n",
        )

    def test_rust_use_of_missing_item_is_stale(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        self._write_workspace(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            "```rust\nuse acme_core::missing_thing;\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        stale = [v for v in violations if v.severity == Severity.ERROR]
        assert any("missing_thing" in v.message for v in stale)

    def test_rust_use_of_real_item_passes_or_warns_never_stale(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        self._write_workspace(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            "<!-- frob:describes crates/core/src/lib.rs::real_thing -->\n\n"
            "```rust\nuse acme_core::real_thing;\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []

    def test_external_crate_use_not_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        self._write_workspace(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            "```rust\nuse tokio::spawn;\nuse serde::Serialize;\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []


# frob:ticket T-0566
class TestCCppNamespace:
    """C/C++: a quoted `#include "..."` of a file this repo actually
    tracks is a real project reference (UNBOUND if unanchored); a quoted
    include that resolves to no tracked file (illustrative/external) is
    skipped; angle-bracket system includes are never flagged."""

    def test_include_of_tracked_header_unanchored_warns(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "include/acme/core.h", "#pragma once\nint acme_init(void);\n")
        _write(
            tmp_path,
            "docs/guide.md",
            '```c\n#include "include/acme/core.h"\nacme_init();\n```\n',
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        warns = [v for v in violations if v.severity == Severity.WARN]
        assert any("not anchored" in v.message for v in warns)

    def test_include_of_tracked_header_anchored_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "include/acme/core.h", "#pragma once\nint acme_init(void);\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "<!-- frob:describes include/acme/core.h -->\n\n"
            '```c\n#include "include/acme/core.h"\nacme_init();\n```\n',
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []

    def test_include_resolving_to_no_tracked_file_not_flagged(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "README.md", "placeholder\n")
        _write(
            tmp_path,
            "docs/guide.md",
            '```cpp\n#include "some/other/projects/header.hpp"\n```\n',
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []

    def test_angle_bracket_system_include_never_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "README.md", "placeholder\n")
        _write(
            tmp_path,
            "docs/guide.md",
            "```c\n#include <stdio.h>\nint main(void) { return 0; }\n```\n",
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []

    def test_waive_suppresses_unbound_c_include(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "include/acme/core.h", "#pragma once\n")
        _write(
            tmp_path,
            "docs/guide.md",
            '<!-- frob:waive DOC004 reason="illustrative" -->\n\n'
            '```c\n#include "include/acme/core.h"\n```\n',
        )
        _git(tmp_path, "add", "-A")

        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _rule_ids(violations, "docs/guide.md") == []


# frob:waive DEAD001 reason="loaded dynamically via importlib.import_module by doc005_gate's _load_parser_factory (dotted-path config value), never a direct call-graph caller"  # noqa: E501
def _fake_parser_factory():
    """A tiny synthetic `argparse.ArgumentParser` with two top-level
    subcommands (`widget`, `gadget`) -- importable via
    `tests.test_docblocks_gate:_fake_parser_factory` (`tests/` is a real
    package), the same "own real CLI as configured source" posture
    `TestDoc004ConsoleCommandDrift` uses for frob's own `_build_parser`,
    kept independent here so DOC005's tests never depend on frob's own
    live command count drifting underneath them."""
    import argparse

    parser = argparse.ArgumentParser(prog="acme")
    sub = parser.add_subparsers(dest="subcommand")
    sub.add_parser("widget", help="widget things")
    sub.add_parser("gadget", help="gadget things")
    return parser


_FAKE_CONFIG = (
    '[[docblocks.commands]]\nprog = "acme"\n'
    'parser = "tests.test_docblocks_gate:_fake_parser_factory"\n'
)


class TestDoc005ReadmeTableDrift:
    """T-0435: DOC005 binds README.md's command table (and any "N
    commands" count claim) to the live top-level subcommand registry --
    the same `[[docblocks.commands]]` config DOC004's console tier reads,
    walked via a synthetic two-command CLI so these tests never depend on
    frob's own live command count."""

    def test_missing_row_for_real_command_fails(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(
            tmp_path,
            "README.md",
            "## Commands\n\n| Command | Description |\n"
            "|---|---|\n| `acme widget` | does widget things |\n",
        )
        _git(tmp_path, "add", "-A")

        violations = doc005_gate(tmp_path)

        assert any(
            v.rule == "DOC005"
            and v.severity == Severity.ERROR
            and "gadget" in v.message
            for v in violations
        )

    def test_stale_row_for_removed_command_fails(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(
            tmp_path,
            "README.md",
            "## Commands\n\n| Command | Description |\n"
            "|---|---|\n"
            "| `acme widget` | does widget things |\n"
            "| `acme gadget` | does gadget things |\n"
            "| `acme thingamajig` | no longer exists |\n",
        )
        _git(tmp_path, "add", "-A")

        violations = doc005_gate(tmp_path)

        assert any(
            v.rule == "DOC005"
            and v.severity == Severity.ERROR
            and "thingamajig" in v.message
            for v in violations
        )

    def test_fully_covered_table_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(
            tmp_path,
            "README.md",
            "## Commands\n\n| Command | Description |\n"
            "|---|---|\n"
            "| `acme widget` | does widget things |\n"
            "| `acme gadget` | does gadget things |\n",
        )
        _git(tmp_path, "add", "-A")

        violations = doc005_gate(tmp_path)

        assert violations == ()

    def test_count_claim_mismatch_fails(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(
            tmp_path,
            "README.md",
            "## Commands\n\n3 total commands.\n\n"
            "| Command | Description |\n"
            "|---|---|\n"
            "| `acme widget` | does widget things |\n"
            "| `acme gadget` | does gadget things |\n",
        )
        _git(tmp_path, "add", "-A")

        violations = doc005_gate(tmp_path)

        assert any(
            v.rule == "DOC005"
            and v.severity == Severity.ERROR
            and "claims 3" in v.message
            for v in violations
        )

    def test_count_claim_matching_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(
            tmp_path,
            "README.md",
            "## Commands\n\n2 total commands.\n\n"
            "| Command | Description |\n"
            "|---|---|\n"
            "| `acme widget` | does widget things |\n"
            "| `acme gadget` | does gadget things |\n",
        )
        _git(tmp_path, "add", "-A")

        violations = doc005_gate(tmp_path)

        assert violations == ()

    def test_no_config_means_no_readme_checking(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "README.md",
            "## Commands\n\n| Command | Description |\n"
            "|---|---|\n| `acme thingamajig` | stale but unconfigured |\n",
        )
        _git(tmp_path, "add", "-A")

        violations = doc005_gate(tmp_path)

        assert violations == ()


_CLI_DOC_TEMPLATE = (
    "# cli doc\n\n<!-- frob:generated-start cli-commands T-1011 -->\n\n"
    "{body}"
    "\n<!-- frob:generated-end cli-commands T-1011 -->\n"
)


# invariant spec: [INV-045](invariants/INV-045.md)
class TestCliCommandTableGenerator:
    """T-1011(b): `generate_cli_command_table`/`sync_cli_command_table`
    regenerate `docs/modules/cli.md`'s marked block from the live argparse
    registry, and `doc005_gate` flags the block ERROR when it drifts from
    a fresh regeneration -- reuses `TestDoc005ReadmeTableDrift`'s synthetic
    `acme widget`/`acme gadget` CLI (`_fake_parser_factory`) so these
    tests never depend on frob's own live command count."""

    def test_generate_sorts_rows_across_sources(self, tmp_path: Path) -> None:
        from frob.gates._docblocks import generate_cli_command_table

        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _git(tmp_path, "add", "-A")

        generated = generate_cli_command_table(tmp_path)

        assert generated is not None
        assert "<!-- frob:generated-start cli-commands T-1011 -->" in generated
        assert "<!-- frob:generated-end cli-commands T-1011 -->" in generated
        assert "| `acme gadget` | gadget things |" in generated
        assert "| `acme widget` | widget things |" in generated
        # sorted: gadget before widget.
        assert generated.index("gadget") < generated.index("widget")

    def test_generate_no_config_is_none(self, tmp_path: Path) -> None:
        from frob.gates._docblocks import generate_cli_command_table

        _init_repo(tmp_path)
        _git(tmp_path, "add", "-A")

        assert generate_cli_command_table(tmp_path) is None

    def test_sync_replaces_only_the_marked_block(self, tmp_path: Path) -> None:
        from frob.gates._docblocks import sync_cli_command_table

        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(
            tmp_path,
            "docs/modules/cli.md",
            "before\n\n" + _CLI_DOC_TEMPLATE.format(body="") + "\nafter\n",
        )
        _git(tmp_path, "add", "-A")

        wrote = sync_cli_command_table(tmp_path)

        assert wrote is True
        text = (tmp_path / "docs/modules/cli.md").read_text()
        assert "before\n" in text
        assert "after\n" in text
        assert "| `acme widget` | widget things |" in text

        # idempotent: a second sync leaves it byte-identical.
        again_text_before = text
        wrote_again = sync_cli_command_table(tmp_path)
        assert wrote_again is True
        assert (tmp_path / "docs/modules/cli.md").read_text() == again_text_before

    def test_sync_no_markers_returns_false(self, tmp_path: Path) -> None:
        from frob.gates._docblocks import sync_cli_command_table

        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(tmp_path, "docs/modules/cli.md", "no markers here\n")
        _git(tmp_path, "add", "-A")

        assert sync_cli_command_table(tmp_path) is False

    def test_doc005_freshness_flags_stale_generated_block(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(
            tmp_path,
            "docs/modules/cli.md",
            _CLI_DOC_TEMPLATE.format(body="| `acme thingamajig` | stale row |\n"),
        )
        _git(tmp_path, "add", "-A")

        violations = doc005_gate(tmp_path)

        assert any(
            v.rule == "DOC005"
            and v.severity == Severity.ERROR
            and "docs/modules/cli.md" in v.file
            and "stale" in v.message
            for v in violations
        )

    def test_doc005_freshness_passes_after_sync(self, tmp_path: Path) -> None:
        from frob.gates._docblocks import sync_cli_command_table

        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _FAKE_CONFIG)
        _write(tmp_path, "docs/modules/cli.md", _CLI_DOC_TEMPLATE.format(body=""))
        _git(tmp_path, "add", "-A")

        assert sync_cli_command_table(tmp_path) is True

        violations = doc005_gate(tmp_path)

        assert not any(
            v.rule == "DOC005" and "docs/modules/cli.md" in v.file for v in violations
        )
