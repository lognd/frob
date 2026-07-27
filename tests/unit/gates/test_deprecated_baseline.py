"""Tests for `frob.gates._deprecated_baseline` (T-0639): the DEPR005
committed reference-set baseline -- load/save round trip and the
shrink-only/seed-only tighten idiom."""

from __future__ import annotations

from pathlib import Path

from frob.gates._deprecated_baseline import (
    DeprecatedBaselineEntry,
    DeprecatedBaselineLock,
    load_deprecated_baseline,
    save_deprecated_baseline,
    tighten_deprecated_baseline,
)


class TestDeprecatedBaselineLock:
    """`DeprecatedBaselineLock.for_symbol`."""

    def test_for_symbol_missing_is_none(self) -> None:
        """T-0639: an un-baselined symbol resolves to `None`, not a crash."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedBaselineLock.test_for_symbol_missing_is_none  # noqa: E501
        lock = DeprecatedBaselineLock(
            entries=(DeprecatedBaselineEntry(symbol="a.py::foo", references=()),)
        )
        assert lock.for_symbol("b.py::bar") is None
        assert lock.for_symbol("a.py::foo") is not None


class TestLoadSave:
    """`load_deprecated_baseline`/`save_deprecated_baseline`."""

    def test_missing_file_is_empty(self, tmp_path: Path) -> None:
        """T-0639: no committed lock file yet is a valid, empty baseline."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestLoadSave.test_missing_file_is_empty  # noqa: E501
        lock = load_deprecated_baseline(tmp_path)
        assert lock.entries == ()

    def test_save_then_load_round_trips(self, tmp_path: Path) -> None:
        """T-0639: a saved lock loads back byte-identical in content, sorted
        deterministically."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestLoadSave.test_save_then_load_round_trips  # noqa: E501
        lock = DeprecatedBaselineLock(
            entries=(
                DeprecatedBaselineEntry(
                    symbol="src/a.py::helper", references=("src/b.py:3", "src/c.py:9")
                ),
            )
        )
        save_deprecated_baseline(tmp_path, lock)
        reloaded = load_deprecated_baseline(tmp_path)
        entry = reloaded.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.references == ("src/b.py:3", "src/c.py:9")

    def test_malformed_file_is_treated_as_empty(self, tmp_path: Path) -> None:
        """T-0639: unparseable JSON fails open to an empty baseline, never a
        crash -- mirrors `load_ratchet_lock`."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestLoadSave.test_malformed_file_is_treated_as_empty  # noqa: E501
        (tmp_path / "frob-deprecated-baseline.lock.json").write_text(
            "not json", encoding="utf-8"
        )
        assert load_deprecated_baseline(tmp_path).entries == ()


class TestTighten:
    """`tighten_deprecated_baseline`: seed-once, shrink-only, drop-if-gone."""

    def test_first_seen_symbol_is_seeded_whole(self, tmp_path: Path) -> None:
        """T-0639: a symbol never baselined before is accepted whole, not
        flagged -- legacy callers at declaration time are not "new"."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_first_seen_symbol_is_seeded_whole  # noqa: E501
        current = {"src/a.py::helper": frozenset({"src/b.py:1", "src/c.py:2"})}
        tightened = tighten_deprecated_baseline(tmp_path, current)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert set(entry.references) == {"src/b.py:1", "src/c.py:2"}

    def test_shrinkage_drops_stale_references(self, tmp_path: Path) -> None:
        """T-0639: a reference present in the baseline but no longer
        observed drops out -- the baseline auto-tightens."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_shrinkage_drops_stale_references  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper",
                        references=("src/b.py:1", "src/c.py:2"),
                    ),
                )
            ),
        )
        current = {"src/a.py::helper": frozenset({"src/b.py:1"})}
        tightened = tighten_deprecated_baseline(tmp_path, current)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.references == ("src/b.py:1",)

    def test_never_absorbs_a_new_reference(self, tmp_path: Path) -> None:
        """T-0639: a reference observed now but absent from the baseline is
        NOT silently absorbed -- tighten only ever shrinks an already-
        baselined entry, it never grows one."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_never_absorbs_a_new_reference  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper", references=("src/b.py:1",)
                    ),
                )
            ),
        )
        current = {"src/a.py::helper": frozenset({"src/b.py:1", "src/new.py:9"})}
        tightened = tighten_deprecated_baseline(tmp_path, current)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.references == ("src/b.py:1",)
        assert "src/new.py:9" not in entry.references

    def test_symbol_no_longer_deprecated_is_dropped(self, tmp_path: Path) -> None:
        """T-0639: a symbol baselined previously but absent from `current`
        (directive removed, or symbol deleted) drops out of the baseline
        entirely."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_symbol_no_longer_deprecated_is_dropped  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper", references=("src/b.py:1",)
                    ),
                )
            ),
        )
        tightened = tighten_deprecated_baseline(tmp_path, {})
        assert tightened.for_symbol("src/a.py::helper") is None
