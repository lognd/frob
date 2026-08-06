"""Unit tests for T-1150 `frob sys sync-interface`
(`frob.strata._sync_interface`): mechanical `interface=` attr upkeep
against the measured real public surface (module docstring)."""

from __future__ import annotations

from pathlib import Path

from frob.strata import StrataError
from frob.strata._code_binding import bind_code
from frob.strata._elaborate import elaborate
from frob.strata._parse import parse_module
from frob.strata._sync_interface import apply_sync_interface, sync_interface_report


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _write_design(root: Path, design_dir: str, rel: str, source: str) -> Path:
    path = root / design_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _write_consumer(root: Path, rel: str, module: str, names: list[str]) -> None:
    """T-1625: a symbol only becomes part of a node's REQUIRED interface
    surface once some file owned by a DIFFERENT node imports it BY NAME
    (`_selfconform._cross_node_referenced_symbols`) -- every fixture below
    that wants a symbol to be required writes one of these alongside a
    `consumer` node in its design text."""
    src = f"from {module} import {', '.join(names)}\n"
    _write(root, rel, src)


class TestSyncInterfaceReport:
    """`sync_interface_report`'s pure-compute diff (never writes)."""

    def test_no_drift_reports_clean(self, tmp_path: Path):
        """A node whose declared `interface=` set already equals its
        REQUIRED (T-1625: real AND cross-node-referenced) surface, written
        in the compact T-1198 form, reports zero drift and an unchanged
        file."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_consumer(
            tmp_path, "src/frob/consumer/_use.py", "frob.widget._io", ["public_fn"]
        )
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=[\n"
            "        public_fn,\n"
            "    ];\n"
            "}\n"
            "node consumer : trusted {\n"
            '    code "src/frob/consumer/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not report.has_drift
        for file_result in report.files:
            assert not file_result.changed
            assert file_result.diffs == ()

    # frob:ticket T-1198
    def test_legacy_form_migrated_even_with_matching_symbol_set(
        self, tmp_path: Path
    ) -> None:
        """T-1198 one-time migration: a node already declared in the OLD
        one-line-per-symbol form, whose symbol SET already matches real,
        still gets rewritten into the compact `[...]` block -- format
        migration is not gated on symbol drift, or a repo would never
        get migrated off the legacy form."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_consumer(
            tmp_path, "src/frob/consumer/_use.py", "frob.widget._io", ["public_fn"]
        )
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=public_fn;\n"
            "}\n"
            "node consumer : trusted {\n"
            '    code "src/frob/consumer/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        file_result = report.files[0]
        assert file_result.changed
        assert "attr interface=[" in file_result.new_text
        assert "attr interface=public_fn;" not in file_result.new_text

    # frob:ticket T-1624
    def test_duplicate_blocks_collapsed_to_one(self, tmp_path: Path) -> None:
        """T-1624 regression: a node carrying TWO `interface=[...]` blocks
        (the shape `design/frob.strata` itself accumulated -- 45 duplicated
        blocks across ~17 nodes, byte-identical symbol sets) collapses down
        to exactly ONE block, even though the union of both blocks' symbol
        SET already equals real -- duplication itself must be flagged and
        fixed, not just a symbol mismatch."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_consumer(
            tmp_path, "src/frob/consumer/_use.py", "frob.widget._io", ["public_fn"]
        )
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            "    attr interface=[\n"
            "        public_fn,\n"
            "    ];\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=[\n"
            "        public_fn,\n"
            "    ];\n"
            "}\n"
            "node consumer : trusted {\n"
            '    code "src/frob/consumer/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        file_result = report.files[0]
        assert file_result.changed
        new_text = file_result.new_text
        assert new_text.count("attr interface=[") == 1
        assert new_text.count("public_fn") == 1

        # Idempotent: re-running against the corrected text finds no more
        # drift.
        _write_design(tmp_path, "design", "widget.strata", new_text)
        second = sync_interface_report(tmp_path)
        assert second.is_ok
        assert not second.danger_ok.has_drift

    # frob:ticket T-1624
    def test_comment_line_is_not_mistaken_for_a_block(self, tmp_path: Path) -> None:
        """The line-anchored span regexes must not fire on a `//` comment
        that merely LOOKS like an `attr interface=[...]` line -- this
        language has no block-comment form (only `//`-prefixed line
        comments, `strata-core/src/parse/lexer.rs`), so the open/close
        regexes are anchored on the full stripped line and a `//`-prefixed
        line can never match them; this pins that down as an explicit
        regression test rather than relying on the anchoring being
        obviously correct forever."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_consumer(
            tmp_path, "src/frob/consumer/_use.py", "frob.widget._io", ["public_fn"]
        )
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            "    // fake: attr interface=[\n"
            "    // fake:     phantom_from_comment,\n"
            "    // fake: ];\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=[\n"
            "        public_fn,\n"
            "    ];\n"
            "}\n"
            "node consumer : trusted {\n"
            '    code "src/frob/consumer/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        # No drift: the comment was never treated as a second span to
        # merge/replace, so the file is untouched byte-for-byte (the
        # comment text, including "phantom_from_comment", survives
        # verbatim -- this test is about the span-finder not treating it
        # as a DECLARATION, not about deleting comment text).
        assert not report.has_drift
        file_result = report.files[0]
        assert not file_result.changed
        assert file_result.new_text == file_result.old_text
        assert file_result.diffs == ()

    def test_addition_and_removal_detected(self, tmp_path: Path):
        """A node with an undeclared real symbol AND a declared-but-absent
        symbol reports both, sorted, and the rewritten text reflects the
        union of the real surface only."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "def public_fn():\n    pass\n\ndef new_fn():\n    pass\n",
        )
        _write_consumer(
            tmp_path,
            "src/frob/consumer/_use.py",
            "frob.widget._io",
            ["public_fn", "new_fn"],
        )
        design_path = _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=public_fn;\n"
            "    attr interface=phantom_fn;\n"
            "}\n"
            "node consumer : trusted {\n"
            '    code "src/frob/consumer/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        assert len(report.files) == 1
        file_result = report.files[0]
        assert file_result.changed
        assert file_result.path == "design/widget.strata"
        diffs = {d.node: d for d in file_result.diffs}
        assert diffs["widget"].added == ("new_fn",)
        assert diffs["widget"].removed == ("phantom_fn",)

        # The rewritten text declares exactly the real surface, sorted,
        # with every comment/other line untouched.
        new_text = file_result.new_text
        assert "new_fn," in new_text
        assert "phantom_fn" not in new_text
        assert "public_fn," in new_text
        assert "attr interface=[" in new_text
        assert 'code "src/frob/widget/**";' in new_text
        # Original file on disk is untouched (report never writes).
        assert design_path.read_text(encoding="utf-8") != new_text

    def test_store_block_missing_interface_attr_is_written(self, tmp_path: Path):
        """T-1425 regression: a `store <id> { ... }` block declaring its own
        `interface=` attrs used to be silently skipped by both the report
        and the writer (only `node` headers matched) even though
        `_interface_conformance_violations` (SYS104) already treats stores
        as first-class subjects via `model.nodes`. A store missing an
        `interface=` attr must now be detected AND rewritten, exactly like
        a node."""
        _write(
            tmp_path,
            "src/frob/widget/_store.py",
            "def public_fn():\n    pass\n",
        )
        _write_consumer(
            tmp_path, "src/frob/consumer/_use.py", "frob.widget._store", ["public_fn"]
        )
        design_path = _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "store widget_store : trusted {\n"
            "    engine sqlite;\n"
            '    code "src/frob/widget/**";\n'
            "}\n"
            "node consumer : trusted {\n"
            '    code "src/frob/consumer/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        file_result = report.files[0]
        assert file_result.changed
        diffs = {d.node: d for d in file_result.diffs}
        assert diffs["widget_store"].added == ("public_fn",)
        assert diffs["widget_store"].removed == ()

        new_text = file_result.new_text
        assert "attr interface=[" in new_text
        assert "public_fn," in new_text

        apply_sync_interface(tmp_path, report)
        assert design_path.read_text(encoding="utf-8") == new_text

    def test_missing_interface_block_is_inserted_after_header(self, tmp_path: Path):
        """A node with a non-empty real surface but zero declared
        `interface=` attrs yet gets its block inserted right after the
        node's opening line (module docstring's insertion convention)."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_consumer(
            tmp_path, "src/frob/consumer/_use.py", "frob.widget._io", ["public_fn"]
        )
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "}\n"
            "node consumer : trusted {\n"
            '    code "src/frob/consumer/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        file_result = report.files[0]
        lines = file_result.new_text.splitlines()
        header_idx = next(
            i for i, line in enumerate(lines) if line.strip().startswith("node widget")
        )
        assert lines[header_idx + 1].strip() == "attr interface=["
        assert "public_fn," in lines[header_idx + 2]

    # frob:tests \
    # tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_no_design_\
    # files_reports_empty
    def test_no_design_files_reports_empty(self, tmp_path: Path):
        """No `.strata` files at all under `design/` -- `Ok` with an empty
        file list, the same vacuous-but-honest posture every other
        design-loading entrypoint in this package takes, not an error."""
        (tmp_path / "design").mkdir()
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        assert result.danger_ok.files == ()

    # frob:tests \
    # tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_bad_design\
    # _file_propagates_load_error
    def test_bad_design_file_propagates_load_error(self, tmp_path: Path):
        """A `.strata` file that fails to parse surfaces as the
        underlying `DesignLoadError.error`, not silently skipped or
        folded into a clean report -- this is the REJECT path, distinct
        from every other case in this class which are all drift-clean or
        drift-dirty successes."""
        _write_design(tmp_path, "design", "bad.strata", "this is not valid strata {{{")
        result = sync_interface_report(tmp_path)
        assert result.is_err

    # frob:tests \
    # tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_ambiguous_\
    # code_binding_propagates_as_error
    def test_ambiguous_code_binding_propagates_as_error(self, tmp_path: Path):
        """Two nodes whose `code=` globs both match the same real file
        make `bind_code` itself fail -- `sync_interface_report` must
        propagate `Err(AmbiguousCodeBinding)` rather than silently
        computing drift off a partial/missing binding."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "}\n"
            "node widget_too : trusted {\n"
            '    code "src/frob/widget/*.py";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.AmbiguousCodeBinding

    # frob:tests \
    # tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_design_fil\
    # e_without_any_node_is_skipped
    def test_design_file_without_any_node_is_skipped(self, tmp_path: Path):
        """A `.strata` file present under `design/` but declaring no
        `node` at all (module-only) is skipped, not reported as a
        zero-node file result -- the `_NODE_HEADER_RE`/`"node "` early
        `continue` guard."""
        _write_design(tmp_path, "design", "empty.strata", "module empty\n")
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        assert result.danger_ok.files == ()


def test_report_and_apply_are_the_tier_a_ready_entry_points(tmp_path: Path):
    """T-1150 acceptance criterion 2 (disclosed deferral, see module
    docstring): `sync_interface_report` (pure compute) and
    `apply_sync_interface` (the only write) are the two functions a future
    T-1137 Tier-A fix-engine handler would call directly, with no
    intermediate CLI-only glue -- this pins that call shape so a future
    handler wiring does not have to rediscover it."""
    _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
    _write_consumer(
        tmp_path, "src/frob/consumer/_use.py", "frob.widget._io", ["public_fn"]
    )
    _write_design(
        tmp_path,
        "design",
        "widget.strata",
        "module widget\n"
        'node widget : trusted {\n    code "src/frob/widget/**";\n}\n'
        'node consumer : trusted {\n    code "src/frob/consumer/**";\n}\n',
    )
    result = sync_interface_report(tmp_path)
    assert result.is_ok
    report = result.danger_ok
    written = apply_sync_interface(tmp_path, report)
    assert written == ("design/widget.strata",)


class TestApplySyncInterface:
    """`apply_sync_interface`'s write side effect."""

    def test_writes_only_changed_files(self, tmp_path: Path):
        """Only files whose report entry is `changed` get written back;
        an unchanged file's mtime/content is left alone."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "def public_fn():\n    pass\n\ndef new_fn():\n    pass\n",
        )
        _write_consumer(
            tmp_path,
            "src/frob/consumer/_use.py",
            "frob.widget._io",
            ["public_fn", "new_fn"],
        )
        design_path = _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=public_fn;\n"
            "}\n"
            "node consumer : trusted {\n"
            '    code "src/frob/consumer/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        written = apply_sync_interface(tmp_path, report)
        assert written == ("design/widget.strata",)
        on_disk = design_path.read_text(encoding="utf-8")
        assert "new_fn," in on_disk

        # Re-running now reports clean and writes nothing.
        result2 = sync_interface_report(tmp_path)
        assert result2.is_ok
        assert not result2.danger_ok.has_drift
        written2 = apply_sync_interface(tmp_path, result2.danger_ok)
        assert written2 == ()


# Sanity: the fixture designs above actually parse/elaborate/bind cleanly
# through the same pipeline `sync_interface_report` uses internally, so a
# regression in that pipeline's own contract fails loudly here too rather
# than only inside `sync_interface_report`'s own error branches.
def test_fixture_design_binds_cleanly(tmp_path: Path):
    """Smoke test: the minimal fixture `.strata` text used above parses,
    elaborates, and binds without error -- guards against the tests above
    silently exercising only the "design failed to load" early-return."""
    _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
    text = (
        "module widget\n"
        "node widget : trusted {\n"
        '    code "src/frob/widget/**";\n'
        "    attr interface=public_fn;\n"
        "}\n"
    )
    parsed = parse_module(text)
    assert parsed.is_ok
    elaborated = elaborate(parsed.danger_ok)
    assert elaborated.is_ok
    bound = bind_code(elaborated.danger_ok, tmp_path)
    assert bound.is_ok
