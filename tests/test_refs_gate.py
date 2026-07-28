"""Tests for frob.gates._refs -- REF001/REF002/REF003 anti-orphan gate
(docs/modules/gates.md#anti-orphan-file-reference-gate-t-0396).

Fixtures are synthetic tempfile-backed git repos, same posture as
`tests/test_pii_structural_gate.py` and `tests/test_secrets_gate.py`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._models import Severity
from frob.gates._refs import ref_gate


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


def _rule_ids(violations, file: str) -> list[str]:
    """Rule ids reported against exactly `file`, in report order."""
    return [v.rule for v in violations if v.file == file]


class TestTiers:
    """REF001 (0 refs), REF002 (1 ref), pass (2+ refs) -- docs/modules/gates.md's
    tier table, T-0396 acceptance criterion (4)."""

    def test_zero_refs_warns_ref001(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "orphan.yaml", "key: value\n")
        _write(tmp_path, "unrelated.md", "nothing here references anything\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "orphan.yaml") == ["REF001"]

    def test_one_ref_weak_warns_ref002(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "single.yaml", "key: value\n")
        _write(tmp_path, "consumer.py", 'load("single.yaml")\n')
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "single.yaml") == ["REF002"]

    def test_two_refs_passes(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "double.yaml", "key: value\n")
        _write(tmp_path, "consumer_a.py", 'load("double.yaml")\n')
        _write(tmp_path, "consumer_b.py", 'load("double.yaml")\n')
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "double.yaml") == []


class TestUsedByDeclaration:
    """`frob:used-by` DECLARE-WHERE-USED: a valid declaration passes, a
    dangling one fails (REF003) -- T-0396 acceptance criterion (2)."""

    def test_valid_declaration_counts_not_dangling(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "declared.yaml",
            "# frob:used-by consumer.py\nkey: value\n",
        )
        # consumer.py DOES spell the literal basename as a quoted string
        # (a real reference position, not bare prose), so the declaration
        # verifies as real -- the case the ticket's declaration mechanism
        # exists for is a path built at runtime the auto-scan structurally
        # cannot see even when a real reference position exists elsewhere.
        _write(tmp_path, "consumer.py", 'name = "declared.yaml"\n')
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        # One valid, verified consumer -> REF002 (single anchor), never
        # REF003 (dangling) -- the declaration is real, just still fragile
        # at exactly one reference.
        assert _rule_ids(violations, "declared.yaml") == ["REF002"]
        assert "REF003" not in [v.rule for v in violations]

    def test_dangling_declaration_nonexistent_consumer_fails(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "dangling.yaml",
            "# frob:used-by does_not_exist.py\nkey: value\n",
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF003" in _rule_ids(violations, "dangling.yaml")
        # And the orphan tier still fires independently -- a dangling
        # declaration is not evidence of use, so it must not suppress
        # REF001/REF002 either.
        assert "REF001" in _rule_ids(violations, "dangling.yaml")

    def test_dangling_declaration_non_reaching_consumer_fails(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "unreached.yaml",
            "# frob:used-by consumer.py\nkey: value\n",
        )
        # consumer.py exists but never mentions unreached.yaml at all --
        # the declaration names a real file that does not actually reach
        # this one, which must fail exactly like a nonexistent consumer.
        _write(tmp_path, "consumer.py", "print('hello')\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF003" in _rule_ids(violations, "unreached.yaml")


class TestEntrypointAllowlist:
    """`[[refs.entrypoint]]` frob.toml table exempts declared entry points
    -- T-0396 acceptance criterion (3)."""

    def test_allowlisted_file_is_exempt(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "README.md", "# nothing references this either\n")
        _write(
            tmp_path,
            "frob.toml",
            '[[refs.entrypoint]]\npath = "README.md"\nreason = "read by humans"\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "README.md") == []

    def test_non_allowlisted_orphan_still_fires(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "README.md", "# nothing references this either\n")
        _write(tmp_path, "also_orphan.md", "# also nothing references this\n")
        _write(
            tmp_path,
            "frob.toml",
            '[[refs.entrypoint]]\npath = "README.md"\nreason = "read by humans"\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "README.md") == []
        assert "REF001" in _rule_ids(violations, "also_orphan.md")


class TestNativeStubLinking:
    """T-0449: a `.pyi` sidecar beside a `pyproject.toml` whose
    `[tool.maturin] module-name` matches the stub's stem is a genuine
    LINKED reference (the manifest counts as a real inbound edge), not an
    exemption -- a `.pyi` with no such adjacent manifest still fires
    REF001 like any other orphan file.

    frob:ticket T-0449
    """

    def test_linked_pyi_beside_matching_manifest_does_not_fire_ref001(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "somecrate/somecrate_native.pyi",
            '"""Typed surface of the somecrate_native extension."""\n\n'
            "def do_thing(x: int) -> int: ...\n",
        )
        _write(
            tmp_path,
            "somecrate/pyproject.toml",
            "[build-system]\n"
            'requires = ["maturin>=1.7,<2"]\n'
            'build-backend = "maturin"\n\n'
            "[tool.maturin]\n"
            'module-name = "somecrate_native"\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" not in _rule_ids(violations, "somecrate/somecrate_native.pyi")

    def test_unlinked_pyi_with_no_adjacent_module_still_fires_ref001(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "orphan_stub/orphan_stub.pyi",
            '"""Nobody builds this -- no adjacent manifest names it."""\n\n'
            "def do_thing(x: int) -> int: ...\n",
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" in _rule_ids(violations, "orphan_stub/orphan_stub.pyi")

    def test_pyi_with_manifest_present_but_module_name_mismatch_still_fires(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "somecrate/somecrate_native.pyi",
            '"""Typed surface of a different extension name."""\n\n'
            "def do_thing(x: int) -> int: ...\n",
        )
        _write(
            tmp_path,
            "somecrate/pyproject.toml",
            '[tool.maturin]\nmodule-name = "totally_different_name"\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" in _rule_ids(violations, "somecrate/somecrate_native.pyi")


class TestSeverityAndDegrade:
    """WARN-only posture and no-tracked-files degrade path."""

    def test_all_violations_are_warn_severity(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "orphan.yaml", "key: value\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert all(v.severity is Severity.WARN for v in violations)

    def test_no_tracked_files_returns_empty(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)

        violations = ref_gate(tmp_path)

        assert violations == ()


class TestReferenceDetection:
    """The auto-scan's syntactic-position discipline: a real reference
    (quoted literal, markdown link, import) counts, a bare prose mention
    of a filename does not -- the exact false positive T-0396's own
    dogfooding run against this repo caught and required fixing."""

    def test_bare_prose_mention_does_not_count_as_a_reference(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "manifest.yaml", "key: value\n")
        _write(
            tmp_path,
            "README.md",
            "The `manifest.yaml` file lists things, but nothing loads it.\n",
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" in _rule_ids(violations, "manifest.yaml")

    def test_markdown_link_counts_as_a_reference(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "linked.yaml", "key: value\n")
        _write(tmp_path, "README.md", "See [the manifest](linked.yaml) for detail.\n")
        _write(tmp_path, "other.md", "Also [linked](linked.yaml) from here.\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "linked.yaml") == []


class TestReviewerRegressionRound2:
    """T-0396 round-2, reviewer-rejected the first landing for an 86%
    false-positive rate (326/379 REF001 were detector gaps, not real
    orphans). Regression coverage for the two cited bugs (multi-name
    `from X import a, b, c` only capturing the module prefix; a pytest-
    collected test file being a permanent false orphan by filesystem
    convention), plus confirmation that fixing them does not silently
    un-flag a genuine orphan."""

    def test_multi_name_from_import_target_not_flagged(self, tmp_path: Path) -> None:
        # Reviewer's cited case: `from frob.arch import _cpp, _python` only
        # captured `frob.arch` (the module prefix), never `_cpp`/`_python`
        # themselves -- so a module reached ONLY via a multi-name
        # from-import was a permanent false REF001/REF002 orphan.
        _init_repo(tmp_path)
        _write(tmp_path, "pkg/_cpp.py", "def check(): pass\n")
        _write(tmp_path, "pkg/_python.py", "def check(): pass\n")
        _write(
            tmp_path,
            "pkg/__init__.py",
            "from pkg import _cpp, _python\n_cpp.check()\n_python.check()\n",
        )
        # A second, independent consumer so the fixture demonstrates a real
        # 2+ pass, not merely "not zero".
        _write(tmp_path, "caller.py", "from pkg import _cpp\n_cpp.check()\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "pkg/_cpp.py") == []
        assert _rule_ids(violations, "pkg/_python.py") != ["REF001"]

    def test_parenthesized_from_import_target_not_flagged(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "pkg/_alpha.py", "def run(): pass\n")
        _write(tmp_path, "pkg/_beta.py", "def run(): pass\n")
        _write(
            tmp_path,
            "pkg/__init__.py",
            "from pkg import (\n    _alpha,\n    _beta,\n)\n_alpha.run()\n_beta.run()\n",
        )
        _write(tmp_path, "caller.py", "from pkg import _alpha\n_alpha.run()\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "pkg/_alpha.py") == []

    def test_dispatch_table_bare_string_target_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # Reviewer's cited case: `_RUNNER_MODULE_NAMES` maps a bare quoted
        # string ("ack_runner") to a module file (ack_runner.py) via a
        # dynamic dispatch table, never a literal `import` statement.
        _init_repo(tmp_path)
        _write(tmp_path, "app/ack_runner.py", "def run(): pass\n")
        _write(
            tmp_path,
            "app/dispatch.py",
            'RUNNER_MODULE_NAMES = ["ack_runner", "other_runner"]\n',
        )
        _write(
            tmp_path,
            "app/loader.py",
            'import importlib\nimportlib.import_module("app.ack_runner")\n',
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "app/ack_runner.py") == []

    def test_pytest_collected_test_file_not_flagged(self, tmp_path: Path) -> None:
        # Reviewer's cited systemic case: 197/379 (52%) of the original
        # false REF001s were test files reached only by pytest's own
        # discovery convention (tests/**, test_*.py), never by another
        # tracked file's text -- a real, collected test file IS referenced,
        # by the test runner, and must not be a permanent orphan.
        _init_repo(tmp_path)
        _write(tmp_path, "tests/test_something.py", "def test_ok():\n    assert True\n")
        _write(tmp_path, "unrelated.md", "nothing here references anything\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "tests/test_something.py") == []

    def test_dead_non_test_file_under_tests_dir_still_fires(
        self, tmp_path: Path
    ) -> None:
        # Round-3, reviewer-caught FALSE NEGATIVE: `frob.excludes.
        # is_test_file` exempts ANY path with a `tests/` directory
        # component, not just files that are themselves tests -- so a
        # genuinely-orphaned fixture/helper file that merely LIVES under
        # tests/ (no test_* name, no test functions, imported nowhere)
        # was silently exempted too. It must still fire REF001.
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "tests/fixtures/orphan_helper.py",
            "def build_fixture():\n    return {}\n",
        )
        _write(tmp_path, "tests/test_something.py", "def test_ok():\n    assert True\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" in _rule_ids(violations, "tests/fixtures/orphan_helper.py")
        # The real test file alongside it must still be exempt -- this is
        # not a regression of the round-2 fix, only a narrowing of it.
        assert _rule_ids(violations, "tests/test_something.py") == []

    def test_registry_style_yaml_with_only_prose_mentions_still_fires(
        self, tmp_path: Path
    ) -> None:
        # The exact shape of the motivating case: a registry yaml named
        # only in OTHER docs' prose/table cells (backtick code spans, not
        # real markdown links or import/quoted-path literals) must still
        # be a REF001 orphan after the fix -- the fix must not regress the
        # very case this gate was built for.
        _init_repo(tmp_path)
        _write(tmp_path, "docs/registry/manifest.yaml", "key: value\n")
        _write(
            tmp_path,
            "docs/registry/README.md",
            "| `manifest.yaml` | some domain | 42 entries |\n",
        )
        _write(
            tmp_path,
            "tickets.md",
            "Reconcile docs/registry/manifest.yaml against actual enforcement.\n",
        )
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" in _rule_ids(violations, "docs/registry/manifest.yaml")

    def test_genuinely_unreferenced_module_still_fires(self, tmp_path: Path) -> None:
        # A module reached by nothing at all -- no import, no quoted
        # string, no markdown link, no directive -- must still fire
        # REF001 after the fix; fixing the import/dispatch-table/test-file
        # gaps must not silently widen into a blanket false-pass.
        _init_repo(tmp_path)
        _write(tmp_path, "pkg/_truly_dead.py", "def unused(): pass\n")
        _write(tmp_path, "pkg/__init__.py", "# nothing imports _truly_dead here\n")
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" in _rule_ids(violations, "pkg/_truly_dead.py")


class TestMarkdownWaive:
    """T-0466: a `.md`-embedded `frob:waive REF001/REF002 reason="..."`
    is text-scanned and honored directly, the same way `_docblocks.py`
    honors `frob:waive DOC004` on a doc -- `frob.graph` has no edge to
    attach a waiver to on a bare tracked `.md` file."""

    def test_ref002_on_md_doc_suppressed_by_inline_waive(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "docs/single.md",
            '# Single\n\nfrob:waive REF002 reason="one anchor is intentional"\n',
        )
        _write(tmp_path, "consumer.py", 'load("docs/single.md")\n')
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "docs/single.md") == []

    def test_ref002_on_md_doc_without_waive_still_fires(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "docs/single.md", "# Single\n\nno waiver here\n")
        _write(tmp_path, "consumer.py", 'load("docs/single.md")\n')
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert _rule_ids(violations, "docs/single.md") == ["REF002"]


class TestBacktickTokenizer:
    """T-0467: a backtick-wrapped path mention (`` `docs/target.md` ``,
    the repo's own doc convention) counts as a real inbound reference --
    previously only "/'-quoted strings and markdown `[]()` links were
    tokenized, so a doc referenced ONLY via a backtick mention was a
    false-positive REF001 orphan."""

    def test_backtick_wrapped_path_mention_counts_as_reference(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write(tmp_path, "docs/target.md", "# Target\n\nsome content\n")
        _write(
            tmp_path,
            "docs/index.md",
            "# Index\n\nSee `docs/target.md` for details.\n",
        )
        _write(tmp_path, "consumer.py", 'load("docs/index.md")\n')
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" not in _rule_ids(violations, "docs/target.md")

    def test_backtick_wrapped_bare_identifier_not_treated_as_reference(
        self, tmp_path: Path
    ) -> None:
        # A backtick-wrapped bare code identifier (no `/`, no extension)
        # must NOT be misread as a path reference -- only path-SHAPED
        # backtick content counts.
        _init_repo(tmp_path)
        _write(tmp_path, "orphan.yaml", "key: value\n")
        _write(
            tmp_path,
            "docs/mentions.md",
            "# Mentions\n\nCall `_reaches` to check reachability.\n",
        )
        _write(tmp_path, "consumer.py", 'load("docs/mentions.md")\n')
        _git(tmp_path, "add", "-A")

        violations = ref_gate(tmp_path)

        assert "REF001" in _rule_ids(violations, "orphan.yaml")
